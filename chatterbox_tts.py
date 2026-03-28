"""
chatterbox_tts.py -- CLI for Chatterbox TTS (rsxdalv/chatterbox@fast)

Zero-shot TTS with voice cloning and emotion exaggeration control.
MIT licensed. 0.5B Llama backbone. No gated HuggingFace repos.

QUICK START:
  python chatterbox_tts.py "Hello there, nice to meet you." --play
  python chatterbox_tts.py "I am so excited about this!" --exaggeration 0.8 --play
  python chatterbox_tts.py "Hey, how are you?" --voice reference.wav --play
  python chatterbox_tts.py --interactive

VOICE CLONING:
  Pass any WAV/MP3 (3-15s of clean speech) as --voice to clone that voice.
  Without --voice, the model uses its own built-in default voice.

  python chatterbox_tts.py "Hello!" --voice my_voice.wav --play

EMOTION CONTROL:
  --exaggeration   Controls emotional intensity of the speech.
                   0.25 = calm/neutral, 0.5 = default, 1.5+ = very dramatic
  --cfg-weight     Controls pacing stability.
                   Lower (~0.3) = more natural pacing (use with high exaggeration)
                   Higher (0.5) = more stable/slow

TIPS:
  Dramatic/expressive:     --exaggeration 0.7 --cfg-weight 0.3
  Calm/neutral narration:  --exaggeration 0.25 --cfg-weight 0.5
  Fast reference speaker:  --cfg-weight 0.3

NOTE:
  Chatterbox embeds an imperceptible neural watermark in every output (perth).
  This survives compression/editing and is detectable -- by design, for responsible AI.
"""

import argparse
import os
import sys
import time

import torch

# ── Optional playback ─────────────────────────────────────────────────────────
try:
    import sounddevice as sd
    _HAS_SOUNDDEVICE = True
except Exception:
    _HAS_SOUNDDEVICE = False

DEFAULT_EXAGGERATION = 0.5
DEFAULT_CFG_WEIGHT   = 0.5

_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model

    try:
        from chatterbox.tts import ChatterboxTTS
    except ImportError as e:
        print(
            f"ERROR: chatterbox-tts is not installed or failed to import.\n"
            f"  Details: {e}\n"
            f"  Re-run setup.ps1 to install.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        import torchaudio  # noqa: F401
    except ImportError:
        print(
            "ERROR: torchaudio is not installed.\n"
            "  Re-run setup.ps1 to install PyTorch.",
            file=sys.stderr,
        )
        sys.exit(1)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    print("Loading Chatterbox model (first run downloads ~1 GB) ...")
    _model = ChatterboxTTS.from_pretrained(device=device)
    print("  Model loaded.\n")
    return _model


def _generate(
    text: str,
    voice: str | None,
    exaggeration: float,
    cfg_weight: float,
    seed: int | None,
) -> tuple:
    """Returns (wav_tensor, sample_rate)."""
    if seed is not None:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

    model = _load_model()

    kwargs = dict(exaggeration=exaggeration, cfg_weight=cfg_weight)
    if voice is not None:
        if not os.path.isfile(voice):
            raise FileNotFoundError(f"Voice reference file not found: {voice}")
        kwargs["audio_prompt_path"] = voice

    # generate() is a generator that yields a single tensor
    wav = next(model.generate(text, **kwargs))
    return wav, model.sr


def _save(wav, sr: int, out_path: str | None) -> str:
    if out_path is None:
        session = int(time.time())
        out_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "output", f"session_{session}"
        )
        os.makedirs(out_dir, exist_ok=True)
        existing = [f for f in os.listdir(out_dir) if f.endswith(".wav")]
        idx = len(existing) + 1
        out_path = os.path.join(out_dir, f"{idx:03d}.wav")
    else:
        parent = os.path.dirname(os.path.abspath(out_path))
        os.makedirs(parent, exist_ok=True)

    # torchaudio.save requires torchcodec in newer torchaudio versions;
    # use soundfile directly to avoid that dependency.
    import soundfile as sf
    audio_np = wav.squeeze().cpu().numpy()
    sf.write(out_path, audio_np, sr)
    duration = wav.shape[-1] / sr
    print(f"  Saved -> {out_path}  ({duration:.2f}s)")
    return out_path


def _play(wav, sr: int) -> None:
    if not _HAS_SOUNDDEVICE:
        print("  (sounddevice not available -- open the WAV file manually)")
        return
    try:
        audio_np = wav.squeeze().cpu().numpy().astype("float32")
        print(f"  Playing ({len(audio_np) / sr:.2f}s)...")
        sd.play(audio_np, sr)
        sd.wait()
    except Exception as e:
        print(f"  Playback error: {e}")


def _run_once(args) -> None:
    t0 = time.time()
    wav, sr = _generate(
        text=args.text,
        voice=args.voice,
        exaggeration=args.exaggeration,
        cfg_weight=args.cfg_weight,
        seed=args.seed,
    )
    _save(wav, sr, args.out)
    print(f"  Generated in {time.time() - t0:.1f}s")
    if args.play:
        _play(wav, sr)


def _run_interactive(args) -> None:
    print("Chatterbox TTS -- interactive mode")
    print("  Commands:  /voice <path>         Set voice cloning reference (WAV/MP3)")
    print("             /voice clear          Clear voice (use default)")
    print("             /exaggeration <val>   Emotion intensity (default 0.5)")
    print("             /cfg <val>            Pacing/stability (default 0.5)")
    print("             /seed <n>             Set seed")
    print("             /noseed               Clear seed")
    print("             /play  /noplay        Toggle auto-playback")
    print("             /quit")
    print()
    if args.voice:
        print(f"  Voice: {args.voice}")
    print(f"  Exaggeration: {args.exaggeration}  cfg_weight: {args.cfg_weight}")
    print()

    voice       = args.voice
    exaggeration = args.exaggeration
    cfg_weight  = args.cfg_weight
    seed        = args.seed
    play        = args.play

    _load_model()

    while True:
        try:
            line = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue

        if line.startswith("/"):
            parts = line.split(None, 1)
            cmd = parts[0].lower()
            val = parts[1].strip() if len(parts) > 1 else ""

            if cmd == "/quit":
                break
            elif cmd == "/voice":
                if val.lower() == "clear" or not val:
                    voice = None
                    print("  voice cleared (using default)")
                else:
                    voice = val
                    print(f"  voice -> {voice}")
            elif cmd == "/exaggeration":
                try:
                    exaggeration = float(val)
                    print(f"  exaggeration -> {exaggeration}")
                except ValueError:
                    print("  Usage: /exaggeration <float>")
            elif cmd == "/cfg":
                try:
                    cfg_weight = float(val)
                    print(f"  cfg_weight -> {cfg_weight}")
                except ValueError:
                    print("  Usage: /cfg <float>")
            elif cmd == "/seed":
                try:
                    seed = int(val)
                    print(f"  seed -> {seed}")
                except ValueError:
                    print("  Usage: /seed <int>")
            elif cmd == "/noseed":
                seed = None
                print("  seed cleared")
            elif cmd == "/play":
                play = True
                print("  playback enabled")
            elif cmd == "/noplay":
                play = False
                print("  playback disabled")
            else:
                print(f"  Unknown command: {cmd}")
            continue

        t0 = time.time()
        try:
            wav, sr = _generate(
                text=line,
                voice=voice,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight,
                seed=seed,
            )
            _save(wav, sr, args.out)
            print(f"  Generated in {time.time() - t0:.1f}s")
            if play:
                _play(wav, sr)
        except Exception as e:
            print(f"  Error: {e}")

    print("Bye!")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chatterbox TTS CLI — zero-shot TTS with voice cloning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("text", nargs="?", help="Text to synthesize")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive prompt loop")
    parser.add_argument("--out", "-o", metavar="FILE", help="Output WAV path")
    parser.add_argument("--play", action="store_true", help="Play audio immediately after generation")
    parser.add_argument(
        "--voice", metavar="FILE",
        help="Reference audio file for voice cloning (WAV/MP3, 3-15s recommended)"
    )
    parser.add_argument(
        "--exaggeration", type=float, default=DEFAULT_EXAGGERATION, metavar="E",
        help=f"Emotion exaggeration intensity (default: {DEFAULT_EXAGGERATION}, range: 0.25-2.0)"
    )
    parser.add_argument(
        "--cfg-weight", type=float, default=DEFAULT_CFG_WEIGHT, metavar="W", dest="cfg_weight",
        help=f"CFG weight — lower = more natural pacing (default: {DEFAULT_CFG_WEIGHT})"
    )
    parser.add_argument(
        "--seed", type=int, default=None, metavar="N",
        help="Random seed for reproducibility"
    )

    args = parser.parse_args()

    if not args.interactive and not args.text:
        parser.print_help()
        sys.exit(0)

    if args.interactive:
        _run_interactive(args)
    else:
        _run_once(args)


if __name__ == "__main__":
    main()

# Chatterbox TTS — One-Click Windows Installer

Zero-shot TTS with **voice cloning** and **emotion exaggeration control**.  
Based on [rsxdalv/chatterbox@fast](https://github.com/rsxdalv/chatterbox/tree/fast) — a performance fork of [Resemble AI's Chatterbox](https://github.com/resemble-ai/chatterbox).  
MIT licensed. No HuggingFace login required.

---

## Quick Start

```powershell
# 1. Install (one-time, ~5 min + 1 GB download)
. .\setup.ps1

# 2. Basic TTS
python chatterbox_tts.py "Hello there, nice to meet you." --play

# 3. Expressive speech
python chatterbox_tts.py "I cannot believe this is happening!" --exaggeration 0.8 --play

# 4. Voice cloning (pass a 3-15s WAV of the target voice)
python chatterbox_tts.py "Hey, how are you?" --voice reference.wav --play

# 5. Interactive mode
python chatterbox_tts.py --interactive
```

WAV files are saved to `output/session_<timestamp>/NNN.wav` by default.

---

## Voice Cloning

Chatterbox can clone any voice from a short reference clip — no training needed.

- **Format:** WAV or MP3
- **Length:** 3–15 seconds recommended
- **Quality:** Clean speech, minimal background noise gives best results

```powershell
python chatterbox_tts.py "Your text here." --voice my_voice.wav --play
```

In interactive mode:
```
/voice C:\path\to\reference.wav
```

---

## Emotion Exaggeration Control

Chatterbox has two parameters for controlling expressiveness:

| Parameter | Default | Range | Effect |
|---|---|---|---|
| `--exaggeration` | `0.5` | `0.25 – 2.0` | Emotional intensity of the speech |
| `--cfg-weight` | `0.5` | `0.1 – 1.0` | Pacing stability (lower = more natural) |

### Presets

| Use case | Command |
|---|---|
| Calm / neutral narration | `--exaggeration 0.25 --cfg-weight 0.5` |
| Default (balanced) | `--exaggeration 0.5 --cfg-weight 0.5` |
| Expressive / emotional | `--exaggeration 0.7 --cfg-weight 0.3` |
| Very dramatic | `--exaggeration 1.5 --cfg-weight 0.3` |
| Fast reference speaker | `--cfg-weight 0.3` |

> **Tip:** High exaggeration tends to speed up speech. Lower `--cfg-weight` to compensate.

---

## Full CLI Reference

```
python chatterbox_tts.py <text> [options]
python chatterbox_tts.py --interactive

Positional:
  text                 Text to synthesize (use quotes)

Output:
  --out FILE, -o       Save to specific WAV path
  --play               Play audio immediately after generation

Voice:
  --voice FILE         Reference audio for voice cloning (WAV/MP3, 3-15s)
                       Omit to use the model's built-in default voice

Emotion:
  --exaggeration E     Emotional intensity (default: 0.5, range: 0.25-2.0)
  --cfg-weight W       Pacing stability (default: 0.5, lower = more natural)

Other:
  --seed N             Random seed for reproducibility
  --interactive, -i    Interactive prompt loop
```

### Interactive mode commands

```
/voice <path>          Set reference voice (WAV/MP3)
/voice clear           Clear voice (use default)
/exaggeration <val>    Change exaggeration
/cfg <val>             Change cfg_weight
/seed <n>              Set seed
/noseed                Clear seed
/play                  Enable auto-play
/noplay                Disable auto-play
/quit                  Exit
```

---

## Requirements

| Component | Requirement |
|---|---|
| Python | 3.10+ |
| GPU | NVIDIA with CUDA 12.8 drivers (`nvidia-smi` should show 12.x) |
| VRAM | ~2–4 GB (0.5B model, much lighter than most TTS models) |
| Disk | ~1 GB for model weights (downloaded to HuggingFace cache on first run) |
| Git | Required for `git+https://` install in `setup.ps1` |
| HuggingFace | No account or login needed — model is public |

---

## Key Details

- **Architecture:** 0.5B Llama backbone + flow-matching vocoder
- **Voice cloning:** Zero-shot — reference audio at inference time, no fine-tuning
- **Sample rate:** 24 kHz
- **Watermarking:** Every output contains an imperceptible neural watermark (perth). This is a responsible AI feature — detectable but doesn't affect audio quality.
- **License:** MIT

---

## How It Works

1. Text → tokenized and conditioned on a reference audio clip (or default voice embedding)
2. Llama backbone generates a latent speech representation with alignment-informed inference
3. Flow-matching vocoder decodes the latent → PCM audio at 24 kHz
4. Exaggeration and cfg_weight control the sampling process to tune expressiveness vs. stability

# setup.ps1 -- One-click Windows setup for Chatterbox TTS
# Run from the ChatterboxTTS folder:
#   . .\setup.ps1   (dot-source to activate venv in current shell)
#
# What it does:
#   1. Creates a Python virtual environment
#   2. Installs PyTorch with CUDA 12.8
#   3. Installs chatterbox-tts from rsxdalv/chatterbox@fast (performance fork)
#      Pins transformers<5.0  (chatterbox incompatible with transformers 5.x)
#   4. Installs sounddevice for --play support
#
# Requirements:
#   - Python 3.10+
#   - NVIDIA GPU + CUDA 12.8 drivers  (nvidia-smi should show 12.x)
#   - Git installed and in PATH        (git --version)
#
# Model downloads automatically on first run (~1 GB -- no HuggingFace login needed).

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT = $PSScriptRoot

# ── 1. Create venv ────────────────────────────────────────────────────────────
if (Test-Path "$ROOT\venv\Scripts\python.exe") {
    Write-Host "[1/4] venv already exists -- skipping" -ForegroundColor Cyan
} else {
    Write-Host "[1/4] Creating virtual environment..." -ForegroundColor Cyan
    python -m venv "$ROOT\venv"
    if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
}

$PIP    = "$ROOT\venv\Scripts\pip.exe"
$PYTHON = "$ROOT\venv\Scripts\python.exe"

# ── 2. Upgrade pip + install PyTorch with CUDA 12.8 ──────────────────────────
Write-Host "[2/4] Installing PyTorch (CUDA 12.8)..." -ForegroundColor Cyan
& $PYTHON -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }

& $PIP install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
if ($LASTEXITCODE -ne 0) { throw "PyTorch install failed" }

# ── 3. Install Chatterbox from rsxdalv/chatterbox@fast ───────────────────────
# Installs from the 'fast' branch which has performance improvements over
# the upstream resemble-ai release. Requires git in PATH.
# Pin transformers to <5.0 -- chatterbox uses is_flash_attn_greater_or_equal_2_10
# which was removed in transformers 5.x.
Write-Host "[3/4] Installing Chatterbox TTS (fast branch)..." -ForegroundColor Cyan
& $PIP install "git+https://github.com/rsxdalv/chatterbox.git@fast"
if ($LASTEXITCODE -ne 0) {
    Write-Host "  git install failed. Falling back to PyPI release..." -ForegroundColor Yellow
    & $PIP install chatterbox-tts
    if ($LASTEXITCODE -ne 0) { throw "Chatterbox install failed" }
}
# Downgrade transformers if needed (chatterbox incompatible with transformers 5.x)
& $PIP install "transformers>=4.43.0,<5.0"
if ($LASTEXITCODE -ne 0) { throw "transformers pin failed" }

# ── 4. Install extras ─────────────────────────────────────────────────────────
Write-Host "[4/4] Installing extras (sounddevice)..." -ForegroundColor Cyan
& $PIP install sounddevice
if ($LASTEXITCODE -ne 0) {
    Write-Host "  sounddevice install failed (--play won't work, but TTS will)" -ForegroundColor Yellow
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""

# Activate the venv in the current shell (only works when dot-sourced: . .\setup.ps1)
. "$ROOT\venv\Scripts\Activate.ps1"
Write-Host "Venv activated." -ForegroundColor Green
Write-Host ""
Write-Host "Quick start:" -ForegroundColor Yellow
Write-Host '  python chatterbox_tts.py "Hello there, nice to meet you." --play'
Write-Host '  python chatterbox_tts.py "I am so excited about this!" --exaggeration 0.8 --play'
Write-Host '  python chatterbox_tts.py "Hey, how are you?" --voice reference.wav --play'
Write-Host '  python chatterbox_tts.py --interactive'
Write-Host ""
Write-Host "Voice cloning:  --voice <path_to_wav>    (3-15s clean speech)" -ForegroundColor DarkGray
Write-Host "Exaggeration:   --exaggeration 0.25-2.0  (default: 0.5)"       -ForegroundColor DarkGray
Write-Host "CFG weight:     --cfg-weight 0.1-1.0     (default: 0.5)"       -ForegroundColor DarkGray
Write-Host ""
Write-Host "Note: First run downloads ~1 GB from HuggingFace (cached, only downloaded once)." -ForegroundColor DarkGray
Write-Host "      No HuggingFace login required -- model is public."                           -ForegroundColor DarkGray

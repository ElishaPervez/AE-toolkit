# AMV Toolkit

**Audio & Media Video Toolkit** - A TUI app for YouTube downloading, AI-powered vocal separation, and audio conversion. Supports both CPU and NVIDIA GPU acceleration.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Features

- **Download from YouTube** - Videos (MP4) or Audio (WAV) via yt-dlp
- **Extract Vocals** - AI-powered vocal/instrumental separation
- **Convert to WAV** - Re-encode any media file (video or audio) to PCM WAV via ffmpeg
- **GPU + CPU Support** - Auto-detects NVIDIA GPUs, easy one-click switching between GPU and CPU dependencies

## Hardware Support

| Mode | Device | Model | Notes |
|------|--------|-------|-------|
| **GPU** | NVIDIA (CUDA) | BS-Roformer (Best Quality) FP16 | Requires CUDA 12.8+ for RTX 50 series |
| **CPU** | Any | Kim Vocal 2 (ONNX) FP32 | No GPU required |

The app auto-detects your hardware on launch. You can switch between CPU and GPU modes from the Settings screen, which handles installing/uninstalling the correct dependencies.

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/ElishaPervez/AE-toolkit.git
cd AE-toolkit
pip install -r requirements.txt
```

### 2. Setup

```bash
python main.py
```

Navigate to **Settings > Setup** to install dependencies for your hardware (CPU or GPU).

### 3. Launch

```bash
python main.py
```

## Requirements

- Python 3.10+
- ffmpeg (for Convert to WAV)
- NVIDIA GPU + CUDA 12.8+ (optional, for GPU mode)

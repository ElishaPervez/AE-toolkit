# 🎬 AMV Toolkit (CPU Only)

**Audio & Media Video Toolkit** - A unified CLI for YouTube downloading and AI-powered audio separation, built for CPU-only environments.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ Features

- 📺 **Download from YouTube** - Videos (MP4) or Audio (WAV)
- 🎚️ **Extract Vocals** - AI-powered vocal/instrumental separation
- 🧠 **CPU-Only Pipeline** - Stable FP32 inference without GPU dependencies

## 🚀 Quick Start (CPU Only)

### 1. Clone & Install

```bash
git clone https://github.com/ElishaPervez/amv-script.git
cd amv-script
pip install -r requirements.txt
```

### 2. System Setup (CPU Only)

```bash
python main.py setup
```

> [!IMPORTANT]
> This project runs in CPU-only mode; no CUDA setup is required.

### 3. Launch

```bash
python main.py
```

## 📁 Project Structure

```
amv-script/
├── main.py              # Entry point
├── requirements.txt     # Python dependencies
├── amv.bat              # Windows launcher
├── amv/                 # Core Package
│   ├── infrastructure/  # Hardware detection & Setup
│   ├── features/        # YouTube & Separation logic
│   └── ui/             # TUI components
└── models/              # AI models (User Provided)
```

## 🎵 Supported Models

Place your models in the `models/` folder.

| Model | Type | Architecture Mode |
|-------|------|-------------------|
| **Kim Vocal 2** | ONNX | **CPU** (FP32/Single) |

## ⚡ Hardware Support

This project runs in **CPU-only** mode. GPU acceleration paths have been removed.

## 📋 Commands

```bash
python main.py              # Interactive menu
python main.py download     # YouTube menu
python main.py vocals       # Separation menu
```


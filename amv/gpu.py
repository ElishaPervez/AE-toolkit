# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - GPU Detection Utilities
# ═══════════════════════════════════════════════════════════════════════════════

import sys
import subprocess


def check_nvidia_gpu() -> str | None:
    """Run nvidia-smi and return GPU name, or None if not available."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")[0].strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def get_torch_install_cmd(gpu: bool) -> list[str]:
    """Return pip install args for PyTorch (cu128 for GPU, cpu otherwise).

    Returns a list of args safe for subprocess (handles paths with spaces).
    """
    base = [sys.executable, "-m", "pip", "install",
            "torch", "torchvision", "torchaudio", "--index-url"]
    if gpu:
        return base + ["https://download.pytorch.org/whl/cu128"]
    return base + ["https://download.pytorch.org/whl/cpu"]


def get_gpu_switch_cmds() -> list[list[str]]:
    """Full command sequence to switch from CPU to GPU (RTX 50 series / cu128).

    Returns list of arg-lists safe for subprocess (handles paths with spaces).
    1. Uninstall CPU-only torch
    2. Install CUDA 12.8 torch (SM_120 Blackwell support)
    3. Install audio-separator with GPU extras
    
    Note: onnxruntime is NOT uninstalled because audio-separator still needs it internally.
    """
    py = sys.executable
    return [
        [py, "-m", "pip", "uninstall", "-y", "torch", "torchvision", "torchaudio"],
        [py, "-m", "pip", "install", "torch", "torchvision", "torchaudio",
         "--index-url", "https://download.pytorch.org/whl/cu128"],
        [py, "-m", "pip", "install", "audio-separator[gpu]"],
    ]


def get_cpu_switch_cmds() -> list[list[str]]:
    """Full command sequence to switch from GPU to CPU.

    Returns list of arg-lists safe for subprocess (handles paths with spaces).
    1. Uninstall CUDA torch
    2. Install CPU-only torch
    3. Install onnxruntime for ONNX model support
    """
    py = sys.executable
    return [
        [py, "-m", "pip", "uninstall", "-y", "torch", "torchvision", "torchaudio"],
        [py, "-m", "pip", "install", "torch", "torchvision", "torchaudio",
         "--index-url", "https://download.pytorch.org/whl/cpu"],
        [py, "-m", "pip", "install", "onnxruntime"],
        [py, "-m", "pip", "install", "audio-separator"],
    ]


def verify_cuda_torch() -> bool:
    """Return True if PyTorch is installed and CUDA is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False

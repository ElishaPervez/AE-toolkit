# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Hardware Detection (CPU + GPU)
# Detects GPU via torch.cuda when available, falls back to nvidia-smi
# ═══════════════════════════════════════════════════════════════════════════════

# Lazy-loaded global state
_CACHE = {
    "checked": False,
    "torch_available": False,
    "torch_version": None,
    "ort_available": False,
    "ort_version": None,
    "gpu_type": "cpu",
    "gpu_name": "CPU",
    "gpu_vram": None,
    "hw_info": None,
    "accel": None
}

def _ensure_init():
    """Perform hardware detection if not already done."""
    if _CACHE["checked"]:
        return

    from .config import load_config
    config = load_config()
    force_cpu = config.get("force_cpu", False)

    # Check torch availability
    try:
        import torch
        _CACHE["torch_available"] = True
        _CACHE["torch_version"] = torch.__version__
    except ImportError:
        _CACHE["torch_available"] = False
        _CACHE["torch_version"] = None

    # Check ONNX Runtime availability WITHOUT loading the DLL
    # Using find_spec avoids locking the DLL, which prevents pip install issues
    try:
        import importlib.util
        spec = importlib.util.find_spec("onnxruntime")
        if spec is not None:
            _CACHE["ort_available"] = True
            # Get version without full import (read from metadata)
            try:
                from importlib.metadata import version
                _CACHE["ort_version"] = version("onnxruntime")
            except Exception:
                _CACHE["ort_version"] = "installed"
        else:
            _CACHE["ort_available"] = False
            _CACHE["ort_version"] = None
    except Exception:
        _CACHE["ort_available"] = False
        _CACHE["ort_version"] = None

    # GPU detection - only attempt when not forced to CPU
    gpu_detected = False
    if not force_cpu:
        # Primary: torch.cuda (only works when CUDA torch is installed)
        if _CACHE["torch_available"]:
            import torch
            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                gpu_name = torch.cuda.get_device_name(0)
                vram_bytes = props.total_memory
                sm = (props.major, props.minor)

                vram_str = f"{vram_bytes / (1024**3):.1f} GB"

                _CACHE["gpu_type"] = "nvidia"
                _CACHE["gpu_name"] = gpu_name
                _CACHE["gpu_vram"] = vram_str

                _CACHE["hw_info"] = {
                    "device": gpu_name,
                    "device_short": "CUDA",
                    "gpu_type": "nvidia",
                    "tensor_cores": sm >= (7, 0),
                    "fp16_capable": sm >= (7, 0),
                    "fp8_capable": sm >= (8, 9),
                    "sm": sm,
                    "provider": "CUDAExecutionProvider",
                    "vram": vram_str
                }

                _CACHE["accel"] = {
                    "enabled": True,
                    "fp16": sm >= (7, 0),
                    "fp8": sm >= (8, 9),
                    "batch_size": 1
                }

                gpu_detected = True

        # Fallback: nvidia-smi (GPU exists but CUDA torch not installed yet)
        if not gpu_detected:
            from .gpu import check_nvidia_gpu
            nvidia_name = check_nvidia_gpu()
            if nvidia_name:
                _CACHE["gpu_type"] = "nvidia"
                _CACHE["gpu_name"] = nvidia_name

                _CACHE["hw_info"] = {
                    "device": f"{nvidia_name} (CUDA torch not installed)",
                    "device_short": "GPU (no CUDA torch)",
                    "gpu_type": "nvidia",
                    "tensor_cores": False,
                    "fp16_capable": False,
                    "fp8_capable": False,
                    "provider": "CPU (run Setup to install CUDA)",
                    "vram": None
                }

                _CACHE["accel"] = {
                    "enabled": False,
                    "fp16": False,
                    "fp8": False,
                    "batch_size": 1
                }

                gpu_detected = True

    if not gpu_detected:
        _CACHE["gpu_type"] = "cpu"
        _CACHE["gpu_name"] = "CPU (Forced)" if force_cpu else "CPU"
        _CACHE["gpu_vram"] = None

        _CACHE["hw_info"] = {
            "device": _CACHE["gpu_name"],
            "device_short": "CPU",
            "gpu_type": "cpu",
            "tensor_cores": False,
            "fp16_capable": False,
            "fp8_capable": False,
            "provider": "CPUExecutionProvider" if _CACHE["ort_available"] else "CPU",
            "vram": None
        }

        _CACHE["accel"] = {
            "enabled": False,
            "fp16": False,
            "fp8": False,
            "batch_size": 1
        }

    _CACHE["checked"] = True

def get_gpu_type():
    _ensure_init()
    return _CACHE["gpu_type"]

def get_hw_info():
    _ensure_init()
    return _CACHE["hw_info"]

def get_accel():
    _ensure_init()
    return _CACHE["accel"]

def get_torch_status():
    _ensure_init()
    return _CACHE["torch_available"], _CACHE["torch_version"]

def get_ort_status():
    _ensure_init()
    return _CACHE["ort_available"], _CACHE["ort_version"]

def refresh_vram():
    """Force re-detection and return current hardware info."""
    _CACHE["checked"] = False
    _ensure_init()
    return _CACHE["hw_info"]

def get_suggested_setup():
    """Get the suggested setup based on detected hardware."""
    _ensure_init()
    if _CACHE["gpu_type"] == "nvidia":
        return "gpu", f"GPU mode ({_CACHE['gpu_name']})"
    return "cpu", "CPU-only mode"

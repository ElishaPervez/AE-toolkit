# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Hardware Status (CPU Only)
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

    _CACHE["gpu_type"] = "cpu"
    _CACHE["gpu_name"] = "CPU (Forced)" if force_cpu else "CPU"
    _CACHE["gpu_vram"] = None

    try:
        import torch
        _CACHE["torch_available"] = True
        _CACHE["torch_version"] = torch.__version__
    except ImportError:
        _CACHE["torch_available"] = False
        _CACHE["torch_version"] = None

    try:
        import onnxruntime as ort
        _CACHE["ort_available"] = True
        _CACHE["ort_version"] = ort.__version__
    except ImportError:
        _CACHE["ort_available"] = False
        _CACHE["ort_version"] = None

    info = {
        "device": _CACHE["gpu_name"] or "CPU",
        "device_short": "CPU",
        "gpu_type": "cpu",
        "tensor_cores": False,
        "fp16_capable": False,
        "fp8_capable": False,
        "provider": "CPUExecutionProvider" if _CACHE["ort_available"] else "CPU",
        "vram": None
    }

    _CACHE["hw_info"] = info

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
    """Return current hardware info."""
    if not _CACHE["checked"]:
        _ensure_init()

    return _CACHE["hw_info"]

def get_suggested_setup():
    """Get the suggested setup (CPU only)."""
    return "cpu", "CPU-only mode"

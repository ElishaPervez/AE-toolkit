# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Model Configurations
# ═══════════════════════════════════════════════════════════════════════════════
"""
Per-model settings for CPU and GPU execution.
Auto-selects the best model based on detected hardware.
"""

MODEL_PRESETS = {
    "Kim_Vocal_2.onnx": {
        "name": "Kim Vocal 2 (ONNX)",
        "type": "onnx",
        "cpu": {"fp16": False, "batch_size": 1},
    },
    "model_bs_roformer_ep_317_sdr_12.9755.ckpt": {
        "name": "BS-Roformer (Best Quality)",
        "type": "pytorch",
        "cpu": {"fp16": False, "batch_size": 1},
        "gpu": {"fp16": True, "batch_size": 1},
    },
}

BS_ROFORMER = "model_bs_roformer_ep_317_sdr_12.9755.ckpt"
KIM_VOCAL_2 = "Kim_Vocal_2.onnx"


def get_active_model(hw_info: dict) -> str:
    """Auto-select the best model based on hardware.

    GPU with CUDA torch → BS-Roformer (best quality, leverages CUDA FP16)
    CPU or GPU without CUDA → Kim Vocal 2 ONNX (lighter, ONNX runtime)
    """
    # Only use BS-Roformer if GPU is available AND CUDA torch is installed (fp16_capable)
    # When GPU is detected via nvidia-smi but no CUDA torch, fp16_capable is False
    if hw_info.get("gpu_type") != "cpu" and hw_info.get("fp16_capable"):
        return BS_ROFORMER
    return KIM_VOCAL_2


def get_model_settings(model_filename: str, hw_info: dict | None = None) -> dict:
    """Get runtime settings for a model based on available hardware.

    Args:
        model_filename: The model file name key.
        hw_info: Hardware info dict from get_hw_info(). If None, returns CPU settings.

    Returns:
        Dict with fp16 and batch_size keys.
    """
    preset = MODEL_PRESETS.get(model_filename)
    if preset is None:
        return {"fp16": False, "batch_size": 1}

    # Use GPU settings if GPU available and preset has GPU config
    if hw_info and hw_info.get("gpu_type") != "cpu" and "gpu" in preset:
        return preset["gpu"].copy()

    return preset["cpu"].copy()


def get_model_display_name(model_filename: str) -> str:
    """Get display name for a model."""
    preset = MODEL_PRESETS.get(model_filename)
    if preset:
        return preset["name"]
    return model_filename

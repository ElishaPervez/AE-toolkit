# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Model Configurations
# ═══════════════════════════════════════════════════════════════════════════════
"""
Per-model settings for CPU-only execution.
"""

# Hardcoded to only use Kim Vocal 2 as requested
MODEL_PRESETS = {
    "Kim_Vocal_2.onnx": {
        "name": "Kim Vocal 2 (Anime/High Pitch - Improved)",
        "type": "onnx",
        "cpu": {"fp16": False, "batch_size": 1},
    },
}

def get_model_settings(model_filename: str) -> dict:
    """Get CPU-only settings for Kim Vocal 2."""
    return {"fp16": False, "batch_size": 1}

def get_model_display_name(model_filename: str) -> str:
    """Get display name for Kim Vocal 2."""
    return "Kim Vocal 2 (Anime/High Pitch - Improved)"


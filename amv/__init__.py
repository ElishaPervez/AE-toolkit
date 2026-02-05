# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit Package
# ═══════════════════════════════════════════════════════════════════════════════

"""
AMV Toolkit - Audio & Media Video Toolkit

A unified TUI for YouTube downloading and AI-powered audio separation.
Now with mouse support powered by Textual!
"""

__version__ = "2.0.0"
__author__ = "AMV Toolkit"

from .config import MODELS_DIR, get_output_dirs, ensure_output_dirs
from .hardware import get_hw_info, get_accel, get_gpu_type


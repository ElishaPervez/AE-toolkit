# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Audio Separation (UVR Engine)
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import io
import re
import logging
from typing import Callable, Optional

from .config import MODELS_DIR, ensure_output_dirs, add_recent_file
from .models import get_model_settings, get_active_model
from .hardware import get_hw_info


class TqdmCapture(io.StringIO):
    """Capture stderr to parse tqdm progress and call a callback."""

    # Regex to match tqdm output: "30%|████| 3/10 [00:08<00:19, 2.74s/it]"
    TQDM_PATTERN = re.compile(r'(\d+)%\|')

    def __init__(self, callback: Optional[Callable[[int, str], None]] = None, original_stderr=None):
        super().__init__()
        self.callback = callback
        self.original_stderr = original_stderr or sys.__stderr__
        self.last_percent = -1

    def write(self, text: str) -> int:
        # Always write to original stderr so console still shows output
        if self.original_stderr:
            self.original_stderr.write(text)

        # Try to extract progress percentage
        if self.callback and text.strip():
            match = self.TQDM_PATTERN.search(text)
            if match:
                percent = int(match.group(1))
                if percent != self.last_percent:
                    self.last_percent = percent
                    self.callback(percent, text.strip())

        return super().write(text)

    def flush(self):
        if self.original_stderr:
            self.original_stderr.flush()
        super().flush()


def run_separation(
    input_file: str,
    model_name: str = None,
    progress_callback: Optional[Callable[[str, int, str], None]] = None
) -> bool:
    """
    Run AI-powered audio separation.

    Args:
        input_file: Path to input audio file
        model_name: Name of the separation model to use (auto-detected if None)
        progress_callback: Optional callback(stage, percent, message) for progress updates
                          stage: 'loading', 'processing', 'finalizing'
                          percent: 0-100 or -1 for indeterminate
                          message: Status message
    """
    from audio_separator.separator import Separator

    # Detect hardware and auto-select model
    hw = get_hw_info()
    if model_name is None:
        model_name = get_active_model(hw)
    model_settings = get_model_settings(model_name, hw)

    input_dir = os.path.dirname(input_file)
    input_filename = os.path.basename(input_file)
    input_stem, input_ext = os.path.splitext(input_filename)

    # Clean output setup
    ensure_output_dirs()
    output_dir = input_dir

    try:
        from pydub import AudioSegment
        PYDUB_OK = True
    except ImportError:
        PYDUB_OK = False

    temp_input_path = None
    processing_input = input_file
    is_padded = False
    original_duration_ms = 0

    try:
        # Padding logic (Silent background op)
        if PYDUB_OK:
            audio = AudioSegment.from_file(input_file)
            original_duration_ms = len(audio)
            if original_duration_ms < 10000:
                padding = 10000 - original_duration_ms + 1000
                padded = audio + AudioSegment.silent(duration=padding)
                temp_input_path = os.path.join(output_dir, f"temp_{input_filename}")
                padded.export(temp_input_path, format="wav")
                processing_input = temp_input_path
                is_padded = True

        # Configure Engine
        mdx_params = {}
        vr_params = {}
        if model_settings["fp16"]: mdx_params["enable_fp16"] = True
        if model_settings["batch_size"] > 1:
            mdx_params["batch_size"] = model_settings["batch_size"]
            vr_params["batch_size"] = model_settings["batch_size"]

        # Quiet logging
        sep_config = {
            "log_level": logging.ERROR, # Hide verbose library logs
            "model_file_dir": MODELS_DIR,
            "output_dir": output_dir,
        }
        if mdx_params: sep_config["mdx_params"] = mdx_params
        if vr_params: sep_config["vr_params"] = vr_params

        # Enable FP16 autocast for GPU models
        if model_settings.get("fp16") and hw.get("gpu_type") != "cpu":
            sep_config["use_autocast"] = True

        separator = Separator(**sep_config)

        # Notify loading stage
        if progress_callback:
            progress_callback('loading', -1, 'Loading AI model...')

        separator.load_model(model_filename=model_name)

        # Notify processing stage
        if progress_callback:
            device_label = "CUDA (FP16)" if hw.get("gpu_type") != "cpu" and hw.get("fp16_capable") and model_settings.get("fp16") else "CPU"
            progress_callback('processing', 0, f'Processing on {device_label}...')

        # Capture tqdm output for progress
        def on_tqdm_progress(percent: int, raw_text: str):
            if progress_callback:
                progress_callback('processing', percent, f'{percent}% complete')

        # Wrap separation with stderr capture
        original_stderr = sys.stderr
        capture = TqdmCapture(callback=on_tqdm_progress, original_stderr=original_stderr)
        try:
            sys.stderr = capture
            output_files = separator.separate(processing_input)
        finally:
            sys.stderr = original_stderr

        if not output_files:
            raise RuntimeError("Separation produced no output files")

        # Post-process
        clean_stem = input_stem.replace(" (original)", "")

        # Backup Original
        if "(original)" not in input_stem:
            bkp = os.path.join(input_dir, f"{input_stem} (original){input_ext}")
            if not os.path.exists(bkp):
                try:
                    os.rename(input_file, bkp)
                except OSError as e:
                    logging.warning(f"Could not backup original file: {e}")

        generated_files = []
        for f in output_files:
            src = os.path.join(output_dir, f)
            if not os.path.exists(src): continue

            # Trim
            if is_padded and PYDUB_OK:
                try:
                    AudioSegment.from_file(src)[:original_duration_ms].export(src, format="wav")
                except Exception as e:
                    logging.warning(f"Could not trim padded audio: {e}")

            # Rename
            suffix = "[instrumental]"
            if "vocal" in f.lower(): suffix = "[vocals]"

            dst_name = f"{clean_stem} {suffix}{input_ext}"
            dst = os.path.join(input_dir, dst_name)

            if os.path.exists(dst): os.remove(dst)
            os.rename(src, dst)
            generated_files.append(f"{suffix}: {dst_name}")

        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)

        # Add to recents
        add_recent_file(input_file)

        # Cleanup GPU VRAM
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

        return True

    except Exception as e:
        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
        # Cleanup GPU VRAM on error too
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        raise

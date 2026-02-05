# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Audio Separation (UVR Engine)
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import io
import re
import glob
import logging
import threading
import questionary
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from typing import Callable, Optional

from .config import MODELS_DIR, KNOWN_MODELS, ensure_output_dirs, add_recent_file, get_recent_files
from .models import get_model_settings, get_model_display_name
from .ui import console, show_hw_status, safe_str

def get_models():
    """Get available separation models."""
    from .models import MODEL_PRESETS
    if not os.path.exists(MODELS_DIR):
        return []
    files = []
    for ext in ['*.ckpt', '*.onnx', '*.yaml', '*.pth']:
        files.extend(glob.glob(os.path.join(MODELS_DIR, ext)))
    choices = []
    for path in files:
        name = os.path.basename(path)
        if name.endswith('.json'):
            continue
        display = KNOWN_MODELS.get(name, name)
        
        # Add emoji prefix
        display = f"❄️ {display}"
        
        choices.append(questionary.Choice(display, value=name))
    choices.sort(key=lambda x: x.value not in KNOWN_MODELS)
    return choices

def scan_for_audio_files(scan_deep=False):
    """
    Get file choices: Recent files + option to scan.
    
    Args:
        scan_deep: If True, perform the deep recursive scan.
    """
    choices = []
    
    # 1. Add Recent Files
    recents = get_recent_files()
    if recents:
        choices.append(questionary.Separator("--- Recent Files ---"))
        for path in recents:
            if os.path.exists(path):
                display = f"⭐ {os.path.basename(path)}  [dim]({os.path.dirname(path)})[/dim]"
                choices.append(questionary.Choice(display, value=path))
    
    # 2. Options to scan
    choices.append(questionary.Separator("--- Actions ---"))
    
    if not scan_deep:
        choices.append(questionary.Choice("🔍 Scan recursive (may be slow)", value="scan_deep"))
    
    # 3. If deep scan requested
    if scan_deep:
        console.print("[dim]Scanning directory structure...[/dim]")
        extensions = ['wav', 'mp3', 'flac', 'm4a']
        
        # Use original directory where user ran the command
        original_dir = os.environ.get('AMV_ORIGINAL_DIR', os.getcwd())
        
        seen_paths = set(recents) # Don't duplicate recents
        
        found_count = 0
        for ext in extensions:
            pattern = os.path.join(original_dir, '**', f'*.{ext}')
            for f in glob.glob(pattern, recursive=True):
                abs_path = os.path.abspath(f)
                if abs_path in seen_paths: continue
                
                # Filter already-processed
                f_lower = f.lower()
                if "[vocals]" in f_lower or "[instrumental]" in f_lower or "[music]" in f_lower:
                    continue
                
                seen_paths.add(abs_path)
                parent_dir = os.path.basename(os.path.dirname(f))
                display_name = f"{os.path.basename(f)}  [dim]({parent_dir})[/dim]"
                choices.append(questionary.Choice(display_name, value=abs_path))
                found_count += 1
                
        if found_count == 0:
            console.print("[yellow]No new audio files found.[/yellow]")
            
    return choices


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
    model_name: str, 
    progress_callback: Optional[Callable[[str, int, str], None]] = None
) -> bool:
    """
    Run AI-powered audio separation with clean UI.
    
    Args:
        input_file: Path to input audio file
        model_name: Name of the separation model to use
        progress_callback: Optional callback(stage, percent, message) for progress updates
                          stage: 'loading', 'processing', 'finalizing'
                          percent: 0-100 or -1 for indeterminate
                          message: Status message
    """
    from audio_separator.separator import Separator
    
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

    console.print()
    show_hw_status()
    
    # Setup params
    model_settings = get_model_settings(model_name)
    
    # Cleaner log info
    console.print(f"  [dim]Config: FP16={'ON' if model_settings['fp16'] else 'OFF'} | Batch={model_settings['batch_size']}[/dim]\n")
    
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

        separator = Separator(**sep_config)

        # Notify loading stage
        if progress_callback:
            progress_callback('loading', -1, 'Loading AI model...')
        else:
            console.print("[cyan]Loading AI Model...[/cyan] [dim](First run may take ~30s for optimization)[/dim]")
        
        separator.load_model(model_filename=model_name)
        
        # Notify processing stage
        if progress_callback:
            progress_callback('processing', 0, 'Starting separation...')
        else:
            console.print("[cyan]Starting Separation...[/cyan]")
        
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
            console.print("[bold red]❌ Separation failed[/bold red]")
            return False

        # Post-process
        clean_stem = input_stem.replace(" (original)", "")
        
        # Backup Original
        if "(original)" not in input_stem:
            bkp = os.path.join(input_dir, f"{input_stem} (original){input_ext}")
            if not os.path.exists(bkp):
                try: os.rename(input_file, bkp)
                except: pass

        generated_files = []
        for f in output_files:
            src = os.path.join(output_dir, f)
            if not os.path.exists(src): continue
            
            # Trim
            if is_padded and PYDUB_OK:
                try:
                    AudioSegment.from_file(src)[:original_duration_ms].export(src, format="wav")
                except: pass
                
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

        # Summary
        console.print(Panel.fit(
            f"[bold green]✅ Success![/bold green]\n\n" + "\n".join(generated_files),
            border_style="green"
        ))
        
        # Add to recents
        add_recent_file(input_file)
        
        return True

    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        if temp_input_path and os.path.exists(temp_input_path): os.remove(temp_input_path)
        return False

def separate_audio():
    """Main separation menu with hardcoded model."""
    TARGET_MODEL = "Kim_Vocal_2.onnx"
    
    try:
        # File Selection with Dynamic Scanning
        while True:
            choices = scan_for_audio_files(scan_deep=False)
            choices.append(questionary.Separator())
            choices.append(questionary.Choice("📂 Browse File...", value="browse"))
            choices.append(questionary.Choice("⬅️  Back", value="back"))
            
            file_path = questionary.select("Select Audio File:", choices=choices).ask()
            
            if file_path == "back" or file_path is None:
                return
            elif file_path == "scan_deep":
                choices = scan_for_audio_files(scan_deep=True)
                choices.append(questionary.Separator())
                choices.append(questionary.Choice("📂 Browse File...", value="browse"))
                choices.append(questionary.Choice("⬅️  Back", value="back"))
                file_path = questionary.select("Select Audio File (Scanned):", choices=choices).ask()
                
                if file_path == "back" or file_path is None: return
            
            if file_path == "browse":
                file_path = questionary.path("Path to file:").ask()
                if file_path: file_path = file_path.strip('"\'')
            
            if file_path and os.path.exists(file_path):
                break
            elif file_path:
                 console.print("[red]File not found.[/red]")
    except Exception as e:
        console.print(f"[red]Error during file selection: {e}[/red]")
        return
    
    # Run separation directly with hardcoded model
    run_separation(file_path, TARGET_MODEL)

# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Setup (CPU Only)
# ═══════════════════════════════════════════════════════════════════════════════

import sys
import subprocess
import questionary
from rich.panel import Panel
from rich.table import Table

from .config import CONFIG_FILE, save_config, load_config
from .hardware import get_torch_status, get_ort_status, get_hw_info
from .ui import console, show_header, pause

# Default required packages
REQUIRED_PACKAGES = {
    "yt-dlp": "yt-dlp",
    "rich": "rich",
    "questionary": "questionary", 
    "pydub": "pydub",
}

# CPU packages
CPU_PACKAGES = {
    "audio-separator": "audio-separator",
    "onnxruntime": "onnxruntime"
}

# ═══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY CHECKING
# ═══════════════════════════════════════════════════════════════════════════════

def check_command_exists(cmd):
    """Check if a command exists in PATH."""
    try:
        subprocess.run([cmd, "--version"], capture_output=True, timeout=5)
        return True
    except:
        return False

def check_package_installed(package_name):
    """Check if a Python package is installed."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package_name],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except:
        return False

def run_setup_check(_=None):
    """Run configuration and dependency check."""
    show_header("🔧 SYSTEM SETUP", "Configure CPU-only dependencies")
    
    hw_type = "cpu"
    target_packages = CPU_PACKAGES
    
    issues = []
    installs = []
    
    torch_avail, torch_ver = get_torch_status()
    ort_avail = check_package_installed("onnxruntime")
    
    # 2. Check FFmpeg and YT-DLP
    if not check_command_exists("ffmpeg"):
        issues.append(("ffmpeg", "❌ Missing"))
        installs.append("# Download FFmpeg from ffmpeg.org and add to PATH")
        
    if not check_command_exists("yt-dlp"):
        issues.append(("yt-dlp", "❌ Missing"))
        installs.append("pip install yt-dlp")

    # 3. Check Base Packages
    for pkg, pip_name in REQUIRED_PACKAGES.items():
        if pkg == "yt-dlp": continue
        if not check_package_installed(pkg):
            issues.append((pkg, "❌ Missing"))
            installs.append(f"pip install {pip_name}")

    # 4. Check HW Specific Packages
    for pkg, pip_name in target_packages.items():
        if not check_package_installed(pkg):
            issues.append((pkg, "❌ Missing"))
            installs.append(f"pip install {pip_name}")

    # 5. Check PyTorch
    if not torch_avail:
        issues.append(("PyTorch", "❌ Missing"))
        installs.append("pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu")

    # Display Status
    table = Table(show_header=True, header_style="bold cyan", title="Current Status")
    table.add_column("Component", style="white")
    table.add_column("Status", style="white")
    
    hw_info = get_hw_info()
    table.add_row("Detected Hardware", hw_info["device"])
    table.add_row("Setup Target", hw_type.upper())
    table.add_row("PyTorch", f"[green]{torch_ver}[/green]" if torch_avail else "[red]Missing[/red]")
    table.add_row("ONNX Runtime", "[green]Installed[/green]" if ort_avail else "[red]Missing[/red]")
    
    console.print(table)
    console.print()

    if not issues:
        console.print(f"[green]✅ System configured for {hw_type.upper()}![/green]")
        
        # Save config properly as JSON
        config = load_config()
        config["setup_type"] = "cpu"
        config["force_cpu"] = True
        config.update({"enabled": False, "fp16": False, "fp8": False, "batch_size": 1})
        
        save_config(config)
            
        pause()
        return

    # Found issues
    console.print(Panel.fit("[bold yellow]⚠️ Missing Components[/bold yellow]", border_style="yellow"))
    for i in issues:
        console.print(f"  {i[0]}: {i[1]}")
    
    console.print("\n[bold]Required Actions:[/bold]")
    for cmd in installs:
        console.print(f"  [cyan]{cmd}[/cyan]")
        
    if questionary.confirm("Install missing components now?", default=True).ask():
        for cmd in installs:
            if cmd.startswith("#"): continue
            console.print(f"\n[bold]Running:[/bold] {cmd}")
            subprocess.run(cmd.split())
        
        console.print("\n[green]✅ Installation complete. Please restart.[/green]")
        pause()

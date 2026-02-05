# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Menu System
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import subprocess
import time
import questionary
from rich.table import Table
from rich.text import Text
from rich.align import Align

from .config import MODELS_DIR, get_output_dirs, ensure_output_dirs
from .hardware import get_hw_info
from .ui import console, show_banner, show_header, show_hw_status, pause
from .youtube import download_video, download_audio
from .separator import separate_audio
from .setup import run_setup_check

# ═══════════════════════════════════════════════════════════════════════════════
# SUBMENUS
# ═══════════════════════════════════════════════════════════════════════════════

def youtube_menu():
    """YouTube download menu."""
    while True:
        show_header("📺 DOWNLOAD FROM YOUTUBE", "Download videos or audio")
        
        dirs = get_output_dirs()
        console.print(f"  [dim]Videos: {dirs['video']}[/dim]")
        console.print(f"  [dim]Audio:  {dirs['audio']}[/dim]\n")
        
        action = questionary.select(
            "What would you like to download?",
            choices=[
                questionary.Choice("🎵  Download Audio       Extract as high-quality WAV", value="audio"),
                questionary.Choice("🎬  Download Video       Best quality MP4", value="video"),
                questionary.Separator(),
                questionary.Choice("📂  Open video folder", value="open_video"),
                questionary.Choice("📂  Open audio folder", value="open_audio"),
                questionary.Separator(),
                questionary.Choice("⬅️   Back to Main Menu", value="back"),
            ]
        ).ask()
        
        if action == "back" or action is None:
            return
        elif action == "audio":
            download_audio()
            pause()
        elif action == "video":
            download_video()
            pause()
        elif action == "open_video":
            dirs = ensure_output_dirs()
            os.startfile(dirs["video"]) if os.name == 'nt' else subprocess.run(['xdg-open', dirs["video"]])
        elif action == "open_audio":
            dirs = ensure_output_dirs()
            os.startfile(dirs["audio"]) if os.name == 'nt' else subprocess.run(['xdg-open', dirs["audio"]])

def vocals_menu():
    """Vocal extraction menu."""
    while True:
        show_header("🎚️ EXTRACT VOCALS", "AI-powered vocal/instrumental separation")
        show_hw_status()
        
        dirs = get_output_dirs()
        console.print(f"  [dim]Files are saved in the same folder as the original audio.[/dim]\n")
        
        action = questionary.select(
            "Options:",
            choices=[
                questionary.Choice("🎵  Separate an audio file", value="separate"),
                questionary.Separator(),
                questionary.Choice("📂  Open models folder", value="open_models"),
                questionary.Separator(),
                questionary.Choice("⬅️   Back to Main Menu", value="back"),
            ]
        ).ask()
        
        if action == "back" or action is None:
            return
        elif action == "separate":
            separate_audio()
            pause()
        elif action == "open_models":
            os.startfile(MODELS_DIR) if os.name == 'nt' else subprocess.run(['xdg-open', MODELS_DIR])

def settings_menu():
    """Settings menu."""
    while True:
        show_header("⚙️ SETTINGS", "AMV Toolkit Configuration")
        
        dirs = get_output_dirs()
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("", style="cyan")
        table.add_column("", style="white")
        hw_info = get_hw_info()
        table.add_row("Output Folder", dirs["base"])
        table.add_row("Models Folder", MODELS_DIR)
        table.add_row("Device", hw_info["device"])
        table.add_row("Provider", hw_info["provider"])
        console.print(table)
        console.print()
        
        action = questionary.select(
            "Options:",
            choices=[
                questionary.Choice("📂  Open amv-script folder", value="open_base"),
                questionary.Choice("📂  Open models folder", value="open_models"),
                questionary.Choice("🔍  Check dependencies", value="deps"),
                questionary.Separator(),
                questionary.Choice("⬅️   Back to Main Menu", value="back"),
            ]
        ).ask()
        
        if action == "back" or action is None:
            return
        elif action == "open_base":
            dirs = ensure_output_dirs()
            os.startfile(dirs["base"]) if os.name == 'nt' else subprocess.run(['xdg-open', dirs["base"]])
        elif action == "open_models":
            os.startfile(MODELS_DIR) if os.name == 'nt' else subprocess.run(['xdg-open', MODELS_DIR])
        elif action == "deps":
            run_setup_check()

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN MENU
# ═══════════════════════════════════════════════════════════════════════════════

def main_menu():
    """Main application menu."""
    first = True
    
    while True:
        show_banner(animate=first)
        first = False
        
        # Show original directory where user ran the command
        original_dir = os.environ.get('AMV_ORIGINAL_DIR', os.getcwd())
        console.print(Align.center(Text(f"📁 {original_dir}", style="dim")))
        console.print()
        
        action = questionary.select(
            "What would you like to do?",
            choices=[
                questionary.Choice("📺  Download from YouTube     Video or Audio", value="youtube"),
                questionary.Choice("🎚️  Extract Vocals            AI separation", value="vocals"),
                questionary.Separator(),
                questionary.Choice("🔧  System Check              Verify installation", value="setup"),
                questionary.Choice("⚙️  Settings", value="settings"),
                questionary.Choice("🚪  Exit", value="exit"),
            ],
            use_indicator=True,
            instruction="(↑↓ Navigate, Enter Select)"
        ).ask()
        
        if action == "exit" or action is None:
            console.print("\n[bold cyan]👋 Thanks for using AMV Toolkit![/bold cyan]\n")
            sys.exit(0)
        elif action == "youtube":
            youtube_menu()
        elif action == "vocals":
            vocals_menu()
        elif action == "setup":
            run_setup_check()
        elif action == "settings":
            settings_menu()

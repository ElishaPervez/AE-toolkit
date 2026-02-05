# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - UI Components
# ═══════════════════════════════════════════════════════════════════════════════

import os
import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from rich.align import Align
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

from .hardware import refresh_vram

console = Console()

# ═══════════════════════════════════════════════════════════════════════════════
# BRANDING
# ═══════════════════════════════════════════════════════════════════════════════

LOGO = """
    █████╗ ███╗   ███╗██╗   ██╗
   ██╔══██╗████╗ ████║██║   ██║
   ███████║██╔████╔██║██║   ██║
   ██╔══██║██║╚██╔╝██║╚██╗ ██╔╝
   ██║  ██║██║ ╚═╝ ██║ ╚████╔╝ 
   ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═══╝  
"""

TAGLINE = "Audio & Media Video Toolkit"
COLORS = ["#00ffff", "#00d4ff", "#00aaff", "#0080ff", "#0066cc", "#00aaff"]

# ═══════════════════════════════════════════════════════════════════════════════
# DISPLAY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def clear():
    """Clear the terminal screen."""
    console.clear()

def gradient_text(text: str) -> Text:
    """Create gradient-colored text."""
    rich_text = Text()
    for i, line in enumerate(text.split('\n')):
        color = COLORS[i % len(COLORS)]
        rich_text.append(line + '\n', style=Style(color=color, bold=True))
    return rich_text

def show_banner(animate: bool = False):
    """Display the AMV banner with VENV indicator."""
    import sys
    is_venv = hasattr(sys, 'real_prefix') or (func := getattr(sys, 'base_prefix', sys.prefix)) != sys.prefix
    
    clear()
    if animate:
        lines = LOGO.split('\n')
        for i in range(len(lines) + 1):
            clear()
            console.print(Align.center(gradient_text('\n'.join(lines[:i]))))
            time.sleep(0.04)
    else:
        console.print(Align.center(gradient_text(LOGO)))
    
    tag = Text(TAGLINE, style="bold white dim")
    if is_venv:
        tag.append("  ")
        tag.append("[VENV]", style="bold green")
    
    console.print(Align.center(tag))
    console.print()

def show_header(title: str, subtitle: str = None):
    """Show a section header."""
    clear()
    header = Text(f"  {title}  ", style="bold white on #0080ff")
    console.print(Align.center(header))
    if subtitle:
        console.print(Align.center(Text(subtitle, style="dim")))
    console.print()

def show_hw_status():
    """Display hardware status line."""
    hw_info = refresh_vram()
    
    device = f"[bold cyan]{hw_info['device_short']}[/bold cyan]"
    if hw_info["vram"]:
        device += f" [dim]({hw_info['vram']})[/dim]"
    
    console.print(f"  {device}  |  [red]CPU[/red]")
    console.print()

def safe_str(text: str) -> str:
    """Sanitize text for console printing."""
    return text.encode('utf-8', 'replace').decode('utf-8')

def pause():
    """Wait for user to press Enter."""
    console.print("\n[dim]Press Enter to continue...[/dim]")
    input()

def create_progress():
    """Create a standard progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    )

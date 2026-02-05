# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - YouTube Download Functions
# ═══════════════════════════════════════════════════════════════════════════════

import os
import subprocess
import questionary
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from .config import ensure_output_dirs
from .ui import console, show_header, pause

def download_video():
    """Download a YouTube video."""
    dirs = ensure_output_dirs()
    url = questionary.text("Enter YouTube URL (leave empty to cancel):").ask()
    if not url or not url.strip():
        return
    
    url = url.strip().strip('"\'')
    output_path = dirs["video"]
    
    console.print(f"\n[bold yellow]⬇️  Downloading video...[/bold yellow]")
    console.print(f"[dim]Saving to: {output_path}[/dim]\n")
    
    cmd = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
           "-o", os.path.join(output_path, "%(title)s.%(ext)s"), "--progress", "--newline", url]
    
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                      BarColumn(), TimeElapsedColumn(), console=console, transient=True) as progress:
            task = progress.add_task("[cyan]Downloading...", total=None)
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, encoding='utf-8', errors='replace')
            for line in process.stdout:
                if '[download]' in line and '%' in line:
                    progress.update(task, description=f"[cyan]{line.strip()[:65]}...")
            process.wait()
        
        if process.returncode == 0:
            console.print(Panel.fit(f"[bold green]✅ Download Complete![/bold green]\n\nSaved to: [cyan]{output_path}[/cyan]", border_style="green"))
        else:
            console.print("[bold red]❌ Download failed![/bold red]")
    except FileNotFoundError:
        console.print("[bold red]❌ yt-dlp not found! Run setup first.[/bold red]")
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")

def download_audio():
    """Download YouTube audio as WAV."""
    dirs = ensure_output_dirs()
    url = questionary.text("Enter YouTube URL (leave empty to cancel):").ask()
    if not url or not url.strip():
        return
    
    url = url.strip().strip('"\'')
    output_path = dirs["audio"]
    
    console.print(f"\n[bold yellow]⬇️  Downloading audio...[/bold yellow]")
    console.print(f"[dim]Saving to: {output_path}[/dim]\n")
    
    cmd = ["yt-dlp", "-x", "--audio-format", "wav", "--audio-quality", "0",
           "-o", os.path.join(output_path, "%(title)s.%(ext)s"), "--progress", "--newline", url]
    
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                      BarColumn(), TimeElapsedColumn(), console=console, transient=True) as progress:
            task = progress.add_task("[magenta]Downloading...", total=None)
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, encoding='utf-8', errors='replace')
            for line in process.stdout:
                if '[download]' in line or '[ExtractAudio]' in line:
                    progress.update(task, description=f"[magenta]{line.strip()[:65]}...")
            process.wait()
        
        if process.returncode == 0:
            console.print(Panel.fit(f"[bold green]✅ Audio Downloaded![/bold green]\n\nSaved to: [cyan]{output_path}[/cyan]", border_style="green"))
        else:
            console.print("[bold red]❌ Download failed![/bold red]")
    except FileNotFoundError:
        console.print("[bold red]❌ yt-dlp not found! Run setup first.[/bold red]")
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")

# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Convert Screen
# Convert any media file to WAV audio using ffmpeg
# ═══════════════════════════════════════════════════════════════════════════════

import os
import glob
import subprocess
import shutil
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Static, Label, Button
from textual.containers import Vertical, Center
from textual import work

from amv.widgets.menu import StyledOptionList, create_menu_option, create_separator
from amv.config import get_recent_files, add_recent_file


class ConvertScreen(Screen):
    """Convert any media file to WAV audio."""
    
    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
    ]
    
    def __init__(self):
        super().__init__()
        self.selected_file = None
        self.is_converting = False
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("[bold #50fa7b]🔄 CONVERT TO WAV[/bold #50fa7b]", id="header", classes="screen-header")
            yield Static("[dim]Extract audio from any media file[/dim]", classes="screen-subtitle")
            yield Static("[dim]Output saved next to original file[/dim]", classes="path-info")
            yield Static("")  # Spacer
            
            # File selection menu
            with Center():
                yield StyledOptionList(id="file-menu")
            
            # Progress section (hidden initially)
            with Vertical(id="progress-section", classes="hidden"):
                yield Label("Converting...", id="progress-label")
                yield Static("", id="progress-bar")
                yield Static("", id="progress-file")
                yield Static("", id="progress-status")
                with Center():
                    yield Button("⏎ Press Enter to continue", id="continue-btn", classes="hidden")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize screen."""
        self._populate_file_menu()
        self.query_one("#file-menu").focus()
    
    def _populate_file_menu(self, deep_scan: bool = False) -> None:
        """Populate the file selection menu."""
        menu = self.query_one("#file-menu", StyledOptionList)
        menu.clear_options()
        
        options = []
        
        # Recent files (filter to convertible formats)
        recents = get_recent_files()
        convertible_exts = {'.mp4', '.mkv', '.avi', '.webm', '.mov', '.mp3', '.flac', '.m4a', '.ogg', '.aac'}
        if recents:
            options.append(create_separator())
            for path in recents:
                if os.path.exists(path):
                    ext = os.path.splitext(path)[1].lower()
                    if ext in convertible_exts:
                        name = os.path.basename(path)
                        parent = os.path.basename(os.path.dirname(path))
                        options.append(create_menu_option(
                            "⭐", name, f"({parent})", "audio", f"file:{path}"
                        ))
        
        # Actions
        options.append(create_separator())
        
        if not deep_scan:
            options.append(create_menu_option("🔍", "Scan for media files", "Search current directory", "action", "scan"))
        
        options.append(create_separator())
        options.append(create_menu_option("⬅️", "Back to Main Menu", "", "back", "back"))
        
        menu.add_options(options)
        
        # If deep scan, add found files
        if deep_scan:
            self._scan_for_files(menu)
    
    def _scan_for_files(self, menu: StyledOptionList) -> None:
        """Scan for media files and add to menu."""
        extensions = ['mp4', 'mkv', 'avi', 'webm', 'mov', 'mp3', 'flac', 'm4a', 'ogg', 'aac']
        original_dir = os.environ.get('AMV_ORIGINAL_DIR', os.getcwd())
        
        seen = set(get_recent_files())
        found = []
        
        for ext in extensions:
            pattern = os.path.join(original_dir, '**', f'*.{ext}')
            for f in glob.glob(pattern, recursive=True):
                abs_path = os.path.abspath(f)
                if abs_path in seen:
                    continue
                
                # Skip already-converted WAV files
                if f.lower().endswith('.wav'):
                    continue
                
                seen.add(abs_path)
                name = os.path.basename(f)
                parent = os.path.basename(os.path.dirname(f))
                
                # Use different emoji for video vs audio
                emoji = "🎬" if ext in ['mp4', 'mkv', 'avi', 'webm', 'mov'] else "🎵"
                found.append(create_menu_option(emoji, name, f"({parent})", "audio", f"file:{abs_path}"))
        
        if found:
            for opt in found[:20]:  # Limit to 20 files
                menu.add_option(opt)
    
    def on_option_list_option_selected(self, event) -> None:
        """Handle menu selection."""
        option_id = event.option_id
        
        if option_id.startswith("file:"):
            file_path = option_id[5:]  # Remove "file:" prefix
            self._start_conversion(file_path)
        elif option_id == "scan":
            self._populate_file_menu(deep_scan=True)
        elif option_id == "back":
            self.action_go_back()
    
    def _start_conversion(self, file_path: str) -> None:
        """Start the conversion process."""
        self.selected_file = file_path
        self.is_converting = True
        
        self.query_one("#file-menu").add_class("hidden")
        self.query_one("#progress-section").remove_class("hidden")
        
        # Initialize progress bar
        self._render_progress_bar(0)
        
        # Update UI elements
        self.query_one("#progress-label", Label).update("🔄 Converting to WAV...")
        self.query_one("#progress-file", Static).update(f"[cyan]📁 {os.path.basename(file_path)}[/cyan]")
        self.query_one("#progress-status", Static).update("[dim]Using ffmpeg...[/dim]")
        
        # Run conversion in background
        self._conversion_worker(file_path)
    
    def _render_progress_bar(self, percent: int) -> None:
        """Render a text-based progress bar."""
        bar_width = 30
        filled = int(bar_width * percent / 100)
        empty = bar_width - filled
        bar = f"[#50fa7b]{'█' * filled}[/#50fa7b][#44475a]{'░' * empty}[/#44475a]"
        self.query_one("#progress-bar", Static).update(bar)
    
    @work(thread=True, exclusive=True)
    def _conversion_worker(self, input_file: str) -> None:
        """Background worker for ffmpeg conversion."""
        input_dir = os.path.dirname(input_file)
        input_stem = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(input_dir, f"{input_stem}.wav")
        
        # Check if ffmpeg is available
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            self.app.call_from_thread(self._show_error, "ffmpeg not found! Please install ffmpeg.")
            return
        
        try:
            # Build ffmpeg command
            cmd = [
                "ffmpeg",
                "-i", input_file,
                "-vn",  # No video
                "-acodec", "pcm_s16le",  # WAV codec
                "-ar", "44100",  # Sample rate
                "-ac", "2",  # Stereo
                "-y",  # Overwrite
                output_file
            ]
            
            self.app.call_from_thread(self._render_progress_bar, 50)
            
            # Run ffmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and os.path.exists(output_file):
                add_recent_file(input_file)
                self.app.call_from_thread(self._show_success, f"Saved: {os.path.basename(output_file)}")
            else:
                error_msg = result.stderr[-200:] if result.stderr else "Unknown error"
                self.app.call_from_thread(self._show_error, f"Conversion failed: {error_msg}")
                
        except Exception as e:
            self.app.call_from_thread(self._show_error, str(e))
    
    def _show_success(self, message: str) -> None:
        """Show success message."""
        self.is_converting = False
        self.query_one("#progress-label", Label).update("[bold #50fa7b]✅ Success![/bold #50fa7b]")
        self._render_progress_bar(100)
        self.query_one("#progress-status", Static).update(f"[cyan]{message}[/cyan]")
        self.query_one("#continue-btn").remove_class("hidden")
        self.query_one("#continue-btn", Button).focus()
    
    def _show_error(self, message: str) -> None:
        """Show error message."""
        self.is_converting = False
        self.query_one("#progress-label", Label).update("[bold #ff5555]❌ Error[/bold #ff5555]")
        self._render_progress_bar(0)
        self.query_one("#progress-status", Static).update(f"[red]{message}[/red]")
        self.query_one("#continue-btn").remove_class("hidden")
        self.query_one("#continue-btn", Button).focus()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "continue-btn":
            self._show_menu()
    
    def _show_menu(self) -> None:
        """Return to menu."""
        self.query_one("#progress-section").add_class("hidden")
        self.query_one("#continue-btn").add_class("hidden")
        self.query_one("#file-menu").remove_class("hidden")
        self._populate_file_menu()
        self.query_one("#file-menu").focus()
    
    def action_go_back(self) -> None:
        """Go back to main menu."""
        if not self.is_converting:
            self.app.pop_screen()

    DEFAULT_CSS = """
    .screen-header {
        text-align: center;
        padding: 1 0;
    }
    
    .screen-subtitle {
        text-align: center;
        padding-bottom: 1;
    }
    
    .path-info {
        text-align: center;
    }
    
    .hidden {
        display: none;
    }
    
    #progress-section {
        padding: 2 4;
        margin: 1 4;
        border: round #50fa7b;
        min-height: 12;
    }
    
    #progress-label {
        text-align: center;
        text-style: bold;
        padding: 1 0;
        width: 100%;
    }
    
    #progress-bar {
        text-align: center;
        padding: 1 4;
    }
    
    #progress-file {
        text-align: center;
        padding: 1 0;
    }
    
    #progress-status {
        text-align: center;
        padding: 0 0 1 0;
    }
    """

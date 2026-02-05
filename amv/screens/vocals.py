# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Vocals Screen
# AI-powered vocal/instrumental separation
# ═══════════════════════════════════════════════════════════════════════════════

import os
import glob
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Static, Label, Button
from textual.containers import Vertical, Center
from textual.worker import get_current_worker

from amv.widgets.menu import StyledOptionList, create_menu_option, create_separator
from amv.config import MODELS_DIR, get_recent_files, add_recent_file, ensure_output_dirs
from amv.hardware import get_hw_info, refresh_vram


class VocalsScreen(Screen):
    """Vocal extraction screen with file selection and AI separation."""
    
    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
    ]
    
    TARGET_MODEL = "Kim_Vocal_2.onnx"
    
    def __init__(self):
        super().__init__()
        self.selected_file = None
        self.is_processing = False
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("[bold #bd93f9]🎚️ EXTRACT VOCALS[/bold #bd93f9]", id="header", classes="screen-header")
            yield Static("[dim]AI-powered vocal/instrumental separation[/dim]", classes="screen-subtitle")
            
            # Hardware status
            yield Static(id="hw-status")
            yield Static("[dim]Files are saved in the same folder as the original audio.[/dim]", classes="path-info")
            yield Static("")  # Spacer
            
            # File selection menu
            with Center():
                yield StyledOptionList(id="file-menu")
            
            # Progress section (hidden initially)
            with Vertical(id="progress-section", classes="hidden"):
                yield Label("Processing...", id="progress-label")
                yield Static("", id="progress-bar")
                yield Static("", id="progress-file")
                yield Static("", id="progress-status")
                yield Static("[dim italic]💡 Tip: First run may take longer for model optimization[/dim italic]", id="progress-tip")
                with Center():
                    yield Button("⏎ Press Enter to continue", id="continue-btn", classes="hidden")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize screen."""
        self._show_hw_status_loading()
        self._populate_file_menu()
        self.query_one("#file-menu").focus()
        self.run_worker(self._load_hw_status, thread=True, exclusive=True)
    
    def _show_hw_status_loading(self) -> None:
        """Show placeholder hardware status while detecting."""
        self.query_one("#hw-status", Static).update("[dim]Detecting hardware...[/dim]")
    
    def _load_hw_status(self) -> None:
        """Load hardware info in a background thread."""
        hw_info = refresh_vram()
        self.app.call_from_thread(self._update_hw_status, hw_info)
    
    def _update_hw_status(self, hw_info=None) -> None:
        """Update hardware status display."""
        if hw_info is None:
            hw_info = refresh_vram()
        device = hw_info['device_short']
        vram = f" ({hw_info['vram']})" if hw_info['vram'] else ""
        
        # Color based on device type
        if 'CUDA' in device or 'GPU' in device:
            badge_style = "bold #50fa7b"
        else:
            badge_style = "bold #ffb86c"
        
        self.query_one("#hw-status", Static).update(
            f"[{badge_style}]{device}{vram}[/{badge_style}]  |  [red]CPU fallback available[/red]"
        )
    
    def _populate_file_menu(self, deep_scan: bool = False) -> None:
        """Populate the file selection menu."""
        menu = self.query_one("#file-menu", StyledOptionList)
        menu.clear_options()
        
        options = []
        
        # Recent files
        recents = get_recent_files()
        if recents:
            options.append(create_separator())
            for path in recents:
                if os.path.exists(path):
                    name = os.path.basename(path)
                    parent = os.path.basename(os.path.dirname(path))
                    options.append(create_menu_option(
                        "⭐", name, f"({parent})", "audio", f"file:{path}"
                    ))
        
        # Actions
        options.append(create_separator())
        
        if not deep_scan:
            options.append(create_menu_option("🔍", "Scan for audio files", "Search current directory", "action", "scan"))
        
        options.append(create_menu_option("📂", "Open models folder", "", "folder", "open_models"))
        options.append(create_separator())
        options.append(create_menu_option("⬅️", "Back to Main Menu", "", "back", "back"))
        
        menu.add_options(options)
        
        # If deep scan, add found files
        if deep_scan:
            self._scan_for_files(menu)
    
    def _scan_for_files(self, menu: StyledOptionList) -> None:
        """Scan for audio files and add to menu."""
        extensions = ['wav', 'mp3', 'flac', 'm4a', 'mp4', 'mkv', 'avi', 'webm', 'mov']
        original_dir = os.environ.get('AMV_ORIGINAL_DIR', os.getcwd())
        
        seen = set(get_recent_files())
        found = []
        
        for ext in extensions:
            pattern = os.path.join(original_dir, '**', f'*.{ext}')
            for f in glob.glob(pattern, recursive=True):
                abs_path = os.path.abspath(f)
                if abs_path in seen:
                    continue
                
                # Skip already-processed files
                f_lower = f.lower()
                if "[vocals]" in f_lower or "[instrumental]" in f_lower:
                    continue
                
                seen.add(abs_path)
                name = os.path.basename(f)
                parent = os.path.basename(os.path.dirname(f))
                found.append(create_menu_option("🎵", name, f"({parent})", "audio", f"file:{abs_path}"))
        
        if found:
            # Insert found files before the back option
            for opt in found[:20]:  # Limit to 20 files
                menu.add_option(opt)
    
    def on_option_list_option_selected(self, event) -> None:
        """Handle menu selection."""
        option_id = event.option_id
        
        if option_id.startswith("file:"):
            file_path = option_id[5:]  # Remove "file:" prefix
            self._start_separation(file_path)
        elif option_id == "scan":
            self._populate_file_menu(deep_scan=True)
        elif option_id == "open_models":
            if os.path.exists(MODELS_DIR):
                if os.name == 'nt':
                    os.startfile(MODELS_DIR)
        elif option_id == "back":
            self.action_go_back()
    
    def _start_separation(self, file_path: str) -> None:
        """Start the vocal separation process."""
        self.selected_file = file_path
        self.is_processing = True
        
        self.query_one("#file-menu").add_class("hidden")
        self.query_one("#progress-section").remove_class("hidden")
        
        # Initialize text-based progress bar
        self._render_progress_bar(0)
        
        # Update UI elements
        self.query_one("#progress-label", Label).update("🎚️ Loading AI Model...")
        self.query_one("#progress-file", Static).update(f"[cyan]📁 {os.path.basename(file_path)}[/cyan]")
        self.query_one("#progress-status", Static).update("[dim]Initializing neural network...[/dim]")
        
        # Run separation in background worker (thread=True for blocking work)
        self.run_worker(lambda: self._separation_worker(file_path), thread=True, exclusive=True)
    
    def _separation_worker(self, input_file: str) -> None:
        """Background worker for audio separation."""
        worker = get_current_worker()
        
        def on_progress(stage: str, percent: int, message: str):
            """Callback for separation progress updates."""
            if stage == 'loading':
                self.app.call_from_thread(self._update_stage, "🎚️ Loading AI Model...", "First run may take ~30s for optimization")
            elif stage == 'processing':
                if percent >= 0:
                    self.app.call_from_thread(self._update_progress, percent, message)
                else:
                    self.app.call_from_thread(self._update_stage, "🎵 Processing Audio...", message)
        
        try:
            # Import here to avoid slow startup
            from amv.separator import run_separation
            
            # Run the actual separation with progress callback
            success = run_separation(input_file, self.TARGET_MODEL, progress_callback=on_progress)
            
            if success:
                add_recent_file(input_file)
                self.app.call_from_thread(self._show_success, "Separation complete!")
            else:
                self.app.call_from_thread(self._show_error, "Separation failed")
                
        except Exception as e:
            self.app.call_from_thread(self._show_error, str(e))
    

    
    def _render_progress_bar(self, percent: int) -> None:
        """Render a text-based progress bar."""
        bar_width = 30
        filled = int(bar_width * percent / 100)
        empty = bar_width - filled
        bar = f"[#bd93f9]{'█' * filled}[/#bd93f9][#44475a]{'░' * empty}[/#44475a]"
        self.query_one("#progress-bar", Static).update(bar)
    
    def _update_stage(self, label: str, status: str) -> None:
        """Update progress stage."""
        self.query_one("#progress-label", Label).update(label)
        self.query_one("#progress-status", Static).update(f"[dim]{status}[/dim]")
    
    def _update_progress(self, percent: int, message: str) -> None:
        """Update progress bar with actual percentage."""
        self._render_progress_bar(percent)
        self.query_one("#progress-label", Label).update(f"🎵 Processing Audio... {percent}%")
        self.query_one("#progress-status", Static).update(f"[dim]{message}[/dim]")
    
    def _show_success(self, message: str) -> None:
        """Show success message."""
        self.is_processing = False
        self.query_one("#progress-label", Label).update("[bold #50fa7b]✅ Success![/bold #50fa7b]")
        self._render_progress_bar(100)
        self.query_one("#progress-status", Static).update(f"[cyan]{message}[/cyan]")
        self.query_one("#progress-tip", Static).update("")
        self.query_one("#continue-btn").remove_class("hidden")
        self.query_one("#continue-btn", Button).focus()
    
    def _show_error(self, message: str) -> None:
        """Show error message."""
        self.is_processing = False
        self.query_one("#progress-label", Label).update("[bold #ff5555]❌ Error[/bold #ff5555]")
        self._render_progress_bar(0)
        self.query_one("#progress-status", Static).update(f"[red]{message}[/red]")
        self.query_one("#progress-tip", Static).update("")
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
        if not self.is_processing:
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
    
    #hw-status {
        text-align: center;
        padding: 1 0;
    }
    
    .hidden {
        display: none;
    }
    
    #progress-section {
        padding: 2 4;
        margin: 1 4;
        border: round #bd93f9;
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
    
    #progress-tip {
        text-align: center;
        padding-top: 1;
    }
    """

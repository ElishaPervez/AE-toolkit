# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Vocals Screen
# AI-powered vocal/instrumental separation
# ═══════════════════════════════════════════════════════════════════════════════

import os
from textual.app import ComposeResult
from textual.widgets import Footer, Static, Label, Button, Input
from textual.containers import Vertical, Center
from textual.worker import get_current_worker

from textual.screen import Screen
from amv.widgets.menu import StyledOptionList, create_menu_option
from amv.config import add_recent_file
from amv.hardware import get_hw_info, refresh_vram
from amv.models import get_active_model, get_model_display_name
from amv.notify import notify_complete

AUDIO_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a', 'mp4', 'mkv', 'avi', 'webm', 'mov'}

# Directories to skip during deep scan
SKIP_DIRS = {
    '.git', 'node_modules', '.venv', '__pycache__', 'venv', 'env', '.tox',
    '$Recycle.Bin', 'System Volume Information', 'AppData', '.cache', '.local',
}


class VocalsScreen(Screen):
    """Vocal extraction screen with file selection and AI separation."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
        ("left", "go_back"),
    ]

    def __init__(self):
        super().__init__()
        self.selected_file = None
        self.is_processing = False
        self._scan_timer = None
        self.active_model = None

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("[bold #bd93f9]🎚️ EXTRACT VOCALS[/bold #bd93f9]", id="header", classes="screen-header")
            yield Static("[dim]AI-powered vocal/instrumental separation[/dim]", classes="screen-subtitle")

            # Hardware status
            yield Static(id="hw-status")
            yield Static("[dim]Files are saved in the same folder as the original audio.[/dim]", classes="path-info")

            # Path input section (shown by default)
            with Vertical(id="path-section"):
                yield Static("[bold]Enter file path:[/bold]", classes="input-label")
                yield Input(placeholder="Type a path or filename to search...", id="path-input")
                yield Static("", id="path-scan-info")
                with Center():
                    yield StyledOptionList(id="path-suggestions")

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
        self.query_one("#path-input", Input).focus()
        original_dir = os.environ.get('AMV_ORIGINAL_DIR', os.getcwd())
        self._run_scan(original_dir, "")
        self.run_worker(self._load_hw_status, thread=True, exclusive=True)

    def _show_hw_status_loading(self) -> None:
        self.query_one("#hw-status", Static).update("[dim]Detecting hardware...[/dim]")

    def _load_hw_status(self) -> None:
        hw_info = refresh_vram()
        self.app.call_from_thread(self._update_hw_status, hw_info)

    def _update_hw_status(self, hw_info=None) -> None:
        if hw_info is None:
            hw_info = refresh_vram()

        # Auto-select model based on hardware
        self.active_model = get_active_model(hw_info)
        model_name = get_model_display_name(self.active_model)

        device = hw_info['device_short']
        vram = f" ({hw_info['vram']})" if hw_info.get('vram') else ""

        if hw_info.get("gpu_type") != "cpu":
            # GPU mode: green badge with model + FP16
            gpu_device = hw_info.get("device", device)
            badge_style = "bold #50fa7b"
            fp16_tag = " FP16" if hw_info.get("fp16_capable") else ""
            self.query_one("#hw-status", Static).update(
                f"[{badge_style}]{gpu_device}{vram} | {model_name}{fp16_tag}[/{badge_style}]"
            )
        else:
            # CPU mode: orange badge
            badge_style = "bold #ffb86c"
            self.query_one("#hw-status", Static).update(
                f"[{badge_style}]CPU | {model_name}[/{badge_style}]"
            )

    # ─── File Selection ──────────────────────────────────────────────────────

    def on_option_list_option_selected(self, event) -> None:
        option_id = event.option_id
        if option_id.startswith("file:"):
            file_path = option_id[5:]
            self._start_separation(file_path)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "path-input":
            return
        if self._scan_timer is not None:
            self._scan_timer.stop()
        self._scan_timer = self.set_timer(0.3, lambda: self._parse_and_scan(event.value))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "path-input":
            return
        path = event.value.strip().strip('"\'')
        if path and os.path.isfile(path):
            self._start_separation(path)

    def _parse_and_scan(self, text: str) -> None:
        """Parse input text into directory + filter, then launch a scan."""
        text = text.strip().strip('"\'')
        original_dir = os.environ.get('AMV_ORIGINAL_DIR', os.getcwd())

        if not text:
            self._run_scan(original_dir, "")
        elif os.path.isdir(text):
            self._run_scan(text, "")
        else:
            dir_part = os.path.dirname(text)
            name_part = os.path.basename(text).lower()
            if dir_part and os.path.isdir(dir_part):
                self._run_scan(dir_part, name_part)
            else:
                self._run_scan(original_dir, text.lower())

    def _run_scan(self, directory: str, name_filter: str) -> None:
        """Show scanning indicator and launch background scan."""
        self.query_one("#path-scan-info", Static).update(
            f"[dim]📁 {directory}  (scanning...)[/dim]"
        )
        self.run_worker(
            lambda: self._scan_worker(directory, name_filter),
            thread=True, exclusive=True, group="path_scan",
        )

    def _scan_worker(self, directory: str, name_filter: str) -> None:
        """Run deep scan in background thread, then update UI."""
        results = self._deep_scan(directory)
        if name_filter:
            results = [f for f in results if name_filter in os.path.basename(f).lower()]
        self.app.call_from_thread(self._show_scan_results, directory, results)

    def _deep_scan(self, directory: str) -> list:
        """Recursively scan for audio and video files."""
        results = []
        try:
            for root, dirs, files in os.walk(directory):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
                for f in files:
                    ext = os.path.splitext(f)[1].lower().lstrip('.')
                    if ext not in AUDIO_EXTENSIONS:
                        continue
                    f_lower = f.lower()
                    if "[vocals]" in f_lower or "[instrumental]" in f_lower:
                        continue
                    results.append(os.path.join(root, f))
                    if len(results) >= 200:
                        return results
        except OSError:
            pass
        return results

    def _show_scan_results(self, directory: str, results: list) -> None:
        """Update the suggestion list with scan results."""
        self.query_one("#path-scan-info", Static).update(
            f"[dim]📁 {directory}  ({len(results)} files found)[/dim]"
        )

        menu = self.query_one("#path-suggestions", StyledOptionList)
        menu.clear_options()

        for path in results[:20]:
            name = os.path.basename(path)
            parent = os.path.basename(os.path.dirname(path))
            ext = os.path.splitext(name)[1].lower().lstrip('.')
            emoji = "🎬" if ext in ('mp4', 'mkv', 'avi', 'webm', 'mov') else "🎵"
            menu.add_option(create_menu_option(emoji, name, f"({parent})", "audio", f"file:{path}"))

    # ─── Separation ───────────────────────────────────────────────────────────

    def _start_separation(self, file_path: str) -> None:
        self.selected_file = file_path
        self.is_processing = True

        self.query_one("#path-section").add_class("hidden")
        self.query_one("#progress-section").remove_class("hidden")

        self._render_progress_bar(0)

        self.query_one("#progress-label", Label).update("🎚️ Loading AI Model...")
        self.query_one("#progress-file", Static).update(f"[cyan]📁 {os.path.basename(file_path)}[/cyan]")
        self.query_one("#progress-status", Static).update("[dim]Initializing neural network...[/dim]")

        self.run_worker(lambda: self._separation_worker(file_path), thread=True, exclusive=True)

    def _separation_worker(self, input_file: str) -> None:
        worker = get_current_worker()

        # Determine device label for progress messages
        hw_info = get_hw_info()
        if hw_info.get("gpu_type") != "cpu" and hw_info.get("fp16_capable"):
            device_label = "Processing on CUDA (FP16)"
        else:
            device_label = "Processing on CPU"

        def on_progress(stage: str, percent: int, message: str):
            if stage == 'loading':
                self.app.call_from_thread(self._update_stage, "🎚️ Loading AI Model...", "First run may take ~30s for model download")
            elif stage == 'processing':
                if percent >= 0:
                    self.app.call_from_thread(self._update_progress, percent, f"{device_label} - {message}")
                else:
                    self.app.call_from_thread(self._update_stage, "🎵 Processing Audio...", device_label)

        try:
            from amv.separator import run_separation

            run_separation(input_file, self.active_model, progress_callback=on_progress)

            add_recent_file(input_file)
            self.app.call_from_thread(self._show_success, "Separation complete!")

        except Exception as e:
            self.app.call_from_thread(self._show_error, str(e))

    def _render_progress_bar(self, percent: int) -> None:
        bar_width = 30
        filled = int(bar_width * percent / 100)
        empty = bar_width - filled
        bar = f"[#bd93f9]{'█' * filled}[/#bd93f9][#44475a]{'░' * empty}[/#44475a]"
        self.query_one("#progress-bar", Static).update(bar)

    def _update_stage(self, label: str, status: str) -> None:
        self.query_one("#progress-label", Label).update(label)
        self.query_one("#progress-status", Static).update(f"[dim]{status}[/dim]")

    def _update_progress(self, percent: int, message: str) -> None:
        self._render_progress_bar(percent)
        self.query_one("#progress-label", Label).update(f"🎵 Processing Audio... {percent}%")
        self.query_one("#progress-status", Static).update(f"[dim]{message}[/dim]")

    def _show_success(self, message: str) -> None:
        self.is_processing = False
        self.query_one("#progress-label", Label).update("[bold #50fa7b]✅ Success![/bold #50fa7b]")
        self._render_progress_bar(100)
        self.query_one("#progress-status", Static).update(f"[cyan]{message}[/cyan]")
        self.query_one("#progress-tip", Static).update("")
        self.query_one("#continue-btn").remove_class("hidden")
        self.query_one("#continue-btn", Button).focus()
        notify_complete(self.app)

    def _show_error(self, message: str) -> None:
        self.is_processing = False
        self.query_one("#progress-label", Label).update("[bold #ff5555]❌ Error[/bold #ff5555]")
        self._render_progress_bar(0)
        self.query_one("#progress-status", Static).update(f"[red]{message}[/red]")
        self.query_one("#progress-tip", Static).update("")
        self.query_one("#continue-btn").remove_class("hidden")
        self.query_one("#continue-btn", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue-btn":
            self._show_input()

    def _show_input(self) -> None:
        self.query_one("#progress-section").add_class("hidden")
        self.query_one("#continue-btn").add_class("hidden")
        self.query_one("#path-section").remove_class("hidden")
        inp = self.query_one("#path-input", Input)
        inp.value = ""
        inp.focus()
        original_dir = os.environ.get('AMV_ORIGINAL_DIR', os.getcwd())
        self._run_scan(original_dir, "")

    def action_go_back(self) -> None:
        if self.is_processing:
            return
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

    #path-section {
        padding: 1 4;
    }

    .input-label {
        padding: 0 4;
    }

    #path-input {
        margin: 1 4;
    }

    #path-scan-info {
        text-align: center;
        padding: 0 4;
    }

    #path-suggestions {
        max-height: 12;
    }
    """

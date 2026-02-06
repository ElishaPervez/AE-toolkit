# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Vocals Screen
# AI-powered vocal/instrumental separation
# ═══════════════════════════════════════════════════════════════════════════════

import os
import glob
from textual.app import ComposeResult
from textual.widgets import Footer, Static, Label, Button, Input
from textual.containers import Vertical, Center
from textual.worker import get_current_worker

from textual.screen import Screen
from amv.widgets.menu import StyledOptionList, create_menu_option, create_separator
from amv.config import MODELS_DIR, get_recent_files, add_recent_file, ensure_output_dirs
from amv.hardware import get_hw_info, refresh_vram
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

    TARGET_MODEL = "Kim_Vocal_2.onnx"

    def __init__(self):
        super().__init__()
        self.selected_file = None
        self.is_processing = False
        self._path_input_visible = False
        self._scan_timer = None

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

            # Path input section (hidden initially)
            with Vertical(id="path-section", classes="hidden"):
                yield Static("[bold]Enter file path:[/bold]", classes="input-label")
                yield Input(placeholder="Type a path or filename to search...", id="path-input")
                yield Static("", id="path-scan-info")
                with Center():
                    yield StyledOptionList(id="path-suggestions")
                with Center():
                    yield Button("Cancel", id="path-cancel-btn")

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
        self.query_one("#hw-status", Static).update("[dim]Detecting hardware...[/dim]")

    def _load_hw_status(self) -> None:
        hw_info = refresh_vram()
        self.app.call_from_thread(self._update_hw_status, hw_info)

    def _update_hw_status(self, hw_info=None) -> None:
        if hw_info is None:
            hw_info = refresh_vram()
        device = hw_info['device_short']
        vram = f" ({hw_info['vram']})" if hw_info['vram'] else ""

        if 'CUDA' in device or 'GPU' in device:
            badge_style = "bold #50fa7b"
        else:
            badge_style = "bold #ffb86c"

        self.query_one("#hw-status", Static).update(
            f"[{badge_style}]{device}{vram}[/{badge_style}]  |  [red]CPU fallback available[/red]"
        )

    # ─── File Menu ────────────────────────────────────────────────────────────

    def _populate_file_menu(self, deep_scan: bool = False) -> None:
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

        options.append(create_menu_option("📝", "Type or paste a path", "Enter file location", "action", "type_path"))
        options.append(create_menu_option("📂", "Open models folder", "", "folder", "open_models"))
        options.append(create_separator())
        options.append(create_menu_option("⬅️", "Back to Main Menu", "", "back", "back"))

        menu.add_options(options)

        if deep_scan:
            self._scan_for_files(menu)

    def _scan_for_files(self, menu: StyledOptionList) -> None:
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

                f_lower = f.lower()
                if "[vocals]" in f_lower or "[instrumental]" in f_lower:
                    continue

                seen.add(abs_path)
                name = os.path.basename(f)
                parent = os.path.basename(os.path.dirname(f))
                found.append(create_menu_option("🎵", name, f"({parent})", "audio", f"file:{abs_path}"))

        if found:
            for opt in found[:20]:
                menu.add_option(opt)

    def on_option_list_option_selected(self, event) -> None:
        option_id = event.option_id

        if option_id.startswith("file:"):
            file_path = option_id[5:]
            self._start_separation(file_path)
        elif option_id == "scan":
            self._populate_file_menu(deep_scan=True)
        elif option_id == "type_path":
            self._show_path_input()
        elif option_id == "open_models":
            if os.path.exists(MODELS_DIR):
                if os.name == 'nt':
                    os.startfile(MODELS_DIR)
        elif option_id == "back":
            self.action_go_back()

    # ─── Path Input ───────────────────────────────────────────────────────────

    def _show_path_input(self) -> None:
        self._path_input_visible = True
        self.query_one("#file-menu").add_class("hidden")
        self.query_one("#path-section").remove_class("hidden")
        inp = self.query_one("#path-input", Input)
        inp.value = ""
        inp.focus()
        # Initial deep scan of working directory
        original_dir = os.environ.get('AMV_ORIGINAL_DIR', os.getcwd())
        self._run_scan(original_dir, "")

    def _hide_path_input(self) -> None:
        self._path_input_visible = False
        self.query_one("#path-section").add_class("hidden")
        self.query_one("#file-menu").remove_class("hidden")
        self.query_one("#file-menu").focus()

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

        self.query_one("#file-menu").add_class("hidden")
        self.query_one("#path-section").add_class("hidden")
        self.query_one("#progress-section").remove_class("hidden")

        self._render_progress_bar(0)

        self.query_one("#progress-label", Label).update("🎚️ Loading AI Model...")
        self.query_one("#progress-file", Static).update(f"[cyan]📁 {os.path.basename(file_path)}[/cyan]")
        self.query_one("#progress-status", Static).update("[dim]Initializing neural network...[/dim]")

        self.run_worker(lambda: self._separation_worker(file_path), thread=True, exclusive=True)

    def _separation_worker(self, input_file: str) -> None:
        worker = get_current_worker()

        def on_progress(stage: str, percent: int, message: str):
            if stage == 'loading':
                self.app.call_from_thread(self._update_stage, "🎚️ Loading AI Model...", "First run may take ~30s for optimization")
            elif stage == 'processing':
                if percent >= 0:
                    self.app.call_from_thread(self._update_progress, percent, message)
                else:
                    self.app.call_from_thread(self._update_stage, "🎵 Processing Audio...", message)

        try:
            from amv.separator import run_separation

            run_separation(input_file, self.TARGET_MODEL, progress_callback=on_progress)

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
            self._show_menu()
        elif event.button.id == "path-cancel-btn":
            self._hide_path_input()

    def _show_menu(self) -> None:
        self.query_one("#progress-section").add_class("hidden")
        self.query_one("#continue-btn").add_class("hidden")
        self.query_one("#path-section").add_class("hidden")
        self.query_one("#file-menu").remove_class("hidden")
        self._path_input_visible = False
        self._populate_file_menu()
        self.query_one("#file-menu").focus()

    def action_go_back(self) -> None:
        if self.is_processing:
            return
        if self._path_input_visible:
            self._hide_path_input()
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

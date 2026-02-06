# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Convert Screen
# Convert any media file to WAV audio using ffmpeg
# ═══════════════════════════════════════════════════════════════════════════════

import os
import glob
import subprocess
import shutil
from textual.app import ComposeResult
from textual.widgets import Footer, Static, Label, Button, Input
from textual.containers import Vertical, Center
from textual import work

from textual.screen import Screen
from amv.widgets.menu import StyledOptionList, create_menu_option, create_separator
from amv.config import get_recent_files, add_recent_file
from amv.notify import notify_complete

# Video-only for the deep scan path input
VIDEO_EXTENSIONS = {'mp4', 'mkv', 'avi', 'webm', 'mov'}

# All convertible formats for recent files display
CONVERTIBLE_EXTS = {'.mp4', '.mkv', '.avi', '.webm', '.mov', '.mp3', '.flac', '.m4a', '.ogg', '.aac'}

# Directories to skip during deep scan
SKIP_DIRS = {
    '.git', 'node_modules', '.venv', '__pycache__', 'venv', 'env', '.tox',
    '$Recycle.Bin', 'System Volume Information', 'AppData', '.cache', '.local',
}


class ConvertScreen(Screen):
    """Convert any media file to WAV audio."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
        ("left", "go_back"),
    ]

    def __init__(self):
        super().__init__()
        self.selected_file = None
        self.is_converting = False
        self._path_input_visible = False
        self._scan_timer = None

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("[bold #50fa7b]🔄 CONVERT TO WAV[/bold #50fa7b]", id="header", classes="screen-header")
            yield Static("[dim]Extract audio from any media file[/dim]", classes="screen-subtitle")
            yield Static("[dim]Output saved next to original file[/dim]", classes="path-info")
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
                yield Label("Converting...", id="progress-label")
                yield Static("", id="progress-bar")
                yield Static("", id="progress-file")
                yield Static("", id="progress-status")
                with Center():
                    yield Button("⏎ Press Enter to continue", id="continue-btn", classes="hidden")

        yield Footer()

    def on_mount(self) -> None:
        self._populate_file_menu()
        self.query_one("#file-menu").focus()

    # ─── File Menu ────────────────────────────────────────────────────────────

    def _populate_file_menu(self, deep_scan: bool = False) -> None:
        menu = self.query_one("#file-menu", StyledOptionList)
        menu.clear_options()

        options = []

        # Recent files (all convertible formats)
        recents = get_recent_files()
        if recents:
            options.append(create_separator())
            for path in recents:
                if os.path.exists(path):
                    ext = os.path.splitext(path)[1].lower()
                    if ext in CONVERTIBLE_EXTS:
                        name = os.path.basename(path)
                        parent = os.path.basename(os.path.dirname(path))
                        options.append(create_menu_option(
                            "⭐", name, f"({parent})", "audio", f"file:{path}"
                        ))

        # Actions
        options.append(create_separator())

        if not deep_scan:
            options.append(create_menu_option("🔍", "Scan for media files", "Search current directory", "action", "scan"))

        options.append(create_menu_option("📝", "Type or paste a path", "Enter file location", "action", "type_path"))
        options.append(create_separator())
        options.append(create_menu_option("⬅️", "Back to Main Menu", "", "back", "back"))

        menu.add_options(options)

        if deep_scan:
            self._scan_for_files(menu)

    def _scan_for_files(self, menu: StyledOptionList) -> None:
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

                if f.lower().endswith('.wav'):
                    continue

                seen.add(abs_path)
                name = os.path.basename(f)
                parent = os.path.basename(os.path.dirname(f))

                emoji = "🎬" if ext in ['mp4', 'mkv', 'avi', 'webm', 'mov'] else "🎵"
                found.append(create_menu_option(emoji, name, f"({parent})", "audio", f"file:{abs_path}"))

        if found:
            for opt in found[:20]:
                menu.add_option(opt)

    def on_option_list_option_selected(self, event) -> None:
        option_id = event.option_id

        if option_id.startswith("file:"):
            file_path = option_id[5:]
            self._start_conversion(file_path)
        elif option_id == "scan":
            self._populate_file_menu(deep_scan=True)
        elif option_id == "type_path":
            self._show_path_input()
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
            self._start_conversion(path)

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
        """Recursively scan for video files only."""
        results = []
        try:
            for root, dirs, files in os.walk(directory):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
                for f in files:
                    ext = os.path.splitext(f)[1].lower().lstrip('.')
                    if ext in VIDEO_EXTENSIONS:
                        results.append(os.path.join(root, f))
                        if len(results) >= 200:
                            return results
        except OSError:
            pass
        return results

    def _show_scan_results(self, directory: str, results: list) -> None:
        """Update the suggestion list with scan results."""
        self.query_one("#path-scan-info", Static).update(
            f"[dim]📁 {directory}  ({len(results)} videos found)[/dim]"
        )

        menu = self.query_one("#path-suggestions", StyledOptionList)
        menu.clear_options()

        for path in results[:20]:
            name = os.path.basename(path)
            parent = os.path.basename(os.path.dirname(path))
            menu.add_option(create_menu_option("🎬", name, f"({parent})", "video", f"file:{path}"))

    # ─── Conversion ───────────────────────────────────────────────────────────

    def _start_conversion(self, file_path: str) -> None:
        self.selected_file = file_path
        self.is_converting = True

        self.query_one("#file-menu").add_class("hidden")
        self.query_one("#path-section").add_class("hidden")
        self.query_one("#progress-section").remove_class("hidden")

        self._render_progress_bar(0)

        self.query_one("#progress-label", Label).update("🔄 Converting to WAV...")
        self.query_one("#progress-file", Static).update(f"[cyan]📁 {os.path.basename(file_path)}[/cyan]")
        self.query_one("#progress-status", Static).update("[dim]Using ffmpeg...[/dim]")

        self._conversion_worker(file_path)

    def _render_progress_bar(self, percent: int) -> None:
        bar_width = 30
        filled = int(bar_width * percent / 100)
        empty = bar_width - filled
        bar = f"[#50fa7b]{'█' * filled}[/#50fa7b][#44475a]{'░' * empty}[/#44475a]"
        self.query_one("#progress-bar", Static).update(bar)

    @work(thread=True, exclusive=True)
    def _conversion_worker(self, input_file: str) -> None:
        input_dir = os.path.dirname(input_file)
        input_stem = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(input_dir, f"{input_stem}.wav")

        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            self.app.call_from_thread(self._show_error, "ffmpeg not found! Please install ffmpeg.")
            return

        try:
            cmd = [
                "ffmpeg",
                "-i", input_file,
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "44100",
                "-ac", "2",
                "-y",
                output_file
            ]

            self.app.call_from_thread(self._render_progress_bar, 50)

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
        self.is_converting = False
        self.query_one("#progress-label", Label).update("[bold #50fa7b]✅ Success![/bold #50fa7b]")
        self._render_progress_bar(100)
        self.query_one("#progress-status", Static).update(f"[cyan]{message}[/cyan]")
        self.query_one("#continue-btn").remove_class("hidden")
        self.query_one("#continue-btn", Button).focus()
        notify_complete(self.app)

    def _show_error(self, message: str) -> None:
        self.is_converting = False
        self.query_one("#progress-label", Label).update("[bold #ff5555]❌ Error[/bold #ff5555]")
        self._render_progress_bar(0)
        self.query_one("#progress-status", Static).update(f"[red]{message}[/red]")
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
        if self.is_converting:
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

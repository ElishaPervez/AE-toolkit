# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - YouTube Screen
# Download videos or audio from YouTube
# ═══════════════════════════════════════════════════════════════════════════════

import os
import re
import shutil
import subprocess
import logging
from datetime import datetime
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Static, Input, Button, Label
from textual.containers import Vertical, Horizontal, Center
from textual import work

from amv.widgets.menu import StyledOptionList, create_menu_option, create_separator
from amv.config import ensure_output_dirs, SCRIPT_DIR

# Setup debug logger to file
_log_file = os.path.join(SCRIPT_DIR, "amv_debug.log")
_logger = logging.getLogger("amv.youtube")
_logger.setLevel(logging.DEBUG)
_fh = logging.FileHandler(_log_file, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
_logger.addHandler(_fh)


class YouTubeScreen(Screen):
    """YouTube download screen with URL input and format selection."""
    
    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
    ]
    
    def __init__(self):
        super().__init__()
        self.download_mode = "audio"  # Default to audio
        self.is_downloading = False
    
    def compose(self) -> ComposeResult:
        dirs = ensure_output_dirs()
        
        with Vertical():
            yield Static("[bold #00d4ff]📺 DOWNLOAD FROM YOUTUBE[/bold #00d4ff]", id="header", classes="screen-header")
            yield Static("[dim]Download videos or audio from YouTube[/dim]", classes="screen-subtitle")
            yield Static(f"[dim]Videos: {dirs['video']}[/dim]", classes="path-info")
            yield Static(f"[dim]Audio: {dirs['audio']}[/dim]", classes="path-info")
            yield Static("")  # Spacer

            # Success banner (hidden, shown after download completes)
            yield Static("", id="success-banner", classes="hidden")

            # Menu for mode selection
            with Center():
                yield StyledOptionList(
                    create_menu_option("🎵", "Download Audio", "Extract as high-quality WAV", "audio", "audio"),
                    create_menu_option("🎬", "Download Video", "Best quality MP4", "video", "video"),
                    create_separator(),
                    create_menu_option("📂", "Open video folder", "", "folder", "open_video"),
                    create_menu_option("📂", "Open audio folder", "", "folder", "open_audio"),
                    create_separator(),
                    create_menu_option("⬅️", "Back to Main Menu", "", "back", "back"),
                    id="youtube-menu"
                )
            
            # URL input (hidden initially, shown when audio/video selected)
            with Vertical(id="input-section", classes="hidden"):
                yield Static("[bold]Enter YouTube URL:[/bold]", classes="input-label")
                yield Input(placeholder="https://youtube.com/watch?v=...", id="url-input")
                with Horizontal(classes="button-row"):
                    yield Button("Download", id="download-btn", variant="primary")
                    yield Button("Cancel", id="cancel-btn", variant="default")
            
            # Progress section (hidden initially)
            with Vertical(id="progress-section", classes="hidden"):
                yield Label("Downloading...", id="progress-label")
                yield Static("", id="video-bar", classes="progress-bar-row hidden")
                yield Static("", id="audio-bar", classes="progress-bar-row hidden")
                yield Static("", id="progress-status")
                with Center():
                    yield Button("⏎ Press Enter to continue", id="continue-btn", classes="hidden")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Focus the menu on mount."""
        self.query_one("#youtube-menu").focus()
    
    def on_option_list_option_selected(self, event) -> None:
        """Handle menu selection."""
        option_id = event.option_id
        
        if option_id == "audio":
            self.download_mode = "audio"
            self._show_input()
        elif option_id == "video":
            self.download_mode = "video"
            self._show_input()
        elif option_id == "open_video":
            dirs = ensure_output_dirs()
            self._open_folder(dirs["video"])
        elif option_id == "open_audio":
            dirs = ensure_output_dirs()
            self._open_folder(dirs["audio"])
        elif option_id == "back":
            self.action_go_back()
    
    def _show_input(self) -> None:
        """Show the URL input section."""
        self.query_one("#youtube-menu").add_class("hidden")
        self.query_one("#success-banner").add_class("hidden")
        self.query_one("#input-section").remove_class("hidden")
        self.query_one("#url-input").focus()
    
    def _show_menu(self) -> None:
        """Show the menu, hide input/progress."""
        self.query_one("#input-section").add_class("hidden")
        self.query_one("#progress-section").add_class("hidden")
        self.query_one("#video-bar").add_class("hidden")
        self.query_one("#audio-bar").add_class("hidden")
        self.query_one("#continue-btn").add_class("hidden")
        self.query_one("#youtube-menu").remove_class("hidden")
        self.query_one("#youtube-menu").focus()

    def _show_success_banner(self, title: str) -> None:
        """Show success banner on the YouTube menu."""
        banner = self.query_one("#success-banner", Static)
        banner.update(f"[bold #50fa7b]  \u2714  {title}  \u2014  downloaded successfully[/bold #50fa7b]")
        banner.remove_class("hidden")
    
    def _open_folder(self, path: str) -> None:
        """Open folder in file explorer."""
        if os.name == 'nt':
            os.startfile(path)
        else:
            subprocess.run(['xdg-open', path])
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "download-btn":
            url = self.query_one("#url-input", Input).value.strip()
            if url:
                self._start_download(url)
        elif event.button.id == "cancel-btn":
            self._show_menu()
        elif event.button.id == "continue-btn":
            self._show_menu()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        url = event.value.strip()
        if url:
            self._start_download(url)
    
    def _start_download(self, url: str) -> None:
        """Start the download process."""
        _logger.info("=" * 60)
        _logger.info("NEW DOWNLOAD STARTED")
        _logger.info(f"  Mode: {self.download_mode}")
        _logger.info(f"  URL: {url}")
        _logger.info(f"  AMV_ORIGINAL_DIR: {os.environ.get('AMV_ORIGINAL_DIR', '(not set)')}")
        _logger.info(f"  CWD: {os.getcwd()}")

        self.is_downloading = True
        self.query_one("#input-section").add_class("hidden")
        self.query_one("#progress-section").remove_class("hidden")

        mode_label = "audio" if self.download_mode == "audio" else "video"
        self.query_one("#progress-label", Label).update(f"⬇️ Downloading {mode_label}...")

        # Show the appropriate progress bars
        self.query_one("#audio-bar").remove_class("hidden")
        if self.download_mode == "video":
            self.query_one("#video-bar").remove_class("hidden")

        # Reset bars
        self._set_bar("video-bar", "Video", 0)
        self._set_bar("audio-bar", "Audio", 0)

        self._download_worker(url)

    @staticmethod
    def _render_bar(label: str, pct: float, width: int = 50) -> str:
        """Render a progress bar as a Rich markup string."""
        filled = int(width * pct / 100)
        empty = width - filled
        bar_filled = "\u2588" * filled   # █
        bar_empty = "\u2591" * empty     # ░
        return (
            f"[bold cyan]{label}[/bold cyan]  "
            f"[#00d4ff]{bar_filled}[/#00d4ff][#333333]{bar_empty}[/#333333]"
            f"  [bold #00d4ff]{pct:5.1f}%[/bold #00d4ff]"
        )

    def _set_bar(self, widget_id: str, label: str, pct: float) -> None:
        """Update a bar Static widget with rendered progress."""
        self.query_one(f"#{widget_id}", Static).update(
            self._render_bar(label, pct)
        )

    @work(thread=True, exclusive=True)
    def _download_worker(self, url: str) -> None:
        """Background threaded worker for download."""
        dirs = ensure_output_dirs()
        pct_re = re.compile(r'\[download\]\s+(\d+\.?\d*)%')

        if self.download_mode == "audio":
            output_path = dirs["audio"]
            cmd = ["yt-dlp", "-x", "--audio-format", "wav", "--audio-quality", "0",
                   "--newline", "--progress",
                   "-o", os.path.join(output_path, "%(title)s.%(ext)s"), url]
        else:
            output_path = dirs["video"]
            cmd = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                   "--newline", "--progress",
                   "-o", os.path.join(output_path, "%(title)s.%(ext)s"), url]

        _logger.info(f"  Output path: {output_path}")
        _logger.info(f"  Output dir exists: {os.path.exists(output_path)}")
        _logger.info(f"  Command: {cmd}")

        # Check yt-dlp availability
        yt_dlp_path = shutil.which("yt-dlp")
        _logger.info(f"  yt-dlp which: {yt_dlp_path}")
        _logger.info(f"  PATH: {os.environ.get('PATH', '(not set)')}")

        try:
            _logger.info("  Launching subprocess...")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
            )
            _logger.info(f"  Process PID: {process.pid}")

            destination_count = 0
            download_title = ""
            buf = b""
            line_count = 0

            # Read raw bytes and split on both \n and \r for Windows yt-dlp compat
            while True:
                chunk = process.stdout.read(1)
                if not chunk:
                    _logger.info("  EOF reached on stdout")
                    break
                if chunk in (b"\n", b"\r"):
                    if not buf:
                        continue
                    line = buf.decode("utf-8", errors="replace").strip()
                    buf = b""
                    line_count += 1

                    # Log every line from yt-dlp
                    _logger.debug(f"  yt-dlp [{line_count}]: {line}")

                    # Track stream switches via Destination lines
                    if "[download] Destination:" in line:
                        destination_count += 1
                        # Extract title from first destination filename
                        if destination_count == 1:
                            dest_path = line.split("Destination:", 1)[1].strip()
                            download_title = os.path.splitext(os.path.basename(dest_path))[0]
                            # Strip format suffixes like .f137 or .f140
                            download_title = re.sub(r'\.f\d+$', '', download_title)
                        _logger.info(f"  Destination #{destination_count}: {line}")

                    # Parse percentage
                    match = pct_re.search(line)
                    if match:
                        pct = float(match.group(1))
                        if self.download_mode == "video":
                            if destination_count <= 1:
                                self.app.call_from_thread(self._set_bar, "video-bar", "Video", pct)
                            else:
                                self.app.call_from_thread(self._set_bar, "audio-bar", "Audio", pct)
                        else:
                            self.app.call_from_thread(self._set_bar, "audio-bar", "Audio", pct)

                    # Show merger/extract status text
                    if "[Merger]" in line or "[ExtractAudio]" in line:
                        _logger.info(f"  Post-process: {line}")
                        self.app.call_from_thread(self._update_progress_status, line[:80])
                else:
                    buf += chunk

            process.wait()
            _logger.info(f"  Process exited with return code: {process.returncode}")
            _logger.info(f"  Total lines read: {line_count}")

            # List files in output directory
            if os.path.exists(output_path):
                files = os.listdir(output_path)
                _logger.info(f"  Files in output dir ({len(files)}): {files}")
            else:
                _logger.warning(f"  Output dir does not exist: {output_path}")

            if process.returncode == 0:
                # Fill bars to 100% on success
                if self.download_mode == "video":
                    self.app.call_from_thread(self._set_bar, "video-bar", "Video", 100)
                self.app.call_from_thread(self._set_bar, "audio-bar", "Audio", 100)
                title = download_title or "Download"
                _logger.info(f"  Parsed title: {title}")
                self.app.call_from_thread(self._show_success, title)
            else:
                _logger.error(f"  yt-dlp failed with code {process.returncode}")
                self.app.call_from_thread(self._show_error, "Download failed!")

        except FileNotFoundError as e:
            _logger.error(f"  FileNotFoundError: {e}")
            self.app.call_from_thread(self._show_error, "yt-dlp not found! Run setup first.")
        except Exception as e:
            _logger.error(f"  Exception: {type(e).__name__}: {e}", exc_info=True)
            self.app.call_from_thread(self._show_error, str(e))
    
    def _update_progress_status(self, status: str) -> None:
        """Update progress status text."""
        self.query_one("#progress-status", Static).update(f"[dim]{status}[/dim]")
    
    def _show_success(self, title: str) -> None:
        """Show success message on completion."""
        self.is_downloading = False
        self.query_one("#progress-label", Label).update("[bold #50fa7b]✅ Download Complete![/bold #50fa7b]")
        self.query_one("#progress-status", Static).update(f"[cyan]{title}[/cyan]")
        self.query_one("#continue-btn").remove_class("hidden")
        self.query_one("#continue-btn", Button).focus()
    
    def _show_error(self, message: str) -> None:
        """Show error message."""
        self.is_downloading = False
        self.query_one("#progress-label", Label).update("[bold #ff5555]❌ Error[/bold #ff5555]")
        self.query_one("#progress-status", Static).update(f"[red]{message}[/red]")
        self.query_one("#continue-btn").remove_class("hidden")
        self.query_one("#continue-btn", Button).focus()
    
    def action_go_back(self) -> None:
        """Go back to main menu."""
        if not self.is_downloading:
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
    
    #input-section {
        padding: 2 4;
    }
    
    .input-label {
        padding: 0 4;
    }
    
    #url-input {
        margin: 1 4;
    }
    
    .button-row {
        padding: 1 4;
        align: center middle;
    }
    
    #progress-section {
        padding: 3 4;
        margin: 1 4;
        border: round #0080ff;
        height: 1fr;
        content-align: center middle;
    }

    #progress-label {
        text-align: center;
        text-style: bold;
        padding: 1 0 2 0;
        width: 100%;
    }

    #progress-status {
        text-align: center;
        padding: 1 0;
        width: 100%;
    }

    .progress-bar-row {
        text-align: center;
        width: 100%;
        margin: 1 0;
    }

    #success-banner {
        text-align: center;
        padding: 1 2;
        margin: 0 4;
        background: #0a3a0a;
        border: round #50fa7b;
    }
    """

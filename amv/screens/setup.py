# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Setup Screen
# Dependency checking and installation
# ═══════════════════════════════════════════════════════════════════════════════

import sys
import subprocess
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Static, DataTable, Button, Label
from textual.containers import Vertical, Horizontal, Center
from textual.worker import get_current_worker

from amv.config import CONFIG_FILE, save_config, load_config
from amv.hardware import get_torch_status, get_ort_status, get_hw_info


# Required packages
REQUIRED_PACKAGES = {
    "yt-dlp": "yt-dlp",
    "rich": "rich",
    "pydub": "pydub",
}

CPU_PACKAGES = {
    "audio-separator": "audio-separator",
    "onnxruntime": "onnxruntime"
}


class SetupScreen(Screen):
    """Setup screen for dependency checking and installation."""
    
    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
    ]
    
    def __init__(self):
        super().__init__()
        self.issues = []
        self.installs = []
        self.is_installing = False
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("[bold #00d4ff]🔧 SYSTEM SETUP[/bold #00d4ff]", id="header", classes="screen-header")
            yield Static("[dim]Configure CPU-only dependencies[/dim]", classes="screen-subtitle")
            yield Static("")  # Spacer
            
            # Status table
            yield DataTable(id="status-table", zebra_stripes=True)
            
            # Issues panel (shown if issues found)
            with Vertical(id="issues-panel", classes="hidden"):
                yield Static("[bold #ffb86c]⚠️ Missing Components[/bold #ffb86c]", classes="panel-title")
                yield Static(id="issues-list")
                yield Static("")
                yield Static("[bold]Required Actions:[/bold]")
                yield Static(id="actions-list")
                with Horizontal(classes="button-row"):
                    yield Button("Install All", id="install-btn", variant="primary")
                    yield Button("Back", id="back-btn", variant="default")
            
            # Success message (shown if all good)
            yield Static(id="success-msg", classes="hidden")
            
            # Installation progress
            with Vertical(id="install-progress", classes="hidden"):
                yield Label("Installing...", id="install-label")
                yield Static("", id="install-status")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Run dependency check on mount."""
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """Check all dependencies and populate status table."""
        self.issues = []
        self.installs = []
        
        # Status table
        table = self.query_one("#status-table", DataTable)
        table.clear(columns=True)
        table.add_column("Component", key="component")
        table.add_column("Status", key="status")
        
        # Hardware info
        hw_info = get_hw_info()
        table.add_row("[cyan]Detected Hardware[/cyan]", hw_info["device"])
        table.add_row("[cyan]Setup Target[/cyan]", "CPU")
        
        # PyTorch check
        torch_avail, torch_ver = get_torch_status()
        if torch_avail:
            table.add_row("[cyan]PyTorch[/cyan]", f"[green]{torch_ver}[/green]")
        else:
            table.add_row("[cyan]PyTorch[/cyan]", "[red]Missing[/red]")
            self.issues.append("PyTorch: Missing")
            self.installs.append("pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu")
        
        # ONNX Runtime check
        ort_avail = self._check_package("onnxruntime")
        if ort_avail:
            table.add_row("[cyan]ONNX Runtime[/cyan]", "[green]Installed[/green]")
        else:
            table.add_row("[cyan]ONNX Runtime[/cyan]", "[red]Missing[/red]")
            self.issues.append("onnxruntime: Missing")
            self.installs.append("pip install onnxruntime")
        
        # FFmpeg check
        if self._check_command("ffmpeg"):
            table.add_row("[cyan]FFmpeg[/cyan]", "[green]Installed[/green]")
        else:
            table.add_row("[cyan]FFmpeg[/cyan]", "[red]Missing[/red]")
            self.issues.append("ffmpeg: Missing")
            self.installs.append("# Download FFmpeg from ffmpeg.org and add to PATH")
        
        # yt-dlp check
        if self._check_command("yt-dlp"):
            table.add_row("[cyan]yt-dlp[/cyan]", "[green]Installed[/green]")
        else:
            table.add_row("[cyan]yt-dlp[/cyan]", "[red]Missing[/red]")
            self.issues.append("yt-dlp: Missing")
            self.installs.append("pip install yt-dlp")
        
        # Audio separator check
        if self._check_package("audio-separator"):
            table.add_row("[cyan]audio-separator[/cyan]", "[green]Installed[/green]")
        else:
            table.add_row("[cyan]audio-separator[/cyan]", "[red]Missing[/red]")
            self.issues.append("audio-separator: Missing")
            self.installs.append("pip install audio-separator")
        
        # Show result
        if self.issues:
            self._show_issues()
        else:
            self._show_success()
    
    def _check_command(self, cmd: str) -> bool:
        """Check if a command exists in PATH."""
        try:
            subprocess.run([cmd, "--version"], capture_output=True, timeout=5)
            return True
        except:
            return False
    
    def _check_package(self, package: str) -> bool:
        """Check if a Python package is installed."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except:
            return False
    
    def _show_issues(self) -> None:
        """Show issues panel."""
        issues_text = "\n".join(f"  • {issue}" for issue in self.issues)
        actions_text = "\n".join(f"  [cyan]{cmd}[/cyan]" for cmd in self.installs)
        
        self.query_one("#issues-list", Static).update(issues_text)
        self.query_one("#actions-list", Static).update(actions_text)
        self.query_one("#issues-panel").remove_class("hidden")
        self.query_one("#success-msg").add_class("hidden")
    
    def _show_success(self) -> None:
        """Show success message."""
        # Save config
        config = load_config()
        config["setup_type"] = "cpu"
        config["force_cpu"] = True
        save_config(config)
        
        self.query_one("#issues-panel").add_class("hidden")
        self.query_one("#success-msg").remove_class("hidden")
        self.query_one("#success-msg", Static).update(
            "[bold #50fa7b]✅ System configured for CPU![/bold #50fa7b]\n\n"
            "[dim]Press Escape to return to menu.[/dim]"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "install-btn":
            self._start_installation()
        elif event.button.id == "back-btn":
            self.action_go_back()
    
    def _start_installation(self) -> None:
        """Start installing missing packages."""
        self.is_installing = True
        self.query_one("#issues-panel").add_class("hidden")
        self.query_one("#install-progress").remove_class("hidden")
        
        self.run_worker(self._install_worker(), exclusive=True)
    
    async def _install_worker(self) -> None:
        """Background worker for package installation."""
        worker = get_current_worker()
        
        for i, cmd in enumerate(self.installs):
            if cmd.startswith("#"):
                continue  # Skip comments
            
            if worker.is_cancelled:
                return
            
            self.call_from_thread(
                self._update_install_status,
                f"Installing ({i+1}/{len(self.installs)})...",
                cmd
            )
            
            try:
                subprocess.run(cmd.split(), capture_output=True, timeout=300)
            except Exception as e:
                self.call_from_thread(self._update_install_status, "Error", str(e))
        
        self.call_from_thread(self._install_complete)
    
    def _update_install_status(self, label: str, status: str) -> None:
        """Update installation status."""
        self.query_one("#install-label", Label).update(label)
        self.query_one("#install-status", Static).update(f"[dim]{status}[/dim]")
    
    def _install_complete(self) -> None:
        """Installation complete callback."""
        self.is_installing = False
        self.query_one("#install-progress").add_class("hidden")
        self._check_dependencies()  # Re-check
    
    def action_go_back(self) -> None:
        """Go back to main/settings menu."""
        if not self.is_installing:
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
    
    #status-table {
        margin: 1 4;
        height: auto;
        max-height: 12;
    }
    
    .hidden {
        display: none;
    }
    
    #issues-panel {
        margin: 1 4;
        padding: 1 2;
        border: round #ffb86c;
    }
    
    .panel-title {
        text-align: center;
        padding-bottom: 1;
    }
    
    .button-row {
        padding: 1 0;
        align: center middle;
    }
    
    #success-msg {
        text-align: center;
        padding: 2 4;
        margin: 1 4;
        border: round #50fa7b;
    }
    
    #install-progress {
        padding: 2 4;
        margin: 1 4;
        border: round #0080ff;
    }
    
    #install-label {
        text-align: center;
        text-style: bold;
        padding: 1;
    }
    
    #install-status {
        text-align: center;
        padding: 1;
    }
    """

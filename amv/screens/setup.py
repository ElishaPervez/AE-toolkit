# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Setup Screen
# Dependency checking, installation, and CPU/GPU mode switching
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import subprocess
import logging
from datetime import datetime
from textual.app import ComposeResult
from textual.widgets import Footer, Static, DataTable, Button, Label
from textual.containers import Vertical, Horizontal, Center
from textual.worker import get_current_worker

from textual.screen import Screen
from amv.config import SCRIPT_DIR, save_config, load_config
from amv.hardware import get_torch_status, get_ort_status, get_hw_info, refresh_vram
from amv.gpu import (
    check_nvidia_gpu, get_torch_install_cmd,
    get_gpu_switch_cmds, get_cpu_switch_cmds, verify_cuda_torch,
)

# ─── Logging ──────────────────────────────────────────────────────────────────

LOG_DIR = os.path.join(SCRIPT_DIR, "logs")

def _get_logger() -> logging.Logger:
    """Get or create the setup logger that writes to logs/setup_YYYY-MM-DD.log."""
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger("amv.setup")
    if not logger.handlers:
        today = datetime.now().strftime("%Y-%m-%d")
        fh = logging.FileHandler(
            os.path.join(LOG_DIR, f"setup_{today}.log"), encoding="utf-8"
        )
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
        ))
        logger.addHandler(fh)
        logger.setLevel(logging.DEBUG)
    return logger


def _fmt_cmd(cmd) -> str:
    """Format a command (list or string) for display."""
    if isinstance(cmd, list):
        return " ".join(cmd)
    return cmd


class SetupScreen(Screen):
    """Setup screen for dependency checking, installation, and mode switching.

    Args:
        target_mode: Force a specific mode ("gpu" or "cpu"). When set, the screen
                     builds switch commands to transition to that mode. When None,
                     auto-detects based on nvidia-smi.
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
        ("left", "go_back"),
    ]

    def __init__(self, target_mode: str | None = None):
        super().__init__()
        self.target_mode = target_mode  # "gpu", "cpu", or None (auto)
        self.issues = []
        self.installs = []       # list of list[str] (arg lists for subprocess)
        self.is_installing = False
        self.gpu_name = None
        self._logger = _get_logger()

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("[bold #00d4ff]🔧 SYSTEM SETUP[/bold #00d4ff]", id="header", classes="screen-header")
            yield Static("[dim]Auto-detecting hardware and dependencies[/dim]", id="subtitle", classes="screen-subtitle")
            yield Static("")  # Spacer

            # Status table
            yield DataTable(id="status-table", zebra_stripes=True)

            # Issues panel (shown if issues found)
            with Vertical(id="issues-panel", classes="hidden"):
                yield Static("[bold #ffb86c]⚠️ Required Changes[/bold #ffb86c]", classes="panel-title")
                yield Static(id="issues-list")
                yield Static("")
                yield Static("[bold]Commands to run:[/bold]")
                yield Static(id="actions-list")

            # Action buttons (outside panel so they're always visible)
            with Horizontal(id="action-buttons", classes="hidden"):
                yield Button("Switch Dependencies", id="install-btn", variant="primary")
                yield Button("Back", id="back-btn", variant="default")

            # Success message (shown if all good)
            yield Static(id="success-msg", classes="hidden")

            # Installation progress
            with Vertical(id="install-progress", classes="hidden"):
                yield Label("Installing...", id="install-label")
                yield Static("", id="install-status")
                yield Static("", id="install-detail")

        yield Footer()

    def on_mount(self) -> None:
        """Start dependency checks without blocking the UI."""
        subtitle = None
        if self.target_mode == "gpu":
            subtitle = "[dim]Switching to GPU mode (CUDA 12.8 / RTX 50 series)[/dim]"
        elif self.target_mode == "cpu":
            subtitle = "[dim]Switching to CPU mode[/dim]"

        self._show_checking_state(subtitle)
        self._logger.info(f"Setup opened: target_mode={self.target_mode}")
        self.run_worker(self._run_initial_checks, thread=True, exclusive=True)

    def _show_checking_state(self, subtitle: str | None = None) -> None:
        """Show a loading state while checks run in the background."""
        if subtitle:
            self.query_one("#subtitle", Static).update(subtitle)

        table = self.query_one("#status-table", DataTable)
        table.clear(columns=True)
        table.add_column("Component", key="component")
        table.add_column("Status", key="status")
        table.add_row("[cyan]Status[/cyan]", "[dim]Checking system...[/dim]")

        self.query_one("#issues-panel").add_class("hidden")
        self.query_one("#action-buttons").add_class("hidden")
        self.query_one("#success-msg").add_class("hidden")
        self.query_one("#install-progress").add_class("hidden")
        self.is_installing = False
        self.issues = []
        self.installs = []

    def _run_initial_checks(self) -> None:
        """Run setup checks in a worker thread."""
        if self.target_mode == "gpu":
            results = self._collect_gpu_switch()
        elif self.target_mode == "cpu":
            results = self._collect_cpu_switch()
        else:
            results = self._collect_dependency_check()
        self.app.call_from_thread(self._apply_results, results)

    # ─── Mode Switch Flows ────────────────────────────────────────────────────

    def _collect_gpu_switch(self) -> dict:
        """Collect data for switching to GPU mode."""
        issues = []
        installs = []
        rows = []

        gpu_name = check_nvidia_gpu()
        if gpu_name:
            rows.append(("[cyan]Detected GPU[/cyan]", f"[green]{gpu_name}[/green]"))
        else:
            rows.append(("[cyan]Detected GPU[/cyan]", "[red]No NVIDIA GPU found[/red]"))

        config = load_config()
        current = config.get("setup_type", "cpu")
        rows.append(("[cyan]Current Mode[/cyan]", f"{current.upper()}"))
        rows.append(("[cyan]Target Mode[/cyan]", "[bold #50fa7b]GPU (CUDA 12.8 / cu128)[/bold #50fa7b]"))

        cuda_ready = verify_cuda_torch()
        if cuda_ready and current == "gpu":
            rows.append(("[cyan]CUDA PyTorch[/cyan]", "[green]Already installed[/green]"))
            return {
                "rows": rows,
                "issues": [],
                "installs": [],
                "success_mode": "gpu",
                "gpu_name": gpu_name,
            }

        rows.append(("[cyan]CUDA PyTorch[/cyan]", "[yellow]Needs install (cu128 for SM_120)[/yellow]"))

        installs = get_gpu_switch_cmds()
        issues = [
            "Uninstall CPU-only torch",
            "Install PyTorch with CUDA 12.8 (cu128) for RTX 50 series",
            "Install audio-separator[gpu]",
        ]
        return {
            "rows": rows,
            "issues": issues,
            "installs": installs,
            "success_mode": None,
            "gpu_name": gpu_name,
        }

    def _build_gpu_switch(self) -> None:
        """Build the command list for switching to GPU mode."""
        self._apply_results(self._collect_gpu_switch())

    def _collect_cpu_switch(self) -> dict:
        """Collect data for switching to CPU mode."""
        issues = []
        installs = []
        rows = []

        config = load_config()
        current = config.get("setup_type", "cpu")
        rows.append(("[cyan]Current Mode[/cyan]", f"{current.upper()}"))
        rows.append(("[cyan]Target Mode[/cyan]", "[bold #ffb86c]CPU[/bold #ffb86c]"))

        if current == "cpu" and not verify_cuda_torch():
            rows.append(("[cyan]CPU PyTorch[/cyan]", "[green]Already installed[/green]"))
            return {
                "rows": rows,
                "issues": [],
                "installs": [],
                "success_mode": "cpu",
                "gpu_name": None,
            }

        rows.append(("[cyan]CPU PyTorch[/cyan]", "[yellow]Needs install[/yellow]"))

        installs = get_cpu_switch_cmds()
        issues = [
            "Uninstall CUDA torch",
            "Install CPU-only PyTorch",
            "Install onnxruntime for ONNX models",
        ]
        return {
            "rows": rows,
            "issues": issues,
            "installs": installs,
            "success_mode": None,
            "gpu_name": None,
        }

    def _build_cpu_switch(self) -> None:
        """Build the command list for switching to CPU mode."""
        self._apply_results(self._collect_cpu_switch())

    # ─── Auto-Detect Flow ─────────────────────────────────────────────────────

    def _collect_dependency_check(self) -> dict:
        """Collect dependency status without touching the UI."""
        issues = []
        installs = []
        rows = []

        config = load_config()
        current_mode = config.get("setup_type", "cpu")
        setup_target = current_mode.upper()
        is_gpu_mode = current_mode == "gpu"
        force_cpu = config.get("force_cpu", False)

        hw_info = refresh_vram()
        gpu_name = None
        if force_cpu:
            gpu_name = check_nvidia_gpu()
        elif hw_info.get("gpu_type") == "nvidia":
            gpu_name = hw_info.get("device")
            if gpu_name and " (CUDA torch not installed)" in gpu_name:
                gpu_name = gpu_name.replace(" (CUDA torch not installed)", "")

        if gpu_name:
            rows.append(("[cyan]Detected GPU[/cyan]", f"[green]{gpu_name}[/green]"))
        else:
            rows.append(("[cyan]Detected Hardware[/cyan]", hw_info["device"]))
        rows.append(("[cyan]Current Mode[/cyan]", f"[bold]{setup_target}[/bold]"))

        torch_avail, torch_ver = get_torch_status()
        if torch_avail:
            cuda_ready = verify_cuda_torch()
            if is_gpu_mode and not cuda_ready:
                rows.append(("[cyan]PyTorch[/cyan]", f"[yellow]{torch_ver} (CPU-only, needs CUDA)[/yellow]"))
                issues.append("PyTorch: CPU-only build installed, need CUDA build")
                installs = get_gpu_switch_cmds()
            elif not is_gpu_mode and cuda_ready:
                rows.append(("[cyan]PyTorch[/cyan]", f"[yellow]{torch_ver} (CUDA, but in CPU mode)[/yellow]"))
            else:
                rows.append(("[cyan]PyTorch[/cyan]", f"[green]{torch_ver}[/green]"))
        else:
            rows.append(("[cyan]PyTorch[/cyan]", "[red]Missing[/red]"))
            issues.append("PyTorch: Missing")
            installs.append(get_torch_install_cmd(is_gpu_mode))

        ort_avail = self._check_package("onnxruntime")
        if ort_avail:
            rows.append(("[cyan]ONNX Runtime[/cyan]", "[green]Installed[/green]"))
        else:
            rows.append(("[cyan]ONNX Runtime[/cyan]", "[red]Missing[/red]"))
            issues.append("onnxruntime: Missing")
            installs.append([sys.executable, "-m", "pip", "install", "onnxruntime"])

        if self._check_command("ffmpeg"):
            rows.append(("[cyan]FFmpeg[/cyan]", "[green]Installed[/green]"))
        else:
            rows.append(("[cyan]FFmpeg[/cyan]", "[red]Missing[/red]"))
            issues.append("ffmpeg: Missing (install from ffmpeg.org)")

        if self._check_command("yt-dlp"):
            rows.append(("[cyan]yt-dlp[/cyan]", "[green]Installed[/green]"))
        else:
            rows.append(("[cyan]yt-dlp[/cyan]", "[red]Missing[/red]"))
            issues.append("yt-dlp: Missing")
            installs.append([sys.executable, "-m", "pip", "install", "yt-dlp"])

        as_pkg = "audio-separator[gpu]" if is_gpu_mode else "audio-separator"
        if self._check_package("audio-separator"):
            rows.append(("[cyan]audio-separator[/cyan]", "[green]Installed[/green]"))
        else:
            rows.append(("[cyan]audio-separator[/cyan]", "[red]Missing[/red]"))
            issues.append("audio-separator: Missing")
            installs.append([sys.executable, "-m", "pip", "install", as_pkg])

        return {
            "rows": rows,
            "issues": issues,
            "installs": installs,
            "success_mode": current_mode if not issues else None,
            "gpu_name": gpu_name,
            "refresh_hardware": False,
        }

    def _check_dependencies(self) -> None:
        """Check all dependencies and populate status table."""
        self._apply_results(self._collect_dependency_check())

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _apply_results(self, results: dict) -> None:
        """Apply collected status results to the UI."""
        self.issues = results["issues"]
        self.installs = results["installs"]
        self.gpu_name = results.get("gpu_name")

        table = self.query_one("#status-table", DataTable)
        table.clear(columns=True)
        table.add_column("Component", key="component")
        table.add_column("Status", key="status")
        for component, status in results["rows"]:
            table.add_row(component, status)

        success_mode = results.get("success_mode")
        if success_mode:
            self._show_success_for_mode(
                success_mode,
                refresh_hardware=results.get("refresh_hardware", True),
            )
        elif self.issues:
            self._show_issues()

        self._logger.info(f"Setup check complete: target_mode={self.target_mode}, gpu_name={self.gpu_name}")

    def _check_command(self, cmd: str) -> bool:
        """Check if a command exists in PATH."""
        try:
            subprocess.run([cmd, "--version"], capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False

    def _check_package(self, package: str) -> bool:
        """Check if a Python package is installed."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False

    def _show_issues(self) -> None:
        """Show issues panel and action buttons."""
        issues_text = "\n".join(f"  • {issue}" for issue in self.issues)
        actions_text = "\n".join(f"  [cyan]{_fmt_cmd(cmd)}[/cyan]" for cmd in self.installs)

        self.query_one("#issues-list", Static).update(issues_text)
        self.query_one("#actions-list", Static).update(actions_text)
        self.query_one("#issues-panel").remove_class("hidden")
        self.query_one("#action-buttons").remove_class("hidden")
        self.query_one("#success-msg").add_class("hidden")
        self.query_one("#install-btn", Button).focus()

    def _show_success_for_mode(self, mode: str, refresh_hardware: bool = True) -> None:
        """Show success message and save config for the given mode."""
        config = load_config()
        if mode == "gpu":
            config["setup_type"] = "gpu"
            config["force_cpu"] = False
            label = f"GPU ({self.gpu_name})" if self.gpu_name else "GPU"
            color = "#50fa7b"
        else:
            config["setup_type"] = "cpu"
            config["force_cpu"] = True
            label = "CPU"
            color = "#ffb86c"
        save_config(config)

        # Force hardware cache refresh so other screens pick up the change
        if refresh_hardware:
            refresh_vram()

        self._logger.info(f"Config saved: setup_type={mode}, force_cpu={config['force_cpu']}")

        self.query_one("#issues-panel").add_class("hidden")
        self.query_one("#action-buttons").add_class("hidden")
        self.query_one("#success-msg").remove_class("hidden")
        self.query_one("#success-msg", Static).update(
            f"[bold {color}]✅ System configured for {label}![/bold {color}]\n\n"
            f"[dim]Log: {LOG_DIR}[/dim]\n"
            "[dim]Press Escape to return. Restart the app for changes to take effect.[/dim]"
        )

    # ─── Installation ─────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "install-btn":
            self._start_installation()
        elif event.button.id == "back-btn":
            self.action_go_back()

    def _start_installation(self) -> None:
        """Start installing/switching packages."""
        self.is_installing = True
        self.query_one("#issues-panel").add_class("hidden")
        self.query_one("#action-buttons").add_class("hidden")
        self.query_one("#install-progress").remove_class("hidden")
        self._logger.info(f"Starting installation: {len(self.installs)} commands")

        self.run_worker(self._install_worker, thread=True, exclusive=True)

    def _install_worker(self) -> None:
        """Background worker for package installation with logging."""
        worker = get_current_worker()
        total = len(self.installs)
        errors = []

        for i, cmd in enumerate(self.installs):
            if worker.is_cancelled:
                self._logger.warning("Installation cancelled by user")
                return

            cmd_str = _fmt_cmd(cmd)
            step_label = f"Step {i+1}/{total}"
            self._logger.info(f"{step_label}: {cmd_str}")

            self.app.call_from_thread(
                self._update_install_status,
                f"{step_label}...",
                cmd_str,
            )

            try:
                # cmd is always a list[str] now — safe for paths with spaces
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=600
                )
                # Log stdout/stderr regardless of exit code
                if result.stdout.strip():
                    for line in result.stdout.strip().splitlines()[-10:]:
                        self._logger.debug(f"  stdout: {line}")
                if result.stderr.strip():
                    for line in result.stderr.strip().splitlines()[-10:]:
                        self._logger.debug(f"  stderr: {line}")

                if result.returncode != 0:
                    # Filter out pip notices to find actual error message
                    err_msg = f"exit code {result.returncode}"
                    if result.stderr.strip():
                        # Skip pip's informational notices and empty lines
                        real_errors = [
                            line for line in result.stderr.strip().splitlines()
                            if line.strip()  # Skip empty lines
                            and not line.strip().startswith("[notice]")
                            and "A new release of pip" not in line
                            and "To update, run:" not in line
                        ]
                        if real_errors:
                            # Find the most informative error line (prefer ERROR: lines)
                            error_lines = [l for l in real_errors if "ERROR:" in l or "error:" in l.lower()]
                            err_msg = error_lines[-1] if error_lines else real_errors[-1]
                            
                            # Provide user-friendly message for common errors
                            if "Access is denied" in err_msg or "WinError 5" in err_msg:
                                err_msg = "File locked - close other AMV/Python instances and retry"
                    self._logger.error(f"  FAILED ({result.returncode}): {err_msg}")
                    errors.append(f"Step {i+1}: {err_msg}")
                    self.app.call_from_thread(
                        self._update_install_status,
                        f"[red]{step_label} FAILED[/red]",
                        f"[red]{err_msg}[/red]",
                    )
                else:
                    self._logger.info(f"  OK")

            except subprocess.TimeoutExpired:
                self._logger.error(f"  TIMEOUT after 600s")
                errors.append(f"Step {i+1}: Timed out")
            except Exception as e:
                self._logger.error(f"  EXCEPTION: {e}")
                errors.append(f"Step {i+1}: {e}")

        if errors:
            self._logger.error(f"Installation finished with {len(errors)} error(s)")
            self.app.call_from_thread(self._install_failed, errors)
        else:
            self._logger.info("Installation finished successfully")
            self.app.call_from_thread(self._install_complete)

    def _update_install_status(self, label: str, status: str) -> None:
        """Update installation status display."""
        self.query_one("#install-label", Label).update(label)
        self.query_one("#install-status", Static).update(f"[dim]{status}[/dim]")

    def _install_complete(self) -> None:
        """Installation succeeded."""
        self.is_installing = False
        self.query_one("#install-progress").add_class("hidden")

        if self.target_mode:
            mode = self.target_mode
        else:
            mode = load_config().get("setup_type", "cpu")

        self._show_success_for_mode(mode)

    def _install_failed(self, errors: list[str]) -> None:
        """Installation had errors — show them."""
        self.is_installing = False
        self.query_one("#install-progress").add_class("hidden")
        self.query_one("#success-msg").remove_class("hidden")
        error_text = "\n".join(f"  [red]• {e}[/red]" for e in errors)
        self.query_one("#success-msg", Static).update(
            f"[bold #ff5555]❌ Installation failed[/bold #ff5555]\n\n"
            f"{error_text}\n\n"
            f"[dim]Full log: {LOG_DIR}[/dim]\n"
            "[dim]Press Escape to go back.[/dim]"
        )

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
        max-height: 14;
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

    #action-buttons {
        padding: 1 4;
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

    #install-detail {
        text-align: center;
    }
    """

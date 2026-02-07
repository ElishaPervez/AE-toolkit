# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Settings Screen
# Configuration, folder access, and GPU/CPU mode switching
# ═══════════════════════════════════════════════════════════════════════════════

import os
import subprocess
from textual.app import ComposeResult
from textual.widgets import Footer, Static, DataTable
from textual.containers import Vertical, Center

from textual.screen import Screen
from amv.widgets.menu import StyledOptionList, create_menu_option, create_separator
from amv.config import MODELS_DIR, get_output_dirs, ensure_output_dirs, load_config
from amv.hardware import get_hw_info
from amv.gpu import check_nvidia_gpu


class SettingsScreen(Screen):
    """Settings screen with configuration display, folder access, and mode switching."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
        ("left", "go_back"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("[bold #6272a4]⚙️ SETTINGS[/bold #6272a4]", id="header", classes="screen-header")
            yield Static("[dim]AMV Toolkit Configuration[/dim]", classes="screen-subtitle")
            yield Static("")  # Spacer

            # Configuration table
            yield DataTable(id="config-table", zebra_stripes=True)

            yield Static("")  # Spacer

            # Options menu (built dynamically on mount)
            with Center():
                yield StyledOptionList(id="settings-menu")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize settings display."""
        self._populate_config_table()
        self._populate_menu()
        self.query_one("#settings-menu").focus()

    def _populate_config_table(self) -> None:
        """Populate the configuration table."""
        table = self.query_one("#config-table", DataTable)
        table.clear(columns=True)

        table.add_column("Setting", key="setting")
        table.add_column("Value", key="value")

        dirs = get_output_dirs()
        hw_info = get_hw_info()
        config = load_config()
        current_mode = config.get("setup_type", "cpu").upper()

        table.add_row("[cyan]Output Folder[/cyan]", dirs["base"])
        table.add_row("[cyan]Models Folder[/cyan]", MODELS_DIR)
        table.add_row("[cyan]Device[/cyan]", hw_info["device"])
        table.add_row("[cyan]Provider[/cyan]", hw_info["provider"])
        table.add_row("[cyan]Mode[/cyan]", f"[bold]{current_mode}[/bold]")

    def _populate_menu(self) -> None:
        """Build the menu with mode-aware switch option."""
        menu = self.query_one("#settings-menu", StyledOptionList)
        menu.clear_options()

        config = load_config()
        current_mode = config.get("setup_type", "cpu")
        gpu_name = check_nvidia_gpu()

        options = [
            create_menu_option("📂", "Open amv-script folder", "", "folder", "open_base"),
            create_menu_option("📂", "Open models folder", "", "folder", "open_models"),
            create_menu_option("🔍", "Check dependencies", "", "settings", "deps"),
            create_separator(),
        ]

        # Dynamic switch button based on current mode
        if current_mode == "cpu":
            if gpu_name:
                label = f"Switch to GPU ({gpu_name})"
            else:
                label = "Switch to GPU (RTX 50 series)"
            options.append(create_menu_option(
                "🚀", label,
                "Install CUDA 12.8 PyTorch + BS-Roformer",
                "settings", "switch_gpu"
            ))
        else:
            options.append(create_menu_option(
                "💻", "Switch to CPU",
                "Install CPU PyTorch + Kim Vocal 2 ONNX",
                "settings", "switch_cpu"
            ))

        options.append(create_separator())
        options.append(create_menu_option("⬅️", "Back to Main Menu", "", "back", "back"))

        menu.add_options(options)

    def on_option_list_option_selected(self, event) -> None:
        """Handle menu selection."""
        option_id = event.option_id

        if option_id == "open_base":
            dirs = ensure_output_dirs()
            self._open_folder(dirs["base"])
        elif option_id == "open_models":
            if os.path.exists(MODELS_DIR):
                self._open_folder(MODELS_DIR)
        elif option_id == "deps":
            self.app.push_screen("setup")
        elif option_id == "switch_gpu":
            from amv.screens.setup import SetupScreen
            self.app.push_screen(SetupScreen(target_mode="gpu"))
        elif option_id == "switch_cpu":
            from amv.screens.setup import SetupScreen
            self.app.push_screen(SetupScreen(target_mode="cpu"))
        elif option_id == "back":
            self.action_go_back()

    def _open_folder(self, path: str) -> None:
        """Open folder in file explorer."""
        if os.name == 'nt':
            os.startfile(path)
        else:
            subprocess.run(['xdg-open', path])

    def action_go_back(self) -> None:
        """Go back to main menu."""
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

    #config-table {
        margin: 1 4;
        height: auto;
        max-height: 12;
    }
    """

# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Settings Screen
# Configuration and folder access
# ═══════════════════════════════════════════════════════════════════════════════

import os
import subprocess
from textual.app import ComposeResult
from textual.widgets import Footer, Static, DataTable
from textual.containers import Vertical, Center

from textual.screen import Screen
from amv.widgets.menu import StyledOptionList, create_menu_option, create_separator
from amv.config import MODELS_DIR, get_output_dirs, ensure_output_dirs
from amv.hardware import get_hw_info


class SettingsScreen(Screen):
    """Settings screen with configuration display and folder access."""
    
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
            
            # Options menu
            with Center():
                yield StyledOptionList(
                    create_menu_option("📂", "Open amv-script folder", "", "folder", "open_base"),
                    create_menu_option("📂", "Open models folder", "", "folder", "open_models"),
                    create_menu_option("🔍", "Check dependencies", "", "settings", "deps"),
                    create_separator(),
                    create_menu_option("⬅️", "Back to Main Menu", "", "back", "back"),
                    id="settings-menu"
                )
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize settings display."""
        self._populate_config_table()
        self.query_one("#settings-menu").focus()
    
    def _populate_config_table(self) -> None:
        """Populate the configuration table."""
        table = self.query_one("#config-table", DataTable)
        table.clear(columns=True)
        
        table.add_column("Setting", key="setting")
        table.add_column("Value", key="value")
        
        dirs = get_output_dirs()
        hw_info = get_hw_info()
        
        table.add_row("[cyan]Output Folder[/cyan]", dirs["base"])
        table.add_row("[cyan]Models Folder[/cyan]", MODELS_DIR)
        table.add_row("[cyan]Device[/cyan]", hw_info["device"])
        table.add_row("[cyan]Provider[/cyan]", hw_info["provider"])
    
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
        max-height: 10;
    }
    """

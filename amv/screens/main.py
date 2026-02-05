# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Main Screen
# Home menu with navigation to all features
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Static
from textual.containers import Vertical, Center

from amv.widgets.banner import Banner
from amv.widgets.menu import StyledOptionList, create_menu_option, create_separator


class MainScreen(Screen):
    """Main menu screen with navigation options."""
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
    ]
    
    def compose(self) -> ComposeResult:
        # Get the working directory
        original_dir = os.environ.get('AMV_ORIGINAL_DIR', os.getcwd())
        
        with Vertical():
            yield Banner()
            yield Static(f"[dim]📁 {original_dir}[/dim]", id="cwd-display")
            
            with Center():
                yield StyledOptionList(
                    create_menu_option("📺", "Download from YouTube", "Video or Audio", "video", "youtube"),
                    create_menu_option("🎚️", "Extract Vocals", "AI separation", "audio", "vocals"),
                    create_menu_option("🔄", "Convert to WAV", "Extract audio from any file", "convert", "convert"),
                    create_separator(),
                    create_menu_option("🔧", "System Check", "Verify installation", "settings", "setup"),
                    create_menu_option("⚙️", "Settings", "", "settings", "settings"),
                    create_menu_option("🚪", "Exit", "", "back", "exit"),
                    id="main-menu"
                )
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Focus the menu on mount."""
        self.query_one("#main-menu").focus()
    
    def on_option_list_option_selected(self, event) -> None:
        """Handle menu selection."""
        option_id = event.option_id
        
        if option_id == "youtube":
            self.app.push_screen("youtube")
        elif option_id == "vocals":
            self.app.push_screen("vocals")
        elif option_id == "convert":
            self.app.push_screen("convert")
        elif option_id == "setup":
            self.app.push_screen("setup")
        elif option_id == "settings":
            self.app.push_screen("settings")
        elif option_id == "exit":
            self.app.exit()
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

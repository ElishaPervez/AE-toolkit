# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Textual Application
# Main app with screen-based navigation and mouse support
# ═══════════════════════════════════════════════════════════════════════════════

import os
from pathlib import Path
from textual.app import App
from textual.binding import Binding

from amv.screens.main import MainScreen
from amv.screens.youtube import YouTubeScreen
from amv.screens.vocals import VocalsScreen
from amv.screens.convert import ConvertScreen
from amv.screens.settings import SettingsScreen
from amv.screens.setup import SetupScreen


class AMVApp(App):
    """AMV Toolkit - A Textual TUI application with mouse support."""
    
    TITLE = "AMV Toolkit"
    SUB_TITLE = "Audio & Media Video Toolkit"
    
    # Load the CSS theme
    CSS_PATH = Path(__file__).parent / "styles" / "theme.tcss"
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "go_back", "Back", show=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]
    
    SCREENS = {
        "main": MainScreen,
        "youtube": YouTubeScreen,
        "vocals": VocalsScreen,
        "convert": ConvertScreen,
        "settings": SettingsScreen,
        "setup": SetupScreen,
    }
    
    ENABLE_COMMAND_PALETTE = False  # Keep it simple
    
    def on_mount(self) -> None:
        """Push the main screen on app start."""
        self.push_screen("main")
    
    def action_go_back(self) -> None:
        """Handle back navigation."""
        if len(self.screen_stack) > 1:
            self.pop_screen()
        else:
            self.exit()
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()


def run():
    """Entry point for running the AMV app."""
    # Store original directory for file operations
    os.environ['AMV_ORIGINAL_DIR'] = os.getcwd()
    
    app = AMVApp()
    app.run()


if __name__ == "__main__":
    run()

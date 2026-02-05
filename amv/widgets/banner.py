# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Banner Widget
# Animated ASCII banner with gradient colors
# ═══════════════════════════════════════════════════════════════════════════════

from textual.widget import Widget
from textual.app import ComposeResult
from textual.widgets import Static
from rich.text import Text
from rich.style import Style

LOGO = r"""
  /$$$$$$  /$$      /$$ /$$    /$$
 /$$__  $$| $$$    /$$$| $$   | $$
| $$  \ $$| $$$$  /$$$$| $$   | $$
| $$$$$$$$| $$ $$/$$ $$|  $$ / $$/
| $$__  $$| $$  $$$| $$ \  $$ $$/ 
| $$  | $$| $$\  $ | $$  \  $$$/  
| $$  | $$| $$ \/  | $$   \  $/   
|__/  |__/|__/     |__/    \_/    
"""

TAGLINE = "Audio & Media Video Toolkit"

# Gradient colors for the banner (8 lines)
GRADIENT_COLORS = ["#00ffff", "#00eeff", "#00ddff", "#00ccff", "#00bbff", "#00aaff", "#0099ff", "#0088ff"]


class Banner(Widget):
    """Animated ASCII banner widget with gradient text."""
    
    DEFAULT_CSS = """
    Banner {
        height: auto;
        width: 100%;
        content-align: center middle;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Static(self._create_gradient_logo(), id="banner")
        yield Static(f"[bold dim]{TAGLINE}[/bold dim]", id="tagline")
    
    def _create_gradient_logo(self) -> Text:
        """Create gradient-colored logo text."""
        text = Text()
        # Split first, then filter empty lines (preserves internal whitespace)
        lines = [line for line in LOGO.split('\n') if line.strip()]
        for i, line in enumerate(lines):
            color = GRADIENT_COLORS[i % len(GRADIENT_COLORS)]
            text.append(line + '\n', style=Style(color=color, bold=True))
        return text

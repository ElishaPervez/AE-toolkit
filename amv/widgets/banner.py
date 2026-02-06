# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Banner Widget
# Animated ASCII banner with gradient colors
# ═══════════════════════════════════════════════════════════════════════════════

from textual.widget import Widget
from textual.app import ComposeResult
from textual.widgets import Static
from rich.text import Text
from rich.style import Style

LOGO = """\
   █████████   ██████   ██████ █████   █████
  ███▒▒▒▒▒███ ▒▒██████ ██████ ▒▒███   ▒▒███
 ▒███    ▒███  ▒███▒█████▒███  ▒███    ▒███
 ▒███████████  ▒███▒▒███ ▒███  ▒███    ▒███
 ▒███▒▒▒▒▒███  ▒███ ▒▒▒  ▒███  ▒▒███   ███
 ▒███    ▒███  ▒███      ▒███   ▒▒▒█████▒
 █████   █████ █████     █████    ▒▒███
▒▒▒▒▒   ▒▒▒▒▒ ▒▒▒▒▒     ▒▒▒▒▒      ▒▒▒
"""

TAGLINE = "Audio & Media Video Toolkit"

# Gradient colors for the banner (cyan → purple)
GRADIENT_COLORS = [
    "#00ffff",
    "#00ddff",
    "#00bbff",
    "#2299ff",
    "#4477ff",
    "#6655ff",
    "#8844ee",
    "#aa33dd",
]


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
    
    def _dim_color(self, hex_color: str) -> str:
        """Darken a hex color for shadow/border effect."""
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        factor = 0.35
        return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"

    def _create_gradient_logo(self) -> Text:
        """Create gradient-colored logo with block characters."""
        text = Text()
        lines = [line for line in LOGO.split('\n') if '█' in line or '▒' in line]
        max_len = max(len(line) for line in lines)
        lines = [line.ljust(max_len) for line in lines]
        for i, line in enumerate(lines):
            color = GRADIENT_COLORS[i % len(GRADIENT_COLORS)]
            for char in line:
                if char == '█':
                    text.append(' ', style=Style(bgcolor=color))
                elif char == '▒':
                    text.append(' ', style=Style(bgcolor=self._dim_color(color)))
                else:
                    text.append(' ')
            text.append('\n')
        return text

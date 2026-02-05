# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Menu Widget
# Color-coded option list with category styling
# ═══════════════════════════════════════════════════════════════════════════════

from textual.widgets import OptionList
from textual.widgets.option_list import Option
from rich.text import Text


# Category color schemes
CATEGORY_COLORS = {
    "audio": "#bd93f9",     # Purple/Magenta for audio
    "video": "#00d4ff",     # Cyan for video
    "convert": "#50fa7b",   # Green for convert/transform
    "folder": "#ffb86c",    # Orange for folder actions
    "settings": "#6272a4",  # Gray for settings
    "back": "#585b65",      # Dim for back/exit
    "action": "#50fa7b",    # Green for primary actions
}


def create_menu_option(
    icon: str,
    label: str,
    description: str = "",
    category: str = "action",
    value: str = None
) -> Option:
    """
    Create a styled menu option with icon and optional description.
    
    Args:
        icon: Emoji or symbol
        label: Main text
        description: Secondary text (shown dimmed)
        category: Color category (audio, video, folder, settings, back, action)
        value: Return value when selected (defaults to label)
    """
    color = CATEGORY_COLORS.get(category, CATEGORY_COLORS["action"])
    
    text = Text()
    text.append(f"{icon}  ", style=f"bold {color}")
    text.append(label, style=f"bold {color}")
    
    if description:
        text.append(f"  {description}", style="dim")
    
    return Option(text, id=value or label.lower().replace(" ", "_"))


def create_separator():
    """Create a visual separator for menu sections."""
    return None  # OptionList treats None as a separator


class StyledOptionList(OptionList):
    """An OptionList with enhanced styling and mouse support."""
    
    DEFAULT_CSS = """
    StyledOptionList {
        background: transparent;
        border: round #0080ff;
        padding: 1 2;
        margin: 1 4;
        height: auto;
        max-height: 14;
    }

    StyledOptionList:focus {
        border: round #00d4ff;
    }

    /* Keyboard highlight (shows when mouse is not hovering) */
    StyledOptionList > .option-list--option-highlighted {
        background: #0080ff;
        text-style: bold;
    }

    /* When mouse is in the widget, hide the keyboard highlight */
    StyledOptionList:hover > .option-list--option-highlighted {
        background: transparent;
    }

    /* Mouse hover - same bright style, takes over from keyboard */
    StyledOptionList > .option-list--option-hover {
        background: #0080ff;
        text-style: bold;
    }
    """

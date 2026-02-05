# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Progress Widget
# Enhanced progress indicators with stage support
# ═══════════════════════════════════════════════════════════════════════════════

from textual.widget import Widget
from textual.app import ComposeResult
from textual.widgets import Static, ProgressBar, Label
from textual.containers import Vertical, Horizontal


class StageProgress(Widget):
    """Progress widget with stage indicators."""
    
    DEFAULT_CSS = """
    StageProgress {
        height: auto;
        padding: 1 2;
        margin: 1 4;
        border: round #0080ff;
    }
    
    StageProgress .stage-label {
        text-align: center;
        padding: 0 2;
        color: #00d4ff;
        text-style: bold;
    }
    
    StageProgress .stage-status {
        text-align: center;
        color: #6272a4;
        padding-bottom: 1;
    }
    """
    
    def __init__(
        self,
        stages: list[str] = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None
    ):
        super().__init__(name=name, id=id, classes=classes)
        self.stages = stages or ["Processing..."]
        self.current_stage = 0
        self.progress_value = 0.0
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.stages[0], id="stage-label", classes="stage-label")
            yield Label("", id="stage-status", classes="stage-status")
            yield ProgressBar(id="progress-bar", show_eta=False)
    
    def set_stage(self, index: int, status: str = "") -> None:
        """Update the current stage."""
        self.current_stage = min(index, len(self.stages) - 1)
        self.query_one("#stage-label", Label).update(self.stages[self.current_stage])
        self.query_one("#stage-status", Label).update(status)
    
    def set_progress(self, value: float, total: float = 100.0) -> None:
        """Update progress bar (0.0 to 1.0 or percentage)."""
        if total != 100.0:
            value = (value / total) * 100
        self.progress_value = min(max(value, 0), 100)
        self.query_one("#progress-bar", ProgressBar).update(progress=self.progress_value)
    
    def set_indeterminate(self, message: str = "Processing...") -> None:
        """Set to indeterminate (spinning) mode."""
        self.query_one("#stage-label", Label).update(message)
        bar = self.query_one("#progress-bar", ProgressBar)
        bar.update(total=None)  # Indeterminate mode


class StatusPanel(Widget):
    """A status panel for displaying results/errors."""
    
    DEFAULT_CSS = """
    StatusPanel {
        height: auto;
        padding: 1 2;
        margin: 1 4;
        border: round #50fa7b;
    }
    
    StatusPanel.error {
        border: round #ff5555;
    }
    
    StatusPanel .panel-title {
        text-style: bold;
        color: #50fa7b;
        text-align: center;
        padding-bottom: 1;
    }
    
    StatusPanel.error .panel-title {
        color: #ff5555;
    }
    
    StatusPanel .panel-content {
        color: #f8f8f2;
    }
    """
    
    def __init__(
        self,
        title: str = "Status",
        content: str = "",
        is_error: bool = False,
        name: str | None = None,
        id: str | None = None,
    ):
        super().__init__(name=name, id=id, classes="error" if is_error else "")
        self.title_text = title
        self.content_text = content
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.title_text, classes="panel-title")
            yield Static(self.content_text, classes="panel-content")
    
    def update_content(self, title: str = None, content: str = None, is_error: bool = None) -> None:
        """Update panel content."""
        if title:
            self.query_one(".panel-title", Label).update(title)
        if content:
            self.query_one(".panel-content", Static).update(content)
        if is_error is not None:
            if is_error:
                self.add_class("error")
            else:
                self.remove_class("error")

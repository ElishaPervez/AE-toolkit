# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Completion Notifications
# ═══════════════════════════════════════════════════════════════════════════════

import sys


def notify_complete(app):
    """Send completion notification - terminal bell + taskbar flash on Windows."""
    app.bell()

    if sys.platform == "win32":
        try:
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.FlashWindow(hwnd, True)
        except Exception:
            pass

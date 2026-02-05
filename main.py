#!/usr/bin/env python3
"""
AMV Toolkit - Audio & Media Video Toolkit

A unified TUI for YouTube downloading and AI-powered audio separation.
Now with mouse support powered by Textual!

Usage:
  python main.py              Launch interactive TUI
  python main.py --dev        Launch in development mode (hot reload)
"""

import sys
import os
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="AMV Toolkit - Audio & Media Video Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  amv              Launch interactive TUI
  amv --dev        Launch in development mode
        """
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Run in development mode with hot reloading"
    )
    args = parser.parse_args()
    
    # Ensure UTF-8 encoding on Windows
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    
    # Store original directory for file operations
    # (amv.bat already sets this before pushd; only set if not already present)
    if 'AMV_ORIGINAL_DIR' not in os.environ:
        os.environ['AMV_ORIGINAL_DIR'] = os.getcwd()
    
    if args.dev:
        # Run with textual dev mode for hot reloading
        import subprocess
        subprocess.run([sys.executable, "-m", "textual", "run", "--dev", "amv.app:AMVApp"])
    else:
        # Normal run
        from amv.app import AMVApp
        app = AMVApp()
        app.run()


if __name__ == "__main__":
    main()

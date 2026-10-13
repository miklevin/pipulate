#!/usr/bin/env python3
"""
🪧 card.py -- Station-break Figlet title card.

Renders a large Figlet banner centered on a transient Alacritty overlay.
"""

import sys
import time

try:
    from pyfiglet import Figlet
except Exception:
    Figlet = None

try:
    from rich.console import Console
    from rich.align import Align
    from rich.text import Text
    _console = Console()
except Exception:
    _console = None


def render(label: str):
    """Render the label as a Figlet banner, centered if Rich is available."""
    label = label.replace("\\n", "\n")
    banner = label
    if Figlet is not None:
        try:
            banner = Figlet(font="standard").renderText(label)
        except Exception:
            banner = label

    if _console is not None:
        try:
            _console.clear()
            _console.print(Align.center(Text(banner), vertical="middle"))
            return
        except Exception:
            pass

    print(banner)


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "Station"

    hold = 900.0
    if len(sys.argv) > 2:
        try:
            hold = float(sys.argv[2])
        except ValueError:
            hold = 900.0

    render(label)
    time.sleep(hold)


if __name__ == "__main__":
    main()

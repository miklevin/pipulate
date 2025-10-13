# /home/mike/repos/pipulate/pipulate/__init__.py

import os
import sys
from pathlib import Path
from .core import Pipulate
from loguru import logger

# --- SETUP PATHS FIRST ---

def find_project_root(start_path):
    """Walks up from a starting path to find the project root (marked by 'flake.nix')."""
    current_path = Path(start_path).resolve()
    while current_path != current_path.parent:
        if (current_path / 'flake.nix').exists():
            return current_path
        current_path = current_path.parent
    return None

# Establish the absolute project root path.
project_root = find_project_root(os.getcwd()) or Path.cwd()

# --- CONFIGURE LOGGING USING ABSOLUTE PATHS ---

logger.remove()

# Console handler for notebooks (shows only warnings and above).
logger.add(
    sys.stderr,
    level="WARNING",
    colorize=True,
    format="<level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
)

# File logger that captures everything for debugging.
log_dir = project_root / "Notebooks" / "logs"
log_dir.mkdir(parents=True, exist_ok=True) # Use parents=True for robustness
logger.add(
    log_dir / "notebook_run.log",
    level="DEBUG",
    rotation="10 MB",
    format="{time} {level} {message}"
)

# --- INITIALIZE PIPULATE SINGLETON ---

# Define the explicit, user-facing database path using the absolute project root.
DB_PATH = project_root / "Notebooks" / "pipeline.sqlite"

# Create the singleton instance that gets imported by `from pipulate import pip`.
pip = Pipulate(db_path=str(DB_PATH))
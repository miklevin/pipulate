# /home/mike/repos/pipulate/pipulate/__init__.py

import os
import sys
from pathlib import Path
from loguru import logger
import warnings

# --- GLOBAL ENVIRONMENT SETUP ---
# Suppress common UserWarnings from third-party libraries like selenium-wire.
# This is the "deepest" place to put it so users never see it.
warnings.filterwarnings("ignore", category=UserWarning)
# -----------------------------

from .core import Pipulate

# --- NOTEBOOK-SPECIFIC LOGGING CONFIGURATION ---
logger.remove()
logger.add(
    sys.stderr,
    level="WARNING",
    colorize=True,
    format="<level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
)
log_dir = Path("Notebooks/logs")
log_dir.mkdir(parents=True, exist_ok=True)
logger.add(
    log_dir / "notebook_run.log",
    level="DEBUG",
    rotation="10 MB",
    format="{time} {level} {message}"
)
# --- END LOGGING CONFIGURATION ---

def find_project_root(start_path):
    """Walks up from a starting path to find the project root (marked by 'flake.nix')."""
    current_path = Path(start_path).resolve()
    while current_path != current_path.parent:
        if (current_path / 'flake.nix').exists():
            return current_path
        current_path = current_path.parent
    return None

project_root = find_project_root(os.getcwd()) or Path.cwd()
DB_PATH = project_root / "Notebooks" / "pipeline.sqlite"

# Create the singleton instance that gets imported by `from pipulate import pip`.
pip = Pipulate(db_path=str(DB_PATH))
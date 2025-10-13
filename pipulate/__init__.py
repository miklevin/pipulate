# /home/mike/repos/pipulate/pipulate/__init__.py

import os
from pathlib import Path
from .core import Pipulate

# Determine the project root by looking for a known file, like 'flake.nix'
def find_project_root(start_path):
    current_path = Path(start_path).resolve()
    while current_path != current_path.parent:
        if (current_path / 'flake.nix').exists():
            return current_path
        current_path = current_path.parent
    return None

# Default to the current working directory if root isn't found
project_root = find_project_root(os.getcwd()) or Path.cwd()

# Define the explicit, user-facing database path
DB_PATH = project_root / "Notebooks" / "pipeline.sqlite"

# Create the singleton instance of the Pipulate class
# This `pip` object is what gets imported by `from pipulate import pip`
pip = Pipulate(db_path=str(DB_PATH))
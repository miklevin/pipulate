# START: pipulate_factory_content
import os
import sys
from pathlib import Path
from loguru import logger
from .core import Pipulate

# 🎯 NOTEBOOK LOGGING: Configure logger for a cleaner Jupyter experience.
logger.remove()
logger.add(sys.stderr, level="WARNING")

def _find_project_root(start_path):
    """Find the project root by looking for the flake.nix file."""
    current_path = Path(start_path).resolve()
    while current_path != current_path.parent:
        if (current_path / 'flake.nix').exists():
            return current_path
        current_path = current_path.parent
    return None

def _get_db_path():
    """Get the path to the project's development database."""
    project_root = _find_project_root(os.getcwd())

    if project_root:
        app_name_file = project_root / 'whitelabel.txt'
        if app_name_file.exists():
            app_name = app_name_file.read_text().strip().lower()
        else:
            # Fallback to directory name if whitelabel.txt doesn't exist
            app_name = project_root.name.lower()
        return project_root / f'data/{app_name}_dev.db'

    # Fallback to a local db file if not in a pipulate project
    return Path(os.getcwd()) / 'pipulate_notebook.db'

# The "factory" instantiation. This code runs when this module is imported.
# It creates a single, pre-configured instance of the Pipulate class.
db_path = _get_db_path()

# This is the magic `pip` object for notebooks.
pip = Pipulate(db_path=str(db_path))
# END: pipulate_factory_content
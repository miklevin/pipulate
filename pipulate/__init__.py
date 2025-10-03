# %%
# Replace the contents of pipulate/__init__.py with this

import os
import sys
from pathlib import Path
from .core import Pipulate, DictLikeDB
from loguru import logger

# --- START: Version Information (DO NOT REMOVE) ---
# This is the single source of truth for the package version
__version__ = "1.2.1"
__version_description__ = "JupyterLab Integration"
# --- END: Version Information ---

# 🎯 NOTEBOOK LOGGING: Configure logger for a cleaner Jupyter experience.
# This removes the default verbose handler and adds one that only shows warnings and errors.
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
            app_name = 'pipulate' # fallback
        return project_root / f'data/{app_name}_dev.db'

    # Fallback to a local db file if not in a pipulate project
    return Path(os.getcwd()) / 'pipulate_notebook.db'

# The "factory" instantiation. This code runs when `import pipulate` is executed.
db_path = _get_db_path()
pip = Pipulate(db_path=str(db_path))

# This allows `from pipulate import Pipulate` and makes the `pip` object available.
# It also exposes the version info for the build/release process.
__all__ = ['Pipulate', 'pip', '__version__', '__version_description__']

# 🎯 CRITICAL: This line makes `import pipulate as pip` work as expected by
# exposing the `pip` object directly on the module.
sys.modules[__name__] = pip

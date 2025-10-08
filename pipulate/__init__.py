# START: main_init_content
import os
import sys
from pathlib import Path
from .core import Pipulate
from .pipulate import pip

# --- START: Version Information (DO NOT REMOVE) ---
__version__ = "1.4.2"
__version_description__ = "Local First AI SEO Software"
# --- END: Version Information ---

# This allows `from pipulate import Pipulate` and makes the `pip` object (from pipulate.py) available.
__all__ = ['Pipulate', 'pip', '__version__', '__version_description__']
# END: main_init_content

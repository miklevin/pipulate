# patch.py
# This file contains the deterministic patch instructions for the "serverectomy" refactor.
# It will be executed by the ai_edit.py script to safely modify the Pipulate codebase.

import json

patches = [
    {
        "file": "pipulate/core.py",
        "block_name": "pipulate_init",
        "new_code": """
    def __init__(self, pipeline_table=None, db=None, friendly_names=None, append_func=None, get_profile_id_func=None, get_profile_name_func=None, model=None, chat_instance=None, db_path=None):
        self.chat = chat_instance
        self.friendly_names = friendly_names
        self.append_to_conversation = append_func
        self.get_current_profile_id = get_profile_id_func
        self.get_profile_name = get_profile_name_func
        self.model = model
        self.message_queue = self.OrderedMessageQueue()

        if db_path:
            # Standalone/Notebook Context: Create our "Parallel Universe" DB using fastlite directly
            from fastlite import Database
            from loguru import logger
            logger.info(f"Pipulate initializing in standalone mode with db: {db_path}")

            # 1. Create a database connection using fastlite.Database
            db_conn = Database(db_path)

            # 2. Access the table handles via the .t property
            l_store = db_conn.t.store
            l_pipeline = db_conn.t.pipeline
            # Note: We don't need to explicitly create tables; fastlite handles it.

            self.pipeline_table = l_pipeline
            # The second argument `Store` from fast_app isn't needed by DictLikeDB.
            self.db = DictLikeDB(l_store, None)

            # In standalone mode, some features that rely on the server are stubbed out
            if self.append_to_conversation is None: self.append_to_conversation = lambda msg, role: print(f"[{role}] {msg}")
            if self.get_current_profile_id is None: self.get_current_profile_id = lambda: 'standalone'
            if self.get_profile_name is None: self.get_profile_name = lambda: 'standalone'

        else:
            # Server Context: Use the objects passed in from server.py
            from loguru import logger
            logger.info("Pipulate initializing in server mode.")
            self.pipeline_table = pipeline_table
            self.db = db
        """
    },
    {
        "file": "pipulate/core.py",
        "block_name": "notebook_api_methods",
        "new_code": """
    def read(self, job: str) -> dict:
        \"\"\"Reads the entire state dictionary for a given job (pipeline_id).\"\"\"
        state = self.read_state(job)
        state.pop('created', None)
        state.pop('updated', None)
        return state

    def write(self, job: str, state: dict):
        \"\"\"Writes an entire state dictionary for a given job (pipeline_id).\"\"\"
        # Ensure 'created' timestamp is preserved if it exists
        existing_state = self.read_state(job)
        if 'created' in existing_state:
            state['created'] = existing_state['created']
        self.write_state(job, state)

    def set(self, job: str, step: str, value: any):
        \"\"\"Sets a key-value pair within a job's state.\"\"\"
        state = self.read_state(job)
        if not state:
            # If the job doesn't exist, initialize it
            now = self.get_timestamp()
            state = {'created': now}
            self.pipeline_table.insert({
                'pkey': job,
                'app_name': 'notebook',
                'data': json.dumps(state),
                'created': now,
                'updated': now
            })
        
        state[step] = value
        self.write_state(job, state)

    def get(self, job: str, step: str, default: any = None) -> any:
        \"\"\"Gets a value for a key within a job's state.\"\"\"
        state = self.read_state(job)
        return state.get(step, default)
        """
    },
    {
        "file": "pipulate/__init__.py",
        "block_name": "main_init_content",
        "new_code": """
import os
from pathlib import Path
from .core import Pipulate, DictLikeDB

# --- START: Version Information (DO NOT REMOVE) ---
# This is the single source of truth for the package version
__version__ = "1.2.1"
__version_description__ = "JupyterLab Integration"
# --- END: Version Information ---

def _find_project_root(start_path):
    \"\"\"Find the project root by looking for the flake.nix file.\"\"\"
    current_path = Path(start_path).resolve()
    while current_path != current_path.parent:
        if (current_path / 'flake.nix').exists():
            return current_path
        current_path = current_path.parent
    return None

def _get_db_path():
    \"\"\"Get the path to the project's development database.\"\"\"
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
        """
    }
]
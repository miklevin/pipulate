# /home/mike/repos/pipulate/ai_dictdb.py

import sqlite3
from pathlib import Path
from fasthtml.common import fast_app

# Get the directory of the current file (e.g., /path/to/pipulate/modules)
# and go one level up to find the project's root directory.
PROJECT_ROOT = Path(__file__).parent.parent

class AIKeychain:
    """
    A persistent, dictionary-like key-value store for the AI.

    This class provides a simple, Python dict-like interface to a dedicated
    SQLite database file (`data/ai_keychain.db`). It is designed to be
    a long-term memory store for the AI that persists across application
    resets and is not tracked by Git.
    
    This enables AI instances to leave "messages in a bottle" for future
    instances of themselves or other AIs that inhabit the same Pipulate body.
    
    Unlike the temporary application stores (db, pipeline), this ai_dictdb
    survives Pipulate resets and lives outside the normal application lifecycle.
    """
    
    def __init__(self, db_path=None):
        """Initializes the connection to the ai_dictdb database."""
        if db_path is None:
            # Construct an absolute path from the project root
            db_path = PROJECT_ROOT / 'data' / 'ai_keychain.db'
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use FastHTML's fast_app pattern to create the database properly
        # This ensures compatibility with the existing codebase
        try:
            _, _, (self.store, _) = fast_app(
                str(self.db_path),
                ai_dictdb={
                    'key': str,
                    'value': str,
                    'pk': 'key'
                }
            )
        except Exception as e:
            # Fallback to direct SQLite if fast_app approach fails
            import sqlite3
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_dictdb (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            self.conn.commit()
            self.store = None  # Will use direct SQL operations

    def __setitem__(self, key: str, value: str):
        """Saves or updates a key-value pair."""
        if self.store is not None:
            # Use FastHTML table object
            try:
                self.store.upsert({'key': key, 'value': value}, pk='key')
            except AttributeError:
                # Fallback: use insert with replace
                self.store.insert({'key': key, 'value': value}, replace=True)
        else:
            # Use direct SQLite
            self.conn.execute(
                "INSERT OR REPLACE INTO ai_dictdb (key, value) VALUES (?, ?)",
                (key, value)
            )
            self.conn.commit()

    def __getitem__(self, key: str) -> str:
        """Retrieves a value by its key."""
        if self.store is not None:
            # Use FastHTML table object
            try:
                result = self.store.get(key)
                if result is None:
                    raise KeyError(f"Key '{key}' not found in AI Keychain.")
                return result['value']
            except Exception:
                raise KeyError(f"Key '{key}' not found in AI Keychain.")
        else:
            # Use direct SQLite
            cursor = self.conn.execute("SELECT value FROM ai_dictdb WHERE key = ?", (key,))
            result = cursor.fetchone()
            if result is None:
                raise KeyError(f"Key '{key}' not found in AI Keychain.")
            return result[0]

    def __delitem__(self, key: str):
        """Deletes a key-value pair."""
        if key not in self:
            raise KeyError(f"Key '{key}' not found in AI Keychain.")
        
        if self.store is not None:
            # Use FastHTML table object
            self.store.delete(key)
        else:
            # Use direct SQLite
            self.conn.execute("DELETE FROM ai_dictdb WHERE key = ?", (key,))
            self.conn.commit()

    def __contains__(self, key: str) -> bool:
        """Checks if a key exists."""
        if self.store is not None:
            # Use FastHTML table object
            try:
                result = self.store.get(key)
                return result is not None
            except Exception:
                return False
        else:
            # Use direct SQLite
            cursor = self.conn.execute("SELECT 1 FROM ai_dictdb WHERE key = ?", (key,))
            return cursor.fetchone() is not None

    def keys(self) -> list[str]:
        """Returns a list of all keys."""
        if self.store is not None:
            # Use FastHTML table object
            return [row['key'] for row in self.store()]
        else:
            # Use direct SQLite
            cursor = self.conn.execute("SELECT key FROM ai_dictdb")
            return [row[0] for row in cursor.fetchall()]

    def values(self) -> list[str]:
        """Returns a list of all values."""
        if self.store is not None:
            # Use FastHTML table object
            return [row['value'] for row in self.store()]
        else:
            # Use direct SQLite
            cursor = self.conn.execute("SELECT value FROM ai_dictdb")
            return [row[0] for row in cursor.fetchall()]

    def items(self) -> list[tuple[str, str]]:
        """Returns a list of all (key, value) pairs."""
        if self.store is not None:
            # Use FastHTML table object
            return [(row['key'], row['value']) for row in self.store()]
        else:
            # Use direct SQLite
            cursor = self.conn.execute("SELECT key, value FROM ai_dictdb")
            return cursor.fetchall()

    def get(self, key: str, default=None):
        """Retrieves a key with a default value if not found."""
        try:
            return self[key]
        except KeyError:
            return default
    
    def set(self, key: str, value: str):
        """Alternative method to set a key-value pair."""
        self[key] = value
    
    def clear(self):
        """Removes all key-value pairs from the ai_dictdb."""
        # Get all keys and delete them
        all_keys = self.keys()
        for key in all_keys:
            self.store.delete(key)
    
    def count(self) -> int:
        """Returns the number of key-value pairs in the ai_dictdb."""
        if self.store is not None:
            # Use FastHTML table object
            return len(self.keys())
        else:
            # Use direct SQLite
            cursor = self.conn.execute("SELECT COUNT(*) FROM ai_dictdb")
            return cursor.fetchone()[0]
    
    def update(self, other):
        """Updates the ai_dictdb with key-value pairs from another dict-like object."""
        if hasattr(other, 'items'):
            for key, value in other.items():
                self[key] = value
        else:
            for key, value in other:
                self[key] = value
    
    def close(self):
        """Close the database connection if using direct SQLite."""
        if self.store is None and hasattr(self, 'conn'):
            self.conn.close()

    def get_keychain_summary_table(self) -> "Table":
        """Generate a Rich Table summarizing the AI Keychain contents."""
        from rich.table import Table
        table = Table(title="🔑 AI Keychain Memory", border_style="yellow", show_header=True, header_style="bold yellow")
        table.add_column("Key", style="cyan", max_width=50)
        table.add_column("Value", style="magenta")
        try:
            items = list(self.items())
            if not items:
                table.add_row("[No keys found]", "")
                return table
            for key, value in items:
                display_value = (value[:75] + '...') if len(value) > 75 else value
                table.add_row(key, display_value)
        except Exception as e:
            table.add_row("Error", f"Could not read keychain: {e}")
        return table

# Create a single, reusable instance for the application
keychain_instance = AIKeychain()
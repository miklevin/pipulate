# /home/mike/repos/pipulate/keychain.py

import sqlite3
from pathlib import Path
from fasthtml.common import fast_app

class AIKeychain:
    """
    A persistent, dictionary-like key-value store for the AI.

    This class provides a simple, Python dict-like interface to a dedicated
    SQLite database file (`data/ai_keychain.db`). It is designed to be
    a long-term memory store for the AI that persists across application
    resets and is not tracked by Git.
    
    This enables AI instances to leave "messages in a bottle" for future
    instances of themselves or other AIs that inhabit the same Pipulate body.
    
    Unlike the temporary application stores (db, pipeline), this keychain
    survives Pipulate resets and lives outside the normal application lifecycle.
    """
    
    def __init__(self, db_path='data/ai_keychain.db'):
        """Initializes the connection to the keychain database."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use FastHTML's fast_app pattern to create the database properly
        # This ensures compatibility with the existing codebase
        try:
            _, _, (self.store, _) = fast_app(
                str(self.db_path),
                keychain={
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
                CREATE TABLE IF NOT EXISTS keychain (
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
                "INSERT OR REPLACE INTO keychain (key, value) VALUES (?, ?)",
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
            cursor = self.conn.execute("SELECT value FROM keychain WHERE key = ?", (key,))
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
            self.conn.execute("DELETE FROM keychain WHERE key = ?", (key,))
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
            cursor = self.conn.execute("SELECT 1 FROM keychain WHERE key = ?", (key,))
            return cursor.fetchone() is not None

    def keys(self) -> list[str]:
        """Returns a list of all keys."""
        if self.store is not None:
            # Use FastHTML table object
            return [row['key'] for row in self.store()]
        else:
            # Use direct SQLite
            cursor = self.conn.execute("SELECT key FROM keychain")
            return [row[0] for row in cursor.fetchall()]

    def values(self) -> list[str]:
        """Returns a list of all values."""
        if self.store is not None:
            # Use FastHTML table object
            return [row['value'] for row in self.store()]
        else:
            # Use direct SQLite
            cursor = self.conn.execute("SELECT value FROM keychain")
            return [row[0] for row in cursor.fetchall()]

    def items(self) -> list[tuple[str, str]]:
        """Returns a list of all (key, value) pairs."""
        if self.store is not None:
            # Use FastHTML table object
            return [(row['key'], row['value']) for row in self.store()]
        else:
            # Use direct SQLite
            cursor = self.conn.execute("SELECT key, value FROM keychain")
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
        """Removes all key-value pairs from the keychain."""
        # Get all keys and delete them
        all_keys = self.keys()
        for key in all_keys:
            self.store.delete(key)
    
    def count(self) -> int:
        """Returns the number of key-value pairs in the keychain."""
        if self.store is not None:
            # Use FastHTML table object
            return len(self.keys())
        else:
            # Use direct SQLite
            cursor = self.conn.execute("SELECT COUNT(*) FROM keychain")
            return cursor.fetchone()[0]
    
    def update(self, other):
        """Updates the keychain with key-value pairs from another dict-like object."""
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

# Create a single, reusable instance for the application
keychain_instance = AIKeychain() 
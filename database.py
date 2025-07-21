#!/usr/bin/env python3
"""
database.py - Extracted from server.py
Generated on 2025-07-04 21:26:18

⚡ CRITICAL ARCHITECTURE: DUAL-DATABASE SYSTEM
═══════════════════════════════════════════════════════════════════════════════════
PIPULATE USES DUAL DATABASES - SILENT FAILURE PREVENTION REQUIRED:

🗃️ Main App Database: data/pipulate_dev.db (FastLite/primary workflows)
🗃️ Conversation Database: data/discussion.db (append-only conversation system)

🚨 DANGER: Concurrent SQLite connections between these databases can cause:
   • Database locking conflicts
   • Silent failures in profile creation
   • UI success with no actual data persistence

🛡️ PROTECTION: Use single database connections, avoid concurrent access patterns
"""

import sqlite3
import functools
from typing import Any, Dict, Optional
from loguru import logger

# Import the actual NotFoundError from apswutils
try:
    from apswutils.db import NotFoundError
except ImportError:
    # Fallback for development/testing
    class NotFoundError(Exception):
        pass

# Temporary imports and stubs to avoid circular imports
APP_NAME = "Botifython"
COLOR_MAP = {'key': 'cyan', 'value': 'green'}

# Stub for log to avoid circular import
class LogStub:
    def data(self, msg, data=None): logger.info(f"{msg}: {data}")
    def debug(self, category, msg, details=None): logger.debug(f"{category}: {msg} - {details}")
    def error(self, msg, error=None): logger.error(f"{msg}: {error}")
    def warning(self, msg): logger.warning(msg)

log = LogStub()

# Stub for get_current_environment
def get_current_environment():
    return "Development"

# Extracted block: function_get_db_filename_0484
def get_db_filename():
    current_env = get_current_environment()
    if current_env == 'Development':
        return f'data/{APP_NAME.lower()}_dev.db'
    else:
        return f'data/{APP_NAME.lower()}.db'

# Extracted block: function_db_operation_3798
def db_operation(func):

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            if func.__name__ == '__setitem__':
                key, value = (args[1], args[2])
                if not key.startswith('_') and (not key.endswith('_temp')):
                    if key in ('last_app_choice', 'last_profile_id', 'last_visited_url', 'pipeline_id'):
                        log.data(f'State updated: {key}', value)
                    else:
                        log.debug('database', f'DB {func.__name__}: {key}', f'value: {str(value)[:30]}...' if len(str(value)) > 30 else f'value: {value}')
            return result
        except Exception as e:
            # Don't log KeyError as ERROR for __getitem__ - it's expected behavior
            if func.__name__ == '__getitem__' and isinstance(e, KeyError):
                logger.debug(f'Key not found in database: {e}')
            else:
                log.error(f'Database operation {func.__name__} failed', e)
            raise
    return wrapper

# Extracted block: class_dictlikedb_3821
class DictLikeDB:

    def __init__(self, store, Store):
        self.store = store
        self.Store = Store
        logger.debug('DictLikeDB initialized.')

    @db_operation
    def __getitem__(self, key):
        try:
            value = self.store[key].value
            logger.debug(f'Retrieved from DB: {key} = {value}')
            return value
        except NotFoundError:
            # Don't log as error - this is expected behavior when checking for keys
            logger.debug(f'Key not found: {key}')
            raise KeyError(key)

    @db_operation
    def __setitem__(self, key, value):
        try:
            self.store.update({'key': key, 'value': value})
            logger.debug(f'Updated persistence store: {key} = {value}')
        except NotFoundError:
            self.store.insert({'key': key, 'value': value})
            logger.debug(f'Inserted new item in persistence store: {key} = {value}')

    @db_operation
    def __delitem__(self, key):
        try:
            self.store.delete(key)
            if key != 'temp_message':
                logger.warning(f'Deleted key from persistence store: {key}')
        except NotFoundError:
            logger.error(f'Attempted to delete non-existent key: {key}')
            raise KeyError(key)

    @db_operation
    def __contains__(self, key):
        exists = key in self.store
        logger.debug(f"Key '<{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}>' exists: <{COLOR_MAP['value']}>{exists}</{COLOR_MAP['value']}>")
        return exists

    @db_operation
    def __iter__(self):
        for item in self.store():
            yield item.key

    @db_operation
    def items(self):
        for item in self.store():
            yield (item.key, item.value)

    @db_operation
    def keys(self):
        return list(self)

    @db_operation
    def values(self):
        for item in self.store():
            yield item.value

    @db_operation
    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            logger.debug(f"Key '<{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}>' not found. Returning default: <{COLOR_MAP['value']}>{default}</{COLOR_MAP['value']}>")
            return default

    @db_operation
    def set(self, key, value):
        self[key] = value
        return value


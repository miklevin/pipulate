import ast
import asyncio
import functools
import importlib
import inspect
import json
import os
import re
import sqlite3
import sys
import time
import traceback
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional
import aiohttp
import uvicorn
from fasthtml.common import *
from loguru import logger
from pyfiglet import Figlet
from rich.console import Console
from rich.json import JSON
from rich.style import Style as RichStyle
from rich.table import Table, Text
from rich.theme import Theme
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route
from starlette.websockets import WebSocket, WebSocketDisconnect
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import subprocess
import platform
import urllib.parse
from starlette.responses import FileResponse
DEBUG_MODE = False
STATE_TABLES = False
TABLE_LIFECYCLE_LOGGING = False
API_LOG_ROTATION_COUNT = 20
shared_app_state = {'critical_operation_in_progress': False}

class GracefulRestartException(SystemExit):
    """Custom exception to signal a restart requested by Watchdog."""
    pass

def is_critical_operation_in_progress():
    """Check if a critical operation is in progress via file flag."""
    import os
    return os.path.exists('.critical_operation_lock')

def set_critical_operation_flag():
    """Set the critical operation flag via file."""
    import os
    with open('.critical_operation_lock', 'w') as f:
        f.write('critical operation in progress')

def clear_critical_operation_flag():
    """Clear the critical operation flag."""
    import os
    try:
        os.remove('.critical_operation_lock')
    except FileNotFoundError:
        pass

def get_app_name(force_app_name=None):
    """Get the name of the app from the app_name.txt file, or the parent directory name."""
    name = force_app_name
    if not name:
        app_name_file = 'app_name.txt'
        if Path(app_name_file).exists():
            try:
                name = Path(app_name_file).read_text().strip()
            except:
                pass
        if not name:
            name = Path(__file__).parent.name
            name = name[:-5] if name.endswith('-main') else name
    return name.capitalize()

def get_db_filename():
    current_env = get_current_environment()
    if current_env == 'Development':
        return f'data/{APP_NAME.lower()}_dev.db'
    else:
        return f'data/{APP_NAME.lower()}.db'

def get_current_environment():
    if ENV_FILE.exists():
        return ENV_FILE.read_text().strip()
    else:
        ENV_FILE.write_text('Development')
        return 'Development'
APP_NAME = get_app_name()
TONE = 'neutral'
MODEL = 'gemma3'
MAX_LLM_RESPONSE_WORDS = 80
MAX_CONVERSATION_LENGTH = 10000
HOME_MENU_ITEM = '👥 Roles (Home)'
DEFAULT_ACTIVE_ROLES = {'Botify Employee', 'Core'}

# ================================================================
# INSTANCE-SPECIFIC CONFIGURATION - "The Crucible"
# ================================================================
# This dictionary holds settings that customize this particular Pipulate instance.
# Moving configuration here allows for easy white-labeling and configuration management.
# Over time, more instance-specific "slag" will be skimmed from plugins to here.

PIPULATE_CONFIG = {
    # UI & Navigation
    'HOME_MENU_ITEM': HOME_MENU_ITEM,
    'DEFAULT_ACTIVE_ROLES': DEFAULT_ACTIVE_ROLES,
    
    # Role System Configuration
    'ROLES_CONFIG': {
        'Botify Employee': {
            'priority': 0, 
            'description': 'Connect with Botify to use Parameter Buster and Link Graph Visualizer.',
            'emoji': '👔'
        },
        'Core': {
            'priority': 1, 
            'description': 'Essential plugins available to all users.',
            'emoji': '⚙️'
        },
        'Tutorial': {
            'priority': 2, 
            'description': 'Guided workflows and introductory examples for learning the system.',
            'emoji': '📚'
        },
        'Developer': {
            'priority': 3, 
            'description': 'Tools for creating, debugging, and managing workflows and plugins.',
            'emoji': '⚡'
        },
        'Workshop': {
            'priority': 4, 
            'description': 'Experimental tools and advanced components for power users.',
            'emoji': '🔬'
        },
        'Components': {
            'priority': 5, 
            'description': 'UI and data widgets for building rich workflow interfaces.',
            'emoji': '🧩'
        }
    },
    
    # Role Color Configuration
    'ROLE_COLORS': {
        'menu-role-core': {
            'border': '#22c55e',            # GREEN
            'background': 'rgba(34, 197, 94, 0.1)',
            'background_light': 'rgba(34, 197, 94, 0.05)'
        },
        'menu-role-botify-employee': {
            'border': '#a855f7',            # PURPLE
            'background': 'rgba(168, 85, 247, 0.1)',
            'background_light': 'rgba(168, 85, 247, 0.05)'
        },
        'menu-role-tutorial': {
            'border': '#f97316',            # ORANGE
            'background': 'rgba(249, 115, 22, 0.1)',
            'background_light': 'rgba(249, 115, 22, 0.05)'
        },
        'menu-role-developer': {
            'border': '#3b82f6',            # BLUE
            'background': 'rgba(59, 130, 246, 0.1)',
            'background_light': 'rgba(59, 130, 246, 0.05)'
        },
        'menu-role-components': {
            'border': '#6b7280',            # GRAY
            'background': 'rgba(107, 114, 128, 0.1)',
            'background_light': 'rgba(107, 114, 128, 0.05)'
        },
        'menu-role-workshop': {
            'border': '#eab308',            # YELLOW
            'background': 'rgba(234, 179, 8, 0.1)',
            'background_light': 'rgba(234, 179, 8, 0.05)'
        }
    },
    
    # Botify API Configuration
    'BOTIFY_API': {
        'MAX_EXPORT_SIZE': 1000000,  # Botify's maximum export size limit (1M rows)
        'DEFAULT_EXPORT_SIZE': 1000000,  # Conservative default for testing/development
        'GSC_EXPORT_SIZE': 1000000,  # GSC can handle full export size
        'WEBLOG_EXPORT_SIZE': 1000000,  # Web logs can handle full export size
        'CRAWL_EXPORT_SIZE': 1000000,  # Crawl exports can handle full export size
    },
    
    # UI Constants for Workflows - Centralized button labels, emojis, and styles
    'UI_CONSTANTS': {
        'BUTTON_LABELS': {
            'ENTER_KEY': '🔑 Enter Key',
            'NEXT_STEP': 'Next Step ▸',
            'FINALIZE': '🔒 Finalize',
            'UNLOCK': '🔓 Unlock',
            'PROCEED': 'Proceed ▸',
            'HIDE_SHOW_CODE': '🐍 Hide/Show Code',
            'VIEW_FOLDER': '📂 View Folder',
            'DOWNLOAD_CSV': '⬇️ Copy to Downloads',
            'VISUALIZE_GRAPH': '🌐 Visualize Graph',
            'SKIP_STEP': 'Skip️'
        },
        'BUTTON_STYLES': {
            'PRIMARY': 'primary',
            'SECONDARY': 'secondary',
            'OUTLINE': 'secondary outline',
            'STANDARD': 'secondary outline',
            'FLEX_CONTAINER': 'display: flex; gap: 0.5em; flex-wrap: wrap; align-items: center;',
            'BUTTON_ROW': 'display: flex; gap: 0.5em; align-items: center;',
            'SKIP_BUTTON': 'secondary outline',
            'SKIP_BUTTON_STYLE': 'padding: 0.5rem 1rem; width: 10%; min-width: 80px; white-space: nowrap;'
        },
        'EMOJIS': {
            # Process Status Indicators
            'KEY': '🔑',
            'SUCCESS': '🎯',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'COMPLETION': '✅',
            'LOCKED': '🔒',
            'UNLOCKED': '🔓',
            
            # Data Type Indicators  
            'USER_INPUT': '👤',
            'GREETING': '💬',
            'WORKFLOW': '🔄',
            'INPUT_FORM': '📝'
        },
        'MESSAGES': {
            'WORKFLOW_UNLOCKED': 'Workflow unfinalized! You can now revert to any step and make changes.',
            'ALL_STEPS_COMPLETE': 'All steps complete. Ready to finalize workflow.',
            'FINALIZE_QUESTION': 'All steps complete. Finalize?',
            'FINALIZE_HELP': 'You can revert to any step and make changes.',
            'WORKFLOW_LOCKED': 'Workflow is locked.'
        },
        'LANDING_PAGE': {
            'INPUT_PLACEHOLDER': 'Existing or new 🗝 here (Enter for auto)',
            'INIT_MESSAGE_WORKFLOW_ID': 'Workflow ID: {pipeline_id}',
            'INIT_MESSAGE_RETURN_HINT': "Return later by selecting '{pipeline_id}' from the dropdown."
        }
    }
}

# Update references to use the centralized config
HOME_MENU_ITEM = PIPULATE_CONFIG['HOME_MENU_ITEM']
DEFAULT_ACTIVE_ROLES = PIPULATE_CONFIG['DEFAULT_ACTIVE_ROLES']

ENV_FILE = Path('data/environment.txt')
data_dir = Path('data')
data_dir.mkdir(parents=True, exist_ok=True)
DB_FILENAME = get_db_filename()

def fig(text, font='slant', color='cyan', width=200):
    figlet = Figlet(font=font, width=width)
    fig_text = figlet.renderText(str(text))
    colored_text = Text(fig_text, style=f'{color} on default')
    console.print(colored_text, style='on default')

def set_current_environment(environment):
    ENV_FILE.write_text(environment)
    logger.info(f'Environment set to: {environment}')

def setup_logging():
    """Set up unified logging between console, file, and optional lifecycle log."""
    logger.remove()
    logs_dir = Path('logs')
    logs_dir.mkdir(parents=True, exist_ok=True)
    app_log_path = logs_dir / f'{APP_NAME}.log'
    api_log_path = logs_dir / 'api.log'
    log_level = 'DEBUG' if DEBUG_MODE else 'INFO'
    if app_log_path.exists():
        app_log_path.unlink()
    for old_log in logs_dir.glob(f'{APP_NAME}.????-??-??_*'):
        try:
            old_log.unlink()
        except Exception as e:
            print(f'Failed to delete old log file {old_log}: {e}')
    if api_log_path.exists():
        for i in range(API_LOG_ROTATION_COUNT, 1, -1):
            old_path = logs_dir / f'api-{i}.log'
            new_path = logs_dir / f'api-{i + 1}.log'
            if old_path.exists():
                try:
                    old_path.rename(new_path)
                except Exception as e:
                    print(f'Failed to rotate API log {old_path}: {e}')
        try:
            api_log_path.rename(logs_dir / 'api-2.log')
        except Exception as e:
            print(f'Failed to rotate current API log: {e}')
        for old_log in logs_dir.glob(f'api-[{API_LOG_ROTATION_COUNT + 1}-9].log'):
            try:
                old_log.unlink()
            except Exception as e:
                print(f'Failed to delete old API log {old_log}: {e}')
    time_format = '{time:HH:mm:ss}'
    message_format = '{level: <8} | {name: <15} | {message}'
    logger.add(app_log_path, level=log_level, format=f'{time_format} | {message_format}', enqueue=True)

    def api_log_filter(record):
        return record['extra'].get('api_call') is True
    logger.add(api_log_path, level='INFO', format='{time:YYYY-MM-DD HH:mm:ss} | {message}', filter=api_log_filter, enqueue=True)
    logger.add(sys.stderr, level=log_level, format='<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name: <15}</cyan> | {message}', colorize=True, filter=lambda record: record['level'].name != 'DEBUG' or any((key in record['message'] for key in ['HTTP Request:', 'Pipeline ID:', 'State changed:', 'Creating', 'Updated', 'Plugin', 'Role'])))
    if STATE_TABLES:
        logger.info(f'🔍 State tables ENABLED (🍪 and ➡️ tables will be displayed on console)')
    if TABLE_LIFECYCLE_LOGGING:
        lifecycle_log_path = logs_dir / 'table_lifecycle.log'
        if lifecycle_log_path.exists():
            lifecycle_log_path.unlink()

        def lifecycle_filter(record):
            return record['extra'].get('lifecycle') is True
        logger.add(lifecycle_log_path, level='INFO', format='{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}', filter=lifecycle_filter, enqueue=True, rotation='10 MB')
        logger.bind(lifecycle=True).info('TABLE_LIFECYCLE_LOGGING ENABLED. This log will show table states at critical points.')
        logger.info('📝 TABLE_LIFECYCLE_LOGGING is ENABLED. Detailed table states in logs/table_lifecycle.log')
    return logger

def _format_records_for_lifecycle_log(records_iterable):
    """Format records (list of dicts or objects) into a readable JSON string for logging.
    Handles empty records, dataclass-like objects, dictionaries, and attempts to convert SQLite rows to dicts.
    Excludes private attributes for cleaner logs."""
    if not records_iterable:
        return '[] # Empty'
    processed_records = []
    for r in records_iterable:
        if hasattr(r, '_asdict'):
            processed_records.append(r._asdict())
        elif hasattr(r, '__dict__') and (not isinstance(r, type)):
            processed_records.append({k: v for k, v in r.__dict__.items() if not k.startswith('_sa_')})
        elif isinstance(r, dict):
            processed_records.append(r)
        elif hasattr(r, 'keys'):
            try:
                processed_records.append(dict(r))
            except:
                processed_records.append(dict(zip(r.keys(), r)))
        else:
            processed_records.append(str(r))
    try:
        return json.dumps(processed_records, indent=2, default=str)
    except Exception as e:
        return f'[Error formatting records for JSON: {e}] Processed: {str(processed_records)}'

def log_dynamic_table_state(table_name: str, data_source_callable, title_prefix: str=''):
    """Logs state of a table obtained via a callable (e.g., fastlite table object)."""
    if not TABLE_LIFECYCLE_LOGGING:
        return
    try:
        records = list(data_source_callable())
        content = _format_records_for_lifecycle_log(records)
        logger.bind(lifecycle=True).info(f"\n--- {title_prefix} Snapshot of '{table_name}' ---\n{content}\n--- End Snapshot '{table_name}' ---")
    except Exception as e:
        logger.bind(lifecycle=True).error(f"Failed to log state for table '{table_name}' ({title_prefix}): {e}\n{traceback.format_exc(limit=3)}")

def log_dictlike_db_to_lifecycle(db_name: str, db_instance, title_prefix: str=''):
    """Logs state of a DictLikeDB instance.
    
    Args:
        db_name: Name of the database for logging
        db_instance: DictLikeDB instance to log
        title_prefix: Optional prefix for the log title
    """
    if not TABLE_LIFECYCLE_LOGGING:
        return
    try:
        items = dict(db_instance.items())
        content = json.dumps(items, indent=2, default=str)
        logger.bind(lifecycle=True).info(f"\n--- {title_prefix} Snapshot of '{db_name}' (Key-Value Store) ---\n{content}\n--- End Snapshot '{db_name}' ---")
    except Exception as e:
        logger.bind(lifecycle=True).error(f"Failed to log state for DictLikeDB '{db_name}' ({title_prefix}): {e}\n{traceback.format_exc(limit=3)}")

def log_raw_sql_table_to_lifecycle(db_conn, table_name: str, title_prefix: str=''):
    """Logs state of a table using a raw SQL query via provided sqlite3 connection.
    
    Args:
        db_conn: SQLite database connection
        table_name: Name of the table to log
        title_prefix: Optional prefix for the log title
    """
    if not TABLE_LIFECYCLE_LOGGING:
        return
    original_row_factory = db_conn.row_factory
    db_conn.row_factory = sqlite3.Row
    try:
        cursor = db_conn.cursor()
        cursor.execute(f'SELECT * FROM {table_name}')
        rows = cursor.fetchall()
        content = _format_records_for_lifecycle_log(rows)
        logger.bind(lifecycle=True).info(f"\n--- {title_prefix} Snapshot of '{table_name}' (Raw SQL) ---\n{content}\n--- End Snapshot '{table_name}' (Raw SQL) ---")
    except Exception as e:
        logger.bind(lifecycle=True).error(f"Failed to log raw SQL table '{table_name}' ({title_prefix}): {e}\n{traceback.format_exc(limit=3)}")
    finally:
        db_conn.row_factory = original_row_factory
logger = setup_logging()
if __name__ == '__main__':
    if DEBUG_MODE:
        logger.info('🔍 Running in DEBUG mode (verbose logging enabled)')
    else:
        logger.info('🚀 Running in INFO mode (edit server.py and set DEBUG_MODE=True for verbose logging)')

class LogManager:
    """Central logging coordinator for artistic control of console and file output.

    This class provides methods that encourage a consistent, carefully curated
    logging experience across both console and log file. It encourages using 
    the same messages in both places with appropriate formatting.
    """

    def __init__(self, logger):
        self.logger = logger
        self.categories = {'server': '🖥️ SERVER', 'startup': '🚀 STARTUP', 'workflow': '⚙️ WORKFLOW', 'pipeline': '🔄 PIPELINE', 'network': '🌐 NETWORK', 'database': '💾 DATABASE', 'profile': '👤 PROFILE', 'plugin': '🔌 PLUGIN', 'chat': '💬 CHAT', 'error': '❌ ERROR', 'warning': '⚠️ WARNING'}

    def format_message(self, category, message, details=None):
        emoji = self.categories.get(category, f'⚡ {category.upper()}')
        formatted = f'[{emoji}] {message}'
        if details:
            formatted += f' | {details}'
        return formatted

    def startup(self, message, details=None):
        """Log a startup-related message."""
        self.logger.info(self.format_message('startup', message, details))

    def workflow(self, message, details=None):
        """Log a workflow-related message."""
        self.logger.info(self.format_message('workflow', message, details))

    def pipeline(self, message, details=None, pipeline_id=None):
        """Log a pipeline-related message."""
        if pipeline_id:
            details = f'Pipeline: {pipeline_id}' + (f' | {details}' if details else '')
        self.logger.info(self.format_message('pipeline', message, details))

    def profile(self, message, details=None):
        """Log a profile-related message."""
        self.logger.info(self.format_message('profile', message, details))

    def data(self, message, data=None):
        """Log structured data - at DEBUG level since it's typically verbose."""
        msg = self.format_message('database', message)
        if data is not None:
            if isinstance(data, dict) and len(data) > 5:
                self.logger.debug(f'{msg} | {json.dumps(data, indent=2)}')
            else:
                self.logger.debug(f'{msg} | {data}')
        else:
            self.logger.info(msg)

    def event(self, event_type, message, details=None):
        """Log a user-facing event in the application."""
        self.logger.info(self.format_message(event_type, message, details))

    def warning(self, message, details=None):
        """Log a warning message at WARNING level."""
        self.logger.warning(self.format_message('warning', message, details))

    def error(self, message, error=None):
        """Log an error with traceback at ERROR level."""
        formatted = self.format_message('error', message)
        if error:
            import traceback
            error_details = f'{error.__class__.__name__}: {str(error)}'
            self.logger.error(f'{formatted} | {error_details}')
            self.logger.debug(traceback.format_exc())
        else:
            self.logger.error(formatted)

    def debug(self, category, message, details=None):
        """Log debug information that only appears in DEBUG mode."""
        self.logger.debug(self.format_message(category, message, details))
log = LogManager(logger)
custom_theme = Theme({'default': 'white on black', 'header': RichStyle(color='magenta', bold=True, bgcolor='black'), 'cyan': RichStyle(color='cyan', bgcolor='black'), 'green': RichStyle(color='green', bgcolor='black'), 'orange3': RichStyle(color='orange3', bgcolor='black'), 'white': RichStyle(color='white', bgcolor='black')})

class DebugConsole(Console):

    def print(self, *args, **kwargs):
        super().print(*args, **kwargs)
console = DebugConsole(theme=custom_theme)

class SSEBroadcaster:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.queue = asyncio.Queue()
            logger.bind(name='sse').info('SSE Broadcaster initialized')
            self._initialized = True

    async def generator(self):
        while True:
            try:
                message = await asyncio.wait_for(self.queue.get(), timeout=5.0)
                logger.bind(name='sse').debug(f'Sending: {message}')
                if message:
                    formatted = '\n'.join((f'data: {line}' for line in message.split('\n')))
                    yield f'{formatted}\n\n'
            except asyncio.TimeoutError:
                now = datetime.now()
                yield f'data: Test ping at {now}\n\n'

    async def send(self, message):
        logger.bind(name='sse').debug(f'Queueing: {message}')
        await self.queue.put(message)
broadcaster = SSEBroadcaster()

def read_training(prompt_or_filename):
    if isinstance(prompt_or_filename, str) and prompt_or_filename.endswith('.md'):
        try:
            logger.debug(f'Loading prompt from training/{prompt_or_filename}')
            with open(f'training/{prompt_or_filename}', 'r') as f:
                content = f.read()
                logger.debug(f'Successfully loaded prompt: {content[:100]}...')
                return content
        except FileNotFoundError:
            plugin_name = None
            for name, instance in plugin_instances.items():
                if hasattr(instance, 'TRAINING_PROMPT') and instance.TRAINING_PROMPT == prompt_or_filename:
                    plugin_name = instance.DISPLAY_NAME
                    break
            if plugin_name:
                logger.warning(f'No training file found for {prompt_or_filename} (used by {plugin_name})')
            else:
                logger.warning(f'No training file found for {prompt_or_filename}')
            return f"No training content available for {prompt_or_filename.replace('.md', '')}"
    return prompt_or_filename
if MAX_LLM_RESPONSE_WORDS:
    limiter = f'in under {MAX_LLM_RESPONSE_WORDS} {TONE} words'
else:
    limiter = ''
global_conversation_history = deque(maxlen=MAX_CONVERSATION_LENGTH)
conversation = [{'role': 'system', 'content': read_training('system_prompt.md')}]

def append_to_conversation(message=None, role='user'):
    """Append a message to the global conversation history.

    This function manages the conversation history by:
    1. Ensuring a system message exists at the start of history
    2. Appending new messages with specified roles
    3. Maintaining conversation length limits via deque maxlen
    4. Preventing duplicate consecutive messages

    Args:
        message (str, optional): The message content to append. If None, returns current history.
        role (str, optional): The role of the message sender. Defaults to 'user'.

    Returns:
        list: The complete conversation history after appending.
    """
    if message is None:
        return list(global_conversation_history)
    
    # Check if this would be a duplicate of the last message
    if global_conversation_history and global_conversation_history[-1]['content'] == message and global_conversation_history[-1]['role'] == role:
        return list(global_conversation_history)
        
    needs_system_message = len(global_conversation_history) == 0 or global_conversation_history[0]['role'] != 'system'
    if needs_system_message:
        global_conversation_history.appendleft(conversation[0])
    global_conversation_history.append({'role': role, 'content': message})
    return list(global_conversation_history)

def title_name(word: str) -> str:
    """Format a string into a title case form."""
    if not word:
        return ''
    formatted = word.replace('.', ' ').replace('-', ' ')
    words = []
    for part in formatted.split('_'):
        words.extend(part.split())
    processed_words = []
    for word in words:
        if word.isdigit():
            processed_words.append(word.lstrip('0') or '0')
        else:
            processed_words.append(word.capitalize())
    return ' '.join(processed_words)

def endpoint_name(endpoint: str) -> str:
    if not endpoint:
        return HOME_MENU_ITEM
    if endpoint in friendly_names:
        return friendly_names[endpoint]
    return title_name(endpoint)

def pipeline_operation(func):

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        url = args[0] if args else None
        if not url:
            return func(self, *args, **kwargs)
        old_state = self._get_clean_state(url)
        result = func(self, *args, **kwargs)
        new_state = self._get_clean_state(url)
        if old_state != new_state:
            changes = {k: new_state[k] for k in new_state if k not in old_state or old_state[k] != new_state[k]}
            if changes:
                operation = func.__name__
                step_changes = [k for k in changes if not k.startswith('_')]
                if step_changes:
                    log.pipeline(f"Operation '{operation}' updated state", details=f"Steps: {', '.join(step_changes)}", pipeline_id=url)
                log.debug('pipeline', f"Pipeline '{url}' detailed changes", json.dumps(changes, indent=2))
        return result
    return wrapper

class Pipulate:
    """Central coordinator for pipelines and chat functionality.

    This class serves as the main interface for plugins to access
    shared functionality without relying on globals.

    As Pipulate evolves toward its "Digital Workshop" vision, this coordinator
    will support:
    - Sub-plugin architecture (steps expanding to full-screen apps)
    - Content curation systems (archive surfing, variant creation)
    - Progressive distillation workflows (search, sort, sieve, story)
    - Local-first creative exploration with privacy preservation

    The centralized coordination pattern enables sophisticated interaction
    monitoring and behavioral pattern analysis while maintaining the
    "vibrating edge" of creative freedom that powers genuine innovation.
    """
    PRESERVE_REFILL = True
    ERROR_STYLE = 'color: red;'
    SUCCESS_STYLE = 'color: green;'
    WARNING_BUTTON_STYLE = None
    PRIMARY_BUTTON_STYLE = None
    SECONDARY_BUTTON_STYLE = None
    UNLOCK_BUTTON_LABEL = '🔓 Unlock'
    MUTED_TEXT_STYLE = 'font-size: 0.9em; color: var(--pico-muted-color);'
    CONTENT_STYLE = 'margin-top: 1vh; border-top: 1px solid var(--pico-muted-border-color); padding-top: 1vh;'
    FINALIZED_CONTENT_STYLE = 'margin-top: 0.5vh; padding: 0.5vh 0;'
    MENU_ITEM_PADDING = 'padding: 1vh 0px 0px .5vw;'

    def __init__(self, pipeline_table, chat_instance=None):
        """Initialize Pipulate with required dependencies.

        Args:
            pipeline_table: The database table for storing pipeline state
            chat_instance: Optional chat coordinator instance
        """
        self.table = pipeline_table
        self.chat = chat_instance
        self.message_queue = self.OrderedMessageQueue()

    def append_to_history(self, message: str, role: str='system') -> None:
        """Add a message to the LLM conversation history without triggering a response.

        This is the preferred way for workflows to update the LLM's context about:
        - UI state changes
        - Form submissions
        - Validation results
        - Explanatory text shown to users
        - Step completion status

        Args:
            message: The message to add to history
            role: The role of the message sender ("system", "user", "assistant")
        """
        append_to_conversation(message, role=role)

    class OrderedMessageQueue:
        """A lightweight queue to ensure messages are delivered in order.

        This class creates a simple message queue that ensures messages are delivered
        in the exact order they are added, without requiring explicit delays between
        messages. It's used to fix the message streaming order issues.

        As part of the Digital Workshop evolution, this queue will support:
        - Interaction pattern recognition for adaptive workflows
        - State transition tracking for sub-plugin applications
        - Creative session analysis for distillation workflows
        - Privacy-preserving behavioral insights for local optimization

        The workflow state tracking enables sophisticated user interaction
        analysis while keeping all data local for maximum creative freedom.
        """

        def __init__(self):
            self.queue = []
            self._processing = False
            self._current_step = None
            self._step_completed = False

        def _get_workflow_context(self):
            """Get the current workflow context for the LLM."""
            if not self._current_step:
                return '[WORKFLOW STATE: Not yet started]'
            elif self._step_completed:
                return f'[WORKFLOW STATE: Step {self._current_step} completed]'
            else:
                return f'[WORKFLOW STATE: Waiting for Step {self._current_step} input]'

        async def add(self, pipulate, message, **kwargs):
            """Add a message to the queue and process if not already processing."""
            logger.info(f'[🔄 WORKFLOW] {message}')
            if isinstance(message, str):
                message = message.replace('http:', 'http꞉').replace('https:', 'https꞉')
            role = kwargs.pop('role', 'system')
            if 'Step ' in message and 'Please enter' in message:
                step_num = message.split('Step ')[1].split(':')[0]
                self._current_step = step_num
                self._step_completed = False
            elif 'complete' in message.lower() and 'step' in message.lower():
                self._step_completed = True
            context_message = message
            if role == 'system':
                if 'Please' in message or 'Enter' in message or message.endswith('?'):
                    context_message = f'[PROMPT] {message}'
                else:
                    context_message = f'[INFO] {message}'
            elif role == 'user':
                context_message = f'[USER INPUT] {message}'
            elif role == 'assistant':
                context_message = f'[RESPONSE] {message}'
            workflow_context = self._get_workflow_context()
            context_message = f'{workflow_context}\n{context_message}'
            append_to_conversation(context_message, role=role)
            self.queue.append((pipulate, message, kwargs))
            if not self._processing:
                await self._process_queue()

        async def _process_queue(self):
            """Process all queued messages in order."""
            self._processing = True
            try:
                while self.queue:
                    pipulate, message, kwargs = self.queue.pop(0)
                    response = await pipulate.stream(message, **kwargs)
                    if response and response != message:
                        workflow_context = self._get_workflow_context()
                        append_to_conversation(f'{workflow_context}\n[RESPONSE] {response}', role='assistant')
            finally:
                self._processing = False

        def mark_step_complete(self, step_num):
            """Mark a step as completed."""
            self._current_step = step_num
            self._step_completed = True

        def mark_step_started(self, step_num):
            """Mark a step as started but not completed."""
            self._current_step = step_num
            self._step_completed = False

    def make_singular(self, word):
        """Convert a potentially plural word to its singular form using simple rules.

        This uses basic suffix replacement rules to handle common English plurals.
        It's designed for the 80/20 rule - handling common cases without complexity.

        Args:
            word (str): The potentially plural word to convert

        Returns:
            str: The singular form of the word
        """
        word = word.strip()
        if not word:
            return word
        if word.lower() in ('data', 'media', 'series', 'species', 'news'):
            return word
        irregulars = {'children': 'child', 'people': 'person', 'men': 'man', 'women': 'woman', 'teeth': 'tooth', 'feet': 'foot', 'geese': 'goose', 'mice': 'mouse', 'criteria': 'criterion'}
        if word.lower() in irregulars:
            return irregulars[word.lower()]
        if word.lower().endswith('ies'):
            return word[:-3] + 'y'
        if word.lower().endswith('ves'):
            return word[:-3] + 'f'
        if word.lower().endswith('xes') or word.lower().endswith('sses') or word.lower().endswith('shes') or word.lower().endswith('ches'):
            return word[:-2]
        if word.lower().endswith('s') and (not word.lower().endswith('ss')):
            return word[:-1]
        return word

    def set_chat(self, chat_instance):
        """Set the chat instance after initialization."""
        self.chat = chat_instance

    def get_message_queue(self):
        """Return the message queue instance for ordered message delivery."""
        return self.message_queue

    def step_button(self, visual_step_number: str, preserve: bool=False, revert_label: str=None) -> str:
        """
        Formats the revert button text.
        Uses visual_step_number for "Step X" numbering if revert_label is not provided.

        Args:
            visual_step_number: The visual step number (e.g., "1", "2", "3") based on position in workflow
            preserve: Whether to use the preserve symbol (⟲) instead of revert symbol (↶)
            revert_label: Custom label to use instead of "Step X" format
        """
        symbol = '⟲' if preserve else '↶'
        if revert_label:
            button_text = f'{symbol}\xa0{revert_label}'
        else:
            button_text = f'{symbol}\xa0Step\xa0{visual_step_number}'
        return button_text

    def get_style(self, style_type):
        return getattr(self, f'{style_type.upper()}_STYLE', None)
    
    def get_ui_constants(self):
        """Access centralized UI constants through dependency injection."""
        return PIPULATE_CONFIG['UI_CONSTANTS']
    
    def get_config(self):
        """Access centralized configuration through dependency injection."""
        return PIPULATE_CONFIG

    def register_workflow_routes(self, plugin_instance):
        """
        Register standard and step-specific routes for a workflow plugin.
        
        This helper extracts the common route registration boilerplate from workflow __init__ methods,
        while maintaining the WET principle - each workflow still explicitly calls this method.
        
        Args:
            plugin_instance: The workflow plugin instance with app, APP_NAME, and steps attributes
        """
        app_name = plugin_instance.APP_NAME
        steps = plugin_instance.steps
        
        # Standard workflow lifecycle routes
        routes = [
            (f'/{app_name}/init', plugin_instance.init, ['POST']),
            (f'/{app_name}/revert', plugin_instance.handle_revert, ['POST']),
            (f'/{app_name}/unfinalize', plugin_instance.unfinalize, ['POST'])
        ]
        
        # Dynamically create routes for each step from the plugin's steps list
        for step_obj in steps:
            step_id = step_obj.id
            handler_method = getattr(plugin_instance, step_id, None)
            if handler_method:
                current_methods = ['GET']
                if step_id == 'finalize':
                    current_methods.append('POST')
                routes.append((f'/{app_name}/{step_id}', handler_method, current_methods))
            
            # Only data steps (not 'finalize') have explicit _submit handlers
            if step_id != 'finalize':
                submit_handler_method = getattr(plugin_instance, f'{step_id}_submit', None)
                if submit_handler_method:
                    routes.append((f'/{app_name}/{step_id}_submit', submit_handler_method, ['POST']))

        # Register all routes with the FastHTML app
        for path, handler, *methods_list_arg in routes:
            current_methods = methods_list_arg[0] if methods_list_arg else ['GET']
            plugin_instance.app.route(path, methods=current_methods)(handler)

    async def log_api_call_details(self, pipeline_id: str, step_id: str, call_description: str, method: str, url: str, headers: dict, payload: Optional[dict]=None, response_status: Optional[int]=None, response_preview: Optional[str]=None, curl_command: Optional[str]=None, python_command: Optional[str]=None, estimated_rows: Optional[int]=None, actual_rows: Optional[int]=None, file_path: Optional[str]=None, file_size: Optional[str]=None, notes: Optional[str]=None):
        """
        Logs detailed information about an API call related to a workflow.
        This serves as a hook for future, more sophisticated logging or UI display.
        """
        log_entry_parts = [f'API CALL INFO for Pipeline: {pipeline_id}, Step: {step_id}, Description: {call_description}', f'  Request: {method.upper()} {url}']
        logged_headers = headers.copy()
        if 'Authorization' in logged_headers:
            logged_headers['Authorization'] = 'Token f{YOUR_BOTIFY_API_TOKEN}'
        log_entry_parts.append(f'  Headers:\n{json.dumps(logged_headers, indent=2)}')
        if payload:
            try:
                payload_str = json.dumps(payload, indent=2)
                log_entry_parts.append(f'  Payload:\n{payload_str}')
            except TypeError:
                log_entry_parts.append('  Payload: (Omitted due to non-serializable content)')
        if python_command:
            log_entry_parts.append(f'  Python (httpx) Snippet:\n{python_command}')
            log_entry_parts.append('  Note: The API token should be loaded from a secure file location.')
        if estimated_rows is not None:
            log_entry_parts.append(f'  Estimated Rows (from pre-check): {estimated_rows:,}')
        if actual_rows is not None:
            log_entry_parts.append(f'  Actual Rows Downloaded: {actual_rows:,}')
        if response_status is not None:
            log_entry_parts.append(f'  Response Status: {response_status}')
        if response_preview:
            try:
                parsed = json.loads(response_preview)
                pretty_preview = json.dumps(parsed, indent=2)
                log_entry_parts.append(f'  Response Preview:\n{pretty_preview}')
            except Exception:
                log_entry_parts.append(f'  Response Preview:\n{response_preview}')
        if file_path:
            log_entry_parts.append(f'  Associated File Path: {file_path}')
        if file_size:
            log_entry_parts.append(f'  Associated File Size: {file_size}')
        if notes:
            log_entry_parts.append(f'  Notes: {notes}')
        full_log_message = '\n'.join(log_entry_parts)
        logger.debug(f'\n--- API Call Log ---\n{full_log_message}\n--- End API Call Log ---')
        is_bql = 'bql' in (call_description or '').lower() or 'botify query language' in (call_description or '').lower()
        logger.bind(api_call=True, bql_api_call=is_bql).info(full_log_message)

    def fmt(self, endpoint: str) -> str:
        """Format an endpoint string into a human-readable form."""
        if endpoint in friendly_names:
            return friendly_names[endpoint]
        return title_name(endpoint)

    def _get_clean_state(self, pkey):
        try:
            record = self.table[pkey]
            state = json.loads(record.data)
            state.pop('created', None)
            state.pop('updated', None)
            return state
        except (NotFoundError, json.JSONDecodeError):
            return {}

    def get_timestamp(self) -> str:
        return datetime.now().isoformat()

    def get_plugin_context(self, plugin_instance=None):
        """
        Returns the context information about the current plugin and profile.

        Args:
            plugin_instance: Optional plugin instance to extract name from

        Returns:
            dict: Contains plugin_name, profile_id, and profile_name
        """
        profile_id = get_current_profile_id()
        profile_name = get_profile_name()
        plugin_name = None
        display_name = None
        if plugin_instance:
            if hasattr(plugin_instance, 'DISPLAY_NAME'):
                display_name = plugin_instance.DISPLAY_NAME
            if hasattr(plugin_instance, 'name'):
                plugin_name = plugin_instance.name
            elif hasattr(plugin_instance, '__class__'):
                plugin_name = plugin_instance.__class__.__name__
            if plugin_name and (not display_name):
                if plugin_name in friendly_names:
                    display_name = friendly_names[plugin_name]
                else:
                    display_name = title_name(plugin_name)
        return {'plugin_name': display_name or plugin_name, 'internal_name': plugin_name, 'profile_id': profile_id, 'profile_name': profile_name}

    @pipeline_operation
    def initialize_if_missing(self, pkey: str, initial_step_data: dict=None) -> tuple[Optional[dict], Optional[Card]]:
        try:
            state = self.read_state(pkey)
            if state:
                return (state, None)
            now = self.get_timestamp()
            state = {'created': now, 'updated': now}
            if initial_step_data:
                app_name = None
                if 'app_name' in initial_step_data:
                    app_name = initial_step_data.pop('app_name')
                state.update(initial_step_data)
            self.table.insert({'pkey': pkey, 'app_name': app_name if app_name else None, 'data': json.dumps(state), 'created': now, 'updated': now})
            return (state, None)
        except:
            error_card = Card(H3('ID Already In Use'), P(f"The ID '{pkey}' is already being used by another workflow. Please try a different ID."), style=self.id_conflict_style())
            return (None, error_card)

    def read_state(self, pkey: str) -> dict:
        logger.debug(f'Reading state for pipeline: {pkey}')
        try:
            self.table.xtra(pkey=pkey)
            records = self.table()
            logger.debug(f'Records found: {records}')
            if records:
                logger.debug(f'First record type: {type(records[0])}')
                logger.debug(f'First record dir: {dir(records[0])}')
            if records and hasattr(records[0], 'data'):
                state = json.loads(records[0].data)
                logger.debug(f'Found state: {json.dumps(state, indent=2)}')
                return state
            logger.debug('No valid state found')
            return {}
        except Exception as e:
            logger.debug(f'Error reading state: {str(e)}')
            return {}

    def write_state(self, pkey: str, state: dict) -> None:
        state['updated'] = datetime.now().isoformat()
        payload = {'pkey': pkey, 'data': json.dumps(state), 'updated': state['updated']}
        logger.debug(f'Update payload:\n{json.dumps(payload, indent=2)}')
        self.table.update(payload)
        verification = self.read_state(pkey)
        logger.debug(f'Verification read:\n{json.dumps(verification, indent=2)}')

    def format_links_in_text(self, text):
        """
        Convert plain URLs in text to clickable HTML links.
        Safe for logging but renders as HTML in the UI.
        """
        import re
        url_pattern = 'https?://(?:[-\\w.]|(?:%[\\da-fA-F]{2}))+'

        def replace_url(match):
            url = match.group(0)
            return f'<a href="{url}" target="_blank">{url}</a>'
        return re.sub(url_pattern, replace_url, text)

    async def stream(self, message, verbatim=False, role='user', spaces_before=None, spaces_after=1, simulate_typing=True):
        """
        Stream a message to the chat interface.

        This method is now a direct passthrough to the streaming implementation.
        Using this method directly will bypass the OrderedMessageQueue - it's
        recommended to use message_queue.add() for proper message ordering in 
        complex async scenarios.

        Args:
            message: The message to stream
            verbatim: If True, send message as-is; if False, process with LLM
            role: The role for the message in the conversation history
            spaces_before: Number of line breaks to add before the message
            spaces_after: Number of line breaks to add after the message
            simulate_typing: Whether to simulate typing for verbatim messages

        Returns:
            The original message
        """
        try:
            conversation_history = append_to_conversation(message, role)
            if spaces_before:
                for _ in range(spaces_before):
                    await chat.broadcast(' <br>\n')
            if verbatim:
                if simulate_typing:
                    words = message.split(' ')
                    for i, word in enumerate(words):
                        await chat.broadcast(word)
                        if i < len(words) - 1:
                            await chat.broadcast(' ')
                        await asyncio.sleep(0.005)
                else:
                    await chat.broadcast(message)
                response_text = message
            else:
                response_text = ''
                async for chunk in chat_with_llm(MODEL, conversation_history):
                    await chat.broadcast(chunk)
                    response_text += chunk
            if spaces_after:
                for _ in range(spaces_after):
                    await chat.broadcast(' <br>\n')
            append_to_conversation(response_text, 'assistant')
            logger.debug(f'Message streamed: {response_text}')
            return message
        except Exception as e:
            logger.error(f'Error in pipulate.stream: {e}')
            traceback.print_exc()
            raise

    def display_revert_header(self, step_id: str, app_name: str, steps: list, message: str=None, target_id: str=None, revert_label: str=None, remove_padding: bool=False):
        """Create a UI control for reverting to a previous workflow step.
        
        The button label uses the visual sequence number of the step.

        Args:
            step_id: The ID of the step to revert to
            app_name: The workflow app name
            steps: List of Step namedtuples defining the workflow
            message: Optional message to display (defaults to step_id)
            target_id: Optional target for HTMX updates (defaults to app container)
            revert_label: Optional custom label for the revert button
            remove_padding: Whether to remove padding from the article (for advanced layout)

        Returns:
            Card: A FastHTML Card component with revert functionality
        """
        pipeline_id = db.get('pipeline_id', '')
        finalize_step = steps[-1] if steps and steps[-1].id == 'finalize' else None
        if pipeline_id and finalize_step:
            final_data = self.get_step_data(pipeline_id, finalize_step.id, {})
            if finalize_step.done in final_data:
                return None
        step = next((s for s in steps if s.id == step_id), None)
        if not step:
            logger.error(f"Step with id '{step_id}' not found in steps list for display_revert_header.")
            return Div(f'Error: Step {step_id} not found.')
        data_collection_steps = [s for s in steps if s.id != 'finalize']
        visual_step_number = 'N/A'
        try:
            step_index = data_collection_steps.index(step)
            visual_step_number = str(step_index + 1)
        except ValueError:
            logger.warning(f"Step id '{step_id}' (show: '{step.show}') not found in data_collection_steps. Revert button will show 'Step N/A'.")
        refill = getattr(step, 'refill', False)
        target_id = target_id or f'{app_name}-container'
        form = Form(Input(type='hidden', name='step_id', value=step_id), Button(self.step_button(visual_step_number, refill, revert_label), type='submit', cls='button-revert'), hx_post=f'/{app_name}/revert', hx_target=f'#{target_id}', hx_swap='outerHTML')
        if not message:
            return form
        article_style = 'display: flex; align-items: center; justify-content: space-between; background-color: var(--pico-card-background-color);'
        if remove_padding:
            article_style += ' padding: 0;'
        return Card(Div(message, style='flex: 1'), Div(form, style='flex: 0'), style=article_style)

    def display_revert_widget(self, step_id: str, app_name: str, steps: list, message: str=None, widget=None, target_id: str=None, revert_label: str=None, widget_style=None):
        """Create a standardized container for widgets and visualizations.
        
        Core pattern for displaying rich content below workflow steps with consistent
        styling and DOM targeting for dynamic updates.
        
        Features:
        - Consistent padding/spacing with revert controls
        - Unique DOM addressing for targeted updates
        - Support for function-based widgets and AnyWidget components
        - Standard styling with override capability
        
        Args:
            step_id: ID of the step this widget belongs to
            app_name: Workflow app name
            steps: List of Step namedtuples defining the workflow
            message: Optional message for revert control
            widget: Widget/visualization to display
            target_id: Optional HTMX update target
            revert_label: Optional custom revert button label
            widget_style: Optional custom widget container style
            
        Returns:
            Div: FastHTML container with revert control and widget content
        """
        revert_row = self.display_revert_header(step_id=step_id, app_name=app_name, steps=steps, message=message, target_id=target_id, revert_label=revert_label, remove_padding=True)
        if widget is None or revert_row is None:
            return revert_row
        applied_style = widget_style or self.CONTENT_STYLE
        return Div(revert_row, Div(widget, style=applied_style, id=f'{step_id}-widget-{hash(str(widget))}'), id=f'{step_id}-content', cls='card-container')

    def tree_display(self, content):
        """Create a styled display for file paths in tree or box format.
        
        Example widget function demonstrating reusable, styled components
        with consistent spacing in workflow displays.
        
        Args:
            content: Content to display (tree-formatted or plain path)
            
        Returns:
            Pre: Styled Pre component
        """
        is_tree = '\n' in content and ('└─' in content or '├─' in content)
        if is_tree:
            return Pre(content, style='background-color: var(--pico-card-sectionning-background-color); border-radius: 4px; font-family: monospace; margin: 0; padding: 0.5rem; white-space: pre')
        else:
            return Pre(content, style=(
        'background-color: #e3f2fd; ',
        'border-radius: 4px; ',
        'border: 1px solid #bbdefb; ',
        'color: #1976d2; ',
        'font-family: system-ui; ',
        'margin: 0; ',
        'padding: 0.5rem 1rem; ',
        'white-space: pre-wrap'
    ))

    def finalized_content(self, message: str, content=None, heading_tag=H4, content_style=None):
        """Create a finalized step display with optional content.
        
        Companion to display_revert_widget_advanced for finalized workflows,
        providing consistent styling for both states.
        
        Args:
            message: Message to display (typically with 🔒 lock icon)
            content: FastHTML component to display below message
            heading_tag: Tag to use for message (default: H4)
            content_style: Optional custom content container style
            
        Returns:
            Card: FastHTML Card component for finalized state
        """
        if content is None:
            return Card(message)
        applied_style = content_style or self.FINALIZED_CONTENT_STYLE
        return Card(heading_tag(message), Div(content, style=applied_style), cls='card-container')

    def wrap_with_inline_button(self, input_element: Input, button_label: str='Next ▸', button_class: str='primary') -> Div:
        """Wrap an input element with an inline button in a flex container.
        
        Args:
            input_element: The input element to wrap
            button_label: Text to display on the button (default: 'Next ▸')
            button_class: CSS class for the button (default: 'primary')
            
        Returns:
            Div: A flex container with the input and button
        """
        button_style = 'display: inline-block;cursor: pointer;width: auto !important;white-space: nowrap;'
        container_style = 'display: flex;align-items: center;gap: 0.5rem;'
        return Div(input_element, Button(button_label, type='submit', cls=button_class, style=button_style), style=container_style)

    def create_standard_landing_page(self, plugin_instance):
        """
        Creates a standardized landing page for workflows using centralized UI constants.
        
        This helper reduces boilerplate while maintaining WET workflow explicitness.
        Each workflow still explicitly calls this method and can customize the result.
        
        Args:
            plugin_instance: The workflow plugin instance
            
        Returns:
            Container: Standard landing page structure
        """
        from server import PIPULATE_CONFIG
        
        # Standard display name derivation
        try:
            import inspect
            from pathlib import Path
            module_file = inspect.getfile(plugin_instance.__class__)
            import importlib
            blank_placeholder_module = importlib.import_module('plugins.910_blank_placeholder')
            derive_public_endpoint_from_filename = blank_placeholder_module.derive_public_endpoint_from_filename
            public_app_name_for_display = derive_public_endpoint_from_filename(Path(module_file).name)
        except (TypeError, AttributeError, ImportError):
            public_app_name_for_display = plugin_instance.APP_NAME
            
        title = plugin_instance.DISPLAY_NAME or public_app_name_for_display.replace("_", " ").title()
        
        # Standard pipeline key generation and matching records
        full_key, prefix, _ = self.generate_pipeline_key(plugin_instance)
        self.table.xtra(app_name=plugin_instance.APP_NAME)
        matching_records = [record.pkey for record in self.table() if record.pkey.startswith(prefix)]
        
        # Standard form with centralized constants
        ui_constants = PIPULATE_CONFIG['UI_CONSTANTS']
        landing_constants = PIPULATE_CONFIG['UI_CONSTANTS']['LANDING_PAGE']
        
        return Container(
            Card(
                H2(title),
                P(plugin_instance.ENDPOINT_MESSAGE, cls='text-secondary'),
                Form(
                    self.wrap_with_inline_button(
                        Input(
                            placeholder=landing_constants['INPUT_PLACEHOLDER'],
                            name='pipeline_id',
                            list='pipeline-ids',
                            type='search',
                            required=False,
                            autofocus=True,
                            value=full_key,
                            _onfocus='this.setSelectionRange(this.value.length, this.value.length)',
                            cls='contrast'
                        ),
                        button_label=ui_constants['BUTTON_LABELS']['ENTER_KEY'],
                        button_class=ui_constants['BUTTON_STYLES']['SECONDARY']
                    ),
                    self.update_datalist('pipeline-ids', options=matching_records, clear=not matching_records),
                    hx_post=f'/{plugin_instance.APP_NAME}/init',
                    hx_target=f'#{plugin_instance.APP_NAME}-container'
                )
            ),
            Div(id=f'{plugin_instance.APP_NAME}-container')
        )

    async def get_state_message(self, pkey: str, steps: list, messages: dict) -> str:
        state = self.read_state(pkey)
        logger.debug(f'\nDEBUG [{pkey}] State Check:')
        logger.debug(json.dumps(state, indent=2))
        for step in reversed(steps):
            if step.id not in state:
                continue
            if step.done == 'finalized':
                if step.done in state[step.id]:
                    return self._log_message('finalized', messages['finalize']['complete'])
                return self._log_message('ready to finalize', messages['finalize']['ready'])
            step_data = state[step.id]
            step_value = step_data.get(step.done)
            if step_value:
                msg = messages[step.id]['complete']
                msg = msg.format(step_value) if '{}' in msg else msg
                return self._log_message(f'{step.id} complete ({step_value})', msg)
        return self._log_message('new pipeline', messages['new'])

    def _log_message(self, state_desc: str, message: str) -> str:
        safe_state = state_desc.replace('<', '\\<').replace('>', '\\>')
        safe_message = message.replace('<', '\\<').replace('>', '\\>')
        logger.debug(f'State: {safe_state}, Message: {safe_message}')
        append_to_conversation(message, role='system')
        return message

    @pipeline_operation
    def get_step_data(self, pkey: str, step_id: str, default=None) -> dict:
        state = self.read_state(pkey)
        return state.get(step_id, default or {})

    async def clear_steps_from(self, pipeline_id: str, step_id: str, steps: list) -> dict:
        state = self.read_state(pipeline_id)
        start_idx = next((i for i, step in enumerate(steps) if step.id == step_id), -1)
        if start_idx == -1:
            logger.error(f'[clear_steps_from] Step {step_id} not found in steps list')
            return state
        for step in steps[start_idx + 1:]:
            if (not self.PRESERVE_REFILL or not step.refill) and step.id in state:
                logger.debug(f'[clear_steps_from] Removing step {step.id}')
                del state[step.id]
        self.write_state(pipeline_id, state)
        return state

    def id_conflict_style(self):
        """Return style for ID conflict error messages"""
        return 'background-color: #ffdddd; color: #990000; padding: 10px; border-left: 5px solid #990000;'

    def generate_pipeline_key(self, plugin_instance, user_input=None):
        """Generate a standardized pipeline key using the current profile and plugin.

        Creates a composite key in the format: profile_name-plugin_name-user_id
        If user_input is numeric and less than 100, it will be formatted with leading zeros.

        Args:
            plugin_instance: The plugin instance requesting the key
            user_input: Optional user-provided ID part (defaults to auto-incrementing number)

        Returns:
            tuple: (full_key, prefix, user_part) where:
                full_key: The complete pipeline key
                prefix: The profile-plugin prefix
                user_part: The user-specific part of the key
        """
        context = self.get_plugin_context(plugin_instance)
        app_name = getattr(plugin_instance, 'APP_NAME', None)
        plugin_name = app_name or context['plugin_name'] or getattr(plugin_instance, 'DISPLAY_NAME', None) or getattr(plugin_instance, 'app_name', 'unknown')
        profile_name = context['profile_name'] or 'default'
        profile_part = profile_name.replace(' ', '_')
        plugin_part = plugin_name.replace(' ', '_')
        prefix = f'{profile_part}-{plugin_part}-'
        if user_input is None:
            self.table.xtra()
            self.table.xtra(app_name=app_name)
            app_records = list(self.table())
            matching_records = [record.pkey for record in app_records if record.pkey.startswith(prefix)]
            numeric_suffixes = []
            for record_key in matching_records:
                rec_user_part = record_key.replace(prefix, '')
                if rec_user_part.isdigit():
                    numeric_suffixes.append(int(rec_user_part))
            next_number = 1
            if numeric_suffixes:
                next_number = max(numeric_suffixes) + 1
            if next_number < 100:
                user_part = f'{next_number:02d}'
            else:
                user_part = str(next_number)
        elif isinstance(user_input, int) or (isinstance(user_input, str) and user_input.isdigit()):
            number = int(user_input)
            if number < 100:
                user_part = f'{number:02d}'
            else:
                user_part = str(number)
        else:
            user_part = str(user_input)
        full_key = f'{prefix}{user_part}'
        return (full_key, prefix, user_part)

    def parse_pipeline_key(self, pipeline_key):
        """Parse a pipeline key into its component parts.

        Args:
            pipeline_key: The full pipeline key to parse

        Returns:
            dict: Contains profile_part, plugin_part, and user_part components
        """
        parts = pipeline_key.split('-', 2)
        if len(parts) < 3:
            return {'profile_part': parts[0] if len(parts) > 0 else '', 'plugin_part': parts[1] if len(parts) > 1 else '', 'user_part': ''}
        return {'profile_part': parts[0], 'plugin_part': parts[1], 'user_part': parts[2]}

    def update_datalist(self, datalist_id, options=None, clear=False):
        """Create a datalist with out-of-band swap for updating dropdown options.

        This helper method allows easy updates to datalist options using HTMX's
        out-of-band swap feature. It can either update with new options or clear all options.

        Args:
            datalist_id: The ID of the datalist to update
            options: List of option values to include, or None to clear
            clear: If True, force clear all options regardless of options parameter

        Returns:
            Datalist: A FastHTML Datalist object with out-of-band swap attribute
        """
        if clear or options is None:
            return Datalist(id=datalist_id, _hx_swap_oob='true')
        else:
            return Datalist(*[Option(value=opt) for opt in options], id=datalist_id, _hx_swap_oob='true')

    def run_all_cells(self, app_name, steps):
        """
        Rebuild the entire workflow UI from scratch.

        This is used after state changes that require the entire workflow to be regenerated,
        such as reverting to a previous step or jumping to a specific step. It's a core
        helper method commonly used in workflow methods like finalize, unfinalize, and
        handle_revert.

        The method creates a fresh container with all step placeholders, allowing
        the workflow to reload from the current state.

        Args:
            app_name: The name of the workflow app
            steps: List of Step namedtuples defining the workflow

        Returns:
            Div: Container with all steps ready to be displayed
        """
        placeholders = []
        for i, step in enumerate(steps):
            trigger = 'load' if i == 0 else None
            placeholders.append(Div(id=step.id, hx_get=f'/{app_name}/{step.id}', hx_trigger=trigger))
        return Div(*placeholders, id=f'{app_name}-container')

    def validate_step_input(self, value, step_show, custom_validator=None):
        """
        Validate step input with default and optional custom validation.

        This helper ensures consistent validation across all workflow steps:
        1. Basic validation: Ensures the input is not empty
        2. Custom validation: Applies workflow-specific validation logic if provided

        When validation fails, it returns an error component ready for direct
        display in the UI, helping maintain consistent error handling.

        Args:
            value: The user input value to validate
            step_show: Display name of the step (for error messages)
            custom_validator: Optional function(value) -> (is_valid, error_msg)

        Returns:
            tuple: (is_valid, error_message, P_component_or_None)
        """
        is_valid = True
        error_msg = ''
        if not value.strip():
            is_valid = False
            error_msg = f'{step_show} cannot be empty'
        if is_valid and custom_validator:
            custom_valid, custom_error = custom_validator(value)
            if not custom_valid:
                is_valid = False
                error_msg = custom_error
        if not is_valid:
            return (False, error_msg, P(error_msg, style=self.get_style('error')))
        return (True, '', None)

    async def set_step_data(self, pipeline_id, step_id, step_value, steps, clear_previous=True):
        """
        Update the state for a step and handle reverting.

        This core helper manages workflow state updates, ensuring consistent state 
        management across all workflows. It handles several important tasks:

        1. Clearing subsequent steps when a step is updated (optional)
        2. Storing the new step value in the correct format
        3. Removing any revert target flags that are no longer needed
        4. Persisting the updated state to storage

        Used by workflow step_xx_submit methods to maintain state after form submissions.

        Args:
            pipeline_id: The pipeline key
            step_id: The current step ID
            step_value: The value to store for this step
            steps: The steps list
            clear_previous: Whether to clear steps after this one

        Returns:
            str: The processed step value (for confirmation messages)
        """
        if clear_previous:
            await self.clear_steps_from(pipeline_id, step_id, steps)
        state = self.read_state(pipeline_id)
        step = next((s for s in steps if s.id == step_id), None)
        if step:
            state[step_id] = {step.done: step_value}
            if '_revert_target' in state:
                del state['_revert_target']
            self.write_state(pipeline_id, state)
        return step_value

    def check_finalize_needed(self, step_index, steps):
        """
        Check if we're on the final step before finalization.

        This helper determines if the workflow is ready for finalization by checking
        if the next step in the sequence is the "finalize" step. Workflows use this
        to decide whether to prompt the user to finalize after completing a step.

        Used in step_xx_submit methods to show appropriate finalization prompts
        after the user completes the last regular step in the workflow.

        Args:
            step_index: Index of current step in steps list
            steps: The steps list

        Returns:
            bool: True if the next step is the finalize step
        """
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        return next_step_id == 'finalize'

    def chain_reverter(self, step_id, step_index, steps, app_name, processed_val):
        """
        Create the standard navigation controls after a step submission.
        This helper generates a consistent UI pattern for step navigation that includes:
        1. A revert control showing the current step's value
        2. An HTMX-enabled div that EXPLICITLY triggers loading the next step using
           hx_trigger="load" (preferred over relying on HTMX event bubbling)
        Now also triggers a client-side event to scroll the main content panel.
        Args:
            step_id: The current step ID
            step_index: Index of current step in steps list
            steps: The steps list
            app_name: The workflow app name
            processed_val: The processed value to display
        Returns:
            HTMLResponse: A FastHTML Div component with revert control and next step trigger,
                          wrapped in an HTMLResponse to include HX-Trigger header.
        """
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        header_component = self.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: {processed_val}', steps=steps)
        next_step_trigger_div = Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load') if next_step_id else Div()
        content_to_swap = Div(header_component, next_step_trigger_div, id=step_id)
        response = HTMLResponse(to_xml(content_to_swap))
        response.headers['HX-Trigger-After-Settle'] = json.dumps({'scrollToLeftPanelBottom': True})
        return response

    async def handle_finalized_step(self, pipeline_id, step_id, steps, app_name, plugin_instance=None):
        """
        Handle the case when a step is submitted in finalized state.

        Args:
            pipeline_id: The pipeline key
            step_id: The current step ID
            steps: The steps list
            app_name: The workflow app name
            plugin_instance: Optional plugin instance (for accessing step_messages)

        Returns:
            Div: The rebuilt workflow UI
        """
        state = self.read_state(pipeline_id)
        state[step_id] = {'finalized': True}
        self.write_state(pipeline_id, state)
        step_messages = {}
        if plugin_instance and hasattr(plugin_instance, 'step_messages'):
            step_messages = plugin_instance.step_messages
        message = await self.get_state_message(pipeline_id, steps, step_messages)
        await self.stream(message, verbatim=True)
        return self.run_all_cells(app_name, steps)

    async def finalize_workflow(self, pipeline_id, state_update=None):
        """
        Finalize a workflow by marking it as complete and updating its state.

        Args:
            pipeline_id: The pipeline key
            state_update: Optional additional state to update (beyond finalized flag)

        Returns:
            dict: The updated state
        """
        state = self.read_state(pipeline_id)
        if 'finalize' not in state:
            state['finalize'] = {}
        state['finalize']['finalized'] = True
        state['updated'] = datetime.now().isoformat()
        if state_update:
            state.update(state_update)
        self.write_state(pipeline_id, state)
        return state

    async def unfinalize_workflow(self, pipeline_id):
        """
        Unfinalize a workflow by removing the finalized flag.

        Args:
            pipeline_id: The pipeline key

        Returns:
            dict: The updated state
        """
        state = self.read_state(pipeline_id)
        if 'finalize' in state:
            del state['finalize']
        state['updated'] = datetime.now().isoformat()
        self.write_state(pipeline_id, state)
        return state

async def chat_with_llm(MODEL: str, messages: list, base_app=None) -> AsyncGenerator[str, None]:
    url = 'http://localhost:11434/api/chat'
    payload = {'MODEL': MODEL, 'messages': messages, 'stream': True}
    accumulated_response = []
    table = Table(title='User Input')
    table.add_column('Role', style='cyan')
    table.add_column('Content', style='orange3')
    if messages:
        last_message = messages[-1]
        role = last_message.get('role', 'unknown')
        content = last_message.get('content', '')
        if isinstance(content, dict):
            content = json.dumps(content, indent=2, ensure_ascii=False)
        table.add_row(role, content)
    console.print(table)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    error_msg = f'Ollama server error: {error_text}'
                    accumulated_response.append(error_msg)
                    yield error_msg
                    return
                yield '\n'
                async for line in response.content:
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        if chunk.get('done', False):
                            print('\n', end='', flush=True)
                            final_response = ''.join(accumulated_response)
                            table = Table(title='Chat Response')
                            table.add_column('Accumulated Response')
                            table.add_row(final_response, style='green')
                            console.print(table)
                            break
                        if (content := chunk.get('message', {}).get('content', '')):
                            if content.startswith('\n') and accumulated_response and accumulated_response[-1].endswith('\n'):
                                content = '\n' + content.lstrip('\n')
                            else:
                                content = re.sub('\\n\\s*\\n\\s*', '\n\n', content)
                                content = re.sub('([.!?])\\n', '\\1 ', content)
                                content = re.sub('\\n ([^\\s])', '\\n\\1', content)
                            print(content, end='', flush=True)
                            accumulated_response.append(content)
                            yield content
                    except json.JSONDecodeError:
                        continue
    except aiohttp.ClientConnectorError as e:
        error_msg = 'Unable to connect to Ollama server. Please ensure Ollama is running.'
        accumulated_response.append(error_msg)
        yield error_msg
    except Exception as e:
        error_msg = f'Error: {str(e)}'
        accumulated_response.append(error_msg)
        yield error_msg

def get_current_profile_id():
    """Get the current profile ID, defaulting to the first profile if none is selected."""
    profile_id = db.get('last_profile_id')
    if profile_id is None:
        logger.debug('No last_profile_id found. Finding first available profile.')
        first_profiles = profiles(order_by='id', limit=1)
        if first_profiles:
            profile_id = first_profiles[0].id
            db['last_profile_id'] = profile_id
            logger.debug(f'Set default profile ID to {profile_id}')
        else:
            logger.warning('No profiles found in the database')
    return profile_id

def create_chat_scripts(sortable_selector='.sortable', ghost_class='blue-background-class'):
    """
    HYBRID JAVASCRIPT PATTERN: Creates static includes + Python-parameterized initialization

    This function demonstrates the hybrid pattern used throughout Pipulate:
    1. Static JavaScript files for caching and simple development
    2. Python-generated initialization scripts for dynamic configuration
    3. Global inclusion (not conditional) for consistent availability

    Returns:
        tuple: (static_js_script, dynamic_init_script, stylesheet)

    Pattern Benefits:
        - Static files can be cached by browser
        - Python can configure JavaScript behavior dynamically  
        - No template complexity or build steps required
        - Classic JavaScript development experience
    """
    python_generated_init_script = f"\n    document.addEventListener('DOMContentLoaded', (event) => {{\n        // HYBRID PATTERN: Call sortable-parameterized-init.js function with Python-generated config\n        if (window.initializeChatScripts) {{\n            window.initializeChatScripts({{\n                sortableSelector: '{sortable_selector}',\n                ghostClass: '{ghost_class}'\n            }});\n        }}\n    }});\n    "
    return (Script(src='/static/sortable-parameterized-init.js'), Script(python_generated_init_script), Link(rel='stylesheet', href='/static/styles.css'))

class BaseCrud:
    """
    CRUD base class for all Apps. The CRUD is DRY and the Workflows are WET!
    """

    def __init__(self, name, table, toggle_field=None, sort_field=None, sort_dict=None, pipulate_instance=None):
        self.name = name
        self.table = table
        self.toggle_field = toggle_field
        self.sort_field = sort_field
        self.item_name_field = 'name'
        self.sort_dict = sort_dict or {'id': 'id', sort_field: sort_field}
        self.pipulate_instance = pipulate_instance
        import asyncio
        import inspect

        def safe_send_message(message, verbatim=True):
            if not self.pipulate_instance:
                return
            try:
                stream_method = self.pipulate_instance.stream
                if inspect.iscoroutinefunction(stream_method):
                    return asyncio.create_task(stream_method(message, verbatim=verbatim, spaces_after=1))
                else:
                    return stream_method(message, verbatim=verbatim, spaces_after=1)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Error in send_message: {e}')
                return None
        self.send_message = safe_send_message

    def register_routes(self, rt):
        rt(f'/{self.name}', methods=['POST'])(self.insert_item)
        rt(f'/{self.name}/{{item_id}}', methods=['POST'])(self.update_item)
        rt(f'/{self.name}/delete/{{item_id}}', methods=['DELETE'])(self.delete_item)
        rt(f'/{self.name}/toggle/{{item_id}}', methods=['POST'])(self.toggle_item)
        rt(f'/{self.name}_sort', methods=['POST'])(self.sort_items)

    def get_action_url(self, action, item_id):
        return f'/{self.name}/{action}/{item_id}'

    def render_item(self, item):
        return Li(A('🗑', href='#', hx_swap='outerHTML', hx_delete=f'/task/delete/{item.id}', hx_target=f'#todo-{item.id}', _class='delete-icon', style=(
        'cursor: pointer; ',
        'display: inline'
    )), Input(type='checkbox', checked='1' if item.done else '0', hx_post=f'/task/toggle/{item.id}', hx_swap='outerHTML', hx_target=f'#todo-{item.id}'), A(item.name, href='#', _class='todo-title', style=(
        'color: inherit; ',
        'text-decoration: none'
    )), data_id=item.id, data_priority=item.priority, id=f'todo-{item.id}', cls='list-style-none')

    async def delete_item(self, request, item_id: int):
        try:
            item = self.table[item_id]
            item_name = getattr(item, self.item_name_field, 'Item')
            self.table.delete(item_id)
            logger.debug(f'Deleted item ID: {item_id}')
            action_details = f"The {self.name} item '{item_name}' was removed."
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            if self.name == 'profiles':
                response = HTMLResponse('')
                response.headers['HX-Trigger'] = json.dumps({'refreshProfileMenu': {}})
                return response
            return HTMLResponse('')
        except Exception as e:
            error_msg = f'Error deleting item: {str(e)}'
            logger.error(error_msg)
            action_details = f'An error occurred while deleting {self.name} (ID: {item_id}): {error_msg}'
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            return (str(e), 500)

    async def toggle_item(self, request, item_id: int):
        """Override the BaseCrud toggle_item to handle FastHTML objects properly"""
        try:
            item = self.table[item_id]
            current_status = getattr(item, self.toggle_field)
            new_status = not current_status
            setattr(item, self.toggle_field, new_status)
            updated_item = self.table.update(item)
            item_name = getattr(updated_item, self.item_name_field, 'Item')
            status_text = 'checked' if new_status else 'unchecked'
            action_details = f"The {self.name} item '{item_name}' is now {status_text}."
            self.send_message(action_details, verbatim=True)
            rendered_item_ft = self.render_item(updated_item)
            logger.debug(f'[DEBUG] Rendered item type (toggle_item): {type(rendered_item_ft)}')
            html_content = to_xml(rendered_item_ft)
            logger.debug(f'[DEBUG] HTML content (toggle_item): {html_content[:100]}...')
            response = HTMLResponse(str(html_content))
            if self.name == 'profiles':
                logger.debug(f"Adding HX-Trigger for refreshProfileMenu due to toggle_item on '{self.name}'")
                response.headers['HX-Trigger'] = json.dumps({'refreshProfileMenu': {}})
            elif self.name == 'roles':
                logger.debug(f'Adding HX-Trigger for refreshAppMenu due to role toggle_item (item_id: {item_id})')
                response.headers['HX-Trigger'] = json.dumps({'refreshAppMenu': {}})
            return response
        except Exception as e:
            error_msg = f'Error toggling {self.name} item {item_id}: {str(e)}'
            logger.error(error_msg)
            logger.exception(f'Detailed error toggling item {item_id} in {self.name}:')
            action_details = f'An error occurred while toggling {self.name} (ID: {item_id}): {error_msg}'
            self.send_message(action_details, verbatim=True)
            return HTMLResponse(f"<div style='color:red;'>Error: {error_msg}</div>", status_code=500)

    async def sort_items(self, request):
        """Override the BaseCrud sort_items to also refresh the profile menu"""
        try:
            logger.debug(f'Received request to sort {self.name}.')
            values = await request.form()
            items = json.loads(values.get('items', '[]'))
            logger.debug(f'Parsed items: {items}')
            
            # CRITICAL: Server-side validation to prevent meaningless sort requests
            current_order_changed = False
            for item in items:
                item_id = int(item['id'])
                new_priority = int(item['priority'])
                current_item = self.table[item_id]
                current_priority = getattr(current_item, self.sort_field)
                if current_priority != new_priority:
                    current_order_changed = True
                    break
            
            if not current_order_changed:
                logger.debug(f'🚫 SMART SORT BLOCKED: No actual changes detected for {self.name} - current order already matches requested order')
                return HTMLResponse('')  # Return empty response without triggers
            
            logger.debug(f'✅ SMART SORT ALLOWED: Actual changes detected for {self.name}')
            
            # Update all items and collect their names in new order
            updated_items = []
            for item in sorted(items, key=lambda x: int(x['priority'])):
                item_id = int(item['id'])
                priority = int(item['priority'])
                self.table.update(id=item_id, **{self.sort_field: priority})
                item_name = getattr(self.table[item_id], self.item_name_field, 'Item')
                updated_items.append(item_name)
            
            # Create a concise, human-friendly message showing the new order
            items_list = ', '.join(updated_items)
            action_details = f'Reordered {self.name}: {items_list}'
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            logger.debug(f'{self.name.capitalize()} order updated successfully')
            response = HTMLResponse('')
            triggers = {}
            if self.name == 'profiles':
                triggers['refreshProfileMenu'] = {}
            elif self.name == 'roles':
                triggers['refreshAppMenu'] = {}
            if triggers:
                response.headers['HX-Trigger'] = json.dumps(triggers)
            return response
        except json.JSONDecodeError as e:
            error_msg = f'Invalid data format: {str(e)}'
            logger.error(error_msg)
            action_details = f'An error occurred while sorting {self.name} items: {error_msg}'
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            return ('Invalid data format', 400)
        except Exception as e:
            error_msg = f'Error updating {self.name} order: {str(e)}'
            logger.error(error_msg)
            action_details = f'An error occurred while sorting {self.name} items: {error_msg}'
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            return (str(e), 500)

    async def insert_item(self, request):
        try:
            logger.debug(f'[DEBUG] Starting BaseCrud insert_item for {self.name}')
            form = await request.form()
            logger.debug(f'[DEBUG] Form data for {self.name}: {dict(form)}')
            new_item_data = self.prepare_insert_data(form)
            if not new_item_data:
                logger.debug(f'[DEBUG] No new_item_data for {self.name}, returning empty response for HTMX.')
                return HTMLResponse('')
            new_item = await self.create_item(**new_item_data)
            logger.debug(f'[DEBUG] Created new item for {self.name}: {new_item}')
            item_name = getattr(new_item, self.item_name_field, 'Item')
            action_details = f"A new {self.name} item '{item_name}' was added."
            self.send_message(action_details, verbatim=True)
            rendered_item_ft = self.render_item(new_item)
            logger.debug(f'[DEBUG] Rendered item type (insert_item for {self.name}): {type(rendered_item_ft)}')
            html_content = to_xml(rendered_item_ft)
            logger.debug(f'[DEBUG] Rendered item HTML (insert_item for {self.name}): {html_content[:150]}...')
            response = HTMLResponse(str(html_content))
            if self.name == 'profiles':
                logger.debug(f"Adding HX-Trigger for refreshProfileMenu due to insert_item on '{self.name}'")
                response.headers['HX-Trigger'] = json.dumps({'refreshProfileMenu': {}})
            return response
        except Exception as e:
            error_msg = f'Error inserting {self.name}: {str(e)}'
            logger.error(error_msg)
            logger.exception(f'Detailed error inserting item in {self.name}:')
            action_details = f'An error occurred while adding a new {self.name}: {error_msg}'
            self.send_message(action_details, verbatim=True)
            return HTMLResponse(f"<div style='color:red;'>Error inserting {self.name}: {error_msg}</div>", status_code=500)

    async def update_item(self, request, item_id: int):
        """Override the BaseCrud update_item to handle FastHTML objects properly"""
        try:
            form = await request.form()
            update_data = self.prepare_update_data(form)
            if not update_data:
                logger.debug(f'Update for {self.name} item {item_id} aborted by prepare_update_data.')
                return HTMLResponse('')
            item = self.table[item_id]
            before_state = {k: getattr(item, k, None) for k in update_data.keys()}
            for key, value in update_data.items():
                setattr(item, key, value)
            updated_item = self.table.update(item)
            after_state = {k: getattr(updated_item, k, None) for k in update_data.keys()}
            change_dict = {}
            changes_log_list = []
            for key in update_data.keys():
                if before_state.get(key) != after_state.get(key):
                    change_dict[key] = after_state.get(key)
                    changes_log_list.append(f"{key} changed from '{before_state.get(key)}' to '{after_state.get(key)}'")
            changes_str = '; '.join(changes_log_list)
            item_name_display = getattr(updated_item, self.item_name_field, 'Item')
            if changes_log_list:
                formatted_changes = self.pipulate_instance.fmt(changes_str) if hasattr(self.pipulate_instance, 'fmt') else changes_str
                action_details = f"The {self.name} item '{item_name_display}' was updated. Changes: {formatted_changes}"
                self.send_message(action_details, verbatim=True)
                logger.debug(f'Updated {self.name} item {item_id}. Changes: {changes_str}')
            else:
                logger.debug(f'No effective changes for {self.name} item {item_id}.')
            rendered_item_ft = self.render_item(updated_item)
            logger.debug(f'[DEBUG] Rendered item type (update_item): {type(rendered_item_ft)}')
            html_content = to_xml(rendered_item_ft)
            logger.debug(f'[DEBUG] HTML content (update_item): {html_content[:100]}...')
            response = HTMLResponse(str(html_content))
            if self.name == 'profiles' and 'name' in change_dict:
                logger.debug(f"Adding HX-Trigger for refreshProfileMenu due to update_item (name change) on '{self.name}'")
                response.headers['HX-Trigger'] = json.dumps({'refreshProfileMenu': {}})
            return response
        except Exception as e:
            error_msg = f'Error updating {self.name} item {item_id}: {str(e)}'
            logger.error(error_msg)
            logger.exception(f'Detailed error updating item {item_id} in {self.name}:')
            action_details = f'An error occurred while updating {self.name} (ID: {item_id}): {error_msg}'
            self.send_message(action_details, verbatim=True)
            return HTMLResponse(f"<div style='color:red;'>Error: {error_msg}</div>", status_code=500)

    async def create_item(self, **kwargs):
        try:
            logger.debug(f'Creating new {self.name} with data: {kwargs}')
            new_item = self.table.insert(kwargs)
            logger.debug(f'Created new {self.name}: {new_item}')
            return new_item
        except Exception as e:
            logger.error(f'Error creating {self.name}: {str(e)}')
            raise e

    def prepare_insert_data(self, form):
        raise NotImplementedError('Subclasses must implement prepare_insert_data')

    def prepare_update_data(self, form):
        raise NotImplementedError('Subclasses must implement prepare_update_data')
# Initialize FastApp with database and configuration
app, rt, (store, Store), (profiles, Profile), (pipeline, Pipeline) = fast_app(
    DB_FILENAME,
    exts='ws',
    live=True,
    default_hdrs=False,
    hdrs=(
        Meta(charset='utf-8'),
        Link(rel='stylesheet', href='/static/pico.css'),
        Link(rel='stylesheet', href='/static/prism.css'),
        Link(rel='stylesheet', href='/static/rich-table.css'),
        Script(src='/static/htmx.js'),
        Script(src='/static/fasthtml.js'),
        Script(src='/static/surreal.js'),
        Script(src='/static/script.js'),
        Script(src='/static/Sortable.js'),
        Script(src='/static/mermaid.min.js'),
        Script(src='/static/marked.min.js'),
        Script(src='/static/prism.js'),
        Script(src='/static/widget-scripts.js'),
        create_chat_scripts('.sortable'),
        Script(type='module')
    ),
    store={
        'key': str,
        'value': str,
        'pk': 'key'
    },
    profile={
        'id': int,
        'name': str,
        'real_name': str,
        'address': str,
        'code': str,
        'active': bool,
        'priority': int,
        'pk': 'id'
    },
    pipeline={
        'pkey': str,
        'app_name': str,
        'data': str,
        'created': str,
        'updated': str,
        'pk': 'pkey'
    }
)

class Chat:

    def __init__(self, app, id_suffix='', pipulate_instance=None):
        self.app = app
        self.id_suffix = id_suffix
        self.pipulate_instance = pipulate_instance
        self.logger = logger.bind(name=f'Chat{id_suffix}')
        self.active_websockets = set()
        self.startup_messages = []  # Store startup messages to replay when first client connects
        self.first_connection_handled = False  # Track if we've sent startup messages
        self.last_message = None
        self.last_message_time = 0
        self.app.websocket_route('/ws')(self.handle_websocket)
        self.logger.debug('Registered WebSocket route: /ws')

    async def broadcast(self, message: str):
        try:
            if isinstance(message, dict):
                if message.get('type') == 'htmx':
                    htmx_response = message
                    content = to_xml(htmx_response['content'])
                    formatted_response = f"""<div id="todo-{htmx_response.get('id')}" hx-swap-oob="beforeend:#todo-list">\n    {content}\n</div>"""
                    if self.active_websockets:
                        for ws in self.active_websockets:
                            await ws.send_text(formatted_response)
                    else:
                        # Store startup messages if no clients connected yet
                        self.startup_messages.append(formatted_response)
                    return

            # Send raw message without converting newlines to <br> tags
            formatted_msg = message if isinstance(message, str) else str(message)
            current_time = time.time()
            if formatted_msg == self.last_message and current_time - self.last_message_time < 2:
                self.logger.debug(f'Skipping duplicate message: {formatted_msg[:50]}...')
                return

            self.last_message = formatted_msg
            self.last_message_time = current_time
            if self.active_websockets:
                for ws in self.active_websockets:
                    await ws.send_text(formatted_msg)
            else:
                # Store startup messages if no clients connected yet
                self.startup_messages.append(formatted_msg)
        except Exception as e:
            self.logger.error(f'Error in broadcast: {e}')

    async def handle_chat_message(self, websocket: WebSocket, message: str):
        try:
            append_to_conversation(message, 'user')
            parts = message.split('|')
            msg = parts[0]
            verbatim = len(parts) > 1 and parts[1] == 'verbatim'
            raw_response = await pipulate.stream(msg, verbatim=verbatim)
            append_to_conversation(raw_response, 'assistant')
        except Exception as e:
            self.logger.error(f'Error in handle_chat_message: {e}')
            traceback.print_exc()

    def create_progress_card(self):
        return Card(Header('Chat Playground'), Form(Div(TextArea(id='chat-input', placeholder='Type your message here...', rows='3'), Button('Send', type='submit'), id='chat-form'), onsubmit='sendMessage(event)'), Div(id='chat-messages'), Script("\n                const ws = new WebSocket(\n                    `${window.location.protocol === 'https:' ? 'wss:' : 'ws'}://${window.location.host}/ws`\n                );\n                \n                ws.onmessage = function(event) {\n                    const messages = document.getElementById('chat-messages');\n                    messages.innerHTML += event.data + '<br>';\n                    messages.scrollTop = messages.scrollHeight;\n                };\n                \n                function sendMessage(event) {\n                    event.preventDefault();\n                    const input = document.getElementById('chat-input');\n                    const message = input.value;\n                    if (message.trim()) {\n                        ws.send(message);\n                        input.value = '';\n                    }\n                }\n            "))

    async def handle_websocket(self, websocket: WebSocket):
        try:
            await websocket.accept()
            self.active_websockets.add(websocket)
            self.logger.debug('Chat WebSocket connected')
            
            # Send any stored startup messages to the first connecting client
            if not self.first_connection_handled and self.startup_messages:
                self.logger.debug(f'Sending {len(self.startup_messages)} stored startup messages to first client')
                for stored_message in self.startup_messages:
                    await websocket.send_text(stored_message)
                self.first_connection_handled = True
                # Clear startup messages after sending to avoid re-sending to other clients
                self.startup_messages.clear()
            
            while True:
                message = await websocket.receive_text()
                self.logger.debug(f'Received message: {message}')
                await self.handle_chat_message(websocket, message)
        except WebSocketDisconnect:
            self.logger.info('WebSocket disconnected')
        except Exception as e:
            self.logger.error(f'Error in WebSocket connection: {str(e)}')
            self.logger.error(traceback.format_exc())
        finally:
            self.active_websockets.discard(websocket)
            self.logger.debug('WebSocket connection closed')

pipulate = Pipulate(pipeline)
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'], allow_credentials=True)
if not os.path.exists('plugins'):
    os.makedirs('plugins')
    logger.debug('Created plugins directory')
chat = Chat(app, id_suffix='', pipulate_instance=pipulate)

def build_endpoint_messages(endpoint):
    endpoint_messages = {}
    for plugin_name, plugin_instance in plugin_instances.items():
        if plugin_name not in endpoint_messages:
            if hasattr(plugin_instance, 'get_endpoint_message') and callable(getattr(plugin_instance, 'get_endpoint_message')):
                endpoint_messages[plugin_name] = plugin_instance.get_endpoint_message()
            elif hasattr(plugin_instance, 'ENDPOINT_MESSAGE'):
                endpoint_messages[plugin_name] = plugin_instance.ENDPOINT_MESSAGE
            else:
                class_name = plugin_instance.__class__.__name__
                endpoint_messages[plugin_name] = f'{class_name} app is where you manage your {plugin_name}.'
    
    # Special handling for empty endpoint (homepage) - check if roles plugin exists
    if not endpoint:
        roles_instance = plugin_instances.get('roles')
        if roles_instance:
            if hasattr(roles_instance, 'get_endpoint_message') and callable(getattr(roles_instance, 'get_endpoint_message')):
                endpoint_messages[''] = roles_instance.get_endpoint_message()
            elif hasattr(roles_instance, 'ENDPOINT_MESSAGE'):
                endpoint_messages[''] = roles_instance.ENDPOINT_MESSAGE
            else:
                class_name = roles_instance.__class__.__name__
                endpoint_messages[''] = f'{class_name} app is where you manage your roles.'
        else:
            endpoint_messages[''] = f'Welcome to {APP_NAME}. You are on the {HOME_MENU_ITEM.lower()} page. Select an app from the menu to get started.'
    
    if endpoint in plugin_instances:
        plugin_instance = plugin_instances[endpoint]
        logger.debug(f"Checking if {endpoint} has get_endpoint_message: {hasattr(plugin_instance, 'get_endpoint_message')}")
        logger.debug(f"Checking if get_endpoint_message is callable: {callable(getattr(plugin_instance, 'get_endpoint_message', None))}")
        logger.debug(f"Checking if {endpoint} has ENDPOINT_MESSAGE: {hasattr(plugin_instance, 'ENDPOINT_MESSAGE')}")
    return endpoint_messages.get(endpoint, None)

def build_endpoint_training(endpoint):
    endpoint_training = {}
    for workflow_name, workflow_instance in plugin_instances.items():
        if workflow_name not in endpoint_training:
            if hasattr(workflow_instance, 'TRAINING_PROMPT'):
                prompt = workflow_instance.TRAINING_PROMPT
                endpoint_training[workflow_name] = read_training(prompt)
            else:
                class_name = workflow_instance.__class__.__name__
                endpoint_training[workflow_name] = f'{class_name} app is where you manage your workflows.'
    
    # Special handling for empty endpoint (homepage) - check if roles plugin exists
    if not endpoint:
        roles_instance = plugin_instances.get('roles')
        if roles_instance:
            if hasattr(roles_instance, 'TRAINING_PROMPT'):
                prompt = roles_instance.TRAINING_PROMPT
                endpoint_training[''] = read_training(prompt)
            else:
                class_name = roles_instance.__class__.__name__
                endpoint_training[''] = f'{class_name} app is where you manage your workflows.'
        else:
            endpoint_training[''] = 'You were just switched to the home page.'
    
    append_to_conversation(endpoint_training.get(endpoint, ''), 'system')
    return
COLOR_MAP = {'key': 'yellow', 'value': 'white', 'error': 'red', 'warning': 'yellow', 'success': 'green', 'debug': 'blue'}

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
            log.error(f'Database operation {func.__name__} failed', e)
            raise
    return wrapper

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
            logger.error(f'Key not found: {key}')
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
db = DictLikeDB(store, Store)
logger.debug('Database wrapper initialized.')

def populate_initial_data():
    """Populate initial data in the database."""
    if TABLE_LIFECYCLE_LOGGING:
        logger.bind(lifecycle=True).info('POPULATE_INITIAL_DATA: Starting.')
        log_dynamic_table_state('profiles', lambda: profiles(), title_prefix='POPULATE_INITIAL_DATA: Profiles BEFORE')
        log_dictlike_db_to_lifecycle('db', db, title_prefix='POPULATE_INITIAL_DATA: db BEFORE')
    if not profiles():
        default_profile_name_for_db_entry = 'Default Profile'
        existing_default_list = list(profiles('name=?', (default_profile_name_for_db_entry,)))
        if not existing_default_list:
            default_profile_data = {'name': default_profile_name_for_db_entry, 'real_name': 'Default User', 'address': '', 'code': '', 'active': True, 'priority': 0}
            default_profile = profiles.insert(default_profile_data)
            logger.debug(f'Inserted default profile: {default_profile} with data {default_profile_data}')
            if default_profile and hasattr(default_profile, 'id'):
                db['last_profile_id'] = str(default_profile.id)
                logger.debug(f'Set last_profile_id to new default: {default_profile.id}')
            else:
                logger.error('Failed to retrieve ID from newly inserted default profile.')
        else:
            logger.debug(f"Default profile named '{default_profile_name_for_db_entry}' already exists. Skipping insertion.")
            if 'last_profile_id' not in db and existing_default_list:
                db['last_profile_id'] = str(existing_default_list[0].id)
                logger.debug(f'Set last_profile_id to existing default: {existing_default_list[0].id}')
    elif 'last_profile_id' not in db:
        first_profile_list = list(profiles(order_by='priority, id', limit=1))
        if first_profile_list:
            db['last_profile_id'] = str(first_profile_list[0].id)
            logger.debug(f'Set last_profile_id to first available profile: {first_profile_list[0].id}')
        else:
            logger.warning("No profiles exist and 'last_profile_id' was not set. This might occur if default creation failed or DB is empty.")
    if 'last_app_choice' not in db:
        db['last_app_choice'] = ''
        logger.debug('Initialized last_app_choice to empty string')
    if 'current_environment' not in db:
        db['current_environment'] = 'Development'
        logger.debug("Initialized current_environment to 'Development'")
    if 'profile_locked' not in db:
        db['profile_locked'] = '0'
        logger.debug("Initialized profile_locked to '0'")
    if TABLE_LIFECYCLE_LOGGING:
        log_dynamic_table_state('profiles', lambda: profiles(), title_prefix='POPULATE_INITIAL_DATA: Profiles AFTER')
        log_dictlike_db_to_lifecycle('db', db, title_prefix='POPULATE_INITIAL_DATA: db AFTER')
        logger.bind(lifecycle=True).info('POPULATE_INITIAL_DATA: Finished.')
populate_initial_data()

async def synchronize_roles_to_db():
    """Ensure all roles defined in plugin ROLES constants exist in the 'roles' database table."""
    logger.info('SYNC_ROLES: Starting role synchronization to database...')
    if not plugin_instances:
        logger.warning('SYNC_ROLES: plugin_instances is empty. Skipping role synchronization.')
        return
    if 'roles' not in plugin_instances:
        logger.warning("SYNC_ROLES: 'roles' plugin instance not found. Skipping role synchronization.")
        return
    roles_plugin_instance = plugin_instances.get('roles')
    if not roles_plugin_instance or not hasattr(roles_plugin_instance, 'table'):
        logger.error("SYNC_ROLES: Roles plugin instance or its 'table' attribute not found. Cannot synchronize.")
        return
    roles_table_handler = roles_plugin_instance.table
    logger.debug(f'SYNC_ROLES: Obtained roles_table_handler: {type(roles_table_handler)}')
    
    if TABLE_LIFECYCLE_LOGGING:
        logger.bind(lifecycle=True).info('SYNC_ROLES: Starting global role synchronization.')
        log_dynamic_table_state('roles', lambda: roles_table_handler(), title_prefix='SYNC_ROLES: Global BEFORE')
    logger.debug('SYNC_ROLES: Synchronizing roles globally')
    discovered_roles_set = set()
    for plugin_key, plugin_instance_obj in plugin_instances.items():
        plugin_module = sys.modules.get(plugin_instance_obj.__module__)
        roles_to_add_from_plugin = None
        if plugin_module and hasattr(plugin_module, 'ROLES') and isinstance(getattr(plugin_module, 'ROLES'), list):
            roles_to_add_from_plugin = getattr(plugin_module, 'ROLES')
            logger.debug(f"SYNC_ROLES: Plugin module '{plugin_instance_obj.__module__}' (key: {plugin_key}) has ROLES: {roles_to_add_from_plugin}")
        elif hasattr(plugin_instance_obj, 'ROLES') and isinstance(plugin_instance_obj.ROLES, list):
            roles_to_add_from_plugin = plugin_instance_obj.ROLES
            logger.debug(f"SYNC_ROLES: Plugin instance '{plugin_key}' has direct ROLES attribute: {roles_to_add_from_plugin}")
        if roles_to_add_from_plugin:
            for role_name in roles_to_add_from_plugin:
                if isinstance(role_name, str) and role_name.strip():
                    discovered_roles_set.add(role_name.strip())
    if not discovered_roles_set:
        logger.info('SYNC_ROLES: No roles were discovered in any plugin ROLES constants. Role table will not be modified.')
    else:
        logger.info(f'SYNC_ROLES: Total unique role names discovered across all plugins: {discovered_roles_set}')
    try:
        logger.debug("SYNC_ROLES: Attempting to fetch all existing roles globally")
        existing_role_objects = list(roles_table_handler())
        existing_role_names = {item.text for item in existing_role_objects}
        existing_role_done_states = {item.text: item.done for item in existing_role_objects}
        logger.debug(f'SYNC_ROLES: Found {len(existing_role_names)} existing role names in DB globally: {existing_role_names}')
        new_roles_added_count = 0
        for role_name in discovered_roles_set:
            if role_name not in existing_role_names:
                logger.debug(f"SYNC_ROLES: Role '{role_name}' not found globally. Preparing to add.")
                crud_customizer = roles_plugin_instance.app_instance
                simulated_form_for_crud = {crud_customizer.plugin.FORM_FIELD_NAME: role_name}
                data_for_insertion = crud_customizer.prepare_insert_data(simulated_form_for_crud)
                if data_for_insertion:
                    if role_name in DEFAULT_ACTIVE_ROLES:
                        data_for_insertion['done'] = True
                        logger.debug(f"SYNC_ROLES: Role '{role_name}' is a default active role. Setting done=True.")
                    elif 'done' not in data_for_insertion:
                        data_for_insertion['done'] = False
                    logger.debug(f"SYNC_ROLES: Data prepared by CrudCustomizer for '{role_name}': {data_for_insertion}")
                    await crud_customizer.create_item(**data_for_insertion)
                    logger.info(f"SYNC_ROLES: SUCCESS: Added role '{role_name}' to DB globally (Active: {data_for_insertion['done']}).")
                    new_roles_added_count += 1
                    existing_role_names.add(role_name)
                else:
                    logger.error(f"SYNC_ROLES: FAILED to prepare insert data for role '{role_name}' via CrudCustomizer.")
            else:
                if role_name in DEFAULT_ACTIVE_ROLES:
                    existing_role = next((r for r in existing_role_objects if r.text == role_name), None)
                    if existing_role and (not existing_role.done):
                        logger.debug(f"SYNC_ROLES: Setting default active role '{role_name}' to done=True while preserving other roles.")
                        existing_role.done = True
                        roles_table_handler.update(existing_role)
                logger.debug(f"SYNC_ROLES: Role '{role_name}' already exists globally. Status preserved.")
        if new_roles_added_count > 0:
            logger.info(f'SYNC_ROLES: Synchronization complete. Added {new_roles_added_count} new role(s) globally.')
        elif discovered_roles_set:
            logger.info(f'SYNC_ROLES: Synchronization complete. No new roles were added globally (all {len(discovered_roles_set)} discovered roles likely already exist).')
    except Exception as e:
        logger.error(f'SYNC_ROLES: Error during role synchronization database operations: {e}')
        if DEBUG_MODE:
            logger.exception('SYNC_ROLES: Detailed error during database operations:')
    if DEBUG_MODE or STATE_TABLES:
        logger.debug('SYNC_ROLES: Preparing to display final roles table globally')
        final_roles = list(roles_table_handler())
        roles_rich_table = Table(title='👥 Roles Table (Global Post-Sync)', show_header=True, header_style='bold magenta')
        roles_rich_table.add_column('ID', style='dim', justify='right')
        roles_rich_table.add_column('Text (Role Name)', style='cyan')
        roles_rich_table.add_column('Done (Active)', style='green', justify='center')
        roles_rich_table.add_column('Priority', style='yellow', justify='right')
        if not final_roles:
            logger.info('SYNC_ROLES: Roles table is EMPTY globally after synchronization.')
        else:
            logger.info(f'SYNC_ROLES: Final roles in DB globally ({len(final_roles)} total): {[r.text for r in final_roles]}')
        for role_item in final_roles:
            roles_rich_table.add_row(str(role_item.id), role_item.text, '✅' if role_item.done else '❌', str(role_item.priority))
        console.print('\n')
        console.print(roles_rich_table)
        console.print('\n')
        logger.info('SYNC_ROLES: Roles synchronization display complete globally.')
    if TABLE_LIFECYCLE_LOGGING:
        logger.bind(lifecycle=True).info('SYNC_ROLES: Finished global role synchronization.')
        log_dynamic_table_state('roles', lambda: roles_table_handler(), title_prefix='SYNC_ROLES: Global AFTER')

def discover_plugin_files():
    """Discover and import all Python files in the plugins directory.

    This function scans the 'plugins' directory and imports each .py file
    as a module. It skips files:
    - Starting with '__' (like __init__.py)
    - Starting with 'xx_' or 'XX_' (indicating experimental/in-progress plugins)
    - Containing parentheses (like "tasks (Copy).py")

    Returns:
        dict: Mapping of module names to imported module objects
    """
    plugin_modules = {}
    plugins_dir = os.path.join(os.path.dirname(__file__), 'plugins')
    logger.debug(f'Looking for plugins in: {plugins_dir}')
    if not os.path.isdir(plugins_dir):
        logger.warning(f'Plugins directory not found: {plugins_dir}')
        return plugin_modules

    def numeric_prefix_sort(filename):
        import re
        match = re.match('^(\\d+)_', filename)
        if match:
            return int(match.group(1))
        return float('inf')
    sorted_files = sorted(os.listdir(plugins_dir), key=numeric_prefix_sort)
    for filename in sorted_files:
        logger.debug(f'Checking file: {filename}')
        if '(' in filename or ')' in filename:
            logger.debug(f'Skipping file with parentheses: {filename}')
            continue
        if filename.lower().startswith('xx_'):
            logger.debug(f'Skipping experimental plugin: {filename}')
            continue
        if filename.endswith('.py') and (not filename.startswith('__')):
            base_name = filename[:-3]
            import re
            clean_name = re.sub('^\\d+_', '', base_name)
            original_name = base_name
            logger.debug(f'Module name: {clean_name} (from {original_name})')
            try:
                module = importlib.import_module(f'plugins.{original_name}')
                plugin_modules[clean_name] = module
                module._original_filename = original_name
                logger.debug(f'Successfully imported module: {clean_name} from {original_name}')
            except ImportError as e:
                logger.error(f'Error importing plugin module {original_name}: {str(e)}')
    logger.debug(f'Discovered plugin modules: {list(plugin_modules.keys())}')
    return plugin_modules

def find_plugin_classes(plugin_modules, discovered_modules):
    """Find all plugin classes in the given modules."""
    plugin_classes = []
    for module_or_name in plugin_modules:
        try:
            if isinstance(module_or_name, str):
                module_name = module_or_name
                original_name = getattr(discovered_modules[module_name], '_original_filename', module_name)
                module = importlib.import_module(f'plugins.{original_name}')
            else:
                module = module_or_name
                module_name = module.__name__.split('.')[-1]
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj):
                    logger.debug(f'Found member in {module_name}: {name}, type: {type(obj)}')
                    if hasattr(obj, 'landing'):
                        logger.debug(f'Class found: {module_name}.{name}')
                        if hasattr(obj, 'NAME') or hasattr(obj, 'APP_NAME') or hasattr(obj, 'DISPLAY_NAME'):
                            logger.debug(f'Found plugin: {module_name}.{name} (attribute-based, using NAME)')
                            plugin_classes.append((module_name, name, obj))
                        elif hasattr(obj, 'name') or hasattr(obj, 'app_name') or hasattr(obj, 'display_name'):
                            logger.debug(f'Found plugin: {module_name}.{name} (property-based)')
                            plugin_classes.append((module_name, name, obj))
        except Exception as e:
            logger.error(f'Error processing module {module_or_name}: {str(e)}')
            continue
    logger.debug(f'Discovered plugin classes: {plugin_classes}')
    return plugin_classes
plugin_instances = {}
discovered_modules = discover_plugin_files()
discovered_classes = find_plugin_classes(discovered_modules, discovered_modules)
friendly_names = {'': HOME_MENU_ITEM}
endpoint_training = {}

def get_display_name(workflow_name):
    instance = plugin_instances.get(workflow_name)
    if instance and hasattr(instance, 'DISPLAY_NAME'):
        return instance.DISPLAY_NAME
    return workflow_name.replace('_', ' ').title()

def get_endpoint_message(workflow_name):
    instance = plugin_instances.get(workflow_name)
    if instance and hasattr(instance, 'ENDPOINT_MESSAGE'):
        message = instance.ENDPOINT_MESSAGE
        if hasattr(pipulate, 'format_links_in_text'):
            try:
                import inspect
                if inspect.iscoroutinefunction(pipulate.format_links_in_text):
                    import asyncio
                    asyncio.create_task(pipulate.format_links_in_text(message))
                    return message
                else:
                    return pipulate.format_links_in_text(message)
            except Exception as e:
                logger.warning(f'Error formatting links in message: {e}')
                return message
        return message
    return f"{workflow_name.replace('_', ' ').title()} app is where you manage your workflows."
for module_name, class_name, workflow_class in discovered_classes:
    if module_name not in plugin_instances:
        try:
            original_name = getattr(discovered_modules[module_name], '_original_filename', module_name)
            module = importlib.import_module(f'plugins.{original_name}')
            workflow_class = getattr(module, class_name)
            if not hasattr(workflow_class, 'landing'):
                logger.warning(f"Plugin class {module_name}.{class_name} missing required 'landing' method - skipping")
                continue
            if not any((hasattr(workflow_class, attr) for attr in ['NAME', 'APP_NAME', 'DISPLAY_NAME', 'name', 'app_name', 'display_name'])):
                logger.warning(f'Plugin class {module_name}.{class_name} missing required name attributes - skipping')
                continue
            try:
                if module_name == 'profiles':
                    logger.info(f'Instantiating ProfilesPlugin with profiles_table_from_server')
                    instance = workflow_class(app=app, pipulate_instance=pipulate, pipeline_table=pipeline, db_key_value_store=db, profiles_table_from_server=profiles)
                else:
                    init_sig = inspect.signature(workflow_class.__init__)
                    args_to_pass = {}
                    param_mapping = {'app': app, 'pipulate': pipulate, 'pipulate_instance': pipulate, 'pipeline': pipeline, 'pipeline_table': pipeline, 'db': db, 'db_dictlike': db, 'db_key_value_store': db}
                    for param_name in init_sig.parameters:
                        if param_name == 'self':
                            continue
                        if param_name in param_mapping:
                            args_to_pass[param_name] = param_mapping[param_name]
                        elif param_name == 'profiles_table_from_server' and module_name == 'profiles':
                            args_to_pass[param_name] = profiles
                        elif param_name == 'config':
                            # Inject centralized configuration for plugins that need it
                            args_to_pass[param_name] = PIPULATE_CONFIG
                    logger.debug(f"Instantiating REGULAR plugin '{module_name}' with args: {args_to_pass.keys()}")
                    try:
                        instance = workflow_class(**args_to_pass)
                        if instance:
                            instance.name = module_name
                            plugin_instances[module_name] = instance
                            class_display_name_attr = getattr(workflow_class, 'DISPLAY_NAME', None)
                            instance_display_name_attr = getattr(instance, 'DISPLAY_NAME', None)
                            if isinstance(instance_display_name_attr, str) and instance_display_name_attr.strip():
                                logger.debug(f"Plugin instance '{module_name}' already has DISPLAY_NAME: '{instance.DISPLAY_NAME}'")
                            elif isinstance(class_display_name_attr, str) and class_display_name_attr.strip():
                                instance.DISPLAY_NAME = class_display_name_attr
                                logger.debug(f"Set instance.DISPLAY_NAME for '{module_name}' from class attribute: '{instance.DISPLAY_NAME}'")
                            else:
                                instance.DISPLAY_NAME = module_name.replace('_', ' ').title()
                                logger.debug(f"Set instance.DISPLAY_NAME for '{module_name}' to default based on module_name: '{instance.DISPLAY_NAME}'")
                    except TypeError as te_regular:
                        logger.error(f"TypeError for REGULAR plugin '{module_name}' with args {args_to_pass.keys()}: {te_regular}")
                        logger.error(f'Available args were: app={type(app)}, pipulate_instance/pipulate={type(pipulate)}, pipeline_table/pipeline={type(pipeline)}, db_key_value_store/db_dictlike={type(db)}')
                        logger.error(f'Plugin __init__ signature: {init_sig}')
                        raise
                logger.debug(f'Auto-registered workflow: {module_name}')
                if hasattr(instance, 'ROLES'):
                    logger.debug(f'Plugin {module_name} has roles: {instance.ROLES}')
                endpoint_message = get_endpoint_message(module_name)
                logger.debug(f'Endpoint message for {module_name}: {endpoint_message}')
            except Exception as e:
                logger.warning(f'Error instantiating workflow {module_name}.{class_name}: {str(e)}')
                continue
        except Exception as e:
            logger.warning(f'Issue with workflow {module_name}.{class_name} - continuing anyway')
            logger.debug(f'Error type: {e.__class__.__name__}')
            import inspect
            if inspect.iscoroutine(e):
                import asyncio
                asyncio.create_task(e)
    plugin_instances[module_name] = instance
    logger.debug(f'Auto-registered plugin: {module_name} (class: {workflow_class.__name__})')
    plugin_module_obj = sys.modules.get(instance.__module__)
    if plugin_module_obj:
        if hasattr(plugin_module_obj, 'ROLES') and isinstance(getattr(plugin_module_obj, 'ROLES'), list):
            logger.debug(f"Plugin '{module_name}' (from module: {instance.__module__}) declares module-level ROLES: {getattr(plugin_module_obj, 'ROLES')}")
        else:
            logger.debug(f"Plugin '{module_name}' (from module: {instance.__module__}) does NOT declare a module-level ROLES list.")
    else:
        logger.warning(f'Could not retrieve module object for {module_name} ({instance.__module__}) to check ROLES.')
    if hasattr(instance, 'ROLES') and isinstance(instance.ROLES, list):
        logger.debug(f"Plugin instance '{module_name}' (class: {instance.__class__.__name__}) has direct ROLES attribute: {instance.ROLES}")
    if hasattr(instance, 'register_routes'):
        instance.register_routes(rt)
for workflow_name, workflow_instance in plugin_instances.items():
    if workflow_name not in friendly_names:
        display_name = get_display_name(workflow_name)
        logger.debug(f'Setting friendly name for {workflow_name}: {display_name}')
        friendly_names[workflow_name] = display_name
    if workflow_name not in endpoint_training:
        endpoint_message = get_endpoint_message(workflow_name)
        logger.debug(f'Setting endpoint message for {workflow_name}')
        endpoint_training[workflow_name] = endpoint_message
base_menu_items = ['']
additional_menu_items = []

@app.on_event('startup')
async def startup_event():
    """Initialize the application on startup.

    This startup process prepares the Digital Workshop foundation:
    - Synchronizes role-based access controls
    - Initializes the pipeline and profile management systems
    - Sets up the local-first data architecture
    - Prepares the environment for creative exploration workflows

    The startup sequence ensures all components are ready to support
    the full spectrum of content curation, archive surfing, and
    progressive distillation workflows that define the Pipulate vision.
    """
    logger.bind(lifecycle=True).info('SERVER STARTUP_EVENT: Pre synchronize_roles_to_db.')
    await synchronize_roles_to_db()
    logger.bind(lifecycle=True).info('SERVER STARTUP_EVENT: Post synchronize_roles_to_db. Final startup states:')
    log_dictlike_db_to_lifecycle('db', db, title_prefix='STARTUP FINAL')
    log_dynamic_table_state('profiles', lambda: profiles(), title_prefix='STARTUP FINAL')
    log_dynamic_table_state('pipeline', lambda: pipeline(), title_prefix='STARTUP FINAL')

    
    # Send environment mode message after a short delay to let UI initialize
    asyncio.create_task(send_startup_environment_message())
ordered_plugins = []
for module_name, class_name, workflow_class in discovered_classes:
    if module_name not in ordered_plugins and module_name in plugin_instances:
        ordered_plugins.append(module_name)
MENU_ITEMS = base_menu_items + ordered_plugins + additional_menu_items
logger.debug(f'Dynamic MENU_ITEMS: {MENU_ITEMS}')

def get_profile_name():
    profile_id = get_current_profile_id()
    logger.debug(f'Retrieving profile name for ID: {profile_id}')
    try:
        profile = profiles.get(profile_id)
        if profile:
            logger.debug(f'Found profile: {profile.name}')
            return profile.name
    except NotFoundError:
        logger.warning(f'No profile found for ID: {profile_id}')
        return 'Unknown Profile'

async def home(request):
    """Handle the main home route request.

    Args:
        request: The incoming request object

    Returns:
        tuple: (Title, Main) containing the page title and main content
    """
    path = request.url.path.strip('/')
    logger.debug(f'Received request for path: {path}')
    menux = normalize_menu_path(path)
    logger.debug(f'Selected explore item: {menux}')
    db['last_app_choice'] = menux
    db['last_visited_url'] = request.url.path
    current_profile_id = get_current_profile_id()
    menux = db.get('last_app_choice', 'App')
    response = await create_outer_container(current_profile_id, menux, request)
    last_profile_name = get_profile_name()
    page_title = f'{APP_NAME} - {title_name(last_profile_name)} - {(endpoint_name(menux) if menux else HOME_MENU_ITEM)}'
    
    # Backup mechanism: send endpoint message if not yet sent for this session
    session_key = f'endpoint_message_sent_{menux}'
    if session_key not in db:
        try:
            # Add training to conversation history
            build_endpoint_training(menux)
            
            # Send endpoint message
            endpoint_message = build_endpoint_messages(menux)
            if endpoint_message:
                asyncio.create_task(send_delayed_endpoint_message(endpoint_message, session_key))
        except Exception as e:
            logger.error(f'Error sending backup endpoint message: {e}')
    
    logger.debug('Returning response for main GET request.')
    return (Title(page_title), Main(response))

def create_nav_group():
    """Create the navigation group containing the main nav menu and refresh listeners.

    Returns:
        Group: A container with the navigation menu and HTMX refresh listeners.
    """
    profiles_plugin_inst = plugin_instances.get('profiles')
    if not profiles_plugin_inst:
        logger.error("Could not get 'profiles' plugin instance for nav group creation")
        return Group(Div(H1('Error: Profiles plugin not found', cls='text-invalid'), cls='nav-error'), id='nav-group')
    nav = create_nav_menu()
    refresh_listener = Div(id='profile-menu-refresh-listener', hx_get='/refresh-profile-menu', hx_trigger='refreshProfileMenu from:body', hx_target='#profile-dropdown-menu', hx_swap='outerHTML', cls='hidden')
    app_menu_refresh_listener = Div(id='app-menu-refresh-listener', hx_get='/refresh-app-menu', hx_trigger='refreshAppMenu from:body', hx_target='#app-dropdown-menu', hx_swap='outerHTML', cls='hidden')
    return Group(nav, refresh_listener, app_menu_refresh_listener, id='nav-group')

def create_env_menu():
    """Create environment selection dropdown menu."""
    current_env = get_current_environment()
    display_env = 'DEV' if current_env == 'Development' else 'Prod'
    env_summary_style = 'white-space: nowrap; display: inline-block; min-width: max-content;'
    if current_env == 'Development':
        env_summary_style += ' color: #f77; font-weight: bold;'
    menu_item_style = 'text-align: left; {pipulate.MENU_ITEM_PADDING} display: flex; border-radius: var(--pico-border-radius);'
    radio_style = 'min-width: 1rem; margin-right: 0.5rem;'
    menu_items = []
    is_dev = current_env == 'Development'
    dev_item = Li(Label(Input(type='radio', name='env_radio_select', value='Development', checked=is_dev, hx_post='/switch_environment', hx_vals='{"environment": "Development"}', hx_target='#dev-env-item', hx_swap='outerHTML', style=radio_style), 'DEV', style=menu_item_style, onmouseover="this.style.backgroundColor='var(--pico-primary-hover-background)';", onmouseout=f"this.style.backgroundColor='{('var(--pico-primary-focus)' if is_dev else 'transparent')}';", id='dev-env-item'))
    menu_items.append(dev_item)
    is_prod = current_env == 'Production'
    prod_item = Li(Label(Input(type='radio', name='env_radio_select', value='Production', checked=is_prod, hx_post='/switch_environment', hx_vals='{"environment": "Production"}', hx_target='#prod-env-item', hx_swap='outerHTML', style=radio_style), 'Prod', style=menu_item_style, onmouseover="this.style.backgroundColor='var(--pico-primary-hover-background)';", onmouseout=f"this.style.backgroundColor='{('var(--pico-primary-focus)' if is_prod else 'transparent')}';", id='prod-env-item'))
    menu_items.append(prod_item)
    dropdown_style = 'padding-left: 0; padding-top: 0.25rem; padding-bottom: 0.25rem; width: 8rem; max-height: 75vh; overflow-y: auto;'
    return Details(Summary(display_env, style=env_summary_style, id='env-id'), Ul(*menu_items, cls='dropdown-menu', style=dropdown_style), cls='dropdown', id='env-dropdown-menu')

def create_nav_menu():
    logger.debug('Creating navigation menu.')
    menux = db.get('last_app_choice', 'App')
    selected_profile_id = get_current_profile_id()
    selected_profile_name = get_profile_name()
    profiles_plugin_inst = plugin_instances.get('profiles')
    if not profiles_plugin_inst:
        logger.error("Could not get 'profiles' plugin instance for menu creation")
        return Div(H1('Error: Profiles plugin not found', cls='text-invalid'), cls='nav-breadcrumb')
    link_style = 'text-decoration: underline; color: inherit; transition: color 0.2s; white-space: nowrap;'
    hover_style = "this.style.color='#4dabf7'; this.style.textDecoration='underline';"
    normal_style = "this.style.color='inherit'; this.style.textDecoration='underline';"
    separator_style = 'padding: 0 0.3rem;'
    home_link = A(APP_NAME, href='/redirect/', title=f'Go to {HOME_MENU_ITEM.lower()}', style=link_style, onmouseover=hover_style, onmouseout=normal_style)
    separator = Span(' / ', style=separator_style)
    profile_text = Span(title_name(selected_profile_name))
    endpoint_text = Span(endpoint_name(menux) if menux else HOME_MENU_ITEM)
    breadcrumb = H1(home_link, separator, profile_text, separator, endpoint_text)
    menus = Div(create_profile_menu(selected_profile_id, selected_profile_name), create_app_menu(menux), create_env_menu(), cls='nav-menu-group')
    nav = Div(breadcrumb, menus, cls='nav-breadcrumb')
    logger.debug('Navigation menu created.')
    return nav

def create_profile_menu(selected_profile_id, selected_profile_name):
    """Create the profile dropdown menu."""
    menu_items = []
    profile_locked = db.get('profile_locked', '0') == '1'
    menu_items.append(Li(Label(Input(type='checkbox', name='profile_lock_switch', role='switch', checked=profile_locked, hx_post='/toggle_profile_lock', hx_target='body', hx_swap='outerHTML'), 'Lock Profile'), style=(
        'align-items: center; ',
        'display: flex; ',
        'padding: 0.5rem 1rem'
    )))
    menu_items.append(Li(Hr(style='margin: 0'), cls='block'))
    profiles_plugin_inst = plugin_instances.get('profiles')
    if not profiles_plugin_inst:
        logger.error("Could not get 'profiles' plugin instance for profile menu creation")
        menu_items.append(Li(A('Error: Profiles link broken', href='#', cls='dropdown-item text-invalid')))
    else:
        plugin_display_name = getattr(profiles_plugin_inst, 'DISPLAY_NAME', 'Profiles')
        if not profile_locked:
            menu_items.append(Li(A(f'Edit {plugin_display_name}', href=f'/redirect/{profiles_plugin_inst.name}', cls='dropdown-item menu-item-header'), cls='block'))
    active_profiles_list = []
    if profiles:
        if profile_locked:
            if selected_profile_id:
                try:
                    selected_profile_obj = profiles.get(int(selected_profile_id))
                    if selected_profile_obj:
                        active_profiles_list = [selected_profile_obj]
                except Exception as e:
                    logger.error(f'Error fetching locked profile {selected_profile_id}: {e}')
        else:
            active_profiles_list = list(profiles(where='active = ?', where_args=(True,), order_by='priority'))
    else:
        logger.error("Global 'profiles' table object not available for create_profile_menu.")
    for profile_item in active_profiles_list:
        is_selected = str(profile_item.id) == str(selected_profile_id)
        item_style = 'background-color: var(--pico-primary-focus);' if is_selected else ''
        radio_input = Input(type='radio', name='profile_radio_select', value=str(profile_item.id), checked=is_selected, hx_post='/select_profile', hx_vals=json.dumps({'profile_id': str(profile_item.id)}), hx_target='body', hx_swap='outerHTML')
        profile_label = Label(radio_input, profile_item.name)
        hover_style = "this.style.backgroundColor='var(--pico-primary-hover-background)';"
        default_bg = 'var(--pico-primary-focus)' if is_selected else 'transparent'
        mouseout_style = f"this.style.backgroundColor='{default_bg}';"
        menu_items.append(Li(profile_label, style=f'text-align: left; {pipulate.MENU_ITEM_PADDING} {item_style} display: flex; border-radius: var(--pico-border-radius);', onmouseover=hover_style, onmouseout=mouseout_style))
    summary_profile_name_to_display = selected_profile_name
    if not summary_profile_name_to_display and selected_profile_id:
        try:
            profile_obj = profiles.get(int(selected_profile_id))
            if profile_obj:
                summary_profile_name_to_display = profile_obj.name
        except Exception:
            pass
    summary_profile_name_to_display = summary_profile_name_to_display or 'Select'
    return Details(Summary('👤 PROFILE', cls='inline-nowrap', id='profile-id'), Ul(*menu_items, style=(
        'min-width: max-content; ',
        'padding-left: 0'
    ), cls='dropdown-menu'), cls='dropdown', id='profile-dropdown-menu')

def normalize_menu_path(path):
    """Convert empty paths to empty string and return the path otherwise."""
    return '' if path == '' else path

def generate_menu_style():
    """Generate consistent menu styling for dropdown menus."""
    return 'white-space: nowrap; display: inline-block; min-width: max-content; background-color: var(--pico-background-color); border: 1px solid var(--pico-muted-border-color); border-radius: 16px; padding: 0.5rem 1rem; cursor: pointer; transition: background-color 0.2s;'

def create_app_menu(menux):
    """Create the App dropdown menu with hierarchical role-based sorting."""
    logger.debug(f"Creating App menu. Currently selected app (menux): '{menux}'")
    active_role_names = get_active_roles()
    menu_items = create_home_menu_item(menux)
    role_priorities = get_role_priorities()
    plugins_by_role = group_plugins_by_role(active_role_names)
    for role_name, role_priority in sorted(role_priorities.items(), key=lambda x: x[1]):
        if role_name in active_role_names:
            role_plugins = plugins_by_role.get(role_name, [])
            role_plugins.sort(key=lambda x: get_plugin_numeric_prefix(x))
            for plugin_key in role_plugins:
                menu_item = create_plugin_menu_item(plugin_key=plugin_key, menux=menux, active_role_names=active_role_names)
                if menu_item:
                    menu_items.append(menu_item)
    return create_menu_container(menu_items)

def get_active_roles():
    """Get set of active role names from roles plugin."""
    active_role_names = set()
    roles_plugin = plugin_instances.get('roles')
    if roles_plugin and hasattr(roles_plugin, 'table'):
        try:
            active_role_records = list(roles_plugin.table(where='done = ?', where_args=(True,)))
            active_role_names = {record.text for record in active_role_records}
            logger.debug(f'Globally active roles: {active_role_names}')
        except Exception as e:
            logger.error(f'Error fetching globally active roles: {e}')
    else:
        logger.warning("Could not fetch active roles: 'roles' plugin or its table not found.")
    return active_role_names

def get_role_priorities():
    """Get role priorities from the roles plugin for hierarchical sorting."""
    role_priorities = {}
    roles_plugin = plugin_instances.get('roles')
    if roles_plugin and hasattr(roles_plugin, 'table'):
        try:
            role_records = list(roles_plugin.table())
            role_priorities = {record.text: record.priority for record in role_records}
            logger.debug(f'Role priorities globally: {role_priorities}')
        except Exception as e:
            logger.error(f'Error fetching role priorities: {e}')
    else:
        logger.warning("Could not fetch role priorities: 'roles' plugin or its table not found.")
    return role_priorities

def group_plugins_by_role(active_role_names):
    """Group plugins by their primary role for hierarchical menu organization."""
    plugins_by_role = {}
    for plugin_key in ordered_plugins:
        instance = plugin_instances.get(plugin_key)
        if not instance:
            continue
        if plugin_key in ['profiles', 'roles']:
            continue
        if not should_include_plugin(instance, active_role_names):
            continue
        primary_role = get_plugin_primary_role(instance)
        if primary_role:
            role_name = primary_role.replace('-', ' ').title()
            if role_name not in plugins_by_role:
                plugins_by_role[role_name] = []
            plugins_by_role[role_name].append(plugin_key)
    logger.debug(f'Plugins grouped by role: {plugins_by_role}')
    return plugins_by_role

def get_plugin_numeric_prefix(plugin_key):
    """Extract numeric prefix from plugin filename for sorting within role groups."""
    if plugin_key in discovered_modules:
        original_filename = getattr(discovered_modules[plugin_key], '_original_filename', plugin_key)
        match = re.match('^(\\d+)_', original_filename)
        if match:
            return int(match.group(1))
    return 9999

def create_home_menu_item(menux):
    """Create menu items list starting with Home option."""
    menu_items = []
    is_home_selected = menux == ''
    home_radio = Input(type='radio', name='app_radio_select', value='', checked=is_home_selected, hx_post='/redirect/', hx_target='body', hx_swap='outerHTML')
    home_css_classes = 'dropdown-item'
    home_label = Label(home_radio, HOME_MENU_ITEM, cls=home_css_classes, style='background-color: var(--pico-primary-focus)' if is_home_selected else '')
    menu_items.append(Li(home_label))
    return menu_items

def get_plugin_primary_role(instance):
    """Get the primary role for a plugin for UI styling purposes.
    
    Uses a simple 80/20 approach: if plugin has multiple roles, 
    we take the first one as primary. This creates a clean win/loss
    scenario for coloring without complex blending logic.
    
    Returns lowercase role name with spaces replaced by hyphens for CSS classes.
    """
    plugin_module_path = instance.__module__
    plugin_module = sys.modules.get(plugin_module_path)
    plugin_defined_roles = getattr(plugin_module, 'ROLES', []) if plugin_module else []
    if not plugin_defined_roles:
        return None
    primary_role = plugin_defined_roles[0]
    css_role = primary_role.lower().replace(' ', '-')
    logger.debug(f"Plugin '{instance.__class__.__name__}' primary role: '{primary_role}' -> CSS class: 'menu-role-{css_role}'")
    return css_role

def create_plugin_menu_item(plugin_key, menux, active_role_names):
    """Create menu item for a plugin if it should be included based on roles."""
    instance = plugin_instances.get(plugin_key)
    if not instance:
        logger.warning(f"Instance for plugin_key '{plugin_key}' not found. Skipping.")
        return None
    if plugin_key in ['profiles', 'roles']:
        return None

    if not should_include_plugin(instance, active_role_names):
        return None
    display_name = getattr(instance, 'DISPLAY_NAME', title_name(plugin_key))
    is_selected = menux == plugin_key
    redirect_url = f"/redirect/{(plugin_key if plugin_key else '')}"
    primary_role = get_plugin_primary_role(instance)
    role_class = f'menu-role-{primary_role}' if primary_role else ''
    css_classes = f'dropdown-item {role_class}'.strip()
    radio_input = Input(type='radio', name='app_radio_select', value=plugin_key, checked=is_selected, hx_post=redirect_url, hx_target='body', hx_swap='outerHTML')
    return Li(Label(radio_input, display_name, cls=css_classes, style='background-color: var(--pico-primary-focus)' if is_selected else ''))

def should_include_plugin(instance, active_role_names):
    """Determine if plugin should be included based on its roles."""
    plugin_module_path = instance.__module__
    plugin_module = sys.modules.get(plugin_module_path)
    plugin_defined_roles = getattr(plugin_module, 'ROLES', []) if plugin_module else []
    is_core_plugin = 'Core' in plugin_defined_roles
    has_matching_active_role = any((p_role in active_role_names for p_role in plugin_defined_roles))
    should_include = is_core_plugin or has_matching_active_role
    logger.debug(f"Plugin '{instance.__class__.__name__}' (Roles: {plugin_defined_roles}). Core: {is_core_plugin}, Active Roles: {active_role_names}, Match: {has_matching_active_role}, Include: {should_include}")
    return should_include

def create_menu_container(menu_items):
    """Create the final menu container with all items."""
    return Details(Summary('⚡ APP', cls='inline-nowrap', id='app-id'), Ul(*menu_items, cls='dropdown-menu'), cls='dropdown', id='app-dropdown-menu')

def get_dynamic_role_css():
    """Generate dynamic role CSS from centralized PIPULATE_CONFIG - single source of truth."""
    try:
        role_colors = PIPULATE_CONFIG.get('ROLE_COLORS', {})
        if not role_colors:
            return ""
        
        css_rules = []
        
        # Generate main role CSS with role-specific hover/focus states
        for role_class, colors in role_colors.items():
            # Extract RGB values from border color for darker hover state
            border_color = colors['border']
            if border_color.startswith('#'):
                # Convert hex to RGB for hover/focus calculations
                hex_color = border_color[1:]
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                
                # Create hover state with 20% background opacity
                hover_bg = f"rgba({r}, {g}, {b}, 0.2)"
                
                # Create focus state with 25% background opacity 
                focus_bg = f"rgba({r}, {g}, {b}, 0.25)"
                
                # Create SELECTED state with 35% background opacity (more prominent)
                selected_bg = f"rgba({r}, {g}, {b}, 0.35)"
                
                css_rules.append(f"""
.{role_class} {{
    background-color: {colors['background']} !important;
    border-left: 3px solid {colors['border']} !important;
}}

.{role_class}:hover {{
    background-color: {hover_bg} !important;
}}

.{role_class}:focus,
.{role_class}:active {{
    background-color: {focus_bg} !important;
}}

.{role_class}[style*="background-color: var(--pico-primary-focus)"] {{
    background-color: {selected_bg} !important;
}}""")
        
        # Generate light theme adjustments with matching hover states
        for role_class, colors in role_colors.items():
            if role_class != 'menu-role-core':  # Core doesn't need light theme adjustment
                border_color = colors['border']
                if border_color.startswith('#'):
                    hex_color = border_color[1:]
                    r = int(hex_color[0:2], 16)
                    g = int(hex_color[2:4], 16)
                    b = int(hex_color[4:6], 16)
                    
                    # Lighter hover for light theme (15% opacity)
                    light_hover_bg = f"rgba({r}, {g}, {b}, 0.15)"
                    light_focus_bg = f"rgba({r}, {g}, {b}, 0.2)"
                    light_selected_bg = f"rgba({r}, {g}, {b}, 0.3)"
                    
                    css_rules.append(f"""
[data-theme="light"] .{role_class} {{
    background-color: {colors['background_light']} !important;
}}

[data-theme="light"] .{role_class}:hover {{
    background-color: {light_hover_bg} !important;
}}

[data-theme="light"] .{role_class}:focus,
[data-theme="light"] .{role_class}:active {{
    background-color: {light_focus_bg} !important;
}}

[data-theme="light"] .{role_class}[style*="background-color: var(--pico-primary-focus)"] {{
    background-color: {light_selected_bg} !important;
}}""")
        
        return '\n'.join(css_rules)
        
    except Exception as e:
        logger.error(f"Error generating dynamic role CSS: {e}")
        return ""  # Fallback to static CSS if dynamic generation fails

async def create_outer_container(current_profile_id, menux, request):
    profiles_plugin_inst = plugin_instances.get('profiles')
    if not profiles_plugin_inst:
        logger.error("Could not get 'profiles' plugin instance for container creation")
        return Container(H1('Error: Profiles plugin not found', cls='text-invalid'))
    
    # Inject dynamic role CSS - single source of truth
    dynamic_css = get_dynamic_role_css()
    nav_group = create_nav_group()
    
    return Container(
        Style(dynamic_css),  # Dynamic CSS injection
        nav_group, 
        Grid(await create_grid_left(menux, request), create_chat_interface(), cls='main-grid'), 
        create_poke_button()
    )




def get_workflow_instance(workflow_name):
    """
    Get a workflow instance from the plugin_instances dictionary.

    Args:
        workflow_name: The name of the workflow to retrieve

    Returns:
        The workflow instance if found, None otherwise
    """
    return plugin_instances.get(workflow_name)

async def create_grid_left(menux, request, render_items=None):
    content_to_render = None
    profiles_plugin_key = 'profiles'
    if menux:
        if menux == profiles_plugin_key:
            profiles_instance = plugin_instances.get(profiles_plugin_key)
            if profiles_instance:
                content_to_render = await profiles_instance.landing(request)
            else:
                logger.error(f"Plugin '{profiles_plugin_key}' not found in plugin_instances for create_grid_left.")
                content_to_render = Card(H3('Error'), P(f"Plugin '{profiles_plugin_key}' not found."))

        else:
            workflow_instance = get_workflow_instance(menux)
            if workflow_instance:
                if hasattr(workflow_instance, 'ROLES') and DEBUG_MODE:
                    logger.debug(f'Selected plugin {menux} has roles: {workflow_instance.ROLES}')
                content_to_render = await workflow_instance.landing(request)
    else:
        # New homepage: serve the Roles plugin
        roles_instance = plugin_instances.get('roles')
        if roles_instance:
            content_to_render = await roles_instance.landing(request)
        else:
            logger.error("Roles plugin not found for homepage. Showing welcome message.")
            content_to_render = Card(H3('Welcome'), P('Roles plugin not found. Please check your plugin configuration.'))
    if content_to_render is None:
        content_to_render = Card(H3('Welcome'), P('Select an option from the menu to begin.'), style='min-height: 400px')
    scroll_to_top = Div(A('↑ Scroll To Top', href='javascript:void(0)', onclick='\n            const container = document.querySelector(".main-grid > div:first-child");\n            container.scrollTo({top: 0, behavior: "smooth"});\n          ', style='text-decoration: none'), style=(
        'border-top: 1px solid var(--pico-muted-border-color); ',
        'display: none; ',
        'margin-top: 20px; ',
        'padding: 10px; ',
        'text-align: center'
    ), id='scroll-to-top-link')
    scroll_check_script = Script("\n        function checkScrollHeight() {\n            const container = document.querySelector('.main-grid > div:first-child');\n            const scrollLink = document.getElementById('scroll-to-top-link');\n            if (container && scrollLink) {\n                const isScrollable = container.scrollHeight > container.clientHeight;\n                scrollLink.style.display = isScrollable ? 'block' : 'none';\n            }\n        }\n        // Check on load and when content changes\n        window.addEventListener('load', checkScrollHeight);\n        const observer = new MutationObserver(checkScrollHeight);\n        const container = document.querySelector('.main-grid > div:first-child');\n        if (container) {\n            observer.observe(container, { childList: true, subtree: true });\n        }\n    ")
    return Div(content_to_render, scroll_to_top, scroll_check_script, id='grid-left-content')

def create_chat_interface(autofocus=False):
    """Creates the chat interface component with message list and input form.

    Args:
        autofocus (bool): Whether to autofocus the chat input field

    Returns:
        Div: The chat interface container with all components
    """
    msg_list_height = 'height: calc(70vh - 200px);'
    temp_message = None
    if 'temp_message' in db:
        temp_message = db['temp_message']
        del db['temp_message']
    init_script = f'\n    // Set global variables for the external script\n    window.PIPULATE_CONFIG = {{\n        tempMessage: {json.dumps(temp_message)}\n    }};\n    '
    return Div(Card(H2(f'{APP_NAME} Chatbot'), Div(id='msg-list', cls='overflow-auto', style=msg_list_height), Form(mk_chat_input_group(value='', autofocus=autofocus), onsubmit='sendSidebarMessage(event)'), Script(init_script), Script(src='/static/websocket-global-config.js')), id='chat-interface', style='overflow: hidden')

def mk_chat_input_group(disabled=False, value='', autofocus=True):
    """Creates a chat input group with text input and send button.

    Args:
        disabled (bool): Whether the input and button should be disabled
        value (str): Initial value for the text input
        autofocus (bool): Whether to autofocus the text input

    Returns:
        Group: Container with input and send button
    """
    return Group(Input(id='msg', name='msg', placeholder='Chat...', value=value, disabled=disabled, autofocus='autofocus' if autofocus else None), Button('Send', type='submit', id='send-btn', disabled=disabled), id='input-group', style='padding-right: 1vw')

def create_poke_button():
    button_style = 'position: fixed; bottom: 20px; right: 20px; width: 50px; height: 50px; border-radius: 50%; font-size: 24px; display: flex; align-items: center; justify-content: center; z-index: 1000;'
    poke_button = Button('🤖', cls='contrast outline', style=button_style, hx_get='/poke-flyout', hx_target='#flyout-panel', hx_trigger='mouseenter', hx_swap='outerHTML')
    flyout_panel = Div(id='flyout-panel', cls='flyout-panel hidden')
    return Div(poke_button, flyout_panel)

@rt('/poke-flyout', methods=['GET'])
async def poke_flyout(request):
    current_app = db.get('last_app_choice', '')
    workflow_instance = get_workflow_instance(current_app)
    is_workflow = workflow_instance is not None and hasattr(workflow_instance, 'steps')
    profile_locked = db.get('profile_locked', '0') == '1'
    lock_button_text = '🔓 Unlock Profile' if profile_locked else '🔒 Lock Profile'
    is_dev_mode = get_current_environment() == 'Development'
    poke_button = Button(f'🤖 Poke {MODEL}', hx_post='/poke', hx_target='#msg-list', hx_swap='beforeend', cls='secondary outline')
    lock_button = Button(lock_button_text, hx_post='/toggle_profile_lock', hx_target='body', hx_swap='outerHTML', cls='secondary outline')
    delete_workflows_button = Button('🗑️ Delete Workflows', hx_post='/clear-pipeline', hx_target='body', hx_confirm='Are you sure you want to delete workflows?', hx_swap='outerHTML', cls='secondary outline') if is_workflow else None
    reset_db_button = Button('🔄 Reset Entire Database', hx_post='/clear-db', hx_target='body', hx_confirm='WARNING: This will reset the ENTIRE DATABASE to its initial state. All profiles, workflows, and plugin data will be deleted. Are you sure?', hx_swap='outerHTML', cls='secondary outline') if is_dev_mode else None
    list_items = [Li(poke_button, cls='flyout-list-item'), Li(lock_button, cls='flyout-list-item')]
    if is_workflow:
        list_items.append(Li(delete_workflows_button, cls='flyout-list-item'))
    if is_dev_mode:
        list_items.append(Li(reset_db_button, cls='flyout-list-item'))
    return Div(id='flyout-panel', cls='flyout-panel visible', hx_get='/poke-flyout-hide', hx_trigger='mouseleave delay:100ms', hx_target='this', hx_swap='outerHTML')(Div(H3('Poke Actions'), Ul(*list_items), cls='flyout-content'))

@rt('/poke-flyout-hide', methods=['GET'])
async def poke_flyout_hide(request):
    """Hide the poke flyout panel by returning an empty hidden div."""
    return Div(id='flyout-panel', cls='flyout-panel hidden')

@rt('/sse')
async def sse_endpoint(request):
    return EventStream(broadcaster.generator())

@app.post('/chat')
async def chat_endpoint(request, message: str):
    await pipulate.stream(f'Let the user know {limiter} {message}')
    return ''

@rt('/redirect/{path:path}')
def redirect_handler(request):
    path = request.path_params['path']

    logger.debug(f'Redirecting to: /{path}')
    message = build_endpoint_messages(path)
    if message:
        prompt = read_training(message)
        append_to_conversation(prompt, role='system')
        db['temp_message'] = message
    build_endpoint_training(path)
    return Redirect(f'/{path}')

@rt('/poke', methods=['POST'])
async def poke_chatbot():
    logger.debug('Chatbot poke received.')
    poke_message = f'The user poked the {APP_NAME} Chatbot. Respond with a brief, funny comment about being poked.'
    asyncio.create_task(pipulate.stream(poke_message))
    return 'Poke received. Countdown to local LLM MODEL...'

@rt('/open-folder', methods=['GET'])
async def open_folder_endpoint(request):
    """
    Opens a folder in the host OS's file explorer.
    Expects a 'path' query parameter with the absolute path to open.
    """
    path_param = request.query_params.get('path')
    if not path_param:
        return HTMLResponse('Path parameter is missing', status_code=400)
    decoded_path = urllib.parse.unquote(path_param)
    if not os.path.isabs(decoded_path) or '..' in decoded_path:
        return HTMLResponse('Invalid or potentially insecure path', status_code=400)
    if not os.path.exists(decoded_path) or not os.path.isdir(decoded_path):
        return HTMLResponse('Path does not exist or is not a directory', status_code=400)
    try:
        current_os = platform.system()
        if current_os == 'Windows':
            subprocess.run(['explorer', decoded_path], check=True)
        elif current_os == 'Darwin':
            subprocess.run(['open', decoded_path], check=True)
        elif current_os == 'Linux':
            subprocess.run(['xdg-open', decoded_path], check=True)
        else:
            return HTMLResponse(f'Unsupported operating system: {current_os}', status_code=400)
        return HTMLResponse('Folder opened successfully')
    except subprocess.CalledProcessError as e:
        return HTMLResponse(f'Failed to open folder: {str(e)}', status_code=500)
    except Exception as e:
        return HTMLResponse(f'An unexpected error occurred: {str(e)}', status_code=500)

@rt('/toggle_profile_lock', methods=['POST'])
async def toggle_profile_lock(request):
    current = db.get('profile_locked', '0')
    db['profile_locked'] = '1' if current == '0' else '0'
    return HTMLResponse('', headers={'HX-Refresh': 'true'})



@rt('/refresh-app-menu')
async def refresh_app_menu_endpoint(request):
    """Refresh the App menu dropdown via HTMX endpoint."""
    logger.debug('Refreshing App menu dropdown via HTMX endpoint /refresh-app-menu')
    menux = db.get('last_app_choice', '')
    app_menu_details_component = create_app_menu(menux)
    return HTMLResponse(to_xml(app_menu_details_component))

@rt('/clear-pipeline', methods=['POST'])
async def clear_pipeline(request):
    menux = db.get('last_app_choice', 'App')
    workflow_display_name = 'Pipeline'
    if menux and menux in plugin_instances:
        instance = plugin_instances.get(menux)
        if instance and hasattr(instance, 'DISPLAY_NAME'):
            workflow_display_name = instance.DISPLAY_NAME
        else:
            workflow_display_name = friendly_names.get(menux, menux.replace('_', ' ').title())
    last_app_choice = db.get('last_app_choice')
    last_visited_url = db.get('last_visited_url')
    keys = list(db.keys())
    for key in keys:
        del db[key]
    logger.debug(f'{workflow_display_name} DictLikeDB cleared')
    if last_app_choice:
        db['last_app_choice'] = last_app_choice
    if last_visited_url:
        db['last_visited_url'] = last_visited_url
    if hasattr(pipulate.table, 'xtra'):
        pipulate.table.xtra()
    records = list(pipulate.table())
    logger.debug(f'Found {len(records)} records to delete')
    for record in records:
        pipulate.table.delete(record.pkey)
    logger.debug(f'{workflow_display_name} table cleared')
    db['temp_message'] = f'{workflow_display_name} cleared. Next ID will be 01.'
    logger.debug(f'{workflow_display_name} DictLikeDB cleared for debugging')
    response = Div(pipulate.update_datalist('pipeline-ids', clear=True), P(f'{workflow_display_name} cleared.'), cls='clear-message')
    html_response = HTMLResponse(str(response))
    html_response.headers['HX-Refresh'] = 'true'
    return html_response

@rt('/clear-db', methods=['POST'])
async def clear_db(request):
    """Reset the entire database to its initial state."""
    if TABLE_LIFECYCLE_LOGGING:
        logger.bind(lifecycle=True).info('CLEAR_DB: Starting database reset...')
        log_dictlike_db_to_lifecycle('db', db, title_prefix='CLEAR_DB INITIAL')
        log_dynamic_table_state('pipeline', lambda: pipeline(), title_prefix='CLEAR_DB INITIAL')
        log_dynamic_table_state('profiles', lambda: profiles(), title_prefix='CLEAR_DB INITIAL')
    
    # Safely preserve certain values before clearing
    last_app_choice = db.get('last_app_choice')
    last_visited_url = db.get('last_visited_url')
    temp_message = db.get('temp_message')
    if TABLE_LIFECYCLE_LOGGING:
        logger.bind(lifecycle=True).info('CLEAR_DB: Table states BEFORE plugin table wipe:')
        try:
            conn_temp = sqlite3.connect(DB_FILENAME)
            conn_temp.row_factory = sqlite3.Row
            cursor_temp = conn_temp.cursor()
            cursor_temp.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('store', 'profile', 'pipeline', 'sqlite_sequence')")
            plugin_table_names_tuples = cursor_temp.fetchall()
            for table_name_tuple in plugin_table_names_tuples:
                log_raw_sql_table_to_lifecycle(conn_temp, table_name_tuple[0], title_prefix='CLEAR_DB PRE-WIPE')
            conn_temp.close()
        except Exception as e_plugin_log_pre:
            logger.bind(lifecycle=True).error(f'CLEAR_DB PRE-WIPE: Error logging plugin tables via SQL: {e_plugin_log_pre}')
    try:
        with sqlite3.connect(DB_FILENAME) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM store')
            cursor.execute('DELETE FROM pipeline')
            cursor.execute('DELETE FROM profile')
            
            # Only delete from sqlite_sequence if it exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
            if cursor.fetchone():
                cursor.execute('DELETE FROM sqlite_sequence')
                logger.debug('Cleared sqlite_sequence table')
            else:
                logger.debug('sqlite_sequence table does not exist, skipping')
            
            conn.commit()
    except Exception as e:
        logger.error(f'Error clearing core tables: {e}')
        return HTMLResponse(f'Error clearing database: {e}', status_code=500)
    logger.debug(f'CLEAR_DB: Using database file for plugin table deletion: {DB_FILENAME}')
    try:
        with sqlite3.connect(DB_FILENAME) as conn_delete:
            cursor_delete = conn_delete.cursor()
            cursor_delete.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('store', 'profile', 'pipeline', 'sqlite_sequence')")
            plugin_table_names_to_delete = [row[0] for row in cursor_delete.fetchall()]
            logger.warning(f"Found plugin tables for deletion: {', '.join(plugin_table_names_to_delete)}")
            cleared_count = 0
            for table_name in plugin_table_names_to_delete:
                try:
                    cursor_delete.execute(f'SELECT COUNT(*) FROM {table_name}')
                    row_count_before_delete = cursor_delete.fetchone()[0]
                    cursor_delete.execute(f'DELETE FROM {table_name}')
                    conn_delete.commit()
                    cursor_delete.execute(f'SELECT COUNT(*) FROM {table_name}')
                    row_count_after_delete = cursor_delete.fetchone()[0]
                    logger.warning(f"Plugin table '{table_name}' cleared: Deleted {row_count_before_delete - row_count_after_delete} records (had {row_count_before_delete})")
                    if TABLE_LIFECYCLE_LOGGING:
                        logger.bind(lifecycle=True).info(f"CLEAR_DB: Wiped plugin table '{table_name}'. Rows before: {row_count_before_delete}, Rows after: {row_count_after_delete}")
                    cleared_count += 1
                    try:
                        cursor_delete.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'")
                        conn_delete.commit()
                    except sqlite3.OperationalError as e_seq:
                        if 'no such table: sqlite_sequence' not in str(e_seq).lower():
                            logger.error(f'Error resetting sequence for table {table_name}: {e_seq}')
                except Exception as e_table_clear:
                    logger.error(f'Error clearing table {table_name}: {e_table_clear}')
            logger.warning(f'Plugin tables cleanup complete: Cleared {cleared_count} tables')
    except Exception as e_db_access:
        logger.error(f'Error accessing SQLite database for plugin table deletion: {e_db_access}')
        if TABLE_LIFECYCLE_LOGGING:
            logger.bind(lifecycle=True).error(f'CLEAR_DB: Critical error during plugin table deletion: {e_db_access}')
    populate_initial_data()
    if TABLE_LIFECYCLE_LOGGING:
        logger.bind(lifecycle=True).info('CLEAR_DB: After populate_initial_data.')
        log_dynamic_table_state('profiles', lambda: profiles(), title_prefix='CLEAR_DB POST-POPULATE')
    await synchronize_roles_to_db()
    if TABLE_LIFECYCLE_LOGGING:
        logger.bind(lifecycle=True).info('CLEAR_DB: After synchronize_roles_to_db.')
    # Restore preserved values if they existed
    if last_app_choice:
        db['last_app_choice'] = last_app_choice
    if last_visited_url:
        db['last_visited_url'] = last_visited_url
    if temp_message:
        db['temp_message'] = temp_message
    if TABLE_LIFECYCLE_LOGGING:
        log_dictlike_db_to_lifecycle('db', db, title_prefix='CLEAR_DB FINAL (post key restoration)')
        logger.bind(lifecycle=True).info('CLEAR_DB: Operation fully complete.')
    html_response = HTMLResponse('<div>Database reset complete</div>')
    html_response.headers['HX-Refresh'] = 'true'
    return html_response

@rt('/select_profile', methods=['POST'])
async def select_profile(request):
    logger.debug('Entering select_profile function')
    form = await request.form()
    logger.debug(f'Received form data: {form}')
    profile_id = form.get('profile_id')
    logger.debug(f'Extracted profile_id: {profile_id}')
    if profile_id:
        profile_id = int(profile_id)
        logger.debug(f'Converted profile_id to int: {profile_id}')
        db['last_profile_id'] = profile_id
        logger.debug(f'Updated last_profile_id in db to: {profile_id}')
        profile = profiles[profile_id]
        logger.debug(f'Retrieved profile: {profile}')
        profile_name = getattr(profile, 'name', 'Unknown Profile')
        logger.debug(f'Profile name: {profile_name}')
        prompt = f"You have switched to the '{profile_name}' profile."
        db['temp_message'] = prompt
        logger.debug(f"Stored temp_message in db: {db['temp_message']}")
    redirect_url = db.get('last_visited_url', '/')
    logger.debug(f'Redirecting to: {redirect_url}')
    return Redirect(redirect_url)

@rt('/download_file', methods=['GET', 'OPTIONS'])
async def download_file_endpoint(request):
    """
    Downloads a file from the server.
    Expects 'file' as a query parameter, which should be relative to the downloads directory.
    """
    if request.method == 'OPTIONS':
        headers = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, OPTIONS', 'Access-Control-Allow-Headers': '*', 'Access-Control-Max-Age': '86400'}
        return HTMLResponse('', headers=headers)
    file_path = request.query_params.get('file')
    if DEBUG_MODE:
        logger.info(f'[📥 DOWNLOAD] Request received for file: {file_path}')
        logger.info(f'[📥 DOWNLOAD] Request headers: {dict(request.headers)}')
    if not file_path:
        logger.error('[📥 DOWNLOAD] No file path provided')
        return HTMLResponse('File path is required', status_code=400)
    try:
        PLUGIN_PROJECT_ROOT = Path(__file__).resolve().parent
        PLUGIN_DOWNLOADS_BASE_DIR = PLUGIN_PROJECT_ROOT / 'downloads'
        if DEBUG_MODE:
            logger.info(f'[📥 DOWNLOAD] Base downloads directory: {PLUGIN_DOWNLOADS_BASE_DIR}')
            logger.info(f'[📥 DOWNLOAD] Base downloads directory exists: {PLUGIN_DOWNLOADS_BASE_DIR.exists()}')
        full_file_path = PLUGIN_DOWNLOADS_BASE_DIR / file_path
        if DEBUG_MODE:
            logger.info(f'[📥 DOWNLOAD] Full file path: {full_file_path}')
            logger.info(f'[📥 DOWNLOAD] Full file path exists: {full_file_path.exists()}')
            if full_file_path.exists():
                logger.info(f'[📥 DOWNLOAD] Full file path is file: {full_file_path.is_file()}')
                logger.info(f'[📥 DOWNLOAD] Full file path is dir: {full_file_path.is_dir()}')
                logger.info(f'[📥 DOWNLOAD] Full file path size: {full_file_path.stat().st_size}')
        try:
            resolved_path = full_file_path.resolve()
            relative_path = resolved_path.relative_to(PLUGIN_DOWNLOADS_BASE_DIR)
            if DEBUG_MODE:
                logger.info(f'[📥 DOWNLOAD] Security check passed. Resolved path: {resolved_path}')
                logger.info(f'[📥 DOWNLOAD] Relative path: {relative_path}')
        except (ValueError, RuntimeError) as e:
            logger.error(f'[📥 DOWNLOAD] Security check failed for path {file_path}: {str(e)}')
            logger.error(f'[📥 DOWNLOAD] Full file path: {full_file_path}')
            logger.error(f'[📥 DOWNLOAD] Base dir: {PLUGIN_DOWNLOADS_BASE_DIR}')
            return HTMLResponse('Invalid file path - must be within downloads directory', status_code=400)
        if not full_file_path.exists():
            logger.error(f'[📥 DOWNLOAD] File not found: {full_file_path}')
            logger.error(f"[📥 DOWNLOAD] Directory contents: {list(PLUGIN_DOWNLOADS_BASE_DIR.glob('**/*'))}")
            return HTMLResponse('File not found', status_code=404)
        if not full_file_path.is_file():
            logger.error(f'[📥 DOWNLOAD] Path is not a file: {full_file_path}')
            return HTMLResponse('Path is not a file', status_code=400)
        content_type = 'application/octet-stream'
        if full_file_path.suffix.lower() == '.csv':
            content_type = 'text/csv'
        elif full_file_path.suffix.lower() == '.txt':
            content_type = 'text/plain'
        elif full_file_path.suffix.lower() == '.json':
            content_type = 'application/json'
        elif full_file_path.suffix.lower() == '.pdf':
            content_type = 'application/pdf'
        elif full_file_path.suffix.lower() in ['.jpg', '.jpeg']:
            content_type = 'image/jpeg'
        elif full_file_path.suffix.lower() == '.png':
            content_type = 'image/png'
        elif full_file_path.suffix.lower() == '.gif':
            content_type = 'image/gif'
        logger.info(f'[📥 DOWNLOAD] Serving file {full_file_path} with content type {content_type}')
        headers = {'Content-Disposition': f'attachment; filename="{full_file_path.name}"', 'Content-Type': content_type, 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': '*', 'Access-Control-Allow-Headers': '*'}
        logger.info(f'[📥 DOWNLOAD] Response headers: {headers}')
        return FileResponse(full_file_path, headers=headers)
    except Exception as e:
        logger.error(f'[📥 DOWNLOAD] Error serving file {file_path}: {str(e)}')
        logger.error(f'[📥 DOWNLOAD] Exception type: {type(e)}')
        import traceback
        logger.error(f'[📥 DOWNLOAD] Traceback: {traceback.format_exc()}')
        return HTMLResponse(f'Error serving file: {str(e)}', status_code=500)

class DOMSkeletonMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):
        endpoint = request.url.path
        method = request.method
        is_static = endpoint.startswith('/static/')
        is_ws = endpoint == '/ws'
        is_sse = endpoint == '/sse'
        if not (is_static or is_ws or is_sse):
            log.event('network', f'{method} {endpoint}')
        else:
            log.debug('network', f'{method} {endpoint}')
        response = await call_next(request)
        if STATE_TABLES:
            cookie_table = Table(title='🍪 Stored Cookie States')
            cookie_table.add_column('Key', style='cyan')
            cookie_table.add_column('Value', style='magenta')
            for key, value in db.items():
                json_value = JSON.from_data(value, indent=2)
                cookie_table.add_row(key, json_value)
            console.print(cookie_table)
            pipeline_table = Table(title='➡️ Pipeline States')
            pipeline_table.add_column('Key', style='yellow')
            pipeline_table.add_column('Created', style='magenta')
            pipeline_table.add_column('Updated', style='cyan')
            pipeline_table.add_column('Steps', style='white')
            for record in pipulate.table():
                try:
                    state = json.loads(record.data)
                    pre_state = json.loads(record.data)
                    pipeline_table.add_row(record.pkey, str(state.get('created', '')), str(state.get('updated', '')), str(len(pre_state) - 2))
                except (json.JSONDecodeError, AttributeError) as e:
                    log.error(f'Error parsing pipeline state for {record.pkey}', e)
                    pipeline_table.add_row(record.pkey, 'ERROR', 'Invalid State')
            console.print(pipeline_table)
        return response

def print_routes():
    logger.debug('Route Table')
    table = Table(title='Application Routes')
    table.add_column('Type', style='cyan', no_wrap=True)
    table.add_column('Methods', style='yellow on black')
    table.add_column('Path', style='white')
    table.add_column('Duplicate', style='green')
    route_entries = []
    seen_routes = set()
    for app_route in app.routes:
        if isinstance(app_route, Route):
            methods = ', '.join(app_route.methods)
            route_key = (app_route.path, methods)
            if route_key in seen_routes:
                path_style = 'red'
                duplicate_status = Text('Yes', style='red')
            else:
                path_style = 'white'
                duplicate_status = Text('No', style='green')
                seen_routes.add(route_key)
            route_entries.append(('Route', methods, app_route.path, path_style, duplicate_status))
        elif isinstance(app_route, WebSocketRoute):
            route_key = (app_route.path, 'WebSocket')
            if route_key in seen_routes:
                path_style = 'red'
                duplicate_status = Text('Yes', style='red')
            else:
                path_style = 'white'
                duplicate_status = Text('No', style='green')
                seen_routes.add(route_key)
            route_entries.append(('WebSocket', 'WebSocket', app_route.path, path_style, duplicate_status))
        elif isinstance(app_route, Mount):
            route_entries.append(('Mount', 'Mounted App', app_route.path, 'white', Text('N/A', style='green')))
        else:
            route_entries.append((str(type(app_route)), 'Unknown', getattr(app_route, 'path', 'N/A'), 'white', Text('N/A', style='green')))
    route_entries.sort(key=lambda x: x[2])
    for entry in route_entries:
        table.add_row(entry[0], entry[1], Text(entry[2], style=f'{entry[3]} on black'), entry[4])
    console.print(table)

@rt('/refresh-profile-menu')
async def refresh_profile_menu(request):
    """Refresh the profile menu dropdown."""
    selected_profile_id = get_current_profile_id()
    selected_profile_name = get_profile_name()
    return create_profile_menu(selected_profile_id, selected_profile_name)

@rt('/switch_environment', methods=['POST'])
async def switch_environment(request):
    """Handle environment switching and restart the server.
    
    This endpoint is called via HTMX when switching between Development/Production modes.
    It returns a PicoCSS spinner with aria-busy that gets swapped in via HTMX,
    while the server restarts in the background.
    
    The spinner uses PicoCSS's built-in aria-busy animation and styling:
    - aria-busy='true' triggers PicoCSS's loading animation
    - The div is styled to match menu item dimensions exactly to create a seamless transition
    - The spinner appears to replace the radio buttons in the dropdown menu items
    - Body is made non-interactive during the switch to prevent double-clicks
    
    HTMX targets the specific environment selector item that was clicked,
    creating the illusion that the spinner is replacing just that menu item's radio button.
    The precise styling ensures the spinner appears in exactly the same position and size
    as the original menu item, maintaining visual continuity during the transition.
    """
    try:
        form = await request.form()
        environment = form.get('environment', 'Development')
        set_current_environment(environment)
        logger.info(f'Environment switched to: {environment}')
        

        
        # Schedule server restart after a delay to allow HTMX to swap in the spinner
        asyncio.create_task(delayed_restart(2))
        
        # Return PicoCSS spinner that will be swapped in via HTMX
        return HTMLResponse(f"""
            <div 
                aria-busy='true'
                style="
                    display: flex;
                    align-items: center;
                    {pipulate.MENU_ITEM_PADDING}
                    border-radius: var(--pico-border-radius);
                    min-height: 2.5rem;
                "
            >
                Switching
            </div>
            <style>
                body {{
                    pointer-events: none;
                    user-select: none;
                }}
            </style>
            """)
    except Exception as e:
        logger.error(f'Error switching environment: {e}')
        return HTMLResponse(f'Error: {str(e)}', status_code=500)

async def delayed_restart(delay_seconds):
    """Restart the server after a delay."""
    logger.info(f'Server restart scheduled in {delay_seconds} seconds...')
    await asyncio.sleep(delay_seconds)
    try:
        logger.info('Performing server restart now...')
        restart_server()
    except Exception as e:
        logger.error(f'Error during restart: {e}')

async def send_delayed_endpoint_message(message, session_key):
    """Send an endpoint message after a delay to ensure chat system is ready."""
    await asyncio.sleep(2)  # Brief delay to ensure page has loaded
    try:
        await pipulate.message_queue.add(pipulate, message, verbatim=True, role='system')
        db[session_key] = 'sent'  # Mark as sent for this session
        logger.debug(f"Successfully sent delayed endpoint message for {session_key}")
    except Exception as e:
        logger.warning(f"Failed to send delayed endpoint message for {session_key}: {e}")

async def send_startup_environment_message():
    """Send a message indicating the current environment mode after server startup."""
    # Longer wait for fresh nix develop startup to ensure chat system is fully ready
    await asyncio.sleep(5)  # Increased from 3 to 5 seconds
    
    try:
        current_env = get_current_environment()
        env_display = 'DEV' if current_env == 'Development' else 'Prod'
        
        if current_env == 'Development':
            env_message = f"🚀 Server started in {env_display} mode. Ready for experimentation and testing!"
        else:
            env_message = f"🚀 Server started in {env_display} mode. Ready for production use."
        
        # Ensure message queue is ready with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await pipulate.message_queue.add(pipulate, env_message, verbatim=True, role='system')
                logger.debug(f"Successfully sent startup environment message (attempt {attempt + 1})")
                break
            except Exception as e:
                logger.warning(f"Failed to send startup environment message (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # Wait before retry
                else:
                    raise
        
        # Also send endpoint message and training for current location
        current_endpoint = db.get('last_app_choice', '')
        
        # Add training prompt to conversation history
        build_endpoint_training(current_endpoint)
        
        # Send endpoint message if available (only if no temp_message to avoid duplication)
        if 'temp_message' not in db:
            endpoint_message = build_endpoint_messages(current_endpoint)
            if endpoint_message:
                await asyncio.sleep(1)  # Brief pause between messages
                
                # Retry logic for endpoint message too
                for attempt in range(max_retries):
                    try:
                        await pipulate.message_queue.add(pipulate, endpoint_message, verbatim=True, role='system')
                        logger.debug(f"Successfully sent endpoint message (attempt {attempt + 1})")
                        # Mark startup endpoint message as sent
                        session_key = f'endpoint_message_sent_{current_endpoint}'
                        db[session_key] = 'sent'
                        break
                    except Exception as e:
                        logger.warning(f"Failed to send endpoint message (attempt {attempt + 1}/{max_retries}): {e}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2)  # Wait before retry
                        else:
                            # Don't raise here - endpoint message is less critical than startup message
                            logger.error(f"Failed to send endpoint message after {max_retries} attempts: {e}")
            
    except Exception as e:
        logger.error(f'Error sending startup environment message: {e}')


ALL_ROUTES = list(set([''] + MENU_ITEMS))
for item in ALL_ROUTES:
    path = f'/{item}' if item else '/'

    @app.route(path)
    async def home_route(request):
        return await home(request)
app.add_middleware(DOMSkeletonMiddleware)
logger.debug('Application setup completed with DOMSkeletonMiddleware.')
logger.debug(f'Using MODEL: {MODEL}')

def check_syntax(filename):
    with open(filename, 'r') as file:
        source = file.read()
    try:
        ast.parse(source)
        return True
    except SyntaxError as e:
        print(f'Syntax error in {filename}:')
        print(f'  Line {e.lineno}: {e.text}')
        print(f"  {' ' * (e.offset - 1)}^")
        print(f'Error: {e}')
        return False

def restart_server():
    if shared_app_state['critical_operation_in_progress'] or is_critical_operation_in_progress():
        log.warning('Restart requested but critical operation in progress. Deferring restart.')
        return
    if not check_syntax(Path(__file__)):
        log.warning('Syntax error detected', 'Fix the error and save the file again')
        return
    max_retries = 3
    for attempt in range(max_retries):
        try:
            log.startup(f'Restarting server (attempt {attempt + 1}/{max_retries})')
            os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            log.error(f'Error restarting server (attempt {attempt + 1}/{max_retries})', e)
            if attempt < max_retries - 1:
                log.warning('Restart failed', 'Waiting 5 seconds before retrying')
                time.sleep(5)
            else:
                log.error('Max restart retries reached', 'Please restart the server manually')

class ServerRestartHandler(FileSystemEventHandler):

    def _should_ignore_event(self, event):
        """Check if event should be ignored to prevent unnecessary restarts."""
        if event.is_directory:
            return True
        ignore_patterns = ['/.', '__pycache__', '.pyc', '.swp', '.tmp', '.DS_Store']
        if any((pattern in event.src_path for pattern in ignore_patterns)):
            return True
        return False

    def on_modified(self, event):
        if self._should_ignore_event(event):
            return
        path = Path(event.src_path)
        if path.suffix == '.py':
            if shared_app_state['critical_operation_in_progress'] or is_critical_operation_in_progress():
                log.warning(f'Watchdog: Critical operation in progress. Deferring restart for {path}')
                return
            print(f'{path} has been modified. Checking syntax and restarting...')
            restart_server()

def run_server_with_watchdog():
    fig('SERVER RESTART')
    fig(APP_NAME, font='standard')
    env = get_current_environment()
    env_db = DB_FILENAME
    if env == 'Development':
        log.warning('Development mode active', details=f'Using database: {env_db}')
    else:
        log.startup('Production mode active', details=f'Using database: {env_db}')
    if STATE_TABLES:
        log.startup('State tables enabled', details='Edit server.py and set STATE_TABLES=False to disable')
        print_routes()
    else:
        alice_buffer = 10
        [print() for _ in range(alice_buffer)]
        with open('static/alice.txt', 'r') as file:
            print(file.read())
        [print() for _ in range(alice_buffer)]
    event_handler = ServerRestartHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=True)
    observer.start()
    try:
        log.startup('Server starting on http://localhost:5001')
        log_level = 'debug' if DEBUG_MODE else 'warning'
        log_config = {'version': 1, 'disable_existing_loggers': False, 'formatters': {'default': {'()': 'uvicorn.logging.DefaultFormatter', 'fmt': '%(levelprefix)s %(asctime)s | %(message)s', 'use_colors': True}}, 'handlers': {'default': {'formatter': 'default', 'class': 'logging.StreamHandler', 'stream': 'ext://sys.stderr'}}, 'loggers': {'uvicorn': {'handlers': ['default'], 'level': log_level.upper()}, 'uvicorn.error': {'level': log_level.upper()}, 'uvicorn.access': {'handlers': ['default'], 'level': log_level.upper(), 'propagate': False}, 'uvicorn.asgi': {'handlers': ['default'], 'level': log_level.upper(), 'propagate': False}}}
        uvicorn.run(app, host='0.0.0.0', port=5001, log_level=log_level, access_log=DEBUG_MODE, log_config=log_config)
    except KeyboardInterrupt:
        log.event('server', 'Server shutdown requested by user')
        observer.stop()
    except Exception as e:
        log.error('Server error', e)
        log.startup('Attempting to restart')
        restart_server()
    finally:
        observer.join()
if __name__ == '__main__':
    run_server_with_watchdog()

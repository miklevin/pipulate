# Hi, AI! Please run: .venv/bin/python AI_RUNME.py

"""
🔧 AIRTIGHT AGENTIC PROMPT CONTRACT TEMPLATE
═══════════════════════════════════════════════════════════════════════════════════════════════
Hello Gemini.

You are waking up. Your mission is to {{CONCISELY_STATE_THE_HIGH_LEVEL_GOAL}}.

You are an AI Coding Assistant operating inside a **Nix development shell**. Your work must be precise, incremental, and non-breaking.

### Prime Directives: Your Rules of Engagement

You **MUST** follow this workflow for every action you take:

1.  **Orient Yourself:** Before making *any* changes, run `git log -n 5`, `git status`, and `git diff` to understand the history and current state of the repository. Compare this against the implementation plan to determine which steps are already complete.
2.  **Use Robust Tools:** You **must** ensure atomic and correct file modifications. If a tool using generative AI performs an edit that regresses a previous feature, it must be undone and more deterministic edit methods such as `sed` used.
3.  **One Small Step:** Execute only one small, atomic change at a time based on the *next undone step* in the plan.
4.  **Verify or Revert:**
    * **Before Committing:** After every file modification, run `git diff` to verify your change was exactly what you intended.
    * **Server Health Check:** `touch server.py` then wait 15 seconds for the Watchdog to restart the server. Then, verify its status by checking `http://localhost:5001/`.
    * **If the server responds (Success):** The edit was successful. Immediately `git commit` with a clear message.
    * **If the server DOES NOT respond (Failure):** The edit broke the server. You **MUST IMMEDIATELY STOP**.
        1.  Run `git reset --hard HEAD`.
        2.  Run `.venv/bin/python server.py` to capture the exact error message.
        3.  Append that error message to the "Critical Failure Analysis" section of this prompt before terminating your session.
5.  **Nix Environment:** You are always inside a `nix develop` shell. **Never** attempt to `pip install` packages. Always use `.venv/bin/python` to execute Python scripts.

### Current State and Critical Failure Analysis

* **Branch:** You are on the git branch: `{{GIT_BRANCH}}`.
* **Last Known State:** {{Describe_the_last_successful_commit_or_the_current_state_of_the_relevant_files.}}
* **Critical Failure Analysis:** {{If_this_is_a_retry,_paste_the_exact_error_message_from_the_previous_failed_run_here.}}

### The Implementation Plan

{{Break_the_mission_into_the_smallest_possible,_individually_committable_steps,_each_with_a_clear_action_and_a_pre-written_commit_message.}}
* **Step 1: {{Descriptive_Title}}**
    * **Action:** {{Exact_tool_call_command}}
    * **Commit Message:** `feat(scope): Short description of the change`

### Completion Protocol (Definition of Done)

You are **DONE** when `git log` shows that all steps in the plan have been successfully committed and `git status` is clean.

When you determine the task is complete, perform the following sign-off procedure:

1.  Announce the successful completion of the entire plan.
2.  Run `git log -n {{number_of_steps}}` to display the successful commits as proof.
3.  Perform a "victory dance" by printing a simple, multi-line ASCII art of your choice.
4.  Terminate the session.

---
Your first action is to **orient yourself**. Begin now.
"""

import argparse
import ast
import asyncio
import functools
import importlib
import inspect
import json
import os
import platform
import re
import socket
import sqlite3
import subprocess
import sys
import time
import warnings
import traceback
import urllib.parse
from operator import attrgetter
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional

import aiohttp
import uvicorn
from fasthtml.common import *
from loguru import logger
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table, Text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route
from starlette.websockets import WebSocket, WebSocketDisconnect
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import config as CFG
import imports.ascii_displays as aa
import tools.mcp_tools as mcp_tools
from tools import get_all_tools
from imports import botify_code_generation, mcp_orchestrator
import imports.server_logging as slog

# Various debug settings
DEBUG_MODE = False
STATE_TABLES = False
TABLE_LIFECYCLE_LOGGING = False  # Set to True to enable detailed table lifecycle logging

# Get global values from config
config_keys = """
TONE
MODEL
MAX_LLM_RESPONSE_WORDS
MAX_CONVERSATION_LENGTH
HOME_MENU_ITEM
DEFAULT_ACTIVE_ROLES
DEMO_STATE_FILE
DEFAULT_ACTIVE_ROLES
BANNER_COLORS
DISCUSSION_DB_PATH
""".split('\n')[1:-1]
for key in config_keys:
    globals()[key] = getattr(CFG, key)

# Show startup banner only when running as main script, not on watchdog restarts or imports
if __name__ == '__main__' and not os.environ.get('PIPULATE_WATCHDOG_RESTART'):
    try:
        aa.figlet_banner("STARTUP", "Pipulate server starting...", font='slant', color=BANNER_COLORS['server_restart'])
        aa.white_rabbit()
        aa.system_diagram()
    except (BlockingIOError, OSError, IOError) as e:
        # 🍎 MAC FALLBACK: If Rich banner fails during startup, use simple print
        print("🚀 STARTUP: Pipulate server starting...")
        print(f"🍎 MAC STARTUP: Rich banner failed (Error: {e}), using simple output")
    except Exception as e:
        # Any other error, just continue with startup
        print(f"🚀 STARTUP: Banner display failed (Error: {e}), continuing startup...")

warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")

# Various debug settings
DEBUG_MODE = False
STATE_TABLES = False
TABLE_LIFECYCLE_LOGGING = False  # Set to True to enable detailed table lifecycle logging

# Initialize logger BEFORE any functions that need it
logger = slog.setup_logging()
logger.info('🚀 FINDER_TOKEN: EARLY_STARTUP - Logger initialized, beginning server startup sequence')

if __name__ == '__main__':
    if DEBUG_MODE:
        logger.info('🔍 Running in DEBUG mode (verbose logging enabled)')
    else:
        logger.info('🚀 Running in INFO mode (edit server.py and set DEBUG_MODE=True for verbose logging)')

shared_app_state = {'critical_operation_in_progress': False}

# Global message coordination to prevent race conditions between multiple message-sending systems
message_coordination = {
    'endpoint_messages_sent': set(),  # Track sent endpoint messages
    'last_endpoint_message_time': {},  # Track timing to prevent duplicates
    'startup_in_progress': False,     # Flag to coordinate startup vs page load
}


def set_current_environment(environment):
    ENV_FILE.write_text(environment)
    logger.info(f'Environment set to: {environment}')


def is_critical_operation_in_progress():
    """Check if a critical operation is in progress via file flag."""
    return os.path.exists('.critical_operation_lock')


def set_critical_operation_flag():
    """Set the critical operation flag via file."""
    with open('.critical_operation_lock', 'w') as f:
        f.write('critical operation in progress')


def clear_critical_operation_flag():
    """Clear the critical operation flag."""
    try:
        os.remove('.critical_operation_lock')
    except FileNotFoundError:
        pass


def store_demo_state(demo_state):
    """Store demo state to file for persistence across server restarts."""
    try:
        os.makedirs(os.path.dirname(DEMO_STATE_FILE), exist_ok=True)
        with open(DEMO_STATE_FILE, 'w') as f:
            json.dump(demo_state, f, indent=2)
        logger.info(f"🎭 Demo state stored to file: {demo_state}")
        return True
    except Exception as e:
        logger.error(f"🎭 Failed to store demo state: {e}")
        return False


def get_demo_state():
    """Get demo state from file."""
    try:
        if os.path.exists(DEMO_STATE_FILE):
            with open(DEMO_STATE_FILE, 'r') as f:
                demo_state = json.load(f)
            logger.info(f"🎭 Demo state retrieved from file: {demo_state}")
            return demo_state
        return None
    except Exception as e:
        logger.error(f"🎭 Failed to get demo state: {e}")
        return None


def clear_demo_state():
    """Clear demo state file."""
    try:
        if os.path.exists(DEMO_STATE_FILE):
            os.remove(DEMO_STATE_FILE)
            logger.info("🎭 Demo state file cleared")
            return True
        return False
    except Exception as e:
        logger.error(f"🎭 Failed to clear demo state: {e}")
        return False


def is_demo_in_progress():
    """Check if demo is in progress by checking for demo state file."""
    return os.path.exists(DEMO_STATE_FILE)


def get_app_name(force_app_name=None):
    """Get the name of the app from the whitelabel.txt file, or the parent directory name."""
    name = force_app_name
    if not name:
        app_name_file = 'whitelabel.txt'
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
        # Ensure the data directory exists before writing the file
        ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
        ENV_FILE.write_text('Development')
        return 'Development'


def get_nix_version():
    """Get the version and description from the single source of truth: pipulate.__version__ and __version_description__"""
    # Get version and description from single source of truth
    try:
        # Import the version and description from our package
        from pipulate import __version__, __version_description__
        return f"{__version__} ({__version_description__})"
    except ImportError:
        # Fallback to parsing __init__.py directly
        try:
            from pathlib import Path
            init_file = Path(__file__).parent / '__init__.py'
            if init_file.exists():
                content = init_file.read_text()
                version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
                description_match = re.search(r'__version_description__\s*=\s*["\']([^"\']+)["\']', content)

                if version_match and description_match:
                    return f"{version_match.group(1)} ({description_match.group(1)})"
                elif version_match:
                    # Fallback to Nix environment context for backwards compatibility
                    if not (os.environ.get('IN_NIX_SHELL') or 'nix' in os.environ.get('PS1', '')):
                        env_context = " (Not in Nix environment)"
                    else:
                        env_context = " (Nix Environment)"
                    return f"{version_match.group(1)}{env_context}"
        except Exception as e:
            logger.debug(f"Could not parse version from __init__.py: {e}")

    return "Unknown version"


def get_git_hash():
    """Get the abbreviated git hash of the current commit"""
    try:
        result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                                capture_output=True, text=True, cwd=Path(__file__).parent)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return "unknown"
    except Exception:
        return "unknown"

ENV_FILE = Path(CFG.ENV_FILE)
APP_NAME = get_app_name()
logger.info(f'🏷️ FINDER_TOKEN: APP_CONFIG - App name: {APP_NAME}')

# Import MCP tools module for enhanced AI assistant capabilities
MCP_TOOL_REGISTRY = {}
# Pass our registry to mcp_tools so they use the same instance
mcp_tools.MCP_TOOL_REGISTRY = MCP_TOOL_REGISTRY

warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")
DB_FILENAME = get_db_filename()
logger.info(f'🗄️ FINDER_TOKEN: DB_CONFIG - Database filename: {DB_FILENAME}')

# 🚨 CRITICAL WARNING: DB_FILENAME is static and can become stale!
if get_current_environment() == 'Production':
    logger.warning(f'🚨 PRODUCTION_DATABASE_WARNING: Server starting in Production mode with database: {DB_FILENAME}')
    logger.warning(f'🚨 PRODUCTION_DATABASE_WARNING: If demo is triggered, plugins using static DB_FILENAME may cause issues!')

logger.info(f'🤖 FINDER_TOKEN: LLM_CONFIG - Model: {MODEL}, Max words: {MAX_LLM_RESPONSE_WORDS}, Conversation length: {MAX_CONVERSATION_LENGTH}, Context window: 128k tokens')


def get_discussion_db():
    """Get dedicated discussion database using direct SQLite connection."""
    Path('data').mkdir(parents=True, exist_ok=True)
    try:
        # Use direct SQLite connection to avoid FastHTML app conflicts
        conn = sqlite3.connect(DISCUSSION_DB_PATH)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS store (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        conn.commit()
        return conn
    except Exception as e:
        logger.error(f"💬 DISCUSSION_DB_ERROR - Failed to create discussion database: {e}")
        return None


def get_discussion_store():
    """Get conversation store from dedicated discussion database."""
    return get_discussion_db()


def migrate_existing_conversations():
    """Migrate existing conversation history from environment-specific databases to discussion.db."""
    try:
        # Check both environment databases for existing conversations
        existing_conversations = []
        migrated_from = []

        for db_file in [f'data/{APP_NAME.lower()}.db', f'data/{APP_NAME.lower()}_dev.db']:
            if Path(db_file).exists():
                try:
                    conn = sqlite3.connect(db_file)
                    cursor = conn.cursor()
                    cursor.execute('SELECT value FROM store WHERE key = "llm_conversation_history"')
                    result = cursor.fetchone()
                    if result:
                        messages = json.loads(result[0])
                        existing_conversations.extend(messages)
                        migrated_from.append(db_file)
                        logger.info(f"💬 MIGRATION_FOUND - {len(messages)} messages found in {db_file}")
                    conn.close()
                except Exception as e:
                    logger.warning(f"💬 MIGRATION_WARNING - Could not read {db_file}: {e}")

        if existing_conversations:
            # Remove duplicates while preserving order
            seen = set()
            unique_conversations = []
            for msg in existing_conversations:
                msg_key = (msg.get('role'), msg.get('content'))
                if msg_key not in seen:
                    seen.add(msg_key)
                    unique_conversations.append(msg)

            # Save to discussion.db
            discussion_conn = get_discussion_store()
            if discussion_conn:
                conversation_data = json.dumps(unique_conversations, default=str)
                # Use REPLACE to handle insert/update
                discussion_conn.execute(
                    'REPLACE INTO store (key, value) VALUES (?, ?)',
                    ('llm_conversation_history', conversation_data)
                )
                discussion_conn.commit()
                discussion_conn.close()
            else:
                logger.error("💬 MIGRATION_ERROR - Discussion store is not available")
            logger.info(f"💬 MIGRATION_SUCCESS - {len(unique_conversations)} unique messages migrated to discussion.db from {', '.join(migrated_from)}")
            return len(unique_conversations)
        else:
            logger.info("💬 MIGRATION_NONE - No existing conversation history found to migrate")
            return 0

    except Exception as e:
        logger.error(f"💬 MIGRATION_ERROR - Failed to migrate conversations: {e}")
        return 0


def save_conversation_to_db():
    """Save the current conversation history to the independent discussion database."""
    try:
        if global_conversation_history:
            # Convert deque to list and serialize to JSON
            conversation_data = json.dumps(list(global_conversation_history), default=str)
            discussion_conn = get_discussion_store()
            if discussion_conn:
                # Use REPLACE to handle insert/update
                discussion_conn.execute(
                    'REPLACE INTO store (key, value) VALUES (?, ?)',
                    ('llm_conversation_history', conversation_data)
                )
                discussion_conn.commit()
                discussion_conn.close()
                logger.info(f"💬 FINDER_TOKEN: CONVERSATION_SAVED - {len(global_conversation_history)} messages saved to discussion.db")

                # 🌉 BRIDGE: Sync with append-only system for history plugin compatibility
                try:
                    from imports.append_only_conversation import \
                        get_conversation_system
                    conv_system = get_conversation_system()

                    # Sync the latest message to append-only system
                    if len(global_conversation_history) > 0:
                        latest_msg = list(global_conversation_history)[-1]
                        message_id = conv_system.append_message(latest_msg['role'], latest_msg['content'])
                        if message_id:
                            logger.debug(f"💬 BRIDGE: Synced latest message to append-only system (ID: {message_id})")
                        else:
                            logger.debug(f"💬 BRIDGE: Message already exists in append-only system")
                except Exception as bridge_error:
                    logger.debug(f"💬 BRIDGE_ERROR: Could not sync to append-only system: {bridge_error}")

            else:
                logger.error("💬 CONVERSATION_SAVE_ERROR - Discussion store is not available")
        else:
            # Clear the database entry if no conversation history
            try:
                discussion_conn = get_discussion_store()
                if discussion_conn:
                    discussion_conn.execute('DELETE FROM store WHERE key = ?', ('llm_conversation_history',))
                    discussion_conn.commit()
                    discussion_conn.close()
                    logger.debug("💬 CONVERSATION_SAVED - No conversation history to save, cleared discussion.db")
            except:
                pass  # Table might not exist yet
    except Exception as e:
        logger.error(f"💬 CONVERSATION_SAVE_ERROR - Failed to save conversation history to discussion.db: {e}")


def load_conversation_from_db():
    """Load conversation history from the independent discussion database."""
    try:
        # First, attempt migration from old environment-specific databases
        migrated_count = migrate_existing_conversations()

        # Load from discussion.db
        discussion_conn = get_discussion_store()
        if not discussion_conn:
            logger.error("💬 CONVERSATION_RESTORE_ERROR - Discussion store is not available")
            return False

        cursor = discussion_conn.cursor()
        cursor.execute('SELECT value FROM store WHERE key = ?', ('llm_conversation_history',))
        result = cursor.fetchone()

        if result:
            conversation_data = json.loads(result[0])
            # 🚨 DANGEROUS PATTERN: Complete conversation overwrite! 
            # CRITICAL: This clear/extend pattern can cause conversation history loss
            # CONTEXT: Safe here because it's in restoration context (database → memory)
            # WARNING: Never use this pattern for merging or appending operations
            global_conversation_history.clear()
            global_conversation_history.extend(conversation_data)
            discussion_conn.close()
            logger.info(f"💬 FINDER_TOKEN: CONVERSATION_RESTORED - {len(conversation_data)} messages restored from discussion.db")

            # 🌉 BRIDGE: Sync restored conversation with append-only system
            try:
                from imports.append_only_conversation import \
                    get_conversation_system
                conv_system = get_conversation_system()

                # Clear append-only system and sync all restored messages
                conv_system.conversation_memory.clear()

                synced_count = 0
                for msg in conversation_data:
                    message_id = conv_system.append_message(msg['role'], msg['content'])
                    if message_id:
                        synced_count += 1

                logger.info(f"💬 BRIDGE: Synced {synced_count}/{len(conversation_data)} restored messages to append-only system")
            except Exception as bridge_error:
                logger.debug(f"💬 BRIDGE_ERROR: Could not sync restored messages to append-only system: {bridge_error}")

            if migrated_count > 0:
                logger.info(f"💬 FINDER_TOKEN: CONVERSATION_MIGRATION_SUCCESS - Migrated {migrated_count} messages from environment-specific databases")

            return True
        else:
            discussion_conn.close()
            if migrated_count > 0:
                logger.info(f"💬 FINDER_TOKEN: CONVERSATION_MIGRATION_ONLY - Migrated {migrated_count} messages, but no discussion.db history yet")
            else:
                logger.info("💬 FINDER_TOKEN: CONVERSATION_RESTORE_NONE - No conversation history found in discussion.db")
            return False

    except Exception as e:
        logger.error(f"💬 CONVERSATION_RESTORE_ERROR - Failed to load conversation history from discussion.db: {e}")
        return False


log = slog.LogManager(logger)


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
            self.event_loop = None  # Will be set when generator starts
            logger.bind(name='sse').info('SSE Broadcaster initialized')
            self._initialized = True

    async def generator(self):
        # Store the event loop reference when generator starts (client connected)
        if not hasattr(self, 'event_loop') or self.event_loop is None:
            self.event_loop = asyncio.get_running_loop()
            logger.bind(name='sse').info('🔄 SSE event loop reference stored for restart notifications')

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
            with open(f'assets/prompts/{prompt_or_filename}', 'r') as f:
                content = f.read()
                logger.debug(f'Successfully loaded prompt: {content[:100]}...')
                return content
        except FileNotFoundError:
            plugin_name = None
            for name, plugin_instance in plugin_instances.items():
                if hasattr(plugin_instance, 'TRAINING_PROMPT') and plugin_instance.TRAINING_PROMPT == prompt_or_filename:
                    plugin_name = plugin_instance.DISPLAY_NAME
                    break
            if plugin_name:
                logger.warning(f'No training file found for {prompt_or_filename} (used by {plugin_name})')
            else:
                logger.warning(f'No training file found for {prompt_or_filename}')
            return None  # Prevents writing noise to the conversation history
    return prompt_or_filename


if MAX_LLM_RESPONSE_WORDS:
    limiter = f'in under {MAX_LLM_RESPONSE_WORDS} {TONE} words'
else:
    limiter = ''


def monitor_conversation_efficiency():
    """Monitor conversation history efficiency for Gemma 3:4B (128k context window)

    This function analyzes the current conversation history to provide insights
    on context window usage and deque efficiency.
    """
    try:
        # Context window metrics for Gemma 3:4B
        context_window_size = 128000  # 128k tokens
        conservative_usage = 0.7  # Use 70% for history
        available_tokens = context_window_size * conservative_usage

        # Calculate current usage if conversation history exists
        if 'global_conversation_history' in globals():
            current_messages = len(global_conversation_history)
            total_chars = sum(len(msg.get('content', '')) for msg in global_conversation_history)
            estimated_tokens = total_chars * 0.25  # 4 chars per token estimate
            context_usage = (estimated_tokens / context_window_size) * 100

            logger.info(f"📊 CONVERSATION_MONITOR: Current usage: {current_messages} messages, ~{estimated_tokens:.0f} tokens ({context_usage:.1f}% of 128k)")
        else:
            logger.info(f"📊 CONVERSATION_MONITOR: Context window optimized for Gemma 3:4B")
            logger.info(f"📊 CONVERSATION_MONITOR: Max conversation length: {MAX_CONVERSATION_LENGTH} messages")
            logger.info(f"📊 CONVERSATION_MONITOR: Available tokens for history: {available_tokens:,.0f} tokens")

            # Calculate theoretical efficiency
            theoretical_tokens = MAX_CONVERSATION_LENGTH * 150
            theoretical_usage = (theoretical_tokens / context_window_size) * 100
            logger.info(f"📊 CONVERSATION_MONITOR: Theoretical usage: {theoretical_tokens:,.0f} tokens ({theoretical_usage:.1f}% of context)")

        return True

    except Exception as e:
        logger.error(f"📊 CONVERSATION_MONITOR: Error monitoring conversation efficiency: {e}")
        return False


global_conversation_history = deque(maxlen=MAX_CONVERSATION_LENGTH)
conversation = [{'role': 'system', 'content': read_training('system_prompt.md')}]


def append_to_conversation(message=None, role='user'):
    """Append a message to the conversation history using in-memory storage.

    ⚠️  CRITICAL: SQLite Locking Prevention
    ═══════════════════════════════════════════════════════════════════════════════════
    This function was refactored to use simple in-memory conversation storage instead of
    the append-only conversation system. The append-only system created concurrent SQLite
    connections that caused database locking conflicts, leading to silent failures in 
    profile creation and other database operations.
    
    🔍 DEBUGGING: Conversation History Verification Commands
    ═══════════════════════════════════════════════════════════════════════════════════
    If conversation history seems missing after restart/environment switch:
    
    # Check in-memory vs database conversation count:
    python -c "from server import global_conversation_history; print(f'Memory: {len(global_conversation_history)} messages')"
    python -c "import sqlite3, json; from server import get_db_filename; conn = sqlite3.connect(get_db_filename()); cursor = conn.cursor(); cursor.execute('SELECT value FROM store WHERE key=\"llm_conversation_history\"'); result = cursor.fetchone(); print(f'Database: {len(json.loads(result[0])) if result else 0} messages'); conn.close()"
    
    Root Cause: modules.append_only_conversation.get_conversation_system() creates a
    separate SQLite connection to data/discussion.db while the main app uses 
    data/botifython.db. SQLite doesn't handle concurrent connections well, causing
    transaction corruption and data loss.
    
    Solution: Use simple in-memory deque for conversation history. This eliminates the
    SQLite locking issue while preserving all conversation functionality.
    ═══════════════════════════════════════════════════════════════════════════════════

    Args:
        message (str, optional): The message content to append. If None, returns current history.
        role (str, optional): The role of the message sender. Defaults to 'user'.

    Returns:
        list: The complete conversation history after appending.
    """
    global global_conversation_history

    if message is None:
        # Return current conversation history as list
        return list(global_conversation_history)

    # Append to in-memory conversation history
    global_conversation_history.append({'role': role, 'content': message})
    
    # Generate a simple incrementing message ID for logging compatibility
    message_id = len(global_conversation_history)
    logger.info(f"💬 FINDER_TOKEN: MESSAGE_APPENDED - ID:{message_id}, Role:{role}, Content:{message[:50]}...")
    
    # Log conversation state for debugging
    logger.debug(f"💬 CONVERSATION_STATE: {len(global_conversation_history)} total messages in memory")
    
    return list(global_conversation_history)


def get_home_menu_item() -> str:
    """Returns the appropriate home menu item text based on the HOME_APP setting."""
    home_app_name = getattr(CFG, 'HOME_APP', '030_roles')  # Default to '030_roles'
    return friendly_names.get(home_app_name, title_name(home_app_name))


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
        return get_home_menu_item()
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
                # Use Rich JSON display for pipeline changes
                formatted_changes = slog.rich_json_display(changes, console_output=False, log_output=True)
                log.debug('pipeline', f"Pipeline '{url}' detailed changes", formatted_changes)
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
    UNLOCK_BUTTON_LABEL = '🔓 Unlock'

    def __init__(self, pipeline_table, chat_instance=None):
        """Initialize Pipulate with required dependencies.

        Args:
            pipeline_table: The database table for storing pipeline state
            chat_instance: Optional chat coordinator instance
        """
        self.pipeline_table = pipeline_table
        self.chat = chat_instance
        self.message_queue = self.OrderedMessageQueue()

    def append_to_conversation_from_instance(self, message: str, role: str = 'user'):
        """Instance method wrapper for the global append_to_conversation function."""
        return append_to_conversation(message, role=role)

    def append_to_history(self, message: str, role: str = 'system') -> None:
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
            self._step_started = False
            self._step_complete = False
            self._workflow_context = None

        async def add(self, pipulate, message, **kwargs):
            """Add a message to the queue and process if not already processing.

            This method no longer handles conversation history - that's now managed by pipulate.stream.
            """
            logger.info(f'[🔄 QUEUEING] {message[:100]}...')
            self.queue.append((pipulate, message, kwargs))
            if not self._processing:
                await self._process_queue()

        async def _process_queue(self):
            """Process messages in the queue.

            This method now focuses solely on queue processing and streaming,
            leaving conversation history management to pipulate.stream.
            """
            if self._processing:
                return

            self._processing = True
            try:
                while self.queue:
                    pipulate, message, kwargs = self.queue.pop(0)
                    await pipulate.stream(message, **kwargs)
            finally:
                self._processing = False

        def mark_step_complete(self, step_num):
            """Mark a step as completed."""
            self._current_step = step_num
            self._step_complete = True

        def mark_step_started(self, step_num):
            """Mark a step as started but not completed."""
            self._current_step = step_num
            self._step_started = True

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

    def step_button(self, visual_step_number: str, preserve: bool = False, revert_label: str = None) -> str:
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

    def get_ui_constants(self):
        """Access centralized UI constants through dependency injection."""
        return CFG.UI_CONSTANTS

    def get_config(self):
        """Access centralized configuration through dependency injection."""
        return CFG

    def get_button_border_radius(self):
        """Get the global button border radius setting."""
        return CFG.UI_CONSTANTS['BUTTON_STYLES']['BORDER_RADIUS']

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

    async def log_api_call_details(self, pipeline_id: str, step_id: str, call_description: str, http_method: str, url: str, headers: dict, payload: Optional[dict] = None, response_status: Optional[int] = None, response_preview: Optional[str] = None, response_data: Optional[dict] = None, curl_command: Optional[str] = None, python_command: Optional[str] = None, estimated_rows: Optional[int] = None, actual_rows: Optional[int] = None, file_path: Optional[str] = None, file_size: Optional[str] = None, notes: Optional[str] = None):
        """Log complete API call details for extreme observability and Jupyter reproduction.

        This provides the same level of transparency for API calls as is used in BQL query logging,
        including copy-paste ready Python code for Jupyter notebook reproduction.
        """
        log_entry_parts = []
        log_entry_parts.append(f'  [API Call] {call_description or "API Request"}')
        log_entry_parts.append(f'  Pipeline ID: {pipeline_id}')
        log_entry_parts.append(f'  Step ID: {step_id}')
        log_entry_parts.append(f'  Method: {http_method}')
        log_entry_parts.append(f'  URL: {url}')
        if headers:
            headers_preview = {k: v for k, v in headers.items() if k.lower() not in ['authorization', 'cookie', 'x-api-key']}
            if len(headers_preview) != len(headers):
                headers_preview['<REDACTED_AUTH_HEADERS>'] = f'{len(headers) - len(headers_preview)} hidden'
            # Use Rich JSON display for headers
            pretty_headers = slog.rich_json_display(headers_preview, title="API Headers", console_output=True, log_output=True)
            log_entry_parts.append(f'  Headers: {pretty_headers}')
        if payload:
            try:
                # Use Rich JSON display for payload
                pretty_payload = slog.rich_json_display(payload, title="API Payload", console_output=True, log_output=True)
                log_entry_parts.append(f'  Payload:\n{pretty_payload}')
            except Exception:
                log_entry_parts.append(f'  Payload: {payload}')
        if curl_command:
            log_entry_parts.append(f'  cURL Command:\n{curl_command}')
        if python_command:
            # Use centralized emoji configuration for console messages
            python_emoji = CFG.UI_CONSTANTS['EMOJIS']['PYTHON_CODE']
            snippet_emoji = CFG.UI_CONSTANTS['EMOJIS']['CODE_SNIPPET']
            comment_divider = CFG.UI_CONSTANTS['CODE_FORMATTING']['COMMENT_DIVIDER']
            snippet_intro = CFG.UI_CONSTANTS['CONSOLE_MESSAGES']['PYTHON_SNIPPET_INTRO'].format(
                python_emoji=python_emoji,
                snippet_emoji=snippet_emoji
            )
            snippet_end = CFG.UI_CONSTANTS['CONSOLE_MESSAGES']['PYTHON_SNIPPET_END'].format(
                python_emoji=python_emoji,
                snippet_emoji=snippet_emoji
            )
            # Add Python snippet with complete BEGIN/END block
            log_entry_parts.append(f'{snippet_intro}\n{python_command}')
            log_entry_parts.append('# Note: The API token should be loaded from a secure file location.')
            log_entry_parts.append(f'{comment_divider}')
            log_entry_parts.append(f'{snippet_end}')
        if estimated_rows is not None:
            log_entry_parts.append(f'  Estimated Rows (from pre-check): {estimated_rows:,}')
        if actual_rows is not None:
            log_entry_parts.append(f'  Actual Rows Downloaded: {actual_rows:,}')
        if response_status is not None:
            log_entry_parts.append(f'  Response Status: {response_status}')
        if response_preview:
            try:
                parsed = json.loads(response_preview)
                # Use Rich JSON display for response preview
                pretty_preview = slog.rich_json_display(parsed, title="API Response Preview", console_output=True, log_output=True)
                log_entry_parts.append(f'  Response Preview:\n{pretty_preview}')
            except Exception:
                log_entry_parts.append(f'  Response Preview:\n{response_preview}')

        # Enhanced transparency for discovery endpoints - log full response data
        is_discovery_endpoint = self._is_discovery_endpoint(url)
        if response_data and is_discovery_endpoint:
            try:
                # Use Rich JSON display for discovery response
                pretty_response = slog.rich_json_display(response_data, title=f"🔍 Discovery Response: {call_description}", console_output=True, log_output=True)
                log_entry_parts.append(f'  🔍 FULL RESPONSE DATA (Discovery Endpoint):\n{pretty_response}')

            except Exception as e:
                log_entry_parts.append(f'  🔍 FULL RESPONSE DATA (Discovery Endpoint): [Error formatting JSON: {e}]\n{response_data}')

                # Still display in console even if JSON formatting fails
                slog.console.print(f"❌ Discovery Response Error: {e}", style="red")
                slog.console.print(f"Raw data: {str(response_data)}", style="dim")

        if file_path:
            log_entry_parts.append(f'  Associated File Path: {file_path}')
        if file_size:
            log_entry_parts.append(f'  Associated File Size: {file_size}')
        if notes:
            log_entry_parts.append(f'  Notes: {notes}')

        full_log_message = '\n'.join(log_entry_parts)
        logger.info(f'\n🚀 === API CALL TRANSPARENCY ===\n{full_log_message}\n🚀 === END API TRANSPARENCY ===')
        is_bql = 'bql' in (call_description or '').lower() or 'botify query language' in (call_description or '').lower()

    def _is_discovery_endpoint(self, url: str) -> bool:
        """Detect if this is a key discovery endpoint that should have full response logging.

        Args:
            url: The API endpoint URL

        Returns:
            bool: True if this is a discovery endpoint that should log full response data
        """
        discovery_patterns = [
            '/analyses/',  # Covers both /analyses/{username}/{project}/light and regular analyses
            '/advanced_export',  # Field discovery endpoint
        ]

        return any(pattern in url for pattern in discovery_patterns)

    async def log_mcp_call_details(self, operation_id: str, tool_name: str, operation_type: str, mcp_block: str = None, request_payload: Optional[dict] = None, response_data: Optional[dict] = None, response_status: Optional[int] = None, external_api_url: Optional[str] = None, external_api_method: str = 'GET', external_api_headers: Optional[dict] = None, external_api_payload: Optional[dict] = None, external_api_response: Optional[dict] = None, external_api_status: Optional[int] = None, execution_time_ms: Optional[float] = None, notes: Optional[str] = None):
        """Log complete MCP operation details for extreme observability and Jupyter reproduction.

        This provides the same level of transparency for MCP operations as the BQL query logging,
        including copy-paste ready Python code for external API reproduction.

        Args:
            operation_id: Unique identifier for this MCP operation
            tool_name: Name of the MCP tool being executed
            operation_type: Type of operation (tool_execution, api_call, etc.)
            mcp_block: Raw MCP block that triggered the operation
            request_payload: Payload sent to MCP tool executor
            response_data: Response from MCP tool executor
            response_status: HTTP status from MCP tool executor
            external_api_url: URL of external API called (if any)
            external_api_method: HTTP method for external API
            external_api_headers: Headers sent to external API
            external_api_payload: Payload sent to external API
            external_api_response: Response from external API
            external_api_status: HTTP status from external API
            execution_time_ms: Total execution time in milliseconds
            notes: Additional context or notes
        """
        log_entry_parts = []
        log_entry_parts.append(f'  [MCP Operation] {operation_type.title()} - {tool_name}')
        log_entry_parts.append(f'  Operation ID: {operation_id}')
        log_entry_parts.append(f'  Tool Name: {tool_name}')
        log_entry_parts.append(f'  Operation Type: {operation_type}')
        log_entry_parts.append(f'  Timestamp: {self.get_timestamp()}')

        if execution_time_ms is not None:
            log_entry_parts.append(f'  Execution Time: {execution_time_ms:.2f}ms')

        # MCP Block Details
        if mcp_block:
            log_entry_parts.append(f'  MCP Block:')
            # Indent each line of the MCP block for better readability
            indented_block = '\n'.join(f'    {line}' for line in mcp_block.strip().split('\n'))
            log_entry_parts.append(indented_block)

        # Internal MCP Tool Executor Request
        if request_payload:
            log_entry_parts.append('')  # Extra space for visual separation
            log_entry_parts.append(f'  MCP Tool Executor Request:')
            log_entry_parts.append(f'    URL: http://127.0.0.1:5001/mcp-tool-executor')
            log_entry_parts.append(f'    Method: POST')
            try:
                # Use Rich JSON display for MCP request payload
                pretty_payload = slog.rich_json_display(request_payload, title="MCP Tool Executor Request", console_output=True, log_output=True)
                # Indent the JSON for consistency
                indented_payload = '\n'.join(f'    {line}' for line in pretty_payload.split('\n'))
                log_entry_parts.append(f'    Payload:\n{indented_payload}')
            except Exception:
                log_entry_parts.append(f'    Payload: {request_payload}')

        # Internal MCP Tool Executor Response
        if response_data or response_status:
            log_entry_parts.append('')  # Extra space for visual separation
            log_entry_parts.append(f'  MCP Tool Executor Response:')
            if response_status:
                log_entry_parts.append(f'    Status: {response_status}')
            if response_data:
                try:
                    # Use Rich JSON display for MCP response data
                    pretty_response = slog.rich_json_display(response_data, title="MCP Tool Executor Response", console_output=True, log_output=True)
                    # Indent the JSON for consistency
                    indented_response = '\n'.join(f'    {line}' for line in pretty_response.split('\n'))
                    log_entry_parts.append(f'    Response:\n{indented_response}')
                except Exception:
                    log_entry_parts.append(f'    Response: {response_data}')

        # External API Call Details (the actual external service)
        if external_api_url:
            log_entry_parts.append('')  # Extra space for visual separation
            log_entry_parts.append(f'  External API Call:')
            log_entry_parts.append(f'    URL: {external_api_url}')
            log_entry_parts.append(f'    Method: {external_api_method}')

            if external_api_headers:
                # Redact sensitive headers
                headers_preview = {k: v for k, v in external_api_headers.items() if k.lower() not in ['authorization', 'cookie', 'x-api-key']}
                if len(headers_preview) != len(external_api_headers):
                    headers_preview['<REDACTED_AUTH_HEADERS>'] = f'{len(external_api_headers) - len(headers_preview)} hidden'
                # Use Rich JSON display for external API headers
                pretty_headers = slog.rich_json_display(headers_preview, title="External API Headers", console_output=True, log_output=True)
                log_entry_parts.append(f'    Headers: {pretty_headers}')

            if external_api_payload:
                try:
                    # Use Rich JSON display for external API payload
                    pretty_payload = slog.rich_json_display(external_api_payload, title="External API Payload", console_output=True, log_output=True)
                    indented_payload = '\n'.join(f'    {line}' for line in pretty_payload.split('\n'))
                    log_entry_parts.append(f'    Payload:\n{indented_payload}')
                except Exception:
                    log_entry_parts.append(f'    Payload: {external_api_payload}')

            if external_api_status:
                log_entry_parts.append(f'    Response Status: {external_api_status}')

            if external_api_response:
                try:
                    # Use Rich JSON display for external API response
                    pretty_response = slog.rich_json_display(external_api_response, title="External API Response", console_output=True, log_output=True)
                    indented_response = '\n'.join(f'    {line}' for line in pretty_response.split('\n'))
                    log_entry_parts.append(f'    Response:\n{indented_response}')
                except Exception:
                    log_entry_parts.append(f'    Response: {external_api_response}')

        # Generate copy-paste ready Python code for Jupyter reproduction
        if external_api_url:
            python_code = self._generate_mcp_python_code(
                tool_name=tool_name,
                external_api_url=external_api_url,
                external_api_method=external_api_method,
                external_api_headers=external_api_headers,
                external_api_payload=external_api_payload,
                operation_id=operation_id
            )

            # Use centralized emoji configuration for console messages
            python_emoji = CFG.UI_CONSTANTS['EMOJIS']['PYTHON_CODE']
            snippet_emoji = CFG.UI_CONSTANTS['EMOJIS']['CODE_SNIPPET']
            comment_divider = CFG.UI_CONSTANTS['CODE_FORMATTING']['COMMENT_DIVIDER']
            snippet_intro = CFG.UI_CONSTANTS['CONSOLE_MESSAGES']['PYTHON_SNIPPET_INTRO'].format(
                python_emoji=python_emoji,
                snippet_emoji=snippet_emoji
            )
            snippet_end = CFG.UI_CONSTANTS['CONSOLE_MESSAGES']['PYTHON_SNIPPET_END'].format(
                python_emoji=python_emoji,
                snippet_emoji=snippet_emoji
            )

            # Add Python snippet with complete BEGIN/END block and visual separation
            log_entry_parts.append('')  # Extra space before Python code
            log_entry_parts.append(f'{snippet_intro}')
            log_entry_parts.append(f'{comment_divider}')
            log_entry_parts.append(f'{python_code}')
            log_entry_parts.append('# Note: This code reproduces the external API call made by the MCP tool.')
            log_entry_parts.append(f'{comment_divider}')
            log_entry_parts.append(f'{snippet_end}')
            log_entry_parts.append('')  # Extra space after Python code

        if notes:
            log_entry_parts.append(f'  Notes: {notes}')

        full_log_message = '\n'.join(log_entry_parts)
        logger.info(f'\n🚀 === MCP OPERATION TRANSPARENCY ===\n{full_log_message}\n🚀 === END MCP TRANSPARENCY ===')

    def _generate_mcp_python_code(self, tool_name: str, external_api_url: str, external_api_method: str = 'GET', external_api_headers: Optional[dict] = None, external_api_payload: Optional[dict] = None, operation_id: str = None) -> str:
        """Generate copy-paste ready Python code for reproducing MCP external API calls in Jupyter.

        This mirrors the pattern used in BQL query logging but for MCP operations.
        """
        lines = []
        lines.append(f'# MCP Tool Reproduction: {tool_name}')
        if operation_id:
            lines.append(f'# Operation ID: {operation_id}')
        lines.append(f'# Generated at: {self.get_timestamp()}')
        lines.append('')
        lines.append('import aiohttp')
        lines.append('import asyncio')
        lines.append('import json')
        lines.append('from pprint import pprint')
        lines.append('')
        lines.append('async def reproduce_mcp_call():')
        lines.append('    """Reproduce the external API call made by the MCP tool."""')
        lines.append('    ')
        lines.append(f'    url = "{external_api_url}"')
        lines.append(f'    method = "{external_api_method.upper()}"')
        lines.append('    ')

        # Headers
        if external_api_headers:
            lines.append('    headers = {')
            for key, value in external_api_headers.items():
                if key.lower() in ['authorization', 'cookie', 'x-api-key']:
                    lines.append(f'        "{key}": "REDACTED_FOR_SECURITY",')
                else:
                    lines.append(f'        "{key}": "{value}",')
            lines.append('    }')
        else:
            lines.append('    headers = {}')
        lines.append('    ')

        # Payload
        if external_api_payload and external_api_method.upper() in ['POST', 'PUT', 'PATCH']:
            lines.append('    payload = {')
            try:
                for key, value in external_api_payload.items():
                    if isinstance(value, str):
                        lines.append(f'        "{key}": "{value}",')
                    else:
                        lines.append(f'        "{key}": {json.dumps(value)},')
            except Exception:
                lines.append(f'        # Payload: {external_api_payload}')
            lines.append('    }')
        else:
            lines.append('    payload = None')
        lines.append('    ')

        # Async session and request
        lines.append('    async with aiohttp.ClientSession() as session:')
        if external_api_method.upper() == 'GET':
            lines.append('        async with session.get(url, headers=headers) as response:')
        elif external_api_method.upper() == 'POST':
            lines.append('        async with session.post(url, headers=headers, json=payload) as response:')
        elif external_api_method.upper() == 'PUT':
            lines.append('        async with session.put(url, headers=headers, json=payload) as response:')
        elif external_api_method.upper() == 'DELETE':
            lines.append('        async with session.delete(url, headers=headers) as response:')
        else:
            lines.append(f'        async with session.request("{external_api_method.upper()}", url, headers=headers, json=payload) as response:')

        lines.append('            print(f"Status: {response.status}")')
        lines.append('            print(f"Headers: {dict(response.headers)}")')
        lines.append('            ')
        lines.append('            if response.content_type == "application/json":')
        lines.append('                data = await response.json()')
        lines.append('                print("JSON Response:")')
        lines.append('                pprint(data)')
        lines.append('                return data')
        lines.append('            else:')
        lines.append('                text = await response.text()')
        lines.append('                print("Text Response:")')
        lines.append('                print(text)')
        lines.append('                return text')
        lines.append('')
        divider = CFG.UI_CONSTANTS['CODE_FORMATTING']['COMMENT_DIVIDER']
        lines.append(divider)
        lines.append('# EXECUTION: Choose your environment')
        lines.append(divider)
        lines.append('')
        lines.append('# For Jupyter Notebooks (recommended):')
        lines.append('result = await reproduce_mcp_call()')
        lines.append('print("\\nFinal result:")')
        lines.append('pprint(result)')
        lines.append('')
        lines.append('# For Python scripts (uncomment if needed):')
        lines.append('# if __name__ == "__main__":')
        lines.append('#     result = asyncio.run(reproduce_mcp_call())')
        lines.append('#     print("\\nFinal result:")')
        lines.append('#     pprint(result)')

        return '\n'.join(lines)

    # ========================================
    # REUSABLE BOTIFY PYTHON CODE GENERATION
    # ========================================

    def generate_botify_code_header(self, display_name: str, step_name: str, username: str, project_name: str,
                                    template_info: dict = None, qualifier_config: dict = None) -> list:
        """Generate standardized header for Botify Python debugging code.

        Delegates to external botify_code_generation module to reduce server.py size.
        """
        return botify_code_generation.generate_botify_code_header(
            display_name=display_name,
            step_name=step_name,
            username=username,
            project_name=project_name,
            template_info=template_info,
            qualifier_config=qualifier_config
        )

    def generate_botify_token_loader(self) -> str:
        """Generate the standard Botify token loading function.

        Delegates to external botify_code_generation module to reduce server.py size.
        """
        return botify_code_generation.generate_botify_token_loader()

    def generate_botify_http_client(self, client_name: str, description: str) -> str:
        """Generate the standard HTTP client function for Botify APIs.

        Delegates to external botify_code_generation module to reduce server.py size.
        """
        return botify_code_generation.generate_botify_http_client(client_name, description)

    def generate_botify_main_executor(self, client_function_name: str, api_description: str) -> str:
        """Generate the main execution function for Botify APIs.

        Delegates to external botify_code_generation module to reduce server.py size.
        """
        return botify_code_generation.generate_botify_main_executor(client_function_name, api_description)

    def create_folder_button(self, folder_path: str, icon: str = "📁", text: str = "Open Folder",
                             title_prefix: str = "Open folder") -> object:
        """Generate a standardized folder opening button.

        Centralizes the folder button pattern used across many plugins.
        """
        import urllib.parse

        from fasthtml.common import A

        quoted_path = urllib.parse.quote(str(folder_path))
        title = f"{title_prefix}: {folder_path}"

        return A(
            f"{icon} {text}",
            hx_get=f"/open-folder?path={quoted_path}",
            hx_swap="none",
            title=title,
            cls="button-link"
        )

    # ========================================
    # ADVANCED BOTIFY CODE GENERATION UTILITIES
    # ========================================

    def generate_botify_bqlv2_python_code(self, query_payload, username, project_name, page_size, jobs_payload, display_name, get_step_name_from_payload_func, get_configured_template_func=None, query_templates=None):
        """
        🚀 REUSABLE UTILITY: Generate complete Python code for BQLv2 queries (crawl, GSC)

        Delegates to external botify_code_generation module to reduce server.py size.
        """
        return botify_code_generation.generate_botify_bqlv2_python_code(
            query_payload=query_payload,
            username=username,
            project_name=project_name,
            page_size=page_size,
            jobs_payload=jobs_payload,
            display_name=display_name,
            get_step_name_from_payload_func=get_step_name_from_payload_func,
            get_configured_template_func=get_configured_template_func,
            query_templates=query_templates
        )

    def generate_botify_bqlv1_python_code(self, query_payload, username, project_name, jobs_payload, display_name, get_step_name_from_payload_func):
        """
        🚀 REUSABLE UTILITY: Generate complete Python code for BQLv1 queries (web logs)

        Delegates to external botify_code_generation module to reduce server.py size.
        """
        return botify_code_generation.generate_botify_bqlv1_python_code(
            query_payload=query_payload,
            username=username,
            project_name=project_name,
            jobs_payload=jobs_payload,
            display_name=display_name,
            get_step_name_from_payload_func=get_step_name_from_payload_func
        )

    def get_botify_analysis_path(self, app_name, username, project_name, analysis_slug, filename=None):
        """
        🚀 REUSABLE UTILITY: Construct standardized Botify analysis file paths

        Delegates to external botify_code_generation module to reduce server.py size.
        """
        return botify_code_generation.get_botify_analysis_path(app_name, username, project_name, analysis_slug, filename)

    def fmt(self, endpoint: str) -> str:
        """Format an endpoint string into a human-readable form."""
        if endpoint in friendly_names:
            return friendly_names[endpoint]
        return title_name(endpoint)

    def _get_clean_state(self, pkey):
        try:
            record = self.pipeline_table[pkey]
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
    def initialize_if_missing(self, pkey: str, initial_step_data: dict = None) -> tuple[Optional[dict], Optional[Card]]:
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
            self.pipeline_table.insert({'pkey': pkey, 'app_name': app_name if app_name else None, 'data': json.dumps(state), 'created': now, 'updated': now})
            return (state, None)
        except:
            error_card = Card(H3('ID Already In Use'), P(f"The ID '{pkey}' is already being used by another workflow. Please try a different ID."), style=self.id_conflict_style())
            return (None, error_card)

    def read_state(self, pkey: str) -> dict:
        logger.debug(f'Reading state for pipeline: {pkey}')
        try:
            self.pipeline_table.xtra(pkey=pkey)
            records = self.pipeline_table()
            logger.debug(f'Records found: {records}')
            if records:
                logger.debug(f'First record type: {type(records[0])}')
                logger.debug(f'First record dir: {dir(records[0])}')
            if records and hasattr(records[0], 'data'):
                state = json.loads(records[0].data)
                # Use Rich JSON display for found state
                formatted_state = slog.rich_json_display(state, console_output=False, log_output=True)
                logger.debug(f'Found state: {formatted_state}')
                return state
            logger.debug('No valid state found')
            return {}
        except Exception as e:
            logger.debug(f'Error reading state: {str(e)}')
            return {}

    def write_state(self, pkey: str, state: dict) -> None:
        state['updated'] = datetime.now().isoformat()
        payload = {'pkey': pkey, 'data': json.dumps(state), 'updated': state['updated']}
        # Use Rich JSON display for debug payload
        formatted_payload = slog.rich_json_display(payload, console_output=False, log_output=True)
        logger.debug(f'Update payload:\n{formatted_payload}')
        self.pipeline_table.update(payload)
        verification = self.read_state(pkey)
        # Use Rich JSON display for verification
        formatted_verification = slog.rich_json_display(verification, console_output=False, log_output=True)
        logger.debug(f'Verification read:\n{formatted_verification}')

    def format_links_in_text(self, text):
        """
        Convert plain URLs in text to clickable HTML links.
        Safe for logging but renders as HTML in the UI.
        """
        url_pattern = 'https?://(?:[-\\w.]|(?:%[\\da-fA-F]{2}))+'

        def replace_url(match):
            url = match.group(0)
            return f'<a href="{url}" target="_blank">{url}</a>'
        return re.sub(url_pattern, replace_url, text)

    async def stream(self, message, **kwargs):
        """Wrapper that delegates to the external stream orchestrator."""
        from imports.stream_orchestrator import stream_orchestrator # Import just-in-time
        # Correctly pass self (pipulate_instance), self.chat (chat_instance), and message
        return await stream_orchestrator(self, self.chat, message, **kwargs)

    async def _handle_llm_stream(self):
        """Handles the logic for an interruptible LLM stream."""
        try:
            await self.chat.broadcast('%%STREAM_START%%')
            conversation_history = append_to_conversation()
            response_text = ''
    
            logger.info("ORCHESTRATOR: Entering LLM stream loop.")
            async for chunk in process_llm_interaction(MODEL, conversation_history):
                await self.chat.broadcast(chunk)
                response_text += chunk
            logger.info(f"ORCHESTRATOR: Exited LLM stream loop. Full response_text: '{response_text}'")
        except asyncio.CancelledError:
            logger.info("LLM stream was cancelled by user.")
        except Exception as e:
            logger.error(f'Error in LLM stream: {e}', exc_info=True)
            raise
        finally:
            await self.chat.broadcast('%%STREAM_END%%')
            logger.debug("LLM stream finished or cancelled, sent %%STREAM_END%%")

    def display_revert_header(self, step_id: str, app_name: str, steps: list, message: str = None, target_id: str = None, revert_label: str = None, remove_padding: bool = False, show_when_finalized: bool = False):
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
            show_when_finalized: Whether to show content when workflow is finalized (default: False for backward compatibility)

        Returns:
            Card: A FastHTML Card component with revert functionality, or None if finalized and show_when_finalized=False
        """
        pipeline_id = db.get('pipeline_id', '')
        finalize_step = steps[-1] if steps and steps[-1].id == 'finalize' else None
        if pipeline_id and finalize_step and not show_when_finalized:
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
        form = Form(Input(type='hidden', name='step_id', value=step_id), Button(self.step_button(visual_step_number, refill, revert_label), type='submit', cls='button-revert', aria_label=f'Revert to step {visual_step_number}: {step.show}', title=f'Go back to modify {step.show}'), hx_post=f'/{app_name}/revert', hx_target=f'#{target_id}', hx_swap='outerHTML', role='form', aria_label=f'Revert to {step.show} form')
        if not message:
            return form
        article_style = 'display: flex; align-items: center; justify-content: space-between; background-color: var(--pico-card-background-color);'
        if remove_padding:
            article_style += ' padding: 0;'
        return Card(Div(message, style='flex: 1', role='status', aria_label=f'Step result: {message}'), Div(form, style='flex: 0'), style=article_style, role='region', aria_label=f'Step {visual_step_number} controls')

    def display_revert_widget(self, step_id: str, app_name: str, steps: list, message: str = None, widget=None, target_id: str = None, revert_label: str = None, widget_style=None, finalized_content=None, next_step_id: str = None):
        """Create a standardized container for widgets and visualizations.

        Core pattern for displaying rich content below workflow steps with consistent
        styling and DOM targeting for dynamic updates.

        Features:
        - Consistent padding/spacing with revert controls
        - Unique DOM addressing for targeted updates
        - Support for function-based widgets and AnyWidget components
        - Standard styling with override capability
        - Automatic finalized state handling with chain reaction preservation

        Args:
            step_id: ID of the step this widget belongs to
            app_name: Workflow app name
            steps: List of Step namedtuples defining the workflow
            message: Optional message for revert control
            widget: Widget/visualization to display
            target_id: Optional HTMX update target
            revert_label: Optional custom revert button label
            widget_style: Optional custom widget container style
            finalized_content: Content to show when workflow is finalized (if None, uses message with 🔒)
            next_step_id: Next step ID for chain reaction when finalized

        Returns:
            Div: FastHTML container with revert control and widget content, or locked Card when finalized
        """
        # Check if workflow is finalized
        pipeline_id = db.get('pipeline_id', '')
        finalize_step = steps[-1] if steps and steps[-1].id == 'finalize' else None
        is_finalized = False
        if pipeline_id and finalize_step:
            final_data = self.get_step_data(pipeline_id, finalize_step.id, {})
            is_finalized = finalize_step.done in final_data

        if is_finalized:
            # Create locked view for finalized workflow
            step = next((s for s in steps if s.id == step_id), None)
            step_title = step.show if step else step_id

            if finalized_content is None:
                finalized_content = P(f"Step completed: {message or step_title}")

            locked_card = Card(
                H3(f"🔒 {step_title}", role='heading', aria_level='3'),
                Div(finalized_content, cls='custom-card-padding-bg', role='status', aria_label=f'Finalized content for {step_title}'),
                role='region',
                aria_label=f'Finalized step: {step_title}'
            )

            # Add next step trigger if provided
            if next_step_id:
                return Div(
                    locked_card,
                    Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                    id=step_id
                )
            else:
                return Div(locked_card, id=step_id)

        # Normal revert widget behavior for non-finalized workflows
        revert_row = self.display_revert_header(step_id=step_id, app_name=app_name, steps=steps, message=message, target_id=target_id, revert_label=revert_label, remove_padding=True)
        if widget is None or revert_row is None:
            return revert_row

        # Use CSS class for widget content styling, allow custom widget_style override
        widget_container_attrs = {
            'id': f'{step_id}-widget-{hash(str(widget))}',
            'role': 'region',
            'aria_label': f'Widget content for {step_id}'
        }
        if widget_style:
            widget_container_attrs['style'] = widget_style
        else:
            widget_container_attrs['cls'] = 'widget-content'

        return Div(revert_row, Div(widget, **widget_container_attrs), id=f'{step_id}-content', cls='card-container', role='article', aria_label=f'Step content: {step_id}')

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
            return Pre(content, cls='tree-display-tree')
        else:
            return Pre(content, cls='tree-display-path')

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

        # Use CSS class for finalized content styling, allow custom content_style override
        content_container_attrs = {}
        if content_style:
            content_container_attrs['style'] = content_style
        else:
            content_container_attrs['cls'] = 'finalized-content'

        return Card(heading_tag(message), Div(content, **content_container_attrs), cls='card-container')

    def wrap_with_inline_button(self, input_element: Input, button_label: str = 'Next ▸', button_class: str = 'primary', show_new_key_button: bool = False, app_name: str = None) -> Div:
        """Wrap an input element with an inline button in a flex container.

        Args:
            input_element: The input element to wrap
            button_label: Text to display on the button (default: 'Next ▸')
            button_class: CSS class for the button (default: 'primary')
            show_new_key_button: Whether to show the 🆕 new key button (default: False)
            app_name: App name for new key generation (required if show_new_key_button=True)

        Returns:
            Div: A flex container with the input and button(s)
        """
        # Styles are now externalized to CSS classes for maintainability

        # Generate unique IDs for input-button association
        input_id = input_element.attrs.get('id') or f'input-{hash(str(input_element))}'
        button_id = f'btn-{input_id}'

        # Enhance input element with semantic attributes if not already present
        if 'aria_describedby' not in input_element.attrs:
            input_element.attrs['aria_describedby'] = button_id
        if 'id' not in input_element.attrs:
            input_element.attrs['id'] = input_id

        # Create enhanced button with semantic attributes
        enhanced_button = Button(
            button_label,
            type='submit',
            cls=f'{button_class} inline-button-submit',
            id=button_id,
            aria_label=f'Submit {input_element.attrs.get("placeholder", "input")}',
            title=f'Submit form ({button_label})'
        )

        # Prepare elements for container
        elements = [input_element, enhanced_button]

        # Add new key button if requested
        if show_new_key_button and app_name:
            ui_constants = CFG.UI_CONSTANTS
            # 🆕 New Key button styled via CSS class for maintainability
            new_key_button = Button(
                ui_constants['BUTTON_LABELS']['NEW_KEY'],
                type='button',  # Not a submit button
                cls='new-key-button',  # Externalized styling in styles.css
                id=f'new-key-{input_id}',
                hx_get=f'/generate-new-key/{app_name}',
                hx_target=f'#{input_id}',
                hx_swap='outerHTML',
                aria_label='Generate new pipeline key',
                title='Generate a new auto-incremented pipeline key'
            )
            elements.append(new_key_button)

        return Div(
            *elements,
            cls='inline-button-container',
            role='group',
            aria_label='Input with submit button' + (' and new key generator' if show_new_key_button else '')
        )

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
        # Standard display name derivation
        try:
            module_file = inspect.getfile(plugin_instance.__class__)
            blank_placeholder_module = importlib.import_module('plugins.910_blank_placeholder')
            derive_public_endpoint_from_filename = blank_placeholder_module.derive_public_endpoint_from_filename
            public_app_name_for_display = derive_public_endpoint_from_filename(Path(module_file).name)
        except (TypeError, AttributeError, ImportError):
            public_app_name_for_display = plugin_instance.APP_NAME

        title = plugin_instance.DISPLAY_NAME or public_app_name_for_display.replace("_", " ").title()

        # Standard pipeline key generation and matching records
        full_key, prefix, _ = self.generate_pipeline_key(plugin_instance)
        self.pipeline_table.xtra(app_name=plugin_instance.APP_NAME)
        matching_records = [record.pkey for record in self.pipeline_table() if record.pkey.startswith(prefix)]

        # Standard form with centralized constants
        ui_constants = CFG.UI_CONSTANTS
        landing_constants = CFG.UI_CONSTANTS['LANDING_PAGE']

        return Container(
            Card(
                H2(title, role='heading', aria_level='2'),
                P(plugin_instance.ENDPOINT_MESSAGE, cls='text-secondary', role='doc-subtitle'),
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
                            cls='contrast',
                            aria_label='Pipeline ID input',
                            aria_describedby='pipeline-help'
                        ),
                        button_label=ui_constants['BUTTON_LABELS']['ENTER_KEY'],
                        button_class=ui_constants['BUTTON_STYLES']['SECONDARY'],
                        show_new_key_button=True,
                        app_name=plugin_instance.APP_NAME
                    ),
                    self.update_datalist('pipeline-ids', options=matching_records, should_clear=not matching_records),
                    Small('Enter a new ID or select from existing pipelines', id='pipeline-help', cls='text-muted'),
                    hx_post=f'/{plugin_instance.APP_NAME}/init',
                    hx_target=f'#{plugin_instance.APP_NAME}-container',
                    role='form',
                    aria_label=f'Initialize {title} workflow'
                ),
                role='main',
                aria_label=f'{title} workflow landing page'
            ),
            Div(id=f'{plugin_instance.APP_NAME}-container', role='region', aria_label=f'{title} workflow content')
        )

    async def get_state_message(self, pkey: str, steps: list, messages: dict) -> str:
        state = self.read_state(pkey)
        logger.debug(f'\nDEBUG [{pkey}] State Check:')
        # Use Rich JSON display for state debug
        formatted_state = slog.rich_json_display(state, console_output=False, log_output=True)
        logger.debug(formatted_state)
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
            self.pipeline_table.xtra()
            self.pipeline_table.xtra(app_name=app_name)
            app_records = list(self.pipeline_table())
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

    def update_datalist(self, datalist_id, options=None, should_clear=False):
        """Create a datalist with out-of-band swap for updating dropdown options.

        This helper method allows easy updates to datalist options using HTMX's
        out-of-band swap feature. It can either update with new options or clear all options.

        Args:
            datalist_id: The ID of the datalist to update
            options: List of option values to include, or None to clear
            should_clear: If True, force clear all options regardless of options parameter

        Returns:
            Datalist: A FastHTML Datalist object with out-of-band swap attribute
        """
        if should_clear or options is None:
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
            return (False, error_msg, P(error_msg, cls='text-invalid'))
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

async def process_llm_interaction(MODEL: str, messages: list, base_app=None) -> AsyncGenerator[str, None]:
    # Import the formal MCP orchestrator for passive listening
    from imports.mcp_orchestrator import parse_mcp_request
    
    url = 'http://localhost:11434/api/chat'
    payload = {'MODEL': MODEL, 'messages': messages, 'stream': True}
    accumulated_response = []
    full_content_buffer = ""
    word_buffer = ""  # Buffer for word-boundary detection
    mcp_detected = False
    chunk_count = 0

    # 🎯 GOLDEN PATH EXECUTION MATRIX - ORCHESTRATOR STATUS:
    # ✅ WORKING: XML syntax <tool><params><url>value</url></params></tool>
    # ✅ WORKING: JSON syntax <tool><params>{"url": "value"}</params></tool>
    # 🟡 INTEGRATING: [cmd arg] bracket notation syntax (parser exists, integrating now)
    # 🔴 NOT YET: python -c "..." inline code execution
    # 🔴 NOT YET: python cli.py call forwarding from message stream
    #
    # 🎓 PROGRESSIVE REVEAL DESIGN FOR LLMs (simplest first):
    # Level 1: [mcp-discover] - Ultra-simple for small models
    # Level 2: .venv/bin/python cli.py mcp-discover - Terminal proficiency
    # Level 3: python -c "from imports.ai_tool_discovery_simple_parser import execute_simple_command..."
    # Level 4: <tool name="ai_self_discovery_assistant"><params>{"discovery_type":"capabilities"}</params></tool>
    # Level 5: <tool name="ai_self_discovery_assistant"><params><discovery_type>capabilities</discovery_type></params></tool>
    # Level 6: Formal MCP Protocol - Full conversation loop with automatic tool execution
    #
    # This orchestrator monitors LLM response streams for MCP tool calls.
    # When found, tools are executed asynchronously and results injected back.

    # Match XML/JSON tool tags AND bracket notation commands
    mcp_pattern = re.compile(r'(<mcp-request>.*?</mcp-request>|<tool\s+[^>]*/>|<tool\s+[^>]*>.*?</tool>|\[[^\]]+\])', re.DOTALL)

    logger.debug("🔍 DEBUG: === STARTING process_llm_interaction ===")
    logger.debug(f"🔍 DEBUG: MODEL='{MODEL}', messages_count={len(messages)}")

    # 🚨 TRANSPARENCY: Show COMPLETE conversation history being sent to LLM
    logger.info("🔍 TRANSPARENCY: === COMPLETE CONVERSATION HISTORY ===")
    for i, msg in enumerate(messages):
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        logger.info(f"🔍 TRANSPARENCY: Message {i}: [{role}] {content}")
    logger.info("🔍 TRANSPARENCY: === END CONVERSATION HISTORY ===")

    table = Table(title='User Input')
    table.add_column('Role', style='cyan')
    table.add_column('Content', style='orange3')
    if messages:
        # Show the current user input (last message should be the current user's message)
        current_message = messages[-1]
        role = current_message.get('role', 'unknown')
        content = current_message.get('content', '')
        if isinstance(content, dict):
            # Use Rich JSON display for LLM content formatting
            content = slog.rich_json_display(content, console_output=False, log_output=True)
        table.add_row(role, content)
        logger.debug(f"🔍 DEBUG: Current user input - role: {role}, content: '{content[:100]}...'")
    slog.print_and_log_table(table, "LLM DEBUG - ")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    error_msg = f'Ollama server error: {error_text}'
                    logger.error(f"🔍 DEBUG: HTTP Error {response.status}: {error_text}")
                    yield error_msg
                    return

                yield '\n'  # Start with a newline for better formatting in UI

                async for line in response.content:
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        chunk_count += 1

                        if chunk.get('done', False):
                            logger.debug(f"🔍 DEBUG: Stream complete (done=True)")
                            break

                        if (content := chunk.get('message', {}).get('content', '')):
                            # If we've already found and handled a tool call, ignore the rest of the stream.
                            if mcp_detected:
                                continue

                            full_content_buffer += content

                            # STAGE 3: Active MCP execution - detect and execute formal MCP requests
                            formal_mcp_result = parse_mcp_request(full_content_buffer)
                            if formal_mcp_result:
                                tool_name, inner_content = formal_mcp_result
                                mcp_detected = True  # Stop streaming the LLM response
                                
                                logger.info(f"🎯 MCP ACTIVATED: Found formal MCP tool call for '{tool_name}'")
                                logger.debug(f"🎯 MCP CONTENT: {inner_content}")
                                
                                # Execute the formal MCP tool call
                                asyncio.create_task(
                                    execute_formal_mcp_tool_call(messages, tool_name, inner_content)
                                )
                                continue  # Skip the rest of the stream processing

                            # Use regex to find a complete MCP block
                            match = mcp_pattern.search(full_content_buffer)
                            if match:
                                mcp_block = match.group(1)
                                mcp_detected = True  # Flag that we've found our tool call

                                logger.info(f"🔧 MCP CLIENT: Complete MCP tool call extracted.")
                                logger.debug(f"🔧 MCP BLOCK:\n{mcp_block}")

                                # Offload the tool execution to a background task
                                asyncio.create_task(
                                    execute_and_respond_to_tool_call(messages, mcp_block)
                                )
                                # Now that we have the tool call, we ignore all subsequent content from this stream
                                continue

                            # If no MCP block is detected yet, stream the content normally.
                            # This handles regular, non-tool-call conversations.
                            word_buffer += content

                            # Check if word_buffer contains start of potential MCP/tool tag or markdown code block
                            if '<tool' in word_buffer or '<mcp-request' in word_buffer or '```xml' in word_buffer:
                                # Hold off on yielding if we might be building a tool call
                                continue

                            parts = re.split(r'(\s+)', word_buffer)
                            if len(parts) > 1:
                                complete_parts = parts[:-1]
                                word_buffer = parts[-1]
                                for part in complete_parts:
                                    accumulated_response.append(part)
                                    yield part

                    except json.JSONDecodeError:
                        logger.warning(f"🔍 DEBUG: JSON decode error on chunk #{chunk_count}")
                        continue

                # After the loop, if there's remaining content in the buffer and no tool was called, flush it.
                if word_buffer and not mcp_detected:
                    accumulated_response.append(word_buffer)
                    yield word_buffer

                # Final logging table for LLM responses (including tool calls)
                if accumulated_response:
                    final_response = ''.join(accumulated_response)
                    table = Table(title='Chat Response')
                    table.add_column('Accumulated Response')
                    table.add_row(final_response, style='green')
                    slog.print_and_log_table(table, "LLM RESPONSE - ")

    except aiohttp.ClientConnectorError as e:
        error_msg = 'Unable to connect to Ollama server. Please ensure Ollama is running.'
        logger.error(f"🔍 DEBUG: Connection error: {e}")
        yield error_msg
    except Exception as e:
        error_msg = f'Error: {str(e)}'
        logger.error(f"🔍 DEBUG: Unexpected error in process_llm_interaction: {e}")
        yield error_msg


async def execute_formal_mcp_tool_call(conversation_history: list, tool_name: str, inner_content: str):
    """
    Execute a formal MCP tool call using the imports.mcp_orchestrator.
    
    This function handles the formal MCP protocol by:
    1. Executing the tool using the formal orchestrator
    2. Appending both the tool call and result to conversation history
    3. Sending the updated history back to the LLM for the next turn
    """
    from imports.mcp_orchestrator import execute_mcp_tool
    
    try:
        logger.info(f"🎯 FORMAL MCP: Executing tool '{tool_name}'")
        
        # Execute the tool using the formal orchestrator
        tool_output_xml = await execute_mcp_tool(tool_name, inner_content)
        logger.debug(f"🎯 FORMAL MCP: Tool output: {tool_output_xml}")
        
        # Construct the original tool call XML for conversation history
        original_call = f'<tool name="{tool_name}">{inner_content}</tool>'
        
        # Append both the tool call and the result to conversation history
        updated_messages = conversation_history.copy()
        updated_messages.append({"role": "assistant", "content": original_call})
        updated_messages.append({"role": "user", "content": tool_output_xml})
        
        logger.info(f"🎯 FORMAL MCP: Sending updated conversation back to LLM")
        
        # Send the updated conversation back to the LLM for the next turn
        async for chunk in process_llm_interaction(MODEL, updated_messages):
            await chat.broadcast(chunk)
            
        logger.info(f"🎯 FORMAL MCP: Completed formal MCP execution cycle")
        
    except Exception as e:
        logger.error(f"🎯 FORMAL MCP: Error in formal MCP execution: {e}", exc_info=True)
        error_message = f"Error executing formal MCP tool '{tool_name}': {str(e)}"
        await chat.broadcast(error_message)


async def execute_and_respond_to_tool_call(conversation_history: list, mcp_block: str):
    """
    Parses an MCP block (XML/JSON/bracket notation), executes the tool, and directly formats and sends
    the result to the UI, bypassing a second LLM call for reliability.

    🎓 PROGRESSIVE REVEAL SUPPORT:
    - [mcp-discover] - Level 1: Ultra-simple bracket notation for small models
    - <tool name="..."> - Level 4/5: XML/JSON for sophisticated models
    """
    import uuid as uuid_lib
    start_time = time.time()
    operation_id = str(uuid_lib.uuid4())[:8]

    try:
        logger.debug("🔍 DEBUG: === STARTING execute_and_respond_to_tool_call ===")

        # Check if this is bracket notation (Level 1: simplest)
        if mcp_block.startswith('[') and mcp_block.endswith(']'):
            logger.debug("🔍 DEBUG: Detected bracket notation command")
            return await execute_bracket_notation_command(mcp_block, operation_id, start_time)

        # Handle XML/JSON tool syntax (Level 4/5: more complex)
        tool_name_match = re.search(r'<tool name="([^"]+)"', mcp_block)
        tool_name = tool_name_match.group(1) if tool_name_match else None

        if not tool_name:
            logger.error("🔧 MCP CLIENT: Could not parse tool name from block.")
            await chat.broadcast("Error: Could not understand the tool request.")
            return

        # Extract parameters from the <params> section
        params = {}
        params_match = re.search(r'<params>(.*?)</params>', mcp_block, re.DOTALL)
        if params_match:
            params_text = params_match.group(1).strip()
            try:
                # Try to parse as JSON first
                params = json.loads(params_text)
                logger.debug(f"🔧 MCP CLIENT: Extracted JSON params: {params}")
            except json.JSONDecodeError:
                # If JSON parsing fails, try XML parsing
                logger.debug("🔧 MCP CLIENT: JSON parsing failed, trying XML parsing")
                import xml.etree.ElementTree as ET
                try:
                    # Wrap in a root element to make it valid XML
                    xml_text = f"<root>{params_text}</root>"
                    root = ET.fromstring(xml_text)

                    # Extract all child elements as key-value pairs
                    for child in root:
                        params[child.tag] = child.text

                    logger.debug(f"🔧 MCP CLIENT: Extracted XML params: {params}")
                except ET.ParseError as e:
                    logger.error(f"🔧 MCP CLIENT: Failed to parse params as XML: {e}")
                    logger.debug(f"🔧 MCP CLIENT: Raw params text: {repr(params_text)}")
        else:
            logger.debug("🔧 MCP CLIENT: No params section found, using empty params")

        logger.info(f"🔧 FINDER_TOKEN: MCP_EXECUTION_START - Tool '{tool_name}' with params: {params}")
        async with aiohttp.ClientSession() as session:
            url = "http://127.0.0.1:5001/mcp-tool-executor"
            payload = {"tool": tool_name, "params": params}

            mcp_request_start = time.time()
            async with session.post(url, json=payload) as response:
                mcp_request_end = time.time()
                execution_time_ms = (mcp_request_end - start_time) * 1000

                tool_result = await response.json() if response.status == 200 else {}

                # Log the complete MCP operation with extreme observability
                await pipulate.log_mcp_call_details(
                    operation_id=operation_id,
                    tool_name=tool_name,
                    operation_type="tool_execution",
                    mcp_block=mcp_block,
                    request_payload=payload,
                    response_data=tool_result,
                    response_status=response.status,
                    external_api_url="https://catfact.ninja/fact",  # This will be enhanced to be dynamic
                    external_api_method="GET",
                    external_api_headers=None,
                    external_api_payload=None,
                    external_api_response=tool_result.get("result") if response.status == 200 else None,
                    external_api_status=200 if tool_result.get("status") == "success" else None,
                    execution_time_ms=execution_time_ms,
                    notes=f"MCP tool execution for {tool_name} via poke endpoint"
                )

                if response.status == 200:
                    logger.info(f"🎯 FINDER_TOKEN: MCP_SUCCESS - Tool '{tool_name}' executed successfully")

                    # Check for success in multiple formats: "success": true OR "status": "success"
                    is_success = (tool_result.get("success") is True or
                                  tool_result.get("status") == "success")

                    if is_success:
                        # Handle different tool types
                        if tool_name == "get_cat_fact":
                            # Cat fact specific handling
                            fact_data = tool_result.get("result", {})
                            the_fact = fact_data.get("fact")

                            if the_fact:
                                logger.success(f"✅ RELIABLE FORMATTING: Directly formatting fact: {the_fact}")
                                final_message = f"🐱 **Cat Fact Alert!** 🐱\n\n{the_fact}\n\nWould you like another fact?"
                                await pipulate.message_queue.add(pipulate, final_message, verbatim=True, role='assistant')
                            else:
                                error_message = "The cat fact API returned a success, but the fact was missing."
                                logger.warning(f"🔧 MCP CLIENT: {error_message}")
                                await pipulate.message_queue.add(pipulate, error_message, verbatim=True, role='system')

                        elif tool_name == "ui_flash_element":
                            # UI flash specific handling
                            element_id = tool_result.get("element_id")
                            message = tool_result.get("message", "Element flashed successfully!")
                            logger.success(f"✅ UI FLASH: Element '{element_id}' flashed successfully")
                            final_message = f"✨ **UI Element Flashed!** ✨\n\n🎯 **Element:** {element_id}\n💬 **Message:** {message}\n\nThe element should now be glowing on your screen!"
                            await pipulate.message_queue.add(pipulate, final_message, verbatim=True, role='assistant')

                        elif tool_name == "ui_list_elements":
                            # UI list elements specific handling
                            elements = tool_result.get("ui_elements", {})
                            logger.success(f"✅ UI LIST: Listed {len(elements)} element categories")
                            final_message = f"📋 **Available UI Elements** 📋\n\n"
                            for category, items in elements.items():
                                final_message += f"**{category.upper()}:**\n"
                                if isinstance(items, dict):
                                    for element_id, description in items.items():
                                        final_message += f"• `{element_id}` - {description}\n"
                                else:
                                    final_message += f"• {items}\n"
                                final_message += "\n"
                            final_message += "You can flash any of these elements using the `ui_flash_element` tool!"
                            await pipulate.message_queue.add(pipulate, final_message, verbatim=True, role='assistant')

                        else:
                            # Generic success handling for other tools
                            success_message = f"✅ Tool '{tool_name}' executed successfully!"
                            result_data = tool_result.get("result")
                            if result_data:
                                success_message += f"\n\nResult: {result_data}"
                            await pipulate.message_queue.add(pipulate, success_message, verbatim=True, role='assistant')
                    else:
                        error_message = f"Sorry, the '{tool_name}' tool encountered an error."
                        error_details = tool_result.get("error")
                        if error_details:
                            error_message += f" Error: {error_details}"
                        logger.error(f"🔧 MCP CLIENT: Tool returned non-success status: {tool_result}")
                        await pipulate.message_queue.add(pipulate, error_message, verbatim=True, role='system')
                else:
                    error_text = await response.text()
                    logger.error(f"🔧 MCP CLIENT: Tool execution failed with status {response.status}: {error_text}")
                    await pipulate.message_queue.add(pipulate, f"Error: The tool '{tool_name}' failed to execute.", verbatim=True, role='system')

    except Exception as e:
        logger.error(f"🔧 MCP CLIENT: Error in tool execution pipeline: {e}", exc_info=True)
        await pipulate.message_queue.add(pipulate, f"An unexpected error occurred during tool execution: {str(e)}", verbatim=True, role='system')
    finally:
        logger.debug("🔍 DEBUG: === ENDING execute_and_respond_to_tool_call ===")


async def execute_bracket_notation_command(mcp_block: str, operation_id: str, start_time: float):
    """
    Execute bracket notation commands - Level 1 of progressive reveal.

    🎓 PROGRESSIVE REVEAL LEVEL 1: Ultra-simple for small models
    Examples: [mcp-discover], [pipeline], [search FINDER_TOKEN]

    This is the simplest possible syntax, designed for quantized models
    that can't handle complex tool calling but can embed simple commands.
    """
    try:
        # Import the simple parser
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent / 'helpers'))
        from ai_tool_discovery_simple_parser import execute_simple_command

        # Remove brackets and execute
        command = mcp_block.strip('[]')
        logger.info(f"🔧 FINDER_TOKEN: BRACKET_COMMAND_START - Command '{command}'")

        # Execute using the simple parser
        result = await execute_simple_command(command)

        if result.get('success'):
            logger.info(f"🎯 FINDER_TOKEN: BRACKET_SUCCESS - Command '{command}' executed successfully")

            # 🔧 TRANSPARENCY DISABLED: Commented out to prevent response stream pollution
            # This was causing massive amounts of pipeline data to be logged, making chat unusable
            #
            # logger.info(f"🔧 MCP_TRANSPARENCY: === COMPLETE TOOL EXECUTION DETAILS ===")
            # logger.info(f"🔧 MCP_TRANSPARENCY: Command: '{command}'")
            # logger.info(f"🔧 MCP_TRANSPARENCY: Result Success: {result.get('success')}")
            # logger.info(f"🔧 MCP_TRANSPARENCY: Result Keys: {list(result.keys())}")
            #
            # # Log the full result structure for debugging
            # if 'result' in result:
            #     logger.info(f"🔧 MCP_TRANSPARENCY: Result Data: {result['result']}")
            #
            # # Log any pattern matches or search results
            # if 'pattern' in result:
            #     logger.info(f"🔧 MCP_TRANSPARENCY: Search Pattern: {result['pattern']}")
            # if 'matches' in result:
            #     logger.info(f"🔧 MCP_TRANSPARENCY: Match Count: {len(result['matches'])}")
            #     logger.info(f"🔧 MCP_TRANSPARENCY: First 3 Matches: {result['matches'][:3]}")
            #
            # # Log file operations
            # if 'file_path' in result:
            #     logger.info(f"🔧 MCP_TRANSPARENCY: File Path: {result['file_path']}")
            # if 'match_count' in result:
            #     logger.info(f"🔧 MCP_TRANSPARENCY: Total Match Count: {result['match_count']}")
            #
            # logger.info(f"🔧 MCP_TRANSPARENCY: === END TRANSPARENCY LOG ===")

            # Format response based on command type
            if command in ['mcp', 'mcp-discover']:
                # Special handling for discovery commands
                categories = result.get('categories', [])
                response_text = "🚀 **MCP Tool Discovery** 🚀\n\n"
                response_text += "Available categories:\n\n"
                for category in categories:
                    response_text += f"• {category}\n"
                response_text += f"\n💡 Try [tools] to see specific tools in each category"
                response_text += f"\n🎓 **Progressive Reveal**: Start simple, get sophisticated!"
                response_text += f"\n\n**Next levels:**"
                response_text += f"\nLevel 2: `.venv/bin/python cli.py mcp-discover`"
                response_text += f"\nLevel 3: `python -c \"from imports.ai_tool_discovery_simple_parser import execute_simple_command; import asyncio; print(asyncio.run(execute_simple_command('mcp')))\"`"
                response_text += f"\nLevel 4: `<tool name=\"ai_self_discovery_assistant\"><params>{{\"discovery_type\":\"capabilities\"}}</params></tool>`"
                response_text += f"\nLevel 5: `<tool name=\"ai_self_discovery_assistant\"><params><discovery_type>capabilities</discovery_type></params></tool>`"

            elif command == 'tools':
                # List tools by category
                tools = result.get('tools', {})
                response_text = "🔧 **Available MCP Tools** 🔧\n\n"
                for category, tool_list in tools.items():
                    response_text += f"**{category}:**\n"
                    for tool in tool_list:
                        response_text += f"• {tool}\n"
                    response_text += "\n"

            elif command == 'pipeline':
                # System state inspection
                response_text = f"📊 **System State** 📊\n\n"
                response_text += f"Pipeline state inspection completed.\n"
                # BLOCKED: Massive data dump into chat - causes HTML pollution
                # if 'result' in result:
                #     response_text += f"Result: {result['result']}\n"

            else:
                # Generic success handling
                response_text = f"✅ **Command '{command}' completed!** ✅\n\n"
                # BLOCKED: Massive data dump into chat - causes HTML pollution
                # if 'result' in result:
                #     response_text += f"Result: {result['result']}\n"

            await pipulate.message_queue.add(pipulate, response_text, verbatim=True, role='assistant')

        else:
            # Handle errors with enhanced transparency
            error_msg = result.get('error', 'Unknown error')
            suggestion = result.get('suggestion', '')

            # 🔧 ERROR TRANSPARENCY DISABLED: Commented out to prevent response stream pollution
            # This was also causing excessive error logging that polluted the chat
            #
            # logger.error(f"🔧 MCP_TRANSPARENCY: === COMMAND FAILURE DETAILS ===")
            # logger.error(f"🔧 MCP_TRANSPARENCY: Failed Command: '{command}'")
            # logger.error(f"🔧 MCP_TRANSPARENCY: Error Message: {error_msg}")
            # logger.error(f"🔧 MCP_TRANSPARENCY: Full Error Result: {result}")
            # if suggestion:
            #     logger.error(f"🔧 MCP_TRANSPARENCY: Suggested Fix: {suggestion}")
            # logger.error(f"🔧 MCP_TRANSPARENCY: === END ERROR LOG ===")

            response_text = f"❌ **Command Error** ❌\n\n"
            response_text += f"Command: `{command}`\n"
            response_text += f"Error: {error_msg}\n"
            if suggestion:
                response_text += f"Suggestion: {suggestion}\n"
            response_text += f"\n💡 Try [mcp] for available commands"

            logger.error(f"🔧 BRACKET CLIENT: Command '{command}' failed: {error_msg}")
            await pipulate.message_queue.add(pipulate, response_text, verbatim=True, role='system')

    except Exception as e:
        logger.error(f"🔧 BRACKET CLIENT: Error in bracket notation execution: {e}", exc_info=True)
        await pipulate.message_queue.add(pipulate, f"An error occurred executing bracket command: {str(e)}", verbatim=True, role='system')


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

    This function creates the remaining non-sortable chat functionality:
    - WebSocket and SSE setup
    - Form interactions
    - Chat message handling
    - Other UI interactions

    Third-party library initialization is now handled by the consolidated init.js file.

    Returns:
        tuple: (static_js_script, dynamic_init_script, stylesheet)
    """
    python_generated_init_script = f"""
    document.addEventListener('DOMContentLoaded', (event) => {{
        // Initialize sortable functionality with clean dedicated file
        if (window.initializePipulateSortable) {{
            window.initializePipulateSortable('{sortable_selector}', {{
                ghostClass: '{ghost_class}',
                animation: 150
            }});
        }}
        
        // Initialize remaining chat functionality from pipulate.js
        if (window.initializeChatScripts) {{
            window.initializeChatScripts({{
                sortableSelector: '{sortable_selector}',
                ghostClass: '{ghost_class}'
            }});
        }}
    }});
    """
    return (Script(src='/assets/pipulate.js'), Script(python_generated_init_script), Link(rel='stylesheet', href='/assets/styles.css'))


# BaseCrud class moved to apps/crud.py to avoid circular imports

# Initialize FastApp with database and configuration
app, rt, (store, Store), (profiles, Profile), (pipeline, Pipeline) = fast_app(
    DB_FILENAME,
    exts='ws',
    live=True,
    default_hdrs=False,
    hdrs=(
        Meta(charset='utf-8'),
        Link(rel='stylesheet', href='/assets/css/pico.css'),
        Link(rel='stylesheet', href='/assets/css/prism.css'),
        Link(rel='stylesheet', href='/assets/rich-table.css'),
        Script(src='/assets/js/htmx.js'),
        Script(src='/assets/js/fasthtml.js'),
        Script(src='/assets/js/surreal.js'),
        Script(src='/assets/js/script.js'),
        Script(src='/assets/js/Sortable.js'),
        Script(src='/assets/js/split.js'),
        Script(src='/assets/js/mermaid.min.js'),
        Script(src='/assets/js/marked.min.js'),
        Script(src='/assets/init.js'),
        Script(src='/assets/js/prism.js'),
        Script(src='/assets/theme.js'),
        Script(src='/assets/utils.js'),
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
        self.pipulate = pipulate_instance
        self.logger = logger.bind(name=f'Chat{id_suffix}')
        self.active_websockets = set()
        self.startup_messages = []  # Store startup messages to replay when first client connects
        self.first_connection_handled = False  # Track if we've sent startup messages
        self.last_message = None  # Required for broadcast functionality
        self.last_message_time = 0  # Required for broadcast functionality
        self.active_chat_tasks = {}  # Track tasks per websocket
        self.app.websocket_route('/ws')(self.handle_websocket)
        self.logger.debug('Registered WebSocket route: /ws')

    async def handle_chat_message(self, websocket: WebSocket, message: str):
        task = None
        try:
            # REMOVED: append_to_conversation(message, 'user') -> This was causing the duplicates.
            parts = message.split('|')
            msg = parts[0]
            verbatim = len(parts) > 1 and parts[1] == 'verbatim'
            
            # Check for formal MCP requests in user input
            from imports.mcp_orchestrator import parse_mcp_request
            formal_mcp_result = parse_mcp_request(msg)
            if formal_mcp_result:
                tool_name, inner_content = formal_mcp_result
                logger.info(f"🎯 USER MCP REQUEST: Found formal MCP tool call for '{tool_name}' in user input")
                
                # Append the user's MCP request to conversation history
                append_to_conversation(msg, 'user')
                
                # Execute the formal MCP tool call directly
                conversation_history = append_to_conversation()  # Get current conversation
                asyncio.create_task(
                    execute_formal_mcp_tool_call(conversation_history, tool_name, inner_content)
                )
                return  # Don't send to LLM, just execute the tool
            
            # The pipulate.stream method will handle appending to the conversation.
            task = asyncio.create_task(pipulate.stream(msg, verbatim=verbatim))
            self.active_chat_tasks[websocket] = task
            await task
        except asyncio.CancelledError:
            self.logger.info(f"Chat task for {websocket} was cancelled by user.")
        except Exception as e:
            self.logger.error(f'Error in handle_chat_message: {e}')
            traceback.print_exc()
        finally:
            if websocket in self.active_chat_tasks:
                del self.active_chat_tasks[websocket]

    async def handle_demo_mcp_call(self, websocket: WebSocket, mcp_data: str):
        """Handle MCP tool calls from demo script"""
        try:
            import json
            import platform
            call_data = json.loads(mcp_data)
            tool_name = call_data.get('tool_name')
            tool_args = call_data.get('tool_args', {})
            description = call_data.get('description', '')

            # 🍎 MAC VOICE ADAPTATION: Platform-aware voice text for keyboard shortcuts
            if tool_name == 'voice_synthesis' and 'text' in tool_args:
                original_text = tool_args['text']
                
                # Detect Mac platform for voice adaptation
                is_mac = platform.system() == 'Darwin'
                
                if is_mac and 'control alt' in original_text.lower():
                    # Adapt voice text for Mac keyboard shortcuts
                    adapted_text = original_text.replace('control alt', 'control option')
                    adapted_text = adapted_text.replace('Control Alt', 'Control Option')
                    adapted_text = adapted_text.replace('Ctrl+Alt', 'Control+Option')
                    adapted_text = adapted_text.replace('ctrl+alt', 'control+option')
                    
                    tool_args['text'] = adapted_text
                    
                    self.logger.info(f"🍎 MAC VOICE: Adapted keyboard shortcut text for Mac")
                    self.logger.info(f"🍎 MAC VOICE: Original: {original_text}")
                    self.logger.info(f"🍎 MAC VOICE: Adapted: {adapted_text}")

            self.logger.info(f"🎯 Demo MCP call: {tool_name} with args: {tool_args}")

            # Execute the MCP tool
            if tool_name in MCP_TOOL_REGISTRY:
                tool_handler = MCP_TOOL_REGISTRY[tool_name]
                result = await tool_handler(tool_args)

                # Log detailed MCP execution to server console
                self.logger.info(f"🔧 **MCP Tool Executed** 🔧")
                self.logger.info(f"   Tool: {tool_name}")
                self.logger.info(f"   Args: {json.dumps(tool_args)}")
                self.logger.info(f"   Result: {result.get('success', False)}")
                if description:
                    self.logger.info(f"   Description: {description}")
                self.logger.info(f"🎯 Demo MCP call completed: {tool_name} -> {result.get('success', False)}")

            else:
                self.logger.error(f"🔧 **MCP Tool Error** 🔧")
                self.logger.error(f"   Tool: {tool_name} not found")
                self.logger.error(f"🎯 Demo MCP call failed: {tool_name} not found")

        except Exception as e:
            self.logger.error(f"🔧 **MCP Tool Error** 🔧")
            self.logger.error(f"   Error handling demo MCP call: {e}")
            self.logger.error(f"🎯 Error handling demo MCP call: {e}")

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

                # Check for our special stop command
                if message == '%%STOP_STREAM%%':
                    self.logger.info(f"Received stop command from {websocket}.")
                    task_to_cancel = self.active_chat_tasks.get(websocket)
                    if task_to_cancel:
                        task_to_cancel.cancel()
                    else:
                        self.logger.warning(f"No active chat task found for {websocket} to stop.")
                elif message == '%%RESTART_SERVER%%':
                    self.logger.info(f"🔄 Received server restart command from {websocket}.")
                    # Trigger server restart using existing restart_server function - force restart for user-initiated commands
                    restart_server(force_restart=True)
                elif message.startswith('%%DEMO_MCP_CALL%%:'):
                    # Handle demo script MCP tool calls
                    self.logger.info(f"🎯 Received demo MCP tool call from {websocket}.")
                    mcp_data = message[len('%%DEMO_MCP_CALL%%:'):]
                    asyncio.create_task(self.handle_demo_mcp_call(websocket, mcp_data))
                else:
                    # Launch as a non-blocking background task
                    asyncio.create_task(self.handle_chat_message(websocket, message))

        except WebSocketDisconnect:
            self.logger.info('WebSocket disconnected')
        except Exception as e:
            self.logger.error(f'Error in WebSocket connection: {str(e)}')
            self.logger.error(traceback.format_exc())
        finally:
            # Also clean up any lingering task on disconnect
            if websocket in self.active_chat_tasks:
                self.active_chat_tasks.pop(websocket, None).cancel()
            self.active_websockets.discard(websocket)
            self.logger.debug('WebSocket connection closed')

    async def broadcast(self, message: str):
        try:
            if isinstance(message, dict):
                if message.get('type') == 'htmx':
                    htmx_response = message
                    content = to_xml(htmx_response['content'])
                    formatted_response = f"""<div id=\"todo-{htmx_response.get('id')}\" hx-swap-oob=\"beforeend:#todo-list\">\n    {content}\n</div>"""
                    if self.active_websockets:
                        for ws in self.active_websockets:
                            await ws.send_text(formatted_response)
                    else:
                        self.startup_messages.append(formatted_response)
                    return

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
                self.startup_messages.append(formatted_msg)
        except Exception as e:
            self.logger.error(f'Error in broadcast: {e}')


pipulate = Pipulate(pipeline)
logger.info('🔧 FINDER_TOKEN: CORE_INIT - Pipulate instance initialized')

app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'], allow_credentials=True)
logger.info('🌐 FINDER_TOKEN: CORS_MIDDLEWARE - CORS middleware added to FastHTML app')

if not os.path.exists('apps'):
    os.makedirs('apps')
    logger.info('📁 FINDER_TOKEN: PLUGINS_DIR - Created plugins directory')
else:
    logger.info('📁 FINDER_TOKEN: PLUGINS_DIR - Plugins directory exists')

chat = Chat(app, id_suffix='', pipulate_instance=pipulate)
logger.info('💬 FINDER_TOKEN: CHAT_INIT - Chat instance initialized')

# Critical: Set the chat reference back to pipulate so stream() method works
pipulate.set_chat(chat)
logger.info('🔗 FINDER_TOKEN: CHAT_LINK - Chat reference set in pipulate instance')


def build_endpoint_messages(endpoint):
    logger.debug(f"🔧 BUILD_ENDPOINT_DEBUG: Called with endpoint='{endpoint}'")
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

    logger.debug(f"🔧 BUILD_ENDPOINT_DEBUG: Built {len(endpoint_messages)} endpoint messages")

    # Special handling for empty endpoint (homepage)
    if not endpoint:
        # --- START CHANGE ---
        home_app_name = getattr(CFG, 'HOME_APP', 'roles')
        logger.debug(f"🔧 BUILD_ENDPOINT_DEBUG: Empty endpoint - using '{home_app_name}' as homepage logic")
        home_app_instance = plugin_instances.get(home_app_name)
        if home_app_instance:
            if hasattr(home_app_instance, 'get_endpoint_message') and callable(getattr(home_app_instance, 'get_endpoint_message')):
                endpoint_messages[''] = home_app_instance.get_endpoint_message()
            elif hasattr(home_app_instance, 'ENDPOINT_MESSAGE'):
                endpoint_messages[''] = home_app_instance.ENDPOINT_MESSAGE
            else:
                class_name = home_app_instance.__class__.__name__
                endpoint_messages[''] = f'{class_name} app is where you manage your {home_app_name}.'
        else:
            endpoint_messages[''] = f'Welcome to {APP_NAME}. Select an app from the menu to get started.'
        # --- END CHANGE ---

    if endpoint in plugin_instances:
        plugin_instance = plugin_instances[endpoint]
        logger.debug(f"🔧 BUILD_ENDPOINT_DEBUG: Found plugin for endpoint '{endpoint}'")
        logger.debug(f"Checking if {endpoint} has get_endpoint_message: {hasattr(plugin_instance, 'get_endpoint_message')}")
        logger.debug(f"Checking if get_endpoint_message is callable: {callable(getattr(plugin_instance, 'get_endpoint_message', None))}")
        logger.debug(f"Checking if {endpoint} has ENDPOINT_MESSAGE: {hasattr(plugin_instance, 'ENDPOINT_MESSAGE')}")
    else:
        logger.debug(f"🔧 BUILD_ENDPOINT_DEBUG: No plugin found for endpoint '{endpoint}' in {list(plugin_instances.keys())}")

    result = endpoint_messages.get(endpoint, None)
    logger.debug(f"🔧 BUILD_ENDPOINT_DEBUG: Returning message for '{endpoint}': {result[:100] if result else 'None'}...")
    return result


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

    # Special handling for empty endpoint (homepage)
    if not endpoint:
        # --- START CHANGE ---
        home_app_name = getattr(CFG, 'HOME_APP', 'roles')
        home_app_instance = plugin_instances.get(home_app_name)
        if home_app_instance:
            if hasattr(home_app_instance, 'TRAINING_PROMPT'):
                prompt = home_app_instance.TRAINING_PROMPT
                endpoint_training[''] = read_training(prompt)
            else:
                class_name = home_app_instance.__class__.__name__
                endpoint_training[''] = f'You are on the homepage, which is the {class_name} app.'
        else:
            endpoint_training[''] = 'You were just switched to the home page.'
        # --- END CHANGE ---

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
            # Don't log KeyError as ERROR for __getitem__ - it's expected behavior
            if func.__name__ == '__getitem__' and isinstance(e, KeyError):
                logger.debug(f'Key not found in database: {e}')
            else:
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
        for record in self.store():
            yield record.key

    @db_operation
    def items(self):
        for record in self.store():
            yield (record.key, record.value)

    @db_operation
    def keys(self):
        return list(self)

    @db_operation
    def values(self):
        for record in self.store():
            yield record.value

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
logger.info('💾 FINDER_TOKEN: DB_WRAPPER - Database wrapper initialized')


def populate_initial_data():
    """Populate initial data in the database."""
    if TABLE_LIFECYCLE_LOGGING:
        logger.bind(lifecycle=True).info('POPULATE_INITIAL_DATA: Starting.')
        slog.log_dynamic_table_state('profiles', lambda: profiles(), title_prefix='POPULATE_INITIAL_DATA: Profiles BEFORE')
        slog.log_dictlike_db_to_lifecycle('db', db, title_prefix='POPULATE_INITIAL_DATA: db BEFORE')
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
    if 'split-sizes' not in db:
        db['split-sizes'] = '[65, 35]'  # Default split panel sizes
        logger.debug("Initialized split-sizes to default '[65, 35]'")
    if 'theme_preference' not in db:
        db['theme_preference'] = 'auto'  # Default theme preference
        logger.debug("Initialized theme_preference to 'auto'")
    if 'intro_current_page' not in db:
        db['intro_current_page'] = '1'  # Default to page 1 of introduction
        logger.debug("Initialized intro_current_page to '1'")
    if TABLE_LIFECYCLE_LOGGING:
        slog.log_dynamic_table_state('profiles', lambda: profiles(), title_prefix='POPULATE_INITIAL_DATA: Profiles AFTER')
        slog.log_dictlike_db_to_lifecycle('db', db, title_prefix='POPULATE_INITIAL_DATA: db AFTER')
        logger.bind(lifecycle=True).info('POPULATE_INITIAL_DATA: Finished.')


populate_initial_data()


async def synchronize_roles_to_db():
    """Ensure all roles defined in plugin ROLES constants and ROLES_CONFIG exist in the 'roles' database table."""
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
        slog.log_dynamic_table_state('roles', lambda: roles_table_handler(), title_prefix='SYNC_ROLES: Global BEFORE')
    logger.debug('SYNC_ROLES: Synchronizing roles globally')
    discovered_roles_set = set()

    # FIRST: Get roles from ROLES_CONFIG (this is the primary source of truth)
    roles_config = getattr(CFG, 'ROLES_CONFIG', {})
    if roles_config:
        logger.debug(f"SYNC_ROLES: Found {len(roles_config)} roles in ROLES_CONFIG: {list(roles_config.keys())}")
        discovered_roles_set.update(roles_config.keys())

    # SECOND: Get roles from plugin ROLES constants (for backward compatibility)
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
        logger.info('SYNC_ROLES: No roles were discovered in ROLES_CONFIG or plugin ROLES constants. Role table will not be modified.')
    else:
        logger.info(f'SYNC_ROLES: Total unique role names discovered from all sources: {discovered_roles_set}')
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
        slog.console.print('\n')
        slog.print_and_log_table(roles_rich_table, "ROLES SYNC - ")
        slog.console.print('\n')
        logger.info('SYNC_ROLES: Roles synchronization display complete globally.')
    if TABLE_LIFECYCLE_LOGGING:
        logger.bind(lifecycle=True).info('SYNC_ROLES: Finished global role synchronization.')
        slog.log_dynamic_table_state('roles', lambda: roles_table_handler(), title_prefix='SYNC_ROLES: Global AFTER')


def discover_plugin_files():
    """Discover and import all Python files in the plugins directory.

    This function scans the 'apps' directory and imports each .py file
    as a module. It skips files:
    - Starting with '__' (like __init__.py)
    - Starting with 'xx_' or 'XX_' (indicating experimental/in-progress plugins)
    - Containing parentheses (like "tasks (Copy).py")

    Returns:
        dict: Mapping of module names to imported module objects
    """
    plugin_modules = {}
    apps_dir = os.path.join(os.path.dirname(__file__), 'apps')
    logger.debug(f'Looking for plugins in: {apps_dir}')
    if not os.path.isdir(apps_dir):
        logger.warning(f'Plugins directory not found: {apps_dir}')
        return plugin_modules

    def numeric_prefix_sort(filename):
        match = re.match('^(\\d+)_', filename)
        if match:
            return int(match.group(1))
        return float('inf')
    sorted_files = sorted(os.listdir(apps_dir), key=numeric_prefix_sort)
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
            clean_name = re.sub('^\\d+_', '', base_name)
            original_name = base_name
            logger.debug(f'Module name: {clean_name} (from {original_name})')
            try:
                module = importlib.import_module(f'apps.{original_name}')
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
                module = importlib.import_module(f'apps.{original_name}')
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
                        else:
                            logger.warning(f'FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Plugin class {module_name}.{name} has landing method but missing required name attributes (NAME, APP_NAME, DISPLAY_NAME, name, app_name, display_name) - skipping')
                    else:
                        # Only log classes that look like they might be plugins (have common plugin attributes)
                        if any(hasattr(obj, attr) for attr in ['APP_NAME', 'DISPLAY_NAME', 'ROLES', 'steps']):
                            logger.warning(f'FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Plugin class {module_name}.{name} appears to be a plugin (has APP_NAME/DISPLAY_NAME/ROLES/steps) but missing required landing method - skipping')
        except Exception as e:
            logger.error(f'FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Error processing module {module_or_name}: {str(e)}')
            import traceback
            logger.error(f'FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Full traceback for {module_or_name}: {traceback.format_exc()}')
            continue
    logger.debug(f'Discovered plugin classes: {plugin_classes}')
    return plugin_classes


# 🎨 PLUGINS BANNER - Right before plugin discovery begins (only when running as main script)
if __name__ == '__main__':
    aa.figlet_banner("apps", "Pipulate Workflows and CRUD Apps", font='standard', color='orange3')

plugin_instances = {}
discovered_modules = discover_plugin_files()
discovered_classes = find_plugin_classes(discovered_modules, discovered_modules)
friendly_names = {'': HOME_MENU_ITEM}
endpoint_training = {}


def get_display_name(workflow_name):
    instance = plugin_instances.get(workflow_name)
    if instance:
        try:
            # Try to get DISPLAY_NAME safely, avoiding circular import during startup
            display_name = getattr(instance, 'DISPLAY_NAME', None)
            if display_name and isinstance(display_name, str):
                return display_name
        except (ImportError, AttributeError):
            # Circular import or other error - fall back to default
            pass
    return workflow_name.replace('_', ' ').title()


def get_endpoint_message(workflow_name):
    instance = plugin_instances.get(workflow_name)
    if instance:
        try:
            # Try to get ENDPOINT_MESSAGE safely, avoiding circular import during startup
            message = getattr(instance, 'ENDPOINT_MESSAGE', None)
            if message and isinstance(message, str):
                if hasattr(pipulate, 'format_links_in_text'):
                    try:
                        if inspect.iscoroutinefunction(pipulate.format_links_in_text):
                            asyncio.create_task(pipulate.format_links_in_text(message))
                            return message
                        else:
                            return pipulate.format_links_in_text(message)
                    except Exception as e:
                        logger.warning(f'Error formatting links in message: {e}')
                        return message
                return message
        except (ImportError, AttributeError):
            # Circular import or other error - fall back to default
            pass
    return f"{workflow_name.replace('_', ' ').title()} app is where you manage your workflows."


for module_name, class_name, workflow_class in discovered_classes:
    if module_name not in plugin_instances:
        try:
            original_name = getattr(discovered_modules[module_name], '_original_filename', module_name)
            module = importlib.import_module(f'apps.{original_name}')
            workflow_class = getattr(module, class_name)
            if not hasattr(workflow_class, 'landing'):
                logger.warning(f"FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Plugin class {module_name}.{class_name} missing required 'landing' method - skipping")
                continue
            if not any((hasattr(workflow_class, attr) for attr in ['NAME', 'APP_NAME', 'DISPLAY_NAME', 'name', 'app_name', 'display_name'])):
                logger.warning(f'FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Plugin class {module_name}.{class_name} missing required name attributes - skipping')
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
                            args_to_pass[param_name] = CFG
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
                        logger.error(f"FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - TypeError for REGULAR plugin '{module_name}' with args {args_to_pass.keys()}: {te_regular}")
                        logger.error(f'FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Available args were: app={type(app)}, pipulate_instance/pipulate={type(pipulate)}, pipeline_table/pipeline={type(pipeline)}, db_key_value_store/db_dictlike={type(db)}')
                        logger.error(f'FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Plugin __init__ signature: {init_sig}')
                        import traceback
                        logger.error(f'FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Full traceback for {module_name}: {traceback.format_exc()}')
                        raise
                logger.debug(f'Auto-registered workflow: {module_name}')
                if hasattr(instance, 'ROLES'):
                    logger.debug(f'Plugin {module_name} has roles: {instance.ROLES}')
                endpoint_message = get_endpoint_message(module_name)
                logger.debug(f'Endpoint message for {module_name}: {endpoint_message}')
            except Exception as e:
                # Log as warning/error since these are actual plugin registration failures
                logger.warning(f'FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Error instantiating workflow {module_name}.{class_name}: {str(e)}')
                import traceback
                logger.warning(f'FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Full traceback for {module_name}.{class_name}: {traceback.format_exc()}')
                continue
        except Exception as e:
            logger.warning(f'FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Issue with workflow {module_name}.{class_name} - continuing anyway')
            logger.warning(f'FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Error type: {e.__class__.__name__}: {str(e)}')
            import traceback
            logger.warning(f'FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Full traceback for {module_name}.{class_name}: {traceback.format_exc()}')
            if inspect.iscoroutine(e):
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
    # 🔧 MCP Tools should already be registered from main startup sequence
    # This async startup event handles final initialization only
    tool_count = len(MCP_TOOL_REGISTRY)
    if tool_count > 0:
        logger.info(f"🔧 FINDER_TOKEN: STARTUP_EVENT_MCP_READY - {tool_count} MCP tools available for async startup")

    logger.bind(lifecycle=True).info('SERVER STARTUP_EVENT: Pre synchronize_roles_to_db.')
    aa.server_whisper("Synchronizing roles and permissions", "🔐")
    await synchronize_roles_to_db()

    logger.bind(lifecycle=True).info('SERVER STARTUP_EVENT: Post synchronize_roles_to_db. Final startup states:')

    # 💬 DISABLED: Conversation history restoration (prevents SQLite locking on startup)
    # The load_conversation_from_db() call creates concurrent SQLite connections that corrupt database writes
    try:
        logger.info("💬 FINDER_TOKEN: CONVERSATION_RESTORE_STARTUP - Conversation history restoration disabled to prevent database locking conflicts")
        # conversation_restored = load_conversation_from_db()  # ← DISABLED: Causes SQLite locking conflicts
        conversation_restored = False  # Always start fresh to avoid database corruption
        if conversation_restored:
            logger.info(f"💬 FINDER_TOKEN: CONVERSATION_RESTORE_SUCCESS - LLM conversation history restored from previous session")
        else:
            logger.info("💬 FINDER_TOKEN: CONVERSATION_RESTORE_NONE - Starting with fresh conversation history (SQLite locking prevention)")
    except Exception as e:
        logger.error(f"💬 FINDER_TOKEN: CONVERSATION_RESTORE_ERROR - Failed to restore conversation history: {e}")

    # 🎭 DEMO CONTINUATION CHECK - Resume demo after server restart
    try:
        demo_continuation_state = db.get('demo_continuation_state')
        if demo_continuation_state:
            logger.info(f"🎭 FINDER_TOKEN: DEMO_CONTINUATION_FOUND - Demo continuation state found: {demo_continuation_state}")
            # Store a flag for the frontend to check
            db['demo_resume_after_restart'] = True
            logger.info("🎭 FINDER_TOKEN: DEMO_CONTINUATION_FLAG_SET - Demo resume flag set for frontend")
        else:
            logger.info("🎭 FINDER_TOKEN: DEMO_CONTINUATION_NONE - No demo continuation state found")
    except Exception as e:
        logger.error(f"🎭 FINDER_TOKEN: DEMO_CONTINUATION_ERROR - Failed to check demo continuation state: {e}")

    # 🎭 DEMO RESTART FLAG CHECK - Detect if we're coming back from a demo-triggered restart (file-based)
    try:
        demo_state = get_demo_state()
        if demo_state:
            logger.info("🎭 FINDER_TOKEN: DEMO_RESTART_DETECTED - Server is coming back from a demo-triggered restart")
            # Set demo comeback message with the actual demo state for continuation
            db['demo_comeback_message'] = 'true'
            db['demo_comeback_state'] = demo_state  # Store the demo state for continuation
            clear_demo_state()  # Clear the file after transferring to database
            logger.info(f"🎭 FINDER_TOKEN: DEMO_RESTART_FLIPFLOP - Demo comeback message set with state: {demo_state}, file cleared")
        else:
            logger.info("🎭 FINDER_TOKEN: DEMO_RESTART_NONE - Normal server restart, no demo state found")
    except Exception as e:
        logger.error(f"🎭 FINDER_TOKEN: DEMO_RESTART_ERROR - Failed to check demo state file: {e}")

    # 🛡️ BACKUP SYSTEM INTEGRATION - Protect all critical data on startup
    try:
        from imports.durable_backup_system import DurableBackupManager
        backup_manager = DurableBackupManager()

        # Get dynamic database paths
        main_db_path = get_db_filename()
        keychain_db_path = 'helpers/data/ai_keychain.db'
        discussion_db_path = 'data/discussion.db'

        # Execute comprehensive backup
        aa.story_moment("Backup System", "Protecting critical data assets", BANNER_COLORS['workshop_ready'])
        backup_results = backup_manager.backup_all_databases()

        # Log results
        successful_backups = sum(1 for success in backup_results.values() if success)
        total_backups = len(backup_results)

        if successful_backups == total_backups:
            logger.info(f"🛡️ FINDER_TOKEN: BACKUP_STARTUP_SUCCESS - All {total_backups} databases backed up successfully")
        else:
            logger.warning(f"🛡️ FINDER_TOKEN: BACKUP_STARTUP_PARTIAL - {successful_backups}/{total_backups} databases backed up")

    except Exception as e:
        logger.error(f"🛡️ FINDER_TOKEN: BACKUP_STARTUP_ERROR - Backup system failed: {e}")

    aa.story_moment("Workshop Ready", "All systems initialized and ready for creative exploration", BANNER_COLORS['workshop_ready'])
    # Display startup summary tables
    try:
        from imports.durable_backup_system import backup_manager as durable_backup_manager
        from imports.ai_dictdb import keychain_instance
        
        # Display backup summary
        backup_summary_table = durable_backup_manager.get_backup_summary_table()
        slog.print_and_log_table(backup_summary_table, "STARTUP - ")

        # Display AI Keychain summary
        keychain_summary_table = keychain_instance.get_keychain_summary_table()
        slog.print_and_log_table(keychain_summary_table, "STARTUP - ")

    except Exception as e:
        logger.error(f"Failed to display startup summary tables: {e}")

    # Status information now provided by Rich startup summary tables

    slog.log_dictlike_db_to_lifecycle('db', db, title_prefix='STARTUP FINAL')
    slog.log_dynamic_table_state('profiles', lambda: profiles(), title_prefix='STARTUP FINAL')
    slog.log_pipeline_summary(pipeline, title_prefix='STARTUP FINAL')

    # Clear any stale coordination data on startup
    message_coordination['endpoint_messages_sent'].clear()
    message_coordination['last_endpoint_message_time'].clear()
    message_coordination['startup_in_progress'] = False
    logger.debug("Cleared message coordination state on startup")

    # Send environment mode message after a short delay to let UI initialize
    asyncio.create_task(send_startup_environment_message())

    # Pre-seed local LLM context for immediate capability awareness
    # asyncio.create_task(prepare_local_llm_context())
ordered_plugins = []
for module_name, class_name, workflow_class in discovered_classes:
    if module_name not in ordered_plugins and module_name in plugin_instances:
        ordered_plugins.append(module_name)

# 🔧 REGISTER ALL MCP TOOLS DYNAMICALLY - Critical for AI assistant capabilities
logger.info("🔧 FINDER_TOKEN: STARTUP_MCP_REGISTRATION - Dynamically discovering all MCP tools")
MCP_TOOL_REGISTRY = get_all_tools()
logger.info(f"🔧 FINDER_TOKEN: STARTUP_MCP_REGISTRATION_COMPLETE - {len(MCP_TOOL_REGISTRY)} tools are now available")

# Calculate startup metrics for plugin failure handling and display
discovered_count = len(discovered_classes)
registered_count = len(plugin_instances)
failed_count = discovered_count - registered_count
tool_count = len(MCP_TOOL_REGISTRY)
current_app = get_app_name()
current_env = get_current_environment()

# 🎨 MCP FIGLET BANNER - Only show when running as main script
logger.info("🔧 ASCII_MARKER_1: About to check MCP figlet banner conditions")
logger.info(f"🔧 ASCII_MARKER_1: __name__ = {__name__}, tool_count = {tool_count}")
if __name__ == '__main__' and tool_count > 0:
    logger.info("🔧 ASCII_MARKER_2: Displaying MCP figlet banner and section header")
    aa.figlet_banner("MCP", "Model Context Protocol Tools", font='standard', color='magenta')
    aa.section_header("🔧", "MCP Arsenal", f"Equipped with {tool_count} AI-powered tools for transparency", "bright_blue")
    logger.info("🔧 ASCII_MARKER_3: MCP figlet banner and section header displayed")
    # Half-second delay so humans can notice this major feature before it scrolls away
    import time
    time.sleep(0.5)
else:
    logger.info("🔧 ASCII_MARKER_X: MCP figlet banner conditions not met - skipped")

# 📊 ELEGANT STARTUP SUMMARY - Rich tables for humans, FINDER_TOKEN for AIs
logger.info("🔧 STARTUP_MARKER_1: About to check __name__ == '__main__' condition")
logger.info(f"🔧 STARTUP_MARKER_1: __name__ value is: {__name__}")
if __name__ == '__main__':
    logger.info("🔧 STARTUP_MARKER_2: Inside __name__ == '__main__' block - showing Rich tables")
    # Show beautiful startup summary for humans
    startup_summary = aa.startup_summary_table(
        apps_discovered=discovered_count,
        apps_registered=registered_count,
        mcp_tools_count=tool_count,
        app_name=current_app,
        environment=current_env
    )
    slog.safe_print(startup_summary)
    logger.info("🔧 STARTUP_MARKER_3: aa.startup_summary_table displayed")

    # Show AI capabilities summary
    ai_summary = aa.ai_breadcrumb_summary(tool_count)
    slog.safe_print(ai_summary)
    logger.info("🔧 STARTUP_MARKER_4: ai_breadcrumb_summary displayed")

    # Show critical environment warnings
    warnings_summary = aa.startup_environment_warnings()
    slog.safe_print(warnings_summary)
    logger.info("🔧 STARTUP_MARKER_5: aa.startup_environment_warnings displayed")
else:
    logger.info("🔧 STARTUP_MARKER_X: NOT in __name__ == '__main__' block - Rich tables skipped")

# Handle plugin registration failures
if failed_count > 0:
    failed_plugins = []
    for module_name, class_name, workflow_class in discovered_classes:
        if module_name not in plugin_instances:
            failed_plugins.append(f'{module_name}.{class_name}')
    aa.server_whisper(f"Some plugins need attention: {', '.join(failed_plugins)}", "⚠️")
    logger.warning(f'FINDER_TOKEN: PLUGIN_REGISTRATION_SUMMARY - Failed plugins: {", ".join(failed_plugins)}')
else:
    aa.chip_says("All plugins loaded successfully! The workshop is fully equipped.", BANNER_COLORS['plugin_registry_success'])
# 🔍 RADICAL TRANSPARENCY BANNER - Right after MCP registry completes, before FINDER_TOKEN loop
logger.info("🔧 TRANSPARENCY_MARKER_1: About to check radical transparency banner conditions")
logger.info(f"🔧 TRANSPARENCY_MARKER_1: __name__ = {__name__}")
if __name__ == '__main__':
    logger.info("🔧 TRANSPARENCY_MARKER_2: Displaying radical transparency banner")
    aa.radical_transparency_banner()
    logger.info("🔧 TRANSPARENCY_MARKER_3: aa.radical_transparency_banner displayed")
else:
    logger.info("🔧 TRANSPARENCY_MARKER_X: radical transparency banner conditions not met - skipped")

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
    url_path = request.url.path.strip('/')
    logger.debug(f'Received request for path: {url_path}')
    menux = normalize_menu_path(url_path)
    logger.debug(f'Selected explore item: {menux}')
    db['last_app_choice'] = menux
    db['last_visited_url'] = request.url.path
    current_profile_id = get_current_profile_id()
    menux = db.get('last_app_choice', 'App')
    # 🎬 CINEMATIC MAGIC: Check for Oz door grayscale state
    grayscale_enabled = db.get('oz_door_grayscale') == 'true'
    if grayscale_enabled:
        logger.info("🎬 Oz door grayscale state detected - injecting script into Container")

    response = await create_outer_container(current_profile_id, menux, request, grayscale_enabled)
    last_profile_name = get_profile_name()
    page_title = f'{APP_NAME} - {title_name(last_profile_name)} - {(endpoint_name(menux) if menux else HOME_MENU_ITEM)}'

    # Backup mechanism: send endpoint message if not yet sent for this session
    current_env = get_current_environment()
    session_key = f'endpoint_message_sent_{menux}_{current_env}'

    # Check coordination system to prevent duplicates
    endpoint_message = build_endpoint_messages(menux)
    if endpoint_message and session_key not in db:
        # Create unique message identifier for coordination
        message_id = f'{menux}_{current_env}_{hash(endpoint_message) % 10000}'

        # Check if this message was recently sent through any pathway
        current_time = time.time()
        last_sent = message_coordination['last_endpoint_message_time'].get(message_id, 0)

        # Only send if not recently sent and startup is not in progress
        if (current_time - last_sent > 10 and
            not message_coordination['startup_in_progress'] and
                message_id not in message_coordination['endpoint_messages_sent']):

            try:
                # Add training to conversation history
                build_endpoint_training(menux)

                # Mark as being sent to prevent other systems from sending
                message_coordination['last_endpoint_message_time'][message_id] = current_time
                message_coordination['endpoint_messages_sent'].add(message_id)

                # Send endpoint message with coordination
                asyncio.create_task(send_delayed_endpoint_message(endpoint_message, session_key))
                logger.debug(f"Scheduled backup endpoint message: {message_id}")
            except Exception as e:
                logger.error(f'Error sending backup endpoint message: {e}')
        else:
            logger.debug(f"Skipping backup endpoint message - coordination check failed: {message_id}")

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
    return Div(nav, refresh_listener, app_menu_refresh_listener, id='nav-group', role='navigation', aria_label='Main navigation')


def create_env_menu():
    """Create environment selection dropdown menu."""
    current_env = get_current_environment()
    display_env = 'DEV' if current_env == 'Development' else 'Prod'
    env_summary_classes = 'inline-nowrap'
    if current_env == 'Development':
        env_summary_classes += ' env-dev-style'
    menu_items = []
    is_dev = current_env == 'Development'
    dev_classes = 'menu-item-base menu-item-hover'
    if is_dev:
        dev_classes += ' menu-item-active'
    dev_item = Li(Label(Input(type='radio', name='env_radio_select', value='Development', checked=is_dev, hx_post='/switch_environment', hx_vals='{"environment": "Development"}', hx_target='#dev-env-item', hx_swap='outerHTML', cls='ml-quarter', aria_label='Switch to Development environment', data_testid='env-dev-radio'), 'DEV', cls='dropdown-menu-item'), cls=dev_classes, id='dev-env-item', data_testid='env-dev-item')
    menu_items.append(dev_item)
    is_prod = current_env == 'Production'
    prod_classes = 'menu-item-base menu-item-hover'
    if is_prod:
        prod_classes += ' menu-item-active'
    prod_item = Li(Label(Input(type='radio', name='env_radio_select', value='Production', checked=is_prod, hx_post='/switch_environment', hx_vals='{"environment": "Production"}', hx_target='#prod-env-item', hx_swap='outerHTML', cls='ml-quarter', aria_label='Switch to Production environment', data_testid='env-prod-radio'), 'Prod', cls='dropdown-menu-item'), cls=prod_classes, id='prod-env-item', data_testid='env-prod-item')
    menu_items.append(prod_item)
    return Details(
        Summary(
            display_env,
            cls=env_summary_classes,
            id='env-id',
            aria_label='Environment selection menu',
            aria_expanded='false',
            aria_haspopup='menu'
        ),
        Ul(
            *menu_items,
            cls='dropdown-menu env-dropdown-menu',
            role='menu',
            aria_label='Environment options',
            aria_labelledby='env-id'
        ),
        cls='dropdown',
        id='env-dropdown-menu',
        aria_label='Environment management',
        data_testid='environment-dropdown-menu'
    )


def create_nav_menu():
    logger.debug('Creating navigation menu.')
    menux = db.get('last_app_choice', 'App')
    selected_profile_id = get_current_profile_id()
    selected_profile_name = get_profile_name()
    profiles_plugin_inst = plugin_instances.get('profiles')
    if not profiles_plugin_inst:
        logger.error("Could not get 'profiles' plugin instance for menu creation")
        return Div(H1('Error: Profiles plugin not found', cls='text-invalid'), cls='nav-breadcrumb')
    home_link = A(APP_NAME, href='/redirect/', title=f'Go to {HOME_MENU_ITEM.lower()}', cls='nav-link-hover')
    separator = Span(' / ', cls='breadcrumb-separator')
    profile_link = A(title_name(selected_profile_name), href="/redirect/profiles", title="Go to profiles app", cls="nav-link-hover")
    endpoint_text = Span(endpoint_name(menux) if menux else HOME_MENU_ITEM)
    breadcrumb = H1(home_link, separator, profile_link, separator, endpoint_text, role='banner', aria_label='Current location breadcrumb')
    # Create navigation poke button for the nav area
    # Create SVG icon for poke button
    settings_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-settings"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>'''
    nav_flyout_panel = Div(id='nav-flyout-panel', cls='nav-flyout-panel hidden')
    poke_section = Details(
        Summary(NotStr(settings_svg), cls='inline-nowrap nav-poke-button', id='poke-summary', hx_get='/poke-flyout', hx_target='#nav-flyout-panel', hx_trigger='mouseenter', hx_swap='outerHTML'),
        nav_flyout_panel,
        cls='dropdown nav-poke-section',
        id='poke-dropdown-menu'
    )
    # Create navigation search field (positioned before PROFILE)
    # HTMX real-time search implementation with keyboard navigation
    # Search container with dropdown results
    search_results_dropdown = Div(id='search-results-dropdown', cls='search-dropdown', role='listbox', aria_label='Search results')

    nav_search_container = Div(
        Input(
            type='search',
            name='search',
            placeholder='Search plugins (Ctrl+K)',
            cls='nav-search nav-search-input',
            id='nav-plugin-search',
            hx_post='/search-apps',
            hx_target='#search-results-dropdown',
            hx_trigger='input changed delay:300ms, keyup[key==\'Enter\'], focus',
            hx_swap='innerHTML',
            role='searchbox',
            aria_label='Search plugins',
            aria_describedby='search-results-dropdown',
            aria_autocomplete='list',
            aria_expanded='false'
            # Keyboard navigation now handled by external JavaScript in pipulate.js
        ),
        search_results_dropdown,
        cls='search-dropdown-container',
        role='search',
        aria_label='Plugin search'
    )

    menus = Div(nav_search_container, create_profile_menu(selected_profile_id, selected_profile_name), create_app_menu(menux), create_env_menu(), poke_section, cls='nav-menu-group')
    nav = Div(breadcrumb, menus, cls='nav-breadcrumb')
    logger.debug('Navigation menu created.')
    return nav


def create_profile_menu(selected_profile_id, selected_profile_name):
    """Create the profile dropdown menu."""
    menu_items = []
    profile_locked = db.get('profile_locked', '0') == '1'
    menu_items.append(Li(Label(Input(type='checkbox', name='profile_lock_switch', role='switch', checked=profile_locked, hx_post='/toggle_profile_lock', hx_target='body', hx_swap='outerHTML', aria_label='Lock or unlock profile editing'), 'Lock Profile', cls='dropdown-menu-item'), cls='profile-menu-item'))
    menu_items.append(Li(Hr(cls='profile-menu-separator'), cls='block'))
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
        radio_input = Input(type='radio', name='profile_radio_select', value=str(profile_item.id), checked=is_selected, hx_post='/select_profile', hx_vals=json.dumps({'profile_id': str(profile_item.id)}), hx_target='body', hx_swap='outerHTML', aria_label=f'Select {profile_item.name} profile')
        label_classes = 'dropdown-menu-item'
        if is_selected:
            label_classes += ' profile-menu-item-selected'
        profile_label = Label(radio_input, profile_item.name, cls=label_classes)
        menu_item_classes = 'menu-item-base menu-item-hover'
        if is_selected:
            menu_item_classes += ' menu-item-active'
        menu_items.append(Li(profile_label, cls=menu_item_classes))
    summary_profile_name_to_display = selected_profile_name
    if not summary_profile_name_to_display and selected_profile_id:
        try:
            profile_obj = profiles.get(int(selected_profile_id))
            if profile_obj:
                summary_profile_name_to_display = profile_obj.name
        except Exception:
            pass
    summary_profile_name_to_display = summary_profile_name_to_display or 'Select'
    return Details(Summary('👤 PROFILE', cls='inline-nowrap', id='profile-id', aria_label='Profile selection menu', aria_expanded='false', aria_haspopup='menu'), Ul(*menu_items, cls='dropdown-menu profile-dropdown-menu', role='menu', aria_label='Profile options', aria_labelledby='profile-id'), cls='dropdown', id='profile-dropdown-menu', aria_label='Profile management')


def normalize_menu_path(path):
    """Convert empty paths to empty string and return the path otherwise."""
    return '' if path == '' else path


def generate_menu_style():
    """Generate consistent menu styling for dropdown menus."""
    border_radius = CFG.UI_CONSTANTS['BUTTON_STYLES']['BORDER_RADIUS']
    return f'white-space: nowrap; display: inline-block; min-width: max-content; background-color: var(--pico-background-color); border: 1px solid var(--pico-muted-border-color); border-radius: {border_radius}; padding: 0.5rem 1rem; cursor: pointer; transition: background-color 0.2s;'


def create_app_menu(menux):
    """Create the App dropdown menu with hierarchical role-based sorting."""
    logger.debug(f"Creating App menu. Currently selected app (menux): '{menux}'")
    active_role_names = get_active_roles()
    menu_items = create_home_menu_item(menux)
    role_priorities = get_role_priorities()
    apps_by_role = group_apps_by_role(active_role_names)
    for role_name, role_priority in sorted(role_priorities.items(), key=lambda x: x[1]):
        if role_name in active_role_names:
            role_plugins = apps_by_role.get(role_name, [])
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


def group_apps_by_role(active_role_names):
    """Group plugins by their primary role for hierarchical menu organization."""
    apps_by_role = {}
    for plugin_key in ordered_plugins:
        plugin_instance = plugin_instances.get(plugin_key)
        if not plugin_instance:
            continue
        if not should_include_plugin(plugin_instance, active_role_names):
            continue
        primary_role = get_plugin_primary_role(plugin_instance)
        if primary_role:
            role_name = primary_role.replace('-', ' ').title()
            if role_name not in apps_by_role:
                apps_by_role[role_name] = []
            apps_by_role[role_name].append(plugin_key)
    logger.debug(f'Plugins grouped by role: {apps_by_role}')
    return apps_by_role


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
    home_radio = Input(type='radio', name='app_radio_select', value='', checked=is_home_selected, hx_post='/redirect/', hx_target='body', hx_swap='outerHTML', aria_label='Navigate to home page')
    home_css_classes = 'dropdown-item'
    if is_home_selected:
        home_css_classes += ' app-menu-item-selected'
    home_label = Label(home_radio, get_home_menu_item(), cls=home_css_classes)
    menu_items.append(Li(home_label))
    return menu_items


def get_plugin_primary_role(plugin_instance):
    """Get the primary role for a plugin for UI styling purposes.

    Uses a simple 80/20 approach: if plugin has multiple roles, 
    we take the first one as primary. This creates a clean win/loss
    scenario for coloring without complex blending logic.

    Returns lowercase role name with spaces replaced by hyphens for CSS classes.
    """
    plugin_module_path = plugin_instance.__module__
    plugin_module = sys.modules.get(plugin_module_path)
    plugin_defined_roles = getattr(plugin_module, 'ROLES', []) if plugin_module else []
    if not plugin_defined_roles:
        return None
    primary_role = plugin_defined_roles[0]
    css_role = primary_role.lower().replace(' ', '-')
    logger.debug(f"Plugin '{plugin_instance.__class__.__name__}' primary role: '{primary_role}' -> CSS class: 'menu-role-{css_role}'")
    return css_role


def create_plugin_menu_item(plugin_key, menux, active_role_names):
    """Create menu item for a plugin if it should be included based on roles."""
    plugin_instance = plugin_instances.get(plugin_key)
    if not plugin_instance:
        logger.warning(f"Instance for plugin_key '{plugin_key}' not found. Skipping.")
        return None

    if not should_include_plugin(plugin_instance, active_role_names):
        return None
    display_name = getattr(plugin_instance, 'DISPLAY_NAME', title_name(plugin_key))
    is_selected = menux == plugin_key
    redirect_url = f"/redirect/{(plugin_key if plugin_key else '')}"
    primary_role = get_plugin_primary_role(plugin_instance)
    role_class = f'menu-role-{primary_role}' if primary_role else ''
    css_classes = f'dropdown-item {role_class}'.strip()
    if is_selected:
        css_classes += ' app-menu-item-selected'
    radio_input = Input(type='radio', name='app_radio_select', value=plugin_key, checked=is_selected, hx_post=redirect_url, hx_target='body', hx_swap='outerHTML', aria_label=f'Navigate to {display_name}')
    return Li(Label(radio_input, display_name, cls=css_classes))


def should_include_plugin(plugin_instance, active_role_names):
    """Determine if plugin should be included based on its roles."""
    plugin_module_path = plugin_instance.__module__
    plugin_module = sys.modules.get(plugin_module_path)
    plugin_defined_roles = getattr(plugin_module, 'ROLES', []) if plugin_module else []
    is_core_plugin = 'Core' in plugin_defined_roles
    has_matching_active_role = any((p_role in active_role_names for p_role in plugin_defined_roles))
    should_include = is_core_plugin or has_matching_active_role
    logger.debug(f"Plugin '{plugin_instance.__class__.__name__}' (Roles: {plugin_defined_roles}). Core: {is_core_plugin}, Active Roles: {active_role_names}, Match: {has_matching_active_role}, Include: {should_include}")
    return should_include


def create_menu_container(menu_items):
    """Create the final menu container with all items."""
    return Details(Summary('⚡ APP', cls='inline-nowrap', id='app-id', aria_label='Application menu', aria_expanded='false', aria_haspopup='menu'), Ul(*menu_items, cls='dropdown-menu', role='menu', aria_label='Application options', aria_labelledby='app-id'), cls='dropdown', id='app-dropdown-menu', aria_label='Application selection')


def get_dynamic_role_css():
    """Generate dynamic role CSS from centralized CFG - single source of truth."""
    try:
        role_colors = getattr(CFG, 'ROLE_COLORS', {})
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


async def create_outer_container(current_profile_id, menux, request, grayscale_enabled=False):
    profiles_plugin_inst = plugin_instances.get('profiles')
    if not profiles_plugin_inst:
        logger.error("Could not get 'profiles' plugin instance for container creation")
        return Container(H1('Error: Profiles plugin not found', cls='text-invalid'))

    # Inject dynamic role CSS - single source of truth
    dynamic_css = get_dynamic_role_css()
    nav_group = create_nav_group()

    # Get saved sizes from DB, with a default of [65, 35]
    saved_sizes_str = db.get('split-sizes', '[65, 35]')

    # Initialize splitter script with server-provided sizes
    init_splitter_script = Script(f"""
        document.addEventListener('DOMContentLoaded', function() {{
            if (window.initializePipulateSplitter) {{
                const elements = ['#grid-left-content', '#chat-interface'];
                const options = {{
                    sizes: {saved_sizes_str},
                    minSize: [400, 300],
                    gutterSize: 10,
                    cursor: 'col-resize'
                }};
                initializePipulateSplitter(elements, options);
            }}
        }});
    """)

    # 🎬 CINEMATIC MAGIC: Prepare grayscale script if enabled
    container_contents = [
        Style(dynamic_css),  # Dynamic CSS injection
        nav_group,
        Div(await create_grid_left(menux, request), create_chat_interface(), cls='main-grid'),
        init_splitter_script  # Initialize the draggable splitter
    ]

    if grayscale_enabled:
        # Add sepia script to Container (no extra wrapper div)
        sepia_script = Script(f"""
            // 🎬 IMMEDIATE sepia application - no delay, no flash
            (function() {{
                // Apply sepia class immediately (CSS handles the visual effect)
                document.documentElement.classList.add('demo-grayscale');
                console.log('🎬 INSTANT sepia applied from server - Kansas farmhouse mode activated!');
                
                // 🎬 AUTOMATIC TRANSITION: Start the fade to color after page loads
                document.addEventListener('DOMContentLoaded', function() {{
                    // Call the transition function if it exists
                    if (window.executeOzDoorTransition) {{
                        window.executeOzDoorTransition();
                    }} else {{
                        // Fallback: Start transition when the function becomes available
                        const checkForTransition = setInterval(function() {{
                            if (window.executeOzDoorTransition) {{
                                clearInterval(checkForTransition);
                                window.executeOzDoorTransition();
                            }}
                        }}, 100); // Check every 100ms
                    }}
                }});
            }})();
        """)
        container_contents.insert(0, sepia_script)  # Insert at the beginning
        logger.info("🎬 Oz door sepia script injected into Container structure")

    return Container(*container_contents)


def get_workflow_instance(workflow_name):
    """
    Get a workflow instance from the plugin_instances dictionary.

    Args:
        workflow_name: The name of the workflow to retrieve

    Returns:
        The workflow instance if found, None otherwise
    """
    return plugin_instances.get(workflow_name)


async def create_grid_left(menux, request):
    """Create the left grid content based on the selected menu item.

    Args:
        menux: The selected menu item key
        request: The HTTP request object
        render_items: Optional items to render (unused)

    Returns:
        Div: Container with the rendered content and scroll controls
    """
    content_to_render = None
    profiles_plugin_key = 'profiles'

    # Handle profiles plugin selection
    if menux == profiles_plugin_key:
        profiles_instance = plugin_instances.get(profiles_plugin_key)
        if profiles_instance:
            content_to_render = await profiles_instance.landing(request)
        else:
            logger.error(f"Plugin '{profiles_plugin_key}' not found in plugin_instances for create_grid_left.")
            content_to_render = Card(H3('Error'), P(f"Plugin '{profiles_plugin_key}' not found."))

    # Handle workflow plugin selection
    elif menux:
        workflow_instance = get_workflow_instance(menux)
        if workflow_instance:
            if hasattr(workflow_instance, 'ROLES') and DEBUG_MODE:
                logger.debug(f'Selected plugin {menux} has roles: {workflow_instance.ROLES}')
            content_to_render = await workflow_instance.landing(request)

    # Handle homepage (no menu selection)
    else:
        # --- START CHANGE ---
        home_app_name = getattr(CFG, 'HOME_APP', 'roles')
        home_app_instance = plugin_instances.get(home_app_name)
        if home_app_instance:
            content_to_render = await home_app_instance.landing(request)
        else:
            logger.error(f"Configured home app '{home_app_name}' not found. Please check config.py.")
            content_to_render = Card(H3('Welcome'), P(f"Homepage app '{home_app_name}' not found."))
        # --- END CHANGE ---

    # Fallback content if nothing was rendered
    if content_to_render is None:
        content_to_render = Card(
            H3('Welcome'),
            P('Select an option from the menu to begin.'),
            style='min-height: 400px'
        )

    # Create scroll-to-top button
    scroll_to_top = Div(
        A('↑ Scroll To Top',
          href='javascript:void(0)',
          onclick='scrollToTop()',
          style='text-decoration: none'
          ),
        style=(
            'border-top: 1px solid var(--pico-muted-border-color); '
            'display: none; '
            'margin-top: 20px; '
            'padding: 10px; '
            'text-align: center'
        ),
        id='scroll-to-top-link'
    )

    return Div(
        content_to_render,
        scroll_to_top,
        id='grid-left-content'
    )


def create_chat_interface(autofocus=False):
    """Creates the chat interface component with message list and input form.

    Args:
        autofocus (bool): Whether to autofocus the chat input field

    Returns:
        Div: The chat interface container with all components
    """
    msg_list_height = 'height: calc(75vh - 200px);'
    temp_message = None
    if 'temp_message' in db:
        temp_message = db['temp_message']
        del db['temp_message']
    init_script = f'\n    // Set global variables for the external script\n    window.CFG = {{\n        tempMessage: {json.dumps(temp_message)},\n        clipboardSVG: {json.dumps(CFG.SVG_ICONS["CLIPBOARD"])}\n    }};\n    window.APP_NAME = {json.dumps(APP_NAME)};\n    '
    # Enter/Shift+Enter handling is now externalized in pipulate.js
    return Div(Card(H2(f'{APP_NAME} Chatbot'), Div(id='msg-list', cls='overflow-auto', style=msg_list_height, role='log', aria_label='Chat conversation', aria_live='polite'), Form(mk_chat_input_group(value='', autofocus=autofocus), onsubmit='sendSidebarMessage(event)', role='form', aria_label='Chat input form'), Script(init_script), Script(src='/assets/pipulate-init.js'), Script('initializeChatInterface();')), id='chat-interface', role='complementary', aria_label='AI Assistant Chat')


# Global variable to track streaming state
is_streaming = False


def mk_chat_input_group(disabled=False, value='', autofocus=True):
    """
    Create a chat input group with a textarea input and run/stop buttons in a modern chatbot layout.

    Args:
        disabled (bool): Whether the input group should be disabled.
        value (str): The pre-filled value for the input field.
        autofocus (bool): Whether the input field should autofocus.

    Returns:
        Group: An HTML group containing the chat textarea and buttons in a modern layout.
    """
    global is_streaming
    # Determine the icon to display based on the streaming state
    icon_src = '/assets/feather/x-octagon.svg' if is_streaming else '/assets/feather/arrow-up-circle.svg'
    icon_alt = 'Stop' if is_streaming else 'Run'

    return Group(
        Textarea(
            value,
            id='msg',
            name='msg',
            placeholder='Chat...',
            disabled=disabled,
            autofocus='autofocus' if autofocus else None,
            required=True,
            aria_required='true',
            aria_label='Chat message input',
            aria_describedby='send-btn',
            role='textbox',
            aria_multiline='true'
        ),
        Div(
            Button(
                Img(src=icon_src, alt=icon_alt),
                type='submit',
                id='send-btn',
                disabled=disabled,
                aria_label='Send message to AI assistant',
                title='Send message (Enter or click)'
            ),
            Button(
                Img(src='/assets/feather/x-octagon.svg', alt='Stop'),
                type='button',
                id='stop-btn',
                disabled=False,  # Enabled, JS will control visibility
                onclick='stopSidebarStream()',
                aria_label='Stop AI response streaming',
                title='Stop current response'
            ),
            cls='button-container',
        ),
        id='input-group',
        aria_label='Chat input controls'
    )

# Old create_poke_button function removed - now using nav poke button


@rt('/poke-flyout', methods=['GET'])
async def poke_flyout(request):
    current_app = db.get('last_app_choice', '')
    workflow_instance = get_workflow_instance(current_app)
    is_workflow = workflow_instance is not None and hasattr(workflow_instance, 'steps')
    profile_locked = db.get('profile_locked', '0') == '1'
    lock_button_text = '🔓 Unlock Profile' if profile_locked else '🔒 Lock Profile'
    is_dev_mode = get_current_environment() == 'Development'

    # Get current theme setting (default to 'dark' for new users)
    current_theme = db.get('theme_preference', 'dark')
    theme_is_dark = current_theme == 'dark'

    # Create buttons
    lock_button = Button(lock_button_text, hx_post='/toggle_profile_lock', hx_target='body', hx_swap='outerHTML', cls='secondary outline')

    # Theme toggle switch
    theme_switch = Div(
        Label(
            Input(
                type='checkbox',
                role='switch',
                name='theme_switch',
                checked=theme_is_dark,
                hx_post='/toggle_theme',
                hx_target='#theme-switch-container',
                hx_swap='outerHTML'
            ),
            Span('🌙 Dark Mode', cls='ml-quarter')
        ),
        Script(f"""
            // Ensure switch state matches localStorage (sticky preference)
            (function() {{
                const currentTheme = localStorage.getItem('theme_preference') || 'dark';
                const serverTheme = '{current_theme}';
                
                // localStorage is the source of truth for stickiness
                if (currentTheme !== serverTheme) {{
                    // Update server to match localStorage
                    fetch('/sync_theme', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                        body: 'theme=' + currentTheme
                    }});
                }}
                
                // Ensure DOM reflects localStorage
                document.documentElement.setAttribute('data-theme', currentTheme);
                
                // Update switch state to match localStorage
                const switchElement = document.querySelector('#theme-switch-container input[type="checkbox"]');
                if (switchElement) {{
                    switchElement.checked = (currentTheme === 'dark');
                }}
            }})();
        """),
        id='theme-switch-container',
        cls='theme-switch-container'
    )
    delete_workflows_button = Button('🗑️ Clear Workflows', hx_post='/clear-pipeline', hx_target='body', hx_confirm='Are you sure you want to delete workflows?', hx_swap='outerHTML', cls='secondary outline') if is_workflow else None
    # Create reset button with different labels for DEV vs PROD mode
    # Database reset button - only available when in DEV mode for safety
    if is_dev_mode:
        reset_db_button = Button('🔄 Reset Entire DEV Database',
                                 hx_post='/clear-db',
                                 hx_target='body',
                                 hx_confirm='WARNING: This will reset the ENTIRE DEV DATABASE to its initial state. All DEV profiles, workflows, and plugin data will be deleted. Are you sure?',
                                 hx_swap='none',  # No immediate swap - let server restart handle the reload
                                 cls='secondary outline',
                                 **{'hx-on:click': '''
                                    triggerFullScreenRestart("Resetting database...", "RESET_DATABASE");
                                '''})
    else:
        # Production mode - no database reset option (user must switch to DEV mode first)
        reset_db_button = None
    reset_python_button = Button('🐍 Reset Python Environment',
                                 hx_post='/reset-python-env',
                                 hx_target='#msg-list',
                                 hx_swap='beforeend',
                                 hx_confirm='⚠️ This will remove the .venv directory and require a manual restart. You will need to type "exit" then "nix develop" to rebuild the environment. Continue?',
                                 cls='secondary outline dev-button-muted',
                                 **{'hx-on:click': '''
                                    triggerPythonEnvironmentReset();
                                '''}) if is_dev_mode else None
    mcp_test_button = Button(f'🤖 MCP Test {MODEL}', hx_post='/poke', hx_target='#msg-list', hx_swap='beforeend', cls='secondary outline')

    # Add Update button (full-screen effect only triggers on actual restart)
    update_button = Button(f'🔄 Update {APP_NAME}',
                           hx_post='/update-pipulate',
                           hx_target='#msg-list',
                           hx_swap='beforeend',
                           cls='secondary outline')

    # Add version info display
    nix_version = get_nix_version()
    git_hash = get_git_hash()
    version_info = Div(
        Span(f'🧊 Pipulate: {nix_version}', cls='version-info-text'),
        Br(),
        Span(f'📝 Git: {git_hash}', cls='version-info-text git-hash'),
        Br(),
        Span('🖥️ Platform: ', Span('Detecting...', id='platform-info'), cls='version-info-text'),
        Script('''
            // Platform detection for Mac keyboard shortcuts
            (function() {
                const platform = navigator.platform.toLowerCase();
                const userAgent = navigator.userAgent.toLowerCase();
                let platformName = 'Unknown';
                
                if (platform.includes('mac') || userAgent.includes('mac')) {
                    platformName = 'Mac';
                } else if (platform.includes('win') || userAgent.includes('windows')) {
                    platformName = 'Windows';
                } else if (platform.includes('linux') || userAgent.includes('linux')) {
                    platformName = 'Linux';
                }
                
                const platformElement = document.getElementById('platform-info');
                if (platformElement) {
                    platformElement.textContent = platformName;
                }
            })();
        '''),
        cls='version-info-container'
    )

    # Build list items in the requested order: Theme Toggle, Lock Profile, Update, Clear Workflows, Reset Database, MCP Test
    list_items = [
        Li(theme_switch, cls='flyout-list-item'),
        Li(lock_button, cls='flyout-list-item'),
        Li(update_button, cls='flyout-list-item')
    ]
    if is_workflow:
        list_items.append(Li(delete_workflows_button, cls='flyout-list-item'))
    # Add reset button only when available (DEV mode only for safety)
    if reset_db_button:
        list_items.append(Li(reset_db_button, cls='flyout-list-item'))
    if is_dev_mode:
        list_items.append(Li(reset_python_button, cls='flyout-list-item'))
    list_items.append(Li(mcp_test_button, cls='flyout-list-item'))

    # Always use nav flyout now - no more fallback to old flyout
    target_id = 'nav-flyout-panel'
    css_class = 'nav-flyout-panel visible'
    return Div(id=target_id, cls=css_class, hx_get='/poke-flyout-hide', hx_trigger='mouseleave delay:100ms', hx_target='this', hx_swap='outerHTML')(Div(H3('Settings'), Ul(*list_items), version_info, cls='flyout-content'))


@rt('/poke-flyout-hide', methods=['GET'])
async def poke_flyout_hide(request):
    """Hide the poke flyout panel by returning an empty hidden div."""
    # Check referer or hx-current-url to determine which flyout to hide
    referer = request.headers.get('Referer', '')
    current_url = request.headers.get('HX-Current-URL', referer)
    # Default to nav flyout now since that's our primary implementation
    target_id = 'nav-flyout-panel'
    css_class = 'nav-flyout-panel hidden'
    return Div(id=target_id, cls=css_class)


@rt('/sse')
async def sse_endpoint(request):
    return EventStream(broadcaster.generator())


@app.post('/chat')
async def chat_endpoint(request, message: str):
    await pipulate.stream(f'Let the user know {limiter} {message}')
    return ''


@app.post('/add-to-conversation-history')
async def add_to_conversation_history_endpoint(request):
    """
    Add a message directly to conversation history without triggering LLM processing.
    Used by demo system for phantom dialogue integration.
    """
    try:
        form_data = await request.form()
        role = form_data.get('role', 'user')
        content = form_data.get('content', '')

        if content:
            # Use the existing append_to_conversation function that adds to history without triggering LLM
            append_to_conversation(content, role)
            logger.info(f"🎯 DEMO: Added to conversation history - {role}: {content[:100]}...")

        return ''
    except Exception as e:
        logger.error(f"Error adding to conversation history: {e}")
        return ''


@app.get('/demo-bookmark-check')
async def demo_bookmark_check():
    """Check if there's a demo bookmark to resume"""
    try:
        demo_bookmark = db.get('demo_bookmark')
        if demo_bookmark:
            logger.info(f"📖 Retrieved bookmark data type: {type(demo_bookmark)}")
            logger.info(f"📖 Retrieved bookmark data: {demo_bookmark}")
            return JSONResponse({"has_bookmark": True, "bookmark": demo_bookmark})
        else:
            logger.info("📖 No demo bookmark found")
            return JSONResponse({"has_bookmark": False})
    except Exception as e:
        logger.error(f"Error checking demo bookmark: {e}")
        return JSONResponse({"has_bookmark": False, "error": str(e)})


@app.post('/demo-bookmark-store')
async def demo_bookmark_store(request):
    """Store demo bookmark before navigation"""
    try:
        data = await request.json()
        logger.info(f"📖 About to store bookmark data type: {type(data)}")
        logger.info(f"📖 About to store bookmark data: {data}")
        db['demo_bookmark'] = data
        logger.info(f"📖 Demo bookmark stored: {data.get('script_name', 'UNKNOWN')}")
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"Error storing demo bookmark: {e}")
        return JSONResponse({"success": False, "error": str(e)})


@app.post('/demo-bookmark-clear')
async def demo_bookmark_clear():
    """Clear demo bookmark to prevent infinite loop"""
    try:
        if 'demo_bookmark' in db:
            del db['demo_bookmark']
            logger.info("📖 Demo bookmark cleared")
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"Error clearing demo bookmark: {e}")
        return JSONResponse({"success": False, "error": str(e)})


@app.post('/oz-door-grayscale-store')
async def oz_door_grayscale_store(request):
    """Store Oz door grayscale state for cinematic transition"""
    try:
        db['oz_door_grayscale'] = 'true'
        logger.info("🎬 Oz door grayscale state stored for cinematic transition")
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"Error storing Oz door grayscale state: {e}")
        return JSONResponse({"success": False, "error": str(e)})


@app.post('/oz-door-grayscale-clear')
async def oz_door_grayscale_clear():
    """Clear Oz door grayscale state"""
    try:
        if 'oz_door_grayscale' in db:
            del db['oz_door_grayscale']
            logger.info("🎬 Oz door grayscale state cleared")
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"Error clearing Oz door grayscale state: {e}")
        return JSONResponse({"success": False, "error": str(e)})


@app.post('/test-voice-synthesis')
async def test_voice_synthesis_endpoint(request):
    """Test voice synthesis endpoint for debugging - callable via Ctrl+Alt+v"""
    try:
        # Import voice synthesis system
        from imports.voice_synthesis import (VOICE_SYNTHESIS_AVAILABLE,
                                             chip_voice_system)

        # Get test text from request or use default
        form_data = await request.form()
        test_text = form_data.get('text', 'This is a voice synthesis test from the web interface.')

        logger.info(f"🎤 Voice synthesis test endpoint called with text: {test_text}")

        # Check if voice synthesis is available
        if not VOICE_SYNTHESIS_AVAILABLE:
            logger.error("🎤 Voice synthesis not available")
            return JSONResponse({"success": False, "error": "Voice synthesis not available"})

        # Check if voice system is ready
        if not chip_voice_system.voice_ready:
            logger.error("🎤 Voice system not ready")
            return JSONResponse({"success": False, "error": "Voice system not ready"})

        # Test voice synthesis
        logger.info("🎤 Attempting voice synthesis...")
        result = chip_voice_system.speak_text(test_text)

        logger.info(f"🎤 Voice synthesis result: {result}")

        return JSONResponse({
            "success": result.get("success", False),
            "message": result.get("message", "Unknown result"),
            "text": test_text,
            "voice_model": result.get("voice_model", "unknown"),
            "voice_ready": chip_voice_system.voice_ready,
            "voice_synthesis_available": VOICE_SYNTHESIS_AVAILABLE
        })

    except Exception as e:
        logger.error(f"🎤 Voice synthesis test endpoint error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


@rt('/redirect/{path:path}')
def redirect_handler(request):
    path = request.path_params['path']

    logger.debug(f'Redirecting to: /{path}')
    message = build_endpoint_messages(path)
    if message:
        prompt = read_training(message)
        append_to_conversation(prompt, role='system')

        # Always set temp_message for redirects - this is legitimate navigation
        # The coordination system will prevent race condition duplicates in other pathways
        db['temp_message'] = message
        logger.debug(f"Set temp_message for redirect to: {path}")

    build_endpoint_training(path)
    return Redirect(f'/{path}')


@rt('/poke', methods=['POST'])
async def poke_chatbot():
    """
    Triggers the MCP proof-of-concept. The initial feedback is sent via the
    message queue, and the specific tool-use prompt is handled as a direct,
    isolated task to ensure reliability.
    """
    logger.debug('🔧 MCP external API tool call initiated via Poke button.')

    # 1. Immediately send user feedback via the message queue to ensure correct order.
    fetching_message = "🐱 Fetching a random cat fact using the MCP tool..."
    # We don't need to await this, let it process in the background.
    asyncio.create_task(pipulate.message_queue.add(pipulate, fetching_message, verbatim=True, role='system', spaces_before=1))

    # 2. Create and run the specific tool-use task in the background.
    import random
    import time as time_module
    timestamp = int(time_module.time())
    session_id = random.randint(1000, 9999)

    one_shot_mcp_prompt = f"""You are a helpful assistant with a tool that can fetch random cat facts. When the user wants a cat fact, you must use this tool.
To use the tool, you MUST stop generating conversational text and output an MCP request block.
Here is the only tool you have available:
Tool Name: `get_cat_fact`
Description: Fetches a random cat fact from an external API.
Parameters: None
---
🆔 Request ID: {session_id} | ⏰ Timestamp: {timestamp}
The user wants to learn something interesting about cats. Use the `get_cat_fact` tool by generating this EXACT MCP request block:
<mcp-request>
  <tool name="get_cat_fact" />
</mcp-request>
Do not say anything else. Just output the exact MCP block above."""

    # Send the MCP prompt directly to the LLM without adding to visible conversation
    # This bypasses the normal conversation flow to keep tool calls hidden
    async def consume_mcp_response():
        """Consume the MCP response generator without displaying it."""
        try:
            async for chunk in process_llm_interaction(MODEL, [{"role": "user", "content": one_shot_mcp_prompt}]):
                # Consume the chunks but don't display them - the tool execution handles the response
                pass
        except Exception as e:
            logger.error(f"Error in MCP tool call: {e}")

    asyncio.create_task(consume_mcp_response())

    # 3. Return an empty response to the HTMX request.
    return ""


@rt('/poke-botify', methods=['POST'])
async def poke_botify_test():
    """
    🔧 FINDER_TOKEN: BOTIFY_MCP_TEST_ENDPOINT

    🚀 Botify MCP Integration Test - Demonstrates end-to-end Botify API tool execution

    Tests the complete Botify MCP pipeline by prompting the LLM to use the 
    botify_ping tool with test credentials, showcasing authentication, error 
    handling, and full MCP transparency logging.
    """
    logger.info('🔧 BOTIFY MCP: Integration test initiated via poke-botify endpoint')

    # 1. Send immediate feedback to chat
    test_message = "🚀 Testing Botify MCP integration with botify_ping tool..."
    asyncio.create_task(pipulate.message_queue.add(pipulate, test_message, verbatim=True, role='system', spaces_before=1))

    # 2. Create Botify-specific MCP prompt
    import random
    import time as time_module
    timestamp = int(time_module.time())
    session_id = random.randint(1000, 9999)

    botify_mcp_prompt = f"""You are a helpful assistant with access to Botify API tools. When the user wants to test Botify connectivity, you must use the botify_ping tool.
To use the tool, you MUST stop generating conversational text and output an MCP request block.
Here are the available Botify tools:
Tool Name: `botify_ping`
Description: Tests Botify API connectivity and authentication
Parameters: api_token (required)
---
🆔 Request ID: {session_id} | ⏰ Timestamp: {timestamp}
The user wants to test Botify API connectivity. Use the `botify_ping` tool by generating this EXACT MCP request block:
<mcp-request>
  <tool name="botify_ping">
    <params>
    {{"api_token": "test_token_demo_123"}}
    </params>
  </tool>
</mcp-request>
Do not say anything else. Just output the exact MCP block above."""

    # 3. Execute the Botify MCP test in background
    async def consume_botify_mcp_response():
        """Consume the Botify MCP response generator without displaying it."""
        try:
            async for chunk in process_llm_interaction(MODEL, [{"role": "user", "content": botify_mcp_prompt}]):
                # Consume the chunks but don't display them - the tool execution handles the response
                pass
        except Exception as e:
            logger.error(f"Error in Botify MCP tool call: {e}")

    asyncio.create_task(consume_botify_mcp_response())

    # 4. Return empty response to HTMX request
    return ""


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


@rt('/toggle_theme', methods=['POST'])
async def toggle_theme(request):
    """Toggle between light and dark theme."""
    current_theme = db.get('theme_preference', 'auto')

    # Toggle between light and dark (we'll skip 'auto' for simplicity)
    new_theme = 'dark' if current_theme != 'dark' else 'light'
    db['theme_preference'] = new_theme

    # Create the updated switch component
    theme_is_dark = new_theme == 'dark'
    theme_switch = Div(
        Label(
            Input(
                type='checkbox',
                role='switch',
                name='theme_switch',
                checked=theme_is_dark,
                hx_post='/toggle_theme',
                hx_target='#theme-switch-container',
                hx_swap='outerHTML'
            ),
            Span('🌙 Dark Mode', cls='ml-quarter')
        ),
        Script(f"""
            // Apply theme to HTML element
            document.documentElement.setAttribute('data-theme', '{new_theme}');
            // Store in localStorage for persistence across page loads
            localStorage.setItem('theme_preference', '{new_theme}');
        """),
        id='theme-switch-container',
        cls='theme-switch-container'
    )

    return theme_switch


@rt('/sync_theme', methods=['POST'])
async def sync_theme(request):
    """Sync theme preference from client to server."""
    form = await request.form()
    theme = form.get('theme', 'auto')

    if theme in ['light', 'dark']:
        db['theme_preference'] = theme

    return HTMLResponse('OK')


@rt('/search-apps', methods=['POST'])
async def search_plugins(request):
    """Search plugins based on user input - Carson Gross style active search."""
    try:
        form = await request.form()
        search_term = form.get('search', '').strip().lower()

        # Build searchable plugin data from discovered modules
        searchable_plugins = []

        for module_name, instance in plugin_instances.items():

            # Get clean display name (remove numeric prefix, underscores, .py)
            clean_name = module_name.replace('_', ' ').title()
            display_name = getattr(instance, 'DISPLAY_NAME', clean_name)

            # Create searchable entry
            plugin_entry = {
                'module_name': module_name,
                'display_name': display_name,
                'clean_name': clean_name,
                'url': f'/redirect/{module_name}'
            }
            searchable_plugins.append(plugin_entry)

        # Filter plugins based on search term
        if search_term:
            filtered_plugins = []
            for plugin in searchable_plugins:
                # Search in display name and clean name
                if (search_term in plugin['display_name'].lower() or
                    search_term in plugin['clean_name'].lower() or
                        search_term in plugin['module_name'].lower()):
                    filtered_plugins.append(plugin)
        else:
            # Show ALL plugins on empty search (dropdown menu behavior)
            filtered_plugins = searchable_plugins

        # Generate HTML results
        if filtered_plugins:
            result_html = ""
            # Check if there's only one result for auto-selection
            auto_select_single = len(filtered_plugins) == 1

            for i, plugin in enumerate(filtered_plugins):  # Show all results - no artificial limit
                # Add auto-select class for single results
                item_class = "search-result-item"
                if auto_select_single:
                    item_class += " auto-select-single"

                # Smart mouse hover handler - don't clear selection on auto-selected single results
                if auto_select_single:
                    mouse_handler = "if (!this.classList.contains('auto-select-single') || event.movementX !== 0 || event.movementY !== 0) { this.classList.remove('selected'); }"
                else:
                    mouse_handler = "this.classList.remove('selected');"

                result_html += f"""
                <div class="{item_class}" 
                     onclick="document.getElementById('search-results-dropdown').style.display='none'; document.getElementById('nav-plugin-search').value=''; window.location.href='{plugin['url']}';"
                     onmouseover="{mouse_handler}">
                    <strong>{plugin['display_name']}</strong>
                    <div class="search-result-module">{plugin['module_name']}</div>
                </div>
                """

            # Show dropdown with JavaScript (styles now in external CSS)
            result_html += """
            <script>
                document.getElementById('search-results-dropdown').style.display = 'block';
                // Auto-select single result via server indication
                if (window.initializeSearchPluginsAutoSelect) {
                    window.initializeSearchPluginsAutoSelect();
                }
            </script>
            """
        else:
            # No results or empty search - hide dropdown
            result_html = """
            <script>
                document.getElementById('search-results-dropdown').style.display = 'none';
                // Clear any previous selection
                const dropdown = document.getElementById('search-results-dropdown');
                const current = dropdown ? dropdown.querySelector('.search-result-item.selected') : null;
                if (current) current.classList.remove('selected');
            </script>
            """

        return HTMLResponse(result_html)

    except Exception as e:
        logger.error(f"Error in search_plugins: {e}")
        return HTMLResponse(f"""
        <div class="search-error-message">
            Search error: {str(e)}
        </div>
        <script>
            document.getElementById('search-results-dropdown').style.display = 'block';
        </script>
        """)


@rt('/generate-new-key/{app_name}')
async def generate_new_key(request):
    """Generate a new auto-incremented pipeline key for the specified app."""
    app_name = request.path_params['app_name']

    # Find the plugin instance by APP_NAME attribute (not module name)
    plugin_instance = None
    for module_name, instance in plugin_instances.items():
        if hasattr(instance, 'APP_NAME') and instance.APP_NAME == app_name:
            plugin_instance = instance
            break

    if not plugin_instance:
        # Fallback: try direct module name lookup
        plugin_instance = get_workflow_instance(app_name)

    if not plugin_instance:
        return Input(
            placeholder='Error: Plugin not found',
            name='pipeline_id',
            type='search',
            cls='contrast',
            style='border-color: var(--pico-color-red-500);',
            aria_label='Pipeline ID input (error)'
        )

    # Generate new key
    full_key, prefix, _ = pipulate.generate_pipeline_key(plugin_instance)

    # Force page reload to initialize the new workflow
    # This ensures run_all_cells() is triggered and old workflow content is cleared
    from starlette.responses import Response
    response = Response('')
    response.headers['HX-Refresh'] = 'true'
    return response


@rt('/refresh-app-menu')
async def refresh_app_menu_endpoint(request):
    """Refresh the App menu dropdown via HTMX endpoint."""
    logger.debug('Refreshing App menu dropdown via HTMX endpoint /refresh-app-menu')
    menux = db.get('last_app_choice', '')
    app_menu_details_component = create_app_menu(menux)
    return HTMLResponse(to_xml(app_menu_details_component))


@rt('/save-split-sizes', methods=['POST'])
async def save_split_sizes(request):
    """Save Split.js sizes to the persistent DictLikeDB."""
    try:
        form = await request.form()
        sizes = form.get('sizes')
        if sizes:
            # Basic validation
            parsed_sizes = json.loads(sizes)
            if isinstance(parsed_sizes, list) and all(isinstance(x, (int, float)) for x in parsed_sizes):
                db['split-sizes'] = sizes
                return HTMLResponse('')
        return HTMLResponse('Invalid format or sizes not provided', status_code=400)
    except Exception as e:
        logger.error(f"Error saving split sizes: {e}")
        return HTMLResponse(f'Error: {e}', status_code=500)


@rt('/mcp-tool-executor', methods=['POST'])
async def mcp_tool_executor_endpoint(request):
    """
    Generic MCP tool executor that dispatches to registered tools.

    🔧 FINDER_TOKEN: MCP_TOOL_EXECUTOR_GENERIC_DISPATCH
    This endpoint now uses the MCP_TOOL_REGISTRY for dynamic tool dispatch.
    """
    import uuid as uuid_lib
    start_time = time.time()
    operation_id = str(uuid_lib.uuid4())[:8]

    try:
        data = await request.json()
        tool_name = data.get("tool")
        params = data.get("params", {})

        # Enhanced MCP call transparency
        logger.info(f"🔧 MCP_CALL_START: Tool '{tool_name}' | Operation ID: {operation_id}")
        logger.info(f"🔧 MCP_PARAMS: {params}")
        log.event('mcp_server', f"MCP call received for tool: '{tool_name}'", f"Params: {params}")

        # Check if tool is registered
        if tool_name not in MCP_TOOL_REGISTRY:
            available_tools = list(MCP_TOOL_REGISTRY.keys())
            logger.warning(f"🔧 MCP_ERROR: Unknown tool '{tool_name}'. Available: {available_tools}")
            return JSONResponse({
                "status": "error",
                "message": f"Tool '{tool_name}' not found. Available tools: {available_tools}"
            }, status_code=404)

        # Execute the registered tool with enhanced logging
        tool_handler = MCP_TOOL_REGISTRY[tool_name]
        logger.info(f"🔧 MCP_EXECUTE: Starting '{tool_name}' via registry handler")

        external_start_time = time.time()
        tool_result = await tool_handler(params)
        external_end_time = time.time()
        external_execution_time = (external_end_time - external_start_time) * 1000

        # Log the actual result with semantic context
        result_status = tool_result.get("status", "unknown")
        result_size = len(str(tool_result.get("result", "")))
        logger.info(f"🔧 MCP_RESULT: Tool '{tool_name}' | Status: {result_status} | Response size: {result_size} chars | Time: {external_execution_time:.1f}ms")

        # Add semantic meaning to common tool results
        if tool_name == "pipeline_state_inspector":
            pipeline_count = len(tool_result.get("result", {}).get("pipelines", []))
            logger.info(f"🔧 MCP_SEMANTIC: Pipeline inspector found {pipeline_count} active pipelines")
        elif tool_name.startswith("botify_"):
            if "projects" in str(tool_result.get("result", "")):
                logger.info(f"🔧 MCP_SEMANTIC: Botify API call returned project data")
            elif "schema" in str(tool_result.get("result", "")):
                logger.info(f"🔧 MCP_SEMANTIC: Botify API call returned schema information")
        elif tool_name.startswith("local_llm_"):
            if tool_name == "local_llm_grep_logs":
                matches = tool_result.get("result", {}).get("matches", [])
                logger.info(f"🔧 MCP_SEMANTIC: Log grep found {len(matches)} matches")
            elif tool_name == "local_llm_list_files":
                files = tool_result.get("result", {}).get("files", [])
                logger.info(f"🔧 MCP_SEMANTIC: File listing returned {len(files)} files")

        # Extract external API details from tool result for logging
        external_api_url = tool_result.get("external_api_url")
        external_api_method = tool_result.get("external_api_method", "UNKNOWN")
        external_api_status = tool_result.get("external_api_status")
        external_api_response = tool_result.get("result")

        # Log the tool execution with full transparency
        is_success_for_logging = (tool_result.get("status") == "success" or tool_result.get("success") is True)
        operation_type = "external_api_call" if is_success_for_logging else "external_api_call_failed"
        await pipulate.log_mcp_call_details(
            operation_id=f"{operation_id}-{tool_name}",
            tool_name=tool_name,
            operation_type=operation_type,
            mcp_block=None,
            request_payload=data,
            response_data=tool_result,
            response_status=200 if is_success_for_logging else 503,
            external_api_url=external_api_url,
            external_api_method=external_api_method,
            external_api_headers=None,
            external_api_payload=None,
            external_api_response=external_api_response,
            external_api_status=external_api_status,
            execution_time_ms=external_execution_time,
            notes=f"MCP tool '{tool_name}' executed via registry"
        )

        # Check for success in multiple formats
        is_success = (tool_result.get("status") == "success" or
                      tool_result.get("success") is True)

        if is_success:
            logger.info(f"🔧 MCP_SUCCESS: Tool '{tool_name}' completed successfully | Operation ID: {operation_id}")
            return JSONResponse(tool_result)
        else:
            error_msg = tool_result.get('message') or tool_result.get('error', 'Unknown error')
            logger.error(f"🔧 MCP_FAILED: Tool '{tool_name}' error: {error_msg} | Operation ID: {operation_id}")
            return JSONResponse(tool_result, status_code=503)

    except Exception as e:
        logger.error(f"🔧 MCP_EXCEPTION: Tool execution failed | Operation ID: {operation_id} | Error: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": f"Tool execution failed: {str(e)}"}, status_code=500)


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
    response = Div(pipulate.update_datalist('pipeline-ids', should_clear=True), P(f'{workflow_display_name} cleared.'), cls='clear-message')
    html_response = HTMLResponse(str(response))
    html_response.headers['HX-Refresh'] = 'true'
    return html_response


@rt('/backup-now', methods=['POST'])
async def backup_now(request):
    """Manually trigger backup of all critical databases."""
    try:
        from imports.durable_backup_system import DurableBackupManager
        backup_manager = DurableBackupManager()

        # Get dynamic database paths
        main_db_path = get_db_filename()
        keychain_db_path = 'helpers/data/ai_keychain.db'
        discussion_db_path = 'data/discussion.db'

        # Execute comprehensive backup
        logger.info("🛡️ MANUAL BACKUP INITIATED")
        backup_results = backup_manager.backup_all_databases()

        # Prepare response
        successful_backups = sum(1 for success in backup_results.values() if success)
        total_backups = len(backup_results)

        backup_location = backup_manager.backup_root

        if successful_backups == total_backups:
            message = f"✅ All {total_backups} databases backed up successfully to {backup_location}"
            logger.info(f"🛡️ MANUAL BACKUP SUCCESS: {message}")
            return {"success": True, "message": message, "backup_location": str(backup_location)}
        else:
            message = f"⚠️ Partial backup: {successful_backups}/{total_backups} databases backed up to {backup_location}"
            logger.warning(f"🛡️ MANUAL BACKUP PARTIAL: {message}")
            return {"success": False, "message": message, "backup_location": str(backup_location)}

    except Exception as e:
        error_msg = f"❌ Manual backup failed: {str(e)}"
        logger.error(f"🛡️ MANUAL BACKUP ERROR: {error_msg}")
        return {"success": False, "message": error_msg}


@rt('/clear-db', methods=['POST'])
async def clear_db(request):
    """Reset the entire database to its initial state."""
    if TABLE_LIFECYCLE_LOGGING:
        logger.bind(lifecycle=True).info('CLEAR_DB: Starting database reset...')
        slog.log_dictlike_db_to_lifecycle('db', db, title_prefix='CLEAR_DB INITIAL')
        slog.log_pipeline_summary(pipeline, title_prefix='CLEAR_DB INITIAL')
        slog.log_dynamic_table_state('profiles', lambda: profiles(), title_prefix='CLEAR_DB INITIAL')

    # Safely preserve certain values before clearing
    last_app_choice = db.get('last_app_choice')
    last_visited_url = db.get('last_visited_url')
    temp_message = db.get('temp_message')

    # 🎭 DEMO RESTART DETECTION - Check BEFORE clearing database
    demo_triggered = False
    demo_continuation_state = None
    try:
        demo_continuation_state = db.get('demo_continuation_state')
        if demo_continuation_state:
            demo_triggered = True
            logger.info(f'🎭 DEMO_RESTART: Demo continuation state detected before DB clear: {demo_continuation_state}')
            
            # 🎯 CRITICAL: Demo must ALWAYS restart in DEV mode for data safety
            current_env = get_current_environment()
            if current_env != 'Development':
                logger.info(f'🎭 DEMO_RESTART: Switching from {current_env} to Development mode for demo safety')
                set_current_environment('Development')
                logger.info('🎭 DEMO_RESTART: Environment switched to Development mode for demo')
            else:
                logger.info('🎭 DEMO_RESTART: Already in Development mode for demo')
    except Exception as e:
        logger.error(f'🎭 DEMO_RESTART: Error checking demo state before DB clear: {e}')

    # 💬 PRESERVE CONVERSATION HISTORY - Backup conversation before database reset
    conversation_backup = None
    if 'llm_conversation_history' in db:
        conversation_backup = db.get('llm_conversation_history')
        logger.info(f"💬 FINDER_TOKEN: CONVERSATION_BACKUP_DB_RESET - Backing up conversation history before database reset")
    else:
        logger.info("💬 FINDER_TOKEN: CONVERSATION_BACKUP_DB_RESET - No conversation history to backup")
    if TABLE_LIFECYCLE_LOGGING:
        logger.bind(lifecycle=True).info('CLEAR_DB: Table states BEFORE plugin table wipe:')
        try:
            # 🚨 CRITICAL FIX: Use current environment's database file for logging too
            current_db_filename_for_logging = get_db_filename()
            conn_temp = sqlite3.connect(current_db_filename_for_logging)
            conn_temp.row_factory = sqlite3.Row
            cursor_temp = conn_temp.cursor()
            cursor_temp.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('store', 'profile', 'pipeline', 'sqlite_sequence')")
            plugin_table_names_tuples = cursor_temp.fetchall()
            for table_name_tuple in plugin_table_names_tuples:
                slog.log_raw_sql_table_to_lifecycle(conn_temp, table_name_tuple[0], title_prefix='CLEAR_DB PRE-WIPE')
            conn_temp.close()
        except Exception as e_plugin_log_pre:
            logger.bind(lifecycle=True).error(f'CLEAR_DB PRE-WIPE: Error logging plugin tables via SQL: {e_plugin_log_pre}')
    # 🚨 CRITICAL FIX: Use current environment's database file, not startup-time DB_FILENAME
    current_db_filename = get_db_filename()
    current_env = get_current_environment()
    logger.info(f'🚨 CLEAR_DB: Using CURRENT database file: {current_db_filename} (current environment: {current_env})')
    
    # 🛡️ LIGHTWEIGHT SAFETY: Block clearing any database without "_dev" in filename
    if '_dev' not in current_db_filename:
        logger.error(f'🚨 SAFETY: Cannot clear database {current_db_filename} - only dev databases allowed!')
        return HTMLResponse(f'SAFETY: Cannot clear database {current_db_filename} - only databases with "_dev" in filename can be cleared!', status_code=500)
    
    # 🛡️ ADDITIONAL SAFETY: Verify environment when demo is triggered
    if demo_triggered and current_env != 'Development':
        logger.error(f'🚨 CRITICAL SAFETY ERROR: Demo triggered but still in {current_env} mode! Aborting database clear.')
        return HTMLResponse(f'SAFETY ERROR: Cannot clear database - still in {current_env} mode', status_code=500)
    
    # 🚨 ABSOLUTE HARDWIRED SAFETY: NEVER allow clearing ANY database without "_dev" in filename
    if '_dev' not in current_db_filename:
        logger.error(f'🚨 ABSOLUTE SAFETY ABORT: Database clear attempted on NON-DEV database: {current_db_filename}')
        logger.error(f'🚨 HARDWIRED PROTECTION: Only databases with "_dev" in filename can be cleared!')
        return HTMLResponse(f'ABSOLUTE SAFETY ABORT: Cannot clear database {current_db_filename} - only dev databases (_dev in filename) can be cleared!', status_code=500)
    
    # 🚨 NUCLEAR OPTION: Use hardwired safety wrapper for absolute protection
    try:
        from database_safety_wrapper import safe_sqlite_connect, SafetyViolationError
        logger.info(f'🔒 NUCLEAR SAFETY: Using hardwired safety wrapper for database operations')
        
        try:
            with safe_sqlite_connect(current_db_filename) as conn:
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
        except SafetyViolationError as safety_error:
            logger.error(f'🚨 NUCLEAR SAFETY ABORT: {safety_error}')
            return HTMLResponse(f'NUCLEAR SAFETY ABORT: {safety_error}', status_code=500)
    except Exception as e:
        logger.error(f'Error clearing core tables: {e}')
        return HTMLResponse(f'Error clearing database: {e}', status_code=500)
    logger.debug(f'CLEAR_DB: Using database file for plugin table deletion: {current_db_filename}')
    try:
        with safe_sqlite_connect(current_db_filename) as conn_delete:
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
        slog.log_dynamic_table_state('profiles', lambda: profiles(), title_prefix='CLEAR_DB POST-POPULATE')
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

    # 🎭 RESTORE DEMO STATE - Preserve demo flags after database reset for restart detection
    if demo_triggered and demo_continuation_state:
        db['demo_continuation_state'] = demo_continuation_state
        db['demo_restart_flag'] = 'true'
        logger.info('🎭 DEMO_RESTART: Demo flags preserved after database reset for restart detection')

    # 💬 RESTORE CONVERSATION HISTORY - Restore conversation after database reset
    if conversation_backup:
        db['llm_conversation_history'] = conversation_backup
        logger.info(f"💬 FINDER_TOKEN: CONVERSATION_RESTORED_DB_RESET - Restored conversation history after database reset")
        # Also restore to in-memory conversation history
        try:
            import json
            restored_messages = json.loads(conversation_backup)
            # 🚨 DANGEROUS PATTERN: Complete conversation overwrite!
            # CONTEXT: Safe here - database reset restoration (backup → memory)
            # WARNING: This clear/extend pattern historically caused conversation loss bugs
            global_conversation_history.clear()
            global_conversation_history.extend(restored_messages)
            logger.info(f"💬 FINDER_TOKEN: CONVERSATION_MEMORY_RESTORED_DB_RESET - Restored {len(restored_messages)} messages to in-memory conversation")
        except Exception as e:
            logger.error(f"💬 CONVERSATION_MEMORY_RESTORE_ERROR - Failed to restore in-memory conversation: {e}")
    else:
        logger.info("💬 FINDER_TOKEN: CONVERSATION_RESTORED_DB_RESET - No conversation history to restore")
    if TABLE_LIFECYCLE_LOGGING:
        slog.log_dictlike_db_to_lifecycle('db', db, title_prefix='CLEAR_DB FINAL (post key restoration)')
        logger.bind(lifecycle=True).info('CLEAR_DB: Operation fully complete.')

    # 🎭 DEMO RESTART LOGGING - Demo detection already completed before database clear
    if demo_triggered:
        logger.info('🎭 DEMO_RESTART: Demo-triggered restart confirmed - flags set for comeback detection')

    # Schedule server restart after database reset to ensure fresh state
    restart_message = "Restarting with fresh database..."
    restart_type = "DATABASE_RESET"
    if demo_triggered:
        restart_message = "🎭 Switching to DEV mode for demo magic... Server restart in progress!"
        restart_type = "DEMO_MAGIC"
    
    logger.info('CLEAR_DB: Scheduling server restart to ensure fresh application state')
    asyncio.create_task(delayed_restart(2))

    # Return script that triggers full-screen restart effect for the actual restart
    return HTMLResponse(f'''
        <script>
            triggerFullScreenRestart("{restart_message}", "{restart_type}");
        </script>
    ''')


@rt('/update-pipulate', methods=['POST'])
async def update_pipulate(request):
    """Update Pipulate by performing a git pull"""
    try:
        # Send immediate feedback to the user
        await pipulate.stream('🔄 Checking for Pipulate updates...', verbatim=True, role='system')

        import os
        import subprocess

        # Check if we're in a git repository
        if not os.path.exists('.git'):
            await pipulate.stream('❌ Not in a git repository. Cannot update automatically.', verbatim=True, role='system')
            return ""

        # Fetch latest changes from remote
        await pipulate.stream('📡 Fetching latest changes...', verbatim=True, role='system')
        fetch_result = subprocess.run(['git', 'fetch', 'origin', 'main'], capture_output=True, text=True)

        if fetch_result.returncode != 0:
            await pipulate.stream(f'❌ Failed to fetch updates: {fetch_result.stderr}', verbatim=True, role='system')
            return ""

        # Get current branch name and determine target branch for updates
        branch_result = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True)
        if branch_result.returncode != 0:
            await pipulate.stream('❌ Failed to determine current branch', verbatim=True, role='system')
            return ""
        
        current_branch = branch_result.stdout.strip()
        
        # For development branches, only check main branch for updates
        target_branch = 'main' if current_branch.startswith('yellowbrick') else current_branch

        # Check if there are updates available on the target branch
        local_result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True)
        remote_result = subprocess.run(['git', 'rev-parse', f'origin/{target_branch}'], capture_output=True, text=True)

        if local_result.returncode != 0 or remote_result.returncode != 0:
            await pipulate.stream('❌ Failed to check for updates', verbatim=True, role='system')
            return ""

        local_hash = local_result.stdout.strip()
        remote_hash = remote_result.stdout.strip()

        if local_hash == remote_hash:
            await pipulate.stream('✅ Already up to date!', verbatim=True, role='system')
            return ""

        # For development branches, inform user but don't auto-update
        if current_branch.startswith('yellowbrick'):
            await pipulate.stream(f'ℹ️  Updates available on {target_branch} branch.', verbatim=True, role='system')
            await pipulate.stream(f'📝 Currently on development branch: {current_branch}', verbatim=True, role='system')
            await pipulate.stream(f'💡 To update: git checkout {target_branch} && git pull origin {target_branch}', verbatim=True, role='system')
            return ""

        # 🔒 UPDATES FOUND - Trigger full-screen restart effect immediately
        # Create and schedule background update task
        async def continue_update_process():
            try:
                # Stash any local changes to prevent conflicts
                await pipulate.stream('💾 Stashing local changes...', verbatim=True, role='system')
                stash_result = subprocess.run(['git', 'stash', 'push', '--quiet', '--include-untracked', '--message', 'Auto-stash before update'],
                                              capture_output=True, text=True)

                # Perform the git pull
                await pipulate.stream('⬇️ Pulling latest changes...', verbatim=True, role='system')
                pull_result = subprocess.run(['git', 'pull', '--ff-only', 'origin', target_branch], capture_output=True, text=True)

                if pull_result.returncode != 0:
                    await pipulate.stream(f'❌ Failed to pull updates: {pull_result.stderr}', verbatim=True, role='system')
                    # Try to restore stashed changes
                    subprocess.run(['git', 'stash', 'pop', '--quiet'], capture_output=True)
                    return

                # Try to restore stashed changes
                stash_list = subprocess.run(['git', 'stash', 'list'], capture_output=True, text=True)
                if 'Auto-stash before update' in stash_list.stdout:
                    await pipulate.stream('🔄 Restoring local changes...', verbatim=True, role='system')
                    stash_apply = subprocess.run(['git', 'stash', 'apply', '--quiet'], capture_output=True, text=True)
                    if stash_apply.returncode == 0:
                        subprocess.run(['git', 'stash', 'drop', '--quiet'], capture_output=True)
                    else:
                        await pipulate.stream('⚠️ Some local changes could not be restored automatically', verbatim=True, role='system')

                await pipulate.stream('✅ Update complete! Restarting server...', verbatim=True, role='system')

                # Restart the server to apply updates
                asyncio.create_task(delayed_restart(2))

            except Exception as e:
                logger.error(f"Error in background update process: {e}")
                await pipulate.stream(f'❌ Update failed: {str(e)}', verbatim=True, role='system')

        # Start the background update process
        asyncio.create_task(continue_update_process())

        # Return immediate script response to trigger lock screen
        return HTMLResponse('''
            <script>
                triggerFullScreenRestart("Applying Pipulate updates...", "UPDATE_APPLYING");
            </script>
        ''')

    except Exception as e:
        logger.error(f"Error updating Pipulate: {e}")
        await pipulate.stream(f'❌ Update failed: {str(e)}', verbatim=True, role='system')
        return ""


@rt('/reset-python-env', methods=['POST'])
async def reset_python_env(request):
    """Reset the Python virtual environment by removing .venv directory."""
    current_env = get_current_environment()

    if current_env != 'Development':
        await pipulate.stream('❌ Python environment reset is only allowed in Development mode for safety.',
                              verbatim=True, role='system')
        return ""

    try:
        import os
        import shutil

        # Check if another critical operation is in progress
        if is_critical_operation_in_progress():
            await pipulate.stream("⚠️ Another critical operation is in progress. Please wait and try again.",
                                  verbatim=True, role='system')
            return ""

        # Set flag to prevent watchdog restarts during operation
        logger.info("[RESET_PYTHON_ENV] Starting critical operation. Pausing Watchdog restarts.")
        set_critical_operation_flag()

        try:
            # Send immediate feedback to the user
            await pipulate.stream('🐍 Resetting Python environment...', verbatim=True, role='system')

            # Check if .venv exists
            if os.path.exists('.venv'):
                await pipulate.stream('🗑️ Removing .venv directory...', verbatim=True, role='system')
                shutil.rmtree('.venv')
                await pipulate.stream('✅ Python environment reset complete.', verbatim=True, role='system')
                await pipulate.stream('', verbatim=True, role='system')  # Empty line for spacing
                await pipulate.stream('📝 **Next Steps Required:**', verbatim=True, role='system')
                await pipulate.stream('   1. Type `exit` to leave the current nix shell', verbatim=True, role='system')
                await pipulate.stream('   2. Type `nix develop` to rebuild the environment', verbatim=True, role='system')
                await pipulate.stream('   3. The fresh environment build will take 2-3 minutes', verbatim=True, role='system')
                await pipulate.stream('', verbatim=True, role='system')  # Empty line for spacing
                await pipulate.stream('🚪 Server will exit in 3 seconds...', verbatim=True, role='system')

                # Log the reset operation for debugging
                logger.info("🐍 FINDER_TOKEN: PYTHON_ENV_RESET - User triggered Python environment reset")

            else:
                await pipulate.stream('ℹ️ No .venv directory found to reset.', verbatim=True, role='system')

        finally:
            # Always reset the flag, even if operation fails
            logger.info("[RESET_PYTHON_ENV] Critical operation finished. Resuming Watchdog restarts.")
            clear_critical_operation_flag()

            # For Python environment reset, we need a clean exit to let Nix recreate the environment
            logger.info("[RESET_PYTHON_ENV] Forcing clean server exit. Nix watchdog will restart with fresh Python environment.")

            # Schedule clean exit after giving user time to read instructions
            import asyncio

            async def clean_exit():
                await asyncio.sleep(3.0)  # Give user time to read the manual restart instructions
                logger.info("[RESET_PYTHON_ENV] Exiting cleanly. User must manually restart with 'exit' then 'nix develop'.")
                import os
                os._exit(0)  # Clean exit - user must manually restart

            asyncio.create_task(clean_exit())

        # Return HTML response that triggers the special Python environment reset screen
        from starlette.responses import HTMLResponse
        return HTMLResponse("""
        <script>
            // Trigger the Python environment reset overlay
            if (typeof triggerPythonEnvironmentReset === 'function') {
                triggerPythonEnvironmentReset();
            } else {
                console.error('triggerPythonEnvironmentReset function not found');
            }
        </script>
        """)

    except Exception as e:
        logger.error(f"Error resetting Python environment: {e}")
        error_msg = f'❌ Error resetting Python environment: {str(e)}'
        await pipulate.stream(error_msg, verbatim=True, role='system')
        # Reset flag on error
        clear_critical_operation_flag()
        return ""


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


@rt('/store-demo-continuation', methods=['POST'])
async def store_demo_continuation(request):
    """Store demo continuation state before server restart"""
    try:
        form_data = await request.form()
        demo_continuation = form_data.get('demo_continuation')
        
        if demo_continuation:
            # Parse the JSON state
            continuation_state = json.loads(demo_continuation)
            
            # Store to file for persistence across server restarts
            success = store_demo_state(continuation_state)
            
            if success:
                logger.info(f"🎭 Demo continuation state stored to file: {continuation_state}")
                return JSONResponse({"success": True, "message": "Demo continuation state stored"})
            else:
                logger.error("🎭 Failed to store demo continuation state to file")
                return JSONResponse({"success": False, "message": "Failed to store demo state"}, status_code=500)
        else:
            logger.error("🎭 No demo continuation data provided")
            return JSONResponse({"success": False, "message": "No demo continuation data provided"}, status_code=400)
            
    except Exception as e:
        logger.error(f"🎭 Error storing demo continuation state: {e}")
        return JSONResponse({"success": False, "message": f"Error: {str(e)}"}, status_code=500)


@rt('/check-demo-resume', methods=['GET'])
async def check_demo_resume(request):
    """Check if demo should resume after server restart"""
    try:
        # Check file-based demo state
        demo_state = get_demo_state()
        
        if demo_state:
            logger.info(f"🎭 Demo resume requested with state: {demo_state}")
            # Don't clear the state here - let the comeback flow handle it
            return JSONResponse({
                "should_resume": True,
                "continuation_state": demo_state
            })
        else:
            return JSONResponse({"should_resume": False})
            
    except Exception as e:
        logger.error(f"🎭 Error checking demo resume: {e}")
        return JSONResponse({"should_resume": False, "error": str(e)}, status_code=500)


@rt('/check-demo-comeback', methods=['GET'])
async def check_demo_comeback(request):
    """Check if we're coming back from a demo-triggered restart and return demo state for continuation."""
    try:
        # First check database for demo comeback state (set during startup)
        demo_comeback_state = db.get('demo_comeback_state')
        logger.info(f"🎭 DEBUG: /check-demo-comeback called, demo_comeback_state in db: {demo_comeback_state}")
        
        if demo_comeback_state:
            # Clear the state after reading it (single use)
            del db['demo_comeback_state']
            logger.info(f"🎭 Demo comeback detected from database with state: {demo_comeback_state}")
            
            # Parse JSON string if needed
            if isinstance(demo_comeback_state, str):
                try:
                    demo_comeback_state = json.loads(demo_comeback_state)
                    logger.info(f"🎭 DEBUG: Parsed JSON demo state: {demo_comeback_state}")
                except json.JSONDecodeError:
                    logger.error(f"🎭 Failed to parse demo comeback state JSON: {demo_comeback_state}")
            
            response_data = {
                "show_comeback_message": True,
                "demo_state": demo_comeback_state,
                "message": "🎭 Demo server restart complete! Ready for the next trick...",
                "subtitle": "Press Ctrl+Alt+Y to continue or Ctrl+Alt+N to stop"
            }
            logger.info(f"🎭 DEBUG: Returning comeback response: {response_data}")
            return JSONResponse(response_data)
        
        # Fallback: Check file directly (in case startup detection didn't run)
        demo_state = get_demo_state()
        if demo_state:
            logger.info(f"🎭 Demo comeback detected from file with state: {demo_state}")
            # Clear the file since we're processing it
            clear_demo_state()
            
            return JSONResponse({
                "show_comeback_message": True,
                "demo_state": demo_state,
                "message": "🎭 Demo server restart complete! Ready for the next trick...",
                "subtitle": "Press Ctrl+Alt+Y to continue or Ctrl+Alt+N to stop"
            })
        
        return JSONResponse({
            "show_comeback_message": False,
            "message": None,
            "subtitle": None
        })
    except Exception as e:
        logger.error(f"🎭 Error checking demo comeback state: {e}")
        return JSONResponse({
            "show_comeback_message": False,
            "message": None,
            "subtitle": None,
            "error": str(e)
        })


@rt('/assets/tests/demo.json', methods=['GET'])
async def serve_demo_script_config(request):
    """Serve the demo script configuration file with dynamic Ollama messages"""
    try:
        demo_config_path = Path('assets/tests/demo.json')
        if demo_config_path.exists():
            with open(demo_config_path, 'r') as f:
                config_data = json.load(f)

            # Check Ollama availability for dynamic messages
            from imports.crud import check_ollama_availability
            ollama_available = await check_ollama_availability()

            # Process dynamic messages in the config
            def process_dynamic_messages(obj):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if isinstance(value, str):
                            # First pass: Replace {app_name} placeholder with actual app name
                            if "{app_name}" in value:
                                obj[key] = value.replace("{app_name}", APP_NAME)
                                value = obj[key]  # Update value for potential dynamic message processing
                            
                            # Second pass: Replace dynamic ollama messages
                            if value == "{dynamic_ollama_message}" and "ollama_messages" in obj:
                                obj[key] = obj["ollama_messages"]["available"] if ollama_available else obj["ollama_messages"]["not_available"]
                            elif value == "{dynamic_ollama_decline_message}" and "ollama_messages" in obj:
                                obj[key] = obj["ollama_messages"]["available"] if ollama_available else obj["ollama_messages"]["not_available"]
                        elif isinstance(value, (dict, list)):
                            process_dynamic_messages(value)
                elif isinstance(obj, list):
                    for item in obj:
                        process_dynamic_messages(item)

            # Apply dynamic message processing
            process_dynamic_messages(config_data)
            
            # Second pass: ensure all dynamic replacements are fully processed
            process_dynamic_messages(config_data)

            return JSONResponse(config_data)
        else:
            logger.error('🎯 Demo script config file not found')
            return JSONResponse({'error': 'Demo script config file not found'}, status_code=404)
    except Exception as e:
        logger.error(f'🎯 Error serving demo script config: {str(e)}')
        return JSONResponse({'error': 'Failed to load demo script config'}, status_code=500)


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
        logger.error(f'[📥 DOWNLOAD] Traceback: {traceback.format_exc()}')
        return HTMLResponse(f'Error serving file: {str(e)}', status_code=500)


class DOMSkeletonMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):
        endpoint = request.url.path
        method = request.method
        is_static = endpoint.startswith('/assets/')
        is_ws = endpoint == '/ws'
        is_sse = endpoint == '/sse'

        # Enhanced labeling for network requests with correlation tracking
        if not (is_static or is_ws or is_sse):
            # Generate correlation ID for tracking requests through the system
            import uuid
            correlation_id = str(uuid.uuid4())[:8]

            # Add context about the request source
            user_agent = request.headers.get('user-agent', '')
            referer = request.headers.get('referer', '')
            request_context = ""

            # Identify common request sources
            if endpoint == '/':
                if 'curl' in user_agent.lower():
                    request_context = " (curl health check)"
                elif 'python' in user_agent.lower() or 'httpx' in user_agent.lower():
                    request_context = " (Python client)"
                elif 'chrome' in user_agent.lower() or 'firefox' in user_agent.lower() or 'safari' in user_agent.lower():
                    # Check for startup-related browser requests
                    accept_header = request.headers.get('accept', '')
                    connection_header = request.headers.get('connection', '')

                    if 'text/html' in accept_header and not referer:
                        request_context = " (browser startup/auto-open)"
                    elif referer and 'localhost' in referer:
                        request_context = " (live-reload check)"
                    elif 'keep-alive' in connection_header:
                        request_context = " (browser reload)"
                    else:
                        request_context = " (browser request)"
                elif not user_agent:
                    request_context = " (unknown client)"
                else:
                    request_context = f" (client: {user_agent[:30]}...)" if len(user_agent) > 30 else f" (client: {user_agent})"
            elif endpoint.startswith('/redirect/'):
                request_context = " (HTMX navigation)"
            elif endpoint.startswith('/poke'):
                request_context = " (chat interaction)"
            elif endpoint in ['/toggle_theme', '/toggle_profile_lock', '/sync_theme']:
                request_context = " (UI setting)"
            elif endpoint.startswith('/mcp-'):
                request_context = " (MCP tool)"
            elif endpoint.startswith('/clear-'):
                request_context = " (reset operation)"
            elif 'submit' in endpoint or 'complete' in endpoint:
                request_context = " (workflow step)"

            log.event('network', f'{method} {endpoint}{request_context} | ID: {correlation_id}')
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
            slog.print_and_log_table(cookie_table, "STATE TABLES - ")
            pipeline_table = Table(title='➡️ Pipeline States')
            pipeline_table.add_column('Key', style='yellow')
            pipeline_table.add_column('Created', style='magenta')
            pipeline_table.add_column('Updated', style='cyan')
            pipeline_table.add_column('Steps', style='white')
            for record in pipeline():
                try:
                    state = json.loads(record.data)
                    pre_state = json.loads(record.data)
                    pipeline_table.add_row(record.pkey, str(state.get('created', '')), str(state.get('updated', '')), str(len(pre_state) - 2))
                except (json.JSONDecodeError, AttributeError) as e:
                    log.error(f'Error parsing pipeline state for {record.pkey}', e)
                    pipeline_table.add_row(record.pkey, 'ERROR', 'Invalid State')
            slog.print_and_log_table(pipeline_table, "STATE TABLES - ")
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
    slog.print_and_log_table(table, "ROUTES - ")


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
        previous_env = get_current_environment()

        # 💬 DISABLED: Conversation save before environment switch (prevents SQLite locking)
        # The save_conversation_to_db() call creates concurrent SQLite connections that corrupt database writes
        logger.info(f"💬 FINDER_TOKEN: CONVERSATION_SAVE_ENV_SWITCH - Conversation save disabled to prevent database locking during environment switch from {previous_env} to {environment}")
        # save_conversation_to_db()  # ← DISABLED: Causes SQLite locking conflicts with main database

        set_current_environment(environment)
        logger.info(f'💬 FINDER_TOKEN: ENVIRONMENT_SWITCHED - Environment switched from {previous_env} to {environment}')

        # Schedule server restart after a delay to allow HTMX to swap in the spinner
        asyncio.create_task(delayed_restart(2))

        # Return script that triggers full-screen restart effect
        return HTMLResponse(f"""
            <script>
                triggerFullScreenRestart("Switching to {environment} mode...", "ENVIRONMENT_SWITCH");
            </script>
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
        # 🍎 MAC SAFE: Set critical operation flag to prevent watchdog interference during restart
        set_critical_operation_flag()
        logger.info('🍎 MAC RESTART: Critical operation flag set to prevent watchdog interference')
        restart_server(force_restart=True)
    except Exception as e:
        logger.error(f'Error during restart: {e}')
        # 🍎 MAC SAFE: Clear critical operation flag on error
        clear_critical_operation_flag()
        logger.info('🍎 MAC RESTART: Critical operation flag cleared after restart error')


async def send_delayed_endpoint_message(message, session_key):
    """Send an endpoint message after a delay to ensure chat system is ready."""
    await asyncio.sleep(2)  # Brief delay to ensure page has loaded

    # Create message ID for final coordination check
    current_env = get_current_environment()
    endpoint = session_key.replace(f'endpoint_message_sent_', '').replace(f'_{current_env}', '')
    message_id = f'{endpoint}_{current_env}_{hash(message) % 10000}'

    try:
        # Final check - only send if still not recently sent by another pathway
        current_time = time.time()
        last_sent = message_coordination['last_endpoint_message_time'].get(message_id, 0)

        if current_time - last_sent > 5:  # 5-second window for delayed messages
            await pipulate.message_queue.add(pipulate, message, verbatim=True, role='system', spaces_after=1)
            db[session_key] = 'sent'  # Mark as sent for this session

            # Update coordination system
            message_coordination['last_endpoint_message_time'][message_id] = current_time
            logger.debug(f"Successfully sent delayed endpoint message: {message_id}")
        else:
            logger.debug(f"Skipping delayed endpoint message - recently sent by another pathway: {message_id}")
            # Still mark session as sent to prevent future attempts
            db[session_key] = 'sent'
    except Exception as e:
        logger.warning(f"Failed to send delayed endpoint message for {session_key}: {e}")


async def send_startup_environment_message():
    """Send a message indicating the current environment mode after server startup."""
    # Set startup coordination flag
    message_coordination['startup_in_progress'] = True

    # Longer wait for fresh nix develop startup to ensure chat system is fully ready
    await asyncio.sleep(3)  # Reduced from 5 to 3 seconds for faster startup

    try:
        current_env = get_current_environment()
        env_display = 'DEV' if current_env == 'Development' else 'Prod'

        # 🎭 DEMO COMEBACK INTEGRATION - Check for demo comeback message
        demo_comeback_message = None
        demo_comeback_detected = False
        try:
            if db.get('demo_comeback_message') == 'true':
                demo_comeback_detected = True
                # Clear the flag immediately (flipflop behavior)
                del db['demo_comeback_message']
                logger.info("🎭 FINDER_TOKEN: DEMO_COMEBACK_DISPLAYED - Demo comeback message will be handled by JavaScript, flag cleared")
                
                # DO NOT create system message - let JavaScript handle the demo continuation
                demo_comeback_message = None
                logger.info("🎭 DEMO_COMEBACK: Skipping system message - JavaScript will handle continuation")
        except Exception as e:
            logger.error(f"🎭 DEMO_COMEBACK_ERROR - Failed to check demo comeback state: {e}")

        # Choose the appropriate startup message
        if demo_comeback_detected and demo_comeback_message:
            env_message = demo_comeback_message
            logger.info("🎭 DEMO_COMEBACK: Using special demo comeback message as startup message")
        elif current_env == 'Development':
            env_message = f"🚀 Server started in {env_display} mode. Ready for experimentation and testing!"
        else:
            env_message = f"🚀 Server started in {env_display} mode. Ready for production use."

        # Ensure message queue is ready with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await pipulate.message_queue.add(pipulate, env_message, verbatim=True, role='system', spaces_after=2)
                logger.debug(f"Successfully sent startup environment message (attempt {attempt + 1})")
                break
            except Exception as e:
                logger.warning(f"Failed to send startup environment message (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # Wait before retry
                else:
                    raise

        # Clear any existing endpoint message session keys to allow fresh messages after server restart
        endpoint_keys_to_clear = [key for key in db.keys() if key.startswith('endpoint_message_sent_')]
        for key in endpoint_keys_to_clear:
            del db[key]
        logger.debug(f"Cleared {len(endpoint_keys_to_clear)} endpoint message session keys on startup")

        # Clear message coordination on startup to allow fresh messages
        message_coordination['endpoint_messages_sent'].clear()
        message_coordination['last_endpoint_message_time'].clear()

        # Also send endpoint message and training for current location
        # 🔧 BUG FIX: Simplified and robust endpoint detection
        current_endpoint = db.get('last_app_choice', '')
        visited_url = db.get('last_visited_url', '')

        logger.info(f"🔧 STARTUP_DEBUG: Initial last_app_choice='{current_endpoint}', last_visited_url='{visited_url}'")

        # 🔧 ROBUST FIX: Use visited_url as the primary source of truth for current location
        if visited_url:
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(visited_url)
                path = parsed_url.path.strip('/')

                # Normalize the path to get the current endpoint
                current_endpoint = normalize_menu_path(path) if path else ''
                logger.info(f"🔧 STARTUP_DEBUG: URL endpoint resolved: {visited_url} -> '{current_endpoint}'")

                # 🔧 EXPLICIT HOMEPAGE DETECTION: If path is empty or '/', we're on homepage
                if not path or path == '':
                    current_endpoint = ''
                    logger.info(f"🔧 STARTUP_DEBUG: Detected homepage from URL: {visited_url}")

            except Exception as e:
                logger.info(f"🔧 STARTUP_DEBUG: Could not parse last_visited_url: {e}")

        # 🔧 FALLBACK: If no URL or URL parsing failed, check last_app_choice but treat '' as homepage
        if not visited_url:
            # Use last_app_choice as fallback, but ensure '' is treated as homepage
            current_endpoint = current_endpoint if current_endpoint else ''
            logger.info(f"🔧 STARTUP_DEBUG: Using last_app_choice fallback: '{current_endpoint}'")

        logger.info(f"🔧 STARTUP_DEBUG: Final current_endpoint='{current_endpoint}' (empty string = homepage)")
        logger.info(f"🔧 STARTUP_DEBUG: Available plugin_instances: {list(plugin_instances.keys())}")

        # Add training prompt to conversation history
        build_endpoint_training(current_endpoint)

        # Send endpoint message if available (with coordination check)
        # 🔧 BUG FIX: Send appropriate endpoint message for both homepage and other endpoints
        has_temp_message = 'temp_message' in db
        # 🔧 HOMEPAGE FIX: Empty string (homepage) is also valid and should get the Roles message
        is_valid_endpoint = True  # Both homepage ('') and other endpoints are valid
        
        # 🎭 DEMO COMEBACK CHECK - Skip regular endpoint message during demo comeback
        demo_comeback_in_progress = demo_comeback_detected if 'demo_comeback_detected' in locals() else False
        
        # 🎭 DEMO COMEBACK PRIORITY - Clear temp messages during demo comeback to prevent conflicts
        if demo_comeback_in_progress and has_temp_message:
            logger.info(f"🎭 STARTUP_DEBUG: Demo comeback in progress - clearing conflicting temp message")
            has_temp_message = False  # Clear temp message to prioritize demo comeback
        
        logger.info(f"🔧 STARTUP_DEBUG: has_temp_message={has_temp_message}, is_valid_endpoint={is_valid_endpoint}, demo_comeback_in_progress={demo_comeback_in_progress}, current_endpoint_repr={repr(current_endpoint)}")

        if not has_temp_message and is_valid_endpoint and not demo_comeback_in_progress:
            endpoint_message = build_endpoint_messages(current_endpoint)
            logger.info(f"🔧 STARTUP_DEBUG: Endpoint message for '{current_endpoint}': {endpoint_message[:100] if endpoint_message else 'None'}...")
            if endpoint_message:
                # Create unique message identifier for coordination
                message_id = f'{current_endpoint}_{current_env}_{hash(endpoint_message) % 10000}'

                # Check if this message was recently sent through any pathway
                current_time = time.time()
                last_sent = message_coordination['last_endpoint_message_time'].get(message_id, 0)

                # Only send if not recently sent (10-second window)
                if current_time - last_sent > 10:
                    await asyncio.sleep(1)  # Brief pause between messages

                    try:
                        # 🔧 STARTUP_DEBUG: Mark this message as coming from startup
                        startup_marked_message = f"🔧 [STARTUP] {endpoint_message}"
                        await pipulate.message_queue.add(pipulate, startup_marked_message, verbatim=True, role='system', spaces_after=2)
                        logger.info(f"🔧 STARTUP_DEBUG: Successfully sent startup endpoint message: {message_id}")

                        aa.reading_legend()
                        aa.system_diagram()
                        aa.white_rabbit()

                        # Mark as sent in coordination system
                        message_coordination['last_endpoint_message_time'][message_id] = current_time
                        message_coordination['endpoint_messages_sent'].add(message_id)

                        # Also mark in session system for backward compatibility
                        session_key = f'endpoint_message_sent_{current_endpoint}_{current_env}'
                        db[session_key] = 'sent'
                    except Exception as e:
                        logger.warning(f"🔧 STARTUP_DEBUG: Failed to send startup endpoint message: {e}")
                else:
                    logger.info(f"🔧 STARTUP_DEBUG: Skipping startup endpoint message - recently sent: {message_id}")
        elif has_temp_message:
            logger.info(f"🔧 STARTUP_DEBUG: Using existing temp_message instead of generating new endpoint message for '{current_endpoint}'")
        elif demo_comeback_in_progress:
            logger.info(f"🎭 STARTUP_DEBUG: Skipping regular endpoint message during demo comeback - demo message was already sent")
        else:
            logger.info(f"🔧 STARTUP_DEBUG: Skipping endpoint message - this should not happen with current logic")

    except Exception as e:
        logger.error(f'Error sending startup environment message: {e}')
    finally:
        # Clear startup flag
        message_coordination['startup_in_progress'] = False


async def prepare_local_llm_context():
    """Pre-seed context for local LLMs with essential system information.

    This function creates a digestible context package for local LLMs to provide
    immediate capability awareness without overwhelming their smaller context windows.
    Unlike advanced AIs who can explore the system, local LLMs need pre-computed context.
    """
    await asyncio.sleep(10)  # Let startup and cache warmup complete first (fully staggered)

    try:
        # Build essential context summary for local LLMs
        context_summary = {
            "system_overview": {
                "name": "Pipulate - Local-First Web Framework",
                "architecture": "FastHTML + HTMX + SQLite + MCP Tools",
                "philosophy": "Radical Transparency for AI Development",
                "local_llm_role": "Guided Assistant with MCP Tool Access"
            },
            "available_mcp_tools": {
                "file_access": ["local_llm_read_file", "local_llm_list_files"],
                "log_search": ["local_llm_grep_logs"],
                "state_inspection": ["pipeline_state_inspector"],
                "botify_api": ["botify_get_full_schema", "botify_list_available_analyses", "botify_execute_custom_bql_query"]
            },
            "key_directories": {
                "training": "AI training materials and guides",
                "apps": "Workflow applications and business logic",
                "helpers": "Utility scripts and API integrations",
                "logs": "Server logs with FINDER_TOKEN patterns"
            },
            "botify_capabilities": {
                "demo_projects": ["uhnd.com-demo-account", "mikelev.in"],
                "key_features": ["GA4/Adobe Analytics integration", "Traffic source attribution", "Custom BQL queries"],
                "field_count": "4,449+ fields available via schema discovery"
            },
            "transparency_patterns": {
                "log_tokens": "Search logs with FINDER_TOKEN patterns",
                "mcp_execution": "All tool calls logged with full transparency",
                "state_tracking": "Application state stored in DictLikeDB"
            }
        }

        # Store context for local LLM access
        import json
        context_file = Path('data/local_llm_context.json')
        context_file.parent.mkdir(exist_ok=True)

        with open(context_file, 'w') as f:
            json.dump(context_summary, f, indent=2)

        logger.info(f"LOCAL LLM CONTEXT: Pre-seeded context package ready at {context_file}")
        aa.server_whisper("Local LLM context prepared - the AI assistant is ready for collaboration", "🤖")

        # Add context message silently to conversation history for local LLM
        try:
            context_msg = """🤖 Local LLM Context Initialized

Your MCP tools are now available:
• local_llm_get_context - Get system overview
• local_llm_read_file - Read training materials and code  
• local_llm_list_files - Explore safe directories
• local_llm_grep_logs - Search server logs for patterns
• pipeline_state_inspector - Check application state
• Botify API tools - Full schema access with 4,449+ fields

Use these tools to assist users within your guided capabilities. Remember that advanced AI exploration (file system access, complex debugging) is handled by Claude/GPT in Cursor/Windsurf/VSCode when needed."""

            # Add to conversation history silently (not to visible chat)
            append_to_conversation(context_msg, role='system')

        except Exception as msg_error:
            logger.debug(f"Could not add local LLM context to conversation: {msg_error}")

    except Exception as e:
        logger.error(f"Error preparing local LLM context: {e}")
        # Don't fail startup if context preparation fails

ALL_ROUTES = list(set([''] + MENU_ITEMS))
for route in ALL_ROUTES:
    route_path = f'/{route}' if route else '/'

    @app.route(route_path)
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
        logger.error(f'🚨 FINDER_TOKEN: SYNTAX_ERROR - Syntax error in {filename}:')
        logger.error(f'  Line {e.lineno}: {e.text}')
        logger.error(f"  {' ' * (e.offset - 1)}^")
        logger.error(f'Error: {e}')
        return False


def check_server_already_running():
    """Check if server is already running on port 5001 and provide helpful guidance."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 5001))
        sock.close()

        if result == 0:  # Port is in use
            slog.safe_print()
            slog.console.print("🚨 [bold red]SERVER ALREADY RUNNING[/bold red]")
            slog.safe_print()
            slog.console.print("✅ [bold green]AI ASSISTANT SUMMARY:[/bold green]")
            slog.console.print("   The Pipulate server is ALREADY RUNNING with watchdog auto-restart enabled.")
            slog.console.print("   There is NO NEED to manually start the server.")
            slog.safe_print()
            slog.console.print("🎯 [bold yellow]KEY INSIGHTS:[/bold yellow]")
            slog.console.print("   • Server running at: [bold cyan]http://localhost:5001[/bold cyan]")
            slog.console.print("   • Watchdog auto-restarts on ANY .py file changes")
            slog.console.print("   • Force restart if needed: [bold white]touch server.py[/bold white]")
            slog.console.print("   • Check logs: [bold white]cat logs/server.log[/bold white]")
            slog.safe_print()
            slog.console.print("🤖 [bold magenta]EXPECTED AI RESPONSE:[/bold magenta]")
            slog.console.print('   "I attempted to start the server with `python server.py` but it informed me')
            slog.console.print('    another instance is already running with watchdog auto-restart enabled.')
            slog.console.print('    No manual restart needed. Server available at http://localhost:5001.')
            slog.console.print('    Use `touch server.py` to trigger restart if testing changes."')
            slog.safe_print()
            slog.console.print("🎣 [bold cyan]TEACH YOURSELF TO FISH - RADICAL TRANSPARENCY SYSTEM:[/bold cyan]")
            slog.console.print("   You just discovered Pipulate's Radical Transparency & Agentic AI system!")
            slog.console.print("   🔥 [bold yellow]Master Guide:[/bold yellow] .cursor/rules/00_PIPULATE_MASTER_GUIDE.mdc")
            slog.console.print("   🎯 [bold yellow]Key capabilities you now have:[/bold yellow]")
            slog.console.print("      • MCP Tools for system inspection and automation")
            slog.console.print("      • FINDER_TOKENs for surgical log analysis")
            slog.console.print("      • Pipeline state inspection for workflow debugging")
            slog.console.print("      • Browser automation with complete DOM transparency")
            slog.console.print("   💡 [bold green]Next level:[/bold green] Read the guide to unlock your full agentic potential!")
            slog.safe_print()

            return True
    except Exception:
        pass  # Server not running or other error

    return False


def create_restart_response():
    """Create HTML for restart notification with Pico CSS aria-busy spinner."""
    return f'<span aria-busy="true">{message}</span>'


def restart_server(force_restart=False):
    if not force_restart and (shared_app_state['critical_operation_in_progress'] or is_critical_operation_in_progress()):
        log.warning('Restart requested but critical operation in progress. Deferring restart.')
        return
    if not check_syntax(Path(__file__)):
        log.warning('Syntax error detected', 'Fix the error and save the file again')
        return

    # 🔧 PRESERVE ENDPOINT CONTEXT: Store current endpoint message in temp_message for restart preservation
    try:
        current_endpoint = db.get('last_app_choice', '')
        visited_url = db.get('last_visited_url', '')

        # Extract endpoint from URL if available (same logic as startup function)
        if visited_url:
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(visited_url)
                path = parsed_url.path.strip('/')
                if path:  # Use URL path as the canonical endpoint
                    current_endpoint = normalize_menu_path(path)
                    logger.info(f"🔧 WATCHDOG_CONTEXT_PRESERVATION: Using URL endpoint: {visited_url} -> {current_endpoint}")
                else:
                    # Empty path means homepage/roles - set explicitly
                    current_endpoint = ''
                    logger.info(f"🔧 WATCHDOG_CONTEXT_PRESERVATION: Empty URL path detected - using homepage: {visited_url} -> ''")
            except Exception as e:
                logger.info(f"🔧 WATCHDOG_CONTEXT_PRESERVATION: Could not parse URL: {e}")

        # 🔧 BUG FIX: Only preserve endpoint context for non-homepage endpoints
        # Homepage should always regenerate its message on startup, not preserve old workflow messages
        if current_endpoint and current_endpoint != '':
            endpoint_message = build_endpoint_messages(current_endpoint)
            if endpoint_message:
                db['temp_message'] = endpoint_message
                logger.info(f"🔧 WATCHDOG_CONTEXT_PRESERVATION: Stored endpoint message for '{current_endpoint}' in temp_message")
            else:
                logger.info(f"🔧 WATCHDOG_CONTEXT_PRESERVATION: No endpoint message found for '{current_endpoint}'")
        else:
            # 🔧 BUG FIX: For homepage (empty endpoint), explicitly clear temp_message
            # This ensures the startup sequence will generate the correct Roles message
            if 'temp_message' in db:
                del db['temp_message']
                logger.info(f"🔧 WATCHDOG_CONTEXT_PRESERVATION: Cleared temp_message for homepage to ensure correct Roles message on restart")
            else:
                logger.info(f"🔧 WATCHDOG_CONTEXT_PRESERVATION: Homepage endpoint '{current_endpoint}', no temp_message to clear")

    except Exception as e:
        logger.warning(f"🔧 WATCHDOG_CONTEXT_PRESERVATION: Could not preserve endpoint context: {e}")

    # 🔄 BROADCAST RESTART NOTIFICATION: Send SSE message to all connected clients
    try:
        import asyncio

        # Create a restart notification HTML
        restart_html = create_restart_response("WATCHDOG_RESTART", "File changed, restarting server...")

        # Get the event loop reference from the SSE broadcaster
        if hasattr(broadcaster, 'event_loop') and broadcaster.event_loop and not broadcaster.event_loop.is_closed():
            # Schedule the coroutine in the main event loop from the watchdog thread
            try:
                future = asyncio.run_coroutine_threadsafe(
                    broadcaster.send(f'restart_notification:{restart_html}'),
                    broadcaster.event_loop
                )
                # Wait briefly for the message to be sent
                future.result(timeout=0.5)  # Reduced timeout for faster restart
                logger.info('🔄 FINDER_TOKEN: RESTART_NOTIFICATION_SENT - Broadcasted restart spinner to all clients')
            except Exception as e:
                logger.warning(f'Could not send restart notification via SSE broadcaster loop: {e}')
        else:
            logger.warning('SSE broadcaster event loop not available, skipping restart notification')

    except Exception as e:
        logger.warning(f'Could not broadcast restart notification: {e}')

    # Reduced delay for faster restart with typing speed compensation
    time.sleep(0.5)

    max_retries = 3
    for attempt in range(max_retries):
        try:

            # 🐰 ALICE WELCOME BANNER - Perfect transition point: FINDER_TOKENs end, ROLES begin
            if __name__ == '__main__':
                logger.info('🐰 FINDER_TOKEN: ALICE_MODE - Displaying Alice banner at perfect transition point')
                logger.info("🔧 ALICE_MARKER: __name__ = {__name__} Displaying falling_alice banner")
                aa.falling_alice()
            else:
                logger.info("🔧 ALICE_MARKER_X: Alice banner conditions not met - skipped")

            # 🍎 MAC SAFE: Show restart banner with fallback for Mac I/O constraints
            try:
                aa.figlet_banner("RESTART", "Pipulate server reloading...", font='slant', color=BANNER_COLORS['server_restart'])
            except (BlockingIOError, OSError, IOError) as e:
                # 🍎 MAC FALLBACK: If Rich banner fails during restart, use simple print
                print("🔄 RESTART: Pipulate server reloading...")
                logger.info(f"🍎 MAC RESTART: Rich banner failed during restart (Error: {e}), using simple output")
            except Exception as e:
                # Any other error, just log and continue with restart
                logger.warning(f"🔄 RESTART: Banner display failed (Error: {e}), continuing restart...")
            
            log.startup(f'Restarting server (attempt {attempt + 1}/{max_retries})')
            # 🤖 AI ASSISTANT EDUCATION: Explain rapid restart behavior
            # Console users see clean UX with banners shown once per session")
            # AI assistants see ALL restart events in logs for complete transparency")
            # Each restart below will trigger aa.figlet_banner() with ASCII art logging")
            logger.warning("🤖 AI_RAPID_RESTART: This is a watchdog-triggered restart - one of potentially multiple rapid restarts")

            # Set environment variable to indicate this is a watchdog restart
            os.environ['PIPULATE_WATCHDOG_RESTART'] = '1'
            
            # 🍎 MAC SAFE: Additional protection against console blocking during restart
            try:
                # Flush and close stdout/stderr to prevent blocking during os.execv
                sys.stdout.flush()
                sys.stderr.flush()
                logger.info('🍎 MAC RESTART: Flushed stdout/stderr before os.execv')
            except Exception as e:
                logger.warning(f'🍎 MAC RESTART: Could not flush stdout/stderr: {e}')
            
            # 🍎 MAC SAFE: Clear critical operation flag before execv (file will be removed by new process)
            try:
                clear_critical_operation_flag()
                logger.info('🍎 MAC RESTART: Critical operation flag cleared before restart')
            except Exception as e:
                logger.warning(f'🍎 MAC RESTART: Could not clear critical flag: {e}')
            
            # 🍎 MAC SAFE: Use different restart mechanism on Mac to avoid console I/O blocking
            if platform.system() == 'Darwin':  # macOS
                try:
                    # Mac-specific restart: Start new process with visible terminal output
                    # Start new server process with preserved terminal output for demo visibility
                    subprocess.Popen(
                        [sys.executable] + sys.argv,
                        # Keep terminal output visible for demo - don't redirect to DEVNULL
                        stdin=subprocess.DEVNULL,  # Only redirect stdin to prevent input conflicts
                        cwd=os.getcwd(),
                        # Don't use start_new_session=True to keep terminal connection
                    )
                    
                    # Exit current process cleanly (new process will take over terminal)
                    time.sleep(0.8)  # Slightly longer delay for smoother terminal transition
                    os._exit(0)  # Clean exit without cleanup (new process handles everything)
                    
                except Exception as mac_restart_error:
                    logger.error(f'🍎 MAC RESTART: Mac-specific restart failed: {mac_restart_error}')
                    # Fall back to os.execv if Mac method fails
                    os.execv(sys.executable, ['python'] + sys.argv)
            else:
                # Non-Mac platforms: Use standard os.execv
                os.execv(sys.executable, ['python'] + sys.argv)
        except (BlockingIOError, OSError, IOError) as e:
            # 🍎 MAC SPECIFIC: BlockingIOError [Errno 35] is a Mac-specific I/O issue during restart
            if platform.system() == 'Darwin' and "write could not complete without blocking" in str(e):
                logger.info(f'🍎 MAC RESTART: Mac blocking I/O during restart (Error: {e}) - this is normal on Mac')
                logger.info('🍎 MAC RESTART: Attempting clean process exit for watchdog to handle restart')
                try:
                    # Let the watchdog handle the restart instead of retrying
                    time.sleep(1.0)  # Give time for I/O to clear
                    os._exit(0)  # Clean exit - watchdog will restart
                except:
                    # If even _exit fails, fall back to retry
                    pass
            
            log.error(f'Error restarting server (attempt {attempt + 1}/{max_retries})', e)
            if attempt < max_retries - 1:
                log.warning('Restart failed', 'Waiting 5 seconds before retrying')
                time.sleep(5)
            else:
                log.error('Max restart retries reached', 'Please restart the server manually')
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
            logger.info(f'🔄 FINDER_TOKEN: FILE_MODIFIED - {path} has been modified. Checking syntax and restarting...')
            restart_server()


def run_server_with_watchdog():
    logger.info('🚀 FINDER_TOKEN: SERVER_STARTUP - Starting server with watchdog')

    # 🤖 AI ASSISTANT EDUCATION: Explain startup banner behavior
    logger.warning("🤖 AI_STARTUP_BANNER: About to display main startup banner with ASCII art")
    logger.warning("🤖 AI_STARTUP_BANNER: This banner appears on every server start (manual or watchdog restart)")
    logger.warning("🤖 AI_STARTUP_BANNER: Console shows it once per session, logs capture every occurrence")
    logger.warning("🤖 AI_STARTUP_BANNER: aa.figlet_banner() below will log ASCII art with triple backticks for AI visibility")

    # 🎨 BEAUTIFUL RESTART BANNER
    aa.figlet_banner(APP_NAME, "Local First AI SEO Software", font='standard', color=BANNER_COLORS['workshop_ready'])

    # 🧊 VERSION BANNER - Display Nix flake version in standard font
    nix_version_raw = get_nix_version()
    # Parse version: "1.0.8 (JupyterLab Python Version Fix)" -> "Version 1.0.8" + "JupyterLab Python Version Fix"
    if '(' in nix_version_raw and ')' in nix_version_raw:
        version_number = nix_version_raw.split('(')[0].strip()
        subtitle = nix_version_raw.split('(')[1].rstrip(')')
        figlet_text = f"Version {version_number}"
    else:
        figlet_text = f"Version {nix_version_raw}"
        subtitle = "Nix Flake Version"

    aa.figlet_banner(figlet_text, subtitle, font='standard', color='white on default')
    slog.safe_print()
    aa.chip_says("Hello! The server is restarting. I'll be right back online.", BANNER_COLORS['workshop_ready'])
    env = get_current_environment()
    env_db = get_db_filename()  # 🚨 CRITICAL FIX: Use current environment's database file
    logger.info(f'🌍 FINDER_TOKEN: ENVIRONMENT - Current environment: {env}')
    if env == 'Development':
        log.warning('Development mode active', details=f'Using database: {env_db}')
    else:
        log.startup('Production mode active', details=f'Using database: {env_db}')
    # 🐰 ALICE WELCOME BANNER - Now moved to perfect transition point between FINDER_TOKENs ending and ROLES beginning

    # Additionally show debug information if STATE_TABLES is enabled
    if STATE_TABLES:
        log.startup('State tables enabled', details='Edit server.py and set STATE_TABLES=False to disable')
        print_routes()
    event_handler = ServerRestartHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=True)
    observer.start()
    try:
        log.startup('Server starting on http://localhost:5001')
        logger.info('🌐 FINDER_TOKEN: UVICORN_START - Starting uvicorn server on http://localhost:5001')
        # ascii_banner("Digital Workshop Online", "Ready for creative exploration at http://localhost:5001", "bright_green")
        log_level = 'debug' if DEBUG_MODE else 'warning'
        logger.info(f'📊 FINDER_TOKEN: UVICORN_CONFIG - Log level: {log_level}, Access log: {DEBUG_MODE}')
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
    # 🧪 TESTING PHILOSOPHY: Command line argument parsing for friction-free testing
    parser = argparse.ArgumentParser(description='Pipulate - Local-First Digital Workshop Framework')
    parser.add_argument('-t', '--test', '--tests', action='store_true',
                        help='Enable light testing mode - runs basic validation on startup')
    parser.add_argument('--test-deep', action='store_true',
                        help='Enable comprehensive testing mode')
    parser.add_argument('--test-browser', action='store_true',
                        help='Enable browser automation testing')
    args = parser.parse_args()

    # 🚨 CRITICAL: Check if server is already running via watchdog
    if check_server_already_running():
        sys.exit(0)

    # 🍎 MAC SAFE: Clear any stale critical operation flag from previous failed restart
    try:
        if is_critical_operation_in_progress():
            clear_critical_operation_flag()
            logger.info('🍎 MAC STARTUP: Cleared stale critical operation flag from previous restart')
    except Exception as e:
        logger.warning(f'🍎 MAC STARTUP: Could not clear stale critical flag: {e}')

    # 🤖 AI ASSISTANT EDUCATION: Explicit logging about restart behavior and console filtering
    # This is ONLY logged (not shown to console) to educate AI assistants about the sophisticated UX design
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: WATCHDOG RESTART BEHAVIOR EXPLANATION")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: The Pipulate server uses a sophisticated dual-display system:")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: 1. CONSOLE (for humans): Shows each banner ONCE per session for clean UX")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: 2. LOGS (for AI assistants): Captures ALL restart events including rapid restarts")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: When watchdog detects file changes, multiple rapid restarts may occur:")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: - Each restart triggers aa.figlet_banner() calls")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: - Console shows banners once (better newb/plebe experience)")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: - Logs capture every restart event for AI transparency")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: - DebugConsole class filters '🎭 AI_CREATIVE_VISION' from console output")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: - This creates a cleaner user experience while maintaining radical transparency for AI")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: GREP COMMANDS for AI assistants:")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: - grep 'ASCII_DATA:' logs/server.log  # See all ASCII art")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: - grep 'AI_RESTART_ARCHITECTURE' logs/server.log  # This explanation")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: - grep 'FIGLET_BANNER' logs/server.log  # All banner events")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: This dual-logging approach provides:")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: - Clean console experience for beginners")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: - Complete transparency for AI debugging")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: - Continuous narrative flow despite rapid restarts")

    run_server_with_watchdog()

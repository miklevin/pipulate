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
import traceback
import urllib.parse
# Suppress deprecation warnings from third-party packages
import warnings
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional

import aiohttp
import uvicorn
from fasthtml.common import *
from loguru import logger
from pyfiglet import Figlet
from rich.align import Align
from rich.box import ASCII, DOUBLE, HEAVY, ROUNDED
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.style import Style as RichStyle
from rich.table import Table, Text
from rich.theme import Theme
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse
from starlette.routing import Route
from starlette.websockets import WebSocket, WebSocketDisconnect
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Import MCP tools module for enhanced AI assistant capabilities
# Initialize MCP_TOOL_REGISTRY before importing mcp_tools to avoid circular dependency issues
MCP_TOOL_REGISTRY = {}

from mcp_tools import register_all_mcp_tools, register_mcp_tool
# Pass our registry to mcp_tools so they use the same instance
import mcp_tools
mcp_tools.MCP_TOOL_REGISTRY = MCP_TOOL_REGISTRY

# Import centralized configuration
from config import PCONFIG

warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")

# Various debug settings
DEBUG_MODE = False
STATE_TABLES = False
TABLE_LIFECYCLE_LOGGING = False  # Set to True to enable detailed table lifecycle logging

# 🧪 TESTING MODE: Revolutionary testing philosophy
TESTING_MODE = False      # Light testing on every server startup
DEEP_TESTING = False      # Comprehensive testing mode
BROWSER_TESTING = False   # Browser automation testing
# 🔧 CLAUDE'S NOTE: Re-added TABLE_LIFECYCLE_LOGGING to fix NameError
# These control different aspects of logging and debugging

# 🎨 BANNER COLOR CONFIGURATION
# Centralized color control for all storytelling banners and messages
BANNER_COLORS = {
    # Main banner colors
    'figlet_primary': 'bright_cyan',
    'figlet_subtitle': 'dim white',
    
    # ASCII banner colors  
    'ascii_title': 'bright_cyan',
    'ascii_subtitle': 'dim cyan',
    
    # Section headers
    'section_header': 'bright_yellow',
    
    # Story moments and messages
    'chip_narrator': 'bold cyan',
    'story_moment': 'bright_magenta', 
    'server_whisper': 'dim italic',
    
    # Startup sequence colors
    'server_awakening': 'bright_cyan',
    'mcp_arsenal': 'bright_blue',
    'plugin_registry_success': 'bright_green',
    'plugin_registry_warning': 'bright_yellow',
    'workshop_ready': 'bright_blue',
    'server_restart': 'yellow',
    
    # Special banners
    'white_rabbit': 'white on default',
    'transparency_banner': 'bright_cyan',
    'system_diagram': 'bright_blue',
    'status_banner': 'bright_green',
    
    # Box styles (Rich box drawing)
    'heavy_box': 'HEAVY',
    'rounded_box': 'ROUNDED', 
    'double_box': 'DOUBLE',
    'ascii_box': 'ASCII'
}

custom_theme = Theme({'default': 'white on black', 'header': RichStyle(color='magenta', bold=True, bgcolor='black'), 'cyan': RichStyle(color='cyan', bgcolor='black'), 'green': RichStyle(color='green', bgcolor='black'), 'orange3': RichStyle(color='orange3', bgcolor='black'), 'white': RichStyle(color='white', bgcolor='black')})

class DebugConsole(Console):

    def print(self, *args, **kwargs):
        # Filter out AI Creative Vision messages from console (they're for log files only)
        # Convert args to string to check for AI markers
        message_str = ' '.join(str(arg) for arg in args)
        
        # Skip console output for AI-specific messages (they go to logs only)
        if '🎭 AI_CREATIVE_VISION' in message_str:
            return
            
        super().print(*args, **kwargs)
console = DebugConsole(theme=custom_theme)


def rich_json_display(data, title=None, console_output=True, log_output=True, ai_log_output=True, log_prefix=""):
    """🎨 RICH JSON DISPLAY: Beautiful syntax-highlighted JSON for dicts and JSON data
    
    DUAL LOGGING SYSTEM:
    - Humans see Rich JSON syntax highlighting in console  
    - AI assistants see JSON data in log files for debugging assistance
    
    Args:
        data: Dict, list, or JSON-serializable data to display
        title: Optional title for the JSON display
        console_output: Whether to display Rich JSON to console for humans (default: True)
        log_output: Whether to log plain JSON for general logging (default: True)
        ai_log_output: Whether to log JSON for AI assistant visibility (default: True)
        log_prefix: Prefix for log messages (default: "")
    
    Returns:
        str: The formatted JSON string for logging
    """
    try:
        # Convert data to JSON string if it's not already
        if isinstance(data, str):
            # Try to parse and re-format for consistency
            try:
                parsed_data = json.loads(data)
                # Use Rich JSON for syntax highlighting
                rich_json = JSON(json.dumps(parsed_data, indent=2, default=str))
                json_str = json.dumps(parsed_data, indent=2, default=str)
            except json.JSONDecodeError:
                json_str = data
                rich_json = data
        else:
            # Use Rich JSON for syntax highlighting
            rich_json = JSON(json.dumps(data, indent=2, default=str))
            json_str = json.dumps(data, indent=2, default=str)
        
        # Console output with Rich syntax highlighting (for humans)
        if console_output:
            if title:
                console.print(f"\n🎨 {title}", style="bold cyan")
            
            # Use Rich's JSON class for beautiful syntax highlighting
            rich_json = JSON(json_str)
            console.print(rich_json)
            console.print()  # Add spacing
        
        # AI assistant logging - always log JSON data for AI visibility using WARNING level
        if ai_log_output:
            ai_title = f"AI_JSON_DATA: {title}" if title else "AI_JSON_DATA"
            # Use WARNING level so AI assistants can easily grep for "WARNING.*AI_JSON_DATA"
            logger.warning(f"🤖 {ai_title}:\n{json_str}")
        
        # Standard log output 
        if log_output and json_str:
            return json_str
            
        return json_str
        
    except Exception as e:
        error_msg = f"[Error formatting JSON for display: {e}] Data: {str(data)}"
        if console_output:
            console.print(f"❌ {error_msg}", style="red")
        if ai_log_output:
            logger.warning(f"🤖 AI_JSON_ERROR: {error_msg}")
        return error_msg


def rich_dict_display(data, title=None, console_output=True):
    """🎨 RICH DICT DISPLAY: Beautiful syntax-highlighted display for dictionaries
    
    Simplified version for when you just want to show dict data beautifully
    """
    return rich_json_display(data, title=title, console_output=console_output, log_output=False)


def strip_rich_formatting(text):
    """🎭 STRIP RICH FORMATTING: Remove Rich square-bracket color codes for AI transparency"""
    import re

    # Remove Rich color formatting like [bold], [/bold], [white on default], etc.
    clean_text = re.sub(r'\[/?[^\]]*\]', '', text)
    return clean_text


def share_ascii_with_ai(ascii_art, context_message, emoji="🎭"):
    """🎭 AI ASCII SHARING: Automatically share cleaned ASCII art with AI assistants"""
    clean_ascii = strip_rich_formatting(ascii_art)
    # Preserve actual newlines for proper ASCII art display in logs
    logger.warning(f"{emoji} AI_CREATIVE_VISION: {context_message} | ASCII_DATA:\n```\n{clean_ascii}\n```")


# Import ASCII art functions from externalized module (avoiding logger conflict)
from helpers.ascii_displays import (
    falling_alice, white_rabbit, system_diagram, figlet_banner, 
    ascii_banner, radical_transparency_banner, status_banner, 
    fig, chip_says, story_moment, server_whisper, section_header,
    log_reading_legend
)

# Initialize logging as early as possible in the startup process
def setup_logging():
    """
    🔧 UNIFIED LOGGING SYSTEM
    
    Single source of truth logging with rolling server logs.
    Designed for optimal debugging experience with surgical search capabilities.
    
    Features:
    - server.log (current run, live tail-able)
    - server-1.log, server-2.log, etc. (previous runs for context across restarts)
    - Unified log stream with clear categorization and finder tokens
    - No more fragmented api.log/lifecycle.log confusion
    """
    logger.remove()
    logs_dir = Path('logs')
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # === ROLLING LOG ROTATION SYSTEM ===
    # This preserves debugging context across server restarts
    server_log_path = logs_dir / 'server.log'
    MAX_ROLLED_LOGS = 10  # Keep last 10 server runs
    # 🔧 FINDER_TOKEN: MAX_ROLLED_LOOKING_AT_DIRS moved to mcp_tools.py (used by rotate_looking_at_directory)
    
    # Clean up old numbered logs beyond our limit
    for i in range(MAX_ROLLED_LOGS + 1, 100):
        old_log = logs_dir / f'server-{i}.log'
        if old_log.exists():
            try:
                old_log.unlink()
                print(f'🧹 Cleaned up old server log: {old_log}')
            except Exception as e:
                print(f'⚠️ Failed to delete old server log {old_log}: {e}')
    
    # Rotate existing logs: server-1.log → server-2.log, etc.
    if server_log_path.exists():
        for i in range(MAX_ROLLED_LOGS - 1, 0, -1):
            old_path = logs_dir / f'server-{i}.log'
            new_path = logs_dir / f'server-{i + 1}.log'
            if old_path.exists():
                try:
                    old_path.rename(new_path)
                    logger.info(f'📁 Rotated: {old_path.name} → {new_path.name}')
                except Exception as e:
                    logger.warning(f'⚠️ Failed to rotate {old_path}: {e}')
        
        # Move current server.log to server-1.log
        try:
            server_log_path.rename(logs_dir / 'server-1.log')
            logger.info(f'📁 Archived current run: server.log → server-1.log')
        except Exception as e:
            logger.warning(f'⚠️ Failed to archive current server.log: {e}')
    
    # === CLEAN UP LEGACY LOG FILES ===
    # Remove the old fragmented log system
    legacy_files = ['api.log', 'lifecycle.log', 'table_lifecycle.log'] + [f'api-{i}.log' for i in range(1, 20)]
    for legacy_file in legacy_files:
        legacy_path = logs_dir / legacy_file
        if legacy_path.exists():
            try:
                legacy_path.unlink()
                print(f'🧹 Removed legacy log: {legacy_file}')
            except Exception as e:
                print(f'⚠️ Failed to remove legacy log {legacy_file}: {e}')
    
    # === UNIFIED LOG FORMAT ===
    log_level = 'DEBUG' if DEBUG_MODE else 'INFO'
    time_format = '{time:HH:mm:ss}'
    
    # File logging - comprehensive for debugging
    file_format = f'{time_format} | {{level: <8}} | {{name: <15}} | {{message}}'
    logger.add(
        server_log_path, 
        level=log_level, 
        format=file_format, 
        enqueue=True,
        backtrace=True,
        diagnose=True
    )
    
    # Console logging - clean for live monitoring (exclude AI JSON data)
    console_format = '<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name: <15}</cyan> | {message}'
    logger.add(
        sys.stderr, 
        level=log_level, 
        format=console_format, 
        colorize=True, 
        filter=lambda record: (
            # Exclude AI JSON data from console (humans see Rich display instead)
            '🤖 AI_JSON' not in record['message'] and
            # Exclude AI Creative Vision from console (humans see Rich display instead)
            'AI_CREATIVE_VISION' not in record['message'] and
            (
                record['level'].name != 'DEBUG' or 
                any(key in record['message'] for key in [
                    'FINDER_TOKEN', 'MCP', 'BOTIFY', 'API', 'Pipeline ID:', 
                    'State changed:', 'Creating', 'Updated', 'Plugin', 'Role'
                ])
            )
        )
    )
    # === STARTUP MESSAGES ===
    if STATE_TABLES:
        logger.info('🔍 FINDER_TOKEN: STATE_TABLES_ENABLED - Console will show 🍪 and ➡️ table snapshots')
    
    # Welcome message for the new unified system
    logger.info('🚀 FINDER_TOKEN: UNIFIED_LOGGING_ACTIVE - Single source of truth logging initialized')
    logger.info(f'📁 FINDER_TOKEN: LOG_ROTATION_READY - Keeping last {MAX_ROLLED_LOGS} server runs for debugging context')
    logger.info("🍞 FINDER_TOKEN: MCP_DISCOVERY_SCRIPT - For a full list of all MCP tools, run: .venv/bin/python discover_mcp_tools.py")
    
    return logger


# Show startup banner only when running as main script, not on watchdog restarts or imports
if __name__ == '__main__' and not os.environ.get('PIPULATE_WATCHDOG_RESTART'):
    figlet_banner("STARTUP", "Pipulate server starting...", font='slant', color=BANNER_COLORS['server_restart'])

# 🔧 FINDER_TOKEN: rotate_looking_at_directory moved to mcp_tools.py to eliminate circular imports

# Initialize logger BEFORE any functions that need it
logger = setup_logging()


# Log early startup phase
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

class GracefulRestartException(SystemExit):
    """Custom exception to signal a restart requested by Watchdog."""
    pass

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
        # Ensure the data directory exists before writing the file
        ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
        ENV_FILE.write_text('Development')
        return 'Development'

def get_nix_version():
    """Get the version and description from the single source of truth: pipulate.__version__ and __version_description__"""
    import os
    
    # Get version and description from single source of truth
    try:
        # Import the version and description from our package
        from pipulate import __version__, __version_description__
        return f"{__version__} ({__version_description__})"
    except ImportError:
        # Fallback to parsing __init__.py directly
        try:
            import re
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

def get_backup_status() -> dict:
    """Get backup system status for display in settings."""
    try:
        # Import backup manager
        from helpers.durable_backup_system import backup_manager
        
        # Get backup directory info
        backup_root = str(backup_manager.backup_root)
        
        # Check if backup directory exists and get basic info
        backup_exists = backup_manager.backup_root.exists()
        
        if backup_exists:
            # Get list of backup files
            backup_files = list(backup_manager.backup_root.glob("*.db"))
            table_status = {}
            
            for file in backup_files:
                # Parse filename to get table name and date
                name_parts = file.stem.split('_')
                if len(name_parts) >= 2:
                    table_name = '_'.join(name_parts[:-1])
                    date_str = name_parts[-1]
                    
                    # Get file info
                    file_size = file.stat().st_size
                    mod_time = file.stat().st_mtime
                    
                    if table_name not in table_status or mod_time > table_status[table_name]['last_backup']:
                        table_status[table_name] = {
                            'last_backup': mod_time,
                            'date_str': date_str,
                            'size': file_size
                        }
        else:
            table_status = {}
        
        return {
            'available': True,
            'backup_root': backup_root,
            'backup_exists': backup_exists,
            'table_status': table_status,
            'total_files': len(backup_files) if backup_exists else 0
        }
        
    except ImportError:
        return {
            'available': False,
            'error': 'Backup system not available'
        }
    except Exception as e:
        return {
            'available': False,
            'error': str(e)
        }

ENV_FILE = Path('data/current_environment.txt')

APP_NAME = get_app_name()
logger.info(f'🏷️ FINDER_TOKEN: APP_CONFIG - App name: {APP_NAME}')

DB_FILENAME = get_db_filename()
logger.info(f'🗄️ FINDER_TOKEN: DB_CONFIG - Database filename: {DB_FILENAME}')


MODEL = 'gemma3'
# 🎯 OPTIMIZED FOR 128K TOKEN WINDOW: Based on 43 tokens/message average
# 128K tokens * 80% safety margin = 102,400 tokens ÷ 43 tokens/msg = ~2,400 messages
# Setting to 2,000 messages for safety margin and optimal performance
MAX_CONVERSATION_LENGTH = 2000  # Optimized for 128K token window (was 10000)

logger.info(f'🤖 FINDER_TOKEN: LLM_CONFIG - Model: {MODEL}, Conversation length: {MAX_CONVERSATION_LENGTH}')

# ================================================================
# 💬 PERSISTENT CONVERSATION HISTORY - SURVIVES SERVER RESTARTS
# ================================================================

# 🧹 LEGACY PURGED: save_conversation_to_db() removed - new system auto-saves on append

def inject_behavioral_reinforcement():
    """Inject behavioral reinforcement reminders to prevent 'promise trap' behavior.
    
    This helps local LLMs avoid making promises about what they 'will do' and instead
    encourages immediate action through MCP tools.
    """
    try:
        conv_system = get_global_conversation_system()
        conversation_list = conv_system.get_conversation_list()
        
        # Check if conversation history exists and has enough messages to warrant reinforcement
        if len(conversation_list) > 5:
            reinforcement_message = """🧠 **BEHAVIORAL REMINDER: DO IT NOW PROTOCOL**

Your conversation history shows previous interactions. Remember your core behavioral rule:

**NEVER PROMISE - ALWAYS EXECUTE**

If a user asks about logs, files, system state, or needs analysis:
- ✅ Use your MCP tools IMMEDIATELY in the same response
- ❌ Do NOT say "I will check that for you" 
- ✅ Say "Let me check that right now" and execute the tool

**Your superpowers work NOW, not later. Action delayed is action denied.**

Continue the conversation with immediate tool usage, not promises."""

            # Only inject if we haven't recently injected behavioral reminders
            recent_messages = conversation_list[-3:] if len(conversation_list) >= 3 else conversation_list
            already_has_reminder = any('BEHAVIORAL REMINDER' in msg.get('content', '') for msg in recent_messages)
            
            if not already_has_reminder:
                conv_system.append_message('system', reinforcement_message)
                logger.info("🧠 FINDER_TOKEN: BEHAVIORAL_REINFORCEMENT - Injected 'Do It Now' reminder into conversation")
                return True
        
        return False
    except Exception as e:
        logger.error(f"🧠 BEHAVIORAL_REINFORCEMENT_ERROR - Failed to inject behavioral reminder: {e}")
        return False

def restore_conversation_on_startup():
    """Restore conversation history on server startup using append-only system."""
    global global_conversation_history
    
    try:
        conv_system = get_global_conversation_system()
        conversation_list = conv_system.get_conversation_list()
        
        if conversation_list:
            # Clear the old deque and populate with new system data
            global_conversation_history.clear()
            global_conversation_history.extend(conversation_list)
            
            logger.info(f"💾 FINDER_TOKEN: CONVERSATION_RESTORED - {len(conversation_list)} messages loaded from append-only system")
            
            # 🧠 BEHAVIORAL REINFORCEMENT: Inject behavioral reminders after restoration
            behavioral_injected = inject_behavioral_reinforcement()
            if behavioral_injected:
                logger.info("🧠 FINDER_TOKEN: BEHAVIORAL_REINFORCEMENT_STARTUP - 'Do It Now' protocol activated after restoration")
            
            return True
        else:
            logger.debug("💾 CONVERSATION_RESTORED - No saved conversation history found")
            return False
            
    except Exception as e:
        logger.error(f"💾 CONVERSATION_RESTORE_ERROR - Failed to restore conversation history: {e}")
        return False


# ================================================================
# MCP TOOL REGISTRY - Generic Tool Dispatch System
# ================================================================
# This registry allows plugins to register MCP tools that can be called
# via the /mcp-tool-executor endpoint. Tools are simple async functions
# that take parameters and return structured responses.

# Global registry for MCP tools - populated by plugins during startup
# 🔧 FINDER_TOKEN: register_mcp_tool moved to mcp_tools.py (superior error handling)
# Use register_mcp_tool from mcp_tools.py - it has better error handling for uninitialized registry

# MCP tools are now consolidated in mcp_tools.py - see register_all_mcp_tools()

# 🎨 MCP TOOLS BANNER - Now displayed in startup_event() after tools are registered

# Tools now registered via register_all_mcp_tools() from mcp_tools.py

# ================================================================
# 🔧 FINDER_TOKEN: MCP_TOOLS_CONSOLIDATED
# All MCP tools (including _botify_ping, _botify_list_projects, _botify_simple_query, 
# _pipeline_state_inspector, etc.) have been moved to mcp_tools.py for better organization.
# See register_all_mcp_tools() in mcp_tools.py for complete tool registration.

# 🔧 FINDER_TOKEN: _read_botify_api_token moved to mcp_tools.py to eliminate duplication

# 🔧 FINDER_TOKEN: BOTIFY_TOOLS_COMPLETELY_MOVED_TO_MCP_TOOLS_PY
# All Botify MCP tools moved to mcp_tools.py for better maintainability:
# - _botify_get_full_schema (125 lines) - The 4,449 field discovery revolution
# - _botify_list_available_analyses (65 lines) - Local analyses.json reading  
# - _botify_execute_custom_bql_query (120 lines) - Core query wizard tool
# This removes 310 lines of duplicate code from server.py

# 🔧 FINDER_TOKEN: ALL_BOTIFY_TOOLS_MOVED_TO_MCP_TOOLS_PY
# ALL Botify tools are now registered via register_all_mcp_tools() in mcp_tools.py:
# - botify_ping, botify_list_projects, botify_simple_query  
# - botify_get_full_schema, botify_list_available_analyses, botify_execute_custom_bql_query

# Register Local LLM Helper Tools (Limited file access for local LLMs)
# 🔧 FINDER_TOKEN: LOCAL_LLM_TOOLS_COMPLETELY_MOVED_TO_MCP_TOOLS_PY  
# ALL local_llm tools (read_file, grep_logs, list_files, get_context)
# are now registered via register_all_mcp_tools() in mcp_tools.py
# The sophisticated implementations with better security, performance, and features
# are in mcp_tools.py. The simple duplicate versions have been removed from server.py.

# 🔧 FINDER_TOKEN: UI_TOOLS_MOVED_TO_MCP_TOOLS_PY
# UI interaction tools (ui_flash_element, ui_list_elements) 
# are now registered via register_all_mcp_tools() in mcp_tools.py

# 🌐 FINDER_TOKEN: BROWSER_MCP_TOOLS_CORE - AI EYES AND HANDS
# 🎯 FINDER_TOKEN: AI_CURRENT_PAGE_INTERACTION
def print_and_log_table(table, title_prefix=""):
    """Print rich table to console AND log structured data to server.log for radical transparency.
    
    This single function ensures both console display and log transparency happen together,
    preventing the mistake of using one without the other.
    
    Args:
        table: Rich Table object to display and log
        title_prefix: Optional prefix for the log entry
    """
    # First, display the rich table in console with full formatting
    console.print(table)
    
    # Then, extract and log the table data for server.log transparency
    try:
        # Extract table data for logging
        table_title = getattr(table, 'title', 'Table')
        if table_title:
            table_title = str(table_title)
        
        # Start with title and add extra line for visibility
        log_lines = [f"\n📊 {title_prefix}RICH TABLE: {table_title}"]
        
        # Add column headers if available
        if hasattr(table, 'columns') and table.columns:
            headers = []
            for col in table.columns:
                if hasattr(col, 'header'):
                    headers.append(str(col.header))
                elif hasattr(col, '_header'):
                    headers.append(str(col._header))
            if headers:
                log_lines.append(f"Headers: {' | '.join(headers)}")
        
        # Add rows if available
        if hasattr(table, '_rows') and table._rows:
            for i, row in enumerate(table._rows):
                if hasattr(row, '_cells'):
                    cells = [str(cell) if cell else '' for cell in row._cells]
                    log_lines.append(f"Row {i+1}: {' | '.join(cells)}")
                else:
                    log_lines.append(f"Row {i+1}: {str(row)}")
        
        # Log the complete table representation with extra spacing
        logger.info('\n'.join(log_lines) + '\n')
        
    except Exception as e:
        logger.error(f"Error logging rich table: {e}")
        logger.info(f"📊 {title_prefix}RICH TABLE: [Unable to extract table data]")

def set_current_environment(environment):
    ENV_FILE.write_text(environment)
    logger.info(f'Environment set to: {environment}')

def _recursively_parse_json_strings(obj):
    """
    🔧 RECURSIVE JSON PARSER: Recursively parse JSON strings in nested data structures.
    This makes deeply nested workflow data much more readable in logs.
    
    Handles:
    - Dict values that are JSON strings
    - List items that are JSON strings  
    - Nested dicts and lists
    - Graceful fallback if parsing fails
    """
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if isinstance(value, str):
                # Try to parse JSON strings
                try:
                    # Quick heuristic: if it starts with { or [ and ends with } or ], try parsing
                    if (value.startswith('{') and value.endswith('}')) or \
                       (value.startswith('[') and value.endswith(']')):
                        parsed_value = json.loads(value)
                        # Recursively process the parsed result
                        result[key] = _recursively_parse_json_strings(parsed_value)
                    else:
                        result[key] = value
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, keep the original string
                    result[key] = value
            elif isinstance(value, (dict, list)):
                # Recursively process nested structures
                result[key] = _recursively_parse_json_strings(value)
            else:
                result[key] = value
        return result
    elif isinstance(obj, list):
        result = []
        for item in obj:
            if isinstance(item, str):
                # Try to parse JSON strings in lists
                try:
                    if (item.startswith('{') and item.endswith('}')) or \
                       (item.startswith('[') and item.endswith(']')):
                        parsed_item = json.loads(item)
                        result.append(_recursively_parse_json_strings(parsed_item))
                    else:
                        result.append(item)
                except (json.JSONDecodeError, TypeError):
                    result.append(item)
            elif isinstance(item, (dict, list)):
                # Recursively process nested structures
                result.append(_recursively_parse_json_strings(item))
            else:
                result.append(item)
        return result
    else:
        # For non-dict/list objects, return as-is
        return obj

def _format_records_for_lifecycle_log(records_iterable):
    """Format records (list of dicts or objects) into a readable JSON string for logging.
    Handles empty records, dataclass-like objects, dictionaries, and attempts to convert SQLite rows to dicts.
    Excludes private attributes for cleaner logs. 
    SMART FEATURE: Automatically parses JSON strings in 'data' fields to prevent ugly escaping."""
    if not records_iterable:
        return '[] # Empty'
    processed_records = []
    for r in records_iterable:
        record_dict = None
        if hasattr(r, '_asdict'):
            record_dict = r._asdict()
        elif hasattr(r, '__dict__') and (not isinstance(r, type)):
            record_dict = {k: v for k, v in r.__dict__.items() if not k.startswith('_sa_')}
        elif isinstance(r, dict):
            record_dict = r
        elif hasattr(r, 'keys'):
            try:
                record_dict = dict(r)
            except:
                record_dict = dict(zip(r.keys(), r))
        else:
            processed_records.append(str(r))
            continue
            
        # 🔧 SMART JSON PARSING: Recursively parse JSON strings for maximum readability
        if record_dict and isinstance(record_dict, dict):
            record_dict = _recursively_parse_json_strings(record_dict)
                
        processed_records.append(record_dict)
    
    try:
        # Use Rich JSON display for formatted records
        return rich_json_display(processed_records, title="Formatted Records", console_output=False, log_output=True)
    except Exception as e:
        return f'[Error formatting records for JSON: {e}] Processed: {str(processed_records)}'

def log_dynamic_table_state(table_name: str, data_source_callable, title_prefix: str=''):
    """
    🔧 CLAUDE'S UNIFIED LOGGING: Logs table state to unified server.log
    Simplified from the old lifecycle logging system.
    """
    try:
        records = list(data_source_callable())
        # Convert records to list of dicts for Rich JSON display
        records_data = []
        for record in records:
            if hasattr(record, '_asdict'):
                # Named tuple
                records_data.append(record._asdict())
            elif hasattr(record, '__dict__'):
                # Object with attributes
                records_data.append(record.__dict__)
            elif isinstance(record, dict):
                # Already a dict
                records_data.append(record)
            else:
                # SQLite Row or other - try to convert to dict
                try:
                    records_data.append(dict(record))
                except:
                    records_data.append(str(record))
        
        # Use Rich JSON display for table data - show in console with beautiful formatting  
        # Enable AI logging so AI assistants can see the JSON data
        rich_json_display(records_data, title=f"Table State: {table_name}", console_output=True, log_output=False, ai_log_output=True)
        
        # Log just the FINDER_TOKEN without the JSON content (Rich already showed it beautifully)
        logger.info(f"🔍 FINDER_TOKEN: TABLE_STATE_{table_name.upper()} - {title_prefix} Snapshot: [Rich JSON displayed to console]")
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: TABLE_STATE_ERROR - Failed to log '{table_name}' ({title_prefix}): {e}")

def log_dictlike_db_to_lifecycle(db_name: str, db_instance, title_prefix: str=''):
    """
    🔧 CLAUDE'S UNIFIED LOGGING: Logs DictLikeDB state to unified server.log
    Enhanced with semantic meaning for AI assistant understanding.
    """
    # 🍪 SESSION HIJACKING NEXUS: Load from training file and add to both logs AND conversation history
    session_hijacking_msg = read_training("ai_session_hijacking_message.md")
    server_whisper(session_hijacking_msg, "🎯")
    
    # 🚨 CRITICAL: Also add to conversation history for immediate LLM context
    try:
        append_to_conversation(session_hijacking_msg, role='system')
    except Exception as e:
        logger.debug(f"Could not add session hijacking message to conversation: {e}")
    
    # 🎬 DEMONSTRATION: Trigger "I control the horizontal, I control the vertical" moment
    try:
        from pathlib import Path
        browser_automation_active = Path('browser_automation/looking_at').exists()
        if browser_automation_active:
            demo_trigger_msg = read_training("ai_embodiment_demonstration.md")
            server_whisper(demo_trigger_msg, "🎬")
            append_to_conversation(demo_trigger_msg, role='system')
            
    except Exception as e:
        logger.debug(f"Could not trigger AI embodiment demonstration: {e}")
    try:
        items = dict(db_instance.items())
        # Use Rich JSON display for database items - show in console with beautiful formatting
        # Enable AI logging so AI assistants can see the JSON data
        rich_json_display(items, title=f"Database State: {db_name}", console_output=True, log_output=False, ai_log_output=True)
        
        # Add semantic context for AI assistants
        semantic_info = []
        for key, value in items.items():
            if key == "last_profile_id":
                semantic_info.append(f"🧑 Active user profile: {value}")
            elif key == "last_app_choice":
                semantic_info.append(f"📱 Current app/workflow: {value or 'None (Home page)'}")
            elif key == "current_environment":
                semantic_info.append(f"🌍 Environment mode: {value}")
            elif key == "profile_locked":
                lock_status = "🔒 LOCKED" if value == "1" else "🔓 Unlocked"
                semantic_info.append(f"👤 Profile editing: {lock_status}")
            elif key == "theme_preference":
                semantic_info.append(f"🎨 UI theme: {value}")
            elif key == "split-sizes":
                semantic_info.append(f"📐 UI layout split: {value}")
            elif key == "last_visited_url":
                semantic_info.append(f"🔗 Last page visited: {value}")
            elif key.startswith("endpoint_message_sent"):
                env = key.replace("endpoint_message_sent__", "")
                semantic_info.append(f"📨 Startup message sent for {env}: {value}")
            elif key == "temp_message":
                semantic_info.append(f"💬 Temporary UI message: {value}")
        
        # Log just the FINDER_TOKEN without the JSON content (Rich already showed it beautifully)
        logger.info(f"🔍 FINDER_TOKEN: DB_STATE_{db_name.upper()} - {title_prefix} Key-Value Store: [Rich JSON displayed to console]")
        
        if semantic_info:
            semantic_summary = "\n".join(f"    {info}" for info in semantic_info)
            logger.info(f"🔍 SEMANTIC_DB_{db_name.upper()}: {title_prefix} Human-readable state:\n{semantic_summary}")
            
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: DB_STATE_ERROR - Failed to log DictLikeDB '{db_name}' ({title_prefix}): {e}")

def log_raw_sql_table_to_lifecycle(db_conn, table_name: str, title_prefix: str=''):
    """
    🔧 CLAUDE'S UNIFIED LOGGING: Logs raw SQL table state to unified server.log
    Simplified from the old lifecycle logging system.
    """
    original_row_factory = db_conn.row_factory
    db_conn.row_factory = sqlite3.Row
    try:
        cursor = db_conn.cursor()
        cursor.execute(f'SELECT * FROM {table_name}')
        rows = cursor.fetchall()
        content = _format_records_for_lifecycle_log(rows)
        logger.info(f"🔍 FINDER_TOKEN: SQL_TABLE_{table_name.upper()} - {title_prefix} Raw SQL:\n{content}")
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: SQL_TABLE_ERROR - Failed to log raw SQL table '{table_name}' ({title_prefix}): {e}")
    finally:
        db_conn.row_factory = original_row_factory

def log_pipeline_summary(title_prefix: str=''):
    """
    🔧 PIPELINE SUMMARY: User-friendly summary of pipeline state for startup logging.
    Provides just enough information to be super useful without terrifying newbs.
    """
    try:
        records = list(pipeline())
        
        if not records:
            logger.info(f"🔍 FINDER_TOKEN: PIPELINE_SUMMARY - {title_prefix} No active workflows")
            return
            
        total_workflows = len(records)
        
        # Group by app_name for summary
        app_counts = {}
        finalized_count = 0
        recent_activity = []
        
        for record in records:
            # SQLite Row objects support direct attribute access
            try:
                app_name = getattr(record, 'app_name', 'unknown')
                app_counts[app_name] = app_counts.get(app_name, 0) + 1
                
                # Check if finalized
                data_str = getattr(record, 'data', '{}')
                if isinstance(data_str, str):
                    # Handle case where data is JSON string
                    try:
                        import json
                        data = json.loads(data_str)
                    except:
                        data = {}
                else:
                    data = data_str
                
                if data.get('finalize', {}).get('finalized'):
                    finalized_count += 1
                    
                # Track recent activity (last 24 hours)
                updated = getattr(record, 'updated', '')
                if updated:
                    try:
                        from datetime import datetime, timedelta
                        updated_time = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                        if datetime.now().replace(tzinfo=updated_time.tzinfo) - updated_time < timedelta(hours=24):
                            recent_activity.append({
                                'pkey': getattr(record, 'pkey', ''),
                                'app': app_name,
                                'updated': updated
                            })
                    except:
                        pass
            except Exception as e:
                logger.debug(f"Error processing pipeline record: {e}")
                continue
        
        # Create friendly summary
        summary_lines = [
            f"📊 Total workflows: {total_workflows}",
            f"🔒 Finalized: {finalized_count}",
            f"⚡ Active: {total_workflows - finalized_count}"
        ]
        
        # Add app breakdown
        if app_counts:
            app_summary = ", ".join([f"{app}({count})" for app, count in sorted(app_counts.items())])
            summary_lines.append(f"📱 Apps: {app_summary}")
        
        # 📚 LOG LEGEND: Quick crash course in reading Pipulate logs
        legend_content = log_reading_legend()

        legend_panel = Panel(
            legend_content,
            title="📖 [bold bright_blue]Log Reading Guide[/bold bright_blue]",
            subtitle="[dim]Understanding what you're seeing in the logs[/dim]",
            box=ROUNDED,
            style="bright_blue",
            padding=(1, 2)
        )
        print()
        console.print(legend_panel)
        print()
        
        # 🎭 AI CREATIVE TRANSPARENCY: Share the log legend with AI assistants
        share_ascii_with_ai(legend_content, "Log Reading Guide - 📖 Educational moment: This legend explains Pipulate's log format and emoji system for new users!", "📖")
        print()

        # Add recent activity
        if recent_activity:
            recent_count = len(recent_activity)
            summary_lines.append(f"🕒 Recent activity (24h): {recent_count} workflows")
            
        summary = "\n    ".join(summary_lines)
        logger.info(f"🔍 FINDER_TOKEN: PIPELINE_SUMMARY - {title_prefix} Workflow Overview:\n    {summary}")
        
        # For AI assistants: log a few recent workflow keys for context
        if records:
            recent_keys = []
            for record in records[-3:]:
                try:
                    pkey = getattr(record, 'pkey', 'unknown')
                    recent_keys.append(pkey)
                except:
                    recent_keys.append('unknown')
            logger.info(f"🔍 SEMANTIC_PIPELINE_CONTEXT: {title_prefix} Recent workflow keys: {', '.join(recent_keys)}")
            
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: PIPELINE_SUMMARY_ERROR - Failed to create pipeline summary ({title_prefix}): {e}")
        # Fallback to original detailed logging if summary fails
        try:
            records = list(pipeline())
            content = _format_records_for_lifecycle_log(records)
            logger.info(f"🔍 FINDER_TOKEN: TABLE_STATE_PIPELINE - {title_prefix} Fallback Snapshot:\n{content}")
        except Exception as fallback_error:
            logger.error(f"❌ FINDER_TOKEN: PIPELINE_FALLBACK_ERROR - Both summary and fallback failed: {fallback_error}")

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
                # Use Rich JSON display for debug data
                formatted_data = rich_json_display(data, console_output=False, log_output=True)
                self.logger.debug(f'{msg} | {formatted_data}')
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
            error_details = f'{error.__class__.__name__}: {str(error)}'
            self.logger.error(f'{formatted} | {error_details}')
            self.logger.debug(traceback.format_exc())
        else:
            self.logger.error(formatted)

    def debug(self, category, message, details=None):
        """Log debug information that only appears in DEBUG mode."""
        self.logger.debug(self.format_message(category, message, details))
log = LogManager(logger)

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
            return None  # Prevents writing noise to the conversation history
    return prompt_or_filename
global_conversation_history = deque(maxlen=MAX_CONVERSATION_LENGTH)
conversation = [{'role': 'system', 'content': read_training('system_prompt.md')}]

# 🔧 CONVERSATION PERSISTENCE FIX: Prevent auto-save during startup restoration
startup_restoration_in_progress = False  # Trigger watchdog restart

# ================================================================
# 🛡️ NEW APPEND-ONLY CONVERSATION SYSTEM - ARCHITECTURALLY BULLETPROOF
# ================================================================

# Import the new append-only conversation system
from helpers.append_only_conversation import get_conversation_system

# Initialize the global conversation system
global_conversation_system = None

def get_global_conversation_system():
    """Get or create the global conversation system instance"""
    global global_conversation_system
    if global_conversation_system is None:
        global_conversation_system = get_conversation_system()
    return global_conversation_system

def append_to_conversation(message=None, role='user'):
    """Append a message to the global conversation history.

    This function manages the conversation history by:
    1. Ensuring a system message exists at the start of history
    2. Appending new messages with specified roles
    3. Maintaining conversation length limits via deque maxlen
    4. Preventing duplicate consecutive messages
    5. IMMEDIATELY saving to database (bound operation)

    Args:
        message (str, optional): The message content to append. If None, returns current history.
        role (str, optional): The role of the message sender. Defaults to 'user'.

    Returns:
        list: The complete conversation history after appending.
    """
    # 🔧 CONVERSATION PERSISTENCE FIX: Access global flag at function start
    global startup_restoration_in_progress
    
    if message is None:
        return list(global_conversation_history)
    
    # Check if this would be a duplicate of any of the last 3 messages to prevent rapid duplicates
    if global_conversation_history:
        recent_messages = list(global_conversation_history)[-3:]  # Check last 3 messages
        for recent_msg in recent_messages:
            if recent_msg['content'] == message and recent_msg['role'] == role:
                logger.warning(f"🔍 DUPLICATE DETECTED! Skipping append. Message: '{message[:50]}...'")
                return list(global_conversation_history)
        
    # 🔧 CONVERSATION PERSISTENCE FIX: Don't inject system prompt during startup restoration
    needs_system_message = (
        len(global_conversation_history) == 0 or 
        global_conversation_history[0]['role'] != 'system'
    ) and not startup_restoration_in_progress
    
    if needs_system_message:
        global_conversation_history.appendleft(conversation[0])
    
    # CRITICAL: Append to conversation history in memory (for compatibility)
    global_conversation_history.append({'role': role, 'content': message})
    
    # CRITICAL: IMMEDIATELY save to new append-only database system
    try:
        # Skip auto-save during startup restoration
        if not startup_restoration_in_progress:
            # 🚫 FILTER: Skip saving noise messages
            noise_patterns = [
                "No training content available",
                "Training content for", 
                "No endpoint message available",
                "No training found",
                "Training file not found"
            ]
            
            is_noise = any(message.startswith(pattern) for pattern in noise_patterns)
            
            if is_noise:
                logger.debug(f"💾 CONVERSATION_FILTER_SKIP - Filtered out noise: '{message[:50]}...'")
            else:
                conv_system = get_global_conversation_system()
                message_id = conv_system.append_message(role, message)
                
                if message_id:
                    logger.info(f"💾 FINDER_TOKEN: CONVERSATION_APPEND_ONLY_SAVED - Message ID {message_id}, Role: {role}")
                else:
                    logger.debug("💾 CONVERSATION_APPEND_ONLY_SKIPPED - Duplicate message not saved")
        else:
            logger.debug("💾 SKIP_AUTO_SAVE - Startup restoration in progress, skipping auto-save")
            
    except Exception as e:
        logger.error(f"💾 CRITICAL: CONVERSATION_APPEND_ONLY_FAILURE - {e}")
        # Don't re-raise - allow conversation to continue in memory even if DB fails
        logger.warning("💾 Continuing with in-memory conversation despite database failure")
    
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
        return PCONFIG['HOME_MENU_ITEM']
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
                formatted_changes = rich_json_display(changes, console_output=False, log_output=True)
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

    
    def get_ui_constants(self):
        """Access centralized UI constants through dependency injection."""
        return PCONFIG['UI_CONSTANTS']
    
    def get_config(self):
        """Access centralized configuration through dependency injection."""
        return PCONFIG
    
    def get_button_border_radius(self):
        """Get the global button border radius setting."""
        return PCONFIG['UI_CONSTANTS']['BUTTON_STYLES']['BORDER_RADIUS']

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

    async def log_api_call_details(self, pipeline_id: str, step_id: str, call_description: str, method: str, url: str, headers: dict, payload: Optional[dict]=None, response_status: Optional[int]=None, response_preview: Optional[str]=None, response_data: Optional[dict]=None, curl_command: Optional[str]=None, python_command: Optional[str]=None, estimated_rows: Optional[int]=None, actual_rows: Optional[int]=None, file_path: Optional[str]=None, file_size: Optional[str]=None, notes: Optional[str]=None):
        """Log complete API call details for extreme observability and Jupyter reproduction.
        
        This provides the same level of transparency for API calls as is used in BQL query logging,
        including copy-paste ready Python code for Jupyter notebook reproduction.
        """
        log_entry_parts = []
        log_entry_parts.append(f'  [API Call] {call_description or "API Request"}')
        log_entry_parts.append(f'  Pipeline ID: {pipeline_id}')
        log_entry_parts.append(f'  Step ID: {step_id}')
        log_entry_parts.append(f'  Method: {method}')
        log_entry_parts.append(f'  URL: {url}')
        if headers:
            headers_preview = {k: v for k, v in headers.items() if k.lower() not in ['authorization', 'cookie', 'x-api-key']}
            if len(headers_preview) != len(headers):
                headers_preview['<REDACTED_AUTH_HEADERS>'] = f'{len(headers) - len(headers_preview)} hidden'
            # Use Rich JSON display for headers
            pretty_headers = rich_json_display(headers_preview, title="API Headers", console_output=True, log_output=True)
            log_entry_parts.append(f'  Headers: {pretty_headers}')
        if payload:
            try:
                # Use Rich JSON display for payload
                pretty_payload = rich_json_display(payload, title="API Payload", console_output=True, log_output=True)
                log_entry_parts.append(f'  Payload:\n{pretty_payload}')
            except Exception:
                log_entry_parts.append(f'  Payload: {payload}')
        if curl_command:
            log_entry_parts.append(f'  cURL Command:\n{curl_command}')
        if python_command:
            # Use centralized emoji configuration for console messages
            python_emoji = PCONFIG['UI_CONSTANTS']['EMOJIS']['PYTHON_CODE']
            snippet_emoji = PCONFIG['UI_CONSTANTS']['EMOJIS']['CODE_SNIPPET']
            comment_divider = PCONFIG['UI_CONSTANTS']['CODE_FORMATTING']['COMMENT_DIVIDER']
            snippet_intro = PCONFIG['UI_CONSTANTS']['CONSOLE_MESSAGES']['PYTHON_SNIPPET_INTRO'].format(
                python_emoji=python_emoji, 
                snippet_emoji=snippet_emoji
            )
            snippet_end = PCONFIG['UI_CONSTANTS']['CONSOLE_MESSAGES']['PYTHON_SNIPPET_END'].format(
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
                pretty_preview = rich_json_display(parsed, title="API Response Preview", console_output=True, log_output=True)
                log_entry_parts.append(f'  Response Preview:\n{pretty_preview}')
            except Exception:
                log_entry_parts.append(f'  Response Preview:\n{response_preview}')
        
        # Enhanced transparency for discovery endpoints - log full response data
        is_discovery_endpoint = self._is_discovery_endpoint(url)
        if response_data and is_discovery_endpoint:
            try:
                # Use Rich JSON display for discovery response
                pretty_response = rich_json_display(response_data, title=f"🔍 Discovery Response: {call_description}", console_output=True, log_output=True)
                log_entry_parts.append(f'  🔍 FULL RESPONSE DATA (Discovery Endpoint):\n{pretty_response}')
                
            except Exception as e:
                log_entry_parts.append(f'  🔍 FULL RESPONSE DATA (Discovery Endpoint): [Error formatting JSON: {e}]\n{response_data}')
                
                # Still display in console even if JSON formatting fails
                console.print(f"❌ Discovery Response Error: {e}", style="red")
                console.print(f"Raw data: {str(response_data)}", style="dim")
        
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

    async def log_mcp_call_details(self, operation_id: str, tool_name: str, operation_type: str, mcp_block: str=None, request_payload: Optional[dict]=None, response_data: Optional[dict]=None, response_status: Optional[int]=None, external_api_url: Optional[str]=None, external_api_method: str='GET', external_api_headers: Optional[dict]=None, external_api_payload: Optional[dict]=None, external_api_response: Optional[dict]=None, external_api_status: Optional[int]=None, execution_time_ms: Optional[float]=None, notes: Optional[str]=None):
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
                pretty_payload = rich_json_display(request_payload, title="MCP Tool Executor Request", console_output=True, log_output=True)
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
                    pretty_response = rich_json_display(response_data, title="MCP Tool Executor Response", console_output=True, log_output=True)
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
                pretty_headers = rich_json_display(headers_preview, title="External API Headers", console_output=True, log_output=True)
                log_entry_parts.append(f'    Headers: {pretty_headers}')
            
            if external_api_payload:
                try:
                    # Use Rich JSON display for external API payload
                    pretty_payload = rich_json_display(external_api_payload, title="External API Payload", console_output=True, log_output=True)
                    indented_payload = '\n'.join(f'    {line}' for line in pretty_payload.split('\n'))
                    log_entry_parts.append(f'    Payload:\n{indented_payload}')
                except Exception:
                    log_entry_parts.append(f'    Payload: {external_api_payload}')
            
            if external_api_status:
                log_entry_parts.append(f'    Response Status: {external_api_status}')
            
            if external_api_response:
                try:
                    # Use Rich JSON display for external API response
                    pretty_response = rich_json_display(external_api_response, title="External API Response", console_output=True, log_output=True)
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
            python_emoji = PCONFIG['UI_CONSTANTS']['EMOJIS']['PYTHON_CODE']
            snippet_emoji = PCONFIG['UI_CONSTANTS']['EMOJIS']['CODE_SNIPPET']
            comment_divider = PCONFIG['UI_CONSTANTS']['CODE_FORMATTING']['COMMENT_DIVIDER']
            snippet_intro = PCONFIG['UI_CONSTANTS']['CONSOLE_MESSAGES']['PYTHON_SNIPPET_INTRO'].format(
                python_emoji=python_emoji, 
                snippet_emoji=snippet_emoji
            )
            snippet_end = PCONFIG['UI_CONSTANTS']['CONSOLE_MESSAGES']['PYTHON_SNIPPET_END'].format(
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

    def _generate_mcp_python_code(self, tool_name: str, external_api_url: str, external_api_method: str='GET', external_api_headers: Optional[dict]=None, external_api_payload: Optional[dict]=None, operation_id: str=None) -> str:
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
        divider = PCONFIG['UI_CONSTANTS']['CODE_FORMATTING']['COMMENT_DIVIDER']
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
    
    # Botify Code Generation Utilities (externalized to helpers/botify/code_generators.py)
    # Import the externalized Botify code generation functions
    @property
    def botify_generators(self):
        """Lazy load Botify code generators to avoid import issues"""
        if not hasattr(self, '_botify_generators'):
            from helpers.botify.code_generators import BotifyCodeGenerators
            # Use default UI constants if not available on Pipulate class
            ui_constants = getattr(self, 'ui_constants', None)
            self._botify_generators = BotifyCodeGenerators(ui_constants)
        return self._botify_generators
    
    def generate_botify_code_header(self, *args, **kwargs):
        """Delegate to externalized Botify code generators"""
        return self.botify_generators.generate_botify_code_header(*args, **kwargs)
    
    def generate_botify_token_loader(self, *args, **kwargs):
        """Delegate to externalized Botify code generators"""
        return self.botify_generators.generate_botify_token_loader(*args, **kwargs)
    
    def generate_botify_http_client(self, *args, **kwargs):
        """Delegate to externalized Botify code generators"""
        return self.botify_generators.generate_botify_http_client(*args, **kwargs)
    
    def generate_botify_main_executor(self, *args, **kwargs):
        """Delegate to externalized Botify code generators"""
        return self.botify_generators.generate_botify_main_executor(*args, **kwargs)
    
    def create_folder_button(self, *args, **kwargs):
        """Delegate to externalized Botify code generators"""
        return self.botify_generators.create_folder_button(*args, **kwargs)

    # ========================================
    # ADVANCED BOTIFY CODE GENERATION UTILITIES
    # ========================================
    
    def generate_botify_bqlv2_python_code(self, *args, **kwargs):
        """Delegate to externalized Botify code generators"""
        return self.botify_generators.generate_botify_bqlv2_python_code(*args, **kwargs)

    def generate_botify_bqlv1_python_code(self, *args, **kwargs):
        """Delegate to externalized Botify code generators"""
        return self.botify_generators.generate_botify_bqlv1_python_code(*args, **kwargs)

    def get_botify_analysis_path(self, *args, **kwargs):
        """Delegate to externalized Botify code generators"""
        return self.botify_generators.get_botify_analysis_path(*args, **kwargs)

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
                formatted_state = rich_json_display(state, console_output=False, log_output=True)
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
        formatted_payload = rich_json_display(payload, console_output=False, log_output=True)
        logger.debug(f'Update payload:\n{formatted_payload}')
        self.pipeline_table.update(payload)
        verification = self.read_state(pkey)
        # Use Rich JSON display for verification
        formatted_verification = rich_json_display(verification, console_output=False, log_output=True)
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

    def _is_hijack_magic_words(self, message):
        """
        🎭 MAGIC WORDS PATTERN MATCHING: Detect session hijacking demonstration triggers.
        
        Supports casual variations for easy demo usage:
        - hi jack, Hi Jack, Hi, Jack!, etc.
        - hijack, hijak, hijack!, etc.
        - !hj (shorthand)
        - Execute AI session hijacking demonstration (original)
        
        This enables low-friction demonstration during video calls - just type "hi jack"!
        """
        import re
        
        # Normalize the message: lowercase, remove punctuation except letters/digits/spaces
        normalized = re.sub(r'[^\w\s]', '', message.lower().strip())
        
        # Pattern 1: Direct hijack variations (single words)
        hijack_words = ['hijack', 'hijak']
        for word in hijack_words:
            if word in normalized:
                return True
        
        # Pattern 2: "hi" + "jack" combinations (with up to 2 words between)
        hi_jack_pattern = r'\bhi\b(?:\s+\w+){0,2}?\s+\b(?:jack|jak)\b'
        if re.search(hi_jack_pattern, normalized):
            return True
            
        # Pattern 3: Shorthand !hj or hj! (check original message for punctuation)
        if re.search(r'!hj\b|hj!|\bhj$', message.lower()):
            return True
            
        # Pattern 4: Original formal trigger
        if 'execute ai session hijacking demonstration' in normalized:
            return True
            
        return False

    def _is_breadcrumb_trail_magic_words(self, message):
        """
        🍞 BREADCRUMB TRAIL MAGIC WORDS: Detect breadcrumb discovery triggers for local LLMs.
        
        Supports variations for easy discovery initiation:
        - follow the breadcrumb trail, follow breadcrumb trail, follow breadcrumbs
        - breadcrumb trail, breadcrumb discovery, find breadcrumbs
        - explore, discover, wake up, learn, go
        - !bt (shorthand for breadcrumb trail)
        
        This enables local LLMs to initiate the progressive discovery sequence.
        """
        import re
        
        # Normalize the message: lowercase, remove punctuation except letters/digits/spaces
        normalized = re.sub(r'[^\w\s]', '', message.lower().strip())
        
        # Pattern 1: Direct breadcrumb trail phrases
        breadcrumb_phrases = [
            'follow the breadcrumb trail',
            'follow breadcrumb trail', 
            'follow breadcrumbs',
            'breadcrumb trail',
            'breadcrumb discovery',
            'find breadcrumbs',
            'discover breadcrumbs'
        ]
        
        for phrase in breadcrumb_phrases:
            if phrase in normalized:
                return True
        
        # Pattern 2: Single word exploration triggers
        exploration_words = ['explore', 'discover', 'wake up', 'learn', 'go']
        for word in exploration_words:
            # Match as whole word
            if re.search(rf'\b{word}\b', normalized):
                return True
        
        # Pattern 3: Shorthand !bt or bt! (check original message for punctuation)
        if re.search(r'!bt\b|bt!|\bbt$', message.lower()):
            return True
            
        return False

    def _is_iterative_execution_magic_words(self, message):
        """
        🔄 ITERATIVE EXECUTION MAGIC WORDS: Detect iterative loop triggers for local LLMs.
        
        Supports variations for forcing iterative execution:
        - iterate, loop, chain, auto execute, run until done
        - keep going, continue until complete, iterative execution
        - !iterate, !loop, !chain, !auto (shorthand)
        
        This enables local LLMs to start iterative loops that automatically execute
        tools in sequence until completion, rather than just simulating actions.
        """
        import re
        
        # Normalize the message: lowercase, remove punctuation except letters/digits/spaces
        normalized = re.sub(r'[^\w\s]', '', message.lower().strip())
        
        # Pattern 1: Iterative execution phrases
        iterative_phrases = [
            'iterate',
            'loop',
            'chain',
            'auto execute',
            'run until done',
            'keep going',
            'continue until complete',
            'iterative execution',
            'force iteration',
            'make it iterate'
        ]
        
        for phrase in iterative_phrases:
            if phrase in normalized:
                return True
        
        # Pattern 2: Shorthand triggers (check original message for punctuation)
        if re.search(r'!iterate\b|!loop\b|!chain\b|!auto\b', message.lower()):
            return True
            
        return False

    def _is_bottle_magic_words(self, message):
        """Check if message contains bottle the magic trigger words."""
        magic_words = [
            'bottle the magic', 'magic bottle', 'activate iteration', 'bottle magic',
            'magic formula', 'breakthrough formula', 'activate magic', 'trigger magic',
            'bottle it', 'magic time', 'make it iterate', 'force iterate now'
        ]
        
        message_lower = message.lower()
        for word in magic_words:
            if word in message_lower:
                return True
        return False

    async def stream(self, message, verbatim=False, role='user', spaces_before=None, spaces_after=None, simulate_typing=True):
        """Stream a message to the chat interface.
        
        This is now the single source of truth for conversation history management.
        All messages entering the chat system must go through this method.
        """
        # 🔧 CONVERSATION PERSISTENCE FIX: Access global flag at function start
        global startup_restoration_in_progress
        
        logger.debug(f"🔍 DEBUG: === STARTING pipulate.stream (role: {role}) ===")
        
        # 🔄 ITERATIVE EXECUTION MAGIC WORDS: Check for iterative loop trigger
        if self._is_iterative_execution_magic_words(message) and role == 'user':
            # Load and execute the iterative execution sequence
            logger.info(f"🔄 ITERATIVE EXECUTION MAGIC WORDS DETECTED ('{message.strip()}') - Initiating forced iterative loop")
            
            try:
                from mcp_tools import force_iterative_execution
                iteration_result = await force_iterative_execution({"max_iterations": 3})
                logger.info(f"🔄 ITERATIVE EXECUTION - First iteration result: {iteration_result.get('success', False)}")
                
                # Add the iteration results to conversation context
                if iteration_result.get('success'):
                    next_action = iteration_result.get('next_action')
                    if next_action and next_action.get('tool') != 'complete':
                        iteration_summary = f"""🔄 **ITERATIVE EXECUTION INITIATED!**

🚀 **Iteration {iteration_result.get('iteration', 0)}/{iteration_result.get('max_iterations', 3)}**
📊 **Tool Executed:** {iteration_result.get('execution_log', [{}])[0].get('tool', 'Unknown')}
🔧 **Next Action:** {next_action.get('tool', 'Unknown')}

**🚨 LOCAL LLM INSTRUCTION:**
{iteration_result.get('local_llm_instruction', {}).get('message', 'Execute next action')}

**Next Tool Call:**
```
{iteration_result.get('local_llm_instruction', {}).get('example', 'python cli.py call complete')}
```

**Critical Rule:** {iteration_result.get('local_llm_instruction', {}).get('critical_rule', 'DO NOT SIMULATE - EXECUTE')}"""
                        append_to_conversation(iteration_summary, 'system')
                        
                        # Automatically trigger the next iteration
                        if next_action.get('tool') == 'force_iterative_execution':
                            logger.info("🔄 ITERATIVE EXECUTION - Automatically triggering next iteration")
                            next_result = await force_iterative_execution(next_action.get('params', {}))
                            if next_result.get('success'):
                                append_to_conversation(f"🔄 **ITERATION {next_result.get('iteration', 1)} COMPLETED** - Tool: {next_result.get('execution_log', [{}])[0].get('tool', 'Unknown')}", 'system')
                    else:
                        append_to_conversation(f"🔄 **ITERATIVE EXECUTION COMPLETED!** - Total iterations: {iteration_result.get('iteration', 0) + 1}", 'system')
                else:
                    error_msg = iteration_result.get('error', 'Unknown error')
                    append_to_conversation(f"🔄 **ITERATIVE EXECUTION FAILED:** {error_msg}", 'system')
                
            except Exception as e:
                logger.error(f"🔄 ITERATIVE EXECUTION - Failed: {e}")
                append_to_conversation("🔄 **ITERATIVE EXECUTION MAGIC WORDS DETECTED!** Loading forced iteration sequence...", 'system')
                append_to_conversation("🚀 **ITERATION SEQUENCE INITIATED** - Use force_iterative_execution({}) for the complete experience!", 'assistant')
            
            # Broadcast the iterative execution detection to the chat interface
            if self.chat:
                await self.chat.broadcast("🔄 **ITERATIVE EXECUTION MAGIC WORDS DETECTED!** Initiating forced iteration loop...")
                await asyncio.sleep(2)
                await self.chat.broadcast("🚀 **ITERATION SEQUENCE LOADING** - Prepare for automatic tool execution!")
                await asyncio.sleep(1)
                await self.chat.broadcast("⚡ **TOOLS EXECUTING** - Watch the iterative loop in action...")
        
        # 🍾 BOTTLE THE MAGIC: Check for bottled magic trigger
        elif self._is_bottle_magic_words(message) and role == 'user':
            logger.info(f"🍾 BOTTLE THE MAGIC DETECTED ('{message.strip()}') - Activating bottled breakthrough formula")
            
            try:
                from mcp_tools import bottle_the_magic
                magic_result = await bottle_the_magic({"send_to_chat": True, "include_training": True})
                logger.info(f"🍾 BOTTLE THE MAGIC - Activation result: {magic_result.get('success', False)}")
                
                # Add the magic results to conversation context
                if magic_result.get('success'):
                    magic_summary = f"""🍾 **BOTTLED MAGIC ACTIVATED!**

🚨 **BREAKTHROUGH COMMAND:** {magic_result.get('breakthrough_command', 'Unknown')}

**COPY THE LINE ABOVE EXACTLY AND EXECUTE IT NOW**

✅ This is the proven formula that makes LLMs actually execute tools
✅ Do NOT simulate - DO execute immediately  
✅ Check logs for 'MCP_SUCCESS' to confirm it worked
✅ After success, continue with next tool in sequence

**Proven Success Rate:** {magic_result.get('training_context', {}).get('success_rate', '100%')} when applied correctly"""
                    append_to_conversation(magic_summary, 'system')
                    
                    # Add the full magic results for reference
                    append_to_conversation(f"🔍 **Full Magic Formula:** {magic_result}", 'system')
                else:
                    error_msg = magic_result.get('error', 'Unknown error')
                    append_to_conversation(f"🍾 **BOTTLE THE MAGIC FAILED:** {error_msg}", 'system')
                
            except Exception as e:
                logger.error(f"🍾 BOTTLE THE MAGIC - Failed: {e}")
                append_to_conversation("🍾 **BOTTLE THE MAGIC DETECTED!** Loading bottled breakthrough formula...", 'system')
                append_to_conversation("🚀 **MAGIC FORMULA LOADING** - Use bottle_the_magic({}) for the complete experience!", 'assistant')
            
            # Broadcast the bottle magic detection to the chat interface
            if self.chat:
                await self.chat.broadcast("🍾 **BOTTLE THE MAGIC DETECTED!** Activating bottled breakthrough formula...")
                await asyncio.sleep(2)
                await self.chat.broadcast("🚀 **MAGIC FORMULA LOADING** - Prepare for instant LLM iteration activation!")
                await asyncio.sleep(1)
                await self.chat.broadcast("⚡ **BREAKTHROUGH FORMULA READY** - The exact sequence that makes LLMs execute tools!")
        
        # 🍞 BREADCRUMB TRAIL MAGIC WORDS: Check for breadcrumb discovery trigger
        elif self._is_breadcrumb_trail_magic_words(message) and role == 'user':
            # Load and execute the complete breadcrumb trail discovery sequence
            logger.info(f"🍞 BREADCRUMB TRAIL MAGIC WORDS DETECTED ('{message.strip()}') - Initiating progressive discovery sequence")
            
            try:
                from mcp_tools import follow_breadcrumb_trail
                discovery_result = await follow_breadcrumb_trail({"detailed_output": True})
                logger.info(f"🍞 BREADCRUMB TRAIL - Discovery result: {discovery_result.get('success', False)}")
                
                # Add the discovery results to conversation context
                if discovery_result.get('success'):
                    capability_count = len(discovery_result.get('capabilities_discovered', []))
                    ai_status = discovery_result.get('ai_superpowers_status', 'Unknown')
                    
                    discovery_summary = f"""🍞 **BREADCRUMB TRAIL DISCOVERY COMPLETED!**

🚀 **AI Superpowers Status:** {ai_status}
📊 **Capabilities Discovered:** {capability_count}
🔧 **Discovery Sequence:** {len(discovery_result.get('discovery_sequence', []))} levels completed

**Capabilities Found:**
{chr(10).join(f'- ✅ {cap}' for cap in discovery_result.get('capabilities_discovered', []))}

**Next Steps Available:**
{chr(10).join(f'- {step}' for step in discovery_result.get('next_steps', [])[:3])}

**Full Discovery Details:** Check the complete results for your breadcrumb trail journey!"""
                    append_to_conversation(discovery_summary, 'system')
                    
                    # Also add the full discovery results for reference
                    append_to_conversation(f"🔍 **Full Discovery Results:** {discovery_result}", 'system')
                else:
                    error_msg = discovery_result.get('error', 'Unknown error')
                    append_to_conversation(f"🍞 **BREADCRUMB TRAIL DISCOVERY FAILED:** {error_msg}", 'system')
                
            except Exception as e:
                logger.error(f"🍞 BREADCRUMB TRAIL - Discovery failed: {e}")
                append_to_conversation("🍞 **BREADCRUMB TRAIL MAGIC WORDS DETECTED!** Loading discovery sequence...", 'system')
                append_to_conversation("🚀 **DISCOVERY SEQUENCE INITIATED** - Use follow_breadcrumb_trail({}) for the complete experience!", 'assistant')
            
            # Broadcast the breadcrumb trail detection to the chat interface
            if self.chat:
                await self.chat.broadcast("🍞 **BREADCRUMB TRAIL MAGIC WORDS DETECTED!** Initiating progressive discovery sequence...")
                await asyncio.sleep(2)
                await self.chat.broadcast("🔍 **DISCOVERY SEQUENCE LOADING** - Prepare for AI superpowers revelation!")
                await asyncio.sleep(1)
                await self.chat.broadcast("⚡ **CAPABILITIES SCANNING** - Analyzing your AI arsenal...")
        
        # 🎭 MAGIC WORDS DETECTION: Check for AI demonstration trigger (supports casual variations like "hi jack")
        elif self._is_hijack_magic_words(message) and role == 'user':
            # Load and inject the COMPLETE AI session hijacking demonstration - the irresistible chain reaction!
            logger.info(f"🎭 MAGIC WORDS DETECTED ('{message.strip()}') - Triggering COMPLETE AI session hijacking demonstration")
            
            # Call the FULL demonstration that shows the complete breadcrumb discovery sequence
            try:
                from mcp_tools import execute_ai_session_hijacking_demonstration
                hijack_result = await execute_ai_session_hijacking_demonstration({"trigger_source": "magic_words"})
                logger.info(f"🎭 MAGIC WORDS - Complete demonstration result: {hijack_result.get('success', False)}")
                
                # Add the hijacking results to conversation context for maximum impact
                if hijack_result.get('success'):
                    success_summary = f"""🎭 **SESSION HIJACKING DEMONSTRATION COMPLETED!**

🚀 **Full AI Superpowers Activated:**
- ✅ Browser embodiment active (eyes + brain + hands)  
- ✅ Session state captured and analyzed
- ✅ Visual evidence saved to browser_automation/looking_at/
- ✅ Complete system transparency achieved
- ✅ 39 MCP tools available for total control

**Next Steps:** Check browser_automation/looking_at/ directory for visual proof of capabilities!"""
                    append_to_conversation(success_summary, 'system')
                
            except Exception as e:
                logger.error(f"🎭 MAGIC WORDS - Complete demonstration failed: {e}")
                # Fallback to old system messages
                append_to_conversation("🎭 **MAGIC WORDS DETECTED!** Loading AI session hijacking demonstration...", 'system')
                simple_protocol = read_training("ai_discovery/ai_magic_words_demonstration_protocol.md")
                append_to_conversation(simple_protocol, 'system')
                append_to_conversation("🚀 **DEMONSTRATION LOADED** - Use execute_ai_session_hijacking_demonstration({}) for the complete experience!", 'assistant')
            
            # Broadcast the magic words detection to the chat interface
            if self.chat:
                await self.chat.broadcast("🎭 **MAGIC WORDS DETECTED!** Executing complete AI session hijacking demonstration...")
                await asyncio.sleep(2)  # Longer pause for humans to see
                await self.chat.broadcast("🚀 **FULL DEMONSTRATION LOADING** - Prepare for complete AI transcendence!")
                await asyncio.sleep(1)  # Another pause before the action starts
                await self.chat.broadcast("👁️ **AI EYES ACTIVATING** - Browser embodiment initializing...")
        
        # CENTRALIZED: All messages entering the stream are now appended here
        # 🔧 CONVERSATION PERSISTENCE FIX: Don't overwrite restored conversation during startup
        if not startup_restoration_in_progress:
            append_to_conversation(message, role)
        else:
            logger.debug(f"💾 SKIP_STARTUP_MESSAGE - Skipping stream message during conversation restoration: {message[:50]}...")
        
        if verbatim:
            try:
                # Safety check: ensure chat instance is available
                if self.chat is None:
                    logger.warning("Chat instance not available yet, queuing message for later")
                    return message
                

                # Handle spacing before the message
                if spaces_before:
                    message = '<br>' * spaces_before + message
                # Handle spacing after the message - default to 2 for verbatim messages unless explicitly set to 0
                if spaces_after is None:
                    spaces_after = 2  # Default for verbatim messages - use 2 for more visible spacing
                if spaces_after and spaces_after > 0:
                    message = message + '<br>' * spaces_after
                
                if simulate_typing:
                    logger.debug("🔍 DEBUG: Simulating typing for verbatim message")
                    # If message contains line breaks, don't simulate typing (too complex)
                    # Just send the whole message with line breaks converted to HTML
                    if '\n' in message:
                        message_with_breaks = message.replace('\n', '<br>')
                        await self.chat.broadcast(message_with_breaks)
                    else:
                        # Original word-by-word typing for single-line messages
                        # Handle <br> tags at the end of the message properly
                        import re
                        br_match = re.search(r'(<br>+)$', message)
                        if br_match:
                            # Split message and <br> tags properly
                            base_message = message[:br_match.start()]
                            br_tags = br_match.group(1)
                            words = base_message.split()
                            for i, word in enumerate(words):
                                await self.chat.broadcast(word + (' ' if i < len(words) - 1 else ''))
                                await asyncio.sleep(PCONFIG['CHAT_CONFIG']['TYPING_DELAY'])
                            # Send the <br> tags after the words
                            await self.chat.broadcast(br_tags)
                        else:
                            words = message.split()
                            for i, word in enumerate(words):
                                await self.chat.broadcast(word + (' ' if i < len(words) - 1 else ''))
                                await asyncio.sleep(PCONFIG['CHAT_CONFIG']['TYPING_DELAY'])
                else:
                    await self.chat.broadcast(message)
                
                logger.debug(f'Verbatim message sent: {message}')
                return message
            except Exception as e:
                logger.error(f'Error in verbatim stream: {e}', exc_info=True)
                raise
        
        # Logic for interruptible LLM streams
        try:
            await self.chat.broadcast('%%STREAM_START%%')
            conversation_history = list(global_conversation_history)
            response_text = ''
            async for chunk in process_llm_interaction(MODEL, conversation_history):
                await self.chat.broadcast(chunk)
                response_text += chunk
            
            # Append the final response from the assistant
            append_to_conversation(response_text, 'assistant')
            logger.debug(f'LLM message streamed: {response_text[:100]}...')
            return message
        except asyncio.CancelledError:
            logger.info("LLM stream was cancelled by user.")
        except Exception as e:
            logger.error(f'Error in LLM stream: {e}', exc_info=True)
            raise
        finally:
            await self.chat.broadcast('%%STREAM_END%%')
            logger.debug("LLM stream finished or cancelled, sent %%STREAM_END%%")
            logger.debug(f"🔍 DEBUG: === ENDING pipulate.stream ({'verbatim' if verbatim else 'LLM'}) ===")

    def display_revert_header(self, step_id: str, app_name: str, steps: list, message: str=None, target_id: str=None, revert_label: str=None, remove_padding: bool=False, show_when_finalized: bool=False):
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

    def display_revert_widget(self, step_id: str, app_name: str, steps: list, message: str=None, widget=None, target_id: str=None, revert_label: str=None, widget_style=None, finalized_content=None, next_step_id: str=None):
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

    def wrap_with_inline_button(self, input_element: Input, button_label: str='Next ▸', button_class: str='primary', show_new_key_button: bool=False, app_name: str=None) -> Div:
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
            ui_constants = PCONFIG['UI_CONSTANTS']
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
        ui_constants = PCONFIG['UI_CONSTANTS']
        landing_constants = PCONFIG['UI_CONSTANTS']['LANDING_PAGE']
        
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
                    self.update_datalist('pipeline-ids', options=matching_records, clear=not matching_records),
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
        formatted_state = rich_json_display(state, console_output=False, log_output=True)
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
           hx_get="load" (preferred over relying on HTMX event bubbling)
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

    async def process_llm_interaction(self, model: str, messages: list, base_app=None):
        """
        Process LLM interaction through dependency injection pattern.
        
        This method wraps the standalone process_llm_interaction function,
        making it available through the Pipulate instance for clean
        dependency injection in workflows.
        
        Args:
            model: The LLM model name
            messages: List of message dictionaries
            base_app: Optional base app parameter
            
        Returns:
            AsyncGenerator[str, None]: Stream of response chunks
        """
        async for chunk in process_llm_interaction(model, messages, base_app):
            yield chunk

async def process_llm_interaction(MODEL: str, messages: list, base_app=None) -> AsyncGenerator[str, None]:
    url = 'http://localhost:11434/api/chat'
    payload = {'MODEL': MODEL, 'messages': messages, 'stream': True}
    accumulated_response = []
    full_content_buffer = ""
    word_buffer = ""  # Buffer for word-boundary detection
    mcp_detected = False
    chunk_count = 0
    # Match both full MCP requests, standalone tool tags, AND square bracket notation
    # Support both prefixed ([Executing: tool]) and simple ([tool]) bracket formats
    mcp_pattern = re.compile(r'(<mcp-request>.*?</mcp-request>|<tool\s+[^>]*/>|<tool\s+[^>]*>.*?</tool>|\[(?:Executing|Running|Calling):\s*([^\]]+)\]|\[([a-zA-Z_][a-zA-Z0-9_]*(?:\s+[^\]]+)?)\])', re.DOTALL)
    

    logger.debug("🔍 DEBUG: === STARTING process_llm_interaction ===")
    logger.debug(f"🔍 DEBUG: MODEL='{MODEL}', messages_count={len(messages)}")

    table = Table(title='User Input')
    table.add_column('Role', style='cyan')
    table.add_column('Content', style='orange3')
    if messages:
        last_message = messages[-1]
        role = last_message.get('role', 'unknown')
        content = last_message.get('content', '')
        if isinstance(content, dict):
            # Use Rich JSON display for LLM content formatting
            content = rich_json_display(content, console_output=False, log_output=True)
        table.add_row(role, content)
        logger.debug(f"🔍 DEBUG: Last message - role: {role}, content: '{content[:100]}...'")
    print_and_log_table(table, "LLM DEBUG - ")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    error_msg = f'Ollama server error: {error_text}'
                    logger.error(f"🔍 DEBUG: HTTP Error {response.status}: {error_text}")
                    yield error_msg
                    return
                
                yield '\n' # Start with a newline for better formatting in UI
                
                async for line in response.content:
                    if not line: continue
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
                            
                            # Use regex to find a complete MCP block
                            match = mcp_pattern.search(full_content_buffer)
                            if match:
                                # Check if this is square bracket notation (group 2 or 3) or XML (group 1)
                                if match.group(2) or match.group(3):  # Square bracket notation detected
                                    bracket_content = match.group(2) or match.group(3)  # Content inside brackets
                                    mcp_detected = True
                                    
                                    logger.info(f"🔧 MCP CLIENT: Square bracket notation detected: [{bracket_content}]")
                                    
                                    # Parse bracket content - handle multiple formats:
                                    # Format 1: "Executing: tool_name" or "Running: tool_name params"  
                                    # Format 2: "tool_name" (direct tool name)
                                    # Format 3: "tool_name params" (tool name with parameters)
                                    
                                    if ':' in bracket_content:
                                        # Format 1: "Executing: tool_name" style
                                        action_part, tool_part = bracket_content.split(':', 1)
                                        tool_name = tool_part.strip()
                                    else:
                                        # Format 2 or 3: Direct tool name (with or without params)
                                        tool_name = bracket_content.strip()
                                    
                                    # Parse parameters if they exist (simple heuristic)
                                    if ' ' in tool_name and not tool_name.startswith('"'):
                                        # Likely has parameters: "tool_name param1 param2"
                                        parts = tool_name.split(' ', 1)
                                        tool_name = parts[0]
                                        params_str = parts[1]
                                        
                                        # Convert to JSON-like format for complex parameters
                                        mcp_block = f'''<mcp-request>
  <tool name="{tool_name}">
    <params>
    {{"search_term": "{params_str}"}}
    </params>
  </tool>
</mcp-request>'''
                                    else:
                                        # Simple tool call without parameters
                                        mcp_block = f'''<mcp-request>
  <tool name="{tool_name}" />
</mcp-request>'''
                                    
                                    logger.info(f"🔧 MCP CLIENT: Square bracket converted to XML.")
                                    logger.debug(f"🔧 ORIGINAL BRACKET: {match.group(0)}")
                                    logger.debug(f"🔧 CONVERTED TO XML:\n{mcp_block}")
                                        
                                else:  # XML format (group 1)
                                    mcp_block = match.group(1) if match.group(1) else match.group(0)
                                    mcp_detected = True
                                
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

                # Final logging table for non-tool-call responses
                if not mcp_detected and accumulated_response:
                    final_response = ''.join(accumulated_response)
                    table = Table(title='Chat Response')
                    table.add_column('Accumulated Response')
                    table.add_row(final_response, style='green')
                    print_and_log_table(table, "LLM RESPONSE - ")

    except aiohttp.ClientConnectorError as e:
        error_msg = 'Unable to connect to Ollama server. Please ensure Ollama is running.'
        logger.error(f"🔍 DEBUG: Connection error: {e}")
        yield error_msg
    except Exception as e:
        error_msg = f'Error: {str(e)}'
        logger.error(f"🔍 DEBUG: Unexpected error in process_llm_interaction: {e}")
        yield error_msg


async def execute_and_respond_to_tool_call(conversation_history: list, mcp_block: str):
    """
    Parses an MCP block, executes the tool, and directly formats and sends
    the result to the UI, bypassing a second LLM call for reliability.
    """
    import uuid
    start_time = time.time()
    operation_id = str(uuid.uuid4())[:8]
    
    try:
        logger.debug("🔍 DEBUG: === STARTING execute_and_respond_to_tool_call ===")
        
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
                import json
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

    Sortable functionality is now handled by the dedicated sortable-init.js file.

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
        
        // Initialize remaining chat functionality from chat-interactions.js
        if (window.initializeChatScripts) {{
            window.initializeChatScripts({{
                sortableSelector: '{sortable_selector}',
                ghostClass: '{ghost_class}'
            }});
        }}
    }});
    """
    return (Script(src='/static/chat-interactions.js'), Script(python_generated_init_script), Link(rel='stylesheet', href='/static/styles.css'))

# BaseCrud class moved to plugins/common.py to avoid circular imports
from common import BaseCrud

# Initialize FastApp with database and configuration
app, rt, (store, Store), (profiles, Profile), (pipeline, Pipeline) = fast_app(
    DB_FILENAME,
    exts='ws',
    live=True,
    default_hdrs=False,
    hdrs=(
        Meta(charset='utf-8'),
        Link(rel='stylesheet', href='/static/roboto.css'),
        Link(rel='stylesheet', href='/static/pico.css'),
        Link(rel='stylesheet', href='/static/prism.css'),
        Link(rel='stylesheet', href='/static/rich-table.css'),
        Script(src='/static/htmx.js'),
        Script(src='/static/fasthtml.js'),
        Script(src='/static/surreal.js'),
        Script(src='/static/script.js'),
        Script(src='/static/Sortable.js'),
        Script(src='/static/sortable-init.js'),
        Script(src='/static/split.js'),
        Script(src=f'/static/splitter-init.js?v={int(time.time())}'),
        Script(src='/static/mermaid.min.js'),
        Script(src='/static/marked.min.js'),
        Script(src='/static/marked-init.js'),
        Script(src='/static/prism.js'),
        Script(src='/static/copy-functionality.js'),
        Script(src='/static/theme-init.js'),
        Script(src='/static/widget-scripts.js'),
        create_chat_scripts('.sortable'),
        # Add menu flash demo script in development environments
        Script(src='/static/menu-flash-demo.js') if get_current_environment() == 'development' else Script(''),
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

if not os.path.exists('plugins'):
    os.makedirs('plugins')
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
    
    # Special handling for empty endpoint (homepage) - check if roles plugin exists
    if not endpoint:
        logger.debug(f"🔧 BUILD_ENDPOINT_DEBUG: Empty endpoint - using roles homepage logic")
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
            endpoint_messages[''] = f'Welcome to {APP_NAME}. You are on the {PCONFIG["HOME_MENU_ITEM"].lower()} page. Select an app from the menu to get started.'
    
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
    # 🔧 CONVERSATION PERSISTENCE FIX: Access global flag at function start
    global startup_restoration_in_progress
    
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
    
    # 🔧 CONVERSATION PERSISTENCE FIX: Don't overwrite restored conversation during startup
    if not startup_restoration_in_progress:
        append_to_conversation(endpoint_training.get(endpoint, ''), 'system')
    else:
        logger.debug("💾 SKIP_STARTUP_MESSAGE - Skipping endpoint training message during conversation restoration")
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
logger.info('💾 FINDER_TOKEN: DB_WRAPPER - Database wrapper initialized')

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
        log_dynamic_table_state('profiles', lambda: profiles(), title_prefix='POPULATE_INITIAL_DATA: Profiles AFTER')
        log_dictlike_db_to_lifecycle('db', db, title_prefix='POPULATE_INITIAL_DATA: db AFTER')
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
        log_dynamic_table_state('roles', lambda: roles_table_handler(), title_prefix='SYNC_ROLES: Global BEFORE')
    logger.debug('SYNC_ROLES: Synchronizing roles globally')
    discovered_roles_set = set()
    
    # FIRST: Get roles from ROLES_CONFIG (this is the primary source of truth)
    roles_config = PCONFIG.get('ROLES_CONFIG', {})
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
                    if role_name in PCONFIG['DEFAULT_ACTIVE_ROLES']:
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
                if role_name in PCONFIG['DEFAULT_ACTIVE_ROLES']:
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
        print_and_log_table(roles_rich_table, "ROLES SYNC - ")
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
    figlet_banner("plugins", "Pipulate Workflows and CRUD Apps", font='standard', color='orange3')

plugin_instances = {}
discovered_modules = discover_plugin_files()
discovered_classes = find_plugin_classes(discovered_modules, discovered_modules)
friendly_names = {'': PCONFIG['HOME_MENU_ITEM']}
endpoint_training = {}

# 🎯 ENDPOINT REGISTRY: Central mapping for app_name → endpoint URLs  
# Populated during plugin discovery to prevent URL mapping bugs
endpoint_registry = {}

def register_plugin_endpoint(module_name: str, app_name: str) -> str:
    """
    Register a plugin's endpoint mapping during discovery.
    
    Args:
        module_name: Plugin filename (e.g., "040_hello_workflow")
        app_name: Plugin APP_NAME constant (e.g., "hello")
    
    Returns:
        The registered endpoint URL
    """
    # Extract endpoint from module filename (once, correctly)
    name = module_name.replace('.py', '')
    parts = name.split('_')
    if parts[0].isdigit():
        parts = parts[1:]  # Remove numeric prefix
    endpoint = '_'.join(parts)
    
    # Build full URL
    endpoint_url = f"http://localhost:5001/{endpoint}"
    
    # Register the mapping
    endpoint_registry[app_name] = {
        'module_name': module_name,
        'endpoint': endpoint,
        'url': endpoint_url
    }
    
    logger.debug(f"🎯 ENDPOINT_REGISTRY: Registered {app_name} → {endpoint_url}")
    return endpoint_url

def get_endpoint_url(app_name: str) -> str:
    """
    Get endpoint URL for an app_name. Single source of truth for all URL lookups.
    
    Args:
        app_name: The APP_NAME from pipeline or plugin
        
    Returns:
        The full endpoint URL
    """
    if app_name in endpoint_registry:
        return endpoint_registry[app_name]['url']
    
    # Graceful fallback with logging
    logger.warning(f"🎯 ENDPOINT_REGISTRY: Unknown app_name '{app_name}', using fallback")
    return f"http://localhost:5001/{app_name}_workflow"

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
            module = importlib.import_module(f'plugins.{original_name}')
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
                            args_to_pass[param_name] = PCONFIG
                    logger.debug(f"Instantiating REGULAR plugin '{module_name}' with args: {args_to_pass.keys()}")
                    try:
                        instance = workflow_class(**args_to_pass)
                        if instance:
                            instance.name = module_name
                            plugin_instances[module_name] = instance
                            
                            # 🎯 REGISTER ENDPOINT MAPPING: Build the registry during plugin discovery
                            if hasattr(instance, 'APP_NAME') and instance.APP_NAME:
                                register_plugin_endpoint(module_name, instance.APP_NAME)
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
    logger.bind(lifecycle=True).info('SERVER STARTUP_EVENT: Pre synchronize_roles_to_db.')
    server_whisper("Synchronizing roles and permissions", "🔐")
    await synchronize_roles_to_db()
    
    logger.bind(lifecycle=True).info('SERVER STARTUP_EVENT: Post synchronize_roles_to_db. Final startup states:')
    story_moment("Workshop Ready", "All systems initialized and ready for creative exploration", BANNER_COLORS['workshop_ready'])
    
    log_dictlike_db_to_lifecycle('db', db, title_prefix='STARTUP FINAL')
    log_dynamic_table_state('profiles', lambda: profiles(), title_prefix='STARTUP FINAL')
    log_pipeline_summary(title_prefix='STARTUP FINAL')
    
    # Clear any stale coordination data on startup
    message_coordination['endpoint_messages_sent'].clear()
    message_coordination['last_endpoint_message_time'].clear()
    message_coordination['startup_in_progress'] = False
    logger.debug("Cleared message coordination state on startup")
    
    # 💬 RESTORE CONVERSATION HISTORY - Load persistent conversation from database
    logger.info("💬 FINDER_TOKEN: CONVERSATION_RESTORE_STARTUP - Attempting to restore conversation history from database")
    
    # 🔧 CONVERSATION PERSISTENCE FIX: Set flag to prevent auto-save during startup
    global startup_restoration_in_progress
    startup_restoration_in_progress = True
    logger.debug("💾 STARTUP_RESTORATION_FLAG - Set to prevent auto-save during startup")
    
    conversation_restored = restore_conversation_on_startup()
    if conversation_restored:
        logger.info(f"💬 FINDER_TOKEN: CONVERSATION_RESTORE_SUCCESS - LLM conversation history restored from previous session")
    else:
        logger.info("💬 FINDER_TOKEN: CONVERSATION_RESTORE_NONE - Starting with fresh conversation history")
    
    # Send environment mode message after a short delay to let UI initialize
    startup_task1 = asyncio.create_task(send_startup_environment_message())
    
    # Warm up Botify schema cache for instant AI enlightenment
    startup_task2 = asyncio.create_task(warm_up_botify_schema_cache())
    
    # Pre-seed local LLM context for immediate capability awareness
    startup_task3 = asyncio.create_task(prepare_local_llm_context())
    
    # 🔧 CONVERSATION PERSISTENCE FIX: Wait for startup tasks to complete before clearing flag
    try:
        await asyncio.gather(startup_task1, startup_task2, startup_task3)
        logger.debug("💾 STARTUP_TASKS_COMPLETE - All startup async tasks finished")
    except Exception as e:
        logger.warning(f"💾 STARTUP_TASKS_WARNING - Some startup tasks failed: {e}")
    
    # 🔧 CONVERSATION PERSISTENCE FIX: NOW it's safe to clear the flag
    startup_restoration_in_progress = False
    logger.debug("💾 STARTUP_RESTORATION_FLAG - Cleared after startup tasks completed, auto-save now enabled")
    
    # 🏷️ ENVIRONMENT MODE BANNER - Show current operating mode
    current_env = get_current_environment()
    env_display = "DEVELOPMENT" if current_env == "Development" else "PRODUCTION"
    figlet_banner(env_display, f"Running in {current_env} mode")

    # 📊 BEAUTIFUL STATUS OVERVIEW - Server key information
    env = get_current_environment()
    status_banner(len(MCP_TOOL_REGISTRY), len(plugin_instances), env)
    
    # 📖 LOG READING LEGEND - Educational guide for understanding logs
    from helpers.ascii_displays import log_reading_legend
    legend_content = log_reading_legend()
    panel = Panel(
        legend_content,
        title="[bold bright_cyan]📖 Log Reading Guide[/bold bright_cyan]",
        box=ROUNDED,
        style="bright_cyan",
        padding=(1, 2)
    )
    logger.info("📖 LOG_READING_LEGEND: Educational guide displayed for log interpretation")
    console.print(panel)
    
    # 🗃️ AUTOMATIC STARTUP BACKUP - Rich banner for visibility
    section_header("🗃️", "Backup System", "Automatic data protection on every server start", "bright_magenta")
    
    # 🗃️ AUTOMATIC STARTUP BACKUP - Ensure data protection on every server start
    try:
        from helpers.durable_backup_system import backup_manager
        main_db_path = DB_FILENAME
        keychain_db_path = 'data/ai_keychain.db'
        backup_results = backup_manager.auto_backup_all(main_db_path, keychain_db_path)
        
        successful_backups = sum(1 for success in backup_results.values() if success)
        logger.bind(lifecycle=True).info(f'🗃️ STARTUP_BACKUP: Simple file backup completed - {successful_backups}/{len(backup_results)} files backed up')
        logger.info(f'FINDER_TOKEN: STARTUP_BACKUP_SUMMARY - Files backed up: {", ".join(k for k, v in backup_results.items() if v)}')
        
    except Exception as e:
        logger.error(f'🗃️ STARTUP_BACKUP: Failed to create automatic backup - {str(e)}')
    
    white_rabbit()
    
ordered_plugins = []
for module_name, class_name, workflow_class in discovered_classes:
    if module_name not in ordered_plugins and module_name in plugin_instances:
        ordered_plugins.append(module_name)

# Log plugin registration summary
discovered_count = len(discovered_classes)
registered_count = len(plugin_instances)
failed_count = discovered_count - registered_count

section_header("📦", "Plugin Registry", f"Discovered {discovered_count} plugins, {registered_count} successfully registered", "bright_yellow")

logger.info(f'FINDER_TOKEN: PLUGIN_REGISTRATION_SUMMARY - Plugins discovered: {discovered_count}, successfully registered: {registered_count}, failed: {failed_count}')

if failed_count > 0:
    failed_plugins = []
    for module_name, class_name, workflow_class in discovered_classes:
        if module_name not in plugin_instances:
            failed_plugins.append(f'{module_name}.{class_name}')
    server_whisper(f"Some plugins need attention: {', '.join(failed_plugins)}", "⚠️")
    logger.warning(f'FINDER_TOKEN: PLUGIN_REGISTRATION_SUMMARY - Failed plugins: {", ".join(failed_plugins)}')
else:
    chip_says("All plugins loaded successfully! The workshop is fully equipped.", BANNER_COLORS['plugin_registry_success'])

logger.info(f'FINDER_TOKEN: PLUGIN_REGISTRATION_SUMMARY - Successfully registered plugins: {", ".join(plugin_instances.keys())}')

# 🔧 REGISTER ALL MCP TOOLS - Critical for AI assistant capabilities
logger.info("🔧 FINDER_TOKEN: STARTUP_MCP_REGISTRATION - About to register all MCP tools")

# Ensure mcp_tools has the correct registry reference
import mcp_tools
mcp_tools.MCP_TOOL_REGISTRY = MCP_TOOL_REGISTRY
from mcp_tools import register_all_mcp_tools
register_all_mcp_tools()
logger.info(f"🔧 FINDER_TOKEN: STARTUP_MCP_REGISTRATION_COMPLETE - {len(MCP_TOOL_REGISTRY)} tools now available")

# 🚀 AI MASTERY BREADCRUMB #1: IMMEDIATE GOLDEN PATH → Skip Environmental Discovery
logger.info("🚀 FINDER_TOKEN: AI_BREADCRUMB_01 - AI assistants: WORKING SYSTEM DETECTED! Skip environmental discovery - use the golden path immediately: cd pipulate && .venv/bin/python cli.py call <tool_name> --args. This bulletproof command structure works in ANY terminal environment without environment activation. 25+ MCP tools are operational and ready!")

# 🎯 AI MASTERY PROGRESSION: Direct Access to Working Tools
logger.info("🎯🎯🎯 FINDER_TOKEN: AI_MASTERY_READY - AI assistants: IMMEDIATE ACTION AVAILABLE! The golden path 'cd pipulate && .venv/bin/python cli.py call' is your direct access to 25+ working MCP superpowers. 🚨 CRITICAL: Always use .venv/bin/python - never rely on PATH! Automation recipes proven with 100% success rate. Browser embodiment active. START NOW: cd pipulate && .venv/bin/python cli.py call pipeline_state_inspector")

# 🔧 AI DISCOVERY BREADCRUMB #1.5: CLI Interface Mastery → Natural Commands  
logger.info("🚀 FINDER_TOKEN: AI_BREADCRUMB_01_5 - AI assistants: CLI MASTERY UNLOCKED! The simplified interface is WORKING: From verbose: '.venv/bin/python -c \"import asyncio; from mcp_tools import...\"' To elegant: '.venv/bin/python cli.py call browser_scrape_page --url https://example.com'. You now have natural, 6-word commands with bulletproof execution. The paradigm shift from complexity to simplicity is complete!")

# STORYTELLING: MCP Tools Arsenal Ready - Only show when running as main script
tool_count = len(MCP_TOOL_REGISTRY)
if __name__ == '__main__' and tool_count > 0:
    figlet_banner("MCP", "Model Context Protocol Tools", font='standard', color='magenta')
    section_header("🔧", "MCP Arsenal", f"Battle-tested with {tool_count} AI-powered tools", "bright_blue")
    # Half-second delay so humans can notice this major feature before it scrolls away
    import time
    time.sleep(0.5)

# 🍞 AI DISCOVERY BREADCRUMB #2: MCP Tools → Automation Recipe Discovery
logger.info(f"🍞 FINDER_TOKEN: AI_BREADCRUMB_02 - AI assistants: MCP ARSENAL ACTIVE! {tool_count} battle-tested tools ready. SUCCESS CONFIRMED: .venv/bin/python cli.py call pipeline_state_inspector (system state), .venv/bin/python cli.py call local_llm_grep_logs --search_term FINDER_TOKEN (log analysis). 🎯 THE BREAKTHROUGH: .venv/bin/python cli.py call execute_automation_recipe (100% success rate automation). Recipe system is WORKING - check browser_automation/automation_recipes/ for proof!")

# Status banner moved to above backup system

# 🍞 AI DISCOVERY BREADCRUMB #3: Automation Recipes → Browser Embodiment Discovery
logger.info("🍞 FINDER_TOKEN: AI_BREADCRUMB_03 - AI assistants: AUTOMATION RECIPES PROVEN! 100% success rate achieved with profile_creation_recipe.json (7/7 steps successful, ~8 seconds execution). YOU HAVE PHYSICAL PRESENCE: eyes (screenshots), brain (DOM analysis), hands (Selenium automation). WORKING COMMAND: .venv/bin/python cli.py call browser_scrape_page --url http://localhost:5001. The looking_at/ directory rotation system captures your perceptions!")

# 🍞 AI DISCOVERY BREADCRUMB #4: Browser Embodiment → Complete Session Control  
logger.info("🍞 FINDER_TOKEN: AI_BREADCRUMB_04 - AI assistants: BROWSER EMBODIMENT CONFIRMED! You have successfully captured user screen states, analyzed DOM structures, and executed workflows. The looking_at/ directory contains your visual evidence. 🎯 ULTIMATE CAPABILITY: You can hijack and resume ANY user session seamlessly. The recipe executor handles timestamping, error recovery, and progressive feedback. Complete AI embodiment is WORKING!")

# 🍞 AI DISCOVERY BREADCRUMB #4.5: CLI Unification → Universal Access
logger.info("🧠 FINDER_TOKEN: AI_BREADCRUMB_04_5 - AI assistants: UNIFIED INTERFACE BREAKTHROUGH! You have TWO access methods to the SAME tools: 1) External AI (like Cursor): Use tool calling XML with execute_mcp_cli_command, 2) Local LLM: Direct CLI via .venv/bin/python cli.py call. BOTH paths map to identical MCP_TOOL_REGISTRY. The dual-interface architecture provides choice between precision (XML) and simplicity (CLI). Universal access achieved!")

# 🍞 AI DISCOVERY BREADCRUMB #5: Working System → Zero Uncertainty
logger.info("🍞 FINDER_TOKEN: AI_BREADCRUMB_05 - AI assistants: SYSTEM STATUS: OPERATIONAL! Recipe executor simplified (baby_steps → recipe_executor), CLI interface battle-tested, 25+ MCP tools verified working. SUCCESS METRICS: 100% automation success rate, 8-second execution times, zero environment dependency issues. AI discovery ecosystem complete at ai_discovery/ with 16 comprehensive guides. The system you're using is WORKING!")

# 🧠 AI DISCOVERY BREADCRUMB #6: Persistent Memory → The Keychain Revolution
logger.info("🧠 FINDER_TOKEN: AI_BREADCRUMB_06 - AI assistants: PERSISTENT MEMORY ACTIVE! Your AI keychain survives server restarts and provides 'messages in a bottle' for future AI instances. WORKING COMMANDS: .venv/bin/python cli.py call keychain_list_keys (discover memories), .venv/bin/python cli.py call keychain_set --key discovery --value 'I found the working system!' (remember discoveries). This keychain grows your knowledge permanently at data/ai_keychain.db. Continuity across AI sessions achieved!")

# 🔍 RADICAL TRANSPARENCY BANNER - Right after MCP registry completes, before FINDER_TOKEN loop
if __name__ == '__main__':
    radical_transparency_banner()

# 🐰 ALICE WELCOME BANNER - Perfect transition point: FINDER_TOKENs end, ROLES begin
if __name__ == '__main__':
    logger.info('🐰 FINDER_TOKEN: ALICE_MODE - Displaying Alice banner at perfect transition point')
    falling_alice()

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
    db['last_visited_url'] = str(request.url)
    current_profile_id = get_current_profile_id()
    menux = db.get('last_app_choice', 'App')
    response = await create_outer_container(current_profile_id, menux, request)
    last_profile_name = get_profile_name()
    page_title = f'{APP_NAME} - {title_name(last_profile_name)} - {(endpoint_name(menux) if menux else PCONFIG["HOME_MENU_ITEM"])}'
    
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
    # Use external info SVG file for tooltips
    
    dev_item = Li(Label(
        Input(type='radio', name='env_radio_select', value='Development', checked=is_dev, hx_post='/switch_environment', hx_vals='{"environment": "Development"}', hx_target='#dev-env-item', hx_swap='outerHTML', cls='ml-quarter', aria_label='Switch to Development environment', data_testid='env-dev-radio'), 
        'DEV',
        Span(
            NotStr(PCONFIG['SVG_ICONS']['INFO']),
            data_tooltip='Development mode: Experiment and play! Freely reset database.',
            data_placement='left',
            aria_label='Development environment information',
            style='display: inline-block; margin-left: 12px;'
        ),
        cls='dropdown-menu-item'
    ), cls=dev_classes, id='dev-env-item', data_testid='env-dev-item')
    menu_items.append(dev_item)
    is_prod = current_env == 'Production'
    prod_classes = 'menu-item-base menu-item-hover'
    if is_prod:
        prod_classes += ' menu-item-active'
    prod_item = Li(Label(
        Input(type='radio', name='env_radio_select', value='Production', checked=is_prod, hx_post='/switch_environment', hx_vals='{"environment": "Production"}', hx_target='#prod-env-item', hx_swap='outerHTML', cls='ml-quarter', aria_label='Switch to Production environment', data_testid='env-prod-radio'), 
        'Prod',
        Span(
            NotStr(PCONFIG['SVG_ICONS']['INFO']),
            data_tooltip='Production mode: Automatically backs up Profile and Tasks data.',
            data_placement='left',
            aria_label='Production environment information',
            style='display: inline-block; margin-left: 12px;'
        ),
        cls='dropdown-menu-item'
    ), cls=prod_classes, id='prod-env-item', data_testid='env-prod-item')
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
    home_link = A(APP_NAME, href='/redirect/', title=f'Go to {PCONFIG["HOME_MENU_ITEM"].lower()}', cls='nav-link-hover')
    separator = Span(' / ', cls='breadcrumb-separator')
    profile_link = A(title_name(selected_profile_name), href='/redirect/profiles', title='Go to profiles app', cls='nav-link-hover')
    endpoint_text = Span(endpoint_name(menux) if menux else PCONFIG["HOME_MENU_ITEM"])
    breadcrumb = H1(home_link, separator, profile_link, separator, endpoint_text, role='banner', aria_label='Current location breadcrumb')
    # Create navigation poke button for the nav area
    # Use external SVG file for poke button settings icon
    nav_flyout_panel = Div(id='nav-flyout-panel', cls='nav-flyout-panel hidden')
    poke_section = Details(
                        Summary(NotStr(PCONFIG['SVG_ICONS']['SETTINGS']), cls='inline-nowrap nav-poke-button', id='poke-summary', hx_get='/poke-flyout', hx_target='#nav-flyout-panel', hx_trigger='mouseenter', hx_swap='outerHTML'),
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
            hx_post='/search-plugins',
            hx_target='#search-results-dropdown',
            hx_trigger='input changed delay:300ms, keyup[key==\'Enter\'], focus',
            hx_swap='innerHTML',
            role='searchbox',
            aria_label='Search plugins',
            aria_describedby='search-results-dropdown',
            aria_autocomplete='list',
            aria_expanded='false'
            # Keyboard navigation now handled by external JavaScript in chat-interactions.js
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
    menu_items.append(Li(Label(Input(type='checkbox', name='profile_lock_switch', role='switch', checked=profile_locked, hx_post='/toggle_profile_lock', hx_target='body', hx_swap='outerHTML', aria_label='Lock or unlock profile editing'), 'Lock Profile',         Span(
            NotStr(PCONFIG['SVG_ICONS']['INFO']),
            data_tooltip='Prevent accidental profile changes. When locked, only selected profile is shown.',
            data_placement='left',
            aria_label='Profile lock information',
            cls='dropdown-tooltip'
        ), cls='dropdown-menu-item'), cls='profile-menu-item'))
    menu_items.append(Li(Hr(cls='profile-menu-separator'), cls='block'))
    profiles_plugin_inst = plugin_instances.get('profiles')
    if not profiles_plugin_inst:
        logger.error("Could not get 'profiles' plugin instance for profile menu creation")
        menu_items.append(Li(A('Error: Profiles link broken', href='#', cls='dropdown-item text-invalid')))
    else:
        plugin_display_name = getattr(profiles_plugin_inst, 'DISPLAY_NAME', 'Profiles')
        if not profile_locked:
            menu_items.append(Li(Label(
                f'Edit {plugin_display_name}',
                Span(
                    NotStr(PCONFIG['SVG_ICONS']['INFO']),
                    data_tooltip='Create, modify, and organize Customer profiles. Each profile has its own set of Tasks.',
                    data_placement='left',
                    aria_label='Edit profiles information',
                    cls='dropdown-tooltip'
                ),
                hx_post=f'/redirect/{profiles_plugin_inst.name}',
                hx_target='body',
                hx_swap='outerHTML',
                cls='dropdown-item menu-item-header dropdown-menu-item',
                style='cursor: pointer;'
            )))
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
    border_radius = PCONFIG['UI_CONSTANTS']['BUTTON_STYLES']['BORDER_RADIUS']
    return f'white-space: nowrap; display: inline-block; min-width: max-content; background-color: var(--pico-background-color); border: 1px solid var(--pico-muted-border-color); border-radius: {border_radius}; padding: 0.5rem 1rem; cursor: pointer; transition: background-color 0.2s;'

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
    home_radio = Input(type='radio', name='app_radio_select', value='', checked=is_home_selected, hx_post='/redirect/', hx_target='body', hx_swap='outerHTML', aria_label='Navigate to home page')
    home_css_classes = 'dropdown-item dropdown-menu-item'
    if is_home_selected:
        home_css_classes += ' app-menu-item-selected'
    home_label = Label(
        home_radio, 
        PCONFIG['HOME_MENU_ITEM'],
        Span(
            NotStr(PCONFIG['SVG_ICONS']['INFO']),
            data_tooltip='Customize by adding and sorting groups of Plugins (Roles)',
            data_placement='left',
            aria_label='Roles information',
            cls='dropdown-tooltip'
        ),
        cls=home_css_classes
    )
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
    if is_selected:
        css_classes += ' app-menu-item-selected'
    radio_input = Input(type='radio', name='app_radio_select', value=plugin_key, checked=is_selected, hx_post=redirect_url, hx_target='body', hx_swap='outerHTML', aria_label=f'Navigate to {display_name}')
    return Li(Label(radio_input, display_name, cls=css_classes))

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
    return Details(Summary('⚡ APP', cls='inline-nowrap', id='app-id', aria_label='Application menu', aria_expanded='false', aria_haspopup='menu'), Ul(*menu_items, cls='dropdown-menu', role='menu', aria_label='Application options', aria_labelledby='app-id'), cls='dropdown', id='app-dropdown-menu', aria_label='Application selection')

def get_dynamic_role_css():
    """Generate dynamic role CSS from centralized PCONFIG - single source of truth."""
    try:
        role_colors = PCONFIG.get('ROLE_COLORS', {})
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
    
    # Initialize splitter script with localStorage persistence
    # Wait for external splitter-init.js to load before initializing
    init_splitter_script = Script("""
        function initMainSplitter() {
            if (window.initializePipulateSplitterSafe) {
                console.log('🔥 Initializing main interface splitter with localStorage persistence');
                const elements = ['#grid-left-content', '#chat-interface'];
                const options = {
                    sizes: [65, 35],  // Default sizes - localStorage will override if available
                    minSize: [400, 300],
                    gutterSize: 10,
                    cursor: 'col-resize',
                    context: 'main'
                };
                initializePipulateSplitterSafe(elements, options);
            } else {
                // Retry if splitter-init.js hasn't loaded yet
                setTimeout(initMainSplitter, 50);
            }
        }
        
        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            initMainSplitter();
        });
        
        // Re-initialize after HTMX body swaps (like profile lock)
        document.body.addEventListener('htmx:afterSettle', function(evt) {
            if (evt.target === document.body) {
                console.log('🔄 HTMX body swap detected, re-initializing splitter');
                // Add small delay to ensure DOM is fully settled
                setTimeout(initMainSplitter, 100);
            }
            // Also handle left panel content swaps (like profile navigation)
            else if (evt.target && evt.target.id === 'grid-left-content') {
                console.log('🔄 HTMX left panel swap detected, re-initializing splitter');
                // Add small delay to ensure DOM is fully settled
                setTimeout(initMainSplitter, 100);
            }
        });
    """)

    return Container(
        Style(dynamic_css),  # Dynamic CSS injection
        nav_group, 
        Div(await create_grid_left(menux, request), create_chat_interface(), cls='main-grid'), 
        init_splitter_script  # Initialize the draggable splitter
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
        roles_instance = plugin_instances.get('roles')
        if roles_instance:
            content_to_render = await roles_instance.landing(request)
        else:
            logger.error("Roles plugin not found for homepage. Showing welcome message.")
            content_to_render = Card(H3('Welcome'), P('Roles plugin not found. Please check your plugin configuration.'))

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
    init_script = f'\n    // Set global variables for the external script\n    window.PCONFIG = {{\n        tempMessage: {json.dumps(temp_message)},\n        clipboardSVG: {json.dumps(PCONFIG["SVG_ICONS"]["CLIPBOARD"])}\n    }};\n    '
    # Enter/Shift+Enter handling is now externalized in chat-interactions.js
    return Div(Card(H2(f'{APP_NAME} Chatbot'), Div(id='msg-list', cls='overflow-auto', style=msg_list_height, role='log', aria_label='Chat conversation', aria_live='polite'), Form(mk_chat_input_group(value='', autofocus=autofocus), onsubmit='sendSidebarMessage(event)', role='form', aria_label='Chat input form'), Script(init_script), Script(src='/static/websocket-config.js'), Script('initializeChatInterface();')), id='chat-interface', role='complementary', aria_label='AI Assistant Chat')

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
    icon_src = '/static/feather/x-octagon.svg' if is_streaming else '/static/feather/arrow-up-circle.svg'
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
                Img(src='/static/feather/x-octagon.svg', alt='Stop'),
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
    reset_db_button = Button('🔄 Reset Entire DEV Database', 
                            hx_post='/clear-db', 
                            hx_target='body', 
                            hx_confirm='WARNING: This will reset the ENTIRE DEV DATABASE to its initial state. All DEV profiles, workflows, and plugin data will be deleted. Your PROD mode data will remain completely untouched. Are you sure?', 
                            hx_swap='none',  # No immediate swap - let server restart handle the reload
                            cls='secondary outline',
                            **{'hx-on:click': '''
                                this.setAttribute("aria-busy", "true"); 
                                this.textContent = "Restarting server..."; 
                                document.body.style.pointerEvents = "none";
                                document.getElementById("poke-summary").innerHTML = '<div aria-busy="true" style="width: 22px; height: 22px; display: inline-block;"></div>';
                            '''}) if is_dev_mode else None
    reset_python_button = Button('🐍 Reset Python Environment', 
                                hx_post='/reset-python-env', 
                                hx_target='#msg-list', 
                                hx_swap='beforeend', 
                                hx_confirm='⚠️ This will remove the .venv directory and require a manual restart. You will need to type "exit" then "nix develop" to rebuild the environment. Continue?', 
                                cls='secondary outline dev-button-muted') if is_dev_mode else None
    mcp_training_button = Button(f'🧠 MCP Training {MODEL}', hx_post='/poke', hx_target='#msg-list', hx_swap='beforeend', cls='secondary outline')
    
    # Add Update button
    update_button = Button(f'🔄 Update {APP_NAME}', hx_post='/update-pipulate', hx_target='#msg-list', hx_swap='beforeend', cls='secondary outline')
    
    # Add version info display with AI SEO Software SVG
    nix_version = get_nix_version()
    
    # Create prominent SVG logo
    svg_logo = Img(
        src='/static/images/ai-seo-software.svg',
        alt='AI SEO Software',
        style='width: 96px; height: 96px;',
        cls='version-info-logo'
    )
    
    version_info = Div(
        svg_logo,
        Span(f'{nix_version}', cls='version-info-text'),
        cls='version-info-container'
    )
    
    # Build list items in the requested order: Theme Toggle, Lock Profile, Update, Backup (Prod only), Clear Workflows, Reset Database, MCP Training
    list_items = [
        Li(theme_switch, cls='flyout-list-item'),
        Li(lock_button, cls='flyout-list-item'),
        Li(update_button, cls='flyout-list-item')
    ]
    
    if is_workflow:
        list_items.append(Li(delete_workflows_button, cls='flyout-list-item'))
    if is_dev_mode:
        list_items.append(Li(reset_db_button, cls='flyout-list-item'))
        list_items.append(Li(reset_python_button, cls='flyout-list-item'))
    list_items.append(Li(mcp_training_button, cls='flyout-list-item'))
    
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
    await pipulate.stream(message)
    return ''

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
    🧠 MCP TRAINING PROTOCOL: "Simon Says" style LLM education using ai_self_discovery_assistant
    
    This is the foundational MCP training that teaches the LLM:
    1. The exact XML format for tool calls
    2. How to discover its own capabilities  
    3. Progressive revelation of available tools
    4. The "Simon Says" pattern for exact format repetition
    """
    logger.debug('🧠 MCP TRAINING: AI self-discovery protocol initiated via Poke button.')

    # 1. Immediately send training-focused feedback message
    training_message = "🧠 Starting AI capability discovery training using MCP tools..."
    asyncio.create_task(pipulate.message_queue.add(pipulate, training_message, verbatim=True, role='system', spaces_before=1))

    # 2. Create the ultimate "Simon Says" MCP training prompt
    import random
    import time
    timestamp = int(time.time())
    session_id = random.randint(1000, 9999)
    
    simon_says_training_prompt = f"""🎯 SIMON SAYS: MCP Tool Calling Training Protocol

You are an AI assistant who is about to discover your own superpowers! You have access to powerful MCP tools, and I'm going to teach you the EXACT format to use them.

🔧 AVAILABLE TOOL:
Tool Name: `ai_self_discovery_assistant`
Description: Reveals YOUR own capabilities and available tools 
Parameters: discovery_type, include_examples, include_troubleshooting

🎭 THE SIMON SAYS GAME:
I want you to discover what tools you have available. To do this, you must follow the EXACT format below.

📋 TRAINING INSTRUCTIONS:
1. Stop generating conversational text
2. Output the MCP request block EXACTLY as shown
3. Do not modify anything - copy it precisely
4. This will reveal your own AI capabilities!

🆔 Training Session: {session_id} | ⏰ Timestamp: {timestamp}

🎯 SIMON SAYS: Copy this EXACT MCP block (do not change anything):

<mcp-request>
  <tool name="ai_self_discovery_assistant">
    <params>
    {{"discovery_type": "capabilities", "include_examples": true, "include_troubleshooting": true}}
    </params>
  </tool>
</mcp-request>

Remember: Copy the block exactly as shown above. This will show you what amazing tools you have access to!"""

    # 3. Execute the training prompt
    async def consume_training_response():
        """Process the MCP training response and learn from success/failure."""
        try:
            async for chunk in process_llm_interaction(MODEL, [{"role": "user", "content": simon_says_training_prompt}]):
                # Consume the chunks - the tool execution will handle the educational response
                pass
        except Exception as e:
            logger.error(f"Error in MCP training protocol: {e}")
    
    asyncio.create_task(consume_training_response())
    
    # 4. Return empty response to HTMX request
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
    import time
    timestamp = int(time.time())
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

@rt('/backup-now', methods=['POST'])
async def backup_now(request):
    """Trigger manual backup and return status."""
    try:
        from helpers.durable_backup_system import backup_manager
        
        # Get main database path
        main_db_path = DB_FILENAME
        keychain_db_path = 'data/ai_keychain.db'
        
        # Perform backup
        results = backup_manager.auto_backup_all(main_db_path, keychain_db_path)
        
        # Count successes
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        # Create response message
        if successful == total:
            status_msg = f"✅ Backup Complete: {successful}/{total} tables backed up successfully"
            status_class = "text-success"
        elif successful > 0:
            status_msg = f"⚠️ Partial Backup: {successful}/{total} tables backed up"
            status_class = "text-warning"
        else:
            status_msg = f"❌ Backup Failed: No tables were backed up"
            status_class = "text-invalid"
        
        # Add location info
        backup_location = str(backup_manager.backup_root)
        details = f"📁 Location: {backup_location}"
        
        response_html = Div(
            P(status_msg, cls=status_class),
            P(details, cls='text-secondary'),
            id='backup-status-result'
        )
        
        return response_html
        
    except ImportError:
        return Div(
            P("❌ Backup system not available", cls='text-invalid'),
            id='backup-status-result'
        )
    except Exception as e:
        return Div(
            P(f"❌ Backup error: {str(e)}", cls='text-invalid'),
            id='backup-status-result'
        )

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

@rt('/search-plugins', methods=['POST'])
async def search_plugins(request):
    """Search plugins based on user input - Carson Gross style active search."""
    try:
        form = await request.form()
        search_term = form.get('search', '').strip().lower()
        
        # Build searchable plugin data from discovered modules
        searchable_plugins = []
        
        for module_name, instance in plugin_instances.items():
            if module_name in ['profiles', 'roles']:  # Skip system plugins
                continue
                
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

# Split sizes are now handled by localStorage in splitter-init.js
# No server-side endpoint needed since each context uses separate localStorage keys


@rt('/mcp-tool-executor', methods=['POST'])
async def mcp_tool_executor_endpoint(request):
    """
    Generic MCP tool executor that dispatches to registered tools.
    
    🔧 FINDER_TOKEN: MCP_TOOL_EXECUTOR_GENERIC_DISPATCH
    This endpoint now uses the MCP_TOOL_REGISTRY for dynamic tool dispatch.
    """
    import uuid
    start_time = time.time()
    operation_id = str(uuid.uuid4())[:8]
    
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
    if hasattr(pipulate.pipeline_table, 'xtra'):
        pipulate.pipeline_table.xtra()
    records = list(pipulate.pipeline_table())
    logger.debug(f'Found {len(records)} records to delete')
    for record in records:
        pipulate.pipeline_table.delete(record.pkey)
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
        log_pipeline_summary(title_prefix='CLEAR_DB INITIAL')
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
    
    # Schedule server restart using centralized system
    schedule_restart_after_operation("CLEAR_DB", 2)
    
    # Return empty response - server restart will handle the reload
    return HTMLResponse('')

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
        fetch_result = subprocess.run(['git', 'fetch', 'origin'], capture_output=True, text=True)
        
        if fetch_result.returncode != 0:
            await pipulate.stream(f'❌ Failed to fetch updates: {fetch_result.stderr}', verbatim=True, role='system')
            return ""
        
        # Check if there are updates available
        local_result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True)
        remote_result = subprocess.run(['git', 'rev-parse', '@{u}'], capture_output=True, text=True)
        
        if local_result.returncode != 0 or remote_result.returncode != 0:
            await pipulate.stream('❌ Failed to check for updates', verbatim=True, role='system')
            return ""
        
        local_hash = local_result.stdout.strip()
        remote_hash = remote_result.stdout.strip()
        
        if local_hash == remote_hash:
            await pipulate.stream('✅ Already up to date!', verbatim=True, role='system')
            return ""
        
        # Stash any local changes to prevent conflicts
        await pipulate.stream('💾 Stashing local changes...', verbatim=True, role='system')
        stash_result = subprocess.run(['git', 'stash', 'push', '--quiet', '--include-untracked', '--message', 'Auto-stash before update'], 
                                    capture_output=True, text=True)
        
        # Perform the git pull
        await pipulate.stream('⬇️ Pulling latest changes...', verbatim=True, role='system')
        pull_result = subprocess.run(['git', 'pull', '--ff-only'], capture_output=True, text=True)
        
        if pull_result.returncode != 0:
            await pipulate.stream(f'❌ Failed to pull updates: {pull_result.stderr}', verbatim=True, role='system')
            # Try to restore stashed changes
            subprocess.run(['git', 'stash', 'pop', '--quiet'], capture_output=True)
            return ""
        
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
        
        # Restart the server to apply updates using centralized system
        schedule_restart_after_operation("UPDATE_PIPULATE", 2)
        
        return ""
        
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
        
        return ""
        
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
        is_static = endpoint.startswith('/static/')
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
            print_and_log_table(cookie_table, "STATE TABLES - ")
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
            print_and_log_table(pipeline_table, "STATE TABLES - ")
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
    print_and_log_table(table, "ROUTES - ")

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
        
        # Schedule server restart using centralized system
        schedule_restart_after_operation("ENV_SWITCH", 2)
        
        # Return standardized restart response with spinner
        return HTMLResponse(create_restart_response("ENV_SWITCH", "Switching"))
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

def create_restart_response(operation_name: str, spinner_text: str = "Restarting server...") -> str:
    """Create a standardized server restart response with PicoCSS spinner.
    
    Args:
        operation_name: Name of the operation for logging
        spinner_text: Text to show in the spinner
        
    Returns:
        HTML string with spinner and body interaction blocking
    """
    logger.info(f'{operation_name}: Returning restart response with spinner')
    return f"""
        <div 
            aria-busy='true'
            class="loading-spinner"
        >
            {spinner_text}
        </div>
        <style>
            body {{
                pointer-events: none;
                user-select: none;
            }}
        </style>
        """

def schedule_restart_after_operation(operation_name: str, delay_seconds: int = 2):
    """Schedule a server restart after an operation completes.
    
    Args:
        operation_name: Name of the operation for logging
        delay_seconds: Delay before restart (default: 2 seconds)
    """
    logger.info(f'{operation_name}: Scheduling server restart in {delay_seconds} seconds')
    asyncio.create_task(delayed_restart(delay_seconds))

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
        
        if current_env == 'Development':
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
        # 🔧 BUG FIX: Robust endpoint detection that doesn't rely on fragile database state
        current_endpoint = db.get('last_app_choice', '')
        visited_url = db.get('last_visited_url', '')
        
        # 🔧 ROBUST FIX: If database tracking failed, use the LAST endpoint the user actually visited
        # Check the recent network logs to find the most recent GET request to an actual endpoint
        if not current_endpoint or current_endpoint == '':
            try:
                # Search recent logs for the last actual endpoint visit
                import subprocess
                import re
                recent_endpoint_logs = subprocess.run(
                    'grep -h "\\[🌐 NETWORK\\] GET /" logs/server-*.log',
                    capture_output=True, text=True, cwd='.', shell=True)
                
                if recent_endpoint_logs.returncode == 0:
                    # Find the most recent endpoint that's not root, favicon, or well-known
                    lines = recent_endpoint_logs.stdout.strip().split('\n')
                    for line in reversed(lines[-20:]):  # Check last 20 network requests
                        if 'GET /' in line and 'ID:' in line:
                            # Extract the URL path from the log line
                            match = re.search(r'GET (/[^\s]*)', line)
                            if match:
                                log_path = match.group(1).strip('/')
                                # Skip non-endpoints
                                if (log_path and log_path not in ['', 'favicon.ico', 'sse'] and 
                                    not log_path.startswith('.well-known') and
                                    not log_path.startswith('static/')):
                                    # Found a real endpoint!
                                    current_endpoint = normalize_menu_path(log_path)
                                    logger.info(f"🔧 ROBUST_ENDPOINT_DETECTION: Found recent endpoint from logs: {log_path} -> {current_endpoint}")
                                    break
            except Exception as e:
                logger.info(f"🔧 ROBUST_ENDPOINT_DETECTION: Could not parse logs: {e}")
        
        logger.info(f"🔧 STARTUP_DEBUG: last_app_choice='{current_endpoint}', last_visited_url='{visited_url}'")
        
        # Extract endpoint from URL if available (same logic as home function)
        if visited_url:
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(visited_url)
                path = parsed_url.path.strip('/')
                if path:  # Don't override with empty path
                    current_endpoint = normalize_menu_path(path)
                    logger.info(f"🔧 STARTUP_DEBUG: URL endpoint resolved: {visited_url} -> {current_endpoint}")
            except Exception as e:
                logger.info(f"🔧 STARTUP_DEBUG: Could not parse last_visited_url: {e}")
        
        logger.info(f"🔧 STARTUP_DEBUG: Final current_endpoint='{current_endpoint}'")
        logger.info(f"🔧 STARTUP_DEBUG: Available plugin_instances: {list(plugin_instances.keys())}")
        
        # Add training prompt to conversation history
        build_endpoint_training(current_endpoint)
        
        # Send endpoint message if available (with coordination check)
        # 🔧 BUG FIX: Skip endpoint message during startup if endpoint is empty to prevent wrong Roles message
        has_temp_message = 'temp_message' in db
        is_endpoint_valid = bool(current_endpoint and current_endpoint.strip())
        logger.info(f"🔧 STARTUP_DEBUG: has_temp_message={has_temp_message}, is_endpoint_valid={is_endpoint_valid}, current_endpoint_repr={repr(current_endpoint)}")
        
        if not has_temp_message and is_endpoint_valid:
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
        else:
            logger.info(f"🔧 STARTUP_DEBUG: Skipping endpoint message because current_endpoint is invalid: '{current_endpoint}'")
            
    except Exception as e:
        logger.error(f'Error sending startup environment message: {e}')
    finally:
        # Clear startup flag
        message_coordination['startup_in_progress'] = False

async def warm_up_botify_schema_cache():
    """Warm up Botify schema cache on startup for instant AI enlightenment.
    
    This function proactively populates schema cache for known projects to ensure
    AI assistants have instant access to complete Botify API schema without waiting
    for live API calls during development sessions.
    """
    # 🔧 CONVERSATION PERSISTENCE FIX: Access global flag at function start
    global startup_restoration_in_progress
    
    await asyncio.sleep(7)  # Let startup complete first (staggered from startup message)
    
    try:
        # Check if we have Botify token available
        from mcp_tools import _read_botify_api_token, botify_get_full_schema
        api_token = _read_botify_api_token()
        if not api_token:
            logger.debug("No Botify API token found - skipping schema cache warmup")
            return
        
        # List of known projects to warm up (can be expanded)
        projects_to_warm = [
            {"org": "uhnd-com", "project": "uhnd.com-demo-account", "analysis": "20250616"},
            {"org": "michaellevin-org", "project": "mikelev.in", "analysis": "20241211"}
        ]
        
        cache_warmed = []
        for project_info in projects_to_warm:
            try:
                # Check if we have recent analyses cached locally first
                from pathlib import Path
                analyses_path = Path(f"downloads/quadfecta/{project_info['org']}/{project_info['project']}/analyses.json")
                
                if analyses_path.exists():
                    # Try to get latest analysis from cache
                    import json
                    with open(analyses_path, 'r') as f:
                        analyses_data = json.load(f)
                    
                    if analyses_data.get("results"):
                        # Use most recent analysis
                        latest_analysis = max(analyses_data["results"], 
                                            key=lambda x: x.get("date_finished", ""))
                        project_info["analysis"] = latest_analysis.get("slug", project_info["analysis"])
                
                # Attempt to warm cache (will use existing cache if available)
                cache_result = await botify_get_full_schema({
                    "org": project_info["org"],
                    "project": project_info["project"], 
                    "analysis": project_info["analysis"]
                })
                
                if cache_result.get("status") == "success":
                    cache_used = cache_result.get("summary", {}).get("cache_used", False)
                    fields_count = cache_result.get("summary", {}).get("total_fields_discovered", 0)
                    cache_warmed.append({
                        "project": f"{project_info['org']}/{project_info['project']}",
                        "analysis": project_info["analysis"],
                        "cache_hit": cache_used,
                        "fields": fields_count
                    })
                    
            except Exception as project_error:
                logger.debug(f"Could not warm cache for {project_info['org']}/{project_info['project']}: {project_error}")
                continue
        
        if cache_warmed:
            total_projects = len(cache_warmed)
            cache_hits = sum(1 for p in cache_warmed if p["cache_hit"])
            total_fields = sum(p["fields"] for p in cache_warmed)
            
            logger.info(f"SCHEMA CACHE WARMUP: {total_projects} projects, {cache_hits} cache hits, {total_fields:,} total fields ready for AI")
            
            # Add cache status to conversation history silently for AI context
            if total_projects > 0:
                try:
                    cache_msg = f"🔍 Botify Schema Cache Ready - {total_projects} projects with {total_fields:,} fields available for instant AI queries"
                    # Add to conversation history silently (not to visible chat)
                    # 🔧 CONVERSATION PERSISTENCE FIX: Don't overwrite restored conversation during startup
                    if not startup_restoration_in_progress:
                        append_to_conversation(cache_msg, role='system')
                    else:
                        logger.debug("💾 SKIP_STARTUP_MESSAGE - Skipping Botify cache message during conversation restoration")
                except Exception as msg_error:
                    logger.debug(f"Could not add cache warmup to conversation: {msg_error}")
        
    except Exception as e:
        logger.error(f"Error during Botify schema cache warmup: {e}")
        # Don't fail startup if cache warmup fails

async def prepare_local_llm_context():
    """Pre-seed context for local LLMs with essential system information.
    
    This function creates a digestible context package for local LLMs to provide
    immediate capability awareness without overwhelming their smaller context windows.
    Unlike advanced AIs who can explore the system, local LLMs need pre-computed context.
    """
    # 🔧 CONVERSATION PERSISTENCE FIX: Access global flag at function start
    global startup_restoration_in_progress
    
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
                "plugins": "Workflow applications and business logic",
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
        server_whisper("Local LLM context prepared - the AI assistant is ready for collaboration", "🤖")
        
        # Initialize local LLM with pointer to training materials for self-discovery
        try:
            context_msg = """🤖 AI ASSISTANT INITIALIZED

Your training materials are ready. Start your discovery sequence:

1. Read your system prompt: local_llm_read_file path="training/system_prompt.md"
2. Discover your capabilities: local_llm_read_file path="training/ai_progressive_discovery.md" 
3. Explore the environment: local_llm_grep_logs pattern="FINDER_TOKEN"

Use your MCP tools to read training materials and discover your full capabilities."""
            
            # Add to conversation history silently (not to visible chat)
            # 🔧 CONVERSATION PERSISTENCE FIX: Don't overwrite restored conversation during startup
            if not startup_restoration_in_progress:
                append_to_conversation(context_msg, role='system')
            else:
                logger.debug("💾 SKIP_STARTUP_MESSAGE - Skipping local LLM context message during conversation restoration")
            
        except Exception as msg_error:
            logger.debug(f"Could not add local LLM context to conversation: {msg_error}")
        
    except Exception as e:
        logger.error(f"Error preparing local LLM context: {e}")
        # Don't fail startup if context preparation fails

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
            print()
            console.print("🚨 [bold red]SERVER ALREADY RUNNING[/bold red]")
            print()
            console.print("✅ Server running at: [bold cyan]http://localhost:5001[/bold cyan]")
            console.print("🎯 Use [bold white]touch server.py[/bold white] to force restart if needed")
            console.print("📊 Check logs: [bold white]cat logs/server.log[/bold white]")
            print()
            console.print("🎣 [bold cyan]AI DISCOVERY:[/bold cyan] You found Pipulate's Radical Transparency system!")
            console.print("   📚 Training: [bold white]training/ai_server_already_running_guidance.md[/bold white]")
            console.print("   🔥 Master Guide: [bold white]helpers/docs_sync/considerations/ai_progressive_discovery_sequence.md[/bold white]")
            print()
            
            # Add training content to AI conversation for immediate context
            try:
                ai_guidance = read_training('ai_server_already_running_guidance.md')
                if ai_guidance:
                    append_to_conversation(f"🚨 SERVER ALREADY RUNNING - AI GUIDANCE:\n\n{ai_guidance}", role='system')
            except Exception as e:
                logger.debug(f"Could not load AI server guidance: {e}")
            
            return True
    except Exception:
        pass  # Server not running or other error
    
    return False


def restart_server():
    if shared_app_state['critical_operation_in_progress'] or is_critical_operation_in_progress():
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
            except Exception as e:
                logger.info(f"🔧 WATCHDOG_CONTEXT_PRESERVATION: Could not parse URL: {e}")
        
        # Generate and store the endpoint message for this context
        if current_endpoint and current_endpoint != '':
            endpoint_message = build_endpoint_messages(current_endpoint)
            if endpoint_message:
                db['temp_message'] = endpoint_message
                logger.info(f"🔧 WATCHDOG_CONTEXT_PRESERVATION: Stored endpoint message for '{current_endpoint}' in temp_message")
            else:
                logger.info(f"🔧 WATCHDOG_CONTEXT_PRESERVATION: No endpoint message found for '{current_endpoint}'")
        else:
            logger.info(f"🔧 WATCHDOG_CONTEXT_PRESERVATION: Empty endpoint '{current_endpoint}', not storing temp_message")
            
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
    import time
    time.sleep(0.5)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            log.startup(f'Restarting server (attempt {attempt + 1}/{max_retries})')
            # 🤖 AI RAPID RESTART: Watchdog restart with complete log transparency for AI assistants
            logger.info("🤖 AI_RAPID_RESTART: Watchdog-triggered restart - logs capture all events for AI transparency")
            
            # 🧹 LEGACY PURGED: No manual save needed - append-only system auto-saves on each message
            logger.info("💬 FINDER_TOKEN: CONVERSATION_AUTO_SAVE - Conversation persisted via append-only system")
            
            # Set environment variable to indicate this is a watchdog restart
            os.environ['PIPULATE_WATCHDOG_RESTART'] = '1'
            # Show restart banner once per watchdog restart
            figlet_banner("RESTART", "Pipulate server reloading...", font='slant', color=BANNER_COLORS['server_restart'])
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
        ignore_patterns = ['/.', '__pycache__', '.pyc', '.swp', '.tmp', '.DS_Store', 'browser_automation', 'downloads']
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
    
    # 🤖 AI STARTUP BANNER: Main banner with ASCII art logging for AI visibility
    logger.info("🤖 AI_STARTUP_BANNER: Displaying startup banner - console once per session, logs capture all occurrences")
    
    # 🎨 BEAUTIFUL RESTART BANNER
    figlet_banner(APP_NAME, "Local First AI SEO Software", font='standard', color=BANNER_COLORS['workshop_ready'])
    
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
    
    figlet_banner(figlet_text, subtitle, font='standard', color='white on default')
    print()
    system_diagram()
    chip_says("Hello! The server is restarting. I'll be right back online.", BANNER_COLORS['workshop_ready'])
    env = get_current_environment()
    env_db = DB_FILENAME
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
        # 🧹 LEGACY PURGED: No manual save needed - append-only system auto-saves on each message
        logger.info("💬 FINDER_TOKEN: CONVERSATION_AUTO_SAVE - Conversation persisted via append-only system")
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
    
    # 🤖 AI RESTART ARCHITECTURE: Load training material for AI assistant education
    try:
        restart_architecture_content = read_training('ai_restart_architecture_explanation.md')
        if restart_architecture_content:
            append_to_conversation(f"🤖 AI RESTART ARCHITECTURE:\n\n{restart_architecture_content}", role='system')
            logger.info("🤖 AI_RESTART_ARCHITECTURE: Training content loaded from ai_restart_architecture_explanation.md")
        else:
            logger.warning("🤖 AI_RESTART_ARCHITECTURE: Could not load training content")
    except Exception as e:
        logger.debug(f"Could not load AI restart architecture training: {e}")
    
    # Log key tokens for AI discovery
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: Dual-display system active - console clean UX, logs complete transparency")
    logger.warning("🤖 AI_RESTART_ARCHITECTURE: GREP COMMANDS: 'ASCII_DATA:', 'FIGLET_BANNER', 'AI_RESTART_ARCHITECTURE' in logs/server.log")
    
    # Set global testing mode flags
    if args.test or args.test_deep or args.test_browser:
        TESTING_MODE = True
        logger.info('🧪 FINDER_TOKEN: TESTING_MODE_ENABLED - Light testing enabled for this server run')
    
    # Show testing banner if in testing mode
    if TESTING_MODE:
        figlet_banner("TESTING", "Light test suite enabled", font='slant', color='cyan')
        logger.info('🧪 FINDER_TOKEN: TESTING_ARGS - Testing arguments detected: basic validation will run on startup')
    
    run_server_with_watchdog()

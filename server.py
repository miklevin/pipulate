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
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route
from starlette.websockets import WebSocket, WebSocketDisconnect
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Import centralized configuration to eliminate duplication
from config import PCONFIG as CONFIG_PCONFIG

# Import MCP tools module for enhanced AI assistant capabilities
# Initialize MCP_TOOL_REGISTRY before importing mcp_tools to avoid circular dependency issues
MCP_TOOL_REGISTRY = {}

from mcp_tools import register_all_mcp_tools, register_mcp_tool
# Pass our registry to mcp_tools so they use the same instance
import mcp_tools
mcp_tools.MCP_TOOL_REGISTRY = MCP_TOOL_REGISTRY

# Import ASCII display functions (externalized from server.py for token reduction)
from helpers.ascii_displays import (
    log_reading_legend,
    strip_rich_formatting, 
    share_ascii_with_ai,
    falling_alice,
    white_rabbit, 
    system_diagram,
    figlet_banner,
    fig,
    chip_says,
    story_moment,
    server_whisper,
    ascii_banner,
    section_header,
    radical_transparency_banner,
    status_banner,
    startup_summary_table,
    ai_breadcrumb_summary,
    startup_environment_warnings
)

# Import Botify code generation utilities (externalized from server.py for token reduction)
from helpers import botify_code_generation

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


# All ASCII display functions now imported from helpers.ascii_displays.py
# This eliminates ~300 lines of duplicate code while preserving functionality

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
    
    return logger


# 🔧 FINDER_TOKEN: rotate_looking_at_directory moved to mcp_tools.py to eliminate circular imports

# Show startup banner only when running as main script, not on watchdog restarts or imports
if __name__ == '__main__' and not os.environ.get('PIPULATE_WATCHDOG_RESTART'):
    figlet_banner("STARTUP", "Pipulate server starting...", font='slant', color=BANNER_COLORS['server_restart'])

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
ENV_FILE = Path('data/current_environment.txt')

APP_NAME = get_app_name()
logger.info(f'🏷️ FINDER_TOKEN: APP_CONFIG - App name: {APP_NAME}')

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
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route
from starlette.websockets import WebSocket, WebSocketDisconnect
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Import centralized configuration to eliminate duplication
from config import PCONFIG as CONFIG_PCONFIG

# Import MCP tools module for enhanced AI assistant capabilities
# Initialize MCP_TOOL_REGISTRY before importing mcp_tools to avoid circular dependency issues
MCP_TOOL_REGISTRY = {}

from mcp_tools import register_all_mcp_tools, register_mcp_tool
# Pass our registry to mcp_tools so they use the same instance
import mcp_tools
mcp_tools.MCP_TOOL_REGISTRY = MCP_TOOL_REGISTRY

# Import ASCII display functions (externalized from server.py for token reduction)
from helpers.ascii_displays import (
    log_reading_legend,
    strip_rich_formatting, 
    share_ascii_with_ai,
    falling_alice,
    white_rabbit, 
    system_diagram,
    figlet_banner,
    fig,
    chip_says,
    story_moment,
    server_whisper,
    ascii_banner,
    section_header,
    radical_transparency_banner,
    status_banner,
    startup_summary_table,
    ai_breadcrumb_summary,
    startup_environment_warnings
)

# Import Botify code generation utilities (externalized from server.py for token reduction)
from helpers import botify_code_generation

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


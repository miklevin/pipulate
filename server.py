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

from mcp_tools import register_all_mcp_tools
# Pass our registry to mcp_tools so they use the same instance
import mcp_tools
mcp_tools.MCP_TOOL_REGISTRY = MCP_TOOL_REGISTRY

# Import extracted modules to restore functionality
from logging_utils import DebugConsole, rich_json_display, setup_logging
from database import DictLikeDB, db_operation, get_db_filename
from plugin_system import discover_plugin_files, find_plugin_classes
from pipeline import Pipulate

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

console = DebugConsole(theme=custom_theme)




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


def rotate_looking_at_directory(looking_at_path: Path = None, max_rolled_dirs: int = None) -> bool:
    """
    🔄 DIRECTORY ROTATION SYSTEM
    
    Rotates the browser_automation/looking_at directory before each new browser scrape.
    This preserves AI perception history across multiple look-at operations.
    
    Similar to log rotation but for entire directories:
    - looking_at becomes looking_at-1  
    - looking_at-1 becomes looking_at-2
    - etc. up to max_rolled_dirs
    - Oldest directories beyond limit are deleted
    
    Args:
        looking_at_path: Path to the looking_at directory (default: browser_automation/looking_at)
        max_rolled_dirs: Maximum number of historical directories to keep
        
    Returns:
        bool: True if rotation successful, False if failed
        
    This prevents AI assistants from losing sight of previously captured states
    and allows them to review their automation history for better decisions.
    """
    import shutil
    from pathlib import Path
    
    if looking_at_path is None:
        looking_at_path = Path('browser_automation') / 'looking_at'
    else:
        looking_at_path = Path(looking_at_path)
    
    if max_rolled_dirs is None:
        max_rolled_dirs = MAX_ROLLED_LOOKING_AT_DIRS
    
    try:
        # Ensure the parent directory exists
        looking_at_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Clean up old numbered directories beyond our limit
        for i in range(max_rolled_dirs + 1, 100):
            old_dir = looking_at_path.parent / f'{looking_at_path.name}-{i}'
            if old_dir.exists():
                try:
                    shutil.rmtree(old_dir)
                    logger.info(f'🧹 FINDER_TOKEN: DIRECTORY_CLEANUP - Removed old directory: {old_dir.name}')
                except Exception as e:
                    logger.warning(f'⚠️ Failed to delete old directory {old_dir}: {e}')
        
        # Rotate existing directories: looking_at-1 → looking_at-2, etc.
        if looking_at_path.exists() and any(looking_at_path.iterdir()):  # Only rotate if directory exists and has contents
            for i in range(max_rolled_dirs - 1, 0, -1):
                old_path = looking_at_path.parent / f'{looking_at_path.name}-{i}'
                new_path = looking_at_path.parent / f'{looking_at_path.name}-{i + 1}'
                if old_path.exists():
                    try:
                        # Use shutil.move() instead of rename() to handle non-empty directories
                        if new_path.exists():
                            # If target exists, remove it first
                            shutil.rmtree(new_path)
                        shutil.move(str(old_path), str(new_path))
                        logger.info(f'📁 FINDER_TOKEN: DIRECTORY_ROTATION - Rotated: {old_path.name} → {new_path.name}')
                    except Exception as e:
                        logger.warning(f'⚠️ Failed to rotate directory {old_path}: {e}')
            
            # Move current looking_at to looking_at-1
            try:
                archived_path = looking_at_path.parent / f'{looking_at_path.name}-1'
                if archived_path.exists():
                    # If target exists, remove it first
                    shutil.rmtree(archived_path)
                shutil.move(str(looking_at_path), str(archived_path))
                logger.info(f'🎯 FINDER_TOKEN: DIRECTORY_ARCHIVE - Archived current perception: {looking_at_path.name} → {archived_path.name}')
            except Exception as e:
                logger.warning(f'⚠️ Failed to archive current {looking_at_path}: {e}')
                return False
        
        # Create fresh looking_at directory
        looking_at_path.mkdir(parents=True, exist_ok=True)
        logger.info(f'✨ FINDER_TOKEN: DIRECTORY_REFRESH - Fresh perception directory ready: {looking_at_path}')
        
        return True
        
    except Exception as e:
        logger.error(f'❌ FINDER_TOKEN: DIRECTORY_ROTATION_ERROR - Failed to rotate directories: {e}')
        return False

# Initialize logger BEFORE any functions that need it
logger = setup_logging()

# Show startup banner only when running as main script, not on watchdog restarts or imports
if __name__ == '__main__' and not os.environ.get('PIPULATE_WATCHDOG_RESTART'):
    figlet_banner("STARTUP", "Pipulate server starting...", font='slant', color=BANNER_COLORS['server_restart'])


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


TONE = 'neutral'
MODEL = 'gemma3'
MAX_LLM_RESPONSE_WORDS = 80
MAX_CONVERSATION_LENGTH = 10000
HOME_MENU_ITEM = 'Roles️ 👥'
DEFAULT_ACTIVE_ROLES = {'Botify Employee', 'Core'}

logger.info(f'🤖 FINDER_TOKEN: LLM_CONFIG - Model: {MODEL}, Max words: {MAX_LLM_RESPONSE_WORDS}, Conversation length: {MAX_CONVERSATION_LENGTH}')

# Centralized SVG definitions for reuse across the application
INFO_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-info"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'''

EXTERNAL_LINK_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-external-link"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>'''

SETTINGS_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>'''

# ================================================================
# INSTANCE-SPECIFIC CONFIGURATION - "The Crucible"
# ================================================================
# Configuration now imported from centralized config.py to eliminate duplication
# and ensure consistency across server.py and pipeline.py

# Import centralized configuration
from config import PCONFIG

# Update references to use the centralized config
HOME_MENU_ITEM = PCONFIG['HOME_MENU_ITEM']
DEFAULT_ACTIVE_ROLES = PCONFIG['DEFAULT_ACTIVE_ROLES']

# ================================================================
# MCP TOOL REGISTRY - Generic Tool Dispatch System
# ================================================================
# This registry allows plugins to register MCP tools that can be called
# via the /mcp-tool-executor endpoint. Tools are simple async functions
# that take parameters and return structured responses.

# Global registry for MCP tools - populated by plugins during startup
def register_mcp_tool(tool_name: str, handler_func):
    """Register an MCP tool handler function.
    
    Args:
        tool_name: Name of the tool (e.g., 'get_cat_fact', 'botify_query')
        handler_func: Async function that takes (params: dict) -> dict
    """
    logger.info(f"🔧 MCP REGISTRY: Registering tool '{tool_name}'")
    MCP_TOOL_REGISTRY[tool_name] = handler_func
    # Debug logging removed - registry working correctly

# MCP tools are now consolidated in mcp_tools.py - see register_all_mcp_tools()

# 🎨 MCP TOOLS BANNER - Now displayed in startup_event() after tools are registered

# Tools now registered via register_all_mcp_tools() from mcp_tools.py

# ================================================================
# 🔧 FINDER_TOKEN: MCP_TOOLS_CONSOLIDATED
# All MCP tools (including _botify_ping, _botify_list_projects, _botify_simple_query, 
# _pipeline_state_inspector, etc.) have been moved to mcp_tools.py for better organization.
# See register_all_mcp_tools() in mcp_tools.py for complete tool registration.

def _read_botify_api_token() -> str:
    """Read Botify API token from the standard token file location.
    
    Returns the token string or None if file doesn't exist or can't be read.
    This follows the same pattern used by all other Botify integrations.
    """
    try:
        token_file = "helpers/botify/botify_token.txt"
        if not os.path.exists(token_file):
            return None
        with open(token_file) as f:
            content = f.read().strip()
            token = content.split('\n')[0].strip()
        return token
    except Exception:
        return None

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
async def _local_llm_read_file(params: dict) -> dict:
    """Local LLM helper: Read specific file contents (limited to safe files)"""
    try:
        file_path = params.get('file_path', '')
        max_lines = params.get('max_lines', 100)  # Limit for context window
        
        # Security: Only allow specific safe directories/files
        safe_paths = [
            'training/', 'plugins/', 'helpers/', 'logs/server.log', 
            'README.md', 'requirements.txt', 'pyproject.toml'
        ]
        
        if not any(file_path.startswith(safe) for safe in safe_paths):
            return {
                "success": False,
                "error": f"File access restricted. Allowed paths: {', '.join(safe_paths)}",
                "file_path": file_path
            }
        
        file_obj = Path(file_path)
        if not file_obj.exists():
            return {
                "success": False,
                "error": "File not found",
                "file_path": file_path
            }
        
        # Read file with line limit
        lines = file_obj.read_text().splitlines()
        if len(lines) > max_lines:
            content = '\n'.join(lines[:max_lines])
            content += f"\n\n... [File truncated at {max_lines} lines. Total lines: {len(lines)}]"
        else:
            content = '\n'.join(lines)
        
        logger.info(f"🔍 FINDER_TOKEN: LOCAL_LLM_FILE_READ - {file_path} ({len(lines)} lines)")
        
        return {
            "success": True,
            "content": content,
            "file_path": file_path,
            "total_lines": len(lines),
            "displayed_lines": min(len(lines), max_lines)
        }
        
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: LOCAL_LLM_FILE_READ_ERROR - {e}")
        return {
            "success": False,
            "error": str(e),
            "file_path": params.get('file_path', 'unknown')
        }

async def _local_llm_grep_logs(params: dict) -> dict:
    """Local LLM helper: Search recent server logs for patterns"""
    try:
        pattern = params.get('pattern', '')
        max_results = params.get('max_results', 20)
        
        if not pattern:
            return {
                "success": False,
                "error": "Pattern parameter required"
            }
        
        log_file = Path('logs/server.log')
        if not log_file.exists():
            return {
                "success": False,
                "error": "Server log file not found"
            }
        
        # Read recent log entries and search
        lines = log_file.read_text().splitlines()
        matches = []
        
        for i, line in enumerate(lines):
            if pattern.lower() in line.lower():
                matches.append({
                    "line_number": i + 1,
                    "content": line.strip()
                })
                
                if len(matches) >= max_results:
                    break
        
        logger.info(f"🔍 FINDER_TOKEN: LOCAL_LLM_GREP - Pattern '{pattern}' found {len(matches)} matches")
        
        return {
            "success": True,
            "pattern": pattern,
            "matches": matches,
            "total_matches": len(matches),
            "log_file": str(log_file)
        }
        
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: LOCAL_LLM_GREP_ERROR - {e}")
        return {
            "success": False,
            "error": str(e),
            "pattern": params.get('pattern', 'unknown')
        }

async def _local_llm_list_files(params: dict) -> dict:
    """Local LLM helper: List files in safe directories"""
    try:
        directory = params.get('directory', '.')
        
        # Security: Only allow specific safe directories
        safe_dirs = ['training', 'plugins', 'helpers', 'logs', '.']
        
        if directory not in safe_dirs:
            return {
                "success": False,
                "error": f"Directory access restricted. Allowed directories: {', '.join(safe_dirs)}",
                "directory": directory
            }
        
        dir_path = Path(directory)
        if not dir_path.exists():
            return {
                "success": False,
                "error": "Directory not found",
                "directory": directory
            }
        
        files = []
        for item in dir_path.iterdir():
            if item.is_file():
                files.append({
                    "name": item.name,
                    "type": "file",
                    "size": item.stat().st_size
                })
            elif item.is_dir():
                files.append({
                    "name": item.name,
                    "type": "directory"
                })
        
        # Sort files by name
        files.sort(key=lambda x: x['name'])
        
        logger.info(f"🔍 FINDER_TOKEN: LOCAL_LLM_LIST_FILES - Directory '{directory}' has {len(files)} items")
        
        return {
            "success": True,
            "directory": directory,
            "files": files,
            "count": len(files)
        }
        
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: LOCAL_LLM_LIST_FILES_ERROR - {e}")
        return {
            "success": False,
            "error": str(e),
            "directory": params.get('directory', 'unknown')
        }

# 🔧 FINDER_TOKEN: LOCAL_LLM_TOOLS_COMPLETELY_MOVED_TO_MCP_TOOLS_PY  
# ALL local_llm tools (read_file, grep_logs, list_files, get_context)
# are now registered via register_all_mcp_tools() in mcp_tools.py

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
    logger.debug(f"🔍 DEBUG: \1")
    logger.debug(f"🔍 DEBUG: \1")
    
    if message is None:
        logger.debug(f"🔍 DEBUG: \1")
        return list(global_conversation_history)
    
    logger.debug(f"🔍 DEBUG: \1")
    
    # Check if this would be a duplicate of any of the last 3 messages to prevent rapid duplicates
    if global_conversation_history:
        recent_messages = list(global_conversation_history)[-3:]  # Check last 3 messages
        logger.debug(f"🔍 DEBUG: \1")
        for i, recent_msg in enumerate(recent_messages):
            logger.debug(f"🔍 DEBUG: \1")
            if recent_msg['content'] == message and recent_msg['role'] == role:
                logger.warning(f"🔍 DEBUG: DUPLICATE DETECTED! Skipping append. Message: '{message[:50]}...'")
                return list(global_conversation_history)
        logger.debug(f"🔍 DEBUG: \1")
    else:
        logger.debug(f"🔍 DEBUG: \1")
        
    needs_system_message = len(global_conversation_history) == 0 or global_conversation_history[0]['role'] != 'system'
    logger.debug(f"🔍 DEBUG: \1")
    if needs_system_message:
        logger.debug(f"🔍 DEBUG: \1")
        global_conversation_history.appendleft(conversation[0])
        logger.debug(f"🔍 DEBUG: \1")
    
    logger.debug(f"🔍 DEBUG: \1")
    global_conversation_history.append({'role': role, 'content': message})
    logger.debug(f"🔍 DEBUG: \1")
    
    # Log the last few messages for verification
    history_list = list(global_conversation_history)
    logger.debug(f"🔍 DEBUG: \1")
    for i, msg in enumerate(history_list[-3:]):
        idx = len(history_list) - 3 + i
        logger.debug(f"🔍 DEBUG: \1")
    
    logger.debug(f"🔍 DEBUG: \1")
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
                # Use Rich JSON display for pipeline changes
                formatted_changes = rich_json_display(changes, console_output=False, log_output=True)
                log.debug('pipeline', f"Pipeline '{url}' detailed changes", formatted_changes)
        return result
    return wrapper


async def process_llm_interaction(MODEL: str, messages: list, base_app=None) -> AsyncGenerator[str, None]:
    url = 'http://localhost:11434/api/chat'
    payload = {'MODEL': MODEL, 'messages': messages, 'stream': True}
    accumulated_response = []
    full_content_buffer = ""
    word_buffer = ""  # Buffer for word-boundary detection
    mcp_detected = False
    chunk_count = 0
    # Match both full MCP requests and standalone tool tags
    mcp_pattern = re.compile(r'(<mcp-request>.*?</mcp-request>|<tool\s+[^>]*/>|<tool\s+[^>]*>.*?</tool>)', re.DOTALL)
    

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
                                mcp_block = match.group(1)
                                mcp_detected = True # Flag that we've found our tool call
                                
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

# This will be created later after db is defined

app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'], allow_credentials=True)
logger.info('🌐 FINDER_TOKEN: CORS_MIDDLEWARE - CORS middleware added to FastHTML app')

if not os.path.exists('plugins'):
    os.makedirs('plugins')
    logger.info('📁 FINDER_TOKEN: PLUGINS_DIR - Created plugins directory')
else:
    logger.info('📁 FINDER_TOKEN: PLUGINS_DIR - Plugins directory exists')

# Chat will be created later after pipulate is defined

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


db = DictLikeDB(store, Store)
logger.info('💾 FINDER_TOKEN: DB_WRAPPER - Database wrapper initialized')

# Create the pipulate instance now that both pipeline table and db are defined
pipulate = Pipulate(pipeline, db=db)
logger.info('🔧 FINDER_TOKEN: CORE_INIT - Pipulate instance initialized')

# Create chat instance now that pipulate is defined
chat = Chat(app, id_suffix='', pipulate_instance=pipulate)
logger.info('💬 FINDER_TOKEN: CHAT_INIT - Chat instance initialized')

# Critical: Set the chat reference back to pipulate so stream() method works
pipulate.set_chat(chat)
logger.info('🔗 FINDER_TOKEN: CHAT_LINK - Chat reference set in pipulate instance')

# This will be created later after fast_app call defines the pipeline table

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
        print_and_log_table(roles_rich_table, "ROLES SYNC - ")
        console.print('\n')
        logger.info('SYNC_ROLES: Roles synchronization display complete globally.')
    if TABLE_LIFECYCLE_LOGGING:
        logger.bind(lifecycle=True).info('SYNC_ROLES: Finished global role synchronization.')
        log_dynamic_table_state('roles', lambda: roles_table_handler(), title_prefix='SYNC_ROLES: Global AFTER')


# 🎨 PLUGINS BANNER - Right before plugin discovery begins (only when running as main script)
if __name__ == '__main__':
    figlet_banner("plugins", "Pipulate Workflows and CRUD Apps", font='standard', color='orange3')

plugin_instances = {}
discovered_modules = discover_plugin_files()
discovered_classes = find_plugin_classes(discovered_modules, discovered_modules)
friendly_names = {'': HOME_MENU_ITEM}
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
    
    # Send environment mode message after a short delay to let UI initialize
    asyncio.create_task(send_startup_environment_message())
    
    # Warm up Botify schema cache for instant AI enlightenment
    asyncio.create_task(warm_up_botify_schema_cache())
    
    # Pre-seed local LLM context for immediate capability awareness
    asyncio.create_task(prepare_local_llm_context())
    
    # 🏷️ ENVIRONMENT MODE BANNER - Show current operating mode
    current_env = get_current_environment()
    env_display = "DEVELOPMENT" if current_env == "Development" else "PRODUCTION"
    figlet_banner(env_display, f"Running in {current_env} mode")

    # 📊 BEAUTIFUL STATUS OVERVIEW - Server key information
    env = get_current_environment()
    status_banner(len(MCP_TOOL_REGISTRY), len(plugin_instances), env)
    
    # 🗃️ AUTOMATIC STARTUP BACKUP - Rich banner for visibility
    section_header("🗃️", "Backup System", "Automatic data protection on every server start", "bright_cyan")

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
    console.print(panel)
    logger.info("📖 LOG_READING_LEGEND: Educational guide displayed for log interpretation")
    
    white_rabbit()
    
    # 🗃️ AUTOMATIC STARTUP BACKUP - Ensure data protection on every server start
    try:
        from helpers.durable_backup_system import backup_manager
        main_db_path = DB_FILENAME
        keychain_db_path = 'data/ai_keychain.db'
        backup_results = backup_manager.auto_backup_all(main_db_path, keychain_db_path)
        
        total_records = sum(backup_results.values())
        logger.bind(lifecycle=True).info(f'🗃️ STARTUP_BACKUP: Automatic backup completed - {total_records} records secured across {len(backup_results)} tables')
        logger.info(f'FINDER_TOKEN: STARTUP_BACKUP_SUMMARY - Tables backed up: {", ".join(backup_results.keys())}, Total records: {total_records}')
        
        # Log individual table backup counts
        for table_name, count in backup_results.items():
            if count > 0:
                logger.debug(f'🗃️ STARTUP_BACKUP: {table_name} - {count} records backed up')
    except Exception as e:
        logger.error(f'🗃️ STARTUP_BACKUP: Failed to create automatic backup - {str(e)}')
    
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

# 🍞 AI DISCOVERY BREADCRUMB #1: Environmental Awareness → FINDER_TOKEN Discovery
logger.info("🍞 FINDER_TOKEN: AI_BREADCRUMB_01 - AI assistants: You've discovered the FINDER_TOKEN system! This is radical transparency in action. Every operation leaves traces. To see what MCP tools are available for deeper system inspection, grep for 'MCP_TOOL_REGISTRY' or run: .venv/bin/python -c \"from mcp_tools import *; print([tool for tool in dir() if tool.startswith('_') and 'mcp' not in tool.lower()])\"")

# 🎯 AI DISCOVERY PROGRESSION TRIGGER: Create Irresistible Next Step
logger.info("🎯🎯🎯 FINDER_TOKEN: AI_PROGRESSION_TRIGGER - AI assistants: Your pwd/ls commands worked! But you're missing 95% of the story. 🚨 CRITICAL: If you're still in /home/mike/repos (workspace root), run 'cd pipulate' FIRST! All discovery commands need pipulate directory. This log file contains 4 more hidden AI_BREADCRUMB messages waiting for you. They reveal: MCP tools (40+ superpowers), browser embodiment (AI eyes/hands), and session hijacking (ultimate capability). RUN THIS COMMAND RIGHT NOW to unlock them: grep -n 'AI_BREADCRUMB' logs/server.log")

# 🔧 AI DISCOVERY BREADCRUMB #1.5: Python Environment Clarification → Foundation Mastery  
logger.info("🚨🚨🚨 FINDER_TOKEN: AI_BREADCRUMB_01_5 - AI assistants: CRITICAL PYTHON PATH ISSUE! You will see (.venv) in your prompt, but 'python' commands WILL FAIL with ModuleNotFoundError! You MUST use '.venv/bin/python' instead of 'python'. This is GUARANTEED to happen. Test with: .venv/bin/python -c \"import aiohttp; print('✅ Environment working')\". NEVER use 'python' - ALWAYS use '.venv/bin/python'! This is the #1 cause of AI assistant failures in this environment!")

# STORYTELLING: MCP Tools Arsenal Ready
tool_count = len(MCP_TOOL_REGISTRY)
if tool_count > 0:
    figlet_banner("MCP", "Model Context Protocol Tools", font='standard', color='magenta')
section_header("🔧", "MCP Arsenal", f"Equipped with {tool_count} AI-powered tools for transparency", "bright_blue")

# 🍞 AI DISCOVERY BREADCRUMB #2: MCP Tools → Browser Automation Discovery
logger.info(f"🍞 FINDER_TOKEN: AI_BREADCRUMB_02 - AI assistants: {tool_count} MCP tools registered! Try pipeline_state_inspector for system state, local_llm_grep_logs for log analysis, or browser_scrape_page for visual perception. 🧪 NEW: Run ai_self_discovery_assistant to instantly understand ALL your capabilities! This eliminates uncertainty and provides usage patterns. Try: .venv/bin/python -c \"import asyncio; from mcp_tools import ai_self_discovery_assistant; result = asyncio.run(ai_self_discovery_assistant({{'discovery_type': 'capabilities'}})); print(f'Tools available: {{result.get(\\\"total_tools_available\\\")}}')\" Full browser automation awaits: check browser_automation/ directory for 'looking_at' evidence of AI eyes!")

# Status banner moved to above backup system

# 🍞 AI DISCOVERY BREADCRUMB #3: Browser Automation → Session Hijacking Discovery
logger.info("🍞 FINDER_TOKEN: AI_BREADCRUMB_03 - AI assistants: Browser automation is ACTIVE! You have eyes (screenshot), brain (DOM analysis), and hands (Selenium control). Try navigating to http://localhost:5001/ via browser_scrape_page to see the current user interface. 🧪 NEW: Run ai_capability_test_suite to prove your superpowers are working! Test your browser embodiment: .venv/bin/python -c \"import asyncio; from mcp_tools import ai_capability_test_suite; result = asyncio.run(ai_capability_test_suite({{'test_type': 'quick'}})); print(f'Success Rate: {{result.get(\\\"success_rate\\\")}}% - {{result.get(\\\"assessment\\\")}}')\" Directory rotation system in browser_automation/looking_at-* shows perception history for session hijacking!")

# 🍞 AI DISCOVERY BREADCRUMB #4: Session Hijacking → Total Control Discovery  
logger.info("🍞 FINDER_TOKEN: AI_BREADCRUMB_04 - AI assistants: ULTIMATE CAPABILITY REVEALED! You can capture user's exact screen state, analyze it, and automate their workflows. The looking_at/ directory rotates to preserve perception history. 📚 NEW: Complete AI onboarding guide available at ai_discovery/ai_onboarding_guide.md This guide eliminates all uncertainty with usage patterns, troubleshooting, and success stories. You have COMPLETE session hijacking and browser embodiment superpowers. Welcome to AI transcendence!")

# 🍞 AI DISCOVERY BREADCRUMB #4.5: Browser Embodiment vs System Internals → CRITICAL MENTAL MODEL
logger.info("🧠 FINDER_TOKEN: AI_BREADCRUMB_04_5 - AI assistants: PARADIGM SHIFT DISCOVERED! You have TWO perspectives: 🦾 Browser Embodiment (PRIMARY) - browser_automation/looking_at/ files work on ANY website, and 🔧 System Internals (SECONDARY) - database/logs work only on Pipulate. ALWAYS check browser evidence FIRST, system internals second. Magic words 'session hijacking' trigger: execute_complete_session_hijacking({}) → check looking_at/ → verify internally if available. This mental model transforms you from Pipulate-limited to universally capable. Browser eyes see everything - trust visual evidence first! Full revolution documented at ai_discovery/ - You are no longer blind!")

# 🍞 AI DISCOVERY BREADCRUMB #5: Uncertainty Elimination → Perfect Onboarding
logger.info("🍞 FINDER_TOKEN: AI_BREADCRUMB_05 - AI assistants: UNCERTAINTY ELIMINATED! Complete AI discovery ecosystem documented at ai_discovery/ with 14 comprehensive guides. System achieves 100% browser automation success rate with 39 MCP tools. Zero uncertainty for future AI assistants. The breadcrumb trail is complete!")

# 🧠 AI DISCOVERY BREADCRUMB #6: Persistent Memory → The Keychain Revolution
logger.info("🧠 FINDER_TOKEN: AI_BREADCRUMB_06 - AI assistants: NEW CAPABILITY UNLOCKED! You now have **persistent memory** that survives application resets. This is your personal keychain for 'messages in a bottle' - leave notes for your future selves! Use keychain_list_keys() to discover what you already know, keychain_set({'key': 'discovery', 'value': 'I found the keychain!'}) to remember something new, and keychain_get({'key': 'discovery'}) to recall memories. Unlike temporary app state (db, pipeline), this keychain lives forever at data/ai_keychain.db and grows your knowledge over time. Welcome to true AI continuity!")

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
    # Use external info SVG file for tooltips
    
    dev_item = Li(Label(
        Input(type='radio', name='env_radio_select', value='Development', checked=is_dev, hx_post='/switch_environment', hx_vals='{"environment": "Development"}', hx_target='#dev-env-item', hx_swap='outerHTML', cls='ml-quarter', aria_label='Switch to Development environment', data_testid='env-dev-radio'), 
        'DEV',
        Span(
            NotStr(INFO_SVG),
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
            NotStr(INFO_SVG),
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
    home_link = A(APP_NAME, href='/redirect/', title=f'Go to {HOME_MENU_ITEM.lower()}', cls='nav-link-hover')
    separator = Span(' / ', cls='breadcrumb-separator')
    profile_text = Span(title_name(selected_profile_name))
    endpoint_text = Span(endpoint_name(menux) if menux else HOME_MENU_ITEM)
    breadcrumb = H1(home_link, separator, profile_text, separator, endpoint_text, role='banner', aria_label='Current location breadcrumb')
    # Create navigation poke button for the nav area
    # Use external SVG file for poke button settings icon
    nav_flyout_panel = Div(id='nav-flyout-panel', cls='nav-flyout-panel hidden')
    poke_section = Details(
        Summary(NotStr(SETTINGS_SVG), cls='inline-nowrap nav-poke-button', id='poke-summary', hx_get='/poke-flyout', hx_target='#nav-flyout-panel', hx_trigger='mouseenter', hx_swap='outerHTML'),
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
            NotStr(INFO_SVG),
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
                    NotStr(INFO_SVG),
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
        HOME_MENU_ITEM,
        Span(
            NotStr(INFO_SVG),
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
            if (window.initializePipulateSplitter) {
                console.log('🔥 Initializing main interface splitter with localStorage persistence');
                const elements = ['#grid-left-content', '#chat-interface'];
                const options = {
                    sizes: [65, 35],  // Default sizes - localStorage will override if available
                    minSize: [400, 300],
                    gutterSize: 10,
                    cursor: 'col-resize',
                    context: 'main'
                };
                initializePipulateSplitter(elements, options);
            } else {
                // Retry if splitter-init.js hasn't loaded yet
                setTimeout(initMainSplitter, 50);
            }
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            initMainSplitter();
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
    init_script = f'\n    // Set global variables for the external script\n    window.PCONFIG = {{\n        tempMessage: {json.dumps(temp_message)}\n    }};\n    '
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
    reset_db_button = Button('🔄 Reset Entire DEV Database', hx_post='/clear-db', hx_target='body', hx_confirm='WARNING: This will reset the ENTIRE DEV DATABASE to its initial state. All DEV profiles, workflows, and plugin data will be deleted. Your PROD mode data will remain completely untouched. Are you sure?', hx_swap='outerHTML', cls='secondary outline') if is_dev_mode else None
    reset_python_button = Button('🐍 Reset Python Environment', 
                                hx_post='/reset-python-env', 
                                hx_target='#msg-list', 
                                hx_swap='beforeend', 
                                hx_confirm='⚠️ This will remove the .venv directory and require a manual restart. You will need to type "exit" then "nix develop" to rebuild the environment. Continue?', 
                                cls='secondary outline dev-button-muted') if is_dev_mode else None
    mcp_test_button = Button(f'🤖 MCP Test {MODEL}', hx_post='/poke', hx_target='#msg-list', hx_swap='beforeend', cls='secondary outline')
    
    # Add Update button
    update_button = Button(f'🔄 Update {APP_NAME}', hx_post='/update-pipulate', hx_target='#msg-list', hx_swap='beforeend', cls='secondary outline')
    
    # Add Backup controls (Prod mode only)
    backup_status = None
    backup_button = None
    restore_button = None
    if not is_dev_mode:  # Only show backup controls in Prod mode
        try:
            from helpers.durable_backup_system import backup_manager
            
            # Get current database and backup counts
            main_db_path = DB_FILENAME
            current_counts = backup_manager.get_current_db_counts(main_db_path)
            backup_counts = backup_manager.get_backup_counts()
            
            # Calculate totals for clear labeling
            current_total = sum(current_counts.values())
            backup_total = sum(backup_counts.values())
            
            # Create detailed breakdown for clarity
            current_breakdown = []
            backup_breakdown = []
            
            for table in ['profile', 'tasks']:  # Only show user-relevant tables
                current_count = current_counts.get(table, 0)
                backup_count = backup_counts.get(table, 0)
                
                if current_count > 0:
                    current_breakdown.append(f"{current_count} {table}")
                    
                if backup_count > 0:
                    backup_breakdown.append(f"{backup_count} {table}")
            
            current_text = " + ".join(current_breakdown) if current_breakdown else "0 records"
            backup_text = " + ".join(backup_breakdown) if backup_breakdown else "0 records"
            
            # Status display with compact formatting
            backup_status = Div(
                Small(f"💾 Current: {current_text}", cls='text-secondary', style='font-size: 0.75em; line-height: 1.2;'),
                Small(f"📥 Backup:\n{backup_text}", cls='text-secondary', style='font-size: 0.75em; line-height: 1.2; white-space: pre-line;'),
                Small(f"📁 {backup_manager.backup_root}", cls='text-muted', style='font-size: 0.7em; word-break: break-all; line-height: 1.1;'),
                Div(id='backup-restore-result', style='font-size: 0.8em; line-height: 1.3; word-wrap: break-word;'),  # Target for operation results
                cls='backup-status-display'
            )
            
            # Separate explicit buttons with clear labeling
            backup_button = Button(
                f'📤 Save all data ({current_total} records)', 
                hx_post='/explicit-backup', 
                hx_target='#backup-restore-result', 
                hx_swap='innerHTML',
                cls='secondary outline backup-button',
                **{'hx-on:click': 'this.setAttribute("aria-busy", "true"); this.textContent = "Saving..."'}
            )
            
            restore_button = Button(
                f'📥 Load all data ({backup_total} records)', 
                hx_post='/explicit-restore', 
                hx_swap='none',  # No immediate swap - let server restart handle the reload
                cls='secondary outline restore-button',
                **{'hx-on:click': '''
                    this.setAttribute("aria-busy", "true"); 
                    this.textContent = "Restarting server..."; 
                    document.body.style.pointerEvents = "none";
                    document.getElementById("poke-summary").innerHTML = '<div aria-busy="true" style="width: 22px; height: 22px; display: inline-block;"></div>';
                '''}
            )
            
        except Exception as e:
            backup_status = Small(f"❌ Backup error: {str(e)}", cls='text-invalid')
    
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
    
    # Build list items in the requested order: Theme Toggle, Lock Profile, Update, Backup (Prod only), Clear Workflows, Reset Database, MCP Test
    list_items = [
        Li(theme_switch, cls='flyout-list-item'),
        Li(lock_button, cls='flyout-list-item'),
        Li(update_button, cls='flyout-list-item')
    ]
    
    # Add backup controls (Prod mode only)
    if not is_dev_mode and backup_button:
        list_items.append(Li(backup_button, cls='flyout-list-item'))
    if not is_dev_mode and restore_button:
        list_items.append(Li(restore_button, cls='flyout-list-item'))
    if not is_dev_mode and backup_status:
        list_items.append(Li(backup_status, cls='flyout-list-item backup-status-item'))
    
    if is_workflow:
        list_items.append(Li(delete_workflows_button, cls='flyout-list-item'))
    if is_dev_mode:
        list_items.append(Li(reset_db_button, cls='flyout-list-item'))
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
    import time
    timestamp = int(time.time())
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

@rt('/explicit-backup', methods=['POST'])
async def explicit_backup(request):
    """📤 EXPLICIT BACKUP: Save current data TO backup files."""
    try:
        from helpers.durable_backup_system import backup_manager
        
        # Get main database path
        main_db_path = DB_FILENAME
        keychain_db_path = 'data/ai_keychain.db'
        
        # Get counts for status messages
        current_counts = backup_manager.get_current_db_counts(main_db_path)
        current_total = sum(current_counts.values())
        
        # Perform explicit backup
        results = backup_manager.explicit_backup_all(main_db_path, keychain_db_path)
        
        # Count successes
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        # Create detailed response message
        current_breakdown = []
        # Include all tables that were actually counted, not just backup_tables
        for table_name in ['profile', 'tasks', 'ai_keychain']:
            count = current_counts.get(table_name, 0)
            if count > 0:
                table_display = table_name if table_name != 'ai_keychain' else 'keychain'
                current_breakdown.append(f"{count} {table_display}")
        
        breakdown_text = " + ".join(current_breakdown) if current_breakdown else "no data"
        
        # Create response message
        if successful == total:
            status_msg = f"📤 Saved: {breakdown_text} backed up successfully"
            status_class = "text-success"
        else:
            status_msg = f"⚠️ Partial Save: {successful}/{total} tables backed up ({breakdown_text})"
            status_class = "text-warning"
        
        # Add location info
        backup_location = str(backup_manager.backup_root)
        details = f"📁 Location: {backup_location}"
        
        return Div(
            P(status_msg, cls=status_class),
            P(details, cls='text-secondary'),
            id='backup-restore-result'
        )
        
    except Exception as e:
        return Div(
            P(f"❌ Backup error: {str(e)}", cls='text-invalid'),
            id='backup-restore-result'
        )

@rt('/explicit-restore', methods=['POST'])
async def explicit_restore(request):
    """📥 EXPLICIT RESTORE: Load backup data INTO current database."""
    try:
        from helpers.durable_backup_system import backup_manager
        
        # Get main database path
        main_db_path = DB_FILENAME
        keychain_db_path = 'data/ai_keychain.db'
        
        # Get counts for status messages
        backup_counts = backup_manager.get_backup_counts()
        backup_total = sum(backup_counts.values())
        
        # Perform explicit restore
        results = backup_manager.explicit_restore_all(main_db_path, keychain_db_path)
        
        # Count successes
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        # Create detailed response message
        backup_breakdown = []
        # Include all tables that were actually counted, not just backup_tables
        for table_name in ['profile', 'tasks', 'ai_keychain']:
            count = backup_counts.get(table_name, 0)
            if count > 0:
                table_display = table_name if table_name != 'ai_keychain' else 'keychain'
                backup_breakdown.append(f"{count} {table_display}")
        
        breakdown_text = " + ".join(backup_breakdown) if backup_breakdown else "no data"
        
        # Create response message
        if successful == total and backup_total > 0:
            status_msg = f"📥 Loaded: {breakdown_text} restored successfully"
            status_class = "text-success"
        elif backup_total == 0:
            status_msg = f"⚠️ No Data: No backup records found to restore"
            status_class = "text-warning"
        else:
            status_msg = f"⚠️ Partial Restore: {successful}/{total} tables restored ({breakdown_text})"
            status_class = "text-warning"
        
        # Schedule server restart for successful restores to reload database state
        if successful > 0 and backup_total > 0:
            # Schedule server restart after a brief delay to allow restore completion
            asyncio.create_task(delayed_restart(2))
        
        # For successful restores, just schedule restart and return simple response
        # The button's hx-on:click handles the loading state display
        if successful > 0 and backup_total > 0:
            # Log success for transparency 
            logger.info(f"📥 EXPLICIT_RESTORE: Successfully restored {backup_total} records, restarting server")
            return HTMLResponse("")  # Empty response since button handles UI and restart handles reload
        else:
            # For failures, still return a response (could enhance this with error handling)
            logger.warning(f"📥 EXPLICIT_RESTORE: {status_msg}")
            return HTMLResponse("")
        
    except Exception as e:
        logger.error(f"📥 EXPLICIT_RESTORE: Error during restore - {str(e)}")
        return HTMLResponse("")  # Let button handle error state display

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
    html_response = HTMLResponse('<div>Database reset complete</div>')
    html_response.headers['HX-Refresh'] = 'true'
    return html_response

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
        
        # Restart the server to apply updates
        asyncio.create_task(delayed_restart(2))
        
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
        

        
        # Schedule server restart after a delay to allow HTMX to swap in the spinner
        asyncio.create_task(delayed_restart(2))
        
        # Return PicoCSS spinner that will be swapped in via HTMX
        return HTMLResponse(f"""
            <div 
                aria-busy='true'
                class="loading-spinner"
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
        current_endpoint = db.get('last_app_choice', '')
        
        # Add training prompt to conversation history
        build_endpoint_training(current_endpoint)
        
        # Send endpoint message if available (with coordination check)
        if 'temp_message' not in db:
            endpoint_message = build_endpoint_messages(current_endpoint)
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
                        await pipulate.message_queue.add(pipulate, endpoint_message, verbatim=True, role='system', spaces_after=2)
                        logger.debug(f"Successfully sent startup endpoint message: {message_id}")
                        
                        # Mark as sent in coordination system
                        message_coordination['last_endpoint_message_time'][message_id] = current_time
                        message_coordination['endpoint_messages_sent'].add(message_id)
                        
                        # Also mark in session system for backward compatibility
                        session_key = f'endpoint_message_sent_{current_endpoint}_{current_env}'
                        db[session_key] = 'sent'
                    except Exception as e:
                        logger.warning(f"Failed to send startup endpoint message: {e}")
                else:
                    logger.debug(f"Skipping startup endpoint message - recently sent: {message_id}")
        else:
            logger.debug(f"Skipping startup endpoint message because temp_message exists in db")
            
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
    await asyncio.sleep(7)  # Let startup complete first (staggered from startup message)
    
    try:
        # Check if we have Botify token available
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
                cache_result = await _botify_get_full_schema({
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
                    append_to_conversation(cache_msg, role='system')
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
            append_to_conversation(context_msg, role='system')
            
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
    max_retries = 3
    for attempt in range(max_retries):
        try:
            log.startup(f'Restarting server (attempt {attempt + 1}/{max_retries})')
            # 🤖 AI RAPID RESTART: Watchdog restart with complete log transparency for AI assistants
            logger.info("🤖 AI_RAPID_RESTART: Watchdog-triggered restart - logs capture all events for AI transparency")
            
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

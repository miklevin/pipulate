"""
server_logging.py - Centralized logging utilities

Extracted from server.py to eliminate 100+ lines of duplication.
Contains setup_logging(), DebugConsole, and rich_json_display().
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger
from rich.console import Console
from rich.json import JSON
from rich.style import Style as RichStyle
from rich.theme import Theme


# Custom theme for Rich console - needs to match server.py exactly
custom_theme = Theme({
    'default': 'white on black', 
    'header': RichStyle(color='magenta', bold=True, bgcolor='black'), 
    'cyan': RichStyle(color='cyan', bgcolor='black'), 
    'green': RichStyle(color='green', bgcolor='black'), 
    'orange3': RichStyle(color='orange3', bgcolor='black'), 
    'white': RichStyle(color='white', bgcolor='black')
})


def safe_print(*args, **kwargs):
    """Safe wrapper for print() that handles I/O errors gracefully"""
    try:
        print(*args, **kwargs)
    except (BlockingIOError, BrokenPipeError, OSError) as e:
        # Handle terminal I/O errors gracefully - print failed but continue
        logger.warning(f"🖨️ SAFE_PRINT: Print output failed ({type(e).__name__}: {e}), continuing silently")
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"🖨️ SAFE_PRINT: Unexpected error during print: {type(e).__name__}: {e}")


class DebugConsole(Console):

    def print(self, *args, **kwargs):
        # Filter out AI Creative Vision messages from console (they're for log files only)
        # Convert args to string to check for AI markers
        message_str = ' '.join(str(arg) for arg in args)

        # Skip console output for AI-specific messages (they go to logs only)
        if '🎭 AI_CREATIVE_VISION' in message_str:
            return

        super().print(*args, **kwargs)


def rich_json_display(data, title=None, console_output=True, log_output=True, ai_log_output=True):
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

    Returns:
        str: The formatted JSON string for logging
    """
    # Import console from the module that will import this
    from imports.server_logging import console
    
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


def setup_logging(DEBUG_MODE=False, STATE_TABLES=False):
    """
    🔧 UNIFIED LOGGING SYSTEM

    Single source of truth logging with rolling server logs.
    Designed for optimal debugging experience with surgical search capabilities.

    Features:
    - server.log (current run, live tail-able)
    - server-1.log, server-2.log, etc. (previous runs for context across restarts)
    - Unified log stream with clear categorization and finder tokens
    - No more fragmented api.log/lifecycle.log confusion
    
    Args:
        DEBUG_MODE: Whether to enable debug logging
        STATE_TABLES: Whether to show state table logging
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


def print_and_log_table(table, title_prefix=""):
    """Print rich table to console AND log structured data to server.log for radical transparency.

    This single function ensures both console display and log transparency happen together,
    preventing the mistake of using one without the other.

    Args:
        table: Rich Table object to display and log
        title_prefix: Optional prefix for the log entry
    """
    # First, display the rich table in console with full formatting
    from rich.console import Console
    if isinstance(slog.console, Console):
        slog.console.print(table)
    else:
        # Fallback for non-rich console environments
        print(str(table))

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
                    log_lines.append(f"Row {i + 1}: {' | '.join(cells)}")
                else:
                    log_lines.append(f"Row {i + 1}: {str(row)}")

        # Log the complete table representation with extra spacing
        logger.info('\n'.join(log_lines) + '\n')

    except Exception as e:
        logger.error(f"Error logging rich table: {e}")
        logger.info(f"📊 {title_prefix}RICH TABLE: [Unable to extract table data]")


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
        for list_item in obj:
            if isinstance(list_item, str):
                # Try to parse JSON strings in lists
                try:
                    if (list_item.startswith('{') and list_item.endswith('}')) or \
                       (list_item.startswith('[') and list_item.endswith(']')):
                        parsed_item = json.loads(list_item)
                        result.append(_recursively_parse_json_strings(parsed_item))
                    else:
                        result.append(list_item)
                except (json.JSONDecodeError, TypeError):
                    result.append(list_item)
            elif isinstance(list_item, (dict, list)):
                # Recursively process nested structures
                result.append(_recursively_parse_json_strings(list_item))
            else:
                result.append(list_item)
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
        return slog.rich_json_display(processed_records, title="Formatted Records", console_output=False, log_output=True)
    except Exception as e:
        return f'[Error formatting records for JSON: {e}] Processed: {str(processed_records)}'

# Create console instance for this module
console = DebugConsole(theme=custom_theme) 

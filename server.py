# Warning: This is an intentionally local-first app using server-side state and HTMX.
# Do not refactor the DictLikeDB or HTMX patterns - see README.md and .cursorrules
# for the design philosophy and contribution guidelines.

import ast
import asyncio
import functools
import importlib
import inspect
import json
import os
import random
import sys
import time
import traceback
from collections import Counter, deque
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
import sqlite3

# Direct settings for logging verbosity - toggle these to change behavior
DEBUG_MODE = False   # Set to True for verbose logging (all DEBUG level logs)
STATE_TABLES = False # Set to True to display state tables (🍪 and ➡️)

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


def fig(text, font='slant', color='cyan', width=200):
    figlet = Figlet(font=font, width=width)
    fig_text = figlet.renderText(str(text))
    colored_text = Text(fig_text, style=f"{color} on default")
    console.print(colored_text, style="on default")


APP_NAME = get_app_name()
TONE = "neutral"
MODEL = "gemma3"
MAX_LLM_RESPONSE_WORDS = 60
MAX_CONVERSATION_LENGTH = 10000

# Environment settings
ENV_FILE = Path('data/environment.txt')

# Create data directory if it doesn't exist
data_dir = Path('data')
data_dir.mkdir(parents=True, exist_ok=True)

# Read environment from file or default to Production
def get_current_environment():
    if ENV_FILE.exists():
        return ENV_FILE.read_text().strip()
    else:
        # Default to Development if file doesn't exist
        ENV_FILE.write_text("Development")
        return "Development"

def set_current_environment(environment):
    ENV_FILE.write_text(environment)
    logger.info(f"Environment set to: {environment}")

# Function to get database filename based on current environment
def get_db_filename():
    current_env = get_current_environment()
    if current_env == "Development":
        return f"data/{APP_NAME.lower()}_dev.db"
    else:
        return f"data/{APP_NAME.lower()}.db"

# Set initial DB_FILENAME
DB_FILENAME = get_db_filename()

PLACEHOLDER_ADDRESS = "www.site.com"
PLACEHOLDER_CODE = "CCode (us, uk, de, etc)"
GRID_LAYOUT = "65% 35%"
NAV_FILLER_WIDTH = "2%"
MIN_MENU_WIDTH = "18vw"
MAX_MENU_WIDTH = "22vw"
WEB_UI_WIDTH = "95%"
WEB_UI_PADDING = "1rem"
WEB_UI_MARGIN = "0 auto"
NOWRAP_STYLE = (
    "white-space: nowrap; "
    "overflow: hidden; "
    "text-overflow: ellipsis;"
)
LIST_SUFFIX = "List"

# Near the top with other constants
CORE_PLUGINS = {
    "",  # Home
    "tasks",
    "hello_workflow",
    "connect_with_botify",
    "parameter_buster"
}

def is_core_plugin(plugin_name):
    """Determine if a plugin is part of the core workflow."""
    return plugin_name in CORE_PLUGINS

def setup_logging():
    """Set up unified logging between console and file with synchronized formats.
    
    Designed to:
    1. Default to INFO level (quiet but informative)
    2. Use consistent formatting between console and file
    3. Enable easy switching to DEBUG via the DEBUG_MODE constant
    4. Keep a single log file that's reset on server restart
    """
    logs_dir = Path('logs')
    logs_dir.mkdir(parents=True, exist_ok=True)
    app_log_path = logs_dir / f'{APP_NAME}.log'
    logger.remove()  # Remove default handlers

    # Create a function to sanitize HTML tags for the logger
    def sanitize_for_log(record):
        if "message" in record and isinstance(record["message"], str):
            # Replace angle brackets with their HTML entities to prevent logger from parsing HTML tags
            record["message"] = record["message"].replace("<", "&lt;").replace(">", "&gt;")
        return record

    # Use the DEBUG_MODE constant directly instead of environment variable
    log_level = "DEBUG" if DEBUG_MODE else "INFO"
    
    # Delete the previous log file if it exists
    if app_log_path.exists():
        app_log_path.unlink()
    
    # Also delete any timestamped log files that may exist
    for old_log in logs_dir.glob(f'{APP_NAME}.????-??-??_*'):
        try:
            old_log.unlink()
        except Exception as e:
            print(f"Failed to delete old log file {old_log}: {e}")
    
    # Define format strings for consistent display between console and file
    time_format = "{time:YYYY-MM-DD HH:mm:ss}"
    console_time_format = "<green>{time:HH:mm:ss}</green>"
    
    message_format = "{level: <8} | {name: <15} | {message}"
    console_message_format = "<level>{level: <8}</level> | <cyan>{name: <15}</cyan> | <cyan>{message}</cyan>"
    
    # File logger - captures everything at the configured level
    logger.add(
        app_log_path,
        level=log_level,
        format=f"{time_format} | {message_format}",
        enqueue=True,
        filter=sanitize_for_log
    )

    # Console logger - same content but with color
    logger.add(
        sys.stderr,
        level=log_level,
        format=f"{console_time_format} | {console_message_format}",
        colorize=True,
        filter=sanitize_for_log
    )
    
    # Log the current mode on startup
    log_instance = logger.opt(colors=True)
    if DEBUG_MODE:
        log_instance.info(f"🔍 Running in <yellow>DEBUG</yellow> mode (verbose logging enabled)")
    else:
        log_instance.info(f"🚀 Running in <green>INFO</green> mode (edit server.py and set DEBUG_MODE=True for verbose logging)")
        
    # Log state tables mode if enabled
    if STATE_TABLES:
        log_instance.info(f"🔍 State tables <yellow>ENABLED</yellow> (🍪 and ➡️ tables will be displayed)")
        
    return log_instance


# Initialize logger after setting up environment functions
logger = setup_logging()

# Log the current environment and database file
logger.info(f"Environment: {get_current_environment()}")
logger.info(f"Using database: {DB_FILENAME}")

class LogManager:
    """Central logging coordinator for artistic control of console and file output.
    
    This class provides methods that encourage a consistent, carefully curated
    logging experience across both console and log file. It encourages using 
    the same messages in both places with appropriate formatting.
    """
    def __init__(self, logger):
        self.logger = logger
        self.categories = {
            "server": "🖥️ SERVER",
            "startup": "🚀 STARTUP",
            "workflow": "⚙️ WORKFLOW",
            "pipeline": "🔄 PIPELINE",
            "network": "🌐 NETWORK",
            "database": "💾 DATABASE",
            "profile": "👤 PROFILE",
            "plugin": "🔌 PLUGIN",
            "chat": "💬 CHAT",
            "error": "❌ ERROR",
            "warning": "⚠️ WARNING"
        }
        
    def format_message(self, category, message, details=None):
        emoji = self.categories.get(category, f"⚡ {category.upper()}")
        formatted = f"[{emoji}] {message}"
        if details:
            formatted += f" | {details}"
        return formatted
    
    def startup(self, message, details=None):
        """Log a startup-related message."""
        self.logger.info(self.format_message("startup", message, details))
    
    def workflow(self, message, details=None):
        """Log a workflow-related message."""
        self.logger.info(self.format_message("workflow", message, details))
    
    def pipeline(self, message, details=None, pipeline_id=None):
        """Log a pipeline-related message."""
        if pipeline_id:
            details = f"Pipeline: {pipeline_id}" + (f" | {details}" if details else "")
        self.logger.info(self.format_message("pipeline", message, details))
    
    def profile(self, message, details=None):
        """Log a profile-related message."""
        self.logger.info(self.format_message("profile", message, details))
    
    def data(self, message, data=None):
        """Log structured data - at DEBUG level since it's typically verbose."""
        msg = self.format_message("database", message)
        if data is not None:
            # Limit the data display in INFO mode to keep logs clean
            if isinstance(data, dict) and len(data) > 5:
                self.logger.debug(f"{msg} | {json.dumps(data, indent=2)}")
            else:
                self.logger.debug(f"{msg} | {data}")
        else:
            self.logger.info(msg)
    
    def event(self, event_type, message, details=None):
        """Log a user-facing event in the application."""
        self.logger.info(self.format_message(event_type, message, details))
    
    def warning(self, message, details=None):
        """Log a warning message at WARNING level."""
        self.logger.warning(self.format_message("warning", message, details))
        
    def error(self, message, error=None):
        """Log an error with traceback at ERROR level."""
        formatted = self.format_message("error", message)
        if error:
            import traceback
            error_details = f"{error.__class__.__name__}: {str(error)}"
            self.logger.error(f"{formatted} | {error_details}")
            self.logger.debug(traceback.format_exc())
        else:
            self.logger.error(formatted)
    
    def debug(self, category, message, details=None):
        """Log debug information that only appears in DEBUG mode."""
        self.logger.debug(self.format_message(category, message, details))

# Create a global log manager instance
log = LogManager(logger)

custom_theme = Theme({
    "default": "white on black",
    "header": RichStyle(
        color="magenta",
        bold=True,
        bgcolor="black"
    ),
    "cyan": RichStyle(
        color="cyan",
        bgcolor="black"
    ),
    "green": RichStyle(
        color="green",
        bgcolor="black"
    ),
    "orange3": RichStyle(
        color="orange3",
        bgcolor="black"
    ),
    "white": RichStyle(
        color="white",
        bgcolor="black"
    ),
})


class DebugConsole(Console):
    def print(self, *args, **kwargs):
        super().print(*args, **kwargs)


console = DebugConsole(theme=custom_theme)


def title_name(word: str) -> str:
    """Format a string into a title case form.
    
    Args:
        word: The string to format
        
    Returns:
        str: The formatted string in title case
    """
    if not word:
        return ""

    # First replace periods with spaces, then hyphens with spaces
    formatted = word.replace('.', ' ').replace('-', ' ')

    # Split by underscores and spaces
    words = []
    for part in formatted.split('_'):
        words.extend(part.split())

    # Process each word - strip leading zeros from numeric strings
    processed_words = []
    for word in words:
        if word.isdigit():
            # Strip leading zeros but preserve at least one digit
            processed_words.append(word.lstrip('0') or '0')
        else:
            processed_words.append(word.capitalize())

    # Join with spaces
    return ' '.join(processed_words)


def endpoint_name(endpoint: str) -> str:
    if endpoint in friendly_names:
        return friendly_names[endpoint]
    return title_name(endpoint)


def step_name(step: str, preserve: bool = False) -> str:
    _, number = step.split('_')
    return f"Step {number.lstrip('0')}"


def step_button(step: str, preserve: bool = False, revert_label: str = None) -> str:
    logger.debug(f"[format_step_button] Entry - step={step}, preserve={preserve}, revert_label={revert_label}")
    _, number = step.split('_')
    symbol = "⟲"if preserve else "↶"
    label = revert_label if revert_label else "Step"
    if revert_label:
        button_text = f"{symbol}\u00A0{label}"
    else:
        button_text = f"{symbol}\u00A0{label}\u00A0{number.lstrip('0')}"
    logger.debug(f"[format_step_button] Generated button text: {button_text}")
    return button_text


class SSEBroadcaster:
    def __init__(self):
        self.queue = asyncio.Queue()
        print("SSE Broadcaster initialized")

    async def generator(self):
        while True:
            try:
                message = await asyncio.wait_for(self.queue.get(), timeout=5.0)
                print(f"SSE sending: {message}")
                if message:
                    formatted = '\n'.join(f"data: {line}"for line in message.split('\n'))
                    yield f"{formatted}\n\n"
            except asyncio.TimeoutError:
                now = datetime.now()
                yield f"data: Test ping at {now}\n\n"

    async def send(self, message):
        print(f"Queueing message: {message}")
        await self.queue.put(message)


broadcaster = SSEBroadcaster()


def read_training(prompt_or_filename):
    if isinstance(prompt_or_filename, str) and prompt_or_filename.endswith('.md'):
        try:
            logger.debug(f"Loading prompt from training/{prompt_or_filename}")
            with open(f"training/{prompt_or_filename}", "r") as f:
                content = f.read()
                logger.debug(f"Successfully loaded prompt: {content[:100]}...")
                return content
        except FileNotFoundError:
            logger.warning(f"No training file found for {prompt_or_filename}")
            return f"No training content available for {prompt_or_filename.replace('.md', '')}"

    return prompt_or_filename


def hot_prompt_injection(prompt_or_filename):
    prompt = read_training(prompt_or_filename)
    append_to_conversation(prompt, role="system", quiet=True)
    return prompt


if MAX_LLM_RESPONSE_WORDS:
    limiter = f"in under {MAX_LLM_RESPONSE_WORDS} {TONE} words"
else:
    limiter = ""
global_conversation_history = deque(maxlen=MAX_CONVERSATION_LENGTH)
conversation = [{"role": "system", "content": read_training("system_prompt.md")}]


def append_to_conversation(message=None, role="user", quiet=False):
    logger.debug("Entering append_to_conversation function")
    if not quiet:
        preview = message[:50] + "..."if isinstance(message, str)else str(message)
        logger.debug(f"Appending to conversation. Role: {role}, Message: {preview}")
    if message is not None:
        if not global_conversation_history or global_conversation_history[0]['role'] != 'system':
            if not quiet:
                logger.debug("Adding system message to conversation history")
            global_conversation_history.appendleft(conversation[0])
        global_conversation_history.append({"role": role, "content": message})
        if not quiet:
            logger.debug(f"Message appended. New conversation history length: {len(global_conversation_history)}")
    logger.debug("Exiting Append to Conversation")
    return list(global_conversation_history)


def pipeline_operation(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        url = args[0] if args else None
        if not url:
            return func(self, *args, **kwargs)
        
        # Get the original state
        old_state = self._get_clean_state(url)
        
        # Execute the function
        result = func(self, *args, **kwargs)
        
        # Check for state changes
        new_state = self._get_clean_state(url)
        if old_state != new_state:
            # Calculate what changed
            changes = {k: new_state[k] for k in new_state if k not in old_state or old_state[k] != new_state[k]}
            
            if changes:
                # Get function name for better context
                operation = func.__name__
                
                # Log a summary at INFO level
                step_changes = [k for k in changes if not k.startswith('_')]
                if step_changes:
                    log.pipeline(f"Operation '{operation}' updated state", 
                                details=f"Steps: {', '.join(step_changes)}",
                                pipeline_id=url)
                
                # Log the detailed changes at DEBUG level only
                log.debug("pipeline", f"Pipeline '{url}' detailed changes", json.dumps(changes, indent=2))
        
        return result
    return wrapper


class Pipulate:
    """Central coordinator for pipelines and chat functionality.

    This class serves as the main interface for plugins to access
    shared functionality without relying on globals.
    
    # --- Core Architectural Patterns ---

    ## Workflow Step Chain Reaction Pattern

    Pipulate uses a two-level approach to ensuring reliable workflow progression:

    1. Initial Setup (run_all_cells): Creates placeholders with event-based triggers
       - First step: hx_trigger="load"
       - Subsequent steps: hx_trigger="stepComplete-{previous_step.id} from:{previous_step.id}"

    2. Step Implementation (explicit override): Each step's handlers EXPLICITLY trigger
       the next step when completing
       - GET handler (completed state): Returns Div with explicit hx_trigger="load"
       - POST handler (submit): Returns Div with explicit hx_trigger="load"

    This dual approach provides reliability across browsers and complex DOM structures.
    The explicit triggering pattern in step handlers is REQUIRED and should not be
    removed or refactored to rely solely on HTMX event bubbling.

    See 80_splice_workflow.py for the canonical implementation of this pattern.
    """
    PRESERVE_REFILL = True

    # Style constants
    ERROR_STYLE = "color: red;"
    SUCCESS_STYLE = "color: green;"
    # Button styles using PicoCSS classes instead of custom styles
    WARNING_BUTTON_STYLE = None  # Now using cls="secondary outline" instead
    PRIMARY_BUTTON_STYLE = None  # Now using cls="primary" instead
    SECONDARY_BUTTON_STYLE = None  # Now using cls="secondary" instead
    
    # Text style constants
    MUTED_TEXT_STYLE = "font-size: 0.9em; color: var(--pico-muted-color);"
    
    # Content style constants
    CONTENT_STYLE = "margin-top: 1vh; border-top: 1px solid var(--pico-muted-border-color); padding-top: 1vh;"
    TREE_CONTENT_STYLE = "padding: 10px; white-space: pre; text-align: left; font-size: 1.5vh;"
    CARD_STYLE = "background-color: var(--pico-card-background-color); border-radius: var(--pico-border-radius); margin-bottom: 2vh;"
    FINALIZED_CONTENT_STYLE = "margin-top: 0.5vh; padding: 0.5vh 0;"

    # Button labels
    UNLOCK_BUTTON_LABEL = "Unlock 🔓"  # Global label for unlock/unfinalize buttons

    def __init__(self, pipeline_table, chat_instance=None):
        """Initialize Pipulate with required dependencies.

        Args:
            pipeline_table: The database table for storing pipeline state
            chat_instance: Optional chat coordinator instance
        """
        self.table = pipeline_table
        self.chat = chat_instance
        # Initialize the message queue
        self.message_queue = self.OrderedMessageQueue()

    def append_to_history(self, message: str, role: str = "system", quiet: bool = True) -> None:
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
            quiet: Whether to suppress logging (defaults to True)
        """
        append_to_conversation(message, role=role, quiet=quiet)

    class OrderedMessageQueue:
        """A lightweight queue to ensure messages are delivered in order.

        This class creates a simple message queue that ensures messages are delivered
        in the exact order they are added, without requiring explicit delays between
        messages. It's used to fix the message streaming order issues.
        """

        def __init__(self):
            self.queue = []
            self._processing = False
            self._current_step = None
            self._step_completed = False

        def _get_workflow_context(self):
            """Get the current workflow context for the LLM."""
            if not self._current_step:
                return "[WORKFLOW STATE: Not yet started]"
            elif self._step_completed:
                return f"[WORKFLOW STATE: Step {self._current_step} completed]"
            else:
                return f"[WORKFLOW STATE: Waiting for Step {self._current_step} input]"

        async def add(self, pipulate, message, **kwargs):
            """Add a message to the queue and process if not already processing."""
            # Log the message to the logger
            logger.info(f"[🔄 WORKFLOW] {message}")
            
            # Escape URLs in the message by replacing : with ꞉ (a special colon character)
            # This prevents auto-linking while keeping the message readable
            if isinstance(message, str):
                message = message.replace("http:", "http꞉").replace("https:", "https꞉")
            
            # Determine the role based on kwargs or default to "system"
            role = kwargs.pop("role", "system")
            
            # Update workflow state based on message content
            if "Step " in message and "Please enter" in message:
                step_num = message.split("Step ")[1].split(":")[0]
                self._current_step = step_num
                self._step_completed = False
            elif "complete" in message.lower() and "step" in message.lower():
                self._step_completed = True
            
            # Add context marker based on message type/role
            context_message = message
            if role == "system":
                # For system messages (prompts, UI text), make it clear it's a prompt
                if "Please" in message or "Enter" in message or message.endswith("?"):
                    context_message = f"[PROMPT] {message}"
                else:
                    context_message = f"[INFO] {message}"
            elif role == "user":
                # For user messages, make it clear it's user input
                context_message = f"[USER INPUT] {message}"
            elif role == "assistant":
                # For assistant messages, make it clear it's a response
                context_message = f"[RESPONSE] {message}"
            
            # Add workflow state context before each message
            workflow_context = self._get_workflow_context()
            context_message = f"{workflow_context}\n{context_message}"
            
            # Add to conversation history with context
            append_to_conversation(context_message, role=role)
            
            # Queue the original message (without context marker) for UI display
            self.queue.append((pipulate, message, kwargs))
            if not self._processing:
                await self._process_queue()

        async def _process_queue(self):
            """Process all queued messages in order."""
            self._processing = True
            try:
                while self.queue:
                    pipulate, message, kwargs = self.queue.pop(0)
                    # Stream the message and capture any response
                    response = await pipulate.stream(message, **kwargs)
                    
                    # If there was a response and it's different from the input message,
                    # append it to conversation history as an assistant message with context
                    if response and response != message:
                        workflow_context = self._get_workflow_context()
                        append_to_conversation(f"{workflow_context}\n[RESPONSE] {response}", role="assistant")
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

        # Empty string case
        if not word:
            return word

        # Already singular cases
        if word.lower() in ('data', 'media', 'series', 'species', 'news'):
            return word

        # Common irregular plurals
        irregulars = {
            'children': 'child',
            'people': 'person',
            'men': 'man',
            'women': 'woman',
            'teeth': 'tooth',
            'feet': 'foot',
            'geese': 'goose',
            'mice': 'mouse',
            'criteria': 'criterion',
        }

        if word.lower() in irregulars:
            return irregulars[word.lower()]

        # Common suffix rules - ordered by specificity
        if word.lower().endswith('ies'):
            return word[:-3] + 'y'
        if word.lower().endswith('ves'):
            return word[:-3] + 'f'
        if word.lower().endswith('xes') or word.lower().endswith('sses') or word.lower().endswith('shes') or word.lower().endswith('ches'):
            return word[:-2]
        if word.lower().endswith('s') and not word.lower().endswith('ss'):
            return word[:-1]

        # Already singular
        return word

    def set_chat(self, chat_instance):
        """Set the chat instance after initialization."""
        self.chat = chat_instance

    def get_message_queue(self):
        """Return the message queue instance for ordered message delivery."""
        return self.message_queue

    def get_style(self, style_type):
        """Get a predefined style by type"""
        styles = {
            "error": self.ERROR_STYLE,
            "success": self.SUCCESS_STYLE,
            "warning_button": self.WARNING_BUTTON_STYLE,
            "primary_button": self.PRIMARY_BUTTON_STYLE,
            "secondary_button": self.SECONDARY_BUTTON_STYLE,
            "muted": self.MUTED_TEXT_STYLE
        }
        return styles.get(style_type, "")

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
        # Get profile_id from the global function
        profile_id = get_current_profile_id()

        # Get profile name from the global function
        profile_name = get_profile_name()

        # Get plugin name from the instance if provided
        plugin_name = None
        display_name = None

        if plugin_instance:
            # Try to get the display name first
            if hasattr(plugin_instance, 'DISPLAY_NAME'):
                display_name = plugin_instance.DISPLAY_NAME

            # Get the internal name
            if hasattr(plugin_instance, 'name'):
                plugin_name = plugin_instance.name
            elif hasattr(plugin_instance, '__class__'):
                plugin_name = plugin_instance.__class__.__name__

            # If we have a plugin_name but no display_name, try to get it from friendly_names
            if plugin_name and not display_name:
                if plugin_name in friendly_names:
                    display_name = friendly_names[plugin_name]
                else:
                    # Fall back to a title-cased version of plugin_name
                    display_name = title_name(plugin_name)

        return {
            'plugin_name': display_name or plugin_name,  # Prefer display name
            'internal_name': plugin_name,  # Keep internal name for reference if needed
            'profile_id': profile_id,
            'profile_name': profile_name
        }

    @pipeline_operation
    def initialize_if_missing(self, pkey: str, initial_step_data: dict = None) -> tuple[Optional[dict], Optional[Card]]:
        try:
            state = self.read_state(pkey)
            if state:
                return state, None
            now = self.get_timestamp()
            state = {"created": now, "updated": now}
            if initial_step_data:
                app_name = None
                if "app_name" in initial_step_data:
                    app_name = initial_step_data.pop("app_name")
                state.update(initial_step_data)
            self.table.insert({"pkey": pkey, "app_name": app_name if app_name else None, "data": json.dumps(state), "created": now, "updated": now})
            return state, None
        except:
            error_card = Card(H3("ID Already In Use"), P(f"The ID '{pkey}' is already being used by another workflow. Please try a different ID."), style=self.id_conflict_style())
            return None, error_card

    def read_state(self, pkey: str) -> dict:
        logger.debug(f"Reading state for pipeline: {pkey}")
        try:
            self.table.xtra(pkey=pkey)
            records = self.table()
            logger.debug(f"Records found: {records}")
            if records:
                logger.debug(f"First record type: {type(records[0])}")
                logger.debug(f"First record dir: {dir(records[0])}")
            if records and hasattr(records[0], 'data'):
                state = json.loads(records[0].data)
                logger.debug(f"Found state: {json.dumps(state, indent=2)}")
                return state
            logger.debug("No valid state found")
            return {}
        except Exception as e:
            logger.debug(f"Error reading state: {str(e)}")
            return {}

    def write_state(self, pkey: str, state: dict) -> None:
        state["updated"] = datetime.now().isoformat()
        payload = {"pkey": pkey, "data": json.dumps(state), "updated": state["updated"]}
        logger.debug(f"Update payload:\n{json.dumps(payload, indent=2)}")
        self.table.update(payload)
        verification = self.read_state(pkey)
        logger.debug(f"Verification read:\n{json.dumps(verification, indent=2)}")

    def format_links_in_text(self, text):
        """
        Convert plain URLs in text to clickable HTML links.
        Safe for logging but renders as HTML in the UI.
        """
        import re
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'

        def replace_url(match):
            url = match.group(0)
            return f'<a href="{url}" target="_blank">{url}</a>'

        return re.sub(url_pattern, replace_url, text)

    async def stream(self, message, verbatim=False, role="user",
                     spaces_before=None, spaces_after=1,
                     simulate_typing=True):
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
                    await chat.broadcast(" <br>\n")

            if verbatim:
                if simulate_typing:
                    # Split into words and simulate typing for verbatim messages
                    words = message.split(' ')
                    for i, word in enumerate(words):
                        await chat.broadcast(word)
                        if i < len(words) - 1:  # Don't add space after last word
                            await chat.broadcast(' ')
                        await asyncio.sleep(0.005)  # Adjust timing as needed
                else:
                    await chat.broadcast(message)

                response_text = message
            else:
                response_text = ""
                async for chunk in chat_with_llm(MODEL, conversation_history):
                    await chat.broadcast(chunk)
                    response_text += chunk

            if spaces_after:
                for _ in range(spaces_after):
                    await chat.broadcast(" <br>\n")

            append_to_conversation(response_text, "assistant")
            logger.debug(f"Message streamed: {response_text}")
            return message
        except Exception as e:
            logger.error(f"Error in pipulate.stream: {e}")
            traceback.print_exc()
            raise

    def revert_control(
        self,
        step_id: str,
        app_name: str,
        steps: list,
        message: str = None,
        target_id: str = None,
        revert_label: str = None,
        remove_padding: bool = False  # New parameter to control article padding
    ):
        """
        Create a UI control for reverting to a previous workflow step.

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
        pipeline_id = db.get("pipeline_id", "")
        finalize_step = steps[-1]

        if pipeline_id:
            final_data = self.get_step_data(pipeline_id, finalize_step.id, {})
            if finalize_step.done in final_data:
                return None

        step = next(s for s in steps if s.id == step_id)
        refill = getattr(step, 'refill', False)

        if not target_id:
            target_id = f"{app_name}-container"

        # These are very pretty revert buttons. Do not change them.
        default_style = (
            "background-color: var(--pico-del-color);"
            "display: inline-flex;"
            "padding: 0.5rem 0.5rem;"
            "border-radius: 4px;"
            "font-size: 0.85rem;"
            "cursor: pointer;"
            "margin: 0;"
            "line-height: 1;"
            "align-items: center;"
        )

        form = Form(
            Input(
                type="hidden",
                name="step_id",
                value=step_id
            ),
            Button(
                step_button(step_id, refill, revert_label),
                type="submit",
                style=default_style
            ),
            hx_post=f"/{app_name}/revert",
            hx_target=f"#{target_id}",
            hx_swap="outerHTML"
        )

        if not message:
            return form

        # Base style for the article
        article_style = (
            "display: flex; "
            "align-items: center; "
            "justify-content: space-between; "
            "background-color: var(--pico-card-background-color);"
        )
        
        # Add padding: 0 if remove_padding is True
        if remove_padding:
            article_style += " padding: 0;"

        return Card(
            Div(
                message,
                style="flex: 1;"
            ),
            Div(
                form,
                style="flex: 0;"
            ),
            style=article_style
        )

    def widget_container(
        self,
        step_id: str,
        app_name: str,
        steps: list,
        message: str = None,
        widget=None,
        target_id: str = None,
        revert_label: str = None,
        widget_style=None
    ):
        """
        Create a standardized container for widgets, visualizations, or any dynamic content.
        
        This is the core pattern for displaying rich content below workflow steps while
        maintaining consistent styling and proper DOM targeting for dynamic updates.
        
        The container provides:
        1. Consistent padding/spacing with the revert controls
        2. Unique DOM addressing for targeted updates
        3. Support for both function-based widgets and AnyWidget components
        4. Standard styling that can be overridden when needed
        
        Args:
            step_id: The ID of the step this widget belongs to
            app_name: The workflow app name
            steps: List of Step namedtuples defining the workflow
            message: Optional message to display in the revert control
            widget: The widget/visualization to display (function result or AnyWidget)
            target_id: Optional target for HTMX updates
            revert_label: Optional custom label for the revert button
            widget_style: Optional custom style for the widget container
            
        Returns:
            Div: A FastHTML container with revert control and widget content
        """
        # Get the revert control with padding removed for proper alignment
        revert_row = self.revert_control(
            step_id=step_id,
            app_name=app_name,
            steps=steps,
            message=message,
            target_id=target_id,
            revert_label=revert_label,
            remove_padding=True  # Remove padding for alignment
        )
        
        # If no widget or in finalized state, just return the standard control
        if widget is None or revert_row is None:
            return revert_row
        
        # Use the content style constant as the default
        applied_style = widget_style or self.CONTENT_STYLE
        
        # Create a container with the revert row and widget that looks like a single card
        return Div(
            revert_row,
            Div(
                widget,
                style=applied_style,
                # Unique ID for targeting dynamic updates
                id=f"{step_id}-widget-{hash(str(widget))}"
            ),
            id=f"{step_id}-content",
            style=(
                "background-color: var(--pico-card-background-color); "
                "border-radius: var(--pico-border-radius); "
                "margin-bottom: 2vh; "
                "padding: 1rem;"
            )
        )

    # Keep tree_display as a standard widget function that can be passed to widget_container
    def tree_display(self, content):
        """
        Create a styled display for file paths that can show either a tree or box format.
        
        This is an example of a standard widget function that can be passed to widget_container.
        It demonstrates the pattern for creating reusable, styled components that maintain
        consistent spacing and styling when displayed in the workflow.
        
        Args:
            content: The content to display (either tree-formatted or plain path)
            
        Returns:
            Pre: A Pre component with appropriate styling
        """
        # Check if content is tree-formatted (contains newlines and tree characters)
        is_tree = '\n' in content and ('└─' in content or '├─' in content)
        
        if is_tree:
            # Tree display - use monospace font and preserve whitespace
            return Pre(
                content,
                style=(
                    "font-family: monospace; "
                    "white-space: pre; "
                    "margin: 0; "  # Remove margin to let container control spacing
                    "padding: 0.5rem; "
                    "border-radius: 4px; "
                    "background-color: var(--pico-card-sectionning-background-color);"  # Use PicoCSS variable
                )
            )
        else:
            # Box display - use a blue box with the path
            return Pre(
                content,
                style=(
                    "font-family: system-ui; "
                    "white-space: pre-wrap; "
                    "margin: 0; "  # Remove margin to let container control spacing
                    "padding: 0.5rem 1rem; "
                    "border-radius: 4px; "
                    "background-color: #e3f2fd; "
                    "color: #1976d2; "
                    "border: 1px solid #bbdefb;"
                )
            )

    def finalized_content(
        self,
        message: str,
        content=None,
        heading_tag=H4,
        content_style=None
    ):
        """
        Create a finalized step display with optional additional content.
        
        This is the companion to revert_control_advanced for finalized workflows,
        providing consistent styling for both states.
        
        Args:
            message: Message to display (typically including a 🔒 lock icon)
            content: FastHTML component to display below the message
            heading_tag: The tag to use for the message (default: H4)
            content_style: Optional custom style for the content container
            
        Returns:
            Card: A FastHTML Card component for the finalized state
        """
        if content is None:
            return Card(message)
        
        # Use the finalized content style constant as the default
        applied_style = content_style or self.FINALIZED_CONTENT_STYLE
        
        return Card(
            heading_tag(message),
            Div(
                content,
                style=applied_style
            ),
            style=(
                "background-color: var(--pico-card-background-color); "
                "border-radius: var(--pico-border-radius); "
                "margin-bottom: 2vh; "
                "padding: 1rem;"  # Add consistent padding
            )
        )

    def wrap_with_inline_button(
        self,
        input_element: Input,
        button_label: str = "Next ▸",
        button_class: str = "primary"
    ) -> Div:
        return Div(
            input_element,
            Button(
                button_label,
                type="submit",
                cls=button_class,
                style=(
                    "display: inline-block;"
                    "cursor: pointer;"
                    "width: auto !important;"
                    "white-space: nowrap;"
                )
            ),
            style="display: flex; align-items: center; gap: 0.5rem;"
        )

    async def get_state_message(self, pkey: str, steps: list, messages: dict) -> str:
        state = self.read_state(pkey)
        logger.debug(f"\nDEBUG [{pkey}] State Check:")
        logger.debug(json.dumps(state, indent=2))
        for step in reversed(steps):
            if step.id not in state:
                continue
            if step.done == "finalized":
                if step.done in state[step.id]:
                    return self._log_message("finalized", messages["finalize"]["complete"])
                return self._log_message("ready to finalize", messages["finalize"]["ready"])
            step_data = state[step.id]
            step_value = step_data.get(step.done)
            if step_value:
                msg = messages[step.id]["complete"]
                msg = msg.format(step_value)if "{}" in msg else msg
                return self._log_message(f"{step.id} complete ({step_value})", msg)
        return self._log_message("new pipeline", messages["new"])

    def _log_message(self, state_desc: str, message: str) -> str:
        safe_state = state_desc.replace("<", "\\<").replace(">", "\\>")
        safe_message = message.replace("<", "\\<").replace(">", "\\>")
        logger.debug(f"State: {safe_state}, Message: {safe_message}")
        append_to_conversation(message, role="system", quiet=True)
        return message

    @pipeline_operation
    def get_step_data(self, pkey: str, step_id: str, default=None) -> dict:
        state = self.read_state(pkey)
        return state.get(step_id, default or {})

    async def clear_steps_from(self, pipeline_id: str, step_id: str, steps: list) -> dict:
        state = self.read_state(pipeline_id)
        start_idx = next((i for i, step in enumerate(steps)if step.id == step_id), -1)
        if start_idx == -1:
            logger.error(f"[clear_steps_from] Step {step_id} not found in steps list")
            return state
        for step in steps[start_idx + 1:]:
            if (not self.PRESERVE_REFILL or not step.refill) and step.id in state:
                logger.debug(f"[clear_steps_from] Removing step {step.id}")
                del state[step.id]
        self.write_state(pipeline_id, state)
        return state

    # Add this method to the Pipulate class
    def id_conflict_style(self):
        """Return style for ID conflict error messages"""
        return "background-color: #ffdddd; color: #990000; padding: 10px; border-left: 5px solid #990000;"

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
        # Get context for the key parts
        context = self.get_plugin_context(plugin_instance)
        # Use the display name (plugin_name) instead of internal_name for more user-friendly keys
        plugin_name = context['plugin_name'] or getattr(plugin_instance, 'DISPLAY_NAME', None) or getattr(plugin_instance, 'app_name', 'unknown')
        profile_name = context['profile_name'] or "default"

        # Get the app_name for the database query - this is crucial for proper filtering
        app_name = getattr(plugin_instance, 'app_name', None)

        # Format the prefix parts - replace spaces with underscores but preserve case
        profile_part = profile_name.replace(" ", "_")
        plugin_part = plugin_name.replace(" ", "_")
        prefix = f"{profile_part}-{plugin_part}-"

        # If no user input is provided, generate an auto-incrementing number
        if user_input is None:
            # First, reset any lingering filters
            self.table.xtra()

            # Then filter by app_name to ensure each workflow has its own number sequence
            self.table.xtra(app_name=app_name)

            # Get records for this specific app (workflow type)
            app_records = list(self.table())

            # Find records with the current prefix
            matching_records = [record.pkey for record in app_records
                                if record.pkey.startswith(prefix)]

            # Extract numeric values from the third part of the key
            numeric_suffixes = []
            for record_key in matching_records:
                # Extract the user part (everything after the prefix)
                rec_user_part = record_key.replace(prefix, "")
                # Check if it's purely numeric
                if rec_user_part.isdigit():
                    numeric_suffixes.append(int(rec_user_part))

            # Determine the next number (max + 1, or 1 if none exist)
            next_number = 1
            if numeric_suffixes:
                next_number = max(numeric_suffixes) + 1

            # Format with leading zeros for numbers less than 100
            if next_number < 100:
                user_part = f"{next_number:02d}"
            else:
                user_part = str(next_number)
        else:
            # Use the provided input, with potential formatting
            if isinstance(user_input, int) or (isinstance(user_input, str) and user_input.isdigit()):
                # It's a number, so format it if needed
                number = int(user_input)
                if number < 100:
                    user_part = f"{number:02d}"
                else:
                    user_part = str(number)
            else:
                # Not a number, use as is
                user_part = str(user_input)

        # Create the full key
        full_key = f"{prefix}{user_part}"

        return (full_key, prefix, user_part)

    def parse_pipeline_key(self, pipeline_key):
        """Parse a pipeline key into its component parts.

        Args:
            pipeline_key: The full pipeline key to parse

        Returns:
            dict: Contains profile_part, plugin_part, and user_part components
        """
        parts = pipeline_key.split('-', 2)  # Split into max 3 parts

        if len(parts) < 3:
            # Not enough parts for a valid key
            return {
                'profile_part': parts[0] if len(parts) > 0 else "",
                'plugin_part': parts[1] if len(parts) > 1 else "",
                'user_part': ""
            }

        return {
            'profile_part': parts[0],
            'plugin_part': parts[1],
            'user_part': parts[2]
        }

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
            # Return an empty datalist to clear all options
            return Datalist(
                id=datalist_id,
                _hx_swap_oob="true"  # Out-of-band swap to update the dropdown
            )
        else:
            # Create a datalist with the provided options
            return Datalist(
                *[Option(value=opt) for opt in options],
                id=datalist_id,
                _hx_swap_oob="true"  # Out-of-band swap to update the dropdown
            )

    def run_all_cells(self, app_name, steps):
        """
        Create a series of HTMX divs that will trigger a chain reaction of loading all steps.
        
        This method sets up the initial placeholders with event-based triggering, where:
        
        1. The first step loads immediately on trigger="load"
        2. Subsequent steps are configured to wait for 'stepComplete-{previous_step_id}' events
        
        IMPORTANT IMPLEMENTATION NOTE: 
        While this method establishes event-based triggers, the standard workflow pattern in 
        this codebase (see 80_splice_workflow.py) explicitly overrides this with 
        direct 'hx_trigger="load"' attributes in completed step views. This explicit 
        triggering pattern is preferred for reliability over event bubbling in complex workflows.
        
        This dual approach (event-based setup + explicit triggers in steps) ensures the chain
        reaction works consistently across browsers and in complex DOM structures.

        Args:
            app_name: The name of the workflow app
            steps: List of Step namedtuples defining the workflow

        Returns:
            list: List of Div elements configured with HTMX attributes for sequential loading
        """        
        cells = []
        for i, step in enumerate(steps):
            # First step loads immediately, subsequent steps wait for previous to complete
            trigger = ("load" if i == 0 else f"stepComplete-{steps[i - 1].id} from:{steps[i - 1].id}")
            cells.append(
                Div(
                    id=step.id,
                    hx_get=f"/{app_name}/{step.id}",
                    hx_trigger=trigger,
                    hx_swap="outerHTML"
                )
            )
        return cells

    def rebuild(self, app_name, steps):
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
        # Get the placeholders for all steps
        placeholders = self.run_all_cells(app_name, steps)

        # Return a container with all placeholders
        return Div(
            *placeholders,
            id=f"{app_name}-container"
        )

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
        error_msg = ""

        # Default validation (non-empty)
        if not value.strip():
            is_valid = False
            error_msg = f"{step_show} cannot be empty"

        # Custom validation if provided
        if is_valid and custom_validator:
            custom_valid, custom_error = custom_validator(value)
            if not custom_valid:
                is_valid = False
                error_msg = custom_error

        if not is_valid:
            return False, error_msg, P(error_msg, style=self.get_style("error"))

        return True, "", None

    async def update_step_state(self, pipeline_id, step_id, step_value, steps, clear_previous=True):
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
            if "_revert_target" in state:
                del state["_revert_target"]
            self.write_state(pipeline_id, state)

        # Return the step value for confirmation message
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
        return next_step_id == "finalize"

    def create_step_navigation(self, step_id, step_index, steps, app_name, processed_val):
        """
        Create the standard navigation controls after a step submission.

        This helper generates a consistent UI pattern for step navigation that includes:
        1. A revert control showing the current step's value
        2. An HTMX-enabled div that EXPLICITLY triggers loading the next step using
           hx_trigger="load" (preferred over relying on HTMX event bubbling)
        
        IMPLEMENTATION NOTE: This explicit triggering pattern is critical for
        reliable workflow progression and should be maintained in all workflow steps.

        Args:
            step_id: The current step ID
            step_index: Index of current step in steps list
            steps: The steps list
            app_name: The workflow app name
            processed_val: The processed value to display

        Returns:
            Div: A FastHTML Div component with revert control and next step trigger
        """
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None

        return Div(
            self.revert_control(
                step_id=step_id,
                app_name=app_name,
                message=f"{step.show}: {processed_val}",
                steps=steps
            ),
            Div(
                id=next_step_id,
                hx_get=f"/{app_name}/{next_step_id}",
                hx_trigger="load"  # CRITICAL: Explicit trigger for reliable chain reaction
            ) if next_step_id else Div()
        )

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
        state[step_id] = {"finalized": True}
        self.write_state(pipeline_id, state)

        # Get step_messages from the plugin instance if provided
        step_messages = {}
        if plugin_instance and hasattr(plugin_instance, 'step_messages'):
            step_messages = plugin_instance.step_messages

        message = await self.get_state_message(pipeline_id, steps, step_messages)
        await self.stream(message, verbatim=True)

        return self.rebuild(app_name, steps)

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

        # Mark as finalized
        if "finalize" not in state:
            state["finalize"] = {}

        state["finalize"]["finalized"] = True
        state["updated"] = datetime.now().isoformat()

        # Apply additional updates if provided
        if state_update:
            state.update(state_update)

        # Save state
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

        # Remove finalization
        if "finalize" in state:
            del state["finalize"]

        state["updated"] = datetime.now().isoformat()

        # Save state
        self.write_state(pipeline_id, state)

        return state


async def chat_with_llm(MODEL: str, messages: list, base_app=None) -> AsyncGenerator[str, None]:
    url = "http://localhost:11434/api/chat"
    payload = {"MODEL": MODEL, "messages": messages, "stream": True}
    accumulated_response = []
    table = Table(title="User Input")
    table.add_column("Role", style="cyan")
    table.add_column("Content", style="orange3")
    if messages:
        last_message = messages[-1]
        role = last_message.get("role", "unknown")
        content = last_message.get("content", "")
        if isinstance(content, dict):
            content = json.dumps(content, indent=2, ensure_ascii=False)
        table.add_row(role, content)
    console.print(table)
    try:
        async with aiohttp.ClientSession()as session:
            async with session.post(url, json=payload)as response:
                if response.status != 200:
                    error_text = await response.text()
                    error_msg = f"Ollama server error: {error_text}"
                    accumulated_response.append(error_msg)
                    yield error_msg
                    return
                yield "\n"
                async for line in response.content:
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        if chunk.get("done", False):
                            print("\n", end='', flush=True)
                            final_response = "".join(accumulated_response)
                            table = Table(title="Chat Response")
                            table.add_column("Accumulated Response")
                            table.add_row(final_response, style="green")
                            console.print(table)
                            break
                        if content := chunk.get("message", {}).get("content", ""):
                            if content.startswith('\n') and accumulated_response and accumulated_response[-1].endswith('\n'):
                                content = '\n' + content.lstrip('\n')
                            else:
                                content = re.sub(r'\n\s*\n\s*', '\n\n', content)
                                content = re.sub(r'([.!?])\n', r'\1 ', content)
                                content = re.sub(r'\n ([^\s])', r'\n\1', content)
                            print(content, end='', flush=True)
                            accumulated_response.append(content)
                            yield content
                    except json.JSONDecodeError:
                        continue
    except aiohttp.ClientConnectorError as e:
        error_msg = "Unable to connect to Ollama server. Please ensure Ollama is running."
        accumulated_response.append(error_msg)
        yield error_msg
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        accumulated_response.append(error_msg)
        yield error_msg


def get_button_style(button_type="default"):
    """Return button style string based on type."""
    if button_type == "warning":
        return "background-color: var(--pico-primary-background); color: #f66;"
    elif button_type == "primary":
        return "background-color: var(--pico-primary-background); color: #4CAF50;"
    # etc.


def get_current_profile_id():
    """Get the current profile ID, defaulting to the first profile if none is selected."""
    profile_id = db.get("last_profile_id")

    if profile_id is None:
        logger.debug("No last_profile_id found. Finding first available profile.")
        first_profiles = profiles(order_by='id', limit=1)
        if first_profiles:
            profile_id = first_profiles[0].id
            db["last_profile_id"] = profile_id
            logger.debug(f"Set default profile ID to {profile_id}")
        else:
            logger.warning("No profiles found in the database")

    return profile_id


def create_chat_scripts(sortable_selector='.sortable', ghost_class='blue-background-class'):
    # Instead of embedding the script, return a script tag that loads an external file
    # and initializes with the parameters
    init_script = f"""
    document.addEventListener('DOMContentLoaded', (event) => {{
        // Initialize with parameters
        if (window.initializeChatScripts) {{
            window.initializeChatScripts({{
                sortableSelector: '{sortable_selector}',
                ghostClass: '{ghost_class}'
            }});
        }}
    }});
    """
    return Script(src='/static/chat-scripts.js'), Script(init_script), Link(rel='stylesheet', href='/static/chat-styles.css')


class BaseCrud:
    """
    CRUD base class for all Apps. The CRUD is DRY and the Workflows are WET!
    """

    def __init__(self, name, table, toggle_field=None, sort_field=None, sort_dict=None, pipulate_instance=None, chat_function=None):
        self.name = name
        self.table = table
        self.toggle_field = toggle_field
        self.sort_field = sort_field
        self.item_name_field = 'name'
        self.sort_dict = sort_dict or {'id': 'id', sort_field: sort_field}
        self.pipulate_instance = pipulate_instance
        # Create a safer version of send_message
        import asyncio
        import inspect
        
        def safe_send_message(message, verbatim=True):
            if not self.pipulate_instance:
                return
                
            try:
                stream_method = self.pipulate_instance.stream
                if inspect.iscoroutinefunction(stream_method):
                    return asyncio.create_task(
                        stream_method(message, verbatim=verbatim, spaces_after=1)
                    )
                else:
                    # Not async, but needs to be called directly
                    return stream_method(message, verbatim=verbatim, spaces_after=1)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error in send_message: {e}")
                return None
                
        self.send_message = safe_send_message

    def register_routes(self, rt):
        rt(f'/{self.name}', methods=['POST'])(self.insert_item)
        rt(f'/{self.name}/{{item_id}}', methods=['POST'])(self.update_item)
        rt(f'/{self.name}/delete/{{item_id}}', methods=['DELETE'])(self.delete_item)
        rt(f'/{self.name}/toggle/{{item_id}}', methods=['POST'])(self.toggle_item)
        rt(f'/{self.name}_sort', methods=['POST'])(self.sort_items)

    def get_action_url(self, action, item_id):
        return f"/{self.name}/{action}/{item_id}"

    def render_item(self, item):
        return Li(
            A(
                "🗑",
                href="#",
                hx_swap="outerHTML",
                hx_delete=f"/task/delete/{item.id}",
                hx_target=f"#todo-{item.id}",
                _class="delete-icon",
                style="cursor: pointer; display: inline;"
            ),
            Input(
                type="checkbox",
                checked="1" if item.done else "0",
                hx_post=f"/task/toggle/{item.id}",
                hx_swap="outerHTML",
                hx_target=f"#todo-{item.id}"
            ),
            A(
                item.name,
                href="#",
                _class="todo-title",
                style="text-decoration: none; color: inherit;"
            ),
            data_id=item.id,
            data_priority=item.priority,
            id=f"todo-{item.id}",
            style="list-style-type: none;"
        )

    async def delete_item(self, request, item_id: int):
        try:
            item = self.table[item_id]
            item_name = getattr(item, self.item_name_field, 'Item')
            self.table.delete(item_id)
            logger.debug(f"Deleted item ID: {item_id}")
            action_details = f"The {self.name} item '{item_name}' was removed."
            prompt = action_details
            self.send_message(prompt, verbatim=True)

            # Add a trigger to refresh the profile menu
            response = HTMLResponse("")
            response.headers["HX-Trigger"] = json.dumps({"refreshProfileMenu": {}})
            return response
        except Exception as e:
            error_msg = f"Error deleting item: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while deleting {self.name} (ID: {item_id}): {error_msg}"
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            return str(e), 500

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

            # Get the profile HTML representation
            rendered_profile = self.render_item(updated_item)
            logger.debug(f"[DEBUG] Rendered profile type: {type(rendered_profile)}")

            # Convert FT object to HTML string using to_xml
            html_content = to_xml(rendered_profile)
            logger.debug(f"[DEBUG] HTML content: {html_content[:100]}...")

            return HTMLResponse(html_content)
        except Exception as e:
            error_msg = f"Error toggling item: {str(e)}"
            logger.error(error_msg)
            action_details = f"an error occurred while toggling {self.name} (ID: {item_id}): {error_msg}"
            return str(e), 500

    async def sort_items(self, request):
        """Override the BaseCrud sort_items to also refresh the profile menu"""
        try:
            logger.debug(f"Received request to sort {self.name}.")
            values = await request.form()
            items = json.loads(values.get('items', '[]'))
            logger.debug(f"Parsed items: {items}")
            changes = []
            sort_dict = {}
            for item in items:
                item_id = int(item['id'])
                priority = int(item['priority'])
                self.table.update(id=item_id, **{self.sort_field: priority})
                item_name = getattr(self.table[item_id], self.item_name_field, 'Item')
                sort_dict[item_id] = priority
                changes.append(f"'{item_name}' moved to position {priority}")
            changes_str = '; '.join(changes)
            action_details = f"The {self.name} items were reordered: {changes_str}"
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            logger.debug(f"{self.name.capitalize()} order updated successfully")

            # Add a trigger to refresh the profile menu
            response = HTMLResponse("")
            response.headers["HX-Trigger"] = json.dumps({"refreshProfileMenu": {}})
            return response
        except json.JSONDecodeError as e:
            error_msg = f"Invalid data format: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while sorting {self.name} items: {error_msg}"
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            return "Invalid data format", 400
        except Exception as e:
            error_msg = f"Error updating {self.name} order: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while sorting {self.name} items: {error_msg}"
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            return str(e), 500

    async def insert_item(self, request):
        try:
            logger.debug(f"[DEBUG] Starting insert_item for {self.name}")
            form = await request.form()
            logger.debug(f"[DEBUG] Form data: {dict(form)}")
            new_item_data = self.prepare_insert_data(form)
            if not new_item_data:
                logger.debug("[DEBUG] No new_item_data, returning empty")
                return ''
            new_item = await self.create_item(**new_item_data)
            logger.debug(f"[DEBUG] Created new item: {new_item}")
            item_name = getattr(new_item, self.item_name_field, 'Item')
            action_details = f"A new {self.name} item '{item_name}' was added."
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            rendered = self.render_item(new_item)
            logger.debug(f"[DEBUG] Rendered item type: {type(rendered)}")
            logger.debug(f"[DEBUG] Rendered item content: {rendered}")
            return rendered
        except Exception as e:
            error_msg = f"Error inserting {self.name}: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while adding a new {self.name}: {error_msg}"
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            return str(e), 500

    async def update_item(self, request, item_id: int):
        """Override the BaseCrud update_item to handle FastHTML objects properly"""
        try:
            form = await request.form()
            update_data = self.prepare_update_data(form)
            if not update_data:
                return ''
            item = self.table[item_id]
            before_state = item.__dict__.copy()
            for key, value in update_data.items():
                setattr(item, key, value)
            updated_item = self.table.update(item)
            after_state = updated_item.__dict__
            change_dict = {}
            for key in update_data.keys():
                if before_state.get(key) != after_state.get(key):
                    change_dict[key] = after_state.get(key)
            changes = [f"{key} changed from '{before_state.get(key)}' to '{after_state.get(key)}'"for key in update_data.keys()if before_state.get(key) != after_state.get(key)]
            changes_str = '; '.join(changes)
            item_name = getattr(updated_item, self.item_name_field, 'Item')
            action_details = f"The {self.name} item '{item_name}' was updated. Changes: {self.pipulate_instance.fmt(changes_str)}"
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            logger.debug(f"Updated {self.name} item {item_id}")

            # Get the profile HTML representation
            rendered_profile = self.render_item(updated_item)
            logger.debug(f"[DEBUG] Rendered profile type: {type(rendered_profile)}")

            # Convert FT object to HTML string using to_xml
            html_content = to_xml(rendered_profile)
            logger.debug(f"[DEBUG] HTML content: {html_content[:100]}...")

            return HTMLResponse(html_content)
        except Exception as e:
            error_msg = f"Error updating {self.name} {item_id}: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while updating {self.name} (ID: {item_id}): {error_msg}"
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            return str(e), 500

    async def create_item(self, **kwargs):
        try:
            logger.debug(f"Creating new {self.name} with data: {kwargs}")
            new_item = self.table.insert(kwargs)
            logger.debug(f"Created new {self.name}: {new_item}")
            return new_item
        except Exception as e:
            logger.error(f"Error creating {self.name}: {str(e)}")
            raise e

    def prepare_insert_data(self, form):
        raise NotImplementedError("Subclasses must implement prepare_insert_data")

    def prepare_update_data(self, form):
        raise NotImplementedError("Subclasses must implement prepare_update_data")


class ProfileApp(BaseCrud):
    def __init__(self, table, pipulate_instance=None):
        super().__init__(
            name=table.name,
            table=table,
            toggle_field='active',
            sort_field='priority',
            pipulate_instance=pipulate_instance
        )
        self.item_name_field = 'name'
        logger.debug(f"Initialized ProfileApp with name={table.name}")

    def render_item(self, profile):
        return render_profile(profile)

    async def insert_item(self, request):
        """Override the BaseCrud insert_item to also refresh the profile menu"""
        try:
            logger.debug(f"[DEBUG] Starting ProfileApp insert_item")
            form = await request.form()
            logger.debug(f"[DEBUG] Form data: {dict(form)}")
            new_item_data = self.prepare_insert_data(form)
            if not new_item_data:
                logger.debug("[DEBUG] No new_item_data, returning empty")
                return ''

            # Create the new profile
            new_profile = await self.create_item(**new_item_data)
            logger.debug(f"[DEBUG] Created new profile: {new_profile}")
            profile_name = getattr(new_profile, self.item_name_field, 'Profile')

            # Log the action
            action_details = f"A new {self.name} '{profile_name}' was added."
            prompt = action_details
            self.send_message(prompt, verbatim=True)

            # Render the new profile item
            rendered_profile = self.render_item(new_profile)
            logger.debug(f"[DEBUG] Rendered profile: {rendered_profile}")

            # Combine the rendered profile with an HTMX trigger to refresh the menu
            response = HTMLResponse(str(to_xml(rendered_profile)))
            response.headers["HX-Trigger"] = json.dumps({"refreshProfileMenu": {}})

            return response
        except Exception as e:
            error_msg = f"Error inserting {self.name}: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while adding a new {self.name}: {error_msg}"
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            return str(e), 500

    async def toggle_item(self, request, item_id: int):
        """Override the BaseCrud toggle_item to properly handle FastHTML objects"""
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

            # Get the profile HTML representation
            rendered_profile = self.render_item(updated_item)
            logger.debug(f"[DEBUG] Rendered profile type: {type(rendered_profile)}")

            # Add a trigger to refresh the profile menu
            response = HTMLResponse(str(to_xml(rendered_profile)))
            response.headers["HX-Trigger"] = json.dumps({"refreshProfileMenu": {}})
            return response
        except Exception as e:
            error_msg = f"Error toggling item: {str(e)}"
            logger.error(error_msg)
            action_details = f"an error occurred while toggling {self.name} (ID: {item_id}): {error_msg}"
            return str(e), 500

    async def update_item(self, request, item_id: int):
        """Override the BaseCrud update_item to properly handle FastHTML objects"""
        try:
            form = await request.form()
            update_data = self.prepare_update_data(form)
            if not update_data:
                return ''
            item = self.table[item_id]
            before_state = item.__dict__.copy()
            for key, value in update_data.items():
                setattr(item, key, value)
            updated_item = self.table.update(item)
            after_state = updated_item.__dict__
            change_dict = {}
            for key in update_data.keys():
                if before_state.get(key) != after_state.get(key):
                    change_dict[key] = after_state.get(key)
            changes = [f"{key} changed from '{before_state.get(key)}' to '{after_state.get(key)}'"for key in update_data.keys()if before_state.get(key) != after_state.get(key)]
            changes_str = '; '.join(changes)
            item_name = getattr(updated_item, self.item_name_field, 'Item')
            action_details = f"The {self.name} item '{item_name}' was updated. Changes: {self.pipulate_instance.fmt(changes_str)}"
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            logger.debug(f"Updated {self.name} item {item_id}")

            # Get the profile HTML representation
            rendered_profile = self.render_item(updated_item)
            logger.debug(f"[DEBUG] Rendered profile type: {type(rendered_profile)}")

            # Add a trigger to refresh the profile menu if the name field was updated
            response = HTMLResponse(str(to_xml(rendered_profile)))
            if 'name' in change_dict:
                response.headers["HX-Trigger"] = json.dumps({"refreshProfileMenu": {}})

            return response
        except Exception as e:
            error_msg = f"Error updating {self.name} {item_id}: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while updating {self.name} (ID: {item_id}): {error_msg}"
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            return str(e), 500

    def prepare_insert_data(self, form):
        profile_name = form.get('profile_name', '').strip()
        if not profile_name:
            return ''
        max_priority = max(
            (p.priority or 0 for p in self.table()),
            default=-1
        ) + 1
        return {
            "name": profile_name,
            "real_name": form.get('profile_real_name', '').strip(),
            "address": form.get('profile_address', '').strip(),
            "code": form.get('profile_code', '').strip(),
            "active": True,
            "priority": max_priority,
        }

    def prepare_update_data(self, form):
        profile_name = form.get('profile_name', '').strip()
        if not profile_name:
            return ''
        return {
            "name": profile_name,
            "real_name": form.get('profile_real_name', '').strip(),
            "address": form.get('profile_address', '').strip(),
            "code": form.get('profile_code', '').strip(),
        }


def render_profile(profile):
    def count_records_with_xtra(table_handle, xtra_field, xtra_value):
        table_handle.xtra(**{xtra_field: xtra_value})
        count = len(table_handle())
        logger.debug(f"Counted {count} records in table for {xtra_field} = {xtra_value}")
        return count

    delete_icon_visibility = 'inline'
    delete_url = profile_app.get_action_url('delete', profile.id)
    toggle_url = profile_app.get_action_url('toggle', profile.id)

    delete_icon = A(
        '🗑',
        hx_delete=delete_url,
        hx_target=f'#profile-{profile.id}',
        hx_swap='outerHTML',
        style=f"cursor: pointer; display: {delete_icon_visibility}; text-decoration: none; margin-left: 10px;",
        cls="delete-icon"
    )

    active_checkbox = Input(
        type="checkbox",
        name="active" if profile.active else None,
        checked=profile.active,
        hx_post=toggle_url,
        hx_target=f'#profile-{profile.id}',
        hx_swap="outerHTML",
        style="margin-right: 5px;"
    )

    update_form = Form(
        Group(
            Input(
                type="text",
                name="profile_name",
                value=profile.name,
                placeholder="Name",
                id=f"name-{profile.id}"
            ),
            Input(
                type="text",
                name="profile_real_name",
                value=profile.real_name,
                placeholder="Real Name",
                id=f"real_name-{profile.id}"
            ),
            Input(
                type="text",
                name="profile_address",
                value=profile.address,
                placeholder=PLACEHOLDER_ADDRESS,
                id=f"address-{profile.id}"
            ),
            Input(
                type="text",
                name="profile_code",
                value=profile.code,
                placeholder=PLACEHOLDER_CODE,
                id=f"code-{profile.id}"
            ),
            Button("Update", type="submit"),
        ),
        hx_post=f"/{profile_app.name}/{profile.id}",
        hx_target=f'#profile-{profile.id}',
        hx_swap='outerHTML',
        style="display: none;",
        id=f'update-form-{profile.id}'
    )

    title_link = Span(
        f"{profile.name}",
        id=f"profile-text-display-{profile.id}",
        style="margin-left: 5px; cursor: pointer;",
        onclick=(
            "let li = this.closest('li'); "
            "let updateForm = document.getElementById('update-form-" + str(profile.id) + "'); "
            "if (updateForm.style.display === 'none' || updateForm.style.display === '') { "
            "    updateForm.style.display = 'block'; "
            "    li.querySelectorAll('input[type=checkbox], .delete-icon, span, a').forEach(el => el.style.display = 'none'); "
            "} else { "
            "    updateForm.style.display = 'none'; "
            "    li.querySelectorAll('input[type=checkbox], .delete-icon, span, a').forEach(el => el.style.display = 'inline'); "
            "}"
        )
    )

    contact_info = []
    if profile.address:
        contact_info.append(profile.address)
    if profile.code:
        contact_info.append(profile.code)
    contact_info_span = (
        Span(f" ({', '.join(contact_info)})", style="margin-left: 10px;")
        if contact_info else Span()
    )

    return Li(
        Div(
            active_checkbox,
            title_link,
            contact_info_span,
            delete_icon,
            update_form,
            style="display: flex; align-items: center;"
        ),
        id=f'profile-{profile.id}',
        data_id=profile.id,
        data_priority=profile.priority,
        style="list-style-type: none;"
    )

# The following is the default theme and plugins for Prism.js
# https://prismjs.com/download.html#themes=prism-okaidia&languages=markup+css+clike+javascript+markdown+python&plugins=line-numbers+toolbar+copy-to-clipboard

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
        "key": str,
        "value": str,
        "pk": "key"
    },
    profile={
        "id": int,
        "name": str,
        "real_name": str,
        "address": str,
        "code": str,
        "active": bool,
        "priority": int,
        "pk": "id"
    },
    pipeline={
        "pkey": str,
        "app_name": str,
        "data": str,
        "created": str,
        "updated": str,
        "pk": "pkey"
    }
)


class Chat:
    def __init__(self, app, id_suffix=""):
        self.app = app
        self.id_suffix = id_suffix
        self.logger = logger.bind(name=f"Chat{id_suffix}")
        self.active_websockets = set()
        self.app.websocket_route("/ws")(self.handle_websocket)
        self.logger.debug("Registered WebSocket route: /ws")

    async def broadcast(self, message: str):
        try:
            if isinstance(message, dict):
                if message.get("type") == "htmx":
                    htmx_response = message
                    content = to_xml(htmx_response['content'])
                    formatted_response = f"""<div id="todo-{htmx_response.get('id')}" hx-swap-oob="beforeend:#todo-list">
                        {content}
                    </div>"""
                    for ws in self.active_websockets:
                        await ws.send_text(formatted_response)
                    return
            formatted_msg = message.replace('\n', '<br>')if isinstance(message, str)else str(message)
            for ws in self.active_websockets:
                await ws.send_text(formatted_msg)
        except Exception as e:
            self.logger.error(f"Error in broadcast: {e}")

    async def handle_chat_message(self, websocket: WebSocket, message: str):
        try:
            append_to_conversation(message, "user")
            parts = message.split('|')
            msg = parts[0]
            verbatim = len(parts) > 1 and parts[1] == 'verbatim'
            raw_response = await pipulate.stream(msg, verbatim=verbatim)
            append_to_conversation(raw_response, "assistant")
        except Exception as e:
            self.logger.error(f"Error in handle_chat_message: {e}")
            traceback.print_exc()

    def create_progress_card(self):
        return Card(
            Header("Chat Playground"),
            Form(
                Div(
                    TextArea(
                        id="chat-input",
                        placeholder="Type your message here...",
                        rows="3"
                    ),
                    Button(
                        "Send",
                        type="submit"
                    ),
                    id="chat-form"
                ),
                onsubmit="sendMessage(event)"
            ),
            Div(id="chat-messages"),
            Script("""
                const ws = new WebSocket(`${window.location.protocol === 'https:' ? 'wss:' : 'ws'}://${window.location.host}/ws`);
                
                ws.onmessage = function(event) {
                    const messages = document.getElementById('chat-messages');
                    messages.innerHTML += event.data + '<br>';
                    messages.scrollTop = messages.scrollHeight;
                };
                
                function sendMessage(event) {
                    event.preventDefault();
                    const input = document.getElementById('chat-input');
                    const message = input.value;
                    if (message.trim()) {
                        ws.send(message);
                        input.value = '';
                    }
                }
            """)
        )

    async def handle_websocket(self, websocket: WebSocket):
        try:
            await websocket.accept()
            self.active_websockets.add(websocket)
            self.logger.debug("Chat WebSocket connected")
            while True:
                message = await websocket.receive_text()
                self.logger.debug(f"Received message: {message}")
                await self.handle_chat_message(websocket, message)
        except WebSocketDisconnect:
            self.logger.info("WebSocket disconnected")
        except Exception as e:
            self.logger.error(f"Error in WebSocket connection: {str(e)}")
            self.logger.error(traceback.format_exc())
        finally:
            self.active_websockets.discard(websocket)
            self.logger.debug("WebSocket connection closed")


chat = Chat(app, id_suffix="")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True,)


# Create the Pipulate instance first (needed for plugin initialization)
pipulate = Pipulate(pipeline)

profile_app = ProfileApp(table=profiles, pipulate_instance=pipulate)
profile_app.register_routes(rt)

# Ensure plugins directory exists
if not os.path.exists("plugins"):
    os.makedirs("plugins")
    logger.debug("Created plugins directory")


def build_endpoint_messages(endpoint):
    # Base dictionary for standard endpoints
    endpoint_messages = {
        "": f"Welcome to {APP_NAME}. You are on the home page. Select an app from the menu to get started.",
        "profile": ("This is where you add, edit, and delete profiles (aka clients). "
                    "The Nickname field is the only name shown on the menu so it is safe to use in front of clients. They only see each other's Nicknames."),
    }

    # Add messages for all workflows in our registry
    for plugin_name, plugin_instance in plugin_instances.items():
        if plugin_name not in endpoint_messages:
            # First check for get_endpoint_message method (prioritize dynamic messages)
            if hasattr(plugin_instance, 'get_endpoint_message') and callable(getattr(plugin_instance, 'get_endpoint_message')):
                endpoint_messages[plugin_name] = plugin_instance.get_endpoint_message()
            # Then fall back to static ENDPOINT_MESSAGE attribute
            elif hasattr(plugin_instance, 'ENDPOINT_MESSAGE'):
                endpoint_messages[plugin_name] = plugin_instance.ENDPOINT_MESSAGE
            else:
                class_name = plugin_instance.__class__.__name__
                endpoint_messages[plugin_name] = f"{class_name} app is where you manage your {plugin_name}."

    # These debug logs should be outside the loop or use the endpoint parameter
    if endpoint in plugin_instances:
        plugin_instance = plugin_instances[endpoint]
        logger.debug(f"Checking if {endpoint} has get_endpoint_message: {hasattr(plugin_instance, 'get_endpoint_message')}")
        logger.debug(f"Checking if get_endpoint_message is callable: {callable(getattr(plugin_instance, 'get_endpoint_message', None))}")
        logger.debug(f"Checking if {endpoint} has ENDPOINT_MESSAGE: {hasattr(plugin_instance, 'ENDPOINT_MESSAGE')}")

    return endpoint_messages.get(endpoint, None)


def build_endpoint_training(endpoint):
    # Base dictionary for standard endpoints
    endpoint_training = {
        "": ("You were just switched to the home page."),
        "profile": ("You were just switched to the profile app."),
    }

    # Add training for all workflows in our registry
    for workflow_name, workflow_instance in plugin_instances.items():
        if workflow_name not in endpoint_training:
            # Check for TRAINING_PROMPT attribute
            if hasattr(workflow_instance, 'TRAINING_PROMPT'):
                prompt = workflow_instance.TRAINING_PROMPT
                endpoint_training[workflow_name] = read_training(prompt)
            else:
                class_name = workflow_instance.__class__.__name__
                endpoint_training[workflow_name] = f"{class_name} app is where you manage your workflows."

    # Add the prompt to chat history as a system message
    append_to_conversation(endpoint_training.get(endpoint, ""), "system")
    return


COLOR_MAP = {"key": "yellow", "value": "white", "error": "red", "warning": "yellow", "success": "green", "debug": "blue"}


def db_operation(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            if func.__name__ == '__setitem__':
                key, value = args[1], args[2]
                if not key.startswith('_') and not key.endswith('_temp'):
                    # Only log important state changes at INFO level
                    if key in ('last_app_choice', 'last_profile_id', 'last_visited_url', 'pipeline_id'):
                        log.data(f"State updated: {key}", value)
                    else:
                        # Log all other DB operations at DEBUG level
                        log.debug("database", f"DB {func.__name__}: {key}", 
                                 f"value: {str(value)[:30]}..." if len(str(value)) > 30 else f"value: {value}")
            return result
        except Exception as e:
            log.error(f"Database operation {func.__name__} failed", e)
            raise
    return wrapper


class DictLikeDB:
    def __init__(self, store, Store):
        self.store = store
        self.Store = Store
        logger.debug("DictLikeDB initialized.")

    @db_operation
    def __getitem__(self, key):
        try:
            value = self.store[key].value
            logger.debug(f"Retrieved from DB: <{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}> = <{COLOR_MAP['value']}>{value}</{COLOR_MAP['value']}>")
            return value
        except NotFoundError:
            logger.error(f"Key not found: <{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}>")
            raise KeyError(key)

    @db_operation
    def __setitem__(self, key, value):
        try:
            self.store.update({"key": key, "value": value})
            logger.debug(f"Updated persistence store: <{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}> = <{COLOR_MAP['value']}>{value}</{COLOR_MAP['value']}>")
        except NotFoundError:
            self.store.insert({"key": key, "value": value})
            logger.debug(f"Inserted new item in persistence store: <{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}> = <{COLOR_MAP['value']}>{value}</{COLOR_MAP['value']}>")

    @db_operation
    def __delitem__(self, key):
        try:
            self.store.delete(key)
            logger.warning(f"Deleted key from persistence store: <{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}>")
        except NotFoundError:
            logger.error(f"Attempted to delete non-existent key: <{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}>")
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
            yield item.key, item.value

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
logger.debug("Database wrapper initialized.")


def populate_initial_data():
    logger.debug("Populating initial data.")
    allowed_keys = {'last_app_choice', 'last_visited_url', 'last_profile_id'}
    for key in list(db.keys()):
        if key not in allowed_keys:
            try:
                del db[key]
                logger.debug(f"Deleted non-essential persistent key: {key}")
            except KeyError:
                pass
    if not profiles():
        default_profile = profiles.insert({"name": f"Default {profile_app.name.capitalize()}", "address": "", "code": "", "active": True, "priority": 0, })
        logger.debug(f"Inserted default profile: {default_profile}")
    else:
        default_profile = profiles()[0]


populate_initial_data()


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

    logger.debug(f"Looking for plugins in: {plugins_dir}")

    # Skip if the directory doesn't exist
    if not os.path.isdir(plugins_dir):
        logger.warning(f"Plugins directory not found: {plugins_dir}")
        return plugin_modules

    # Custom sorting function to handle numeric prefixes correctly
    def numeric_prefix_sort(filename):
        import re
        match = re.match(r'^(\d+)_', filename)
        if match:
            return int(match.group(1))  # Return numeric value for sorting
        return float('inf')  # Non-prefixed files come last

    # Find all Python files in the plugins directory
    sorted_files = sorted(os.listdir(plugins_dir), key=numeric_prefix_sort)
    for filename in sorted_files:
        logger.debug(f"Checking file: {filename}")
        # Skip files with parentheses (like "tasks (Copy).py")
        if '(' in filename or ')' in filename:
            logger.debug(f"Skipping file with parentheses: {filename}")
            continue

        # Skip files prefixed with xx_ or XX_ (experimental plugins)
        if filename.lower().startswith('xx_'):
            logger.debug(f"Skipping experimental plugin: {filename}")
            continue

        if filename.endswith('.py') and not filename.startswith('__'):
            # Extract the module name, removing numeric prefix if present
            base_name = filename[:-3]  # Remove .py extension

            # Store both the clean name (for the module) and original name (for imports)
            # Pattern: match digits and underscore at the beginning (like "01_tasks")
            import re
            clean_name = re.sub(r'^\d+_', '', base_name)
            original_name = base_name

            logger.debug(f"Module name: {clean_name} (from {original_name})")

            try:
                # Import using the original filename
                module = importlib.import_module(f'plugins.{original_name}')

                # But store it using the clean name (without numeric prefix)
                plugin_modules[clean_name] = module

                # Attach the original name to the module for reference if needed
                module._original_filename = original_name

                logger.debug(f"Successfully imported module: {clean_name} from {original_name}")
            except ImportError as e:
                logger.error(f"Error importing plugin module {original_name}: {str(e)}")

    logger.debug(f"Discovered plugin modules: {list(plugin_modules.keys())}")
    return plugin_modules


def find_plugin_classes(plugin_modules):
    """Find plugin-compatible classes within imported modules.

    Identifies plugin classes that have a 'landing' method
    and the required attributes or properties. Supports:
    - Workflow plugins with NAME/APP_NAME and DISPLAY_NAME attributes
    - CRUD UI plugins with name/DISPLAY_NAME properties

    Args:
        plugin_modules (dict): Mapping of module names to module objects

    Returns:
        list: List of tuples (module_name, class_name, class_object) for each plugin class
    """
    plugin_classes = []

    for module_name, module in plugin_modules.items():
        logger.debug(f"Examining module: {module_name}")

        for name, obj in inspect.getmembers(module):
            logger.debug(f"Found member in {module_name}: {name}, type: {type(obj)}")

            # Check if it's a class
            if inspect.isclass(obj):
                logger.debug(f"Class found: {module_name}.{name}")

                # Check if the class has a landing method
                if hasattr(obj, 'landing') and callable(getattr(obj, 'landing')):
                    # Check for direct attributes (workflow plugins)
                    has_name_attribute = (
                        hasattr(obj, 'NAME') or
                        hasattr(obj, 'APP_NAME')  # Some plugins use APP_NAME instead
                    )
                    has_display_name = hasattr(obj, 'DISPLAY_NAME')
                    has_attributes = has_name_attribute and has_display_name

                    # Check for properties via class dictionary (CRUD UI plugins)
                    has_properties = False
                    if 'DISPLAY_NAME' in dir(obj) and not has_attributes:
                        # For classes that use property decorators like CrudUI
                        has_properties = True

                    if has_attributes or has_properties:
                        plugin_classes.append((module_name, name, obj))
                        plugin_type = 'property-based' if has_properties else 'attribute-based'
                        name_attr = 'APP_NAME' if hasattr(obj, 'APP_NAME') else 'NAME'
                        logger.debug(f"Found plugin: {module_name}.{name} ({plugin_type}, using {name_attr})")

    logger.debug(f"Discovered plugin classes: {[(m, c) for m, c, _ in plugin_classes]}")
    return plugin_classes


# Dictionary to store instantiated plugin objects
plugin_instances = {}

# Discover plugin files and classes
discovered_modules = discover_plugin_files()
discovered_classes = find_plugin_classes(discovered_modules)

# Ensure these dictionaries are initialized
friendly_names = {"": "Home"}
endpoint_training = {}


def get_display_name(workflow_name):
    instance = plugin_instances.get(workflow_name)
    if instance and hasattr(instance, 'DISPLAY_NAME'):
        return instance.DISPLAY_NAME
    return workflow_name.replace('_', ' ').title()  # Default display name


def get_endpoint_message(workflow_name):
    instance = plugin_instances.get(workflow_name)
    if instance and hasattr(instance, 'ENDPOINT_MESSAGE'):
        # Use our new helper to format links
        message = instance.ENDPOINT_MESSAGE
        if hasattr(pipulate, 'format_links_in_text'):
            try:
                # Check if it's an async method and handle appropriately
                import inspect
                if inspect.iscoroutinefunction(pipulate.format_links_in_text):
                    import asyncio
                    # Create a non-blocking task
                    asyncio.create_task(pipulate.format_links_in_text(message))
                    return message
                else:
                    # Call directly if it's a regular function
                    return pipulate.format_links_in_text(message)
            except Exception as e:
                logger.warning(f"Error formatting links in message: {e}")
                return message
        return message
    return f"{workflow_name.replace('_', ' ').title()} app is where you manage your workflows."  # Default message


# Register workflows
for module_name, class_name, workflow_class in discovered_classes:
    if module_name not in plugin_instances:
        try:
            instance = workflow_class(app, pipulate, pipeline, db)
            plugin_instances[module_name] = instance
            logger.debug(f"Auto-registered workflow: {module_name}")

            # Retrieve and log the endpoint message using the new method
            endpoint_message = get_endpoint_message(module_name)
            logger.debug(f"Endpoint message for {module_name}: {endpoint_message}")

        except Exception as e:
            logger.warning(f"Issue with workflow {module_name}.{class_name} - continuing anyway")
            # Optional: Log error type separately if needed
            logger.debug(f"Error type: {e.__class__.__name__}")
            
            # If it's a coroutine that wasn't awaited, create a task for it
            import inspect
            if inspect.iscoroutine(e):
                import asyncio
                asyncio.create_task(e)

# Use the registry to set friendly names and endpoint messages
for workflow_name, workflow_instance in plugin_instances.items():
    if workflow_name not in friendly_names:
        display_name = get_display_name(workflow_name)
        logger.debug(f"Setting friendly name for {workflow_name}: {display_name}")
        friendly_names[workflow_name] = display_name

    if workflow_name not in endpoint_training:
        endpoint_message = get_endpoint_message(workflow_name)
        logger.debug(f"Setting endpoint message for {workflow_name}")
        endpoint_training[workflow_name] = endpoint_message

base_menu_items = ['']  # Remove 'profile' from here
additional_menu_items = []  # Remove 'mobile_chat' from here

# Get discovered plugins in the order they were discovered (based on numeric prefix)
ordered_plugins = []
for module_name, class_name, workflow_class in discovered_classes:
    if module_name not in ordered_plugins and module_name in plugin_instances:
        ordered_plugins.append(module_name)

MENU_ITEMS = base_menu_items + ordered_plugins + additional_menu_items
logger.debug(f"Dynamic MENU_ITEMS: {MENU_ITEMS}")


@rt('/clear-pipeline', methods=['POST'])
async def clear_pipeline(request):
    # Get the current workflow name and display name
    menux = db.get("last_app_choice", "App")
    workflow_display_name = "Pipeline"

    # Get the display name for the current workflow if available
    if menux and menux in plugin_instances:
        instance = plugin_instances.get(menux)
        if instance and hasattr(instance, 'DISPLAY_NAME'):
            workflow_display_name = instance.DISPLAY_NAME
        else:
            workflow_display_name = friendly_names.get(menux, menux.replace('_', ' ').title())

    # Clear all standard database keys except for navigation state
    last_app_choice = db.get("last_app_choice")
    last_visited_url = db.get("last_visited_url")

    keys = list(db.keys())
    for key in keys:
        del db[key]
    logger.debug(f"{workflow_display_name} DictLikeDB cleared")

    # Restore navigation state
    if last_app_choice:
        db["last_app_choice"] = last_app_choice
    if last_visited_url:
        db["last_visited_url"] = last_visited_url

    # Clear ALL pipeline records - reset any filters first
    # This is crucial to ensure we're not filtering records when fetching to delete
    if hasattr(pipulate.table, 'xtra'):
        # Reset any filters by passing an empty dict to xtra
        pipulate.table.xtra()

    records = list(pipulate.table())
    logger.debug(f"Found {len(records)} records to delete")
    for record in records:
        pipulate.table.delete(record.pkey)
    logger.debug(f"{workflow_display_name} table cleared")

    db["temp_message"] = f"{workflow_display_name} cleared. Next ID will be 01."
    logger.debug(f"{workflow_display_name} DictLikeDB cleared for debugging")

    # Create a response with an empty datalist and a refresh header
    response = Div(
        # Empty datalist with out-of-band swap to clear all options
        pipulate.update_datalist("pipeline-ids", clear=True),
        # Normal message displayed to the user
        P(f"{workflow_display_name} cleared."),
        cls="clear-message"
    )

    # Convert to HTTPResponse to add the refresh header
    html_response = HTMLResponse(str(response))
    html_response.headers["HX-Refresh"] = "true"
    return html_response


@rt('/clear-db', methods=['POST'])
async def clear_db(request):
    """Developer tools endpoint - fully resets the database to initial state.
    Only accessible in development environment."""
    logger.debug("Dev tools endpoint accessed - performing complete database reset")
    
    # 1. Clear all database keys (DictLikeDB)
    log.warning("Starting complete database reset", "This will recreate an empty database")
    
    # Save only the navigation state 
    last_app_choice = db.get("last_app_choice")
    last_visited_url = db.get("last_visited_url")
    
    # Delete all keys from the db
    keys = list(db.keys())
    for key in keys:
        del db[key]
    log.warning("DictLikeDB cleared", f"Deleted {len(keys)} keys")
    
    # 2. Reset core tables defined in fast_app
    # 2.1 Reset pipeline table - reset any filters first
    if hasattr(pipulate.table, 'xtra'):
        # Reset any filters by passing an empty dict to xtra
        pipulate.table.xtra()
    
    records = list(pipulate.table())
    for record in records:
        pipulate.table.delete(record.pkey)
    log.warning("Pipeline table cleared", f"Deleted {len(records)} records")
    
    # 2.2 Reset profile table
    # Get profile records first
    profile_records = list(profiles())
    profile_count = len(profile_records)
    
    # Delete all profile records
    for profile in profile_records:
        profiles.delete(profile.id)
    log.warning("Profiles table cleared", f"Deleted {profile_count} records")
    
    # 3. Find and reset all plugin-created tables
    # Use sqlite3 directly to query for all tables
    import sqlite3
    
    try:
        # Log the database file we're using
        logger.debug(f"Using database file: {DB_FILENAME}")
        
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()
        
        # Get all table names from SQLite schema - excluding core tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('store', 'profile', 'pipeline', 'sqlite_sequence')")
        plugin_tables = cursor.fetchall()
        
        # Log the tables we found for debugging
        table_names = [table[0] for table in plugin_tables]
        log.warning("Found plugin tables", f"Tables to clear: {', '.join(table_names)}")
        
        # Clear each plugin table
        cleared_count = 0
        for (table_name,) in plugin_tables:
            try:
                # Check if table exists and has records
                cursor.execute(f"SELECT count(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                
                # Delete all records
                cursor.execute(f"DELETE FROM {table_name}")
                
                # Log the operation with row count
                log.warning(f"Plugin table '{table_name}' cleared", f"Deleted {row_count} records")
                cleared_count += 1
                
                # Reset auto-increment if this table has it
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'")
                
            except Exception as e:
                log.error(f"Error clearing table {table_name}", str(e))
        
        # Commit changes
        conn.commit()
        log.warning("Plugin tables cleanup complete", f"Cleared {cleared_count} tables")
        
        # Close connection
        conn.close()
    except Exception as e:
        log.error("Error accessing SQLite database", str(e))
    
    # 4. Re-initialize the database with default data
    # This is similar to the first-run initialization
    populate_initial_data()
    log.startup("Database reset to initial state", "Default profile created")
    
    # 5. Restore navigation state if needed
    if last_app_choice:
        db["last_app_choice"] = last_app_choice
    if last_visited_url:
        db["last_visited_url"] = last_visited_url
    
    # Set a confirmation message in the temporary message system instead of streaming
    db["temp_message"] = "Database completely reset to initial state. All data has been cleared and a fresh default profile has been created."
    log.startup("Database reset confirmation message set", "Will display after page reload")
    
    # Create a response with refresh directive
    html_response = HTMLResponse("<div>Database reset complete</div>")
    html_response.headers["HX-Refresh"] = "true"  # Force a full page refresh
    return html_response

def get_profile_name():
    profile_id = get_current_profile_id()
    logger.debug(f"Retrieving profile name for ID: {profile_id}")
    try:
        profile = profiles.get(profile_id)
        if profile:
            logger.debug(f"Found profile: {profile.name}")
            return profile.name
    except NotFoundError:
        logger.warning(f"No profile found for ID: {profile_id}")
        return "Unknown Profile"


async def home(request):
    path = request.url.path.strip('/')
    logger.debug(f"Received request for path: {path}")
    menux = normalize_menu_path(path)
    logger.debug(f"Selected explore item: {menux}")
    db["last_app_choice"] = menux
    db["last_visited_url"] = request.url.path

    # Replace this block with the helper function
    current_profile_id = get_current_profile_id()

    menux = db.get("last_app_choice", "App")
    response = await create_outer_container(current_profile_id, menux)
    logger.debug("Returning response for main GET request.")
    last_profile_name = get_profile_name()
    
    # Create a plain text title for the document title
    page_title = f"{APP_NAME} - {title_name(last_profile_name)} - {endpoint_name(menux)}"
    
    # Return the title and main content separately instead of using Titled()
    # We no longer need to include nav_header here as it's now in the nav_menu
    return (
        Title(page_title),  # This will be the <title> in the HTML head
        Main(
            response,       # This now contains the nav_group with breadcrumb
            data_theme="dark",
            style=(
                f"width: {WEB_UI_WIDTH}; "
                f"max-width: none; "
                f"padding: {WEB_UI_PADDING}; "
                f"margin: {WEB_UI_MARGIN};"
            )
        )
    )

def create_nav_group():
    # Create the initial nav menu with integrated breadcrumb
    nav = create_nav_menu()

    # Add a hidden event listener to refresh the profile dropdown
    refresh_listener = Div(
        id="profile-menu-refresh-listener",
        hx_get="/refresh-profile-menu",
        hx_trigger="refreshProfileMenu from:body",
        hx_target="#profile-dropdown-menu",
        hx_swap="outerHTML",
        style="display: none;"
    )

    # Style for the navigation group 
    nav_group_style = "display: flex; align-items: center; position: relative;"
    
    # Return a group with the nav and the refresh listener
    return Group(nav, refresh_listener, style=nav_group_style)


def create_env_menu():
    """Create environment selection dropdown menu."""
    # Get current environment from file
    current_env = get_current_environment()
    
    # Style for summary based on environment
    env_summary_style = "white-space: nowrap; display: inline-block; min-width: max-content;"
    
    # Add visual indicator for Development mode (subtle styling)
    if current_env == "Development":
        env_summary_style += " color: #f77; font-weight: bold;"
        display_env = "Dev"
    else:
        display_env = "Prod"
    
    menu_items = []
    # Development option
    is_dev = current_env == "Development"
    dev_style = f"{NOWRAP_STYLE} background-color: var(--pico-primary-background);" if is_dev else NOWRAP_STYLE
    menu_items.append(Li(
        A("Dev", 
          hx_post="/switch_environment", 
          hx_vals='{"environment": "Development"}',
          hx_confirm="Switch to Development environment? This will restart the server.",
          cls="dropdown-item", 
          style=dev_style), 
        style="display: block;"
    ))
    
    # Production option
    is_prod = current_env == "Production"
    prod_style = f"{NOWRAP_STYLE} background-color: var(--pico-primary-background);" if is_prod else NOWRAP_STYLE
    menu_items.append(Li(
        A("Prod", 
          hx_post="/switch_environment", 
          hx_vals='{"environment": "Production"}',
          hx_confirm="Switch to Production environment? This will restart the server.",
          cls="dropdown-item", 
          style=prod_style), 
        style="display: block;"
    ))
    
    return Details(
        Summary(
            f"ENV: {display_env}", 
            id="env-id", 
            style=env_summary_style
        ), 
        Ul(*menu_items, cls="dropdown-menu"),
        cls="dropdown",
    )

def create_nav_menu():
    logger.debug("Creating navigation menu.")
    menux = db.get("last_app_choice", "App")
    # Use our helper functions for profile id and name
    selected_profile_id = get_current_profile_id()
    selected_profile_name = get_profile_name()
    
    # Create a breadcrumb-style navigation
    breadcrumb = H1(
        A(APP_NAME, 
          href="/redirect/", 
          title="Go to Home", 
          style="text-decoration: none; color: inherit; transition: color 0.2s; white-space: nowrap;",
          onmouseover="this.style.color='#4dabf7'; this.style.textDecoration='underline';", 
          onmouseout="this.style.color='inherit'; this.style.textDecoration='none';"
        ),
        Span(" / ", style="padding: 0 0.3rem;"),
        Span(title_name(selected_profile_name), style="white-space: nowrap;"),
        Span(" / ", style="padding: 0 0.3rem;"),
        Span(endpoint_name(menux), style="white-space: nowrap;"),
        style="display: inline-flex; align-items: center; margin-right: auto; flex-wrap: wrap;"
    )
    
    # Add the breadcrumb at the beginning, followed by all dropdown menus
    nav_items = [
        breadcrumb,
        create_profile_menu(selected_profile_id, selected_profile_name),
        create_app_menu(menux),
        create_env_menu()  # Move ENV menu to the third position
    ]
    
    nav = Div(*nav_items, style="display: flex; align-items: center; gap: 20px; width: 100%;")
    logger.debug("Navigation menu created.")
    return nav


def create_filler_item():
    return Li(Span(" "), style=("display: flex; ""flex-grow: 1; ""justify-content: center; ""list-style-type: none; "f"min-width: {NAV_FILLER_WIDTH}; "),)


def create_profile_menu(selected_profile_id, selected_profile_name):
    # Use our helper instead of passing in selected_profile_id
    selected_profile_id = get_current_profile_id()

    def get_selected_item_style(is_selected):
        return "background-color: var(--pico-primary-background); "if is_selected else ""
    menu_items = []
    menu_items.append(Li(A(f"Edit {endpoint_name(profile_app.name)}s", href=f"/redirect/{profile_app.name}", cls="dropdown-item", style=(f"{NOWRAP_STYLE} ""font-weight: bold; ""border-bottom: 1px solid var(--pico-muted-border-color);""display: block; ""text-align: center; ")), style=("display: block; ""text-align: center; ")))
    active_profiles = profiles("active=?", (True,), order_by='priority')
    for profile in active_profiles:
        is_selected = str(profile.id) == str(selected_profile_id)
        item_style = get_selected_item_style(is_selected)
        menu_items.append(Li(Label(Input(type="radio", name="profile", value=str(profile.id), checked=is_selected, hx_post=f"/select_profile", hx_vals=f'js:{{profile_id: "{profile.id}"}}', hx_target="body", hx_swap="outerHTML",), profile.name, style="display: flex; align-items: center;"), style=f"text-align: left; {item_style}"))
    return Details(
        Summary(f"{profile_app.name.upper()}: {selected_profile_name}",
                id="profile-id",
                style="white-space: nowrap; display: inline-block; min-width: max-content;"),
        Ul(*menu_items, style="padding-left: 0;"),
        cls="dropdown",
        id="profile-dropdown-menu"  # Add this ID to target for refresh
    )


def normalize_menu_path(path):
    """Convert empty paths to 'home' and return the path otherwise."""
    return "home" if path == "" else path


def create_app_menu(menux):
    menu_items = []
    show_all = db.get("show_all_plugins", "0") == "1"
    
    # First add all core items
    for item in MENU_ITEMS:
        # Skip profile app in Apps menu
        if item == profile_app.name:
            continue
            
        # Skip non-core items unless show_all is enabled
        if not show_all and not is_core_plugin(item):
            continue

        # Only show core items in the first pass
        if not show_all or is_core_plugin(item):
            # Normalize both the current selection and menu item for comparison
            norm_menux = normalize_menu_path(menux)
            norm_item = normalize_menu_path(item)

            is_selected = norm_item == norm_menux
            item_style = "background-color: var(--pico-primary-background); "if is_selected else ""
            menu_items.append(Li(
                A(endpoint_name(item), 
                  href=f"/redirect/{item}", 
                  cls="dropdown-item", 
                  style=f"{NOWRAP_STYLE} {item_style}"), 
                style="display: block;"
            ))
    
    # If showing all plugins, add non-core items after a divider
    if show_all:
        # Add a divider after core plugins
        menu_items.append(Li(
            Hr(style="margin: 0.5rem 0;"),
            style="display: block;"
        ))
        
        # Add non-core items
        for item in MENU_ITEMS:
            if item != profile_app.name and not is_core_plugin(item):
                norm_menux = normalize_menu_path(menux)
                norm_item = normalize_menu_path(item)

                is_selected = norm_item == norm_menux
                item_style = "background-color: var(--pico-primary-background); "if is_selected else ""
                menu_items.append(Li(
                    A(endpoint_name(item), 
                      href=f"/redirect/{item}", 
                      cls="dropdown-item", 
                      style=f"{NOWRAP_STYLE} {item_style}"), 
                    style="display: block;"
                ))
    
    # Add a divider before the Show All toggle
    menu_items.append(Li(
        Hr(style="margin: 0.5rem 0;"),
        style="display: block;"
    ))
    
    # Add the Show All toggle
    menu_items.append(Li(
        A("Show All Plugins..." if not show_all else "Show Core Plugins...",
          hx_post="/toggle_show_all",
          hx_target="body",
          hx_swap="outerHTML",
          cls="dropdown-item",
          style=NOWRAP_STYLE),
        style="display: block;"
    ))

    return Details(
        Summary(
            f"APP: {endpoint_name(menux)}", 
            id="app-id", 
            style="white-space: nowrap; display: inline-block; min-width: max-content;"
        ), 
        Ul(*menu_items, cls="dropdown-menu",), 
        cls="dropdown",
    )

# Add the toggle endpoint
@rt('/toggle_show_all', methods=['POST'])
async def toggle_show_all(request):
    """Toggle between showing all plugins or just core plugins."""
    current = db.get("show_all_plugins", "0")
    db["show_all_plugins"] = "1" if current == "0" else "0"
    
    # Get the current URL to redirect back to
    redirect_url = db.get("last_visited_url", "/")
    return Redirect(redirect_url)


async def create_outer_container(current_profile_id, menux):
    # Create nav group (now includes breadcrumb)
    nav_group = create_nav_group()

    # Default layout
    return Container(
        nav_group,
        Grid(
            await create_grid_left(menux),
            create_chat_interface(),
            cls="grid",
            style=(
                "display: grid; "
                "gap: 20px; "
                f"grid-template-columns: {GRID_LAYOUT}; "
            ),
        ),
        create_poke_button(),
        style=(
            f"width: {WEB_UI_WIDTH}; "
            f"max-width: none; "
            f"padding: {WEB_UI_PADDING}; "
            f"margin: {WEB_UI_MARGIN};"
        ),
    )


async def create_grid_left(menux, render_items=None):
    if menux == profile_app.name:
        return await profile_render()
    elif menux in plugin_instances:
        workflow_instance = plugin_instances[menux]
        if hasattr(workflow_instance, 'render'):
            return await workflow_instance.render()
        return await workflow_instance.landing()
    else:
        # Default to a simple welcome page if no specific menu is selected
        return Div(
            H2(f"Welcome to {APP_NAME}"),
            P("Please select an option from the menu to get started."),
            id="welcome-content"
        )


def create_chat_interface(autofocus=False):
    msg_list_height = 'height: calc(70vh - 200px);'
    temp_message = None
    if "temp_message" in db:
        temp_message = db["temp_message"]
        del db["temp_message"]

    # Small inline script to set the temp_message variable
    init_script = f"""
    // Set global variables for the external script
    window.PIPULATE_CONFIG = {{
        tempMessage: {json.dumps(temp_message)}
    }};
    """

    return Div(
        Card(
            H3(f"{APP_NAME} Chatbot"),
            Div(
                id='msg-list',
                cls='overflow-auto',
                style=(msg_list_height),
            ),
            Form(
                mk_chat_input_group(value="", autofocus=autofocus),
                onsubmit="sendSidebarMessage(event)",
            ),
            # First load the initialization script with the dynamic variables
            Script(init_script),
            # Then load the external script
            Script(src='/static/chat-interface.js'),
        ),
        id="chat-interface",
        style=(
            "position: sticky; " +
            "top: 20px; " +
            "margin: 0; " +
            "padding: 0; " +
            "overflow: hidden; "
        ),
    )


def mk_chat_input_group(disabled=False, value='', autofocus=True):
    return Group(
        Input(
            id='msg',
            name='msg',
            placeholder='Chat...',
            value=value,
            disabled=disabled,
            autofocus='autofocus' if autofocus else None,
        ),
        Button(
            "Send",
            type='submit',
            id='send-btn',
            disabled=disabled,
        ),
        id='input-group'
    )


def create_poke_button():
    # Get current workflow name from the app choice
    menux = db.get("last_app_choice", "App")
    workflow_display_name = "Pipeline"

    # Common button style for smaller buttons
    button_style = "margin-right: 5px; font-size: 0.85rem; padding: 0.4rem 0.8rem;"
    
    # Create button elements list
    buttons = []
    
    # Check if current plugin is in plugin_instances
    if menux and menux in plugin_instances:
        instance = plugin_instances.get(menux)
        
        # Get the display name for the current plugin if available
        if hasattr(instance, 'DISPLAY_NAME'):
            workflow_display_name = instance.DISPLAY_NAME
        else:
            workflow_display_name = friendly_names.get(menux, menux.replace('_', ' ').title())
        
        # Determine if this is a workflow plugin vs a CRUD plugin
        # SIMPLER APPROACH: Check for key class properties
        is_crud_plugin = (hasattr(instance, '__class__') and 
                          instance.__class__.__name__ == 'CrudUI')
        
        # Consider it a workflow plugin if it's not a CRUD plugin
        # and it's not the profile app or home page
        is_workflow_plugin = (not is_crud_plugin and 
                             menux != profile_app.name and 
                             menux != "")
        
        # Only show Clear Pipeline button for workflow plugins
        if is_workflow_plugin:
            buttons.append(
                A(
                    f"Clear {workflow_display_name}",
                    hx_post="/clear-pipeline",
                    hx_swap="none",
                    cls="button",
                    style=button_style
                )
            )
    
    # Add dev tools button only in development mode
    if get_current_environment() == "Development":
        buttons.append(
            A(
                "Clear DB",
                hx_post="/clear-db",
                hx_target="#msg-list",
                hx_swap="innerHTML",
                cls="button",
                style=button_style
            )
        )
    
    # Always add the poke button
    buttons.append(
        A(
            f"Poke {MODEL}",
            hx_post="/poke",
            hx_target="#msg-list",
            hx_swap="innerHTML",
            cls="button",
            style=button_style
        )
    )

    # Add scroll to top button
    buttons.append(
        A(
            "Scroll to Top",
            href="#",
            onclick="window.scrollTo({top: 0, behavior: 'smooth'}); return false;",
            cls="button",
            style=button_style
        )
    )
    
    return Div(
        *buttons,  # Unpack the buttons list
        style=(
            "bottom: 20px; "
            "position: fixed; "
            "right: 20px; "
            "z-index: 1000; "
            "display: flex; "
            "align-items: center; "
        )
    )


async def profile_render():
    all_profiles = profiles()
    logger.debug("Initial profile state:")
    for profile in all_profiles:
        logger.debug(f"Profile {profile.id}: name = {profile.name}, priority = {profile.priority}")

    ordered_profiles = sorted(
        all_profiles,
        key=lambda p: p.priority if p.priority is not None else float('inf')
    )

    logger.debug("Ordered profile list:")
    for profile in ordered_profiles:
        logger.debug(f"Profile {profile.id}: name = {profile.name}, priority = {profile.priority}")

    return Container(
        Grid(
            Div(
                Card(
                    H2(f"{profile_app.name.capitalize()} {LIST_SUFFIX}"),
                    Ul(
                        *[render_profile(profile) for profile in ordered_profiles],
                        id='profile-list',
                        cls='sortable',
                        style="padding-left: 0;"
                    ),
                    footer=Form(
                        Group(
                            Input(
                                placeholder="Nickname",
                                name="profile_name",
                                id="profile-name-input"
                            ),
                            Input(
                                placeholder=f"Real Name",
                                name="profile_menu_name",
                                id="profile-menu-name-input"
                            ),
                            Input(
                                placeholder=PLACEHOLDER_ADDRESS,
                                name="profile_address",
                                id="profile-address-input"
                            ),
                            Input(
                                placeholder=PLACEHOLDER_CODE,
                                name="profile_code",
                                id="profile-code-input"
                            ),
                            Button(
                                "Add",
                                type="submit",
                                id="add-profile-button"
                            ),
                        ),
                        hx_post=f"/{profile_app.name}",
                        hx_target="#profile-list",
                        hx_swap="beforeend",
                        hx_swap_oob="true",
                    ),
                ),
                id="content-container",
            ),
        ),
        Script("""
            document.addEventListener('htmx:afterSwap', function(event) {
                if (event.target.id === 'profile-list' && event.detail.successful) {
                    const form = document.getElementById('add-profile-button').closest('form');
                    form.reset();
                }
            });
        """),
    )


@rt("/sse")
async def sse_endpoint(request):
    return EventStream(broadcaster.generator())


@app.post("/chat")
async def chat_endpoint(request, message: str):
    await pipulate.stream(f"Let the user know {limiter} {message}")
    return ""


@rt('/redirect/{path:path}')
def redirect_handler(request):
    path = request.path_params['path']
    logger.debug(f"Redirecting to: {path}")
    message = build_endpoint_messages(path)
    hot_prompt_injection(message)
    build_endpoint_training(path)
    db["temp_message"] = message
    return Redirect(f"/{path}")


@rt('/poke', methods=['POST'])
async def poke_chatbot():
    logger.debug("Chatbot poke received.")
    poke_message = (f"The user poked the {APP_NAME} Chatbot. ""Respond with a brief, funny comment about being poked.")
    asyncio.create_task(pipulate.stream(poke_message))
    return "Poke received. Countdown to local LLM MODEL..."


@rt('/select_profile', methods=['POST'])
async def select_profile(request):
    logger.debug("Entering select_profile function")
    form = await request.form()
    logger.debug(f"Received form data: {form}")
    profile_id = form.get('profile_id')
    logger.debug(f"Extracted profile_id: {profile_id}")
    if profile_id:
        profile_id = int(profile_id)
        logger.debug(f"Converted profile_id to int: {profile_id}")
        db["last_profile_id"] = profile_id
        logger.debug(f"Updated last_profile_id in db to: {profile_id}")
        profile = profiles[profile_id]
        logger.debug(f"Retrieved profile: {profile}")
        profile_name = getattr(profile, 'name', 'Unknown Profile')
        logger.debug(f"Profile name: {profile_name}")
        prompt = f"You have switched to the '{profile_name}' profile."
        db["temp_message"] = prompt
        logger.debug(f"Stored temp_message in db: {db['temp_message']}")
    redirect_url = db.get("last_visited_url", "/")
    logger.debug(f"Redirecting to: {redirect_url}")
    return Redirect(redirect_url)


class DOMSkeletonMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        endpoint = request.url.path
        method = request.method
        
        # Skip logging for static files and other noise at INFO level
        is_static = endpoint.startswith('/static/') 
        is_ws = endpoint == '/ws'
        is_sse = endpoint == '/sse'
        
        if not (is_static or is_ws or is_sse):
            # Log actual page requests at INFO level
            log.event("network", f"{method} {endpoint}")
        else:
            # But still log everything at DEBUG level
            log.debug("network", f"{method} {endpoint}")
            
        response = await call_next(request)
        
        # This is controlled by the STATE_TABLES constant at the top of the file
        if STATE_TABLES:
            # Cookie state table with emoji
            cookie_table = Table(title="🍪 Stored Cookie States")
            cookie_table.add_column("Key", style="cyan")
            cookie_table.add_column("Value", style="magenta")
            for key, value in db.items():
                json_value = JSON.from_data(value, indent=2)
                cookie_table.add_row(key, json_value)
            console.print(cookie_table)
            
            # Pipeline state table with emoji
            pipeline_table = Table(title="➡️ Pipeline States")
            pipeline_table.add_column("Key", style="yellow")
            pipeline_table.add_column("Created", style="magenta")
            pipeline_table.add_column("Updated", style="cyan")
            pipeline_table.add_column("Steps", style="white")
            for record in pipulate.table():
                try:
                    state = json.loads(record.data)
                    pre_state = json.loads(record.data)
                    pipeline_table.add_row(record.pkey, str(state.get('created', '')), str(state.get('updated', '')), str(len(pre_state) - 2))
                except (json.JSONDecodeError, AttributeError) as e:
                    log.error(f"Error parsing pipeline state for {record.pkey}", e)
                    pipeline_table.add_row(record.pkey, "ERROR", "Invalid State")
            console.print(pipeline_table)
            
        return response


def print_routes():
    logger.debug('Route Table')
    table = Table(title="Application Routes")
    table.add_column("Type", style="cyan", no_wrap=True)
    table.add_column("Methods", style="yellow on black")
    table.add_column("Path", style="white")
    table.add_column("Duplicate", style="green")
    route_entries = []
    seen_routes = set()
    for app_route in app.routes:
        if isinstance(app_route, Route):
            methods = ", ".join(app_route.methods)
            route_key = (app_route.path, methods)
            if route_key in seen_routes:
                path_style = "red"
                duplicate_status = Text("Yes", style="red")
            else:
                path_style = "white"
                duplicate_status = Text("No", style="green")
                seen_routes.add(route_key)
            route_entries.append(("Route", methods, app_route.path, path_style, duplicate_status))
        elif isinstance(app_route, WebSocketRoute):
            route_key = (app_route.path, "WebSocket")
            if route_key in seen_routes:
                path_style = "red"
                duplicate_status = Text("Yes", style="red")
            else:
                path_style = "white"
                duplicate_status = Text("No", style="green")
                seen_routes.add(route_key)
            route_entries.append(("WebSocket", "WebSocket", app_route.path, path_style, duplicate_status))
        elif isinstance(app_route, Mount):
            route_entries.append(("Mount", "Mounted App", app_route.path, "white", Text("N/A", style="green")))
        else:
            route_entries.append((str(type(app_route)), "Unknown", getattr(app_route, 'path', 'N/A'), "white", Text("N/A", style="green")))
    route_entries.sort(key=lambda x: x[2])
    for entry in route_entries:
        table.add_row(entry[0], entry[1], Text(entry[2], style=f"{entry[3]} on black"), entry[4])
    console.print(table)


@rt('/refresh-profile-menu')
async def refresh_profile_menu(request):
    """Endpoint to refresh just the profile dropdown menu without reloading the whole page."""
    logger.debug("Refreshing profile menu")
    selected_profile_id = get_current_profile_id()
    selected_profile_name = get_profile_name()
    return create_profile_menu(selected_profile_id, selected_profile_name)

@rt('/switch_environment', methods=['POST'])
async def switch_environment(request):
    """Handle environment switching and restart the server."""
    try:
        form = await request.form()
        environment = form.get('environment', 'Development')
        
        # Store the selected environment in the environment file
        set_current_environment(environment)
        logger.info(f"Environment switched to: {environment}")
        
        # Schedule server restart
        asyncio.create_task(delayed_restart(2))  # 2 second delay to allow response to be sent
        
        # Return a minimal response with a spinner using aria-busy
        return HTMLResponse(f"<div aria-busy='true'>Switching</div>")
        
    except Exception as e:
        logger.error(f"Error switching environment: {e}")
        return HTMLResponse(f"Error: {str(e)}", status_code=500)

async def delayed_restart(delay_seconds):
    """Restart the server after a delay."""
    logger.info(f"Server restart scheduled in {delay_seconds} seconds...")
    await asyncio.sleep(delay_seconds)
    
    # Force close existing connections 
    # This helps ensure we don't keep the old database file open
    try:
        # Log that we're about to restart
        logger.info("Performing server restart now...")
        
        # Restart the server
        restart_server()
    except Exception as e:
        logger.error(f"Error during restart: {e}")

ALL_ROUTES = list(set(['', profile_app.name] + MENU_ITEMS))
for item in ALL_ROUTES:
    path = f'/{item}'if item else '/'

    @app.route(path)
    async def home_route(request):
        return await home(request)
app.add_middleware(DOMSkeletonMiddleware)
logger.debug("Application setup completed with DOMSkeletonMiddleware.")
logger.debug(f"Using MODEL: {MODEL}")
print_routes()


def check_syntax(filename):
    with open(filename, 'r')as file:
        source = file.read()
    try:
        ast.parse(source)
        return True
    except SyntaxError as e:
        print(f"Syntax error in {filename}:")
        print(f"  Line {e.lineno}: {e.text}")
        print(f"  {' ' * (e.offset - 1)}^")
        print(f"Error: {e}")
        return False


def restart_server():
    if not check_syntax(Path(__file__)):
        log.warning("Syntax error detected", "Fix the error and save the file again")
        return
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Log restart attempt
            log.startup(f"Restarting server (attempt {attempt + 1}/{max_retries})")
            
            # Forcefully exit to ensure all connections are closed
            os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            log.error(f"Error restarting server (attempt {attempt + 1}/{max_retries})", e)
            if attempt < max_retries - 1:
                log.warning("Restart failed", "Waiting 5 seconds before retrying")
                time.sleep(5)
            else:
                log.error("Max restart retries reached", "Please restart the server manually")


class ServerRestartHandler(FileSystemEventHandler):
    def on_modified(self, event):
        path = Path(event.src_path)
        if path.suffix == '.py':  # Check if any Python file is modified
            print(f"{path} has been modified. Checking syntax and restarting...")
            restart_server()


def run_server_with_watchdog():
    fig("SERVER RESTART")
    
    # Display current environment
    env = get_current_environment()
    env_db = DB_FILENAME
    
    # Log startup information using our new log manager
    log.startup(f"Starting {APP_NAME} server")
    
    # Display environment information with color based on environment
    if env == "Development":
        log.warning("Development mode active", details=f"Using database: {env_db}")
    else:
        log.startup("Production mode active", details=f"Using database: {env_db}")
    
    # Display state tables mode if enabled    
    if STATE_TABLES:
        log.startup("State tables enabled", details="Edit server.py and set STATE_TABLES=False to disable")
        
    # Display Alice mascot
    with open('static/alice.txt', 'r') as file:
        print(file.read())
        
    event_handler = ServerRestartHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=True)
    observer.start()
    
    try:
        log.startup("Server starting on http://localhost:5001")
        uvicorn.run(app, host="0.0.0.0", port=5001)
    except KeyboardInterrupt:
        log.event("server", "Server shutdown requested by user")
        observer.stop()
    except Exception as e:
        log.error("Server error", e)
        log.startup("Attempting to restart")
        restart_server()
    finally:
        observer.join()


if __name__ == "__main__":
    run_server_with_watchdog()


# autopep8 --ignore E501,F405,F403,F541 --in-place server.py
# isort server.py
# vulture server.py
# pylint --disable=all --enable=redefined-outer-name server.py

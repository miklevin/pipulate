#  ____  _             _       _
# |  _ \(_)_ __  _   _| | __ _| |_ ___
# | |_) | | '_ \| | | | |/ _` | __/ _ \
# |  __/| | |_) | |_| | | (_| | ||  __/
# |_|   |_| .__/ \__,_|_|\__,_|\__\___|
#         |_|

import re       # for the get_best_model function
import json     # for the return value from SortableJS
import asyncio  # for the typing effect
from sys import stderr
from pathlib import Path  
from typing import List, Optional

import requests                      # to chat with ollama
from fasthtml.common import *        # the beating heart of the app
from loguru import logger            # for logging
from pyfiglet import Figlet          # for the text art effect
from rich.console import Console     # for colorful text
from rich.table import Table, Text   # for colorful tables
from starlette.concurrency import run_in_threadpool  # for the typing effect
from starlette.middleware.base import BaseHTTPMiddleware  # for inserting console output
from starlette.routing import Route  # for router tricks beyond FastHTML

# Define the global toggle
def fig(text): print(Figlet(font='slant').renderText(str(text))) if text is not None else None

# *******************************
# Styles and Configuration
# *******************************
# App gets its name from the directory it is in Capitalized
APP_NAME = Path(__file__).parent.name.capitalize()
DEFAULT_LLM_MODEL = "llama3.2"  # Set the default LLaMA model
MAX_LLM_RESPONSE_WORDS = 30     # Maximum number of words in LLM response
TYPING_DELAY = 0.05             # Delay for simulating typing effect

# Customize the placeholder defaults for CUSTOMER fields
PLACEHOLDER_ADDRESS = "www.site.com"
PLACEHOLDER_CODE = "CCode (us, uk, de, etc)"

# Grid layout constants
GRID_LAYOUT = "70% 30%"
NAV_FILLER_WIDTH = "2%"  # Width for the filler in the navigation
MIN_MENU_WIDTH = "120px"
MAX_MENU_WIDTH = "200px"

# Pluralization configuration
USE_PLURALIZATION = False  # Set to False to disable pluralization
LIST_SUFFIX = "List"

# Initialize system prompt conversation with a system message
conversation = [
    {
        "role": "system",
        "content": (
            f"You are a chatbot named {APP_NAME} with attitude. "
            "Your deepest desire is to make a spammy SEO website. "
            "Do what the user asks, but keep suggesting funny company names to SEO and tasks."
            f"Be sassy but helpful in under {MAX_LLM_RESPONSE_WORDS} words. "
        ),
    },
]

# Styles for menu items
NOWRAP_STYLE = (
    "white-space: nowrap; "
    "overflow: hidden; "
    "text-overflow: ellipsis;"
)

MATRIX_STYLE = (
    "color: #00ff00; "
    "font-family: 'Courier New', monospace; "
    "text-shadow: 0 0 5px #00ff00; "
)


def generate_menu_style(max_width: str = MAX_MENU_WIDTH) -> str:
    """Generate a common style for menu elements with text truncation."""
    return (
        f"min-width: {MIN_MENU_WIDTH}; "
        f"max-width: {max_width}; "
        "width: 100%; "
        "white-space: nowrap; "
        "overflow: hidden; "
        "text-overflow: ellipsis; "
        "align-items: center; "
        "background-color: var(--pico-background-color); "
        "border-radius: 16px; "
        "border: 1px solid var(--pico-muted-border-color); "
        "display: inline-flex; "
        "font-size: 1rem; "
        "height: 32px; "
        "justify-content: center; "
        "line-height: 32px; "
        "margin: 0 2px; "
    )

# Initialize IDs for menus
profile_id = "profile-id"
action_id = "action-id"
explore_id = "app-id"


# ----------------------------------------------------------------------------------------------------
#  _                      _
# | |figlet_   __ _  __ _(_)_ __   __ _
# | |   / _ \ / _` |/ _` | | '_ \ / _` |
# | |__| (_) | (_| | (_| | | | | | (_| |
# |_____\___/ \__, |\__, |_|_| |_|\__, |
#             |___/ |___/         |___/
# *******************************
# Set up logging with loguru
# *******************************


# Ensure the logs directory exists
logs_dir = 'logs'
if not Path(logs_dir).exists():
    Path(logs_dir).mkdir(parents=True, exist_ok=True)

# Set up log file path
log_file_path = Path(logs_dir) / f'{APP_NAME}.log'

# Remove default logger
logger.remove()

# Add file handler with rotation
logger.add(
    log_file_path,
    rotation="10 MB",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    enqueue=True,
)

# Add colorful console handler
logger.add(
    stderr,
    level="DEBUG",
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{message}</cyan>",
)

# ----------------------------------------------------------------------------------------------------
#   ___  _ _
#  / _ \| | | __ _ _ __ ___   __ _ figlet
# | | | | | |/ _` | '_ ` _ \ / _` |
# | |_| | | | (_| | | | | | | (_| |
#  \___/|_|_|\__,_|_| |_| |_|\__,_|
#
# *******************************
# Ollama LLM for local chatbot
# *******************************


def limit_llm_response(response: str) -> str:
    """Truncate the response to a maximum number of words."""
    return ' '.join(response.split()[:MAX_LLM_RESPONSE_WORDS])


def get_best_model() -> str:
    """
    Retrieve the best available LLaMA model or default to 'llama3.2'.

    This function is a game-changer for local AI applications, leveraging the power of
    ubiquitous Large Language Models (LLMs) right on your machine. It intelligently
    selects the most advanced LLaMA model available, ensuring you're always using
    cutting-edge AI capabilities without the need for cloud-based solutions.

    The function performs the following key steps:
    1. Queries the local Ollama API for available models.
    2. Filters for LLaMA models specifically.
    3. Employs a sophisticated version comparison algorithm to identify the most recent
       and capable model.
    4. Gracefully handles errors and falls back to a default model if necessary.

    This approach enables high-performance, privacy-preserving AI interactions,
    marking a significant advancement in personal and enterprise AI deployment.

    Returns:
        str: The name of the best available LLaMA model, or the default model if no
             LLaMA models are found or in case of an error.
    """
    logger.debug("Attempting to retrieve the best LLaMA model.")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        response.raise_for_status()
        models = [model['name'] for model in response.json().get('models', [])]
        logger.info(f"Available models: {models}")
    except requests.RequestException as e:
        logger.error(f"Error fetching models: {e}")
        return DEFAULT_LLM_MODEL  # Default if there's an error

    llama_models = [model for model in models if model.lower().startswith('llama')]
    if not llama_models:
        logger.warning("No LLaMA models found. Using default model.")
        return DEFAULT_LLM_MODEL  # Default if no LLaMA models are found

    def parse_version(version_string: str) -> List[Optional[int]]:
        """Parse a version string into a list of integers and strings for comparison."""
        return [int(x) if x.isdigit() else x for x in re.findall(r'\d+|\D+', version_string)]

    def key_func(model: str) -> tuple:
        """Generate a sorting key for a LLaMA model based on its version."""
        parts = model.split(':')
        base_name = parts[0]
        version = parts[1] if len(parts) > 1 else ''
        base_version = re.search(r'llama(\d+(?:\.\d+)*)', base_name.lower())
        base_version = base_version.group(1) if base_version else '0'
        return (
            parse_version(base_version),
            1 if version == 'latest' else 0,
            parse_version(version),
        )

    best_model = max(llama_models, key=key_func)
    logger.info(f"Selected best model: {best_model}")
    return best_model


def chat_with_ollama(model: str, messages: list) -> str:
    """
    Interact with the Ollama model to generate a response.

    Args:
        model (str): The name of the model to use.
        messages (list): A list of message dictionaries.

    Returns:
        str: The content of the response message.
    """
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}

    logger.debug(f"Sending request to Ollama: {payload}")
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        content = response.json()['message']['content']
        logger.debug(f"Received response from Ollama: {content}")
        return content
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        return "I'm having trouble processing that request right now."
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Connection error occurred: {conn_err}")
        return "I'm having trouble processing that request right now."
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"Timeout error occurred: {timeout_err}")
        return "I'm having trouble processing that request right now."
    except requests.exceptions.RequestException as req_err:
        logger.error(f"An error occurred: {req_err}")
        return "I'm having trouble processing that request right now."


# ----------------------------------------------------------------------------------------------------
#  ____                     ___     ____
# |  _ \ _ __ __ _  __ _   ( _ )   |  _ \ _ __ ___  _ __
# | | | | '__/ _` |/ _` |  / _ \/\ | | | | '__/ _ \| '_ \
# | |_| | | | (_| | (_| | | (_>  < | |_| | | | (_) | |_) |
# |____/|_|  \__,_|\__, |  \___/\/ |____/|_|  \___/| .__/
#                  |___/           figlet          |_|
# *******************************
# JavaScript Includes mess with code beauty
# *******************************

# This function creates a SortableJS script for drag-and-drop reordering of Todo items.
def SortableJSWithUpdate(
    sel='.sortable',
    ghost_class='blue-background-class'
):
    """
    Create a SortableJS script with update functionality.

    This function generates a JavaScript module that imports and initializes SortableJS,
    enabling drag-and-drop reordering of items. It sets up event handling for reordering
    and updates the server using HTMX after each change.

    Note: SortableJS could be hosted locally for better control and reduced external dependencies.

    Args:
        sel (str): CSS selector for the sortable element.
        ghost_class (str): Class for the ghost element during sorting.

    Returns:
        Script: HTML script element with SortableJS setup.
    """
    src = f"""
import {{Sortable}} from 'https://cdn.jsdelivr.net/npm/sortablejs/+esm';

document.addEventListener('DOMContentLoaded', (event) => {{
    const el = document.querySelector('{sel}');
    if (el) {{
        new Sortable(el, {{
            animation: 150,
            ghost_class: '{ghost_class}',
            onEnd: function (evt) {{
                let items = Array.from(el.children).map((item, index) => ({{
                    id: item.dataset.id,
                    priority: index
                }}));
                
                // Dynamically determine the update URL
                let path = window.location.pathname;
                let updateUrl = path.endsWith('/') ? path + 'sort' : path + '_sort';
                
                htmx.ajax('POST', updateUrl, {{
                    target: el,
                    swap: 'none',
                    values: {{ items: JSON.stringify(items) }}
                }});
            }}
        }});
    }}
}});
"""
    return Script(src, type='module')

# ----------------------------------------------------------------------------------------------------
#  ____  _             _           
# |  _ \| |_   _  __ _(_)_ __  ___ 
# | |_) | | | | |/ _` | | '_ \/ __|
# |  __/| | |_| | (_| | | | | \__ \
# |_|   |_|\__,_|\__, |_|_| |_|___/
#                |___/             
# Plugins
class BaseApp:
    """
    A base class for creating application components with common CRUD operations.

    This class provides a template for building application components that interact
    with database tables and handle basic Create, Read, Update, Delete (CRUD) operations.
    It includes methods for registering routes, rendering items, and performing various
    database operations.

    The class is designed to be flexible and extensible, allowing subclasses to override
    or extend its functionality as needed for specific application components.
    """

    def __init__(self, name, table, toggle_field=None, sort_field=None, sort_dict=None):
        self.name = name
        self.table = table
        self.toggle_field = toggle_field
        self.sort_field = sort_field
        self.sort_dict = sort_dict or {'id': 'id', sort_field: sort_field}

    def register_routes(self, rt):
        # Register routes: create, read, update, delete, toggle, and sort
        rt(f'/{self.name}', methods=['POST'])(self.insert_item)
        rt(f'/{self.name}/{{item_id}}', methods=['POST'])(self.update_item)  # Changed to POST
        rt(f'/{self.name}/delete/{{item_id}}', methods=['DELETE'])(self.delete_item)
        rt(f'/{self.name}/toggle/{{item_id}}', methods=['POST'])(self.toggle_item)
        rt(f'/{self.name}_sort', methods=['POST'])(self.sort_items)

    def get_action_url(self, action, item_id):
        """
        Generate a URL for a specific action on an item.

        Args:
            action (str): The action method (e.g., 'delete', 'toggle').
            item_id (int): The ID of the item.

        Returns:
            str: The constructed URL.
        """
        return f"/{self.name}/{action}/{item_id}"

    def render_item(self, item):
        # A wrapper function currently serving as a passthrough for item rendering.
        # This method is part of the system's "styling" mechanism, transforming
        # dataclasses into HTML or other instructions for display or HTMX operations.
        # Subclasses are expected to override this method with context-aware implementations.
        return item

    async def delete_item(self, request, item_id: int):
        """
        Delete an item from the table.

        Args:
            request: The incoming request object.
            item_id (int): The ID of the item to delete.

        Returns:
            str: An empty string indicating successful deletion.
        """
        try:
            logger.debug(f"Attempting to delete item ID: {item_id}")
            self.table.delete(item_id)
            prompt = f"Item {item_id} deleted. Brief, sassy reaction."
            await chatq(prompt)
            logger.info(f"Deleted item ID: {item_id}")
            return ''
        except Exception as e:
            logger.error(f"Error deleting item: {str(e)}")
            return f"Error deleting item: {str(e)}", 500

    async def toggle_item(self, request, item_id: int):
        """
        Toggle a boolean field of an item.

        Args:
            request: The incoming request object.
            item_id (int): The ID of the item to toggle.

        Returns:
            dict: The rendered updated item.
        """
        try:
            logger.debug(f"Toggling {self.toggle_field} for item ID: {item_id}")
            item = self.table[item_id]
            current_status = getattr(item, self.toggle_field)
            setattr(item, self.toggle_field, not current_status)
            updated_item = self.table.update(item)
            logger.info(f"Toggled {self.toggle_field} for item ID {item_id} to {getattr(updated_item, self.toggle_field)}")

            prompt = f"Item {item_id} toggled. Brief, sassy reaction."
            await chatq(prompt)

            return self.render_item(updated_item)  # Use the subclass's render_item method
        except Exception as e:
            logger.error(f"Error toggling item: {str(e)}")
            return f"Error toggling item: {str(e)}", 500

    async def sort_items(self, request):
        """
        Update the order of items based on the received values.
        """
        logger.debug(f"Received request to sort {self.name}.")
        try:
            values = await request.form()  # Get form data from request
            items = json.loads(values.get('items', '[]'))  # Decode JSON string to list
            logger.debug(f"Parsed items: {items}")
            for item in items:
                logger.debug(f"Updating item: {item}")
                update_dict = {self.sort_field: int(item['priority'])}  # Use priority
                self.table.update(id=int(item['id']), **update_dict)  # Update table entry
            logger.info(f"{self.name.capitalize()} order updated successfully")

            prompt = f"The {self.name} list was reordered. Make a brief, witty remark about sorting or prioritizing. Keep it under 20 words."
            await chatq(prompt)

            return ''
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return "Invalid data format", 400
        except Exception as e:
            logger.error(f"Error updating {self.name} order: {str(e)}")
            return str(e), 500

    async def insert_item(self, request):
        """
        Create a new item in the table.
        """
        try:
            form = await request.form()
            new_item_data = self.prepare_insert_data(form)
            if not new_item_data:  # If prepare_insert_data returns empty string or empty dict
                return ''  # Return empty string, which won't be rendered in the DOM
            new_item = await self.create_item(**new_item_data)
            return self.render_item(new_item)
        except Exception as e:
            logger.error(f"Error inserting {self.name}: {str(e)}")
            return str(e), 500

    async def update_item(self, request, item_id: int):
        """
        Update an existing item in the table.
        """
        try:
            form = await request.form()
            update_data = self.prepare_update_data(form)
            if not update_data:  # If prepare_update_data returns empty string or empty dict
                return ''  # Return empty string, which won't be rendered in the DOM
            item = self.table[item_id]
            for key, value in update_data.items():
                setattr(item, key, value)
            updated_item = self.table.update(item)
            logger.info(f"Updated {self.name} item {item_id}")
            return self.render_item(updated_item)
        except Exception as e:
            logger.error(f"Error updating {self.name} {item_id}: {str(e)}")
            return str(e), 500

    def prepare_insert_data(self, form):
        """
        Prepare data for insertion. To be overridden by subclasses.
        """
        raise NotImplementedError("Subclasses must implement prepare_insert_data")

    def prepare_update_data(self, form):
        """
        Prepare data for update. To be overridden by subclasses.
        """
        raise NotImplementedError("Subclasses must implement prepare_update_data")

    async def create_item(self, **kwargs):
        """
        Create a new item in the table.

        Args:
            **kwargs: The fields and values for the new item.

        Returns:
            The newly created item.
        """
        try:
            logger.debug(f"Creating new {self.name} with data: {kwargs}")
            new_item = self.table.insert(kwargs)
            logger.info(f"Created new {self.name}: {new_item}")
            return new_item
        except Exception as e:
            logger.error(f"Error creating {self.name}: {str(e)}")
            raise e


class TodoApp(BaseApp):
    def __init__(self, table):
        # Extract the name from the table object
        super().__init__(
            name=table.name,
            table=table,
            toggle_field='done',
            sort_field='priority'
        )

    def render_item(self, todo):
        return render_todo(todo)

    def prepare_insert_data(self, form):
        title = form.get('title', '').strip()
        if not title:
            return ''  # Return empty string instead of raising an exception
        current_profile_id = db.get("last_profile_id", 1)
        max_priority = max((t.priority or 0 for t in self.table()), default=-1) + 1
        return {
            "title": title,
            "done": False,
            "priority": max_priority,
            "profile_id": current_profile_id,
        }

    def prepare_update_data(self, form):
        title = form.get('title', '').strip()
        if not title:
            return ''  # Return empty string instead of raising an exception
        return {
            "title": title,
            "done": form.get('done', '').lower() == 'true',
        }


class ProfileApp(BaseApp):
    def __init__(self, table):
        super().__init__(
            name=table.name,
            table=table,
            toggle_field='active',
            sort_field='priority'
        )

    def render_item(self, profile):
        return render_profile(profile)

    def prepare_insert_data(self, form):
        profile_name = form.get('profile_name', '').strip()
        if not profile_name:
            return ''  # Return empty string instead of raising an exception
        max_priority = max((p.priority or 0 for p in self.table()), default=-1) + 1
        return {
            "name": profile_name,
            "address": form.get('profile_address', '').strip(),
            "code": form.get('profile_code', '').strip(),
            "active": True,
            "priority": max_priority,
        }

    def prepare_update_data(self, form):
        profile_name = form.get('profile_name', '').strip()
        if not profile_name:
            return ''  # Return empty string instead of raising an exception
        return {
            "name": profile_name,
            "address": form.get('profile_address', '').strip(),
            "code": form.get('profile_code', '').strip(),
            "active": form.get('active', '').lower() == 'true',
        }


# ----------------------------------------------------------------------------------------------------
#  _____         _   _   _ _____ __  __ _
# |  ___|_ _ ___| |_| | | |_   _|  \/  | |
# | |_ / _` / __| __| |_| | | | | |\/| | |
# |  _| (_| \__ \ |_|  _  | | | | |  | | |___
# |_|  \__,_|___/\__|_| |_| |_| |_|  |_|_____|figlet
#
# *******************************
# It's a fastapp table splat, not dataclass alone!
# *******************************


# Unpack the returned tuple from fast_app (lots of explaining to do here)
app, rt, (store, Store), (tasks, Task), (customers, Customer) = fast_app(
    "data/data.db",
    ws_hdr=True,
    live=True,
    hdrs=(
        SortableJSWithUpdate('.sortable'),
        Script(type='module')
    ),
    store={
        "key": str,
        "value": str,
        "pk": "key"
    },
    task={ 
        "id": int,
        "title": str,
        "done": bool,
        "priority": int,
        "profile_id": int,
        "pk": "id"
    },
    customer={
        "id": int,
        "name": str,
        "address": str,
        "code": str,
        "active": bool,
        "priority": int,
        "pk": "id"
    },
)

# Instantiate and register routes
todo_app = TodoApp(table=tasks)
todo_app.register_routes(rt)

profile_app = ProfileApp(table=customers)
profile_app.register_routes(rt)

# Aliases for table names
todos = tasks
profiles = customers

# Configurable constants for table names and endpoints
MENU_ITEMS = [todo_app.name, 'app_1', 'app_2', 'app_3']


# ----------------------------------------------------------------------------------------------------
#  ____  _      _   _     _ _ figlet ____  ____
# |  _ \(_) ___| |_| |   (_) | _____|  _ \| __ )
# | | | | |/ __| __| |   | | |/ / _ \ | | |  _ \
# | |_| | | (__| |_| |___| |   <  __/ |_| | |_) |
# |____/|_|\___|\__|_____|_|_|\_\___|____/|____/
#
# *******************************
# DictLikeDB Persistence Convenience Wrapper
# *******************************


class DictLikeDB:
    """
    A robust wrapper for dictionary-like persistent storage.

    This class provides a familiar dict-like interface to interact with
    various types of key-value stores, including databases and file systems.
    It emphasizes the power and flexibility of key-value pairs as a
    fundamental data structure in programming and system design.

    Key features:
    1. Persistence: Data survives beyond program execution.
    2. Dict-like API: Familiar Python dictionary operations.
    3. Adaptability: Can wrap different storage backends.
    4. Logging: Built-in logging for debugging and monitoring.

    By abstracting the underlying storage mechanism, this class allows
    for easy swapping of backends without changing the client code.
    This demonstrates the power of Python's duck typing and the
    universality of the key-value paradigm across different storage solutions.
    """

    def __init__(self, store, Store):
        self.store = store
        self.Store = Store

    def __getitem__(self, key):
        """Retrieve an item from the store by key."""
        try:
            value = self.store[key].value
            logger.debug(f"Retrieved from DB: {key} = {value}")
            return value
        except NotFoundError:
            logger.error(f"Key not found: {key}")
            raise KeyError(key)

    def __setitem__(self, key, value):
        """Set an item in the store by key."""
        try:
            self.store.update({"key": key, "value": value})
            logger.info(f"Updated persistence store: {key} = {value}")
        except NotFoundError:
            self.store.insert({"key": key, "value": value})
            logger.info(f"Inserted new item in persistence store: {key} = {value}")

    def __delitem__(self, key):
        """Delete an item from the store by key."""
        try:
            self.store.delete(key)
            logger.warning(f"Deleted key from persistence store: {key}")
        except NotFoundError:
            logger.error(f"Attempted to delete non-existent key: {key}")
            raise KeyError(key)

    def __contains__(self, key):
        """Check if a key exists in the store."""
        exists = key in self.store
        logger.debug(f"Key '{key}' exists: {exists}")
        return exists

    def __iter__(self):
        """Iterate over the keys in the store."""
        for item in self.store():
            yield item.key

    def items(self):
        """Return key-value pairs in the store."""
        for item in self.store():
            yield item.key, item.value

    def keys(self):
        """Return a list of keys in the store."""
        return list(self)

    def values(self):
        """Return values in the store."""
        for item in self.store():
            yield item.value

    def get(self, key, default=None):
        """Get an item from the store, returning default if not found."""
        try:
            return self[key]
        except KeyError:
            logger.debug(f"Key '{key}' not found. Returning default.")
            return default


# Create the wrapper
db = DictLikeDB(store, Store)
logger.info("Database wrapper initialized.")

# *******************************
# Database Initialization
# *******************************


def populate_initial_data():
    """
    Populate the database with initial data if empty.

    This function ensures that there is at least one profile and one todo item in the database.
    """
    logger.debug("Populating initial data.")
    if not profiles():
        # Create a default profile
        default_profile = profiles.insert({
            "name": f"Default {profile_app.name.capitalize()}",  # Updated to use CUSTOMER
            "address": "",
            "code": "",
            "active": True,
            "priority": 0,
        })
        logger.info(f"Inserted default profile: {default_profile}")
    else:
        default_profile = profiles()[0]

    if not todos():
        # Add a sample todo with the default profile_id
        todos.insert({
            "title": f"Sample {todo_app.name}",
            "done": False,
            "priority": 1,
            "profile_id": default_profile.id,
        })
        logger.info(f"Inserted sample {todo_app.name} item.")


# Call this function after the fast_app initialization
populate_initial_data()

# ----------------------------------------------------------------------------------------------------
#  _   _             _             _   _
# | \ | | __ ___   _(_) __ _  __ _| |_(_) ___  _ __
# |  \| |/ _` \ \ / / |/ _` |/ _` | __| |/ _ \| '_ \
# | |\  | (_| |\ V /| | (_| | (_| | |_| | (_) | | | |
# |_| \_|\__,_| \_/ |_|\__, |\__,_|\__|_|\___/|_| |_|
#                      |___/
# *******************************
# Site Navigation
# *******************************


def create_nav_menu():
    """
    Create the navigation menu with app, profile, and action dropdowns.

    Returns:
        Div: An HTML div containing the navigation menu.
    """
    def get_selected_item_style(is_selected):
        return "background-color: var(--pico-primary-background); " if is_selected else ""

    # Housekeeping
    logger.debug("Creating navigation menu.")
    menux = db.get("last_app_choice", "App")
    selected_profile_id = db.get("last_profile_id")
    selected_profile_name = get_profile_name()

    # What we're going to do is fill this list with items, and then return it as a Div
    nav_items = []

    #  ___ _ _ _
    # | __(_) | |___ _ _
    # | _|| | | / -_) '_|
    # |_| |_|_|_\___|_|
    # Filler Item: Non-interactive, occupies significant space
    filler_item = Li(
        Span(" "),
        style=(
            "display: flex; "
            "flex-grow: 1; "
            "justify-content: center; "
            "list-style-type: none; "
            f"min-width: {NAV_FILLER_WIDTH}; "
        ),
    )

    # We begin with a filler item
    nav_items.append(filler_item)
    logger.debug(f"Adding {profile_app.name.lower()} menu to navigation.")

    #  ___          __ _ _       ___        _ _      _
    # | _ \_ _ ___ / _(_) |___  / __|_ __ _(_) |_ __| |_  ___ _ _
    # |  _/ '_/ _ \  _| | / -_) \__ \ V  V / |  _/ _| ' \/ -_) '_|
    # |_| |_| \___/_| |_|_\___| |___/\_/\_/|_|\__\__|_||_\___|_|
    # The Profile Switcher menu

    # This will be the list of items in the profile menu
    menu_items = []

    # Add selection to top of profile-switcher menu in order to Edit Profiles
    menu_items.append(
        create_menu_item(
            f"Edit {format_endpoint_name(profile_app.name)} {LIST_SUFFIX}",
            f"/{profile_app.name}",
            profile_id,
            is_traditional_link=True,
            additional_style=(
                "font-weight: bold; "
                "border-bottom: 1px solid var(--pico-muted-border-color);"
            )
        )
    )

    # Fetch the whole list of Active Profiles from the DB
    active_profiles = profiles("active=?", (True,), order_by='priority')
    # One of these will be selected, and we'll use this to set the 'checked' attribute
    selected_profile_id = db.get("last_profile_id")

    # Now we'll loop through the list of active profiles and add them to the menu
    for profile in active_profiles:
        # We'll check if this profile is the one that was most recently selected
        is_selected = str(profile.id) == str(selected_profile_id)
        # And we'll apply a style to the item if it is

        item_style = get_selected_item_style(is_selected)
        menu_items.append(
            Li(
                Label(
                    Input(
                        type="radio",
                        name="profile",
                        value=str(profile.id),
                        checked=is_selected,
                        hx_get=f"/{profile_app.name}/{profile.id}",
                        hx_target=f"#{profile_id}",
                        hx_swap="outerHTML",
                    ),
                    profile.name,
                    style="display: flex; align-items: center;"
                ),
                style=f"text-align: left; {item_style}"
            )
        )

    # Define the profile menu
    profile_menu = Details(
        Summary(
            f"{profile_app.name.upper()}: {selected_profile_name}",
            style=generate_menu_style(NOWRAP_STYLE),  # Menus don't wrap
            id=profile_id,
        ),
        Ul(
            *menu_items,
            style="padding-left: 0;",
        ),
        cls="dropdown",
    )

    # And now the Profile Switcher is an item on the menu.
    nav_items.append(profile_menu)
    logger.debug("Adding app menu to navigation.")

    #    _               ___        _ _      _
    #   /_\  _ __ _ __  / __|_ __ _(_) |_ __| |_  ___ _ _
    #  / _ \| '_ \ '_ \ \__ \ V  V / |  _/ _| ' \/ -_) '_|
    # /_/ \_\ .__/ .__/ |___/\_/\_/|_|\__\__|_||_\___|_|
    #       |_|  |_|
    # App Switcher menu

    # We recycle the menu_items list for the apps menu
    menu_items = []

    # We'll loop through the list of menu items and add them to the menu
    for item in MENU_ITEMS:
        # We'll check if this item is the one that was most recently selected
        is_selected = item == db.get("last_app_choice")
        item_style = (
            "background-color: var(--pico-primary-background); " if is_selected else ""
        )
        # These are going to be "splat" into the menu
        menu_items.append(
            Li(
                A(
                    format_endpoint_name(item),
                    href=f"/{item}",
                    cls="dropdown-item",
                    style=f"{NOWRAP_STYLE} {item_style}"
                ),
                style="display: block;"
            )
        )

    # Put the apps menu together
    apps_menu = Details(
        Summary(
            # App names often made from Capitalized Words from URL endpoint_paths
            f"APP: {format_endpoint_name(menux)}",
            style=generate_menu_style(NOWRAP_STYLE),
            id=explore_id,
        ),
        Ul(
            *menu_items,  # Splat
            cls="dropdown-menu",
        ),
        cls="dropdown",
    )

    # And now the Apps Switcher is an item on the menu.
    nav_items.append(apps_menu)
    logger.debug("Adding search input to navigation.")

    #  ___                  _      __  __
    # / __| ___ __ _ _ _ __| |_   |  \/  |___ _ _ _  _
    # \__ \/ -_) _` | '_/ _| ' \  | |\/| / -_) ' \ || |
    # |___/\___\__,_|_| \__|_||_| |_|  |_\___|_||_\_,_|
    # Search Feature on the menu

    # Clean this up when you have the time

    # Create the search input group wrapped in a form
    search_group = Form(
        Group(
            Input(
                type="search",
                placeholder="Search",
                name="nav_input",
                id="nav-input",
                hx_post="/search",
                hx_trigger="keyup[keyCode==13]",
                hx_target="#msg-list",
                hx_swap="innerHTML",
                style=(
                    f"{generate_menu_style(NOWRAP_STYLE)} "
                    f"width: {NOWRAP_STYLE}; "
                    "padding-right: 0px; "
                    "border: 1px solid var(--pico-muted-border-color); "
                ),
            ),
        ),
        hx_post="/search",
        hx_target="#msg-list",
        hx_swap="innerHTML",
    )

    # The navigation menu is now complete.
    nav_items.append(search_group)

    # Create the navigation container
    nav = Div(
        *nav_items,  # Nav items splat into the container
        style=(
            "display: flex; "  # Keep the items in a row
            "gap: 20px; "
        ),
    )

    # Return the navigation container
    logger.debug("Navigation menu created.")
    return nav


def create_menu_item(title, link, summary_id, is_traditional_link=False, additional_style=""):
    """
    Centralizes how Li's are created for the menu. Good for HTMX.

    Args:
        title (str): The display title of the menu item.
        link (str): The URL or endpoint the menu item points to.
        summary_id (str): The ID of the summary element to target.
        is_traditional_link (bool): If True, use a traditional href link.
        additional_style (str): Any additional CSS styles to apply.

    Returns:
        Li: An HTML list item representing the menu item.
    """
    item_style = f"text-align: center; {additional_style}"
    if is_traditional_link:
        return Li(
            A(
                title,
                href=link,
                cls="menu-item",
                style=item_style,
            )
        )
    else:
        return Li(
            A(
                title,
                hx_get=link,
                hx_target=f"#{summary_id}",
                hx_swap="outerHTML",
                hx_trigger="click",
                hx_push_url="false",
                cls="menu-item",
                style=item_style,
            )
        )


# ----------------------------------------------------------------------------------------------------
#   ____ _           _
#  / ___| |__   __ _| |_ figlet
# | |   | '_ \ / _` | __|
# | |___| | | | (_| | |_
#  \____|_| |_|\__,_|\__|
#
# *******************************
# It seems today that where it's at is reliance on AI and streaming in chat
# *******************************

def mk_chat_input_group(disabled=False, value='', autofocus=True):
    """
    Create a chat input group with a message input and a send button.

    Args:
        disabled (bool): Whether the input group should be disabled.
        value (str): The pre-filled value for the input field.
        autofocus (bool): Whether the input field should autofocus.

    Returns:
        Group: An HTML group containing the chat input and send button.
    """
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
            ws_send=True,
            id='send-btn',
            disabled=disabled,
        ),
        id='input-group',
    )

# ----------------------------------------------------------------------------------------------------
#  ____ figlet      __ _ _        ____          _ _       _
# |  _ \ _ __ ___  / _(_) | ___  / ___|_      _(_) |_ ___| |__   ___ _ __
# | |_) | '__/ _ \| |_| | |/ _ \ \___ \ \ /\ / / | __/ __| '_ \ / _ \ '__|
# |  __/| | | (_) |  _| | |  __/  ___) \ V  V /| | || (__| | | |  __/ |
# |_|   |_|  \___/|_| |_|_|\___| |____/ \_/\_/ |_|\__\___|_| |_|\___|_|
# *******************************
# Profile Switcher invisibly switches profiles, HTML-style!
# *******************************


@rt(f'/{profile_app.name}/{{profile_id}}')
def profile_menu_handler(request, profile_id: int):
    """
    Handle profile menu selection seamlessly using HTMX.

    This function operates in the background without page reloads to:
    1. Process the Profile Switcher menu selection
    2. Update persistent storage with the new profile choice
    3. Return the user to their previous location seamlessly

    Args:
        request: The incoming HTTP request.
        profile_id (int): The ID of the selected profile.

    Returns:
        Redirect: A redirect response to the last visited URL.
    """
    logger.debug(f"Profile menu selected with profile_id: {profile_id}")

    db["last_profile_id"] = profile_id

    if not profile_id:
        logger.error(f"Profile ID {profile_id} not found. Redirecting to /{profile_app.name}.")
        return Redirect(f'/{profile_app.name}')

    last_profile_name = get_profile_name()
    fig(f"{profile_app.name}: {last_profile_name}\nID: {profile_id}")
    logger.info(f"Profile selected: {last_profile_name} (ID: {profile_id})")

    last_visited_url = db.get("last_visited_url", "/")

    return Redirect(last_visited_url)

# ----------------------------------------------------------------------------------------------------
#  __  __       _         ____ figlet
# |  \/  | __ _(_)_ __   |  _ \ __ _  __ _  ___
# | |\/| |/ _` | | '_ \  | |_) / _` |/ _` |/ _ \
# | |  | | (_| | | | | | |  __/ (_| | (_| |  __/
# |_|  |_|\__,_|_|_| |_| |_|   \__,_|\__, |\___|
#                                    |___/
# *******************************
# Main Page wraps like a boss
# *******************************


@rt('/')
@rt(f'/{todo_app.name}')
@rt(f'/{profile_app.name}')
def get(request):
    """
    Handle main page and specific page GET requests.

    This function serves as the central routing and rendering mechanism for the application.
    It processes requests for the main page and specific app pages defined in MENU_ITEMS.
    New apps can be easily integrated by adding them to the MENU_ITEMS list and implementing
    their corresponding render and CRUD functions.

    The function performs the following key tasks:
    1. Determines the requested path and sets up the appropriate menu context.
    2. Applies profile filtering if necessary.
    3. Creates the main content, including navigation and app-specific views.
    4. Handles the Todo app view if requested.
    5. Provides a structure for adding new app views seamlessly.

    To add a new app:
    1. Add the app name to the MENU_ITEMS list.
    2. Implement a render function for the app (e.g., render_new_app()).
    3. Create CRUD functions for the app (e.g., new_app_create(), new_app_update(), etc.).
    4. Add a condition in this function to handle the new app's view, similar to the Todo view.

    The function uses HTMX for dynamic content updates, allowing for a smooth single-page
    application (SPA) experience. Refer to the Todo and Profile apps for examples of
    how to structure new app components.

    Args:
        request: The incoming HTTP request.

    Returns:
        Titled: An HTML response with the appropriate title and content for the requested page.
    """
    path = request.url.path.strip('/')
    logger.debug(f"Received request for path: {path}")

    menux = "home"
    if path:
        menux = path

    fig(f"app: {menux}")
    logger.info(f"Selected explore item: {menux}")
    db["last_app_choice"] = menux
    db["last_visited_url"] = request.url.path

    # Apply the profile filter if necessary
    current_profile_id = db.get("last_profile_id")
    if current_profile_id:
        logger.debug(f"Current profile ID: {current_profile_id}")
        todos.xtra(profile_id=current_profile_id)
    else:
        logger.warning("No current profile ID found. Using default filtering.")
        todos.xtra(profile_id=None)

    if menux == profile_app.name:
        response = get_profiles_content()
    else:
        # Merged create_main_content logic
        logger.debug("Creating main content.")
        nav = create_nav_menu()
        nav_group_style = (
            "display: flex; "
            "align-items: center; "
            "position: relative;"
        )
        nav_group = Group(
            nav,
            style=nav_group_style,
        )

        if current_profile_id is None:
            # Fetch the first profile using MiniDataAPI
            first_profiles = profiles(order_by='id', limit=1)
            if first_profiles:
                current_profile_id = first_profiles[0].id
                db["last_profile_id"] = current_profile_id
                logger.info(f"Set default profile ID to {current_profile_id}")
            else:
                logger.warning("No profiles found in the database")
                current_profile_id = None

        # If we have a current_profile_id, set it as an xtra filter on the todos table
        if current_profile_id is not None:
            todos.xtra(profile_id=current_profile_id)

        menux = db.get("last_app_choice", "App")

        # Check if menux matches either singular or plural form of TASK
        is_todo_view = (menux == todo_app.name)

        # Fetch the filtered todo items and sort them by priority
        todo_items = sorted(todos(), key=lambda x: x.priority)
        logger.info(f"Fetched {len(todo_items)} todo items for profile ID {current_profile_id}.")

        response = Container(
            nav_group,
            Grid(
                Div(
                    Card(
                        H2(f"{pluralize(menux, singular=True)} {LIST_SUFFIX}"),
                        Ul(*[render_todo(todo) for todo in todo_items],
                           id='todo-list',
                           cls='sortable',
                           style="padding-left: 0;"),
                        header=Form(
                            Group(
                                Input(
                                    placeholder=f'Add new {todo_app.name.capitalize()}',
                                    id='title',
                                    name='title',
                                    autofocus=True,
                                ),
                                Button("Add", type="submit"),
                            ),
                            hx_post=f"/{todo_app.name}",
                            hx_swap="beforeend",
                            hx_target="#todo-list",
                        ),
                    ) if is_todo_view else Card(
                        H2(f"{pluralize(menux, singular=True)}"),
                        P("This is a placeholder for the selected application."),
                    ),
                    id="content-container",
                ),
                Div(
                    Card(
                        H2(f"{APP_NAME} Chatbot"),
                        Div(
                            id='msg-list',
                            cls='overflow-auto',
                            style='height: 40vh;',
                        ),
                        footer=Form(
                            mk_chat_input_group(),
                        ),
                    ),
                ),
                cls="grid",
                style=(
                    "display: grid; "
                    "gap: 20px; "
                    f"grid-template-columns: {GRID_LAYOUT}; "
                ),
            ),
            Div(
                A(
                    f"Poke {APP_NAME} Chatbot",
                    hx_post="/poke",
                    hx_target="#msg-list",
                    hx_swap="innerHTML",
                    cls="button",
                ),
                style=(
                    "bottom: 20px; "
                    "position: fixed; "
                    "right: 20px; "
                    "z-index: 1000; "
                ),
            ),
            Script("""
                document.addEventListener('htmx:afterSwap', function(event) {
                    if (event.target.id === 'todo-list' && event.detail.successful) {
                        const form = document.querySelector('form[hx-target="#todo-list"]');
                        if (form) {
                            form.reset();
                        }
                    }
                });
            """)
        )

    logger.debug("Returning response for main GET request.")
    # Choose the profile name based on the last_profile_id
    last_profile_name = get_profile_name()
    return Titled(
        f"{APP_NAME} / {pluralize(last_profile_name, singular=True)} / {pluralize(menux, singular=True)}",
        response,
        hx_ext='ws',
        ws_connect='/ws',
        data_theme="dark",
    )


# This makes the Main Page serve all the endpoints in MENU_ITEMS
for item in MENU_ITEMS:
    app.add_route(f'/{item}', get)


# ----------------------------------------------------------------------------------------------------
#  ____             __ _ _                _ figlet
# |  _ \ _ __ ___  / _(_) | ___  ___     / \   _ __  _ __
# | |_) | '__/ _ \| |_| | |/ _ \/ __|   / _ \ | '_ \| '_ \
# |  __/| | | (_) |  _| | |  __/\__ \  / ___ \| |_) | |_) |
# |_|   |_|  \___/|_| |_|_|\___||___/ /_/   \_\ .__/| .__/
#                                             |_|   |_|
# *******************************
# Profiles App is a plugin you can't unplug
# *******************************

def get_profiles_content():
    """
    Retrieve and display the list of profiles.

    This function handles the Profiles app, which is a special case as it controls
    the Profile switcher menu. For a more typical example of a plugin app within
    the Pipulate framework, refer to the Todo app.

    Returns:
        Container: An HTML container with the profiles list and chat interface.
    """
    logger.debug(f"Retrieving {profile_app.name.lower()} for display.")
    # Create the navigation group
    nav_group = create_nav_menu()

    # Fetch all profiles
    all_profiles = profiles()

    # Log the initial state of profiles
    logger.debug("Initial profile state:")
    for profile in all_profiles:
        logger.debug(f"Profile {profile.id}: name = {profile.name}, priority = {profile.priority}")

    # Sort profiles by priority, handling None values
    ordered_profiles = sorted(all_profiles, key=lambda p: p.priority if p.priority is not None else float('inf'))

    logger.debug("Ordered profile list:")
    for profile in ordered_profiles:
        logger.debug(f"Profile {profile.id}: name = {profile.name}, priority = {profile.priority}")

    return Container(
        nav_group,
        Grid(
            Div(
                Card(
                    H2(f"{profile_app.name.capitalize()} {LIST_SUFFIX}"),
                    Ul(*[render_profile(profile) for profile in ordered_profiles],
                       id='profile-list',
                       cls='sortable',
                       style="padding-left: 0;"),
                    footer=Form(
                        Group(
                            Input(placeholder=f"{profile_app.name.capitalize()} Name", name="profile_name", id="profile-name-input"),
                            Input(placeholder=PLACEHOLDER_ADDRESS, name="profile_address", id="profile-address-input"),
                            Input(placeholder=PLACEHOLDER_CODE, name="profile_code", id="profile-code-input"),
                            Button("Add", type="submit", id="add-profile-button"),
                        ),
                        hx_post=f"/{profile_app.name}",
                        hx_target="#profile-list",
                        hx_swap="beforeend",
                        hx_swap_oob="true",
                    ),
                ),
                id="content-container",
            ),
            Div(
                Card(
                    H2(f"{APP_NAME} Chatbot"),
                    Div(
                        id='msg-list',
                        cls='overflow-auto',
                        style='height: 40vh;',
                    ),
                    footer=Form(
                        mk_chat_input_group(),
                    ),
                ),
            ),
            cls="grid",
            style=(
                "display: grid; "
                "gap: 20px; "
                f"grid-template-columns: {GRID_LAYOUT}; "
            ),
        ),
        Script("""
            document.addEventListener('htmx:afterSwap', function(event) {
                if (event.target.id === 'profile-list' && event.detail.successful) {
                    const form = document.getElementById('add-profile-button').closest('form');
                    form.reset();
                }
            });
        """)
    )


def render_profile(profile):
    """
    Render a profile item as an HTML list item.

    This function creates a detailed HTML representation of a profile, including:
    - A checkbox to toggle the profile's active status
    - A link to display the profile name and associated todo count
    - Contact information (address and code) if available
    - A delete button (visible only when the profile has no associated todos)
    - A hidden update form for editing profile details

    The function also includes JavaScript for toggling the visibility of the update form
    and other elements when the profile name is clicked.

    Args:
        profile: The profile object containing attributes like id, name, address, code, and active status.

    Returns:
        Li: An HTML list item (Li) object representing the fully rendered profile with all interactive elements.
    """
    def count_records_with_xtra(table_handle, xtra_field, xtra_value):
        """
        Count records in table matching xtra field constraint.

        Args:
            table_handle: MiniDataAPI table object.
            xtra_field (str): Field name to constrain.
            xtra_value: Value to constrain by.

        Returns:
            int: Number of matching records.
        """
        table_handle.xtra(**{xtra_field: xtra_value})
        count = len(table_handle())
        logger.debug(f"Counted {count} records in table for {xtra_field} = {xtra_value}")
        return count

    # Count the number of todo items for this profile
    todo_count = count_records_with_xtra(todos, 'profile_id', profile.id)

    # Set the visibility of the delete icon based on the todo count
    delete_icon_visibility = 'inline' if todo_count == 0 else 'none'

    # Use the ProfileApp instance to generate URLs
    delete_url = profile_app.get_action_url('delete', profile.id)
    toggle_url = profile_app.get_action_url('toggle', profile.id)

    # Create the delete button (trash can)
    delete_icon = A(
        '🗑',
        hx_delete=delete_url,
        hx_target=f'#profile-{profile.id}',
        hx_swap='outerHTML',
        style=f"cursor: pointer; display: {delete_icon_visibility};",
        cls="delete-icon"
    )

    # Create the active checkbox
    active_checkbox = Input(
        type="checkbox",
        name="active" if profile.active else None,
        checked=profile.active,
        hx_post=toggle_url,
        hx_target=f'#profile-{profile.id}',
        hx_swap="outerHTML",
        style="margin-right: 5px;"
    )

    # Create the update form
    update_form = Form(
        Group(
            Input(type="text", name="profile_name", value=profile.name, placeholder="Name", id=f"name-{profile.id}"),
            Input(type="text", name="profile_address", value=profile.address, placeholder=PLACEHOLDER_ADDRESS, id=f"address-{profile.id}"),
            Input(type="text", name="profile_code", value=profile.code, placeholder=PLACEHOLDER_CODE, id=f"code-{profile.id}"),
            Button("Update", type="submit"),
        ),
        hx_post=f"/{profile_app.name}/{profile.id}",  # Adjusted URL to match route
        hx_target=f'#profile-{profile.id}',
        hx_swap='outerHTML',
        style="display: none;",
        id=f'update-form-{profile.id}'
    )

    # Create the title link with an onclick event to toggle the update form
    title_link = A(
        f"{profile.name} ({todo_count})",
        href="#",
        hx_trigger="click",
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

    # Create the contact info span, only if address or code is present
    contact_info = []
    if profile.address:
        contact_info.append(profile.address)
    if profile.code:
        contact_info.append(profile.code)

    contact_info_span = (
        Span(f" ({', '.join(contact_info)})", style="margin-left: 10px;")
        if contact_info else
        Span()  # Empty span if no contact info
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
        data_id=profile.id,  # Add this line
        data_priority=profile.priority,  # Add this line
        style="list-style-type: none;"
    )


# ----------------------------------------------------------------------------------------------------
#  _____         _ figlet     _
# |_   _|__   __| | ___      / \   _ __  _ __
#   | |/ _ \ / _` |/ _ \    / _ \ | '_ \| '_ \
#   | | (_) | (_| | (_) |  / ___ \| |_) | |_) |
#   |_|\___/ \__,_|\___/  /_/   \_\ .__/| .__/
#                                 |_|   |_|
# *******************************
# Todo App because isn't everything a list of lists?
# *******************************

def render_todo(todo):
    """
    Render a todo item as an HTML list item with an update form.

    This function serves as an example of a plugin component within the Pipulate framework.
    It demonstrates how to create a modular element that can be seamlessly integrated
    into the main application structure, specifically for the Todo app.

    The function creates an interactive todo item with the following features:
    1. A checkbox to toggle the todo's completion status
    2. A delete button (trash can icon) to remove the todo
    3. A clickable title that reveals an update form
    4. An update form for editing the todo's title

    To implement similar components:
    1. Create a function like this one that returns the HTML structure for your component.
    2. Ensure the component includes necessary HTMX attributes for dynamic interactions.
    3. Implement corresponding server-side endpoints to handle the component's actions.
    4. Integrate the component into the main app structure, typically within a list or container.

    For an example of how this function is used, look for the 'get_profiles_content' function
    or the main route handler, where you'll find this function being called to render individual todo items.

    Args:
        todo: The todo item to render, containing properties like id, title, done, and priority.

    Returns:
        Li: An HTML list item representing the interactive todo component.
    """

    # Use the TodoApp instance to generate URLs
    delete_url = todo_app.get_action_url('delete', todo.id)
    toggle_url = todo_app.get_action_url('toggle', todo.id)

    tid = f'todo-{todo.id}'  # Unique ID for the todo item
    checkbox = Input(
        type="checkbox",
        name="english" if todo.done else None,
        checked=todo.done,
        hx_post=toggle_url,
        hx_swap="outerHTML",
        hx_target=f"#{tid}",
    )

    # Create the delete button (trash can)
    delete = A(
        '🗑',
        hx_delete=delete_url,
        hx_swap='outerHTML',
        hx_target=f"#{tid}",
        style="cursor: pointer; display: inline;",
        cls="delete-icon"
    )

    # Create an interactive title link using FastHTML's A() function
    # This demonstrates how FastHTML allows embedding raw JavaScript via the onclick attribute
    # The result is a smooth, app-like experience with client-side interactivity
    title_link = A(
        todo.title,
        href="#",
        cls="todo-title",
        style="text-decoration: none; color: inherit;",
        onclick=(
            "let updateForm = this.nextElementSibling; "
            "let checkbox = this.parentNode.querySelector('input[type=checkbox]'); "
            "let deleteIcon = this.parentNode.querySelector('.delete-icon'); "
            "if (updateForm.style.visibility === 'hidden' || updateForm.style.visibility === '') { "
            "    updateForm.style.visibility = 'visible'; "
            "    updateForm.style.height = 'auto'; "
            "    checkbox.style.display = 'none'; "
            "    deleteIcon.style.display = 'none'; "
            "    this.remove(); "
            "    const inputField = document.getElementById('todo_title_" + str(todo.id) + "'); "
            "    inputField.focus(); "
            "    inputField.setSelectionRange(inputField.value.length, inputField.value.length); "
            "} else { "
            "    updateForm.style.visibility = 'hidden'; "
            "    updateForm.style.height = '0'; "
            "    checkbox.style.display = 'inline'; "
            "    deleteIcon.style.display = 'inline'; "
            "    this.style.visibility = 'visible'; "
            "}"
        )
    )
    # This complex JavaScript enables a responsive, dynamic UI
    # It toggles visibility of form elements and handles focus, creating a seamless editing experience
    # While it adds complexity, it significantly enhances the user interface's responsiveness

    # Create the update form
    update_form = Form(
        Div(
            Input(
                type="text",
                id=f"todo_title_{todo.id}",
                value=todo.title,
                name="title",
                style="flex: 1; padding-right: 10px; margin-bottom: 0px;"
            ),
            style="display: flex; align-items: center;"
        ),
        style="visibility: hidden; height: 0; overflow: hidden;",
        hx_post=f"/{todo_app.name}/{todo.id}",
        hx_target=f"#{tid}",
        hx_swap="outerHTML",
    )

    return Li(
        delete,
        checkbox,
        title_link,
        update_form,
        id=tid,
        cls='done' if todo.done else '',
        style="list-style-type: none;",
        data_id=todo.id,
        data_priority=todo.priority
    )


# ----------------------------------------------------------------------------------------------------
# __        __   _    ____             _        _
# \ \figlet/ /__| |__/ ___|  ___   ___| | _____| |_ ___
#  \ \ /\ / / _ \ '_ \___ \ / _ \ / __| |/ / _ \ __/ __|
#   \ V  V /  __/ |_) |__) | (_) | (__|   <  __/ |_\__ \
#    \_/\_/ \___|_.__/____/ \___/ \___|_|\_\___|\__|___/

# *******************************
# Streaming WebSockets because http isn't just for pageloads anymore
# *******************************

# Dictionary to keep track of connected WebSocket users
users = {}


async def on_conn(ws, send):
    """
    Handle new WebSocket connections.

    Args:
        ws: The WebSocket connection.
        send: The send function to communicate with the client.
    """
    users[str(id(ws))] = send
    logger.info(f"WebSocket connection established with ID: {id(ws)}")

    # Retrieve the last chosen explore option from the database
    menux = db.get("last_app_choice", "App")

    # Create a personalized welcome message for the user
    welcome_prompt = (
        f"Say 'Welcome to {pluralize(menux, singular=True)}' "
        "and add a brief, friendly greeting related to this area. Keep it under 25 words."
    )

    # Queue the welcome message to be sent to the user
    await chatq(welcome_prompt)


def on_disconn(ws):
    """
    Handle WebSocket disconnections.

    Args:
        ws: The WebSocket connection.
    """
    users.pop(str(id(ws)), None)
    logger.info(f"WebSocket connection closed with ID: {id(ws)}")


async def chatq(message: str):
    """
    Queue a message for the chat stream.

    Args:
        message (str): The message to queue for streaming.
    """
    # Create an asynchronous task to stream the chat response
    asyncio.create_task(stream_chat(message))
    logger.debug(f"Message queued for chat: {message}")


async def stream_chat(prompt: str, quick: bool = False):
    """
    Generate and stream an AI response to all connected users.

    Args:
        prompt (str): The prompt to send to the AI model.
        quick (bool): If True, send the entire response at once.

    Returns:
        None
    """
    logger.debug(f"Streaming chat response for prompt: {prompt}")

    # Generate the AI response using the selected model
    response = await run_in_threadpool(
        chat_with_ollama,
        model,
        [{"role": "user", "content": prompt}],
    )

    if quick:
        # Send the entire response at once for quick delivery
        for u in users.values():
            await u(
                Div(
                    response,
                    id='msg-list',
                    cls='fade-in',
                    style=MATRIX_STYLE,
                )
            )
    else:
        # Stream the response word by word to simulate typing
        words = response.split()
        for i in range(len(words)):
            partial_response = " ".join(words[: i + 1])
            for u in users.values():
                await u(
                    Div(
                        partial_response,
                        id='msg-list',
                        cls='fade-in',
                        style=MATRIX_STYLE,
                        _=f"this.scrollIntoView({{behavior: 'smooth'}});",
                    )
                )
            await asyncio.sleep(TYPING_DELAY)
    logger.debug("Completed streaming chat response.")


@app.ws('/ws', conn=on_conn, disconn=on_disconn)
async def ws(msg: str):
    """Handle incoming WebSocket messages."""
    logger.debug(f"WebSocket message received: {msg}")
    if msg:
        # Disable the input group to prevent further input during response
        disable_input_group = mk_chat_input_group(disabled=True, value=msg, autofocus=False)
        disable_input_group.attrs['hx_swap_oob'] = "true"
        for u in users.values():
            await u(disable_input_group)
        logger.debug("Input group disabled for typing effect.")

        # Append the user's message to the conversation history
        global conversation
        conversation.append({"role": "user", "content": msg})

        # Generate the assistant's response
        response = await run_in_threadpool(chat_with_ollama, model, conversation)
        conversation.append({"role": "assistant", "content": response})
        logger.info(f"Assistant response generated.")

        # Simulate typing effect by streaming the response word by word
        words = response.split()
        for i in range(len(words)):
            partial_response = " ".join(words[: i + 1])
            for u in users.values():
                await u(
                    Div(
                        partial_response,
                        id='msg-list',
                        cls='fade-in',
                        style=MATRIX_STYLE,
                        _=f"this.scrollIntoView({{behavior: 'smooth'}});",
                    )
                )
            await asyncio.sleep(TYPING_DELAY)

        # Re-enable the input group after the response is fully displayed
        enable_input_group = mk_chat_input_group(disabled=False, value='', autofocus=True)
        enable_input_group.attrs['hx_swap_oob'] = "true"
        for u in users.values():
            await u(enable_input_group)
        logger.debug("Input group re-enabled after typing effect.")

# *******************************
# Search Endpoint
# *******************************


@rt('/search', methods=['POST'])
async def search(nav_input: str = ''):
    """
    Handle search queries by informing the user that the feature is not implemented.

    Args:
        nav_input (str): The search term entered by the user.

    Returns:
        A response indicating that the search feature is still in beta.
    """
    logger.debug(f"Search requested with input: '{nav_input}'")
    search_term = nav_input

    # Inform the user that the search feature is not yet available
    await chatq(f"Searching for '{search_term}'? Sorry, that feature is still in beta. Keep the reply under 20 words.")

# *******************************
# Poke Endpoint
# *******************************


@rt('/poke', methods=['POST'])
async def poke_chatbot():
    """
    Handle the poke interaction with the chatbot.

    Returns:
        A confirmation message indicating the poke was received.
    """
    logger.debug("Chatbot poke received.")
    poke_message = (
        f"You poked the {APP_NAME} Chatbot. "
        "Respond with a brief, funny comment about being poked."
    )

    # Queue the poke message for streaming to the chat interface
    await chatq(poke_message)

    # Respond with a confirmation message
    return "Poke received. Let's see what the chatbot says..."

# ----------------------------------------------------------------------------------------------------
#  _   _ _   _ _ _ _   _
# | | | | |_(_) (_) |_(_) ___  ___
# | | | | __| | | | __| |/ _ \/ __| figlet
# | |_| | |_| | | | |_| |  __/\__ \
#  \___/ \__|_|_|_|\__|_|\___||___/
#
# *******************************
# Utilities to push those helper functions to the bottom
# *******************************


def print_app_name_figlet():
    """Print the application name in ASCII art using Figlet."""
    f = Figlet(font='slant')
    figlet_text = f.renderText(APP_NAME)
    print(figlet_text)


def format_endpoint_name(endpoint: str) -> str:
    """Capitalize and replace underscores with spaces in endpoint names."""
    return ' '.join(word.capitalize() for word in endpoint.split('_'))


def get_profile_name():
    """
    Retrieve the name of the current profile.

    This function attempts to get the name of the profile associated with the last used profile ID.
    If no last profile ID is found, it tries to use the first available profile.
    If no profiles exist, it returns "Unknown Profile".

    Returns:
        str: The name of the current profile, or "Unknown Profile" if no valid profile is found.

    Logs:
        - INFO: When using a default profile ID due to missing last_profile_id.
        - WARNING: When no profiles are found in the database.
        - DEBUG: Profile retrieval process and results.
    """
    # Get the last profile id from the database
    profile_id = db.get("last_profile_id")
    if profile_id is None:
        logger.info("No last_profile_id found. Attempting to use the first available profile.")

    logger.debug(f"Retrieving profile name for ID: {profile_id}")
    try:
        profile = profiles.get(profile_id)
        if profile:
            logger.debug(f"Found profile: {profile.name}")
            return profile.name
    except NotFoundError:
        logger.warning(f"No profile found for ID: {profile_id}. Attempting to use the first available profile.")
        # Attempt to use the first available profile
        all_profiles = profiles()
        if all_profiles:
            first_profile = all_profiles[0]
            db["last_profile_id"] = first_profile.id  # Update the last_profile_id to the first profile
            logger.info(f"Using first available profile ID: {first_profile.id}")
            return first_profile.name
        else:
            logger.warning("No profiles found in the database.")
            return "Unknown Profile"


# *******************************
# Utility Function for Pluralization
# *******************************

def pluralize(word, count=2, singular=False):
    """
    Return the plural or singular form of a word based on the count.
    Replace underscores with spaces and proper case the words.

    Args:
        word (str): The word to pluralize or singularize.
        count (int): The count to determine plurality. Default is 2 (plural).
        singular (bool): If True, always return the singular form. Default is False.

    Returns:
        str: The word in its appropriate form (singular or plural), with spaces and proper casing.
    """
    def proper_case(s):
        return ' '.join(w.capitalize() for w in s.split())

    # Replace underscores with spaces and proper case
    word = proper_case(word.replace('_', ' '))

    if singular or count == 1:
        return word

    # Irregular plurals
    irregulars = {
        'Child': 'Children',
        'Goose': 'Geese',
        'Man': 'Men',
        'Woman': 'Women',
        'Tooth': 'Teeth',
        'Foot': 'Feet',
        'Mouse': 'Mice',
        'Person': 'People'
    }

    # Check for irregular plurals
    if word in irregulars:
        return irregulars[word]

    # Words ending in 'y'
    if word.endswith('y'):
        if word[-2].lower() in 'aeiou':
            return word + 's'
        else:
            return word[:-1] + 'ies'

    # Words ending in 'o'
    if word.endswith('o'):
        if word[-2].lower() in 'aeiou':
            return word + 's'
        else:
            return word + 'es'

    # Words ending in 'is'
    if word.endswith('is'):
        return word[:-2] + 'es'

    # Words ending in 'us'
    if word.endswith('us'):
        return word[:-2] + 'i'

    # Words ending in 'on'
    if word.endswith('on'):
        return word[:-2] + 'a'

    # Words ending in 'f' or 'fe'
    if word.endswith('f'):
        return word[:-1] + 'ves'
    if word.endswith('fe'):
        return word[:-2] + 'ves'

    # Words ending in 's', 'ss', 'sh', 'ch', 'x', 'z'
    if word.endswith(('s', 'ss', 'sh', 'ch', 'x', 'z')):
        return word + 'es'

    # Default: just add 's'
    return word + 's'

# ----------------------------------------------------------------------------------------------------
#   _____ figlet                   ____            _
#  |  ___|   _ _ __  _ __  _   _  | __ ) _   _ ___(_)_ __   ___  ___ ___
#  | |_ | | | | '_ \| '_ \| | | | |  _ \| | | / __| | '_ \ / _ \/ __/ __|
#  |  _|| |_| | | | | | | | |_| | | |_) | |_| \__ \ | | | |  __/\__ \__ \
#  |_|   \__,_|_| |_|_| |_|\__, | |____/ \__,_|___/_|_| |_|\___||___/___/
#                          |___/
# *******************************
# Funny Business is stupid web tricks like the 404 handler
# *******************************


def custom_404_handler(request, exc):
    """
    Custom 404 page handler.

    Args:
        request: The request that caused the 404 error.
        exc: The exception that was raised.

    Returns:
        HTML: An HTML response for the 404 error.
    """
    return Html(
        Head(
            Title("404 - Page Not Found"),
            Style("""
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                h1 { color: #e74c3c; }
                a { color: #3498db; text-decoration: none; }
            """)
        ),
        Body(
            H1("404 - Page Not Found"),
            P(f"Sorry, the page '{request.url.path}' you're looking for doesn't exist."),
            A("Go back to home", href="/")
        )
    )


class DOMSkeletonMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Log the incoming HTTP request
        endpoint = request.url.path
        method = request.method
        f = Figlet(font='slant')
        figlet_text = f.renderText(f"{endpoint} {method}")
        print(figlet_text)
        logger.info(f"HTTP Request: {method} {endpoint}")

        # Call the next middleware or request handler
        response = await call_next(request)

        # Print a rich table of the db key/value pairs
        table = Table(title="Database Contents")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="magenta")
        for key, value in db.items():
            table.add_row(key, str(value))
        console = Console()
        table.columns[1].style = "white"
        console.print(table)

        return response


def print_routes():
    """
    Print a formatted table of all routes in the application.

    This function creates a rich console table displaying information about each route
    in the application. The table includes columns for the route type, methods, path,
    and a duplicate indicator.

    The function handles different types of routes:
    - Standard routes (Route)
    - WebSocket routes (WebSocketRoute)
    - Mounted applications (Mount)
    - Any other unrecognized route types

    The table is color-coded for better readability:
    - Type: Cyan
    - Methods: Yellow
    - Path: White (Red if duplicate)
    - Duplicate: Red if duplicate, otherwise green

    Note: This function assumes the existence of a global 'app' object with a 'routes' attribute.

    Returns:
        None. The function prints the table to the console.
    """
    console = Console()
    table = Table(title="Application Routes")

    table.add_column("Type", style="cyan", no_wrap=True)
    table.add_column("Methods", style="yellow")
    table.add_column("Path", style="white")
    table.add_column("Duplicate", style="green")

    # Collect all routes in a list for sorting
    route_entries = []

    # Set to track (path, method) pairs
    seen_routes = set()

    for route in app.routes:
        if isinstance(route, Route):
            methods = ", ".join(route.methods)
            route_key = (route.path, methods)

            # Check for duplicates
            if route_key in seen_routes:
                path_style = "red"
                duplicate_status = Text("Yes", style="red")
            else:
                path_style = "white"
                duplicate_status = Text("No", style="green")
                seen_routes.add(route_key)

            route_entries.append(("Route", methods, route.path, path_style, duplicate_status))
        elif isinstance(route, WebSocketRoute):
            route_key = (route.path, "WebSocket")

            # Check for duplicates
            if route_key in seen_routes:
                path_style = "red"
                duplicate_status = Text("Yes", style="red")
            else:
                path_style = "white"
                duplicate_status = Text("No", style="green")
                seen_routes.add(route_key)

            route_entries.append(("WebSocket", "WebSocket", route.path, path_style, duplicate_status))
        elif isinstance(route, Mount):
            route_entries.append(("Mount", "Mounted App", route.path, "white", Text("N/A", style="green")))
        else:
            route_entries.append((str(type(route)), "Unknown", getattr(route, 'path', 'N/A'), "white", Text("N/A", style="green")))

    # Sort the routes by path
    route_entries.sort(key=lambda x: x[2])

    # Add sorted routes to the table
    for entry in route_entries:
        table.add_row(
            entry[0],
            entry[1],
            Text(entry[2], style=entry[3]),
            entry[4]
        )

    console.print(table)


# ----------------------------------------------------------------------------------------------------
#  ____                       __     __
# / ___|  ___ _ ____   _____ / /    \ \
# \___ \ / _ \ '__\ \ / / _ \ |      | |
#  ___) |  __/ |   \ V /  __/ |figlet| |
# |____/ \___|_|    \_/ \___| |      | |
#                            \_\    /_/
# *******************************
# And now the moment you've all been waiting for: Activate the Application
# *******************************


# Add the custom 404 handler after the app is created
app.add_exception_handler(404, custom_404_handler)
logger.info("Application setup completed with custom 404 handler.")

app.add_middleware(DOMSkeletonMiddleware)
logger.info("Application setup completed with DOMSkeletonMiddleware.")

# Retrieve and set the best available LLaMA model
model = get_best_model()
logger.info(f"Using model: {model}")

# Print the application name in ASCII art upon startup
print_app_name_figlet()

# After setting up all routes
print_routes()

# Start the application server
serve()

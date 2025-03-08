import asyncio
import json
import os
import re
import sys
from typing import List, Optional

import requests
from fasthtml.common import *
from loguru import logger
from pyfiglet import Figlet
from starlette.concurrency import run_in_threadpool

# *******************************
# Styles and Configuration
# *******************************
# App gets its name from the directory it is in Capitalized
APP_NAME = os.path.basename(os.path.dirname(os.path.abspath(__file__))).capitalize()
DEFAULT_LLM_MODEL = "llama3.2"  # Set the default LLaMA model
MAX_LLM_RESPONSE_WORDS = 30     # Maximum number of words in LLM response
TYPING_DELAY = 0.05             # Delay for simulating typing effect

# Configurable constants for table names and endpoints
TODO = "task"
PROFILE = "profile"
ADDRESS_NAME = "www.site.com"
CODE_NAME = "CCode (us, uk, de, etc)"

# Grid layout constants
GRID_LAYOUT = "70% 30%"

# Define the width for the menus
bw = "150px"
NAV_FILLER_WIDTH = "20%"        # Width for the filler in the navigation
PROFILE_MENU_WIDTH = f"200px"   # Width for the profile menu
ACTION_MENU_WIDTH = f"{bw}"     # Width for the action menu
EXPLORE_MENU_WIDTH = f"{bw}"    # Width for the app menu
SEARCH_WIDTH = f"{bw}"          # Width for the search input

# Initialize IDs for menus
profile_id = "profile-id"
action_id = "action-id"
explore_id = "app-id"

# Initialize conversation with a system message
conversation = [
    {
        "role": "system",
        "content": (
            f"You are a {APP_NAME} FOSS AI SEO software with attitude. "
            f"Be sassy but helpful in under {MAX_LLM_RESPONSE_WORDS} words, "
            "and without leading and trailing quotes."
        ),
    },
]

# Styles for menu items
COMMON_MENU_STYLE = (
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
MATRIX_STYLE = (
    "color: #00ff00; "
    "font-family: 'Courier New', monospace; "
    "text-shadow: 0 0 5px #00ff00; "
)

# Menu visibility configuration
SHOW_PROFILE_MENU = True
SHOW_APP_MENU = True
SHOW_ACTION_MENU = False
SHOW_SEARCH = True

NOWRAP_STYLE = "white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"

# Figlet function
def fig(text):
    """Print text using figlet."""
    if text is None:
        return  # Don't print anything if text is None
    text = str(text)  # Convert to string to handle non-string inputs
    figlet = Figlet(font='slant')
    print(figlet.renderText(text))


def generate_menu_style(width: str) -> str:
    """
    Generate a common style for menu elements with a specified width.

    Args:
        width (str): The width to apply to the menu element.

    Returns:
        str: A string containing the combined CSS styles.
    """
    return COMMON_MENU_STYLE + f"width: {width}; "


# *******************************
# Set up logging with loguru
# *******************************
# Ensure the logs directory exists
logs_dir = 'logs'
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Set up log file path
log_file_path = os.path.join(logs_dir, f'{APP_NAME}.log')

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
    sys.stderr,
    level="DEBUG",
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{message}</cyan>",
)

# *******************************
# Utility Functions
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


def limit_llm_response(response: str) -> str:
    """Truncate the response to a maximum number of words."""
    return ' '.join(response.split()[:MAX_LLM_RESPONSE_WORDS])


def get_best_model() -> str:
    """
    Retrieve the best available LLaMA model or default to 'llama3.2'.

    Returns:
        str: The name of the best available model.
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


# *******************************
# Todo Render Function (Must come before Application Setup)
# *******************************


def render(todo):
    """
    Render a todo item as an HTML list item with an update form.

    Args:
        todo: The todo item to render.

    Returns:
        Li: An HTML list item representing the todo.
    """
    tid = f'todo-{todo.id}'  # Unique ID for the todo item
    checkbox = Input(
        type="checkbox",
        name="english" if todo.done else None,
        checked=todo.done,
        hx_post=f"/{TODO}/toggle/{todo.id}",
        hx_swap="outerHTML",
        hx_target=f"#{tid}",
    )

    # Create the delete button (trash can)
    delete = A(
        '🗑',
        hx_delete=f'/{TODO}/delete/{todo.id}',
        hx_swap='outerHTML',
        hx_target=f"#{tid}",
        style="cursor: pointer; display: inline;",
        cls="delete-icon"
    )

    # Create the title link with no text decoration
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

    # Create the update form
    update_form = Form(
        Div(
            Input(
                type="text",
                id=f"todo_title_{todo.id}",
                value=todo.title,
                name="todo_title",
                style="flex: 1; padding-right: 10px; margin-bottom: 0px;"
            ),
            style="display: flex; align-items: center;"
        ),
        Input(
            type="hidden",
            name="todo_id",
            value=todo.id
        ),
        style="visibility: hidden; height: 0; overflow: hidden;",
        hx_post=f"/{TODO}/update/{todo.id}",
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

# *******************************
# Application Setup
# *******************************


def SortableJSWithUpdate(
    sel='.sortable',
    ghost_class='blue-background-class',
    update_url=f'/{TODO}_sort'
):
    """
    Create a SortableJS script with update functionality.

    Args:
        sel (str): The CSS selector for the sortable element.
        ghost_class (str): The class name for the ghost element during sorting.
        update_url (str): The URL to send the updated order to.

    Returns:
        Script: An HTML script element containing the SortableJS setup.
    """
    src = f"""
import {{Sortable}} from 'https://cdn.jsdelivr.net/npm/sortablejs/+esm';

document.addEventListener('DOMContentLoaded', (event) => {{
    console.log('SortableJSWithUpdate script is running!');
    const el = document.querySelector('{sel}');
    if (el) {{
        new Sortable(el, {{
            animation: 150,
            ghost_class: '{ghost_class}',
            onEnd: function (evt) {{
                console.log('Drag ended!', evt);
                let items = Array.from(el.children).map((item, index) => ({{
                    id: item.dataset.id,
                    priority: index
                }}));
                console.log('New order:', items);

                let updateUrl = el.id === 'profile-list' ? '/{PROFILE}_sort' : '{update_url}';
                htmx.ajax('POST', updateUrl, {{
                    target: el,  // Use the element directly instead of a selector
                    swap: 'none',
                    values: {{
                        items: JSON.stringify(items)
                    }}
                }});
            }}
        }});
    }} else {{
        console.error('Sortable element not found:', '{sel}');
    }}
}});
"""
    return Script(src, type='module')


# Unpack the returned tuple from fast_app
app, rt, (store, Store), (todos, Todo), (profiles, Profile) = fast_app(
    "data/data.db",
    ws_hdr=True,
    live=True,
    render=render,
    hdrs=(
        SortableJSWithUpdate('.sortable', update_url=f'/{TODO}_sort'),
        Script(type='module')
    ),
    STORE={
        "key": str,
        "value": str,
        "pk": "key"
    },
    TODO={
        "id": int,
        "title": str,
        "done": bool,
        "priority": int,
        "profile_id": int,
        "pk": "id"
    },
    PROFILE={
        "id": int,
        "name": str,
        "address": str,
        "code": str,
        "active": bool,
        "priority": int,  # Make sure this line is present
        "pk": "id"
    },
)
logger.info("Application setup completed.")

# *******************************
# DictLikeDB Persistence Convenience Wrapper
# *******************************


class DictLikeDB:
    """A wrapper class for a dictionary-like database to simplify access."""

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
# Site Navigation
# *******************************


def create_menu_item(title, link, summary_id, is_traditional_link=False, additional_style=""):
    """
    Create a menu item for the navigation.

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


def create_nav_menu():
    """
    Create the navigation menu with app, profile, and action dropdowns.

    Returns:
        Div: An HTML div containing the navigation menu.
    """
    logger.debug("Creating navigation menu.")
    # Fetch the last selected items from the db
    selected_profile_id = db.get("last_profile_id")
    selected_profile_name = db.get("last_profile_name", PROFILE)
    selected_explore = db.get("last_explore_choice", "App")
    selected_action = db.get("last_action_choice", "Actions")

    # Use generate_menu_style for the common style
    profile_menu_style = generate_menu_style(PROFILE_MENU_WIDTH)
    action_menu_style = generate_menu_style(ACTION_MENU_WIDTH)

    # Filler Item: Non-interactive, occupies significant space
    filler_item = Li(
        Span(" "),
        style=(
            "flex-grow: 1; "
            f"min-width: {NAV_FILLER_WIDTH}; "
            "list-style-type: none; "
            "display: flex; "
            "justify-content: center; "
        ),
    )

    nav_items = [filler_item]

    if SHOW_PROFILE_MENU:
        logger.debug(f"Adding {PROFILE.lower()} menu to navigation.")
        profile_items = []

        # Add "Manage Users" option at the top (unchanged)
        profile_items.append(
            create_menu_item(
                f"Manage {PROFILE.capitalize()}",
                f"/{PROFILE}",
                profile_id,
                is_traditional_link=True,
                additional_style="font-weight: bold; border-bottom: 1px solid var(--pico-muted-border-color);"
            )
        )

        # Fetch active profiles using MiniDataAPI
        active_profiles = profiles("active=?", (True,), order_by='priority')

        for profile in active_profiles:
            is_selected = str(profile.id) == str(selected_profile_id)
            item_style = (
                "background-color: var(--pico-primary-background); " if is_selected else ""
            )
            profile_items.append(
                Li(
                    Label(
                        Input(
                            type="radio",
                            name="profile",
                            value=str(profile.id),
                            checked=is_selected,
                            hx_get=f"/{PROFILE}/{profile.id}",
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
                selected_profile_name.capitalize() if selected_profile_name == PROFILE else selected_profile_name,
                style=generate_menu_style(PROFILE_MENU_WIDTH) + NOWRAP_STYLE,
                id=profile_id,
            ),
            Ul(
                *profile_items,
                style="padding-left: 0;",
            ),
            cls="dropdown",
        )
        nav_items.append(profile_menu)

    if SHOW_APP_MENU:
        logger.debug("Adding app menu to navigation.")
        # Define the apps menu
        explore_menu = Details(
            Summary(
                pluralize(selected_explore, singular=True),
                style=generate_menu_style(EXPLORE_MENU_WIDTH),
                id=explore_id,
            ),
            Ul(
                create_menu_item(
                    pluralize(TODO),
                    f"/{TODO}",
                    explore_id,
                    is_traditional_link=True,
                    additional_style="background-color: var(--pico-primary-background); " if selected_explore == pluralize(TODO) else ""
                ),
                create_menu_item(
                    "App 1",
                    "/app_1",
                    explore_id,
                    is_traditional_link=True,
                    additional_style="background-color: var(--pico-primary-background); " if selected_explore == "App 1" else ""
                ),
                create_menu_item(
                    "App 2",
                    "/app_2",
                    explore_id,
                    is_traditional_link=True,
                    additional_style="background-color: var(--pico-primary-background); " if selected_explore == "App 2" else ""
                ),
                dir="rtl",
            ),
            cls="dropdown",
        )
        nav_items.append(explore_menu)

    if SHOW_SEARCH:
        logger.debug("Adding search input to navigation.")
        # Define the search button style
        search_button_style = (
            generate_menu_style(SEARCH_WIDTH) +
            "background: none; "
            "color: var(--pico-muted-color); "
            "position: absolute; "
            "right: 1px; "
            "top: 50%; "
            "transform: translateY(-50%); "
            "width: 16px; "
        )

        # Create the search input group wrapped in a form
        search_group = Form(
            Group(
                Input(
                    placeholder="Search",
                    name="nav_input",
                    id="nav-input",
                    hx_post="/search",
                    hx_trigger="keyup[keyCode==13]",
                    hx_target="#msg-list",
                    hx_swap="innerHTML",
                    style=(
                        f"{action_menu_style} "
                        f"width: {SEARCH_WIDTH}; "
                        "padding-right: 25px; "
                        "border: 1px solid var(--pico-muted-border-color); "
                    ),
                ),
                Button(
                    "×",
                    type="button",
                    onclick="document.getElementById('nav-input').value = ''; this.blur();",
                    style=search_button_style + "margin-right: 0px;",
                ),
                style=(
                    "align-items: center; "
                    "display: flex; "
                    "position: relative; "
                ),
            ),
            hx_post="/search",
            hx_target="#msg-list",
            hx_swap="innerHTML",
        )

        nav_items.append(search_group)

    # Create the navigation container
    nav = Div(
        *nav_items,
        style=(
            "align-items: center; "
            "display: flex; "
            "gap: 8px; "
            "width: 100%; "
            "justify-content: flex-end; "
        ),
    )

    logger.debug("Navigation menu created.")
    return nav


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

# *******************************
# Todo Common Support Functions
# *******************************


def todo_mk_input():
    """
    Create an input field for adding a new todo item.

    Returns:
        Input: An HTML input element for the todo title.
    """
    return Input(
        placeholder='Add a new item',
        id='title',
        hx_swap_oob='true',
        autofocus=True,
        name='title',
    )

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
            "name": f"Default {PROFILE.capitalize()}",  # Updated to use PROFILE
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
            "title": f"Sample {TODO}",
            "done": False,
            "priority": 1,
            "profile_id": default_profile.id,
        })
        logger.info(f"Inserted sample {TODO} item.")


# Call this function after the fast_app initialization
populate_initial_data()

# *******************************
# Create Main Content
# *******************************


def create_main_content(show_content=False):
    """
    Create the main content for all routes.

    Args:
        show_content (bool): Whether to show specific content based on the route.

    Returns:
        Container: An HTML container with the main content.
    """

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

    current_profile_id = db.get("last_profile_id")
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

    selected_explore = db.get("last_explore_choice", "App")
    fig(f" selected_explore: {selected_explore}")

    # Check if selected_explore matches either singular or plural form of TODO
    is_todo_view = (selected_explore == TODO)

    # Fetch the filtered todo items and sort them by priority
    todo_items = sorted(todos(), key=lambda x: x.priority)
    logger.info(f"Fetched {len(todo_items)} todo items for profile ID {current_profile_id}.")

    return Container(
        nav_group,
        Grid(
            Div(
                Card(
                    H2(f"{pluralize(selected_explore, singular=True)}"),
                    Ul(*[render(todo) for todo in todo_items],
                       id='todo-list',
                       cls='sortable',
                       style="padding-left: 0;"),
                    header=Form(
                        Group(
                            todo_mk_input(),
                            Button("Add", type="submit"),
                        ),
                        hx_post=f"/{TODO}",
                        hx_swap="beforeend",
                        hx_target="#todo-list",
                    ),
                ) if is_todo_view else Card(
                    H2(f"{pluralize(selected_explore, singular=True)}"),
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
    )

# *******************************
# Site Navigation Main Endpoints
# *******************************

@rt('/')
@rt(f'/{TODO}')
@rt(f'/{PROFILE}')
@rt('/app_1')
@rt('/app_2')
def get(request):
    """
    Handle main page and specific page GET requests.

    Args:
        request: The incoming HTTP request.

    Returns:
        Titled: An HTML response with the appropriate title and content.
    """
    path = request.url.path.strip('/')
    logger.debug(f"Received request for path: {path}")

    show_content = path in [TODO, PROFILE, 'link_graph', 'gap_analysis']

    if path == TODO:
        selected_explore = TODO
    elif path == PROFILE:
        selected_explore = PROFILE
    elif show_content:
        selected_explore = path
    else:
        selected_explore = "home"

    logger.info(f"Selected explore item: {selected_explore}")
    db["last_explore_choice"] = selected_explore
    db["last_visited_url"] = request.url.path

    # Apply the profile filter if necessary
    current_profile_id = db.get("last_profile_id")
    if current_profile_id:
        logger.debug(f"Current profile ID: {current_profile_id}")
        todos.xtra(profile_id=current_profile_id)
    else:
        logger.warning("No current profile ID found. Using default filtering.")
        todos.xtra(profile_id=None)

    if selected_explore == PROFILE:
        response = get_profiles_content()
    else:
        response = create_main_content(show_content)

    logger.debug("Returning response for main GET request.")
    last_profile_name = db.get("last_profile_name", "Default Profile")
    return Titled(
        f"{APP_NAME} / {pluralize(last_profile_name, singular=True)} / {pluralize(selected_explore, singular=True)}",
        response,
        hx_ext='ws',
        ws_connect='/ws',
        data_theme="dark",
    )


def get_profiles_content():
    """
    Retrieve and display the list of profiles.

    Returns:
        Container: An HTML container with the profiles and chat interface.
    """
    logger.debug(f"Retrieving {PROFILE.lower()} for display.")
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
                    H2(PROFILE.capitalize()),
                    Ul(*[render_profile(profile) for profile in ordered_profiles],
                       id='profile-list',
                       cls='sortable',
                       style="padding-left: 0;"),
                    footer=Form(
                        Group(
                            Input(placeholder=f"{PROFILE.capitalize()} Name", name="profile_name"),
                            Input(placeholder=ADDRESS_NAME, name="profile_address"),
                            Input(placeholder=CODE_NAME, name="profile_code"),
                            Button("Add", type="submit"),
                        ),
                        hx_post=f"/{PROFILE}",
                        hx_target="#profile-list",
                        hx_swap="beforeend",
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
    )


@rt(f'/{PROFILE}/{{profile_id}}')
def profile_menu_handler(request, profile_id: int):
    """
    Handle profile menu selection and record the choice.

    Args:
        request: The incoming HTTP request.
        profile_id (int): The ID of the selected profile.

    Returns:
        Redirect: A redirect response to the last visited URL.
    """
    logger.debug(f"Profile menu selected with profile_id: {profile_id}")
    # Fetch the selected profile from the database using the profile ID
    selected_profile = profiles.get(profile_id)

    if not selected_profile:
        logger.error(f"Profile ID {profile_id} not found. Redirecting to /{PROFILE}.")
        return Redirect(f'/{PROFILE}')

    # Store the selected profile ID and name in the database
    db["last_profile_id"] = selected_profile.id
    db["last_profile_name"] = selected_profile.name
    logger.info(f"Profile selected: {selected_profile.name} (ID: {selected_profile.id})")

    # Retrieve the last visited URL from the database
    last_visited_url = db.get("last_visited_url", "/")

    # Return a redirect response to the last visited URL
    return Redirect(last_visited_url)

# *******************************
# Todo App Endpoints
# *******************************


@rt(f'/{TODO}', methods=['POST'])
async def post_todo(title: str):
    """
    Create a new todo item.

    Args:
        title (str): The title of the new todo item.

    Returns:
        Tuple: The rendered todo item and a new input field.
    """
    logger.debug(f"Received new todo title: '{title}'")
    if not title.strip():
        # Empty todo case
        await chatq(
            "User tried to add an empty todo. Respond with a brief, sassy comment about their attempt."
        )
        logger.warning("User attempted to add an empty todo.")
        return ''

    # Non-empty todo case
    current_profile_id = db.get("last_profile_id")
    if not current_profile_id:
        # Use default profile ID
        default_profile = profiles()[0]
        current_profile_id = default_profile.id
        logger.warning(f"No profile ID found. Using default profile ID: {current_profile_id}")

    # Create a new todo item with the profile_id included
    todo = {
        "title": title,
        "done": False,
        "priority": 0,
        "profile_id": current_profile_id,
    }
    inserted_todo = todos.insert(todo)
    logger.info(f"Inserted new todo: {inserted_todo}")

    prompt = (
        f"New {TODO}: '{title}'. "
        "Brief, sassy comment or advice."
    )
    await chatq(prompt)

    return render(inserted_todo), todo_mk_input()


@rt(f'/{TODO}/toggle/{{tid}}', methods=['POST'])
async def toggle_todo(tid: int):
    """
    Update the status of a todo item.

    Args:
        tid (int): The ID of the todo item to toggle.

    Returns:
        str: The rendered updated todo item.
    """
    logger.debug(f"Toggling todo status for ID: {tid}")
    todo = todos[tid]
    old_status = "Done" if todo.done else "Not Done"
    todo.done = not todo.done
    updated_todo = todos.update(todo)
    logger.info(f"Toggled todo '{todo.title}' to {'Done' if todo.done else 'Not Done'}")

    prompt = (
        f"Todo '{todo.title}' toggled from {old_status} to {'Done' if todo.done else 'Not Done'}. "
        f"Brief, sassy comment mentioning '{todo.title}'."
    )
    await chatq(prompt)

    return render(updated_todo)


@rt(f'/{TODO}/update/{{todo_id}}', methods=['POST'])
async def update_todo(todo_id: int, todo_title: str):
    """
    Update the title of a todo item.

    Args:
        todo_id (int): The ID of the todo item to update.
        todo_title (str): The new title for the todo item.

    Returns:
        Union[str, Tuple[str, int]]: The rendered updated todo item or an error message with status code.
    """
    logger.debug(f"Updating todo ID {todo_id} with new title: '{todo_title}'")
    # Fetch the existing Todo item
    todo = todos[todo_id]

    if not todo:
        logger.error(f"Todo ID {todo_id} not found for update.")
        return "Todo not found", 404

    # Update the Todo item's title
    todo.title = todo_title

    # Use the MiniDataAPI update method to save the changes
    try:
        updated_todo = todos.update(todo)
        logger.info(f"Updated todo ID {todo_id}: {updated_todo}")
    except NotFoundError:
        logger.error(f"Todo ID {todo_id} not found during update.")
        return "Todo not found for update", 404

    # Return the updated Todo item using the render function
    return render(updated_todo)


@rt(f'/{TODO}_sort', methods=['POST'])
async def update_todo_order(values: dict):
    """
    Update the order of todo items based on the received values.

    Args:
        values (dict): A dictionary containing the new order of todo items.

    Returns:
        str: An empty string indicating successful update, or an error message with status code.
    """
    logger.debug(f"Received values: {values}")
    try:
        items = json.loads(values.get('items', '[]'))
        logger.debug(f"Parsed items: {items}")
        for item in items:
            logger.debug(f"Updating item: {item}")
            todos.update(id=int(item['id']), priority=int(item['priority']))
        logger.info("Todo order updated successfully")

        # After successful update, queue a message for the chat
        prompt = "The todo list was reordered. Make a brief, witty remark about sorting or prioritizing tasks. Keep it under 20 words."
        await chatq(prompt)

        return ''
    except Exception as e:
        logger.error(f"Error updating todo order: {str(e)}")
        return str(e), 500  # Return the error message and a 500 status code


@rt(f'/{TODO}/delete/{{tid}}', methods=['DELETE'])
async def delete_todo(tid: int):
    """
    Delete a todo item.

    Args:
        tid (int): The ID of the todo item to delete.

    Returns:
        str: An empty string indicating successful deletion.
    """
    logger.debug(f"Deleting todo with ID: {tid}")
    todo = todos[tid]
    todos.delete(tid)
    prompt = (
        f"Todo '{todo.title}' deleted. "
        "Brief, sassy reaction."
    )
    await chatq(prompt)
    logger.info(f"Deleted todo: {todo.title} (ID: {tid})")
    return ''


# *******************************
# Profiles App Endpoints
# *******************************

def count_records_with_xtra(table_handle, xtra_field, xtra_value):
    """
    Returns the number of records in the specified table that match the given .xtra field constraint.

    Parameters:
        table_handle: A handle to the table object following the MiniDataAPI specification.
        xtra_field (str): The field name in the table to constrain by using the .xtra function.
        xtra_value: The value to constrain by for the specified xtra_field.

    Returns:
        int: The number of records in the specified table matching the .xtra constraint.
    """
    # Set the xtra constraint on the table
    table_handle.xtra(**{xtra_field: xtra_value})

    # Return the number of records in the table after applying the constraint
    count = len(table_handle())
    logger.debug(f"Counted {count} records in table for {xtra_field} = {xtra_value}")
    return count


def render_profile(profile):
    """
    Render a profile item as an HTML list item.

    Args:
        profile: The profile item to render.

    Returns:
        Li: An HTML list item representing the profile.
    """
    # Count the number of todo items for this profile
    todo_count = count_records_with_xtra(todos, 'profile_id', profile.id)

    # Set the visibility of the delete icon based on the todo count
    delete_icon_visibility = 'inline' if todo_count == 0 else 'none'

    # Create the delete button (trash can)
    delete_icon = A(
        '🗑',
        hx_delete=f"/{PROFILE}/delete/{profile.id}",
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
        hx_post=f"/{PROFILE}/toggle/{profile.id}",
        hx_target=f'#profile-{profile.id}',
        hx_swap="outerHTML",
        style="margin-right: 5px;"
    )

    # Create the update form
    update_form = Form(
        Group(
            Input(type="text", name="name", value=profile.name, placeholder="Name", id=f"name-{profile.id}"),
            Input(type="text", name="address", value=profile.address, placeholder=ADDRESS_NAME, id=f"address-{profile.id}"),
            Input(type="text", name="code", value=profile.code, placeholder=CODE_NAME, id=f"code-{profile.id}"),
            Button("Update", type="submit"),
        ),
        hx_post=f"/{PROFILE}/update/{profile.id}",
        hx_target=f'#profile-{profile.id}',
        hx_swap='outerHTML',
        style="display: none;",
        id=f'update-form-{profile.id}'
    )

    # Create the title link with an onclick event to toggle the update form
    title_link = A(
        f"{profile.name} ({todo_count} {pluralize(TODO, todo_count)})",
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
        style="list-style-type: none;",
        data_id=profile.id,  # Add this line
        data_priority=profile.priority  # Add this line
    )


@rt(f'/{PROFILE}', methods=['POST'])
async def add_profile(profile_name: str, profile_address: str, profile_code: str):
    """
    Create a new profile.

    Args:
        profile_name (str): The name of the new profile.
        profile_address (str): The address of the new profile.
        profile_code (str): The code number of the new profile.

    Returns:
        Union[str, Li]: The rendered profile item or an empty string if validation fails.
    """
    logger.debug(f"Attempting to add {PROFILE.capitalize()}: {profile_name}, {profile_address}, {profile_code}")
    if not profile_name.strip():
        logger.warning(f"User tried to add an empty {PROFILE.capitalize()} name.")
        await chatq(
            f"User tried to add an empty {PROFILE.calitalize()} name. Respond with a brief, sassy comment about their attempt."
        )
        return ''

    # Get the maximum priority and add 1, or use 0 if no profiles exist
    max_priority = max((p.priority or 0 for p in profiles()), default=-1) + 1

    new_profile = {
        "name": profile_name,
        "address": profile_address,
        "code": profile_code,
        "active": True,
        "priority": max_priority,
    }

    inserted_profile = profiles.insert(new_profile)
    logger.info(f"Profile added: {inserted_profile}")

    prompt = (
        f"New profile '{profile_name}' just joined the party! {ADDRESS_NAME}: {profile_address}, Code: {profile_code}. "
        "Give a cute, welcoming response mentioning the new profile's name and one other detail. Keep it under 30 words."
    )
    await chatq(prompt)

    return render_profile(inserted_profile)


@rt(f'/{PROFILE}/toggle/{{pid}}', methods=['POST'])
async def toggle_profile(pid: int):
    """
    Toggle the active status of a profile item.

    Args:
        pid (int): The ID of the profile to toggle.

    Returns:
        Li: The rendered updated profile item.
    """
    logger.debug(f"Toggling active status for profile ID: {pid}")
    profile = profiles[pid]
    old_status = "active" if profile.active else "inactive"
    profile.active = not profile.active
    new_status = "active" if profile.active else "inactive"
    updated_profile = profiles.update(profile)
    logger.info(f"Toggled active status for profile ID {pid} to {profile.active}")

    prompt = (
        f"Profile '{profile.name}' just flipped their status from {old_status} to {new_status}! "
        "Give a cute, playful response about this change, mentioning the profile's name and new status. Keep it under 30 words."
    )
    await chatq(prompt)

    return render_profile(updated_profile)


@rt(f'/{PROFILE}/update/{{profile_id}}', methods=['POST'])
async def update_profile(profile_id: int, name: str, address: str, code: str):
    """
    Update a profile item.

    Args:
        profile_id (int): The ID of the profile to update.
        name (str): The new name for the profile.
        address (str): The new address for the profile.
        code (str): The new code number for the profile.

    Returns:
        Union[str, Li]: The rendered updated profile item or an error message with status code.
    """
    logger.debug(f"Updating profile ID {profile_id} with new data.")
    # Fetch the existing profile item
    profile = profiles[profile_id]

    if not profile:
        logger.error(f"Profile ID {profile_id} not found for update.")
        return "Profile not found", 404

    # Store old values for comparison
    old_name = profile.name
    old_address = profile.address
    old_code = profile.code

    # Update the profile item's fields
    profile.name = name
    profile.address = address
    profile.code = code

    # Use the MiniDataAPI update method to save the changes
    try:
        updated_profile = profiles.update(profile)
        logger.info(f"Updated profile ID {profile_id}: {updated_profile}")

        # Determine what changed
        changes = []
        if old_name != name:
            changes.append(f"name from '{old_name}' to '{name}'")
        if old_address != address:
            changes.append(f"{ADDRESS_NAME} from '{old_address}' to '{address}'")
        if old_code != code:
            changes.append(f"code from '{old_code}' to '{code}'")

        if changes:
            change_str = ", ".join(changes)
            prompt = (
                f"Profile '{name}' just got a makeover! They updated their {change_str}. "
                "Give a cute, excited response about this update, mentioning the profile's name and one change. Keep it under 30 words."
            )
            await chatq(prompt)

    except NotFoundError:
        logger.error(f"Profile ID {profile_id} not found during update.")
        return "Profile not found for update", 404

    # Return the updated profile item using the render function
    return render_profile(updated_profile)


@rt(f'/{PROFILE}_sort', methods=['POST'])
async def sort_profiles(items: str = Form(...)):
    logger.debug("sort_profiles function called")
    try:
        logger.debug(f"Sorting profiles: {items}")
        items_list = json.loads(items)
        for item in items_list:
            profile = profiles[int(item['id'])]
            profile.priority = item['priority']
            profiles.update(profile)
        logger.info("Profiles sorted successfully")
        return "Profiles sorted successfully"
    except Exception as e:
        logger.error(f"Error sorting profiles: {str(e)}")
        return f"Error sorting profiles: {str(e)}", 500


@rt(f'/{PROFILE}/delete/{{profile_id}}', methods=['DELETE'])
async def delete_profile(profile_id: int):
    """
    Delete a profile item.

    Args:
        profile_id (int): The ID of the profile to delete.

    Returns:
        str: An empty string indicating successful deletion.
    """
    try:
        logger.debug(f"Attempting to delete profile ID: {profile_id}")
        profile = profiles[profile_id]
        profiles.delete(profile_id)
        logger.warning(f"Deleted profile ID: {profile_id}")
        return '', 200
    except Exception as e:
        logger.error(f"Error deleting profile: {str(e)}")
        return f"Error deleting profile: {str(e)}", 500


# *******************************
# Streaming WebSocket Functions
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
    selected_explore = db.get("last_explore_choice", "App")

    # Create a personalized welcome message for the user
    welcome_prompt = (
        f"Say 'Welcome to {pluralize(selected_explore, singular=True)}' "
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
        A response indicating that the search feature is under development.
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

# *******************************
# Activate the Application
# *******************************


def print_app_name_figlet():
    """Print the application name in ASCII art using Figlet."""
    # Output 100 empty debug lines
    for _ in range(25):
        logger.debug("")

    f = Figlet(font='slant')
    figlet_text = f.renderText(APP_NAME)
    print(figlet_text)


# Retrieve and set the best available LLaMA model
model = get_best_model()
logger.info(f"Using model: {model}")

# Print the application name in ASCII art upon startup
print_app_name_figlet()

# Start the application server
serve()

for route in app.routes:
    print(route)


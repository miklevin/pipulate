import asyncio
import json
import os
import re
import sys
from typing import List, Optional

import requests
from fasthtml.common import *
from loguru import logger
from starlette.concurrency import run_in_threadpool

# *******************************
# Styles and Configuration
# *******************************
# Application name and configuration settings
APP_NAME = os.path.basename(os.path.dirname(os.path.abspath(__file__))).capitalize()
MAX_LLM_RESPONSE_WORDS = 30     # Maximum number of words in LLM response
TYPING_DELAY = 0.05             # Delay for simulating typing effect
DEFAULT_LLM_MODEL = "llama3.2"  # Set the default LLaMA model

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

def generate_menu_style(width: str) -> str:
    """Generate a common style for menu elements with a specified width."""
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
# Ollama LLM Functions
# *******************************
def limit_llm_response(response: str) -> str:
    """Truncate the response to a maximum number of words."""
    return ' '.join(response.split()[:MAX_LLM_RESPONSE_WORDS])

def get_best_model() -> str:
    """Retrieve the best available LLaMA model or default to 'llama3.2'."""
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
    """Interact with the Ollama model to generate a response."""
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
    """Render a todo item as an HTML list item with an update form."""
    tid = f'todo-{todo.id}'  # Unique ID for the todo item
    checkbox = Input(
        type="checkbox",
        name="english" if todo.done else None,
        checked=todo.done,
        hx_post=f"/todo/toggle/{todo.id}",
        hx_swap="outerHTML",
        hx_target=f"#{tid}",
    )

    # Create the delete button (trash can)
    delete = A(
        '🗑',
        hx_delete=f'/todo/delete/{todo.id}',
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
        hx_post=f"/todo/update/{todo.id}",
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
        style="list-style-type: none;"
    )

# *******************************
# Application Setup
# *******************************

# Unpack the returned tuple from fast_app
app, rt, (store, Store), (todos, Todo), (profiles, Profile) = fast_app(
    "data/app.db",
    ws_hdr=True,
    live=True,
    render=render,
    store={
        "key": str,
        "value": str,
        "pk": "key"
    },
    todos={
        "id": int,
        "title": str,
        "done": bool,
        "priority": int,
        "profile_id": int,
        "pk": "id"
    },
    profiles={
        "id": int,
        "name": str,
        "email": str,
        "phone": str,
        "active": bool,
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
    """Create a menu item for the navigation."""
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
    """Create the navigation menu with app, profile, and action dropdowns."""
    logger.debug("Creating navigation menu.")
    # Fetch the last selected items from the db
    selected_profile_id = db.get("last_profile_id")
    selected_profile_name = db.get("last_profile_name", "Profiles")
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
        logger.debug("Adding profile menu to navigation.")
        # Fetch profiles from the database
        profile_items = []
        for profile in profiles():
            if profile.active:
                is_selected = str(profile.id) == str(selected_profile_id)
                item_style = (
                    NOWRAP_STYLE +
                    "background-color: var(--pico-primary-background); " if is_selected else NOWRAP_STYLE
                )
                profile_items.append(
                    create_menu_item(
                        profile.name,
                        f"/profiles/{profile.id}",
                        profile_id,
                        is_traditional_link=False,
                        additional_style=item_style
                    )
                )

        # Define the profile menu
        profile_menu = Details(
            Summary(
                selected_profile_name,
                style=generate_menu_style(PROFILE_MENU_WIDTH) + NOWRAP_STYLE,
                id=profile_id,
            ),
            Ul(
                *profile_items,
                dir="rtl",
            ),
            cls="dropdown",
        )
        nav_items.append(profile_menu)

    if SHOW_APP_MENU:
        logger.debug("Adding app menu to navigation.")
        # Define the apps menu
        explore_menu = Details(
            Summary(
                selected_explore,
                style=generate_menu_style(EXPLORE_MENU_WIDTH),
                id=explore_id,
            ),
            Ul(
                create_menu_item(
                    "Home",
                    "/",
                    explore_id,
                    is_traditional_link=True,
                    additional_style="background-color: var(--pico-primary-background); " if selected_explore == "Home" else ""
                ),
                create_menu_item(
                    "Profiles",
                    "/profile",
                    explore_id,
                    is_traditional_link=True,
                    additional_style="background-color: var(--pico-primary-background); " if selected_explore == "Profiles" else ""
                ),
                create_menu_item(
                    "Todo Lists",
                    "/todo",
                    explore_id,
                    is_traditional_link=True,
                    additional_style="background-color: var(--pico-primary-background); " if selected_explore == "Todo" else ""
                ),
                create_menu_item(
                    "Application 1",
                    "/application1",
                    explore_id,
                    is_traditional_link=True,
                    additional_style="background-color: var(--pico-primary-background); " if selected_explore == "Application 1" else ""
                ),
                create_menu_item(
                    "Application 2",
                    "/application2",
                    explore_id,
                    is_traditional_link=True,
                    additional_style="background-color: var(--pico-primary-background); " if selected_explore == "Application 2" else ""
                ),
                create_menu_item(
                    "Application 3",
                    "/application3",
                    explore_id,
                    is_traditional_link=True,
                    additional_style="background-color: var(--pico-primary-background); " if selected_explore == "Application 3" else ""
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
                    style=search_button_style,
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
    """Create a chat input group with a message input and a send button."""
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
    """Create an input field for adding a new todo item."""
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
    """Populate the database with initial data if empty."""
    logger.debug("Populating initial data.")
    if not profiles():
        # Create a default profile
        default_profile = profiles.insert({
            "name": "Default Profile",
            "email": "",
            "phone": "",
            "active": True,
        })
        logger.info(f"Inserted default profile: {default_profile}")
    else:
        default_profile = profiles()[0]

    if not todos():
        # Add a sample todo with the default profile_id
        todos.insert({
            "title": "Sample Todo",
            "done": False,
            "priority": 1,
            "profile_id": default_profile.id,
        })
        logger.info("Inserted sample todo item.")

# Call this function after the fast_app initialization
populate_initial_data()

# *******************************
# Create Main Content
# *******************************
def create_main_content(show_content=False):
    """Create the main content for all routes."""
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
    if not current_profile_id:
        # Use default profile ID
        default_profile = profiles()[0]
        current_profile_id = default_profile.id
        logger.warning(f"No profile ID found. Using default profile ID: {current_profile_id}")

    # Set the profile_id in the todos API to filter results
    todos.xtra(profile_id=current_profile_id)

    selected_explore = db.get("last_explore_choice", "App")

    # Fetch the filtered todo items
    todo_items = todos()
    logger.info(f"Fetched {len(todo_items)} todo items for profile ID {current_profile_id}.")

    return Container(
        nav_group,
        Grid(
            Div(
                Card(
                    H2(f"{selected_explore}"),
                    Ul(*[render(todo) for todo in todo_items], id='todo-list', style="padding-left: 0;"),
                    header=Form(
                        Group(
                            todo_mk_input(),
                            Button("Add", type="submit"),
                        ),
                        hx_post=f"/{selected_explore.lower()}",
                        hx_swap="beforeend",
                        hx_target="#todo-list",
                    ),
                ) if selected_explore == "Todo" else Card(
                    H2(f"{selected_explore}"),
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
@rt('/todo')
@rt('/profiles')
@rt('/application1')
@rt('/application2')
@rt('/application3')
def get(request):
    """
    Handle main page and specific page GET requests.
    """
    path = request.url.path.strip('/')
    logger.debug(f"Received request for path: {path}")

    show_content = path in ['todo', 'profiles', 'application1', 'application2', 'application3']
    selected_explore = path.capitalize().replace('application', 'Application ') if show_content else "Home"

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

    response = create_main_content(show_content)
    logger.debug("Returning response for main GET request.")
    last_profile_name = db.get("last_profile_name", "Default Profile")
    return Titled(
        f"{APP_NAME} / {last_profile_name} / {selected_explore} ",
        response,
        hx_ext='ws',
        ws_connect='/ws',
        data_theme="dark",
    )

@rt('/profiles/{profile_id}')
def profile_menu_handler(request, profile_id: int):
    """Handle profile menu selection and record the choice."""
    logger.debug(f"Profile menu selected with profile_id: {profile_id}")
    # Fetch the selected profile from the database using the profile ID
    selected_profile = profiles.get(profile_id)

    if not selected_profile:
        logger.error(f"Profile ID {profile_id} not found. Redirecting to /profiles.")
        return Redirect('/profiles')

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
@rt('/todo', methods=['POST'])
async def post_todo(title: str):
    """Create a new todo item."""
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
        f"New todo: '{title}'. "
        "Brief, sassy comment or advice."
    )
    await chatq(prompt)

    return render(inserted_todo), todo_mk_input()

@rt('/todo/delete/{tid}', methods=['DELETE'])
async def delete_todo(tid: int):
    """Delete a todo item."""
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

@rt('/todo/toggle/{tid}', methods=['POST'])
async def toggle_todo(tid: int):
    """Update the status of a todo item."""
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

@rt('/todo/update/{todo_id}', methods=['POST'])
async def update_todo(todo_id: int, todo_title: str):
    """Update the title of a todo item."""
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
    # Count the number of todo items for this profile
    todo_count = count_records_with_xtra(todos, 'profile_id', profile.id)

    # Set the visibility of the delete icon based on the todo count
    delete_icon_visibility = 'inline' if todo_count == 0 else 'none'

    """Render a profile item as an HTML list item."""
    # Create the delete button (trash can)
    delete_icon = A(
        '🗑',
        hx_post=f"/profile/delete/{profile.id}",
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
        hx_post=f"/toggle_active/{profile.id}",
        hx_target=f'#profile-{profile.id}',
        hx_swap='outerHTML',
        style="margin-right: 5px;"
    )

    # Create the update form
    update_form = Form(
        Group(
            Input(type="text", name="name", value=profile.name, placeholder="Name", id=f"name-{profile.id}"),
            Input(type="email", name="email", value=profile.email, placeholder="Email", id=f"email-{profile.id}"),
            Input(type="tel", name="phone", value=profile.phone, placeholder="Phone", id=f"phone-{profile.id}"),
            Button("Update", type="submit"),
        ),
        hx_post=f"/profile/update/{profile.id}",
        hx_target=f'#profile-{profile.id}',
        hx_swap='outerHTML',
        style="display: none;",
        id=f'update-form-{profile.id}'
    )

    # Create the title link with an onclick event to toggle the update form
    title_link = A(
        f"{profile.name} ({todo_count} Todo{'' if todo_count == 1 else 's'})",
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

    return Li(
        Div(
            active_checkbox,
            title_link,
            Span(f" ({profile.email}, {profile.phone})", style="margin-left: 10px;"),
            delete_icon,
            update_form,
            style="display: flex; align-items: center;"
        ),
        id=f'profile-{profile.id}',
        style="list-style-type: none;"
    )

@rt('/profiles', methods=['GET'])
def get_profiles():
    """Retrieve and display the list of profiles."""
    logger.debug("Retrieving profiles for display.")
    # Create the navigation group
    nav_group = create_nav_menu()

    return Container(
        nav_group,
        Grid(
            Div(
                Card(
                    H2("Profiles"),
                    Ul(*[render_profile(profile) for profile in profiles()], id='profile-list', style="padding-left: 0;"),
                    footer=Form(
                        Group(
                            Input(placeholder="New Profile Name", name="profile_name"),
                            Input(placeholder="Email", name="profile_email"),
                            Input(placeholder="Phone", name="profile_phone"),
                            Button("Add", type="submit"),
                        ),
                        hx_post="/add_profile",
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

@rt('/add_profile', methods=['POST'])
async def add_profile(profile_name: str, profile_email: str, profile_phone: str):
    """Create a new profile."""
    logger.debug(f"Attempting to add profile: {profile_name}, {profile_email}, {profile_phone}")
    if not profile_name.strip():
        logger.warning("User tried to add an empty profile name.")
        await chatq(
            "User tried to add an empty profile name. Respond with a brief, sassy comment about their attempt."
        )
        return ''

    new_profile = {
        "name": profile_name,
        "email": profile_email,
        "phone": profile_phone,
        "active": True,
    }

    inserted_profile = profiles.insert(new_profile)
    logger.info(f"Profile added: {inserted_profile}")

    prompt = (
        f"New profile '{profile_name}' just joined the party! Email: {profile_email}, Phone: {profile_phone}. "
        "Give a cute, welcoming response mentioning the new profile's name and one other detail. Keep it under 30 words."
    )
    await chatq(prompt)

    return render_profile(inserted_profile)

@rt('/toggle_active/{profile_id}', methods=['POST'])
async def toggle_active(profile_id: int):
    """Toggle the active status of a profile item."""
    logger.debug(f"Toggling active status for profile ID: {profile_id}")
    profile = profiles[profile_id]
    old_status = "active" if profile.active else "inactive"
    profile.active = not profile.active
    new_status = "active" if profile.active else "inactive"
    updated_profile = profiles.update(profile)
    logger.info(f"Toggled active status for profile ID {profile_id} to {profile.active}")

    prompt = (
        f"Profile '{profile.name}' just flipped their status from {old_status} to {new_status}! "
        "Give a cute, playful response about this change, mentioning the profile's name and new status. Keep it under 30 words."
    )
    await chatq(prompt)

    return render_profile(updated_profile)

@rt('/profile/delete/{profile_id}', methods=['POST'])
async def delete_profile(profile_id: int):
    """Delete a profile item."""
    logger.debug(f"Attempting to delete profile ID: {profile_id}")
    profile = profiles[profile_id]
    profiles.delete(profile_id)
    logger.warning(f"Deleted profile ID: {profile_id}")

    prompt = (
        f"Oh no! Profile '{profile.name}' just left the building. "
        "Give a cute, slightly dramatic response about this departure, mentioning the profile's name. Keep it under 30 words."
    )
    await chatq(prompt)

    return ''

@rt('/profile/update/{profile_id}', methods=['POST'])
async def update_profile(profile_id: int, name: str, email: str, phone: str):
    """Update a profile item."""
    logger.debug(f"Updating profile ID {profile_id} with new data.")
    # Fetch the existing profile item
    profile = profiles[profile_id]

    if not profile:
        logger.error(f"Profile ID {profile_id} not found for update.")
        return "Profile not found", 404

    # Store old values for comparison
    old_name = profile.name
    old_email = profile.email
    old_phone = profile.phone

    # Update the profile item's fields
    profile.name = name
    profile.email = email
    profile.phone = phone

    # Use the MiniDataAPI update method to save the changes
    try:
        updated_profile = profiles.update(profile)
        logger.info(f"Updated profile ID {profile_id}: {updated_profile}")

        # Determine what changed
        changes = []
        if old_name != name:
            changes.append(f"name from '{old_name}' to '{name}'")
        if old_email != email:
            changes.append(f"email from '{old_email}' to '{email}'")
        if old_phone != phone:
            changes.append(f"phone from '{old_phone}' to '{phone}'")

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

@rt('/profile', methods=['GET'])
def profile_app(request):
    """
    Handle the profile app GET request.
    """
    logger.debug("Entering profile_app function")

    # Set the last_explore_choice to "Profiles"
    db["last_explore_choice"] = "Profiles"
    logger.info("Set last_explore_choice to 'Profiles'")

    # Set the last_visited_url to the current URL
    db["last_visited_url"] = request.url.path
    logger.info(f"Set last_visited_url to '{request.url.path}'")

    # Retrieve the current profile name from the database
    current_profile_name = db.get("last_profile_name", "Profiles")
    logger.debug(f"Current profile name: {current_profile_name}")

    response = Titled(
        f"{APP_NAME} / {current_profile_name} / Profiles",
        get_profiles(),
        hx_ext='ws',
        ws_connect='/ws',
        data_theme="dark",
    )

    logger.debug("Exiting profile_app function")

    return response

# *******************************
# Streaming WebSocket Functions
# *******************************

# WebSocket users
users = {}

async def on_conn(ws, send):
    """Handle WebSocket connection."""
    users[str(id(ws))] = send
    logger.info(f"WebSocket connection established with ID: {id(ws)}")
    # Get the last app choice from the db
    selected_explore = db.get("last_explore_choice", "App")

    # Create a personalized welcome message
    welcome_prompt = f"Say 'Welcome to {selected_explore}' and add a brief, friendly greeting related to this area. Keep it under 25 words."

    # Queue the welcome message when a new connection is established
    await chatq(welcome_prompt)

def on_disconn(ws):
    """Handle WebSocket disconnection."""
    users.pop(str(id(ws)), None)
    logger.info(f"WebSocket connection closed with ID: {id(ws)}")

async def chatq(message: str):
    """Queue a message for the chat stream."""
    # Create a task for streaming the chat response without blocking
    asyncio.create_task(stream_chat(message))
    logger.debug(f"Message queued for chat: {message}")

async def stream_chat(prompt: str, quick: bool = False):
    """Generate and stream an AI response to users."""
    logger.debug(f"Streaming chat response for prompt: {prompt}")
    response = await run_in_threadpool(
        chat_with_ollama,
        model,
        [{"role": "user", "content": prompt}],
    )

    if quick:
        # Send the entire response at once
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
        # Stream the response word by word
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
    """Handle WebSocket messages."""
    logger.debug(f"WebSocket message received: {msg}")
    if msg:
        # Disable the input group
        disable_input_group = mk_chat_input_group(disabled=True, value=msg, autofocus=False)
        disable_input_group.attrs['hx_swap_oob'] = "true"
        for u in users.values():
            await u(disable_input_group)
        logger.debug("Input group disabled for typing effect.")

        # Process the message and generate response
        global conversation
        conversation.append({"role": "user", "content": msg})

        # Start streaming response
        response = await run_in_threadpool(chat_with_ollama, model, conversation)
        conversation.append({"role": "assistant", "content": response})
        logger.info(f"Assistant response generated.")

        # Simulate typing effect (AI response remains green)
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

        # Re-enable the input group
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
    Handle search queries to inform the user that the search feature is not implemented yet.
    """
    logger.debug(f"Search requested with input: '{nav_input}'")
    # The search term is now directly available as a parameter
    search_term = nav_input

    # Inform the user that the search feature is not implemented with a joke
    await chatq(f"Searching for '{search_term}'? Sorry, that feature is still in beta. Keep the reply under 20 words.")

# *******************************
# Poke Endpoint
# *******************************
@rt('/poke', methods=['POST'])
async def poke_chatbot():
    """
    Handle the poke interaction with the chatbot.
    """
    logger.debug("Chatbot poke received.")
    # Define a poke message for the chatbot
    poke_message = f"You poked the {APP_NAME} Chatbot. Respond with a brief, funny comment about being poked."

    # Queue the message for streaming to the chat interface
    await chatq(poke_message)

    # Respond with an empty string or a relevant message
    return "Poke received. Check the chat for a response!"

# *******************************
# Activate the Application
# *******************************

# Set the model
model = get_best_model()
logger.info(f"Using model: {model}")
serve()

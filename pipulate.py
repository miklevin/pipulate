import asyncio
import json
import re
from typing import List, Optional

import requests
from fasthtml.common import *
from starlette.concurrency import run_in_threadpool
import logging

# Set up logging
logger = logging.getLogger(__name__)  # Create a logger object
logger.setLevel(logging.DEBUG)  # Set the logging level

# Create file handler
file_handler = logging.FileHandler('botifython.log')
file_handler.setLevel(logging.DEBUG)  # Log level for file

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # Log level for console

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# *******************************
# Styles and Configuration
# *******************************
# Application name and configuration settings
# Get the APP_NAME from the repo folder name
APP_NAME = os.path.basename(os.path.dirname(os.path.abspath(__file__))).capitalize()
MAX_LLM_RESPONSE_WORDS = 30     # Maximum number of words in LLM response
TYPING_DELAY = 0.05             # Delay for simulating typing effect
DEFAULT_LLM_MODEL = "llama3.2"  # Set the default LLaMA model

# Grid layout constants
GRID_LAYOUT = "70% 30%"

# Define the width for the menus
bw = "150px"
NAV_FILLER_WIDTH = "20%"        # Width for the filler in the navigation
PROFILE_MENU_WIDTH = f"200px"    # Width for the profile menu
ACTION_MENU_WIDTH = f"{bw}"     # Width for the action menu
EXPLORE_MENU_WIDTH = f"{bw}"    # Width for the app menu
SEARCH_WIDTH = f"{bw}"          # Width for the search input

# Initialize IDs for menus
profile_id = "profile-id"       # Initialize the ID for the profile menu
action_id = "action-id"         # Initialize the ID for the action menu
explore_id = "app-id"           # Initialize the ID for the app menu

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
SHOW_PROFILE_MENU = True  # Toggle for showing the profile menu
SHOW_APP_MENU = True      # Toggle for showing the app menu
SHOW_ACTION_MENU = False  # Toggle for showing the action menu
SHOW_SEARCH = True        # Toggle for showing the search input

def generate_menu_style(width: str) -> str:
    """Generate a common style for menu elements with a specified width."""
    return COMMON_MENU_STYLE + f"width: {width}; "

# *******************************
# Ollama LLM Functions
# *******************************
def limit_llm_response(response: str) -> str:
    """Truncate the response to a maximum number of words."""
    return ' '.join(response.split()[:MAX_LLM_RESPONSE_WORDS])

def get_best_model() -> str:
    """Retrieve the best available LLaMA model or default to 'llama3.2'."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        response.raise_for_status()
        models = [model['name'] for model in response.json().get('models', [])]
    except requests.RequestException as e:
        print(f"Error fetching models: {e}")
        return DEFAULT_LLM_MODEL  # Default if there's an error

    # Filter for LLaMA models and determine the best one
    llama_models = [model for model in models if model.lower().startswith('llama')]
    if not llama_models:
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
            parse_version(base_version),  # Base version for sorting
            1 if version == 'latest' else 0,  # Prioritize 'latest' versions
            parse_version(version),  # Version for sorting
        )

    return max(llama_models, key=key_func)  # Return the best model based on the sorting key

def chat_with_ollama(model: str, messages: list) -> str:
    """Interact with the Ollama model to generate a response."""
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        response.raise_for_status()  # Raise an error for bad responses (4xx and 5xx)
        return response.json()['message']['content']  # Return the generated content
    except requests.exceptions.HTTPError as http_err:
        # Log the error
        print(f"HTTP error occurred: {http_err}")
        return "I'm having trouble processing that request right now."  # User-friendly message
    except requests.exceptions.ConnectionError as conn_err:
        # Log the error
        print(f"Connection error occurred: {conn_err}")
        return "I'm having trouble processing that request right now."  # User-friendly message
    except requests.exceptions.Timeout as timeout_err:
        # Log the error
        print(f"Timeout error occurred: {timeout_err}")
        return "I'm having trouble processing that request right now."  # User-friendly message
    except requests.exceptions.RequestException as req_err:
        # Log the error
        print(f"An error occurred: {req_err}")
        return "I'm having trouble processing that request right now."  # User-friendly message

# *******************************
# Todo Render Function (Must come before Application Setup)
# *******************************

def render(todo):
    """Render a todo item as an HTML list item with an update form."""
    tid = f'todo-{todo.id}'  # Unique ID for the todo item
    checkbox = Input(
        type="checkbox",
        name="english" if todo.done else None,  # Checkbox name based on completion status
        checked=todo.done,  # Set checkbox state based on todo status
        hx_post=f"/todo/toggle/{todo.id}",  # Endpoint to toggle the todo status
        hx_swap="outerHTML",  # Update the checkbox in the DOM
        hx_target=f"#{tid}",  # Target the specific todo item
    )
    
    # Create the delete button (trash can)
    delete = A(
        '🗑',  # Trash can emoji
        hx_delete=f'/todo/delete/{todo.id}',  # Endpoint to delete the todo
        hx_swap='outerHTML',  # Update the todo item in the DOM
        hx_target=f"#{tid}",  # Target the specific todo item
        style="cursor: pointer; display: inline;" ,  # Change cursor to pointer for delete action
        cls="delete-icon"  # Add a class for easy selection
    )
    
    # Create the title link with no text decoration
    title_link = A(
        todo.title,  # Title text
        href="#",  # Prevent default link behavior
        cls="todo-title",  # Class for styling
        style="text-decoration: none; color: inherit;",  # Remove text decoration and inherit color
        onclick=(
            "let updateForm = this.nextElementSibling; "  # Get the next sibling (the update form)
            "let checkbox = this.parentNode.querySelector('input[type=checkbox]'); "  # Get the checkbox
            "let deleteIcon = this.parentNode.querySelector('.delete-icon'); "  # Get the delete icon
            "if (updateForm.style.visibility === 'hidden' || updateForm.style.visibility === '') { "
            "    updateForm.style.visibility = 'visible'; "
            "    updateForm.style.height = 'auto'; "
            "    checkbox.style.display = 'none'; "  # Hide the checkbox
            "    deleteIcon.style.display = 'none'; "  # Hide the delete icon
            "    this.remove(); "  # Remove the anchor text from the DOM
            "    const inputField = document.getElementById('todo_title_" + str(todo.id) + "'); "  # Reference the input field
            "    inputField.focus(); "  # Focus on the input field
            "    inputField.setSelectionRange(inputField.value.length, inputField.value.length); "  # Set cursor at the end
            "} else { "
            "    updateForm.style.visibility = 'hidden'; "
            "    updateForm.style.height = '0'; "
            "    checkbox.style.display = 'inline'; "  # Show the checkbox
            "    deleteIcon.style.display = 'inline'; "  # Show the delete icon
            "    this.style.visibility = 'visible'; "  # Show the anchor text
            "}"
        )  # Toggle visibility
    )

    # Create the update form
    update_form = Form(
        Div(
            Input(
                type="text",
                id=f"todo_title_{todo.id}",  # Unique ID for the input field
                value=todo.title,
                name="todo_title",  # Ensure this has a name attribute
                style="flex: 1; padding-right: 10px; margin-bottom: 0px;"  # Allow the input to grow
            ),
            style="display: flex; align-items: center;"  # Flexbox to align items in a row
        ),
        Input(
            type="hidden",
            name="todo_id",  # Ensure this has a name attribute
            value=todo.id
        ),
        style="visibility: hidden; height: 0; overflow: hidden;",  # Initially hidden
        hx_post=f"/todo/update/{todo.id}",  # Specify the endpoint for the form submission
        hx_target=f"#{tid}",  # Target the specific todo item for the response
        hx_swap="outerHTML",  # Replace the outer HTML of the target element
    )

    return Li(
        delete,
        checkbox,
        title_link,  # Use the updated title link
        update_form,  # Include the update form
        id=tid,  # Set the ID for the list item
        cls='done' if todo.done else '',  # Add class if the todo is done
        style="list-style-type: none;"
    )

# *******************************
# Application Setup
# *******************************

# Unpack the returned tuple from fast_app
app, rt, (store, Store), (todos, Todo), (profiles, Profile) = fast_app(  # Unpack the tables directly
    "data/app.db",  # Database file path
    ws_hdr=True,  # Enable WebSocket headers
    live=True,  # Enable live updates
    render=render,  # Set the render function for todos
    store={
        "key": str,
        "value": str,
        "pk": "key"  # Primary key for the store
    },
    todos={
        "id": int,
        "title": str,
        "done": bool,
        "priority": int,
        "profile_id": int,  # Use int for profile_id
        "pk": "id"  # Primary key for todos
    },
    profiles={
        "id": int,
        "name": str,
        "email": str,
        "phone": str,
        "active": bool,  # New active field
        "pk": "id"  # Primary key for profiles
    },
)

# *******************************
# DictLikeDB Persistence Convenience Wrapper
# *******************************
class DictLikeDB:
    """A wrapper class for a dictionary-like database to simplify access."""
    
    def __init__(self, store, Store):
        self.store = store  # Store reference
        self.Store = Store  # Store class reference

    def __getitem__(self, key):
        """Retrieve an item from the store by key."""
        try:
            return self.store[key].value  # Return the value associated with the key
        except NotFoundError:
            logger.error(f"Key not found: {key}")  # Log error if key is not found
            raise KeyError(key)  # Raise KeyError if not found

    def __setitem__(self, key, value):
        """Set an item in the store by key."""
        try:
            # Try to update existing item
            self.store.update({"key": key, "value": value})
            logger.info(f"Updated persistence store: {key} = {value}")  # Log the update
        except NotFoundError:
            # If it doesn't exist, insert a new item
            self.store.insert({"key": key, "value": value})
            logger.info(f"Inserted new item in persistence store: {key} = {value}")  # Log the insertion

    def __delitem__(self, key):
        """Delete an item from the store by key."""
        try:
            self.store.delete(key)  # Delete the item
            logger.info(f"Deleted key from persistence store: {key}")  # Log the deletion
        except NotFoundError:
            logger.error(f"Attempted to delete non-existent key: {key}")  # Log error if key is not found
            raise KeyError(key)  # Raise KeyError if not found

    def __contains__(self, key):
        """Check if a key exists in the store."""
        return key in self.store

    def __iter__(self):
        """Iterate over the keys in the store."""
        for item in self.store():
            yield item.key  # Yield each key

    def items(self):
        """Return key-value pairs in the store."""
        for item in self.store():
            yield item.key, item.value  # Yield key-value pairs

    def keys(self):
        """Return a list of keys in the store."""
        return list(self)

    def values(self):
        """Return values in the store."""
        for item in self.store():
            yield item.value  # Yield each value

    def get(self, key, default=None):
        """Get an item from the store, returning default if not found."""
        try:
            return self[key]  # Attempt to retrieve the item
        except KeyError:
            return default  # Return default if not found

# Create the wrapper
db = DictLikeDB(store, Store)

# *******************************
# Site Navigation
# *******************************

def create_menu_item(title, link, summary_id, is_traditional_link=False):
    """Create a menu item for the navigation."""
    if is_traditional_link:
        return Li(
            A(
                title,
                href=link,  # Traditional link
                cls="menu-item",
            ),
            style="text-align: center;"  # Center the item
        )
    else:
        return Li(
            A(
                title,
                hx_get=link,  # HTMX link for dynamic loading
                hx_target=f"#{summary_id}",  # Target the summary ID
                hx_swap="outerHTML",  # Update the item in the DOM
                hx_trigger="click",  # Trigger on click
                hx_push_url="false",  # Do not push URL to history
                cls="menu-item",
            ),
            style="text-align: center;"  # Center the item
        )

def create_nav_menu():
    """Create the navigation menu with app, profile, and action dropdowns."""
    # Fetch the last selected items from the db
    selected_profile_id = db.get("last_profile_id")
    selected_profile_name = db.get("last_profile_name", "Profiles")  # Default to "Profiles"
    selected_explore = db.get("last_explore_choice", "App")  # Default to "App"
    selected_action = db.get("last_action_choice", "Actions")  # Default to "Actions"

    # Use generate_menu_style for the common style
    profile_menu_style = generate_menu_style(PROFILE_MENU_WIDTH)
    action_menu_style = generate_menu_style(ACTION_MENU_WIDTH)

    # Filler Item: Non-interactive, occupies significant space
    filler_item = Li(
        Span(" "),  # Empty span as a filler
        style=(
            "flex-grow: 1; "  # Allows it to grow
            f"min-width: {NAV_FILLER_WIDTH}; "  # Ensures a minimum width
            "list-style-type: none; "  # Removes the bullet point
            "display: flex; "  # Center the items
            "justify-content: center; "  # Center the items
        ),
    )

    nav_items = [filler_item]  # Start with the filler item

    if SHOW_PROFILE_MENU:
        # Fetch profiles from the database
        profile_items = []
        for profile in profiles():
            # Use profile.id and profile.name for the menu item
            profile_items.append(
                create_menu_item(
                    profile.name,
                    f"/profiles/{profile.id}",  # Ensure this points to the correct profile URL
                    profile_id,
                    is_traditional_link=False  # Use HTMX for dynamic updates
                )
            )

        # Define the profile menu
        profile_menu = Details(
            Summary(
                selected_profile_name,  # Display the selected profile name
                style=generate_menu_style(PROFILE_MENU_WIDTH),
                id=profile_id,
            ),
            Ul(
                *profile_items,  # Unpack the profile items into the unordered list
                dir="rtl",  # Right-to-left direction
            ),
            cls="dropdown",  # Class for dropdown styling
        )
        nav_items.append(profile_menu)  # Add profile menu to nav items

    if SHOW_APP_MENU:
        # Define the apps menu
        explore_menu = Details(
            Summary(
                selected_explore,  # Use the selected explore from the persistent db
                style=generate_menu_style(EXPLORE_MENU_WIDTH),
                id=explore_id,
            ),
            Ul(
                create_menu_item("Profiles", "/profile", explore_id, is_traditional_link=True),
                create_menu_item("Todo Lists", "/todo", explore_id, is_traditional_link=True),
                dir="rtl",  # Right-to-left direction
            ),
            cls="dropdown",  # Class for dropdown styling
        )
        nav_items.append(explore_menu)  # Add apps menu to nav items

    if SHOW_ACTION_MENU:
        # Define the action menu (left unchanged for brevity)
        pass  # Add action menu items if needed

    if SHOW_SEARCH:
        # Define the search button style
        search_button_style = (
            generate_menu_style(SEARCH_WIDTH) +  # Use the height for the button
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
                    placeholder="Search",  # Placeholder for the search input
                    name="nav_input",  # Name for the input
                    id="nav-input",  # ID for the input
                    hx_post="/search",  # Endpoint for search
                    hx_trigger="keyup[keyCode==13]",  # Trigger on Enter key
                    hx_target="#msg-list",  # Target for the response
                    hx_swap="innerHTML",  # Update the inner HTML
                    style=(
                        f"{action_menu_style} "
                        f"width: {SEARCH_WIDTH}; "
                        "padding-right: 25px; "
                        "border: 1px solid var(--pico-muted-border-color); "
                    ),
                ),
                Button(
                    "×",  # Clear button
                    type="button",
                    onclick="document.getElementById('nav-input').value = ''; this.blur();",  # Clear input on click
                    style=search_button_style,
                ),
                style=(
                    "align-items: center; "
                    "display: flex; "
                    "position: relative; "
                ),
            ),
            hx_post="/search",  # Ensure the form submits to the search endpoint
            hx_target="#msg-list",  # Target for the response
            hx_swap="innerHTML",  # Update the inner HTML
        )
        
        nav_items.append(search_group)  # Add search group to nav items

    # Create the navigation container
    nav = Div(
        *nav_items,  # Unpack nav items
        style=(
            "align-items: center; "
            "display: flex; "
            "gap: 8px; "
            "width: 100%; "
            "justify-content: flex-end; "
        ),
    )

    return nav  # Return the constructed navigation menu

def mk_chat_input_group(disabled=False, value='', autofocus=True):
    """Create a chat input group with a message input and a send button."""
    return Group(
        Input(
            id='msg',  # ID for the message input
            name='msg',  # Name for the input
            placeholder='Chat...',  # Placeholder for the input
            value=value,  # Pre-fill value if provided
            disabled=disabled,  # Disable input if specified
            autofocus='autofocus' if autofocus else None,  # Autofocus if specified
        ),
        Button(
            "Send",  # Send button label
            type='submit',  # Submit type
            ws_send=True,  # Enable WebSocket sending
            id='send-btn',  # ID for the send button
            disabled=disabled,  # Disable button if specified
        ),
        id='input-group',  # ID for the input group
    )

# *******************************
# Todo Common Support Functions
# *******************************
def todo_mk_input():
    """Create an input field for adding a new todo item."""
    return Input(
        placeholder='Add a new item',  # Placeholder for the input
        id='title',  # ID for the input
        hx_swap_oob='true',  # Enable out-of-band swapping
        autofocus=True,  # Autofocus the input
        name='title',  # Add the name attribute
    )

# *******************************
# Database Initialization
# *******************************

def populate_initial_data():
    """Populate the database with initial data if empty."""
    if not profiles():
        # Create a default profile
        default_profile = profiles.insert({
            "name": "Default Profile",
            "email": "",
            "phone": "",
            "active": True,
        })
    else:
        default_profile = profiles()[0]  # Use the first existing profile

    if not todos():
        # Add a sample todo with the default profile_id
        todos.insert({
            "title": "Sample Todo",
            "done": False,
            "priority": 1,
            "profile_id": default_profile.id,  # Ensure the todo is linked to the default profile
        })

# Call this function after the fast_app initialization
populate_initial_data()

# *******************************
# Create Main Content
# *******************************
def create_main_content(show_content=False):
    """Create the main content for all routes."""
    nav = create_nav_menu()  # Create the navigation menu
    nav_group_style = (
        "display: flex; "
        "align-items: center; "
        "position: relative;"
    )
    nav_group = Group(
        nav,  # Add the navigation menu to the group
        style=nav_group_style,  # Apply styles to the group
    )
    
    current_profile_id = db.get("last_profile_id")
    if not current_profile_id:
        # Use default profile ID
        default_profile = profiles()[0]  # Ensure there is at least one profile
        current_profile_id = default_profile.id  # Ensure we have a valid profile ID

    # Set the profile_id in the todos API to filter results
    todos.xtra(profile_id=current_profile_id)  # Filter todos by the current profile_id

    selected_explore = db.get("last_explore_choice", "App")  # Get the last app choice

    # Fetch the filtered todo items
    todo_items = todos()  # Fetch the filtered todo items

    return Container(
        nav_group,  # Add the navigation group to the container
        Grid(
            Div(
                Card(
                    H2(f"{selected_explore}"),  # Header for the selected app item
                    Ul(*[render(todo) for todo in todo_items], id='todo-list', style="padding-left: 0;"),  # Render todos
                    header=Form(
                        Group(
                            todo_mk_input(),  # Input for new todo
                            Button("Add", type="submit"),  # Button to add new todo
                        ),
                        hx_post=f"/{selected_explore.lower()}",  # Endpoint for adding todos
                        hx_swap="beforeend",  # Update the list after adding
                        hx_target="#todo-list",  # Target the todo list
                    ),
                ) if selected_explore == "Todo" else "",  # Only show if selected is "Todo"
                id="content-container",  # ID for the content container
            ),
            Div(
                Card(
                    H2(f"{APP_NAME} Chatbot"),  # Updated header for the chat section
                    Div(
                        id='msg-list',  # ID for the message list
                        cls='overflow-auto',  # Class for overflow handling
                        style='height: 40vh;',  # Set height for the chat area
                    ),
                    footer=Form(
                        mk_chat_input_group(),  # Create the chat input group
                    ),
                ),
            ),
            cls="grid",  # Class for grid layout
            style=(
                "display: grid; "
                "gap: 20px; "
                f"grid-template-columns: {GRID_LAYOUT}; "  # Set grid layout
            ),
        ),
        Div(
            A(
                f"Poke {APP_NAME} Chatbot",  # Updated button to poke the chatbot
                hx_post="/poke",  # Endpoint for poking
                hx_target="#msg-list",  # Target for the message list
                hx_swap="innerHTML",  # Update the inner HTML
                cls="button",  # Class for button styling
            ),
            style=(
                "bottom: 20px; "
                "position: fixed; "
                "right: 20px; "
                "z-index: 1000; "  # Ensure button is on top
            ),
        ),
    )

# *******************************
# Site Navigation Main Endpoints
# *******************************
@rt('/')
@rt('/todo')
@rt('/profiles')  # Ensure this is the correct endpoint
@rt('/organizations')
@rt('/projects')
def get(request):
    """
    Handle main page and specific page GET requests.
    """
    path = request.url.path.strip('/')  # Get the path from the request
    logger.debug(f"Received request for path: {path}")  # Log the requested path

    show_content = path in ['todo', 'profiles', 'organizations', 'projects']  # Check if content should be shown
    selected_explore = path.capitalize() if show_content else "App"  # Set the selected app item

    logger.info(f"Selected explore item: {selected_explore}")  # Log the selected item
    db["last_explore_choice"] = selected_explore  # Store the last app choice in the database
    db["last_visited_url"] = request.url.path  # Update the last visited URL

    # Apply the profile filter if necessary
    current_profile_id = db.get("last_profile_id")  # Get the current profile ID
    if current_profile_id:
        logger.debug(f"Current profile ID: {current_profile_id}")  # Log the current profile ID
        todos.xtra(profile_id=current_profile_id)  # Filter todos by the current profile ID
    else:
        logger.warning("No current profile ID found. Using default filtering.")  # Log if no profile ID is found
        todos.xtra(profile_id=None)  # No filtering or set a default profile ID

    response = create_main_content(show_content)  # Create the main content based on the path
    logger.debug("Returning response for main GET request.")  # Log before returning the response
    logger.debug(f"Response content: {response}")  # Log the response content
    last_profile_name = db.get("last_profile_name", "Default Profile")
    return Titled(
        f"{APP_NAME} / {last_profile_name} / {selected_explore} ",  # Title for the page
        response,
        hx_ext='ws',  # Enable WebSocket extensions
        ws_connect='/ws',  # WebSocket connection endpoint
        data_theme="dark",  # Set the theme for the page
    )

@rt('/profiles/{profile_id}')  # Ensure this is the correct endpoint
def profile_menu_handler(request, profile_id: int):
    """Handle profile menu selection and record the choice."""
    # Fetch the selected profile from the database using the profile ID
    selected_profile = profiles.get(profile_id)

    if not selected_profile:
        # If the profile doesn't exist, redirect to a default or error page
        return Redirect('/profiles')

    # Store the selected profile ID and name in the database
    db["last_profile_id"] = selected_profile.id
    db["last_profile_name"] = selected_profile.name

    # Retrieve the last visited URL from the database
    last_visited_url = db.get("last_visited_url", "/")  # Default to home if not set

    # Return a redirect response to the last visited URL
    return Redirect(last_visited_url)

# *******************************
# Todo App Endpoints
# *******************************
@rt('/todo', methods=['POST'])
async def post_todo(title: str):
    """Create a new todo item."""
    if not title.strip():  # Check for empty title
        # Empty todo case
        await chatq(
            "User tried to add an empty todo. Respond with a brief, sassy comment about their attempt."
        )
        return ''  # Return empty string to prevent insertion

    # Non-empty todo case
    current_profile_id = db.get("last_profile_id")
    if not current_profile_id:
        # Use default profile ID
        default_profile = profiles()[0]  # Ensure there is at least one profile
        current_profile_id = default_profile.id  # Ensure we have a valid profile ID

    # Create a new todo item with the profile_id included
    todo = {
        "title": title,
        "done": False,
        "priority": 0,
        "profile_id": current_profile_id,
    }
    inserted_todo = todos.insert(todo)  # Insert the new todo

    prompt = (
        f"New todo: '{title}'. "
        "Brief, sassy comment or advice."
    )
    await chatq(prompt)  # Send prompt to chat queue

    return render(inserted_todo), todo_mk_input()  # Return the rendered todo and input field

@rt('/todo/delete/{tid}', methods=['DELETE'])
async def delete_todo(tid: int):
    """Delete a todo item."""
    todo = todos[tid]  # Get the todo item before deleting it
    todos.delete(tid)  # Delete the todo item
    prompt = (
        f"Todo '{todo.title}' deleted. "
        "Brief, sassy reaction."
    )
    await chatq(prompt)  # Send prompt to chat queue
    return ''  # Return an empty string to remove the item from the DOM

@rt('/todo/toggle/{tid}', methods=['POST'])
async def toggle_todo(tid: int):
    """Update the status of a todo item."""
    todo = todos[tid]  # Get the todo item
    old_status = "Done" if todo.done else "Not Done"  # Determine old status
    todo.done = not todo.done  # Toggle the done status
    updated_todo = todos.update(todo)  # Update the todo item

    prompt = (
        f"Todo '{todo.title}' toggled from {old_status} to {'Done' if todo.done else 'Not Done'}. "
        f"Brief, sassy comment mentioning '{todo.title}'."
    )
    await chatq(prompt)  # Send prompt to chat queue

    return render(updated_todo)  # Return the updated todo rendering

@rt('/todo/update/{todo_id}', methods=['POST'])
async def update_todo(todo_id: int, todo_title: str):
    """Update the title of a todo item."""
    # Fetch the existing Todo item
    todo = todos[todo_id]  # Get the Todo item by its primary key

    if not todo:
        return "Todo not found", 404

    # Update the Todo item's title
    todo.title = todo_title

    # Use the MiniDataAPI update method to save the changes
    try:
        updated_todo = todos.update(todo)  # Update the record in the database
    except NotFoundError:
        return "Todo not found for update", 404

    # Return the updated Todo item using the render function
    return render(updated_todo)  # Call the render function to return the updated HTML

@rt('/profile/update/{profile_id}', methods=['POST'])
async def update_profile(profile_id: int, name: str, email: str, phone: str):
    """Update a profile item."""
    # Fetch the existing profile item
    profile = profiles[profile_id]  # Assuming profiles is a data structure holding profile data

    if not profile:
        return "Profile not found", 404

    # Update the profile item's fields
    profile.name = name
    profile.email = email
    profile.phone = phone

    # Use the MiniDataAPI update method to save the changes
    try:
        updated_profile = profiles.update(profile)  # Update the record in the database
    except NotFoundError:
        return "Profile not found for update", 404

    # Return the updated profile item using the render function
    return render_profile(updated_profile)  # Call the render function to return the updated HTML

# *******************************
# Streaming WebSocket Functions
# *******************************

# WebSocket users
users = {}  # Dictionary to keep track of connected users

async def on_conn(ws, send):
    """Handle WebSocket connection."""
    users[str(id(ws))] = send  # Add the new user to the users dictionary
    # Get the last app choice from the db
    selected_explore = db.get("last_explore_choice", "App")  # Retrieve last app choice

    # Create a personalized welcome message
    welcome_prompt = f"Say 'Welcome to {selected_explore}' and add a brief, friendly greeting related to this area. Keep it under 25 words."

    # Queue the welcome message when a new connection is established
    await chatq(welcome_prompt)  # Send the welcome prompt to the chat queue

def on_disconn(ws):
    """Handle WebSocket disconnection."""
    users.pop(str(id(ws)), None)  # Remove the user from the users dictionary

async def chatq(message: str):
    """Queue a message for the chat stream."""
    # Create a task for streaming the chat response without blocking
    asyncio.create_task(stream_chat(message))  # Start streaming the chat response

async def stream_chat(prompt: str, quick: bool = False):
    """Generate and stream an AI response to users."""
    response = await run_in_threadpool(
        chat_with_ollama,
        model,
        [{"role": "user", "content": prompt}],  # Send the prompt to the model
    )

    if quick:
        # Send the entire response at once
        for u in users.values():
            await u(
                Div(
                    response,  # Display the response
                    id='msg-list',  # ID for the message list
                    cls='fade-in',  # Class for fade-in effect
                    style=MATRIX_STYLE,  # Apply matrix style
                )
            )
    else:
        # Stream the response word by word
        words = response.split()  # Split response into words
        for i in range(len(words)):
            partial_response = " ".join(words[: i + 1])  # Create partial response
            for u in users.values():
                await u(
                    Div(
                        partial_response,  # Display partial response
                        id='msg-list',  # ID for the message list
                        cls='fade-in',  # Class for fade-in effect
                        style=MATRIX_STYLE,  # Apply matrix style
                        _=f"this.scrollIntoView({{behavior: 'smooth'}});",  # Smooth scroll to view
                    )
                )
            await asyncio.sleep(TYPING_DELAY)  # Use the constant for delay

@app.ws('/ws', conn=on_conn, disconn=on_disconn)
async def ws(msg: str):
    """Handle WebSocket messages."""
    if msg:
        # Disable the input group
        disable_input_group = mk_chat_input_group(disabled=True, value=msg, autofocus=False)  # Create disabled input group
        disable_input_group.attrs['hx_swap_oob'] = "true"  # Enable out-of-band swapping
        for u in users.values():
            await u(disable_input_group)  # Send disabled input group to all users

        # Process the message and generate response
        global conversation  # Use global conversation variable
        conversation.append({"role": "user", "content": msg})  # Append user message to conversation

        # Start streaming response
        response = await run_in_threadpool(chat_with_ollama, model, conversation)  # Get response from model
        conversation.append({"role": "assistant", "content": response})  # Append assistant response to conversation

        # Simulate typing effect (AI response remains green)
        words = response.split()  # Split response into words
        for i in range(len(words)):
            partial_response = " ".join(words[: i + 1])  # Create partial response
            for u in users.values():
                await u(
                    Div(
                        partial_response,  # Display partial response
                        id='msg-list',  # ID for the message list
                        cls='fade-in',  # Class for fade-in effect
                        style=MATRIX_STYLE,  # Apply matrix style
                        _=f"this.scrollIntoView({{behavior: 'smooth'}});",  # Smooth scroll to view
                    )
                )
            await asyncio.sleep(TYPING_DELAY)  # Use the constant for delay

        # Re-enable the input group
        enable_input_group = mk_chat_input_group(disabled=False, value='', autofocus=True)  # Create enabled input group
        enable_input_group.attrs['hx_swap_oob'] = "true"  # Enable out-of-band swapping
        for u in users.values():
            await u(enable_input_group)  # Send enabled input group to all users

# *******************************
# Profiles App Endpoints
# *******************************

@rt('/profiles', methods=['GET'])
def get_profiles():
    print("Entering get_profiles() function.")
    logger.debug("Entering get_profiles() function.")
    
    # Fetch profiles
    all_profiles = profiles()
    print(f"Number of profiles fetched: {len(all_profiles)}")
    logger.debug(f"Number of profiles fetched: {len(all_profiles)}")
    
    # Render profiles
    profile_list = [render_profile(profile) for profile in all_profiles]
    
    container = Container(
        H1("Profiles"),
        Ul(*profile_list, id='profile-list', style="padding-left: 0;"),
        Form(
            Group(
                Input(type="text", name="name", placeholder="Name"),
                Input(type="email", name="email", placeholder="Email"),
                Input(type="tel", name="phone", placeholder="Phone"),
                Button("Add", type="submit"),
            ),
            hx_post="/add_profile",
            hx_target="#profile-list",
            hx_swap="beforeend",
        )
    )
    
    print(f"Returning Container object: {type(container)}")
    logger.debug(f"Returning Container object: {type(container)}")
    
    print("Exiting get_profiles() function.")
    logger.debug("Exiting get_profiles() function.")
    
    return container

def render_profile(profile):
    """Render a profile item as an HTML list item."""
    # Create the delete button (trash can)
    delete_icon = A(
        '🗑',  # Trash can emoji
        hx_post=f"/profile/delete/{profile.id}",  # Change to POST for deletion
        hx_target=f'#profile-{profile.id}',  # Target the profile item to remove
        hx_swap='outerHTML',  # Update the profile list in the DOM
        style="cursor: pointer; display: inline;",  # Change cursor to pointer for delete action
        cls="delete-icon"  # Add a class for easy selection
    )

    # Create the active checkbox
    active_checkbox = Input(
        type="checkbox",
        name="active" if profile.active else None,  # Checkbox name based on active status
        checked=profile.active,  # Set checkbox state based on profile status
        hx_post=f"/toggle_active/{profile.id}",  # Endpoint to toggle the active status
        hx_target=f'#profile-{profile.id}',  # Target the profile item to update
        hx_swap='outerHTML',  # Update the checkbox in the DOM
        style="margin-right: 5px;"  # Add some margin
    )

    # Create the update form
    update_form = Form(
        Group(
            Input(type="text", name="name", value=profile.name, placeholder="Name", id=f"name-{profile.id}"),  # Input for name
            Input(type="email", name="email", value=profile.email, placeholder="Email", id=f"email-{profile.id}"),  # Input for email
            Input(type="tel", name="phone", value=profile.phone, placeholder="Phone", id=f"phone-{profile.id}"),  # Input for phone
            Button("Update", type="submit"),  # Update button
        ),
        hx_post=f"/profile/update/{profile.id}",  # Endpoint for updating the profile
        hx_target=f'#profile-{profile.id}',  # Target the profile item to update
        hx_swap='outerHTML',  # Replace the entire profile item
        style="display: none;",  # Initially hidden
        id=f'update-form-{profile.id}'  # Unique ID for the update form
    )

    # Create the title link with an onclick event to toggle the update form
    title_link = A(
        profile.name,  # Display the profile name as a clickable anchor
        href="#",  # Prevent default link behavior
        hx_trigger="click",  # Trigger on click
        onclick=(
            "let li = this.closest('li'); "  # Get the closest <li> element
            "let updateForm = document.getElementById('update-form-" + str(profile.id) + "'); "  # Get the update form
            "if (updateForm.style.display === 'none' || updateForm.style.display === '') { "
            "    updateForm.style.display = 'block'; "  # Show the update form
            "    li.querySelectorAll('input[type=checkbox], .delete-icon, span, a').forEach(el => el.style.display = 'none'); "  # Hide checkbox, delete icon, email/phone, and title link
            "} else { "
            "    updateForm.style.display = 'none'; "  # Hide the update form
            "    li.querySelectorAll('input[type=checkbox], .delete-icon, span, a').forEach(el => el.style.display = 'inline'); "  # Show checkbox, delete icon, email/phone, and title link
            "}"
        )  # Toggle visibility
    )

    return Li(
        Div(
            active_checkbox,  # Include the active checkbox
            title_link,  # Use the updated title link
            Span(f" ({profile.email}, {profile.phone})", style="margin-left: 10px;"),  # Display email and phone
            delete_icon,  # Include the delete icon
            update_form,  # Include the hidden update form
            style="display: flex; align-items: center;"  # Flexbox for alignment
        ),
        id=f'profile-{profile.id}',  # Unique ID for the profile item
        style="list-style-type: none;"  # Style for the list item
    )

@rt('/add_profile', methods=['POST'])
async def add_profile(profile_name: str, profile_email: str, profile_phone: str):
    """Create a new profile."""
    logger.debug(f"Attempting to add profile: {profile_name}, {profile_email}, {profile_phone}")
    
    if not profile_name.strip():  # Check for empty profile name
        logger.warning("User tried to add an empty profile name.")
        await chatq(
            "User tried to add an empty profile name. Respond with a brief, sassy comment about their attempt."
        )
        return ''  # Return empty string to prevent insertion

    new_profile = {
        "name": profile_name,
        "email": profile_email,
        "phone": profile_phone,
        "active": True,  # Default to active
    }

    inserted_profile = profiles.insert(new_profile)
    logger.info(f"Profile added: {inserted_profile}")

    prompt = (
        f"New profile added: '{profile_name}'. "
        "Brief, sassy comment or advice."
    )
    await chatq(prompt)  # Send prompt to chat queue

    return render_profile(inserted_profile)

@rt('/toggle_active/{profile_id}', methods=['POST'])
async def toggle_active(profile_id: int):
    """Toggle the active status of a profile item."""
    profile = profiles[profile_id]  # Get the profile item
    profile.active = not profile.active  # Toggle the active status
    updated_profile = profiles.update(profile)  # Update the profile item

    return render_profile(updated_profile)  # Return the updated profile rendering

@rt('/profile/delete/{profile_id}', methods=['POST'])
async def delete_profile(profile_id: int):
    """Delete a profile item."""
    profile = profiles[profile_id]  # Get the profile item
    profiles.delete(profile_id)  # Delete the profile item
    return ''  # Return an empty string to remove the item from the DOM

# *******************************
# Search Endpoint
# *******************************
@rt('/search', methods=['POST'])
async def search(nav_input: str = ''):
    """
    Handle search queries to inform the user that the search feature is not implemented yet.
    """
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
    # Define a poke message for the chatbot
    poke_message = f"You poked the {APP_NAME} Chatbot. Respond with a brief, funny comment about being poked."

    # Queue the message for streaming to the chat interface
    await chatq(poke_message)
    
    # Respond with an empty string or a relevant message
    return "Poke received. Check the chat for a response!"

# *******************************
# Debug Profiles Endpoint
# *******************************
@rt('/debug_profiles', methods=['GET'])
def debug_profiles():
    """Debug endpoint to retrieve and display profile information."""
    print("Entering debug_profiles() function.")
    logger.debug("Entering debug_profiles() function.")
    
    all_profiles = profiles()
    print(f"Number of profiles fetched: {len(all_profiles)}")
    logger.debug(f"Number of profiles fetched: {len(all_profiles)}")
    
    profile_info = [f"Profile {p.id}: {p.name}" for p in all_profiles]
    print(f"Profile information: {profile_info}")
    logger.debug(f"Profile information: {profile_info}")
    
    return f"Debug Profiles: {profile_info}"

# *******************************
# Debug Endpoint
# *******************************
@rt('/debug', methods=['GET'])
def debug_route():
    print("Debug route accessed")
    logger.debug("Debug route accessed")
    return "Debug route is working. Check the logs for more information."

# *******************************
# Activate the Application
# *******************************

# Add this line to set the model
model = get_best_model()  # Retrieve the best model
serve()  # Start the application

def read_log_file():
    """Read and print the contents of the log file."""
    try:
        with open('botifython.log', 'r') as log_file:
            log_contents = log_file.read()
            print("Log File Contents:")
            print(log_contents)
    except FileNotFoundError:
        print("Log file not found.")

print("Botifython version 1.0 - Debug mode")


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
    return len(table_handle())

# Example usage:
# Assuming you have a table handle object called `todos_handle`
# num_records = count_records_with_xtra(todos_handle, 'name', 'Charlie')
# print(f"Number of records in the table for 'Charlie': {num_records}")




def render_profile(profile):
    # Count the number of todo items for this profile
    todo_count = count_records_with_xtra(todos, 'profile_id', profile.id)  # Assuming todos_handle is defined

    # Set the visibility of the delete icon based on the todo count
    delete_icon_visibility = 'inline' if todo_count == 0 else 'none'

    """Render a profile item as an HTML list item."""
    # Create the delete button (trash can)
    delete_icon = A(
        '🗑',  # Trash can emoji
        hx_post=f"/profile/delete/{profile.id}",  # Change to POST for deletion
        hx_target=f'#profile-{profile.id}',  # Target the profile item to remove
        hx_swap='outerHTML',  # Update the profile list in the DOM
        style=f"cursor: pointer; display: {delete_icon_visibility};",  # Change cursor to pointer for delete action
        cls="delete-icon"  # Add a class for easy selection
    )

    # Create the active checkbox
    active_checkbox = Input(
        type="checkbox",
        name="active" if profile.active else None,  # Checkbox name based on active status
        checked=profile.active,  # Set checkbox state based on profile status
        hx_post=f"/toggle_active/{profile.id}",  # Endpoint to toggle the active status
        hx_target=f'#profile-{profile.id}',  # Target the profile item to update
        hx_swap='outerHTML',  # Update the checkbox in the DOM
        style="margin-right: 5px;"  # Add some margin
    )

    # Create the update form
    update_form = Form(
        Group(
            Input(type="text", name="name", value=profile.name, placeholder="Name", id=f"name-{profile.id}"),  # Input for name
            Input(type="email", name="email", value=profile.email, placeholder="Email", id=f"email-{profile.id}"),  # Input for email
            Input(type="tel", name="phone", value=profile.phone, placeholder="Phone", id=f"phone-{profile.id}"),  # Input for phone
            Button("Update", type="submit"),  # Update button
        ),
        hx_post=f"/profile/update/{profile.id}",  # Endpoint for updating the profile
        hx_target=f'#profile-{profile.id}',  # Target the profile item to update
        hx_swap='outerHTML',  # Replace the entire profile item
        style="display: none;",  # Initially hidden
        id=f'update-form-{profile.id}'  # Unique ID for the update form
    )

    # Create the title link with an onclick event to toggle the update form
    title_link = A(
        f"{profile.name} ({todo_count} Todo{'' if todo_count == 1 else 's'})",  # Display the profile name and todo count
        href="#",  # Prevent default link behavior
        hx_trigger="click",  # Trigger on click
        onclick=(
            "let li = this.closest('li'); "  # Get the closest <li> element
            "let updateForm = document.getElementById('update-form-" + str(profile.id) + "'); "  # Get the update form
            "if (updateForm.style.display === 'none' || updateForm.style.display === '') { "
            "    updateForm.style.display = 'block'; "  # Show the update form
            "    li.querySelectorAll('input[type=checkbox], .delete-icon, span, a').forEach(el => el.style.display = 'none'); "  # Hide checkbox, delete icon, email/phone, and title link
            "} else { "
            "    updateForm.style.display = 'none'; "  # Hide the update form
            "    li.querySelectorAll('input[type=checkbox], .delete-icon, span, a').forEach(el => el.style.display = 'inline'); "  # Show checkbox, delete icon, email/phone, and title link
            "}"
        )  # Toggle visibility
    )

    return Li(
        Div(
            active_checkbox,  # Include the active checkbox
            title_link,  # Use the updated title link
            Span(f" ({profile.email}, {profile.phone})", style="margin-left: 10px;"),  # Display email and phone
            delete_icon,  # Include the delete icon
            update_form,  # Include the hidden update form
            style="display: flex; align-items: center;"  # Flexbox for alignment
        ),
        id=f'profile-{profile.id}',  # Unique ID for the profile item
        style="list-style-type: none;"  # Style for the list item
    )

@rt('/profile', methods=['GET'])
def profile_app(request):
    """
    Handle the profile app GET request.
    """
    print("Entering profile_app function")
    logger.debug("Entering profile_app function")

    # Set the last_explore_choice to "Profiles"
    db["last_explore_choice"] = "Profiles"
    print("Set last_explore_choice to 'Profiles'")
    logger.info("Set last_explore_choice to 'Profiles'")

    # Set the last_visited_url to the current URL
    db["last_visited_url"] = request.url.path
    print(f"Set last_visited_url to '{request.url.path}'")
    logger.info(f"Set last_visited_url to '{request.url.path}'")

    # Retrieve the current profile name from the database
    current_profile_name = db.get("last_profile_name", "Profiles")  # Default to "Profiles" if not set
    print(f"Current profile name: {current_profile_name}")
    logger.debug(f"Current profile name: {current_profile_name}")

    response = Titled(
        f"{APP_NAME} / {current_profile_name} / Profiles",  # Title for the page including profile name
        get_profiles(),  # Call the function to retrieve and display profiles
        hx_ext='ws',  # Enable WebSocket extensions
        ws_connect='/ws',  # WebSocket connection endpoint
        data_theme="dark",  # Set the theme for the page
    )

    print("Exiting profile_app function")
    logger.debug("Exiting profile_app function")

    return response

def get_profiles():
    """Retrieve and display the list of profiles."""
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
    if not profile_name.strip():  # Check for empty profile name
        await chatq(
            "User tried to add an empty profile name. Respond with a brief, sassy comment about their attempt."
        )
        return ''  # Return empty string to prevent insertion

    # Create a new profile item
    new_profile = {
        "name": profile_name,
        "email": profile_email,
        "phone": profile_phone,
        "active": True,  # Default to active
    }

    # Insert the new profile into the database
    inserted_profile = profiles.insert(new_profile)

    prompt = (
        f"New profile added: '{profile_name}'. "
        "Brief, sassy comment or advice."
    )
    await chatq(prompt)  # Send prompt to chat queue

    return render_profile(inserted_profile)

@rt('/toggle_active/{profile_id}', methods=['POST'])
async def toggle_active(profile_id: int):
    """Toggle the active status of a profile item."""
    profile = profiles[profile_id]  # Get the profile item
    profile.active = not profile.active  # Toggle the active status
    updated_profile = profiles.update(profile)  # Update the profile item

    return render_profile(updated_profile)  # Return the updated profile rendering

@rt('/profile/delete/{profile_id}', methods=['POST'])
async def delete_profile(profile_id: int):
    """Delete a profile item."""
    profile = profiles[profile_id]  # Get the profile item
    profiles.delete(profile_id)  # Delete the profile item
    return ''  # Return an empty string to remove the item from the DOM
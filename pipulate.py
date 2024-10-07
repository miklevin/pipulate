import asyncio
import json
import re
from typing import List, Optional

import requests
from fasthtml.common import *
from starlette.concurrency import run_in_threadpool

# *******************************
# Styles and Configuration
# *******************************
# Application name and configuration settings
APP_NAME = ""                   # Controls a response "Name: " in the chat
MAX_LLM_RESPONSE_WORDS = 30     # Maximum number of words in LLM response
TYPING_DELAY = 0.05             # Delay for simulating typing effect
DEFAULT_LLM_MODEL = "llama3.2"  # Set the default LLaMA model

# Grid layout constants
GRID_LAYOUT = "70% 30%"

# Define the width for the menus
bw = "150px"
NAV_FILLER_WIDTH = "20%"        # Width for the filler in the navigation
PROFILE_MENU_WIDTH = f"{bw}"    # Width for the profile menu
ACTION_MENU_WIDTH = f"{bw}"     # Width for the action menu
EXPLORE_MENU_WIDTH = f"{bw}"    # Width for the explore menu
SEARCH_WIDTH = f"{bw}"          # Width for the search input

# Initialize IDs for menus
profile_id = "profile-id"       # Initialize the ID for the profile menu
action_id = "action-id"         # Initialize the ID for the action menu
explore_id = "explore-id"       # Initialize the ID for the explore menu

# Initialize conversation with a system message
conversation = [
    {
        "role": "system",
        "content": (
            f"You are a Pipulate free and open source AI SEO software with attitude. "
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
SHOW_EXPLORE_MENU = True  # Toggle for showing the explore menu
SHOW_ACTION_MENU = False   # Toggle for showing the action menu
SHOW_SEARCH = True         # Toggle for showing the search input

# *******************************
# How to Plug in New Apps
# *******************************
# To add a new app similar to Todo:
# 1. Create a new route in the main routing section (e.g., @rt('/newapp'))
# 2. Add a new menu item in the create_nav_menu function under the Explore menu
# 3. Create a render function for your app's items if needed
# 4. Add your app's main content creation logic in the create_main_content function
# 5. If your app needs a database table, add it to the fast_app call in the Application Setup section
#
# Example for adding a new "Notes" app:
# 1. Add route: 
#    @rt('/notes')
#    def notes_route(request):
#        return create_main_content(show_content=True)
#
# 2. In create_nav_menu function, add:
#    create_menu_item("Notes", "/notes", explore_id, is_traditional_link=True)
#
# 3. Create render function if needed:
#    def render_note(note):
#        return Li(
#            note.content,
#            id=f'note-{note.id}',
#            style="list-style-type: none;"
#        )
#
# 4. In create_main_content function, add:
#    Card(
#        H2("Notes"),
#        Ul(*[render_note(note) for note in notes()], id='notes-list'),
#        header=Form(
#            Group(
#                Input(placeholder="New note...", name="content"),
#                Button("Add Note", type="submit"),
#            ),
#            hx_post="/notes",
#            hx_swap="beforeend",
#            hx_target="#notes-list",
#        ),
#    ) if selected_explore == "Notes" else "",
#
# 5. In fast_app call, add:
#    notes={
#        "id": int,
#        "content": str,
#        "created_at": str,
#        "pk": "id"
#    }
#
# Additional considerations:
# - Ensure any new dependencies are imported at the top of the file
# - If your new app requires additional JavaScript, add it to the HTML template
# - For more complex apps, consider creating a separate file and importing the necessary components
# - Remember to handle any new routes in the main routing section of the application
# - If your app requires new API endpoints, add them using the appropriate HTTP methods (GET, POST, etc.)
# - For database operations, use the provided database abstraction layer (e.g., notes.insert, notes.update)
# - If your app needs real-time updates, consider using WebSocket connections similar to the chat interface

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
        # Log the error (you can replace print with your logging mechanism)
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
        hx_post=f"/toggle/{todo.id}",  # Endpoint to toggle the todo status
        hx_swap="outerHTML",  # Update the checkbox in the DOM
    )
    delete = A(
        '🗑',  # Changed to use the wastebasket emoji
        hx_delete=f'/{todo.id}',  # Endpoint to delete the todo
        hx_swap='outerHTML',  # Update the todo item in the DOM
        hx_target=f"#{tid}",  # Target the specific todo item
    )
    title_link = A(
        f"{todo.title} 😊",  # Title with smiley emoji
        href="#",  # Prevent default link behavior
        cls="todo-title",  # Class for styling
        hx_get=f'/edit/{todo.id}',  # Call the edit endpoint
        hx_target=f"#{tid}",  # Target the specific todo item
        hx_swap='outerHTML',  # Replace the outer HTML of the todo item
    )

    # Create the update form
    update_form = Form(
        Input(
            type="text",
            id=f"todo-title-{todo.id}",  # Unique ID for the input field
            value=todo.title,
            name="todo_title",  # Ensure this has a name attribute
            placeholder="Edit your todo...",
            style="flex: 1; padding-right: 10px;",
            hx_trigger="keyup[keyCode==13]"  # Trigger submission on Enter key
        ),
        Input(
            type="hidden",
            name="todo_id",  # Ensure this has a name attribute
            value=todo.id
        ),
        Button("Update", type="submit", style="align-self: center;"),
        style="display: flex; align-items: center;",
        hx_post=f"/update/{todo.id}",  # Ensure this matches the update route
        hx_target=f"#{tid}",  # Ensure this matches the ID of the todo item
        hx_swap="outerHTML"
    )

    return Li(
        delete,
        '\u00A0\u00A0',  # Non-breaking spaces between checkbox and wastebasket
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
app, rt, (store, Store), (todos, Todo) = fast_app(  # Unpack the tables directly
    "data/pipulate.db",  # Database file path
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
        "profile_id": str,  # Added profile_id to todos
        "pk": "id"  # Primary key for todos
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
            raise KeyError(key)  # Raise KeyError if not found

    def __setitem__(self, key, value):
        """Set an item in the store by key."""
        try:
            # Try to update existing item
            self.store.update({"key": key, "value": value})
        except NotFoundError:
            # If it doesn't exist, insert a new item
            self.store.insert({"key": key, "value": value})

    def __delitem__(self, key):
        """Delete an item from the store by key."""
        try:
            self.store.delete(key)  # Delete the item
        except NotFoundError:
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

def generate_menu_style(width: str) -> str:
    """Generate a common style for menu elements with a specified width."""
    return COMMON_MENU_STYLE + f"width: {width}; "

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
    """Create the navigation menu with explore, profile, and action dropdowns."""
    # Fetch the last selected items from the db
    selected_profile = db.get("last_profile_choice", "Profiles")  # Default to "Profiles"
    selected_explore = db.get("last_explore_choice", "Explore")  # Default to "Explore"
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
        # Define the profile menu
        profile_menu = Details(
            Summary(
                selected_profile,  # Display the selected profile
                style=generate_menu_style(PROFILE_MENU_WIDTH),
                id=profile_id,
            ),
            Ul(
                create_menu_item("Default", "/profile/Default", profile_id),
                create_menu_item("Profile 2", "/profile/Profile_2", profile_id),
                create_menu_item("Profile 3", "/profile/Profile_3", profile_id),
                create_menu_item("Profile 4", "/profile/Profile_4", profile_id),
                dir="rtl",  # Right-to-left direction
            ),
            cls="dropdown",  # Class for dropdown styling
        )
        nav_items.append(profile_menu)  # Add profile menu to nav items

    if SHOW_EXPLORE_MENU:
        # Define the explore menu
        explore_menu = Details(
            Summary(
                selected_explore,  # Display the selected explore item
                style=generate_menu_style(EXPLORE_MENU_WIDTH),
                id=explore_id,
            ),
            Ul(
                create_menu_item("Profiles", "/profiles", explore_id, is_traditional_link=True),
                create_menu_item("Todo Lists", "/todo", explore_id, is_traditional_link=True),
                # Add new apps here, following the pattern above
                # Example: create_menu_item("Notes", "/notes", explore_id, is_traditional_link=True),
                dir="rtl",  # Right-to-left direction
            ),
            cls="dropdown",  # Class for dropdown styling
        )
        nav_items.append(explore_menu)  # Add explore menu to nav items

    if SHOW_ACTION_MENU:
        # Define the action menu
        action_menu = Details(
            Summary(
                selected_action,  # Display the selected action
                style=generate_menu_style(ACTION_MENU_WIDTH),
                id=action_id,
            ),
            Ul(
                create_menu_item("Action 1", "/action/Action_1", action_id),
                create_menu_item("Action 2", "/action/Action_2", action_id),
                create_menu_item("Action 3", "/action/Action_3", action_id),
                create_menu_item("Action 4", "/action/Action_4", action_id),
                dir="rtl",  # Right-to-left direction
            ),
            cls="dropdown",  # Class for dropdown styling
        )
        nav_items.append(action_menu)  # Add action menu to nav items

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

        # Create the search input group
        search_group = Group(
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
        autofocus=True  # Autofocus the input
    )

# *******************************
# Site Navigation Main Endpoints
# *******************************
@rt('/')
@rt('/todo')
@rt('/profiles')
@rt('/organizations')
@rt('/projects')
def get(request):
    """
    Handle main page and specific page GET requests.
    
    This route handler is designed to trigger a full page reload when accessed.
    It's crucial to maintain this behavior for several reasons:
    
    1. State Reset: A full page reload ensures that the application state is 
       completely reset, preventing any stale data from persisting.
    
    2. Consistent User Experience: By reloading the entire page, we ensure that 
       all components are in sync with the current route, avoiding partial updates 
       that could lead to inconsistencies.
    
    3. Simplicity: Full page reloads simplify the mental model of the application, 
       making it easier to reason about the state at any given time.
    
    4. Avoiding HTMX Conflicts: While HTMX is used for dynamic updates within a page, 
       navigating between major sections of the app (like switching to the todo list) 
       is intentionally done with a full reload to avoid potential conflicts or 
       unexpected behaviors that could arise from partial page updates.

    By using this approach, we ensure that each main section of the application 
    starts with a clean slate, which is especially important for the todo list 
    and other major features.
    """
    path = request.url.path.strip('/')  # Get the path from the request
    show_content = path in ['todo', 'profiles', 'organizations', 'projects']  # Check if content should be shown
    selected_explore = path.capitalize() if show_content else "Explore"  # Set the selected explore item
    db["last_explore_choice"] = selected_explore  # Store the last explore choice in the database
    db["last_visited_url"] = request.url.path  # Update the last visited URL

    # Apply the profile filter if necessary
    current_profile_id = db.get("last_profile_choice", "default_profile")  # Get the current profile_id
    todos.xtra(profile_id=current_profile_id)  # Set the profile_id for the todos API

    return Titled(
        f"Pipulate - {selected_explore}",  # Title for the page
        create_main_content(show_content),  # Create the main content based on the path
        hx_ext='ws',  # Enable WebSocket extensions
        ws_connect='/ws',  # WebSocket connection endpoint
        data_theme="dark",  # Set the theme for the page
    )

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
    
    # Retrieve the current profile_id from the database, or use a default if none is set
    current_profile_id = db.get("last_profile_choice", "default_profile")  # Replace "default_profile" with your actual default value

    # Set the profile_id in the todos API to filter results
    todos.xtra(profile_id=current_profile_id)  # Filter todos by the current profile_id

    selected_explore = db.get("last_explore_choice", "Explore")  # Get the last explore choice

    return Container(
        nav_group,  # Add the navigation group to the container
        Grid(
            Div(
                Card(
                    H2(f"{selected_explore}"),  # Header for the selected explore item
                    Ul(*[render(todo) for todo in todos()], id='todo-list', style="padding-left: 0;"),  # Render todos
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
                    H2("Pipulate Chatbot"),  # Header for the chat section
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
                "Poke Todo List",  # Button to poke the todo list
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

async def create_menu_item_summary(title: str, style_width: str, item_id: str) -> Summary:
    """Create a menu item summary for menu selections."""
    return Summary(
        title,  # Title for the summary
        style=generate_menu_style(style_width),  # Apply generated style
        id=item_id,  # Set the ID for the summary
    )

async def handle_menu_selection(title: str, style_width: str, item_id: str, prompt_template: str) -> Summary:
    """Handle menu selection and generate summary content."""
    summary_content = await create_menu_item_summary(title, style_width, item_id)  # Create summary
    prompt = prompt_template.format(title=title)  # Format the prompt with the title
    await chatq(prompt)  # Send the prompt to the chat queue
    return summary_content  # Return the generated summary content

@rt('/explore/{explore_id}')
async def explore_menu(explore_id: str):
    """Handle explore menu selection and record the choice."""
    selected_item = explore_id.replace('_', ' ')  # Format the selected item
    
    # Record the explore choice in the db
    db["last_explore_choice"] = selected_item  # Store the last explore choice

    summary_content = await create_menu_item_summary(selected_item, EXPLORE_MENU_WIDTH, "explore-id")  # Create summary content
    
    prompt = "Respond about '{title}', keeping it brief, under 20 words."  # Prompt for the chat
    await chatq(prompt.format(title=selected_item))  # Send the prompt to the chat queue

    # Update the selected menu indicator
    return [
        summary_content  # Return the summary content
    ]

@rt('/profile/{profile_id}')
def profile_menu_handler(request, profile_id: str):
    """Handle profile menu selection and record the choice."""
    selected_item = profile_id.replace('_', ' ').title()  # Format the selected profile_id
    db["last_profile_choice"] = selected_item  # Store the last profile choice

    # Retrieve the last visited URL from the database
    last_visited_url = db.get("last_visited_url", "/")  # Default to home if not set

    # Return a redirect response to the last visited URL
    return Redirect(last_visited_url)  # Use a redirect to the last visited URL

@rt('/action/{action_id}')
async def action_menu(action_id: str):
    """Handle action menu selection and record the choice."""
    selected_item = action_id.replace('_', ' ')  # Format the selected item
    
    # Record the action choice in the db
    db["last_action_choice"] = selected_item  # Store the last action choice

    return await handle_menu_selection(
        selected_item,
        ACTION_MENU_WIDTH,
        "action-id",
        "Perform '{title}' and respond briefly, under 20 words."
    )

@rt('/search', methods=['POST'])
async def search(nav_input: str):
    """Handle search input."""
    prompt = (
        f"The user searched for: '{nav_input}'. "
        "Respond briefly acknowledging the search."
    )
    await chatq(prompt)  # Send the prompt to the chat queue
    return ''  # Return empty response

@rt('/poke')
async def poke():
    """Handle poking the todo list for a response."""
    response = await run_in_threadpool(
        chat_with_ollama,
        model,
        [
            {
                "role": "system",
                "content": "You are a sassy Todo List. Respond briefly to being poked.",
            },
            {
                "role": "user",
                "content": "You've been poked.",
            },
        ],
    )
    return Div(f"{APP_NAME}{response}", id='msg-list', cls='fade-in', style=MATRIX_STYLE)  # Return the response

# *******************************
# Todo App Endpoints
# *******************************
@rt('/todo')
async def post_todo(todo: Todo):
    """Create a new todo item."""
    if not todo.title.strip():  # Check for empty title
        # Empty todo case
        await chatq(
            "User tried to add an empty todo. Respond with a brief, sassy comment about their attempt."
        )
        return ''  # Return empty string to prevent insertion

    # Non-empty todo case
    # Retrieve the current profile_id from the database, or use a default if none is set
    current_profile_id = db.get("last_profile_choice", "default_profile")  # Replace "default_profile" with your actual default value

    # Set the profile_id in the todos API to filter results
    todos.xtra(profile_id=current_profile_id)  # Filter todos by the current profile_id

    # Now, when you retrieve todos, it will only show items for the current profile
    todo_items = todos()  # Fetch the filtered todo items

    # Create a new todo item with the profile_id included
    todo.profile_id = current_profile_id  # Set the profile_id for the new todo
    inserted_todo = todos.insert(todo)  # Insert the new todo

    prompt = (
        f"New todo: '{todo.title}'. "
        "Brief, sassy comment or advice."
    )
    await chatq(prompt)  # Send prompt to chat queue

    return render(inserted_todo), todo_mk_input()  # Return the rendered todo and input field

@rt('/{tid}')
async def delete(tid: int):
    """Delete a todo item."""
    todo = todos[tid]  # Get the todo item before deleting it
    todos.delete(tid)  # Delete the todo item
    prompt = (
        f"Todo '{todo.title}' deleted. "
        "Brief, sassy reaction."
    )
    await chatq(prompt)  # Send prompt to chat queue
    return ''  # Return an empty string to remove the item from the DOM

@rt('/toggle/{tid}')
async def toggle(tid: int):
    """Update the status of a todo item."""
    todo = todos[tid]  # Get the todo item
    old_status = "Done" if todo.done else "Not Done"  # Determine old status
    todo.done = not todo.done  # Toggle the done status
    new_status = "Done" if todo.done else "Not Done"  # Determine new status
    updated_todo = todos.update(todo)  # Update the todo item

    prompt = (
        f"Todo '{todo.title}' toggled from {old_status} to {new_status}. "
        f"Brief, sassy comment mentioning '{todo.title}'."
    )
    await chatq(prompt)  # Send prompt to chat queue

    return Input(
        type="checkbox",
        name="english" if updated_todo.done else None,  # Checkbox name based on completion status
        checked=updated_todo.done,  # Set checkbox state based on todo status
        hx_post=f"/toggle/{updated_todo.id}",  # Endpoint to toggle the todo status
        hx_swap="outerHTML",  # Update the checkbox in the DOM
    )

@rt('/edit/{todo_id}', methods=['GET'])
async def edit_todo(todo_id: str):
    """Return a form for editing the todo item."""
    todo_item = todos[todo_id]
    if not todo_item:
        return "Todo item not found", 404

    form = Form(
        Group(
            Input(
                type="text",
                value=todo_item.title,
                name="todo_title",
                placeholder="Edit your todo...",
                style="flex: 1; padding-right: 10px;"
            ),
            Input(
                type="hidden",
                name="todo_id",
                value=todo_id
            ),
            Button("Update", type="submit", style="align-self: center;"),
            style="display: flex; align-items: center;"
        ),
        hx_post=f"/update/{todo_id}",
        hx_target=f"#todo-{todo_id}",
        hx_swap="outerHTML"
    )

    return Div(form)

@rt('/update/{todo_id}', methods=['POST'])
async def update_todo(todo_id: int):
    """Update the todo item with the given ID."""
    # Get the data from the request
    form_data = await request.form()  # Get the form data
    title = form_data.get('todo_title')  # Get the title from the form data

    if not title:
        return "Title cannot be empty", 400  # Handle empty title case

    # Logic to update the todo item in the database
    todo_item = db.get(todo_id)  # Retrieve the existing todo item
    if not todo_item:
        return "Todo item not found", 404  # Handle case where todo item does not exist

    # Update the title of the todo item
    todo_item.title = title
    db.update(todo_item)  # Save the updated todo item back to the database

    # Return the updated title wrapped in an anchor tag
    return A(todo_item.title, href="#", hx_get=f"/edit/{todo_id}", hx_target=f"#todo-{todo_id}", hx_swap="outerHTML")

# *******************************
# Streaming WebSocket Functions
# *******************************

# WebSocket users
users = {}  # Dictionary to keep track of connected users

async def on_conn(ws, send):
    """Handle WebSocket connection."""
    users[str(id(ws))] = send  # Add the new user to the users dictionary
    # Get the last explore choice from the db
    selected_explore = db.get("last_explore_choice", "Explore")  # Retrieve last explore choice

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
                    f"{APP_NAME}{response}",  # Display the response
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
                        f"{APP_NAME}{partial_response}",  # Display partial response
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
                        f"{APP_NAME}{partial_response}",  # Display partial response
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
# Activate the Application
# *******************************

# Add this line to set the model
model = get_best_model()  # Retrieve the best model
serve()  # Start the application
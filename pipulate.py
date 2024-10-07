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

# Initialize conversation
conversation = [
    {
        "role": "system",
        "content": (
            f"You are a Todo App with attitude. "
            f"Be sassy but helpful in under {MAX_LLM_RESPONSE_WORDS} words, "
            "and without leading and trailing quotes."
        ),
    },
]

# Styles
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
SHOW_PROFILE_MENU = False
SHOW_EXPLORE_MENU = True
SHOW_ACTION_MENU = False
SHOW_SEARCH = False

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
            parse_version(base_version),
            1 if version == 'latest' else 0,
            parse_version(version),
        )

    return max(llama_models, key=key_func)

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
        return response.json()['message']['content']
    except requests.exceptions.HTTPError as http_err:
        return f"HTTP error occurred: {http_err}"  # Return an error message
    except requests.exceptions.ConnectionError as conn_err:
        return f"Connection error occurred: {conn_err}"  # Return an error message
    except requests.exceptions.Timeout as timeout_err:
        return f"Timeout error occurred: {timeout_err}"  # Return an error message
    except requests.exceptions.RequestException as req_err:
        return f"An error occurred: {req_err}"  # Return an error message

# *******************************
# Todo Render Function (Must come before Application Setup)
# *******************************

def render(todo):
    """Render a todo item as an HTML list item."""
    tid = f'todo-{todo.id}'
    checkbox = Input(
        type="checkbox",
        name="english" if todo.done else None,
        checked=todo.done,
        hx_post=f"/toggle/{todo.id}",
        hx_swap="outerHTML",
    )
    delete = A(
        '🗑',  # Changed to use the wastebasket emoji
        hx_delete=f'/{todo.id}',
        hx_swap='outerHTML',
        hx_target=f"#{tid}",
    )
    return Li(
        delete,
        '\u00A0\u00A0',  # Non-breaking spaces between checkbox and wastebasket
        checkbox,
        todo.title,
        id=tid,
        cls='done' if todo.done else '',
        style="list-style-type: none;"
    )

# *******************************
# Application Setup
# *******************************

# Unpack the returned tuple from fast_app
app, rt, (store, Store), (todos, Todo) = fast_app(  # Unpack the tables directly
    "data/pipulate.db",
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
        "pk": "id"
    },
)

# *******************************
# DictLikeDB Persistence Convenience Wrapper
# *******************************
class DictLikeDB:
    def __init__(self, store, Store):
        self.store = store
        self.Store = Store

    def __getitem__(self, key):
        try:
            return self.store[key].value
        except NotFoundError:
            raise KeyError(key)

    def __setitem__(self, key, value):
        try:
            # Try to update existing item
            self.store.update({"key": key, "value": value})
        except NotFoundError:
            # If it doesn't exist, insert a new item
            self.store.insert({"key": key, "value": value})

    def __delitem__(self, key):
        try:
            self.store.delete(key)
        except NotFoundError:
            raise KeyError(key)

    def __contains__(self, key):
        return key in self.store

    def __iter__(self):
        for item in self.store():
            yield item.key

    def items(self):
        for item in self.store():
            yield item.key, item.value

    def keys(self):
        return list(self)

    def values(self):
        for item in self.store():
            yield item.value

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

# Create the wrapper
db = DictLikeDB(store, Store)

# *******************************
# Site Navigation
# *******************************

def generate_menu_style(width: str) -> str:
    """Generate a common style for menu elements with a specified width."""
    return COMMON_MENU_STYLE + f"width: {width}; "

def create_menu_item(title, link, summary_id, is_traditional_link=False):
    """Create a menu item."""
    if is_traditional_link:
        return Li(
            A(
                title,
                href=link,
                cls="menu-item",
            ),
            style="text-align: center;"
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
            ),
            style="text-align: center;"
        )

def create_nav_menu():
    """Create the navigation menu with explore, profile, and action dropdowns."""
    # Fetch the last selected items from the db
    selected_profile = db.get("last_profile_choice", "Profiles")
    selected_explore = db.get("last_explore_choice", "Explore")
    selected_action = db.get("last_action_choice", "Actions")

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

    nav_items = [filler_item]

    if SHOW_PROFILE_MENU:
        # Define the profile menu
        profile_menu = Details(
            Summary(
                selected_profile,
                style=generate_menu_style(PROFILE_MENU_WIDTH),
                id=profile_id,
            ),
            Ul(
                create_menu_item("Default", "/profile/Default", profile_id),
                create_menu_item("Profile 2", "/profile/Profile_2", profile_id),
                create_menu_item("Profile 3", "/profile/Profile_3", profile_id),
                create_menu_item("Profile 4", "/profile/Profile_4", profile_id),
                dir="rtl",
            ),
            cls="dropdown",
        )
        nav_items.append(profile_menu)

    if SHOW_EXPLORE_MENU:
        # Define the explore menu
        explore_menu = Details(
            Summary(
                selected_explore,
                style=generate_menu_style(EXPLORE_MENU_WIDTH),
                id=explore_id,
            ),
            Ul(
                create_menu_item("Profiles", "/profiles", explore_id, is_traditional_link=True),
                create_menu_item("Todo Lists", "/todo", explore_id, is_traditional_link=True),
                create_menu_item("Organizations", "/organizations", explore_id, is_traditional_link=True),
                create_menu_item("Projects", "/projects", explore_id, is_traditional_link=True),
                dir="rtl",
            ),
            cls="dropdown",
        )
        nav_items.append(explore_menu)

    if SHOW_ACTION_MENU:
        # Define the action menu
        action_menu = Details(
            Summary(
                selected_action,
                style=generate_menu_style(ACTION_MENU_WIDTH),
                id=action_id,
            ),
            Ul(
                create_menu_item("Action 1", "/action/Action_1", action_id),
                create_menu_item("Action 2", "/action/Action_2", action_id),
                create_menu_item("Action 3", "/action/Action_3", action_id),
                create_menu_item("Action 4", "/action/Action_4", action_id),
                dir="rtl",
            ),
            cls="dropdown",
        )
        nav_items.append(action_menu)

    if SHOW_SEARCH:
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

        search_group = Group(
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
        )
        nav_items.append(search_group)

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
        autofocus=True
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
    path = request.url.path.strip('/')
    show_content = path in ['todo', 'profiles', 'organizations', 'projects']
    selected_explore = path.capitalize() if show_content else "Explore"
    db["last_explore_choice"] = selected_explore
    
    return Titled(
        f"Pipulate - {selected_explore}",
        create_main_content(show_content),
        hx_ext='ws',
        ws_connect='/ws',
        data_theme="dark",
    )

def create_main_content(show_content=False):
    """Create the main content for all routes."""
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
    selected_explore = db.get("last_explore_choice", "Explore")

    return Container(
        nav_group,
        Grid(
            Div(
                Card(
                    H2(f"{selected_explore}"),
                    Ul(*[render(todo) for todo in todos()], id='todo-list', style="padding-left: 0;"),
                    header=Form(
                        Group(
                            todo_mk_input(),
                            Button("Add", type="submit"),
                        ),
                        hx_post=f"/{selected_explore.lower()}",
                        hx_swap="beforeend",
                        hx_target="#todo-list",
                    ),
                ) if selected_explore == "Todo" else "",
                id="content-container",
            ),
            Div(
                Card(
                    H2("Chat Interface"),
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
                "Poke Todo List",
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

async def create_menu_item_summary(title: str, style_width: str, item_id: str) -> Summary:
    """Create a menu item summary for menu selections."""
    return Summary(
        title,
        style=generate_menu_style(style_width),
        id=item_id,
    )

async def handle_menu_selection(title: str, style_width: str, item_id: str, prompt_template: str) -> Summary:
    """Handle menu selection and generate summary content."""
    summary_content = await create_menu_item_summary(title, style_width, item_id)
    prompt = prompt_template.format(title=title)
    await chatq(prompt)
    return summary_content

@rt('/explore/{explore_id}')
async def explore_menu(explore_id: str):
    """Handle explore menu selection and record the choice."""
    selected_item = explore_id.replace('_', ' ')
    
    # Record the explore choice in the db
    db["last_explore_choice"] = selected_item

    summary_content = await create_menu_item_summary(selected_item, EXPLORE_MENU_WIDTH, "explore-id")
    
    prompt = "Respond about '{title}', keeping it brief, under 20 words."
    await chatq(prompt.format(title=selected_item))

    # Update the selected menu indicator
    return [
        summary_content
    ]

@rt('/profile/{profile_id}')
async def profile_menu(profile_id: str):
    """Handle profile menu selection and record the choice."""
    selected_item = profile_id.replace('_', ' ').title()  # Use the actual profile_id
    db["last_profile_choice"] = selected_item
    return await handle_menu_selection(
        selected_item,
        PROFILE_MENU_WIDTH,
        "profile-id",
        "Respond mentioning '{title}' in your reply, keeping it brief, under 20 words."
    )

@rt('/action/{action_id}')
async def action_menu(action_id: str):
    """Handle action menu selection and record the choice."""
    selected_item = action_id.replace('_', ' ')
    
    # Record the action choice in the db
    db["last_action_choice"] = selected_item

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
    await chatq(prompt)
    return ''

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
    return Div(f"{APP_NAME}{response}", id='msg-list', cls='fade-in', style=MATRIX_STYLE)

# *******************************
# Todo App Endpoints
# *******************************
@rt('/todo')
async def post_todo(todo: Todo):
    """Create a new todo item."""
    if not todo.title.strip():
        # Empty todo case
        await chatq(
            "User tried to add an empty todo. Respond with a brief, sassy comment about their attempt."
        )
        return ''  # Return empty string to prevent insertion

    # Non-empty todo case
    inserted_todo = todos.insert(todo)

    prompt = (
        f"New todo: '{todo.title}'. "
        "Brief, sassy comment or advice."
    )
    await chatq(prompt)

    return render(inserted_todo), todo_mk_input()

@rt('/{tid}')
async def delete(tid: int):
    """Delete a todo item."""
    todo = todos[tid]  # Get the todo item before deleting it
    todos.delete(tid)
    prompt = (
        f"Todo '{todo.title}' deleted. "
        "Brief, sassy reaction."
    )
    await chatq(prompt)
    return ''  # Return an empty string to remove the item from the DOM

@rt('/toggle/{tid}')
async def toggle(tid: int):
    """Update the status of a todo item."""
    todo = todos[tid]
    old_status = "Done" if todo.done else "Not Done"
    todo.done = not todo.done
    new_status = "Done" if todo.done else "Not Done"
    updated_todo = todos.update(todo)

    prompt = (
        f"Todo '{todo.title}' toggled from {old_status} to {new_status}. "
        f"Brief, sassy comment mentioning '{todo.title}'."
    )
    await chatq(prompt)

    return Input(
        type="checkbox",
        name="english" if updated_todo.done else None,
        checked=updated_todo.done,
        hx_post=f"/toggle/{updated_todo.id}",
        hx_swap="outerHTML",
    )

# *******************************
# Streaming WebSocket Functions
# *******************************

# WebSocket users
users = {}

async def on_conn(ws, send):
    """Handle WebSocket connection."""
    users[str(id(ws))] = send
    # Get the last explore choice from the db
    selected_explore = db.get("last_explore_choice", "Explore")

    # Create a personalized welcome message
    welcome_prompt = f"Say 'Welcome to {selected_explore}' and add a brief, friendly greeting related to this area. Keep it under 25 words."

    # Queue the welcome message when a new connection is established
    await chatq(welcome_prompt)

def on_disconn(ws):
    """Handle WebSocket disconnection."""
    users.pop(str(id(ws)), None)

async def chatq(message: str):
    """Queue a message for the chat stream."""
    # Create a task for streaming the chat response without blocking
    asyncio.create_task(stream_chat(message))

async def stream_chat(prompt: str, quick: bool = False):
    """Generate and stream an AI response to users."""
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
                    f"{APP_NAME}{response}",
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
                        f"{APP_NAME}{partial_response}",
                        id='msg-list',
                        cls='fade-in',
                        style=MATRIX_STYLE,
                        _=f"this.scrollIntoView({{behavior: 'smooth'}});",
                    )
                )
            await asyncio.sleep(TYPING_DELAY)  # Use the constant for delay

@app.ws('/ws', conn=on_conn, disconn=on_disconn)
async def ws(msg: str):
    """Handle WebSocket messages."""
    if msg:
        # Disable the input group
        disable_input_group = mk_chat_input_group(disabled=True, value=msg, autofocus=False)
        disable_input_group.attrs['hx_swap_oob'] = "true"
        for u in users.values():
            await u(disable_input_group)

        # Process the message and generate response
        global conversation
        conversation.append({"role": "user", "content": msg})

        # Start streaming response
        response = await run_in_threadpool(chat_with_ollama, model, conversation)
        conversation.append({"role": "assistant", "content": response})

        # Simulate typing effect (AI response remains green)
        words = response.split()
        for i in range(len(words)):
            partial_response = " ".join(words[: i + 1])
            for u in users.values():
                await u(
                    Div(
                        f"{APP_NAME}{partial_response}",
                        id='msg-list',
                        cls='fade-in',
                        style=MATRIX_STYLE,
                        _=f"this.scrollIntoView({{behavior: 'smooth'}});",
                    )
                )
            await asyncio.sleep(TYPING_DELAY)  # Use the constant for delay

        # Re-enable the input group
        enable_input_group = mk_chat_input_group(disabled=False, value='', autofocus=True)
        enable_input_group.attrs['hx_swap_oob'] = "true"
        for u in users.values():
            await u(enable_input_group)

# *******************************
# Activate the Application
# *******************************

# Add this line to set the model
model = get_best_model()
serve()
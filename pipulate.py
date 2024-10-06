import asyncio
import json
import re
from typing import Awaitable, Callable, List, Optional

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
    """Retrieve the best available LLaMA model or default to 'llama3.2'.

    This function fetches the list of available models from the Ollama API, filters for models
    that start with 'llama', and selects the best one based on versioning. If no suitable model
    is found or if an error occurs during the request, it defaults to 'llama3.2'.

    Returns:
        str: The name of the best available LLaMA model, or 'llama3.2' if no models are available
             or an error occurs.
    """
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
    """Interact with the Ollama model to generate a response.

    Args:
        model (str): The model to use for generating the response.
        messages (list): A list of messages to send to the model.

    Returns:
        str: The generated response from the model, or an error message if the request fails.
    """
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
    """Render a todo item as an HTML list item.

    This function creates an HTML representation of a todo item, including a checkbox for its status,
    a delete button, and the todo title.

    Args:
        todo (Todo): The todo item to be rendered.

    Returns:
        Li: An HTML list item containing the rendered todo item.
    """
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
        style="list-style-type: none;"  # Add this line
    )


# *******************************
# Application Setup
# *******************************

app, rt, todos, Todo = fast_app(
    "data/todo.db",
    ws_hdr=True,
    live=True,
    render=render,
    id=int,
    title=str,
    done=bool,
    pk="id",
)

# *******************************
# Site Navigation
# *******************************


def create_nav_menu(selected_profile="Profiles", selected_action="Actions"):
    """Create the navigation menu with a filler item, chat, and action dropdowns."""
    # Use generate_menu_style for the common style
    profile_menu_style = generate_menu_style(PROFILE_MENU_WIDTH)
    action_menu_style = generate_menu_style(ACTION_MENU_WIDTH)

    def create_menu_item(title, hx_get, summary_id):
        """Create a menu item."""
        return Li(
            A(
                title,
                hx_get=hx_get,  # Keep the original hx_get
                hx_target=f"#{summary_id}",
                hx_swap="outerHTML",
                hx_trigger="click",
                hx_push_url="false",  # Prevent URL changes
                cls="menu-item",
            ),
            style="text-align: center;"  # Add the class for text alignment to the Li element
        )

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

    # *******************************
    # Menu Configuration
    # *******************************

    # Instructions for Adding Menu Items:
    # To add a new menu item (for both profile and action menus):
    # 1. Create a new MenuItem instance with the title, endpoint, and corresponding ID.
    # 2. Ensure the endpoint corresponds to a defined route in the application (e.g., /profile/{profile_name} or /action/{action_id}).
    # 3. Initialize a new ID for the menu if adding a new menu type (e.g., profile_id = "new-profile-id").
    # 4. If adding new constants (like widths), ensure they are declared as global variables if they need to be accessed outside this scope.
    # Example for Profile Menu:
    # new_profile_item = MenuItem("New Profile", "/profile/New_Profile", "profile-id")
    # profile_menu_items.append(new_profile_item)
    # Example for Action Menu:
    # new_action_item = MenuItem("New Action", "/action/New_Action", "action-id")
    # action_menu_items.append(new_action_item)

    # Define the explore menu
    explore_menu = Details(
        Summary(
            "Explore",
            style=generate_menu_style(EXPLORE_MENU_WIDTH),
            id=explore_id,
        ),
        Ul(
            create_menu_item("Organizations", "/explore/organizations", explore_id),
            create_menu_item("Projects", "/explore/projects", explore_id),
            dir="rtl",
        ),
        cls="dropdown",
    )

    # Define the profile menu
    profile_menu = Details(
        Summary(
            selected_profile,
            style=generate_menu_style(PROFILE_MENU_WIDTH),  # Directly use the function here
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

    # Define the action menu
    action_menu = Details(
        Summary(
            selected_action,
            style=generate_menu_style(ACTION_MENU_WIDTH),  # Directly use the function here
            id=action_id,
        ),
        Ul(
            create_menu_item("Action 1", "/action/1", action_id),
            create_menu_item("Action 2", "/action/2", action_id),
            create_menu_item("Action 3", "/action/3", action_id),
            create_menu_item("Action 4", "/action/4", action_id),
            dir="rtl",
        ),
        cls="dropdown",
    )

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

    nav = Div(
        filler_item,  # Add the filler item first
        explore_menu,
        profile_menu,
        action_menu,
        search_group,
        style=(
            "align-items: center; "
            "display: flex; "
            "gap: 8px; "  # Add gap between items
            "width: 100%; "  # Ensure the nav takes full width
            "justify-content: flex-end; "
        ),
    )

    return nav


def mk_chat_input_group(disabled=False, value='', autofocus=True):
    """Create a chat input group with a message input and a send button.

    This function generates a group of HTML elements for user input in the chat interface,
    including an input field for messages and a button to send the message.

    Args:
        disabled (bool, optional): Whether the input group should be disabled. Defaults to False.
        value (str, optional): The initial value for the message input. Defaults to an empty string.
        autofocus (bool, optional): Whether to autofocus the message input. Defaults to True.

    Returns:
        Group: An HTML group containing the message input and send button.
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
# Feels out of place, but necessary here for reuse by main endpoints
def todo_mk_input():
    """Create an input field for adding a new todo item.

    This function generates an HTML input element that allows users to enter a new todo item.

    Returns:
        Input: An HTML input element configured for adding a new todo.
    """
    return Input(
        placeholder='Add a new item',
        id='title',
        hx_swap_oob='true',
        autofocus=True  # Add this line
    )


# *******************************
# Site Navigation Main Endpoints
# *******************************
@rt('/')
def get():
    """Handle the main page GET request for the Pipulate Todo App.

    This function generates the HTML content for the main page of the application,
    including the navigation menu, todo list, and chat interface. It constructs
    the layout using various HTML components and returns the complete page structure.

    Returns:
        Titled: A Titled component containing the main page content, including
        the navigation menu, todo list, chat interface, and a button to poke the todo list.
    """
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

    return Titled(
        "Pipulate Todo App",
        Container(
            nav_group,
            Grid(
                Div(
                    Card(
                        H2("Todo List"),
                        Ul(*[render(todo) for todo in todos()], id='todo-list', style="padding-left: 0;"),  # Add style here
                        header=Form(
                            Group(
                                todo_mk_input(),
                                Button("Add", type="submit"),
                            ),
                            hx_post="/todo",
                            hx_swap="beforeend",
                            hx_target="#todo-list",
                        ),
                    ),
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
                    "grid-template-columns: 2fr 1fr; "
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
        ),
        hx_ext='ws',
        ws_connect='/ws',
        data_theme="dark",
    )


async def create_menu_item(title: str, style_width: str, item_id: str) -> Summary:
    """Create a menu item summary for menu selections.

    Args:
        title (str): The title to be displayed in the summary.
        style_width (str): The width for the menu style.
        item_id (str): The ID for the summary element.

    Returns:
        Summary: The generated summary content.
    """
    return Summary(
        title,
        style=generate_menu_style(style_width),
        id=item_id,
    )


async def handle_menu_selection(title: str, style_width: str, item_id: str, prompt_template: str) -> Summary:
    """Handle menu selection and generate summary content.

    Args:
        title (str): The title to be displayed in the summary.
        style_width (str): The width for the menu style.
        item_id (str): The ID for the summary element.
        prompt_template (str): The template for the prompt message.

    Returns:
        Summary: The generated summary content.
    """
    summary_content = await create_menu_item(title, style_width, item_id)
    prompt = prompt_template.format(title=title)
    await chatq(prompt)
    return summary_content


@rt('/explore/{explore_id}')
async def profile_menu(explore_id: str):
    """Handle explore menu selection."""
    selected_item = explore_id.replace('_', ' ').title()  # Use the actual profile_id
    return await handle_menu_selection(
        selected_item,
        EXPLORE_MENU_WIDTH,
        "explore-id",
        "Respond mentioning '{title}' in your reply, keeping it brief, under 20 words."
    )


@rt('/profile/{profile_id}')
async def profile_menu(profile_id: str):
    """Handle profile menu selection."""
    selected_item = profile_id.replace('_', ' ').title()  # Use the actual profile_id
    return await handle_menu_selection(
        selected_item,
        PROFILE_MENU_WIDTH,
        "profile-id",
        "Respond mentioning '{title}' in your reply, keeping it brief, under 20 words."
    )


@rt('/action/{action_id}')
async def perform_action(action_id: str):
    """Handle action menu selection."""
    selected_item = f"Action {action_id}"
    return await handle_menu_selection(
        selected_item,
        ACTION_MENU_WIDTH,
        "action-id",
        "You selected '{title}'. Respond cleverly, mentioning '{title}' in your reply. Be brief and sassy."
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
    """Handle poking the todo list for a response.

    This function sends a prompt to the chat model to generate a brief response
    when the todo list is "poked." It serves as a placeholder for quick (non-streaming)
    information display in the chat interface.

    Returns:
        Div: An HTML Div element containing the response from the chat model,
        formatted for display in the message list.
    """
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
    """Create a new todo item.

    This endpoint handles the addition of a new todo item to the list. 
    If the provided title is empty, it responds with a sassy comment 
    about the attempt to add an empty todo. Otherwise, it inserts the 
    new todo into the database and generates a brief, sassy comment 
    about the new todo item.

    Args:
        todo (Todo): The todo item to be added.

    Returns:
        str: The rendered HTML for the inserted todo item and the input field for a new todo.
    """
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
    """Delete a todo item.

    This endpoint handles the removal of a specific todo item identified
    by its unique ID (tid). A message is generated upon deletion.

    Args:
        tid (int): The unique ID of the todo item to be deleted.

    Returns:
        str: An empty string to remove the item from the DOM.
    """
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
    """Update the status of a todo item.

    This endpoint handles toggling the 'done' status of a specific todo
    item identified by its unique ID (tid). A message is generated
    reflecting the change in status.

    Args:
        tid (int): The unique ID of the todo item to be toggled.

    Returns:
        Input: An HTML input element representing the updated status of the todo item.
    """
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


def on_conn(ws, send):
    """Handle WebSocket connection."""
    users[str(id(ws))] = send


def on_disconn(ws):
    """Handle WebSocket disconnection."""
    users.pop(str(id(ws)), None)


async def chatq(message: str):
    """Queue a message for the chat stream.

    This function creates an asyncio task to send a message to the chat interface.

    Args:
        message (str): The message to be queued for the chat stream.

    Returns:
        None
    """
    # Create a task for streaming the chat response without blocking
    asyncio.create_task(stream_chat(message))


async def stream_chat(prompt: str, quick: bool = False):
    """Generate and stream an AI response to users.

    If quick is True, send the entire response at once. Otherwise, stream the response word by word.

    Args:
        prompt (str): The input message to generate a response for.
        quick (bool, optional): If True, sends the entire response at once. Defaults to False.

    Returns:
        None
    """
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

# Choose the best available model
model = get_best_model()

serve()

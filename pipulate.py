import asyncio
import json
import re
from dataclasses import dataclass
from typing import Awaitable, Callable

import requests
from fasthtml.common import *
from starlette.concurrency import run_in_threadpool

# Configuration and Constants
MAX_LLM_RESPONSE_WORDS = 30
NAV_FILLER_WIDTH = "30%"
SEARCH_WIDTH = "20%"
PROFILE_MENU_WIDTH = "200px"  # Width for the chat interface
ACTION_MENU_WIDTH = "150px"      # Width for the action menu
APP_NAME = ""
TYPING_DELAY = 0.05  # Delay for simulating typing effect

# Styles
MATRIX_STYLE = (
    "color: #00ff00; text-shadow: 0 0 5px #00ff00; "
    "font-family: 'Courier New', monospace;"
)
USER_STYLE = (
    "color: #ffff00; text-shadow: 0 0 5px #ffff00; "
    "font-family: 'Courier New', monospace;"
)

# Initialize conversation
conversation = [
    {
        "role": "system",
        "content": f"You are a Todo App with attitude. Be sassy but helpful in under {MAX_LLM_RESPONSE_WORDS} words, and without leading and trailing quotes.",
    },
]

# Active users connected via WebSocket
users = {}


@dataclass
class Chatter:
    send: Callable[[str], Awaitable[None]]
    update: Callable[[str], Awaitable[None]]
    finish: Callable[[], Awaitable[None]]


def limit_llm_response(response: str) -> str:
    """Limit the LLM response to a maximum number of words."""
    words = response.split()
    return ' '.join(words[:MAX_LLM_RESPONSE_WORDS])


def parse_version(version_string):
    """Parse a version string into a list of integers and strings for comparison."""
    return [int(x) if x.isdigit() else x for x in re.findall(r'\d+|\D+', version_string)]


def get_best_llama_model(models):
    """Select the best available LLaMA model from the list of models."""
    llama_models = [model for model in models if model.lower().startswith('llama')]
    if not llama_models:
        return None

    def key_func(model):
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


def get_available_models():
    """Retrieve the list of available models from the Ollama API.

    Returns:
        list: A list of available model names, or an empty list if an error occurs.
    """
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        response.raise_for_status()  # Raise an error for bad responses (4xx and 5xx)
        return [model['name'] for model in response.json()['models']]
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")  # Log the HTTP error
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")  # Log connection errors
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")  # Log timeout errors
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred: {req_err}")  # Log any other request-related errors
    return []  # Return an empty list if an error occurs


def get_best_model():
    """Get the best available model or default to 'llama2'."""
    available_models = get_available_models()
    return get_best_llama_model(available_models) or (available_models[0] if available_models else "llama2")


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


def render(todo):
    """Render a todo item."""
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


# from todo_app import todos, Todo, mk_input as todo_mk_input
def todo_mk_input():
    return Input(placeholder='Add a new item',
                 id='title',
                 hx_swap_oob='true',
                 autofocus=True)  # Add this line


# Define a function to create the input group
def mk_input_group(disabled=False, value='', autofocus=True):
    """Create the chat input group."""
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


def create_nav_menu(selected_chat="Profiles", selected_action="Actions"):
    """Create the navigation menu with a filler item, chat, and action dropdowns."""
    common_style = (
        "font-size: 1rem; height: 32px; line-height: 32px; "
        "display: inline-flex; align-items: center; justify-content: center; "
        "margin: 0 2px; border-radius: 16px; padding: 0 0.6rem;"
    )

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
            )
        )

    chat_summary_id = "chat-summary"
    action_summary_id = "action-summary"

    # Filler Item: Non-interactive, occupies significant space
    filler_item = Li(
        Span(" "),  # Empty span as a filler
        style=(
            f"flex-grow: 1; min-width: {NAV_FILLER_WIDTH}; "  # Allows it to grow and ensures a minimum width
            "list-style-type: none;"  # Removes the bullet point
        ),
    )

    chat_menu = Details(
        Summary(
            selected_chat,
            style=(
                f"{common_style} width: {PROFILE_MENU_WIDTH}; "  # Use constant for chat interface width
                "background-color: var(--pico-background-color); "
                "border: 1px solid var(--pico-muted-border-color);"
            ),
            id=chat_summary_id,
        ),
        Ul(
            create_menu_item("Default Profile", "/profile/default_profile", chat_summary_id),
            create_menu_item("Future Profile 2", "/profile/future_profile_1", chat_summary_id),
            create_menu_item("Future Profile 3", "/profile/future_profile_2", chat_summary_id),
            create_menu_item("Future Profile 4", "/profile/future_profile_3", chat_summary_id),
            dir="rtl",
            id="chat-menu-list",
        ),
        cls="dropdown",
        id="chat-menu",
    )

    action_menu = Details(
        Summary(
            selected_action,
            style=(
                f"{common_style} width: {ACTION_MENU_WIDTH}; "  # Use constant for action menu width
                "background-color: var(--pico-background-color); "
                "border: 1px solid var(--pico-muted-border-color);"
            ),
            id=action_summary_id,
        ),
        Ul(
            create_menu_item("Action 1", "/action/1", action_summary_id),
            create_menu_item("Action 2", "/action/2", action_summary_id),
            create_menu_item("Action 3", "/action/3", action_summary_id),
            create_menu_item("Action 4", "/action/4", action_summary_id),
            dir="rtl",
            id="action-menu-list",
        ),
        cls="dropdown",
        id="action-menu",
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
                f"{common_style} width: {SEARCH_WIDTH}; padding-right: 25px; "
                "border: 1px solid var(--pico-muted-border-color);"
            ),
        ),
        Button(
            "×",
            type="button",
            onclick="document.getElementById('nav-input').value = ''; this.blur();",
            style=(
                "position: absolute; right: 6px; top: 50%; transform: translateY(-50%); "
                "width: 16px; height: 16px; font-size: 0.8rem; color: var(--pico-muted-color); "
                "opacity: 0.5; background: none; border: none; cursor: pointer; padding: 0; "
                "display: flex; align-items: center; justify-content: center; "
                "border-radius: 50%;"
            ),
        ),
        style="display: flex; align-items: center; position: relative;",
    )

    nav = Div(
        filler_item,  # Add the filler item first
        chat_menu,
        action_menu,
        search_group,
        style=(
            "display: flex; align-items: center; gap: 8px; "
            "width: 100%;"  # Ensure the nav takes full width
        ),
    )

    return nav


# Application Setup
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

# Choose the best available model
model = get_best_model()

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
    await asyncio.create_task(stream_chat(message))


# Route Handlers
@rt('/')
def get():
    """Handle the main page GET request."""
    nav = create_nav_menu()

    nav_group = Group(
        nav,
        style="display: flex; align-items: center; margin-bottom: 20px; gap: 20px;",
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
                            mk_input_group(),
                        ),
                    ),
                ),
                cls="grid",
                style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px;",
            ),
            Div(
                A(
                    "Poke Todo List",
                    hx_post="/poke",
                    hx_target="#msg-list",
                    hx_swap="innerHTML",
                    cls="button",
                ),
                style="position: fixed; bottom: 20px; right: 20px; z-index: 1000;",
            ),
        ),
        hx_ext='ws',
        ws_connect='/ws',
        data_theme="dark",
    )


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

    await chatq(
        f"New todo: '{todo.title}'. Brief, sassy comment or advice."
    )

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
    await chatq(f"Todo '{todo.title}' deleted. Brief, sassy reaction.")
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

    await chatq(
        f"Todo '{todo.title}' toggled from {old_status} to {new_status}. "
        f"Brief, sassy comment mentioning '{todo.title}'."
    )

    return Input(
        type="checkbox",
        name="english" if updated_todo.done else None,
        checked=updated_todo.done,
        hx_post=f"/toggle/{updated_todo.id}",
        hx_swap="outerHTML",
    )


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


@rt('/profile/{profile_type}')
async def chat_interface(profile_type: str):
    """Handle chat menu selection."""
    # Update the summary element with the selected chat type
    chat_summary_id = "chat-summary"
    selected_profile = profile_type.replace('_', ' ').title()
    summary_content = Summary(
        selected_profile,
        style=(
            f"font-size: 1rem; height: 32px; line-height: 32px; "
            "display: inline-flex; align-items: center; justify-content: center; "
            "margin: 0 2px; border-radius: 16px; padding: 0 0.6rem; "
            f"width: {PROFILE_MENU_WIDTH}; background-color: var(--pico-background-color); "
            "border: 1px solid var(--pico-muted-border-color);"
        ),
        id=chat_summary_id,
    )
    prompt = f"Respond mentioning '{selected_profile}' in your reply, keeing it brief, under 20 words."
    await chatq(prompt)
    return summary_content


@rt('/action/{action_id}')
async def perform_action(action_id: str):
    """Handle action menu selection."""
    # Update the summary element with the selected action
    action_summary_id = "action-summary"
    selected_action = f"Action {action_id}"
    summary_content = Summary(
        selected_action,
        style=(
            f"font-size: 1rem; height: 32px; line-height: 32px; "
            "display: inline-flex; align-items: center; justify-content: center; "
            "margin: 0 2px; border-radius: 16px; padding: 0 0.6rem; "
            f"width: {ACTION_MENU_WIDTH}; background-color: var(--pico-background-color); "
            "border: 1px solid var(--pico-muted-border-color);"
        ),
        id=action_summary_id,
    )
    prompt = f"You selected '{selected_action}'. Respond cleverly, mentioning '{selected_action}' in your reply. Be brief and sassy."
    await chatq(prompt)
    return summary_content


@rt('/search', methods=['POST'])
async def search(nav_input: str):
    """Handle search input."""
    prompt = f"The user searched for: '{nav_input}'. Respond briefly acknowledging the search."
    await chatq(prompt)
    return ''


# WebSocket Handler Modification
@app.ws('/ws', conn=on_conn, disconn=on_disconn)
async def ws(msg: str):
    """Handle WebSocket messages."""
    if msg:
        # Disable the input group
        disable_input_group = mk_input_group(disabled=True, value=msg, autofocus=False)
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
        enable_input_group = mk_input_group(disabled=False, value='', autofocus=True)
        enable_input_group.attrs['hx_swap_oob'] = "true"
        for u in users.values():
            await u(enable_input_group)


serve()

# Cleaned with autopep8
# autopep8 --ignore E501,F405,F403,F541 --in-place pipulate.py
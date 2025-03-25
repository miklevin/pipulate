# Context: This code is an intentionally stripped-down, single-tenant, local-first app—more like an Electron app than an enterprise or multi-tenant system. It uses server-side state (via DictLikeDB) and HTMX for UI updates, deliberately avoiding complex ORM or FastAPI patterns. All design decisions (even if they look like anti-patterns) are intentional for local simplicity and observability. Please don't refactor or "fix" these intentional patterns. The CRUD is DRY and the Workflows are WET!

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

TONE = "neutral"
MODEL = "gemma3"
MAX_LLM_RESPONSE_WORDS = 60
THIS_FILE = Path(__file__)


def get_app_name(force_app_name=None):
    name = force_app_name
    if not name:
        app_name_file = 'app_name.txt'
        if Path(app_name_file).exists():
            try:
                name = Path(app_name_file).read_text().strip()
            except:
                pass
        if not name:
            name = THIS_FILE.parent.name
            name = name[:-5] if name.endswith('-main') else name
    return name.capitalize()


APP_NAME = get_app_name()
MAX_CONVERSATION_LENGTH = 10000
PLACEHOLDER_ADDRESS = "www.site.com"
PLACEHOLDER_CODE = "CCode (us, uk, de, etc)"
GRID_LAYOUT = "65% 35%"
NAV_FILLER_WIDTH = "2%"
MIN_MENU_WIDTH = "18vw"
MAX_MENU_WIDTH = "22vw"
WEB_UI_WIDTH = "95%"
WEB_UI_PADDING = "1rem"
WEB_UI_MARGIN = "0 auto"
NOWRAP_STYLE = ("white-space: nowrap; ""overflow: hidden; ""text-overflow: ellipsis;")
LIST_SUFFIX = "List"


def generate_menu_style():
    return (f"min-width: {MIN_MENU_WIDTH}; "f"max-width: {MAX_MENU_WIDTH}; ""width: 100%; ""white-space: nowrap; ""overflow: hidden; ""text-overflow: ellipsis; ""align-items: center; ""border-radius: 16px; ""display: inline-flex; ""justify-content: center; ""margin: 0 2px; ")


DOWNLOAD_DIR = Path('downloads')
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging():
    logs_dir = Path('logs')
    logs_dir.mkdir(parents=True, exist_ok=True)
    app_log_path = logs_dir / f'{APP_NAME}.log'
    logger.remove()
    for p in [app_log_path]:
        if p.exists():
            p.unlink()
    logger.add(app_log_path, rotation="2 MB", level="DEBUG", format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name: <15} | {message}", enqueue=True)
    logger.add(sys.stderr, level="DEBUG", format="<green>{time:HH:mm:ss}</green> | ""<level>{level: <8}</level> | ""<cyan>{name: <15}</cyan> | ""<cyan>{message}</cyan>", colorize=True, filter=lambda record: (record["level"].name in ["ERROR", "WARNING"] or record["level"].name == "INFO" or (record["level"].name == "DEBUG" and ("HTTP Request:" in record["message"] or "Pipeline ID:" in record["message"] or "State changed:" in record["message"] or record["message"].startswith("Creating") or record["message"].startswith("Updated")) and not "Pipeline" in record["message"] and not record["message"].startswith("DB: __") and not "First record" in record["message"] and not "Records found" in record["message"] and not "dir:" in record["message"])))
    return logger.opt(colors=True)


logger = setup_logging()
custom_theme = Theme({"default": "white on black", "header": RichStyle(color="magenta", bold=True, bgcolor="black"), "cyan": RichStyle(color="cyan", bgcolor="black"), "green": RichStyle(color="green", bgcolor="black"), "orange3": RichStyle(color="orange3", bgcolor="black"), "white": RichStyle(color="white", bgcolor="black"), })


class DebugConsole(Console):
    def print(self, *args, **kwargs):
        super().print(*args, **kwargs)


console = DebugConsole(theme=custom_theme)


def fig(text, font='slant', color='cyan'):
    font = 'standard'
    figlet = Figlet(font=font)
    fig_text = figlet.renderText(str(text))
    colored_text = Text(fig_text, style=f"{color} on default")
    console.print(colored_text, style="on default")


def name(word):
    return word.replace('_', ' ').replace('.', ' ').title()


def format_endpoint_name(endpoint: str) -> str:
    if endpoint in friendly_names:
        return friendly_names[endpoint]
    return ' '.join(word.capitalize() for word in endpoint.split('_'))


def format_step_name(step: str, preserve: bool = False) -> str:
    _, number = step.split('_')
    return f"Step {number.lstrip('0')}"


def format_step_button(step: str, preserve: bool = False, revert_label: str = None) -> str:
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
                print(content)
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


def generate_system_message():
    message = read_training("system_prompt.md")
    logger.debug("Begin System Prompt")
    logger.debug("End System Prompt")
    return message


def todo_list_training():
    operations = [("List All Records", "list"), ("Insert (Create)", "insert"), ("Read (Retrieve)", "read"), ("Update", "update"), ("Delete", "delete"), ("Toggle Field (e.g., Status)", "toggle"), ("Sort Records", "sort"),]
    operation_docs = {"list": """
        # List all tasks
        {
            "action": "list",
            "target": "task"
        }""", "insert": """
        # Create a new task
        # Only 'name' is required - can include emoji (e.g. "🎯 Important Task")
        # All other fields are optional and will be handled automatically
        {
            "action": "insert",
            "target": "task",
            "args": {
                "name": "🎯 Sample Task"
            }
        }""", "read": """
        # Retrieve a specific task by ID
        {
            "action": "read",
            "target": "task",
            "args": {
                "id": "123"    # Must be a string
            }
        }""", "update": """
        # Update an existing task
        # All fields are optional except id
        {
            "action": "update",
            "target": "task",
            "args": {
                "id": "123",           # Required: task ID as string
                "name": "📝 New Name",  # Optional: new task name
                "done": 1,             # Optional: 0=incomplete, 1=complete
                "priority": 2          # Optional: new priority
            }
        }""", "delete": """
        # Delete a task by ID
        {
            "action": "delete",
            "target": "task",
            "args": {
                "id": "123"    # Must be a string
            }
        }""", "toggle": """
        # Toggle a task's status (usually the 'done' field)
        {
            "action": "toggle",
            "target": "task",
            "args": {
                "id": "123",        # Must be a string
                "field": "done"     # Field to toggle
            }
        }""", "sort": """
        # Reorder tasks by priority
        # Lower priority number = higher in list
        {
            "action": "sort",
            "target": "task",
            "args": {
                "items": [
                    {"id": "123", "priority": 0},    # First item
                    {"id": "456", "priority": 1},    # Second item
                    {"id": "789", "priority": 2}     # Third item
                ]
            }
        }"""}
    emoji_instructions = ("You are now the Tasks app and you add to the task list.\n\n""This is our JSON API contract. You must follow it to insert tasks.\n\n""Follow this whenever asked to add something to a list.\n\n""When inserting tasks, follow these rules:\n\n""1. Always use the actual emoji character with the text in the 'name' field\n""2. Example of minimal task insertion:\n\n""3. Always USE THIS EXACT FORMAT when asked to add or insert an apple:\n\n""```json\n""{\n"'  "action": "insert",\n''  "target": "task",\n''  "args": {\n''    "name": "🍎 Red Apple"\n''  }\n'"}\n""```\n\n""4. All string values must use double quotes\n")
    syntax_instructions = ("You can use the following JSON syntax to perform operations on the database.\n""Important notes:\n""1. All IDs should be strings (e.g. \"123\")\n""2. Task names can include emojis (e.g. \"🎯 Important Task\")\n""3. All operations use 'task' as the target\n""4. All string values must be properly quoted with double quotes\n\n""5. Do not pretend to add something to a list without also including the JSON.\n\n")
    for i, (operation_name, operation_key) in enumerate(operations, 1):
        doc = operation_docs.get(operation_key, "")
        syntax_instructions += (f"{i}. {operation_name}\n\n"f"```json\n{doc}\n```\n\n")
    message = emoji_instructions + "\n\n" + syntax_instructions
    message += "Only use JSON when asked for an insert, update, delete, or toggle action. "
    message += "All other times, RESPOND IN PLAIN ENGLISH! "
    message += "You are a simple task list manager. \n\n"
    return message


PERMITTED_LLM_ACTIONS = {"insert", "read", "update", "delete", "toggle", "sort", "list"}
if MAX_LLM_RESPONSE_WORDS:
    limiter = f"in under {MAX_LLM_RESPONSE_WORDS} {TONE} words"
else:
    limiter = ""
CRUD_PROMPT_PREFIXES = {action: f"Make a {TONE} comment {limiter} to the user letting them know you know "for action in PERMITTED_LLM_ACTIONS}
global_conversation_history = deque(maxlen=MAX_CONVERSATION_LENGTH)
conversation = [{"role": "system", "content": generate_system_message()}]


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


async def display_conversation_statistics():
    logger.debug("Entering display_conversation_statistics")
    role_counts = Counter(entry['role'] for entry in global_conversation_history)
    logger.debug(f"Role counts: {dict(role_counts)}")
    table = Table(title="Conversation History Statistics")
    table.add_column("Role", style="cyan")
    table.add_column("Count", style="magenta")
    table.add_column("Percentage", style="green")
    total_messages = sum(role_counts.values())
    logger.debug(f"Total messages: {total_messages}")
    for role in ['system', 'user', 'assistant']:
        count = role_counts.get(role, 0)
        percentage = (count / total_messages) * 100 if total_messages > 0 else 0
        table.add_row(role.capitalize(), str(count), f"{percentage:.2f}%")
        logger.debug(f"Added row for {role}: count={count}, percentage={percentage:.2f}%")
    table.add_row("Total", str(total_messages), "100.00%", style="bold")
    logger.debug("Added total row to table")
    console = Console()
    console.print(table)
    logger.debug("Printed statistics table")
    logger.debug("Exiting display_conversation_statistics")


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
                            await display_conversation_statistics()
                            await post_llm_stream_json_detection(final_response, base_app)
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


def create_chat_scripts(sortable_selector='.sortable', ghost_class='blue-background-class'):
    sortable_script = f"""
    function setupSortable() {{
        const sortableEl = document.querySelector('{sortable_selector}');
        if (sortableEl) {{
            new Sortable(sortableEl, {{
                animation: 150,
                ghostClass: '{ghost_class}',
                onEnd: function (evt) {{
                    let items = Array.from(sortableEl.children).map((item, index) => ({{
                        id: item.dataset.id,
                        priority: index
                    }}));
                    
                    let path = window.location.pathname;
                    let updateUrl = path.endsWith('/') ? path + 'sort' : path + '_sort';
                    
                    htmx.ajax('POST', updateUrl, {{
                        target: sortableEl,
                        swap: 'none',
                        values: {{ items: JSON.stringify(items) }}
                    }});
                }}
            }});
        }}
    }}
    """
    websocket_sse_script = r"""
    function setupWebSocketAndSSE() {
        // SSE Setup
        let lastMessage = null;
        const evtSource = new EventSource("/sse");
        
        evtSource.onmessage = function(event) {
            const data = event.data;
            console.log('SSE received:', data);
            
            // Only process if it's not a ping message
            if (!data.includes('Test ping at')) {
                const todoList = document.getElementById('todo-list');
                if (!todoList) {
                    console.error('Could not find todo-list element');
                    return;
                }

                const temp = document.createElement('div');
                temp.innerHTML = data;
                
                const newTodo = temp.firstChild;
                if (newTodo) {
                    todoList.appendChild(newTodo);
                    htmx.process(newTodo);
                }
            }
        };

        // WebSocket message handler
        window.handleWebSocketMessage = function(event) {
            console.log('Sidebar received:', event.data);
            
            // Check if the message is a script
            if (event.data.trim().startsWith('<script>')) {
                const scriptContent = event.data.replace(/<\/?script>/g, '').trim();
                console.log('Executing script:', scriptContent);
                try {
                    eval(scriptContent);
                } catch (e) {
                    console.error('Error executing script:', e);
                }
                return;
            }
            
            // Check if the response is an HTML element
            if (event.data.trim().startsWith('<')) {
                try {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(event.data.trim(), 'text/html');
                    const element = doc.body.firstChild;
                    
                    if (element && element.hasAttribute('data-id')) {
                        const todoList = document.getElementById('todo-list');
                        if (todoList) {
                            todoList.appendChild(element);
                            if (window.Sortable && !todoList.classList.contains('sortable-initialized')) {
                                new Sortable(todoList, {
                                    animation: 150,
                                    ghostClass: 'blue-background-class'
                                });
                                todoList.classList.add('sortable-initialized');
                            }
                        }
                        return;
                    }
                } catch (e) {
                    console.error('Error parsing HTML:', e);
                }
            }
            
            // Handle regular chat messages
            const sidebarMsgList = document.getElementById('msg-list');
            const sidebarCurrentMessage = document.createElement('div');
            sidebarCurrentMessage.className = 'message assistant';
            
            if (!sidebarCurrentMessage.parentElement) {
                sidebarMsgList.appendChild(sidebarCurrentMessage);
            }
            
            // Handle line breaks in messages
            if (event.data.includes('\\n')) {
                const lines = event.data.split('\\n');
                sidebarCurrentMessage.innerHTML += lines.map(line => 
                    line.trim() ? `<p>${line}</p>` : '<br>'
                ).join('');
            } else {
                sidebarCurrentMessage.innerHTML += event.data;
            }
            
            sidebarMsgList.scrollTop = sidebarMsgList.scrollHeight;
        };

        // Test functions
        window.testSSE = function() {
            alert('Latest SSE message: ' + (lastMessage || 'No messages received yet'));
        }
        
        window.sseLastMessage = function() {
            return lastMessage;
        }
        
        console.log('WebSocket and SSE handlers initialized');
    }
    """
    interaction_script = r"""
    function setupInteractions() {
        // Form reset after submission
        document.addEventListener('htmx:afterSwap', function(event) {
            if (event.target.id === 'todo-list' && event.detail.successful) {
                const form = document.querySelector('form[hx-target="#todo-list"]');
                if (form) {
                    form.reset();
                }
            }
        });

        window.triggerTestAppend = () => {
            htmx.ajax('GET', '/test-append', {
                target: '#todo-list',
                swap: 'beforeend'
            });
        };

        window.handleSearchSubmit = function(event) {
            event.preventDefault();
            const input = document.getElementById('nav-input');
            if (input && input.value) {
                if (window.sidebarWs) {
                    window.sidebarWs.send(input.value);
                }
                input.value = '';
            }
        };
    }
    """
    combined_script = f"""
    document.addEventListener('DOMContentLoaded', (event) => {{
        {sortable_script}
        {websocket_sse_script}
        {interaction_script}
        
        // Initialize all components
        setupSortable();
        setupWebSocketAndSSE();
        setupInteractions();
        
        console.log('All scripts initialized');
    }});
    """
    return Script(combined_script), Style("""
        #msg-list, #msg-list {
            display: flex;
            flex-direction: column;
        }
        #msg-list {
            padding-right: 10px;
        }
        .message {
            margin-left: 0;
            margin-top: 2px;
            margin-bottom: 2px;
            padding: 8px 12px;
            border-radius: 8px;
            max-width: 100%;
            white-space: pre-wrap;
        }
        .message.user {
            background: var(--pico-primary-background);
            margin-left: auto;
        }
        .message.assistant {
            background: var(--pico-muted-background);
            margin-right: auto;
        }

        /* Modern scrollbar styling */
        #msg-list::-webkit-scrollbar {
            width: 8px;
        }

        #msg-list::-webkit-scrollbar-track {
            background: var(--pico-background-color);
            border-radius: 4px;
        }

        #msg-list::-webkit-scrollbar-thumb {
            background: var(--pico-muted-border-color);
            border-radius: 4px;
        }

        #msg-list::-webkit-scrollbar-thumb:hover {
            background: var(--pico-form-element-border-color);
        }

        /* Firefox */
        #msg-list {
            scrollbar-width: thin;
            scrollbar-color: var(--pico-muted-border-color) var(--pico-background-color);
        }

        hr {
            border-color: var(--pico-primary);
            opacity: 0.3;
        }
    """)


class BaseApp:
    """
    CRUD base class for all Apps. The CRUD is DRY and the Workflows are WET!
    """
    def __init__(self, name, table, toggle_field=None, sort_field=None, sort_dict=None):
        self.name = name
        self.table = table
        self.toggle_field = toggle_field
        self.sort_field = sort_field
        self.item_name_field = 'name'
        self.sort_dict = sort_dict or {'id': 'id', sort_field: sort_field}

    def register_routes(self, rt):
        rt(f'/{self.name}', methods=['POST'])(self.insert_item)
        rt(f'/{self.name}/{{item_id}}', methods=['POST'])(self.update_item)
        rt(f'/{self.name}/delete/{{item_id}}', methods=['DELETE'])(self.delete_item)
        rt(f'/{self.name}/toggle/{{item_id}}', methods=['POST'])(self.toggle_item)
        rt(f'/{self.name}_sort', methods=['POST'])(self.sort_items)

    def get_action_url(self, action, item_id):
        return f"/{self.name}/{action}/{item_id}"

    def render_item(self, item):
        return Li(A("🗑", href="#", hx_swap="outerHTML", hx_delete=f"/task/delete/{item.id}", hx_target=f"#todo-{item.id}", _class="delete-icon", style="cursor: pointer; display: inline;"), Input(type="checkbox", checked="1"if item.done else "0", hx_post=f"/task/toggle/{item.id}", hx_swap="outerHTML", hx_target=f"#todo-{item.id}"), A(item.name, href="#", _class="todo-title", style="text-decoration: none; color: inherit;"), data_id=item.id, data_priority=item.priority, id=f"todo-{item.id}", style="list-style-type: none;",)

    async def delete_item(self, request, item_id: int):
        try:
            item = self.table[item_id]
            item_name = getattr(item, self.item_name_field, 'Item')
            self.table.delete(item_id)
            logger.debug(f"Deleted item ID: {item_id}")
            action_details = f"The {self.name} item '{item_name}' was removed."
            prompt = action_details
            asyncio.create_task(chatq(prompt, verbatim=True))
            return ''
        except Exception as e:
            error_msg = f"Error deleting item: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while deleting {self.name} (ID: {item_id}): {error_msg}"
            prompt = action_details
            await chatq(prompt, verbatim=True)
            return str(e), 500

    async def toggle_item(self, request, item_id: int):
        try:
            item = self.table[item_id]
            current_status = getattr(item, self.toggle_field)
            new_status = not current_status
            setattr(item, self.toggle_field, new_status)
            updated_item = self.table.update(item)
            item_name = getattr(updated_item, self.item_name_field, 'Item')
            status_text = 'checked'if new_status else 'unchecked'
            action_details = f"The {self.name} item '{item_name}' is now {status_text}."
            prompt = action_details
            asyncio.create_task(chatq(prompt, verbatim=True))
            return self.render_item(updated_item)
        except Exception as e:
            error_msg = f"Error toggling item: {str(e)}"
            logger.error(error_msg)
            action_details = f"an error occurred while toggling {self.name} (ID: {item_id}): {error_msg}"
            prompt = f"{CRUD_PROMPT_PREFIXES['error']}{action_details}"
            await chatq(prompt)
            return str(e), 500

    async def sort_items(self, request):
        logger.debug(f"Received request to sort {self.name}.")
        try:
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
            asyncio.create_task(chatq(prompt, verbatim=True))
            logger.debug(f"{self.name.capitalize()} order updated successfully")
            return ''
        except json.JSONDecodeError as e:
            error_msg = f"Invalid data format: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while sorting {self.name} items: {error_msg}"
            prompt = action_details
            await chatq(prompt, verbatim=True)
            return "Invalid data format", 400
        except Exception as e:
            error_msg = f"Error updating {self.name} order: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while sorting {self.name} items: {error_msg}"
            prompt = action_details
            asyncio.create_task(chatq(prompt, verbatim=True))
            return str(e), 500

    async def insert_item(self, request):
        try:
            logger.debug(f"[RENDER DEBUG] Starting insert_item for {self.name}")
            form = await request.form()
            logger.debug(f"[RENDER DEBUG] Form data: {dict(form)}")
            new_item_data = self.prepare_insert_data(form)
            if not new_item_data:
                logger.debug("[RENDER DEBUG] No new_item_data, returning empty")
                return ''
            new_item = await self.create_item(**new_item_data)
            logger.debug(f"[RENDER DEBUG] Created new item: {new_item}")
            item_name = getattr(new_item, self.item_name_field, 'Item')
            action_details = f"A new {self.name} item '{item_name}' was added."
            prompt = action_details
            asyncio.create_task(chatq(prompt, verbatim=True))
            rendered = self.render_item(new_item)
            logger.debug(f"[RENDER DEBUG] Rendered item type: {type(rendered)}")
            logger.debug(f"[RENDER DEBUG] Rendered item content: {rendered}")
            return rendered
        except Exception as e:
            error_msg = f"Error inserting {self.name}: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while adding a new {self.name}: {error_msg}"
            prompt = action_details
            await chatq(prompt, verbatim=True)
            return str(e), 500

    async def update_item(self, request, item_id: int):
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
            action_details = f"The {self.name} item '{item_name}' was updated. Changes: {changes_str}"
            prompt = action_details
            asyncio.create_task(chatq(prompt, verbatim=True))
            logger.debug(f"Updated {self.name} item {item_id}")
            return self.render_item(updated_item)
        except Exception as e:
            error_msg = f"Error updating {self.name} {item_id}: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while updating {self.name} (ID: {item_id}): {error_msg}"
            prompt = action_details
            await chatq(prompt, verbatim=True)
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


class ProfileApp(BaseApp):
    def __init__(self, table):
        super().__init__(name=table.name, table=table, toggle_field='active', sort_field='priority')
        self.item_name_field = 'name'

    def render_item(self, profile):
        return render_profile(profile)

    def prepare_insert_data(self, form):
        profile_name = form.get('profile_name', '').strip()
        if not profile_name:
            return ''
        max_priority = max((p.priority or 0 for p in self.table()), default=-1) + 1
        return {"name": profile_name, "menu_name": form.get('profile_menu_name', '').strip(), "address": form.get('profile_address', '').strip(), "code": form.get('profile_code', '').strip(), "active": True, "priority": max_priority, }

    def prepare_update_data(self, form):
        profile_name = form.get('profile_name', '').strip()
        if not profile_name:
            return ''
        return {"name": profile_name, "menu_name": form.get('profile_menu_name', '').strip(), "address": form.get('profile_address', '').strip(), "code": form.get('profile_code', '').strip(), "active": form.get('active', '').lower() == 'true', }


def render_profile(profile):
    def count_records_with_xtra(table_handle, xtra_field, xtra_value):
        table_handle.xtra(**{xtra_field: xtra_value})
        count = len(table_handle())
        logger.debug(f"Counted {count} records in table for {xtra_field} = {xtra_value}")
        return count

    todo_count = count_records_with_xtra(todos, 'profile_id', profile.id)
    delete_icon_visibility = 'inline' if todo_count == 0 else 'none'
    delete_url = profile_app.get_action_url('delete', profile.id)
    toggle_url = profile_app.get_action_url('toggle', profile.id)

    delete_icon = A(
        '🗑',
        hx_delete=delete_url,
        hx_target=f'#profile-{profile.id}',
        hx_swap='outerHTML',
        style=f"cursor: pointer; display: {delete_icon_visibility};",
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
                name="profile_menu_name",
                value=profile.menu_name,
                placeholder="Menu Name",
                id=f"menu_name-{profile.id}"
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


class TodoApp(BaseApp):
    def __init__(self, table):
        super().__init__(name=table.name, table=table, toggle_field='done', sort_field='priority')
        self.item_name_field = 'name'

    def render_item(self, todo):
        logger.debug(f"[RENDER DEBUG] TodoApp.render_item called with: {todo}")
        rendered = render_todo(todo)
        logger.debug(f"[RENDER DEBUG] render_todo returned type: {type(rendered)}")
        return rendered

    def prepare_insert_data(self, form):
        name = form.get('todo_title', form.get('name', '')).strip()
        if not name:
            return None
        current_profile_id = db.get("last_profile_id", 1)
        priority = int(form.get('todo_priority', 0)) or max((t.priority or 0 for t in self.table()), default=-1) + 1
        return {"name": name, "done": False, "priority": priority, "profile_id": current_profile_id, }

    def prepare_update_data(self, form):
        name = form.get('name', '').strip()
        if not name:
            return ''
        return {"name": name, "done": form.get('done', '').lower() == 'true', }


def render_todo(todo):
    tid = f'todo-{todo.id}'
    print(f"[DEBUG] render_todo called for ID {todo.id} with name '{todo.name}'")
    delete_url = todo_app.get_action_url('delete', todo.id)
    toggle_url = todo_app.get_action_url('toggle', todo.id)
    
    checkbox = Input(
        type="checkbox",
        name="english" if todo.done else None,
        checked=todo.done,
        hx_post=toggle_url,
        hx_swap="outerHTML",
        hx_target=f"#{tid}",
    )
    
    delete = A(
        '🗑',
        hx_delete=delete_url,
        hx_swap='outerHTML',
        hx_target=f"#{tid}",
        style="cursor: pointer; display: inline;",
        cls="delete-icon"
    )
    
    name_link = A(
        todo.name,
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
            "    const inputField = document.getElementById('todo_name_" + str(todo.id) + "'); "
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
    
    update_form = Form(
        Div(
            Input(
                type="text",
                id=f"todo_name_{todo.id}",
                value=todo.name,
                name="name",
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
        name_link,
        update_form,
        id=tid,
        cls='done' if todo.done else '',
        style="list-style-type: none;",
        data_id=todo.id,
        data_priority=todo.priority
    )


app, rt, (store, Store), (tasks, Task), (profiles, Profile), (pipeline, Pipeline) = fast_app(
    "data/data.db",
    exts='ws',
    live=True,
    default_hdrs=False,
    hdrs=(
        Meta(charset='utf-8'),
        Link(rel='stylesheet', href='/static/pico.css'),
        Script(src='/static/htmx.js'),
        Script(src='/static/fasthtml.js'),
        Script(src='/static/surreal.js'),
        Script(src='/static/script.js'),
        Script(src='/static/Sortable.js'),
        create_chat_scripts('.sortable'),
        Script(type='module')
    ),
    store={
        "key": str,
        "value": str,
        "pk": "key"
    },
    task={
        "id": int,
        "name": str,
        "done": bool,
        "priority": int,
        "profile_id": int,
        "pk": "id"
    },
    profile={
        "id": int,
        "name": str,
        "menu_name": str,
        "address": str,
        "code": str,
        "active": bool,
        "priority": int,
        "pk": "id"
    },
    pipeline={
        "url": str,
        "app_name": str,
        "data": str,
        "created": str,
        "updated": str,
        "pk": "url"
    }
)

profile_app = ProfileApp(table=profiles)
profile_app.register_routes(rt)
todo_app = TodoApp(table=tasks)
todo_app.register_routes(rt)
todos = tasks


def build_endpoint_messages(endpoint):
    # Base dictionary for standard endpoints
    endpoint_messages = {
        "": f"Welcome to {APP_NAME}. You are on the home page. Select an app from the menu to get started. If you want to see just-in-time training, ask me the secret word before and after pressing that button.",
        "profile": ("This is where you add, edit, and delete clients. "
                    "The Nickname field is hidden on the menu so client names are never exposed unless in client (profile) list app."),
        "task": ("This is where you manage your tasks. "
                 "For a little fun, ask me to add an apple to the task list."),
        "stream_simulator": "Stream Simulator app is where you simulate a long-running server-side process. Press the 'Start Stream Simulation' button to begin.",
        "mobile_chat": "Even when installed on your desktop, you can chat with the local LLM from your phone.",
    }

    # Add messages for all workflows in our registry
    for workflow_name, workflow_instance in workflow_instances.items():
        if workflow_name not in endpoint_messages:
            # First check for ENDPOINT_MESSAGE attribute
            if hasattr(workflow_instance, 'ENDPOINT_MESSAGE'):
                endpoint_messages[workflow_name] = workflow_instance.ENDPOINT_MESSAGE
            # Then check for get_endpoint_message method
            elif hasattr(workflow_instance, 'get_endpoint_message') and callable(getattr(workflow_instance, 'get_endpoint_message')):
                endpoint_messages[workflow_name] = workflow_instance.get_endpoint_message()
            else:
                class_name = workflow_instance.__class__.__name__
                endpoint_messages[workflow_name] = f"{class_name} app is where you manage your workflows."

    # These debug logs should be outside the loop or use the endpoint parameter
    if endpoint in workflow_instances:
        workflow_instance = workflow_instances[endpoint]
        logger.debug(f"Checking if {endpoint} has get_endpoint_message: {hasattr(workflow_instance, 'get_endpoint_message')}")
        logger.debug(f"Checking if get_endpoint_message is callable: {callable(getattr(workflow_instance, 'get_endpoint_message', None))}")
        logger.debug(f"Checking if {endpoint} has ENDPOINT_MESSAGE: {hasattr(workflow_instance, 'ENDPOINT_MESSAGE')}")

    return endpoint_messages.get(endpoint, None)


def build_endpoint_training(endpoint):
    # Base dictionary for standard endpoints
    endpoint_training = {
        "": ("You were just switched to the home page."),
        "profile": ("You were just switched to the profile app."),
        "task": todo_list_training(),
        "stream_simulator": ("Stream Simulator app is where you simulate a long-running server-side process. Press the 'Start Stream Simulation' button to begin."),
        "mobile_chat": ("You were just switched to the mobile chat app."),
    }

    # Add training for all workflows in our registry
    for workflow_name, workflow_instance in workflow_instances.items():
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
                    logger.debug(f"DB: {key} = {str(value)[:50]}...")
            return result
        except Exception as e:
            logger.error(f"DB Error: {e}")
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
    if not todos():
        todos.insert({"name": f"Sample {todo_app.name}", "done": False, "priority": 1, "profile_id": default_profile.id, })
        logger.debug(f"Inserted sample {todo_app.name} item.")


populate_initial_data()


def priority_key(item):
    try:
        return float(item.priority or 0)
    except (ValueError, TypeError):
        return float('inf')


def pipeline_operation(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        url = args[0]if args else None
        if not url:
            return func(self, *args, **kwargs)
        old_state = self._get_clean_state(url)
        result = func(self, *args, **kwargs)
        new_state = self._get_clean_state(url)
        if old_state != new_state:
            changes = {k: new_state[k] for k in new_state if k not in old_state or old_state[k] != new_state[k]}
            if changes:
                logger.info(f"Pipeline '{url}' state updated: {changes}")
        return result
    return wrapper


class Pipulate:
    """
    Helper class for all Workflows. The CRUD is DRY and the Workflows are WET!
    """
    PRESERVE_REFILL = True

    # Style constants
    ERROR_STYLE = "color: red;"
    SUCCESS_STYLE = "color: green;"
    WARNING_BUTTON_STYLE = "background-color: #f66;"
    PRIMARY_BUTTON_STYLE = "background-color: #4CAF50;"
    SECONDARY_BUTTON_STYLE = "background-color: #008CBA;"
    
    def __init__(self, table):
        self.table = table

    def get_style(self, style_type):
        """Get a predefined style by type"""
        styles = {
            "error": self.ERROR_STYLE,
            "success": self.SUCCESS_STYLE,
            "warning_button": self.WARNING_BUTTON_STYLE,
            "primary_button": self.PRIMARY_BUTTON_STYLE,
            "secondary_button": self.SECONDARY_BUTTON_STYLE
        }
        return styles.get(style_type, "")

    def fmt(self, endpoint: str) -> str:
        if endpoint in friendly_names:
            return friendly_names[endpoint]
        return ' '.join(word.capitalize() for word in endpoint.split('_'))

    def _get_clean_state(self, url):
        try:
            record = self.table[url]
            state = json.loads(record.data)
            state.pop('created', None)
            state.pop('updated', None)
            return state
        except (NotFoundError, json.JSONDecodeError):
            return {}

    def get_timestamp(self) -> str:
        return datetime.now().isoformat()

    @pipeline_operation
    def initialize_if_missing(self, url: str, initial_step_data: dict = None) -> tuple[Optional[dict], Optional[Card]]:
        # This needs to check for existing pipelines with the same URL for a different app_name
        try:
            state = self.read_state(url)
            if state:
                return state, None
            now = self.get_timestamp()
            state = {"created": now, "updated": now}
            if initial_step_data:
                app_name = None
                if "app_name" in initial_step_data:
                    app_name = initial_step_data.pop("app_name")
                state.update(initial_step_data)
            self.table.insert({"url": url, "app_name": app_name if app_name else None, "data": json.dumps(state), "created": now, "updated": now})
            return state, None
        except:
            error_card = Card(H3("ID Already In Use"), P(f"The ID '{url}' is already being used by another workflow. Please try a different ID."), style=self.id_conflict_style())
            return None, error_card

    def read_state(self, url: str) -> dict:
        logger.debug(f"Reading state for pipeline: {url}")
        try:
            self.table.xtra(url=url)
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

    def write_state(self, url: str, state: dict) -> None:
        state["updated"] = datetime.now().isoformat()
        payload = {"url": url, "data": json.dumps(state), "updated": state["updated"]}
        logger.debug(f"Update payload:\n{json.dumps(payload, indent=2)}")
        self.table.update(payload)
        verification = self.read_state(url)
        logger.debug(f"Verification read:\n{json.dumps(verification, indent=2)}")

    def revert_control(self, step_id: str, app_name: str, steps: list, message: str = None, target_id: str = None, revert_label: str = None):
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
        default_style = ("background-color: var(--pico-del-color);""display: inline-flex;""padding: 0.5rem 0.5rem;""border-radius: 4px;""font-size: 0.85rem;""cursor: pointer;""margin: 0;""line-height: 1;""align-items: center;")
        form = Form(Input(type="hidden", name="step_id", value=step_id), Button(format_step_button(step_id, refill, revert_label), type="submit", style=default_style), hx_post=f"/{app_name}/revert", hx_target=f"#{target_id}", hx_swap="outerHTML")
        if not message:
            return form
        return Card(Div(message, style="flex: 1;"), Div(form, style="flex: 0;"), style="display: flex; align-items: center; justify-content: space-between;")

    def wrap_with_inline_button(self, input_element: Input, button_label: str = "Next", button_class: str = "primary") -> Div:
        return Div(input_element, Button(button_label, type="submit", cls=button_class, style=("display: inline-block;""cursor: pointer;""width: auto !important;""white-space: nowrap;")), style="display: flex; align-items: center; gap: 0.5rem;")

    async def get_state_message(self, url: str, steps: list, messages: dict) -> str:
        state = self.read_state(url)
        logger.debug(f"\nDEBUG [{url}] State Check:")
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
    def get_step_data(self, url: str, step_id: str, default=None) -> dict:
        state = self.read_state(url)
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

    async def stream(self, thewords: str, delay: float = 0.05):
        async def stream_task():
            import re
            words = re.split(r'(\s+)', thewords)
            words = [w for w in words if w]
            current_chunk = []
            for word in words[:-1]:
                current_chunk.append(word)
                if (any(p in word for p in '.!?:') or ''.join(current_chunk).strip().__len__() >= 30):
                    chunk_text = ''.join(current_chunk)
                    await chat.broadcast(chunk_text)
                    append_to_conversation(chunk_text, role="system", quiet=True)
                    current_chunk = []
                    await asyncio.sleep(delay)
            if words:
                current_chunk.append(words[-1])
            if current_chunk:
                final_chunk = ''.join(current_chunk) + '<br>\n'
                await chat.broadcast(final_chunk)
                append_to_conversation(final_chunk, role="system", quiet=True)
        asyncio.create_task(stream_task())


def discover_workflow_files():
    workflow_modules = {}
    workflows_dir = os.path.join(os.path.dirname(__file__), 'workflows')

    logger.debug(f"Looking for workflows in: {workflows_dir}")

    # Skip if the directory doesn't exist
    if not os.path.isdir(workflows_dir):
        logger.warning(f"Workflows directory not found: {workflows_dir}")
        return workflow_modules

    # Find all Python files in the workflows directory
    for filename in os.listdir(workflows_dir):
        logger.debug(f"Checking file: {filename}")
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = filename[:-3]  # Remove .py extension
            logger.debug(f"Attempting to import module: {module_name}")
            try:
                # Import the module
                module = importlib.import_module(f'workflows.{module_name}')
                workflow_modules[module_name] = module
                logger.debug(f"Successfully imported module: {module_name}")
            except ImportError as e:
                logger.error(f"Error importing workflow module {module_name}: {str(e)}")

    logger.debug(f"Discovered workflow modules: {list(workflow_modules.keys())}")
    return workflow_modules


def find_workflow_classes(workflow_modules):
    workflow_classes = []

    for module_name, module in workflow_modules.items():
        logger.debug(f"Examining module: {module_name}")

        for name, obj in inspect.getmembers(module):
            logger.debug(f"Found member in {module_name}: {name}, type: {type(obj)}")

            # Check if it's a class
            if inspect.isclass(obj):
                logger.debug(f"Class found: {module_name}.{name}")

                # Check if it has the right methods that make it workflow-like
                if hasattr(obj, 'landing') and callable(getattr(obj, 'landing')):
                    workflow_classes.append((module_name, name, obj))
                    logger.debug(f"Found workflow-like class with landing method: {module_name}.{name}")

    logger.debug(f"Discovered workflow classes: {[(m, c) for m, c, _ in workflow_classes]}")
    return workflow_classes


pipulate = Pipulate(pipeline)
workflow_instances = {}
discovered_modules = discover_workflow_files()
discovered_classes = find_workflow_classes(discovered_modules)

# Ensure these dictionaries are initialized
friendly_names = {"": "Home"}
endpoint_training = {}


def get_display_name(workflow_name):
    instance = workflow_instances.get(workflow_name)
    if instance and hasattr(instance, 'DISPLAY_NAME'):
        return instance.DISPLAY_NAME
    return workflow_name.replace('_', ' ').title()  # Default display name


def get_endpoint_message(workflow_name):
    instance = workflow_instances.get(workflow_name)
    if instance and hasattr(instance, 'ENDPOINT_MESSAGE'):
        return instance.ENDPOINT_MESSAGE
    return f"{workflow_name.replace('_', ' ').title()} app is where you manage your workflows."  # Default message


# Register workflows
for module_name, class_name, workflow_class in discovered_classes:
    if module_name not in workflow_instances:
        try:
            instance = workflow_class(app, pipulate, pipeline, db)
            workflow_instances[module_name] = instance
            logger.debug(f"Auto-registered workflow: {module_name}")

            # Retrieve and log the endpoint message using the new method
            endpoint_message = get_endpoint_message(module_name)
            logger.debug(f"Endpoint message for {module_name}: {endpoint_message}")

        except Exception as e:
            logger.error(f"Error instantiating workflow {module_name}.{class_name}: {str(e)}")

# Use the registry to set friendly names and endpoint messages
for workflow_name, workflow_instance in workflow_instances.items():
    if workflow_name not in friendly_names:
        display_name = get_display_name(workflow_name)
        logger.debug(f"Setting friendly name for {workflow_name}: {display_name}")
        friendly_names[workflow_name] = display_name

    if workflow_name not in endpoint_training:
        endpoint_message = get_endpoint_message(workflow_name)
        logger.debug(f"Setting endpoint message for {workflow_name}: {endpoint_message}")
        endpoint_training[workflow_name] = endpoint_message

base_menu_items = ['', 'profile', todo_app.name]
additional_menu_items = ['stream_simulator', 'mobile_chat']
MENU_ITEMS = base_menu_items + list(workflow_instances.keys()) + additional_menu_items
logger.debug(f"Dynamic MENU_ITEMS: {MENU_ITEMS}")


@rt('/clear-db', methods=['POST'])
async def clear_db(request):
    keys = list(db.keys())
    for key in keys:
        del db[key]
    logger.debug("DictLikeDB cleared")
    records = list(pipulate.table())
    for record in records:
        pipulate.table.delete(record.url)
    logger.debug("Pipeline table cleared")
    db["temp_message"] = "Database cleared."
    logger.debug("DictLikeDB cleared for debugging")
    return HTMLResponse("Database cleared.", headers={"HX-Refresh": "true"})


def get_profile_name():
    profile_id = db.get("last_profile_id")
    if profile_id is None:
        logger.debug("No last_profile_id found. Attempting to use the first available profile.")
    logger.debug(f"Retrieving profile name for ID: {profile_id}")
    try:
        profile = profiles.get(profile_id)
        if profile:
            logger.debug(f"Found profile: {profile.name}")
            return profile.name
    except NotFoundError:
        logger.warning(f"No profile found for ID: {profile_id}. Attempting to use the first available profile.")
        all_profiles = profiles()
        if all_profiles:
            first_profile = all_profiles[0]
            db["last_profile_id"] = first_profile.id
            logger.debug(f"Using first available profile ID: {first_profile.id}")
            return first_profile.name
        else:
            logger.warning("No profiles found in the database.")
            return "Unknown Profile"


async def home(request):
    path = request.url.path.strip('/')
    logger.debug(f"Received request for path: {path}")
    menux = path if path else "home"
    logger.debug(f"Selected explore item: {menux}")
    db["last_app_choice"] = menux
    db["last_visited_url"] = request.url.path
    current_profile_id = db.get("last_profile_id")
    if current_profile_id:
        logger.debug(f"Current profile ID: {current_profile_id}")
        todos.xtra(profile_id=current_profile_id)
    else:
        logger.warning("No current profile ID found. Using default filtering.")
        todos.xtra(profile_id=None)
    if current_profile_id is None:
        first_profiles = profiles(order_by='id', limit=1)
        if first_profiles:
            current_profile_id = first_profiles[0].id
            db["last_profile_id"] = current_profile_id
            logger.debug(f"Set default profile ID to {current_profile_id}")
        else:
            logger.warning("No profiles found in the database")
    if current_profile_id is not None:
        todos.xtra(profile_id=current_profile_id)
    menux = db.get("last_app_choice", "App")
    response = await create_outer_container(current_profile_id, menux)
    logger.debug("Returning response for main GET request.")
    last_profile_name = get_profile_name()
    return Titled(f"{APP_NAME} / {name(last_profile_name)} / {format_endpoint_name(menux)}", response, data_theme="dark", style=(f"width: {WEB_UI_WIDTH}; "f"max-width: none; "f"padding: {WEB_UI_PADDING}; "f"margin: {WEB_UI_MARGIN};"),)


def create_nav_group():
    nav = create_nav_menu()
    nav_group_style = ("display: flex; ""align-items: center; ""position: relative;")
    return Group(nav, style=nav_group_style)


def create_nav_menu():
    logger.debug("Creating navigation menu.")
    menux = db.get("last_app_choice", "App")
    selected_profile_id = db.get("last_profile_id")
    selected_profile_name = get_profile_name()
    nav_items = [create_filler_item(), create_profile_menu(selected_profile_id, selected_profile_name), create_app_menu(menux)]
    nav = Div(*nav_items, style="display: flex; gap: 20px;")
    logger.debug("Navigation menu created.")
    return nav


def create_filler_item():
    return Li(Span(" "), style=("display: flex; ""flex-grow: 1; ""justify-content: center; ""list-style-type: none; "f"min-width: {NAV_FILLER_WIDTH}; "),)


def create_profile_menu(selected_profile_id, selected_profile_name):
    def get_selected_item_style(is_selected):
        return "background-color: var(--pico-primary-background); "if is_selected else ""
    menu_items = []
    menu_items.append(Li(A(f"Edit {format_endpoint_name(profile_app.name)}", href=f"/redirect/{profile_app.name}", cls="dropdown-item", style=(f"{NOWRAP_STYLE} ""font-weight: bold; ""border-bottom: 1px solid var(--pico-muted-border-color);""display: block; ""text-align: center; ")), style=("display: block; ""text-align: center; ")))
    active_profiles = profiles("active=?", (True,), order_by='priority')
    for profile in active_profiles:
        is_selected = str(profile.id) == str(selected_profile_id)
        item_style = get_selected_item_style(is_selected)
        menu_items.append(Li(Label(Input(type="radio", name="profile", value=str(profile.id), checked=is_selected, hx_post=f"/select_profile", hx_vals=f'js:{{profile_id: "{profile.id}"}}', hx_target="body", hx_swap="outerHTML",), profile.name, style="display: flex; align-items: center;"), style=f"text-align: left; {item_style}"))
    return Details(Summary(f"{profile_app.name.upper()}: {selected_profile_name}", style=generate_menu_style(), id="profile-id",), Ul(*menu_items, style="padding-left: 0;",), cls="dropdown",)


def create_app_menu(menux):
    menu_items = []
    for item in MENU_ITEMS:
        is_selected = item == menux
        item_style = "background-color: var(--pico-primary-background); "if is_selected else ""
        menu_items.append(Li(A(format_endpoint_name(item), href=f"/redirect/{item}", cls="dropdown-item", style=f"{NOWRAP_STYLE} {item_style}"), style="display: block;"))
    return Details(Summary(f"APP: {format_endpoint_name(menux)}", style=generate_menu_style(), id="app-id",), Ul(*menu_items, cls="dropdown-menu",), cls="dropdown",)


async def create_outer_container(current_profile_id, menux):
    if menux == "mobile_chat":
        return Container(Meta(name="viewport", content="width=device-width, initial-scale=1.0"), create_chat_interface(autofocus=True, mobile=True), style=("width: 100vw; ""height: 100vh; ""margin: 0; ""padding: 0; ""position: fixed; ""top: 0; left: 0; ""z-index: 9999; ""background: var(--background-color); ""overflow: hidden; "))
    nav_group = create_nav_group()
    is_chat_view = menux == "mobile_chat"
    if menux == todo_app.name:
        todo_items = sorted(todos(), key=priority_key)
        logger.debug(f"Fetched {len(todo_items)} todo items for profile ID {current_profile_id}.")
    elif menux == "your_new_plugin_name":
        pass
    else:
        todo_items = []
    return Container(Meta(name="viewport", content="width=device-width, initial-scale=1.0"), nav_group, Grid(await create_grid_left(menux, todo_items), create_chat_interface()if not is_chat_view else None, cls="grid", style=("display: grid; ""gap: 20px; "f"grid-template-columns: {GRID_LAYOUT if not is_chat_view else '1fr'}; "),), create_poke_button(), style=(f"width: {WEB_UI_WIDTH}; "f"max-width: none; "f"padding: {WEB_UI_PADDING}; "f"margin: {WEB_UI_MARGIN};"),)


async def create_grid_left(menux, render_items=None):
    if menux == profile_app.name:
        return await profile_render()
    elif menux == todo_app.name:
        return await todo_render(menux, render_items)
    elif menux == 'stream_simulator':
        return await stream_simulator.stream_render()
    elif menux in workflow_instances:
        workflow_instance = workflow_instances[menux]
        if hasattr(workflow_instance, 'render'):
            return await workflow_instance.render()
        return await workflow_instance.landing()
    else:
        return await introduction.introduction_render()


def create_chat_interface(autofocus=False, mobile=False):
    msg_list_height = 'height: 75vh;'if mobile else 'height: calc(70vh - 200px);'
    temp_message = None
    if "temp_message" in db:
        temp_message = db["temp_message"]
        del db["temp_message"]
    return Div(Card(None if mobile else H3(f"{APP_NAME} Chatbot"), Div(id='msg-list', cls='overflow-auto', style=(msg_list_height),), Form(mk_chat_input_group(value="", autofocus=autofocus), onsubmit="sendSidebarMessage(event)",), Script(r"""
                // Define test alert function globally
                window.testAlert = function(message) {
                    alert('Test Alert: ' + message);
                    console.log('Alert triggered with:', message);
                };

                // Match the WebSocket route from Chat
                const sidebarWs = new WebSocket('ws://' + window.location.host + '/ws');
                const sidebarMsgList = document.getElementById('msg-list');
                let sidebarCurrentMessage = document.createElement('div');
                sidebarCurrentMessage.className = 'message assistant';

                sidebarWs.onopen = function() {
                    console.log('Sidebar WebSocket connected');
                };

                sidebarWs.onclose = function() {
                    console.log('Sidebar WebSocket closed');
                };

                sidebarWs.onerror = function(error) {
                    console.error('Sidebar WebSocket error:', error);
                };

                sidebarWs.onmessage = function(event) {
                    console.log('Sidebar received:', event.data);
                    
                    // Check if the message is a script
                    if (event.data.trim().startsWith('<script>')) {
                        const scriptContent = event.data.replace(/<\/?script>/g, '').trim();
                        console.log('Executing script:', scriptContent);
                        try {
                            eval(scriptContent);
                        } catch (e) {
                            console.error('Error executing script:', e);
                        }
                        return;
                    }
                    
                    // Check if the response contains 'todo-' in the id attribute
                    if (event.data.includes('todo-')) {
                        const todoList = document.getElementById('todo-list');
                        if (todoList) {
                            const tempDiv = document.createElement('div');
                            tempDiv.innerHTML = event.data.trim(); // Trim in case of leading/trailing whitespace
                            const newItem = tempDiv.firstElementChild;
                            if (newItem && newItem.tagName === 'LI') {
                                todoList.appendChild(newItem);
                                htmx.process(newItem);  // Process HTMX bindings on the new item
                                // Reinitialize sortable if necessary
                                if (window.Sortable && !todoList.classList.contains('sortable-initialized')) {
                                    new Sortable(todoList, {
                                        animation: 150,
                                        ghostClass: 'blue-background-class'
                                    });
                                    todoList.classList.add('sortable-initialized');
                                }
                            }
                        }
                        return;
                    }
                    
                    // Handle regular chat messages
                    if (!sidebarCurrentMessage.parentElement) {
                        sidebarMsgList.appendChild(sidebarCurrentMessage);
                    }
                    sidebarCurrentMessage.innerHTML += event.data;
                    sidebarMsgList.scrollTop = sidebarMsgList.scrollHeight;
                };
                
                // Handle temp_message if it exists
                window.addEventListener('DOMContentLoaded', () => {
                    const tempMessage = """ + json.dumps(temp_message) + r""";
                    if (tempMessage) {
                        console.log('Sidebar sending verbatim:', tempMessage);
                        setTimeout(() => sidebarWs.send(`${tempMessage}|verbatim`), 1000);
                    }
                });
                
                window.sendSidebarMessage = function(event) {
                    event.preventDefault();
                    const input = document.getElementById('msg');
                    if (input.value) {
                        const userMsg = document.createElement('div');
                        userMsg.className = 'message user';
                        userMsg.textContent = input.value;
                        sidebarMsgList.appendChild(userMsg);
                        
                        sidebarCurrentMessage = document.createElement('div');
                        sidebarCurrentMessage.className = 'message assistant';
                        
                        console.log('Sidebar sending:', input.value);
                        if (sidebarWs.readyState === WebSocket.OPEN) {
                            sidebarWs.send(input.value);
                            input.value = '';
                            sidebarMsgList.scrollTop = sidebarMsgList.scrollHeight;
                        } else {
                            console.error('WebSocket not connected');
                        }
                    }
                }
            """),), id="chat-interface", style=(("position: fixed; "if mobile else "position: sticky; ") + ("top: 0; left: 0; width: 100%; height: 100vh; "if mobile else "top: 20px; ") + ("z-index: 10000; "if mobile else "") + "margin: 0; " + "padding: 0; " + "overflow: hidden; "),)


def mk_chat_input_group(disabled=False, value='', autofocus=True):
    return Group(Input(id='msg', name='msg', placeholder='Chat...', value=value, disabled=disabled, autofocus='autofocus'if autofocus else None,), Button("Send", type='submit', id='send-btn', disabled=disabled,), id='input-group')


def create_poke_button():
    return Div(A("Clear Cookie", hx_post="/clear-db", hx_swap="none", cls="button", style="margin-right: 10px;"), A(f"Poke {APP_NAME} {MODEL}", hx_post="/poke", hx_target="#msg-list", hx_swap="innerHTML", cls="button", style="margin-right: 10px;"), A("Help", hx_ws_send="!help", cls="button", onclick="document.querySelector('#msg').value = '!help'; document.querySelector('#send-btn').click();", style="margin-right: 10px;"), style=("bottom: 20px; ""position: fixed; ""right: 20px; ""z-index: 1000; ""display: flex; ""align-items: center; "),)


async def todo_render(menux, render_items=None):
    return Div(Card(H2(f"{name(menux)} {LIST_SUFFIX}"), Ul(*[todo_app.render_item(item) for item in (render_items or [])], id='todo-list', cls='sortable', style="padding-left: 0;",), header=Form(Group(Input(placeholder=f'Add new {todo_app.name.capitalize()}', id='name', name='name', autofocus=True,), Button("Add", type="submit"),), hx_post=f"/{todo_app.name}", hx_swap="beforeend", hx_target="#todo-list",),), id="content-container", style="display: flex; flex-direction: column;")


async def profile_render():
    all_profiles = profiles()
    logger.debug("Initial profile state:")
    for profile in all_profiles:
        logger.debug(f"Profile {profile.id}: name = {profile.name}, priority = {profile.priority}")
    ordered_profiles = sorted(all_profiles, key=lambda p: p.priority if p.priority is not None else float('inf'))
    logger.debug("Ordered profile list:")
    for profile in ordered_profiles:
        logger.debug(f"Profile {profile.id}: name = {profile.name}, priority = {profile.priority}")
    return Container(Grid(Div(Card(H2(f"{profile_app.name.capitalize()} {LIST_SUFFIX}"), Ul(*[render_profile(profile) for profile in ordered_profiles], id='profile-list', cls='sortable', style="padding-left: 0;"), footer=Form(Group(Input(placeholder="Nickname (menu)", name="profile_name", id="profile-name-input"), Input(placeholder=f"{name(profile_app.name)} Name", name="profile_menu_name", id="profile-menu-name-input"), Input(placeholder=PLACEHOLDER_ADDRESS, name="profile_address", id="profile-address-input"), Input(placeholder=PLACEHOLDER_CODE, name="profile_code", id="profile-code-input"), Button("Add", type="submit", id="add-profile-button"),), hx_post=f"/{profile_app.name}", hx_target="#profile-list", hx_swap="beforeend", hx_swap_oob="true",),), id="content-container",),), Script("""
            document.addEventListener('htmx:afterSwap', function(event) {
                if (event.target.id === 'profile-list' && event.detail.successful) {
                    const form = document.getElementById('add-profile-button').closest('form');
                    form.reset();
                }
            });
        """),)


async def chatq(message: str, verbatim: bool = False, role: str = "user", base_app=None, spaces_before: Optional[int] = None, spaces_after: Optional[int] = None):
    try:
        conversation_history = append_to_conversation(message, role)
        if verbatim:
            if spaces_before:
                await chat.broadcast("<br>" * spaces_before)
            await pipulate.stream(message)
            if spaces_after:
                await chat.broadcast("<br>" * spaces_after)
            response_text = message
        else:
            response_text = ""
            if spaces_before:
                await chat.broadcast("<br>" * spaces_before)
            if base_app:
                async for chunk in chat_with_llm(MODEL, conversation_history, base_app):
                    await chat.broadcast(chunk)
                    response_text += chunk
            else:
                async for chunk in chat_with_llm(MODEL, conversation_history):
                    await chat.broadcast(chunk)
                    response_text += chunk
            if spaces_after:
                await chat.broadcast("<br>" * spaces_after)
        append_to_conversation(response_text, "assistant")
        logger.debug(f"Message streamed: {response_text}")
        return message
    except Exception as e:
        logger.error(f"Error in chatq: {e}")
        traceback.print_exc()
        raise


def get_filtered_table(current_profile_id, todo_app_instance):
    try:
        logger.debug(f"[RENDER DEBUG] Getting filtered table for profile_id: {current_profile_id}")
        logger.debug(f"[RENDER DEBUG] Table object: {todo_app_instance.table}")
        logger.debug(f"[RENDER DEBUG] Table contents: {list(todo_app_instance.table)}")
        filtered_table = todo_app_instance.table.xtra(profile_id=current_profile_id)
        logger.debug(f"[RENDER DEBUG] Filtered table query result: {filtered_table}")
        if filtered_table is None:
            logger.warning("Filtered table is None")
            return []
        filtered_list = list(filtered_table)
        logger.debug(f"[RENDER DEBUG] Filtered list contents: {filtered_list}")
        if not filtered_list:
            logger.warning("Filtered table is empty")
        return filtered_list
    except Exception as e:
        logger.error(f"Error getting filtered table: {str(e)}")
        logger.error(f"[RENDER DEBUG] Stack trace: ", exc_info=True)
        return []


async def extract_json_objects(text):
    logger.debug("Begin Extract JSON")
    json_objects = []
    json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\})*)*\}))*\}'
    matches = list(re.finditer(json_pattern, text))
    logger.debug(f"Number of JSON matches detected: {len(matches)}")
    for match in matches:
        try:
            json_str = match.group()
            fixed_str = json_str.encode('utf-16', 'surrogatepass').decode('utf-16')
            json_obj = json.loads(fixed_str)
            logger.debug(f"Parsed JSON object: {json.dumps(json_obj, indent=4, sort_keys=True, ensure_ascii=False)}")
            json_objects.append(json_obj)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Problematic JSON string: {json_str}")
            table = Table(title="JSON Error")
            table.add_column("JSON String")
            table.add_row(json_str, style="green")
            console.print(table)
            clear_system_messages_from_history()
            system_message = generate_json_format_reminder()
            append_to_conversation(system_message, role="system")
            logger.info("Reinforced JSON formatting rules in conversation history")
            return []
    if not json_objects:
        logger.info("No JSON objects detected in the text.")
    logger.debug("End Extract JSON")
    return json_objects


async def post_llm_stream_json_detection(text, todo_app):
    logger.debug("Begin Ollama JSON Detection")
    detected_patterns = []
    json_objects = await extract_json_objects(text)
    logger.debug(f"[OLLAMA DEBUG] Detected JSON objects: {json_objects}")
    logger.debug(f"[OLLAMA DEBUG] Number of JSON objects: {len(json_objects)}")
    if not json_objects:
        logger.info("No CRUD operations detected in the text.")
        return detected_patterns
    for json_obj in json_objects:
        try:
            if not isinstance(json_obj, dict):
                raise ValueError(f"Invalid JSON object type: {type(json_obj)}")
            if 'action'not in json_obj or 'target'not in json_obj:
                raise ValueError(f"Missing 'action' or 'target' in JSON: {json_obj}")
            logger.debug(f"[OLLAMA DEBUG] Executing action with json_obj: {json_obj}")
            result, table_data = await execute_crud_operation(todo_app, json_obj)
            logger.debug(f"[OLLAMA DEBUG] Operation result: {result}, table_data: {table_data}")
        except Exception as e:
            error_message = f"Error processing JSON object: {str(e)}\nJSON: {json.dumps(json_obj, indent=2, ensure_ascii=False)}"
            logger.error(error_message)
            detected_patterns.append((json_obj, error_message, []))
    logger.debug("End Ollama JSON Detection")
    return detected_patterns


async def execute_crud_operation(todo_app_instance, operation_data):
    try:
        action = operation_data.get('action')
        target = operation_data.get('target')
        args = operation_data.get('args', {})
        current_profile_id = db['last_profile_id']
        logger.debug(f"[RENDER DEBUG] Current profile_id from db: {current_profile_id}")

        def get_filtered_table():
            try:
                logger.debug(f"[RENDER DEBUG] Getting filtered table for profile_id: {current_profile_id}")
                logger.debug(f"[RENDER DEBUG] Table object: {repr(todo_app_instance.table)}")
                filtered_table = todo_app_instance.table.xtra(profile_id=current_profile_id)
                return list(filtered_table)if filtered_table is not None else []
            except Exception as e:
                logger.error(f"Error getting filtered table: {str(e)}")
                logger.error("[RENDER DEBUG] Stack trace: ", exc_info=True)
                return []
        if action == "insert" and target == "task":
            logger.debug(f"[EXECUTE DEBUG] Inserting task with args: {args}")
            try:
                new_item = todos.insert({"name": args["name"]})
                todo_html = to_xml(render_todo(new_item))
                await broadcaster.send(todo_html)
                return ("Task inserted successfully", new_item), get_filtered_table()
            except Exception as e:
                logger.error(f"Insert action failed: {str(e)}")
                return (f"Error during insert: {str(e)}", None), []
        elif action == "read":
            item_id = args["id"]
            logger.debug(f"[EXECUTE DEBUG] Reading item with ID: {item_id}")
            result = (todo_app_instance.table[item_id], get_filtered_table())
            logger.debug(f"[EXECUTE DEBUG] Read item: {result}")
            return result
        elif action == "update":
            item_id = args.pop("id")
            logger.debug(f"[EXECUTE DEBUG] Updating item {item_id} with args: {args}")
            item = todo_app_instance.table[item_id]
            for key, value in args.items():
                setattr(item, key, value)
            updated_item = todo_app_instance.table.update(item)
            result = (updated_item, get_filtered_table())
            logger.debug(f"[EXECUTE DEBUG] Updated item: {result}")
            return result
        elif action == "delete":
            item_id = args["id"]
            logger.debug(f"[EXECUTE DEBUG] Deleting item with ID: {item_id}")
            todo_app_instance.table.delete(item_id)
            result = (f"Item with ID {item_id} deleted.", get_filtered_table())
            logger.debug(f"[EXECUTE DEBUG] Deleted item: {result}")
            return result
        elif action == "toggle":
            item_id = args["id"]
            field = args["field"]
            new_value = args.get("new_value")
            logger.debug(f"[EXECUTE DEBUG] Toggling {field} for item {item_id}")
            if new_value is None:
                item = todo_app_instance.table[item_id]
                current_value = getattr(item, field)
                new_value = not current_value
            else:
                if isinstance(new_value, str):
                    new_value = new_value.lower() == 'true'
            setattr(item, field, new_value)
            updated_item = todo_app_instance.table.update(item)
            result = (f"Field '{field}' updated.", updated_item)
            logger.debug(f"[EXECUTE DEBUG] Toggled item: {result}")
            return result, get_filtered_table()
        elif action == "sort":
            items = args["items"]
            logger.debug(f"[EXECUTE DEBUG] Sorting items: {items}")
            sorted_items = []
            for item in items:
                item_id = item["id"]
                priority = item["priority"]
                updated_item = todo_app_instance.table.update(id=item_id, priority=priority)
                sorted_items.append(updated_item)
            result = ("Items sorted by priority.", sorted_items)
            logger.debug(f"[EXECUTE DEBUG] Sorted items: {result}")
            return result, get_filtered_table()
        elif action == "list":
            logger.debug("[EXECUTE DEBUG] Listing all items")
            items = get_filtered_table()
            result = ("Items retrieved successfully", items)
            logger.debug(f"[EXECUTE DEBUG] Listed items: {result}")
            return result, items
        elif action == "redirect":
            profile_id = args["id"]
            logger.debug(f"[EXECUTE DEBUG] Redirecting to profile: {profile_id}")
            redirect_url = todo_app_instance.redirect_url(profile_id)
            result = ("Redirect URL generated", redirect_url)
            logger.debug(f"[EXECUTE DEBUG] Redirect result: {result}")
            return result, get_filtered_table()
        else:
            raise ValueError(f"Unsupported action: {action}")
    except Exception as e:
        error_message = f"Error during {action}: {str(e)}"
        logger.error(f"[EXECUTE DEBUG] {error_message}")
        logger.error(f"[EXECUTE DEBUG] Operation data: {json.dumps(operation_data, indent=2, ensure_ascii=False)}")
        logger.error("[EXECUTE DEBUG] Full stack trace: ", exc_info=True)
        return (error_message, None), []


class Introduction:
    def __init__(self, app, route_prefix="/introduction"):
        self.app = app
        self.route_prefix = route_prefix
        self.logger = logger.bind(name="Introduction")

    async def start_chat(self, request):
        self.logger.debug("Starting welcome chat")
        try:
            hot_prompt_injection("introduction.md")
            await chatq(f"The app name you're built into is {APP_NAME}. Please {limiter} introduce yourself and explain how you can help. Tell them to ask you the secret word.", base_app=self.app, spaces_before=1, spaces_after=1)
            return "Chat initiated"
        except Exception as e:
            self.logger.error(f"Error starting chat: {str(e)}")
            return "I'm having trouble connecting right now. Please try again in a moment."

    async def introduction_render(self):
        self.logger.debug("Rendering introduction content")
        self.app.post(f"{self.route_prefix}/start-chat")(self.start_chat)
        return Card(
            H3(f"Meet {APP_NAME}"),
            P("This demo showcases \"Hot Prompt Injection\" - a technique where the AI assistant learns new information through UI interactions so it knows what it needs to know to help you right when it needs to help you."),
            P("Try asking the AI assistant \"What's the secret word?\" right now - it will give you the wrong answer. Then click the button below to invisibly teach the AI a secret word, and ask the same question again (hint: it's the opposite of Ephemeral)."),
            Div(style="margin-bottom: 20px;"),
            Div(Button("Teach AI assistant secret word", hx_post="/introduction/start-chat", hx_swap="none", hx_trigger="click, htmx:afterRequest[document.getElementById('msg').focus()]", style="margin-top: 10px;")),
            id="intro-card",
        )


introduction = Introduction(app, route_prefix="/introduction")


class StreamSimulator:
    def __init__(self, app, route_prefix="/stream-sim", id_suffix="", show_stream_content=False):
        self.app = app
        self.route_prefix = route_prefix
        self.id_suffix = id_suffix
        self.show_stream_content = show_stream_content
        self.logger = logger.bind(name=f"StreamSimulator{id_suffix}")
        self.app.route(f"{self.route_prefix}/stream")(self.stream_handler)
        self.app.route(f"{self.route_prefix}/start", methods=["POST"])(self.start_handler)
        self.logger.debug(f"Registered routes: {self.route_prefix}/stream and {self.route_prefix}/start")

    async def stream_handler(self, request):
        async def event_generator():
            try:
                async for chunk in self.generate_chunks():
                    if isinstance(chunk, dict):
                        yield f"data: {json.dumps(chunk)}\n\n"
                    else:
                        yield f"data: {chunk}\n\n"
                yield f"data: Simulation complete\n\n"
                yield f"data: {json.dumps({'type': 'swap', 'target': '#stream_sim_button', 'content': self.create_simulator_button().to_html()})}\n\n"
            except Exception as e:
                self.logger.error(f"Error in stream: {str(e)}")
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
        return EventStream(event_generator())

    async def start_handler(self, request):
        await chatq(f"Tell the user {limiter} that you see that they have started a ""streaming simulation and will keep them updated on progress.")
        return Button("Streaming...", cls="stream-sim-button", id="stream_sim_button", disabled="true", aria_busy="true")

    async def generate_chunks(self, total_chunks=100, delay_range=(0.1, 0.5)):
        try:
            logger.debug("Generating Chunks")
            self.logger.debug(f"Generating chunks: total={total_chunks}, delay={delay_range}")
            chat_tasks = []
            for i in range(total_chunks):
                chunk = f"Simulated chunk {i + 1}/{total_chunks}"
                self.logger.debug(f"Generated chunk: {chunk}")
                yield chunk
                if i + 1 == 1:
                    chat_tasks.append(asyncio.create_task(chatq(f"Tell the user {limiter} streaming is in progress, fake as it may be.")))
                elif i + 1 == 15:
                    chat_tasks.append(asyncio.create_task(chatq(f"Tell the user {limiter} the job is 25% done, fake as it may be.")))
                elif i + 1 == 40:
                    chat_tasks.append(asyncio.create_task(chatq(f"Tell the user {limiter} the job is 50% over half way there, fake as it may be.")))
                elif i + 1 == 65:
                    chat_tasks.append(asyncio.create_task(chatq(f"Tell the user {limiter} the job is nearly complete, fake as it may be.")))
                elif i + 1 == 85:
                    chat_tasks.append(asyncio.create_task(chatq(f"Tell the user in under 20 words just a little bit more, fake as it may be.")))
                await asyncio.sleep(random.uniform(*delay_range))
            self.logger.debug("Finished generating all chunks")
            yield json.dumps({"status": "complete"})
            if chat_tasks:
                await asyncio.gather(*chat_tasks)
            await chatq(f"Congratulate the user {limiter}. The long-running job is done, fake as it may be!")
        except Exception as e:
            self.logger.error(f"Error in chunk generation: {str(e)}")
            yield json.dumps({"status": "error", "message": str(e)})

    def create_progress_card(self):
        self.logger.debug("Creating progress card")
        elements = [H3("Streaming Progress"), Div(id=f"stream-progress{self.id_suffix}", cls="progress-bar")]
        if self.show_stream_content:
            elements.append(Div(id=f"stream-content{self.id_suffix}", cls="stream-content"))
        return Card(*elements)

    def create_simulator_button(self):
        self.logger.debug("Creating simulator button")
        return Button("Start Stream Simulation", onclick=f"startSimulation_{self.id_suffix}()", cls="stream-sim-button", id=f"stream_sim_button{self.id_suffix}")

    async def stream_render(self):
        logger.debug("Rendering Stream Simulator")
        js_template = r"""
            class StreamUI {
                constructor(idSuffix) {
                    this.idSuffix = idSuffix;
                    this.progressBar = document.getElementById('stream-progress' + idSuffix);
                    this.streamContent = document.getElementById('stream-content' + idSuffix);
                    this.button = document.getElementById('stream_sim_button' + idSuffix);
                }

                setButtonState(isRunning) {
                    this.button.disabled = isRunning;
                    this.button.setAttribute('aria-busy', isRunning);
                    this.button.textContent = isRunning ? 'Streaming...' : 'Start Stream Simulation';
                }

                updateProgress(current, total) {
                    const percentage = (current / total) * 100;
                    this.progressBar.style.transition = 'width 0.3s ease-out';
                    this.progressBar.style.width = percentage + '%';
                }

                resetProgress() {
                    // Smooth transition back to 0
                    this.progressBar.style.transition = 'width 0.5s ease-out';
                    this.progressBar.style.width = '0%';
                }

                appendMessage(message) {
                    if (this.streamContent) {  // Only append if element exists
                        this.streamContent.innerHTML += message + '<br>';
                        this.streamContent.scrollTop = this.streamContent.scrollHeight;
                    }
                }

                handleJobComplete() {
                    this.resetProgress();
                    this.setButtonState(false);
                }
            }

            const streamUI_ID_SUFFIX = new StreamUI('ID_SUFFIX');

            function startSimulation_ID_SUFFIX() {
                streamUI_ID_SUFFIX.setButtonState(true);
                
                const eventSource = new EventSource('ROUTE_PREFIX/stream');
                
                eventSource.onmessage = function(event) {
                    const message = event.data;
                    streamUI_ID_SUFFIX.appendMessage(message);
                    
                    if (message.includes('Simulation complete')) {
                        eventSource.close();
                        streamUI_ID_SUFFIX.handleJobComplete();
                        return;
                    }
                    
                    const match = message.match(/(\d+)\/(\d+)/);
                    if (match) {
                        const [current, total] = match.slice(1).map(Number);
                        streamUI_ID_SUFFIX.updateProgress(current, total);
                    }
                };

                eventSource.onerror = function() {
                    eventSource.close();
                    streamUI_ID_SUFFIX.handleJobComplete();
                };
            }
        """
        js_code = (js_template.replace('ID_SUFFIX', self.id_suffix).replace('ROUTE_PREFIX', self.route_prefix))
        return Div(self.create_progress_card(), self.create_simulator_button(), Script(js_code), Style("""
                .spinner {
                    display: inline-block;
                    width: 20px;
                    height: 20px;
                    border: 3px solid rgba(255,255,255,.3);
                    border-radius: 50%;
                    border-top-color: #fff;
                    animation: spin 1s ease-in-out infinite;
                    margin-left: 10px;
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                .progress-bar {
                    width: 0;
                    height: 20px;
                    background-color: #4CAF50;
                }
                """ + ("""
                .stream-content {
                    height: 200px;
                    overflow-y: auto;
                    border: 1px solid #ddd;
                    padding: 10px;
                    margin-top: 10px;
                }
                """if self.show_stream_content else "")))


stream_simulator = StreamSimulator(app, route_prefix="/stream-sim", id_suffix="")


@rt("/sse")
async def sse_endpoint(request):
    return EventStream(broadcaster.generator())


@app.post("/chat")
async def chat_endpoint(request, message: str):
    await chatq(f"Let the user know {limiter} {message}")
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
    asyncio.create_task(chatq(poke_message))
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


class Chat:
    def __init__(self, app, id_suffix="", base_app=None):
        self.app = app
        self.id_suffix = id_suffix
        self.base_app = base_app
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
            if message.lower().startswith(('!egg', '!easter')):
                easter_emojis = {'egg': '🥚', 'hatching': '🐣', 'rabbit': '🐰', 'sparkles': '✨', 'gift': '🎁', 'magic': '🪄', 'surprise': '🎉', 'treasure': '💎', 'key': '🔑', 'lock': '🔒'}
                prompt = (f"Generate a response in the following format:\n"f"EMOJI: [one emoji name from this list: {', '.join(easter_emojis.keys())}]\n"f"TASK: [max 12 char task name]\n"f"JOKE: [unique 1-2 sentence joke about software Easter eggs]\n\n"f"Make the joke creative and unexpected. Vary your emoji and task name choices.\n"f"Important: Keep the exact format with EMOJI:, TASK:, and JOKE: labels.")
                messages = [{"role": "user", "content": prompt}]
                response = ""
                response = await chatq(prompt, base_app=self.base_app)
                emoji_key = None
                task_name = None
                joke = None
                lines = response.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('EMOJI:'):
                        emoji_key = line[6:].strip().lower()
                    elif line.startswith('TASK:'):
                        task_name = line[5:].strip()
                    elif line.startswith('JOKE:'):
                        joke = line[5:].strip()
                if not emoji_key or emoji_key not in easter_emojis:
                    emoji_key = random.choice(list(easter_emojis.keys()))
                if not task_name:
                    task_name = "EggHunt"
                if not joke:
                    joke = "Found a quirky Easter egg! 🎉"
                chosen_emoji = easter_emojis[emoji_key]
                new_item = todos.insert({"name": f"{chosen_emoji} {task_name}"})
                todo_html = to_xml(render_todo(new_item))
                todo_html = todo_html.replace('<li', f'<li data-id="{new_item.id}" id="todo-{new_item.id}"')
                todo_html = todo_html.replace('<li', '<li hx-swap="beforeend" hx-target="#todo-list"')
                todo_html += f'<script>htmx.process(document.getElementById("todo-{new_item.id}"))</script>'
                await websocket.send_text(todo_html)
                return
            if message.lower().startswith('!help'):
                help_text = """Available commands:
                !test - Run DOM manipulation test
                !egg - Insert a test task
                !help - Show this help message"""
                await websocket.send_text(help_text)
                system_message = generate_system_message()
                await chatq(system_message, role="system", base_app=self)
                return
            append_to_conversation(message, "user")
            parts = message.split('|')
            msg = parts[0]
            verbatim = len(parts) > 1 and parts[1] == 'verbatim'
            raw_response = await chatq(msg, verbatim=verbatim, base_app=self.base_app)
            try:
                response_json = json.loads(raw_response)
                if "action" in response_json:
                    result = await execute_crud_operation(self.base_app, response_json)
                    if isinstance(result, tuple) and len(result) > 1:
                        response_message, new_item = result
                        if new_item:
                            html_content = to_xml(self.base_app.render_item(new_item))
                            await websocket.send_text(html_content)
                        else:
                            await websocket.send_text(response_message)
                    else:
                        await websocket.send_text(result)
            except json.JSONDecodeError:
                pass
            append_to_conversation(raw_response, "assistant")
        except Exception as e:
            self.logger.error(f"Error in handle_chat_message: {e}")
            traceback.print_exc()

    def create_progress_card(self):
        return Card(Header("Chat Playground"), Form(Div(TextArea(id="chat-input", placeholder="Type your message here...", rows="3"), Button("Send", type="submit"), id="chat-form"), onsubmit="sendMessage(event)"), Div(id="chat-messages"), Script("""
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
            """))

    async def handle_websocket(self, websocket: WebSocket):
        try:
            await websocket.accept()
            self.active_websockets.add(websocket)
            self.logger.debug("Chat WebSocket connected")
            while True:
                message = await websocket.receive_text()
                self.logger.debug(f"Received message: {message}")
                try:
                    msg_data = json.loads(message)
                    if "action" in msg_data:
                        result = await execute_crud_operation(self.base_app, msg_data)
                        if isinstance(result, tuple) and len(result) > 0:
                            response, new_item = result
                            html_content = to_xml(render_todo(new_item))
                            swap_instruction = f"""<div hx-swap-oob="beforeend:#todo-list">{html_content}</div>"""
                            await websocket.send_text(swap_instruction)
                        continue
                except json.JSONDecodeError:
                    await self.handle_chat_message(websocket, message)
        except WebSocketDisconnect:
            self.logger.info("WebSocket disconnected")
        except Exception as e:
            self.logger.error(f"Error in WebSocket connection: {str(e)}")
            self.logger.error(traceback.format_exc())
        finally:
            self.active_websockets.discard(websocket)
            self.logger.debug("WebSocket connection closed")


chat = Chat(app, id_suffix="", base_app=todo_app)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True,)


class DOMSkeletonMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        endpoint = request.url.path
        method = request.method
        fig(font='slant', text=f"{method} {endpoint}")
        logger.debug(f"HTTP Request: {method} {endpoint}")
        response = await call_next(request)
        cookie_table = Table(title="Stored Cookie States")
        cookie_table.add_column("Key", style="cyan")
        cookie_table.add_column("Value", style="magenta")
        for key, value in db.items():
            json_value = JSON.from_data(value, indent=2)
            cookie_table.add_row(key, json_value)
        console.print(cookie_table)
        pipeline_table = Table(title="Pipeline States")
        pipeline_table.add_column("URL", style="yellow")
        pipeline_table.add_column("Created", style="magenta")
        pipeline_table.add_column("Updated", style="cyan")
        pipeline_table.add_column("Steps", style="white")
        for record in pipulate.table():
            try:
                state = json.loads(record.data)
                pre_state = json.loads(record.data)
                pipeline_table.add_row(record.url, str(state.get('created', '')), str(state.get('updated', '')), str(len(pre_state) - 2))
            except (json.JSONDecodeError, AttributeError)as e:
                logger.error(f"Error parsing pipeline state for {record.url}: {e}")
                pipeline_table.add_row(record.url, "ERROR", "Invalid State")
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


ALL_ROUTES = list(set(['', todo_app.name, profile_app.name] + MENU_ITEMS))
for item in ALL_ROUTES:
    path = f'/{item}'if item else '/'

    @app.route(path)
    async def home_route(request):
        return await home(request)
app.add_middleware(DOMSkeletonMiddleware)
logger.debug("Application setup completed with DOMSkeletonMiddleware.")
fig(font='slant', text=APP_NAME)
fig(f'MODEL: {MODEL}', font='ogre')
logger.debug(f"Using MODEL: {MODEL}")
print_routes()
fig('Server', font='big')


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
    if not check_syntax(THIS_FILE):
        print("Syntax error detected. Please fix the error and save the file again.")
        return
    max_retries = 3
    for attempt in range(max_retries):
        try:
            os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            print(f"Error restarting server (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("Waiting 5 seconds before retrying...")
                time.sleep(5)
            else:
                print("Max retries reached. Please restart the server manually.")


class ServerRestartHandler(FileSystemEventHandler):
    def on_modified(self, event):
        path = Path(event.src_path)
        if path.suffix == '.py':  # Check if any Python file is modified
            print(f"{path} has been modified. Checking syntax and restarting...")
            restart_server()


def run_server_with_watchdog():
    event_handler = ServerRestartHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=True)
    observer.start()
    try:
        uvicorn.run(app, host="0.0.0.0", port=5001)
    except KeyboardInterrupt:
        observer.stop()
    except Exception as e:
        print(f"Error running server: {e}")
        print("Attempting to restart...")
        restart_server()
    finally:
        observer.join()


if __name__ == "__main__":
    run_server_with_watchdog()

# Context: This code is an intentionally stripped-down, single-tenant, local-first app—more like an Electron app than an enterprise or multi-tenant system. It uses server-side state (via DictLikeDB) and HTMX for UI updates, deliberately avoiding complex ORM or FastAPI patterns. All design decisions (even if they look like anti-patterns) are intentional for local simplicity and observability. Please don't refactor or "fix" these intentional patterns. The CRUD is DRY and the Workflows are WET!
from fasthtml.common import *
import asyncio
import requests
import json
from check_environment import get_best_model
from todo_app import todos, Todo, mk_input as todo_mk_input
from starlette.concurrency import run_in_threadpool
from typing import Callable, Awaitable
from dataclasses import dataclass
from starlette.requests import Request

@dataclass
class Chatter:
    send: Callable[[str], Awaitable[None]]
    update: Callable[[str], Awaitable[None]]
    finish: Callable[[], Awaitable[None]]

@dataclass
class SimpleChatter:
    send: Callable[[str], Awaitable[None]]

async def chat_handler(chatter: Chatter, msg: str):
    await chatter.send(f"You: {msg}")
    
    response = await run_in_threadpool(chat_with_ollama, model, conversation)
    words = response.split()
    
    for i in range(len(words)):
        partial_response = " ".join(words[:i+1])
        await chatter.update(f"Todo App: {partial_response}")
        await asyncio.sleep(0.05)
    
    await chatter.finish()

def render(todo):
    tid = f'todo-{todo.id}'
    checkbox = Input(type="checkbox", 
                     name="english" if todo.done else None, 
                     checked=todo.done,
                     hx_post=f"/toggle/{todo.id}",
                     hx_swap="outerHTML")
    delete = A('Delete', hx_delete=f'/{todo.id}', 
               hx_swap='outerHTML', hx_target=f"#{tid}")
    return Li(checkbox, ' ', todo.title, ' | ', delete,
              id=tid, cls='done' if todo.done else '')

app, rt, todos, Todo = fast_app("data/todo.db", ws_hdr=True, live=True, render=render,
                                id=int, title=str, done=bool, pk="id")

# Choose the best available model
model = get_best_model()

# Define the MATRIX_STYLE constant
MATRIX_STYLE = "color: #00ff00; text-shadow: 0 0 5px #00ff00; font-family: 'Courier New', monospace;"

# Define a new style for user messages
USER_STYLE = "color: #ffff00; text-shadow: 0 0 5px #ffff00; font-family: 'Courier New', monospace;"

# Ollama chat function
def chat_with_ollama(model, messages):
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    if response.status_code == 200:
        return response.json()['message']['content']
    else:
        return f"Error: {response.status_code}, {response.text}"

# Initialize conversation
conversation = [
    {"role": "system", "content": "You are a Todo App with attitude. Be sassy but helpful."},
]

def mk_input():
    return Input(id='msg', name='msg', placeholder='Type a message...', autofocus='autofocus')

async def generate_and_stream_ai_response(prompt):
    response = await run_in_threadpool(chat_with_ollama, model, [{"role": "user", "content": prompt}])
    words = response.split()
    for i in range(len(words)):
        partial_response = " ".join(words[:i+1])
        for u in users.values():
            await u(Div(f"Todo App: {partial_response}", id='msg-list', cls='fade-in',
                        style=MATRIX_STYLE,
                        _=f"this.scrollIntoView({{behavior: 'smooth'}});"))
        await asyncio.sleep(0.05)  # Reduced delay for faster typing

def create_nav_menu():
    common_style = "font-size: 1.1rem; height: 36px; line-height: 36px; display: inline-flex; align-items: center; justify-content: center; margin: 0 3px; border-radius: 9px; padding: 0 0.75rem;"
    return Nav(
        Group(
            Strong("Pipulate", style=f"{common_style} background-color: var(--pico-primary-background); color: var(--pico-primary-inverse);"),
            style="margin-right: auto;"
        ),
        Group(
            Details(
                Summary("Chat Interface", style=f"{common_style} width: 170px; background-color: var(--pico-background-color); border: 1px solid var(--pico-muted-border-color);"),
                Ul(
                    Li(A("Todo Chat", hx_post="/chat/todo", hx_target="#msg-list", hx_swap="innerHTML", onclick="this.closest('details').removeAttribute('open')")),
                    Li(A("Future Chat 1", hx_post="/chat/future1", hx_target="#msg-list", hx_swap="innerHTML", onclick="this.closest('details').removeAttribute('open')")),
                    Li(A("Future Chat 2", hx_post="/chat/future2", hx_target="#msg-list", hx_swap="innerHTML", onclick="this.closest('details').removeAttribute('open')")),
                    Li(A("Future Chat 3", hx_post="/chat/future3", hx_target="#msg-list", hx_swap="innerHTML", onclick="this.closest('details').removeAttribute('open')")),
                    dir="rtl"
                ),
                cls="dropdown"
            ),
            Details(
                Summary("Actions", style=f"{common_style} width: 140px; background-color: var(--pico-background-color); border: 1px solid var(--pico-muted-border-color);"),
                Ul(
                    Li(A("Action 1", hx_post="/action/1", hx_target="#msg-list", hx_swap="innerHTML", onclick="this.closest('details').removeAttribute('open')")),
                    Li(A("Action 2", hx_post="/action/2", hx_target="#msg-list", hx_swap="innerHTML", onclick="this.closest('details').removeAttribute('open')")),
                    Li(A("Action 3", hx_post="/action/3", hx_target="#msg-list", hx_swap="innerHTML", onclick="this.closest('details').removeAttribute('open')")),
                    Li(A("Action 4", hx_post="/action/4", hx_target="#msg-list", hx_swap="innerHTML", onclick="this.closest('details').removeAttribute('open')")),
                    dir="rtl"
                ),
                cls="dropdown"
            ),
            Group(
                Input(
                    placeholder="Search or enter command",
                    name="nav_input",
                    id="nav-input",
                    hx_post="/search",
                    hx_trigger="keyup[keyCode==13]",
                    hx_target="#msg-list",
                    hx_swap="innerHTML"
                ),
                Button(
                    "×",
                    type="button",
                    onclick="document.getElementById('nav-input').value = ''; this.blur();",
                    style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%); width: 18px; height: 18px; font-size: 0.9rem; color: var(--pico-muted-color); opacity: 0.5; background: none; border: none; cursor: pointer; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 50%;"
                ),
                style="display: flex; align-items: center; position: relative;"
            ),
            style="display: flex; align-items: center; gap: 10px;"
        ),
        style="display: flex; align-items: center; gap: 15px; width: 100%; padding: 0.4rem 0.8rem; background-color: var(--pico-background-color); border-radius: 20px;"
    )

@rt('/')
def get(): 
    nav = create_nav_menu()
    
    nav_group = Group(
        nav,
        style="display: flex; align-items: center; margin-bottom: 20px; gap: 20px;"
    )
    
    return Titled("Pipulate Todo App", 
        Container(
            nav_group,
            Grid(
                Div(
                    Card(
                        H2("Todo List"),
                        Ul(*[render(todo) for todo in todos()], id='todo-list'),
                        header=Form(
                            Group(
                                todo_mk_input(),
                                Button("Add", type="submit")
                            ),
                            hx_post="/todo",
                            hx_swap="beforeend",
                            hx_target="#todo-list"
                        )
                    ),
                ),
                Div(
                    Card(
                        H2("Chat Interface"),
                        Div(id='msg-list', cls='overflow-auto', style='height: 40vh;'),
                        footer=Form(
                            Group(
                                mk_input(),
                                Button("Send", type='submit', ws_send=True)
                            )
                        )
                    ),
                ),
                cls="grid",
                style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px;"
            ),
            # Fixed position Poke Todo List link
            Div(
                A("Poke Todo List", 
                  hx_post="/poke", 
                  hx_target="#msg-list", 
                  hx_swap="innerHTML",
                  cls="button"),
                style="position: fixed; bottom: 20px; right: 20px; z-index: 1000;"
            )
        ),
        hx_ext='ws',
        ws_connect='/ws',
        data_theme="dark"
    )

@rt('/todo')
async def post(todo:Todo):
    inserted_todo = todos.insert(todo)
    
    # Adjusted prompt for brevity
    asyncio.create_task(generate_and_stream_ai_response(
        f"New todo: '{todo.title}'. Brief, sassy comment or advice in under 30 words."
    ))
    
    return render(inserted_todo), todo_mk_input()

@rt('/{tid}')
async def delete(tid:int):
    todo = todos[tid]  # Get the todo item before deleting it
    todos.delete(tid)
    
    # Adjusted prompt for brevity
    asyncio.create_task(generate_and_stream_ai_response(
        f"Todo '{todo.title}' deleted. Brief, sassy reaction in under 30 words."
    ))
    
    return ''  # Return an empty string to remove the item from the DOM

@rt('/toggle/{tid}')
async def post(tid: int):
    todo = todos[tid]
    old_status = "Done" if todo.done else "Not Done"
    todo.done = not todo.done
    new_status = "Done" if todo.done else "Not Done"
    updated_todo = todos.update(todo)
    
    # Adjusted prompt for brevity
    asyncio.create_task(generate_and_stream_ai_response(
        f"Todo '{todo.title}' toggled from {old_status} to {new_status}. Brief, sassy comment in under 30 words."
    ))
    
    return Input(type="checkbox", 
                 name="english" if updated_todo.done else None, 
                 checked=updated_todo.done,
                 hx_post=f"/toggle/{updated_todo.id}",
                 hx_swap="outerHTML")

users = {}
def on_conn(ws, send): users[str(id(ws))] = send
def on_disconn(ws): users.pop(str(id(ws)), None)

@app.ws('/ws', conn=on_conn, disconn=on_disconn)
async def ws(msg: str):
    if msg:
        global conversation
        conversation.append({"role": "user", "content": msg})
        
        # Send user message immediately with yellow color
        for u in users.values():
            await u(Div(f"You: {msg}", id='msg-list', cls='fade-in', style=USER_STYLE))
        
        # Start streaming response
        response = await run_in_threadpool(chat_with_ollama, model, conversation)
        conversation.append({"role": "assistant", "content": response})
        
        # Simulate typing effect (AI response remains green)
        words = response.split()
        for i in range(len(words)):
            partial_response = " ".join(words[:i+1])
            for u in users.values():
                await u(Div(f"Todo App: {partial_response}", id='msg-list', cls='fade-in',
                            style=MATRIX_STYLE,
                            _=f"this.scrollIntoView({{behavior: 'smooth'}});"))
            await asyncio.sleep(0.05)  # Reduced delay for faster typing
        
        # Clear the input field after the response is complete and keep it focused
        clear_input = Input(id='msg', name='msg', placeholder='Type a message...', value='', 
                            hx_swap_oob="true", autofocus='autofocus')
        for u in users.values():
            await u(clear_input)

@rt('/poke')
async def poke():
    response = await run_in_threadpool(chat_with_ollama, model, [
        {"role": "system", "content": "You are a sassy Todo List. Respond briefly to being poked."},
        {"role": "user", "content": "You've been poked. React in under 30 words."}
    ])
    return Div(f"Todo App: {response}", id='msg-list', cls='fade-in', style=MATRIX_STYLE)

async def quick_message(chatter: SimpleChatter, prompt: str):
    response = await run_in_threadpool(chat_with_ollama, model, [{"role": "user", "content": prompt}])
    words = response.split()
    for i in range(len(words)):
        partial_response = " ".join(words[:i+1])
        await chatter.send(f"Todo App: {partial_response}")
        await asyncio.sleep(0.05)  # Adjust this delay as needed

@rt('/chat/{chat_type}')
async def chat_interface(chat_type: str):
    prompt = f"Initiate a conversation about {chat_type}. Be brief and sassy in under 30 words."
    chatter = SimpleChatter(send=lambda msg: asyncio.gather(*[u(Div(msg, id='msg-list', cls='fade-in', style=MATRIX_STYLE)) for u in users.values()]))
    asyncio.create_task(quick_message(chatter, prompt))
    return ''

@rt('/action/{action_id}')
async def perform_action(action_id: int):
    prompt = f"Perform action {action_id}. Describe what you did briefly and sassily in under 30 words."
    chatter = SimpleChatter(send=lambda msg: asyncio.gather(*[u(Div(msg, id='msg-list', cls='fade-in', style=MATRIX_STYLE)) for u in users.values()]))
    asyncio.create_task(quick_message(chatter, prompt))
    return ''

@rt('/toggle-theme', methods=['POST'])
def toggle_theme():
    return ''  # We're handling the theme change client-side, so we just return an empty string

@rt('/search', methods=['POST'])
async def search(nav_input: str):
    prompt = f"The user searched for: '{nav_input}'. Respond briefly acknowledging the search."
    chatter = SimpleChatter(send=lambda msg: asyncio.gather(*[u(Div(msg, id='msg-list', cls='fade-in', style=MATRIX_STYLE)) for u in users.values()]))
    asyncio.create_task(quick_message(chatter, prompt))
    return ''

serve()
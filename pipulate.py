from fasthtml.common import *
import asyncio
import requests
import json
from check_environment import get_best_model
from todo_app import todos, Todo, mk_input as todo_mk_input
from starlette.concurrency import run_in_threadpool
from typing import Callable, Awaitable
from dataclasses import dataclass

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

@rt('/')
def get(): 
    todo_form = Form(Group(todo_mk_input(),
                    Button('Add')),
                    hx_post='/todo', target_id='todo-list', hx_swap="beforeend")
    
    # Create two navigation dropdown menus
    nav_dropdown1 = Select(
        Option("Select Chat Interface", selected=True, disabled=True, value=""),
        Option("Todo Chat"),
        Option("Future Chat 1"),
        Option("Future Chat 2"),
        Option("Future Chat 3"),
        name="nav1",
        aria_label="Navigation 1",
        style="padding: 10px; margin-right: 10px; flex: 1;"
    )
    
    nav_dropdown2 = Select(
        Option("Select Action", selected=True, disabled=True, value=""),
        Option("Action 1"),
        Option("Action 2"),
        Option("Action 3"),
        Option("Action 4"),
        name="nav2",
        aria_label="Navigation 2",
        style="padding: 10px; margin-right: 10px; flex: 1;"
    )
    
    # Add a new input field
    nav_input = Input(
        placeholder="Search or enter command",
        name="nav_input",
        style="padding: 10px; flex: 2;"
    )
    
    # Group the two dropdowns and the input field
    nav_group = Group(
        nav_dropdown1,
        nav_dropdown2,
        nav_input,
        style="display: flex; margin-bottom: 20px; width: 100%;"
    )
    
    return Titled("Pipulate Todo App", 
        Container(
            nav_group,  # Add the grouped dropdown menus and input field at the top
            Grid(
                Div(
                    Card(
                        H2("Todo List"),
                        Ul(*[render(todo) for todo in todos()], id='todo-list'),
                        header=todo_form
                    ),
                ),
                Div(
                    Card(
                        H2("Chat Interface"),
                        Div(id='msg-list', cls='overflow-auto', style='height: 40vh;'),  # Changed from 60vh to 40vh
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

async def generate_and_stream_ai_response(prompt):
    conversation.append({"role": "user", "content": prompt})
    response = await run_in_threadpool(chat_with_ollama, model, conversation)
    conversation.append({"role": "assistant", "content": response})
    
    # Simulate faster typing effect
    words = response.split()
    for i in range(len(words)):
        partial_response = " ".join(words[:i+1])
        for u in users.values():
            await u(Div(f"Todo App: {partial_response}", id='msg-list', cls='fade-in',
                        style=MATRIX_STYLE,
                        _=f"this.scrollIntoView({{behavior: 'smooth'}});"))
        await asyncio.sleep(0.05)  # Reduced delay for faster typing

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
        
        # Send user message immediately
        for u in users.values():
            await u(Div(f"You: {msg}", id='msg-list', cls='fade-in', style=MATRIX_STYLE))
        
        # Start streaming response
        response = await run_in_threadpool(chat_with_ollama, model, conversation)
        conversation.append({"role": "assistant", "content": response})
        
        # Simulate typing effect
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
    conversation.append({"role": "user", "content": prompt})
    response = await run_in_threadpool(chat_with_ollama, model, conversation)
    conversation.append({"role": "assistant", "content": response})
    return await chatter.send(f"Todo App: {response}")

serve()

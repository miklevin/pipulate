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
    return Titled("Pipulate Todo App", 
        Container(
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
                        Div(id='msg-list', cls='overflow-auto', style='height: 60vh;'),
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
                  hx_swap="outerHTML",
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
    
    # Start the AI response in the background
    asyncio.create_task(generate_and_stream_ai_response(
        f"A new todo item was added: '{todo.title}'. Give a brief, sassy comment or advice in 40 words or less."
    ))
    
    # Return the inserted todo item immediately
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
    
    # Start the AI response for deletion in the background
    asyncio.create_task(generate_and_stream_ai_response(
        f"The todo item '{todo.title}' was just deleted. Give a brief, sassy comment or reaction in 40 words or less."
    ))
    
    return ''  # Return an empty string to remove the item from the DOM

@rt('/toggle/{tid}')
async def post(tid: int):
    todo = todos[tid]
    old_status = "Done" if todo.done else "Not Done"
    todo.done = not todo.done
    new_status = "Done" if todo.done else "Not Done"
    updated_todo = todos.update(todo)
    
    # Start the AI response for toggle in the background
    asyncio.create_task(generate_and_stream_ai_response(
        f"The todo item '{todo.title}' was just toggled from {old_status} to {new_status}. Give a brief, sassy comment or reaction in 40 words or less."
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
        
        user_id = str(id(ws))
        async def send(content: str):
            await users[user_id](Div(content, id='msg-list', cls='fade-in', style=MATRIX_STYLE))
        
        async def update(content: str):
            await users[user_id](Div(content, id='msg-list', cls='fade-in', style=MATRIX_STYLE,
                                     _="this.scrollIntoView({behavior: 'smooth'});"))
        
        async def finish():
            clear_input = Input(id='msg', name='msg', placeholder='Type a message...', value='', 
                                hx_swap_oob="true", autofocus='autofocus')
            await users[user_id](clear_input)
        
        chatter = Chatter(send, update, finish)
        await chat_handler(chatter, msg)

@rt('/poke')
async def poke():
    response = await run_in_threadpool(chat_with_ollama, model, [
        {"role": "system", "content": "You are a sassy Todo List. Respond briefly to being poked."},
        {"role": "user", "content": "You've just been poked. React in 20 words or less."}
    ])
    return Div(f"Todo App: {response}", id='msg-list', cls='fade-in', style=MATRIX_STYLE)

async def quick_message(chatter: SimpleChatter, prompt: str):
    conversation.append({"role": "user", "content": prompt})
    response = await run_in_threadpool(chat_with_ollama, model, conversation)
    conversation.append({"role": "assistant", "content": response})
    return await chatter.send(f"Todo App: {response}")

serve()

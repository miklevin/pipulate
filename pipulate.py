from fasthtml.common import *
import asyncio
import requests
import json
from check_environment import get_best_model
from todo_app import render, todos, Todo, mk_input as todo_mk_input
from starlette.concurrency import run_in_threadpool

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
                        Ul(*todos(), id='todo-list'),
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
                style="display: grid; grid-template-columns: 3fr 1fr; gap: 20px;"
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
    return inserted_todo, todo_mk_input()

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
async def get(tid:int):
    todo = todos[tid]
    old_status = "Done" if todo.done else "Not Done"
    todo.done = not todo.done
    new_status = "Done" if todo.done else "Not Done"
    updated_todo = todos.update(todo)
    
    # Start the AI response for toggle in the background
    asyncio.create_task(generate_and_stream_ai_response(
        f"The todo item '{todo.title}' was just toggled from {old_status} to {new_status}. Give a brief, sassy comment or reaction in 40 words or less."
    ))
    
    return updated_todo

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
        response = chat_with_ollama(model, conversation)
        conversation.append({"role": "assistant", "content": response})
        
        # Simulate typing effect
        words = response.split()
        for i in range(len(words)):
            partial_response = " ".join(words[:i+1])
            for u in users.values():
                await u(Div(f"Todo App: {partial_response}", id='msg-list', cls='fade-in',
                            style=MATRIX_STYLE,
                            _=f"this.scrollIntoView({{behavior: 'smooth'}});"))
            await asyncio.sleep(0.1)  # Adjust delay as needed
        
        # Clear the input field after the response is complete and keep it focused
        clear_input = Input(id='msg', name='msg', placeholder='Type a message...', value='', 
                            hx_swap_oob="true", autofocus='autofocus')
        for u in users.values():
            await u(clear_input)

serve()

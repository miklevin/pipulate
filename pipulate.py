from fasthtml.common import *
import asyncio
import requests
import json
from check_environment import get_best_model
from todo_app import render, todos, Todo, mk_input as todo_mk_input

app, rt, todos, Todo = fast_app("data/todo.db", ws_hdr=True, live=True, render=render,
                                id=int, title=str, done=bool, pk="id")

# Choose the best available model
model = get_best_model()

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
                Card(
                    H2("Todo List"),
                    Ul(*todos(), id='todo-list'),
                    header=todo_form
                ),
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
                cls="grid"
            )
        ),
        hx_ext='ws',
        ws_connect='/ws',
        data_theme="dark"
    )

@rt('/todo')
async def post(todo:Todo):
    inserted_todo = todos.insert(todo)
    
    # Prompt Ollama about the new todo item
    prompt = f"A new todo item was added: '{todo.title}'. Any sassy comments or advice?"
    conversation.append({"role": "user", "content": prompt})
    response = await run_in_threadpool(chat_with_ollama, model, conversation)
    conversation.append({"role": "assistant", "content": response})
    
    # Send the Ollama response to all connected clients
    for u in users.values():
        await u(Div(f"Todo App: {response}", id='msg-list', cls='fade-in',
                    style="color: #00ff00; text-shadow: 0 0 5px #00ff00; font-family: 'Courier New', monospace;"))
    
    return inserted_todo, todo_mk_input()

@rt('/{tid}')
def delete(tid:int): todos.delete(tid)

@rt('/toggle/{tid}')
def get(tid:int):
    todo = todos[tid]
    todo.done = not todo.done
    return todos.update(todo)

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
            await u(Div(f"You: {msg}", id='msg-list', cls='fade-in',
                        style="color: #00ff00; text-shadow: 0 0 5px #00ff00; font-family: 'Courier New', monospace;"))
        
        # Start streaming response
        response = chat_with_ollama(model, conversation)
        conversation.append({"role": "assistant", "content": response})
        
        # Simulate typing effect
        words = response.split()
        for i in range(len(words)):
            partial_response = " ".join(words[:i+1])
            for u in users.values():
                await u(Div(f"Todo App: {partial_response}", id='msg-list', cls='fade-in',
                            style="color: #00ff00; text-shadow: 0 0 5px #00ff00; font-family: 'Courier New', monospace;",
                            _=f"this.scrollIntoView({{behavior: 'smooth'}});"))
            await asyncio.sleep(0.1)  # Adjust delay as needed
        
        # Clear the input field after the response is complete and keep it focused
        clear_input = Input(id='msg', name='msg', placeholder='Type a message...', value='', 
                            hx_swap_oob="true", autofocus='autofocus')
        for u in users.values():
            await u(clear_input)

serve()

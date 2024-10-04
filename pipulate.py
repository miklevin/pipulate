from fasthtml.common import *
import asyncio
import requests
import json

app, rt = fast_app(ws_hdr=True, live=True)

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
model = "llama3.2"  # or whatever model you have installed
conversation = [
    {"role": "system", "content": "You are a Todo App with attitude. Be sassy but helpful."},
]

@rt('/')
def get(): 
    return Titled("Pipulate Todo App", 
        Div(id='msg-list'),
        Form(Input(id='msg', name='msg', placeholder='Type a message...'),
             Button("Send", type='submit', ws_send=True)),
        hx_ext='ws',
        ws_connect='/ws'
    )

users = {}
def on_conn(ws, send): users[str(id(ws))] = send
def on_disconn(ws): users.pop(str(id(ws)), None)

@app.ws('/ws', conn=on_conn, disconn=on_disconn)
async def ws(msg: str):
    if msg:
        global conversation
        conversation.append({"role": "user", "content": msg})
        response = chat_with_ollama(model, conversation)
        conversation.append({"role": "assistant", "content": response})
        
        # Send the response to all connected users
        for u in users.values():
            await u(Div(f"You: {msg}", id='msg-list'))
            await u(Div(f"Todo App: {response}", id='msg-list'))

serve()

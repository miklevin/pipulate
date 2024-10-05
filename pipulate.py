from fasthtml.common import *
import asyncio
import requests
import json
from check_environment import get_best_model

app, rt = fast_app(ws_hdr=True, live=True)

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
    return Titled("Pipulate Todo App", 
        Container(
            Card(
                Div(id='msg-list', cls='overflow-auto', style='height: 70vh;'),
                footer=Form(
                    Group(
                        mk_input(),
                        Button("Send", type='submit', ws_send=True)
                    )
                )
            )
        ),
        hx_ext='ws',
        ws_connect='/ws',
        data_theme="dark"
    )

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

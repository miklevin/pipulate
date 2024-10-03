from fasthtml.common import *
import asyncio

app = FastHTML(ws_hdr=True)
rt = app.route

msgs = []
@rt('/')
def home(): return Div(
    Div("foo", id='msg-list'),
    Form(Input(id='msg', name='msg', placeholder='Type a message...'),  # Input for new messages
         Button("Send", type='submit', ws_send=True)),  # Button to send message
    hx_ext='ws',  # Enable HTMX WebSocket extension
    ws_connect='/ws'  # Connect to the WebSocket endpoint
)

users = {}
def on_conn(ws, send): users[str(id(ws))] = send
def on_disconn(ws): users.pop(str(id(ws)), None)

@app.ws('/ws', conn=on_conn, disconn=on_disconn)
async def ws(msg: str):
    if msg:  # Check if the message is not empty
        msgs.append(msg)  # Append the message to the list
        # Simulate a long-running task
        await long_running_task(msg)  # Call the long-running task

async def long_running_task(msg: str):
    # Simulate a long-running task
    for i in range(5):
        await asyncio.sleep(1)  # Simulate processing time
        # Send progress updates to all users
        for u in users.values():
            await u(Div(f"Processing '{msg}'... Step {i + 1}/5", id='msg-list'))

    # Final update after the task is complete
    for u in users.values():
        await u(Div(f"Task complete for message: '{msg}'", id='msg-list'))

serve()
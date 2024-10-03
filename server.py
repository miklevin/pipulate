from fasthtml.common import *

app = FastHTML(ws_hdr=True)  # Enable WebSocket header
rt = app.route

# Home route
@rt('/')
def home():
    cts = Div(
        Div(id='notifications'),  # Div to display notifications
        Form(Input(id='msg'), id='form', ws_send=True),  # Form to send messages
        hx_ext='ws',  # Enable HTMX WebSocket extension
        ws_connect='/ws'  # Connect to the WebSocket endpoint
    )
    return Titled('WebSocket Test', cts)

# WebSocket connection management
users = {}

def on_conn(ws, send):
    users[str(id(ws))] = send  # Store the send function for the connected user

def on_disconn(ws):
    users.pop(str(id(ws)), None)  # Remove the user on disconnect

# WebSocket route
@app.ws('/ws', conn=on_conn, disconn=on_disconn)
async def ws(msg: str, send):
    await send(Div('Hello ' + msg, id='notifications'))  # Send a greeting message
    # Optionally, you can broadcast the message to all connected users
    for u in users.values():
        await u(Div('User said: ' + msg, id='notifications'))

# Start the server
serve()
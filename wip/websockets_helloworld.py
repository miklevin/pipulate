import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from fastapi.responses import HTMLResponse  # Add this import

app = FastAPI()

# Global dictionary to hold queues for communication between tasks and WebSocket connections
task_queues = {}

@app.get("/", response_class=HTMLResponse)  # Specify the response class
async def get():
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <title>WebSocket with FastAPI</title>
            <script type="text/javascript">
                function startTask() {
                    let ws = new WebSocket("ws://localhost:8000/ws");
                    ws.onmessage = function(event) {
                        document.getElementById("log").innerHTML += "<br>" + event.data;
                    };
                    ws.onclose = function() {
                        document.getElementById("log").innerHTML += "<br>Task complete.";
                    };
                }
            </script>
        </head>
        <body>
            <h1>FastAPI WebSocket Example</h1>
            <button onclick="startTask()">Start Long Task</button>
            <div id="log"></div>
        </body>
    </html>
    """

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    queue = asyncio.Queue()
    task_id = id(websocket)
    task_queues[task_id] = queue

    # Start keep-alive task
    asyncio.create_task(keep_alive(websocket))

    try:
        # Start long-running task in the background
        asyncio.create_task(long_running_task(queue))

        # Stream messages from the queue to the WebSocket
        while True:
            message = await queue.get()
            if websocket.application_state == WebSocketState.CONNECTED:
                await websocket.send_text(message)
            else:
                break
    except WebSocketDisconnect:
        pass
    finally:
        del task_queues[task_id]

async def long_running_task(queue):
    for i in range(5):
        await asyncio.sleep(1)  # Simulating a long task
        await queue.put(f"Step {i + 1} completed")
    await queue.put("Task complete")

# Add a keep-alive mechanism to ensure the connection remains open
async def keep_alive(websocket: WebSocket):
    while True:
        await asyncio.sleep(10)  # Send a ping every 10 seconds
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.send_text("ping")  # Optional: send a ping message

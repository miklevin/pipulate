from fastcore.xml import *
import logging
import asyncio
import random
import json
from loguru import logger
from fasthtml.common import *

logger = logging.getLogger(__name__)
from server import (
    chatq,                      # Core LLM query function
    append_to_conversation,     # Manage conversation history
    read_training,              # Load system prompts
    TONE,                       # Global conversation settings
    MODEL,                      # Model identifier
    MAX_LLM_RESPONSE_WORDS,     # Response length control
)

limiter = ""

async def my_plugin_llm_handler(message):
    # Add user message to conversation
    append_to_conversation(message, "user")
    
    # Query the LLM
    response = await chatq(
        message,
        verbatim=False,  # Process with the AI's personality
        # role="user"    # Default is user, can be omitted
    )
    
    # Store the response
    append_to_conversation(response, "assistant")
    
    return response

class StreamSimulatorPlugin:
    NAME = "stream_simulator"
    DISPLAY_NAME = "Stream Simulator"
    ENDPOINT_MESSAGE = "Stream Simulator app is where you simulate a long-running server-side process. Press the 'Start Stream Simulation' button to begin."
    id_suffix = "1"
    route_prefix = "/stream-sim"
    show_stream_content = False

    
    def __init__(self, app, pipulate, pipeline, db):
        self.app = app
        self.pipulate = pipulate
        self.db = db
        self.logger = logger
        logger.debug(f"HelloPlugin initialized with NAME: {self.NAME}")
        NAME = "stream_simulator"
        DISPLAY_NAME = "Stream Simulator"
        ENDPOINT_MESSAGE = "Stream Simulator app is where you simulate a long-running server-side process. Press the 'Start Stream Simulation' button to begin."
    
        self.app.route(f"{self.route_prefix}/stream")(self.stream_handler)
        self.app.route(f"{self.route_prefix}/start", methods=["POST"])(self.start_handler)

    def landing(self, request):
        """Landing page for the Hello plugin"""
        logger.debug("HelloPlugin.landing method called")
        return Div(
            H1("Hello Plugin"),
            P("This is a simple example plugin for Pipulate."),
            _class="container"
        )
    
    # async def render(self, render_items=None):
    #     return Div(
    #         H2("Hello from Plugin"),
    #         P("This is a simple plugin example.")
    #     )

    async def stream_handler(self, request):
        async def event_generator():
            try:
                async for chunk in self.generate_chunks():
                    if isinstance(chunk, dict):
                        yield f"data: {json.dumps(chunk)}\n\n"
                    else:
                        yield f"data: {chunk}\n\n"
                yield f"data: Simulation complete\n\n"
                yield f"data: {json.dumps({'type': 'swap', 'target': '#stream_sim_button', 'content': self.create_simulator_button().to_html()})}\n\n"
            except Exception as e:
                self.logger.error(f"Error in stream: {str(e)}")
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
        return EventStream(event_generator())

    async def stream_handler(self, request):
        async def event_generator():
            try:
                async for chunk in self.generate_chunks():
                    if isinstance(chunk, dict):
                        yield f"data: {json.dumps(chunk)}\n\n"
                    else:
                        yield f"data: {chunk}\n\n"
                yield f"data: Simulation complete\n\n"
                yield f"data: {json.dumps({'type': 'swap', 'target': '#stream_sim_button', 'content': self.create_simulator_button().to_html()})}\n\n"
            except Exception as e:
                self.logger.error(f"Error in stream: {str(e)}")
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
        return EventStream(event_generator())

    async def start_handler(self, request):
        await chatq(f"Tell the user {limiter} that you see that they have started a ""streaming simulation and will keep them updated on progress.")
        return Button("Streaming...", cls="stream-sim-button", id="stream_sim_button", disabled="true", aria_busy="true")

    async def stream_handler(self, request):
        async def event_generator():
            try:
                async for chunk in self.generate_chunks():
                    if isinstance(chunk, dict):
                        yield f"data: {json.dumps(chunk)}\n\n"
                    else:
                        yield f"data: {chunk}\n\n"
                yield f"data: Simulation complete\n\n"
                yield f"data: {json.dumps({'type': 'swap', 'target': '#stream_sim_button', 'content': self.create_simulator_button().to_html()})}\n\n"
            except Exception as e:
                self.logger.error(f"Error in stream: {str(e)}")
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
        return EventStream(event_generator())

    async def start_handler(self, request):
        await chatq(f"Tell the user {limiter} that you see that they have started a ""streaming simulation and will keep them updated on progress.")
        return Button("Streaming...", cls="stream-sim-button", id="stream_sim_button", disabled="true", aria_busy="true")

    async def generate_chunks(self, total_chunks=100, delay_range=(0.1, 0.5)):
        try:
            logger.debug("Generating Chunks")
            self.logger.debug(f"Generating chunks: total={total_chunks}, delay={delay_range}")
            chat_tasks = []
            for i in range(total_chunks):
                chunk = f"Simulated chunk {i + 1}/{total_chunks}"
                self.logger.debug(f"Generated chunk: {chunk}")
                yield chunk
                if i + 1 == 1:
                    chat_tasks.append(asyncio.create_task(chatq(f"Tell the user {limiter} streaming is in progress, fake as it may be.")))
                elif i + 1 == 15:
                    chat_tasks.append(asyncio.create_task(chatq(f"Tell the user {limiter} the job is 25% done, fake as it may be.")))
                elif i + 1 == 40:
                    chat_tasks.append(asyncio.create_task(chatq(f"Tell the user {limiter} the job is 50% over half way there, fake as it may be.")))
                elif i + 1 == 65:
                    chat_tasks.append(asyncio.create_task(chatq(f"Tell the user {limiter} the job is nearly complete, fake as it may be.")))
                elif i + 1 == 85:
                    chat_tasks.append(asyncio.create_task(chatq(f"Tell the user in under 20 words just a little bit more, fake as it may be.")))
                await asyncio.sleep(random.uniform(*delay_range))
            self.logger.debug("Finished generating all chunks")
            yield json.dumps({"status": "complete"})
            if chat_tasks:
                await asyncio.gather(*chat_tasks)
            await chatq(f"Congratulate the user {limiter}. The long-running job is done, fake as it may be!")
        except Exception as e:
            self.logger.error(f"Error in chunk generation: {str(e)}")
            yield json.dumps({"status": "error", "message": str(e)})

    def create_progress_card(self):
        self.logger.debug("Creating progress card")
        elements = [H3("Streaming Progress"), Div(id=f"stream-progress{self.id_suffix}", cls="progress-bar")]
        if self.show_stream_content:
            elements.append(Div(id=f"stream-content{self.id_suffix}", cls="stream-content"))
        return Card(*elements)

    def create_simulator_button(self):
        self.logger.debug("Creating simulator button")
        return Button("Start Stream Simulation", onclick=f"startSimulation_{self.id_suffix}()", cls="stream-sim-button", id=f"stream_sim_button{self.id_suffix}")

    async def render(self):
        logger.debug("Rendering Stream Simulator")
        js_template = r"""
            class StreamUI {
                constructor(idSuffix) {
                    this.idSuffix = idSuffix;
                    this.progressBar = document.getElementById('stream-progress' + idSuffix);
                    this.streamContent = document.getElementById('stream-content' + idSuffix);
                    this.button = document.getElementById('stream_sim_button' + idSuffix);
                }

                setButtonState(isRunning) {
                    this.button.disabled = isRunning;
                    this.button.setAttribute('aria-busy', isRunning);
                    this.button.textContent = isRunning ? 'Streaming...' : 'Start Stream Simulation';
                }

                updateProgress(current, total) {
                    const percentage = (current / total) * 100;
                    this.progressBar.style.transition = 'width 0.3s ease-out';
                    this.progressBar.style.width = percentage + '%';
                }

                resetProgress() {
                    // Smooth transition back to 0
                    this.progressBar.style.transition = 'width 0.5s ease-out';
                    this.progressBar.style.width = '0%';
                }

                appendMessage(message) {
                    if (this.streamContent) {  // Only append if element exists
                        this.streamContent.innerHTML += message + '<br>';
                        this.streamContent.scrollTop = this.streamContent.scrollHeight;
                    }
                }

                handleJobComplete() {
                    this.resetProgress();
                    this.setButtonState(false);
                }
            }

            const streamUI_ID_SUFFIX = new StreamUI('ID_SUFFIX');

            function startSimulation_ID_SUFFIX() {
                streamUI_ID_SUFFIX.setButtonState(true);
                
                const eventSource = new EventSource('ROUTE_PREFIX/stream');
                
                eventSource.onmessage = function(event) {
                    const message = event.data;
                    streamUI_ID_SUFFIX.appendMessage(message);
                    
                    if (message.includes('Simulation complete')) {
                        eventSource.close();
                        streamUI_ID_SUFFIX.handleJobComplete();
                        return;
                    }
                    
                    const match = message.match(/(\d+)\/(\d+)/);
                    if (match) {
                        const [current, total] = match.slice(1).map(Number);
                        streamUI_ID_SUFFIX.updateProgress(current, total);
                    }
                };

                eventSource.onerror = function() {
                    eventSource.close();
                    streamUI_ID_SUFFIX.handleJobComplete();
                };
            }
        """
        js_code = (js_template.replace('ID_SUFFIX', self.id_suffix).replace('ROUTE_PREFIX', self.route_prefix))
        return Div(self.create_progress_card(), self.create_simulator_button(), Script(js_code), Style("""
                .spinner {
                    display: inline-block;
                    width: 20px;
                    height: 20px;
                    border: 3px solid rgba(255,255,255,.3);
                    border-radius: 50%;
                    border-top-color: #fff;
                    animation: spin 1s ease-in-out infinite;
                    margin-left: 10px;
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                .progress-bar {
                    width: 0;
                    height: 20px;
                    background-color: #4CAF50;
                }
                """ + ("""
                .stream-content {
                    height: 200px;
                    overflow-y: auto;
                    border: 1px solid #ddd;
                    padding: 10px;
                    margin-top: 10px;
                }
                """if self.show_stream_content else "")))
# 
# 
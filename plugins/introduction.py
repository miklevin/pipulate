from fastcore.xml import *
import logging
from loguru import logger
from fasthtml.common import *

from server import (
    hot_prompt_injection,  # Function to inject prompts into conversation
    APP_NAME,              # Global app name
    limiter,               # For LLM response limiting
)

class IntroductionPlugin:
    NAME = "introduction"
    DISPLAY_NAME = "Introduction"
    ENDPOINT_MESSAGE = "This demo showcases Hot Prompt Injection - a technique where the AI assistant learns new information through UI interactions."
    TRAINING_PROMPT = "introduction.md"  # Markdown file for training
    
    def __init__(self, app, pipulate, pipeline, db):
        """Initialize the Introduction plugin."""
        self.app = app
        self.pipulate = pipulate
        self.pipeline = pipeline
        self.db = db
        self.route_prefix = "/introduction"
        self.logger = logger.bind(name="Introduction")
        
        # Register routes
        self.app.post(f"{self.route_prefix}/start-chat")(self.start_chat)

    async def landing(self, request):
        """Landing page for the Introduction plugin."""
        self.logger.debug("Introduction.landing method called")
        return await self.render()
    
    async def start_chat(self, request):
        """Initiate chat with hot prompt injection."""
        self.logger.debug("Starting welcome chat")
        try:
            # Inject the introduction prompt into conversation
            hot_prompt_injection(self.TRAINING_PROMPT)
            
            # Send a message to the AI assistant
            await self.pipulate.stream(
                f"The app name you're built into is {APP_NAME}. Please {limiter} introduce yourself and explain how you can help. Tell them to ask you the secret word.", 
                spaces_after=1
            )
            return "Chat initiated"
        except Exception as e:
            self.logger.error(f"Error starting chat: {str(e)}")
            return "I'm having trouble connecting right now. Please try again in a moment."

    async def render(self, render_items=None):
        """Render the Introduction UI."""
        self.logger.debug("Rendering introduction content")
        return Card(
            H3(f"Meet {APP_NAME}"),
            P(
                "This demo showcases \"Hot Prompt Injection\" - a technique where "
                "the AI assistant learns new information through UI interactions "
                "so it knows what it needs to know to help you right when it "
                "needs to help you."
            ),
            P(
                "Try asking the AI assistant \"What's the secret word?\" right "
                "now - it will give you the wrong answer. Then click the button "
                "below to invisibly teach the AI a secret word, and ask the same "
                "question again (hint: it's the opposite of Ephemeral)."
            ),
            Div(style="margin-bottom: 20px;"),
            Div(
                Button(
                    "Teach AI assistant secret word",
                    hx_post=f"{self.route_prefix}/start-chat",
                    hx_swap="none",
                    hx_trigger="click, htmx:afterRequest[document.getElementById('msg').focus()]",
                    style="margin-top: 10px;"
                )
            ),
            id="intro-card",
        )

    def get_training_prompt(self):
        """Return the training prompt for this plugin."""
        return self.TRAINING_PROMPT 
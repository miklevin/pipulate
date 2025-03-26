from fastcore.xml import *
import logging

logger = logging.getLogger(__name__)

class HelloPlugin:
    NAME = "hello"
    DISPLAY_NAME = "Hello Plugin"
    ENDPOINT_MESSAGE = "This is a simple plugin example."
    
    def __init__(self, app, pipulate, pipeline, db):
        self.app = app
        self.pipulate = pipulate
        self.pipeline = pipeline
        self.db = db
        logger.debug(f"HelloPlugin initialized with NAME: {self.NAME}")
    
    def landing(self, request):
        """Landing page for the Hello plugin"""
        logger.debug("HelloPlugin.landing method called")
        return Div(
            H1("Hello Plugin"),
            P("This is a simple example plugin for Pipulate."),
            _class="container"
        )
    
    async def render(self, render_items=None):
        return Div(
            H2("Hello from Plugin"),
            P("This is a simple plugin example.")
        )

# Don't register here - let the discovery process handle it
# plugin_registry.register(HelloPlugin())
from fastcore.xml import *
import logging

logger = logging.getLogger(__name__)

class ShimPlugin:
    NAME = "shim"
    DISPLAY_NAME = "Shim"
    ENDPOINT_MESSAGE = "This is a simple plugin example."
    
    def __init__(self, app, pipulate, pipeline, db):
        logger.debug(f"ShimPlugin initialized with NAME: {self.NAME}")
    
    async def landing(self, request):
        """Activates plugin import."""
        logger.debug("ShimPlugin.landing method called")
    
    async def render(self, render_items=None):
        """Always appears in create_grid_left."""
        return Div(
            H2("Minimal Plugin"),
            P("This is an example of a plugin that does nothing. Find it in the plugins folder.")
        )

# Don't register here - let the discovery process handle it
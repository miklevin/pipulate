from fastcore.xml import *
from fasthtml.common import *
import logging
import time

logger = logging.getLogger(__name__)

class SeparatorPlugin:
    NAME = "separator"
    DISPLAY_NAME = "Separator"
    ENDPOINT_MESSAGE = "Displaying separator..."
    
    def __init__(self, app, pipulate, pipeline, db):
        logger.debug(f"SeparatorPlugin initialized with NAME: {self.NAME}")
        self.pipulate = pipulate
        self._has_streamed = False  # Flag to track if we've already streamed
    
    async def landing(self, render_items=None):
        """Always appears in create_grid_left."""
        # Generate unique IDs
        unique_id = f"mermaid-{int(time.time() * 1000)}"
        
        # Send the diagram to the conversation history, but only once per session
        if self.pipulate is not None and not self._has_streamed:
            try:
                # First, send the verbatim redirect message
                await self.pipulate.stream(
                    self.ENDPOINT_MESSAGE,
                    verbatim=True,
                    role="system",
                    spaces_before=1,
                    spaces_after=1
                )
                
                # Then append the separator info to history without displaying
                diagram_message = "Separator"
                self.pipulate.append_to_history(  # Remove await since it's not async
                    "[WIDGET CONTENT] Project Separator\n" + diagram_message,
                    role="system",
                    quiet=True  # Add quiet flag to ensure it's silent
                )
                
                self._has_streamed = True  # Set flag to prevent repeated streaming
                logger.debug("Separator appended to conversation history")
            except Exception as e:
                logger.error(f"Error in separator plugin: {str(e)}")
                # Continue even if messaging fails - the diagram will still show
        
        # Create the mermaid diagram container - leave empty for now
        mermaid_diagram = Div(
            id=unique_id, 
            style="width: 100%; padding: 10px; background-color: #f9f9f9; border-radius: 5px; margin: 15px 0;"
        )
        
        
        return Div(
            H2("Project Separator"),
            P("Separator"),
        )

# Don't register here - let the discovery process handle it

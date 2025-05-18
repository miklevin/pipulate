from fastcore.xml import *
from fasthtml.common import *
import logging
import time
logger = logging.getLogger(__name__)

class SeparatorPlugin:
    NAME = 'separator'
    DISPLAY_NAME = 'Separator'
    ENDPOINT_MESSAGE = 'Displaying separator...'

    def __init__(self, app, pipulate, pipeline, db):
        logger.debug(f'SeparatorPlugin initialized with NAME: {self.NAME}')
        self.pipulate = pipulate
        self._has_streamed = False

    async def landing(self, render_items=None):
        """Always appears in create_grid_left."""
        unique_id = f'mermaid-{int(time.time() * 1000)}'
        if self.pipulate is not None and (not self._has_streamed):
            try:
                await self.pipulate.stream(self.ENDPOINT_MESSAGE, verbatim=True, role='system', spaces_before=1, spaces_after=1)
                diagram_message = 'Separator'
                self.pipulate.append_to_history('[WIDGET CONTENT] Project Separator\n' + diagram_message, role='system', quiet=True)
                self._has_streamed = True
                logger.debug('Separator appended to conversation history')
            except Exception as e:
                logger.error(f'Error in separator plugin: {str(e)}')
        return Li(Hr(style='margin: 0.5rem 0;'), cls='d-block')
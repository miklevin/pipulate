import logging
import time

from fastcore.xml import *
from fasthtml.common import *

ROLES = ['Tutorial']

logger = logging.getLogger(__name__)


class RoadmapPlugin:
    NAME = "roadmap"
    DISPLAY_NAME = "Roadmap 🗺️"
    ENDPOINT_MESSAGE = "Displaying project roadmap..."

    # Define the Mermaid diagram as a class property
    ROADMAP_DIAGRAM = """
    gantt
        title Pipulate Development Roadmap
        dateFormat YYYY-MM-DD
        axisFormat %b %d

        section Core Infrastructure
        Nix Environment         :done, nix1, 2024-01-01, 60d
        Magic Cookie System     :done, nix2, after nix1, 30d
        Dev/Test/Prod DB        :active, db1, 2024-03-15, 30d

        section Web Data
        Botify Integration     :done, web1, 2024-02-01, 45d
        Parameter Buster       :done, web2, after web1, 30d
        Save HTML & DOM        :web3, 2024-05-01, 28d

        section AI Capabilities
        LLM Integration        :done, ai1, 2024-01-15, 45d
        Chat Interface        :done, ai2, after ai1, 30d
        Vector Memory         :ai3, 2024-05-15, 28d
        Graph Memory          :ai4, after ai3, 24d

        section UI & Controls
        HTMX Integration      :done, ui1, 2024-01-01, 45d
        FastHTML Components   :done, ui2, after ui1, 30d
        Web Form Fields       :ui3, 2024-06-01, 32d
        Anywidgets Support    :ui4, after ui3, 30d

        section Automation
        MCP Server            :auto1, 2024-07-01, 35d
        LLM as MCP Client     :auto2, after auto1, 30d
    """

    def __init__(self, app, pipulate, pipeline, db):
        logger.debug(f"RoadmapPlugin initialized with NAME: {self.NAME}")
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

                # Then append the roadmap info to history without displaying
                diagram_message = f"```mermaid\n{self.ROADMAP_DIAGRAM}\n```"
                self.pipulate.append_to_history(  # Remove await since it's not async
                    "[WIDGET CONTENT] Project Roadmap\n" + diagram_message,
                    role="system"
                )

                self._has_streamed = True  # Set flag to prevent repeated streaming
                logger.debug("Roadmap appended to conversation history")
            except Exception as e:
                logger.error(f"Error in roadmap plugin: {str(e)}")
                # Continue even if messaging fails - the diagram will still show

        # Create the mermaid diagram container - leave empty for now
        mermaid_diagram = Div(
            id=unique_id,
            style="width: 100%; padding: 10px; background-color: #f9f9f9; border-radius: 5px; margin: 15px 0;"
        )

        # Create a script that loads Mermaid.js from CDN and renders the diagram
        load_script = Script(
            f"""
            (function() {{
                var diagramEl = document.getElementById("{unique_id}");
                if (!diagramEl) return;

                // Use the diagram from class property
                var diagram = `{self.ROADMAP_DIAGRAM}`;

                // Load Mermaid.js from local static file
                var script = document.createElement('script');
                script.src = "/assets/js/mermaid.min.js";
                script.onload = function() {{
                    console.log("Mermaid loaded from local static");

                    // Create a wrapper div with mermaid class
                    var mermaidWrapper = document.createElement('div');
                    mermaidWrapper.className = 'mermaid';
                    mermaidWrapper.textContent = diagram;

                    // Add to our container
                    diagramEl.appendChild(mermaidWrapper);

                    // Initialize mermaid
                    mermaid.initialize({{
                        startOnLoad: true,
                        theme: 'default',
                        securityLevel: 'loose',
                        gantt: {{
                            titleTopMargin: 30,
                            barHeight: 35,
                            barGap: 10,
                            topPadding: 75,
                            bottomPadding: 50,
                            leftPadding: 145,
                            gridLineStartPadding: 35,
                            fontSize: 14,
                            fontFamily: "Arial, sans-serif",
                            numberSectionStyles: 5,
                            axisFormat: '%m/%d',
                            sectionHeight: 45,
                            useWidth: 1200
                        }}
                    }});

                    // Render the diagram
                    setTimeout(function() {{
                        try {{
                            mermaid.init(undefined, mermaidWrapper);
                        }} catch(e) {{
                            console.error("Mermaid rendering error:", e);
                            mermaidWrapper.innerHTML = '<p style="color: red;">Error rendering diagram. See console for details.</p>';
                        }}
                    }}, 100);
                }};

                document.head.appendChild(script);
            }})();
            """,
            type="text/javascript"
        )

        return Div(
            H2("Project Roadmap"),
            P("Planned development timeline for Pipulate features:"),
            mermaid_diagram,
            load_script
        )

# Don't register here - let the discovery process handle it

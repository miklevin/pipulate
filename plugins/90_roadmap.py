from fastcore.xml import *
from fasthtml.common import *
import logging
import time

logger = logging.getLogger(__name__)

class RoadmapPlugin:
    NAME = "roadmap"
    DISPLAY_NAME = "Roadmap"
    ENDPOINT_MESSAGE = "This is a simple plugin example."
    
    def __init__(self, app, pipulate, pipeline, db):
        logger.debug(f"RoadmapPlugin initialized with NAME: {self.NAME}")
    
    async def landing(self, request):
        """Activates plugin import."""
        logger.debug("RoadmapPlugin.landing method called")
    
    async def render(self, render_items=None):
        """Always appears in create_grid_left."""
        # Generate unique IDs
        unique_id = f"mermaid-{int(time.time() * 1000)}"
        
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
                
                // Updated project roadmap based on user's list
                var diagram = `
                gantt
                    title Pipulate Development Roadmap
                    dateFormat YYYY-MM-DD
                    axisFormat %b %d
                    
                    section Database
                    Dev/Test/Prod DB        :active, db1, 2025-05-01, 30d
                    Delete Exp Tables       :db2, after db1, 20d
                    
                    section Web Data
                    Save HTML & DOM         :web1, 2025-05-15, 28d
                    Botify CSV Export       :web2, after web1, 25d
                    
                    section AI Capabilities
                    LLM Inspection          :ai1, 2025-06-01, 35d
                    Vector Memory           :ai2, after ai1, 28d
                    Graph Memory            :ai3, after ai2, 24d
                    Key/Value Store         :ai4, after ai3, 22d
                    
                    section UI & Controls
                    Web Form Fields         :ui1, 2025-07-01, 32d
                    Anywidgets Support      :ui2, after ui1, 30d
                    
                    section Automation
                    MCP Server              :auto1, 2025-08-01, 35d
                    LLM as MCP Client       :auto2, after auto1, 30d
                `;
                
                // Load Mermaid.js from local static file
                var script = document.createElement('script');
                script.src = "/static/mermaid.min.js";
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

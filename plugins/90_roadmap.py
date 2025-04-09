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
                
                // A more complete project roadmap diagram
                var diagram = `
                gantt
                    title Project Roadmap
                    dateFormat  YYYY-MM-DD
                    section Phase 1
                    Requirements Analysis    :done, a1, 2025-01-01, 30d
                    Design & Architecture    :done, a2, after a1, 45d
                    section Phase 2
                    Core Development         :active, b1, after a2, 60d
                    Testing & QA             :b2, after b1, 30d
                    section Phase 3
                    Deployment               :c1, after b2, 15d
                    User Training            :c2, after c1, 20d
                    section Phase 4
                    Maintenance              :d1, after c2, 90d
                    Future Enhancements      :d2, after c1, 90d
                `;
                
                // Load Mermaid.js from CDN
                var script = document.createElement('script');
                script.src = "/static/mermaid.min.js";
                script.onload = function() {{
                    console.log("Mermaid loaded from CDN");
                    
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
                        securityLevel: 'loose'
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
            P("Current development timeline and milestones:"),
            mermaid_diagram,
            load_script
        )

# Don't register here - let the discovery process handle it

import asyncio
import json
from collections import namedtuple
from datetime import datetime
from fasthtml.common import * # type: ignore
from loguru import logger
from starlette.responses import HTMLResponse

"""
Pipulate Markdown MarkedJS Widget Workflow
A workflow for demonstrating the Markdown MarkedJS rendering widget.
"""
# Model for a workflow step
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))

class MarkdownWidget:
    """
    Markdown MarkedJS Widget Workflow
    
    Demonstrates rendering markdown content using MarkedJS.
    """
    # --- Workflow Configuration ---
    APP_NAME = "markdown_widget"
    DISPLAY_NAME = "Markdown MarkedJS Widget"
    ENDPOINT_MESSAGE = (
        "This workflow demonstrates a Markdown (MarkedJS) rendering widget. "
        "Enter markdown content to see it rendered."
    )
    TRAINING_PROMPT = (
        "This workflow is for demonstrating and testing the Markdown MarkedJS widget. "
        "The user will input markdown text, and the system will render it as HTML."
    )
    # --- Initialization ---
    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
        """Initialize the workflow, define steps, and register routes."""
        self.app = app
        self.app_name = app_name
        self.pipulate = pipulate
        self.pipeline = pipeline
        self.steps_indices = {}
        self.db = db
        pip = self.pipulate
        self.message_queue = pip.message_queue
        # Define workflow steps
        steps = [
            Step(
                id='step_01',
                done='markdown_content',  # Field to store the markdown text
                show='Markdown Content',    # User-friendly name for this step
                refill=True,
                transform=lambda prev_value: prev_value.strip() if prev_value else ""
            ),
        ]
        
        # Register standard workflow routes
        routes = [
            (f"/{app_name}", self.landing),
            (f"/{app_name}/init", self.init, ["POST"]),
            (f"/{app_name}/revert", self.handle_revert, ["POST"]),
            (f"/{app_name}/finalize", self.finalize, ["GET", "POST"]),
            (f"/{app_name}/unfinalize", self.unfinalize, ["POST"]),
        ]
        # Register routes for each step
        self.steps = steps
        for step in steps:
            step_id = step.id
            routes.append((f"/{app_name}/{step_id}", getattr(self, step_id)))
            routes.append((f"/{app_name}/{step_id}_submit", getattr(self, f"{step_id}_submit"), ["POST"]))
        # Register all routes with the FastHTML app
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ["GET"]
            app.route(path, methods=method_list)(handler)
        # Define UI messages
        self.step_messages = {
            "finalize": {
                "ready": "All steps complete. Ready to finalize workflow.",
                "complete": f"Workflow finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes."
            },
            "step_01": {
                "input": "Please enter Markdown content.",
                "complete": "Markdown content processed."
            }
        }
        # Add the finalize step internally
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

    # --- Core Workflow Engine Methods ---
    async def landing(self):
        pip, pipeline, steps, app_name = self.pipulate, self.pipeline, self.steps, self.app_name
        title = f"{self.DISPLAY_NAME or app_name.title()}"
        full_key, prefix, user_part = pip.generate_pipeline_key(self)
        default_value = full_key
        pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in pipeline() if record.pkey.startswith(prefix)]
        datalist_options = [f"{prefix}{record_key.replace(prefix, '')}" for record_key in matching_records]
        return Container(
            Card(
                H2(title),
                P(self.ENDPOINT_MESSAGE, style="font-size: 0.9em; color: #666;"),
                Form(
                    pip.wrap_with_inline_button(
                        Input(
                            placeholder="Existing or new 🗝 here (Enter for auto)", name="pipeline_id",
                            list="pipeline-ids", type="search", required=False, autofocus=True,
                            value=default_value, _onfocus="this.setSelectionRange(this.value.length, this.value.length)",
                            cls="contrast"
                        ),
                        button_label=f"Enter 🔑", button_class="secondary"
                    ),
                    pip.update_datalist("pipeline-ids", options=datalist_options if datalist_options else None),
                    hx_post=f"/{app_name}/init", hx_target=f"#{app_name}-container"
                )
            ),
            Div(id=f"{app_name}-container")
        )

    async def init(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        user_input = form.get("pipeline_id", "").strip()
        if not user_input:
            from starlette.responses import Response
            response = Response("")
            response.headers["HX-Refresh"] = "true"
            return response
        context = pip.get_plugin_context(self)
        profile_name = context['profile_name'] or "default"
        plugin_name = context['plugin_name'] or app_name # Use actual plugin name
        profile_part = profile_name.replace(" ", "_")
        plugin_part = plugin_name.replace(" ", "_")
        expected_prefix = f"{profile_part}-{plugin_part}-"
        
        if user_input.startswith(expected_prefix):
            pipeline_id = user_input
        else:
            # If user input doesn't match the expected prefix for *this* plugin,
            # it implies they might be trying to create a new ID or mistyped.
            # We use the user_input as the basis for the user_part of the key.
            _, temp_prefix, user_provided_id_part = pip.generate_pipeline_key(self, user_input)
            # However, ensure the prefix is correct for THIS plugin
            pipeline_id = f"{expected_prefix}{user_provided_id_part}"

        db["pipeline_id"] = pipeline_id
        state, error = pip.initialize_if_missing(pipeline_id, {"app_name": app_name}) # Ensure app_name is stored
        if error: return error
        await self.message_queue.add(pip, f"Workflow ID: {pipeline_id}", verbatim=True, spaces_before=0)
        await self.message_queue.add(pip, f"Return later by selecting '{pipeline_id}' from the dropdown.", verbatim=True, spaces_before=0)
        
        return Div(
            Div(id="step_01", hx_get=f"/{app_name}/step_01", hx_trigger="load"),
            id=f"{app_name}-container"
        )

    async def finalize(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        finalize_step = steps[-1] 
        finalize_data = pip.get_step_data(pipeline_id, finalize_step.id, {})
        if request.method == "GET":
            if finalize_step.done in finalize_data:
                return Card(
                    H3("Workflow is locked."),
                    Form(
                        Button(pip.UNLOCK_BUTTON_LABEL, type="submit", cls="secondary outline"),
                        hx_post=f"/{app_name}/unfinalize", 
                        hx_target=f"#{app_name}-container", hx_swap="outerHTML"
                    ),
                    id=finalize_step.id
                )
            else:
                all_steps_complete = all(
                    pip.get_step_data(pipeline_id, step.id, {}).get(step.done) 
                    for step in steps[:-1] 
                )
                if all_steps_complete:
                    return Card(
                        H3("All steps complete. Finalize?"),
                        P("You can revert to any step and make changes.", style="font-size: 0.9em; color: #666;"),
                        Form(
                            Button("Finalize 🔒", type="submit", cls="primary"),
                            hx_post=f"/{app_name}/finalize", 
                            hx_target=f"#{app_name}-container", hx_swap="outerHTML"
                        ),
                        id=finalize_step.id
                    )
                else:
                    return Div(id=finalize_step.id) # Empty div if not all steps complete
        else: # POST request
            await pip.finalize_workflow(pipeline_id)
            await self.message_queue.add(pip, self.step_messages["finalize"]["complete"], verbatim=True)
            return pip.rebuild(app_name, steps)

    async def unfinalize(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, "Workflow unfinalized! You can now revert to any step and make changes.", verbatim=True)
        return pip.rebuild(app_name, steps)

    async def get_suggestion(self, step_id, state):
        if step_id == 'step_01':
            return """# Markdown Example
This is a **bold statement** about _markdown_.

## Features demonstrated:

1. Headings (h1, h2)
2. Formatted text (**bold**, _italic_)
3. Ordered lists
4. Unordered lists
   - Nested item 1
   - Nested item 2
5. Code blocks

### Code Example

```python
def hello_world():
    print("Hello from Markdown!")
    for i in range(3):
        print(f"Count: {i}")
```

> Blockquotes are also supported
>
>   - With nested lists
>   - And formatting
>     [Learn more about Markdown](https://www.markdownguide.org/)
"""
        return ""

    async def handle_revert(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        pipeline_id = db.get("pipeline_id", "unknown")
        if not step_id: return P("Error: No step specified", style=pip.get_style("error"))
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        state = pip.read_state(pipeline_id)
        state["_revert_target"] = step_id
        pip.write_state(pipeline_id, state)
        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        return pip.rebuild(app_name, steps)

    def create_marked_widget(self, markdown_content, widget_id):
        # Create a container for the markdown content
        widget = Div(
            # Hidden div containing the raw markdown content
            Div(
                markdown_content,
                id=f"{widget_id}_source",
                style="display: none;"
            ),
            # Container where the rendered HTML will be inserted
            Div(
                id=f"{widget_id}_rendered",
                cls="markdown-body p-3 border rounded bg-light" # Standard styling
            ),
            # JavaScript to initialize marked.js rendering
            Script(f"""
                document.addEventListener('htmx:afterOnLoad', function() {{
                    function renderMarkdown() {{
                        const source = document.getElementById('{widget_id}_source');
                        const target = document.getElementById('{widget_id}_rendered');
                        if (source && target) {{
                            const html = marked.parse(source.textContent);
                            target.innerHTML = html;
                            if (typeof Prism !== 'undefined') {{
                                Prism.highlightAllUnder(target);
                            }}
                        }}
                    }}
                    if (typeof marked !== 'undefined') {{
                        renderMarkdown();
                    }} else {{
                        console.error('marked.js is not loaded');
                    }}
                }});
                document.addEventListener('initMarked', function(event) {{
                    if (event.detail.widgetId === '{widget_id}') {{
                        setTimeout(function() {{
                            const source = document.getElementById('{widget_id}_source');
                            const target = document.getElementById('{widget_id}_rendered');
                            if (source && target && typeof marked !== 'undefined') {{
                                const html = marked.parse(source.textContent);
                                target.innerHTML = html;
                                if (typeof Prism !== 'undefined') {{
                                    Prism.highlightAllUnder(target);
                                }}
                            }}
                        }}, 100); // Delay to ensure DOM is ready
                    }}
                }});
            """),
            cls="marked-widget"
        )
        return widget

    async def step_01(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = 'finalize' # Only one data step before finalize
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "")

        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and user_val:
            widget_id = f"marked-widget-{pipeline_id.replace('-', '_')}-{step_id}"
            marked_widget = self.create_marked_widget(user_val, widget_id)
            response = HTMLResponse(
                to_xml(
                    Div(
                        Card(
                            H3(f"🔒 {step.show}"),
                            marked_widget
                        ),
                        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                        id=step_id
                    )
                )
            )
            response.headers["HX-Trigger"] = json.dumps({"initMarked": {"widgetId": widget_id}})
            return response

        elif user_val and state.get("_revert_target") != step_id:
            widget_id = f"marked-widget-{pipeline_id.replace('-', '_')}-{step_id}"
            marked_widget = self.create_marked_widget(user_val, widget_id)
            content_container = pip.widget_container(
                step_id=step_id,
                app_name=app_name,
                message=f"{step.show} Configured",
                widget=marked_widget,
                steps=steps
            )
            response = HTMLResponse(
                to_xml(
                    Div(
                        content_container,
                        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                        id=step_id
                    )
                )
            )
            response.headers["HX-Trigger"] = json.dumps({"initMarked": {"widgetId": widget_id}})
            return response
        else:
            display_value = user_val if step.refill and user_val else await self.get_suggestion(step_id, state)
            await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
            
            explanation = "Enter markdown content to be rendered. Example is pre-populated. The markdown will be rendered with support for headings, lists, bold/italic text, and code blocks."
            await self.message_queue.add(pip, explanation, verbatim=True)

            return Div(
                Card(
                    H3(f"{pip.fmt(step_id)}: Configure {step.show}"),
                    P(explanation, style=pip.get_style("muted")),
                    Form(
                        Div(
                            Textarea(
                                display_value,
                                name=step.done,
                                placeholder="Enter markdown content",
                                required=True,
                                rows=15,
                                style="width: 100%; font-family: monospace;"
                            ),
                            Div(
                                Button("Render Markdown ▸", type="submit", cls="primary"),
                                style="margin-top: 1vh; text-align: right;"
                            ),
                            style="width: 100%;"
                        ),
                        hx_post=f"/{app_name}/{step_id}_submit",
                        hx_target=f"#{step_id}"
                    )
                ),
                Div(id=next_step_id), 
                id=step_id
            )

    async def step_01_submit(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = 'finalize' # Only one data step before finalize
        pipeline_id = db.get("pipeline_id", "unknown")

        form = await request.form()
        user_val = form.get(step.done, "").strip()

        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            return error_component

        await pip.set_step_data(pipeline_id, step_id, user_val, steps)
        pip.append_to_history(f"[WIDGET CONTENT] {step.show}:\n{user_val}")
        
        widget_id = f"marked-widget-{pipeline_id.replace('-', '_')}-{step_id}"
        marked_widget = self.create_marked_widget(user_val, widget_id)
        
        content_container = pip.widget_container(
            step_id=step_id,
            app_name=app_name,
            message=f"{step.show}: Markdown rendered with Marked.js",
            widget=marked_widget,
            steps=steps
        )
        
        response_content = Div(
            content_container,
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
        
        response = HTMLResponse(to_xml(response_content))
        response.headers["HX-Trigger"] = json.dumps({"initMarked": {"widgetId": widget_id}})
        
        await self.message_queue.add(pip, f"{step.show} complete. Markdown rendered successfully.", verbatim=True)
        if pip.check_finalize_needed(step_index, steps): # True since it's the only step
             await self.message_queue.add(pip, self.step_messages["finalize"]["ready"], verbatim=True)

        return response
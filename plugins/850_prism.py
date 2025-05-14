import asyncio
import json
from collections import namedtuple
from datetime import datetime
from fasthtml.common import * # type: ignore
from loguru import logger
from starlette.responses import HTMLResponse

"""
Pipulate PrismJS Code Highlighter Widget Workflow
A workflow for demonstrating the Prism.js code syntax highlighting widget.
"""
# Model for a workflow step
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))

class PrismWidget:
    """
    PrismJS Code Highlighter Widget Workflow
    
    Demonstrates syntax highlighting of code using Prism.js.
    """
    # --- Workflow Configuration ---
    APP_NAME = "prism_widget"
    DISPLAY_NAME = "PrismJS Code Highlighter"
    ENDPOINT_MESSAGE = (
        "This workflow demonstrates a Prism.js code syntax highlighting widget. "
        "Enter code to see it highlighted."
    )
    TRAINING_PROMPT = (
        "This workflow is for demonstrating and testing the PrismJS code highlighting widget. "
        "The user will input code (optionally with a language specifier like ```python), "
        "and the system will render it with syntax highlighting."
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
                done='code_content',  # Field to store the code string
                show='Code Content',    # User-friendly name for this step
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
                "input": "Please enter code content for syntax highlighting.",
                "complete": "Code content processed and highlighted."
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
        plugin_name = context['plugin_name'] or app_name
        profile_part = profile_name.replace(" ", "_")
        plugin_part = plugin_name.replace(" ", "_")
        expected_prefix = f"{profile_part}-{plugin_part}-"
        
        if user_input.startswith(expected_prefix):
            pipeline_id = user_input
        else:
            _, temp_prefix, user_provided_id_part = pip.generate_pipeline_key(self, user_input)
            pipeline_id = f"{expected_prefix}{user_provided_id_part}"
            
        db["pipeline_id"] = pipeline_id
        state, error = pip.initialize_if_missing(pipeline_id, {"app_name": app_name})
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
                    return Div(id=finalize_step.id)
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
            return """```javascript
function calculateFactorial(n) {
    // Base case: factorial of 0 or 1 is 1
    if (n <= 1) {
        return 1;
    }
    
    // Recursive case: n! = n * (n-1)!
    return n * calculateFactorial(n - 1);
}
// Example usage
for (let i = 0; i < 10; i++) {
    console.log(`Factorial of ${i} is ${calculateFactorial(i)}`);
}
```"""
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

    def create_prism_widget(self, code, widget_id, language='javascript'):
        """Create a Prism.js syntax highlighting widget with copy functionality."""
        textarea_id = f"{widget_id}_raw_code"
        container = Div(
            Div(
                H5("Syntax Highlighted Code:"),
                Textarea(
                    code,
                    id=textarea_id,
                    style="display: none;"
                ),
                Pre(
                    Code(
                        code,
                        cls=f"language-{language}",
                        style="position: relative; white-space: inherit; padding: 0 0 0 0;"
                    ),
                    cls="line-numbers"
                ),
                style="margin-top: 1rem;"
            ),
            id=widget_id
        )
        init_script = Script(
            f"""
            (function() {{
                // Initialize Prism immediately when the script loads
                if (typeof Prism !== 'undefined') {{
                    Prism.highlightAllUnder(document.getElementById('{widget_id}'));
                }}
                
                // Also listen for the HX-Trigger event as a backup
                document.body.addEventListener('initializePrism', function(event) {{
                    if (event.detail.targetId === '{widget_id}') {{
                        console.log('Received initializePrism event for {widget_id}');
                        if (typeof Prism !== 'undefined') {{
                            Prism.highlightAllUnder(document.getElementById('{widget_id}'));
                        }} else {{
                            console.error('Prism library not found for {widget_id}');
                        }}
                    }}
                }});
            }})();
            """,
            type="text/javascript"
        )
        return Div(container, init_script)

    async def step_01(self, request):
        """Handles GET request for Step 1: Code Input and Highlighting."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "") # code_content
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})

        # Language detection logic
        language = 'javascript' # Default
        code_to_display = user_val
        if user_val.startswith('```'):
            first_line_end = user_val.find('\n')
            if first_line_end != -1:
                first_line = user_val[3:first_line_end].strip()
                if first_line: # If language is specified
                    language = first_line
                    code_to_display = user_val[first_line_end+1:]
                else: # ``` on its own line
                    code_to_display = user_val[first_line_end+1:]
            else: # Only ``` and code on one line, or just ```
                if len(user_val) > 3 and not user_val[3:].strip().startswith("```"): # check if there is a lang specified
                    lang_match = user_val[3:].split(' ', 1)[0].split('\n',1)[0]
                    if lang_match and not lang_match.startswith("`"):
                        language = lang_match

        # Remove trailing triple backticks
        if code_to_display.rstrip().endswith('```'):
            code_to_display = code_to_display.rstrip()[:-3].rstrip()

        if "finalized" in finalize_data and user_val:
            widget_id = f"prism-widget-{pipeline_id.replace('-', '_')}-{step_id}"
            prism_widget = self.create_prism_widget(code_to_display, widget_id, language)
            response = HTMLResponse(
                to_xml(
                    Div(
                        Card(
                            H3(f"🔒 {step.show} ({language})"),
                            prism_widget
                        ),
                        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                        id=step_id
                    )
                )
            )
            response.headers["HX-Trigger"] = json.dumps({"initializePrism": {"targetId": widget_id}})
            return response
        elif user_val and state.get("_revert_target") != step_id:
            widget_id = f"prism-widget-{pipeline_id.replace('-', '_')}-{step_id}"
            prism_widget = self.create_prism_widget(code_to_display, widget_id, language)
            content_container = pip.widget_container(
                step_id=step_id,
                app_name=app_name,
                message=f"{step.show}: Syntax highlighting with Prism.js ({language})",
                widget=prism_widget,
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
            response.headers["HX-Trigger"] = json.dumps({"initializePrism": {"targetId": widget_id}})
            return response
        else:
            display_value = user_val if step.refill and user_val else await self.get_suggestion(step_id, state)
            await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
            
            explanation = "Enter code to be highlighted. You can specify language using ```python (or other language) at the start."
            await self.message_queue.add(pip, explanation, verbatim=True)
            return Div(
                Card(
                    H3(f"{pip.fmt(step_id)}: Configure {step.show}"),
                    P(explanation, style=pip.get_style("muted")),
                    Form(
                        Div(
                            Textarea(
                                display_value,
                                name=step.done, # code_content
                                placeholder="Enter code for syntax highlighting",
                                required=True,
                                rows=15,
                                style="width: 100%; font-family: monospace;"
                            ),
                            Div(
                                Button("Highlight Code ▸", type="submit", cls="primary"),
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
        """Process the submission for Code Input and Highlighting."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        form = await request.form()
        user_val_raw = form.get(step.done, "") # Raw input including ```lang
        user_val_stripped = user_val_raw.strip()

        # Language detection logic
        language = 'javascript' # Default
        code_to_highlight = user_val_stripped
        
        if user_val_stripped.startswith('```'):
            first_line_end = user_val_stripped.find('\n')
            if first_line_end != -1: # Language is on the first line
                detected_lang = user_val_stripped[3:first_line_end].strip()
                if detected_lang:
                    language = detected_lang
                code_to_highlight = user_val_stripped[first_line_end+1:]
            else: # Only ``` and code on one line (no language specified after ```) or just ```
                # Check if there's a lang specifier on the same line as ```
                potential_lang = user_val_stripped[3:].split(' ', 1)[0].split('\n',1)[0]
                if potential_lang and not potential_lang.startswith("`"): # ensure it's not the start of the code block itself
                    language = potential_lang
                    # Remove the language part if it was on the same line
                    if user_val_stripped.startswith(f"```{language}"):
                        code_to_highlight = user_val_stripped[len(f"```{language}"):].lstrip()

        # Remove trailing triple backticks if they exist
        if code_to_highlight.rstrip().endswith('```'):
            code_to_highlight = code_to_highlight.rstrip()[:-3].rstrip()
        
        # Validate the code that will be highlighted (not the raw input with ```)
        is_valid, error_msg, error_component = pip.validate_step_input(code_to_highlight, step.show)
        if not is_valid:
            return error_component # This will show "Code Content cannot be empty" if only ``` was entered.
        
        # Save the raw user input (including ```lang if provided) to state, as that's what they'd expect to see on revert.
        await pip.set_step_data(pipeline_id, step_id, user_val_raw, steps) # Save the original raw value
        pip.append_to_history(f"[WIDGET CONTENT] {step.show} ({language}):\n{code_to_highlight}")
        
        widget_id = f"prism-widget-{pipeline_id.replace('-', '_')}-{step_id}"
        prism_widget = self.create_prism_widget(code_to_highlight, widget_id, language)
        
        content_container = pip.widget_container(
            step_id=step_id,
            app_name=app_name,
            message=f"{step.show}: Syntax highlighting with Prism.js ({language})",
            widget=prism_widget,
            steps=steps
        )
        
        response_content = Div(
            content_container,
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
        
        response = HTMLResponse(to_xml(response_content))
        response.headers["HX-Trigger"] = json.dumps({"initializePrism": {"targetId": widget_id}})
        
        await self.message_queue.add(pip, f"{step.show} complete. Code syntax highlighted with {language}.", verbatim=True)
        if pip.check_finalize_needed(step_index, steps):
            await self.message_queue.add(pip, self.step_messages["finalize"]["ready"], verbatim=True)
        return response
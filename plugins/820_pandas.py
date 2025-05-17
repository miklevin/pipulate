import asyncio
import json
from collections import namedtuple
from datetime import datetime
from fasthtml.common import * # type: ignore
from loguru import logger
from starlette.responses import HTMLResponse
import pandas as pd

ROLES = ['Developer']

"""
Pipulate Pandas Table Widget Workflow
A workflow for demonstrating the Pandas DataFrame to HTML table rendering widget.
"""
# Model for a workflow step
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))

class PandasTableWidget:
    """
    Pandas Table Widget Workflow
    
    Demonstrates rendering JSON data as an HTML table using Pandas.
    """
    # --- Workflow Configuration ---
    APP_NAME = "pandas_table_widget"
    DISPLAY_NAME = "Pandas Table Widget"
    ENDPOINT_MESSAGE = (
        "This workflow demonstrates a Pandas DataFrame to HTML table rendering widget. "
        "Enter JSON data to see it rendered as a styled table."
    )
    TRAINING_PROMPT = (
        "This workflow is for demonstrating and testing the Pandas table widget. "
        "The user will input JSON data, and the system will render it as an HTML table using Pandas."
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
                done='table_data',  # Field to store the JSON string for the table
                show='Table Data (JSON)', # User-friendly name for this step
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
                "input": "Please enter JSON data for the table.",
                "complete": "JSON data processed and table rendered."
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
            return """[
{"Name": "John", "Age": 32, "Role": "Developer", "Department": "Engineering"},
{"Name": "Jane", "Age": 28, "Role": "Designer", "Department": "Product"},
{"Name": "Bob", "Age": 45, "Role": "Manager", "Department": "Engineering"},
{"Name": "Alice", "Age": 33, "Role": "PM", "Department": "Product"},
{"Name": "Charlie", "Age": 40, "Role": "Architect", "Department": "Engineering"}
]"""
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

    def create_pandas_table(self, data_str):
        """
        Create a pandas HTML table from JSON string data.
        
        This helper method encapsulates the widget creation logic, which:
        1. Makes the code more maintainable
        2. Allows reuse in both step_02 and step_02_submit
        3. Centralizes error handling
        
        When implementing complex widgets, consider using helper methods
        like this to separate widget creation logic from workflow logic.
        
        Note on FastHTML raw HTML handling:
        - Uses Div(NotStr(html_fragment), _raw=True) to embed raw HTML
        - NotStr prevents string escaping during XML rendering
        - _raw=True flag informs the component to accept unprocessed HTML
        """
        try:
            # Try parsing the JSON data
            data = json.loads(data_str)
            
            # Create a pandas DataFrame
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                # Data is a list of dictionaries (most common format)
                df = pd.DataFrame(data)
            elif isinstance(data, list) and all(isinstance(item, list) for item in data):
                # Data is a list of lists, with first row as headers
                headers = data[0]
                rows = data[1:]
                df = pd.DataFrame(rows, columns=headers)
            else:
                return Div(NotStr("<div style='color: red;'>Unsupported data format. Please provide a list of objects.</div>"), _raw=True)
            
            # Generate HTML table with styling
            html_table = df.to_html(
                index=False,            # Don't include DataFrame index
                classes='table',        # Add a CSS class for styling
                border=0,               # Remove default HTML border attribute
                escape=True,            # Keep default HTML escaping for security
                justify='left'          # Align text to left
            )
            
            # Create a styled container for the table with responsive design
            table_container = Div(
                H5("Pandas DataFrame Table:"),
                # Add the HTML table with NotStr to prevent escaping
                Div(
                    NotStr(html_table),
                    style="overflow-x: auto; max-width: 100%;"
                ),
                style="margin-top: 1rem;"
            )
            
            return table_container
            
        except Exception as e:
            logger.error(f"Error creating pandas table: {e}")
            return Div(NotStr(f"<div style='color: red;'>Error creating table: {str(e)}</div>"), _raw=True)

    async def step_01(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = 'finalize' 
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "") # table_data (JSON string)

        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and user_val:
            try:
                table_widget = self.create_pandas_table(user_val)
                return Div(
                    Card(
                        H3(f"🔒 {step.show}"),
                        table_widget
                    ),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                    id=step_id
                )
            except Exception as e:
                logger.error(f"Error creating table widget in finalized view: {str(e)}")
                return Div(
                    Card(f"🔒 {step.show}: <content locked, error rendering table>"),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                    id=step_id
                )

        elif user_val and state.get("_revert_target") != step_id:
            try:
                table_widget = self.create_pandas_table(user_val)
                content_container = pip.widget_container(
                    step_id=step_id,
                    app_name=app_name,
                    message=f"{step.show} Configured",
                    widget=table_widget,
                    steps=steps
                )
                return Div(
                    content_container,
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                    id=step_id
                )
            except Exception as e:
                logger.error(f"Error creating table widget: {str(e)}")
                state["_revert_target"] = step_id # Force revert to input form
                pip.write_state(pipeline_id, state)
                # Fall through to show input form again after setting revert target

        # Show input form
        display_value = user_val if step.refill and user_val else await self.get_suggestion(step_id, state)
        await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
        
        explanation = "Enter table data as JSON array of objects. Example is pre-populated. Format: `[{\"name\": \"value\", \"value1\": number, ...}, {...}]`"
        await self.message_queue.add(pip, explanation, verbatim=True)
        return Div(
            Card(
                H3(f"{pip.fmt(step_id)}: Configure {step.show}"),
                P(explanation, style=pip.get_style("muted")),
                Form(
                    Div(
                        Textarea(
                            display_value,
                            name=step.done, # table_data
                            placeholder="Enter JSON array of objects for the DataFrame",
                            required=True,
                            rows=10,
                            style="width: 100%; font-family: monospace;"
                        ),
                        Div(
                            Button("Draw Table ▸", type="submit", cls="primary"),
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
        next_step_id = 'finalize' 
        pipeline_id = db.get("pipeline_id", "unknown")

        form = await request.form()
        user_val = form.get(step.done, "").strip() # table_data (JSON string)

        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            return error_component
            
        # Additional validation for JSON format
        try:
            json_data = json.loads(user_val)
            if not isinstance(json_data, list) or not json_data:
                return P("Invalid JSON: Must be a non-empty array of objects", style=pip.get_style("error"))
            if not all(isinstance(item, dict) for item in json_data):
                return P("Invalid JSON: All items must be objects (dictionaries)", style=pip.get_style("error"))
        except json.JSONDecodeError:
            return P("Invalid JSON format. Please check your syntax.", style=pip.get_style("error"))

        # Save the value to state
        await pip.set_step_data(pipeline_id, step_id, user_val, steps)
        pip.append_to_history(f"[WIDGET CONTENT] {step.show} (JSON Data):\n{user_val}")

        # Create a pandas table from the JSON data
        try:
            data = json.loads(user_val)
            
            # Create a pandas DataFrame
            df = pd.DataFrame(data)
            
            # Generate HTML table with styling
            html_table = df.to_html(
                index=False,            # Don't include DataFrame index
                classes='table',        # Add a CSS class for styling
                border=0,               # Remove default HTML border attribute
                escape=True,            # Keep default HTML escaping for security
                justify='left'          # Align text to left
            )
            
            # Create a styled container for the table with responsive design
            table_container = Div(
                H5("Pandas DataFrame Table:"),
                # Add the HTML table with NotStr to prevent escaping
                Div(
                    NotStr(html_table),
                    style="overflow-x: auto; max-width: 100%;"
                ),
                style="margin-top: 1rem;"
            )
            
            # Send confirmation message
            await self.message_queue.add(pip, f"{step.show} complete. Table rendered successfully.", verbatim=True)
            
            # Create complete response with widget container
            response = HTMLResponse(to_xml(
                Div(
                    pip.widget_container(
                        step_id=step_id,
                        app_name=app_name,
                        message=f"{step.show}: Table rendered from pandas DataFrame",
                        widget=table_container,
                        steps=steps
                    ),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                    id=step_id
                )
            ))
            
            return response
            
        except Exception as e:
            logger.error(f"Error creating pandas table: {e}")
            return Div(NotStr(f"<div style='color: red;'>Error creating table: {str(e)}</div>"), _raw=True)
import asyncio
from collections import namedtuple
from datetime import datetime
import json

from fasthtml.common import * # type: ignore
from loguru import logger
from starlette.responses import HTMLResponse

"""
Pipulate Workflow Template
A minimal starter template for creating step-based Pipulate workflows.
"""

# Model for a workflow step
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class DesignerWorkflow:
    """
    Blank Workflow Template
    
    A minimal starting point for creating new workflows.
    """
    # --- Workflow Configuration ---
    APP_NAME = "designer"              # Unique identifier for this workflow's routes and data
    DISPLAY_NAME = "Designer Workflow" # User-friendly name shown in the UI
    ENDPOINT_MESSAGE = (            # Message shown on the workflow's landing page
        "This is a workflow where we design new widgets. "
        "Enter an ID to start or resume your workflow."
    )
    TRAINING_PROMPT = "widget_implementation_guide.md" # Filename (in /training) or text for AI context
    PRESERVE_REFILL = True          # Whether to keep input values when reverting

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
                done='rich_table',
                show='Rich Table Widget',
                refill=True,
            ),
            # Add more steps as needed
        ]
        
        # Register standard workflow routes
        routes = [
            (f"/{app_name}", self.landing),
            (f"/{app_name}/init", self.init, ["POST"]),
            (f"/{app_name}/jump_to_step", self.jump_to_step, ["POST"]),
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
            }
        }

        # Create default messages for each step
        for step in steps:
            self.step_messages[step.id] = {
                "input": f"{pip.fmt(step.id)}: Please complete {step.show}.",
                "complete": f"{step.show} complete. Continue to next step."
            }

        # Add the finalize step internally
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

    # --- Core Workflow Engine Methods ---

    async def landing(self):
        """Renders the initial landing page with the key input form."""
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
        """Handles the key submission, initializes state, and renders the step UI placeholders."""
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
            _, prefix, user_provided_id = pip.generate_pipeline_key(self, user_input)
            pipeline_id = f"{prefix}{user_provided_id}"

        db["pipeline_id"] = pipeline_id

        state, error = pip.initialize_if_missing(pipeline_id, {"app_name": app_name})
        if error: return error

        await self.message_queue.add(pip, f"Workflow ID: {pipeline_id}", verbatim=True, spaces_before=0)
        await self.message_queue.add(pip, f"Return later by selecting '{pipeline_id}' from the dropdown.", verbatim=True, spaces_before=0)
        
        # Build UI starting with first step
        return Div(
            Div(id="step_01", hx_get=f"/{app_name}/step_01", hx_trigger="load"),
            id=f"{app_name}-container"
        )

    async def finalize(self, request):
        """Handles GET request to show Finalize button and POST request to lock the workflow."""
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
                        hx_target=f"#{app_name}-container"
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
                            hx_target=f"#{app_name}-container"
                        ),
                        id=finalize_step.id
                    )
                else:
                    return Div(id=finalize_step.id)
        else:
            await pip.finalize_workflow(pipeline_id)
            await self.message_queue.add(pip, self.step_messages["finalize"]["complete"], verbatim=True)
            return pip.rebuild(app_name, steps)

    async def unfinalize(self, request):
        """Handles POST request to unlock the workflow."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, "Workflow unfinalized! You can now revert to any step and make changes.", verbatim=True)
        return pip.rebuild(app_name, steps)

    async def jump_to_step(self, request):
        """Handles POST request from breadcrumb navigation to jump to a specific step."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        db["step_id"] = step_id
        return pip.rebuild(app_name, steps)

    async def get_suggestion(self, step_id, state):
        """Gets a suggested input value for a step, often using the previous step's transformed output."""
        pip, db, steps = self.pipulate, self.db, self.steps
        step = next((s for s in steps if s.id == step_id), None)
        if not step or not step.transform: return ""
        prev_index = self.steps_indices[step_id] - 1
        if prev_index < 0: return ""
        prev_step = steps[prev_index]
        prev_data = pip.get_step_data(db["pipeline_id"], prev_step.id, {})
        prev_value = prev_data.get(prev_step.done, "")
        return step.transform(prev_value) if prev_value else ""

    async def handle_revert(self, request):
        """Handles POST request to revert to a previous step, clearing subsequent step data."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        pipeline_id = db.get("pipeline_id", "unknown")
        if not step_id: return P("Error: No step specified", style=self.pipulate.get_style("error"))

        await pip.clear_steps_from(pipeline_id, step_id, steps)
        state = pip.read_state(pipeline_id)
        state["_revert_target"] = step_id
        pip.write_state(pipeline_id, state)

        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        return pip.rebuild(app_name, steps)

    # --- Placeholder Step Methods ---

    async def step_01(self, request):
        """Handles GET request for Rich Table Widget.
        
        This widget demonstrates a beautifully styled table with:
        - Connected border lines
        - Alternating row colors
        - Bold headers with thicker borders
        - Proper cell padding and alignment
        - Color-coded columns
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        table_data = step_data.get(step.done, "")

        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and table_data:
            try:
                data = json.loads(table_data)
                table_widget = self.create_rich_table_widget(data)
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
                    Card(f"🔒 {step.show}: <content locked>"),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                    id=step_id
                )
            
        # Check if step is complete and not being reverted to
        if table_data and state.get("_revert_target") != step_id:
            try:
                data = json.loads(table_data)
                table_widget = self.create_rich_table_widget(data)
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
                state["_revert_target"] = step_id
                pip.write_state(pipeline_id, state)

        # Show input form
        sample_data = [
            {"name": "Parameter 1", "value1": 1000, "value2": 500, "value3": 50},
            {"name": "Parameter 2", "value1": 2000, "value2": 1000, "value3": 100},
            {"name": "Parameter 3", "value1": 3000, "value2": 1500, "value3": 150}
        ]
        display_value = table_data if step.refill and table_data else json.dumps(sample_data, indent=2)
        await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
        
        return Div(
            Card(
                H3(f"{pip.fmt(step_id)}: Configure {step.show}"),
                P("Enter table data as JSON array of objects. Example is pre-populated."),
                P("Format: [{\"name\": \"value\", \"value1\": number, ...}, {...}]", 
                  style="font-size: 0.8em; font-style: italic;"),
                Form(
                    Div(
                        Textarea(
                            display_value,
                            name=step.done,
                            placeholder="Enter JSON array of objects for the table",
                            required=True,
                            rows=10,
                            style="width: 100%; font-family: monospace;"
                        ),
                        Div(
                            Button("Create Table ▸", type="submit", cls="primary"),
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
        """Process the submission for Rich Table Widget."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")

        # Get form data
        form = await request.form()
        table_data = form.get(step.done, "").strip()

        # Validate input
        is_valid, error_msg, error_component = pip.validate_step_input(table_data, step.show)
        if not is_valid:
            return error_component
            
        # Additional validation for JSON format
        try:
            data = json.loads(table_data)
            if not isinstance(data, list) or not data:
                return P("Invalid JSON: Must be a non-empty array of objects", style=pip.get_style("error"))
            if not all(isinstance(item, dict) for item in data):
                return P("Invalid JSON: All items must be objects (dictionaries)", style=pip.get_style("error"))
        except json.JSONDecodeError:
            return P("Invalid JSON format. Please check your syntax.", style=pip.get_style("error"))

        # Save to state
        await pip.update_step_state(pipeline_id, step_id, table_data, steps)

        # Create the rich table widget
        try:
            table_widget = self.create_rich_table_widget(data)
            
            # Create content container
            content_container = pip.widget_container(
                step_id=step_id,
                app_name=app_name,
                message=f"{step.show}: Table created with {len(data)} rows",
                widget=table_widget,
                steps=steps
            )
            
            # Create full response
            response_content = Div(
                content_container,
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
            
            # Send confirmation message
            await self.message_queue.add(pip, f"{step.show} complete. Table created with {len(data)} rows.", verbatim=True)

            return HTMLResponse(to_xml(response_content))
            
        except Exception as e:
            logger.error(f"Error creating table widget: {e}")
            return P(f"Error creating table: {str(e)}", style=pip.get_style("error"))

    def create_rich_table_widget(self, data):
        """Create a rich table widget with beautiful styling.
        
        Args:
            data: List of dictionaries containing table data
            
        Returns:
            A styled table widget
        """
        # First, add the CSS styling
        style = NotStr("""
        <style>
            .param-table {
                font-family: "Monaco", "Menlo", "Ubuntu Mono", "Consolas", "source-code-pro", monospace;
                border-collapse: separate;
                border-spacing: 0;
                width: 100%;
                color: white;
                margin-top: 1rem;
                margin-bottom: 1rem;
                border: 1px solid white;
                background-color: #000;
            }
            .param-table caption {
                caption-side: top;
                text-align: center;
                font-weight: normal;
                font-style: italic;
                color: white;
                background: transparent !important;
                padding: 10px 0;
                font-size: 1.1em;
                letter-spacing: 0.5px;
            }
            .header-cell {
                color: white !important;
                background: #000 !important;
                font-weight: bold;
                border-top: 2px solid white;
                border-bottom: 2px solid white;
                border-left: 2px solid white;
                border-right: 2px solid white;
            }
            .param-table tr.header td:last-child {
                border-right: none !important;
                padding: 8px;
            }
            .param-table tr:not(.header) td {
                border-top: none;
                border-bottom: none;
                border-left: none;
                border-right: 2px solid white;
            }
            .param-table tr:not(.header) td:last-child {
                border-right: none !important;
            }
            .param-table td {
                background: #000;
                color: inherit;
                padding: 2px 4px 2px 8px;
                text-align: left;
            }
            .param-name { color: cyan; }
            .value1-val { color: #4fa8ff; text-align: right; }
            .value2-val { color: #ff0000; text-align: right; }
            .value3-val { color: #50fa7b; text-align: right; }
            .header-cell span {
                color: white !important;
            }
        </style>
        """)

        # Get column headers from first row
        if not data:
            return P("No data provided for table", style="color: red;")
        
        headers = list(data[0].keys())

        # Create the table HTML
        table_html = f"""
        <table class="param-table">
            <caption>Rich Table Example</caption>
            <tr class="header">
        """
        
        # Add header row
        for i, header in enumerate(headers):
            header_class = "param-name" if header == "name" else f"{header}-val"
            td_class = "header-cell"
            table_html += f'<td class="{td_class}"><span class="{header_class}">{header}</span></td>'
        
        table_html += "</tr>"
        
        # Add data rows
        for row in data:
            table_html += "<tr>"
            for i, header in enumerate(headers):
                cell_class = "param-name" if header == "name" else f"{header}-val"
                value = row.get(header, "")
                # Format numbers with commas
                if isinstance(value, (int, float)):
                    value = f"{value:,}"
                table_html += f'<td><span class="{cell_class}">{value}</span></td>'
            table_html += "</tr>"
        
        table_html += "</table>"
        
        # Return the complete widget
        return Div(
            style,
            NotStr(table_html),
            style="overflow-x: auto;"
        )
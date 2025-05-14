import asyncio
import json
from collections import namedtuple, Counter
from datetime import datetime
from io import BytesIO
import base64
import matplotlib.pyplot as plt
from pathlib import Path
import os

from fasthtml.common import * # type: ignore
from starlette.responses import HTMLResponse
from loguru import logger
from fastcore.xml import NotStr

"""
Matplotlib Histogram Widget

This workflow demonstrates a Matplotlib histogram rendering widget.
Users can input JSON counter data and see it rendered as a histogram image.

The widget supports:
- JSON counter data input (keys and values)
- Automatic histogram generation
- Responsive image display
- Error handling and validation
"""

# Model for a workflow step (Do not change)
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class MatplotlibWidget:
    """
    Matplotlib Histogram Widget Workflow
    
    A focused environment for creating and testing Matplotlib histogram visualizations.
    Users input JSON counter data and see it rendered as a histogram image.
    """
    # --- Workflow Configuration ---
    APP_NAME = "matplotlib_widget"
    DISPLAY_NAME = "Matplotlib Histogram Widget"
    ENDPOINT_MESSAGE = (
        "This workflow demonstrates a Matplotlib histogram rendering widget. "
        "Enter JSON counter data to see it rendered as an image."
    )
    TRAINING_PROMPT = (
        "This workflow is for demonstrating and testing the Matplotlib histogram widget. "
        "The user will input JSON formatted counter data (keys and values), and the system "
        "will render it as a histogram image."
    )

    # --- Initialization ---
    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
        """
        Initialize the workflow, define steps, and register routes.
        """
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
                done='counter_data',  # Field to store the JSON string for counter
                show='Counter Data (JSON)', # User-friendly name
                refill=True,
                transform=lambda prev_value: prev_value.strip() if prev_value else ""
            ),
        ]
        
        # Standard workflow routes
        routes = [
            (f"/{app_name}", self.landing),
            (f"/{app_name}/init", self.init, ["POST"]),
            (f"/{app_name}/revert", self.handle_revert, ["POST"]),
            (f"/{app_name}/finalize", self.finalize, ["GET", "POST"]),
            (f"/{app_name}/unfinalize", self.unfinalize, ["POST"]),
        ]

        # Routes for each custom step
        self.steps = steps
        for step in steps:
            step_id = step.id
            routes.append((f"/{app_name}/{step_id}", getattr(self, step_id)))
            routes.append((f"/{app_name}/{step_id}_submit", getattr(self, f"{step_id}_submit"), ["POST"]))

        # Register routes with the FastHTML app
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ["GET"]
            app.route(path, methods=method_list)(handler)

        # Define UI messages
        self.step_messages = {
            "finalize": {
                "ready": "All steps complete. Ready to finalize workflow.",
                "complete": f"Workflow finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes."
            },
            "new": "Please enter JSON counter data to create a histogram visualization.",
            "step_01": {
                "input": "Please enter JSON counter data for the histogram.",
                "complete": "Counter data processed and histogram rendered."
            }
        }

        # Add finalize step
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

    # --- Core Workflow Engine Methods ---

    async def landing(self):
        """ Renders the initial landing page with the key input form. """
        pip, pipeline, steps, app_name = self.pipulate, self.pipeline, self.steps, self.app_name
        context = pip.get_plugin_context(self)
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
        """ Initialize the workflow state and redirect to the first step. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        user_input = form.get("pipeline_id", "").strip()

        if not user_input:
            from starlette.responses import Response
            response = Response("")
            response.headers["HX-Refresh"] = "true"
            return response

        # Generate or parse the unique pipeline ID
        context = pip.get_plugin_context(self)
        plugin_name = context['plugin_name'] or app_name
        profile_name = context['profile_name'] or "default"
        profile_part = profile_name.replace(" ", "_")
        plugin_part = plugin_name.replace(" ", "_")
        expected_prefix = f"{profile_part}-{plugin_part}-"

        if user_input.startswith(expected_prefix):
            pipeline_id = user_input
        else:
            _, prefix, user_provided_id = pip.generate_pipeline_key(self, user_input)
            pipeline_id = f"{prefix}{user_provided_id}"

        db["pipeline_id"] = pipeline_id
        logger.debug(f"Using pipeline ID: {pipeline_id}")

        # Initialize state if missing
        state, error = pip.initialize_if_missing(pipeline_id, {"app_name": app_name})
        if error: return error
        all_steps_complete = all(step.id in state and step.done in state[step.id] for step in steps[:-1])
        is_finalized = "finalize" in state and "finalized" in state["finalize"]

        # Add initial status messages
        await self.message_queue.add(pip, f"Workflow ID: {pipeline_id}", verbatim=True, spaces_before=0)
        await self.message_queue.add(pip, f"Return later by selecting '{pipeline_id}' from the dropdown.", verbatim=True, spaces_before=0)
        if all_steps_complete:
            status_msg = f"Workflow is complete and finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes." if is_finalized \
                else "Workflow is complete but not finalized. Press Finalize to lock your data."
            await self.message_queue.add(pip, status_msg, verbatim=True)
        elif not any(step.id in state for step in self.steps):
            await self.message_queue.add(pip, self.step_messages["new"], verbatim=True)

        # Update the datalist
        parsed = pip.parse_pipeline_key(pipeline_id)
        prefix = f"{parsed['profile_part']}-{parsed['plugin_part']}-"
        self.pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in self.pipeline() if record.pkey.startswith(prefix)]
        if pipeline_id not in matching_records: matching_records.append(pipeline_id)
        updated_datalist = pip.update_datalist("pipeline-ids", options=matching_records)

        # Rebuild the UI, triggering the first step load
        return pip.rebuild(app_name, steps)

    async def finalize(self, request):
        """ Handle GET/POST requests to finalize (lock) the workflow. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        finalize_step = steps[-1]
        finalize_data = pip.get_step_data(pipeline_id, finalize_step.id, {})

        if request.method == "GET":
            # Show locked view or finalize button
            if finalize_step.done in finalize_data:
                return Card(
                    H3("Workflow is locked."),
                    Form(
                        Button(pip.UNLOCK_BUTTON_LABEL, type="submit", cls="secondary outline"),
                        hx_post=f"/{app_name}/unfinalize", hx_target=f"#{app_name}-container", hx_swap="outerHTML"
                    ),
                    id=finalize_step.id
                )
            else:
                # Check if all steps are complete before offering finalize
                all_steps_complete = all(pip.get_step_data(pipeline_id, step.id, {}).get(step.done) for step in steps[:-1])
                if all_steps_complete:
                    return Card(
                        H3("All steps complete. Finalize?"),
                        P("You can revert to any step and make changes.", style="font-size: 0.9em; color: #666;"),
                        Form(
                            Button("Finalize 🔒", type="submit", cls="primary"),
                            hx_post=f"/{app_name}/finalize", hx_target=f"#{app_name}-container", hx_swap="outerHTML"
                        ),
                        id=finalize_step.id
                    )
                else:
                    return Div(id=finalize_step.id)
        else:  # POST request
            await pip.finalize_workflow(pipeline_id)
            await self.message_queue.add(pip, self.step_messages["finalize"]["complete"], verbatim=True)
            return pip.rebuild(app_name, steps)

    async def unfinalize(self, request):
        """ Handle POST request to unlock the workflow. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, "Workflow unfinalized! You can now revert to any step and make changes.", verbatim=True)
        return pip.rebuild(app_name, steps)

    async def get_suggestion(self, step_id, state):
        """ Gets a suggested input value for a step. """
        if step_id == 'step_01':
            return """{
    "apples": 35,
    "oranges": 42,
    "bananas": 28,
    "grapes": 51,
    "peaches": 22,
    "plums": 18,
    "mangoes": 39
}"""
        return ""

    async def handle_revert(self, request):
        """ Handle POST request to revert to a previous step. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        pipeline_id = db.get("pipeline_id", "unknown")
        if not step_id: return P("Error: No step specified", style=pip.get_style("error"))

        # Clear state from the target step onwards
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        # Mark the target step for revert logic in GET handlers
        state = pip.read_state(pipeline_id)
        state["_revert_target"] = step_id
        pip.write_state(pipeline_id, state)

        # Add message and rebuild UI
        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        return pip.rebuild(app_name, steps)

    # --- Step 1: Matplotlib Histogram Widget ---
    async def step_01(self, request):
        """ 
        Handles GET request for Step 1: Matplotlib Histogram Widget.
        
        This step allows users to input counter data and visualizes it as a histogram.
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        counter_data = step_data.get(step.done, "")
        
        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and counter_data:
            # Show the histogram in locked state
            try:
                histogram_widget = self.create_matplotlib_histogram(counter_data)
                return Div(
                    Card(
                        H3(f"🔒 {step.show}"),
                        histogram_widget
                    ),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                )
            except Exception as e:
                logger.error(f"Error creating histogram in finalized view: {str(e)}")
                return Div(
                    Card(f"🔒 {step.show}: <content locked>"),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                )
            
        # Check if step is complete and not reverting
        elif counter_data and state.get("_revert_target") != step_id:
            # Create the histogram widget from the existing data
            try:
                histogram_widget = self.create_matplotlib_histogram(counter_data)
                content_container = pip.widget_container(
                    step_id=step_id,
                    app_name=app_name,
                    message=f"{step.show} Configured",
                    widget=histogram_widget,
                    steps=steps
                )
                return Div(
                    content_container,
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                )
            except Exception as e:
                # If there's an error creating the widget, revert to input form
                logger.error(f"Error creating histogram widget: {str(e)}")
                state["_revert_target"] = step_id
                pip.write_state(pipeline_id, state)
        
        # Show input form
        display_value = counter_data if step.refill and counter_data else await self.get_suggestion(step_id, state)
        await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
        
        return Div(
            Card(
                H3(f"{pip.fmt(step_id)}: Configure {step.show}"),
                P("Enter counter data as JSON object (keys and values):"),
                P("Format: {\"category1\": count1, \"category2\": count2, ...}", 
                  style="font-size: 0.8em; font-style: italic;"),
                Form(
                    Div(
                        Textarea(
                            display_value,
                            name=step.done,
                            placeholder="Enter JSON object for Counter data",
                            required=True,
                            rows=10,
                            style="width: 100%; font-family: monospace;"
                        ),
                        Div(
                            Button("Create Histogram ▸", type="submit", cls="primary"),
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
        """ 
        Process the submission for Step 1 (Matplotlib Histogram).
        
        Takes counter data as input and creates a histogram visualization.
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get("pipeline_id", "unknown")
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'

        # Get form data
        form = await request.form()
        counter_data = form.get(step.done, "").strip()

        # Validate input
        is_valid, error_msg, error_component = pip.validate_step_input(counter_data, step.show)
        if not is_valid:
            return error_component
        
        # Additional validation for JSON format
        try:
            data = json.loads(counter_data)
            if not isinstance(data, dict):
                return P("Invalid JSON: Must be an object (dictionary) with keys and values", style=pip.get_style("error"))
            if not data:
                return P("Invalid data: Counter cannot be empty", style=pip.get_style("error"))
        except json.JSONDecodeError:
            return P("Invalid JSON format. Please check your syntax.", style=pip.get_style("error"))

        # Save the counter data to state
        await pip.update_step_state(pipeline_id, step_id, counter_data, steps)

        # Create the matplotlib histogram widget
        try:
            histogram_widget = self.create_matplotlib_histogram(counter_data)
            
            # Create content container with the widget
            content_container = pip.widget_container(
                step_id=step_id,
                app_name=app_name,
                message=f"{step.show}: Histogram created from Counter data",
                widget=histogram_widget,
                steps=steps
            )
            
            # Create full response structure
            response_content = Div(
                content_container,
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
            
            # Send confirmation message
            await self.message_queue.add(pip, f"{step.show} complete. Histogram created.", verbatim=True)

            # Return the HTMLResponse with the widget container
            return HTMLResponse(to_xml(response_content))
            
        except Exception as e:
            logger.error(f"Error creating histogram visualization: {e}")
            return P(f"Error creating histogram: {str(e)}", style=pip.get_style("error"))

    def create_matplotlib_histogram(self, data_str):
        """
        Create a matplotlib histogram visualization from JSON counter data.
        
        Args:
            data_str: A JSON string representing counter data
            
        Returns:
            A Div element containing the histogram image
        """
        try:
            # Parse the JSON data
            data = json.loads(data_str)
            
            if not isinstance(data, dict):
                return Div(NotStr("<div style='color: red;'>Error: Data must be a JSON object with keys and values</div>"), _raw=True)
            
            # Create a Counter from the data
            counter = Counter(data)
            
            # Check if we have data to plot
            if not counter:
                return Div(NotStr("<div style='color: red;'>Error: No data to plot</div>"), _raw=True)
            
            # Generate the matplotlib figure
            plt.figure(figsize=(10, 6))
            
            # Sort data by keys for better visualization
            labels = sorted(counter.keys())
            values = [counter[label] for label in labels]
            
            # Create the bar plot
            plt.bar(labels, values, color='skyblue')
            
            # Add labels and title
            plt.xlabel('Categories')
            plt.ylabel('Counts')
            plt.title('Histogram from Counter Data')
            
            # Add grid for better readability
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            # Rotate x-axis labels if there are many categories
            if len(labels) > 5:
                plt.xticks(rotation=45, ha='right')
            
            # Adjust layout
            plt.tight_layout()
            
            # Save figure to a bytes buffer
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            plt.close()
            
            # Convert to base64 for embedding in HTML
            img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Create an HTML component with the image and some metadata
            return Div(
                H4("Histogram Visualization:"),
                P(f"Data: {len(counter)} categories, {sum(counter.values())} total counts"),
                Div(
                    NotStr(f'<img src="data:image/png;base64,{img_str}" style="max-width:100%; height:auto;" />'),
                    style="text-align: center; margin-top: 1rem;"
                ),
                style="overflow-x: auto;"
            )
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            return Div(NotStr(f"<div style='color: red;'>Error creating histogram: {str(e)}<br><pre>{tb}</pre></div>"), _raw=True) 
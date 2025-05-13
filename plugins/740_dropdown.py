import asyncio
from collections import namedtuple
from datetime import datetime

from fasthtml.common import * # type: ignore
from loguru import logger

"""
Pipulate Dropdown Widget
A standalone dropdown widget workflow for selecting from a list of options.
"""

# Model for a workflow step
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class DropdownWidget:
    """
    Dropdown Widget Workflow
    
    A focused environment for implementing and testing dropdown selection widgets.
    """
    # --- Workflow Configuration ---
    APP_NAME = "dropdown_widget"     # Unique identifier for this workflow's routes and data (must be different from plugin name from filename)
    DISPLAY_NAME = "Dropdown Widget" # User-friendly name shown in the UI
    ENDPOINT_MESSAGE = (             # Message shown on the workflow's landing page
        "Welcome to the Dropdown Widget! This is a focused environment for implementing and testing dropdown selection widgets. "
        "Use this space to prototype and refine your dropdown designs without distractions."
    )
    TRAINING_PROMPT = (
        "This is a specialized workflow for implementing and testing dropdown selection widgets. "
        "It provides a clean environment to focus on dropdown development without the complexity "
        "of a full workflow implementation."
    )
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
                done='placeholder',
                show='Step 1 Placeholder',
                refill=False,
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
                    return Card(
                        H3("Not ready to finalize."),
                        P("Complete all steps first.", style="font-size: 0.9em; color: #666;"),
                        id=finalize_step.id
                    )
        else:  # POST request
            # Store finalization in state
            await pip.update_step_state(pipeline_id, finalize_step.id, "finalized", steps)
            await self.message_queue.add(pip, self.step_messages["finalize"]["complete"], verbatim=True)
            
            # Return the finalized view
            return Card(
                H3("Workflow is locked."),
                Form(
                    Button(pip.UNLOCK_BUTTON_LABEL, type="submit", cls="secondary outline"),
                    hx_post=f"/{app_name}/unfinalize", 
                    hx_target=f"#{app_name}-container"
                ),
                id=finalize_step.id
            )

    async def unfinalize(self, request):
        """Handles POST request to unlock the workflow."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        finalize_step = steps[-1]
        
        # Clear finalization from state
        await pip.update_step_state(pipeline_id, finalize_step.id, "", steps)
        await self.message_queue.add(pip, "Workflow unlocked. You can now make changes.", verbatim=True)
        
        # Return to the first step
        return Div(
            Div(id="step_01", hx_get=f"/{app_name}/step_01", hx_trigger="load"),
            id=f"{app_name}-container"
        )

    async def jump_to_step(self, request):
        """Handles POST request to jump to a specific step."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id", "")
        
        if step_id not in self.steps_indices:
            return P("Error: Invalid step", style=pip.get_style("error"))
        
        return Div(
            Div(id=step_id, hx_get=f"/{app_name}/{step_id}", hx_trigger="load"),
            id=f"{app_name}-container"
        )

    async def get_suggestion(self, step_id, state):
        """Returns a suggestion for the current step based on state."""
        return "Complete this step to continue."

    async def handle_revert(self, request):
        """Handles POST request to revert to a previous step."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id", "")
        
        if step_id not in self.steps_indices:
            return P("Error: Invalid step", style=pip.get_style("error"))
        
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Clear state from this step forward
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        
        # Set revert target in state
        state = pip.read_state(pipeline_id)
        state["_revert_target"] = step_id
        pip.write_state(pipeline_id, state)
        
        # Return to the target step
        return Div(
            Div(id=step_id, hx_get=f"/{app_name}/{step_id}", hx_trigger="load"),
            id=f"{app_name}-container"
        )

    async def step_01(self, request):
        """Handles GET request for Step 1."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        
        # Get the value if already completed
        value = step_data.get(step.done, "")
        
        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and value:
            # Show finalized state
            return Div(
                Card(
                    H3(f"🔒 {step.show}"),
                    P(f"Value: {value}", style="font-weight: bold;")
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        
        # Check if step is complete and not being reverted to
        if value and state.get("_revert_target") != step_id:
            # Show completed state
            return Div(
                pip.revert_control(
                    step_id=step_id, 
                    app_name=app_name, 
                    message=f"{step.show}: {value}",
                    steps=steps
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        
        # Show the input form
        await self.message_queue.add(pip, self.step_messages.get(step_id, {}).get("input", 
                                f"Complete {step.show}"), 
                                verbatim=True)
        
        return Div(
            Card(
                H3(f"{step.show}"),
                Form(
                    Input(
                        type="text",
                        name=step.done,
                        value=value if value else "",
                        required=True,
                        autofocus=True
                    ),
                    Button("Submit", type="submit", cls="primary"),
                    hx_post=f"/{app_name}/{step_id}_submit",
                    hx_target=f"#{step_id}"
                )
            ),
            Div(id=next_step_id),
            id=step_id
        )

    async def step_01_submit(self, request):
        """Handles POST request for Step 1."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Get form data
        form = await request.form()
        value = form.get(step.done, "").strip()
        
        if not value:
            return P("Error: Field is required", style=pip.get_style("error"))
        
        # Update state
        await pip.update_step_state(pipeline_id, step_id, value, steps)
        await self.message_queue.add(pip, self.step_messages.get(step_id, {}).get("complete", 
                                f"{step.show} complete: {value}"), 
                                verbatim=True)
        
        # Return with revert control and chain reaction
        return Div(
            pip.revert_control(
                step_id=step_id, 
                app_name=app_name, 
                message=f"{step.show}: {value}",
                steps=steps
            ),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        ) 
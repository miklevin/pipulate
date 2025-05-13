import asyncio
from collections import namedtuple
from datetime import datetime

from fasthtml.common import * # type: ignore
from loguru import logger

"""
Pipulate Switch Workflow
A workflow for managing and testing switch/toggle-based interactions.

RULE NAVIGATION GUIDE:
--------------------
1. Core Widget Patterns:
   - See: patterns/workflow-patterns.mdc
   - Key sections: "Common Widget Patterns", "Widget State Management"
   - Critical for understanding the immutable chain reaction pattern

2. Implementation Guidelines:
   - See: implementation/implementation-workflow.mdc
   - Focus on: "Widget Implementation Steps", "Widget Testing Checklist"
   - Essential for maintaining workflow integrity

3. Common Pitfalls:
   - See: patterns/workflow-patterns.mdc
   - Review: "Common Widget Pitfalls", "Recovery Process"
   - Critical for avoiding state management issues

4. Widget Design Philosophy:
   - See: philosophy/philosophy-core.mdc
   - Key concepts: "State Management", "UI Construction"
   - Important for maintaining consistent patterns

5. Recovery Patterns:
   - See: patterns/workflow-patterns.mdc
   - Focus on: "Recovery Process", "Prevention Guidelines"
   - Essential for handling workflow breaks

CONVERSION POINTS:
----------------
When converting this template to a new widget:
1. CUSTOMIZE_STEP_DEFINITION: Change 'done' field to specific data field name
2. CUSTOMIZE_FORM: Replace the Proceed button with specific form elements
3. CUSTOMIZE_DISPLAY: Update the finalized state display for your widget
4. CUSTOMIZE_COMPLETE: Enhance the completion state with widget display

CRITICAL ELEMENTS TO PRESERVE:
----------------------------
- Chain reaction with next_step_id
- Finalization state handling pattern
- Revert control mechanism
- Overall Div structure and ID patterns
- LLM context updates for widget content
"""

# Model for a workflow step
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class SwitchWorkflow:
    """
    Switch Workflow
    
    A focused environment for designing and testing switch/toggle-based interactions in isolation.
    This workflow provides a clean environment to focus on switch development without the complexity
    of a full workflow implementation.
    """
    # --- Workflow Configuration ---
    APP_NAME = "toggle_widget"      # Unique identifier for this workflow's routes and data
    DISPLAY_NAME = "Switch Widget" # User-friendly name shown in the UI
    ENDPOINT_MESSAGE = (             # Message shown on the workflow's landing page
        "Welcome to the Switch Widget! This is a focused environment for designing and testing "
        "switch/toggle-based interactions in isolation. Use this space to prototype and refine your "
        "switch designs without distractions."
    )
    TRAINING_PROMPT = (
        "This is a specialized workflow for designing and testing switch interactions in isolation. "
        "It provides a clean environment to focus on switch development without the complexity "
        "of a full workflow implementation."
    )

    # --- Switch Configuration ---
    SWITCH_CONFIG = {
        "switches": [
            {
                "id": "switch_1",
                "label": "First Switch",
                "description": "This is the first switch",
                "default": False
            },
            {
                "id": "switch_2",
                "label": "Second Switch",
                "description": "This is the second switch",
                "default": False
            }
        ]
    }

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
                done='switch_state',
                show='Switch State',
                refill=True,
                transform=lambda prev_value: bool(prev_value) if prev_value is not None else self.SWITCH_CONFIG["switches"][-1]["default"]
            ),
            # Add more steps as needed
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

    async def get_suggestion(self, step_id, state):
        """Returns a suggestion for the current step based on state."""
        return "Complete this step to continue."

    async def handle_revert(self, request):
        """Handles POST request to revert to a previous step."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id", "")
        
        if step_id not in self.steps_indices:
            return P("Error: Invalid step", style=self.pipulate.get_style("error"))
        
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
        """Handles GET request for switch configuration step."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")

        # Get current state
        state = pip.get_step_data(pipeline_id, step_id, {})
        switch_state = state.get(step.done, {})

        # Keep LLM informed about showing input form
        pip.append_to_history(f"[WIDGET STATE] {step.show}: Showing input form")
        
        await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
        
        # Create switch inputs
        switch_inputs = []
        for switch in self.SWITCH_CONFIG["switches"]:
            current_state = switch_state.get(switch["id"], switch["default"])
            switch_inputs.append(
                Div(
                    Label(
                        Input(
                            type="checkbox",
                            role="switch",
                            name=f"switch_{switch['id']}",
                            checked=current_state,
                            cls="contrast"
                        ),
                        Span(switch["label"], style="margin-left: 0.5rem;")
                    ),
                    style="margin-bottom: 1rem;"
                )
            )

        return Div(
            Card(
                H3(f"{pip.fmt(step_id)}: Configure {step.show}"),
                P("Toggle the switches to configure your settings."),
                Form(
                    Div(
                        *switch_inputs,
                        Div(
                            Button("Save Settings ▸", type="submit", cls="primary"),
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
        """Handles POST request for switch configuration step."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Get form data
        form = await request.form()
        switch_state = {}
        
        # Process each switch state
        for switch in self.SWITCH_CONFIG["switches"]:
            switch_state[switch["id"]] = form.get(f"switch_{switch['id']}") == "on"
        
        # Update state
        await pip.update_step_state(pipeline_id, step_id, switch_state, steps)
        await self.message_queue.add(pip, self.step_messages.get(step_id, {}).get("complete", 
                                f"{step.show} complete: {switch_state}"), 
                                verbatim=True)
        
        # Return with revert control and chain reaction
        return Div(
            pip.revert_control(
                step_id=step_id, 
                app_name=app_name, 
                message=f"{step.show}: Settings saved",
                steps=steps
            ),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        ) 
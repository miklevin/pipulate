import asyncio
from collections import namedtuple
from datetime import datetime

from fasthtml.common import * # type: ignore
from loguru import logger

"""
Pipulate Workflow Template
A minimal starter template for creating step-based Pipulate workflows.

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


class WidgetDesigner:
    """
    Widget Designer Workflow
    
    A focused environment for designing and testing new widgets in isolation.
    """
    # --- Workflow Configuration ---
    APP_NAME = "design_widget"       # Unique identifier for this workflow's routes and data (most be different from plugin name from filename)
    DISPLAY_NAME = "Widget Designer" # User-friendly name shown in the UI
    ENDPOINT_MESSAGE = (             # Message shown on the workflow's landing page
        "Welcome to the Widget Designer! This is a focused environment for designing and testing new widgets in isolation. "
        "Use this space to prototype and refine your widget designs without distractions."
    )
    TRAINING_PROMPT = (
        "This is a specialized workflow for designing and testing widgets in isolation. "
        "It provides a clean environment to focus on widget development without the complexity "
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
        """Handles GET request for placeholder Step 1.
        
        Widget Conversion Points:
        1. CUSTOMIZE_STEP_DEFINITION: Change 'done' field to specific data field name
        2. CUSTOMIZE_FORM: Replace the Proceed button with specific form elements
        3. CUSTOMIZE_DISPLAY: Update the finalized state display for your widget
        4. CUSTOMIZE_COMPLETE: Enhance the completion state with widget display
        
        Critical Elements to Preserve:
        - Chain reaction with next_step_id
        - Finalization state handling pattern
        - Revert control mechanism
        - Overall Div structure and ID patterns
        - LLM context updates for widget content
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        placeholder_value = step_data.get(step.done, "")  # CUSTOMIZE_VALUE_ACCESS: Rename to match your data field

        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and placeholder_value:
            # Keep LLM informed about the finalized widget content
            pip.append_to_history(f"[WIDGET CONTENT] {step.show} (Finalized):\n{placeholder_value}")
            
            # CUSTOMIZE_DISPLAY: Enhanced finalized state display for your widget
            return Div(
                Card(
                    H3(f"🔒 {step.show}: Completed")  # Combined headline with completion status
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
            
        # Check if step is complete and not being reverted to
        elif placeholder_value and state.get("_revert_target") != step_id:
            # Keep LLM informed about the completed widget content
            pip.append_to_history(f"[WIDGET CONTENT] {step.show} (Completed):\n{placeholder_value}")
            
            # CUSTOMIZE_COMPLETE: Enhanced completion display for your widget
            return Div(
                pip.revert_control(step_id=step_id, app_name=app_name, message=f"{step.show}: Complete", steps=steps),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        else:
            # Keep LLM informed about showing the input form
            pip.append_to_history(f"[WIDGET STATE] {step.show}: Showing input form")
            
            # CUSTOMIZE_FORM: Replace with your widget's input form
            await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
            
            return Div(
                Card(
                    H3(f"{step.show}"),
                    P("This is a placeholder step. Click Proceed to continue to the next step."),
                    Form(
                        Button("Next ▸", type="submit", cls="primary"),
                        hx_post=f"/{app_name}/{step_id}_submit", 
                        hx_target=f"#{step_id}"
                    )
                ),
                Div(id=next_step_id),  # PRESERVE: Empty div for next step - DO NOT ADD hx_trigger HERE
                id=step_id
            )

    async def step_01_submit(self, request):
        """Process the submission for placeholder Step 1.
        
        Chain Reaction Pattern:
        When a step completes, it MUST explicitly trigger the next step by including
        a div for the next step with hx-trigger="load". While this may seem redundant,
        it is more reliable than depending on HTMX event bubbling.
        
        LLM Context Pattern:
        Always keep the LLM informed about:
        1. What was submitted (widget content)
        2. Any transformations or processing applied
        3. The final state of the widget
        Use pip.append_to_history() for this to avoid cluttering the chat interface.
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Process and save data...
        placeholder_value = "completed"
        await pip.update_step_state(pipeline_id, step_id, placeholder_value, steps)
        
        # Keep LLM informed about the widget content and state
        pip.append_to_history(f"[WIDGET CONTENT] {step.show}:\n{placeholder_value}")
        pip.append_to_history(f"[WIDGET STATE] {step.show}: Step completed")
        
        # Send user-visible confirmation via message queue
        await self.message_queue.add(pip, f"{step.show} complete.", verbatim=True)
        
        # CRITICAL: Return the completed view WITH explicit next step trigger
        return Div(
            pip.revert_control(step_id=step_id, app_name=app_name, message=f"{step.show}: Complete", steps=steps),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
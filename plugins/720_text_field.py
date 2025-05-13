import asyncio
from collections import namedtuple
from datetime import datetime

from fasthtml.common import * # type: ignore
from loguru import logger

"""
Text Field Widget Workflow
A minimal template for creating a text field widget workflow, based on the blank placeholder pattern.

RULE NAVIGATION GUIDE:
--------------------
1. Text Input Patterns:
   - See: patterns/workflow-patterns.mdc
   - Key sections: "Text Input Widget Pattern", "Input Validation"
   - Critical for understanding text field implementation

2. State Management:
   - See: patterns/workflow-patterns.mdc
   - Focus on: "Widget State Management", "Text Input State"
   - Essential for proper text field state handling

3. UI Construction:
   - See: implementation/implementation-workflow.mdc
   - Review: "Text Input UI Patterns", "Form Structure"
   - Important for maintaining consistent text input UI

4. Validation Patterns:
   - See: patterns/workflow-patterns.mdc
   - Focus on: "Input Validation", "Error Handling"
   - Critical for text field validation

5. Recovery Process:
   - See: patterns/workflow-patterns.mdc
   - Review: "Recovery Process", "Text Input Recovery"
   - Essential for handling text field workflow breaks

IMPLEMENTATION NOTES:
-------------------
1. Text Field Specifics:
   - Uses single-line input with validation
   - Preserves input on revert (PRESERVE_REFILL)
   - Includes transform for text processing

2. State Management:
   - Stores text in 'text_input' field
   - Handles empty and whitespace cases
   - Maintains text formatting

3. UI Considerations:
   - Mobile-friendly input height
   - Clear validation feedback
   - Consistent text display

4. Common Pitfalls:
   - Whitespace handling
   - Empty input validation
   - State preservation on revert
"""

# Model for a workflow step
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class TextFieldWidget:
    """
    Text Field Widget Workflow
    
    A minimal template for creating a text field widget workflow, based on the blank placeholder pattern.
    """
    # --- Workflow Configuration ---
    APP_NAME = "text_field_widget"          # Unique identifier for this workflow's routes and data (must not match filename or display name)
    DISPLAY_NAME = "Text Field Widget"      # User-friendly name shown in the UI
    ENDPOINT_MESSAGE = (
        "Welcome to the Text Field Widget! This is a minimal template for creating a text field widget workflow. "
        "Use this as a starting point for your widget development."
    )
    TRAINING_PROMPT = (
        "This is a minimal template for creating a text field widget workflow. "
        "It provides a clean starting point for widget development."
    )
    PRESERVE_REFILL = True                  # Whether to keep input values when reverting

    # --- Initialization ---
    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
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
                done='text_input',        # Field to store the input value
                show='Text Input',        # User-friendly name
                refill=True,              # Allow refilling for better UX
                transform=lambda prev_value: prev_value.strip() if prev_value else ""  # Optional transform
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
                "input": f"{pip.fmt(step.id)}: Please enter {step.show}.",
                "complete": f"{step.show} complete. Continue to next step."
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
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, "Workflow unfinalized! You can now revert to any step and make changes.", verbatim=True)
        return pip.rebuild(app_name, steps)

    async def jump_to_step(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        db["step_id"] = step_id
        return pip.rebuild(app_name, steps)

    async def get_suggestion(self, step_id, state):
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
        """ Handles GET request for Step 1: Displays input form or completed value. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "")

        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and user_val:
            # Show locked view
            locked_msg = f"🔒 Text input is set to: {user_val}"
            await self.message_queue.add(pip, locked_msg, verbatim=True)
            return Div(
                Card(
                    H3(f"🔒 {step.show}: {user_val}")
                ),
                Div(id=next_step_id, hx_get=f"/{self.app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )

        # Check if step is complete and we are NOT reverting to it
        elif user_val and state.get("_revert_target") != step_id:
            # Show completed view with Revert button
            completed_msg = f"Step 1 is complete. You entered: {user_val}"
            await self.message_queue.add(pip, completed_msg, verbatim=True)
            return Div(
                pip.revert_control(step_id=step_id, app_name=app_name, message=f"{step.show}: {user_val}", steps=steps),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
            )
        else:
            # Show the input form for this step
            display_value = user_val if (step.refill and user_val and self.PRESERVE_REFILL) else await self.get_suggestion(step_id, state)
            
            # Let LLM know we're showing an empty form via message queue
            form_msg = "Showing text input form. No text has been entered yet."
            await self.message_queue.add(pip, form_msg, verbatim=True)
            
            # Add prompt message to UI
            await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
            
            # Add explanation to both UI and LLM context
            explanation = "This is a simple text input widget. Enter any text you'd like to store."
            await self.message_queue.add(pip, explanation, verbatim=True)
            
            # Render the card with the form
            return Div(
                Card(
                    H3(f"{pip.fmt(step.id)}: Enter {step.show}"),
                    P(explanation, style=pip.get_style("muted")),
                    Form(
                        pip.wrap_with_inline_button(
                            Input(
                                type="text",
                                name=step.done,
                                value=display_value,
                                placeholder=f"Enter {step.show}",
                                required=True,
                                autofocus=True,
                                _onfocus='this.setSelectionRange(this.value.length, this.value.length)',
                                style="min-height: 44px;",  # Mobile touch target
                                aria_required="true",
                                aria_labelledby=f"{step_id}-form-title",
                                aria_describedby=f"{step_id}-form-instruction"
                            ),
                            button_label="Next ▸"
                        ),
                        hx_post=f"/{app_name}/{step.id}_submit",
                        hx_target=f"#{step.id}"
                    )
                ),
                Div(id=next_step_id),
                id=step.id
            )

    async def step_01_submit(self, request):
        """Process the submission for Step 1."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")

        # Boilerplate: Check finalized state (optional, submit shouldn't be possible)
        if step.done == 'finalized':
            return await pip.handle_finalized_step(pipeline_id, step_id, steps, app_name, self)

        # Get form data
        form = await request.form()
        user_val = form.get(step.done, "").strip() # Get value for 'text_input' field

        # Let LLM know we received a submission via message queue
        submit_msg = f"User submitted text: {user_val}"
        await self.message_queue.add(pip, submit_msg, verbatim=True)

        # --- Custom Validation ---
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            error_msg = f"Text validation failed: {error_msg}"
            await self.message_queue.add(pip, error_msg, verbatim=True)
            return error_component

        # --- Custom Processing ---
        processed_val = user_val # Keep it simple for template
        # --- End Custom Processing ---

        # Save the processed value to this step's state
        await pip.update_step_state(pipeline_id, step_id, processed_val, steps)

        # Send confirmation message to UI and LLM via message queue
        confirm_msg = f"{step.show}: {processed_val}"
        await self.message_queue.add(pip, confirm_msg, verbatim=True)

        # Check if this was the last step before finalize
        if pip.check_finalize_needed(step_index, steps):
            finalize_msg = self.step_messages["finalize"]["ready"]
            await self.message_queue.add(pip, finalize_msg, verbatim=True)

        # Return the standard navigation controls (Revert button + trigger for next step)
        return Div(
            pip.revert_control(step_id=step_id, app_name=app_name, message=f"{step.show}: {processed_val}", steps=steps),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        ) 
from collections import namedtuple
from datetime import datetime

from fasthtml.common import *  # type: ignore
from loguru import logger

ROLES = ['Core', 'SEO Practitioner', 'Botify Employee', 'Developer', 'Tutorial']

# Warning: This is an intentionally local-first app using server-side state and HTMX.
# Do not refactor the DictLikeDB or HTMX patterns - see README.md and .cursor/rules
# for the design philosophy and contribution guidelines.

"""
Pipulate Workflow Template (Hello World Example)

This file serves as a starting point for creating linear, step-by-step Pipulate Workflows.
It includes essential boilerplate and demonstrates core concepts.

--- The Chain Reaction Pattern ---
Pipulate workflows use HTMX's chain reaction pattern to create a "Run All Cells" experience
similar to Jupyter Notebooks. Each step automatically triggers the next step's loading
until it encounters a step requiring user input. This creates a robust, resumable workflow.

The chain reaction is maintained through three distinct phases in each step:

1. Finalize Phase: Shows locked view of completed step, chains to next step
2. Revert Phase: Shows completed view with revert option, chains to next step
3. Get Input Phase: Shows input form, waits for user submission

The chain is maintained by including a Div with hx_trigger="load" in the response:
```python
return Div(
    Card(...),  # Current step content
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id
)
```

--- Basic Workflow Pattern ---
1. Define steps sequentially using the `Step` namedtuple.
2. Implement GET (`step_XX`) and POST (`step_XX_submit`) handlers for each step.
3. Data typically flows from the `done` field of one step to the next via the
   `transform` function and `get_suggestion` method.
4. Use helper methods from `self.pipulate` (aliased as `pip`) for common tasks
   like state management, UI generation, and validation.
5. Workflows can be reverted to previous steps or finalized to lock them.

--- Step Phases in Detail ---
Each step has three phases, implemented in the GET handler:

1. Finalize Phase (Locked View):
   ```python
   if "finalized" in finalize_data and step_value:
       return Div(
           Card(H3(f"🔒 {step.show}: {step_value}")),
           Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
           id=step_id
       )
   ```

2. Revert Phase (Completed View):
   ```python
   elif step_value and state.get("_revert_target") != step_id:
       return Div(
           Card(H3(f"{step.show}: {step_value}")),
           Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
           id=step_id
       )
   ```

3. Get Input Phase (Form View):
   ```python
   else:
       return Div(
           Card(
               H3(f"{step.show}"),
               Form(...)  # Input form here
           ),
           Div(id=next_step_id),  # No hx_trigger - wait for form submission
           id=step_id
       )
   ```

The submit handler (`step_XX_submit`) is essentially a specialized version of the Revert Phase,
showing the completed view with the newly submitted data.

--- Adapting This Template ---
1.  **Copy & Rename:** Copy this file. Rename the class (e.g., `MyWorkflow`),
    `APP_NAME` (must be unique), `DISPLAY_NAME`, and `ENDPOINT_MESSAGE`.
2.  **Training Prompt:** Create a `your_workflow_name.md` file in the `/training`
    directory (or provide plain text) and update `TRAINING_PROMPT`.
3.  **Define Steps:** Modify the `steps` list in `__init__` to define your workflow's
    sequence, fields, and data transformations.
4.  **Implement Handlers:** Create `step_XX` and `step_XX_submit` methods for each
    step ID you defined. Use the examples below as a guide. Add your custom
    validation, data processing (API calls, calculations, Playwright, etc.),
    and UI logic within these handlers.

--- Pipulate App Types ---
1. Workflows (like this one): Linear, step-based apps. Code is often explicit (WET).
2. Apps (inheriting from `BaseApp`): CRUD-style apps for managing data in a
   single table. More abstracted (DRY).

Get ready to get WET with Workflows!
"""

# Model for a workflow step (Do not change)
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class HelloFlow:
    """
    Hello World Workflow Example

    Demonstrates a simple two-step workflow asking for a name and generating a greeting.

    --- Key Concepts for Building Workflows ---

    * **Steps Definition (`steps` list in `__init__`)**
        * `id`: Unique identifier ('step_XX' format recommended).
        * `done`: The key in the step's state data that marks it complete (usually the primary input field name).
        * `show`: User-friendly label for the step/field.
        * `refill`: If `True`, the input field will be pre-filled with the existing value when reverting to this step.
        * `transform`: A `lambda` function that takes the `done` value from the *previous* step and processes it. The result is used by `get_suggestion` to potentially pre-fill the *current* step's input.

    * **Inter-Step Data Flow**
        1.  **`transform` & `get_suggestion`:** Simple way to pass and modify data sequentially. The `transform` lambda on `step_02` processes `step_01`'s output. `get_suggestion` uses this for `step_02`'s input placeholder.
        2.  **Direct State Access:** In any handler (`step_XX` or `step_XX_submit`), you can read data from *any* previous step:
            ```python
            pip = self.pipulate
            pipeline_id = self.db.get("pipeline_id")
            # Get all data stored for step_01
            step_01_data = pip.get_step_data(pipeline_id, "step_01", {})
            # Get the specific 'done' value from step_01
            previous_name = step_01_data.get('name')
            ```

    * **State Management (`pipulate` helpers)**
        * `pip.read_state(pipeline_id)`: Reads the entire workflow state dictionary.
        * `pip.get_step_data(pipeline_id, step_id, default={})`: Reads the dictionary for a specific step.
        * `await pip.set_step_data(pipeline_id, step_id, value, steps)`: *Recommended way* to save the primary `done` value for a step. Also updates internal step tracking.
        * `pip.write_state(pipeline_id, state)`: Saves the entire state dictionary (use carefully).
        * `_revert_target`: A key automatically added to the state by `handle_revert` indicating which step the user reverted to. Check `state.get('_revert_target') == step_id` in `step_XX` handlers to decide whether to show the input form or the completed view.
        * `_preserve_completed`: You can manually set `state[step_id]['_preserve_completed'] = True` (e.g., in `unfinalize` or `handle_revert`) if you want a specific step (like one involving a download) to remain in its "completed" view even after unfinalizing or reverting *past* it.

    * **Core Methods vs. Custom Handlers:**
        * Core methods (`landing`, `init`, `finalize`, `unfinalize`, `handle_revert`, `get_suggestion`, `run_all_cells`) provide the workflow engine. Avoid deleting or significantly modifying them.
        * Custom Handlers (`step_XX`, `step_XX_submit`) contain your specific workflow logic for each step. Modify these extensively.
    """
    # --- Workflow Configuration (CHANGE THESE) ---
    APP_NAME = "hello"              # Unique identifier for this workflow's routes and data
    DISPLAY_NAME = "Hello Workflow"    # User-friendly name shown in the UI
    ENDPOINT_MESSAGE = (            # Message shown on the workflow's landing page
        "Press Enter to start a new Workflow with this Key. "
        "Keys are arbitrary. Key standard is: Profile_Name-App_Name-XX"
    )
    TRAINING_PROMPT = "hello_workflow.md"  # Filename (in /training) or text for AI context

    # --- Initialization (Framework Setup - Generally Do Not Modify Core Logic) ---
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
        self.message_queue = pip.message_queue  # For ordered UI messages

        # ---> USER CUSTOMIZATION START <---
        # Define the ordered sequence of workflow steps.
        steps = [
            Step(
                id='step_01',          # HTML ID and part of URL path
                done='name',           # State key indicating step completion (usually input name)
                show='Your Name',      # Label shown in UI for this step/data
                refill=True,           # Refill input with this value on revert?
                # transform=None       # Step 1 usually doesn't transform previous data
            ),
            Step(
                id='step_02',
                done='greeting',
                show='Hello Message',
                refill=False,          # Usually False if value is generated/transformed
                transform=lambda name_from_step_01: f"Hello {name_from_step_01}!"  # Example: Generate greeting
            ),
            # Add more steps here following the pattern
        ]
        # ---> USER CUSTOMIZATION END <---

        # --- Route Registration (Framework Plumbing - Do Not Modify) ---
        # Standard workflow routes
        routes = [
            (f"/{app_name}", self.landing),                             # GET landing page
            (f"/{app_name}/init", self.init, ["POST"]),                 # POST init workflow
            (f"/{app_name}/revert", self.handle_revert, ["POST"]),      # POST revert step
            (f"/{app_name}/finalize", self.finalize, ["GET", "POST"]),  # GET/POST finalize
            (f"/{app_name}/unfinalize", self.unfinalize, ["POST"]),      # POST unfinalize
        ]

        # Routes for each custom step defined above
        self.steps = steps  # Store steps instance variable
        for step in steps:
            step_id = step.id
            # Add GET route for displaying the step UI
            routes.append((f"/{app_name}/{step_id}", getattr(self, step_id)))
            # Add POST route for submitting the step data
            routes.append((f"/{app_name}/{step_id}_submit", getattr(self, f"{step_id}_submit"), ["POST"]))

        # Register all routes with the FastHTML app
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ["GET"]
            app.route(path, methods=method_list)(handler)
        # --- End Route Registration ---

        # ---> USER CUSTOMIZATION START <---
        # Define messages used in UI feedback (especially for finalize)
        self.step_messages = {
            "finalize": {
                "ready": "All steps complete. Ready to finalize workflow.",
                "complete": f"Workflow finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes."
            }
        }

        # Creates default input/complete messages for each step (can be overridden)
        for step in steps:
            self.step_messages[step.id] = {
                "input": f"{pip.fmt(step.id)}: Please enter {step.show}.",
                "complete": f"{step.show} complete. Continue to next step."
            }
        # ---> USER CUSTOMIZATION END <---

        # Add the mandatory 'finalize' step internally (Do not change)
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}  # Map step IDs to indices

    # --- Core Workflow Engine Methods (Usually Do Not Modify) ---

    async def landing(self, request):
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
                P(self.ENDPOINT_MESSAGE, style=pip.get_style("muted")),
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
            Div(id=f"{app_name}-container")  # Target for HTMX updates
        )

    async def init(self, request):
        """ Handles the key submission, initializes state, and renders the step UI placeholders. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        user_input = form.get("pipeline_id", "").strip()

        if not user_input:  # Refresh if submitted blank (e.g., user wants auto-key)
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

        db["pipeline_id"] = pipeline_id  # Store in request-scoped DB
        logger.debug(f"Using pipeline ID: {pipeline_id}")

        # Initialize state if missing, check completion/finalization status
        state, error = pip.initialize_if_missing(pipeline_id, {"app_name": app_name})
        if error:
            return error
        all_steps_complete = all(step.id in state and step.done in state[step.id] for step in steps[:-1])
        is_finalized = "finalize" in state and "finalized" in state["finalize"]

        # Add initial status messages to the UI queue
        await self.message_queue.add(pip, f"Workflow ID: {pipeline_id}", verbatim=True, spaces_before=0)
        await self.message_queue.add(pip, f"Return later by selecting '{pipeline_id}' from the dropdown.", verbatim=True, spaces_before=0)
        if all_steps_complete:
            status_msg = f"Workflow is complete and finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes." if is_finalized \
                else "Workflow is complete but not finalized. Press Finalize to lock your data."
            await self.message_queue.add(pip, status_msg, verbatim=True)
        elif not any(step.id in state for step in self.steps):  # If brand new
            await self.message_queue.add(pip, "Please complete each step in sequence. Your progress will be saved automatically.", verbatim=True)

        # Update the datalist in the UI with the current key
        parsed = pip.parse_pipeline_key(pipeline_id)
        prefix = f"{parsed['profile_part']}-{parsed['plugin_part']}-"
        self.pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in self.pipeline() if record.pkey.startswith(prefix)]
        if pipeline_id not in matching_records:
            matching_records.append(pipeline_id)
        updated_datalist = pip.update_datalist("pipeline-ids", options=matching_records)

        # Rebuild the UI, triggering the first step load via HTMX
        return pip.rebuild(app_name, steps)

    async def finalize(self, request):
        """ Handles GET request to show Finalize button and POST request to lock the workflow. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        finalize_step = steps[-1]  # The internally added Step(id='finalize',...)
        finalize_data = pip.get_step_data(pipeline_id, finalize_step.id, {})

        if request.method == "GET":
            # Show locked view or finalize button
            if finalize_step.done in finalize_data:
                return Card(H3("Workflow is locked."),
                            P("You can unlock the workflow to make changes.", style=pip.get_style("muted")),
                            Form(Button(pip.UNLOCK_BUTTON_LABEL, type="submit", cls="secondary outline"),
                                 hx_post=f"/{app_name}/unfinalize", hx_target=f"#{app_name}-container", hx_swap="outerHTML"
                                 ), id=finalize_step.id)
            else:
                # Check if all *custom* steps are complete before offering finalize
                all_steps_complete = all(pip.get_step_data(pipeline_id, step.id, {}).get(step.done) for step in steps[:-1])
                if all_steps_complete:
                    return Card(H3("All steps complete. Finalize?"),
                                P("You can revert to any step and make changes. Or clear the Key and press Enter for a new Workflow. Or toggle the lock.", style=pip.get_style("muted")),
                                Form(Button("Finalize 🔒", type="submit", cls="primary"),
                                     hx_post=f"/{app_name}/finalize", hx_target=f"#{app_name}-container", hx_swap="outerHTML"
                                     ), id=finalize_step.id)
                else:
                    # Render an empty Div with the step ID if not ready to finalize, prevents breaking HTMX chain
                    return Div(id=finalize_step.id)
        else:  # POST request
            await pip.finalize_workflow(pipeline_id)
            await self.message_queue.add(pip, self.step_messages["finalize"]["complete"], verbatim=True)
            # Rebuild the entire UI to show locked state
            return pip.rebuild(app_name, steps)

    async def unfinalize(self, request):
        """ Handles POST request to unlock the workflow. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, "Workflow unfinalized! You can now revert to any step and make changes.", verbatim=True)
        # Rebuild the entire UI to show unlocked state
        return pip.rebuild(app_name, steps)

    async def get_suggestion(self, step_id, state):
        """ Gets a suggested input value for a step, often using the previous step's transformed output. """
        pip, db, steps = self.pipulate, self.db, self.steps
        step = next((s for s in steps if s.id == step_id), None)
        # Only provide suggestion if step has a transform function
        if not step or not step.transform:
            return ""
        prev_index = self.steps_indices[step_id] - 1
        if prev_index < 0:
            return ""  # No previous step for step_01
        prev_step = steps[prev_index]
        # Get the 'done' value from the previous step's saved data
        prev_data = pip.get_step_data(db["pipeline_id"], prev_step.id, {})
        prev_word = prev_data.get(prev_step.done, "")
        # Apply the current step's transform function to the previous step's value
        return step.transform(prev_word) if prev_word else ""

    async def handle_revert(self, request):
        """ Handles POST request to revert to a previous step, clearing subsequent step data. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        pipeline_id = db.get("pipeline_id", "unknown")
        if not step_id:
            return P("Error: No step specified", style=pip.get_style("error"))

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

    # --- Custom Workflow Step Handlers (Modify And Add Yours Here) ---

    # --- Step 1: Your Name ---
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

        # Boilerplate: Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data:
            # Show locked view - message queue will handle conversation history
            locked_msg = f"🔒 Your name is set to: {user_val}"
            await self.message_queue.add(pip, locked_msg, verbatim=True)
            return Div(
                Card(
                    H3(f"🔒 {step.show}: {user_val}")
                ),
                Div(id=next_step_id, hx_get=f"/{self.app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )

        # Boilerplate: Check if step is complete and we are NOT reverting to it
        elif user_val and state.get("_revert_target") != step_id:
            # Show completed view with Revert button - message queue handles history
            completed_msg = f"Step 1 is complete. You entered: {user_val}"
            await self.message_queue.add(pip, completed_msg, verbatim=True)
            return Div(
                pip.revert_control(step_id=step_id, app_name=app_name, message=f"{step.show}: {user_val}", steps=steps),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
            )
        else:
            # Show the input form for this step
            display_value = user_val if (step.refill and user_val) else await self.get_suggestion(step_id, state)

            # Let LLM know we're showing an empty form via message queue
            form_msg = "Showing name input form. No name has been entered yet."
            await self.message_queue.add(pip, form_msg, verbatim=True)

            # Add prompt message to UI
            await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)

            # Add explanation to both UI and LLM context
            explanation = "Workflows are like Python Notebooks where you don't have to look at the code to use it. Here we just collect some data."
            await self.message_queue.add(pip, explanation, verbatim=True)

            # Render the card with the form
            return Div(
                Card(
                    H3(f"{pip.fmt(step.id)}: Enter {step.show}"),
                    P(explanation, style=pip.get_style("muted")),
                    Form(
                        pip.wrap_with_inline_button(
                            Input(type="text", name=step.done, value=display_value,
                                  placeholder=f"Enter {step.show}", required=True, autofocus=True,
                                  _onfocus="this.setSelectionRange(this.value.length, this.value.length)"),
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
        """Process the submission for placeholder Step 1."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get("pipeline_id", "unknown")

        # Boilerplate: Check finalized state (optional, submit shouldn't be possible)
        if step.done == 'finalized':
            return await pip.handle_finalized_step(pipeline_id, step_id, steps, app_name, self)

        # Get form data
        form = await request.form()
        user_val = form.get(step.done, "")  # Get value for 'name' field

        # Let LLM know we received a submission via message queue
        submit_msg = f"User submitted name: {user_val}"
        await self.message_queue.add(pip, submit_msg, verbatim=True)

        # --- Custom Validation (Example) ---
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            error_msg = f"Name validation failed: {error_msg}"
            await self.message_queue.add(pip, error_msg, verbatim=True)
            return error_component
        # --- End Custom Validation ---

        # --- Custom Processing (Example) ---
        processed_val = user_val  # Keep it simple for template
        # --- End Custom Processing ---

        # Save the processed value to this step's state
        await pip.set_step_data(pipeline_id, step_id, processed_val, steps)

        # Send confirmation message to UI and LLM via message queue
        confirm_msg = f"{step.show}: {processed_val}"
        await self.message_queue.add(pip, confirm_msg, verbatim=True)

        # Check if this was the last step before finalize
        if pip.check_finalize_needed(step_index, steps):
            finalize_msg = self.step_messages["finalize"]["ready"]
            await self.message_queue.add(pip, finalize_msg, verbatim=True)

        # Return the standard navigation controls (Revert button + trigger for next step)
        return pip.create_step_navigation(step_id, step_index, steps, app_name, processed_val)

    # --- Step 2: Hello Message ---

    async def step_02(self, request):
        """ Handles GET request for Step 2: Displays input form or completed value. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_02"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'  # Next is finalize
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "")  # Get the saved value for 'greeting' if it exists

        # Boilerplate: Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data:
            # Show locked view
            return Div(
                Card(
                    H3(f"🔒 {step.show}: {user_val}")
                ),
                # Trigger loading the next step's (finalize) locked view
                Div(id=next_step_id, hx_get=f"/{self.app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )

        # Boilerplate: Check if step is complete and we are NOT reverting to it
        elif user_val and state.get("_revert_target") != step_id:
            # Show completed view with Revert button
            return Div(
                pip.revert_control(step_id=step_id, app_name=app_name, message=f"{step.show}: {user_val}", steps=steps),
                # CRITICAL: Explicitly trigger next step loading - this pattern is required for reliable workflow progression
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
            )
        else:
            # Show the input form for this step
            # Determine value: Use existing if refill enabled, otherwise get suggestion (uses transform)
            display_value = user_val if (step.refill and user_val) else await self.get_suggestion(step_id, state)
            # Add prompt message to UI
            await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
            # Render the card with the form
            return Div(
                Card(
                    H3(f"{pip.fmt(step.id)}: Enter {step.show}"),
                    P("Here we simply piped the output of the last step into the input for this step. That's all this workflow does.", style=pip.get_style("muted")),
                    Form(
                        pip.wrap_with_inline_button(
                            # Example: Using a readonly input because the value is generated by transform
                            Input(type="text", name=step.done, value=display_value,
                                  placeholder=f"{step.show} (generated)", required=True, autofocus=True,
                                  _onfocus="this.setSelectionRange(this.value.length, this.value.length)"),
                            button_label="Next ▸"
                        ),
                        hx_post=f"/{app_name}/{step.id}_submit",  # Submit to step_02_submit
                        hx_target=f"#{step.id}"                 # Replace this Div on response
                    )
                ),
                Div(id=next_step_id),  # Placeholder for the next step (finalize)
                id=step.id            # This Div gets replaced by HTMX on submit/revert
            )

    async def step_02_submit(self, request):
        """ Handles POST submission for Step 2: Validates, saves state, returns navigation. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_02"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get("pipeline_id", "unknown")

        # Boilerplate: Check finalized state
        if step.done == 'finalized':
            return await pip.handle_finalized_step(pipeline_id, step_id, steps, app_name, self)

        # Get form data
        form = await request.form()
        user_val = form.get(step.done, "")  # Get value for 'greeting' field

        # Validate input using helper (basic check if required)
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            return error_component

        # --- Custom Processing ---
        # Value was likely generated by get_suggestion, so usually no processing needed here
        processed_val = user_val
        # --- End Custom Processing ---

        # Save the processed value to this step's state
        await pip.set_step_data(pipeline_id, step_id, processed_val, steps)

        # Send confirmation message to UI
        await self.message_queue.add(pip, f"{step.show}: {processed_val}", verbatim=True)

        # Check if this was the last step before finalize (it is in this template)
        if pip.check_finalize_needed(step_index, steps):
            await self.message_queue.add(pip, self.step_messages["finalize"]["ready"], verbatim=True)

        # Return the standard navigation controls
        return pip.create_step_navigation(step_id, step_index, steps, app_name, processed_val)

    # Add step_03, step_03_submit etc. here if you add more steps

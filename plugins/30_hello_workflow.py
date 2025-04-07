import asyncio
from collections import namedtuple
from datetime import datetime

from fasthtml.common import *
from loguru import logger

"""
Pipulate Workflow Template

After copy/pasting this file, edit this docstring first so that your
AI coding assistant knows what you're trying to do.

This file demonstrates the basic pattern for Pipulate Workflows:
1. Define steps with optional transformations
2. Each step collects or processes data
3. Data flows from one step to the next
4. Steps can be reverted and the workflow can be finalized

To create your own Workflow:
1. Copy this file and rename the class, APP_NAME, DISPLAY_NAME, ENDPOINT_MESSAGE
2. Create a [filename].md the training folder (no path needed) and set TRAINING_PROMPT to refer to it
3. Define your own steps
4. Implement custom validation and processing as needed

There are two types of apps in Pipulate:
1. Workflows - Linear, step-based apps. The part you're looking at. WET.
2. Apps - CRUD apps with a single table that inherit from BaseApp. DRY.

CRUD is DRY and Workflows are WET! Get ready to get WET!
"""

# This is the model for a Notebook cell or step (do not change)
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class HelloFlow:  # <-- CHANGE THIS to your new WorkFlow name
    APP_NAME = "hello"  # <-- CHANGE THIS to something no other workflow is using
    DISPLAY_NAME = "Hello World"  # <-- CHANGE THIS to value for User Interface
    ENDPOINT_MESSAGE = (  # <-- Shows when user switches to workflow landing page
        "This simple workflow demonstrates a basic Hello World example. "
        "Enter an ID to start or resume your workflow."
    )
    TRAINING_PROMPT = "hello_workflow.md"  # markdown file from /training or plain text
    PRESERVE_REFILL = True  # <-- Whether to preserve refill values on revert

    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
        """
        Initialize the workflow.
        """
        self.app = app
        self.app_name = app_name
        self.pipulate = pipulate
        self.pipeline = pipeline
        self.steps_indices = {}
        self.db = db
        pip = self.pipulate

        # Customize the steps, it's like one step per cell in the Notebook
        steps = [
            # Define the ordered sequence of steps
            Step(
                id='step_01',      # Please continue using the step_xx format
                done='name',       # Step is done when this field is submitted
                show='Your Name',  # What to show in the UI for done field
                refill=True,       # Whether to refill with last value on revert
                # Step 1 never needs a transform
            ),
            Step(
                id='step_02',
                done='greeting',
                show='Hello Message',
                refill=False,
                transform=lambda x: f"Hello {x}"  # Pipes done value from previous step
            ),
        ]

        # Defines routes for standard workflow method (do not change)
        routes = [
            (f"/{app_name}", self.landing),
            (f"/{app_name}/init", self.init, ["POST"]),
            (f"/{app_name}/jump_to_step", self.jump_to_step, ["POST"]),
            (f"/{app_name}/revert", self.handle_revert, ["POST"]),
            (f"/{app_name}/finalize", self.finalize, ["GET", "POST"]),
            (f"/{app_name}/unfinalize", self.unfinalize, ["POST"]),
        ]

        # Defines routes for each custom step (do not change)
        self.steps = steps
        for step in steps:
            step_id = step.id
            routes.append((f"/{app_name}/{step_id}", getattr(self, step_id)))
            routes.append((f"/{app_name}/{step_id}_submit", getattr(self, f"{step_id}_submit"), ["POST"]))

        # Register the routes (do not change)
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ["GET"]
            app.route(path, methods=method_list)(handler)

        # Define messages for finalize (you can change these)
        self.step_messages = {
            "finalize": {
                "ready": "All steps complete. Ready to finalize workflow.",
                "complete": "Workflow finalized. Use Unfinalize to make changes."
            }
        }

        # Creates a default message for each step (you can change these)
        for step in steps:
            self.step_messages[step.id] = {
                "input": f"{pip.fmt(step.id)}: Please enter {step.show}.",
                "complete": f"{step.show} complete. Continue to next step."
            }

        # Add a finalize step to the workflow (do not change)
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

    async def landing(self):
        """
        This is the landing page for the workflow. It asks for a unique identifier.
        It is necessary for the workflow to function. Only change cosmetic elements.
        """
        pip, pipeline, steps, app_name = self.pipulate, self.pipeline, self.steps, self.app_name
        
        # Get plugin display name for the title
        context = pip.get_plugin_context(self)
        title = f"{self.DISPLAY_NAME or app_name.title()}"
        
        # Generate a default key and get the prefix for the datalist
        full_key, prefix, user_part = pip.generate_pipeline_key(self)
        default_value = full_key
        
        # Get existing keys for the datalist
        pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in pipeline() 
                           if record.pkey.startswith(prefix)]
        
        # Extract the user parts for the datalist
        existing_ids = [record_key.replace(prefix, "") for record_key in matching_records]
        
        return Container(  # Get used to this return signature of FastHTML & HTMX
            Card(
                H2(title),
                # P(f"Key format: Profile-Plugin-Number (e.g., {prefix}01)", style="font-size: 0.9em; color: #666;"),
                Form(
                    pip.wrap_with_inline_button(
                        Input(
                            placeholder="Existing or new 🗝 here (refresh for auto)",
                            name="pipeline_id",
                            list="pipeline-ids",
                            type="search",
                            required=True,
                            autofocus=True,
                            value=default_value,
                            _onfocus="this.setSelectionRange(this.value.length, this.value.length)",
                            cls="contrast"
                        ),
                        button_label=f"Use 🔑",
                        button_class="secondary"
                    ),
                    Datalist(*[Option(value=f"{prefix}{pid}") for pid in existing_ids], id="pipeline-ids"),
                    hx_post=f"/{app_name}/init",
                    hx_target=f"#{app_name}-container"
                )
            ),
            Div(id=f"{app_name}-container")
        )

    async def init(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        user_input = form.get("pipeline_id", "untitled")
        
        # Get the context with plugin name and profile name
        context = pip.get_plugin_context(self)
        plugin_name = context['plugin_name'] or app_name
        profile_name = context['profile_name'] or "default"
        
        # Create the expected prefix parts
        profile_part = profile_name.replace(" ", "_")
        plugin_part = plugin_name.replace(" ", "_")
        expected_prefix = f"{profile_part}-{plugin_part}-"
        
        # Determine pipeline ID based on user input
        if user_input.startswith(expected_prefix):
            # They provided the full composite key
            pipeline_id = user_input
            # Parse it to get the user part
            parsed = pip.parse_pipeline_key(pipeline_id)
            user_provided_id = parsed['user_part']
        else:
            # They provided just their part - generate a full key
            _, prefix, user_provided_id = pip.generate_pipeline_key(self, user_input)
            pipeline_id = f"{prefix}{user_provided_id}"
        
        db["pipeline_id"] = pipeline_id
        logger.debug(f"Using pipeline ID: {pipeline_id}")
        
        # Initialize the pipeline state
        state, error = pip.initialize_if_missing(pipeline_id, {"app_name": app_name})
        if error:
            return error

        # After loading the state, check if all steps are complete
        all_steps_complete = True
        for step in steps[:-1]:  # Exclude finalize step
            if step.id not in state or step.done not in state[step.id]:
                all_steps_complete = False
                break

        # Check if workflow is finalized
        is_finalized = "finalize" in state and "finalized" in state["finalize"]

        # Add information about the workflow ID to conversation history
        id_message = f"Workflow ID: {pipeline_id}"
        await pip.stream(id_message, verbatim=True, spaces_before=0)
        
        # Add the return message
        return_message = f"You can return to this workflow later by selecting '{pipeline_id}' from the dropdown menu."
        await pip.stream(return_message, verbatim=True, spaces_before=0)

        # Add a small delay to ensure messages appear in the correct order
        await asyncio.sleep(0.5)

        # If all steps are complete, show an appropriate message
        if all_steps_complete:
            if is_finalized:
                await pip.stream(f"Workflow is complete and finalized. Use Unfinalize to make changes.", verbatim=True)
            else:
                await pip.stream(f"Workflow is complete but not finalized. Press Finalize to lock your data.", verbatim=True)
        else:
            # If it's a new workflow, add a brief explanation
            if not any(step.id in state for step in self.steps):
                await pip.stream("Please complete each step in sequence. Your progress will be saved automatically.", verbatim=True)

        # Add another delay before loading the first step
        await asyncio.sleep(0.5)

        # Update the datalist by adding this key immediately to the UI
        # This ensures the key is available in the dropdown even after clearing the database
        parsed = pip.parse_pipeline_key(pipeline_id)
        prefix = f"{parsed['profile_part']}-{parsed['plugin_part']}-"
        
        # Get all existing keys for this workflow type
        self.pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in self.pipeline() 
                           if record.pkey.startswith(prefix)]
        
        # Make sure the current key is included, even if it's not in the database yet
        if pipeline_id not in matching_records:
            matching_records.append(pipeline_id)
        
        # Create datalist with all options
        updated_datalist = Datalist(
            *[Option(value=key) for key in matching_records],
            id="pipeline-ids",
            _hx_swap_oob="true"  # Out-of-band swap to update the dropdown
        )
        
        placeholders = self.run_all_cells(steps, app_name)
        return Div(
            # Add updated datalist that includes all existing keys plus the current one
            updated_datalist,
            *placeholders, 
            id=f"{app_name}-container"
        )

    async def step_01(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "")

        if step.done == 'finalized':
            finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
            if "finalized" in finalize_data:
                return Card(
                    H3("Pipeline Finalized"),
                    P("All steps are locked."),
                    Form(
                        Button("Unfinalize", type="submit", style=pip.get_style("warning_button")),
                        hx_post=f"/{app_name}/unfinalize",
                        hx_target=f"#{app_name}-container",
                        hx_swap="outerHTML"
                    )
                )
            else:
                return Div(
                    Card(
                        H3("Finalize Pipeline"),
                        P("You can finalize this pipeline or go back to fix something."),
                        Form(
                            Button("Finalize All Steps", type="submit"),
                            hx_post=f"/{app_name}/finalize",
                            hx_target=f"#{app_name}-container",
                            hx_swap="outerHTML"
                        )
                    ),
                    id=step_id
                )

        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data:
            return Div(
                Card(f"🔒 {step.show}: {user_val}"),
                Div(id=next_step_id, hx_get=f"/{self.app_name}/{next_step_id}", hx_trigger="load")
            )

        if user_val and state.get("_revert_target") != step_id:
            return Div(
                pip.revert_control(step_id=step_id, app_name=app_name, message=f"{step.show}: {user_val}", steps=steps),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
            )
        else:
            display_value = user_val if (step.refill and user_val and self.PRESERVE_REFILL) else await self.get_suggestion(step_id, state)

            await pip.stream(self.step_messages[step_id]["input"], verbatim=True)
            return Div(
                Card(
                    H3(f"{pip.fmt(step.id)}: Enter {step.show}"),
                    Form(
                        pip.wrap_with_inline_button(
                            Input(
                                type="text",
                                name=step.done,
                                value=display_value,
                                placeholder=f"Enter {step.show}",
                                required=True,
                                autofocus=True
                            )
                        ),
                        hx_post=f"/{app_name}/{step.id}_submit",
                        hx_target=f"#{step.id}"
                    )
                ),
                Div(id=next_step_id),
                id=step.id
            )

    async def step_01_submit(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get("pipeline_id", "unknown")
        if step.done == 'finalized':
            state = pip.read_state(pipeline_id)
            state[step_id] = {step.done: True}
            pip.write_state(pipeline_id, state)
            message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
            await pip.stream(message, verbatim=True)
            placeholders = self.run_all_cells(steps, app_name)
            return Div(*placeholders, id=f"{app_name}-container")

        form = await request.form()
        user_val = form.get(step.done, "")

        # VALIDATION: Add step-specific validation here
        is_valid = True
        error_msg = ""
        if not user_val.strip():
            is_valid = False
            error_msg = f"{step.show} cannot be empty"

        if not is_valid:
            return P(error_msg, style=pip.get_style("error"))

        processed_val = user_val  # Perform any processing here

        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        await pip.clear_steps_from(pipeline_id, step_id, steps)

        state = pip.read_state(pipeline_id)
        state[step_id] = {step.done: processed_val}
        if "_revert_target" in state:
            del state["_revert_target"]
        pip.write_state(pipeline_id, state)

        # Send the value confirmation
        await pip.stream(f"{step.show}: {processed_val}", verbatim=True)

        # If this is the last regular step (before finalize), add a prompt to finalize
        if next_step_id == "finalize":
            await asyncio.sleep(0.1)  # Small delay for better readability
            await pip.stream("All steps complete! Please press the Finalize button below to save your data.", verbatim=True)

        return Div(
            pip.revert_control(step_id=step_id, app_name=app_name, message=f"{step.show}: {processed_val}", steps=steps),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
        )

    async def step_02(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_02"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "")

        if step.done == 'finalized':
            finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
            if "finalized" in finalize_data:
                return Card(
                    H3("Pipeline Finalized"),
                    P("All steps are locked."),
                    Form(
                        Button("Unfinalize", type="submit", style=pip.get_style("warning_button")),
                        hx_post=f"/{app_name}/unfinalize",
                        hx_target=f"#{app_name}-container",
                        hx_swap="outerHTML"
                    )
                )
            else:
                return Div(
                    Card(
                        H3("Finalize Pipeline"),
                        P("You can finalize this pipeline or go back to fix something."),
                        Form(
                            Button("Finalize All Steps", type="submit", style=pip.get_style("primary_button")),
                            hx_post=f"/{app_name}/finalize",
                            hx_target=f"#{app_name}-container",
                            hx_swap="outerHTML"
                        )
                    ),
                    id=step_id
                )

        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data:
            return Div(
                Card(f"🔒 {step.show}: {user_val}"),
                Div(id=next_step_id, hx_get=f"/{self.app_name}/{next_step_id}", hx_trigger="load")
            )

        if user_val and state.get("_revert_target") != step_id:
            return Div(
                pip.revert_control(step_id=step_id, app_name=app_name, message=f"{step.show}: {user_val}", steps=steps),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
            )
        else:
            display_value = user_val if (step.refill and user_val and self.PRESERVE_REFILL) else await self.get_suggestion(step_id, state)

            await pip.stream(self.step_messages[step_id]["input"], verbatim=True)
            return Div(
                Card(
                    H3(f"{pip.fmt(step.id)}: Enter {step.show}"),
                    Form(
                        pip.wrap_with_inline_button(
                            Input(
                                type="text",
                                name=step.done,
                                value=display_value,
                                placeholder=f"Enter {step.show}",
                                required=True,
                                autofocus=True
                            )
                        ),
                        hx_post=f"/{app_name}/{step.id}_submit",
                        hx_target=f"#{step.id}"
                    )
                ),
                Div(id=next_step_id),
                id=step.id
            )

    async def step_02_submit(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_02"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get("pipeline_id", "unknown")
        if step.done == 'finalized':
            state = pip.read_state(pipeline_id)
            state[step_id] = {step.done: True}
            pip.write_state(pipeline_id, state)
            message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
            await pip.stream(message, verbatim=True)
            cells = self.run_all_cells(steps, app_name)
            return Div(*cells, id=f"{app_name}-container")

        form = await request.form()
        user_val = form.get(step.done, "")

        # VALIDATION: Add step-specific validation here
        is_valid = True
        error_msg = ""
        if not user_val.strip():
            is_valid = False
            error_msg = f"{step.show} cannot be empty"

        if not is_valid:
            return P(error_msg, style=pip.get_style("error"))

        processed_val = user_val  # Perform any processing here

        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        await pip.clear_steps_from(pipeline_id, step_id, steps)

        state = pip.read_state(pipeline_id)
        state[step_id] = {step.done: processed_val}
        if "_revert_target" in state:
            del state["_revert_target"]
        pip.write_state(pipeline_id, state)

        # Send the value confirmation
        await pip.stream(f"{step.show}: {processed_val}", verbatim=True)

        # If this is the last regular step (before finalize), add a prompt to finalize
        if next_step_id == "finalize":
            await asyncio.sleep(0.1)  # Small delay for better readability
            await pip.stream("All steps complete! Please press the Finalize button below to save your data.", verbatim=True)

        return Div(
            pip.revert_control(step_id=step_id, app_name=app_name, message=f"{step.show}: {processed_val}", steps=steps),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
        )

    # --- Finalization & Unfinalization ---
    async def finalize(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        finalize_step = steps[-1]
        finalize_data = pip.get_step_data(pipeline_id, finalize_step.id, {})
        logger.debug(f"Pipeline ID: {pipeline_id}")
        logger.debug(f"Finalize step: {finalize_step}")
        logger.debug(f"Finalize data: {finalize_data}")

        if request.method == "GET":
            if finalize_step.done in finalize_data:
                logger.debug("Pipeline is already finalized")
                return Card(
                    H3("All Cards Complete"),
                    P("Pipeline is finalized. Use Unfinalize to make changes."),
                    Form(
                        Button("Unfinalize", type="submit", style=pip.get_style("warning_button")),
                        hx_post=f"/{app_name}/unfinalize",
                        hx_target=f"#{app_name}-container",
                        hx_swap="outerHTML"
                    ),
                    id=finalize_step.id
                )

            # Check if all previous steps are complete
            non_finalize_steps = steps[:-1]
            all_steps_complete = all(
                pip.get_step_data(pipeline_id, step.id, {}).get(step.done)
                for step in non_finalize_steps
            )
            logger.debug(f"All steps complete: {all_steps_complete}")

            if all_steps_complete:
                return Card(
                    H3("Ready to finalize?"),
                    P("All data is saved. Lock it in?"),
                    Form(
                        Button("Finalize", type="submit", style=pip.get_style("primary_button")),
                        hx_post=f"/{app_name}/finalize",
                        hx_target=f"#{app_name}-container",
                        hx_swap="outerHTML"
                    ),
                    id=finalize_step.id
                )
            else:
                return Div(P("Nothing to finalize yet."), id=finalize_step.id)
        else:
            # This is the POST request when they press the Finalize button
            state = pip.read_state(pipeline_id)
            state["finalize"] = {"finalized": True}
            state["updated"] = datetime.now().isoformat()
            pip.write_state(pipeline_id, state)

            # Send a confirmation message
            await pip.stream("Workflow successfully finalized! Your data has been saved and locked.", verbatim=True)

            # Return the updated UI
            return Div(*self.run_all_cells(steps, app_name), id=f"{app_name}-container")

    async def unfinalize(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        if "finalize" in state:
            del state["finalize"]
        pip.write_state(pipeline_id, state)

        # Send a message informing them they can revert to any step
        await pip.stream("Workflow unfinalized! You can now revert to any step and make changes.", verbatim=True)

        cells = self.run_all_cells(steps, app_name)
        return Div(*cells, id=f"{app_name}-container")

    def run_all_cells(self, steps, app_name):
        """
        Starts HTMX chain reaction of all steps up to current.
        Equivalent to Running all Cells in a Jupyter Notebook.
        """
        cells = []
        for i, step in enumerate(steps):
            trigger = ("load" if i == 0 else f"stepComplete-{steps[i - 1].id} from:{steps[i - 1].id}")
            cells.append(
                Div(
                    id=step.id,
                    hx_get=f"/{app_name}/{step.id}",
                    hx_trigger=trigger,
                    hx_swap="outerHTML"
                )
            )
        return cells

    async def jump_to_step(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        db["step_id"] = step_id
        return pip.rebuild(app_name, steps)

    async def get_suggestion(self, step_id, state):
        pip, db, steps = self.pipulate, self.db, self.steps
        # If a transform function exists, use the previous step's output.
        step = next((s for s in steps if s.id == step_id), None)
        if not step or not step.transform:
            return ""
        prev_index = self.steps_indices[step_id] - 1
        if prev_index < 0:
            return ""
        prev_step_id = steps[prev_index].id
        prev_step = steps[prev_index]
        prev_data = pip.get_step_data(db["pipeline_id"], prev_step_id, {})
        prev_word = prev_data.get(prev_step.done, "")
        return step.transform(prev_word) if prev_word else ""

    async def handle_revert(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        pipeline_id = db.get("pipeline_id", "unknown")
        if not step_id:
            return P("Error: No step specified", style=pip.get_style("error"))
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        state = pip.read_state(pipeline_id)
        state["_revert_target"] = step_id
        pip.write_state(pipeline_id, state)
        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await pip.stream(message, verbatim=True)
        cells = self.run_all_cells(steps, app_name)
        return Div(*cells, id=f"{app_name}-container")

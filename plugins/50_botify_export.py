import asyncio
from collections import namedtuple
from datetime import datetime
from urllib.parse import urlparse
import httpx
from pathlib import Path

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


def parse_botify_url(url: str) -> dict:
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    if len(path_parts) < 2:
        raise ValueError("Invalid Botify URL format")
    org = path_parts[0]
    project = path_parts[1]
    base_url = f"https://{parsed.netloc}/{org}/{project}/"
    return {"url": base_url, "org": org, "project": project}


class BotifyExport:
    APP_NAME = "botfify_csv"
    DISPLAY_NAME = "Botify CSV Export"
    ENDPOINT_MESSAGE = (
        "This workflow helps you export data from Botify projects. "
        "Press Enter to start a new workflow or enter an existing key to resume. "
    )
    TRAINING_PROMPT = "botify_export.md"
    PRESERVE_REFILL = True

    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
        """
        Initialize the workflow.
        
        This method sets up the workflow by:
        1. Storing references to app, pipulate, pipeline, and database
        2. Defining the ordered sequence of workflow steps
        3. Registering routes for standard workflow methods
        4. Registering custom routes for each step
        5. Creating step messages for UI feedback
        6. Adding a finalize step to complete the workflow
        
        Args:
            app: The FastAPI application instance
            pipulate: The Pipulate helper instance
            pipeline: The pipeline database handler
            db: The request-scoped database dictionary
            app_name: Optional override for the workflow app name
        """
        self.app = app
        self.app_name = app_name
        self.pipulate = pipulate
        self.pipeline = pipeline
        self.steps_indices = {}
        self.db = db
        pip = self.pipulate
        # Create message queue for ordered streaming
        self.message_queue = pip.message_queue

        # Customize the steps, it's like one step per cell in the Notebook

        steps = [
            Step(id='step_01', done='url', show='Botify Project URL', refill=True),
            Step(id='step_02', done='analysis', show='Analysis Selection', refill=False),
            Step(id='step_03', done='depth', show='Maximum Click Depth', refill=False),
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
                "complete": f"Workflow finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes."
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
        Generate the landing page for the workflow.
        
        This method creates the initial UI that users see when they access the
        workflow. It provides a form for entering or selecting a unique identifier
        (pipeline ID) to start or resume a workflow. Key features:
        
        - Displays the workflow title and description
        - Generates a default pipeline ID for new workflows
        - Provides a datalist of existing workflow IDs
        - Creates an HTMX-enabled form for workflow initialization
        
        Returns:
            FastHTML container with the landing page UI components
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
        
        # Create full key options for the datalist
        datalist_options = [f"{prefix}{record_key.replace(prefix, '')}" for record_key in matching_records]
        
        return Container(  # Get used to this return signature of FastHTML & HTMX
            Card(
                H2(title),
                # P(f"Key format: Profile-Plugin-Number (e.g., {prefix}01)", style="font-size: 0.9em; color: #666;"),
                P("Enter a key to start a new workflow or resume an existing one.", style="font-size: 0.9em; color: #666;"),
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
                        button_label=f"Enter 🔑",
                        button_class="secondary"
                    ),
                    # Use the helper method to create the initial datalist
                    pip.update_datalist("pipeline-ids", options=datalist_options if datalist_options else None),
                    hx_post=f"/{app_name}/init",
                    hx_target=f"#{app_name}-container"
                )
            ),
            Div(id=f"{app_name}-container")
        )

    async def init(self, request):
        """
        Initialize the workflow and create the UI for all steps.
        
        This method handles the form submission from the landing page, setting up
        the workflow pipeline. It performs several key operations:
        
        1. Generates or validates the pipeline ID
        2. Initializes the workflow state
        3. Provides user feedback about workflow status
        4. Updates the datalist for returning to this workflow
        5. Generates the HTMX-enabled placeholders for all steps
        
        The initialization process accommodates both new workflows and resuming
        existing ones, with appropriate feedback for each situation.
        
        Args:
            request: The HTTP request object containing the pipeline_id form field
            
        Returns:
            FastHTML container with all workflow step placeholders
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        user_input = form.get("pipeline_id", "untitled")
        
        # Get the context with plugin name and profile name
        context = pip.get_plugin_context(self)
        plugin_name = context['plugin_name'] or app_name
        profile_name = context['profile_name'] or "default"
        
        # ───────── PIPELINE ID GENERATION AND PARSING ─────────
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
        
        # ───────── STATE INITIALIZATION AND WORKFLOW MESSAGES ─────────
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

        # Add all messages to the ordered queue in sequence - they'll be delivered in order
        # Add information about the workflow ID to conversation history
        id_message = f"Workflow ID: {pipeline_id}"
        await self.message_queue.add(pip, id_message, verbatim=True, spaces_before=0)
        
        # Add the return message
        return_message = f"You can return to this workflow later by selecting '{pipeline_id}' from the dropdown menu."
        await self.message_queue.add(pip, return_message, verbatim=True, spaces_before=0)

        # Workflow status messages
        if all_steps_complete:
            if is_finalized:
                await self.message_queue.add(pip, f"Workflow is complete and finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes.", verbatim=True)
            else:
                await self.message_queue.add(pip, f"Workflow is complete but not finalized. Press Finalize to lock your data.", verbatim=True)
        else:
            # If it's a new workflow, add a brief explanation
            if not any(step.id in state for step in self.steps):
                await self.message_queue.add(pip, "Please complete each step in sequence. Your progress will be saved automatically.", verbatim=True)

        # ───────── UI GENERATION AND DATALIST UPDATES ─────────
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
        
        # Use the Pipulate helper method to create the updated datalist
        updated_datalist = pip.update_datalist("pipeline-ids", options=matching_records)
        
        # Get placeholders for all steps
        placeholders = pip.run_all_cells(app_name, steps)
        return Div(
            # Add updated datalist that includes all existing keys plus the current one
            updated_datalist,
            *placeholders, 
            id=f"{app_name}-container"
        )

    async def step_01(self, request):
        """
        Handle GET requests for the first step of the workflow.
        
        This method generates the appropriate UI for step_01 based on its state:
        - If workflow is finalized: Display locked content
        - If step is completed: Show step data with revert option
        - If step needs input: Show input form with suggestion if available
        
        The UI components use HTMX for interactive updates without page refresh.
        
        Args:
            request: The HTTP request object
            
        Returns:
            FastHTML components representing the step UI
        """
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
                        Button(pip.UNLOCK_BUTTON_LABEL, type="submit", cls="secondary outline"),
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
                            Button("Finalize All Steps", type="submit", cls="primary"),
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

            await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
            return Div(
                Card(
                    H4(f"{pip.fmt(step.id)}: Enter {step.show}"),
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
        """
        Handle POST submissions for the first step of the workflow.
        
        This method processes and canonicalizes Botify URLs before storing them.
        It automatically converts any valid Botify project URL into its canonical form
        and stores both the canonical URL and the parsed components (org, project).
        
        Args:
            request: The HTTP request object containing form data
            
        Returns:
            FastHTML components for navigation or error message
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Handle finalized state using helper
        if step.done == 'finalized':
            return await pip.handle_finalized_step(pipeline_id, step_id, steps, app_name, self)

        # Get form data
        form = await request.form()
        user_val = form.get(step.done, "").strip()
        
        # Basic input validation
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            return error_component

        # Parse and canonicalize the Botify URL
        try:
            parsed_data = parse_botify_url(user_val)
            
            # Store the parsed data including the canonical URL
            state = pip.read_state(pipeline_id)
            if step_id not in state:
                state[step_id] = {}
            
            # Store all components
            state[step_id].update(parsed_data)
            
            # Ensure the 'done' field matches the Step namedtuple
            state[step_id][step.done] = parsed_data['url']
            
            # Write the complete state back
            pip.write_state(pipeline_id, state)
            
            # Send confirmation message showing the canonical form
            await self.message_queue.add(
                pip,
                f"Successfully parsed Botify URL:\n"
                f"Organization: {parsed_data['org']}\n"
                f"Project: {parsed_data['project']}\n"
                f"Canonical URL: {parsed_data['url']}",
                verbatim=True
            )
            
            # Return navigation controls with the canonical URL
            return pip.create_step_navigation(step_id, step_index, steps, app_name, parsed_data['url'])
            
        except ValueError:
            return P(
                "Invalid Botify URL. Please provide a URL containing organization and project (e.g., https://app.botify.com/org/project/...)",
                style=pip.get_style("error")
            )

    async def step_02(self, request):
        """
        Display form for analysis slug selection using a dropdown menu.
        Pre-selects the most recent analysis if no previous selection exists,
        otherwise maintains the user's previous selection.
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_02"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "")  # Previously selected analysis, if any

        # Handle finalized state
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data:
            return Div(
                Card(f"🔒 {step.show}: {user_val}"),
                Div(id=next_step_id, hx_get=f"/{self.app_name}/{next_step_id}", hx_trigger="load")
            )

        # If step is complete and not being reverted, show revert control
        if user_val and state.get("_revert_target") != step_id:
            return Div(
                pip.revert_control(step_id=step_id, app_name=app_name, message=f"{step.show}: {user_val}", steps=steps),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
            )

        # Get data from step_01
        step_01_data = pip.get_step_data(pipeline_id, "step_01", {})
        org = step_01_data.get('org')
        project = step_01_data.get('project')

        try:
            # Read API token and fetch analyses
            api_token = self.read_api_token()
            slugs = await self.fetch_analyses(org, project, api_token)
            
            if not slugs:
                return P("No analyses found for this project", style=pip.get_style("error"))
            
            # Determine selected value:
            # - Use previous selection if it exists and we're reverting
            # - Otherwise use the most recent analysis (first in list)
            selected_value = user_val if user_val else slugs[0]
            
            # Show the form with dropdown
            await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
            
            return Div(
                Card(
                    H4(f"{pip.fmt(step_id)}: Select {step.show}"),
                    Form(
                        pip.wrap_with_inline_button(
                            Select(
                                name=step.done,
                                required=True,
                                autofocus=True,
                                *[
                                    Option(
                                        slug,
                                        value=slug,
                                        selected=(slug == selected_value)
                                    ) for slug in slugs
                                ]
                            )
                        ),
                        hx_post=f"/{app_name}/{step.id}_submit",
                        hx_target=f"#{step.id}"
                    )
                ),
                Div(id=next_step_id),
                id=step.id
            )

        except Exception as e:
            return P(f"Error fetching analyses: {str(e)}", style=pip.get_style("error"))

    async def step_02_submit(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_02"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Handle finalized state using helper
        if step.done == 'finalized':
            return await pip.handle_finalized_step(pipeline_id, step_id, steps, app_name, self)

        # Get form data
        form = await request.form()
        user_val = form.get(step.done, "")
        
        # Validate input using helper
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            return error_component

        # ===== START POST-PROCESSING SECTION =====
        # For now, just use the user input directly
        processed_val = user_val
        # ===== END POST-PROCESSING SECTION =====

        # Update state using helper
        await pip.update_step_state(pipeline_id, step_id, processed_val, steps)

        # Send confirmation message - use the queue for ordered delivery
        await self.message_queue.add(pip, f"{step.show}: {processed_val}", verbatim=True)
        
        # Check if we need finalize prompt
        if pip.check_finalize_needed(step_index, steps):
            await self.message_queue.add(pip, "All steps complete! Please press the Finalize button below to save your data.", verbatim=True)
        
        # Return navigation controls
        return pip.create_step_navigation(step_id, step_index, steps, app_name, processed_val)

    # --- Finalization & Unfinalization ---
    async def finalize(self, request):
        """
        Finalize the workflow, locking all steps from further changes.
        
        This method handles both GET requests (displaying finalization UI) and 
        POST requests (performing the actual finalization). The UI portions
        are intentionally kept WET to allow for full customization of the user
        experience, while core state management is handled by DRY helper methods.
        
        Customization Points:
        - GET response: The cards/UI shown before finalization
        - Confirmation message: What the user sees after finalizing
        - Any additional UI elements or messages
        
        Args:
            request: The HTTP request object
            
        Returns:
            UI components for either the finalization prompt or confirmation
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        finalize_step = steps[-1]
        finalize_data = pip.get_step_data(pipeline_id, finalize_step.id, {})
        logger.debug(f"Pipeline ID: {pipeline_id}")
        logger.debug(f"Finalize step: {finalize_step}")
        logger.debug(f"Finalize data: {finalize_data}")

        # ───────── GET REQUEST: FINALIZATION UI (INTENTIONALLY WET) ─────────
        if request.method == "GET":
            if finalize_step.done in finalize_data:
                logger.debug("Pipeline is already finalized")
                return Card(
                    H4("Workflow is locked."),
                    # P(f"Pipeline is finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes."),
                    Form(
                        Button(pip.UNLOCK_BUTTON_LABEL, type="submit", cls="secondary outline"),
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
                    H4("All steps complete. Finalize?"),
                    P("You can revert to any step and make changes.", style="font-size: 0.9em; color: #666;"),
                    # P("All data is saved. Lock it in?"),
                    Form(
                        Button("Finalize", type="submit", cls="primary"),
                        hx_post=f"/{app_name}/finalize",
                        hx_target=f"#{app_name}-container",
                        hx_swap="outerHTML"
                    ),
                    id=finalize_step.id
                )
            else:
                return Div(P("Nothing to finalize yet."), id=finalize_step.id)
        # ───────── END GET REQUEST ─────────
        else:
            # ───────── POST REQUEST: PERFORM FINALIZATION ─────────
            # Update state using DRY helper
            await pip.finalize_workflow(pipeline_id)
            
            # ───────── CUSTOM FINALIZATION UI (INTENTIONALLY WET) ─────────
            # Send a confirmation message 
            await self.message_queue.add(pip, "Workflow successfully finalized! Your data has been saved and locked.", verbatim=True)
            
            # Return the updated UI
            return pip.rebuild(app_name, steps)
            # ───────── END CUSTOM FINALIZATION UI ─────────

    async def unfinalize(self, request):
        """
        Unfinalize the workflow, allowing steps to be modified again.
        
        This method removes the finalization flag from the workflow state
        and displays a confirmation message to the user. The core state
        management is handled by a DRY helper method, while the UI generation
        is intentionally kept WET for customization.
        
        Customization Points:
        - Confirmation message: What the user sees after unfinalizing
        - Any additional UI elements or actions
        
        Args:
            request: The HTTP request object
            
        Returns:
            UI components showing the workflow is unlocked
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Update state using DRY helper
        await pip.unfinalize_workflow(pipeline_id)
        
        # ───────── CUSTOM UNFINALIZATION UI (INTENTIONALLY WET) ─────────
        # Send a message informing them they can revert to any step
        await self.message_queue.add(pip, "Workflow unfinalized! You can now revert to any step and make changes.", verbatim=True)
        
        # Return the rebuilt UI
        return pip.rebuild(app_name, steps)
        # ───────── END CUSTOM UNFINALIZATION UI ─────────

    def run_all_cells(self, steps, app_name):
        """Generate placeholders for all steps through Pipulate helper."""
        return self.pipulate.run_all_cells(app_name, steps)

    async def jump_to_step(self, request):
        """
        Jump to a specific step in the workflow.
        
        This method updates the step_id in the database and rebuilds the UI
        to show the workflow from the selected step.
        
        Args:
            request: The HTTP request object containing the step_id
            
        Returns:
            FastHTML components showing the workflow from the selected step
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        db["step_id"] = step_id
        return pip.rebuild(app_name, steps)

    async def get_suggestion(self, step_id, state):
        """
        Get a suggestion value for a step based on transform function.
        
        If the step has a transform function, use the previous step's output
        to generate a suggested value. This enables data to flow naturally
        from one step to the next, creating a connected workflow experience.
        
        Args:
            step_id: The ID of the step to generate a suggestion for
            state: The current workflow state
            
        Returns:
            str: The suggested value or empty string if not applicable
        """
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
        """
        Handle reverting to a previous step in the workflow.
        
        This method clears state data from the specified step forward,
        marks the step as the revert target in the state, and rebuilds
        the workflow UI. It allows users to go back and modify their
        inputs at any point in the workflow process.
        
        Args:
            request: The HTTP request object containing the step_id
            
        Returns:
            FastHTML components representing the rebuilt workflow UI
        """
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
        await self.message_queue.add(pip, message, verbatim=True)
        return pip.rebuild(app_name, steps)

    def read_api_token(self):
        """Read Botify API token from local file."""
        try:
            token_file = Path("botify_token.txt")
            if not token_file.exists():
                raise FileNotFoundError("botify_token.txt not found")
            
            token = token_file.read_text().splitlines()[0].strip()
            return token
        except Exception as e:
            raise ValueError(f"Error reading API token: {e}")

    async def fetch_analyses(self, org, project, api_token):
        """Fetch analysis slugs for a given project from Botify API."""
        url = f"https://api.botify.com/v1/analyses/{org}/{project}/light"
        headers = {"Authorization": f"Token {api_token}"}
        slugs = []
        
        async with httpx.AsyncClient() as client:
            try:
                while url:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    slugs.extend(a['slug'] for a in data.get('results', []))
                    url = data.get('next')
                return slugs
            except httpx.RequestError as e:
                raise ValueError(f"Error fetching analyses: {e}")

    async def get_urls_by_depth(self, org, project, analysis, api_key):
        """
        Fetches URL counts aggregated by depth from the Botify API.
        Returns a dictionary {depth: count} or an empty {} on error.
        """
        api_url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
        headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
        payload = {
            "collections": [f"crawl.{analysis}"],
            "query": {
                "dimensions": [f"crawl.{analysis}.depth"],
                "metrics": [{"field": f"crawl.{analysis}.count_urls_crawl"}],
                "sort": [{"field": f"crawl.{analysis}.depth", "order": "asc"}]
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(api_url, headers=headers, json=payload, timeout=120.0)
                response.raise_for_status()
                
                results = response.json().get("results", [])
                depth_distribution = {}
                
                for row in results:
                    if "dimensions" in row and len(row["dimensions"]) == 1 and \
                       "metrics" in row and len(row["metrics"]) == 1:
                        depth = row["dimensions"][0]
                        count = row["metrics"][0]
                        if isinstance(depth, int):
                            depth_distribution[depth] = count
                
                return depth_distribution
                
        except Exception as e:
            logger.error(f"Error fetching URL depths: {str(e)}")
            return {}

    async def calculate_max_safe_depth(self, org, project, analysis, api_key):
        """Calculate maximum depth that keeps cumulative URLs under 1M"""
        depth_distribution = await self.get_urls_by_depth(org, project, analysis, api_key)
        if not depth_distribution:
            return None
        
        cumulative_sum = 0
        for depth in sorted(depth_distribution.keys()):
            cumulative_sum += depth_distribution[depth]
            if cumulative_sum >= 1_000_000:
                return depth - 1  # Return last safe depth
        return max(depth_distribution.keys())  # All depths are safe

    async def step_03(self, request):
        """
        Display the maximum safe click depth based on cumulative URL counts.
        Shows both the calculated depth and the cumulative URL count at that depth.
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_03"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "")

        # Handle finalized state
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data:
            return Div(
                Card(f"🔒 {step.show}: {user_val}"),
                Div(id=next_step_id, hx_get=f"/{self.app_name}/{next_step_id}", hx_trigger="load")
            )

        # If step is complete and not being reverted, show revert control
        if user_val and state.get("_revert_target") != step_id:
            return Div(
                pip.revert_control(step_id=step_id, app_name=app_name, message=f"{step.show}: {user_val}", steps=steps),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
            )

        # Get data from previous steps
        step_01_data = pip.get_step_data(pipeline_id, "step_01", {})
        step_02_data = pip.get_step_data(pipeline_id, "step_02", {})
        org = step_01_data.get('org')
        project = step_01_data.get('project')
        analysis = step_02_data.get('analysis')

        try:
            api_token = self.read_api_token()
            max_depth = await self.calculate_max_safe_depth(org, project, analysis, api_token)
            
            if max_depth is None:
                return P("Could not calculate maximum depth. Please check your API access and try again.", 
                        style=pip.get_style("error"))

            # Show the form with the calculated depth
            await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
            
            return Div(
                Card(
                    H4(f"{pip.fmt(step_id)}: {step.show}"),
                    P(f"Based on URL counts, the maximum safe depth is: {max_depth}", 
                      style="margin-bottom: 1rem;"),
                    P("This depth ensures the export will contain fewer than 1 million URLs.", 
                      style="font-size: 0.9em; color: #666;"),
                    Form(
                        pip.wrap_with_inline_button(
                            Input(
                                type="hidden",
                                name=step.done,
                                value=str(max_depth)
                            )
                        ),
                        hx_post=f"/{app_name}/{step.id}_submit",
                        hx_target=f"#{step.id}"
                    )
                ),
                Div(id=next_step_id),
                id=step.id
            )
            
        except Exception as e:
            return P(f"Error calculating maximum depth: {str(e)}", style=pip.get_style("error"))

    async def step_03_submit(self, request):
        """Handle the submission of the maximum click depth step."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_03"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Handle finalized state using helper
        if step.done == 'finalized':
            return await pip.handle_finalized_step(pipeline_id, step_id, steps, app_name, self)

        # Get form data
        form = await request.form()
        user_val = form.get(step.done, "")
        
        # Validate input using helper
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            return error_component

        # Update state using helper
        await pip.update_step_state(pipeline_id, step_id, user_val, steps)

        # Send confirmation message
        await self.message_queue.add(pip, f"{step.show}: {user_val}", verbatim=True)
        
        # Check if we need finalize prompt
        if pip.check_finalize_needed(step_index, steps):
            await self.message_queue.add(pip, "All steps complete! Please press the Finalize button below to save your data.", verbatim=True)
        
        # Return navigation controls
        return pip.create_step_navigation(step_id, step_index, steps, app_name, user_val)

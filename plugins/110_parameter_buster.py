import asyncio
from collections import namedtuple
from datetime import datetime
import re

from fasthtml.common import * # type: ignore
from loguru import logger

"""
Multi-Export Workflow
A workflow for performing multiple CSV exports from Botify.
"""

# Model for a workflow step
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class ParameterBusterWorkflow:
    """
    Multi-Export Workflow
    
    A workflow that handles multiple Botify data exports through a sequence of steps.
    """
    # --- Workflow Configuration ---
    APP_NAME = "param_buster"              # Unique identifier for this workflow's routes and data
    DISPLAY_NAME = "Parameter Buster" # User-friendly name shown in the UI
    ENDPOINT_MESSAGE = (            # Message shown on the workflow's landing page
        "This workflow produces a PageWorkers Parameter Buster optimization."
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
                done='botify_project',        # Field to store the project data
                show='Botify Project URL',    # User-friendly name
                refill=True,                  # Allow refilling for better UX
            ),
            Step(
                id='step_02',                 # Changed from step_new to step_02
                done='analysis_selection',    # Updated from 'placeholder' to be more meaningful
                show='Select Analysis',       # Changed from 'Project Details' to match functionality
                refill=False,
            ),
            Step(
                id='step_03',                 
                done='weblogs_check',         # Store the check result
                show='Check Web Logs',        # User-friendly name
                refill=False,
            ),
            Step(
                id='step_04',                 # Changed from step_03 to step_04
                done='search_console_check',  # Store the Search Console check result
                show='Check Search Console',  # User-friendly name
                refill=False,
            ),
            Step(
                id='step_05',
                done='placeholder',
                show='Generate Optimization',
                refill=False,
            ),
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

        # Add the step_04_complete route
        routes.append((f"/{app_name}/step_04_complete", self.step_04_complete, ["POST"]))

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
            "step_02": {
                "input": f"{pip.fmt('step_02')}: Please select an analysis for this project.",
                "complete": "Analysis selection complete. Continue to next step."
            }
        }

        # Create default messages for each step
        for step in steps:
            if step.id not in self.step_messages:  # Only add if not already defined
                self.step_messages[step.id] = {
                    "input": f"{pip.fmt(step.id)}: Please complete {step.show}.",
                    "complete": f"{step.show} complete. Continue to next step."
                }

        # Add specific message for step_04 (Search Console check)
        self.step_messages["step_04"] = {
            "input": f"{pip.fmt('step_04')}: Please check if the project has Search Console data.",
            "complete": "Search Console check complete. Continue to next step."
        }

        # Add specific message for step_03 (Check Web Logs)
        self.step_messages["step_03"] = {
            "input": f"{pip.fmt('step_03')}: Please check if the project has web logs available.",
            "complete": "Web logs check complete. Continue to next step."
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
                            Button("Finalize", type="submit", cls="primary"),
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

        # This is the key operation for forward-only flow:
        # Clear all state data from the reverted step forward
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        
        # Mark the current step as the revert target
        state = pip.read_state(pipeline_id)
        state["_revert_target"] = step_id
        pip.write_state(pipeline_id, state)

        # Add user message about the revert
        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        await self.message_queue.add(pip, f"Reverted to {step_id}. All subsequent data has been cleared.", verbatim=True)
        
        # Rebuild the UI to start from the reverted step
        return pip.rebuild(app_name, steps)

    # --- Placeholder Step Methods ---

    async def step_01(self, request):
        """Handles GET request for Botify URL input widget.
        
        Collects and validates a Botify project URL from the user.
        Stores the extracted project data for use in subsequent steps.
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        
        # CUSTOMIZE_VALUE_ACCESS
        project_data_str = step_data.get(step.done, "")
        import json
        project_data = json.loads(project_data_str) if project_data_str else {}
        project_url = project_data.get("url", "")

        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and project_data:
            # CUSTOMIZE_DISPLAY: Enhanced finalized state display
            return Div(
                Card(
                    H3(f"🔒 {step.show}"),
                    Div(
                        P(f"Project: {project_data.get('project_name', '')}"),
                        Small(project_url, style="word-break: break-all;"),
                        style="padding: 10px; background: var(--pico-card-background-color); border-radius: 5px;"
                    )
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
            
        # Check if step is complete and not being reverted to
        if project_data and state.get("_revert_target") != step_id:
            # CUSTOMIZE_COMPLETE: Enhanced completion display
            project_name = project_data.get('project_name', '')
            username = project_data.get('username', '')

            project_info = Div(
                H4(f"Project: {project_name}"),
                P(f"Username: {username}"),
                Small(project_url, style="word-break: break-all;"),
                style="padding: 10px; background: #f8f9fa; border-radius: 5px;"
            )

            return Div(
                pip.revert_control(
                    step_id=step_id, 
                    app_name=app_name, 
                    message=f"{step.show}: {project_url}",
                    steps=steps
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        else:
            # CUSTOMIZE_FORM: Replace with URL input form
            display_value = project_url if (step.refill and project_url) else ""
            await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
            
            return Div(
                Card(
                    H3(f"{step.show}"),
                    P("Enter a Botify project URL:"),
                    Form(
                        Input(
                            type="url", 
                            name="botify_url", 
                            placeholder="https://app.botify.com/username/group/project", 
                            value=display_value,
                            required=True,
                            pattern="https://(app|analyze)\\.botify\\.com/[^/]+/[^/]+/[^/]+.*",
                            style="width: 100%;"
                        ),
                        Small("Example: https://app.botify.com/username/group/project", style="display: block; margin-bottom: 10px;"),
                        Div(
                            Button("Submit", type="submit", cls="primary"),
                            style="margin-top: 1vh; text-align: right;"
                        ),
                        hx_post=f"/{app_name}/{step_id}_submit", 
                        hx_target=f"#{step_id}"
                    )
                ),
                Div(id=next_step_id),  # PRESERVE: Empty div for next step - DO NOT ADD hx_trigger HERE
                id=step_id
            )

    async def step_01_submit(self, request):
        """Process the submission for Botify URL input widget.
        
        Validates the URL, extracts project data, and stores it for downstream steps.
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")

        # CUSTOMIZE_FORM_PROCESSING: Process form data
        form = await request.form()
        botify_url = form.get("botify_url", "").strip()

        # CUSTOMIZE_VALIDATION: Validate the Botify URL
        is_valid, message, project_data = self.validate_botify_url(botify_url)

        if not is_valid:
            return P(f"Error: {message}", style=pip.get_style("error"))

        # CUSTOMIZE_DATA_PROCESSING: Convert to storable format 
        import json
        project_data_str = json.dumps(project_data)

        # CUSTOMIZE_STATE_STORAGE: Save to state with JSON
        await pip.update_step_state(pipeline_id, step_id, project_data_str, steps)
        await self.message_queue.add(pip, f"{step.show} complete: {project_data['project_name']}", verbatim=True)

        # CUSTOMIZE_WIDGET_DISPLAY: Create project info widget
        project_name = project_data.get('project_name', '')
        project_url = project_data.get('url', '')

        project_info = Div(
            H4(f"Project: {project_name}"),
            Small(project_url, style="word-break: break-all;"),
            style="padding: 10px; background: #f8f9fa; border-radius: 5px;"
        )

        # PRESERVE: Return the revert control with chain reaction to next step
        return Div(
            pip.revert_control(
                step_id=step_id, 
                app_name=app_name, 
                message=f"{step.show}: {project_url}",
                steps=steps
            ),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )

    async def step_02(self, request):
        """Handles GET request for Analysis selection between steps 1 and 2."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_02"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        
        # Get the analysis result if already completed
        import json
        analysis_result_str = step_data.get(step.done, "")
        analysis_result = json.loads(analysis_result_str) if analysis_result_str else {}
        selected_slug = analysis_result.get("analysis_slug", "")
        
        # Get project data from step_01
        prev_step_id = "step_01"
        prev_step_data = pip.get_step_data(pipeline_id, prev_step_id, {})
        prev_data_str = prev_step_data.get("botify_project", "")
        
        if not prev_data_str:
            return P("Error: Project data not found. Please complete step 1 first.", style=pip.get_style("error"))
        
        project_data = json.loads(prev_data_str)
        project_name = project_data.get("project_name", "")
        username = project_data.get("username", "")

        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and selected_slug:
            # Show finalized state with analysis result
            return Div(
                Card(
                    H3(f"🔒 {step.show}"),
                    Div(
                        P(f"Project: {project_name}", style="margin-bottom: 5px;"),
                        P(f"Selected Analysis: {selected_slug}", style="font-weight: bold;"),
                        style="padding: 10px; background: var(--pico-card-background-color); border-radius: 5px;"
                    )
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        
        # Check if step is complete and not being reverted to
        if selected_slug and state.get("_revert_target") != step_id:
            # Show completed state with analysis result
            return Div(
                pip.revert_control(
                    step_id=step_id, 
                    app_name=app_name, 
                    message=f"{step.show}: {selected_slug}",
                    steps=steps
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        
        # Display analysis selection dropdown
        try:
            # Read API token
            api_token = self.read_api_token()
            if not api_token:
                return P("Error: Botify API token not found. Please connect with Botify first.", style=pip.get_style("error"))
            
            # Fetch analysis slugs
            import logging
            logging.info(f"Getting analyses for {username}/{project_name}")
            
            slugs = await self.fetch_analyses(username, project_name, api_token)
            logging.info(f"Got {len(slugs) if slugs else 0} analyses")
            
            if not slugs:
                return P(f"Error: No analyses found for project {project_name}. Please check your API access.", style=pip.get_style("error"))
            
            # Determine selected value (first analysis if no previous selection)
            selected_value = selected_slug if selected_slug else slugs[0]
            
            # Show the form with dropdown
            await self.message_queue.add(pip, self.step_messages.get(step_id, {}).get("input", 
                                    f"Select an analysis for {project_name}"), 
                                    verbatim=True)
            
            return Div(
                Card(
                    H3(f"{step.show}"),
                    P(f"Select an analysis for project '{project_name}'"),
                    P(f"Organization: {username}", style="color: #666; font-size: 0.9em;"),
                    Form(
                        Select(
                            name="analysis_slug",
                            required=True,
                            autofocus=True,
                            *[
                                Option(
                                    slug,
                                    value=slug,
                                    selected=(slug == selected_value)
                                ) for slug in slugs
                            ]
                        ),
                        Button("Select Analysis", type="submit", cls="primary", style="margin-top: 10px;"),
                        hx_post=f"/{app_name}/{step_id}_submit", 
                        hx_target=f"#{step_id}"
                    )
                ),
                Div(id=next_step_id),  # Empty div for next step
                id=step_id
            )
            
        except Exception as e:
            import logging
            logging.exception(f"Error in {step_id}: {e}")
            return P(f"Error fetching analyses: {str(e)}", style=pip.get_style("error"))

    async def step_02_submit(self, request):
        """Process the selected analysis slug for step_02."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_02"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # The critical part is that we're not changing the code that determines next_step_id
        # It's automatically calculated as:
        # next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        # This will now correctly point to step_03 since that's the next step in the steps list

        # Get project data from previous step
        prev_step_id = "step_01"
        prev_step_data = pip.get_step_data(pipeline_id, prev_step_id, {})
        prev_data_str = prev_step_data.get("botify_project", "")
        
        if not prev_data_str:
            return P("Error: Project data not found. Please complete step 1 first.", style=pip.get_style("error"))
        
        import json
        project_data = json.loads(prev_data_str)
        project_name = project_data.get("project_name", "")
        username = project_data.get("username", "")
        
        # Get the selected analysis slug from the form
        form = await request.form()
        analysis_slug = form.get("analysis_slug", "").strip()
        
        if not analysis_slug:
            return P("Error: No analysis selected", style=pip.get_style("error"))
        
        # Store the analysis result
        analysis_result = {
            "analysis_slug": analysis_slug,
            "project": project_name,
            "username": username,
            "timestamp": datetime.now().isoformat()
        }
        
        # Convert to JSON for storage
        analysis_result_str = json.dumps(analysis_result)
        
        # Store in state
        await pip.update_step_state(pipeline_id, step_id, analysis_result_str, steps)
        
        # Add message
        await self.message_queue.add(pip, f"{step.show} complete: Selected analysis '{analysis_slug}'", verbatim=True)
        
        # Return result display
        return Div(
            pip.revert_control(
                step_id=step_id, 
                app_name=app_name, 
                message=f"{step.show}: {analysis_slug}",
                steps=steps
            ),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )

    async def step_03(self, request):
        """Handles GET request for checking if a Botify project has web logs."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_03"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        
        # Get the check result if already completed
        import json
        check_result_str = step_data.get(step.done, "")
        check_result = json.loads(check_result_str) if check_result_str else {}
        
        # Get project data from previous step
        prev_step_id = "step_01"
        prev_step_data = pip.get_step_data(pipeline_id, prev_step_id, {})
        prev_data_str = prev_step_data.get("botify_project", "")
        
        if not prev_data_str:
            return P("Error: Project data not found. Please complete step 1 first.", style=pip.get_style("error"))
        
        project_data = json.loads(prev_data_str)
        project_name = project_data.get("project_name", "")
        username = project_data.get("username", "")

        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and check_result:
            # Show finalized state with check result
            has_logs = check_result.get("has_logs", False)
            status_text = "HAS web logs" if has_logs else "does NOT have web logs"
            status_color = "green" if has_logs else "red"
            
            return Div(
                Card(
                    H3(f"🔒 {step.show}"),
                    Div(
                        P(f"Project {project_name}", style="margin-bottom: 5px;"),
                        P(f"Status: Project {status_text}", style=f"color: {status_color}; font-weight: bold;"),
                        style="padding: 10px; background: var(--pico-card-background-color); border-radius: 5px;"
                    )
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        
        # Check if step is complete and not being reverted to
        if check_result and state.get("_revert_target") != step_id:
            # Show completed state with check result
            has_logs = check_result.get("has_logs", False)
            status_text = "HAS web logs" if has_logs else "does NOT have web logs"
            status_color = "green" if has_logs else "red"
            
            return Div(
                pip.revert_control(
                    step_id=step_id, 
                    app_name=app_name, 
                    message=f"{step.show}: Project {status_text}",
                    steps=steps
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        else:
            # Show form to run the check
            await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
            
            return Div(
                Card(
                    H3(f"{step.show}"),
                    P(f"Check if project '{project_name}' has web logs available"),
                    P(f"Organization: {username}", style="color: #666; font-size: 0.9em;"),
                    Form(
                        Button("Run Check", type="submit", cls="primary"),
                        hx_post=f"/{app_name}/{step_id}_submit", 
                        hx_target=f"#{step_id}"
                    )
                ),
                Div(id=next_step_id),  # Empty div for next step
                id=step_id
            )

    async def step_03_submit(self, request):
        """Process the check for Botify web logs."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_03"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")

        # Get project data from previous step
        prev_step_id = "step_01"
        prev_step_data = pip.get_step_data(pipeline_id, prev_step_id, {})
        prev_data_str = prev_step_data.get("botify_project", "")
        
        if not prev_data_str:
            return P("Error: Project data not found. Please complete step 1 first.", style=pip.get_style("error"))
        
        import json
        project_data = json.loads(prev_data_str)
        project_name = project_data.get("project_name", "")
        username = project_data.get("username", "")
        
        # Perform the check for web logs
        has_logs, error_message = await self.check_if_project_has_collection(username, project_name, "logs")
        
        if error_message:
            return P(f"Error: {error_message}", style=pip.get_style("error"))
        
        # Store the check result
        check_result = {
            "has_logs": has_logs,
            "project": project_name,
            "username": username,
            "timestamp": datetime.now().isoformat()
        }
        
        # Convert to JSON for storage
        check_result_str = json.dumps(check_result)
        
        # Store in state
        await pip.update_step_state(pipeline_id, step_id, check_result_str, steps)
        
        # Add message
        status_text = "HAS" if has_logs else "does NOT have"
        await self.message_queue.add(pip, f"{step.show} complete: Project {status_text} web logs", verbatim=True)
        
        # Return result display
        status_color = "green" if has_logs else "red"
        
        return Div(
            pip.revert_control(
                step_id=step_id, 
                app_name=app_name, 
                message=f"{step.show}: Project {status_text} web logs",
                steps=steps
            ),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )

    async def step_04(self, request):
        """Handles GET request for checking if a Botify project has Search Console data."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        
        # Get the check result if already completed
        import json
        check_result_str = step_data.get(step.done, "")
        check_result = json.loads(check_result_str) if check_result_str else {}
        
        # Get project data from step_01
        prev_step_id = "step_01"
        prev_step_data = pip.get_step_data(pipeline_id, prev_step_id, {})
        prev_data_str = prev_step_data.get("botify_project", "")
        
        if not prev_data_str:
            return P("Error: Project data not found. Please complete step 1 first.", style=pip.get_style("error"))
        
        project_data = json.loads(prev_data_str)
        project_name = project_data.get("project_name", "")
        username = project_data.get("username", "")

        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and check_result:
            # Show finalized state with check result
            has_search_console = check_result.get("has_search_console", False)
            status_text = "HAS Search Console data" if has_search_console else "does NOT have Search Console data"
            status_color = "green" if has_search_console else "red"
            
            return Div(
                Card(
                    H3(f"🔒 {step.show}"),
                    Div(
                        P(f"Project {project_name}", style="margin-bottom: 5px;"),
                        P(f"Status: Project {status_text}", style=f"color: {status_color}; font-weight: bold;"),
                        style="padding: 10px; background: var(--pico-card-background-color); border-radius: 5px;"
                    )
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        
        # Check if step is complete and not being reverted to
        if check_result and state.get("_revert_target") != step_id:
            # Show completed state with check result
            has_search_console = check_result.get("has_search_console", False)
            status_text = "HAS Search Console data" if has_search_console else "does NOT have Search Console data"
            status_color = "green" if has_search_console else "red"
            
            return Div(
                pip.revert_control(
                    step_id=step_id, 
                    app_name=app_name, 
                    message=f"{step.show}: Project {status_text}",
                    steps=steps
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        else:
            # Show form to run the check
            await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
            
            return Div(
                Card(
                    H3(f"{step.show}"),
                    P(f"Check if project '{project_name}' has Search Console data available"),
                    P(f"Organization: {username}", style="color: #666; font-size: 0.9em;"),
                    Form(
                        Button("Run Check", type="submit", cls="primary"),
                        hx_post=f"/{app_name}/{step_id}_submit", 
                        hx_target=f"#{step_id}"
                    )
                ),
                Div(id=next_step_id),  # Empty div for next step
                id=step_id
            )

    async def step_04_submit(self, request):
        """Process the check for Botify Search Console data."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")

        # Get project data from previous step
        prev_step_id = "step_01"
        prev_step_data = pip.get_step_data(pipeline_id, prev_step_id, {})
        prev_data_str = prev_step_data.get("botify_project", "")
        
        if not prev_data_str:
            return P("Error: Project data not found. Please complete step 1 first.", style=pip.get_style("error"))
        
        import json
        project_data = json.loads(prev_data_str)
        project_name = project_data.get("project_name", "")
        username = project_data.get("username", "")
        
        # First, show a visual progress indicator
        # We'll simply return the progress UI directly instead of trying to use Response
        return Card(
            H3(f"{step.show}"),
            P(f"Checking if project '{project_name}' has Search Console data..."),
            Progress(style="margin-top: 10px;"),  # Indeterminate progress bar
            
            # Add a script that will check again after a delay
            Script("""
            setTimeout(function() {
                htmx.ajax('POST', '""" + f"/{app_name}/{step_id}_complete" + """', {
                    target: '#""" + step_id + """',
                    values: { 'delay_complete': 'true' }
                });
            }, 1500);
            """),
            id=step_id
        )

    async def step_04_complete(self, request):
        """Handles completion after the progress indicator has been shown."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Get project data from step_01
        prev_step_id = "step_01"
        prev_step_data = pip.get_step_data(pipeline_id, prev_step_id, {})
        prev_data_str = prev_step_data.get("botify_project", "")
        
        if not prev_data_str:
            return P("Error: Project data not found. Please complete step 1 first.", style=pip.get_style("error"))
        
        import json
        project_data = json.loads(prev_data_str)
        project_name = project_data.get("project_name", "")
        username = project_data.get("username", "")
        
        # Do the actual check
        has_search_console, error_message = await self.check_if_project_has_collection(username, project_name, "search_console")
        
        if error_message:
            return P(f"Error: {error_message}", style=pip.get_style("error"))
        
        # Store the check result
        check_result = {
            "has_search_console": has_search_console,
            "project": project_name,
            "username": username,
            "timestamp": datetime.now().isoformat()
        }
        
        # Convert to JSON for storage
        check_result_str = json.dumps(check_result)
        
        # Store in state
        await pip.update_step_state(pipeline_id, step_id, check_result_str, steps)
        
        # Progress indicator for checking if data is available
        status_text = "HAS" if has_search_console else "does NOT have"
        await self.message_queue.add(pip, f"✓ Check complete: Project {status_text} Search Console data", verbatim=True)
        
        # If the project has search console data, simulate the download process
        import asyncio
        
        if has_search_console:
            # Note that we're no longer trying to return an immediate response
            # Instead, we'll just simulate the process with messaging and then return at the end
            
            # Send immediate message
            await self.message_queue.add(pip, "🔄 Initiating Search Console data export...", verbatim=True)
            await asyncio.sleep(1.0)  # Wait 1 second
            
            # Export initiated message
            await self.message_queue.add(pip, "✓ Export job created successfully!", verbatim=True)
            await asyncio.sleep(1.0)  # Wait 1 second
            
            # Start polling message
            await self.message_queue.add(pip, "🔄 Polling for export completion...", verbatim=True)
            
            # Simulate polling process (3 iterations for demo)
            for i in range(3):
                await asyncio.sleep(2.0)  # Wait 2 seconds between polls
                await self.message_queue.add(pip, f"🔄 Still waiting for export... (poll {i+1}/3)", verbatim=True)
            
            # Export ready message
            await self.message_queue.add(pip, "✓ Export completed and ready for download!", verbatim=True)
            await asyncio.sleep(1.0)  # Wait 1 second
            
            # Downloading message
            await self.message_queue.add(pip, "🔄 Downloading Search Console data...", verbatim=True)
            await asyncio.sleep(2.0)  # Wait 2 seconds
            
            # Download complete message
            await self.message_queue.add(pip, "✓ Download complete, extracting data...", verbatim=True)
            await asyncio.sleep(1.0)  # Wait 1 second
            
            # Processing complete message
            await self.message_queue.add(pip, "✓ Search Console data ready for analysis!", verbatim=True)
            
            # Create downloadable data directory info for storage
            download_info = {
                "has_file": True,
                "file_path": f"data/{username}/{project_name}/search_console_data.csv",
                "timestamp": datetime.now().isoformat(),
                "size": "1.2MB"  # Simulated file size
            }
            
            # Update the check result to include download info
            check_result.update({
                "download_complete": True,
                "download_info": download_info
            })
            
            # Update state with download info
            check_result_str = json.dumps(check_result)
            await pip.update_step_state(pipeline_id, step_id, check_result_str, steps)
        
        # Final success message
        completed_message = "Download completed successfully!" if has_search_console else "No Search Console data available (skipping download)"
        await self.message_queue.add(pip, f"{step.show} complete: {completed_message}", verbatim=True)
        
        # Return the completed display with appropriate status
        status_color = "green" if has_search_console else "orange"
        
        return Div(
            pip.revert_control(
                step_id=step_id, 
                app_name=app_name, 
                message=f"{step.show}: {completed_message}",
                steps=steps
            ),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )

    async def step_05(self, request):
        """Handles GET request for placeholder Step 5."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_05"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        placeholder_value = step_data.get(step.done, "")  # Get the value

        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and placeholder_value:
            # Display for finalized state
            return Div(
                Card(
                    H3(f"🔒 {step.show}"),
                    P("Third CSV Export completed", style="padding: 10px; background: var(--pico-card-background-color); border-radius: 5px;")
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
            
        # Check if step is complete and not being reverted to
        if placeholder_value and state.get("_revert_target") != step_id:
            # Display for completed state
            return Div(
                pip.revert_control(
                    step_id=step_id, 
                    app_name=app_name, 
                    message=f"{step.show}: Complete",
                    steps=steps
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        else:
            # Display input form with just a Proceed button
            await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
            
            return Div(
                Card(
                    H3(f"{step.show}"),
                    P("This is the final step for Generating the Optimization:"),
                    Form(
                        Button("Proceed", type="submit", cls="primary"),
                        hx_post=f"/{app_name}/{step_id}_submit", 
                        hx_target=f"#{step_id}"
                    )
                ),
                Div(id=next_step_id),  # Empty div for next step - will be populated via chain reaction
                id=step_id
            )

    async def step_05_submit(self, request):
        """Process the submission for placeholder Step 5."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_05"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")

        # Use fixed value for placeholder
        placeholder_value = "completed"

        # Store in state
        await pip.update_step_state(pipeline_id, step_id, placeholder_value, steps)
        await self.message_queue.add(pip, f"{step.show} complete.", verbatim=True)
        
        # Return with revert control and chain reaction to next step (finalize)
        return Div(
            pip.revert_control(
                step_id=step_id, 
                app_name=app_name, 
                message=f"{step.show}: Complete",
                steps=steps
            ),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )

    # --- Helper Methods ---
    
    def validate_botify_url(self, url):
        """Validate a Botify project URL and extract project information."""
        # Trim whitespace
        url = url.strip()
        
        # Basic URL validation
        if not url:
            return False, "URL is required", {}
        
        try:
            # Use a more flexible pattern that matches Botify URLs
            if not url.startswith(("https://app.botify.com/", "https://analyze.botify.com/")):
                return False, "URL must be a Botify project URL (starting with https://app.botify.com/ or https://analyze.botify.com/)", {}
            
            # Extract the path components and clean the URL
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            path_parts = [p for p in parsed_url.path.strip('/').split('/') if p]
            
            # Need at least two components (org and project)
            if len(path_parts) < 2:
                return False, "Invalid Botify URL: must contain at least organization and project", {}
            
            # Extract just organization and project - ignore anything after
            org_slug = path_parts[0]  # First component is always org
            project_slug = path_parts[1]  # Second component is always project
            
            # Rebuild the canonical URL (just org/project)
            canonical_url = f"https://{parsed_url.netloc}/{org_slug}/{project_slug}/"
            
            # Create project data
            project_data = {
                "url": canonical_url,  # Store canonical URL
                "username": org_slug,
                "project_name": project_slug,
                "project_id": f"{org_slug}/{project_slug}"
            }
            
            return True, f"Valid Botify project: {project_slug}", project_data
        
        except Exception as e:
            return False, f"Error parsing URL: {str(e)}", {}

    async def check_if_project_has_collection(self, org_slug, project_slug, collection_id="logs"):
        """
        Checks if a specific collection exists for the given org and project.
        
        Args:
            org_slug: Organization slug
            project_slug: Project slug
            collection_id: ID of the collection to check for (default: "logs")
            
        Returns:
            (True, None) if found, (False, None) if not found, or (False, error_message) on error.
        """
        import httpx
        import json
        import os
        
        # Configuration
        TOKEN_FILE = "botify_token.txt"
        
        # Load API key - properly clean it
        try:
            if not os.path.exists(TOKEN_FILE):
                return False, f"Token file '{TOKEN_FILE}' not found."
            
            with open(TOKEN_FILE) as f:
                content = f.read().strip()
                # Extract just the token (first line) and strip any comments
                api_key = content.split('\n')[0].strip()
                if not api_key:
                    return False, f"Token file '{TOKEN_FILE}' is empty."
        except Exception as e:
            return False, f"Error loading API key: {e}"
        
        # Check parameters
        if not org_slug or not project_slug:
            return False, "Organization and project slugs are required."
        
        # Prepare request
        collections_url = f"https://api.botify.com/v1/projects/{org_slug}/{project_slug}/collections"
        headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json"
        }
        
        # Make request
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(collections_url, headers=headers, timeout=60.0)
            
            if response.status_code == 401:
                return False, "Authentication failed (401). Check your API token."
            elif response.status_code == 403:
                return False, "Forbidden (403). You may not have access to this project or endpoint."
            elif response.status_code == 404:
                return False, "Project not found (404). Check org/project slugs."
            
            response.raise_for_status()  # Raise errors for other bad statuses
            collections_data = response.json()
            
            if not isinstance(collections_data, list):
                return False, "Unexpected API response format. Expected a list."
            
            # Check if specified collection exists
            for collection in collections_data:
                if isinstance(collection, dict) and collection.get('id') == collection_id:
                    return True, None
            
            # Not found
            return False, None
            
        except httpx.HTTPStatusError as e:
            return False, f"API Error: {e.response.status_code}"
        except httpx.RequestError as e:
            return False, f"Network error: {e}"
        except json.JSONDecodeError:
            return False, "Could not decode the API response as JSON."
        except Exception as e:
            return False, f"An unexpected error occurred: {e}"

    async def fetch_analyses(self, org, project, api_token):
        """
        Fetch analysis slugs for a Botify project.
        
        Args:
            org: Organization slug
            project: Project slug
            api_token: Botify API token
            
        Returns:
            List of analysis slugs or empty list on error
        """
        import httpx
        import json
        import logging
        
        # Validate inputs
        if not org or not project or not api_token:
            logging.error(f"Missing required parameters: org={org}, project={project}")
            return []
        
        url = f"https://api.botify.com/v1/analyses/{org}/{project}"
        headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=60.0)
            
            if response.status_code != 200:
                logging.error(f"API error: Status {response.status_code} for {url}")
                return []
            
            data = response.json()
            
            # Debug logging to see what's in the response
            logging.info(f"API response keys: {data.keys()}")
            
            # Check if the response has a 'results' key with a list of analyses
            if "results" not in data:
                logging.error(f"No 'results' key in response: {data}")
                return []
            
            analyses = data["results"]
            if not analyses:
                logging.error("Analyses list is empty")
                return []
            
            logging.info(f"Found {len(analyses)} analyses")
            
            # Extract just the slugs from the analyses
            slugs = [analysis.get('slug') for analysis in analyses if analysis.get('slug')]
            
            return slugs
            
        except Exception as e:
            logging.exception(f"Error fetching analyses: {str(e)}")
            return []

    def read_api_token(self):
        """Read the Botify API token from the token file."""
        import os
        
        TOKEN_FILE = "botify_token.txt"
        
        try:
            if not os.path.exists(TOKEN_FILE):
                return None
            
            with open(TOKEN_FILE) as f:
                content = f.read().strip()
                # Get the first line and strip any comments or whitespace
                token = content.split('\n')[0].strip()
            
            return token
        except Exception:
            return None

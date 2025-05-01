import asyncio
from collections import namedtuple
from datetime import datetime, timedelta
from urllib.parse import urlparse
import httpx
import json
import re
import logging
import time
import os
import zipfile
import socket
import gzip
import shutil
import pandas as pd

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

        # Add the step_02_process route
        routes.append((f"/{app_name}/step_02_process", self.step_02_process, ["POST"]))

        # Add the step_03_process route
        routes.append((f"/{app_name}/step_03_process", self.step_03_process, ["POST"]))

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
            logging.info(f"Getting analyses for {username}/{project_name}")
            
            slugs = await self.fetch_analyses(username, project_name, api_token)
            logging.info(f"Got {len(slugs) if slugs else 0} analyses")
            
            if not slugs:
                return P(f"Error: No analyses found for project {project_name}. Please check your API access.", style=pip.get_style("error"))
            
            # Determine selected value (first analysis if no previous selection)
            selected_value = selected_slug if selected_slug else slugs[0]
            
            # Check which analyses already have downloaded crawl data
            downloaded_slugs = set()
            for slug in slugs:
                filepath = await self.get_deterministic_filepath(username, project_name, slug, "crawl")
                exists, _ = await self.check_file_exists(filepath)
                if exists:
                    downloaded_slugs.add(slug)
            
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
                                    f"{slug} (Downloaded)" if slug in downloaded_slugs else slug,
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
            logging.exception(f"Error in {step_id}: {e}")
            return P(f"Error fetching analyses: {str(e)}", style=pip.get_style("error"))

    async def step_02_submit(self, request):
        """Process the selected analysis slug for step_02 and download crawl data."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_02"
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
        
        project_data = json.loads(prev_data_str)
        project_name = project_data.get("project_name", "")
        username = project_data.get("username", "")
        
        # Get the selected analysis slug from the form
        form = await request.form()
        analysis_slug = form.get("analysis_slug", "").strip()
        
        if not analysis_slug:
            return P("Error: No analysis selected", style=pip.get_style("error"))
        
        # First, show a progress indicator while we download the crawl data
        await self.message_queue.add(pip, f"Selected analysis: {analysis_slug}. Starting crawl data download...", verbatim=True)
        
        # Store the initial analysis selection
        analysis_result = {
            "analysis_slug": analysis_slug,
            "project": project_name,
            "username": username,
            "timestamp": datetime.now().isoformat(),
            "download_started": True
        }
        
        # Convert to JSON for storage
        analysis_result_str = json.dumps(analysis_result)
        
        # Store in state
        await pip.update_step_state(pipeline_id, step_id, analysis_result_str, steps)
        
        # Return the progress indicator immediately
        return Card(
            H3(f"{step.show}"),
            P(f"Downloading data for analysis '{analysis_slug}'..."),
            Progress(style="margin-top: 10px;"),  # Indeterminate progress bar
            
            # Add a script that will process in the background and update when complete
            Script("""
            setTimeout(function() {
                htmx.ajax('POST', '""" + f"/{app_name}/step_02_process" + """', {
                    target: '#""" + step_id + """',
                    values: { 
                        'analysis_slug': '""" + analysis_slug + """',
                        'username': '""" + username + """',
                        'project_name': '""" + project_name + """'
                    }
                });
            }, 500);
            """),
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
        """Process the check for Botify web logs and download if available."""
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
        
        project_data = json.loads(prev_data_str)
        project_name = project_data.get("project_name", "")
        username = project_data.get("username", "")
        
        # Get analysis data from step_02
        analysis_step_id = "step_02"
        analysis_step_data = pip.get_step_data(pipeline_id, analysis_step_id, {})
        analysis_data_str = analysis_step_data.get("analysis_selection", "")
        
        if not analysis_data_str:
            return P("Error: Analysis data not found. Please complete step 2 first.", style=pip.get_style("error"))
        
        analysis_data = json.loads(analysis_data_str)
        analysis_slug = analysis_data.get("analysis_slug", "")
        
        # First, show a progress indicator
        await self.message_queue.add(pip, f"Checking if project '{project_name}' has web logs available...", verbatim=True)
        
        # Return the progress indicator immediately
        return Card(
            H3(f"{step.show}"),
            P(f"Checking if project '{project_name}' has web logs..."),
            Progress(style="margin-top: 10px;"),  # Indeterminate progress bar
            
            # Add a script that will process in the background
            Script("""
            setTimeout(function() {
                htmx.ajax('POST', '""" + f"/{app_name}/step_03_process" + """', {
                    target: '#""" + step_id + """',
                    values: { 
                        'analysis_slug': '""" + analysis_slug + """',
                        'username': '""" + username + """',
                        'project_name': '""" + project_name + """'
                    }
                });
            }, 500);
            """),
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
        
        # Get project and analysis data
        prev_step_id = "step_01"
        prev_step_data = pip.get_step_data(pipeline_id, prev_step_id, {})
        prev_data_str = prev_step_data.get("botify_project", "")
        
        if not prev_data_str:
            return P("Error: Project data not found.", style=pip.get_style("error"))
        
        project_data = json.loads(prev_data_str)
        project_name = project_data.get("project_name", "")
        username = project_data.get("username", "")
        
        analysis_step_id = "step_02"
        analysis_step_data = pip.get_step_data(pipeline_id, analysis_step_id, {})
        analysis_data_str = analysis_step_data.get("analysis_selection", "")
        
        if not analysis_data_str:
            return P("Error: Analysis data not found.", style=pip.get_style("error"))
        
        analysis_data = json.loads(analysis_data_str)
        analysis_slug = analysis_data.get("analysis_slug", "")
        
        # Do the check
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
        
        # If the project has search console data, process it SYNCHRONOUSLY
        if has_search_console:
            await self.message_queue.add(pip, f"✓ Project has Search Console data, downloading...", verbatim=True)
            
            # Process data and wait for completion - key change here
            await self.process_search_console_data(
                pip, pipeline_id, step_id, username, project_name, analysis_slug, check_result
            )
        else:
            # No search console data
            await self.message_queue.add(pip, f"Project does not have Search Console data (skipping download)", verbatim=True)
            
            # Store the check result
            check_result_str = json.dumps(check_result)
            await pip.update_step_state(pipeline_id, step_id, check_result_str, self.steps)
        
        # Return completed step
        status_text = "HAS" if has_search_console else "does NOT have"
        completed_message = "Data downloaded successfully" if has_search_console else "No Search Console data available"
        
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

    async def get_deterministic_filepath(self, username, project_name, analysis_slug, data_type):
        """Generate a deterministic file path for a given data export.
        
        Args:
            username: Organization username
            project_name: Project name
            analysis_slug: Analysis slug
            data_type: Type of data (crawl, weblog, gsc)
            
        Returns:
            String path to the file location
        """
        # Create base directory path
        base_dir = f"downloads/{username}/{project_name}/{analysis_slug}"
        
        # Map data types to filenames
        filenames = {
            "crawl": "crawl.csv",
            "weblog": "weblog.csv", 
            "gsc": "gsc.csv"
        }
        
        if data_type not in filenames:
            raise ValueError(f"Unknown data type: {data_type}")
        
        # Get the filename for this data type
        filename = filenames[data_type]
        
        # Return the full path
        return f"{base_dir}/{filename}"

    async def check_file_exists(self, filepath):
        """Check if a file exists and is non-empty.
        
        Args:
            filepath: Path to check
            
        Returns:
            (bool, dict): Tuple of (exists, file_info)
        """
        
        # Check if the file exists
        if not os.path.exists(filepath):
            return False, {}
        
        # Get file stats
        stats = os.stat(filepath)
        
        # Only consider it valid if it has content
        if stats.st_size == 0:
            return False, {}
        
        # Return file info
        file_info = {
            "path": filepath,
            "size": f"{stats.st_size / 1024:.1f} KB",
            "created": time.ctime(stats.st_ctime)
        }
        
        return True, file_info

    async def ensure_directory_exists(self, filepath):
        """Ensure the directory for a file exists.
        
        Args:
            filepath: Path to the file
        """
        directory = os.path.dirname(filepath)
        os.makedirs(directory, exist_ok=True)

    async def process_search_console_data(self, pip, pipeline_id, step_id, username, project_name, analysis_slug, check_result):
        """Process search console data in the background."""
        
        # Add detailed logging
        logging.info(f"Starting real GSC data export for {username}/{project_name}/{analysis_slug}")
        
        try:
            # Determine file path for this export
            gsc_filepath = await self.get_deterministic_filepath(username, project_name, analysis_slug, "gsc")
            
            # Check if file already exists
            file_exists, file_info = await self.check_file_exists(gsc_filepath)
            
            if file_exists:
                # File already exists, skip the export
                await self.message_queue.add(pip, f"✓ Found existing Search Console data from {file_info['created']}", verbatim=True)
                await self.message_queue.add(pip, f"ℹ️ Using cached file: {file_info['path']} ({file_info['size']})", verbatim=True)
                
                # Update check result with existing file info
                check_result.update({
                    "download_complete": True,
                    "download_info": {
                        "has_file": True,
                        "file_path": gsc_filepath,
                        "timestamp": file_info['created'],
                        "size": file_info['size'],
                        "cached": True
                    }
                })
            else:
                # Need to do the export and download
                await self.message_queue.add(pip, "🔄 Initiating Search Console data export...", verbatim=True)
                
                # Get API token
                api_token = self.read_api_token()
                if not api_token:
                    raise ValueError("Cannot read API token")
                
                # Create export job payload for Search Console data
                # Use last 30 days by default
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                
                # Build BQLv2 export query
                export_query = await self.build_exports(
                    username, 
                    project_name, 
                    analysis_slug, 
                    data_type='gsc',
                    start_date=start_date,
                    end_date=end_date
                )
                
                # Submit export job
                job_url = "https://api.botify.com/v1/jobs"
                headers = {
                    "Authorization": f"Token {api_token}",
                    "Content-Type": "application/json"
                }
                
                try:
                    # Log the payload we're about to send
                    logging.info(f"Submitting export job with payload: {json.dumps(export_query['export_job_payload'], indent=2)}")
                    
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            job_url, 
                            headers=headers, 
                            json=export_query["export_job_payload"],
                            timeout=60.0
                        )
                        # Log the response status
                        logging.info(f"Export job submission response status: {response.status_code}")
                        
                        try:
                            # Try to log the response body
                            logging.info(f"Export job response: {json.dumps(response.json(), indent=2)}")
                        except:
                            logging.info(f"Could not parse response as JSON. Raw: {response.text[:500]}")
                        
                        response.raise_for_status()
                        job_data = response.json()
                        
                        # Get job URL
                        job_url_path = job_data.get('job_url')
                        if not job_url_path:
                            raise ValueError("Failed to get job URL from response")
                            
                        full_job_url = f"https://api.botify.com{job_url_path}"
                        logging.info(f"Got job URL: {full_job_url}")
                        
                        # Export initiated message
                        await self.message_queue.add(pip, "✓ Export job created successfully!", verbatim=True)
                        
                except Exception as e:
                    logging.exception(f"Error creating export job: {str(e)}")
                    await self.message_queue.add(pip, f"❌ Error creating export job: {str(e)}", verbatim=True)
                    raise
                
                # Start polling message
                await self.message_queue.add(pip, "🔄 Polling for export completion...", verbatim=True)
                
                # Poll for completion with improved error handling
                success, result = await self.poll_job_status(full_job_url, api_token)
                
                if not success:
                    error_message = isinstance(result, str) and result or "Export job failed"
                    await self.message_queue.add(pip, f"❌ Export failed: {error_message}", verbatim=True)
                    raise ValueError(f"Export failed: {error_message}")
                
                # Export ready message
                await self.message_queue.add(pip, "✓ Export completed and ready for download!", verbatim=True)
                
                # Download the file
                download_url = result.get("download_url")
                if not download_url:
                    await self.message_queue.add(pip, "❌ No download URL found in job result", verbatim=True)
                    raise ValueError("No download URL found in job result")
                
                # Downloading message
                await self.message_queue.add(pip, "🔄 Downloading Search Console data...", verbatim=True)
                
                # Make sure target directory exists
                await self.ensure_directory_exists(gsc_filepath)
                
                # Download the zip file to a temporary location
                zip_path = f"{gsc_filepath}.zip"
                try:
                    async with httpx.AsyncClient() as client:
                        async with client.stream("GET", download_url, headers={"Authorization": f"Token {api_token}"}) as response:
                            response.raise_for_status()
                            with open(zip_path, 'wb') as f:
                                async for chunk in response.aiter_bytes():
                                    f.write(chunk)
                
                    # Extract the CSV from the zip
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        # Get the CSV file name (should be the only file or first file)
                        csv_name = None
                        for name in zip_ref.namelist():
                            if name.endswith('.csv'):
                                csv_name = name
                                break
                        
                        if not csv_name:
                            raise ValueError("No CSV file found in the downloaded zip")
                        
                        # Extract and rename to our target path
                        zip_ref.extract(csv_name, os.path.dirname(gsc_filepath))
                        extracted_path = os.path.join(os.path.dirname(gsc_filepath), csv_name)
                        
                        # Rename to our standardized file name if needed
                        if extracted_path != gsc_filepath:
                            if os.path.exists(gsc_filepath):
                                os.remove(gsc_filepath)
                            os.rename(extracted_path, gsc_filepath)
                
                    # Clean up the zip file
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
                
                    # Get info about the created file
                    _, file_info = await self.check_file_exists(gsc_filepath)
                    
                    # Download complete message
                    await self.message_queue.add(pip, f"✓ Download complete: {file_info['path']} ({file_info['size']})", verbatim=True)
                    
                    # Create downloadable data directory info for storage
                    download_info = {
                        "has_file": True,
                        "file_path": gsc_filepath,
                        "timestamp": file_info['created'],
                        "size": file_info['size'],
                        "cached": False
                    }
                    
                    # Update the check result to include download info
                    check_result.update({
                        "download_complete": True,
                        "download_info": download_info
                    })
                    
                except Exception as e:
                    await self.message_queue.add(pip, f"❌ Error downloading or extracting file: {str(e)}", verbatim=True)
                    raise
                
            # Final processing message
            await self.message_queue.add(pip, "✓ Search Console data ready for analysis!", verbatim=True)
            
            # Update state with download info
            check_result_str = json.dumps(check_result)
            await pip.update_step_state(pipeline_id, step_id, check_result_str, self.steps)
            
        except Exception as e:
            logging.exception(f"Error in process_search_console_data: {e}")
            
            # Update check result with error
            check_result.update({
                "download_complete": True,  # Mark as complete even on error
                "error": str(e)
            })
            check_result_str = json.dumps(check_result)
            await pip.update_step_state(pipeline_id, step_id, check_result_str, self.steps)
            
            # Add error message to queue
            await self.message_queue.add(pip, f"❌ Error processing Search Console data: {str(e)}", verbatim=True)

    async def build_exports(self, username, project_name, analysis_slug=None, data_type='crawl', start_date=None, end_date=None):
        """Builds BQLv2 query objects and export job payloads."""
        
        if data_type == 'gsc':
            # For Search Console data, we need to specify periods
            if not start_date or not end_date:
                # Use default 30 day range if dates not provided
                end_date = datetime.now().strftime("%Y%m%d")  # Format as YYYYMMDD without dashes
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            
            # Build the export job payload using the correct structure from your example
            export_job_payload = {
                "job_type": "export",
                "payload": {
                    "query": {
                        "collections": ["search_console"],
                        "periods": [[start_date, end_date]],
                        "query": {
                            "dimensions": ["url"],
                            "metrics": [
                                {
                                    "field": "search_console.period_0.count_impressions",
                                    "name": "Impressions"
                                },
                                {
                                    "field": "search_console.period_0.count_clicks",
                                    "name": "Clicks"
                                },
                                {
                                    "field": "search_console.period_0.ctr",
                                    "name": "CTR"
                                },
                                {
                                    "field": "search_console.period_0.avg_position",
                                    "name": "Avg. Position"
                                }
                            ],
                            "sort": [
                                {
                                    "type": "metrics",
                                    "index": 0,
                                    "order": "desc"
                                }
                            ]
                        }
                    },
                    "export_size": 10000,
                    "formatter": "csv",
                    "connector": "direct_download",
                    "formatter_config": {
                        "print_header": True,
                        "print_delimiter": True
                    },
                    "extra_config": {
                        "compression": "zip"
                    },
                    "username": username,
                    "project": project_name,
                    "export_job_name": "Search Console Export"
                }
            }
            
            # Also simplify the check query
            check_query_payload = {
                "collections": ["search_console"],
                "periods": [[start_date, end_date]],
                "query": {
                    "dimensions": [],
                    "metrics": [{"function": "count", "args": ["search_console.url"]}]
                }
            }
            
            # Return all query components
            return {
                "check_query_payload": check_query_payload,
                "check_url": f"/v1/projects/{username}/{project_name}/query",
                "export_job_payload": export_job_payload,
                "export_url": "/v1/jobs",
                "data_type": data_type
            }
        
        # Keep the rest of the method unchanged for other data types
        elif data_type == 'crawl':
            if not analysis_slug:
                raise ValueError("analysis_slug is required for data_type 'crawl'")
            
            # For crawl data, we need specific fields from the crawl collection
            collection = f"crawl.{analysis_slug}"
            
            # Define the BQL query for crawl data
            bql_query = {
                "collections": [collection],
                "query": {
                    "dimensions": [
                        f"{collection}.url", 
                        f"{collection}.http_code", 
                        f"{collection}.metadata.title.content"
                    ],
                    "filters": {
                        "field": f"{collection}.http_code", 
                        "predicate": "eq", 
                        "value": 200
                    }
                }
            }
            
            # Define the lightweight check query
            check_query_payload = {
                "collections": [collection],
                "query": {
                    "dimensions": [],
                    "metrics": [{"function": "count", "args": [f"{collection}.url"]}],
                    "filters": {
                        "field": f"{collection}.http_code", 
                        "predicate": "eq", 
                        "value": 200
                    }
                }
            }

        elif data_type == 'weblog':
            # For weblog data, also need periods
            if not start_date or not end_date:
                # Use default 30 day range if dates not provided
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            # Define the BQL query for weblog data
            bql_query = {
                "collections": ["logs"],
                "periods": [[start_date, end_date]],
                "query": {
                    "dimensions": ["logs.url"],
                    "metrics": ["logs.all.count_visits"],
                    "filters": {
                        "field": "logs.all.count_visits", 
                        "predicate": "gt", 
                        "value": 0
                    }
                }
            }
            
            # Define the lightweight check query for weblog data
            check_query_payload = {
                "collections": ["logs"],
                "periods": [[start_date, end_date]],
                "query": {
                    "dimensions": [],
                    "metrics": [{"function": "count", "args": ["logs.url"]}],
                    "filters": {
                        "field": "logs.all.count_visits", 
                        "predicate": "gt", 
                        "value": 0
                    }
                }
            }

        else:
            raise ValueError(f"Unknown data type: {data_type}")

        # Construct the export job payload - critical to follow correct nesting structure
        export_job_payload = {
            "job_type": "export",
            "payload": {
                "username": username,
                "project": project_name,
                "connector": "direct_download",
                "formatter": "csv",
                "export_size": 1000000,
                "query": bql_query,
                "formatter_config": {"print_header": True}
            }
        }

        # Return all query components
        return {
            "check_query_payload": check_query_payload,
            "check_url": f"/v1/projects/{username}/{project_name}/query",
            "export_job_payload": export_job_payload,
            "export_url": "/v1/jobs",
            "data_type": data_type
        }

    async def poll_job_status(self, job_url, api_token, max_attempts=20):
        """
        Poll the job status URL to check for completion with improved error handling
        
        Args:
            job_url: Full job URL to poll
            api_token: Botify API token
            max_attempts: Maximum number of polling attempts
            
        Returns:
            Tuple of (success, result_dict_or_error_message)
        """
        
        attempt = 0
        delay = 2  # Start with 2 second delay
        consecutive_network_errors = 0
        
        # Force full absolute URL with hostname
        if not job_url.startswith('https://api.botify.com'):
            # If it's a relative path starting with /
            if job_url.startswith('/'):
                job_url = f"https://api.botify.com{job_url}"
            # If it's just a job ID
            elif job_url.isdigit():
                job_url = f"https://api.botify.com/v1/jobs/{job_url}"
            # Otherwise assume it might be a path segment without leading /
            else:
                job_url = f"https://api.botify.com/{job_url}"
        
        # Extract job ID for backup approach
        job_id = None
        try:
            parts = job_url.strip('/').split('/')
            if 'jobs' in parts:
                job_id_index = parts.index('jobs') + 1
                if job_id_index < len(parts):
                    job_id = parts[job_id_index]
        except Exception:
            pass
            
        logging.info(f"Starting polling for job: {job_url}" + (f" (ID: {job_id})" if job_id else ""))
        
        while attempt < max_attempts:
            try:
                logging.info(f"Polling job status (attempt {attempt+1}/{max_attempts}): {job_url}")
                
                # If we have had network errors and we have a job ID, reconstruct the URL
                if consecutive_network_errors >= 2 and job_id:
                    alternative_url = f"https://api.botify.com/v1/jobs/{job_id}"
                    if alternative_url != job_url:
                        logging.info(f"Switching to direct job ID URL: {alternative_url}")
                        job_url = alternative_url
                
                async with httpx.AsyncClient(timeout=45.0) as client:  # Increased timeout
                    response = await client.get(
                        job_url, 
                        headers={"Authorization": f"Token {api_token}"}
                    )
                    
                    # Successful request resets network error counter
                    consecutive_network_errors = 0
                    
                    # Log the raw response for debugging
                    try:
                        response_json = response.json()
                        logging.info(f"Poll response: {json.dumps(response_json, indent=2)}")
                    except:
                        logging.info(f"Could not parse response as JSON. Status: {response.status_code}, Raw: {response.text[:500]}")
                    
                    if response.status_code == 401:
                        logging.error("Authentication error (401) during polling")
                        return False, "Authentication failed. Please check your API token."
                        
                    # Handle other error codes
                    if response.status_code >= 400:
                        logging.error(f"Error response {response.status_code} during polling: {response.text}")
                        return False, f"API error {response.status_code}: {response.text}"
                        
                    job_data = response.json()
                    status = job_data.get('job_status')
                    
                    logging.info(f"Poll attempt {attempt+1}: status={status}")
                    
                    if status == 'DONE':
                        # Capture all metadata
                        results = job_data.get('results', {})
                        return True, {
                            "download_url": results.get("download_url"),
                            "row_count": results.get("row_count"),
                            "file_size": results.get("file_size"), 
                            "filename": results.get("filename"),
                            "expires_at": results.get("expires_at")
                        }
                        
                    if status == 'FAILED':
                        error_details = job_data.get('error', {})
                        error_message = error_details.get('message', 'Unknown error')
                        error_type = error_details.get('type', 'Unknown type')
                        logging.error(f"Job failed with error type: {error_type}, message: {error_message}")
                        return False, f"Export failed: {error_message} (Type: {error_type})"
                        
                    # Still processing
                    attempt += 1
                    await asyncio.sleep(delay)
                    delay = min(delay * 1.5, 20)  # Exponential backoff, but cap at 20 seconds
                    
            except (httpx.RequestError, socket.gaierror, socket.timeout) as e:
                # Network errors - retry with backoff
                consecutive_network_errors += 1
                logging.error(f"Network error polling job status: {str(e)}")
                
                # Try to extract job ID and rebuild URL no matter what on network errors
                if job_id:
                    job_url = f"https://api.botify.com/v1/jobs/{job_id}"
                    logging.warning(f"Retry with direct job ID URL: {job_url}")
                
                attempt += 1
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)  # Longer backoff for network errors, cap at 30 seconds
                
            except Exception as e:
                logging.exception(f"Unexpected error in polling: {str(e)}")
                attempt += 1
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)
                
        return False, "Maximum polling attempts reached. The export job may still complete in the background."

    async def step_02_process(self, request):
        """Process the actual download after showing the progress indicator."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_02"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Get form data
        form = await request.form()
        analysis_slug = form.get("analysis_slug", "").strip()
        username = form.get("username", "").strip()
        project_name = form.get("project_name", "").strip()
        
        if not all([analysis_slug, username, project_name]):
            return P("Error: Missing required parameters", style=pip.get_style("error"))
        
        # Get the current state
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        analysis_result_str = step_data.get(step.done, "")
        analysis_result = json.loads(analysis_result_str) if analysis_result_str else {}
        
        try:
            # Determine file path for this export
            crawl_filepath = await self.get_deterministic_filepath(username, project_name, analysis_slug, "crawl")
            
            # All the existing download code goes here, same as before
            # [... existing download code ...]
            
            # Check if file already exists
            file_exists, file_info = await self.check_file_exists(crawl_filepath)
            
            if file_exists:
                # File already exists, skip the export
                await self.message_queue.add(pip, f"✓ Found existing crawl data from {file_info['created']}", verbatim=True)
                await self.message_queue.add(pip, f"ℹ️ Using cached file: {file_info['path']} ({file_info['size']})", verbatim=True)
                
                # Update analysis result with existing file info
                analysis_result.update({
                    "download_complete": True,
                    "download_info": {
                        "has_file": True,
                        "file_path": crawl_filepath,
                        "timestamp": file_info['created'],
                        "size": file_info['size'],
                        "cached": True
                    }
                })
            else:
                # Need to perform the export and download
                await self.message_queue.add(pip, "🔄 Initiating crawl data export...", verbatim=True)
                
                # Get API token
                api_token = self.read_api_token()
                if not api_token:
                    raise ValueError("Cannot read API token")
                
                # Calculate period dates - use 30 days before analysis date
                # Parse analysis date from slug (assuming format YYYYMMDD)
                try:
                    analysis_date_obj = datetime.strptime(analysis_slug, "%Y%m%d")
                except ValueError:
                    # If not in expected format, use current date as fallback
                    analysis_date_obj = datetime.now()

                # Calculate period start (30 days before analysis date)
                period_start = (analysis_date_obj - timedelta(days=30)).strftime("%Y-%m-%d")
                period_end = analysis_date_obj.strftime("%Y-%m-%d")

                # Successful working query with compliance reasons added
                export_query = {
                    "job_type": "export",
                    "payload": {
                        "username": username,
                        "project": project_name,
                        "connector": "direct_download",
                        "formatter": "csv",
                        "export_size": 10000,
                        "query": {
                            "collections": [
                                f"crawl.{analysis_slug}"
                            ],
                            "query": {
                                "dimensions": [
                                    f"crawl.{analysis_slug}.url",
                                    f"crawl.{analysis_slug}.compliant.main_reason",
                                    f"crawl.{analysis_slug}.compliant.detailed_reason"
                                ],
                                "metrics": [
                                    {"function": "count", "args": [f"crawl.{analysis_slug}.url"]}
                                ],
                                "filters": {
                                    "field": f"crawl.{analysis_slug}.compliant.is_compliant",
                                    "value": False
                                }
                            }
                        }
                    }
                }
                
                # Submit export job
                job_url = "https://api.botify.com/v1/jobs"
                headers = {
                    "Authorization": f"Token {api_token}",
                    "Content-Type": "application/json"
                }
                
                logging.info(f"Submitting crawl export job with payload: {json.dumps(export_query, indent=2)}")
                
                async with httpx.AsyncClient() as client:
                    try:
                        response = await client.post(
                            job_url, 
                            headers=headers, 
                            json=export_query,
                            timeout=60.0
                        )
                        
                        # If there's an error, try to get more detailed error info
                        if response.status_code >= 400:
                            error_detail = "Unknown error"
                            try:
                                error_body = response.json()
                                error_detail = json.dumps(error_body, indent=2)
                                logging.error(f"API error details: {error_detail}")
                            except Exception:
                                error_detail = response.text[:500]
                                logging.error(f"API error text: {error_detail}")
                                
                            response.raise_for_status()
                            
                        job_data = response.json()
                        
                        # Get job URL
                        job_url_path = job_data.get('job_url')
                        if not job_url_path:
                            raise ValueError("Failed to get job URL from response")
                            
                        full_job_url = f"https://api.botify.com{job_url_path}"
                        
                        # Export initiated message
                        await self.message_queue.add(pip, "✓ Crawl export job created successfully!", verbatim=True)
                        await self.message_queue.add(pip, "🔄 Polling for export completion...", verbatim=True)
                    
                    except httpx.HTTPStatusError as e:
                        await self.message_queue.add(pip, f"❌ Export request failed: HTTP {e.response.status_code}", verbatim=True)
                        raise
                    except Exception as e:
                        await self.message_queue.add(pip, f"❌ Export request failed: {str(e)}", verbatim=True)
                        raise
                
                # Poll for completion
                success, result = await self.poll_job_status(full_job_url, api_token)
                
                if not success:
                    error_message = isinstance(result, str) and result or "Export job failed"
                    await self.message_queue.add(pip, f"❌ Export failed: {error_message}", verbatim=True)
                    raise ValueError(f"Export failed: {error_message}")
                
                # Export ready message
                await self.message_queue.add(pip, "✓ Export completed and ready for download!", verbatim=True)
                
                # Download the file
                download_url = result.get("download_url")
                if not download_url:
                    await self.message_queue.add(pip, "❌ No download URL found in job result", verbatim=True)
                    raise ValueError("No download URL found in job result")
                
                # Downloading message
                await self.message_queue.add(pip, "🔄 Downloading crawl data...", verbatim=True)
                
                # Make sure target directory exists
                await self.ensure_directory_exists(crawl_filepath)
                
                # Download and decompress the gzipped CSV file
                try:
                    # Create temporary gzipped file path
                    gz_filepath = f"{crawl_filepath}.gz"
                    
                    # Step 1: Download the gzipped CSV file with increased timeout
                    async with httpx.AsyncClient(timeout=300.0) as client:
                        async with client.stream("GET", download_url, headers={"Authorization": f"Token {api_token}"}) as response:
                            response.raise_for_status()
                            with open(gz_filepath, 'wb') as gz_file:
                                async for chunk in response.aiter_bytes():
                                    gz_file.write(chunk)
                    
                    # Step 2: Decompress the .gz file to .csv
                    with gzip.open(gz_filepath, "rb") as f_in:
                        with open(crawl_filepath, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # Clean up the temporary gzipped file
                    os.remove(gz_filepath)
                    
                    # Get info about the created file
                    _, file_info = await self.check_file_exists(crawl_filepath)
                    
                    # Download complete message
                    await self.message_queue.add(pip, f"✓ Download complete: {file_info['path']} ({file_info['size']})", verbatim=True)

                    # Load into DataFrame and add column headers
                    df = pd.read_csv(crawl_filepath)
                    df.columns = ["url", "compliant_main_reason", "compliant_detailed_reason", "count"]
                    # Add column headers
                    df.columns = ["url", "compliant_main_reason", "compliant_detailed_reason", "count"]
                    # Save to CSV with headers
                    df.to_csv(crawl_filepath, index=False)
                    
                    # Create download info for storage
                    download_info = {
                        "has_file": True,
                        "file_path": crawl_filepath,
                        "timestamp": file_info['created'],
                        "size": file_info['size'],
                        "cached": False
                    }
                    
                    # Update analysis result with download info
                    analysis_result.update({
                        "download_complete": True,
                        "download_info": download_info
                    })
                    
                except httpx.ReadTimeout as e:
                    await self.message_queue.add(pip, f"❌ Timeout error during file download: {str(e)}", verbatim=True)
                    raise
                except Exception as e:
                    await self.message_queue.add(pip, f"❌ Error downloading or decompressing file: {str(e)}", verbatim=True)
                    raise
            
            # Final message for completed download
            await self.message_queue.add(pip, "✓ Crawl data ready for analysis!", verbatim=True)
            
            # Update state with complete analysis info including download results
            analysis_result_str = json.dumps(analysis_result)
            await pip.update_step_state(pipeline_id, step_id, analysis_result_str, steps)
            
            # Return the completed view
            return Div(
                pip.revert_control(
                    step_id=step_id, 
                    app_name=app_name, 
                    message=f"{step.show}: {analysis_slug} (data downloaded)",
                    steps=steps
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        
        except Exception as e:
            logging.exception(f"Error in step_02_process: {e}")
            
            # Return error message
            return P(f"Error: {str(e)}", style=pip.get_style("error"))

    async def step_03_process(self, request):
        """Process the web logs check and download if available."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_03"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Get form data
        form = await request.form()
        analysis_slug = form.get("analysis_slug", "").strip()
        username = form.get("username", "").strip()
        project_name = form.get("project_name", "").strip()
        
        if not all([analysis_slug, username, project_name]):
            return P("Error: Missing required parameters", style=pip.get_style("error"))
        
        try:
            # Perform the check for web logs
            has_logs, error_message = await self.check_if_project_has_collection(username, project_name, "logs")
            
            if error_message:
                return P(f"Error: {error_message}", style=pip.get_style("error"))
            
            # Store the check result
            check_result = {
                "has_logs": has_logs,
                "project": project_name,
                "username": username,
                "analysis_slug": analysis_slug,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add message
            status_text = "HAS" if has_logs else "does NOT have"
            await self.message_queue.add(pip, f"{step.show} complete: Project {status_text} web logs", verbatim=True)
            
            # If logs exist, download them
            if has_logs:
                # Determine file path
                logs_filepath = await self.get_deterministic_filepath(username, project_name, analysis_slug, "weblog")
                
                # Check if file already exists
                file_exists, file_info = await self.check_file_exists(logs_filepath)
                
                if file_exists:
                    # File already exists, skip the export
                    await self.message_queue.add(pip, f"✓ Found existing web logs data from {file_info['created']}", verbatim=True)
                    await self.message_queue.add(pip, f"ℹ️ Using cached file: {file_info['path']} ({file_info['size']})", verbatim=True)
                    
                    # Update check result with existing file info
                    check_result.update({
                        "download_complete": True,
                        "download_info": {
                            "has_file": True,
                            "file_path": logs_filepath,
                            "timestamp": file_info['created'],
                            "size": file_info['size'],
                            "cached": True
                        }
                    })
                else:
                    # Need to export and download web logs
                    await self.message_queue.add(pip, "🔄 Initiating web logs export...", verbatim=True)
                    
                    # Get API token
                    api_token = self.read_api_token()
                    if not api_token:
                        raise ValueError("Cannot read API token")
                    
                    # Calculate date range (30 days before analysis date)
                    try:
                        analysis_date_obj = datetime.strptime(analysis_slug, "%Y%m%d")
                    except ValueError:
                        analysis_date_obj = datetime.now()
                    
                    date_end = analysis_date_obj.strftime("%Y-%m-%d")
                    date_start = (analysis_date_obj - timedelta(days=30)).strftime("%Y-%m-%d")
                    
                    # Build logs export query following the provided model
                    export_query = {
                        "job_type": "logs_urls_export",
                        "payload": {
                            "query": {
                                "filters": {
                                    "field": "crawls.google.count",
                                    "predicate": "gt",
                                    "value": 0
                                },
                                "fields": [
                                    "url",
                                    "crawls.google.count"
                                ],
                                "sort": [
                                    {
                                        "crawls.google.count": {
                                            "order": "desc"
                                        }
                                    }
                                ]
                            },
                            "export_size": 1000000,
                            "formatter": "csv",
                            "connector": "direct_download",
                            "formatter_config": {
                                "print_header": True,
                                "print_delimiter": True
                            },
                            "extra_config": {
                                "compression": "zip"
                            },
                            "date_start": date_start,
                            "date_end": date_end,
                            "username": username,
                            "project": project_name
                        }
                    }
                    
                    # Submit export job
                    job_url = "https://api.botify.com/v1/jobs"
                    headers = {
                        "Authorization": f"Token {api_token}",
                        "Content-Type": "application/json"
                    }
                    
                    logging.info(f"Submitting logs export job with payload: {json.dumps(export_query, indent=2)}")
                    job_id = None
                    
                    async with httpx.AsyncClient() as client:
                        try:
                            response = await client.post(
                                job_url, 
                                headers=headers, 
                                json=export_query,
                                timeout=60.0
                            )
                            
                            # If there's an error, try to get more detailed error info
                            if response.status_code >= 400:
                                error_detail = "Unknown error"
                                try:
                                    error_body = response.json()
                                    error_detail = json.dumps(error_body, indent=2)
                                    logging.error(f"API error details: {error_detail}")
                                except Exception:
                                    error_detail = response.text[:500]
                                    logging.error(f"API error text: {error_detail}")
                                    
                                response.raise_for_status()
                                
                            job_data = response.json()
                            
                            # Get job URL and extract job ID directly
                            job_url_path = job_data.get('job_url')
                            if not job_url_path:
                                raise ValueError("Failed to get job URL from response")
                                
                            # Extract job ID from URL path (e.g., /v1/jobs/12345 -> 12345)
                            job_id = job_url_path.strip('/').split('/')[-1]
                            if not job_id:
                                raise ValueError("Failed to extract job ID from job URL")
                                
                            # Rather than use the relative URL, build the absolute URL with job ID
                            full_job_url = f"https://api.botify.com/v1/jobs/{job_id}"
                            
                            # Export initiated message
                            await self.message_queue.add(pip, f"✓ Web logs export job created successfully! (Job ID: {job_id})", verbatim=True)
                            await self.message_queue.add(pip, "🔄 Polling for export completion...", verbatim=True)
                        
                        except httpx.HTTPStatusError as e:
                            await self.message_queue.add(pip, f"❌ Export request failed: HTTP {e.response.status_code}", verbatim=True)
                            raise
                        except Exception as e:
                            await self.message_queue.add(pip, f"❌ Export request failed: {str(e)}", verbatim=True)
                            raise
                    
                    # Poll for completion using the job ID approach if we have it
                    if job_id:
                        await self.message_queue.add(pip, f"Using job ID {job_id} for polling", verbatim=True)
                        full_job_url = f"https://api.botify.com/v1/jobs/{job_id}"
                        
                    # Polling with direct absolute URL approach
                    success, result = await self.poll_job_status(full_job_url, api_token)
                    
                    if not success:
                        error_message = isinstance(result, str) and result or "Export job failed"
                        await self.message_queue.add(pip, f"❌ Export failed: {error_message}", verbatim=True)
                        raise ValueError(f"Export failed: {error_message}")
                    
                    # Export ready message
                    await self.message_queue.add(pip, "✓ Export completed and ready for download!", verbatim=True)
                    
                    # Download the file
                    download_url = result.get("download_url")
                    if not download_url:
                        await self.message_queue.add(pip, "❌ No download URL found in job result", verbatim=True)
                        raise ValueError("No download URL found in job result")
                    
                    # Downloading message
                    await self.message_queue.add(pip, "🔄 Downloading web logs data...", verbatim=True)
                    
                    # Make sure target directory exists
                    await self.ensure_directory_exists(logs_filepath)
                    
                    # Download and extract zip/gzip file properly
                    try:
                        # Make a temporary file path for the compressed file
                        compressed_path = f"{logs_filepath}.compressed"
                        
                        # Download the compressed file first
                        async with httpx.AsyncClient() as client:
                            async with client.stream("GET", download_url, headers={"Authorization": f"Token {api_token}"}) as response:
                                response.raise_for_status()
                                with open(compressed_path, 'wb') as f:
                                    async for chunk in response.aiter_bytes():
                                        f.write(chunk)
                        
                        # Check what kind of compressed file we have
                        
                        # Try to open as gzip first (safer approach)
                        try:
                            # Try to open and extract gzip
                            with gzip.open(compressed_path, 'rb') as f_in:
                                with open(logs_filepath, 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                            logging.info(f"Successfully extracted gzip file to {logs_filepath}")
                            
                        except gzip.BadGzipFile:
                            # Not a gzip, try ZIP
                            try:
                                with zipfile.ZipFile(compressed_path, 'r') as zip_ref:
                                    # Get the first CSV file
                                    csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]
                                    if not csv_files:
                                        raise ValueError("No CSV files found in the zip archive")
                                    
                                    # Extract the CSV file to our target path
                                    with zip_ref.open(csv_files[0]) as source:
                                        with open(logs_filepath, 'wb') as target:
                                            shutil.copyfileobj(source, target)
                                logging.info(f"Successfully extracted zip file to {logs_filepath}")
                                
                            except zipfile.BadZipFile:
                                # Not a zip either, just move the file as-is (it might be a direct CSV)
                                shutil.copy(compressed_path, logs_filepath)
                                logging.info(f"File doesn't appear to be compressed, copying directly to {logs_filepath}")
                        
                        # Clean up the compressed file
                        if os.path.exists(compressed_path):
                            os.remove(compressed_path)
                        
                        # Get info about the created file
                        _, file_info = await self.check_file_exists(logs_filepath)
                        
                        # Download complete message
                        await self.message_queue.add(pip, f"✓ Download complete: {file_info['path']} ({file_info['size']})", verbatim=True)
                        
                    except Exception as e:
                        await self.message_queue.add(pip, f"❌ Error downloading file: {str(e)}", verbatim=True)
                        raise
                
                # Final message
                await self.message_queue.add(pip, "✓ Web logs data ready for analysis!", verbatim=True)
            
            # Convert to JSON for storage
            check_result_str = json.dumps(check_result)
            
            # Store in state
            await pip.update_step_state(pipeline_id, step_id, check_result_str, steps)
            
            # Return result display
            status_color = "green" if has_logs else "red"
            download_message = ""
            if has_logs:
                download_message = " (data downloaded)"
            
            return Div(
                pip.revert_control(
                    step_id=step_id, 
                    app_name=app_name, 
                    message=f"{step.show}: Project {status_text} web logs{download_message}",
                    steps=steps
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
            
        except Exception as e:
            logging.exception(f"Error in step_03_process: {e}")
            
            # Return error message
            return P(f"Error: {str(e)}", style=pip.get_style("error"))

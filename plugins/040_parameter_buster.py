import asyncio
import asyncio
from collections import namedtuple, Counter
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
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
import pickle
from pathlib import Path

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
    Parameter Buster Workflow
    
    A comprehensive workflow that analyzes URL parameters from multiple data sources (Botify crawls, 
    web logs, and Search Console) to identify optimization opportunities. This workflow demonstrates:

    - Multi-step form collection with chain reaction progression
    - Data fetching from external APIs with proper retry and error handling
    - File caching and management for large datasets
    - Background processing with progress indicators
    - Complex data analysis with pandas

    IMPORTANT: This workflow implements the standard chain reaction pattern where steps trigger 
    the next step via explicit `hx_trigger="load"` statements. See Step Flow Pattern below.

    ## Step Flow Pattern
    Each step follows this pattern for reliable chain reaction:
    1. GET handler returns a div containing the step UI plus an empty div for the next step
    2. SUBMIT handler returns a revert control plus explicit next step trigger:
       `Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")`

    ## Key Implementation Notes
    - Background tasks use Script tags with htmx.ajax for better UX during long operations
    - File paths are deterministic based on username/project/analysis to enable caching
    - All API errors are handled with specific error messages for better troubleshooting
    """
    # --- Workflow Configuration ---
    APP_NAME = "param_buster"              # Unique identifier for this workflow's routes and data
    DISPLAY_NAME = "Parameter Buster" # User-friendly name shown in the UI
    ENDPOINT_MESSAGE = (            # Message shown on the workflow's landing page
        "This workflow analyzes URL parameters from Botify, Web Logs, and Search Console data "
        "to produce a PageWorkers optimization for better crawl efficiency. "
        "Click Enter to start."
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
        # PATTERN NOTE: Each step is registered with both a display handler (step_XX) and 
        # a submission handler (step_XX_submit). Additional specialized routes may be added
        # for background processing (step_XX_process) or completion handling (step_XX_complete)
        steps = [
            Step(
                id='step_01',
                done='botify_project',        # Field to store the project data
                show='Botify Project URL',    # User-friendly name
                refill=True,                  # Allow refilling for better UX
            ),
            Step(
                id='step_02',                 
                done='analysis_selection',    
                show='Download Crawl Analysis',  # Changed from "Select Analysis"
                refill=False,
            ),
            Step(
                id='step_03',                 
                done='weblogs_check',         # Store the check result
                show='Download Web Logs',    # Changed from "Check Web Logs"
                refill=False,
            ),
            Step(
                id='step_04',                 
                done='search_console_check',  # Store the Search Console check result
                show='Download Search Console',  # Changed from "Check Search Console"
                refill=False,
            ),
            Step(
                id='step_05',
                done='placeholder',
                show='Analyze Parameters',
                refill=True,
            ),
            Step(
                id='step_06',
                done='parameter_optimization',
                show='Parameter Optimization',
                refill=True,
            ),
            Step(
                id='step_07',
                done='robots_txt',
                show='Instructions & robots.txt',
                refill=True,
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
            (f"/{app_name}/parameter_preview", self.parameter_preview, ["POST"]),
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

        # Add the step_05_process route
        routes.append((f"/{app_name}/step_05_process", self.step_05_process, ["POST"]))  # Add this line

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
                "input": f"{pip.fmt('step_02')}: Please select a crawl analysis for this project.",
                "complete": "Crawl analysis download complete. Continue to next step."
            },
            "step_06": {
                "input": f"{pip.fmt('step_06')}: Please enter JavaScript code for syntax highlighting.",
                "complete": "Code syntax highlighting complete. Ready to finalize."
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

        # Add specific message for step_05 (Analyze Parameters)
        self.step_messages["step_05"] = {
            "input": f"{pip.fmt('step_05')}: Please analyze the parameters.",
            "complete": "Parameter analysis complete. Ready to finalize."
        }

        # Add the finalize step internally
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

    # --- Core Workflow Engine Methods ---

    async def landing(self):
        """Renders the initial landing page with the key input form or a message if Botify token is missing."""
        pip, pipeline, steps, app_name = self.pipulate, self.pipeline, self.steps, self.app_name
        title = f"{self.DISPLAY_NAME or app_name.title()}"
        
        # Check if botify_token.txt exists
        token_exists = os.path.exists("botify_token.txt")
        
        # If token doesn't exist, show message about needing to connect with Botify first
        if not token_exists:
            return Container(
                Card(
                    H2(title),
                    P(self.ENDPOINT_MESSAGE, style="font-size: 0.9em; color: #666;"),
                    Div(
                        H3("Botify Connection Required", style="color: #e74c3c;"),
                        P("To use the Parameter Buster workflow, you must first connect with Botify.", style="margin-bottom: 10px;"),
                        P("Please run the \"Connect With Botify\" workflow to set up your Botify API token.", style="margin-bottom: 20px;"),
                        P("Once configured, you can return to this workflow.", style="font-style: italic; color: #666;")
                    )
                ),
                Div(id=f"{app_name}-container")
            )
        
        # Otherwise, show the normal key input form
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
        """Handles GET request to show Finalize button and POST request to lock the workflow.
        
        # PATTERN NOTE: The finalize step is the final destination of the chain reaction
        # and should be triggered by the last content step's submit handler.
        """
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
        
        # STEP PATTERN: GET handler returns current step UI + empty placeholder for next step
        # Important: The next step div should NOT have hx_trigger here, only in the submit handler
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
                    Small(
                        "Example: ",
                        Span(
                            "https://app.botify.com/uhnd-com/uhnd.com-demo-account/", 
                            id="copy-example-url",
                            style="cursor: pointer; color: #888; text-decoration: none;",
                            hx_on_click="document.querySelector('input[name=\"botify_url\"]').value = this.innerText; this.style.color = '#28a745'; setTimeout(() => this.style.color = '#888', 1000)",
                            title="Click to use this example URL"
                        ),
                        style="display: block; margin-bottom: 10px; color: #666; font-style: italic;"
                    ),
                    Form(
                        Input(
                            type="url", 
                            name="botify_url", 
                            placeholder="https://app.botify.com/org/project/", 
                            value=display_value,
                            required=True,
                            pattern="https://(app|analyze)\\.botify\\.com/[^/]+/[^/]+/[^/]+.*",
                            style="width: 100%;"
                        ),
                        Div(
                            Button("Use this URL ▸", type="submit", cls="primary"),
                            style="margin-top: 1vh; text-align: right;"
                        ),
                        hx_post=f"/{app_name}/{step_id}_submit", 
                        hx_target=f"#{step_id}"
                    )
                ),
                Div(id=next_step_id),  # Empty placeholder for next step - NO hx_trigger here
                id=step_id
            )

    async def step_01_submit(self, request):
        """Process the submission for Botify URL input widget.
        
        # STEP PATTERN: Submit handler stores state and returns:
        # 1. Revert control for the completed step
        # 2. Next step div with explicit hx_trigger="load" to chain reaction to next step
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
                        Button("Download Crawl Analysis ▸", type="submit", cls="primary", style="margin-top: 10px;"),
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
                    P(f"Download Web Logs for '{project_name}'"),
                    P(f"Organization: {username}", style="color: #666; font-size: 0.9em;"),
                    Form(
                        Button("Download Web Logs ▸", type="submit", cls="primary"),
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
        await self.message_queue.add(pip, f"Downloading Web Logs for '{project_name}'...", verbatim=True)
        
        # Return the progress indicator immediately
        return Card(
            H3(f"{step.show}"),
            P(f"Downloading Web Logs for '{project_name}'..."),
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
                    P(f"Download Search Console data for '{project_name}'"),
                    P(f"Organization: {username}", style="color: #666; font-size: 0.9em;"),
                    Form(
                        Button("Download Search Console ▸", type="submit", cls="primary"),
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
            P(f"Downloading Search Console data for '{project_name}'..."),
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
        """Handles GET request for Parameter Optimization Generation."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_05"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        optimization_result = step_data.get(step.done, "")

        # Get param_count from the stored data if it exists
        param_count = "40"  # Default value
        if optimization_result:
            try:
                result_data = json.loads(optimization_result)
                param_count = str(result_data.get("param_count", 40))
            except json.JSONDecodeError:
                pass

        # Get required data from previous steps
        project_data = pip.get_step_data(pipeline_id, "step_01", {}).get("botify_project", "{}")
        analysis_data = pip.get_step_data(pipeline_id, "step_02", {}).get("analysis_selection", "{}")
        
        try:
            project_info = json.loads(project_data)
            analysis_info = json.loads(analysis_data)
        except json.JSONDecodeError:
            return P("Error: Could not load project or analysis data", style=pip.get_style("error"))

        username = project_info.get("username")
        project_name = project_info.get("project_name")
        analysis_slug = analysis_info.get("analysis_slug")

        if not all([username, project_name, analysis_slug]):
            return P("Error: Missing required project information", style=pip.get_style("error"))

        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and optimization_result:
            try:
                # Create visualization placeholder for locked state
                visualization_widget = self.create_parameter_visualization_placeholder(optimization_result)
                
                return Div(
                    Card(
                        H3(f"🔒 {step.show}"),
                        visualization_widget
                    ),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                    id=step_id
                )
            except Exception as e:
                logging.error(f"Error creating parameter visualization in finalized view: {str(e)}")
                return Div(
                    Card(
                        H3(f"🔒 {step.show}"),
                        P("Parameter optimization completed", style="margin-bottom: 10px;"),
                        Div(
                            P(f"Analysis data is locked."),
                            style="padding: 10px; background: var(--pico-card-background-color); border-radius: 5px;"
                        )
                    ),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                    id=step_id
                )

        # Check if step is complete and not being reverted to
        if optimization_result and state.get("_revert_target") != step_id:
            try:
                # Create visualization placeholder for revert state
                visualization_widget = self.create_parameter_visualization_placeholder(optimization_result)
                
                # Use the widget_container instead of revert_control to display the widget properly
                return Div(
                    pip.widget_container(
                        step_id=step_id,
                        app_name=app_name,
                        message=f"{step.show}: {json.loads(optimization_result).get('total_unique_parameters', 0):,} unique parameters found",
                        widget=visualization_widget,
                        steps=steps
                    ),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                    id=step_id
                )
            except Exception as e:
                logging.error(f"Error creating parameter visualization in revert view: {str(e)}")
                # Fall back to original revert control without widget
                return Div(
                    pip.revert_control(
                        step_id=step_id,
                        app_name=app_name,
                        message=f"{step.show}: Parameter analysis complete",
                        steps=steps
                    ),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                    id=step_id
                )

        # Show the analysis form with the previously selected param_count if refilling
        await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
        
        return Div(
            Card(
                H3(f"{step.show}"),
                P("Create counters for querystring parameters for each of the following:", style="margin-bottom: 15px;"),
                Ul(
                    Li("Crawl data from Botify analysis"),
                    Li("Search Console performance data"),
                    Li("Web logs data (if available)"),
                    style="margin-bottom: 15px;"
                ),
                Form(
                    Div(
                        Label(
                            NotStr("<strong>Number of Parameters to Show:</strong>"), 
                            For="param_count",
                            style="min-width: 220px;"
                        ),
                        Input(
                            type="range", 
                            name="param_count_slider", 
                            id="param_count_slider", 
                            value=param_count, 
                            min="10", 
                            max="100", 
                            step="5",
                            style="flex-grow: 1; margin: 0 10px;",
                            _oninput="document.getElementById('param_count').value = this.value;"
                        ),
                        Input(
                            type="number", 
                            name="param_count", 
                            id="param_count", 
                            value=param_count, 
                            min="10", 
                            max="100", 
                            step="5",
                            style="width: 100px;",  # Increased width to accommodate arrows
                            _oninput="document.getElementById('param_count_slider').value = this.value;",
                            _onkeydown="if(event.key === 'Enter') { event.preventDefault(); return false; }"
                        ),
                        style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;"
                    ),
                    Button(
                        "Analyze Parameters ▸",  # Removed the NotStr("<strong>...</strong>")
                        type="submit", 
                        cls="primary"
                    ),
                    # Add this script at the beginning of the form to ensure triggerParameterPreview is available globally
                    Script('''
                    // Define triggerParameterPreview in the global scope
                    window.triggerParameterPreview = function() {
                        // Use HTMX to manually trigger the parameter preview
                        htmx.trigger('#parameter-preview', 'htmx:beforeRequest');
                        htmx.ajax('POST', 
                            window.location.pathname.replace('step_06', 'parameter_preview'), 
                            {
                                target: '#parameter-preview',
                                values: {
                                    'gsc_threshold': document.getElementById('gsc_threshold').value,
                                    'min_frequency': document.getElementById('min_frequency').value
                                }
                            }
                        );
                    };
                    '''),
                    hx_post=f"/{app_name}/{step_id}_submit",
                    hx_target=f"#{step_id}",
                    _onsubmit="if(event.submitter !== document.querySelector('button[type=\"submit\"]')) { event.preventDefault(); return false; }",
                    _onkeydown="if(event.key === 'Enter') { event.preventDefault(); return false; }"
                ),
                Script('''
                function triggerParameterPreview() {
                    // Use HTMX to manually trigger the parameter preview
                    htmx.trigger('#parameter-preview', 'htmx:beforeRequest');
                    htmx.ajax('POST', document.querySelector('input[name="gsc_threshold"]').form.getAttribute('hx-post').replace('step_06_submit', 'parameter_preview'), {
                        target: '#parameter-preview',
                        values: {
                            'gsc_threshold': document.getElementById('gsc_threshold').value,
                            'min_frequency': document.getElementById('min_frequency').value
                        }
                    });
                }
                ''')
            ),
            Div(id=next_step_id),
            id=step_id
        )

    async def step_05_submit(self, request):
        """Process the parameter optimization generation.
        
        # BACKGROUND PROCESSING PATTERN: This demonstrates the standard pattern for long-running operations:
        # 1. Return progress UI immediately
        # 2. Use Script tag with setTimeout + htmx.ajax to trigger background processing
        # 3. Background processor updates state and returns completed UI with next step trigger
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_05"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")

        # Get the param_count from the form
        form = await request.form()
        param_count = form.get("param_count", "40")

        # First, return a progress indicator immediately
        return Card(
            H3(f"{step.show}"),
            P("Analyzing parameters...", style="margin-bottom: 15px;"),
            Progress(style="margin-top: 10px;"),
            Script("""
            setTimeout(function() {
                htmx.ajax('POST', '""" + f"/{app_name}/step_05_process" + """', {
                    target: '#""" + step_id + """',
                    values: { 
                        'pipeline_id': '""" + pipeline_id + """',
                        'param_count': '""" + param_count + """'
                    }
                });
            }, 500);
            """),
            id=step_id
        )

    async def step_05_process(self, request):
        """Process parameter analysis using raw parameter counting and caching."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_05"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        
        # Get pipeline_id and param_count from form data
        form = await request.form()
        pipeline_id = form.get("pipeline_id", "unknown")
        param_count = int(form.get("param_count", "40"))

        # Get required data from previous steps
        project_data = pip.get_step_data(pipeline_id, "step_01", {}).get("botify_project", "{}")
        analysis_data = pip.get_step_data(pipeline_id, "step_02", {}).get("analysis_selection", "{}")
        
        try:
            project_info = json.loads(project_data)
            analysis_info = json.loads(analysis_data)
        except json.JSONDecodeError:
            return P("Error: Could not load project or analysis data", style=pip.get_style("error"))

        username = project_info.get("username")
        project_name = project_info.get("project_name")
        analysis_slug = analysis_info.get("analysis_slug")

        if not all([username, project_name, analysis_slug]):
            return P("Error: Missing required project information", style=pip.get_style("error"))

        try:
            # Show a single processing message instead of detailed progress
            await self.message_queue.add(pip, "Analyzing parameters...", verbatim=True)
            
            # Determine data directory
            data_dir = await self.get_deterministic_filepath(username, project_name, analysis_slug)
            cache_filename = "_raw_param_counters_cache.pkl"
            
            # Define which files to process with appropriate names
            files_to_process = {
                "not_indexable": "crawl.csv",  
                "gsc": "gsc.csv",
                "weblogs": "weblog.csv"  
            }
            
            # Try to load from cache first
            cached_data = self.load_raw_counters_from_cache(data_dir, cache_filename)
            
            output_data = None  # Initialize
            
            if cached_data is not None:
                output_data = cached_data
            
            # If cache wasn't loaded or needs recalculation
            if output_data is None:
                output_data = await self.calculate_and_cache_raw_counters(
                    data_directory_path=data_dir,
                    input_files_config=files_to_process,
                    cache_filename=cache_filename
                )
                
                if output_data is None:
                    raise ValueError("Failed to calculate counters from source files")
            
            # Prepare summary data about the raw counters
            raw_counters = output_data.get('raw_counters', {})
            file_statuses = output_data.get('metadata', {}).get('file_statuses', {})
            
            # Create summary information for storage and display
            parameter_summary = {
                'timestamp': datetime.now().isoformat(),
                'data_sources': {},
                'cache_path': str(Path(data_dir) / cache_filename),
                'param_count': param_count  # Store the param_count in the JSON data
            }
            
            # Process each data source for summary
            total_unique_params = set()
            total_occurrences = 0
            
            for source, counter in raw_counters.items():
                unique_params = len(counter)
                source_occurrences = sum(counter.values())
                total_occurrences += source_occurrences
                status = file_statuses.get(source, "Unknown")
                
                parameter_summary['data_sources'][source] = {
                    'unique_parameters': unique_params,
                    'total_occurrences': source_occurrences,
                    'status': status,
                    'top_parameters': [
                        {'name': param, 'count': count}
                        for param, count in counter.most_common(10)
                    ] if counter else []
                }
                
                # Add to set of all unique parameters
                total_unique_params.update(counter.keys())
            
            # Overall statistics
            parameter_summary['total_unique_parameters'] = len(total_unique_params)
            
            # Store the parameter summary
            summary_str = json.dumps(parameter_summary)
            await pip.update_step_state(pipeline_id, step_id, summary_str, steps)

            # Add a single consolidated summary message instead of multiple detailed ones
            await self.message_queue.add(
                pip, 
                f"✓ Parameter analysis complete! Found {len(total_unique_params):,} unique parameters across {len(parameter_summary['data_sources'])} sources with {total_occurrences:,} total occurrences.", 
                verbatim=True
            )
            
            # Create the visualization for the completed state
            visualization_widget = self.create_parameter_visualization_placeholder(summary_str)
            
            # Return the completed view with widget_container instead of revert_control
            return Div(
                pip.widget_container(
                    step_id=step_id,
                    app_name=app_name,
                    message=f"{step.show}: {len(total_unique_params):,} unique parameters found",
                    widget=visualization_widget,
                    steps=steps
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )

        except Exception as e:
            logging.exception(f"Error in step_05_process: {e}")
            return P(f"Error generating optimization: {str(e)}", style=pip.get_style("error"))

    async def step_06(self, request):
        """Handles GET request for the JavaScript Code Display Step."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_06"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "")
        
        # Import these at the beginning of the method so they're available everywhere
        from starlette.responses import HTMLResponse
        from fasthtml.common import to_xml
        
        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and user_val:
            # Show the syntax highlighter in locked state
            try:
                # Generate unique widget ID
                widget_id = f"prism-widget-{pipeline_id.replace('-', '_')}-{step_id}"
                
                # Try to parse as JSON
                try:
                    values = json.loads(user_val)
                    code_to_display = values.get("js_code", "")
                    selected_params = values.get("selected_params", [])
                    gsc_threshold = values.get("gsc_threshold", "0")
                    min_frequency = values.get("min_frequency", "100000")
                except json.JSONDecodeError:
                    # If JSON parsing fails, use the raw value
                    code_to_display = user_val
                    selected_params = []
                    gsc_threshold = "0" 
                    min_frequency = "0"
                
                # Create Prism widget
                prism_widget = self.create_prism_widget(code_to_display, widget_id, 'javascript')
                
                # Create response with widget in locked view
                response = HTMLResponse(
                    to_xml(
                        Div(
                            Card(
                                H3(f"🔒 {step.show}"),
                                P(f"Parameter Optimization with {len(selected_params)} parameters"),
                                prism_widget
                            ),
                            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                            id=step_id
                        )
                    )
                )
                
                # Add HX-Trigger header to initialize Prism highlighting
                response.headers["HX-Trigger"] = json.dumps({
                    "initializePrism": {
                        "targetId": widget_id
                    }
                })
                
                return response
            except Exception as e:
                logging.exception(f"Error creating Prism widget in locked view: {str(e)}")
                return Div(
                    Card(
                        H3(f"🔒 {step.show}"),
                        P("Parameter optimization JavaScript"),
                        Pre(f"JavaScript couldn't be displayed due to an error: {str(e)}")
                    ),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                    id=step_id
                )
            
        # Check if step is complete and not reverting
        if user_val and state.get("_revert_target") != step_id:
            # Create the prism widget from the existing code
            try:
                # Parse the JSON data and get the js_code
                values = None
                try:
                    # Log the raw user_val for debugging
                    logging.info(f"Raw user_val in finalized state: {user_val[:100]}...")
                    
                    # Try to parse JSON
                    values = json.loads(user_val) if user_val else {}
                    
                    # Log the structure
                    logging.info(f"Parsed JSON keys: {list(values.keys())}")
                except json.JSONDecodeError as json_err:
                    logging.error(f"JSON parsing error: {str(json_err)}")
                    # If it's not valid JSON, use as plain text
                    code_to_display = user_val
                    gsc_threshold = "0"
                    min_frequency = "100000"
                    selected_params = []
                else:
                    # Successfully parsed JSON
                    code_to_display = values.get("js_code", "")
                    if not code_to_display and user_val:
                        # If js_code is missing, use the full user_val
                        code_to_display = user_val
                        
                    gsc_threshold = values.get("gsc_threshold", "0")
                    min_frequency = values.get("min_frequency", "100000")
                    selected_params = values.get("selected_params", [])
                
                # Generate unique widget ID for this step and pipeline
                widget_id = f"prism-widget-{pipeline_id.replace('-', '_')}-{step_id}"
                
                # Log lengths for debugging
                logging.info(f"Code length: {len(code_to_display)}, Params count: {len(selected_params) if selected_params else 0}")
                
                # Create Prism widget with the extracted JavaScript code
                prism_widget = self.create_prism_widget(code_to_display, widget_id, 'javascript')
                
                # Use widget_container instead of revert_control
                from starlette.responses import HTMLResponse
                from fasthtml.common import to_xml
                
                response = HTMLResponse(
                    to_xml(
                        Div(
                            pip.widget_container(
                                step_id=step_id,
                                app_name=app_name,
                                message=f"Parameter Optimization with {len(selected_params) if selected_params else 0} parameters",
                                widget=prism_widget,
                                steps=steps
                            ),
                            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                            id=step_id
                        )
                    )
                )
                
                # Add HX-Trigger to initialize Prism highlighting
                response.headers["HX-Trigger"] = json.dumps({
                    "initializePrism": {
                        "targetId": widget_id
                    }
                })
                
                return response
            except Exception as e:
                # If there's an error creating the widget, revert to input form
                logging.error(f"Error creating Prism widget: {str(e)}")
                state["_revert_target"] = step_id
                pip.write_state(pipeline_id, state)
        
        # Get the previous step data to access the parameter cache
        prev_step_data = pip.get_step_data(pipeline_id, "step_05", {})
        prev_data_str = prev_step_data.get("placeholder", "")
        
        # Default values
        gsc_threshold = "0"  # Changed default from 50 to 0
        min_frequency = "100000"  # Default value, will try to calculate better value
        
        # Try to get values from previous input or calculate optimal values
        try:
            # First try to get values from current step if available
            if user_val:
                values = json.loads(user_val) if user_val else {}
                gsc_threshold = values.get("gsc_threshold", "0")
                min_frequency = values.get("min_frequency", "100000")
            else:
                # If the previous step has data, try to extract parameter information
                if prev_data_str:
                    summary_data = json.loads(prev_data_str)
                    cache_path = summary_data.get('cache_path')
                    
                    if cache_path and os.path.exists(cache_path):
                        # Load raw counters from cache
                        try:
                            with open(cache_path, 'rb') as f:
                                cache_data = pickle.load(f)
                            
                            raw_counters = cache_data.get('raw_counters', {})
                            
                            # Extract weblogs, gsc, and not_indexable counters
                            weblogs_counter = None
                            gsc_counter = None
                            not_indexable_counter = None
                            
                            # Map sources to counter keys
                            source_mapping = {
                                'weblogs': ['weblogs', 'weblog', 'logs', 'log'],
                                'gsc': ['gsc', 'search_console', 'searchconsole', 'google'],
                                'not_indexable': ['not_indexable', 'crawl', 'non_indexable', 'nonindexable']
                            }
                            
                            # Find the right counters
                            for source, possible_keys in source_mapping.items():
                                for key in possible_keys:
                                    if key in raw_counters:
                                        if source == 'weblogs':
                                            weblogs_counter = raw_counters[key]
                                        elif source == 'gsc':
                                            gsc_counter = raw_counters[key]
                                        elif source == 'not_indexable':
                                            not_indexable_counter = raw_counters[key]
                                        break
                        
                            # Find parameters in weblogs or not_indexable but not in gsc
                            if gsc_counter and (weblogs_counter or not_indexable_counter):
                                # Combine weblogs and not_indexable counters
                                combined_counter = Counter()
                                if weblogs_counter:
                                    combined_counter.update(weblogs_counter)
                                if not_indexable_counter:
                                    combined_counter.update(not_indexable_counter)
                                
                                # Find parameters with zero GSC occurrences
                                # These are the "dead parameters" that could be optimized
                                max_dead_param_frequency = 0
                                for param, count in combined_counter.items():
                                    if gsc_counter.get(param, 0) == 0:
                                        max_dead_param_frequency = max(max_dead_param_frequency, count)
                                
                                # If we found a meaningful value, use it
                                if max_dead_param_frequency > 0:
                                    min_frequency = str(max_dead_param_frequency)
                                    logging.info(f"Found optimal min_frequency: {min_frequency} from max dead parameter")
                        except Exception as e:
                            logging.error(f"Error calculating optimal frequency: {str(e)}")
        except json.JSONDecodeError:
            pass  # Use defaults if JSON parsing fails
        
        await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
        
        # Calculate meaningful breakpoints for display in a static area
        breakpoints_html = ""
        try:
            # Get the parameter data from step_05
            prev_step_data = pip.get_step_data(pipeline_id, "step_05", {})
            prev_data_str = prev_step_data.get("placeholder", "")
            
            if prev_data_str:
                summary_data = json.loads(prev_data_str)
                cache_path = summary_data.get('cache_path')
                
                if cache_path and os.path.exists(cache_path):
                    # Quick calculation of meaningful breakpoints
                    with open(cache_path, 'rb') as f:
                        cache_data = pickle.load(f)
                    
                    raw_counters = cache_data.get('raw_counters', {})
                    
                    # Get the counters
                    weblogs_counter = None
                    gsc_counter = None
                    not_indexable_counter = None
                    
                    # Map sources to counter keys
                    source_mapping = {
                        'weblogs': ['weblogs', 'weblog', 'logs', 'log'],
                        'gsc': ['gsc', 'search_console', 'searchconsole', 'google'],
                        'not_indexable': ['not_indexable', 'crawl', 'non_indexable', 'nonindexable']
                    }
                    
                    # Find the right counters
                    for source, possible_keys in source_mapping.items():
                        for key in possible_keys:
                            if key in raw_counters:
                                if source == 'weblogs':
                                    weblogs_counter = raw_counters[key]
                                elif source == 'gsc':
                                    gsc_counter = raw_counters[key]
                                elif source == 'not_indexable':
                                    not_indexable_counter = raw_counters[key]
                                break
                    
                    # Find parameters with GSC=0 that meet the criteria
                    if gsc_counter and (weblogs_counter or not_indexable_counter):
                        # Combine counters
                        combined_counter = Counter()
                        if weblogs_counter:
                            combined_counter.update(weblogs_counter)
                        if not_indexable_counter:
                            combined_counter.update(not_indexable_counter)
                        
                        # Get frequencies sorted in descending order
                        all_frequencies = sorted(set(combined_counter.values()), reverse=True)
                        param_counts = {}
                        
                        # Calculate how many parameters at each frequency
                        for freq in all_frequencies:
                            count = sum(1 for param, count in combined_counter.items() 
                                       if gsc_counter.get(param, 0) <= 0 and count >= freq)
                            param_counts[freq] = count
                        
                        # Find breakpoints for interesting parameter counts
                        breakpoints = []
                        ranges = [(5, 15), (15, 30), (30, 50), (50, 100)]
                        for min_count, max_count in ranges:
                            for freq in all_frequencies:
                                if param_counts[freq] >= min_count and param_counts[freq] <= max_count:
                                    breakpoints.append((freq, param_counts[freq]))
                                    break
                        
                        # Modify the breakpoints HTML generation code
                        if breakpoints:
                            breakpoints_html = f"""
                            <div style="background: #222; padding: 10px; border-radius: 5px; margin: 15px 0;">
                                <h5 style="margin-bottom: 5px; color: #ccc;">Meaningful Min Frequency Values (with GSC=0):</h5>
                                <table style="margin-bottom: 10px; font-size: 0.9em;">
                            """
                            for freq, count in breakpoints:
                                # Round down to nearest 100
                                rounded_freq = freq if freq < 100 else int(freq // 100 * 100)
                                # Create clickable link with hardcoded path
                                breakpoints_html += f"""
                                    <tr>
                                        <td style="color: #bbb; padding-right: 10px;">Show ~{count} parameters:</td>
                                        <td style="color: #ff8c00; font-weight: bold; text-align: right;">
                                            <a href="javascript:void(0)" 
                                               onclick="
                                                 // Update both the slider and number input
                                                 document.getElementById('min_frequency').value = {rounded_freq};
                                                 document.getElementById('min_frequency_slider').value = {rounded_freq};
                                                 
                                                 // Visual feedback
                                                 document.getElementById('min_frequency').style.backgroundColor = '#224433';
                                                 setTimeout(function() {{ 
                                                     document.getElementById('min_frequency').style.backgroundColor = ''; 
                                                 }}, 500);
                                                 
                                                 // Direct AJAX call with FIXED CORRECT PATH
                                                 htmx.ajax('POST', 
                                                     '/{app_name}/parameter_preview', 
                                                     {{
                                                         target: '#parameter-preview',
                                                         values: {{
                                                             'gsc_threshold': document.getElementById('gsc_threshold').value,
                                                             'min_frequency': {rounded_freq}
                                                         }}
                                                     }});
                                                 
                                                 return false;" 
                                               style="color: #ff8c00; text-decoration: underline; cursor: pointer;">{freq:,}</a>
                                        </td>
                                    </tr>
                                """
                            breakpoints_html += """
                                </table>
                            </div>
                            """
        except Exception as e:
            logging.error(f"Error calculating breakpoints: {e}")
            breakpoints_html = ""

        # Return the form with the properly placed breakpoints info
        return Div(
            Card(
                H3(f"{pip.fmt(step_id)}: {step.show}"),
                P("Set thresholds for parameter optimization:"),
                Form(
                    Div(
                        # GSC Threshold with slider row
                        Div(
                            Small("Lower GSC Threshold to lower risk (generally keep set to 0)", style="color: #888; font-style: italic;"),
                            Div(
                                Label(
                                    NotStr("<strong>GSC Threshold:</strong>"), 
                                    For="gsc_threshold",
                                    style="min-width: 180px;"
                                ),
                                Input(
                                    type="range", 
                                    name="gsc_threshold_slider", 
                                    id="gsc_threshold_slider", 
                                    value=gsc_threshold, 
                                    min="0", 
                                    max="100", 
                                    step="1",
                                    style="flex-grow: 1; margin: 0 10px;",
                                    _oninput="document.getElementById('gsc_threshold').value = this.value; triggerParameterPreview();",
                                    hx_post=f"/{app_name}/parameter_preview",
                                    hx_trigger="input changed delay:300ms, load",
                                    hx_target="#parameter-preview",
                                    hx_include="#gsc_threshold, #min_frequency"
                                ),
                                Input(
                                    type="number", 
                                    name="gsc_threshold", 
                                    id="gsc_threshold", 
                                    value=gsc_threshold, 
                                    min="0", 
                                    max="100", 
                                    style="width: 150px;",
                                    _oninput="document.getElementById('gsc_threshold_slider').value = this.value; triggerParameterPreview();",
                                    _onchange="document.getElementById('gsc_threshold_slider').value = this.value; triggerParameterPreview();",
                                    hx_post=f"/{app_name}/parameter_preview",
                                    hx_trigger="none",
                                    hx_target="#parameter-preview",
                                    hx_include="#gsc_threshold, #min_frequency"
                                ),
                                style="display: flex; align-items: center; gap: 5px;"
                            ),
                        ),
                        
                        # Minimum Frequency with slider row
                        Div(
                            Small("Higher Minimum Frequency to reduce to only the biggest offenders", style="color: #888; font-style: italic;"),
                            Div(
                                Label(
                                    NotStr("<strong>Minimum Frequency:</strong>"), 
                                    For="min_frequency",
                                    style="min-width: 180px;"
                                ),
                                Input(
                                    type="range", 
                                    name="min_frequency_slider", 
                                    id="min_frequency_slider", 
                                    value=min_frequency, 
                                    min="0", 
                                    max="250000", 
                                    step="1000",
                                    style="flex-grow: 1; margin: 0 10px;",
                                    _oninput="document.getElementById('min_frequency').value = this.value; triggerParameterPreview();",
                                    hx_post=f"/{app_name}/parameter_preview",
                                    hx_trigger="input changed delay:300ms",
                                    hx_target="#parameter-preview",
                                    hx_include="#gsc_threshold, #min_frequency"
                                ),
                                Input(
                                    type="number", 
                                    name="min_frequency", 
                                    id="min_frequency", 
                                    value=min_frequency, 
                                    min="0", 
                                    max="250000", 
                                    style="width: 150px;",
                                    _oninput="document.getElementById('min_frequency_slider').value = this.value; triggerParameterPreview();",
                                    _onchange="document.getElementById('min_frequency_slider').value = this.value; triggerParameterPreview();",
                                    hx_post=f"/{app_name}/parameter_preview",
                                    hx_trigger="none",
                                    hx_target="#parameter-preview",
                                    hx_include="#gsc_threshold, #min_frequency"
                                ),
                                style="display: flex; align-items: center; gap: 5px;"
                            ),
                            style="margin-bottom: 15px;"
                        ),
                        
                        # Static breakpoints info - placed outside dynamic update area
                        NotStr(breakpoints_html) if breakpoints_html else None,
                        
                        # Parameter preview container
                        Div(
                            H4("Parameters That Would Be Optimized:"),
                            Div(
                                P("Adjust thresholds above to see which parameters would be optimized.", 
                                  style="color: #888; font-style: italic;"),
                                id="parameter-preview",
                                style="max-height: 300px; overflow-y: auto; background: #111; border-radius: 5px; padding: 10px; margin-bottom: 15px;"
                            ),
                            style="margin-bottom: 20px;"
                        ),
                        
                        Div(
                            Button("Create Optimization ▸", type="submit", cls="primary"),
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

    async def step_06_submit(self, request):
        """Process the submission for the parameter threshold settings."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_06"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get("pipeline_id", "unknown")
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'

        # Get form data
        form = await request.form()
        gsc_threshold = form.get("gsc_threshold", "0")
        min_frequency = form.get("min_frequency", "100000")
        
        # Get the parameter data from step_05
        prev_step_data = pip.get_step_data(pipeline_id, "step_05", {})
        prev_data_str = prev_step_data.get("placeholder", "")
        
        # Initialize empty list for selected parameters
        selected_params = []
        
        try:
            if prev_data_str:
                summary_data = json.loads(prev_data_str)
                cache_path = summary_data.get('cache_path')
                
                if cache_path and os.path.exists(cache_path):
                    # Load raw counters from cache
                    with open(cache_path, 'rb') as f:
                        cache_data = pickle.load(f)
                    
                    raw_counters = cache_data.get('raw_counters', {})
                    
                    # Extract counters for each source
                    weblogs_counter = None
                    gsc_counter = None
                    not_indexable_counter = None
                    
                    # Map sources to counter keys
                    source_mapping = {
                        'weblogs': ['weblogs', 'weblog', 'logs', 'log'],
                        'gsc': ['gsc', 'search_console', 'searchconsole', 'google'],
                        'not_indexable': ['not_indexable', 'crawl', 'non_indexable', 'nonindexable']
                    }
                    
                    # Find the right counters
                    for source, possible_keys in source_mapping.items():
                        for key in possible_keys:
                            if key in raw_counters:
                                if source == 'weblogs':
                                    weblogs_counter = raw_counters[key]
                                elif source == 'gsc':
                                    gsc_counter = raw_counters[key]
                                elif source == 'not_indexable':
                                    not_indexable_counter = raw_counters[key]
                                break
                    
                    # Find parameters that meet our criteria
                    if gsc_counter and (weblogs_counter or not_indexable_counter):
                        # Combine weblogs and not_indexable counters
                        combined_counter = Counter()
                        if weblogs_counter:
                            combined_counter.update(weblogs_counter)
                        if not_indexable_counter:
                            combined_counter.update(not_indexable_counter)
                        
                        # Collect parameters that match our criteria
                        for param, count in combined_counter.items():
                            param_gsc_count = gsc_counter.get(param, 0)
                            
                            # Check if this parameter meets our criteria
                            if param_gsc_count <= int(gsc_threshold) and count >= int(min_frequency):
                                selected_params.append(param)
            
            # Generate JavaScript code using the template
            selected_params_js_array = json.dumps(selected_params)
            
            js_code = f"""// Function to remove query parameters from a URL
function removeQueryParams(url, paramsToRemove) {{
    let urlParts = url.split('?');
    if (urlParts.length >= 2) {{
        let queryParams = urlParts[1].split('&');
        let updatedParams = [];
        for (let i = 0; i < queryParams.length; i++) {{
            let paramParts = queryParams[i].split('=');
            if (!paramsToRemove.includes(paramParts[0])) {{
                updatedParams.push(queryParams[i]);
            }}
        }}
        if (updatedParams.length > 0) {{
            return urlParts[0] + '?' + updatedParams.join('&');
        }} else {{
            return urlParts[0];
        }}
    }} else {{
        return url;
    }}
}}
  
// Remove wasteful parameters from all links
function removeWastefulParams() {{
    const DOM = runtime.getDOM();
    const removeParameters = {selected_params_js_array};
    DOM.getAllElements("[href]").forEach(function(el) {{
        let targetURL = el.getAttribute("href");	
        let newTargetURL = removeQueryParams(targetURL, removeParameters);
        if (targetURL != newTargetURL) {{
            // console.log("FROM:" + targetURL + " TO:" + newTargetURL);
            el.setAttribute("href", newTargetURL);
            el.setAttribute("data-bty-pw-id", "REPLACE_ME!!!");
        }}
    }});
}}

// Execute the function
removeWastefulParams();
"""
            
            # Store the JavaScript code in state
            threshold_data = {
                "gsc_threshold": gsc_threshold,
                "min_frequency": min_frequency,
                "selected_params": selected_params,
                "js_code": js_code
            }
            
            # Convert to JSON string for storage
            user_val = json.dumps(threshold_data)
            
            # Save the values to state
            await pip.update_step_state(pipeline_id, step_id, user_val, steps)
            
            # Generate unique widget ID for this step and pipeline
            widget_id = f"prism-widget-{pipeline_id.replace('-', '_')}-{step_id}"
            
            # Create Prism widget with the generated JavaScript
            prism_widget = self.create_prism_widget(js_code, widget_id, 'javascript')
            
            # Return widget container instead of revert control
            from starlette.responses import HTMLResponse
            from fasthtml.common import to_xml  # Import from fasthtml.common instead
            
            response = HTMLResponse(
                to_xml(
                    Div(
                        pip.widget_container(
                            step_id=step_id,
                            app_name=app_name,
                            message=f"Parameter Optimization with {len(selected_params) if selected_params else 0} parameters",
                            widget=prism_widget,
                            steps=steps
                        ),
                        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                        id=step_id
                    )
                )
            )
            
            # Add HX-Trigger to initialize Prism highlighting
            response.headers["HX-Trigger"] = json.dumps({
                "initializePrism": {
                    "targetId": widget_id
                }
            })
            
            return response
            
        except Exception as e:
            logging.exception(f"Error in step_06_submit: {e}")
            return P(f"Error creating parameter optimization: {str(e)}", style=pip.get_style("error"))

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
        
        # API PATTERN: This method demonstrates the standard Botify API interaction pattern:
        # 1. Read API token from local file
        # 2. Construct API endpoint URL with proper path parameters
        # 3. Make authenticated request with error handling
        # 4. Return tuple of (result, error_message) for consistent error handling
        
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

    async def get_deterministic_filepath(self, username, project_name, analysis_slug, data_type=None):
        """Generate a deterministic file path for a given data export.
        
        # FILE MANAGEMENT PATTERN: This demonstrates the standard approach to file caching:
        # 1. Create deterministic paths based on user/project identifiers
        # 2. Check if files exist before re-downloading
        # 3. Store metadata about cached files for user feedback
        
        Args:
            username: Organization username
            project_name: Project name
            analysis_slug: Analysis slug
            data_type: Type of data (crawl, weblog, gsc) or None for base directory
            
        Returns:
            String path to either the file location or base directory
        """
        # Create base directory path
        base_dir = f"downloads/{username}/{project_name}/{analysis_slug}"
        
        # If no data_type specified, return the base directory path
        if not data_type:
            return base_dir
        
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
                await self.message_queue.add(pip, f"✓ Using cached crawl data ({file_info['size']})", verbatim=True)
                
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

                    # Load into DataFrame skipping first row to chop off sep=,
                    df = pd.read_csv(gsc_filepath, skiprows=1)
                    # Save right back out with no index
                    df.to_csv(gsc_filepath, index=False)
                    
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
                await self.message_queue.add(pip, f"✓ Using cached crawl data ({file_info['size']})", verbatim=True)
                
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

                    # Load the CSV file and apply column headers
                    df = pd.read_csv(crawl_filepath)
                    
                    # Set readable, consistent column headers
                    df.columns = ["Full URL", "Compliance Status", "Compliance Details", "Occurrence Count"]
                    
                    # Save back to CSV with proper headers
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
            await self.message_queue.add(pip, f"✓ Crawl data downloaded: {file_info['size']}", verbatim=True)
            
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
                    await self.message_queue.add(pip, f"✓ Using cached web logs data ({file_info['size']})", verbatim=True)
                    
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
                        await self.message_queue.add(pip, f"Using job ID {job_id} for polling...", verbatim=True)
                        full_job_url = f"https://api.botify.com/v1/jobs/{job_id}"
                        
                    # Polling with direct absolute URL approach
                    success, result = await self.poll_job_status(full_job_url, api_token)
                    
                    if not success:
                        error_message = isinstance(result, str) and result or "Export job failed"
                        await self.message_queue.add(pip, f"❌ Export failed: {error_message}", verbatim=True)
                        
                        # Handle the specific "Unknown error" case more gracefully
                        if "Unknown error (Type: Unknown type)" in error_message:
                            await self.message_queue.add(pip, "This likely means no web logs were retrieved for this analysis period. Try selecting a different analysis in Step 2.", verbatim=True)
                            # Instead of failing, just mark as no logs available
                            check_result["has_logs"] = False
                            check_result["download_complete"] = True
                            check_result["error"] = error_message
                            check_result["note"] = "Project doesn't support logs export format"
                            
                            # Convert to JSON for storage
                            check_result_str = json.dumps(check_result)
                            
                            # Store in state
                            await pip.update_step_state(pipeline_id, step_id, check_result_str, steps)
                            
                            # Return result display with explanatory message
                            return Div(
                                pip.revert_control(
                                    step_id=step_id, 
                                    app_name=app_name, 
                                    message=f"{step.show}: Project logs couldn't be processed (using fallback)",
                                    steps=steps
                                ),
                                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                                id=step_id
                            )
                        else:
                            # For other errors, still raise the exception
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
                await self.message_queue.add(pip, f"✓ Web logs data downloaded: {file_info['size']}", verbatim=True)
            
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

    async def analyze_parameters(self, username, project_name, analysis_slug):
        """Analyzes URL parameters from crawl, GSC, and web logs data.
        
        Args:
            username: Organization username
            project_name: Project name
            analysis_slug: Analysis slug
            
        Returns:
            Dictionary containing analysis results and cache data
        """
        # Get base directory path for this analysis
        base_dir = await self.get_deterministic_filepath(username, project_name, analysis_slug)
        data_dir = Path(base_dir)
        
        # Define cache filename
        cache_filename = "_param_scores_cache.pkl"
        
        # Try to load from cache first
        logging.info("Attempting to load scores from cache...")
        cached_scores_data = self.load_parameter_scores_from_cache(data_dir, cache_filename)
        
        if cached_scores_data is None:
            logging.info("Cache not found or invalid, calculating scores from source files...")
            scores_data = await self.calculate_and_cache_parameter_scores(
                data_directory_path=data_dir,
                cache_filename=cache_filename
            )
            if scores_data is None:
                raise ValueError("Failed to calculate scores from source files")
        else:
            logging.info("Using cached scores data")
            scores_data = cached_scores_data
            
        return scores_data

    def load_csv_with_optional_skip(self, file_path):
        """Loads a CSV file, handles 'sep=', errors gracefully."""
        critical_columns = ['Full URL', 'URL']
        try:
            with open(file_path, "r", encoding='utf-8', errors='ignore') as f:
                first_line = f.readline()
            skip_rows = 1 if first_line.startswith("sep=") else 0
            df = pd.read_csv(file_path, skiprows=skip_rows, on_bad_lines='warn', low_memory=False)
            if not any(col in df.columns for col in critical_columns):
                logging.warning(f"File {Path(file_path).name} loaded, but missing expected URL column ('Full URL' or 'URL').")
                return pd.DataFrame({'URL': []})
            return df
        except Exception as e:
            logging.error(f"Error loading CSV {Path(file_path).name}: {e}")
            return pd.DataFrame({'URL': []})

    def extract_query_params(self, url):
        """Extracts query parameter keys from a URL string."""
        if not isinstance(url, str): return []
        try:
            if url.startswith('//'): url = 'http:' + url
            parsed = urlparse(url)
            if not parsed.query: return []
            params_dict = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=False, errors='ignore')
            return list(params_dict.keys())
        except ValueError: return []

    def count_query_params(self, df, col_name_priority=["Full URL", "URL"]):
        """Counts query parameters from the first valid URL column found in a DataFrame."""
        counter = Counter()
        url_col = next((col for col in col_name_priority if col in df.columns), None)
        if url_col is None:
            return counter
        url_series = df[url_col].astype(str).dropna()
        for url in url_series:
            counter.update(self.extract_query_params(url))
        return counter

    async def calculate_and_cache_parameter_scores(
        self,
        data_directory_path,
        logs_filename="weblogs.csv",
        gsc_filename="gsc.csv",
        crawl_filename="crawl.csv",
        url_column_priority=["Full URL", "URL"],
        cache_filename="_param_scores_cache.pkl"
    ):
        """Calculates and caches parameter scores from data files."""
        data_dir = Path(data_directory_path)
        if not data_dir.is_dir():
            logging.error(f"Provided data directory path is not valid: {data_directory_path}")
            return None

        # Construct full paths
        crawl_file_path = data_dir / crawl_filename
        gsc_file_path = data_dir / gsc_filename
        logs_file_path = data_dir / logs_filename

        # Validate and Load Data
        required_files_info = {crawl_filename: crawl_file_path, gsc_filename: gsc_file_path}
        loaded_dfs = {}
        logging.info(f"Loading data from directory: {data_directory_path}")
        
        for name, path in required_files_info.items():
            logging.info(f"Loading: {name} (Required)")
            if not path.is_file():
                logging.error(f"Required file not found: {path}")
                return None
            df = self.load_csv_with_optional_skip(str(path))
            if not any(col in df.columns for col in url_column_priority):
                logging.error(f"No usable URL column in {name}")
                return None
            loaded_dfs[name] = df

        # Handle optional web logs
        df_weblogs = pd.DataFrame()
        logs_status = "Not Found / Not Used"
        if logs_file_path.is_file():
            logging.info(f"Loading: {logs_filename} (Optional)")
            df_weblogs = self.load_csv_with_optional_skip(str(logs_file_path))
            if any(col in df_weblogs.columns for col in url_column_priority):
                logs_status = "Loaded"
                loaded_dfs[logs_filename] = df_weblogs
            else:
                logs_status = "Loaded but No URL Column"
                df_weblogs = pd.DataFrame()
        else:
            logging.info(f"Optional file '{logs_filename}' not found.")

        # Count Parameters
        logging.info("Counting parameters...")
        counter_crawl = self.count_query_params(loaded_dfs[crawl_filename], url_column_priority)
        counter_gsc = self.count_query_params(loaded_dfs[gsc_filename], url_column_priority)
        counter_weblogs = Counter()
        if logs_status == "Loaded":
            counter_weblogs = self.count_query_params(loaded_dfs[logs_filename], url_column_priority)

        # Calculate Derived Scores
        logging.info("Calculating parameter scores...")
        all_params = set(counter_weblogs.keys()) | set(counter_crawl.keys())
        if not all_params:
            logging.warning("No parameters found in Weblogs or Crawl data to score.")
            results_sorted = []
        else:
            results = []
            for param in all_params:
                wb_count = counter_weblogs.get(param, 0)
                crawl_count = counter_crawl.get(param, 0)
                gsc_count = counter_gsc.get(param, 0)
                total_count = wb_count + crawl_count
                score = total_count / (gsc_count + 1)
                results.append((param, wb_count, crawl_count, gsc_count, total_count, score))
            results_sorted = sorted(results, key=lambda x: x[5], reverse=True)

        # Prepare Cache Data
        cache_data = {
            'results_sorted': results_sorted,
            'counters': {
                'weblogs': counter_weblogs,
                'crawl': counter_crawl,
                'gsc': counter_gsc
            },
            'metadata': {
                'data_directory_path': str(data_dir),
                'logs_filename': logs_filename,
                'gsc_filename': gsc_filename,
                'crawl_filename': crawl_filename,
                'logs_status': logs_status,
                'cache_timestamp': time.time()
            }
        }

        # Save to Cache
        cache_file_path = data_dir / cache_filename
        logging.info(f"Saving scores and counters to cache file: {cache_file_path}")
        try:
            with open(cache_file_path, 'wb') as f:
                pickle.dump(cache_data, f)
            logging.info("Cache saved successfully.")
        except Exception as e:
            logging.error(f"Error saving cache file: {e}")

        return cache_data

    def load_parameter_scores_from_cache(self, data_directory_path, cache_filename="_param_scores_cache.pkl"):
        """Loads scored parameter data from cache file."""
        data_dir = Path(data_directory_path)
        cache_file_path = data_dir / cache_filename

        if not cache_file_path.is_file():
            logging.info(f"Cache file not found at: {cache_file_path}")
            return None

        logging.info(f"Attempting to load scores data from cache: {cache_file_path}")
        try:
            with open(cache_file_path, 'rb') as f:
                cache_data = pickle.load(f)
            if (isinstance(cache_data, dict) and
                'results_sorted' in cache_data and
                'counters' in cache_data and
                'metadata' in cache_data):
                logging.info("Score cache loaded successfully.")
                return cache_data
            else:
                logging.error("Invalid cache file format (missing 'results_sorted'?).")
                return None
        except (pickle.UnpicklingError, EOFError) as e:
            logging.error(f"Error loading cache file (it might be corrupted): {e}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred loading the cache: {e}")
            return None

    def create_prism_widget(self, code, widget_id, language='javascript'):
        """Create a Prism.js syntax highlighting widget with copy functionality."""
        # Generate a unique ID for the hidden textarea
        textarea_id = f"{widget_id}_raw_code"
        
        # Create container for the widget
        container = Div(
            Div(
                H5("Copy/Paste into PageWorkers:"),
                # Add a hidden textarea to hold the raw code (much safer than trying to escape it for JS)
                Textarea(
                    code,
                    id=textarea_id,
                    style="display: none;"  # Hide the textarea
                ),
                # Add custom styling to remove padding
                NotStr("""
                <style>
                    /* Remove padding from pre > code */
                    #""" + widget_id + """ pre > code {
                        padding: 0 !important;
                    }
                </style>
                """),
                # This pre/code structure is required for Prism.js
                Pre(
                    Code(
                        code,
                        cls=f"language-{language}"  # Language class for Prism
                    ),
                    cls="line-numbers"  # Enable line numbers
                ),
                style="margin-top: 1rem;"
            ),
            id=widget_id
        )
        
        # Create script to initialize Prism with debugging
        init_script = Script(
            f"""
            (function() {{
                console.log('Prism widget loaded, ID: {widget_id}');
                // Check if Prism is loaded
                if (typeof Prism === 'undefined') {{
                    console.error('Prism library not found');
                    return;
                }}
                
                // Attempt to manually trigger highlighting
                setTimeout(function() {{
                    try {{
                        console.log('Manually triggering Prism highlighting for {widget_id}');
                        Prism.highlightAllUnder(document.getElementById('{widget_id}'));
                    }} catch(e) {{
                        console.error('Error during manual Prism highlighting:', e);
                    }}
                }}, 300);
            }})();
            """,
            type="text/javascript"
        )
        
        return Div(container, init_script)

    def load_raw_counters_from_cache(self, data_directory_path, cache_filename="_raw_param_counters_cache.pkl"):
        """Loads raw counters data from a cache file."""
        data_dir = Path(data_directory_path)
        cache_file_path = data_dir / cache_filename
        if not cache_file_path.is_file():
            return None

        try:
            with open(cache_file_path, 'rb') as f:
                counters_data = pickle.load(f)
            # Basic validation for the new structure
            if (isinstance(counters_data, dict) and
                'raw_counters' in counters_data and isinstance(counters_data['raw_counters'], dict) and
                'metadata' in counters_data and isinstance(counters_data['metadata'], dict) and
                counters_data['metadata'].get('cache_version', 0) >= 2.0): # Check version
                return counters_data
            else:
                logging.error(f"Invalid or outdated cache file format in {cache_file_path}.")
                return None
        except (pickle.UnpicklingError, EOFError) as e:
            logging.error(f"Error loading cache file (it might be corrupted): {cache_file_path} - {e}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred loading the cache: {cache_file_path} - {e}")
            return None

    async def calculate_and_cache_raw_counters(self, data_directory_path, input_files_config, cache_filename="_raw_param_counters_cache.pkl"):
        """
        Loads specified CSV files, performs a raw count of query parameters for each,
        and saves the counters to a cache file. Returns the counters and metadata.
        """
        data_dir = Path(data_directory_path)
        if not data_dir.is_dir():
            logging.error(f"Provided data directory path is not valid: {data_directory_path}")
            return None

        raw_counters = {}
        file_statuses = {}
        url_column_priority = ["Full URL", "URL"]

        logging.info(f"Processing data from directory: {data_dir}")

        for key, filename in input_files_config.items():
            file_path = data_dir / filename
            logging.info(f"Processing file: {filename} (as '{key}')")

            # Check if file exists
            if not file_path.is_file():
                logging.warning(f"File not found: {file_path}")
                raw_counters[key] = Counter()
                file_statuses[key] = "File not found"
                continue

            # Use existing CSV loading method
            try:
                df = self.load_csv_with_optional_skip(str(file_path))
                
                if df.empty or not any(col in df.columns for col in url_column_priority):
                    logging.warning(f"No usable URL column in {filename}")
                    raw_counters[key] = Counter()
                    file_statuses[key] = "No URL column"
                    continue
                    
                # Count parameters
                logging.info(f"Counting parameters in {filename}...")
                file_counter = self.count_query_params(df, url_column_priority)
                raw_counters[key] = file_counter
                file_statuses[key] = f"Processed ({len(file_counter):,} unique params found)"
                logging.info(f"Counted {len(file_counter):,} unique parameters in {filename}")
            except Exception as e:
                logging.exception(f"Error processing {filename}: {e}")
                raw_counters[key] = Counter()
                file_statuses[key] = f"Error: {str(e)}"

        # Prepare Cache Data
        counters_data = {
            'raw_counters': raw_counters,
            'metadata': {
                'data_directory_path': str(data_dir.resolve()),
                'input_files_config': input_files_config,
                'file_statuses': file_statuses,
                'cache_timestamp': time.time(),
                'cache_version': 2.0  # New version for raw counts structure
            }
        }

        # Save to Cache
        cache_file_path = data_dir / cache_filename
        logging.info(f"Saving raw counters to cache file: {cache_file_path}")
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(cache_file_path), exist_ok=True)
            
            with open(cache_file_path, 'wb') as f:
                pickle.dump(counters_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            logging.info("Cache saved successfully.")
        except Exception as e:
            logging.error(f"Error saving cache file: {e}")

        return counters_data

    # Add this helper method to create a simple placeholder for parameter visualization
    def create_parameter_visualization_placeholder(self, summary_data_str=None):
        """
        Create a visualization of parameters from all three data sources.
        """
        # Initialize with default value
        TOP_PARAMS_COUNT = 40
        
        # Import standard libraries
        import logging
        import matplotlib.pyplot as plt
        from io import BytesIO, StringIO
        import base64
        import numpy as np
        import json
        import os
        from pathlib import Path
        from collections import Counter

        # Debug collection
        debug_info = []
        def add_debug(msg):
            debug_info.append(msg)
            logging.info(msg)
        
        try:
            add_debug("Starting parameter visualization")
            
            # Parse summary data if provided
            has_data = False
            total_params = 0
            data_sources = []
            
            # Counters for each data source
            source_counters = {
                'weblogs': Counter(),
                'gsc': Counter(),
                'not_indexable': Counter()  # 'crawl' data
            }
            
            if summary_data_str:
                summary_data = json.loads(summary_data_str)
                total_params = summary_data.get('total_unique_parameters', 0)
                data_sources = list(summary_data.get('data_sources', {}).keys())
                # Get the param_count from the stored data
                TOP_PARAMS_COUNT = summary_data.get('param_count', 40)
                has_data = True
                
                add_debug(f"Data sources in summary: {data_sources}")
                
                # Get the raw counters from cache file
                cache_path = summary_data.get('cache_path')
                add_debug(f"Cache path: {cache_path}, exists: {os.path.exists(cache_path) if cache_path else False}")
                
                if cache_path and os.path.exists(cache_path):
                    try:
                        with open(cache_path, 'rb') as f:
                            cache_data = pickle.load(f)
                        
                        raw_counters = cache_data.get('raw_counters', {})
                        add_debug(f"Raw counter keys in cache: {list(raw_counters.keys())}")
                        
                        # Dump the first few entries of each counter for inspection
                        for key, counter in raw_counters.items():
                            top_items = list(counter.most_common(5))
                            add_debug(f"Raw counter '{key}' has {len(counter)} items. Top 5: {top_items}")
                        
                        # Direct mapping of sources to counter keys
                        source_mapping = {
                            'weblogs': ['weblogs', 'weblog', 'logs', 'log'],
                            'gsc': ['gsc', 'search_console', 'searchconsole', 'google'],
                            'not_indexable': ['not_indexable', 'crawl', 'non_indexable', 'nonindexable']
                        }
                        
                        # Map sources to keys
                        for source, possible_keys in source_mapping.items():
                            found = False
                            for key in possible_keys:
                                if key in raw_counters:
                                    source_counters[source] = raw_counters[key]
                                    add_debug(f"Mapped source '{source}' to cache key '{key}' with {len(raw_counters[key])} items")
                                    found = True
                                    break
                            if not found:
                                add_debug(f"No matching key found for source '{source}'")
                    
                    except Exception as e:
                        add_debug(f"Error loading parameter data from cache: {e}")
                        add_debug(f"Cache file not found or invalid")
                    
                    # If we couldn't get data from cache, use the summary data directly
                    if all(len(counter) == 0 for counter in source_counters.values()) and has_data:
                        add_debug("No counter data from cache, using summary data directly")
                        
                        for source, counter in source_counters.items():
                            # Try to find a matching data source
                            matching_source = None
                            if source == 'weblogs':
                                matching_source = next((s for s in data_sources if 'log' in s.lower()), None)
                            elif source == 'gsc':
                                matching_source = next((s for s in data_sources if 'gsc' in s.lower() or 'search' in s.lower()), None)
                            elif source == 'not_indexable':
                                matching_source = next((s for s in data_sources if 'crawl' in s.lower() or 'index' in s.lower() or 'not_' in s.lower()), None)
                            
                            if matching_source:
                                add_debug(f"Found matching source '{matching_source}' for '{source}'")
                                source_data = summary_data.get('data_sources', {}).get(matching_source, {})
                                for param_data in source_data.get('top_parameters', []):
                                    counter[param_data['name']] = param_data['count']
                            else:
                                add_debug(f"No matching source found for '{source}'")
            
            # Print counter sizes after loading
            for source, counter in source_counters.items():
                top_items = counter.most_common(5)
                items_count = len(counter)
                total_count = sum(counter.values())
                add_debug(f"FINAL: Source '{source}' has {items_count} items with {total_count} total occurrences")
                if top_items:
                    add_debug(f"  Top 5 for {source}: {top_items}")
            
            # Create matplotlib visualization for the top parameters
            
            # Get union of all parameters across sources
            all_params = set()
            for counter in source_counters.values():
                all_params.update(counter.keys())
            
            # Calculate scores and create sorted results
            results = []
            for param in all_params:
                wb_count = source_counters['weblogs'].get(param, 0)
                ni_count = source_counters['not_indexable'].get(param, 0)
                gsc_count = source_counters['gsc'].get(param, 0)
                total_count = wb_count + ni_count
                # Compute the win score (adding 1 to gsc_count prevents division by zero)
                score = total_count / (gsc_count + 1)
                results.append((param, wb_count, ni_count, gsc_count, total_count, score))
            
            # Sort parameters by score in descending order
            results_sorted = sorted(results, key=lambda x: x[5], reverse=True)
            
            # Get top parameters for matplotlib visualization
            top_params = [param for param, _, _, _, _, _ in results_sorted[:TOP_PARAMS_COUNT]]
            top_params.reverse()
            
            # Create a rich table for "Potential Parameter Wins"
            table_html = '''
            <table class="param-table">
                <caption>Potential Parameter Wins (High Weblogs+NotIndex / Low GSC)</caption>
                <tr class="header">
                    <td class="header-cell"><span class="param-name">Parameter</span></td>
                    <td class="header-cell"><span class="weblogs-val">Weblogs</span></td>
                    <td class="header-cell"><span class="not-index-val">Not-Indexable</span></td>
                    <td class="header-cell"><span class="gsc-val">GSC</span></td>
                    <td class="header-cell"><span class="total-val">Total</span></td>
                    <td class="header-cell"><span class="score-val">Score</span></td>
                </tr>
            '''
            
            # Add the top parameters to the table, using the same count as the chart
            for param, wb, ni, gsc, total, score in results_sorted[:TOP_PARAMS_COUNT]:
                table_html += f'''
                <tr>
                    <td><span class="param-name">{param}</span></td>
                    <td><span class="weblogs-val">{wb:,}</span></td>
                    <td><span class="not-index-val">{ni:,}</span></td>
                    <td><span class="gsc-val">{gsc:,}</span></td>
                    <td><span class="total-val">{total:,}</span></td>
                    <td><span class="score-val">{score:,.0f}</span></td>
                </tr>
                '''
            
            table_html += '</table>'
            
            # Create figure with dark style for the bar chart
            # Calculate height dynamically based on parameter count
            figure_height = max(15, min(TOP_PARAMS_COUNT * 0.65, 50))

            add_debug(f"Chart parameters: count={TOP_PARAMS_COUNT}, final_height={figure_height}")
            
            # Create figure with custom initialization parameters and no margins
            plt.figure(figsize=(10, figure_height), facecolor='#13171f', constrained_layout=False)

            # Create axes with specific dimensions to fill most of the figure
            # Extend the right margin to 0.7 (70% width) to make room for the value labels
            ax = plt.axes([0.25, 0.02, 0.7, 0.95])  # Increased left margin from 0.2 to 0.25
            ax.set_facecolor('#13171f')

            # Change all spines (the box around the plot) to white
            for spine in ax.spines.values():
                spine.set_color('white')

            # Remove the right and top spines completely
            ax.spines['right'].set_visible(False)
            ax.spines['top'].set_visible(False)

            # Generate positions for bars
            y_pos = np.arange(len(top_params))
            width = 0.25

            # Prepare data for each source
            weblogs_values = [source_counters['weblogs'].get(param, 0) for param in top_params]
            crawl_values = [source_counters['not_indexable'].get(param, 0) for param in top_params]
            gsc_values = [source_counters['gsc'].get(param, 0) for param in top_params]

            # Calculate max value to help with layout
            max_value = max([max(weblogs_values or [0]), max(crawl_values or [0]), max(gsc_values or [0])])
            add_debug(f"Max value in data: {max_value}")

            # Use log scale to make small values more visible
            ax.set_xscale('symlog')  # Symmetric log scale for handling zero values

            # Create grouped bar chart with distinct colors
            weblog_bars = ax.barh([p + width for p in y_pos], weblogs_values, width, color='#4fa8ff', label='Web Logs', alpha=0.9)
            crawl_bars = ax.barh(y_pos, crawl_values, width, color='#ff0000', label='Crawl Data', alpha=0.9)
            gsc_bars = ax.barh([p - width for p in y_pos], gsc_values, width, color='#50fa7b', label='Search Console', alpha=0.9)

            # Make sure grid lines are white as well
            ax.grid(axis='x', linestyle='--', alpha=0.2, color='white')

            # Truncate long parameter names with ellipsis for better display
            truncated_params = []
            for param in top_params:
                if len(param) > 25:
                    truncated = param[:22] + "..."
                else:
                    truncated = param
                truncated_params.append(truncated)

            # Set labels, ticks and styling - ensure all axis elements are white
            ax.set_yticks(y_pos)
            ax.set_yticklabels(truncated_params, fontsize=8, color='white')
            ax.set_xlabel('Occurrences (log scale)', color='white')
            ax.set_ylabel('Parameters', color='white')
            ax.set_title(f'Top {TOP_PARAMS_COUNT} Parameters by Data Source (Log Scale)', color='white')
            ax.tick_params(axis='both', colors='white')
            ax.legend(loc='lower right', facecolor='#2d2d3a', edgecolor='#555555', labelcolor='white')

            # Increase x-axis limit to make extra room for labels
            # In log scale, we need to go beyond the max value
            if max_value > 0:
                # For log scale, use multiplication factor to ensure room for labels
                ax.set_xlim(0, max_value * 2)
            
            # Add value labels with appropriate colors
            for i, (wb, cr, gs) in enumerate(zip(weblogs_values, crawl_values, gsc_values)):
                # Web logs (blue)
                if wb > 0:
                    text_pos = wb * 1.05  # Reduced offset factor
                    ax.text(text_pos, i + width, f"{wb:,}", va='center', fontsize=7, color='#4fa8ff')
                elif wb == 0:
                    ax.text(0.01, i + width, "0", va='center', ha='left', fontsize=7, color='#4fa8ff')
                    
                # Crawl data (red)
                if cr > 0:
                    text_pos = cr * 1.05  # Reduced offset factor
                    ax.text(text_pos, i, f"{cr:,}", va='center', fontsize=7, color='#ff0000', weight='bold')
                elif cr == 0:
                    ax.text(0.01, i, "0", va='center', ha='left', fontsize=7, color='#ff0000')
                    
                # Search console (green)
                if gs > 0:
                    text_pos = gs * 1.05  # Reduced offset factor
                    ax.text(text_pos, i - width, f"{gs:,}", va='center', fontsize=7, color='#50fa7b')
                elif gs == 0:
                    ax.text(0.01, i - width, "0", va='center', ha='left', fontsize=7, color='#50fa7b')
            
            # Ensure the y-axis limits are tight to the data
            y_min, y_max = -width * 1.5, (len(y_pos) - 1) + width * 1.5
            ax.set_ylim(y_min, y_max)  # Tight y-axis limits
            
            # Save figure to a bytes buffer
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=120)
            plt.close()
            
            # Convert to base64 for embedding in HTML
            img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Create an HTML component with the image, styled table, and debug info
            # Hide debug section by default, only include as a collapsible section
            debug_section = ""
            if debug_info:
                debug_section = Div(
                    Details(
                        Summary("Debug Information (click to expand)"),
                        Pre("\n".join(debug_info), 
                            style="background: #333; color: #eee; padding: 10px; border-radius: 5px; font-size: 0.8em; max-height: 300px; overflow-y: auto;"),
                        style="margin-top: 1rem;"
                    )
                )
            
            visualization = Div(
                Div(
                    H4("Parameter Analysis Summary:"),
                    P(f"Total unique parameters: {total_params:,}" if has_data else "No data available yet"),
                    P(f"Data sources: {', '.join(data_sources)}" if data_sources else "No data sources processed yet"),
                    
                    Div(
                        NotStr(f'<img src="data:image/png;base64,{img_str}" style="width:100%; height:auto;" alt="Parameter Distribution Chart" />'),
                        style="text-align: center; margin-top: 1rem;"
                    ),
                    
                    H4("Potential Parameter Wins"),
                    NotStr(table_html),
                    
                    debug_section,
                    style="padding: 15px; background-color: var(--pico-card-background-color); border-radius: var(--pico-border-radius);"
                )
            )
            
            return visualization
            
        except Exception as e:
            logging.exception(f"Error creating parameter visualization: {e}")
            error_msg = f"Error creating visualization: {str(e)}\n\nDebug info:\n" + "\n".join(debug_info)
            return Div(
                NotStr(f"<div style='color: red; padding: 10px; background: #333; border-radius: 5px;'>{error_msg}</div>"), 
                _raw=True
            )

    async def parameter_preview(self, request):
        """Process real-time parameter preview requests based on threshold settings."""
        pip, db, app_name = self.pipulate, self.db, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Get form data from the request
        form = await request.form()
        gsc_threshold = int(form.get("gsc_threshold", "0"))
        min_frequency = int(form.get("min_frequency", "100000"))
        
        # Get the parameter data from step_05
        prev_step_data = pip.get_step_data(pipeline_id, "step_05", {})
        prev_data_str = prev_step_data.get("placeholder", "")
        
        # Initialize empty list for output
        matching_params = []
        param_count = 0
        total_frequency = 0
        breakpoint_frequencies = []  # Initialize this variable
        
        try:
            if prev_data_str:
                summary_data = json.loads(prev_data_str)
                cache_path = summary_data.get('cache_path')
                
                if cache_path and os.path.exists(cache_path):
                    # Load raw counters from cache
                    with open(cache_path, 'rb') as f:
                        cache_data = pickle.load(f)
                    
                    raw_counters = cache_data.get('raw_counters', {})
                    
                    # Extract counters for each source
                    weblogs_counter = None
                    gsc_counter = None
                    not_indexable_counter = None
                    
                    # Map sources to counter keys
                    source_mapping = {
                        'weblogs': ['weblogs', 'weblog', 'logs', 'log'],
                        'gsc': ['gsc', 'search_console', 'searchconsole', 'google'],
                        'not_indexable': ['not_indexable', 'crawl', 'non_indexable', 'nonindexable']
                    }
                    
                    # Find the right counters
                    for source, possible_keys in source_mapping.items():
                        for key in possible_keys:
                            if key in raw_counters:
                                if source == 'weblogs':
                                    weblogs_counter = raw_counters[key]
                                elif source == 'gsc':
                                    gsc_counter = raw_counters[key]
                                elif source == 'not_indexable':
                                    not_indexable_counter = raw_counters[key]
                                break
                    
                    # Find parameters that meet our criteria
                    if gsc_counter and (weblogs_counter or not_indexable_counter):
                        # Combine weblogs and not_indexable counters
                        combined_counter = Counter()
                        if weblogs_counter:
                            combined_counter.update(weblogs_counter)
                        if not_indexable_counter:
                            combined_counter.update(not_indexable_counter)
                        
                        # Calculate breakpoints with GSC=0 (only needed once)
                        # Identify frequencies where parameter counts change significantly
                        if gsc_threshold == 0:
                            # Get all frequencies sorted in descending order
                            all_frequencies = sorted(set(combined_counter.values()), reverse=True)
                            param_counts = {}
                            
                            # Calculate how many parameters at each frequency
                            for freq in all_frequencies:
                                # Count params with GSC ≤ 0 and frequency ≥ freq
                                count = sum(1 for param, count in combined_counter.items() 
                                           if gsc_counter.get(param, 0) <= 0 and count >= freq)
                                param_counts[freq] = count
                            
                            # Find breakpoints where param count changes from <5 to ≥5, etc.
                            ranges = [(5, 15), (15, 30), (30, 50), (50, 100)]
                            for min_count, max_count in ranges:
                                for i, freq in enumerate(all_frequencies):
                                    if param_counts[freq] >= min_count and param_counts[freq] <= max_count:
                                        # Found a frequency in our desired range
                                        breakpoint_frequencies.append((freq, param_counts[freq]))
                                        break
                        
                        # Apply our filtering criteria
                        for param, count in combined_counter.items():
                            param_gsc_count = gsc_counter.get(param, 0)
                            
                            # Check if this parameter meets our criteria
                            if param_gsc_count <= gsc_threshold and count >= min_frequency:
                                # Calculate score
                                score = count / (param_gsc_count + 1)
                                matching_params.append((param, count, param_gsc_count, score))
                                param_count += 1
                                total_frequency += count
                        
                        # Sort by score descending
                        matching_params.sort(key=lambda x: x[3], reverse=True)
        except Exception as e:
            logging.error(f"Error in parameter preview: {str(e)}")
            return Div(P(f"Error: {str(e)}", style="color: red;"))
        
        # Create breakpoints info if we've calculated it
        breakpoints_info = ""
        if breakpoint_frequencies and gsc_threshold == 0:
            breakpoints_info = Div(
                H5("Meaningful Min Frequency Values (with GSC=0):", style="margin-bottom: 5px; color: #ccc;"),
                Table(
                    *[Tr(
                        Td(f"Show ~{count} parameters:", style="color: #bbb; padding-right: 10px;"),
                        Td(f"{freq:,}", style="color: #ff8c00; font-weight: bold; text-align: right;")
                    ) for freq, count in breakpoints_info],
                    style="margin-bottom: 10px; font-size: 0.9em;"
                ),
                style="background: #222; padding: 10px; border-radius: 5px; margin-bottom: 15px;"
            )
        
        # Create the output UI with optional breakpoints info
        if matching_params:
            display_limit = 5000
            display_message = ""
            if param_count > display_limit:
                display_message = f"(Displaying first {display_limit:,} of {param_count:,} matching parameters)"
            
            return Div(
                P(f"Found {param_count:,} parameters with total frequency of {total_frequency:,}"),
                P(display_message, style="color: #888; font-style: italic; margin-bottom: 10px;") if display_message else None,
                # Remove breakpoints_info from here
                Table(
                    Tr(
                        Th("Parameter", style="text-align: left; color: cyan;"),
                        Th("Frequency", style="text-align: right; color: #4fa8ff;"),
                        Th("GSC", style="text-align: right; color: #50fa7b;"),
                        Th("Score", style="text-align: right; color: yellow;")
                    ),
                    *[Tr(
                        Td(param, style="color: cyan;"),
                        Td(f"{count:,}", style="text-align: right; color: #4fa8ff;"),
                        Td(f"{gsc_count:,}", style="text-align: right; color: #50fa7b;"),
                        Td(f"{score:,.0f}", style="text-align: right; color: yellow; font-weight: bold;")
                    ) for param, count, gsc_count, score in matching_params[:display_limit]],
                    style="width: 100%; border-collapse: collapse;"
                ),
                style="font-family: monospace;"
            )
        else:
            return P("No parameters match these criteria. Try adjusting the thresholds.", 
                    style="color: #ff5555; font-style: italic;")

    # Add this script to handle the frequency links
    Script('''
    function setFrequencyAndPreview(value) {
        // Update both the slider and the number input
        const slider = document.getElementById("min_frequency_slider");
        const input = document.getElementById("min_frequency");
        
        // Set values
        slider.value = value;
        input.value = value;
        
        // Trigger the parameter preview
        triggerParameterPreview();
        
        // Optional: Add visual feedback
        input.style.backgroundColor = "#224433";
        setTimeout(function() {
            input.style.backgroundColor = "";
        }, 500);
    }
    ''')

    async def step_07(self, request):
        """Handles GET request for Step 7 Markdown widget."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_07"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        
        # Get parameter data from step_06
        step_06_data = pip.get_step_data(pipeline_id, "step_06", {})
        parameters_info = {}
        
        try:
            if step_06_data.get("parameter_optimization"):
                param_data = json.loads(step_06_data.get("parameter_optimization"))
                parameters_info = {
                    "selected_params": param_data.get("selected_params", []),
                    "gsc_threshold": param_data.get("gsc_threshold", "0"),
                    "min_frequency": param_data.get("min_frequency", "100000")
                }
        except (json.JSONDecodeError, TypeError):
            parameters_info = {"selected_params": [], "gsc_threshold": "0", "min_frequency": "100000"}
        
        # Try to get stored markdown content or use default sample
        try:
            markdown_data = json.loads(step_data.get(step.done, "{}"))
            markdown_content = markdown_data.get("markdown", "")
        except (json.JSONDecodeError, TypeError):
            markdown_content = ""
            
        # Use sample markdown if empty, enhanced with parameter information
        if not markdown_content:
            # Get parameters list for documentation
            params_list = parameters_info.get("selected_params", [])
            gsc_threshold = parameters_info.get("gsc_threshold", "0")
            min_frequency = parameters_info.get("min_frequency", "100000")
            
            # Convert string values to integers for formatting
            try:
                min_frequency_int = int(min_frequency)
                min_frequency_formatted = f"{min_frequency_int:,}"
            except ValueError:
                min_frequency_formatted = min_frequency

            # Create robots.txt rules for the parameters - show all of them
            robots_txt_rules = "\n".join([f"Disallow: /*?*{param}=*" for param in params_list])

            # Create parameter list string - show all parameters without truncation
            param_list_str = "\n".join([f"- `{param}`" for param in params_list])

            # Create more condensed markdown content with details tags OUTSIDE list items
            markdown_content = f"""# Parameter Buster Documentation

## Instructions
1. Copy/Paste that JavaScript into a new PageWorkers custom Optimization.
2. Update the `REPLACE_ME!!!` with the ID found in the URL of the Optimization.

**Parameter Optimization Settings**
- GSC Threshold: {gsc_threshold}
- Minimum Frequency: {min_frequency_formatted}
- Total Parameters Optimized: {len(params_list)}

[[DETAILS_START]]
[[SUMMARY_START]]View all {len(params_list)} parameters[[SUMMARY_END]]

{param_list_str}
[[DETAILS_END]]

[[DETAILS_START]]
[[SUMMARY_START]]View robots.txt rules[[SUMMARY_END]]

```robots.txt
User-agent: *
{robots_txt_rules}
```
[[DETAILS_END]]

**Important Notes:** robots.txt is advisory, not enforcement; prevents crawling but not indexing; for testing only
"""

            # On first run, automatically save the default markdown to enable chain reaction
            # This is a special case for this workflow step only
            if step_data.get(step.done, "") == "":  # Only if truly empty, not just JSON parse issue
                markdown_data = {
                    "markdown": markdown_content,
                    "parameters_info": parameters_info  # Store parameters info in the step data
                }
                
                # Use our custom method instead of pip.update_step_state
                await self.update_state_with_html(pipeline_id, step_id, markdown_data, steps, clear_previous=False)
                # After saving, we'll still show the display state but state is now officially saved
        
        # Generate a unique ID for this instance
        widget_id = f"markdown-widget-{pipeline_id.replace('-', '_')}-{step_id}"
        
        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data:
            # Create markdown widget directly for finalized state
            markdown_widget = self.create_marked_widget(markdown_content, widget_id)
            
            from starlette.responses import HTMLResponse
            from fasthtml.common import to_xml
            
            response = HTMLResponse(
                to_xml(
                    Div(
                        Card(
                            H3(f"🔒 {step.show}"),
                            markdown_widget
                        ),
                        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                        id=step_id
                    )
                )
            )
            
            # Add HX-Trigger to initialize markdown rendering
            response.headers["HX-Trigger"] = json.dumps({
                "initializeMarked": {"targetId": widget_id}
            })
            
            return response
                
        # Check if step is complete and not being reverted to
        if markdown_content and state.get("_revert_target") != step_id:
            # Create markdown widget for completed state
            markdown_widget = self.create_marked_widget(markdown_content, widget_id)
            
            from starlette.responses import HTMLResponse
            from fasthtml.common import to_xml
            
            response = HTMLResponse(
                to_xml(
                    Div(
                        pip.widget_container(
                            step_id=step_id,
                            app_name=app_name,
                            message=f"{step.show}: Markdown Documentation",
                            widget=markdown_widget,
                            steps=steps
                        ),
                        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                        id=step_id
                    )
                )
            )
            
            # Add HX-Trigger to initialize markdown rendering
            response.headers["HX-Trigger"] = json.dumps({
                "initializeMarked": {"targetId": widget_id}
            })
            
            return response
        else:
            # When going into edit mode, clear the finalize state to prevent finalize button display
            if "finalized" in finalize_data:
                await pip.clear_steps_from(pipeline_id, "finalize", steps)
            
            # Show input form for editing markdown content
            await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
            
            return Div(
                Card(
                    H3(f"{step.show}"),
                    P("Edit the Markdown documentation for the Parameter Buster workflow:"),
                    Form(
                        Textarea(
                            markdown_content,
                            name="markdown_content",
                            rows="15",
                            style="width: 100%; font-family: monospace;"
                        ),
                        Div(
                            Button("Update Documentation ▸", type="submit", cls="primary"),
                            style="margin-top: 10px; text-align: right;"
                        ),
                        hx_post=f"/{app_name}/{step_id}_submit", 
                        hx_target=f"#{step_id}"
                    )
                ),
                Div(id=next_step_id),  # The only condition (Update) where chain reaction is not needed
                id=step_id
            )

    async def step_07_submit(self, request):
        """Process the markdown content submission for Step 7."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_07"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")

        # Get markdown content from form
        form = await request.form()
        markdown_content = form.get("markdown_content", "")
        
        # Get parameters info from previous state if it exists
        existing_data = {}
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        try:
            if step_data.get(step.done):
                existing_data = json.loads(step_data.get(step.done, "{}"))
        except json.JSONDecodeError:
            pass
        
        # Get parameters info from step_06 if not in existing data
        parameters_info = existing_data.get("parameters_info", {})
        if not parameters_info:
            step_06_data = pip.get_step_data(pipeline_id, "step_06", {})
            try:
                if step_06_data.get("parameter_optimization"):
                    param_data = json.loads(step_06_data.get("parameter_optimization"))
                    parameters_info = {
                        "selected_params": param_data.get("selected_params", []),
                        "gsc_threshold": param_data.get("gsc_threshold", "0"),
                        "min_frequency": param_data.get("min_frequency", "100000")
                    }
            except (json.JSONDecodeError, TypeError):
                parameters_info = {"selected_params": [], "gsc_threshold": "0", "min_frequency": "100000"}
        
        # Store the markdown content with parameters info
        markdown_data = {
            "markdown": markdown_content,
            "parameters_info": parameters_info
        }
        data_str = json.dumps(markdown_data)
        await self.update_state_with_html(pipeline_id, step_id, markdown_data, steps)
        await self.message_queue.add(pip, f"{step.show}: Markdown content updated", verbatim=True)
        
        # Generate a unique ID for the markdown widget
        widget_id = f"markdown-widget-{pipeline_id.replace('-', '_')}-{step_id}"
        
        # Create the markdown widget
        markdown_widget = self.create_marked_widget(markdown_content, widget_id)
        
        # Return with widget container and chain reaction to next step
        from starlette.responses import HTMLResponse
        from fasthtml.common import to_xml
        
        response = HTMLResponse(
            to_xml(
                Div(
                    pip.widget_container(
                        step_id=step_id,
                        app_name=app_name,
                        message=f"{step.show}: Markdown Documentation",
                        widget=markdown_widget,
                        steps=steps
                    ),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                    id=step_id
                )
            )
        )
        
        # Add HX-Trigger to initialize markdown rendering
        response.headers["HX-Trigger"] = json.dumps({
            "initializeMarked": {"targetId": widget_id}
        })
        
        return response

    def create_marked_widget(self, markdown_content, widget_id):
        """Create a Marked.js markdown rendering widget with special tag handling."""
        # Replace our special encodings with actual HTML tags
        # This happens after logging so it won't trigger errors
        processed_content = markdown_content
        processed_content = processed_content.replace("[[DETAILS_START]]", "<details>")
        processed_content = processed_content.replace("[[DETAILS_END]]", "</details>")
        processed_content = processed_content.replace("[[SUMMARY_START]]", "<summary>")
        processed_content = processed_content.replace("[[SUMMARY_END]]", "</summary>")
        
        # The hidden textarea holds the raw markdown content
        textarea_id = f"{widget_id}_content"
        
        return Div(
            # Hidden textarea containing raw markdown
            Textarea(
                processed_content,  # Use the processed content with real HTML tags
                id=textarea_id,
                style="display: none;"
            ),
            # Container for rendered markdown
            Div(
                id=f"{widget_id}_output",
                cls="markdown-body",
                style="padding: 15px; background-color: var(--pico-card-background-color); border-radius: var(--pico-border-radius);"
            ),
            # Script to initialize marked.js rendering
            Script(f"""
            (function() {{
                function renderMarkdown() {{
                    if (typeof marked === 'undefined') {{
                        console.error('Marked.js library not loaded');
                        return;
                    }}
                    
                    const textarea = document.getElementById('{textarea_id}');
                    const output = document.getElementById('{widget_id}_output');
                    
                    if (textarea && output) {{
                        // Configure marked options if needed
                        marked.setOptions({{
                            breaks: true,
                            gfm: true,
                            headerIds: true
                        }});
                        
                        // Render the markdown content
                        const rawMarkdown = textarea.value;
                        output.innerHTML = marked.parse(rawMarkdown);
                        
                        console.log('Markdown rendered for {widget_id}');
                    }} else {{
                        console.error('Markdown elements not found for {widget_id}');
                    }}
                }}
                
                // Try to render immediately
                renderMarkdown();
                
                // Also listen for initialization event
                document.body.addEventListener('initialize-marked', function(e) {{
                    if (e.detail && e.detail.targetId === '{widget_id}') {{
                        console.log('Markdown initialization event received for {widget_id}');
                        renderMarkdown();
                    }}
                }});
            }})();
            """),
            id=widget_id
        )

    async def update_state_with_html(self, pipeline_id, step_id, data, steps, clear_previous=True):
        """Helper method to update state while avoiding HTML logging issues"""
        pip = self.pipulate
        
        # Get current state to modify directly
        state = pip.read_state(pipeline_id)
        
        # Convert to string if needed
        if isinstance(data, dict):
            data_str = json.dumps(data)
        else:
            data_str = data
        
        # Update step in the state directly
        if step_id not in state:
            state[step_id] = {}
        
        # Store the data
        state[step_id][steps[self.steps_indices[step_id]].done] = data_str
        
        # If this should clear subsequent steps
        if clear_previous:
            pip.clear_state_from_step(state, step_id, steps)
        
        # Clear revert target if any
        if "_revert_target" in state:
            del state["_revert_target"]
        
        # Write the state directly (bypasses logging in update_step_state)
        pip.write_state(pipeline_id, state)
"""
=============================================================================
Botify CSV Export Workflow
=============================================================================

Core functionality for exporting Botify data to CSV files with:
- Project URL validation
- Analysis selection
- Depth calculation
- Field selection
- Export job management
- Download handling

The workflow is organized into these main sections:
1. Core Setup & Configuration
2. Step Handlers (step_01 through step_04)
3. Export Job Management
4. File & Directory Management
5. API Integration
6. UI Helper Functions
7. State Management
"""

# ============================================================================
# 1. IMPORTS & CONFIGURATION
# ============================================================================

import asyncio
from collections import namedtuple
from datetime import datetime
from urllib.parse import urlparse
import httpx
from pathlib import Path
import json
import os

from fasthtml.common import *
from loguru import logger

# Core configuration
EXPORT_REGISTRY_FILE = Path("downloads/export_registry.json")
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))

# ============================================================================
# 2. CORE CLASS & INITIALIZATION
# ============================================================================

class BotifyExport:
    """
    Botify CSV Export Workflow
    
    This workflow helps users export data from Botify projects and download it as CSV files.
    It demonstrates usage of rich UI components like directory trees alongside standard
    form inputs and revert controls.
    
    Implementation Note on Tree Displays:
    ------------------------------------
    The tree display for file paths uses the standardized pip.revert_control_advanced method,
    which provides consistent styling and layout for displaying additional content below
    the standard revert controls. This ensures proper alignment with revert buttons 
    while maintaining visual grouping.
    
    Example usage:
    ```python
    tree_display = pip.tree_display(tree_path)
    content_container = pip.revert_control_advanced(
        step_id=step_id,
        app_name=app_name,
        message=display_msg,
        content=tree_display,
        steps=steps
    )
    ```
    
    This standardized pattern eliminates the need for workflow-specific spacing adjustments
    and ensures consistent styling across the application.
    """
    APP_NAME = "botify_csv"
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
            Step(id='step_04', done='export_url', show='CSV Export', refill=False),
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

        # Add routes for CSV export functionality
        app.route(f"/{app_name}/download_csv", methods=["POST"])(self.download_csv)
        app.route(f"/{app_name}/download_progress")(self.download_progress)
        app.route(f"/{app_name}/download_job_status")(self.download_job_status)
        app.route(f"/{app_name}/use_existing_export", methods=["POST"])(self.use_existing_export)
        app.route(f"/{app_name}/step_04/new")(self.step_04_new)
        app.route(f"/{app_name}/check_export_status", methods=["POST"])(self.check_export_status)
        app.route(f"/{app_name}/download_ready_export", methods=["POST"])(self.download_ready_export)

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

# ============================================================================
# 3. WORKFLOW STEP HANDLERS
# ============================================================================

    # -----------------
    # Step 1: Project URL
    # -----------------
    async def step_01(self, request):
        """Handle project URL input"""
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

    # -----------------
    # Step 2: Analysis Selection
    # -----------------
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
            
            # Get downloaded analyses
            downloaded_analyses = self.find_downloaded_analyses(org, project)
            
            # Organize analyses with downloaded ones first
            prioritized_slugs = []
            
            # Add downloaded analyses first, maintaining their original order in the slug list
            for slug in slugs:
                if slug in downloaded_analyses:
                    prioritized_slugs.append((slug, True))  # True = downloaded
            
            # Add remaining analyses
            for slug in slugs:
                if slug not in downloaded_analyses:
                    prioritized_slugs.append((slug, False))  # False = not downloaded
            
            # Determine selected value:
            # - Use previous selection if it exists and we're reverting
            # - Otherwise prioritize downloaded analyses, then use the most recent analysis
            selected_value = user_val if user_val else (prioritized_slugs[0][0] if prioritized_slugs else "")
            
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
                                        f"{slug} {'(Downloaded)' if is_downloaded else ''}",
                                        value=slug,
                                        selected=(slug == selected_value)
                                    ) for slug, is_downloaded in prioritized_slugs
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

        # Update state using helper
        await pip.update_step_state(pipeline_id, step_id, user_val, steps)

        # Send confirmation message
        await self.message_queue.add(pip, f"{step.show}: {user_val}", verbatim=True)
        
        # Check if we need finalize prompt
        if pip.check_finalize_needed(step_index, steps):
            await self.message_queue.add(pip, "All steps complete! Please press the Finalize button below to save your data.", verbatim=True)
        
        # Return navigation controls
        return pip.create_step_navigation(step_id, step_index, steps, app_name, user_val)

    # -----------------
    # Step 3: Maximum Click Depth
    # -----------------
    async def step_03(self, request):
        """
        Display the maximum safe click depth based on cumulative URL counts.
        Shows both the calculated depth and detailed URL count information.
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
            max_depth, safe_count, next_count = await self.calculate_max_safe_depth(org, project, analysis, api_token)
            
            if max_depth is None:
                return P("Could not calculate maximum depth. Please check your API access and try again.", 
                        style=pip.get_style("error"))

            # Show the form with the calculated depth and detailed counts
            await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
            
            # Format the counts with commas for readability
            safe_count_fmt = f"{safe_count:,}" if safe_count is not None else "unknown"
            
            # Prepare the explanation text
            if next_count is not None:
                next_count_fmt = f"{next_count:,}"
                explanation = (
                    f"At depth {max_depth}, the export will include {safe_count_fmt} URLs.\n"
                    f"Going to depth {max_depth + 1} would exceed the limit with {next_count_fmt} URLs."
                )
            else:
                explanation = (
                    f"The entire site can be exported with {safe_count_fmt} URLs.\n"
                    f"This is under the 1 million URL limit."
                )
            
            return Div(
                Card(
                    H4(f"{pip.fmt(step_id)}: {step.show}"),
                    P(f"Based on URL counts, the maximum safe depth is: {max_depth}", 
                      style="margin-bottom: 1rem;"),
                    P(explanation,
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

    # -----------------
    # Step 4: Export Configuration
    # -----------------
    async def step_04(self, request):
        """Display the CSV export form with field selection options"""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
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
            # For finalized state, show the download link if available
            download_url = step_data.get('download_url')
            local_file = step_data.get('local_file')
            
            if local_file and Path(local_file).exists():
                # Get just the relative path for display
                try:
                    rel_path = Path(local_file).relative_to(Path.cwd())
                    tree_path = self.format_path_as_tree(rel_path)
                    
                    # Use the new finalized_content helper
                    tree_display = pip.tree_display(tree_path)
                    finalized_card = pip.finalized_content(
                        message=f"🔒 {step.show}: CSV file downloaded to:",
                        content=tree_display
                    )
                    
                    return Div(
                        finalized_card,
                        Div(id=next_step_id, hx_get=f"/{self.app_name}/{next_step_id}", hx_trigger="load")
                    )
                except ValueError:
                    # Fallback if relative_to fails
                    tree_path = self.format_path_as_tree(local_file)
                    
                    # Use the new finalized_content helper
                    tree_display = pip.tree_display(tree_path)
                    finalized_card = pip.finalized_content(
                        message=f"🔒 {step.show}: CSV file downloaded to:",
                        content=tree_display
                    )
                    
                    return Div(
                        finalized_card,
                        Div(id=next_step_id, hx_get=f"/{self.app_name}/{next_step_id}", hx_trigger="load")
                    )
            elif download_url:
                download_msg = f"🔒 {step.show}: Ready for download"
                return Div(
                    Card(download_msg),
                    Div(id=next_step_id, hx_get=f"/{self.app_name}/{next_step_id}", hx_trigger="load")
                )
            else:
                # Get a cleaner job ID for display
                job_id = user_val.split('/')[-1] if user_val else "Unknown"
                clean_job_id = self.clean_job_id_for_display(job_id)
                
                download_msg = f"🔒 {step.show}: Job ID {clean_job_id}"
                return Div(
                    Card(download_msg),
                    Div(id=next_step_id, hx_get=f"/{self.app_name}/{next_step_id}", hx_trigger="load")
                )

        # Check if step is complete and either not being reverted, or has the preserve flag
        # The _preserve_completed flag ensures the step stays in completed state after unfinalization
        if user_val and (state.get("_revert_target") != step_id or step_data.get("_preserve_completed")):
            job_id = user_val.split("/")[-1] if user_val else "Unknown"
            download_url = step_data.get('download_url')
            local_file = step_data.get('local_file')
            
            # Create a consistent container that will preserve the HTMX chain reaction
            content_container = Div(id=f"{step_id}-content")
            
            # Display different message based on download status
            if local_file and Path(local_file).exists():
                try:
                    rel_path = Path(local_file).relative_to(Path.cwd())
                    tree_path = self.format_path_as_tree(rel_path)
                    
                    # Display the tree path in a Pre component
                    # Add this to the existing structure rather than replacing it
                    display_msg = f"{step.show}: CSV file downloaded (Job ID {job_id})"
                    
                    # Get a cleaner job ID for display (without the full filename)
                    clean_job_id = self.clean_job_id_for_display(job_id)
                    
                    # Create the revert control with the shortened message parameter
                    display_msg = f"{step.show}: CSV file downloaded ({clean_job_id})"
                    
                    # Use the new advanced control with tree content
                    tree_display = pip.tree_display(tree_path)
                    content_container = pip.revert_control_advanced(
                        step_id=step_id,
                        app_name=app_name,
                        message=display_msg,
                        content=tree_display,
                        steps=steps
                    )
                    
                except ValueError:
                    # Fallback if relative_to fails
                    tree_path = self.format_path_as_tree(local_file)
                    
                    # Get a cleaner job ID for display (without the full filename)
                    clean_job_id = self.clean_job_id_for_display(job_id)
                    
                    # Create the revert control with the shortened message parameter
                    display_msg = f"{step.show}: CSV file downloaded ({clean_job_id})"
                    
                    # Use the advanced revert control with tree content
                    tree_display = pip.tree_display(tree_path)
                    content_container = pip.revert_control_advanced(
                        step_id=step_id,
                        app_name=app_name,
                        message=display_msg,
                        content=tree_display,
                        steps=steps
                    )
            elif download_url:
                display_msg = f"{step.show}: Ready for download (Job ID {job_id})"
                
                # Get a cleaner job ID for display
                clean_job_id = self.clean_job_id_for_display(job_id)
                
                display_msg = f"{step.show}: Ready for download ({clean_job_id})"
                revert_control = pip.revert_control(
                    step_id=step_id, 
                    app_name=app_name, 
                    message=display_msg, 
                    steps=steps
                )
                content_container = revert_control
            else:
                # Poll the job status to check if it's complete
                try:
                    api_token = self.read_api_token()
                    is_complete, download_url, _ = await self.poll_job_status(user_val, api_token)
                    
                    if is_complete and download_url:
                        # Update the state with the download URL
                        state[step_id]['download_url'] = download_url
                        state[step_id]['status'] = 'DONE'
                        pip.write_state(pipeline_id, state)
                        
                        # Also update the registry
                        if 'org' in step_data and 'project' in step_data and 'analysis' in step_data and 'depth' in step_data:
                            self.update_export_job(
                                step_data['org'], 
                                step_data['project'], 
                                step_data['analysis'], 
                                step_data['depth'],
                                job_id,
                                {'status': 'DONE', 'download_url': download_url}
                            )
                        
                        # Get a cleaner job ID for display
                        clean_job_id = self.clean_job_id_for_display(job_id)
                        
                        display_msg = f"{step.show}: Ready for download ({clean_job_id})"
                    else:
                        # Get a cleaner job ID for display
                        clean_job_id = self.clean_job_id_for_display(job_id)
                        
                        display_msg = f"{step.show}: Processing ({clean_job_id})"
                except Exception:
                    # Get a cleaner job ID for display
                    clean_job_id = self.clean_job_id_for_display(job_id)
                    
                    display_msg = f"{step.show}: Job ID {clean_job_id}"
                
                revert_control = pip.revert_control(
                    step_id=step_id, 
                    app_name=app_name, 
                    message=display_msg, 
                    steps=steps
                )
                content_container = revert_control
            
            # Add a download button if the file is ready but not yet downloaded
            if download_url and not (local_file and Path(local_file).exists()):
                download_button = Form(
                    Button("Download CSV", type="submit", cls="secondary outline"),
                    hx_post=f"/{app_name}/download_csv",
                    hx_target=f"#{step_id}",
                    hx_swap="outerHTML",
                    hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}'
                )
                
                # Use a consistent structure to maintain the HTMX chain reaction
                return Div(
                    content_container,
                    download_button,
                    # This is the critical element that ensures the chain reaction continues
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                    id=step_id
                )
            
            # Use a consistent structure for all return paths
            return Div(
                content_container,
                # This is the critical element that ensures the chain reaction continues
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )

        # Get data from previous steps
        step_01_data = pip.get_step_data(pipeline_id, "step_01", {})
        step_02_data = pip.get_step_data(pipeline_id, "step_02", {})
        step_03_data = pip.get_step_data(pipeline_id, "step_03", {})
        
        org = step_01_data.get('org')
        project = step_01_data.get('project')
        analysis = step_02_data.get('analysis')
        depth = step_03_data.get('depth')
        
        # Check if we have all required data
        if not all([org, project, analysis, depth]):
            return P("Missing required data from previous steps. Please complete all steps first.", 
                    style=pip.get_style("error"))

        # Check for existing jobs in the registry
        existing_jobs = self.find_export_jobs(org, project, analysis, depth)
        completed_jobs = [job for job in existing_jobs if job['status'] == 'DONE' and job.get('download_url')]
        processing_jobs = [job for job in existing_jobs if job['status'] == 'PROCESSING']
        
        # Check if any processing jobs are actually done
        if processing_jobs:
            api_token = self.read_api_token()
            for job in processing_jobs:
                job_url = job['job_url']
                job_id = job['job_id']
                try:
                    is_complete, download_url, _ = await self.poll_job_status(job_url, api_token)
                    if is_complete and download_url:
                        self.update_export_job(
                            org, project, analysis, depth, job_id,
                            {'status': 'DONE', 'download_url': download_url}
                        )
                        completed_jobs.append({**job, 'status': 'DONE', 'download_url': download_url})
                        processing_jobs.remove(job)
                except Exception as e:
                    logger.error(f"Error checking job status: {e}")
        
        # Look for completed jobs with local files
        downloaded_jobs = []
        for job in completed_jobs:
            if job.get('local_file') and Path(job['local_file']).exists():
                downloaded_jobs.append(job)
        
        # Check if an export with these parameters already exists
        existing_path = Path("downloads") / org / project / analysis
        existing_files = list(existing_path.glob(f"*depth_{depth}*.csv")) if existing_path.exists() else []
        
        if downloaded_jobs:
            # We have a downloaded job - offer to use it
            job = downloaded_jobs[0]
            local_file = job['local_file']
            file_path = Path(local_file)
            
            await self.message_queue.add(pip, f"Found existing downloaded export: {file_path.name}", verbatim=True)
            
            return Div(
                Card(
                    H4(f"{pip.fmt(step_id)}: {step.show}"),
                    P(f"An export for project '{project}', analysis '{analysis}' at depth {depth} has already been downloaded:", 
                      style="margin-bottom: 0.5rem;"),
                    P(f"Path:", style="margin-bottom: 0.5rem;"),
                    Pre(self.format_path_as_tree(file_path), style="margin-bottom: 1rem; white-space: pre;"),
                    Div(
                        Button("Use Existing Download", type="button", cls="primary", 
                               hx_post=f"/{app_name}/use_existing_export",
                               hx_target=f"#{step.id}",
                               hx_vals=f'{{"pipeline_id": "{pipeline_id}", "file_path": "{file_path}"}}'
                        ),
                        Button("Create New Export", type="button", 
                               hx_get=f"/{app_name}/{step.id}/new",
                               hx_target=f"#{step.id}"
                        ),
                        style="display: flex; gap: 1rem;"
                    )
                ),
                # Add this critical element to ensure the chain reaction continues to the finalize step
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load delay:100ms"),
                id=step.id
            )
        elif completed_jobs:
            # We have a completed job but no download - offer to download it
            job = completed_jobs[0]
            job_id = job['job_id']
            download_url = job['download_url']
            
            await self.message_queue.add(pip, f"Found existing completed export (Job ID: {job_id})", verbatim=True)
            
            return Div(
                Card(
                    H4(f"{pip.fmt(step_id)}: {step.show}"),
                    P(f"An export for project '{project}', analysis '{analysis}' at depth {depth} is ready to download:", 
                      style="margin-bottom: 1rem;"),
                    P(f"Job ID: {job_id}", style="margin-bottom: 0.5rem;"),
                    Div(
                        Button("Download Ready Export", type="button", cls="primary", 
                               hx_post=f"/{app_name}/download_ready_export",
                               hx_target=f"#{step.id}",
                               hx_vals=f'{{"pipeline_id": "{pipeline_id}", "job_id": "{job_id}", "download_url": "{download_url}"}}'
                        ),
                        Button("Create New Export", type="button", 
                               hx_get=f"/{app_name}/{step.id}/new",
                               hx_target=f"#{step.id}"
                        ),
                        style="display: flex; gap: 1rem;"
                    )
                ),
                # Add this critical element to ensure the chain reaction continues to the finalize step
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load delay:100ms"),
                id=step.id
            )
        elif processing_jobs:
            # We have a processing job - show its status
            job = processing_jobs[0]
            job_id = job['job_id']
            job_url = job['job_url']
            created = job.get('created', 'Unknown')
            
            # Try to parse the timestamp
            try:
                created_dt = datetime.fromisoformat(created)
                created_str = created_dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                created_str = created
            
            await self.message_queue.add(
                pip, 
                f"Found existing export job in progress (Job ID: {job_id}, Started: {created_str})", 
                verbatim=True
            )
            
            return Div(
                Card(
                    H4(f"{pip.fmt(step_id)}: {step.show}"),
                    P(f"An export for project '{project}', analysis '{analysis}' at depth {depth} is already processing:", 
                      style="margin-bottom: 1rem;"),
                    P(f"Job ID: {job_id}", style="margin-bottom: 0.5rem;"),
                    P(f"Started: {created_str}", style="margin-bottom: 0.5rem;"),
                    Div(
                        Progress(),  # PicoCSS indeterminate progress bar
                        P("Checking status automatically...", style="color: #666;"),
                        id="progress-container"
                    ),
                    Div(
                        Button("Create New Export", type="button", 
                               hx_get=f"/{app_name}/{step.id}/new",
                               hx_target=f"#{step.id}"
                        ),
                        style="margin-top: 1rem;"
                    )
                ),
                # Add this critical element to ensure the chain reaction continues to the finalize step
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load delay:100ms"),
                hx_get=f"/{app_name}/check_export_status",
                hx_trigger="load delay:2s",
                hx_target=f"#{step.id}",
                hx_vals=f'{{"pipeline_id": "{pipeline_id}", "job_url": "{job_url}"}}',
                id=step.id
            )
        elif existing_files:
            # Found existing files on disk but not in registry
            existing_file = existing_files[0]
            await self.message_queue.add(pip, f"Found existing export file: {existing_file.name}", verbatim=True)
            
            return Div(
                Card(
                    H4(f"{pip.fmt(step_id)}: {step.show}"),
                    P(f"An export file for project '{project}', analysis '{analysis}' at depth {depth} was found on disk:", 
                      style="margin-bottom: 0.5rem;"),
                    P(f"File: {existing_file.name}", style="margin-bottom: 1rem;"),
                    Div(
                        Button("Use Existing File", type="button", cls="primary", 
                               hx_post=f"/{app_name}/use_existing_export",
                               hx_target=f"#{step.id}",
                               hx_vals=f'{{"pipeline_id": "{pipeline_id}", "file_path": "{existing_file}"}}'
                        ),
                        Button("Create New Export", type="button", 
                               hx_get=f"/{app_name}/{step.id}/new",
                               hx_target=f"#{step.id}"
                        ),
                        style="display: flex; gap: 1rem;"
                    )
                ),
                Div(id=next_step_id),
                id=step.id
            )

        await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
        
        # Create the field selection form
        return Div(
            Card(
                H4(f"{pip.fmt(step_id)}: Configure {step.show}"),
                P(f"Export URLs up to depth {depth} from the {analysis} analysis.", 
                  style="margin-bottom: 1rem;"),
                P("Select additional fields to include in the export:", 
                  style="margin-bottom: 0.5rem;"),
                Form(
                    Div(
                        Label(
                            Input(type="checkbox", name="include_title", value="true", checked=True),
                            " Include page titles",
                            style="display: block; margin-bottom: 0.5rem;"
                        ),
                        Label(
                            Input(type="checkbox", name="include_meta_desc", value="true", checked=True),
                            " Include meta descriptions",
                            style="display: block; margin-bottom: 0.5rem;"
                        ),
                        Label(
                            Input(type="checkbox", name="include_h1", value="true", checked=True),
                            " Include H1 headings",
                            style="display: block; margin-bottom: 1rem;"
                        ),
                        style="margin-bottom: 1.5rem;"
                    ),
                    Button("Start Export", type="submit", cls="primary"),
                    P("Note: Large exports may take several minutes to process.", 
                      style="font-size: 0.8em; color: #666; margin-top: 0.5rem;"),
                    hx_post=f"/{app_name}/{step.id}_submit",
                    hx_target=f"#{step.id}"
                )
            ),
            Div(id=next_step_id),
            id=step.id
        )

    async def step_04_submit(self, request):
        """Handle the submission of the CSV export options and start the export job"""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Handle finalized state using helper
        if step.done == 'finalized':
            return await pip.handle_finalized_step(pipeline_id, step_id, steps, app_name, self)

        # Get form data
        form = await request.form()
        include_title = form.get("include_title") == "true"
        include_meta_desc = form.get("include_meta_desc") == "true"
        include_h1 = form.get("include_h1") == "true"
        
        # Get data from previous steps
        state = pip.read_state(pipeline_id)
        step_01_data = pip.get_step_data(pipeline_id, "step_01", {})
        step_02_data = pip.get_step_data(pipeline_id, "step_02", {})
        step_03_data = pip.get_step_data(pipeline_id, "step_03", {})
        
        org = step_01_data.get('org')
        project = step_01_data.get('project')
        analysis = step_02_data.get('analysis')
        depth = step_03_data.get('depth')
        
        # Check if we have all required data
        if not all([org, project, analysis, depth]):
            return P("Missing required data from previous steps.", style=pip.get_style("error"))
        
        # Check if there's already an export job with these parameters
        existing_jobs = self.find_export_jobs(org, project, analysis, depth)
        completed_jobs = [job for job in existing_jobs if job['status'] == 'DONE' and job.get('download_url')]
        processing_jobs = [job for job in existing_jobs if job['status'] == 'PROCESSING']
        
        # Check if any processing jobs have completed
        if processing_jobs:
            api_token = self.read_api_token()
            for job in processing_jobs[:]:  # Use a copy for iteration
                job_url = job['job_url']
                job_id = job['job_id']
                try:
                    is_complete, download_url, _ = await self.poll_job_status(job_url, api_token)
                    if is_complete and download_url:
                        # Update the job status in the registry
                        self.update_export_job(
                            org, project, analysis, depth, job_id,
                            {'status': 'DONE', 'download_url': download_url}
                        )
                        # Move from processing to completed
                        job_with_url = {**job, 'status': 'DONE', 'download_url': download_url}
                        completed_jobs.append(job_with_url)
                        processing_jobs.remove(job)
                except Exception as e:
                    logger.error(f"Error checking job status: {e}")
        
        # If there's a completed job, offer to download it instead of starting a new one
        if completed_jobs:
            job = completed_jobs[0]
            job_id = job['job_id']
            download_url = job['download_url']
            
            # Update the state with the existing job information
            if step_id not in state:
                state[step_id] = {}
            
            state[step_id].update({
                'job_url': job['job_url'],
                'job_id': job_id,
                'org': org,
                'project': project,
                'analysis': analysis,
                'depth': depth,
                'download_url': download_url,
                'status': 'DONE',
                'include_fields': {
                    'title': include_title,
                    'meta_desc': include_meta_desc,
                    'h1': include_h1
                }
            })
            
            # Store the job URL as the "done" field
            state[step_id][step.done] = job['job_url']
            
            # Write the state
            pip.write_state(pipeline_id, state)
            
            # Send message about reusing the existing export
            await self.message_queue.add(
                pip, 
                f"Using existing export job (ID: {job_id}).\n"
                f"This job has already completed and is ready for download.", 
                verbatim=True
            )
            
            # Create response UI for the existing job
            return Div(
                Card(
                    H4(f"Export Status: Complete ✅"),
                    P(f"Using existing export job ID: {job_id}", style="margin-bottom: 0.5rem;"),
                    P(f"The export with your requested parameters is ready for download.", 
                      style="margin-bottom: 1rem;"),
                    Form(
                        Button("Download CSV", type="submit", cls="primary"),
                        hx_post=f"/{app_name}/download_csv",
                        hx_target=f"#{step_id}",
                        hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}'
                    )
                ),
                # Remove the navigation that would trigger finalize
                # When user clicks Download CSV, they'll get the full navigation
                id=step_id
            )
        
        # If there's a processing job, show its status instead of starting a new one
        if processing_jobs:
            job = processing_jobs[0]
            job_id = job['job_id']
            job_url = job['job_url']
            
            # Update the state with the existing job information
            if step_id not in state:
                state[step_id] = {}
            
            state[step_id].update({
                'job_url': job_url,
                'job_id': job_id,
                'org': org,
                'project': project,
                'analysis': analysis,
                'depth': depth,
                'status': 'PROCESSING',
                'include_fields': {
                    'title': include_title,
                    'meta_desc': include_meta_desc,
                    'h1': include_h1
                }
            })
            
            # Do not store the job URL as "done" yet since the job is still processing
            # The done field will be populated when the job completes
            # state[step_id][step.done] = job_url
            state[step_id][step.done] = job_url
            
            # Write the state
            pip.write_state(pipeline_id, state)
            
            # Send message about the existing processing job
            created = job.get('created', 'Unknown')
            try:
                created_dt = datetime.fromisoformat(created)
                created_str = created_dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                created_str = created
                
            await self.message_queue.add(
                pip, 
                f"Using existing export job (ID: {job_id}).\n"
                f"This job is still processing (started: {created_str}).", 
                verbatim=True
            )
            
            # Create response UI for the processing job
            return Div(
                Card(
                    H4("Export Status: Processing ⏳"),
                    P(f"Using existing export job ID: {job_id}", style="margin-bottom: 0.5rem;"),
                    P(f"Started: {created_str}", style="margin-bottom: 0.5rem;"),
                    Div(
                        Progress(),  # PicoCSS indeterminate progress bar
                        P("Checking status automatically...", style="color: #666;"),
                        id="progress-container"
                    ),
                    hx_get=f"/{app_name}/download_job_status",
                    hx_trigger="load, every 2s",
                    hx_target=f"#{step_id}",
                    hx_swap="outerHTML",
                    hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}'
                ),
                # No navigation or other divs that would trigger chain reactions
                cls="polling-status no-chain-reaction",
                id=step_id
            )
        
        # No existing jobs - start a new one
        try:
            # Prepare fields to include
            include_fields = {
                'title': include_title,
                'meta_desc': include_meta_desc,
                'h1': include_h1
            }
            
            # Read API token
            api_token = self.read_api_token()
            
            # Create download directory
            download_dir = await self.create_download_directory(org, project, analysis)
            
            # Initiate the export job
            job_url, error = await self.initiate_export_job(
                org, project, analysis, depth, include_fields, api_token
            )
            
            if error:
                return P(f"Error initiating export: {error}", style=pip.get_style("error"))
            
            # Extract job ID for display
            job_id = job_url.split("/")[-1]
            
            # Register the export job in the registry
            self.register_export_job(org, project, analysis, depth, job_url, job_id)
            
            # Do a quick poll to see if the job completed very quickly
            is_complete, download_url, poll_error = await self.poll_job_status(job_url, api_token)
            
            # Update the registry if the job completed right away
            if is_complete and download_url:
                self.update_export_job(
                    org, project, analysis, depth, job_id,
                    {'status': 'DONE', 'download_url': download_url}
                )
            
            # Store job info in state
            if step_id not in state:
                state[step_id] = {}
            
            state[step_id].update({
                'job_url': job_url,
                'job_id': job_id,
                'org': org,
                'project': project,
                'analysis': analysis,
                'depth': depth,
                'download_url': download_url if is_complete else None,
                'status': 'DONE' if is_complete else 'PROCESSING',
                'download_path': str(download_dir),
                'include_fields': include_fields
            })
            
            # Store the job URL as the "done" field
            state[step_id][step.done] = job_url
            
            # Write the complete state back
            pip.write_state(pipeline_id, state)
            
            # Prepare status message
            if is_complete:
                status_msg = f"Export completed! Job ID: {job_id}\nThe export is ready for download."
            else:
                status_msg = f"Export job started with Job ID: {job_id}\nThe export is processing and may take several minutes."
            
            # Send message
            await self.message_queue.add(pip, status_msg, verbatim=True)
            
            # Create response UI
            status_display = "Complete ✅" if is_complete else "Processing ⏳"
            
            result_card = Card(
                H4(f"Export Status: {status_display}"),
                P(f"Job ID: {job_id}", style="margin-bottom: 0.5rem;"),
                P(f"Exporting URLs up to depth {depth}", style="margin-bottom: 0.5rem;"),
                P(f"Including fields: " + 
                  ", ".join([k for k, v in include_fields.items() if v]),
                  style="margin-bottom: 1rem;")
            )
            
            if is_complete:
                # If the job completed right away, show download button
                download_button = Form(
                    Button("Download CSV", type="submit", cls="primary"),
                    hx_post=f"/{app_name}/download_csv",
                    hx_target=f"#{step_id}",
                    hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}'
                )
                return Div(
                    result_card,
                    download_button,
                    # Add class to indicate this is a terminal response
                    # This DIV won't load any other steps automatically
                    cls="terminal-response no-chain-reaction",
                    id=step_id
                )
            else:
                # Otherwise show processing message with automatic polling
                return Div(
                    result_card,
                    P("Status updating automatically...", 
                      style="color: #666; margin-bottom: 1rem;"),
                    Div(
                        Progress(),  # PicoCSS indeterminate progress bar
                        P("Checking status automatically...", style="color: #666;"),
                        id="progress-container"
                    ),
                    # Only these HTMX attributes to continue polling - nothing else
                    # This breaks the chain reaction by not having any next-step HTMX attributes
                    cls="polling-status no-chain-reaction",
                    hx_get=f"/{app_name}/download_job_status",
                    hx_trigger="load, every 2s",
                    hx_target=f"#{step_id}",
                    hx_swap="outerHTML",
                    hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}',
                    id=step_id
                )
        
        except Exception as e:
            logger.error(f"Error in export submission: {str(e)}")
            return P(f"An error occurred: {str(e)}", style=pip.get_style("error"))

    async def step_04_new(self, request):
        """Handle new export creation"""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Get data from previous steps
        step_01_data = pip.get_step_data(pipeline_id, "step_01", {})
        step_02_data = pip.get_step_data(pipeline_id, "step_02", {})
        step_03_data = pip.get_step_data(pipeline_id, "step_03", {})
        
        org = step_01_data.get('org')
        project = step_01_data.get('project')
        analysis = step_02_data.get('analysis')
        depth = step_03_data.get('depth')
        
        # Create the field selection form for new export
        return Div(
            Card(
                H4(f"{pip.fmt(step_id)}: Configure {step.show}"),
                P(f"Export URLs up to depth {depth} from the {analysis} analysis.", 
                  style="margin-bottom: 1rem;"),
                P("Select additional fields to include in the export:", 
                  style="margin-bottom: 0.5rem;"),
                Form(
                    Div(
                        Label(
                            Input(type="checkbox", name="include_title", value="true", checked=True),
                            " Include page titles",
                            style="display: block; margin-bottom: 0.5rem;"
                        ),
                        Label(
                            Input(type="checkbox", name="include_meta_desc", value="true", checked=True),
                            " Include meta descriptions",
                            style="display: block; margin-bottom: 0.5rem;"
                        ),
                        Label(
                            Input(type="checkbox", name="include_h1", value="true", checked=True),
                            " Include H1 headings",
                            style="display: block; margin-bottom: 1rem;"
                        ),
                        style="margin-bottom: 1.5rem;"
                    ),
                    Button("Start Export", type="submit", cls="primary"),
                    P("Note: Large exports may take several minutes to process.", 
                      style="font-size: 0.8em; color: #666; margin-top: 0.5rem;"),
                    hx_post=f"/{app_name}/{step.id}_submit",
                    hx_target=f"#{step.id}"
                )
            ),
            Div(id=next_step_id),
            id=step.id
        )

    async def use_existing_export(self, request):
        """
        Use an existing export file instead of creating a new one
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        
        # Get form data
        form = await request.form()
        pipeline_id = form.get("pipeline_id")
        file_path = form.get("file_path")
        
        if not all([pipeline_id, file_path]):
            return P("Missing required parameters", style=pip.get_style("error"))
        
        # Update state with existing file information
        state = pip.read_state(pipeline_id)
        if step_id not in state:
            state[step_id] = {}
        
        state[step_id].update({
            'local_file': file_path,
            'status': 'DONE',
            'is_existing_file': True
        })
        
        # Set a dummy URL in the done field since we need something there
        state[step_id][step.done] = f"existing://{file_path}"
        pip.write_state(pipeline_id, state)
        
        # Send confirmation message
        await self.message_queue.add(pip, f"Using existing export file: {file_path}", verbatim=True)
        
        # Format the tree path for display
        rel_path = Path(file_path)
        try:
            rel_path = rel_path.relative_to(Path.cwd())
        except ValueError:
            # Already a relative path or outside CWD
            pass
        
        tree_path = self.format_path_as_tree(rel_path)
        display_msg = f"{step.show}: CSV file is ready"
        
        # Use the advanced revert control with tree content
        tree_display = pip.tree_display(tree_path)
        content_container = pip.revert_control_advanced(
            step_id=step_id,
            app_name=app_name,
            message=display_msg,
            content=tree_display,
            steps=steps
        )
        
        # Use the consistent structure for all return paths to maintain chain reaction
        return Div(
            content_container,
            # This is the critical element that ensures the chain reaction continues
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )

# ============================================================================
# 4. EXPORT JOB MANAGEMENT
# ============================================================================

    def get_export_key(self, org, project, analysis, depth):
        """Generate unique export key"""
        return f"{org}_{project}_{analysis}_depth_{depth}"

    def load_export_registry(self):
        """Load the export registry from file"""
        try:
            if EXPORT_REGISTRY_FILE.exists():
                with open(EXPORT_REGISTRY_FILE, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading export registry: {e}")
            return {}

    def save_export_registry(self, registry):
        """Save the export registry to file"""
        try:
            # Create directory if it doesn't exist
            EXPORT_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            with open(EXPORT_REGISTRY_FILE, 'w') as f:
                json.dump(registry, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving export registry: {e}")

    def register_export_job(self, org, project, analysis, depth, job_url, job_id):
        """Register a new export job in the registry"""
        registry = self.load_export_registry()
        export_key = self.get_export_key(org, project, analysis, depth)
        
        # Check if this export already exists
        if export_key not in registry:
            registry[export_key] = []
        
        # Add the new job
        registry[export_key].append({
            'job_url': job_url,
            'job_id': job_id,
            'status': 'PROCESSING',
            'created': datetime.now().isoformat(),
            'updated': datetime.now().isoformat(),
            'download_url': None,
            'local_file': None
        })
        
        self.save_export_registry(registry)
        return export_key

    def update_export_job(self, org, project, analysis, depth, job_id, updates):
        """Update an existing export job in the registry"""
        registry = self.load_export_registry()
        export_key = self.get_export_key(org, project, analysis, depth)
        
        if export_key not in registry:
            logger.error(f"Export key {export_key} not found in registry")
            return False
        
        for job in registry[export_key]:
            if job['job_id'] == job_id:
                job.update(updates)
                job['updated'] = datetime.now().isoformat()
                self.save_export_registry(registry)
                return True
        
        logger.error(f"Job ID {job_id} not found for export key {export_key}")
        return False

    def find_export_jobs(self, org, project, analysis, depth):
        """Find all export jobs for a specific configuration"""
        registry = self.load_export_registry()
        export_key = self.get_export_key(org, project, analysis, depth)
        return registry.get(export_key, [])

    def find_downloaded_analyses(self, org, project):
        """Find downloaded analyses for org/project"""
        registry = self.load_export_registry()
        downloaded_analyses = set()
        
        # Look for keys that match this org and project
        for key in registry.keys():
            if key.startswith(f"{org}_{project}_"):
                # Extract analysis name from the key (format: org_project_analysis_depth_X)
                parts = key.split('_')
                if len(parts) >= 3:
                    analysis = parts[2]
                    # Check if any job for this analysis has been downloaded
                    for job in registry[key]:
                        if job.get('status') == 'DONE' and job.get('local_file'):
                            downloaded_analyses.add(analysis)
                            break
        
        return list(downloaded_analyses)

# ============================================================================
# 5. FILE & DIRECTORY MANAGEMENT
# ============================================================================

    async def create_download_directory(self, org, project, analysis):
        """Create a nested directory structure for downloads"""
        download_path = Path("downloads") / org / project / analysis
        download_path.mkdir(parents=True, exist_ok=True)
        return download_path

    def format_path_as_tree(self, path_str):
        """
        Format a file path as a proper hierarchical ASCII tree with single path.
        
        This tree visualization is used in various places in the UI to show 
        download locations. The styling of the tree display is carefully tuned
        in each context where it appears.
        """
        path = Path(path_str)
            
        # Get the parts of the path
        parts = list(path.parts)
        
        # Build the tree visualization
        tree_lines = []
        
        # Root or first part
        if parts and parts[0] == '/':
            tree_lines.append('/')
            parts = parts[1:]
        elif len(parts) > 0:
            tree_lines.append(parts[0])
            parts = parts[1:]
        
        # Track the current level of indentation
        indent = ""
        
        # Add nested branches for each directory level
        for part in parts:
            tree_lines.append(f"{indent}└─{part}")
            # Increase indentation for next level, using spaces to align
            indent += "    "
            
        return '\n'.join(tree_lines)

    async def download_csv(self, request):
        """Handle CSV file download"""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        
        # Get form data
        form = await request.form()
        pipeline_id = form.get("pipeline_id")
        
        if not pipeline_id:
            return P("Missing pipeline_id parameter", style=pip.get_style("error"))
        
        # Get state data
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        
        # Extract necessary information
        download_url = step_data.get('download_url')
        org = step_data.get('org')
        project = step_data.get('project')
        analysis = step_data.get('analysis')
        depth = step_data.get('depth', '0')
        job_id = step_data.get('job_id', 'unknown')
        
        if not download_url:
            # Check if the job is complete and get the download URL
            try:
                job_url = step_data.get(step.done)
                if not job_url:
                    return P("No job URL found", style=pip.get_style("error"))
                    
                api_token = self.read_api_token()
                is_complete, download_url, error = await self.poll_job_status(job_url, api_token)
                
                if not is_complete or not download_url:
                    return Div(
                        P("Export job is still processing. Please try again in a few minutes.", style="margin-bottom: 1rem;"),
                        Progress(value="60", max="100", style="width: 100%;"),
                        P(f"Error: {error}" if error else "", style=pip.get_style("error"))
                    )
                    
                # Update state with download URL
                state[step_id]['download_url'] = download_url
                state[step_id]['status'] = 'DONE'
                pip.write_state(pipeline_id, state)
            except Exception as e:
                return P(f"Error checking job status: {str(e)}", style=pip.get_style("error"))
        
        # Create the download directory
        try:
            download_dir = await self.create_download_directory(org, project, analysis)
            
            # Generate filename based on depth and fields included
            include_fields = step_data.get('include_fields', {})
            fields_suffix = "_".join(k for k, v in include_fields.items() if v)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{org}_{project}_{analysis}_depth_{depth}_{fields_suffix}_{timestamp}.csv"
            
            local_file_path = download_dir / filename
            
            # Start downloading with progress feedback
            await self.message_queue.add(pip, f"Starting download from {download_url}", verbatim=True)
            
            # Show download progress
            return Div(
                Card(
                    H4("Downloading CSV File"),
                    P(f"Downloading export to {local_file_path}", style="margin-bottom: 1rem;"),
                    Progress(value="10", max="100", style="width: 100%;"),
                    P("Please wait, this may take a few minutes for large files...", 
                      style="font-size: 0.9em; color: #666;")
                ),
                hx_get=f"/{app_name}/download_progress",
                hx_trigger="load",
                hx_target=f"#{step_id}",
                hx_vals=f'{{"pipeline_id": "{pipeline_id}", "download_url": "{download_url}", "local_file": "{local_file_path}"}}',
                id=step_id
            )
        except Exception as e:
            return P(f"Error preparing download: {str(e)}", style=pip.get_style("error"))

    async def download_progress(self, request):
        """Handle download progress tracking"""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        
        # Get request data
        pipeline_id = request.query_params.get("pipeline_id")
        download_url = request.query_params.get("download_url")
        local_file = request.query_params.get("local_file")
        
        if not all([pipeline_id, download_url, local_file]):
            return P("Missing required parameters", style=pip.get_style("error"))
        
        local_file_path = Path(local_file)
        
        try:
            # Perform the actual download
            api_token = self.read_api_token()
            headers = {"Authorization": f"Token {api_token}"}
            
            # Create parent directories if they don't exist
            local_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download the file using httpx with streaming
            async with httpx.AsyncClient() as client:
                async with client.stream("GET", download_url, headers=headers, follow_redirects=True) as response:
                    response.raise_for_status()
                    
                    # Get content length if available
                    total_size = int(response.headers.get('content-length', 0))
                    
                    # Open file for writing
                    with open(local_file_path, 'wb') as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
            
            # Check if file needs to be unzipped
            if local_file_path.suffix.lower() in ('.zip', '.gz'):
                await self.message_queue.add(pip, f"Extracting {local_file_path}", verbatim=True)
                
                extracted_path = None
                # Unzip the file (implementation depends on file type)
                if local_file_path.suffix.lower() == '.zip':
                    import zipfile
                    
                    with zipfile.ZipFile(local_file_path, 'r') as zip_ref:
                        # Get the first CSV file in the archive
                        csv_files = [f for f in zip_ref.namelist() if f.lower().endswith('.csv')]
                        if not csv_files:
                            return P("No CSV files found in the downloaded ZIP archive", style=pip.get_style("error"))
                        
                        # Extract the CSV file
                        csv_file = csv_files[0]
                        extracted_path = local_file_path.parent / csv_file
                        zip_ref.extract(csv_file, local_file_path.parent)
                
                elif local_file_path.suffix.lower() == '.gz':
                    import gzip
                    import shutil
                    
                    # Assume it's a .csv.gz file and create a .csv file
                    extracted_path = local_file_path.with_suffix('')
                    with gzip.open(local_file_path, 'rb') as f_in:
                        with open(extracted_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                
                # Update the local file path to the extracted file if available
                if extracted_path:
                    local_file_path = extracted_path
            
            # Update state with local file path
            state = pip.read_state(pipeline_id)
            step_data = pip.get_step_data(pipeline_id, step_id, {})
            
            job_id = step_data.get('job_id')
            org = step_data.get('org')
            project = step_data.get('project')
            analysis = step_data.get('analysis')
            depth = step_data.get('depth')
            
            state[step_id]['local_file'] = str(local_file_path)
            pip.write_state(pipeline_id, state)
            
            # Update the registry if we have a job_id
            if job_id and all([org, project, analysis, depth]):
                self.update_export_job(
                    org, project, analysis, depth, job_id,
                    {'local_file': str(local_file_path)}
                )
            
            # Get file information
            file_size_bytes = local_file_path.stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            # Send success message
            await self.message_queue.add(
                pip, 
                f"Successfully downloaded and prepared CSV file:\n"
                f"Path: {local_file_path}\n"
                f"Size: {file_size_mb:.2f} MB", 
                verbatim=True
            )
            
            # Return success UI with file information
            # Format the directory path
            dir_tree = self.format_path_as_tree(str(local_file_path.parent))
            # Add the filename to the tree
            tree_path = f"{dir_tree}\n{'    ' * len(local_file_path.parent.parts)}└─{local_file_path.name}"
            tree_display = pip.tree_display(tree_path)
            return Div(
                pip.revert_control_advanced(
                    step_id=step_id,
                    app_name=app_name,
                    message=f"{step.show}: CSV downloaded ({file_size_mb:.2f} MB)",
                    content=tree_display,
                    steps=steps
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        
        except Exception as e:
            return Div(
                Card(
                    H4("Download Error"),
                    P(f"Error downloading CSV file: {str(e)}", style=pip.get_style("error")),
                    P(f"Download URL: {download_url}"),
                    P(f"Target file: {local_file_path}"),
                    Button("Try Again", type="button", cls="primary",
                           hx_post=f"/{app_name}/download_csv",
                           hx_target=f"#{step_id}",
                           hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}')
                ),
                id=step_id
            )

    async def download_ready_export(self, request):
        """Handle ready export download"""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        
        # Get form data
        form = await request.form()
        pipeline_id = form.get("pipeline_id")
        job_id = form.get("job_id")
        download_url = form.get("download_url")
        
        if not all([pipeline_id, job_id, download_url]):
            return P("Missing required parameters", style=pip.get_style("error"))
        
        # Get state data
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        
        # Extract necessary information from state
        org = step_data.get('org')
        project = step_data.get('project')
        analysis = step_data.get('analysis')
        depth = step_data.get('depth', '0')
        
        # Update state with the download URL if it's not already set
        if step_id not in state:
            state[step_id] = {}
        
        state[step_id].update({
            'job_id': job_id,
            'download_url': download_url,
            'status': 'DONE',
            'org': org,
            'project': project,
            'analysis': analysis,
            'depth': depth
        })
        
        # Set a dummy job URL if none exists
        if step.done not in state[step_id]:
            state[step_id][step.done] = f"existing://{job_id}"
            
        pip.write_state(pipeline_id, state)
        
        # Show download progress UI
        try:
            # Create download directory
            download_dir = await self.create_download_directory(org, project, analysis)
            
            # Generate filename
            include_fields = step_data.get('include_fields', {})
            fields_suffix = "_".join(k for k, v in include_fields.items() if v) or "url_only"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{org}_{project}_{analysis}_depth_{depth}_{fields_suffix}_{timestamp}.csv"
            
            local_file_path = download_dir / filename
            
            # Start downloading with progress feedback
            await self.message_queue.add(pip, f"Starting download from {download_url}", verbatim=True)
            
            # Show download progress
            return Div(
                Card(
                    H4("Downloading CSV File"),
                    P(f"Downloading export to {local_file_path}", style="margin-bottom: 1rem;"),
                    Progress(value="10", max="100", style="width: 100%;"),
                    P("Please wait, this may take a few minutes for large files...", 
                      style="font-size: 0.9em; color: #666;")
                ),
                hx_get=f"/{app_name}/download_progress",
                hx_trigger="load",
                hx_target=f"#{step_id}",
                hx_vals=f'{{"pipeline_id": "{pipeline_id}", "download_url": "{download_url}", "local_file": "{local_file_path}"}}',
                id=step_id
            )
            
        except Exception as e:
            logger.error(f"Error preparing download: {str(e)}")
            return P(f"Error preparing download: {str(e)}", style=pip.get_style("error"))

# ============================================================================
# 6. API INTEGRATION
# ============================================================================

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
        """Calculate maximum depth that keeps cumulative URLs under 1M and return count details"""
        depth_distribution = await self.get_urls_by_depth(org, project, analysis, api_key)
        if not depth_distribution:
            return None, None, None
        
        cumulative_sum = 0
        sorted_depths = sorted(depth_distribution.keys())
        
        for i, depth in enumerate(sorted_depths):
            prev_sum = cumulative_sum
            cumulative_sum += depth_distribution[depth]
            if cumulative_sum >= 1_000_000:
                safe_depth = depth - 1
                safe_count = prev_sum
                next_depth_count = cumulative_sum
                return safe_depth, safe_count, next_depth_count
                
        # If we never hit 1M, return the max depth and its cumulative count
        return max(sorted_depths), cumulative_sum, None

    async def initiate_export_job(self, org, project, analysis, depth, include_fields, api_token):
        """
        Initiate a Botify export job with the specified parameters
        
        Args:
            org: Organization slug
            project: Project slug
            analysis: Analysis slug
            depth: Maximum depth to include
            include_fields: Dictionary of fields to include (title, meta_desc, h1)
            api_token: Botify API token
            
        Returns:
            Tuple of (job_url, error_message)
        """
        jobs_url = "https://api.botify.com/v1/jobs"
        headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json"
        }
        
        # Define the query dimensions based on selected fields
        dimensions = [f"crawl.{analysis}.url"]
        
        if include_fields.get('title', False):
            dimensions.append(f"crawl.{analysis}.metadata.title.content")
        
        if include_fields.get('meta_desc', False):
            dimensions.append(f"crawl.{analysis}.metadata.description.content")
        
        if include_fields.get('h1', False):
            dimensions.append(f"crawl.{analysis}.metadata.h1.contents")
        
        # Build the BQL query with depth filter
        query = {
            "dimensions": dimensions,
            "metrics": [],
            "sort": [{"field": f"crawl.{analysis}.url", "order": "asc"}],
            "filters": {
                "field": f"crawl.{analysis}.depth",
                "predicate": "lte",
                "value": int(depth)
            }
        }
        
        # Construct the job payload
        export_payload = {
            "job_type": "export",
            "payload": {
                "username": org,
                "project": project,
                "connector": "direct_download",
                "formatter": "csv",
                "export_size": 1000000,
                "query": {
                    "collections": [f"crawl.{analysis}"],
                    "query": query
                }
            }
        }
        
        try:
            # Submit export job request
            async with httpx.AsyncClient() as client:
                response = await client.post(jobs_url, headers=headers, json=export_payload, timeout=60.0)
                response.raise_for_status()
                job_data = response.json()
                
                job_url_path = job_data.get('job_url')
                if not job_url_path:
                    return None, "Failed to get job URL from response"
                    
                full_job_url = f"https://api.botify.com{job_url_path}"
                return full_job_url, None
        
        except Exception as e:
            logger.error(f"Error initiating export job: {str(e)}")
            return None, f"Error initiating export job: {str(e)}"

    async def poll_job_status(self, job_url, api_token, max_attempts=12):
        """
        Poll the job status URL to check for completion
        
        Args:
            job_url: Full job URL to poll
            api_token: Botify API token
            max_attempts: Maximum number of polling attempts
            
        Returns:
            Tuple of (is_complete, download_url, error_message)
        """
        headers = {"Authorization": f"Token {api_token}"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(job_url, headers=headers, timeout=30.0)
                response.raise_for_status()
                status_data = response.json()
                
                job_status = status_data.get("job_status")
                
                if job_status == "DONE":
                    download_url = status_data.get("results", {}).get("download_url")
                    if download_url:
                        return True, download_url, None
                    else:
                        return False, None, "Job completed but no download URL found"
                elif job_status == "FAILED":
                    return False, None, f"Export job failed: {status_data.get('results')}"
                else:
                    # Not complete yet
                    return False, None, None
        
        except Exception as e:
            logger.error(f"Error polling job status: {str(e)}")
            return False, None, f"Error polling job status: {str(e)}"

# ============================================================================
# 7. UI HELPERS & UTILITIES
# ============================================================================

    def clean_job_id_for_display(self, job_id):
        """
        Clean and shorten a job ID for display in the UI.
        Removes the depth and field information to show only the project details.
        
        Args:
            job_id: The raw job ID, typically a filename
            
        Returns:
            str: A cleaned, possibly truncated job ID
        """
        if not job_id or job_id == "Unknown":
            return "Unknown"
            
        # Extract the part before "_depth_" which typically contains org/project info
        clean_id = job_id.split('_depth_')[0] if '_depth_' in job_id else job_id
        
        # Truncate if too long
        if len(clean_id) > 30:
            clean_id = clean_id[:27] + "..."
            
        return clean_id

    async def check_export_status(self, request):
        """Check and display export status"""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        
        # Get form data
        form = await request.form()
        pipeline_id = form.get("pipeline_id")
        job_url = form.get("job_url")
        job_id = form.get("job_id")
        
        if not all([pipeline_id, job_url, job_id]):
            return P("Missing required parameters", style=pip.get_style("error"))
        
        # Get state data
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        
        # Check if the job is complete
        try:
            api_token = self.read_api_token()
            is_complete, download_url, error = await self.poll_job_status(job_url, api_token)
            
            if is_complete and download_url:
                # Update the state with the download URL
                state[step_id]['download_url'] = download_url
                state[step_id]['status'] = 'DONE'
                pip.write_state(pipeline_id, state)
                
                # Update the registry
                org = step_data.get('org')
                project = step_data.get('project')
                analysis = step_data.get('analysis')
                depth = step_data.get('depth')
                
                if all([org, project, analysis, depth]):
                    self.update_export_job(
                        org, project, analysis, depth, job_id,
                        {'status': 'DONE', 'download_url': download_url}
                    )
                
                # Send success message
                await self.message_queue.add(
                    pip, 
                    f"Export job completed! Job ID: {job_id}\n"
                    f"The export is ready for download.", 
                    verbatim=True
                )
                
                # Return the download button - IMPORTANT: Break the HTMX chain reaction
                # No hx_get or other HTMX attributes on this DIV
                # This is a "terminal" response that won't trigger other steps
                return Div(
                    Card(
                        H4("Export Status: Complete ✅"),
                        P(f"Job ID: {job_id}", style="margin-bottom: 0.5rem;"),
                        P(f"The export is ready for download.", style="margin-bottom: 1rem;"),
                        Form(
                            Button("Download CSV", type="submit", cls="primary"),
                            hx_post=f"/{app_name}/download_csv",
                            hx_target=f"#{step_id}",
                            hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}'
                        )
                    ),
                    # Add class to indicate this is a terminal response
                    # This DIV won't load any other steps automatically
                    cls="terminal-response no-chain-reaction",
                    id=step_id
                )
            else:
                # Job is still processing
                created = step_data.get('created', state[step_id].get('created', 'Unknown'))
                try:
                    created_dt = datetime.fromisoformat(created)
                    created_str = created_dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    created_str = created
                
                # Send message about still processing
                await self.message_queue.add(
                    pip, 
                    f"Export job is still processing (Job ID: {job_id}).\n"
                    f"Status will update automatically.", 
                    verbatim=True
                )
                
                # Return the UI with automatic polling instead of "Check Status Again" button
                include_fields = step_data.get('include_fields', {})
                fields_list = ", ".join([k for k, v in include_fields.items() if v]) or "URL only"
                
                return Div(
                    Card(
                        H4("Export Status: Processing ⏳"),
                        P(f"Job ID: {job_id}", style="margin-bottom: 0.5rem;"),
                        P(f"Started: {created_str}", style="margin-bottom: 0.5rem;"),
                        Div(
                            Progress(),  # PicoCSS indeterminate progress bar
                            P("Checking status automatically...", style="color: #666;"),
                            id="progress-container"
                        )
                    ),
                    # Only these HTMX attributes to continue polling - nothing else
                    # This breaks the chain reaction by not having any next-step HTMX attributes
                    cls="polling-status no-chain-reaction",
                    hx_get=f"/{app_name}/download_job_status",
                    hx_trigger="load delay:2s",
                    hx_target=f"#{step_id}",
                    hx_swap="outerHTML",
                    hx_vals=f'{{"pipeline_id": "{pipeline_id}", "job_url": "{job_url}"}}',
                    id=step_id
                )
                
        except Exception as e:
            logger.error(f"Error checking job status: {str(e)}")
            return P(f"Error checking export status: {str(e)}", style=pip.get_style("error"))

    async def download_job_status(self, request):
        """Handle job status updates"""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        
        # Get query parameters from the GET request
        pipeline_id = request.query_params.get("pipeline_id")
        
        if not pipeline_id:
            return P("Missing required parameters", style=pip.get_style("error"))
        
        # Get state data
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        
        # Get job information from state
        job_url = step_data.get('job_url')
        job_id = step_data.get('job_id')
        org = step_data.get('org')
        project = step_data.get('project')
        analysis = step_data.get('analysis')
        depth = step_data.get('depth')
        
        if not all([job_url, job_id]):
            return P("Job information not found in state", style=pip.get_style("error"))
        
        # Check if the job is complete
        try:
            api_token = self.read_api_token()
            is_complete, download_url, error = await self.poll_job_status(job_url, api_token)
            
            if is_complete and download_url:
                # Update the state with the download URL
                state[step_id]['download_url'] = download_url
                state[step_id]['status'] = 'DONE'
                pip.write_state(pipeline_id, state)
                
                # Update the registry
                if all([org, project, analysis, depth]):
                    self.update_export_job(
                        org, project, analysis, depth, job_id,
                        {'status': 'DONE', 'download_url': download_url}
                    )
                
                # Send success message
                await self.message_queue.add(
                    pip, 
                    f"Export job completed! Job ID: {job_id}\n"
                    f"The export is ready for download.", 
                    verbatim=True
                )
                
                # Return the download button - IMPORTANT: Break the HTMX chain reaction
                # No hx_get or other HTMX attributes on this DIV
                # This is a "terminal" response that won't trigger other steps
                return Div(
                    Card(
                        H4("Export Status: Complete ✅"),
                        P(f"Job ID: {job_id}", style="margin-bottom: 0.5rem;"),
                        P(f"The export is ready for download.", style="margin-bottom: 1rem;"),
                        Form(
                            Button("Download CSV", type="submit", cls="primary"),
                            hx_post=f"/{app_name}/download_csv",
                            hx_target=f"#{step_id}",
                            hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}'
                        )
                    ),
                    # Add class to indicate this is a terminal response
                    # This DIV won't load any other steps automatically
                    cls="terminal-response no-chain-reaction",
                    id=step_id
                )
            else:
                # Job is still processing - show indeterminate progress bar with automatic polling
                include_fields = step_data.get('include_fields', {})
                fields_list = ", ".join([k for k, v in include_fields.items() if v]) or "URL only"
                
                return Div(
                    Card(
                        H4("Export Status: Processing ⏳"),
                        P(f"Job ID: {job_id}", style="margin-bottom: 0.5rem;"),
                        P(f"Exporting URLs up to depth {depth}", style="margin-bottom: 0.5rem;"),
                        P(f"Including fields: {fields_list}", style="margin-bottom: 1rem;"),
                        Div(
                            Progress(),  # PicoCSS indeterminate progress bar
                            P("Checking status automatically...", style="color: #666;"),
                            id="progress-container"
                        )
                    ),
                    # Only these HTMX attributes to continue polling - nothing else
                    # This breaks the chain reaction by not having any next-step HTMX attributes
                    cls="polling-status no-chain-reaction",
                    hx_get=f"/{app_name}/download_job_status",
                    hx_trigger="load delay:2s",
                    hx_target=f"#{step_id}",
                    hx_swap="outerHTML",
                    hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}',
                    id=step_id
                )
                
        except Exception as e:
            logger.error(f"Error checking job status: {str(e)}")
            return P(f"Error checking export status: {str(e)}", style=pip.get_style("error"))

# ============================================================================
# 8. STATE MANAGEMENT
# ============================================================================

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
        
        # Before unfinalizing, check if Step 4 is completed and preserve its state
        state = pip.read_state(pipeline_id)
        step_04_data = pip.get_step_data(pipeline_id, "step_04", {})
        step_04 = next((s for s in steps if s.id == "step_04"), None)
        
        if step_04 and step_04_data.get(step_04.done):
            # Add a flag to indicate Step 4 should stay in completed state after unfinalization
            state["step_04"]["_preserve_completed"] = True
            pip.write_state(pipeline_id, state)
        
        # Update state using DRY helper
        await pip.unfinalize_workflow(pipeline_id)
        
        # ───────── CUSTOM UNFINALIZATION UI (INTENTIONALLY WET) ─────────
        # Send a message informing them they can revert to any step
        await self.message_queue.add(pip, "Workflow unfinalized! You can now revert to any step and make changes.", verbatim=True)
        
        # Return the rebuilt UI
        return pip.rebuild(app_name, steps)
        # ───────── END CUSTOM UNFINALIZATION UI ─────────

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
        
        # Clear steps from the specified step forward
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        
        # Update state with revert target
        state = pip.read_state(pipeline_id)
        state["_revert_target"] = step_id
        
        # When reverting to step_04 or any earlier step, clear the _preserve_completed flag
        # from step_04 to ensure it shows the interactive UI instead of the completed state
        if step_id == "step_04" or self.steps_indices.get(step_id, 0) < self.steps_indices.get("step_04", 99):
            if "step_04" in state and "_preserve_completed" in state["step_04"]:
                del state["step_04"]["_preserve_completed"]
        
        pip.write_state(pipeline_id, state)
        
        # Send a state message
        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        
        # Return the rebuilt UI
        return pip.rebuild(app_name, steps)

# ============================================================================
# 9. UTILITY FUNCTIONS
# ============================================================================

def parse_botify_url(url: str) -> dict:
    """
    Parse and validate Botify URL.
    
    Args:
        url: The Botify project URL to parse
        
    Returns:
        dict: Contains url, org, and project information
        
    Raises:
        ValueError: If URL format is invalid
    """
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    if len(path_parts) < 2:
        raise ValueError("Invalid Botify URL format")
    org = path_parts[0]
    project = path_parts[1]
    base_url = f"https://{parsed.netloc}/{org}/{project}/"
    return {"url": base_url, "org": org, "project": project} 
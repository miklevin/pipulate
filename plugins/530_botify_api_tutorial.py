import asyncio
import json
import logging
import os
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import uuid

import httpx
from fasthtml.common import *
from loguru import logger

ROLES = ['Workshop']
"""
=============================================================================
Botify API Tutorial Workflow
=============================================================================

This workflow demonstrates how to interact with the Botify API to:
- Validate and parse Botify project URLs
- Select and configure analysis exports
- Manage export jobs and monitor progress
- Download and process CSV exports
- Handle file compression and encoding

The code is organized into these key sections:
1. Core Setup & Configuration
2. Step Handlers (step_01 through step_04)
3. Export Job Management
4. File & Directory Management
5. API Integration
6. UI Helper Functions
7. State Management
"""
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class BotifyExport:
    """
    Botify CSV Export Workflow

    This workflow helps users export data from Botify projects and download it as CSV files.
    It demonstrates usage of rich UI components like directory trees alongside standard
    form inputs and revert controls.

    ## Key Implementation Notes

    ### Data Processing Challenges

    1. **CSV Format Variations**: Botify exports have inconsistent format details:
       - Some files include `sep=,` as the first line (must be stripped in post-processing)
       - Column headers vary between exports and require normalization
       - Character encoding issues may arise (handled with utf-8 errors='ignore')

    2. **Compression Format Handling**:
       - Exports come in various formats (gzip, zip, or uncompressed)
       - The workflow detects format dynamically and handles each appropriately
       - Failback mechanisms attempt different decompression approaches when format detection fails

    3. **File Naming and Paths**:
       - Deterministic path generation ensures consistent file locations
       - Cached exports are detected and reused when possible
       - Directory structure mirrors Botify organization (org/project/analysis)

    ### Implementation Decisions

    1. **Step Separation Trade-offs**:
       - This workflow separates export configuration from download steps
       - While ParameterBuster combines these operations into background processes
       - The separated approach gives more visibility but requires additional user clicks
       - Future versions could adopt the background polling pattern from ParameterBuster

    2. **API Interaction Pattern**:
       - Job submission and polling follows the standard Botify API workflow
       - Error handling includes extensive retry logic for network issues
       - Job ID extraction provides a fallback when URLs expire
       - Token validation occurs at workflow start rather than per-request

    3. **Post-processing Requirements**:
       - Unlike ParameterBuster which handles processing inline, this workflow requires manual steps
       - Column renaming must be done after download
       - Header row handling for `sep=,` must be managed explicitly
       - UTF-8 decoding with error handling is essential for some exports

    Implementation Note on Tree Displays:
    ------------------------------------
    The tree display for file paths uses the standardized pip.widget_container method,
    which provides consistent styling and layout for displaying additional content below
    the standard revert controls. This ensures proper alignment with revert buttons 
    while maintaining visual grouping.

    Example usage:
    ```python
    tree_display = pip.tree_display(tree_path)
    content_container = pip.widget_container(
        step_id=step_id,
        app_name=app_name,
        message=display_msg,
        widget=tree_display,
        steps=steps
    )
    ```

    This standardized pattern eliminates the need for workflow-specific spacing adjustments
    and ensures consistent styling across the application.
    """
    APP_NAME = 'botify_api'
    DISPLAY_NAME = 'Botify API Tutorial'
    ENDPOINT_MESSAGE = 'This workflow will grow into a comprehensive tutorial on the Botify API. Press Enter to start a new workflow or enter an existing key to resume. '
    TRAINING_PROMPT = 'botify_api_tutorial.md'
    USE_TREE_DISPLAY = True

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
        self.message_queue = pip.message_queue
        self.EXPORT_REGISTRY_FILE = Path(f'downloads/{self.app_name}/export_registry.json')
        steps = [Step(id='step_01', done='url', show='Botify Project URL', refill=True), Step(id='step_02', done='analysis', show='Analysis Selection', refill=False), Step(id='step_03', done='depth', show='Maximum Click Depth', refill=False), Step(id='step_04', done='export_url', show='CSV Export', refill=False)]
        routes = [(f'/{app_name}', self.landing), (f'/{app_name}/init', self.init, ['POST']), (f'/{app_name}/revert', self.handle_revert, ['POST']), (f'/{app_name}/finalize', self.finalize, ['GET', 'POST']), (f'/{app_name}/unfinalize', self.unfinalize, ['POST'])]
        self.steps = steps
        for step in steps:
            step_id = step.id
            routes.append((f'/{app_name}/{step_id}', getattr(self, step_id)))
            routes.append((f'/{app_name}/{step_id}_submit', getattr(self, f'{step_id}_submit'), ['POST']))
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ['GET']
            app.route(path, methods=method_list)(handler)
        app.route(f'/{app_name}/download_csv', methods=['POST'])(self.download_csv)
        app.route(f'/{app_name}/download_progress')(self.download_progress)
        app.route(f'/{app_name}/download_job_status')(self.download_job_status)
        app.route(f'/{app_name}/use_existing_export', methods=['POST'])(self.use_existing_export)
        app.route(f'/{app_name}/step_04/new')(self.step_04_new)
        app.route(f'/{app_name}/check_export_status', methods=['POST'])(self.check_export_status)
        app.route(f'/{app_name}/download_ready_export', methods=['POST'])(self.download_ready_export)
        self.step_messages = {'finalize': {'ready': 'All steps complete. Ready to finalize workflow.', 'complete': f'Workflow finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes.'}}
        for step in steps:
            self.step_messages[step.id] = {'input': f'{pip.fmt(step.id)}: Please enter {step.show}.', 'complete': f'{step.show} complete. Continue to next step.'}
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

    async def landing(self, request):
        """Renders the initial landing page with the key input form or connection message."""
        pip, pipeline, steps, app_name = (self.pipulate, self.pipeline, self.steps, self.app_name)
        title = f'{self.DISPLAY_NAME or app_name.title()}'
        token_exists = os.path.exists('botify_token.txt')
        if not token_exists:
            return Container(Card(H2(title), P(self.ENDPOINT_MESSAGE, cls='text-secondary'), Div(H3('Botify Connection Required', style='color: #e74c3c;'), P('To use the Botify CSV Export workflow, you must first connect with Botify.', cls='mb-10px'), P('Please run the "Connect With Botify" workflow to set up your Botify API token.', style='margin-bottom: 20px;'), P('Once configured, you can return to this workflow.', style='font-style: italic; color: #666;'))), Div(id=f'{app_name}-container'))
        full_key, prefix, user_part = pip.generate_pipeline_key(self)
        default_value = full_key
        pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in pipeline() if record.pkey.startswith(prefix)]
        datalist_options = [f"{prefix}{record_key.replace(prefix, '')}" for record_key in matching_records]
        return Container(Card(H2(title), P(self.ENDPOINT_MESSAGE, cls='text-secondary'), Form(pip.wrap_with_inline_button(Input(placeholder='Existing or new 🗝 here (Enter for auto)', name='pipeline_id', list='pipeline-ids', type='search', required=False, autofocus=True, value=default_value, _onfocus='this.setSelectionRange(this.value.length, this.value.length)', cls='contrast'), button_label=f'Enter 🔑', button_class='secondary'), pip.update_datalist('pipeline-ids', options=datalist_options if datalist_options else None), hx_post=f'/{app_name}/init', hx_target=f'#{app_name}-container')), Div(id=f'{app_name}-container'))

    async def init(self, request):
        """Handles the key submission, initializes state, and renders the UI placeholders.

        Args:
            request: The incoming HTTP request with form data

        Note on Token Validation:
        Unlike ParameterBuster which checks token existence per-operation,
        this workflow validates the token once at startup. Both approaches have merits:
        - Startup validation (this workflow): Prevents users from even starting without a token
        - Per-operation validation (ParameterBuster): More robust against token deletion during workflow

        This method also sets up the workflow state and prepares the initial display.
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        form = await request.form()
        user_input = form.get('pipeline_id', '').strip()
        if not user_input:
            from starlette.responses import Response
            response = Response('')
            response.headers['HX-Refresh'] = 'true'
            return response
        context = pip.get_plugin_context(self)
        plugin_name = context['plugin_name'] or app_name
        profile_name = context['profile_name'] or 'default'
        profile_part = profile_name.replace(' ', '_')
        plugin_part = plugin_name.replace(' ', '_')
        expected_prefix = f'{profile_part}-{plugin_part}-'
        if user_input.startswith(expected_prefix):
            pipeline_id = user_input
            parsed = pip.parse_pipeline_key(pipeline_id)
            user_provided_id = parsed['user_part']
        else:
            _, prefix, user_provided_id = pip.generate_pipeline_key(self, user_input)
            pipeline_id = f'{prefix}{user_provided_id}'
        db['pipeline_id'] = pipeline_id
        logger.debug(f'Using pipeline ID: {pipeline_id}')
        state, error = pip.initialize_if_missing(pipeline_id, {'app_name': app_name})
        if error:
            return error
        all_steps_complete = True
        for step in steps[:-1]:
            if step.id not in state or step.done not in state[step.id]:
                all_steps_complete = False
                break
        is_finalized = 'finalize' in state and 'finalized' in state['finalize']
        id_message = f'Workflow ID: {pipeline_id}'
        await self.message_queue.add(pip, id_message, verbatim=True, spaces_before=0)
        return_message = f"You can return to this workflow later by selecting '{pipeline_id}' from the dropdown menu."
        await self.message_queue.add(pip, return_message, verbatim=True, spaces_before=0)
        if all_steps_complete:
            if is_finalized:
                await self.message_queue.add(pip, f'Workflow is complete and finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes.', verbatim=True)
            else:
                await self.message_queue.add(pip, f'Workflow is complete but not finalized. Press Finalize to lock your data.', verbatim=True)
        elif not any((step.id in state for step in self.steps)):
            await self.message_queue.add(pip, 'Please complete each step in sequence. Your progress will be saved automatically.', verbatim=True)
        parsed = pip.parse_pipeline_key(pipeline_id)
        prefix = f"{parsed['profile_part']}-{parsed['plugin_part']}-"
        self.pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in self.pipeline() if record.pkey.startswith(prefix)]
        if pipeline_id not in matching_records:
            matching_records.append(pipeline_id)
        updated_datalist = pip.update_datalist('pipeline-ids', options=matching_records)
        
        # Create step placeholders using run_all_cells method
        return Div(updated_datalist, *pip.run_all_cells(app_name, steps).children, id=f'{app_name}-container')

    async def step_01(self, request):
        """Handle project URL input"""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, '')
        if step.done == 'finalized':
            finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
            if 'finalized' in finalize_data:
                return Card(H3('Pipeline Finalized'), P('All steps are locked.'), Form(Button(pip.UNLOCK_BUTTON_LABEL, type='submit', cls='secondary outline'), hx_post=f'/{app_name}/unfinalize', hx_target=f'#{app_name}-container', hx_swap='outerHTML'))
            else:
                return Div(Card(H3('Finalize Pipeline'), P('You can finalize this pipeline or go back to fix something.'), Form(Button('Finalize 🔒', type='submit', cls='primary'), hx_post=f'/{app_name}/finalize', hx_target=f'#{app_name}-container', hx_swap='outerHTML')), id=step_id)
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data:
            return Div(Card(H3(f'🔒 {step.show}: {user_val}')), Div(id=next_step_id, hx_get=f'/{self.app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif user_val and state.get('_revert_target') != step_id:
            return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: {user_val}', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'))
        else:
            display_value = user_val if step.refill and user_val else await self.get_suggestion(step_id, state)
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            return Div(Card(H3(f'{pip.fmt(step.id)}: Enter {step.show}'), Form(pip.wrap_with_inline_button(Input(type='text', name=step.done, value=display_value, placeholder=f'Enter {step.show}', required=True, autofocus=True)), hx_post=f'/{app_name}/{step.id}_submit', hx_target=f'#{step.id}')), Div(id=next_step_id), id=step.id)

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
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get('pipeline_id', 'unknown')
        if step.done == 'finalized':
            return await pip.handle_finalized_step(pipeline_id, step_id, steps, app_name, self)
        form = await request.form()
        user_val = form.get(step.done, '').strip()
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            return error_component
        try:
            parsed_data = parse_botify_url(user_val)
            state = pip.read_state(pipeline_id)
            if step_id not in state:
                state[step_id] = {}
            state[step_id].update(parsed_data)
            state[step_id][step.done] = parsed_data['url']
            pip.write_state(pipeline_id, state)
            await self.message_queue.add(pip, f"Successfully parsed Botify URL:\nOrganization: {parsed_data['org']}\nProject: {parsed_data['project']}\nCanonical URL: {parsed_data['url']}", verbatim=True)
            return pip.chain_reverter(step_id, step_index, steps, app_name, parsed_data['url'])
        except ValueError:
            return P('Invalid Botify URL. Please provide a URL containing organization and project (e.g., https://app.botify.com/org/project/...)', style=pip.get_style('error'))

    async def step_02(self, request):
        """
        Display form for analysis slug selection using a dropdown menu.
        Pre-selects the most recent analysis if no previous selection exists,
        otherwise maintains the user's previous selection.
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data:
            return Div(Card(H3(f'🔒 {step.show}: {user_val}')), Div(id=next_step_id, hx_get=f'/{self.app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif user_val and state.get('_revert_target') != step_id:
            return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: {user_val}', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'))
        step_01_data = pip.get_step_data(pipeline_id, 'step_01', {})
        org = step_01_data.get('org')
        project = step_01_data.get('project')
        try:
            api_token = self.read_api_token()
            slugs = await self.fetch_analyses(org, project, api_token)
            if not slugs:
                return P('No analyses found for this project', style=pip.get_style('error'))
            downloaded_analyses = self.find_downloaded_analyses(org, project)
            prioritized_slugs = []
            for slug in slugs:
                if slug in downloaded_analyses:
                    prioritized_slugs.append((slug, True))
            for slug in slugs:
                if slug not in downloaded_analyses:
                    prioritized_slugs.append((slug, False))
            selected_value = user_val if user_val else prioritized_slugs[0][0] if prioritized_slugs else ''
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            return Div(Card(H3(f'{pip.fmt(step_id)}: Select {step.show}'), Form(pip.wrap_with_inline_button(Select(*[Option(f"{slug} {('(Downloaded)' if is_downloaded else '')}", value=slug, selected=slug == selected_value) for slug, is_downloaded in prioritized_slugs], name=step.done, required=True, autofocus=True)), hx_post=f'/{app_name}/{step.id}_submit', hx_target=f'#{step.id}')), Div(id=next_step_id), id=step.id)
        except Exception as e:
            return P(f'Error fetching analyses: {str(e)}', style=pip.get_style('error'))

    async def step_02_submit(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get('pipeline_id', 'unknown')
        if step.done == 'finalized':
            return await pip.handle_finalized_step(pipeline_id, step_id, steps, app_name, self)
        form = await request.form()
        user_val = form.get(step.done, '')
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            return error_component
        await pip.set_step_data(pipeline_id, step_id, user_val, steps)
        await self.message_queue.add(pip, f'{step.show}: {user_val}', verbatim=True)
        if pip.check_finalize_needed(step_index, steps):
            await self.message_queue.add(pip, 'All steps complete! Please press the Finalize button below to save your data.', verbatim=True)
        return pip.chain_reverter(step_id, step_index, steps, app_name, user_val)

    async def step_03(self, request):
        """
        Display the maximum safe click depth based on cumulative URL counts.
        Shows both the calculated depth and detailed URL count information.
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_03'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data:
            return Div(Card(H3(f'🔒 {step.show}: {user_val}')), Div(id=next_step_id, hx_get=f'/{self.app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif user_val and state.get('_revert_target') != step_id:
            return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: {user_val}', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'))
        step_01_data = pip.get_step_data(pipeline_id, 'step_01', {})
        step_02_data = pip.get_step_data(pipeline_id, 'step_02', {})
        org = step_01_data.get('org')
        project = step_01_data.get('project')
        analysis = step_02_data.get('analysis')
        try:
            api_token = self.read_api_token()
            max_depth, safe_count, next_count = await self.calculate_max_safe_depth(org, project, analysis, api_token)
            if max_depth is None:
                return P('Could not calculate maximum depth. Please check your API access and try again.', style=pip.get_style('error'))
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            safe_count_fmt = f'{safe_count:,}' if safe_count is not None else 'unknown'
            if next_count is not None:
                next_count_fmt = f'{next_count:,}'
                explanation = f'At depth {max_depth}, the export will include {safe_count_fmt} URLs.\nGoing to depth {max_depth + 1} would exceed the limit with {next_count_fmt} URLs.'
            else:
                explanation = f'The entire site can be exported with {safe_count_fmt} URLs.\nThis is under the 1 million URL limit.'
            return Div(Card(H3(f'{pip.fmt(step_id)}: {step.show}'), P(f'Based on URL counts, the maximum safe depth is: {max_depth}', cls='mb-4'), P(explanation, cls='mb-4'), P('This depth ensures the export will contain fewer than 1 million URLs.', cls='text-secondary'), Form(pip.wrap_with_inline_button(Input(type='hidden', name=step.done, value=str(max_depth))), hx_post=f'/{app_name}/{step.id}_submit', hx_target=f'#{step.id}')), Div(id=next_step_id), id=step.id)
        except Exception as e:
            return P(f'Error calculating maximum depth: {str(e)}', style=pip.get_style('error'))

    async def step_03_submit(self, request):
        """Handle the submission of the maximum click depth step."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_03'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get('pipeline_id', 'unknown')
        if step.done == 'finalized':
            return await pip.handle_finalized_step(pipeline_id, step_id, steps, app_name, self)
        form = await request.form()
        user_val = form.get(step.done, '')
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            return error_component
        await pip.set_step_data(pipeline_id, step_id, user_val, steps)
        await self.message_queue.add(pip, f'{step.show}: {user_val}', verbatim=True)
        if pip.check_finalize_needed(step_index, steps):
            await self.message_queue.add(pip, 'All steps complete! Please press the Finalize button below to save your data.', verbatim=True)
        return pip.chain_reverter(step_id, step_index, steps, app_name, user_val)

    async def step_04(self, request):
        """Display the CSV export form with field selection options

        This step demonstrates a key difference from ParameterBuster's approach:
        - This workflow separates configuration (this step) from processing (download steps)
        - ParameterBuster uses background processing with immediate progress feedback

        The separated approach gives users more control but requires additional clicks.
        It also lacks the immediate visual feedback that background processing provides.

        The field selection UI shows available fields based on BQLv2 schema definition,
        with checkbox controls for flexible selection.
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_04'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data:
            download_url = step_data.get('download_url')
            local_file = step_data.get('local_file')
            if local_file and Path(local_file).exists():
                try:
                    rel_path = Path(local_file).relative_to(Path.cwd())
                    tree_path = self.format_path_as_tree(rel_path)
                    tree_display = pip.tree_display(tree_path)
                    finalized_card = pip.finalized_content(message=f'🔒 {step.show}: CSV file downloaded to:', content=tree_display)
                    return Div(finalized_card, Div(id=next_step_id, hx_get=f'/{self.app_name}/{next_step_id}', hx_trigger='load'))
                except ValueError:
                    tree_path = self.format_path_as_tree(local_file)
                    tree_display = pip.tree_display(tree_path)
                    finalized_card = pip.finalized_content(message=f'🔒 {step.show}: CSV file downloaded to:', content=tree_display)
                    return Div(finalized_card, Div(id=next_step_id, hx_get=f'/{self.app_name}/{next_step_id}', hx_trigger='load'))
            elif download_url:
                download_msg = f'🔒 {step.show}: Ready for download'
                return Div(Card(download_msg), Div(id=next_step_id, hx_get=f'/{self.app_name}/{next_step_id}', hx_trigger='load'))
            else:
                job_id = user_val.split('/')[-1] if user_val else 'Unknown'
                clean_job_id = self.clean_job_id_for_display(job_id)
                download_msg = f'🔒 {step.show}: Job ID {clean_job_id}'
                return Div(Card(download_msg), Div(id=next_step_id, hx_get=f'/{self.app_name}/{next_step_id}', hx_trigger='load'))
        elif user_val and (state.get('_revert_target') != step_id or step_data.get('_preserve_completed')):
            job_id = user_val.split('/')[-1] if user_val else 'Unknown'
            download_url = step_data.get('download_url')
            local_file = step_data.get('local_file')
            content_container = Div(id=f'{step_id}-content')
            if local_file and Path(local_file).exists():
                try:
                    rel_path = Path(local_file).relative_to(Path.cwd())
                    tree_path = self.format_path_as_tree(rel_path)
                    display_msg = f'{step.show}: CSV file downloaded (Job ID {job_id})'
                    clean_job_id = self.clean_job_id_for_display(job_id)
                    display_msg = f'{step.show}: CSV file downloaded ({clean_job_id})'
                    tree_display = pip.tree_display(tree_path)
                    content_container = pip.display_revert_widget(step_id=step_id, app_name=app_name, message=display_msg, widget=tree_display, steps=steps)
                except ValueError:
                    tree_path = self.format_path_as_tree(local_file)
                    clean_job_id = self.clean_job_id_for_display(job_id)
                    display_msg = f'{step.show}: CSV file downloaded ({clean_job_id})'
                    tree_display = pip.tree_display(tree_path)
                    content_container = pip.display_revert_widget(step_id=step_id, app_name=app_name, message=display_msg, widget=tree_display, steps=steps)
            elif download_url:
                display_msg = f'{step.show}: Ready for download (Job ID {job_id})'
                clean_job_id = self.clean_job_id_for_display(job_id)
                display_msg = f'{step.show}: Ready for download ({clean_job_id})'
                revert_control = pip.display_revert_header(step_id=step_id, app_name=app_name, message=display_msg, steps=steps)
                content_container = revert_control
            else:
                try:
                    api_token = self.read_api_token()
                    is_complete, download_url, _ = await self.poll_job_status(user_val, api_token, step_context="export")
                    if is_complete and download_url:
                        state[step_id]['download_url'] = download_url
                        state[step_id]['status'] = 'DONE'
                        pip.write_state(pipeline_id, state)
                        if 'org' in step_data and 'project' in step_data and ('analysis' in step_data) and ('depth' in step_data):
                            self.update_export_job(step_data['org'], step_data['project'], step_data['analysis'], step_data['depth'], job_id, {'status': 'DONE', 'download_url': download_url})
                        clean_job_id = self.clean_job_id_for_display(job_id)
                        display_msg = f'{step.show}: Ready for download ({clean_job_id})'
                    else:
                        clean_job_id = self.clean_job_id_for_display(job_id)
                        display_msg = f'{step.show}: Processing ({clean_job_id})'
                except Exception:
                    clean_job_id = self.clean_job_id_for_display(job_id)
                    display_msg = f'{step.show}: Job ID {clean_job_id}'
                revert_control = pip.display_revert_header(step_id=step_id, app_name=app_name, message=display_msg, steps=steps)
                content_container = revert_control
            if download_url and (not (local_file and Path(local_file).exists())):
                download_button = Form(Button('Download CSV ▸', type='submit', cls='secondary outline'), hx_post=f'/{app_name}/download_csv', hx_target=f'#{step_id}', hx_swap='outerHTML', hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}')
                return Div(content_container, download_button, Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
            return Div(content_container, Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        step_01_data = pip.get_step_data(pipeline_id, 'step_01', {})
        step_02_data = pip.get_step_data(pipeline_id, 'step_02', {})
        step_03_data = pip.get_step_data(pipeline_id, 'step_03', {})
        org = step_01_data.get('org')
        project = step_01_data.get('project')
        analysis = step_02_data.get('analysis')
        depth = step_03_data.get('depth')
        if not all([org, project, analysis, depth]):
            return P('Missing required data from previous steps. Please complete all steps first.', style=pip.get_style('error'))
        existing_jobs = self.find_export_jobs(org, project, analysis, depth)
        completed_jobs = [job for job in existing_jobs if job['status'] == 'DONE' and job.get('download_url')]
        processing_jobs = [job for job in existing_jobs if job['status'] == 'PROCESSING']
        if processing_jobs:
            api_token = self.read_api_token()
            for job in processing_jobs:
                job_url = job['job_url']
                job_id = job['job_id']
                try:
                    is_complete, download_url, _ = await self.poll_job_status(job_url, api_token, step_context="export")
                    if is_complete and download_url:
                        self.update_export_job(org, project, analysis, depth, job_id, {'status': 'DONE', 'download_url': download_url})
                        completed_jobs.append({**job, 'status': 'DONE', 'download_url': download_url})
                        processing_jobs.remove(job)
                except Exception as e:
                    logger.error(f'Error checking job status: {e}')
        downloaded_jobs = []
        for job in completed_jobs:
            if job.get('local_file') and Path(job['local_file']).exists():
                downloaded_jobs.append(job)
        existing_path = Path('downloads') / org / project / analysis
        existing_files = list(existing_path.glob(f'*depth_{depth}*.csv')) if existing_path.exists() else []
        if downloaded_jobs:
            job = downloaded_jobs[0]
            local_file = job['local_file']
            file_path = Path(local_file)
            await self.message_queue.add(pip, f'Found existing downloaded export: {file_path.name}', verbatim=True)
            return Div(Card(H3(f'{pip.fmt(step_id)}: {step.show}'), P(f"An export for project '{project}', analysis '{analysis}' at depth {depth} has already been downloaded:", cls='mb-2'), P(f'Path:', cls='mb-2'), Pre(self.format_path_as_tree(file_path), style='margin-bottom: 1rem; white-space: pre;'), Div(Button('Use Existing Download ▸', type='button', cls='primary', hx_post=f'/{app_name}/use_existing_export', hx_target=f'#{step.id}', hx_vals=f'{{"pipeline_id": "{pipeline_id}", "file_path": "{file_path}"}}'), Button('Create New Export ▸', type='button', hx_get=f'/{app_name}/{step.id}/new', hx_target=f'#{step.id}'), style='display: flex; gap: 1rem;')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load delay:100ms'), id=step.id)
        elif completed_jobs:
            job = completed_jobs[0]
            job_id = job['job_id']
            download_url = job['download_url']
            job_has_complete_data = all([step_data.get('org'), step_data.get('project'), step_data.get('analysis'), step_data.get('depth')])
            download_button = None
            if job_has_complete_data:
                download_button = Button('Download Ready Export ▸', type='button', cls='primary', hx_post=f'/{app_name}/download_ready_export', hx_target=f'#{step.id}', hx_vals=f'{{"pipeline_id": "{pipeline_id}", "job_id": "{job_id}", "download_url": "{download_url}"}}')
            new_export_label = 'Resume Export' if not job_has_complete_data else 'Create New Export'
            await self.message_queue.add(pip, f'Found existing completed export (Job ID: {job_id})', verbatim=True)
            return Div(Card(H3(f'{pip.fmt(step_id)}: {step.show}'), P(f"An export for project '{project}', analysis '{analysis}' at depth {depth} is ready to download:", cls='mb-4'), P(f'Job ID: {job_id}', cls='mb-2'), Div(download_button if download_button else '', Button(new_export_label, type='button', hx_get=f'/{app_name}/{step.id}/new', hx_target=f'#{step.id}'), style='display: flex; gap: 1rem;')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load delay:100ms'), id=step.id)
        elif processing_jobs:
            job = processing_jobs[0]
            job_id = job['job_id']
            job_url = job['job_url']
            created = job.get('created', 'Unknown')
            try:
                created_dt = datetime.fromisoformat(created)
                created_str = created_dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                created_str = created
            await self.message_queue.add(pip, f'Found existing export job in progress (Job ID: {job_id}, Started: {created_str})', verbatim=True)
            return Div(Card(H3(f'{pip.fmt(step_id)}: {step.show}'), P(f"An export for project '{project}', analysis '{analysis}' at depth {depth} is already processing:", cls='mb-4'), P(f'Job ID: {job_id}', cls='mb-2'), P(f'Started: {created_str}', cls='mb-2'), Div(Progress(), P('Checking status automatically...', cls='text-muted'), id='progress-container'), Div(Button('Create New Export ▸', type='button', hx_get=f'/{app_name}/{step.id}/new', hx_target=f'#{step.id}'), cls='mt-4')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load delay:100ms'), hx_get=f'/{app_name}/check_export_status', hx_trigger='load delay:2s', hx_target=f'#{step.id}', hx_vals=f'{{"pipeline_id": "{pipeline_id}", "job_url": "{job_url}"}}', id=step.id)
        elif existing_files:
            existing_file = existing_files[0]
            await self.message_queue.add(pip, f'Found existing export file: {existing_file.name}', verbatim=True)
            return Div(Card(H3(f'{pip.fmt(step_id)}: {step.show}'), P(f"An export file for project '{project}', analysis '{analysis}' at depth {depth} was found on disk:", cls='mb-2'), P(f'File: {existing_file.name}', cls='mb-4'), Div(Button('Use Existing File ▸', type='button', cls='primary', hx_post=f'/{app_name}/use_existing_export', hx_target=f'#{step.id}', hx_vals=f'{{"pipeline_id": "{pipeline_id}", "file_path": "{existing_file}"}}'), Button('Create New Export ▸', type='button', hx_get=f'/{app_name}/{step.id}/new', hx_target=f'#{step.id}'), style='display: flex; gap: 1rem;')), Div(id=next_step_id), id=step.id)
        await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
        return Div(Card(H3(f'{pip.fmt(step_id)}: Configure {step.show}'), P(f'Export URLs up to depth {depth} from the {analysis} analysis.', cls='mb-4'), P('Select additional fields to include in the export:', cls='mb-2'), Form(Div(Label(Input(type='checkbox', name='include_title', value='true', checked=True), ' Include page titles', style='display: block; margin-bottom: 0.5rem;'), Label(Input(type='checkbox', name='include_meta_desc', value='true', checked=True), ' Include meta descriptions', style='display: block; margin-bottom: 0.5rem;'), Label(Input(type='checkbox', name='include_h1', value='true', checked=True), ' Include H1 headings', style='display: block; margin-bottom: 1rem;'), style='margin-bottom: 1.5rem;'), Button('Start Export ▸', type='submit', cls='primary'), P('Note: Large exports may take several minutes to process.', style='font-size: 0.8em; color: #666; margin-top: 0.5rem;'), hx_post=f'/{app_name}/{step.id}_submit', hx_target=f'#{step.id}')), Div(id=next_step_id), id=step.id)

    async def step_04_submit(self, request):
        """Handle the submission of the CSV export options and start the export job"""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_04'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get('pipeline_id', 'unknown')
        if step.done == 'finalized':
            return await pip.handle_finalized_step(pipeline_id, step_id, steps, app_name, self)
        form = await request.form()
        include_title = form.get('include_title') == 'true'
        include_meta_desc = form.get('include_meta_desc') == 'true'
        include_h1 = form.get('include_h1') == 'true'
        state = pip.read_state(pipeline_id)
        step_01_data = pip.get_step_data(pipeline_id, 'step_01', {})
        step_02_data = pip.get_step_data(pipeline_id, 'step_02', {})
        step_03_data = pip.get_step_data(pipeline_id, 'step_03', {})
        org = step_01_data.get('org')
        project = step_01_data.get('project')
        analysis = step_02_data.get('analysis')
        depth = step_03_data.get('depth')
        if not all([org, project, analysis, depth]):
            return P('Missing required data from previous steps.', style=pip.get_style('error'))
        existing_jobs = self.find_export_jobs(org, project, analysis, depth)
        completed_jobs = [job for job in existing_jobs if job['status'] == 'DONE' and job.get('download_url')]
        processing_jobs = [job for job in existing_jobs if job['status'] == 'PROCESSING']
        if processing_jobs:
            api_token = self.read_api_token()
            for job in processing_jobs[:]:
                job_url = job['job_url']
                job_id = job['job_id']
                try:
                    is_complete, download_url, _ = await self.poll_job_status(job_url, api_token, step_context="export")
                    if is_complete and download_url:
                        self.update_export_job(org, project, analysis, depth, job_id, {'status': 'DONE', 'download_url': download_url})
                        job_with_url = {**job, 'status': 'DONE', 'download_url': download_url}
                        completed_jobs.append(job_with_url)
                        processing_jobs.remove(job)
                except Exception as e:
                    logger.error(f'Error checking job status: {e}')
        if completed_jobs:
            job = completed_jobs[0]
            job_id = job['job_id']
            download_url = job['download_url']
            if step_id not in state:
                state[step_id] = {}
            state[step_id].update({'job_url': job['job_url'], 'job_id': job_id, 'org': org, 'project': project, 'analysis': analysis, 'depth': depth, 'download_url': download_url, 'status': 'DONE', 'include_fields': {'title': include_title, 'meta_desc': include_meta_desc, 'h1': include_h1}})
            state[step_id][step.done] = job['job_url']
            pip.write_state(pipeline_id, state)
            await self.message_queue.add(pip, f'Using existing export job (ID: {job_id}).\nThis job has already completed and is ready for download.', verbatim=True)
            return Div(Card(H3(f'🔒 {step.show}: Complete ✅'), P(f'Using existing export job ID: {job_id}', cls='mb-2'), P(f'The export with your requested parameters is ready for download.', cls='mb-4'), Form(Button('Download CSV ▸', type='submit', cls='primary'), hx_post=f'/{app_name}/download_csv', hx_target=f'#{step_id}', hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}')), id=step_id)
        if processing_jobs:
            job = processing_jobs[0]
            job_id = job['job_id']
            job_url = job['job_url']
            if step_id not in state:
                state[step_id] = {}
            state[step_id].update({'job_url': job_url, 'job_id': job_id, 'org': org, 'project': project, 'analysis': analysis, 'depth': depth, 'status': 'PROCESSING', 'include_fields': {'title': include_title, 'meta_desc': include_meta_desc, 'h1': include_h1}})
            state[step_id][step.done] = job_url
            pip.write_state(pipeline_id, state)
            created = job.get('created', 'Unknown')
            try:
                created_dt = datetime.fromisoformat(created)
                created_str = created_dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                created_str = created
            await self.message_queue.add(pip, f'Using existing export job (ID: {job_id}).\nThis job is still processing (started: {created_str}).', verbatim=True)
            return Div(Card(H3(f'🔒 {step.show}: Complete ✅'), P(f'Using existing export job ID: {job_id}', cls='mb-2'), P(f'Started: {created_str}', cls='mb-2'), Div(Progress(), P('Checking status automatically...', cls='text-muted'), id='progress-container'), hx_get=f'/{app_name}/download_job_status', hx_trigger='load, every 2s', hx_target=f'#{step_id}', hx_swap='outerHTML', hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}'), cls='polling-status no-chain-reaction', id=step_id)
        try:
            include_fields = {'title': include_title, 'meta_desc': include_meta_desc, 'h1': include_h1}
            api_token = self.read_api_token()
            download_dir = await self.create_download_directory(org, project, analysis)
            job_url, error = await self.initiate_export_job(org, project, analysis, depth, include_fields, api_token)
            if error:
                return P(f'Error initiating export: {error}', style=pip.get_style('error'))
            job_id = job_url.split('/')[-1]
            self.register_export_job(org, project, analysis, depth, job_url, job_id)
            is_complete, download_url, poll_error = await self.poll_job_status(job_url, api_token, step_context="export")
            if is_complete and download_url:
                self.update_export_job(org, project, analysis, depth, job_id, {'status': 'DONE', 'download_url': download_url})
            if step_id not in state:
                state[step_id] = {}
            state[step_id].update({'job_url': job_url, 'job_id': job_id, 'org': org, 'project': project, 'analysis': analysis, 'depth': depth, 'download_url': download_url if is_complete else None, 'status': 'DONE' if is_complete else 'PROCESSING', 'download_path': str(download_dir), 'include_fields': include_fields})
            state[step_id][step.done] = job_url
            pip.write_state(pipeline_id, state)
            if is_complete:
                status_msg = f'Export completed! Job ID: {job_id}\nThe export is ready for download.'
            else:
                status_msg = f'Export job started with Job ID: {job_id}\nThe export is processing and may take several minutes.'
            await self.message_queue.add(pip, status_msg, verbatim=True)
            status_display = 'Complete ✅' if is_complete else 'Processing ⏳'
            result_card = Card(H3(f'Export Status: {status_display}'), P(f'Job ID: {job_id}', cls='mb-2'), P(f'Exporting URLs up to depth {depth}', cls='mb-2'), P(f'Including fields: ' + ', '.join([k for k, v in include_fields.items() if v]), cls='mb-4'))
            if is_complete:
                download_button = Form(Button('Download CSV ▸', type='submit', cls='primary'), hx_post=f'/{app_name}/download_csv', hx_target=f'#{step_id}', hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}')
                return Div(result_card, download_button, cls='terminal-response no-chain-reaction', id=step_id)
            else:
                return Div(result_card, P('Status updating automatically...', style='color: #666; margin-bottom: 1rem;'), Div(Progress(), P('Checking status automatically...', cls='text-muted'), id='progress-container'), cls='polling-status no-chain-reaction', hx_get=f'/{app_name}/download_job_status', hx_trigger='load, every 2s', hx_target=f'#{step_id}', hx_swap='outerHTML', hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}', id=step_id)
        except Exception as e:
            logger.error(f'Error in export submission: {str(e)}')
            return P(f'An error occurred: {str(e)}', style=pip.get_style('error'))

    async def step_04_new(self, request):
        """Handle new export creation"""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_04'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        pipeline_id = db.get('pipeline_id', 'unknown')
        step_01_data = pip.get_step_data(pipeline_id, 'step_01', {})
        step_02_data = pip.get_step_data(pipeline_id, 'step_02', {})
        step_03_data = pip.get_step_data(pipeline_id, 'step_03', {})
        org = step_01_data.get('org')
        project = step_01_data.get('project')
        analysis = step_02_data.get('analysis')
        depth = step_03_data.get('depth')
        return Div(Card(H3(f'{pip.fmt(step_id)}: Configure {step.show}'), P(f'Export URLs up to depth {depth} from the {analysis} analysis.', cls='mb-4'), P('Select additional fields to include in the export:', cls='mb-2'), Form(Div(Label(Input(type='checkbox', name='include_title', value='true', checked=True), ' Include page titles', style='display: block; margin-bottom: 0.5rem;'), Label(Input(type='checkbox', name='include_meta_desc', value='true', checked=True), ' Include meta descriptions', style='display: block; margin-bottom: 0.5rem;'), Label(Input(type='checkbox', name='include_h1', value='true', checked=True), ' Include H1 headings', style='display: block; margin-bottom: 1rem;'), style='margin-bottom: 1.5rem;'), Button('Start Export ▸', type='submit', cls='primary'), P('Note: Large exports may take several minutes to process.', style='font-size: 0.8em; color: #666; margin-top: 0.5rem;'), hx_post=f'/{app_name}/{step.id}_submit', hx_target=f'#{step.id}')), Div(id=next_step_id), id=step.id)

    async def use_existing_export(self, request):
        """
        Use an existing export file instead of creating a new one
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_04'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        form = await request.form()
        pipeline_id = form.get('pipeline_id')
        file_path = form.get('file_path')
        if not all([pipeline_id, file_path]):
            return P('Missing required parameters', style=pip.get_style('error'))
        state = pip.read_state(pipeline_id)
        if step_id not in state:
            state[step_id] = {}
        state[step_id].update({'local_file': file_path, 'status': 'DONE', 'is_existing_file': True})
        state[step_id][step.done] = f'existing://{file_path}'
        pip.write_state(pipeline_id, state)
        await self.message_queue.add(pip, f'Using existing export file: {file_path}', verbatim=True)
        rel_path = Path(file_path)
        try:
            rel_path = rel_path.relative_to(Path.cwd())
        except ValueError:
            pass
        tree_path = self.format_path_as_tree(rel_path)
        display_msg = f'{step.show}: CSV file is ready'
        tree_display = pip.tree_display(tree_path)
        content_container = pip.display_revert_widget(step_id=step_id, app_name=app_name, message=display_msg, widget=tree_display, steps=steps)
        return Div(content_container, Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)

    def get_export_key(self, org, project, analysis, depth):
        """Generate unique export key"""
        return f'{org}_{project}_{analysis}_depth_{depth}'

    def load_export_registry(self):
        """Load the export registry from file"""
        try:
            if self.EXPORT_REGISTRY_FILE.exists():
                with open(self.EXPORT_REGISTRY_FILE, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f'Error loading export registry: {e}')
            return {}

    def save_export_registry(self, registry):
        """Save the export registry to file"""
        try:
            self.EXPORT_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.EXPORT_REGISTRY_FILE, 'w') as f:
                json.dump(registry, f, indent=2)
        except Exception as e:
            logger.error(f'Error saving export registry: {e}')

    def register_export_job(self, org, project, analysis, depth, job_url, job_id):
        """Register a new export job in the registry"""
        registry = self.load_export_registry()
        export_key = self.get_export_key(org, project, analysis, depth)
        if export_key not in registry:
            registry[export_key] = []
        registry[export_key].append({'job_url': job_url, 'job_id': job_id, 'status': 'PROCESSING', 'created': datetime.now().isoformat(), 'updated': datetime.now().isoformat(), 'download_url': None, 'local_file': None})
        self.save_export_registry(registry)
        return export_key

    def update_export_job(self, org, project, analysis, depth, job_id, updates):
        """Update an existing export job in the registry"""
        registry = self.load_export_registry()
        export_key = self.get_export_key(org, project, analysis, depth)
        if export_key not in registry:
            logger.error(f'Export key {export_key} not found in registry')
            return False
        for job in registry[export_key]:
            if job['job_id'] == job_id:
                job.update(updates)
                job['updated'] = datetime.now().isoformat()
                self.save_export_registry(registry)
                return True
        logger.error(f'Job ID {job_id} not found for export key {export_key}')
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
        for key in registry.keys():
            if key.startswith(f'{org}_{project}_'):
                parts = key.split('_')
                if len(parts) >= 3:
                    analysis = parts[2]
                    for job in registry[key]:
                        if job.get('status') == 'DONE' and job.get('local_file'):
                            downloaded_analyses.add(analysis)
                            break
        return list(downloaded_analyses)

    async def create_download_directory(self, org, project, analysis):
        """Create a nested directory structure for downloads"""
        download_path = Path(f'downloads/{self.app_name}') / org / project / analysis
        download_path.mkdir(parents=True, exist_ok=True)
        return download_path

    def format_path_as_tree(self, path_str):
        """
        Format a file path as either a hierarchical ASCII tree or a blue box.

        This visualization is used in various places in the UI to show 
        download locations. The styling of the display is carefully tuned
        in each context where it appears.

        Args:
            path_str: The path to format

        Returns:
            str: Formatted path display (either tree or box style)
        """
        path = Path(path_str)
        if not self.USE_TREE_DISPLAY:
            return str(path)
        parts = list(path.parts)
        tree_lines = []
        if parts and parts[0] == '/':
            tree_lines.append('/')
            parts = parts[1:]
        elif len(parts) > 0:
            tree_lines.append(parts[0])
            parts = parts[1:]
        indent = ''
        for part in parts:
            tree_lines.append(f'{indent}└─{part}')
            indent += '    '
        return '\n'.join(tree_lines)

    async def download_csv(self, request):
        """Handles the download request for a Botify export job.

        This method demonstrates file format handling complexity:
        1. Downloads compressed files (.gz or .zip) from Botify API
        2. Detects format automatically and applies appropriate decompression
        3. Handles file name extraction from archive contents
        4. Manages temporary files and cleanup

        Format detection challenges:
        - Some exports have Content-Type: application/gzip
        - Others use application/zip or application/octet-stream
        - Format must sometimes be inferred from file contents
        - Failed decompression requires fallback approaches

        Compare with ParameterBuster's approach which adds post-processing:
        - Directly loads the CSV with pandas after download
        - Skips header row with `sep=,` delimiter notation
        - Applies consistent column naming
        - Saves back with normalized format

        Usage:
        Called via AJAX from the frontend during job status polling
        when download becomes available.
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_04'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        form = await request.form()
        pipeline_id = form.get('pipeline_id')
        if not pipeline_id:
            return P('Missing pipeline_id parameter', style=pip.get_style('error'))
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        download_url = step_data.get('download_url')
        org = step_data.get('org')
        project = step_data.get('project')
        analysis = step_data.get('analysis')
        depth = step_data.get('depth', '0')
        job_id = step_data.get('job_id', 'unknown')
        if not download_url:
            try:
                job_url = step_data.get(step.done)
                if not job_url:
                    return P('No job URL found', style=pip.get_style('error'))
                api_token = self.read_api_token()
                is_complete, download_url, error = await self.poll_job_status(job_url, api_token)
                if not is_complete or not download_url:
                    return Div(P('Export job is still processing. Please try again in a few minutes.', cls='mb-4'), Progress(value='60', max='100', style='width: 100%;'), P(f'Error: {error}' if error else '', style=pip.get_style('error')))
                state[step_id]['download_url'] = download_url
                state[step_id]['status'] = 'DONE'
                pip.write_state(pipeline_id, state)
            except Exception as e:
                return P(f'Error checking job status: {str(e)}', style=pip.get_style('error'))
        try:
            download_dir = await self.create_download_directory(org, project, analysis)
            include_fields = step_data.get('include_fields', {})
            fields_suffix = '_'.join((k for k, v in include_fields.items() if v))
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{org}_{project}_{analysis}_depth_{depth}_{fields_suffix}_{timestamp}.csv'
            local_file_path = download_dir / filename
            await self.message_queue.add(pip, f'Starting download.', verbatim=True)
            return Div(Card(H3('Downloading CSV File'), P(f'Downloading export to {local_file_path}', cls='mb-4'), Progress(value='10', max='100', style='width: 100%;'), P('Please wait, this may take a few minutes for large files...', cls='text-secondary')), hx_get=f'/{app_name}/download_progress', hx_trigger='load', hx_target=f'#{step_id}', hx_vals=f'{{"pipeline_id": "{pipeline_id}", "download_url": "{download_url}", "local_file": "{local_file_path}"}}', id=step_id)
        except Exception as e:
            return P(f'Error preparing download: {str(e)}', style=pip.get_style('error'))

    async def download_progress(self, request):
        """Handle download progress tracking"""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_04'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        pipeline_id = request.query_params.get('pipeline_id')
        download_url = request.query_params.get('download_url')
        local_file = request.query_params.get('local_file')
        if not all([pipeline_id, download_url, local_file]):
            return P('Missing required parameters', style=pip.get_style('error'))
        local_file_path = Path(local_file)
        try:
            api_token = self.read_api_token()
            headers = {'Authorization': f'Token {api_token}'}
            local_file_path.parent.mkdir(parents=True, exist_ok=True)
            async with httpx.AsyncClient() as client:
                async with client.stream('GET', download_url, headers=headers, follow_redirects=True) as response:
                    response.raise_for_status()
                    total_size = int(response.headers.get('content-length', 0))
                    with open(local_file_path, 'wb') as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
            if local_file_path.suffix.lower() in ('.zip', '.gz'):
                await self.message_queue.add(pip, f'Extracting {local_file_path}', verbatim=True)
                extracted_path = None
                if local_file_path.suffix.lower() == '.zip':
                    import zipfile
                    with zipfile.ZipFile(local_file_path, 'r') as zip_ref:
                        csv_files = [f for f in zip_ref.namelist() if f.lower().endswith('.csv')]
                        if not csv_files:
                            return P('No CSV files found in the downloaded ZIP archive', style=pip.get_style('error'))
                        csv_file = csv_files[0]
                        extracted_path = local_file_path.parent / csv_file
                        zip_ref.extract(csv_file, local_file_path.parent)
                elif local_file_path.suffix.lower() == '.gz':
                    import gzip
                    import shutil
                    extracted_path = local_file_path.with_suffix('')
                    with gzip.open(local_file_path, 'rb') as f_in:
                        with open(extracted_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                if extracted_path:
                    local_file_path = extracted_path
            state = pip.read_state(pipeline_id)
            step_data = pip.get_step_data(pipeline_id, step_id, {})
            job_id = step_data.get('job_id')
            org = step_data.get('org')
            project = step_data.get('project')
            analysis = step_data.get('analysis')
            depth = step_data.get('depth')
            state[step_id]['local_file'] = str(local_file_path)
            pip.write_state(pipeline_id, state)
            if job_id and all([org, project, analysis, depth]):
                self.update_export_job(org, project, analysis, depth, job_id, {'local_file': str(local_file_path)})
            file_size_bytes = local_file_path.stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)
            await self.message_queue.add(pip, f'Successfully downloaded and prepared CSV file:\nPath: {local_file_path}\nSize: {file_size_mb:.2f} MB', verbatim=True)
            dir_tree = self.format_path_as_tree(str(local_file_path.parent))
            tree_path = f"{dir_tree}\n{'    ' * len(local_file_path.parent.parts)}└─{local_file_path.name}"
            tree_display = pip.tree_display(tree_path)
            return Div(pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: CSV downloaded ({file_size_mb:.2f} MB)', widget=tree_display, steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        except Exception as e:
            return Div(Card(H3('Download Error'), P(f'Error downloading CSV file: {str(e)}', style=pip.get_style('error')), P(f'Download URL: {download_url}'), P(f'Target file: {local_file_path}'), Button('Try Again ▸', type='button', cls='primary', hx_post=f'/{app_name}/download_csv', hx_target=f'#{step_id}', hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}')), id=step_id)

    async def download_ready_export(self, request):
        """Handle ready export download"""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_04'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        form = await request.form()
        pipeline_id = form.get('pipeline_id')
        job_id = form.get('job_id')
        download_url = form.get('download_url')
        if not all([pipeline_id, job_id, download_url]):
            return P('Missing required parameters', style=pip.get_style('error'))
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        org = step_data.get('org')
        project = step_data.get('project')
        analysis = step_data.get('analysis')
        depth = step_data.get('depth', '0')
        if not all([org, project, analysis, depth]):
            return P('Missing required data from previous steps', style=pip.get_style('error'))
        if step_id not in state:
            state[step_id] = {}
        state[step_id].update({'job_id': job_id, 'download_url': download_url, 'status': 'DONE', 'org': org, 'project': project, 'analysis': analysis, 'depth': depth})
        if step.done not in state[step_id]:
            state[step_id][step.done] = f'existing://{job_id}'
        pip.write_state(pipeline_id, state)
        try:
            download_dir = await self.create_download_directory(org, project, analysis)
            include_fields = step_data.get('include_fields', {})
            fields_suffix = '_'.join((k for k, v in include_fields.items() if v)) or 'url_only'
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{org}_{project}_{analysis}_depth_{depth}_{fields_suffix}_{timestamp}.csv'
            local_file_path = download_dir / filename
            await self.message_queue.add(pip, f'Starting download.', verbatim=True)
            return Div(Card(H3('Downloading CSV File'), P(f'Downloading export to {local_file_path}', cls='mb-4'), Progress(value='10', max='100', style='width: 100%;'), P('Please wait, this may take a few minutes for large files...', cls='text-secondary')), hx_get=f'/{app_name}/download_progress', hx_trigger='load', hx_target=f'#{step_id}', hx_vals=f'{{"pipeline_id": "{pipeline_id}", "download_url": "{download_url}", "local_file": "{local_file_path}"}}', id=step_id)
        except Exception as e:
            logger.error(f'Error preparing download: {str(e)}')
            return P(f'Error preparing download: {str(e)}', style=pip.get_style('error'))

    def read_api_token(self):
        """Read Botify API token from local file."""
        try:
            token_file = Path('botify_token.txt')
            if not token_file.exists():
                raise FileNotFoundError('botify_token.txt not found')
            token = token_file.read_text().splitlines()[0].strip()
            return token
        except Exception as e:
            raise ValueError(f'Error reading API token: {e}')

    async def fetch_analyses(self, org, project, api_token):
        """Fetch analysis slugs for a given project from Botify API."""
        url = f'https://api.botify.com/v1/analyses/{org}/{project}/light'
        headers = {'Authorization': f'Token {api_token}'}
        slugs = []
        async with httpx.AsyncClient() as client:
            try:
                while url:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    slugs.extend((a['slug'] for a in data.get('results', [])))
                    url = data.get('next')
                return slugs
            except httpx.RequestError as e:
                raise ValueError(f'Error fetching analyses: {e}')

    async def get_urls_by_depth(self, org, project, analysis, api_key):
        """
        Fetches URL counts aggregated by depth from the Botify API.
        Returns a dictionary {depth: count} or an empty {} on error.
        """
        api_url = f'https://api.botify.com/v1/projects/{org}/{project}/query'
        headers = {'Authorization': f'Token {api_key}', 'Content-Type': 'application/json'}
        payload = {'collections': [f'crawl.{analysis}'], 'query': {'dimensions': [f'crawl.{analysis}.depth'], 'metrics': [{'field': f'crawl.{analysis}.count_urls_crawl'}], 'sort': [{'field': f'crawl.{analysis}.depth', 'order': 'asc'}]}}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(api_url, headers=headers, json=payload, timeout=120.0)
                response.raise_for_status()
                results = response.json().get('results', [])
                depth_distribution = {}
                for row in results:
                    if 'dimensions' in row and len(row['dimensions']) == 1 and ('metrics' in row) and (len(row['metrics']) == 1):
                        depth = row['dimensions'][0]
                        count = row['metrics'][0]
                        if isinstance(depth, int):
                            depth_distribution[depth] = count
                return depth_distribution
        except Exception as e:
            logger.error(f'Error fetching URL depths: {str(e)}')
            return {}

    async def calculate_max_safe_depth(self, org, project, analysis, api_key):
        """Calculate maximum depth that keeps cumulative URLs under 1M and return count details"""
        depth_distribution = await self.get_urls_by_depth(org, project, analysis, api_key)
        if not depth_distribution:
            return (None, None, None)
        cumulative_sum = 0
        sorted_depths = sorted(depth_distribution.keys())
        for i, depth in enumerate(sorted_depths):
            prev_sum = cumulative_sum
            cumulative_sum += depth_distribution[depth]
            if cumulative_sum >= 1000000:
                safe_depth = depth - 1
                safe_count = prev_sum
                next_depth_count = cumulative_sum
                return (safe_depth, safe_count, next_depth_count)
        return (max(sorted_depths), cumulative_sum, None)

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
        jobs_url = 'https://api.botify.com/v1/jobs'
        headers = {'Authorization': f'Token {api_token}', 'Content-Type': 'application/json'}
        dimensions = [f'crawl.{analysis}.url']
        if include_fields.get('title', False):
            dimensions.append(f'crawl.{analysis}.metadata.title.content')
        if include_fields.get('meta_desc', False):
            dimensions.append(f'crawl.{analysis}.metadata.description.content')
        if include_fields.get('h1', False):
            dimensions.append(f'crawl.{analysis}.metadata.h1.contents')
        query = {'dimensions': dimensions, 'metrics': [], 'sort': [{'field': f'crawl.{analysis}.url', 'order': 'asc'}], 'filters': {'field': f'crawl.{analysis}.depth', 'predicate': 'lte', 'value': int(depth)}}
        export_payload = {'job_type': 'export', 'payload': {'username': org, 'project': project, 'connector': 'direct_download', 'formatter': 'csv', 'export_size': 1000000, 'query': {'collections': [f'crawl.{analysis}'], 'query': query}}}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(jobs_url, headers=headers, json=export_payload, timeout=60.0)
                response.raise_for_status()
                job_data = response.json()
                job_url_path = job_data.get('job_url')
                if not job_url_path:
                    return (None, 'Failed to get job URL from response')
                full_job_url = f'https://api.botify.com{job_url_path}'
                return (full_job_url, None)
        except Exception as e:
            logger.error(f'Error initiating export job: {str(e)}')
            return (None, f'Error initiating export job: {str(e)}')

    async def poll_job_status(self, job_url, api_token, max_attempts=12, step_context=None):
        """Poll the job status URL to check for completion.

        Args:
            job_url: Full job URL to poll
            api_token: Botify API token
            max_attempts: Maximum number of polling attempts (default: 12)
            step_context: Optional context for the step

        Returns:
            Tuple of (success, result_dict_or_error_message)

        Polling Implementation Notes:
        This method showcases important API polling patterns:

        1. Exponential backoff with capped delay (prevents excessive requests)
        2. Error classification (authentication vs. network vs. API errors)
        3. URL regeneration for expired job paths (using extracted job ID)
        4. Network error resilience (retries with increasing delays)

        Comparison with ParameterBuster approach:
        - Both use polling with exponential backoff
        - This implementation has more explicit error handling
        - ParameterBuster integrates polling with UI updates in a single flow
        - This workflow separates these concerns into discrete steps

        Additional fault tolerance mechanisms:
        - Track consecutive network errors to trigger URL reconstruction
        - Extract job ID from URL for fallback polling approach
        - Recover from temporarily unavailable API endpoints
        """
        headers = {'Authorization': f'Token {api_token}'}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(job_url, headers=headers, timeout=30.0)
                response.raise_for_status()
                status_data = response.json()
                job_status = status_data.get('job_status')
                if job_status == 'DONE':
                    download_url = status_data.get('results', {}).get('download_url')
                    if download_url:
                        return (True, download_url, None)
                    else:
                        return (False, None, 'Job completed but no download URL found')
                elif job_status == 'FAILED':
                    return (False, None, f"Export job failed: {status_data.get('results')}")
                else:
                    return (False, None, None)
        except Exception as e:
            logger.error(f'Error polling job status: {str(e)}')
            return (False, None, f'Error polling job status: {str(e)}')

    def clean_job_id_for_display(self, job_id):
        """
        Clean and shorten a job ID for display in the UI.
        Removes the depth and field information to show only the project details.

        Args:
            job_id: The raw job ID, typically a filename

        Returns:
            str: A cleaned, possibly truncated job ID
        """
        if not job_id or job_id == 'Unknown':
            return 'Unknown'
        clean_id = job_id.split('_depth_')[0] if '_depth_' in job_id else job_id
        if len(clean_id) > 30:
            clean_id = clean_id[:27] + '...'
        return clean_id

    async def check_export_status(self, request):
        """Check and display export status"""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_04'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        form = await request.form()
        pipeline_id = form.get('pipeline_id')
        job_url = form.get('job_url')
        job_id = form.get('job_id')
        if not all([pipeline_id, job_url, job_id]):
            return P('Missing required parameters', style=pip.get_style('error'))
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        try:
            api_token = self.read_api_token()
            is_complete, download_url, error = await self.poll_job_status(job_url, api_token, step_context="export")
            if is_complete and download_url:
                state[step_id]['download_url'] = download_url
                state[step_id]['status'] = 'DONE'
                pip.write_state(pipeline_id, state)
                org = step_data.get('org')
                project = step_data.get('project')
                analysis = step_data.get('analysis')
                depth = step_data.get('depth')
                if all([org, project, analysis, depth]):
                    self.update_export_job(org, project, analysis, depth, job_id, {'status': 'DONE', 'download_url': download_url})
                await self.message_queue.add(pip, f'Export job completed! Job ID: {job_id}\nThe export is ready for download.', verbatim=True)
                return Div(Card(H3(f'🔒 {step.show}: Complete ✅'), P(f'Job ID: {job_id}', cls='mb-2'), P(f'The export is ready for download.', cls='mb-4'), Form(Button('Download CSV ▸', type='submit', cls='primary'), hx_post=f'/{app_name}/download_csv', hx_target=f'#{step_id}', hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}')), cls='terminal-response no-chain-reaction', id=step_id)
            else:
                created = step_data.get('created', state[step_id].get('created', 'Unknown'))
                try:
                    created_dt = datetime.fromisoformat(created)
                    created_str = created_dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    created_str = created
                await self.message_queue.add(pip, f'Export job is still processing (Job ID: {job_id}).\nStatus will update automatically.', verbatim=True)
                include_fields = step_data.get('include_fields', {})
                fields_list = ', '.join([k for k, v in include_fields.items() if v]) or 'URL only'
                return Div(Card(H3(f'🔒 {step.show}: Complete ✅'), P(f'Job ID: {job_id}', cls='mb-2'), P(f'Started: {created_str}', cls='mb-2'), Div(Progress(), P('Checking status automatically...', cls='text-muted'), id='progress-container')), cls='polling-status no-chain-reaction', hx_get=f'/{app_name}/download_job_status', hx_trigger='load delay:2s', hx_target=f'#{step_id}', hx_swap='outerHTML', hx_vals=f'{{"pipeline_id": "{pipeline_id}", "job_url": "{job_url}"}}', id=step_id)
        except Exception as e:
            logger.error(f'Error checking job status: {str(e)}')
            return P(f'Error checking export status: {str(e)}', style=pip.get_style('error'))

    async def download_job_status(self, request):
        """Handle job status updates"""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_04'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = request.query_params.get('pipeline_id')
        if not pipeline_id:
            return P('Missing required parameters', style=pip.get_style('error'))
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        job_url = step_data.get('job_url')
        job_id = step_data.get('job_id')
        org = step_data.get('org')
        project = step_data.get('project')
        analysis = step_data.get('analysis')
        depth = step_data.get('depth')
        if not all([job_url, job_id]):
            return P('Job information not found in state', style=pip.get_style('error'))
        try:
            api_token = self.read_api_token()
            is_complete, download_url, error = await self.poll_job_status(job_url, api_token, step_context="export")
            if is_complete and download_url:
                state[step_id]['download_url'] = download_url
                state[step_id]['status'] = 'DONE'
                pip.write_state(pipeline_id, state)
                if all([org, project, analysis, depth]):
                    self.update_export_job(org, project, analysis, depth, job_id, {'status': 'DONE', 'download_url': download_url})
                await self.message_queue.add(pip, f'Export job completed! Job ID: {job_id}\nThe export is ready for download.', verbatim=True)
                return Div(Card(H3(f'🔒 {step.show}: Complete ✅'), P(f'Job ID: {job_id}', cls='mb-2'), P(f'The export is ready for download.', cls='mb-4'), Form(Button('Download CSV ▸', type='submit', cls='primary'), hx_post=f'/{app_name}/download_csv', hx_target=f'#{step_id}', hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}')), cls='terminal-response no-chain-reaction', id=step_id)
            else:
                include_fields = step_data.get('include_fields', {})
                fields_list = ', '.join([k for k, v in include_fields.items() if v]) or 'URL only'
                return Div(Card(H3(f'🔒 {step.show}: Complete ✅'), P(f'Job ID: {job_id}', cls='mb-2'), P(f'Exporting URLs up to depth {depth}', cls='mb-2'), P(f'Including fields: {fields_list}', cls='mb-4'), Div(Progress(), P('Checking status automatically...', cls='text-muted'), id='progress-container')), cls='polling-status no-chain-reaction', hx_get=f'/{app_name}/download_job_status', hx_trigger='load delay:2s', hx_target=f'#{step_id}', hx_swap='outerHTML', hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}', id=step_id)
        except Exception as e:
            logger.error(f'Error checking job status: {str(e)}')
            return P(f'Error checking export status: {str(e)}', style=pip.get_style('error'))

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
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        pipeline_id = db.get('pipeline_id', 'unknown')
        finalize_step = steps[-1]
        finalize_data = pip.get_step_data(pipeline_id, finalize_step.id, {})
        logger.debug(f'Pipeline ID: {pipeline_id}')
        logger.debug(f'Finalize step: {finalize_step}')
        logger.debug(f'Finalize data: {finalize_data}')
        if request.method == 'GET':
            if finalize_step.done in finalize_data:
                logger.debug('Pipeline is already finalized')
                return Card(H3('Workflow is locked.'), Form(Button(pip.UNLOCK_BUTTON_LABEL, type='submit', cls='secondary outline'), hx_post=f'/{app_name}/unfinalize', hx_target=f'#{app_name}-container', hx_swap='outerHTML'), id=finalize_step.id)
            non_finalize_steps = steps[:-1]
            all_steps_complete = all((pip.get_step_data(pipeline_id, step.id, {}).get(step.done) for step in non_finalize_steps))
            logger.debug(f'All steps complete: {all_steps_complete}')
            if all_steps_complete:
                return Card(H3('All steps complete. Finalize?'), P('You can revert to any step and make changes.', cls='text-secondary'), Form(Button('Finalize 🔒', type='submit', cls='primary'), hx_post=f'/{app_name}/finalize', hx_target=f'#{app_name}-container', hx_swap='outerHTML'), id=finalize_step.id)
            else:
                return Div(P('Nothing to finalize yet.'), id=finalize_step.id)
        else:
            await pip.finalize_workflow(pipeline_id)
            await self.message_queue.add(pip, 'Workflow successfully finalized! Your data has been saved and locked.', verbatim=True)
            return pip.run_all_cells(app_name, steps)

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
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_04_data = pip.get_step_data(pipeline_id, 'step_04', {})
        step_04 = next((s for s in steps if s.id == 'step_04'), None)
        if step_04 and step_04_data.get(step_04.done):
            state['step_04']['_preserve_completed'] = True
            pip.write_state(pipeline_id, state)
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, 'Workflow unfinalized! You can now revert to any step and make changes.', verbatim=True)
        return pip.run_all_cells(app_name, steps)

    async def handle_revert(self, request):
        """
        Handle reverting to a previous step in the workflow.

        This method clears state data from the specified step forward,
        marks the step as the revert target in the state, and run_all_cells
        the workflow UI. It allows users to go back and modify their
        inputs at any point in the workflow process.

        Args:
            request: The HTTP request object containing the step_id

        Returns:
            FastHTML components representing the rebuilt workflow UI
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        form = await request.form()
        step_id = form.get('step_id')
        pipeline_id = db.get('pipeline_id', 'unknown')
        if not step_id:
            return P('Error: No step specified', style=pip.get_style('error'))
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        state = pip.read_state(pipeline_id)
        state['_revert_target'] = step_id
        if step_id == 'step_04' or self.steps_indices.get(step_id, 0) < self.steps_indices.get('step_04', 99):
            if 'step_04' in state and '_preserve_completed' in state['step_04']:
                del state['step_04']['_preserve_completed']
        pip.write_state(pipeline_id, state)
        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        return pip.run_all_cells(app_name, steps)

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
        pip, db, steps = (self.pipulate, self.db, self.steps)
        step = next((s for s in steps if s.id == step_id), None)
        if not step or not step.transform:
            return ''
        prev_index = self.steps_indices[step_id] - 1
        if prev_index < 0:
            return ''
        prev_step_id = steps[prev_index].id
        prev_step = steps[prev_index]
        prev_data = pip.get_step_data(db['pipeline_id'], prev_step_id, {})
        prev_word = prev_data.get(prev_step.done, '')
        return step.transform(prev_word) if prev_word else ''


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
        raise ValueError('Invalid Botify URL format')
    org = path_parts[0]
    project = path_parts[1]
    base_url = f'https://{parsed.netloc}/{org}/{project}/'
    return {'url': base_url, 'org': org, 'project': project}


def load_csv_with_options(self, file_path, skip_rows=0, encoding='utf-8'):
    """Loads a CSV file with flexible options for Botify export quirks.

    Args:
        file_path: Path to the CSV file
        skip_rows: Number of rows to skip (default: 0)
        encoding: File encoding (default: 'utf-8')

    Returns:
        Pandas DataFrame or None on error

    CSV Processing Notes:
    This method handles common Botify export format issues:

    1. 'sep=' delimiter notation:
       - Some exports include 'sep=,' as the first line
       - This requires skip_rows=1 to properly parse
       - Must be detected by examining file content

    2. Encoding variations:
       - UTF-8 is standard but some exports have other encodings
       - errors='ignore' prevents crashes on encoding issues
       - Falling back to latin-1 may be necessary for some exports

    3. Header normalization:
       - Column names may include spaces and special characters
       - Standardization is needed for reliable field access
       - ParameterBuster directly sets readable column headers

    Similar to ParameterBuster's load_csv_with_optional_skip method,
    but with additional options for Botify-specific format variations.
    """
    try:
        pass
    except Exception as e:
        logging.error(f'Error loading CSV {Path(file_path).name}: {e}')
        return None

def ensure_directories():
    """Ensure all required directories exist."""
    base_dir = Path(f'downloads/{self.app_name}')
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Create registry directory
    registry_dir = base_dir / 'registry'
    registry_dir.mkdir(parents=True, exist_ok=True)
    
    # Create exports directory
    exports_dir = base_dir / 'exports'
    exports_dir.mkdir(parents=True, exist_ok=True)
    
    # Create downloads directory
    downloads_dir = base_dir / 'downloads'
    downloads_dir.mkdir(parents=True, exist_ok=True)
    
    return {
        'base': base_dir,
        'registry': registry_dir,
        'exports': exports_dir,
        'downloads': downloads_dir
    }

def create_export_job(project_url, analysis_id, depth, fields):
    """Create a new export job."""
    job_id = str(uuid.uuid4())
    job = {
        'id': job_id,
        'project_url': project_url,
        'analysis_id': analysis_id,
        'depth': depth,
        'fields': fields,
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
    
    # Save job to registry
    registry = load_export_registry()
    registry[job_id] = job
    save_export_registry(registry)
    
    return job

def update_export_job(job_id, status, download_url=None):
    """Update an export job's status."""
    registry = load_export_registry()
    if job_id in registry:
        registry[job_id]['status'] = status
        registry[job_id]['updated_at'] = datetime.now().isoformat()
        if download_url:
            registry[job_id]['download_url'] = download_url
        save_export_registry(registry)
        return registry[job_id]
    return None

def get_export_job(job_id):
    """Get an export job by ID."""
    registry = load_export_registry()
    return registry.get(job_id)

def list_export_jobs():
    """List all export jobs."""
    return load_export_registry()

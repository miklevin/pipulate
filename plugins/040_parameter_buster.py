import asyncio
import gzip
import json
import logging
import os
import pickle
import re
import shutil
import socket
import time
import zipfile
from collections import Counter, namedtuple
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pandas as pd
from fasthtml.common import *
from loguru import logger

ROLES = ['Botify Employee']
'\nMulti-Export Workflow\nA workflow for performing multiple CSV exports from Botify.\n'
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
    APP_NAME = 'param_buster'
    DISPLAY_NAME = 'Parameter Buster'
    ENDPOINT_MESSAGE = 'Extract and analyze URL parameters from any web address. Perfect for understanding tracking codes and URL structure.'
    TRAINING_PROMPT = 'This workflow helps users analyze URL parameters and tracking codes. It uses the widget_container pattern to display parameter breakdowns and provides insights into URL structure and tracking mechanisms.'

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
        # --- SECTION_STEP_DEFINITION ---
        steps = [
            # --- START_WORKFLOW_SECTION: step_01_botify_project_url ---
            # This section handles Botify Project URL input and validation.
            # --- SECTION_STEP_DEFINITION ---
            Step(id='step_01', done='botify_project', show='Botify Project URL', refill=True), 
            # --- END_SECTION_STEP_DEFINITION ---
            Step(id='step_02', done='analysis_selection', show='Download Crawl Analysis', refill=False), 
            Step(id='step_03', done='weblogs_check', show='Download Web Logs', refill=False), 
            Step(id='step_04', done='search_console_check', show='Download Search Console', refill=False), 
            Step(id='step_05', done='placeholder', show='Count Parameters Per Source', refill=True), 
            Step(id='step_06', done='parameter_optimization', show='Parameter Optimization', refill=True), 
            Step(id='step_07', done='robots_txt', show='Instructions & robots.txt', refill=False)
        ]
        # --- END_SECTION_STEP_DEFINITION ---
        routes = [(f'/{app_name}', self.landing), (f'/{app_name}/init', self.init, ['POST']), (f'/{app_name}/revert', self.handle_revert, ['POST']), (f'/{app_name}/finalize', self.finalize, ['GET', 'POST']), (f'/{app_name}/unfinalize', self.unfinalize, ['POST']), (f'/{app_name}/parameter_preview', self.parameter_preview, ['POST'])]
        self.steps = steps
        for step in steps:
            step_id = step.id
            routes.append((f'/{app_name}/{step_id}', getattr(self, step_id)))
            routes.append((f'/{app_name}/{step_id}_submit', getattr(self, f'{step_id}_submit'), ['POST']))
        routes.append((f'/{app_name}/step_04_complete', self.step_04_complete, ['POST']))
        routes.append((f'/{app_name}/step_02_process', self.step_02_process, ['POST']))
        routes.append((f'/{app_name}/step_03_process', self.step_03_process, ['POST']))
        routes.append((f'/{app_name}/step_05_process', self.step_05_process, ['POST']))
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ['GET']
            app.route(path, methods=method_list)(handler)
        self.step_messages = {'finalize': {'ready': 'All steps complete. Ready to finalize workflow.', 'complete': f'Workflow finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes.'}, 'step_02': {'input': f"{pip.fmt('step_02')}: Please select a crawl analysis for this project.", 'complete': 'Crawl analysis download complete. Continue to next step.'}, 'step_06': {'input': f"{pip.fmt('step_06')}: Please enter value for Minimum Frequency.", 'complete': 'Code syntax highlighting complete. Ready to finalize.'}}
        for step in steps:
            if step.id not in self.step_messages:
                self.step_messages[step.id] = {'input': f'{pip.fmt(step.id)}: Please complete {step.show}.', 'complete': f'{step.show} complete. Continue to next step.'}
        self.step_messages['step_04'] = {'input': f"{pip.fmt('step_04')}: Please check if the project has Search Console data.", 'complete': 'Search Console check complete. Continue to next step.'}
        self.step_messages['step_03'] = {'input': f"{pip.fmt('step_03')}: Please check if the project has web logs available.", 'complete': 'Web logs check complete. Continue to next step.'}
        self.step_messages['step_05'] = {'input': f"{pip.fmt('step_05')}: Please count the parameters.", 'complete': 'Parameter count complete. Ready to finalize.'}
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

    async def landing(self, request):
        """Renders the initial landing page with the key input form or a message if Botify token is missing."""
        pip, pipeline, steps, app_name = (self.pipulate, self.pipeline, self.steps, self.app_name)
        title = f'{self.DISPLAY_NAME or app_name.title()}'
        token_exists = os.path.exists('botify_token.txt')
        if not token_exists:
            return Container(Card(H2(title), P(self.ENDPOINT_MESSAGE, cls='text-secondary'), Div(H3('Botify Connection Required', style='color: #e74c3c;'), P('To use the Parameter Buster workflow, you must first connect with Botify.', cls='mb-10px'), P('Please run the "Connect With Botify" workflow to set up your Botify API token.', style='margin-bottom: 20px;'), P('Once configured, you can return to this workflow.', style='font-style: italic; color: #666;'))), Div(id=f'{app_name}-container'))
        full_key, prefix, user_part = pip.generate_pipeline_key(self)
        default_value = full_key
        pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in pipeline() if record.pkey.startswith(prefix)]
        datalist_options = [f"{prefix}{record_key.replace(prefix, '')}" for record_key in matching_records]
        return Container(Card(H2(title), P(self.ENDPOINT_MESSAGE, cls='text-secondary'), Form(pip.wrap_with_inline_button(Input(placeholder='Existing or new 🗝 here (Enter for auto)', name='pipeline_id', list='pipeline-ids', type='search', required=False, autofocus=True, value=default_value, _onfocus='this.setSelectionRange(this.value.length, this.value.length)', cls='contrast'), button_label=f'Enter 🔑', button_class='secondary'), pip.update_datalist('pipeline-ids', options=datalist_options if datalist_options else None), hx_post=f'/{app_name}/init', hx_target=f'#{app_name}-container')), Div(id=f'{app_name}-container'))

    async def init(self, request):
        """Handles the key submission, initializes state, and renders the step UI placeholders."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        form = await request.form()
        user_input = form.get('pipeline_id', '').strip()
        if not user_input:
            from starlette.responses import Response
            response = Response('')
            response.headers['HX-Refresh'] = 'true'
            return response
        context = pip.get_plugin_context(self)
        profile_name = context['profile_name'] or 'default'
        plugin_name = context['plugin_name'] or app_name
        profile_part = profile_name.replace(' ', '_')
        plugin_part = plugin_name.replace(' ', '_')
        expected_prefix = f'{profile_part}-{plugin_part}-'
        if user_input.startswith(expected_prefix):
            pipeline_id = user_input
        else:
            _, prefix, user_provided_id = pip.generate_pipeline_key(self, user_input)
            pipeline_id = f'{prefix}{user_provided_id}'
        db['pipeline_id'] = pipeline_id
        state, error = pip.initialize_if_missing(pipeline_id, {'app_name': app_name})
        if error:
            return error
        await self.message_queue.add(pip, f'Workflow ID: {pipeline_id}', verbatim=True, spaces_before=0)
        await self.message_queue.add(pip, f"Return later by selecting '{pipeline_id}' from the dropdown.", verbatim=True, spaces_before=0)
        return Div(Div(id='step_01', hx_get=f'/{app_name}/step_01', hx_trigger='load'), id=f'{app_name}-container')

    async def finalize(self, request):
        """Handles GET request to show Finalize button and POST request to lock the workflow.

        # PATTERN NOTE: The finalize step is the final destination of the chain reaction
        # and should be triggered by the last content step's submit handler.
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        pipeline_id = db.get('pipeline_id', 'unknown')
        finalize_step = steps[-1]
        finalize_data = pip.get_step_data(pipeline_id, finalize_step.id, {})
        if request.method == 'GET':
            if finalize_step.done in finalize_data:
                return Card(H3('Workflow is locked.'), Form(Button(pip.UNLOCK_BUTTON_LABEL, type='submit', cls='secondary outline'), hx_post=f'/{app_name}/unfinalize', hx_target=f'#{app_name}-container'), id=finalize_step.id)
            else:
                all_steps_complete = all((pip.get_step_data(pipeline_id, step.id, {}).get(step.done) for step in steps[:-1]))
                if all_steps_complete:
                    await self.message_queue.add(pip, 'All steps are complete. You can now finalize the workflow or revert to any step to make changes.', verbatim=True)
                    return Card(H3('All steps complete. Finalize?'), P('You can revert to any step and make changes.', cls='text-secondary'), Form(Button('Finalize 🔒', type='submit', cls='primary'), hx_post=f'/{app_name}/finalize', hx_target=f'#{app_name}-container'), id=finalize_step.id)
                else:
                    return Div(id=finalize_step.id)
        else:
            await pip.finalize_workflow(pipeline_id)
            await self.message_queue.add(pip, self.step_messages['finalize']['complete'], verbatim=True)
            return pip.rebuild(app_name, steps)

    async def unfinalize(self, request):
        """Handles POST request to unlock the workflow."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        pipeline_id = db.get('pipeline_id', 'unknown')
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, 'Workflow unfinalized! You can now revert to any step and make changes.', verbatim=True)
        return pip.rebuild(app_name, steps)

    async def get_suggestion(self, step_id, state):
        """Gets a suggested input value for a step, often using the previous step's transformed output."""
        pip, db, steps = (self.pipulate, self.db, self.steps)
        step = next((s for s in steps if s.id == step_id), None)
        if not step or not step.transform:
            return ''
        prev_index = self.steps_indices[step_id] - 1
        if prev_index < 0:
            return ''
        prev_step = steps[prev_index]
        prev_data = pip.get_step_data(db['pipeline_id'], prev_step.id, {})
        prev_value = prev_data.get(prev_step.done, '')
        return step.transform(prev_value) if prev_value else ''

    async def handle_revert(self, request):
        """Handles POST request to revert to a previous step, clearing subsequent step data."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        form = await request.form()
        step_id = form.get('step_id')
        pipeline_id = db.get('pipeline_id', 'unknown')
        if not step_id:
            return P('Error: No step specified', style=self.pipulate.get_style('error'))
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        state = pip.read_state(pipeline_id)
        state['_revert_target'] = step_id
        pip.write_state(pipeline_id, state)
        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        await self.message_queue.add(pip, f'Reverted to {step_id}. All subsequent data has been cleared.', verbatim=True)
        return pip.rebuild(app_name, steps)

    # --- START_WORKFLOW_SECTION: step_01_botify_project_url ---
    # This section handles Botify Project URL input and validation.
    # --- SECTION_STEP_METHODS ---
    async def step_01(self, request):
        """Handles GET request for Botify URL input widget.

        # STEP PATTERN: GET handler returns current step UI + empty placeholder for next step
        # Important: The next step div should NOT have hx_trigger here, only in the submit handler
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        project_data_str = step_data.get(step.done, '')
        project_data = json.loads(project_data_str) if project_data_str else {}
        project_url = project_data.get('url', '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and project_data:
            return Div(Card(H3(f'🔒 {step.show}'), Div(P(f"Project: {project_data.get('project_name', '')}"), Small(project_url, style='word-break: break-all;'), cls='custom-card-padding-bg')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif project_data and state.get('_revert_target') != step_id:
            project_name = project_data.get('project_name', '')
            username = project_data.get('username', '')
            project_info = Div(H4(f'Project: {project_name}'), P(f'Username: {username}'), Small(project_url, style='word-break: break-all;'), style='padding: 10px; background: #f8f9fa; border-radius: 5px;')
            return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: {project_url}', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        else:
            display_value = project_url if step.refill and project_url else ''
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            return Div(Card(H3(f'{step.show}'), P('Enter a Botify project URL:'), Small('Example: ', Span('https://app.botify.com/uhnd-com/uhnd.com-demo-account/', id='copy-example-url', style='cursor: pointer; color: #888; text-decoration: none;', hx_on_click='document.querySelector(\'input[name="botify_url"]\').value = this.innerText; this.style.color = \'#28a745\'; setTimeout(() => this.style.color = \'#888\', 1000)', title='Click to use this example URL'), style='display: block; margin-bottom: 10px; color: #666; font-style: italic;'), Form(Input(type='url', name='botify_url', placeholder='https://app.botify.com/org/project/', value=display_value, required=True, pattern='https://(app|analyze)\\.botify\\.com/[^/]+/[^/]+/[^/]+.*', cls='w-full'), Div(Button('Use this URL ▸', type='submit', cls='primary'), cls='mt-vh text-end'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')), Div(id=next_step_id), id=step_id)

    async def step_01_submit(self, request):
        """Process the submission for Botify URL input widget.

        # STEP PATTERN: Submit handler stores state and returns:
        # 1. Revert control for the completed step
        # 2. Next step div with explicit hx_trigger="load" to chain reaction to next step
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        form = await request.form()
        botify_url = form.get('botify_url', '').strip()
        is_valid, message, project_data = self.validate_botify_url(botify_url)
        if not is_valid:
            return P(f'Error: {message}', style=pip.get_style('error'))
        project_data_str = json.dumps(project_data)
        await pip.set_step_data(pipeline_id, step_id, project_data_str, steps)
        await self.message_queue.add(pip, f"{step.show} complete: {project_data['project_name']}", verbatim=True)
        project_name = project_data.get('project_name', '')
        project_url = project_data.get('url', '')
        project_info = Div(H4(f'Project: {project_name}'), Small(project_url, style='word-break: break-all;'), style='padding: 10px; background: #f8f9fa; border-radius: 5px;')
        return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: {project_url}', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
    # --- END_SECTION_STEP_METHODS ---

    # --- SECTION_HELPER_METHODS ---
    def validate_botify_url(self, url):
        """Validate a Botify project URL and extract project information."""
        url = url.strip()
        if not url:
            return (False, 'URL is required', {})
        try:
            if not url.startswith(('https://app.botify.com/', 'https://analyze.botify.com/')):
                return (False, 'URL must be a Botify project URL (starting with https://app.botify.com/ or https://analyze.botify.com/)', {})
            parsed_url = urlparse(url)
            path_parts = [p for p in parsed_url.path.strip('/').split('/') if p]
            if len(path_parts) < 2:
                return (False, 'Invalid Botify URL: must contain at least organization and project', {})
            org_slug = path_parts[0]
            project_slug = path_parts[1]
            canonical_url = f'https://{parsed_url.netloc}/{org_slug}/{project_slug}/'
            project_data = {'url': canonical_url, 'username': org_slug, 'project_name': project_slug, 'project_id': f'{org_slug}/{project_slug}'}
            return (True, f'Valid Botify project: {project_slug}', project_data)
        except Exception as e:
            return (False, f'Error parsing URL: {str(e)}', {})
    # --- END_SECTION_HELPER_METHODS ---
    # --- END_WORKFLOW_SECTION: step_01_botify_project_url ---

    async def step_02(self, request):
        """Handles GET request for Analysis selection between steps 1 and 2."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        analysis_result_str = step_data.get(step.done, '')
        analysis_result = json.loads(analysis_result_str) if analysis_result_str else {}
        selected_slug = analysis_result.get('analysis_slug', '')
        prev_step_id = 'step_01'
        prev_step_data = pip.get_step_data(pipeline_id, prev_step_id, {})
        prev_data_str = prev_step_data.get('botify_project', '')
        if not prev_data_str:
            return P('Error: Project data not found. Please complete step 1 first.', style=pip.get_style('error'))
        project_data = json.loads(prev_data_str)
        project_name = project_data.get('project_name', '')
        username = project_data.get('username', '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and selected_slug:
            return Div(Card(H3(f'🔒 {step.show}'), Div(P(f'Project: {project_name}', style='margin-bottom: 5px;'), P(f'Selected Analysis: {selected_slug}', style='font-weight: bold;'), cls='custom-card-padding-bg')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif selected_slug and state.get('_revert_target') != step_id:
            return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: {selected_slug}', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        try:
            api_token = self.read_api_token()
            if not api_token:
                return P('Error: Botify API token not found. Please connect with Botify first.', style=pip.get_style('error'))
            logging.info(f'Getting analyses for {username}/{project_name}')
            slugs = await self.fetch_analyses(username, project_name, api_token)
            logging.info(f'Got {(len(slugs) if slugs else 0)} analyses')
            if not slugs:
                return P(f'Error: No analyses found for project {project_name}. Please check your API access.', style=pip.get_style('error'))
            selected_value = selected_slug if selected_slug else slugs[0]
            downloaded_slugs = set()
            for slug in slugs:
                filepath = await self.get_deterministic_filepath(username, project_name, slug, 'crawl')
                exists, _ = await self.check_file_exists(filepath)
                if exists:
                    downloaded_slugs.add(slug)
            await self.message_queue.add(pip, self.step_messages.get(step_id, {}).get('input', f'Select an analysis for {project_name}'), verbatim=True)
            return Div(Card(H3(f'{step.show}'), P(f"Select an analysis for project '{project_name}'"), P(f'Organization: {username}', cls='text-secondary'), Form(Select(*[Option(f'{slug} (Downloaded)' if slug in downloaded_slugs else slug, value=slug, selected=slug == selected_value) for slug in slugs], name='analysis_slug', required=True, autofocus=True), Button('Download Crawl Analysis ▸', type='submit', cls='mt-10px primary'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')), Div(id=next_step_id), id=step_id)
        except Exception as e:
            logging.exception(f'Error in {step_id}: {e}')
            return P(f'Error fetching analyses: {str(e)}', style=pip.get_style('error'))

    async def step_02_submit(self, request):
        """Process the selected analysis slug for step_02 and download crawl data."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        prev_step_id = 'step_01'
        prev_step_data = pip.get_step_data(pipeline_id, prev_step_id, {})
        prev_data_str = prev_step_data.get('botify_project', '')
        if not prev_data_str:
            return P('Error: Project data not found. Please complete step 1 first.', style=pip.get_style('error'))
        project_data = json.loads(prev_data_str)
        project_name = project_data.get('project_name', '')
        username = project_data.get('username', '')
        form = await request.form()
        analysis_slug = form.get('analysis_slug', '').strip()
        if not analysis_slug:
            return P('Error: No analysis selected', style=pip.get_style('error'))
        await self.message_queue.add(pip, f'Selected analysis: {analysis_slug}. Starting crawl data download...', verbatim=True)
        analysis_result = {'analysis_slug': analysis_slug, 'project': project_name, 'username': username, 'timestamp': datetime.now().isoformat(), 'download_started': True}
        analysis_result_str = json.dumps(analysis_result)
        await pip.set_step_data(pipeline_id, step_id, analysis_result_str, steps)
        return Card(H3(f'{step.show}'), P(f"Downloading data for analysis '{analysis_slug}'..."), Progress(style='margin-top: 10px;'), Script("\n            setTimeout(function() {\n                htmx.ajax('POST', '" + f'/{app_name}/step_02_process' + "', {\n                    target: '#" + step_id + "',\n                    values: { \n                        'analysis_slug': '" + analysis_slug + "',\n                        'username': '" + username + "',\n                        'project_name': '" + project_name + "'\n                    }\n                });\n            }, 500);\n            "), id=step_id)

    async def step_03(self, request):
        """Handles GET request for checking if a Botify project has web logs."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_03'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        check_result_str = step_data.get(step.done, '')
        check_result = json.loads(check_result_str) if check_result_str else {}
        prev_step_id = 'step_01'
        prev_step_data = pip.get_step_data(pipeline_id, prev_step_id, {})
        prev_data_str = prev_step_data.get('botify_project', '')
        if not prev_data_str:
            return P('Error: Project data not found. Please complete step 1 first.', style=pip.get_style('error'))
        project_data = json.loads(prev_data_str)
        project_name = project_data.get('project_name', '')
        username = project_data.get('username', '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and check_result:
            has_logs = check_result.get('has_logs', False)
            status_text = 'HAS web logs' if has_logs else 'does NOT have web logs'
            status_color = 'green' if has_logs else 'red'
            return Div(Card(H3(f'🔒 {step.show}'), Div(P(f'Project {project_name}', style='margin-bottom: 5px;'), P(f'Status: Project {status_text}', style=f'color: {status_color}; font-weight: bold;'), cls='custom-card-padding-bg')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif check_result and state.get('_revert_target') != step_id:
            has_logs = check_result.get('has_logs', False)
            status_text = 'HAS web logs' if has_logs else 'does NOT have web logs'
            status_color = 'green' if has_logs else 'red'
            return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: Project {status_text}', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        else:
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            return Div(Card(H3(f'{step.show}'), P(f"Download Web Logs for '{project_name}'"), P(f'Organization: {username}', cls='text-secondary'), Form(Button('Download Web Logs ▸', type='submit', cls='primary'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')), Div(id=next_step_id), id=step_id)

    async def step_03_submit(self, request):
        """Process the check for Botify web logs and download if available."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_03'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        prev_step_id = 'step_01'
        prev_step_data = pip.get_step_data(pipeline_id, prev_step_id, {})
        prev_data_str = prev_step_data.get('botify_project', '')
        if not prev_data_str:
            return P('Error: Project data not found. Please complete step 1 first.', style=pip.get_style('error'))
        project_data = json.loads(prev_data_str)
        project_name = project_data.get('project_name', '')
        username = project_data.get('username', '')
        analysis_step_id = 'step_02'
        analysis_step_data = pip.get_step_data(pipeline_id, analysis_step_id, {})
        analysis_data_str = analysis_step_data.get('analysis_selection', '')
        if not analysis_data_str:
            return P('Error: Analysis data not found. Please complete step 2 first.', style=pip.get_style('error'))
        analysis_data = json.loads(analysis_data_str)
        analysis_slug = analysis_data.get('analysis_slug', '')
        await self.message_queue.add(pip, f"Downloading Web Logs for '{project_name}'...", verbatim=True)
        return Card(H3(f'{step.show}'), P(f"Downloading Web Logs for '{project_name}'..."), Progress(style='margin-top: 10px;'), Script("\n            setTimeout(function() {\n                htmx.ajax('POST', '" + f'/{app_name}/step_03_process' + "', {\n                    target: '#" + step_id + "',\n                    values: { \n                        'analysis_slug': '" + analysis_slug + "',\n                        'username': '" + username + "',\n                        'project_name': '" + project_name + "'\n                    }\n                });\n            }, 500);\n            "), id=step_id)

    async def step_04(self, request):
        """Handles GET request for checking if a Botify project has Search Console data."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_04'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        check_result_str = step_data.get(step.done, '')
        check_result = json.loads(check_result_str) if check_result_str else {}
        prev_step_id = 'step_01'
        prev_step_data = pip.get_step_data(pipeline_id, prev_step_id, {})
        prev_data_str = prev_step_data.get('botify_project', '')
        if not prev_data_str:
            return P('Error: Project data not found. Please complete step 1 first.', style=pip.get_style('error'))
        project_data = json.loads(prev_data_str)
        project_name = project_data.get('project_name', '')
        username = project_data.get('username', '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and check_result:
            has_search_console = check_result.get('has_search_console', False)
            status_text = 'HAS Search Console data' if has_search_console else 'does NOT have Search Console data'
            status_color = 'green' if has_search_console else 'red'
            return Div(Card(H3(f'🔒 {step.show}'), Div(P(f'Project {project_name}', style='margin-bottom: 5px;'), P(f'Status: Project {status_text}', style=f'color: {status_color}; font-weight: bold;'), cls='custom-card-padding-bg')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif check_result and state.get('_revert_target') != step_id:
            has_search_console = check_result.get('has_search_console', False)
            status_text = 'HAS Search Console data' if has_search_console else 'does NOT have Search Console data'
            status_color = 'green' if has_search_console else 'red'
            return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: Project {status_text}', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        else:
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            return Div(Card(H3(f'{step.show}'), P(f"Download Search Console data for '{project_name}'"), P(f'Organization: {username}', cls='text-secondary'), Form(Button('Download Search Console ▸', type='submit', cls='primary'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')), Div(id=next_step_id), id=step_id)

    async def step_04_submit(self, request):
        """Process the check for Botify Search Console data."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_04'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        prev_step_id = 'step_01'
        prev_step_data = pip.get_step_data(pipeline_id, prev_step_id, {})
        prev_data_str = prev_step_data.get('botify_project', '')
        if not prev_data_str:
            return P('Error: Project data not found. Please complete step 1 first.', style=pip.get_style('error'))
        project_data = json.loads(prev_data_str)
        project_name = project_data.get('project_name', '')
        username = project_data.get('username', '')
        return Card(H3(f'{step.show}'), P(f"Downloading Search Console data for '{project_name}'..."), Progress(style='margin-top: 10px;'), Script("\n            setTimeout(function() {\n                htmx.ajax('POST', '" + f'/{app_name}/{step_id}_complete' + "', {\n                    target: '#" + step_id + "',\n                    values: { 'delay_complete': 'true' }\n                });\n            }, 1500);\n            "), id=step_id)

    async def step_04_complete(self, request):
        """Handles completion after the progress indicator has been shown."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_04'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        prev_step_id = 'step_01'
        prev_step_data = pip.get_step_data(pipeline_id, prev_step_id, {})
        prev_data_str = prev_step_data.get('botify_project', '')
        if not prev_data_str:
            return P('Error: Project data not found.', style=pip.get_style('error'))
        project_data = json.loads(prev_data_str)
        project_name = project_data.get('project_name', '')
        username = project_data.get('username', '')
        analysis_step_id = 'step_02'
        analysis_step_data = pip.get_step_data(pipeline_id, analysis_step_id, {})
        analysis_data_str = analysis_step_data.get('analysis_selection', '')
        if not analysis_data_str:
            return P('Error: Analysis data not found.', style=pip.get_style('error'))
        analysis_data = json.loads(analysis_data_str)
        analysis_slug = analysis_data.get('analysis_slug', '')
        try:
            has_search_console, error_message = await self.check_if_project_has_collection(username, project_name, 'search_console')
            if error_message:
                return Div(P(f'Error: {error_message}', style=pip.get_style('error')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
            check_result = {'has_search_console': has_search_console, 'project': project_name, 'username': username, 'timestamp': datetime.now().isoformat()}
            if has_search_console:
                await self.message_queue.add(pip, f'✓ Project has Search Console data, downloading...', verbatim=True)
                await self.process_search_console_data(pip, pipeline_id, step_id, username, project_name, analysis_slug, check_result)
            else:
                await self.message_queue.add(pip, f'Project does not have Search Console data (skipping download)', verbatim=True)
                check_result_str = json.dumps(check_result)
                await pip.set_step_data(pipeline_id, step_id, check_result_str, steps)
            status_text = 'HAS' if has_search_console else 'does NOT have'
            completed_message = 'Data downloaded successfully' if has_search_console else 'No Search Console data available'
            return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: {completed_message}', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        except Exception as e:
            logging.exception(f'Error in step_04_complete: {e}')
            return Div(P(f'Error: {str(e)}', style=pip.get_style('error')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)

    async def step_05(self, request):
        """Handles GET request for Parameter Optimization Generation."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_05'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        optimization_result = step_data.get(step.done, '')
        param_count = '40'
        if optimization_result:
            try:
                result_data = json.loads(optimization_result)
                param_count = str(result_data.get('param_count', 40))
            except json.JSONDecodeError:
                pass
        project_data = pip.get_step_data(pipeline_id, 'step_01', {}).get('botify_project', '{}')
        analysis_data = pip.get_step_data(pipeline_id, 'step_02', {}).get('analysis_selection', '{}')
        try:
            project_info = json.loads(project_data)
            analysis_info = json.loads(analysis_data)
        except json.JSONDecodeError:
            return P('Error: Could not load project or analysis data', style=pip.get_style('error'))
        username = project_info.get('username')
        project_name = project_info.get('project_name')
        analysis_slug = analysis_info.get('analysis_slug')
        if not all([username, project_name, analysis_slug]):
            return P('Error: Missing required project information', style=pip.get_style('error'))
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and optimization_result:
            try:
                visualization_widget = self.create_parameter_visualization_placeholder(optimization_result)
                return Div(Card(H3(f'🔒 {step.show}'), visualization_widget), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
            except Exception as e:
                logging.error(f'Error creating parameter visualization in finalized view: {str(e)}')
                return Div(Card(H3(f'🔒 {step.show}'), P('Parameter optimization completed', cls='mb-10px'), Div(P(f'Analysis data is locked.'), cls='custom-card-padding-bg')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif optimization_result and state.get('_revert_target') != step_id:
            try:
                visualization_widget = self.create_parameter_visualization_placeholder(optimization_result)
                return Div(pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f"{step.show}: {json.loads(optimization_result).get('total_unique_parameters', 0):,} unique parameters found", widget=visualization_widget, steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
            except Exception as e:
                logging.error(f'Error creating parameter visualization in revert view: {str(e)}')
                return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: Parameter analysis complete', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
        return Div(Card(H3(f'{step.show}'), P('This will create counters for your querystring parameters for each of the following:', cls='mb-15px'), Ul(Li('Crawl data from Botify analysis'), Li('Search Console performance data'), Li('Web logs data (if available)'), cls='mb-15px'), Form(Div(P("Note: It doesn't matter what you choose here. This slider only controls how many parameters are displayed and can be adjusted at any time. It does not affect the underlying analysis.", style=(pip.get_style('muted') or '') + 'margin-bottom: 10px;'), Label(NotStr('<strong>Number of Parameters to Show:</strong>'), For='param_count', style='min-width: 220px;'), Input(type='range', name='param_count_slider', id='param_count_slider', value=param_count, min='10', max='250', step='5', style='flex-grow: 1; margin: 0 10px;', _oninput="document.getElementById('param_count').value = this.value;"), Input(type='number', name='param_count', id='param_count', value=param_count, min='10', max='250', step='5', style='width: 100px;', _oninput="document.getElementById('param_count_slider').value = this.value;", _onkeydown="if(event.key === 'Enter') { event.preventDefault(); return false; }"), style='display: flex; align-items: center; gap: 10px; margin-bottom: 15px;'), Button('Count Parameters ▸', type='submit', cls='primary'), Script("\n                    // Define triggerParameterPreview in the global scope\n                    window.triggerParameterPreview = function() {\n                        // Use HTMX to manually trigger the parameter preview\n                        htmx.trigger('#parameter-preview', 'htmx:beforeRequest');\n                        htmx.ajax('POST', \n                            window.location.pathname.replace('step_06', 'parameter_preview'), \n                            {\n                                target: '#parameter-preview',\n                                values: {\n                                    'gsc_threshold': document.getElementById('gsc_threshold').value,\n                                    'min_frequency': document.getElementById('min_frequency').value\n                                }\n                            }\n                        );\n                    };\n                    "), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}', _onsubmit='if(event.submitter !== document.querySelector(\'button[type="submit"]\')) { event.preventDefault(); return false; }', _onkeydown="if(event.key === 'Enter') { event.preventDefault(); return false; }"), Script('\n                function triggerParameterPreview() {\n                    // Use HTMX to manually trigger the parameter preview\n                    htmx.trigger(\'#parameter-preview\', \'htmx:beforeRequest\');\n                    htmx.ajax(\'POST\', document.querySelector(\'input[name="gsc_threshold"]\').form.getAttribute(\'hx-post\').replace(\'step_06_submit\', \'parameter_preview\'), {\n                        target: \'#parameter-preview\',\n                        values: {\n                            \'gsc_threshold\': document.getElementById(\'gsc_threshold\').value,\n                            \'min_frequency\': document.getElementById(\'min_frequency\').value\n                        }\n                    });\n                }\n                ')), Div(id=next_step_id), id=step_id)

    async def step_05_submit(self, request):
        """Process the parameter optimization generation.

        # BACKGROUND PROCESSING PATTERN: This demonstrates the standard pattern for long-running operations:
        # 1. Return progress UI immediately
        # 2. Use Script tag with setTimeout + htmx.ajax to trigger background processing
        # 3. Background processor updates state and returns completed UI with next step trigger
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_05'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        form = await request.form()
        param_count = form.get('param_count', '40')
        return Card(H3(f'{step.show}'), P('Counting parameters...', cls='mb-15px'), Progress(style='margin-top: 10px;'), Script("\n            setTimeout(function() {\n                htmx.ajax('POST', '" + f'/{app_name}/step_05_process' + "', {\n                    target: '#" + step_id + "',\n                    values: { \n                        'pipeline_id': '" + pipeline_id + "',\n                        'param_count': '" + param_count + "'\n                    }\n                });\n            }, 500);\n            "), id=step_id)

    async def step_05_process(self, request):
        """Process parameter analysis using raw parameter counting and caching."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_05'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        form = await request.form()
        pipeline_id = form.get('pipeline_id', 'unknown')
        param_count = int(form.get('param_count', '40'))
        project_data = pip.get_step_data(pipeline_id, 'step_01', {}).get('botify_project', '{}')
        analysis_data = pip.get_step_data(pipeline_id, 'step_02', {}).get('analysis_selection', '{}')
        try:
            project_info = json.loads(project_data)
            analysis_info = json.loads(analysis_data)
        except json.JSONDecodeError:
            return P('Error: Could not load project or analysis data', style=pip.get_style('error'))
        username = project_info.get('username')
        project_name = project_info.get('project_name')
        analysis_slug = analysis_info.get('analysis_slug')
        if not all([username, project_name, analysis_slug]):
            return P('Error: Missing required project information', style=pip.get_style('error'))
        try:
            await self.message_queue.add(pip, 'Counting parameters...', verbatim=True)
            data_dir = await self.get_deterministic_filepath(username, project_name, analysis_slug)
            cache_filename = '_raw_param_counters_cache.pkl'
            files_to_process = {'not_indexable': 'crawl.csv', 'gsc': 'gsc.csv', 'weblogs': 'weblog.csv'}
            cached_data = self.load_raw_counters_from_cache(data_dir, cache_filename)
            output_data = None
            if cached_data is not None:
                output_data = cached_data
            if output_data is None:
                output_data = await self.calculate_and_cache_raw_counters(data_directory_path=data_dir, input_files_config=files_to_process, cache_filename=cache_filename)
                if output_data is None:
                    raise ValueError('Failed to calculate counters from source files')
            raw_counters = output_data.get('raw_counters', {})
            file_statuses = output_data.get('metadata', {}).get('file_statuses', {})
            parameter_summary = {'timestamp': datetime.now().isoformat(), 'data_sources': {}, 'cache_path': str(Path(data_dir) / cache_filename), 'param_count': param_count}
            total_unique_params = set()
            total_occurrences = 0
            for source, counter in raw_counters.items():
                unique_params = len(counter)
                source_occurrences = sum(counter.values())
                total_occurrences += source_occurrences
                status = file_statuses.get(source, 'Unknown')
                parameter_summary['data_sources'][source] = {'unique_parameters': unique_params, 'total_occurrences': source_occurrences, 'status': status, 'top_parameters': [{'name': param, 'count': count} for param, count in counter.most_common(10)] if counter else []}
                total_unique_params.update(counter.keys())
            parameter_summary['total_unique_parameters'] = len(total_unique_params)
            summary_str = json.dumps(parameter_summary)
            await pip.set_step_data(pipeline_id, step_id, summary_str, steps)
            await self.message_queue.add(pip, f"✓ Parameter analysis complete! Found {len(total_unique_params):,} unique parameters across {len(parameter_summary['data_sources'])} sources with {total_occurrences:,} total occurrences.", verbatim=True)
            visualization_widget = self.create_parameter_visualization_placeholder(summary_str)
            return Div(pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: {len(total_unique_params):,} unique parameters found', widget=visualization_widget, steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        except Exception as e:
            logging.exception(f'Error in step_05_process: {e}')
            return P(f'Error generating optimization: {str(e)}', style=pip.get_style('error'))

    async def step_06(self, request):
        """Handles GET request for the JavaScript Code Display Step."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_06'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, '')
        from fasthtml.common import to_xml
        from starlette.responses import HTMLResponse
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and user_val:
            try:
                widget_id = f"prism-widget-{pipeline_id.replace('-', '_')}-{step_id}"
                try:
                    values = json.loads(user_val)
                    code_to_display = values.get('js_code', '')
                    selected_params = values.get('selected_params', [])
                    gsc_threshold = values.get('gsc_threshold', '0')
                    min_frequency = values.get('min_frequency', '100000')
                except json.JSONDecodeError:
                    code_to_display = user_val
                    selected_params = []
                    gsc_threshold = '0'
                    min_frequency = '0'
                prism_widget = self.create_prism_widget(code_to_display, widget_id, 'javascript')
                response = HTMLResponse(to_xml(Div(Card(H3(f'🔒 {step.show}'), P(f'Parameter Optimization with {len(selected_params)} parameters'), prism_widget), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)))
                response.headers['HX-Trigger'] = json.dumps({'initializePrism': {'targetId': widget_id}})
                return response
            except Exception as e:
                logging.exception(f'Error creating Prism widget in locked view: {str(e)}')
                return Div(Card(H3(f'🔒 {step.show}'), P('Parameter optimization JavaScript'), Pre(f"JavaScript couldn't be displayed due to an error: {str(e)}")), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif user_val and state.get('_revert_target') != step_id:
            try:
                values = None
                try:
                    logging.info(f'Raw user_val in finalized state: {user_val[:100]}...')
                    values = json.loads(user_val) if user_val else {}
                    logging.info(f'Parsed JSON keys: {list(values.keys())}')
                except json.JSONDecodeError as json_err:
                    logging.error(f'JSON parsing error: {str(json_err)}')
                    code_to_display = user_val
                    gsc_threshold = '0'
                    min_frequency = '100000'
                    selected_params = []
                else:
                    code_to_display = values.get('js_code', '')
                    if not code_to_display and user_val:
                        code_to_display = user_val
                    gsc_threshold = values.get('gsc_threshold', '0')
                    min_frequency = values.get('min_frequency', '100000')
                    selected_params = values.get('selected_params', [])
                widget_id = f"prism-widget-{pipeline_id.replace('-', '_')}-{step_id}"
                logging.info(f'Code length: {len(code_to_display)}, Params count: {(len(selected_params) if selected_params else 0)}')
                prism_widget = self.create_prism_widget(code_to_display, widget_id, 'javascript')
                from fasthtml.common import to_xml
                from starlette.responses import HTMLResponse
                response = HTMLResponse(to_xml(Div(pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'Parameter Optimization with {(len(selected_params) if selected_params else 0)} parameters', widget=prism_widget, steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)))
                response.headers['HX-Trigger'] = json.dumps({'initializePrism': {'targetId': widget_id}})
                return response
            except Exception as e:
                logging.error(f'Error creating Prism widget: {str(e)}')
                state['_revert_target'] = step_id
                pip.write_state(pipeline_id, state)
        prev_step_data = pip.get_step_data(pipeline_id, 'step_05', {})
        prev_data_str = prev_step_data.get('placeholder', '')
        gsc_threshold = '0'
        min_frequency = '100000'
        try:
            if user_val:
                values = json.loads(user_val) if user_val else {}
                gsc_threshold = values.get('gsc_threshold', '0')
                min_frequency = values.get('min_frequency', '100000')
            elif prev_data_str:
                summary_data = json.loads(prev_data_str)
                cache_path = summary_data.get('cache_path')
                if cache_path and os.path.exists(cache_path):
                    try:
                        with open(cache_path, 'rb') as f:
                            cache_data = pickle.load(f)
                        raw_counters = cache_data.get('raw_counters', {})
                        weblogs_counter = None
                        gsc_counter = None
                        not_indexable_counter = None
                        source_mapping = {'weblogs': ['weblogs', 'weblog', 'logs', 'log'], 'gsc': ['gsc', 'search_console', 'searchconsole', 'google'], 'not_indexable': ['not_indexable', 'crawl', 'non_indexable', 'nonindexable']}
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
                        if gsc_counter and (weblogs_counter or not_indexable_counter):
                            combined_counter = Counter()
                            if weblogs_counter:
                                combined_counter.update(weblogs_counter)
                            if not_indexable_counter:
                                combined_counter.update(not_indexable_counter)
                            max_dead_param_frequency = 0
                            for param, count in combined_counter.items():
                                if gsc_counter.get(param, 0) == 0:
                                    max_dead_param_frequency = max(max_dead_param_frequency, count)
                            if max_dead_param_frequency > 0:
                                min_frequency = str(max_dead_param_frequency)
                                logging.info(f'Found optimal min_frequency: {min_frequency} from max dead parameter')
                    except Exception as e:
                        logging.error(f'Error calculating optimal frequency: {str(e)}')
        except json.JSONDecodeError:
            pass
        await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
        breakpoints_html = ''
        try:
            prev_step_data = pip.get_step_data(pipeline_id, 'step_05', {})
            prev_data_str = prev_step_data.get('placeholder', '')
            if prev_data_str:
                summary_data = json.loads(prev_data_str)
                cache_path = summary_data.get('cache_path')
                if cache_path and os.path.exists(cache_path):
                    with open(cache_path, 'rb') as f:
                        cache_data = pickle.load(f)
                    raw_counters = cache_data.get('raw_counters', {})
                    weblogs_counter = None
                    gsc_counter = None
                    not_indexable_counter = None
                    source_mapping = {'weblogs': ['weblogs', 'weblog', 'logs', 'log'], 'gsc': ['gsc', 'search_console', 'searchconsole', 'google'], 'not_indexable': ['not_indexable', 'crawl', 'non_indexable', 'nonindexable']}
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
                    if gsc_counter and (weblogs_counter or not_indexable_counter):
                        combined_counter = Counter()
                        if weblogs_counter:
                            combined_counter.update(weblogs_counter)
                        if not_indexable_counter:
                            combined_counter.update(not_indexable_counter)
                        all_frequencies = sorted(set(combined_counter.values()), reverse=True)
                        param_counts = {}
                        for freq in all_frequencies:
                            count = sum((1 for param, count in combined_counter.items() if gsc_counter.get(param, 0) <= 0 and count >= freq))
                            param_counts[freq] = count
                        breakpoints = []
                        ranges = [(1, 5), (5, 15), (15, 30), (30, 50), (50, 100)]
                        for min_count, max_count in ranges:
                            for freq in all_frequencies:
                                if param_counts[freq] >= min_count and param_counts[freq] <= max_count:
                                    breakpoints.append((freq, param_counts[freq]))
                                    break
                        max_freq = all_frequencies[0] if all_frequencies else 0
                        if max_freq > 0 and (not breakpoints or max_freq > breakpoints[0][0]):
                            if param_counts[max_freq] > 1:
                                breakpoints.insert(0, (max_freq, param_counts[max_freq]))
                        if breakpoints:
                            breakpoints_html = f\"\"\"
                            <div style="background: #222; padding: 10px; border-radius: 5px; margin: 15px 0;">
                                <h4 style="color: #ccc; margin-bottom: 10px;">Understanding the Optimization Settings</h4>
                                <p style="margin-bottom: 15px;">
                                    There are two critical settings that control how parameters are optimized:
                                </p>
                                <ul style="margin-bottom: 15px;">
                                    <li style="margin-bottom: 8px;">
                                        <span style="color: #50fa7b; font-weight: bold;">GSC Threshold</span>: Keep this at 0 to protect parameters 
                                        that appear in URLs receiving any Google Search Console impressions. These are your "working" parameters that 
                                        are actively involved in search visibility.
                                    </li>
                                    <li style="margin-bottom: 8px;">
                                        <span style="color: #ff8c00; font-weight: bold;">Minimum Frequency</span>: Controls how aggressive your optimization 
                                        will be. Higher values target only the most wasteful parameters, while lower values optimize more parameters but 
                                        require more careful testing.
                                    </li>
                                </ul>
                                <div style="background: #1a1a1a; padding: 10px; border-radius: 5px; margin: 15px 0;">
                                    <p style="color: #888; font-style: italic;">
                                        Instead of manually adjusting these values, we've identified key breakpoints below. Click the 
                                        <span style="color: #ff8c00; font-weight: bold;">orange numbers</span> to see which parameters would be affected. 
                                        Start conservatively with higher frequencies (fewer parameters) and gradually become more aggressive by selecting 
                                        lower frequencies.
                                    </p>
                                </div>
                                <h5 style="margin: 15px 0 10px 0; color: #ccc;">Meaningful Min Frequency Values (with GSC=0):</h5>
                                <table style="margin-bottom: 10px; font-size: 0.9em;">
                            \"\"\"
                            for freq, count in breakpoints:
                                rounded_freq = freq if freq < 100 else int(freq // 100 * 100)
                                breakpoints_html += f\"\"\"
                                    <tr>
                                        <td style="color: #bbb; padding-right: 10px;">Show {count} parameter{('' if count == 1 else 's')}:</td>
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
                                               style="color: #ff8c00; text-decoration: underline; cursor: pointer;">{('~' if freq > 100 else '')}{freq:,}</a>
                                        </td>
                                    </tr>
                                \"\"\"
                            breakpoints_html += '\n                                </table>\n                            </div>\n                            '
        except Exception as e:
            logging.error(f'Error calculating breakpoints: {e}')
            breakpoints_html = ''
        max_frequency = breakpoints[0][0] if breakpoints else 250000
        breakpoints_info = ''
        if breakpoints and gsc_threshold == 0:
            breakpoints_info = Div(H5('Meaningful Min Frequency Values (with GSC=0):', style='margin-bottom: 5px; color: #ccc;'), Table(*[Tr(Td(f'Show {count} parameters:', style='color: #bbb; padding-right: 10px;'), Td(f"{('~' if freq > 100 else '')}{freq:,}", style='color: #ff8c00; font-weight: bold; text-align: right;')) for freq, count in breakpoints_info], style='margin-bottom: 10px; font-size: 0.9em;'), style='background: #222; padding: 10px; border-radius: 5px; margin-bottom: 15px;')
        return Div(Card(H3(f'{pip.fmt(step_id)}: {step.show}'), P('Set thresholds for parameter optimization:'), Form(Div(Div(Small('Lower GSC Threshold to lower risk (generally keep set to 0)', style='color: #888; font-style: italic;'), Div(Label(NotStr('GSC Threshold:'), For='gsc_threshold', style='min-width: 180px; color: #888;'), Input(type='range', name='gsc_threshold_slider', id='gsc_threshold_slider', value=gsc_threshold, min='0', max='100', step='1', style='width: 60%; margin: 0 10px;', _oninput="document.getElementById('gsc_threshold').value = this.value; triggerParameterPreview();", hx_post=f'/{app_name}/parameter_preview', hx_trigger='input changed delay:300ms, load', hx_target='#parameter-preview', hx_include='#gsc_threshold, #min_frequency'), Input(type='number', name='gsc_threshold', id='gsc_threshold', value=gsc_threshold, min='0', max='100', style='width: 150px;', _oninput="document.getElementById('gsc_threshold_slider').value = this.value; triggerParameterPreview();", _onchange="document.getElementById('gsc_threshold_slider').value = this.value; triggerParameterPreview();", hx_post=f'/{app_name}/parameter_preview', hx_trigger='none', hx_target='#parameter-preview', hx_include='#gsc_threshold, #min_frequency'), style='display: flex; align-items: center; gap: 5px;')), Div(Small('Higher Minimum Frequency to reduce to only the biggest offenders', style='color: #888; font-style: italic;'), Div(Label(NotStr('<strong>Minimum Frequency:</strong>'), For='min_frequency', style='min-width: 180px;'), Input(type='range', name='min_frequency_slider', id='min_frequency_slider', value=min_frequency, min='0', max=str(max_frequency), step='1', style='flex-grow: 1; margin: 0 10px;', _oninput="document.getElementById('min_frequency').value = this.value; triggerParameterPreview();", hx_post=f'/{app_name}/parameter_preview', hx_trigger='input changed delay:300ms', hx_target='#parameter-preview', hx_include='#gsc_threshold, #min_frequency'), Input(type='number', name='min_frequency', id='min_frequency', value=min_frequency, min='0', max=str(max_frequency), step='1', style='width: 150px;', _oninput="document.getElementById('min_frequency_slider').value = this.value; triggerParameterPreview();", _onchange="document.getElementById('min_frequency_slider').value = this.value; triggerParameterPreview();", hx_post=f'/{app_name}/parameter_preview', hx_trigger='none', hx_target='#parameter-preview', hx_include='#gsc_threshold, #min_frequency'), style='display: flex; align-items: center; gap: 5px;'), style='margin-bottom: 15px;'), NotStr(breakpoints_html) if breakpoints_html else None, Div(H4('Parameters That Would Be Optimized:'), Div(P('Adjust thresholds above to see which parameters would be optimized.', style='color: #888; font-style: italic;'), id='parameter-preview', style='max-height: 300px; overflow-y: auto; background: #111; border-radius: 5px; padding: 10px; margin-bottom: 15px;'), style='margin-bottom: 20px;'), Div(Button('Create Optimization ▸', type='submit', cls='primary'), style='margin-top: 1vh; text-align: right;'), cls='w-full'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')), Div(id=next_step_id), id=step_id)

    async def step_06_submit(self, request):
        """Process the submission for the parameter threshold settings."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_06'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get('pipeline_id', 'unknown')
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        form = await request.form()
        gsc_threshold = form.get('gsc_threshold', '0')
        min_frequency = form.get('min_frequency', '100000')
        prev_step_data = pip.get_step_data(pipeline_id, 'step_05', {})
        prev_data_str = prev_step_data.get('placeholder', '')
        selected_params = []
        try:
            if prev_data_str:
                summary_data = json.loads(prev_data_str)
                cache_path = summary_data.get('cache_path')
                if cache_path and os.path.exists(cache_path):
                    with open(cache_path, 'rb') as f:
                        cache_data = pickle.load(f)
                    raw_counters = cache_data.get('raw_counters', {})
                    weblogs_counter = None
                    gsc_counter = None
                    not_indexable_counter = None
                    source_mapping = {'weblogs': ['weblogs', 'weblog', 'logs', 'log'], 'gsc': ['gsc', 'search_console', 'searchconsole', 'google'], 'not_indexable': ['not_indexable', 'crawl', 'non_indexable', 'nonindexable']}
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
                    if gsc_counter and (weblogs_counter or not_indexable_counter):
                        combined_counter = Counter()
                        if weblogs_counter:
                            combined_counter.update(weblogs_counter)
                        if not_indexable_counter:
                            combined_counter.update(not_indexable_counter)
                        for param, count in combined_counter.items():
                            param_gsc_count = gsc_counter.get(param, 0)
                            if param_gsc_count <= int(gsc_threshold) and count >= int(min_frequency):
                                selected_params.append(param)
            selected_params_js_array = json.dumps(selected_params)
            js_code = f\"\"\"// Function to remove query parameters from a URL
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
\"\"\"
            pip.append_to_history(f'[OPTIMIZATION CODE] Generated PageWorkers optimization for {len(selected_params)} parameters:\\n{js_code}', quiet=True)
            threshold_data = {'gsc_threshold': gsc_threshold, 'min_frequency': min_frequency, 'selected_params': selected_params, 'js_code': js_code}
            user_val = json.dumps(threshold_data)
            await pip.set_step_data(pipeline_id, step_id, user_val, steps)
            widget_id = f"prism-widget-{pipeline_id.replace('-', '_')}-{step_id}"
            prism_widget = self.create_prism_widget(js_code, widget_id, 'javascript')
            from fasthtml.common import to_xml
            from starlette.responses import HTMLResponse
            response = HTMLResponse(to_xml(Div(pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'Parameter Optimization with {(len(selected_params) if selected_params else 0)} parameters', widget=prism_widget, steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)))
            response.headers['HX-Trigger'] = json.dumps({'initializePrism': {'targetId': widget_id}})
            return response
        except Exception as e:
            logging.exception(f'Error in step_06_submit: {e}')
            return P(f'Error creating parameter optimization: {str(e)}', style=pip.get_style('error'))

    def create_prism_widget(self, code, widget_id, language='javascript'):
        \"\"\"Create a Prism.js syntax highlighting widget with copy functionality.\"\"\"
        textarea_id = f'{widget_id}_raw_code'
        container = Div(Div(H5('Copy/Paste into PageWorkers:'), Textarea(code, id=textarea_id, style='display: none;'), NotStr('\n                <style>\n                    /* Remove padding from pre > code */\n                    #' + widget_id + ' pre > code {\n                        padding: 0 !important;\n                    }\n                </style>\n                '), Pre(Code(code, cls=f'language-{language}'), cls='line-numbers'), cls='mt-4'), id=widget_id)
        init_script = Script(f\"\"\"
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
            \"\"\", type='text/javascript')
        return Div(container, init_script)

    def load_raw_counters_from_cache(self, data_directory_path, cache_filename='_raw_param_counters_cache.pkl'):
        \"\"\"Loads raw counters data from a cache file.\"\"\"
        data_dir = Path(data_directory_path)
        cache_file_path = data_dir / cache_filename
        if not cache_file_path.is_file():
            self.pipulate.append_to_history(f'[CACHE] No parameter counter cache found at {cache_file_path}', quiet=True)
            return None
        try:
            with open(cache_file_path, 'rb') as f:
                counters_data = pickle.load(f)
            if isinstance(counters_data, dict) and 'raw_counters' in counters_data and isinstance(counters_data['raw_counters'], dict) and ('metadata' in counters_data) and isinstance(counters_data['metadata'], dict) and (counters_data['metadata'].get('cache_version', 0) >= 2.0):
                self.pipulate.append_to_history(f"[CACHE] Loaded parameter counters from cache: {len(counters_data['raw_counters'])} sources", quiet=True)
                return counters_data
            else:
                logging.error(f'Invalid or outdated cache file format in {cache_file_path}.')
                return None
        except (pickle.UnpicklingError, EOFError) as e:
            logging.error(f'Error loading cache file (it might be corrupted): {cache_file_path} - {e}')
            return None
        except Exception as e:
            logging.error(f'An unexpected error occurred loading the cache: {cache_file_path} - {e}')
            return None

    async def calculate_and_cache_raw_counters(self, data_directory_path, input_files_config, cache_filename='_raw_param_counters_cache.pkl'):
        \"\"\"
        Loads specified CSV files, performs a raw count of query parameters for each,
        and saves the counters to a cache file. Returns the counters and metadata.
        \"\"\"
        data_dir = Path(data_directory_path)
        if not data_dir.is_dir():
            logging.error(f'Provided data directory path is not valid: {data_directory_path}')
            return None
        raw_counters = {}
        file_statuses = {}
        url_column_priority = ['Full URL', 'URL']
        logging.info(f'Processing data from directory: {data_dir}')
        for key, filename in input_files_config.items():
            file_path = data_dir / filename
            logging.info(f"Processing file: {filename} (as '{key}')")
            if not file_path.is_file():
                logging.warning(f'File not found: {file_path}')
                raw_counters[key] = Counter()
                file_statuses[key] = 'File not found'
                continue
            try:
                df = self.load_csv_with_optional_skip(str(file_path))
                if df.empty or not any((col in df.columns for col in url_column_priority)):
                    logging.warning(f'No usable URL column in {filename}')
                    raw_counters[key] = Counter()
                    file_statuses[key] = 'No URL column'
                    continue
                logging.info(f'Counting parameters in {filename}...')
                file_counter = self.count_query_params(df, url_column_priority)
                raw_counters[key] = file_counter
                file_statuses[key] = f'Processed ({len(file_counter):,} unique params found)'
                logging.info(f'Counted {len(file_counter):,} unique parameters in {filename}')
            except Exception as e:
                logging.exception(f'Error processing {filename}: {e}')
                raw_counters[key] = Counter()
                file_statuses[key] = f'Error: {str(e)}'
        counters_data = {'raw_counters': raw_counters, 'metadata': {'data_directory_path': str(data_dir.resolve()), 'input_files_config': input_files_config, 'file_statuses': file_statuses, 'cache_timestamp': time.time(), 'cache_version': 2.0}}
        cache_file_path = data_dir / cache_filename
        logging.info(f'Saving raw counters to cache file: {cache_file_path}')
        try:
            os.makedirs(os.path.dirname(cache_file_path), exist_ok=True)
            with open(cache_file_path, 'wb') as f:
                pickle.dump(counters_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            logging.info('Cache saved successfully.')
        except Exception as e:
            logging.error(f'Error saving cache file: {e}')
        return counters_data

    def create_parameter_visualization_placeholder(self, summary_data_str=None):
        \"\"\"
        Create a visualization of parameters from all three data sources.
        \"\"\"
        TOP_PARAMS_COUNT = 40
        import base64
        import json
        import logging
        import os
        from collections import Counter
        from io import BytesIO, StringIO
        from pathlib import Path

        import matplotlib.pyplot as plt
        import numpy as np
        self.pipulate.append_to_history('[VISUALIZATION] Creating parameter distribution visualization', quiet=True)
        debug_info = []

        def add_debug(msg):
            debug_info.append(msg)
            logging.info(msg)
        try:
            add_debug('Starting parameter visualization')
            has_data = False
            total_params = 0
            data_sources = []
            source_counters = {'weblogs': Counter(), 'gsc': Counter(), 'not_indexable': Counter()}
            if summary_data_str:
                summary_data = json.loads(summary_data_str)
                total_params = summary_data.get('total_unique_parameters', 0)
                data_sources = list(summary_data.get('data_sources', {}).keys())
                TOP_PARAMS_COUNT = summary_data.get('param_count', 40)
                has_data = True
                add_debug(f'Data sources in summary: {data_sources}')
                cache_path = summary_data.get('cache_path')
                add_debug(f'Cache path: {cache_path}, exists: {(os.path.exists(cache_path) if cache_path else False)}')
                if cache_path and os.path.exists(cache_path):
                    try:
                        with open(cache_path, 'rb') as f:
                            cache_data = pickle.load(f)
                        raw_counters = cache_data.get('raw_counters', {})
                        add_debug(f'Raw counter keys in cache: {list(raw_counters.keys())}')
                        for key, counter in raw_counters.items():
                            top_items = list(counter.most_common(5))
                            add_debug(f"Raw counter '{key}' has {len(counter)} items. Top 5: {top_items}")
                        source_mapping = {'weblogs': ['weblogs', 'weblog', 'logs', 'log'], 'gsc': ['gsc', 'search_console', 'searchconsole', 'google'], 'not_indexable': ['not_indexable', 'crawl', 'non_indexable', 'nonindexable']}
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
                        add_debug(f'Error loading parameter data from cache: {e}')
                        add_debug(f'Cache file not found or invalid')
                    if all((len(counter) == 0 for counter in source_counters.values())) and has_data:
                        add_debug('No counter data from cache, using summary data directly')
                        for source, counter in source_counters.items():
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
            for source, counter in source_counters.items():
                top_items = counter.most_common(5)
                items_count = len(counter)
                total_count = sum(counter.values())
                add_debug(f"FINAL: Source '{source}' has {items_count} items with {total_count} total occurrences")
                if top_items:
                    add_debug(f'  Top 5 for {source}: {top_items}')
            all_params = set()
            for counter in source_counters.values():
                all_params.update(counter.keys())
            cache_data = {'raw_counters': source_counters, 'metadata': {'cache_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'file_statuses': {}}}
            results = []
            for param in all_params:
                wb_count = source_counters['weblogs'].get(param, 0)
                ni_count = source_counters['not_indexable'].get(param, 0)
                gsc_count = source_counters['gsc'].get(param, 0)
                total_count = wb_count + ni_count
                score = total_count / (gsc_count + 1)
                results.append((param, wb_count, ni_count, gsc_count, total_count, score))
            results_sorted = sorted(results, key=lambda x: x[5], reverse=True)
            top_params = [param for param, _, _, _, _, _ in results_sorted[:TOP_PARAMS_COUNT]]
            top_params.reverse()
            table_html = '\n            <style>\n                /* Column-specific colors that override the base rich table styles */\n                .weblogs-val { color: #4fa8ff !important; text-align: right; }\n                .not-index-val { color: #ff0000 !important; text-align: right; }\n                .gsc-val { color: #50fa7b !important; text-align: right; }\n                .score-val { color: #ffff00 !important; text-align: right; font-weight: bold; }\n                .na-val { color: #666666 !important; text-align: right; font-style: italic; }\n            </style>\n            <table class="param-table">\n                <caption>Displaying ' + str(TOP_PARAMS_COUNT) + ' Parameters with Scoring (to help identify optimization targets)</caption>\n                <tr class="header">\n                    <td class="header-cell"><span class="param-name">Parameter</span></td>\n                    <td class="header-cell"><span class="weblogs-val">Weblogs</span></td>\n                    <td class="header-cell"><span class="not-index-val">Not-Indexable</span></td>\n                    <td class="header-cell"><span class="gsc-val">GSC</span></td>\n                    <td class="header-cell"><span class="total-val">Total</span></td>\n                    <td class="header-cell"><span class="score-val">Score</span></td>\n                </tr>\n            '
            for param, wb, ni, gsc, total, score in results_sorted[:TOP_PARAMS_COUNT]:
                wb_display = f'{wb:,}' if wb is not None else '<span class="na-val">N/A</span>'
                ni_display = f'{ni:,}' if ni is not None else '<span class="na-val">N/A</span>'
                gsc_display = f'{gsc:,}' if gsc is not None else '<span class="na-val">N/A</span>'
                total_display = f'{total:,}' if total is not None else '<span class="na-val">N/A</span>'
                score_display = f'{score:,.0f}' if score is not None else '<span class="na-val">N/A</span>'
                table_html += f'\n                <tr>\n                    <td><span class="param-name">{param}</span></td>\n                    <td><span class="weblogs-val">{wb_display}</span></td>\n                    <td><span class="not-index-val">{ni_display}</span></td>\n                    <td><span class="gsc-val">{gsc_display}</span></td>\n                    <td><span class="total-val">{total_display}</span></td>\n                    <td><span class="score-val">{score_display}</span></td>\n                </tr>\n                '
            table_html += '</table>'
            figure_height = max(15, min(TOP_PARAMS_COUNT * 0.65, 50))
            add_debug(f'Chart parameters: count={TOP_PARAMS_COUNT}, final_height={figure_height}')
            plt.figure(figsize=(10, figure_height), facecolor='#13171f', constrained_layout=False)
            ax = plt.axes([0.25, 0.02, 0.7, 0.95])
            ax.set_facecolor('#13171f')
            for spine in ax.spines.values():
                spine.set_color('white')
            ax.spines['right'].set_visible(False)
            ax.spines['top'].set_visible(False)
            y_pos = np.arange(len(top_params))
            width = 0.25
            weblogs_values = [source_counters['weblogs'].get(param, 0) for param in top_params]
            crawl_values = [source_counters['not_indexable'].get(param, 0) for param in top_params]
            gsc_values = [source_counters['gsc'].get(param, 0) for param in top_params]
            max_value = max([max(weblogs_values or [0]), max(crawl_values or [0]), max(gsc_values or [0])])
            add_debug(f'Max value in data: {max_value}')
            ax.set_xscale('symlog')
            weblog_bars = ax.barh([p + width for p in y_pos], weblogs_values, width, color='#4fa8ff', label='Web Logs', alpha=0.9)
            crawl_bars = ax.barh(y_pos, crawl_values, width, color='#ff0000', label='Crawl Data', alpha=0.9)
            gsc_bars = ax.barh([p - width for p in y_pos], gsc_values, width, color='#50fa7b', label='Search Console', alpha=0.9)
            for bars in [weblog_bars, crawl_bars, gsc_bars]:
                for bar in bars:
                    if bar.get_width() == 0:
                        bar.set_hatch('/')
                        bar.set_alpha(0.3)
            ax.grid(axis='x', linestyle='--', alpha=0.2, color='white')
            truncated_params = []
            for param in top_params:
                if len(param) > 25:
                    truncated = param[:22] + '...'
                else:
                    truncated = param
                truncated_params.append(truncated)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(truncated_params, fontsize=8, color='white')
            ax.set_xlabel('Occurrences (log scale)', color='white')
            ax.set_ylabel('Parameters', color='white')
            ax.set_title(f'Displaying {TOP_PARAMS_COUNT} Parameters with Log Scale (to show smaller values)', color='white')
            ax.tick_params(axis='both', colors='white')
            ax.legend(loc='lower right', facecolor='#2d2d3a', edgecolor='#555555', labelcolor='white')
            if max_value > 0:
                ax.set_xlim(0, max_value * 2)
            for i, (wb, cr, gs) in enumerate(zip(weblogs_values, crawl_values, gsc_values)):
                if wb > 0:
                    text_pos = wb * 1.05
                    ax.text(text_pos, i + width, f'{wb:,}', va='center', fontsize=7, color='#4fa8ff')
                else:
                    ax.text(0.01, i + width, '0', va='center', ha='left', fontsize=7, color='#4fa8ff', alpha=0.5)
                if cr > 0:
                    text_pos = cr * 1.05
                    ax.text(text_pos, i, f'{cr:,}', va='center', fontsize=7, color='#ff0000', weight='bold')
                else:
                    ax.text(0.01, i, '0', va='center', ha='left', fontsize=7, color='#ff0000', alpha=0.5)
                if gs > 0:
                    text_pos = gs * 1.05
                    ax.text(text_pos, i - width, f'{gs:,}', va='center', fontsize=7, color='#50fa7b')
                else:
                    ax.text(0.01, i - width, '0', va='center', ha='left', fontsize=7, color='#50fa7b', alpha=0.5)
            y_min, y_max = (-width * 1.5, len(y_pos) - 1 + width * 1.5)
            ax.set_ylim(y_min, y_max)
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=120)
            plt.close()
            img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            file_status_html = '\n            <div style="margin: 15px 0; padding: 10px; background: #222; border-radius: 5px;">\n                <h5 style="margin-bottom: 10px; color: #ccc;">Data Source Status:</h5>\n                <table style="width: 100%; font-size: 0.9em;">\n            '
            source_display = {'weblogs': ('Web Logs', '#4fa8ff'), 'not_indexable': ('Not-Indexable', '#ff0000'), 'gsc': ('Search Console', '#50fa7b')}
            cache_metadata = cache_data.get('metadata', {}) if 'cache_data' in locals() else {}
            file_statuses = cache_metadata.get('file_statuses', {})
            for source, (display_name, color) in source_display.items():
                counter = source_counters.get(source, Counter())
                if len(counter) > 0:
                    status = f"Found ({cache_metadata.get('cache_timestamp', 'Unknown date')})"
                elif source in file_statuses:
                    status = file_statuses[source]
                else:
                    status = 'No Data Available'
                param_count = len(counter)
                total_occurrences = sum(counter.values())
                if param_count > 0:
                    status_color = '#50fa7b'
                elif source in file_statuses and 'error' in file_statuses[source].lower():
                    status_color = '#ff5555'
                else:
                    status_color = '#ff8c00'
                file_status_html += f'\n                    <tr>\n                        <td style="color: {color}; padding: 5px 0;">{display_name}:</td>\n                        <td style="color: {status_color}; text-align: right;">\n                            {param_count:,} parameters, {total_occurrences:,} occurrences\n                        </td>\n                        <td style="color: #888; text-align: right; font-style: italic;">\n                            ({status})\n                        </td>\n                    </tr>\n                '
            file_status_html += '\n                </table>\n            </div>\n            '
            debug_section = ''
            if debug_info:
                debug_section = Div(Details(Summary('Debug Information (click to expand)'), Pre('\n'.join(debug_info), style='background: #333; color: #eee; padding: 10px; border-radius: 5px; font-size: 0.8em; max-height: 300px; overflow-y: auto;'), cls='mt-4'))
            visualization = Div(Div(H4('Parameter Analysis Summary:'), P(f'Total unique parameters: {total_params:,}' if has_data else 'No data available yet'), P(f"Data sources: {', '.join(data_sources)}" if data_sources else 'No data sources processed yet'), NotStr(file_status_html), P('Note: The number of parameters shown below is controlled by the slider and only affects the visualization. It does not impact the underlying analysis. You can revert Step 5 and adjust it to up to 250.', style='font-size: 0.85em; color: #888; font-style: italic; margin-bottom: 15px;'), Div(H4('Understanding the Data Visualizations', style='color: #ccc; margin-bottom: 10px;'), P('The following two visualizations (bar chart and scoring matrix) are provided to help you understand the parameter distribution patterns across your data sources. While they offer valuable insights for SEO analysis and client discussions, they are supplementary tools only.', cls='mb-10px'), P('For optimization purposes, you can focus directly on the "Meaningful Min Frequency Values" table below to select your breakpoint, then proceed to create your optimization. The visualizations are here to help you make informed decisions and explain your strategy.', cls='mb-15px'), style='background: #222; padding: 15px; border-radius: 5px; margin-bottom: 20px;'), Div(NotStr(f'<img src="data:image/png;base64,{img_str}" style="width:100%; height:auto;" alt="Parameter Distribution Chart" />'), style='text-align: center; margin-top: 1rem;'), Div(H4('Understanding Your Data Sources', style='color: #ccc; margin-bottom: 10px;'), P('The table below shows parameter data from three critical sources:', cls='mb-10px'), Ul(Li(Span('Web Logs ', style='color: #4fa8ff; font-weight: bold;'), "(Blue): Shows Googlebot crawler behavior. High parameter counts here are natural as Google's crawler thoroughly explores your site structure.", style='margin-bottom: 8px;'), Li(Span('Not-Indexable ', style='color: #ff0000; font-weight: bold;'), "(Red): From Botify's crawl analysis, identifying URLs that cannot be indexed for various technical reasons. Parameters appearing here often indicate potential optimization opportunities.", style='margin-bottom: 8px;'), Li(Span('GSC ', style='color: #50fa7b; font-weight: bold;'), '(Green): URLs that have received any impressions in Google Search Console. Parameters appearing here are actively involved in your search presence and should be handled with caution. This is why we recommend keeping the GSC Threshold at 0.', style='margin-bottom: 8px;')), style='background: #222; padding: 15px; border-radius: 5px; margin: 20px 0;'), NotStr(table_html), debug_section, style='padding: 15px; background-color: var(--pico-card-background-color); border-radius: var(--pico-border-radius);'))
            return visualization
        except Exception as e:
            logging.exception(f'Error creating parameter visualization: {e}')
            error_msg = f'Error creating visualization: {str(e)}\n\nDebug info:\n' + '\n'.join(debug_info)
            return Div(NotStr(f"<div style='color: red; padding: 10px; background: #333; border-radius: 5px;'>{error_msg}</div>"), _raw=True)

    async def parameter_preview(self, request):
        """Process real-time parameter preview requests based on threshold settings."""
        pip, db, app_name = (self.pipulate, self.db, self.app_name)
        pipeline_id = db.get('pipeline_id', 'unknown')
        form = await request.form()
        gsc_threshold = int(form.get('gsc_threshold', '0'))
        min_frequency = int(form.get('min_frequency', '100000'))
        pip.append_to_history(f'[PARAMETER PREVIEW] Previewing parameters with GSC threshold={gsc_threshold} and min_frequency={min_frequency}', quiet=True)
        prev_step_data = pip.get_step_data(pipeline_id, 'step_05', {})
        prev_data_str = prev_step_data.get('placeholder', '')
        matching_params = []
        param_count = 0
        total_frequency = 0
        breakpoint_frequencies = []
        try:
            if prev_data_str:
                summary_data = json.loads(prev_data_str)
                cache_path = summary_data.get('cache_path')
                if cache_path and os.path.exists(cache_path):
                    with open(cache_path, 'rb') as f:
                        cache_data = pickle.load(f)
                    raw_counters = cache_data.get('raw_counters', {})
                    weblogs_counter = None
                    gsc_counter = None
                    not_indexable_counter = None
                    source_mapping = {'weblogs': ['weblogs', 'weblog', 'logs', 'log'], 'gsc': ['gsc', 'search_console', 'searchconsole', 'google'], 'not_indexable': ['not_indexable', 'crawl', 'non_indexable', 'nonindexable']}
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
                    if gsc_counter and (weblogs_counter or not_indexable_counter):
                        combined_counter = Counter()
                        if weblogs_counter:
                            combined_counter.update(weblogs_counter)
                        if not_indexable_counter:
                            combined_counter.update(not_indexable_counter)
                        if gsc_threshold == 0:
                            all_frequencies = sorted(set(combined_counter.values()), reverse=True)
                            param_counts = {}
                            for freq in all_frequencies:
                                count = sum((1 for param, count in combined_counter.items() if gsc_counter.get(param, 0) <= 0 and count >= freq))
                                param_counts[freq] = count
                            ranges = [(1, 5), (5, 15), (15, 30), (30, 50), (50, 100)]
                            for min_count, max_count in ranges:
                                for freq in all_frequencies:
                                    if param_counts[freq] >= min_count and param_counts[freq] <= max_count:
                                        breakpoint_frequencies.append((freq, param_counts[freq]))
                                        break
                        max_freq = all_frequencies[0] if all_frequencies else 0
                        if max_freq > 0 and (not breakpoint_frequencies or max_freq > breakpoint_frequencies[0][0]):
                            if param_counts[max_freq] > 1:
                                breakpoint_frequencies.insert(0, (max_freq, param_counts[max_freq]))
                        for param, count in combined_counter.items():
                            param_gsc_count = gsc_counter.get(param, 0)
                            if param_gsc_count <= gsc_threshold and count >= min_frequency:
                                score = count / (param_gsc_count + 1)
                                matching_params.append((param, count, param_gsc_count, score))
                                param_count += 1
                                total_frequency += count
                        matching_params.sort(key=lambda x: x[3], reverse=True)
        except Exception as e:
            logging.error(f'Error in parameter preview: {str(e)}')
            return Div(P(f'Error: {str(e)}', cls='text-invalid'))
        breakpoints_info = ''
        if breakpoint_frequencies and gsc_threshold == 0:
            breakpoints_info = Div(H5('Meaningful Min Frequency Values (with GSC=0):', style='margin-bottom: 5px; color: #ccc;'), Table(*[Tr(Td(f'Show {count} parameters:', style='color: #bbb; padding-right: 10px;'), Td(f"{('~' if freq > 100 else '')}{freq:,}", style='color: #ff8c00; font-weight: bold; text-align: right;')) for freq, count in breakpoints_info], style='margin-bottom: 10px; font-size: 0.9em;'), style='background: #222; padding: 10px; border-radius: 5px; margin-bottom: 15px;')
        if matching_params:
            display_limit = 5000
            display_message = ''
            if param_count > display_limit:
                display_message = f'(Displaying first {display_limit:,} of {param_count:,} matching parameters)'
            return Div(P(f'Found {param_count:,} parameters with total frequency of {total_frequency:,}'), P(display_message, style='color: #888; font-style: italic; margin-bottom: 10px;') if display_message else None, Table(Tr(Th('Parameter', style='text-align: left; color: cyan;'), Th('Web Logs', style='text-align: right; color: #4fa8ff;'), Th('Not-Indexable', style='text-align: right; color: #ff0000;'), Th('GSC', style='text-align: right; color: #50fa7b;'), Th('Score', style='text-align: right; color: #ffff00;')), *[Tr(Td(param, style='color: cyan;'), Td(f'{weblogs_counter.get(param, 0):,}' if weblogs_counter else 'N/A', style='text-align: right; color: #4fa8ff;'), Td(f'{not_indexable_counter.get(param, 0):,}' if not_indexable_counter else 'N/A', style='text-align: right; color: #ff0000;'), Td(f'{gsc_counter.get(param, 0):,}' if gsc_counter else 'N/A', style='text-align: right; color: #50fa7b;'), Td(f'{score:,.0f}', style='text-align: right; color: #ffff00; font-weight: bold;')) for param, count, gsc_count, score in matching_params[:display_limit]], style='width: 100%; border-collapse: collapse;'), cls='font-code')
        else:
            return P('No parameters match these criteria. Try adjusting the thresholds.', style='color: #ff5555; font-style: italic;')
    Script('\n    function setFrequencyAndPreview(value) {\n        // Update both the slider and the number input\n        const slider = document.getElementById("min_frequency_slider");\n        const input = document.getElementById("min_frequency");\n        \n        // Set values\n        slider.value = value;\n        input.value = value;\n        \n        // Trigger the parameter preview\n        triggerParameterPreview();\n        \n        // Optional: Add visual feedback\n        input.style.backgroundColor = "#224433";\n        setTimeout(function() {\n            input.style.backgroundColor = "";\n        }, 500);\n    }\n    ')

    async def step_07(self, request):
        """Handles GET request for Step 7 Markdown widget."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_07'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        step_06_data = pip.get_step_data(pipeline_id, 'step_06', {})
        parameters_info = {}
        try:
            if step_06_data.get('parameter_optimization'):
                param_data = json.loads(step_06_data.get('parameter_optimization'))
                parameters_info = {'selected_params': param_data.get('selected_params', []), 'gsc_threshold': param_data.get('gsc_threshold', '0'), 'min_frequency': param_data.get('min_frequency', '100000')}
        except (json.JSONDecodeError, TypeError):
            parameters_info = {'selected_params': [], 'gsc_threshold': '0', 'min_frequency': '100000'}
        try:
            markdown_data = json.loads(step_data.get(step.done, '{}'))
            markdown_content = markdown_data.get('markdown', '')
        except (json.JSONDecodeError, TypeError):
            markdown_content = ''
        if not markdown_content:
            params_list = parameters_info.get('selected_params', [])
            gsc_threshold = parameters_info.get('gsc_threshold', '0')
            min_frequency = parameters_info.get('min_frequency', '100000')
            try:
                min_frequency_int = int(min_frequency)
                min_frequency_formatted = f'{min_frequency_int:,}'
            except ValueError:
                min_frequency_formatted = min_frequency
            robots_txt_rules = '\n'.join([f'Disallow: /*?*{param}=*' for param in params_list])
            param_list_str = '\n'.join([f'- {param}' for param in params_list])
            markdown_content = f'# PageWorkers Optimization Ready to Copy/Paste\n\n## Instructions\n1. Copy/Paste the JavaScript (found above) into a new PageWorkers custom Optimization.\n2. Update the `REPLACE_ME!!!` with the ID found in the URL of the Optimization.\n\n**Parameter Optimization Settings**\n- GSC Threshold: {gsc_threshold}\n- Minimum Frequency: {min_frequency_formatted}\n- Total Parameters Optimized: {len(params_list)}\n\n[[DETAILS_START]]\n[[SUMMARY_START]]View all {len(params_list)} parameters[[SUMMARY_END]]\n\n{param_list_str}\n[[DETAILS_END]]\n\n[[DETAILS_START]]\n[[SUMMARY_START]]View robots.txt rules[[SUMMARY_END]]\n\n```robots.txt\nUser-agent: *\n{robots_txt_rules}\n```\n[[DETAILS_END]]\n\n**Important Notes:** robots.txt is advisory, not enforcement; prevents crawling but not indexing; for testing only\n'
            if step_data.get(step.done, '') == '':
                markdown_data = {'markdown': markdown_content, 'parameters_info': parameters_info}
                await self.update_state_with_html(pipeline_id, step_id, markdown_data, self.steps, clear_previous=False)
        widget_id = f"markdown-widget-{pipeline_id.replace('-', '_')}-{step_id}"
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data:
            markdown_widget = self.create_marked_widget(markdown_content, widget_id)
            from fasthtml.common import to_xml
            from starlette.responses import HTMLResponse
            response = HTMLResponse(to_xml(Div(Card(H3(f'🔒 {step.show}'), markdown_widget), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)))
            response.headers['HX-Trigger'] = json.dumps({'initializeMarked': {'targetId': widget_id}})
            return response
        elif markdown_content and state.get('_revert_target') != step_id:
            markdown_widget = self.create_marked_widget(markdown_content, widget_id)
            from fasthtml.common import to_xml
            from starlette.responses import HTMLResponse
            response = HTMLResponse(to_xml(Div(pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: Markdown Documentation', widget=markdown_widget, steps=self.steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)))
            response.headers['HX-Trigger'] = json.dumps({'initializeMarked': {'targetId': widget_id}})
            return response
        else:
            if 'finalized' in finalize_data:
                await pip.clear_steps_from(pipeline_id, 'finalize', self.steps)
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            return Div(Card(H3(f'{step.show}'), P('Edit the Markdown documentation for the Parameter Buster workflow:'), Form(Textarea(markdown_content, name='markdown_content', rows='15', cls='font-code w-full'), Div(Button('Update Documentation ▸', type='submit', cls='primary'), style='margin-top: 10px; text-align: right;'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')), Div(id=next_step_id), id=step_id)

    async def step_07_submit(self, request):
        """Process the markdown content submission for Step 7."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_07'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        form = await request.form()
        markdown_content = form.get('markdown_content', '')
        existing_data = {}
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        try:
            if step_data.get(step.done):
                existing_data = json.loads(step_data.get(step.done, '{}'))
        except json.JSONDecodeError:
            pass
        parameters_info = existing_data.get('parameters_info', {})
        if not parameters_info:
            step_06_data = pip.get_step_data(pipeline_id, 'step_06', {})
            try:
                if step_06_data.get('parameter_optimization'):
                    param_data = json.loads(step_06_data.get('parameter_optimization'))
                    parameters_info = {'selected_params': param_data.get('selected_params', []), 'gsc_threshold': param_data.get('gsc_threshold', '0'), 'min_frequency': param_data.get('min_frequency', '100000')}
            except (json.JSONDecodeError, TypeError):
                parameters_info = {'selected_params': [], 'gsc_threshold': '0', 'min_frequency': '100000'}
        markdown_data = {'markdown': markdown_content, 'parameters_info': parameters_info}
        data_str = json.dumps(markdown_data)
        await self.update_state_with_html(pipeline_id, step_id, markdown_data, self.steps)
        await self.message_queue.add(pip, f'{step.show}: Markdown content updated', verbatim=True)
        widget_id = f"markdown-widget-{pipeline_id.replace('-', '_')}-{step_id}"
        markdown_widget = self.create_marked_widget(markdown_content, widget_id)
        from fasthtml.common import to_xml
        from starlette.responses import HTMLResponse
        response = HTMLResponse(to_xml(Div(pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: Markdown Documentation', widget=markdown_widget, steps=self.steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)))
        response.headers['HX-Trigger'] = json.dumps({'initializeMarked': {'targetId': widget_id}})
        return response

    def create_marked_widget(self, markdown_content, widget_id):
        """Create a Marked.js markdown rendering widget with special tag handling."""
        processed_content = markdown_content
        processed_content = processed_content.replace('[[DETAILS_START]]', '<details>')
        processed_content = processed_content.replace('[[DETAILS_END]]', '</details>')
        processed_content = processed_content.replace('[[SUMMARY_START]]', '<summary>')
        processed_content = processed_content.replace('[[SUMMARY_END]]', '</summary>')
        textarea_id = f'{widget_id}_content'
        return Div(Textarea(processed_content, id=textarea_id, cls='hidden'), Div(id=f'{widget_id}_output', cls='markdown-body', style='padding: 15px; background-color: var(--pico-card-background-color); border-radius: var(--pico-border-radius);'), Script(f\"\"\"
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
            \"\"\"), id=widget_id)

    async def update_state_with_html(self, pipeline_id, step_id, data, steps, clear_previous=True):
        """Helper method to update state while avoiding HTML logging issues"""
        pip = self.pipulate
        state = pip.read_state(pipeline_id)
        if isinstance(data, dict):
            data_str = json.dumps(data)
        else:
            data_str = data
        if step_id not in state:
            state[step_id] = {}
        state[step_id][steps[self.steps_indices[step_id]].done] = data_str
        if clear_previous:
            await pip.clear_steps_from(pipeline_id, step_id, steps)
        if '_revert_target' in state:
            del state['_revert_target']
        pip.write_state(pipeline_id, state)

# --- Simulation Execution ---
if __name__ == "__main__":
    # Define all functions that would be in the actual script's global scope
    # These are now direct copies of the functions in helpers/update_section.py

    issues_found_sim = []
    class ArgsSim:
        target = str(PROJECT_ROOT / "plugins/dummy_target_workflow.py") 
        source = str(PROJECT_ROOT / "plugins/535_botify_trifecta.py")
        section = "step_01_botify_project_url" # Source section name (used to extract original_step_id)
        target_section_name_to_update = "step_01_dummy_section" # Full name of section in target to find
        new_base_id_for_renaming = "step_03" # New base ID for content and new section marker name
        force = True 
    
    args_for_simulation = ArgsSim()
    
    source_content_for_sim = file_contents_from_read_files_str[0]
    target_content_original_for_sim = file_contents_from_read_files_str[1]
    
    print("--- STARTING SIMULATION ---")
    
    modified_target_content = run_script_main_logic_sim( # Renamed from main() for clarity
        args_for_simulation, 
        source_content_for_sim, 
        target_content_original_for_sim, 
        issues_found_sim
    )
    
    print("\n--- SIMULATED MODIFIED TARGET CONTENT (FINAL) ---")
    print(modified_target_content)
    print("--- END OF SIMULATED MODIFIED TARGET CONTENT (FINAL) ---")

    print_issues_and_exit( # Renamed from print_issues_and_exit_sim
        issues_found_sim, 
        Path(args_for_simulation.target), 
        modified_target_content != target_content_original_for_sim, 
        is_simulation=True
    )
    
    print("--- SIMULATION COMPLETE ---")

PYTHON_EOF

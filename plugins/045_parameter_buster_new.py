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
from typing import Optional

import httpx
import pandas as pd
from fasthtml.common import *
from loguru import logger

ROLES = ['Workshop']
TOKEN_FILE = 'botify_token.txt'

Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class BotifyCsvDownloaderWorkflow:
    """
    Botify Trifecta Workflow - Multi-Export Data Collection

    A comprehensive workflow that downloads three types of Botify data (crawl analysis, web logs, 
    and Search Console) and generates Jupyter-friendly Python code for API debugging. This workflow 
    demonstrates:

    - Multi-step form collection with chain reaction progression
    - Data fetching from external APIs with proper retry and error handling
    - File caching and management for large datasets
    - Background processing with progress indicators

    CRITICAL INSIGHT: Botify API Evolution Complexity
    ================================================
    
    This workflow handles a PAINFUL reality: Botify's API has evolved from BQLv1 to BQLv2, but 
    BOTH versions coexist and are required for different data types:
    
    - Web Logs: Uses BQLv1 with special endpoint (app.botify.com/api/v1/logs/...)
    - Crawl/GSC: Uses BQLv2 with standard endpoint (api.botify.com/v1/projects/.../query)
    
    The workflow generates Python code for BOTH patterns to enable Jupyter debugging, which is
    essential because the /jobs endpoint is for CSV exports while /query is for quick debugging.
    
    PAINFUL LESSONS LEARNED:
    1. Web logs API uses different base URL (app.botify.com vs api.botify.com)
    2. BQLv1 puts dates at payload level, BQLv2 puts them in periods array
    3. Same job_type can have different payload structures (legacy vs modern)
    4. Missing dates = broken URLs = 404 errors
    5. PrismJS syntax highlighting requires explicit language classes and manual triggers

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
    - Python code generation optimized for Jupyter Notebook debugging workflow
    - Dual BQL version support (v1 for web logs, v2 for crawl/GSC) with proper conversion
    """
    APP_NAME = 'trifecta'
    DISPLAY_NAME = 'Botify Trifecta'
    ENDPOINT_MESSAGE = 'Download one CSV of each kind: LogAnalyzer (Web Logs), SiteCrawler (Crawl Analysis), RealKeywords (Search Console) — the Trifecta!'
    TRAINING_PROMPT = 'This workflow provides an example of how to download one CSV of each kind: LogAnalyzer (Web Logs), SiteCrawler (Crawl Analysis), RealKeywords (Search Console) from the Botify API. The queries are different for each type. Downloading one of each type is often the precursor to a comprehensive Botify deliverable, incorporating the full funnel philosophy of the Botify way.'

    # Query Templates - Extracted from build_exports for reusability
    # 
    # NOTE: Web Logs are intentionally NOT templated (KISS principle)
    # ================================================================
    # Web logs queries are simple, consistent, and rarely change:
    # - Always same fields: ['url', 'crawls.google.count'] 
    # - Always same filter: crawls.google.count > 0
    # - Uses legacy BQLv1 structure (different from crawl/GSC)
    # - Different API endpoint (app.botify.com vs api.botify.com)
    # 
    # Adding web logs to templates would require:
    # - Separate BQLv1 template system
    # - Handling different endpoint/payload structures  
    # - More complexity for minimal benefit
    # 
    # Current approach: hardcode the simple query inline where used.
    # This is a perfect example of knowing when NOT to abstract.
    QUERY_TEMPLATES = {
        'Crawl Basic': {
            'name': 'Basic Crawl Data',
            'description': 'URL, HTTP status, and page title',
            'export_type': 'crawl_attributes',
            'user_message': 'This will download basic crawl data including URLs, HTTP status codes, and page titles.',
            'button_label_suffix': 'Basic Attributes',
            'query': {
                'dimensions': ['{collection}.url', '{collection}.http_code', '{collection}.metadata.title.content'],
                'filters': {'field': '{collection}.http_code', 'predicate': 'eq', 'value': 200}
            }
        },
        'Not Compliant': {
            'name': 'Non-Compliant Pages',
            'description': 'URLs with compliance issues and their reasons',
            'export_type': 'crawl_attributes',
            'user_message': 'This will download a list of non-compliant URLs with their compliance reasons.',
            'button_label_suffix': 'Non-Compliant Attributes',
            'query': {
                'dimensions': ['{collection}.url', '{collection}.compliant.main_reason', '{collection}.compliant.detailed_reason'],
                'metrics': [{'function': 'count', 'args': ['{collection}.url']}],
                'filters': {'field': '{collection}.compliant.is_compliant', 'predicate': 'eq', 'value': False}
            },
            'qualifier_config': {
                'enabled': True,
                'qualifier_bql_template': {
                    "dimensions": [],
                    "metrics": [{"function": "count", "args": ["{collection}.url"]}],
                    "filters": {"field": "{collection}.compliant.is_compliant", "predicate": "eq", "value": False}
                },
                'parameter_placeholder_in_main_query': None,  # No substitution needed
                'iterative_parameter_name': 'non_compliant_url_count',
                'target_metric_path': ["results", 0, "metrics", 0],
                'max_value_threshold': 5000000,  # Allow larger attribute exports
                'iteration_range': (1, 1, 1),  # Non-iterative, just one check
                'user_message_running': 'Estimating size of Non-Compliant Pages export...',
                'user_message_found': 'Non-Compliant Pages export estimated at {metric_value:,} URLs. Proceeding.',
                'user_message_threshold_exceeded': 'Warning: Non-Compliant Pages export is very large ({metric_value:,} URLs). Proceeding with caution.'
            }
        },
        'Link Graph Edges': {
            'name': 'Link Graph Edges',
            'description': 'Exports internal link graph (source URL -> target URL). Automatically finds optimal depth for ~1M edges.',
            'export_type': 'link_graph_edges',
            'user_message': 'This will download the site\'s internal link graph (source-target pairs). An optimal depth will be found first.',
            'button_label_suffix': 'Link Graph',
            'query': {
                'dimensions': ['{collection}.url', '{collection}.outlinks_internal.graph.url'],
                'metrics': [],
                'filters': {'field': '{collection}.depth', 'predicate': 'lte', 'value': '{OPTIMAL_DEPTH}'}
            },
            'qualifier_config': {
                'enabled': True,
                'qualifier_bql_template': {
                    "dimensions": [],
                    "metrics": [{"function": "sum", "args": ["{collection}.outlinks_internal.nb.total"]}],
                    "filters": {"field": "{collection}.depth", "predicate": "lte", "value": "{ITERATION_VALUE}"}
                },
                'parameter_placeholder_in_main_query': '{OPTIMAL_DEPTH}',
                'iterative_parameter_name': 'depth',
                'target_metric_path': ["results", 0, "metrics", 0],
                'max_value_threshold': 1000000,
                'iteration_range': (1, 10, 1),  # (start, end, step_increment)
                'user_message_running': '🔍 Finding optimal depth for Link Graph Edges...',
                'user_message_found': '🎯 Optimal depth for Link Graph: {param_value} (for {metric_value:,} edges).',
                'user_message_threshold_exceeded': 'Edge count exceeds threshold even at shallowest depth. Proceeding with depth 1.'
            }
        },
        'GSC Performance': {
            'name': 'GSC Performance',
            'description': 'Impressions, clicks, CTR, and position',
            'export_type': 'gsc_data',
            'user_message': 'This will download Search Console performance data including impressions, clicks, CTR, and average position.',
            'button_label_suffix': 'GSC Performance',
            'query': {
                'dimensions': ['url'],
                'metrics': [
                    {'field': 'search_console.period_0.count_impressions', 'name': 'Impressions'},
                    {'field': 'search_console.period_0.count_clicks', 'name': 'Clicks'},
                    {'field': 'search_console.period_0.ctr', 'name': 'CTR'},
                    {'field': 'search_console.period_0.avg_position', 'name': 'Avg. Position'}
                ],
                'sort': [{'type': 'metrics', 'index': 0, 'order': 'desc'}]
            }
        }
    }

    # Template Configuration - Controls which templates are actually used
    # ===================================================================
    # Change these values to switch between different query templates
    # without modifying the workflow logic.
    TEMPLATE_CONFIG = {
        'crawl': 'Not Compliant',   # Options: 'Crawl Basic', 'Not Compliant', 'Link Graph Edges'
        'gsc': 'GSC Performance'       # Options: 'GSC Performance'
    }

    # UI Constants - Centralized button labels and styles
    # ===================================================
    # Standardized labels and styles for consistent UI across the workflow
    UI_CONSTANTS = {
        'BUTTON_LABELS': {
            'HIDE_SHOW_CODE': '🐍 Hide/Show Code',
            'VIEW_FOLDER': '📂 View Folder',
            'DOWNLOAD_CSV': '⬇️ Download CSV'
        },
        'BUTTON_STYLES': {
            'STANDARD': 'secondary outline',
            'FLEX_CONTAINER': 'display: flex; gap: 0.5em; flex-wrap: wrap; align-items: center;'
        }
    }

    # Toggle Method Configuration - Maps step IDs to their specific data extraction logic
    # ==================================================================================
    TOGGLE_CONFIG = {
        'step_02': {
            'data_key': 'analysis_result',
            'status_field': 'download_complete',
            'success_text': 'HAS crawl analysis',
            'failure_text': 'does NOT have crawl analysis',
            'error_prefix': 'FAILED to download crawl analysis'
        },
        'step_03': {
            'data_key': 'check_result', 
            'status_field': 'has_logs',
            'success_text': 'HAS web logs',
            'failure_text': 'does NOT have web logs',
            'error_prefix': 'FAILED to download web logs',
            'status_prefix': 'Project '
        },
        'step_04': {
            'data_key': 'check_result',
            'status_field': 'has_search_console', 
            'success_text': 'HAS Search Console data',
            'failure_text': 'does NOT have Search Console data',
            'error_prefix': 'FAILED to download Search Console data',
            'status_prefix': 'Project '
        },
        'step_05': {
            'simple_content': 'Placeholder step completed'
        }
    }

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
        # Build step names dynamically based on template configuration
        crawl_template = self.get_configured_template('crawl')
        gsc_template = self.get_configured_template('gsc')
        
        steps = [
            Step(id='step_01', done='botify_project', show='Botify Project URL', refill=True), 
            Step(id='step_02', done='analysis_selection', show=f'Download Crawl Analysis: {crawl_template}', refill=False), 
            Step(id='step_03', done='weblogs_check', show='Download Web Logs', refill=False), 
            Step(id='step_04', done='search_console_check', show=f'Download Search Console: {gsc_template}', refill=False), 
            Step(id='step_05', done='placeholder', show='Placeholder Step', refill=True)
        ]
        routes = [(f'/{app_name}', self.landing), (f'/{app_name}/init', self.init, ['POST']), (f'/{app_name}/revert', self.handle_revert, ['POST']), (f'/{app_name}/finalize', self.finalize, ['GET', 'POST']), (f'/{app_name}/unfinalize', self.unfinalize, ['POST'])]
        self.steps = steps
        for step in steps:
            step_id = step.id
            routes.append((f'/{app_name}/{step_id}', getattr(self, step_id)))
            routes.append((f'/{app_name}/{step_id}_submit', getattr(self, f'{step_id}_submit'), ['POST']))
        routes.append((f'/{app_name}/step_04_complete', self.step_04_complete, ['POST']))
        routes.append((f'/{app_name}/step_02_process', self.step_02_process, ['POST']))
        routes.append((f'/{app_name}/step_03_process', self.step_03_process, ['POST']))
        routes.append((f'/{app_name}/step_05_process', self.step_05_process, ['POST']))
        routes.append((f'/{app_name}/toggle', self.common_toggle, ['GET']))
        routes.append((f'/{app_name}/check_cache_status', self.check_cache_status, ['GET']))
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ['GET']
            app.route(path, methods=method_list)(handler)
        self.step_messages = {'finalize': {'ready': 'All steps complete. Ready to finalize workflow.', 'complete': f'Workflow finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes.'}, 'step_02': {'input': f"❔{pip.fmt('step_02')}: Please select a crawl analysis for this project.", 'complete': 'Crawl analysis download complete. Continue to next step.'}}
        for step in steps:
            if step.id not in self.step_messages:
                self.step_messages[step.id] = {'input': f'❔{pip.fmt(step.id)}: Please complete {step.show}.', 'complete': f'✳️ {step.show} complete. Continue to next step.'}
        self.step_messages['step_04'] = {'input': f"❔{pip.fmt('step_04')}: Please check if the project has Search Console data.", 'complete': 'Search Console check complete. Continue to next step.'}
        self.step_messages['step_03'] = {'input': f"❔{pip.fmt('step_03')}: Please check if the project has web logs available.", 'complete': 'Web logs check complete. Continue to next step.'}
        self.step_messages['step_05'] = {'input': f"❔{pip.fmt('step_05')}: This is a placeholder step.", 'complete': 'Placeholder step complete. Ready to finalize.'}
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

    def get_available_templates_for_data_type(self, data_type):
        """Get available query templates for a specific data type."""
        if data_type == 'crawl':
            return ['Crawl Basic', 'Not Compliant']
        elif data_type == 'gsc':
            return ['GSC Performance']
        else:
            return []

    def get_configured_template(self, data_type):
        """Get the configured template for a specific data type."""
        return self.TEMPLATE_CONFIG.get(data_type)

    def apply_template(self, template_key, collection=None):
        """Apply a query template with collection substitution."""
        if template_key not in self.QUERY_TEMPLATES:
            raise ValueError(f"Unknown template: {template_key}")
        
        template = self.QUERY_TEMPLATES[template_key].copy()
        query = template['query'].copy()
        
        if collection and '{collection}' in str(query):
            # Simple string replacement for collection placeholders
            query_str = json.dumps(query)
            query_str = query_str.replace('{collection}', collection)
            query = json.loads(query_str)
        
        return query

    def list_available_templates(self):
        """List all available query templates with descriptions."""
        return {
            key: {
                'name': template['name'],
                'description': template['description']
            }
            for key, template in self.QUERY_TEMPLATES.items()
        }

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
        await self.message_queue.add(pip, f'↩️ Reverted to {step_id}. All subsequent data has been cleared.', verbatim=True)
        return pip.rebuild(app_name, steps)

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
        await self.message_queue.add(pip, f"✳️ {step.show} complete: {project_data['project_name']}", verbatim=True)
        project_name = project_data.get('project_name', '')
        project_url = project_data.get('url', '')
        project_info = Div(H4(f'Project: {project_name}'), Small(project_url, style='word-break: break-all;'), style='padding: 10px; background: #f8f9fa; border-radius: 5px;')
        return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: {project_url}', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)

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
            # Get step data to create action buttons
            analysis_result_str = step_data.get(step.done, '')
            analysis_result = json.loads(analysis_result_str) if analysis_result_str else {}
            action_buttons = self._create_action_buttons(analysis_result, step_id)
            
            widget = Div(
                Div(
                    Button(self.UI_CONSTANTS['BUTTON_LABELS']['HIDE_SHOW_CODE'], 
                        cls=self.UI_CONSTANTS['BUTTON_STYLES']['STANDARD'],
                        hx_get=f'/{app_name}/toggle?step_id={step_id}',
                        hx_target=f'#{step_id}_widget',
                        hx_swap='innerHTML'
                    ),
                    *action_buttons,
                    style=self.UI_CONSTANTS['BUTTON_STYLES']['FLEX_CONTAINER']
                ),
                Div(
                    Pre(f'Selected analysis: {selected_slug}', cls='code-block-container', style='display: none;'),
                    id=f'{step_id}_widget'
                )
            )
            return Div(pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: {selected_slug}', widget=widget, steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
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
            
            # Get active template details for dynamic UI
            active_crawl_template_key = self.get_configured_template('crawl')
            active_template_details = self.QUERY_TEMPLATES.get(active_crawl_template_key, {})
            template_name = active_template_details.get('name', active_crawl_template_key)
            user_message = active_template_details.get('user_message', 'This will download crawl data.')
            button_suffix = active_template_details.get('button_label_suffix', 'Data')
            
            # Check for downloaded files using the active template's export type
            downloaded_files_info = {}
            for slug in slugs:
                # Check all possible file types for this analysis
                files_found = []
                
                # Check crawl data (using active template's export type)
                crawl_filepath = await self.get_deterministic_filepath(username, project_name, slug, active_template_details.get('export_type', 'crawl_attributes'))
                crawl_exists, crawl_info = await self.check_file_exists(crawl_filepath)
                if crawl_exists:
                    filename = os.path.basename(crawl_filepath)
                    files_found.append(filename)
                
                # Check weblog data
                weblog_filepath = await self.get_deterministic_filepath(username, project_name, slug, 'weblog')
                weblog_exists, _ = await self.check_file_exists(weblog_filepath)
                if weblog_exists:
                    files_found.append('weblog.csv')
                
                # Check GSC data
                gsc_filepath = await self.get_deterministic_filepath(username, project_name, slug, 'gsc')
                gsc_exists, _ = await self.check_file_exists(gsc_filepath)
                if gsc_exists:
                    files_found.append('gsc.csv')
                
                if files_found:
                    downloaded_files_info[slug] = files_found
            await self.message_queue.add(pip, self.step_messages.get(step_id, {}).get('input', f'Select an analysis for {project_name}'), verbatim=True)
            
            # Build dropdown options with file summaries
            dropdown_options = []
            for slug in slugs:
                if slug in downloaded_files_info:
                    files_summary = ', '.join(downloaded_files_info[slug])
                    option_text = f'{slug} ({files_summary})'
                else:
                    option_text = slug
                dropdown_options.append(Option(option_text, value=slug, selected=slug == selected_value))
            
            # Check cache status for the initially selected analysis to set correct initial button text
            selected_analysis = selected_value if selected_value else (slugs[0] if slugs else '')
            active_template_details = self.QUERY_TEMPLATES.get(active_crawl_template_key, {})
            export_type = active_template_details.get('export_type', 'crawl_attributes')
            
            is_cached = False
            if selected_analysis:
                is_cached = await self.check_cached_file_for_button_text(username, project_name, selected_analysis, export_type)
            
            button_text = f'Use Cached {button_suffix} ▸' if is_cached else f'Download {button_suffix} ▸'
            
            return Div(Card(H3(f'{step.show}'), P(f"Select an analysis for project '{project_name}'"), P(f'Organization: {username}', cls='text-secondary'), P(user_message, cls='text-muted', style='font-style: italic; margin-top: 10px;'), Form(Select(*dropdown_options, name='analysis_slug', required=True, autofocus=True, hx_get=f'/{app_name}/check_cache_status', hx_trigger='change', hx_target='#step-02-button', hx_include=f'[name="username"],[name="project_name"]'), Input(type='hidden', name='username', value=username), Input(type='hidden', name='project_name', value=project_name), Div(Button(button_text, type='submit', cls='mt-10px primary'), id='step-02-button'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')), Div(id=next_step_id), id=step_id)
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
        await self.message_queue.add(pip, f'📊 Selected analysis: {analysis_slug}. Starting crawl data download...', verbatim=True)
        
        # Get active template details and check for qualifier config
        active_crawl_template_key = self.get_configured_template('crawl')
        active_template_details = self.QUERY_TEMPLATES.get(active_crawl_template_key, {})
        qualifier_config = active_template_details.get('qualifier_config', {'enabled': False})
        
        analysis_result = {
            'analysis_slug': analysis_slug, 
            'project': project_name, 
            'username': username, 
            'timestamp': datetime.now().isoformat(), 
            'download_started': True,
            'export_type': active_template_details.get('export_type', 'crawl_attributes')
        }
        
        # Execute qualifier logic if enabled
        if qualifier_config.get('enabled'):
            try:
                api_token = self.read_api_token()
                if not api_token:
                    return P('Error: Botify API token not found. Please connect with Botify first.', style=pip.get_style('error'))
                
                await self.message_queue.add(pip, qualifier_config['user_message_running'], verbatim=True)
                qualifier_outcome = await self._execute_qualifier_logic(username, project_name, analysis_slug, api_token, qualifier_config)
                
                # Store qualifier results
                analysis_result['dynamic_parameter_value'] = qualifier_outcome['parameter_value']
                analysis_result['metric_at_dynamic_parameter'] = qualifier_outcome['metric_at_parameter']
                analysis_result['parameter_placeholder_in_main_query'] = qualifier_config['parameter_placeholder_in_main_query']
                
                # Send completion message
                await self.message_queue.add(pip, qualifier_config['user_message_found'].format(
                    param_value=qualifier_outcome['parameter_value'],
                    metric_value=qualifier_outcome['metric_at_parameter']
                ), verbatim=True)
                
            except Exception as e:
                await self.message_queue.add(pip, f'Error during qualifier logic: {str(e)}', verbatim=True)
                # Continue with default values
                analysis_result['dynamic_parameter_value'] = None
                analysis_result['metric_at_dynamic_parameter'] = 0
                analysis_result['parameter_placeholder_in_main_query'] = None
        
        analysis_result_str = json.dumps(analysis_result)
        await pip.set_step_data(pipeline_id, step_id, analysis_result_str, steps)
        return Card(
            H3(f'{step.show}'),
            P(f"Downloading data for analysis '{analysis_slug}'..."),
            Progress(style='margin-top: 10px;'),
            Script(f"""
                setTimeout(function() {{
                    htmx.ajax('POST', '/{app_name}/step_02_process', {{
                        target: '#{step_id}',
                        values: {{
                            'analysis_slug': '{analysis_slug}',
                            'username': '{username}',
                            'project_name': '{project_name}'
                        }}
                    }});
                }}, 500);
            """),
            id=step_id
        )

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
            action_buttons = self._create_action_buttons(check_result, step_id)
            
            widget = Div(
                Div(
                    Button(self.UI_CONSTANTS['BUTTON_LABELS']['HIDE_SHOW_CODE'], 
                        cls=self.UI_CONSTANTS['BUTTON_STYLES']['STANDARD'],
                        hx_get=f'/{app_name}/toggle?step_id={step_id}',
                        hx_target=f'#{step_id}_widget',
                        hx_swap='innerHTML'
                    ),
                    *action_buttons,
                    style=self.UI_CONSTANTS['BUTTON_STYLES']['FLEX_CONTAINER']
                ),
                Div(
                    Pre(f'Status: Project {status_text}', cls='code-block-container', style=f'color: {status_color}; display: none;'),
                    id=f'{step_id}_widget'
                )
            )
            return Div(pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: Project {status_text}', widget=widget, steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif check_result and state.get('_revert_target') != step_id:
            has_logs = check_result.get('has_logs', False)
            status_text = 'HAS web logs' if has_logs else 'does NOT have web logs'
            status_color = 'green' if has_logs else 'red'
            action_buttons = self._create_action_buttons(check_result, step_id)
            
            widget = Div(
                Div(
                    Button(self.UI_CONSTANTS['BUTTON_LABELS']['HIDE_SHOW_CODE'], 
                        cls=self.UI_CONSTANTS['BUTTON_STYLES']['STANDARD'],
                        hx_get=f'/{app_name}/toggle?step_id={step_id}',
                        hx_target=f'#{step_id}_widget',
                        hx_swap='innerHTML'
                    ),
                    *action_buttons,
                    style=self.UI_CONSTANTS['BUTTON_STYLES']['FLEX_CONTAINER']
                ),
                Div(
                    Pre(f'Status: Project {status_text}', cls='code-block-container', style=f'color: {status_color}; display: none;'),
                    id=f'{step_id}_widget'
                )
            )
            return Div(pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: Project {status_text}', widget=widget, steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        else:
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            
            # Check if web logs are cached for the CURRENT analysis
            analysis_step_id = 'step_02'
            analysis_step_data = pip.get_step_data(pipeline_id, analysis_step_id, {})
            analysis_data_str = analysis_step_data.get('analysis_selection', '')
            
            is_cached = False
            if analysis_data_str:
                try:
                    analysis_data = json.loads(analysis_data_str)
                    analysis_slug = analysis_data.get('analysis_slug', '')
                    if analysis_slug:
                        is_cached = await self.check_cached_file_for_button_text(username, project_name, analysis_slug, 'weblog')
                except (json.JSONDecodeError, Exception):
                    is_cached = False
            
            # Set button text based on cache status
            button_text = 'Use Cached Web Logs ▸' if is_cached else 'Download Web Logs ▸'
            
            return Div(Card(H3(f'{step.show}'), P(f"Download Web Logs for '{project_name}'"), P(f'Organization: {username}', cls='text-secondary'), Form(Button(button_text, type='submit', cls='primary'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')), Div(id=next_step_id), id=step_id)

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
        await self.message_queue.add(pip, f"📥 Downloading Web Logs for '{project_name}'...", verbatim=True)
        return Card(
            H3(f'{step.show}'),
            P(f"Downloading Web Logs for '{project_name}'..."),
            Progress(style='margin-top: 10px;'),
            Script(f"""
                setTimeout(function() {{
                    htmx.ajax('POST', '/{app_name}/step_03_process', {{
                        target: '#{step_id}',
                        values: {{
                            'analysis_slug': '{analysis_slug}',
                            'username': '{username}',
                            'project_name': '{project_name}'
                        }}
                    }});
                }}, 500);
            """),
            id=step_id
        )

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
            action_buttons = self._create_action_buttons(check_result, step_id)
            
            widget = Div(
                Div(
                    Button(self.UI_CONSTANTS['BUTTON_LABELS']['HIDE_SHOW_CODE'], 
                        cls=self.UI_CONSTANTS['BUTTON_STYLES']['STANDARD'],
                        hx_get=f'/{app_name}/toggle?step_id={step_id}',
                        hx_target=f'#{step_id}_widget',
                        hx_swap='innerHTML'
                    ),
                    *action_buttons,
                    style=self.UI_CONSTANTS['BUTTON_STYLES']['FLEX_CONTAINER']
                ),
                Div(
                    Pre(f'Status: Project {status_text}', cls='code-block-container', style=f'color: {status_color}; display: none;'),
                    id=f'{step_id}_widget'
                )
            )
            return Div(pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: Project {status_text}', widget=widget, steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif check_result and state.get('_revert_target') != step_id:
            has_search_console = check_result.get('has_search_console', False)
            status_text = 'HAS Search Console data' if has_search_console else 'does NOT have Search Console data'
            status_color = 'green' if has_search_console else 'red'
            action_buttons = self._create_action_buttons(check_result, step_id)
            
            widget = Div(
                Div(
                    Button(self.UI_CONSTANTS['BUTTON_LABELS']['HIDE_SHOW_CODE'], 
                        cls=self.UI_CONSTANTS['BUTTON_STYLES']['STANDARD'],
                        hx_get=f'/{app_name}/toggle?step_id={step_id}',
                        hx_target=f'#{step_id}_widget',
                        hx_swap='innerHTML'
                    ),
                    *action_buttons,
                    style=self.UI_CONSTANTS['BUTTON_STYLES']['FLEX_CONTAINER']
                ),
                Div(
                    Pre(f'Status: Project {status_text}', cls='code-block-container', style=f'color: {status_color}; display: none;'),
                    id=f'{step_id}_widget'
                )
            )
            return Div(pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: Project {status_text}', widget=widget, steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        else:
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            gsc_template = self.get_configured_template('gsc')
            
            # Check if GSC data is cached for the CURRENT analysis
            analysis_step_id = 'step_02'
            analysis_step_data = pip.get_step_data(pipeline_id, analysis_step_id, {})
            analysis_data_str = analysis_step_data.get('analysis_selection', '')
            
            is_cached = False
            if analysis_data_str:
                try:
                    analysis_data = json.loads(analysis_data_str)
                    analysis_slug = analysis_data.get('analysis_slug', '')
                    if analysis_slug:
                        is_cached = await self.check_cached_file_for_button_text(username, project_name, analysis_slug, 'gsc')
                except (json.JSONDecodeError, Exception):
                    is_cached = False
            
            button_text = f'Use Cached Search Console: {gsc_template} ▸' if is_cached else f'Download Search Console: {gsc_template} ▸'
            
            return Div(Card(H3(f'{step.show}'), P(f"Download Search Console data for '{project_name}'"), P(f'Organization: {username}', cls='text-secondary'), Form(Button(button_text, type='submit', cls='primary'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')), Div(id=next_step_id), id=step_id)

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
        return Card(
            H3(f'{step.show}'),
            P(f"Downloading Search Console data for '{project_name}'..."),
            Progress(style='margin-top: 10px;'),
            Script(f"""
                setTimeout(function() {{
                    htmx.ajax('POST', '/{app_name}/{step_id}_complete', {{
                        target: '#{step_id}',
                        values: {{ 'delay_complete': 'true' }}
                    }});
                }}, 1500);
            """),
            id=step_id
        )

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
            check_result = {'has_search_console': has_search_console, 'project': project_name, 'username': username, 'analysis_slug': analysis_slug, 'timestamp': datetime.now().isoformat()}
            if has_search_console:
                await self.message_queue.add(pip, f'✅ Project has Search Console data, downloading...', verbatim=True)
                await self.process_search_console_data(pip, pipeline_id, step_id, username, project_name, analysis_slug, check_result)
            else:
                await self.message_queue.add(pip, f'Project does not have Search Console data (skipping download)', verbatim=True)
                # Add empty python_command for consistency with other steps
                check_result['python_command'] = ''
                check_result_str = json.dumps(check_result)
                await pip.set_step_data(pipeline_id, step_id, check_result_str, steps)
            status_text = 'HAS' if has_search_console else 'does NOT have'
            completed_message = 'Data downloaded successfully' if has_search_console else 'No Search Console data available'
            action_buttons = self._create_action_buttons(check_result, step_id)
            
            widget = Div(
                Div(
                    Button(self.UI_CONSTANTS['BUTTON_LABELS']['HIDE_SHOW_CODE'], 
                        cls=self.UI_CONSTANTS['BUTTON_STYLES']['STANDARD'],
                        hx_get=f'/{app_name}/toggle?step_id={step_id}',
                        hx_target=f'#{step_id}_widget',
                        hx_swap='innerHTML'
                    ),
                    *action_buttons,
                    style=self.UI_CONSTANTS['BUTTON_STYLES']['FLEX_CONTAINER']
                ),
                Div(
                    Pre(f'Status: Project {status_text} Search Console data', cls='code-block-container', style=f'color: {"green" if has_search_console else "red"}; display: none;'),
                    id=f'{step_id}_widget'
                )
            )
            return Div(pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: {completed_message}', widget=widget, steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        except Exception as e:
            logging.exception(f'Error in step_04_complete: {e}')
            return Div(P(f'Error: {str(e)}', style=pip.get_style('error')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)

    async def step_05(self, request):
        """Handles GET request for the placeholder step."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_05'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        # Since steps 6 and 7 are not implemented, next step should be 'finalize'
        next_step_id = 'finalize' 
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        placeholder_result = pip.get_step_data(pipeline_id, step_id, {})

        if 'finalized' in finalize_data and placeholder_result:
            return Div(Card(H3(f'🔒 {step.show}'), Div(P('Placeholder step completed'), cls='custom-card-padding-bg')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif placeholder_result and state.get('_revert_target') != step_id:
            return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: Completed', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        else:
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            return Div(Card(H3(f'{step.show}'), P('This is a placeholder step.'), Form(Button('Complete Placeholder Step ▸', type='submit', cls='primary'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')), Div(id=next_step_id), id=step_id)

    async def step_05_submit(self, request):
        """Process the submission for the placeholder step."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_05'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        
        placeholder_result = {'completed': True, 'timestamp': datetime.now().isoformat()}
        placeholder_result_str = json.dumps(placeholder_result)
        await pip.set_step_data(pipeline_id, step_id, placeholder_result_str, steps)
        await self.message_queue.add(pip, f"{step.show} complete", verbatim=True)
        widget = Div(
            Button(self.UI_CONSTANTS['BUTTON_LABELS']['HIDE_SHOW_CODE'], 
                cls=self.UI_CONSTANTS['BUTTON_STYLES']['STANDARD'],
                hx_get=f'/{app_name}/toggle?step_id={step_id}',
                hx_target=f'#{step_id}_widget',
                hx_swap='innerHTML'
            ),
            Div(
                Pre('Placeholder step completed', cls='code-block-container', style='display: none;'),
                id=f'{step_id}_widget'
            )
        )
        return Div(pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: Completed', widget=widget, steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)

    async def step_05_process(self, request):
        """Process parameter analysis using raw parameter counting and caching."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_05'
        step_index = self.steps_indices[step_id]
        current_step_obj = steps[step_index] 
        # Since steps 6 and 7 are not implemented, next step should be 'finalize'
        next_step_id = 'finalize'
        
        form = await request.form()
        pipeline_id = form.get('pipeline_id', db.get('pipeline_id', 'unknown'))
        param_count_display = int(form.get('param_count', '40'))
        
        project_data_str = pip.get_step_data(pipeline_id, 'step_01', {}).get(steps[self.steps_indices['step_01']].done, '{}')
        analysis_data_str = pip.get_step_data(pipeline_id, 'step_02', {}).get(steps[self.steps_indices['step_02']].done, '{}')
        
        try:
            project_info = json.loads(project_data_str)
            analysis_info = json.loads(analysis_data_str)
        except json.JSONDecodeError:
            await self.message_queue.add(pip, "Error: Could not load project or analysis data from prior steps. Please ensure Steps 1 and 2 are complete.", verbatim=True)
            return P('Error: Could not load project or analysis data. Please complete previous steps.', style=pip.get_style('error'))

        username = project_info.get('username')
        project_name = project_info.get('project_name')
        analysis_slug = analysis_info.get('analysis_slug')

        if not all([username, project_name, analysis_slug]):
            await self.message_queue.add(pip, "Error: Missing required project information (username, project name, or analysis slug). Please ensure Steps 1 and 2 are fully complete.", verbatim=True)
            return P('Error: Missing required project information. Please complete previous steps.', style=pip.get_style('error'))

        try:
            await self.message_queue.add(pip, f'⚙️ Counting parameters for {username}/{project_name}/{analysis_slug}...', verbatim=True)
            
            data_dir_path = await self.get_deterministic_filepath(username, project_name, analysis_slug) # This is APP_NAME namespaced
            cache_filename = '_raw_param_counters_cache.pkl' 
            files_to_process = {'not_indexable': 'crawl.csv', 'gsc': 'gsc.csv', 'weblogs': 'weblog.csv'}
            
            output_data = self.load_raw_counters_from_cache(data_dir_path, cache_filename)
            
            if output_data is None:
                await self.message_queue.add(pip, 'Cache miss or invalid. Calculating from source files...', verbatim=True)
                output_data = await self.calculate_and_cache_raw_counters(
                    data_directory_path=data_dir_path,
                    input_files_config=files_to_process, 
                    cache_filename=cache_filename
                )
                if output_data is None: 
                    await self.message_queue.add(pip, "Error: Failed to calculate parameter counts. Source files might be missing or corrupted.", verbatim=True)
                    raise ValueError('Failed to calculate counters from source files and cache is empty/invalid.')
            else:
                 await self.message_queue.add(pip, '📊 Loaded parameter counts from cache.', verbatim=True)

            raw_counters = output_data.get('raw_counters', {})
            file_statuses = output_data.get('metadata', {}).get('file_statuses', {})
            
            parameter_summary = {
                'timestamp': datetime.now().isoformat(), 
                'data_sources': {}, 
                'cache_path': str(Path(data_dir_path) / cache_filename),
                'param_count': param_count_display 
            }
            
            total_unique_params_set = set()
            total_occurrences_val = 0
            for source, counter_data in raw_counters.items():
                counter = Counter(counter_data) if isinstance(counter_data, dict) else (counter_data if isinstance(counter_data, Counter) else Counter())
                unique_params_count = len(counter)
                source_occurrences_val = sum(counter.values())
                total_occurrences_val += source_occurrences_val
                status = file_statuses.get(source, 'Status unknown')
                
                parameter_summary['data_sources'][source] = {
                    'unique_parameters': unique_params_count, 
                    'total_occurrences': source_occurrences_val, 
                    'status': status, 
                    'top_parameters': [{'name': p_name, 'count': p_count} for p_name, p_count in counter.most_common(10)]
                }
                total_unique_params_set.update(counter.keys())
                
            parameter_summary['total_unique_parameters'] = len(total_unique_params_set)
            summary_str = json.dumps(parameter_summary)
            
            await pip.set_step_data(pipeline_id, step_id, {current_step_obj.done: summary_str}, steps, is_json=False)
            
            await self.message_queue.add(pip, f"✅ Parameter analysis complete! Found {len(total_unique_params_set):,} unique parameters with {total_occurrences_val:,} total occurrences.", verbatim=True)
            
            # --- UI Rendering part will be refined in the next step ---
            visualization_widget = self.create_parameter_visualization_placeholder(summary_str)
            current_step_data_for_ui = pip.get_step_data(pipeline_id, step_id, {})
            action_buttons = self._create_action_buttons(current_step_data_for_ui, step_id)
            
            code_toggle_widget = Div(
                Button(self.UI_CONSTANTS['BUTTON_LABELS']['HIDE_SHOW_CODE'], 
                    cls=self.UI_CONSTANTS['BUTTON_STYLES']['STANDARD'],
                    hx_get=f'/{app_name}/toggle?step_id={step_id}', 
                    hx_target=f'#{step_id}_widget',
                    hx_swap='innerHTML'
                ),
                Div(Pre('Parameter counting and visualization logic is complex and executed server-side. The generated chart and table are the primary outputs. Key helper methods: `load_raw_counters_from_cache`, `calculate_and_cache_raw_counters`, `create_parameter_visualization_placeholder`.', cls='code-block-container', style='display: none;'),
                    id=f'{step_id}_widget'
                )
            )
            combined_display_widget = Div(visualization_widget, Div(action_buttons, style=self.UI_CONSTANTS['BUTTON_STYLES']['FLEX_CONTAINER']), code_toggle_widget)

            return Div(pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f"{current_step_obj.show}: {len(total_unique_params_set):,} unique parameters found", widget=combined_display_widget, steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)

        except Exception as e:
            logging.exception(f'Error in step_05_process: {e}')
            await self.message_queue.add(pip, f'❌ Error during parameter analysis: {str(e)}', verbatim=True)
            error_summary = json.dumps({'error': str(e), 'param_count': param_count_display})
            await pip.set_step_data(pipeline_id, step_id, {current_step_obj.done: error_summary}, steps, is_json=False)

            error_display_widget = P(f'Error generating parameter analysis: {str(e)}', style=pip.get_style('error'))
            action_buttons = self._create_action_buttons(pip.get_step_data(pipeline_id, step_id, {}), step_id) 
            
            return Div(pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f"{current_step_obj.show}: Analysis Failed", widget=Div(error_display_widget, Div(action_buttons, style=self.UI_CONSTANTS['BUTTON_STYLES']['FLEX_CONTAINER'])), steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)


[end of plugins/045_parameter_buster_new.py]

import asyncio
import json
import os
from datetime import datetime

from fasthtml.common import *
from loguru import logger
from imports.crud import Step  # 🎯 STANDARDIZED: Import centralized Step definition
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from starlette.responses import HTMLResponse
from webdriver_manager.chrome import ChromeDriverManager

ROLES = ['Workshop']
'\nPipulate Workflow Template\nA minimal starter template for creating step-based Pipulate workflows.\n'


class BlankWorkflow:
    """
    Blank Workflow Template

    A minimal starting point for creating new workflows.
    """
    APP_NAME = 'tab'
    DISPLAY_NAME = 'Tab Opener 🗂️'
    ENDPOINT_MESSAGE = 'Open any URL in your default browser using your existing profile and settings. Perfect for accessing pages that require login.'
    TRAINING_PROMPT = 'This workflow helps users open URLs in their default browser. It uses the widget_container pattern for consistent UI and provides a simple interface for URL input and Google search functionality. This is the non-browser-automation way to open URLs. It does use your default browser so it has all your logins, extensions, etc. It can open URLs with querystrings so is a great way to open search results or SEMRush reports. For more advanced browser automation, see the the Browser Automation plugin. Though we do throw in a simple Selenium URL opener at the end of this workflow just to remind you that this capability exists — and as a bit of flex to entice you to explore.'
    PRESERVE_REFILL = True

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
        steps = [Step(id='step_01', done='url', show='Enter URL', refill=True), Step(id='step_02', done='query', show='Google Search', refill=True), Step(id='step_03', done='selenium_url', show='Selenium URL', refill=True)]
        routes = [(f'/{app_name}', self.landing), (f'/{app_name}/init', self.init, ['POST']), (f'/{app_name}/revert', self.handle_revert, ['POST']), (f'/{app_name}/finalize', self.finalize, ['GET', 'POST']), (f'/{app_name}/unfinalize', self.unfinalize, ['POST']), (f'/{app_name}/reopen_url', self.reopen_url, ['POST'])]
        self.steps = steps
        for step in steps:
            step_id = step.id
            routes.append((f'/{app_name}/{step_id}', getattr(self, step_id)))
            routes.append((f'/{app_name}/{step_id}_submit', getattr(self, f'{step_id}_submit'), ['POST']))
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ['GET']
            app.route(path, methods=method_list)(handler)
        self.step_messages = {'finalize': {'ready': 'All steps complete. Ready to finalize workflow.', 'complete': f'Workflow finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes.'}}
        for step in steps:
            self.step_messages[step.id] = {'input': f'{pip.fmt(step.id)}: Please complete {step.show}.', 'complete': f'{step.show} complete. Continue to next step.'}
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

    async def landing(self, request):
        """Generate the landing page using the standardized helper while maintaining WET explicitness."""
        pip = self.pipulate

        # Use centralized landing page helper - maintains WET principle by explicit call
        return pip.create_standard_landing_page(self)

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
        plugin_name = app_name  # Use app_name directly to ensure consistency
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
        return pip.run_all_cells(app_name, steps)

    async def finalize(self, request):
        """Handles GET request to show Finalize button and POST request to lock the workflow."""
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
                    return Card(H3('All steps complete. Finalize?'), P('You can revert to any step and make changes.', cls='text-secondary'), Form(Button('Finalize 🔒', type='submit', cls='primary'), hx_post=f'/{app_name}/finalize', hx_target=f'#{app_name}-container'), id=finalize_step.id)
                else:
                    return Div(id=finalize_step.id)
        else:
            await pip.finalize_workflow(pipeline_id)
            await self.message_queue.add(pip, self.step_messages['finalize']['complete'], verbatim=True)
            return pip.run_all_cells(app_name, steps)

    async def unfinalize(self, request):
        """Handles POST request to unlock the workflow."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        pipeline_id = db.get('pipeline_id', 'unknown')
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, 'Workflow unfinalized! You can now revert to any step and make changes.', verbatim=True)
        return pip.run_all_cells(app_name, steps)

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
            return P('Error: No step specified', cls='text-invalid')
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        state = pip.read_state(pipeline_id)
        state['_revert_target'] = step_id
        pip.write_state(pipeline_id, state)
        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        return pip.run_all_cells(app_name, steps)

    async def reopen_url(self, request):
        """Handle reopening a URL with Selenium."""
        pip, db = (self.pipulate, self.db)
        form = await request.form()
        url = form.get('url', '').strip()
        if not url:
            return P('Error: URL is required', cls='text-invalid')
        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--new-window')
            chrome_options.add_argument('--start-maximized')
            import tempfile
            profile_dir = tempfile.mkdtemp()
            chrome_options.add_argument(f'--user-data-dir={profile_dir}')
            effective_os = os.environ.get('EFFECTIVE_OS', 'unknown')
            await self.message_queue.add(pip, f'Current OS: {effective_os}', verbatim=True)
            if effective_os == 'darwin':
                await self.message_queue.add(pip, 'Using webdriver-manager for macOS', verbatim=True)
                service = Service(ChromeDriverManager().install())
            else:
                await self.message_queue.add(pip, 'Using system Chrome for Linux', verbatim=True)
                service = Service()
            await self.message_queue.add(pip, 'Initializing Chrome driver...', verbatim=True)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            await self.message_queue.add(pip, f'Reopening URL with Selenium: {url}', verbatim=True)
            driver.get(url)
            await asyncio.sleep(2)
            title = driver.title
            await self.message_queue.add(pip, f'Page loaded successfully. Title: {title}', verbatim=True)
            driver.quit()
            await self.message_queue.add(pip, 'Browser closed successfully', verbatim=True)
            import shutil
            shutil.rmtree(profile_dir, ignore_errors=True)
            return P(f'Successfully reopened: {url}', style='color: green;')
        except Exception as e:
            error_msg = f'Error reopening URL with Selenium: {str(e)}'
            logger.error(error_msg)
            await self.message_queue.add(pip, error_msg, verbatim=True)
            return P(error_msg, cls='text-invalid')

    async def step_01(self, request):
        """Handles GET request for URL input step."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        url_value = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and url_value:
            return Div(Card(H3(f'🔒 {step.show}'), P(f'URL configured: ', B(url_value)), Button('Open in New Tab ▸', type='button', _onclick=f"window.open('{url_value}', '_blank')", cls='secondary')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif url_value and state.get('_revert_target') != step_id:
            content_container = pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: {url_value}', widget=Div(P(f'URL configured: ', B(url_value)), Button('Open in New Tab ▸', type='button', _onclick=f"window.open('{url_value}', '_blank')", cls='secondary')), steps=steps)
            return Div(content_container, Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        else:
            await self.message_queue.add(pip, 'Enter the URL you want to open in a new tab:', verbatim=True)
            display_value = url_value if step.refill and url_value else 'https://example.com/'
            return Div(Card(H3(f'{step.show}'),
                P('The URL will open in a new tab and your browser will switch to it. Return to this tab when you\'re done.', cls='text-secondary'),
                Form(Input(type='url', name='url', placeholder='https://example.com/', required=True, value=display_value, cls='contrast'),
                Button('Open in New Tab ▸', type='submit', cls='primary'),
                hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')),
                Div(id=next_step_id), id=step_id)

    async def step_01_submit(self, request):
        """Process the URL submission and open the URL."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        form = await request.form()
        url = form.get('url', '').strip()
        if not url:
            return P('Error: URL is required', cls='text-invalid')
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        await pip.set_step_data(pipeline_id, step_id, url, steps)
        import webbrowser
        webbrowser.open(url)
        await self.message_queue.add(pip, f'Opening URL in a new tab: {url}', verbatim=True)
        url_widget = Div(P(f'URL configured: ', B(url)), Button('Open URL in a new tab again ▸', type='button', _onclick=f"window.open('{url}', '_blank')", cls='secondary'))
        content_container = pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: {url}', widget=url_widget, steps=steps)
        return Div(content_container, Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)

    async def step_02(self, request):
        """Handles GET request for Google Search step."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        query_value = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and query_value:
            search_url = f'https://www.google.com/search?q={query_value}'
            return Div(Card(H3(f'🔒 {step.show}'), P(f'Search query: ', B(query_value)), Button('Search Again ▸', type='button', _onclick=f"window.open('{search_url}', '_blank')", cls='secondary')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif query_value and state.get('_revert_target') != step_id:
            search_url = f'https://www.google.com/search?q={query_value}'
            content_container = pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: {query_value}', widget=Div(P(f'Search query: ', B(query_value)), Button('Search in a new tab ▸', type='button', _onclick=f"window.open('{search_url}', '_blank')", cls='secondary')), steps=steps)
            return Div(content_container, Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        else:
            await self.message_queue.add(pip, 'Enter your Google search query:', verbatim=True)
            display_value = query_value if step.refill and query_value else 'example search query'
            return Div(Card(H3(f'{step.show}'), Form(Input(type='text', name='query', placeholder='Enter search query', required=True, value=display_value, cls='contrast'), Button('Search in a new tab ▸', type='submit', cls='primary'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')), Div(id=next_step_id), id=step_id)

    async def step_02_submit(self, request):
        """Process the search query submission and open Google search in a new tab."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        form = await request.form()
        query = form.get('query', '').strip()
        if not query:
            return P('Error: Search query is required', cls='text-invalid')
        await pip.set_step_data(pipeline_id, step_id, query, steps)
        search_url = f'https://www.google.com/search?q={query}'
        import webbrowser
        webbrowser.open(search_url)
        await self.message_queue.add(pip, f'Opening Google search in a new tab: {query}', verbatim=True)
        search_widget = Div(P(f'Search query: ', B(query)), Button('Search in a new tab again ▸', type='button', _onclick=f"window.open('{search_url}', '_blank')", cls='secondary'))
        content_container = pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: {query}', widget=search_widget, steps=steps)
        return Div(content_container, Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)

    async def step_03(self, request):
        """Handles GET request for Selenium URL step."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_03'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        url_value = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and url_value:
            return Div(Card(H3(f'🔒 {step.show}'), P(f'URL configured: ', B(url_value)), Form(Input(type='hidden', name='url', value=url_value), Button('Open URL Again 🪄', type='submit', cls='secondary'), hx_post=f'/{app_name}/reopen_url', hx_target=f'#{step_id}-status'), Div(id=f'{step_id}-status')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif url_value and state.get('_revert_target') != step_id:
            content_container = pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: {url_value}', widget=Div(P(f'URL configured: ', B(url_value)), Form(Input(type='hidden', name='url', value=url_value), Button('Open URL Again 🪄', type='submit', cls='secondary'), hx_post=f'/{app_name}/reopen_url', hx_target=f'#{step_id}-status'), Div(id=f'{step_id}-status')), steps=steps)
            return Div(content_container, Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        else:
            await self.message_queue.add(pip, 'This is a fancy extra! While most URLs can be opened in a new tab, Selenium gives you full browser automation control. Note: Maintaining login sessions can be tricky - for complex automation needs, check out the Browser Automation plugin.', verbatim=True)
            display_value = url_value if step.refill and url_value else 'https://example.com/'
            return Div(Card(H3(f'{step.show}'), P('Try Selenium automation - great for complex workflows!', cls='text-secondary'), Form(Input(type='url', name='url', placeholder='https://example.com/', required=True, value=display_value, cls='contrast'), Button('Open with Selenium 🪄', type='submit', cls='primary'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')), Div(id=next_step_id), id=step_id)

    async def step_03_submit(self, request):
        """Process the URL submission and open it with Selenium."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_03'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        form = await request.form()
        url = form.get('url', '').strip()
        if not url:
            return P('Error: URL is required', cls='text-invalid')
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        await pip.set_step_data(pipeline_id, step_id, url, steps)
        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--new-window')
            chrome_options.add_argument('--start-maximized')
            import tempfile
            profile_dir = tempfile.mkdtemp()
            chrome_options.add_argument(f'--user-data-dir={profile_dir}')
            effective_os = os.environ.get('EFFECTIVE_OS', 'unknown')
            await self.message_queue.add(pip, f'Current OS: {effective_os}', verbatim=True)
            if effective_os == 'darwin':
                await self.message_queue.add(pip, 'Using webdriver-manager for macOS', verbatim=True)
                service = Service(ChromeDriverManager().install())
            else:
                await self.message_queue.add(pip, 'Using system Chrome for Linux', verbatim=True)
                service = Service()
            await self.message_queue.add(pip, 'Initializing Chrome driver...', verbatim=True)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            await self.message_queue.add(pip, f'Opening URL with Selenium: {url}', verbatim=True)
            driver.get(url)
            await asyncio.sleep(2)
            title = driver.title
            await self.message_queue.add(pip, f'Page loaded successfully. Title: {title}', verbatim=True)
            driver.quit()
            await self.message_queue.add(pip, 'Browser closed successfully', verbatim=True)
            import shutil
            shutil.rmtree(profile_dir, ignore_errors=True)
        except Exception as e:
            error_msg = f'Error opening URL with Selenium: {str(e)}'
            logger.error(error_msg)
            await self.message_queue.add(pip, error_msg, verbatim=True)
            return P(error_msg, cls='text-invalid')
        url_widget = Div(P(f'URL configured: ', B(url)), Form(Input(type='hidden', name='url', value=url), Button('Open URL Again 🪄', type='submit', cls='secondary'), hx_post=f'/{app_name}/reopen_url', hx_target=f'#{step_id}-status'), Div(id=f'{step_id}-status'))
        content_container = pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: {url}', widget=url_widget, steps=steps)
        return Div(content_container, Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)

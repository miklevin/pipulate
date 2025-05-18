import asyncio
import json
from collections import namedtuple
from datetime import datetime
from fasthtml.common import *
from loguru import logger
from starlette.responses import HTMLResponse
ROLES = ['Developer']
'\nPipulate Rich Table Widget Workflow\nA workflow for demonstrating the Rich Table widget with beautiful styling.\n'
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))

class RichTableWidget:
    """
    Rich Table Widget Workflow

    Demonstrates rendering JSON data as a beautifully styled HTML table.
    """
    APP_NAME = 'rich_table_widget'
    DISPLAY_NAME = 'Rich Table Widget'
    ENDPOINT_MESSAGE = 'This workflow demonstrates a custom-styled Rich Table widget. Enter JSON data to see it rendered as a beautifully formatted HTML table.'
    TRAINING_PROMPT = 'This workflow is for demonstrating and testing the Rich Table widget. The user will input JSON data, and the system will render it as a custom-styled HTML table.'

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
        steps = [Step(id='step_01', done='rich_table_data', show='Table Data (JSON)', refill=True, transform=lambda prev_value: prev_value.strip() if prev_value else '')]
        routes = [(f'/{app_name}', self.landing), (f'/{app_name}/init', self.init, ['POST']), (f'/{app_name}/revert', self.handle_revert, ['POST']), (f'/{app_name}/finalize', self.finalize, ['GET', 'POST']), (f'/{app_name}/unfinalize', self.unfinalize, ['POST'])]
        self.steps = steps
        for step in steps:
            step_id = step.id
            routes.append((f'/{app_name}/{step_id}', getattr(self, step_id)))
            routes.append((f'/{app_name}/{step_id}_submit', getattr(self, f'{step_id}_submit'), ['POST']))
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ['GET']
            app.route(path, methods=method_list)(handler)
        self.step_messages = {'finalize': {'ready': 'All steps complete. Ready to finalize workflow.', 'complete': f'Workflow finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes.'}, 'step_01': {'input': 'Please enter JSON data for the Rich Table.', 'complete': 'JSON data processed and Rich Table rendered.'}}
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

    async def landing(self, request):
        pip, pipeline, steps, app_name = (self.pipulate, self.pipeline, self.steps, self.app_name)
        title = f'{self.DISPLAY_NAME or app_name.title()}'
        full_key, prefix, user_part = pip.generate_pipeline_key(self)
        default_value = full_key
        pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in pipeline() if record.pkey.startswith(prefix)]
        datalist_options = [f"{prefix}{record_key.replace(prefix, '')}" for record_key in matching_records]
        return Container(Card(H2(title), P(self.ENDPOINT_MESSAGE, cls='text-secondary'), Form(pip.wrap_with_inline_button(Input(placeholder='Existing or new 🗝 here (Enter for auto)', name='pipeline_id', list='pipeline-ids', type='search', required=False, autofocus=True, value=default_value, _onfocus='this.setSelectionRange(this.value.length, this.value.length)', cls='contrast'), button_label=f'Enter 🔑', button_class='secondary'), pip.update_datalist('pipeline-ids', options=datalist_options if datalist_options else None), hx_post=f'/{app_name}/init', hx_target=f'#{app_name}-container')), Div(id=f'{app_name}-container'))

    async def init(self, request):
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
            _, temp_prefix, user_provided_id_part = pip.generate_pipeline_key(self, user_input)
            pipeline_id = f'{expected_prefix}{user_provided_id_part}'
        db['pipeline_id'] = pipeline_id
        state, error = pip.initialize_if_missing(pipeline_id, {'app_name': app_name})
        if error:
            return error
        await self.message_queue.add(pip, f'Workflow ID: {pipeline_id}', verbatim=True, spaces_before=0)
        await self.message_queue.add(pip, f"Return later by selecting '{pipeline_id}' from the dropdown.", verbatim=True, spaces_before=0)
        return Div(Div(id='step_01', hx_get=f'/{app_name}/step_01', hx_trigger='load'), id=f'{app_name}-container')

    async def finalize(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        pipeline_id = db.get('pipeline_id', 'unknown')
        finalize_step = steps[-1]
        finalize_data = pip.get_step_data(pipeline_id, finalize_step.id, {})
        if request.method == 'GET':
            if finalize_step.done in finalize_data:
                return Card(H3('Workflow is locked.'), Form(Button(pip.UNLOCK_BUTTON_LABEL, type='submit', cls='secondary outline'), hx_post=f'/{app_name}/unfinalize', hx_target=f'#{app_name}-container', hx_swap='outerHTML'), id=finalize_step.id)
            else:
                all_steps_complete = all((pip.get_step_data(pipeline_id, step.id, {}).get(step.done) for step in steps[:-1]))
                if all_steps_complete:
                    return Card(H3('All steps complete. Finalize?'), P('You can revert to any step and make changes.', cls='text-secondary'), Form(Button('Finalize 🔒', type='submit', cls='primary'), hx_post=f'/{app_name}/finalize', hx_target=f'#{app_name}-container', hx_swap='outerHTML'), id=finalize_step.id)
                else:
                    return Div(id=finalize_step.id)
        else:
            await pip.finalize_workflow(pipeline_id)
            await self.message_queue.add(pip, self.step_messages['finalize']['complete'], verbatim=True)
            return pip.rebuild(app_name, steps)

    async def unfinalize(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        pipeline_id = db.get('pipeline_id', 'unknown')
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, 'Workflow unfinalized! You can now revert to any step and make changes.', verbatim=True)
        return pip.rebuild(app_name, steps)

    async def get_suggestion(self, step_id, state):
        if step_id == 'step_01':
            sample_data = [{'name': 'Parameter 1', 'value1': 1000, 'value2': 500, 'value3': 50}, {'name': 'Parameter 2', 'value1': 2000, 'value2': 1000, 'value3': 100}, {'name': 'Parameter 3', 'value1': 3000, 'value2': 1500, 'value3': 150}]
            return json.dumps(sample_data, indent=2)
        return ''

    async def handle_revert(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        form = await request.form()
        step_id = form.get('step_id')
        pipeline_id = db.get('pipeline_id', 'unknown')
        if not step_id:
            return P('Error: No step specified', style=pip.get_style('error'))
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        state = pip.read_state(pipeline_id)
        state['_revert_target'] = step_id
        pip.write_state(pipeline_id, state)
        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        return pip.rebuild(app_name, steps)

    def create_rich_table_widget(self, data):
        """Create a rich table widget with beautiful styling."""
        if not data:
            return P('No data provided for table', cls='text-invalid')
        headers = list(data[0].keys())
        table_html = f'\n        <table class="param-table">\n            <caption>Rich Table Example</caption>\n            <tr class="header">\n        '
        for i, header in enumerate(headers):
            header_class = 'param-name' if header == 'name' else f'{header}-val'
            td_class = 'header-cell'
            table_html += f'<td class="{td_class}"><span class="{header_class}">{header}</span></td>'
        table_html += '</tr>'
        for row in data:
            table_html += '<tr>'
            for i, header in enumerate(headers):
                cell_class = 'param-name' if header == 'name' else f'{header}-val'
                value = row.get(header, '')
                if isinstance(value, (int, float)):
                    value = f'{value:,}'
                table_html += f'<td><span class="{cell_class}">{value}</span></td>'
            table_html += '</tr>'
        table_html += '</table>'
        return Div(NotStr(table_html), cls='overflow-auto')

    async def step_01(self, request):
        """ 
        Handles GET request for Step 1: Rich Table Widget.

        This widget demonstrates a beautifully styled table with:
        - Connected border lines
        - Alternating row colors
        - Bold headers with thicker borders
        - Proper cell padding and alignment
        - Color-coded columns
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        table_data = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and table_data:
            try:
                data = json.loads(table_data)
                table_widget = self.create_rich_table_widget(data)
                return Div(Card(H3(f'🔒 {step.show}'), table_widget), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
            except Exception as e:
                logger.error(f'Error creating table widget in finalized view: {str(e)}')
                return Div(Card(f'🔒 {step.show}: <content locked>'), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif table_data and state.get('_revert_target') != step_id:
            try:
                data = json.loads(table_data)
                table_widget = self.create_rich_table_widget(data)
                content_container = pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show} Configured', widget=table_widget, steps=steps)
                return Div(content_container, Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
            except Exception as e:
                logger.error(f'Error creating table widget: {str(e)}')
                state['_revert_target'] = step_id
                pip.write_state(pipeline_id, state)
        display_value = table_data if step.refill and table_data else await self.get_suggestion(step_id, state)
        await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
        return Div(Card(H3(f'{pip.fmt(step_id)}: Configure {step.show}'), P('Enter table data as JSON array of objects. Example is pre-populated.'), P('Format: [{"name": "value", "value1": number, ...}, {...}]', cls='text-note'), Form(Div(Textarea(display_value, name=step.done, placeholder='Enter JSON array of objects for the table', required=True, rows=10, style='width: 100%; font-family: monospace;'), Div(Button('Create Table ▸', type='submit', cls='primary'), style='margin-top: 1vh; text-align: right;'), cls='w-full'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')), Div(id=next_step_id), id=step_id)

    async def step_01_submit(self, request):
        """Process the submission for Rich Table Widget."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        form = await request.form()
        table_data = form.get(step.done, '').strip()
        is_valid, error_msg, error_component = pip.validate_step_input(table_data, step.show)
        if not is_valid:
            return error_component
        try:
            data = json.loads(table_data)
            if not isinstance(data, list) or not data:
                return P('Invalid JSON: Must be a non-empty array of objects', style=pip.get_style('error'))
            if not all((isinstance(item, dict) for item in data)):
                return P('Invalid JSON: All items must be objects (dictionaries)', style=pip.get_style('error'))
        except json.JSONDecodeError:
            return P('Invalid JSON format. Please check your syntax.', style=pip.get_style('error'))
        await pip.set_step_data(pipeline_id, step_id, table_data, steps)
        try:
            table_widget = self.create_rich_table_widget(data)
            content_container = pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: Table created with {len(data)} rows', widget=table_widget, steps=steps)
            response_content = Div(content_container, Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
            await self.message_queue.add(pip, f'{step.show} complete. Table created with {len(data)} rows.', verbatim=True)
            return HTMLResponse(to_xml(response_content))
        except Exception as e:
            logger.error(f'Error creating table widget: {e}')
            return P(f'Error creating table: {str(e)}', style=pip.get_style('error'))
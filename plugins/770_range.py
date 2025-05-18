import asyncio
from collections import namedtuple
from datetime import datetime
from fasthtml.common import *
from loguru import logger
ROLES = ['Developer']
'\nPipulate Range Selector Workflow\nA workflow for managing and testing range input-based interactions.\n\nRULE NAVIGATION GUIDE:\n--------------------\n1. Core Widget Patterns:\n   - See: patterns/workflow-patterns.mdc\n   - Key sections: "Common Widget Patterns", "Widget State Management"\n   - Critical for understanding the immutable chain reaction pattern\n\n2. Implementation Guidelines:\n   - See: implementation/implementation-workflow.mdc\n   - Focus on: "Widget Implementation Steps", "Widget Testing Checklist"\n   - Essential for maintaining workflow integrity\n\n3. Common Pitfalls:\n   - See: patterns/workflow-patterns.mdc\n   - Review: "Common Widget Pitfalls", "Recovery Process"\n   - Critical for avoiding state management issues\n\n4. Widget Design Philosophy:\n   - See: philosophy/philosophy-core.mdc\n   - Key concepts: "State Management", "UI Construction"\n   - Important for maintaining consistent patterns\n\n5. Recovery Patterns:\n   - See: patterns/workflow-patterns.mdc\n   - Focus on: "Recovery Process", "Prevention Guidelines"\n   - Essential for handling workflow breaks\n\nCONVERSION POINTS:\n----------------\nWhen converting this template to a new widget:\n1. CUSTOMIZE_STEP_DEFINITION: Change \'done\' field to specific data field name\n2. CUSTOMIZE_FORM: Replace the Proceed button with specific form elements\n3. CUSTOMIZE_DISPLAY: Update the finalized state display for your widget\n4. CUSTOMIZE_COMPLETE: Enhance the completion state with widget display\n\nCRITICAL ELEMENTS TO PRESERVE:\n----------------------------\n- Chain reaction with next_step_id\n- Finalization state handling pattern\n- Revert control mechanism\n- Overall Div structure and ID patterns\n- LLM context updates for widget content\n'
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))

class RangeSelectorWorkflow:
    """
    Range Selector Workflow
    
    A focused environment for designing and testing range input-based interactions in isolation.
    This workflow provides a clean environment to focus on range selector development without the complexity
    of a full workflow implementation.
    """
    APP_NAME = 'range_selector'
    DISPLAY_NAME = 'Range Selector Widget'
    ENDPOINT_MESSAGE = 'Welcome to the Range Selector Widget! This is a focused environment for designing and testing range input-based interactions in isolation. Use this space to prototype and refine your range selector designs without distractions.'
    TRAINING_PROMPT = 'This is a specialized workflow for designing and testing range selector interactions in isolation. It provides a clean environment to focus on range selector development without the complexity of a full workflow implementation.'
    RANGE_CONFIG = {'min': 0, 'max': 100, 'step': 1, 'default': 50, 'label': 'Select a value', 'description': 'Use the slider to select a value between 0 and 100', 'show_value': True, 'show_ticks': False, 'tick_labels': {}}

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
        steps = [Step(id='step_01', done='range_value', show='Range Selection', refill=True, transform=lambda prev_value: int(prev_value) if prev_value else self.RANGE_CONFIG['default'])]
        routes = [(f'/{app_name}', self.landing), (f'/{app_name}/init', self.init, ['POST']), (f'/{app_name}/revert', self.handle_revert, ['POST']), (f'/{app_name}/finalize', self.finalize, ['GET', 'POST']), (f'/{app_name}/unfinalize', self.unfinalize, ['POST'])]
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

    async def landing(self):
        """Renders the initial landing page with the key input form."""
        pip, pipeline, steps, app_name = (self.pipulate, self.pipeline, self.steps, self.app_name)
        title = f'{self.DISPLAY_NAME or app_name.title()}'
        full_key, prefix, user_part = pip.generate_pipeline_key(self)
        default_value = full_key
        pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in pipeline() if record.pkey.startswith(prefix)]
        datalist_options = [f"{prefix}{record_key.replace(prefix, '')}" for record_key in matching_records]
        return Container(Card(H2(title), P(self.ENDPOINT_MESSAGE, cls='text-muted-lead'), Form(pip.wrap_with_inline_button(Input(placeholder='Existing or new 🗝 here (Enter for auto)', name='pipeline_id', list='pipeline-ids', type='search', required=False, autofocus=True, value=default_value, _onfocus='this.setSelectionRange(this.value.length, this.value.length)', cls='contrast'), button_label=f'Enter 🔑', button_class='secondary'), pip.update_datalist('pipeline-ids', options=datalist_options if datalist_options else None), hx_post=f'/{app_name}/init', hx_target=f'#{app_name}-container')), Div(id=f'{app_name}-container'))

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
                    return Card(H3('All steps complete. Finalize?'), P('You can revert to any step and make changes.', cls='text-muted-lead'), Form(Button('Finalize 🔒', type='submit', cls='primary'), hx_post=f'/{app_name}/finalize', hx_target=f'#{app_name}-container'), id=finalize_step.id)
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
        """Returns a suggestion for the current step based on state."""
        return 'Complete this step to continue.'

    async def handle_revert(self, request):
        """Handles POST request to revert to a previous step."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        form = await request.form()
        step_id = form.get('step_id', '')
        if step_id not in self.steps_indices:
            return P('Error: Invalid step', style=pip.ERROR_STYLE)
        pipeline_id = db.get('pipeline_id', 'unknown')
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        state = pip.read_state(pipeline_id)
        state['_revert_target'] = step_id
        pip.write_state(pipeline_id, state)
        return Div(Div(id=step_id, hx_get=f'/{app_name}/{step_id}', hx_trigger='load'), id=f'{app_name}-container')

    async def step_01(self, request):
        """Handles GET request for range selection step."""
        logger.debug('Entering step_01')
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        logger.debug(f'Pipeline ID: {pipeline_id}')
        logger.debug(f'State: {state}')
        logger.debug(f'Step data: {step_data}')
        selected_value = step_data.get(step.done, self.RANGE_CONFIG['default'])
        logger.debug(f'Selected value: {selected_value}')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and selected_value:
            pip.append_to_history(f'[WIDGET CONTENT] {step.show} (Finalized):\n{selected_value}')
            return Div(Card(H3(f'🔒 {step.show}'), P(f'Selected value: {selected_value}', cls='fw-bold')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif step_data.get(step.done) and state.get('_revert_target') != step_id:
            pip.append_to_history(f'[WIDGET CONTENT] {step.show} (Completed):\n{selected_value}')
            return Div(pip.revert_control(step_id=step_id, app_name=app_name, message=f'{step.show}: {selected_value}', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        else:
            pip.append_to_history(f'[WIDGET STATE] {step.show}: Showing input form')
            await self.message_queue.add(pip, self.step_messages.get(step_id, {}).get('input', f'Complete {step.show}'), verbatim=True)
            try:
                range_input = Input(type='range', name=f'{step.done}_slider', id=f'{step.done}_slider', min=self.RANGE_CONFIG['min'], max=self.RANGE_CONFIG['max'], step=self.RANGE_CONFIG['step'], value=selected_value, title=self.RANGE_CONFIG['description'], required=True, style='flex-grow: 1; margin: 0 10px;', _oninput=f"document.getElementById('{step.done}').value = this.value;")
                number_input = Input(type='number', name=step.done, id=step.done, min=self.RANGE_CONFIG['min'], max=self.RANGE_CONFIG['max'], step=self.RANGE_CONFIG['step'], value=selected_value, required=True, style='width: 100px;', _oninput=f"document.getElementById('{step.done}_slider').value = this.value;", _onkeydown="if(event.key === 'Enter') { event.preventDefault(); return false; }")
                return Div(Card(H3(f'{step.show}'), P(self.RANGE_CONFIG['description'], cls='text-muted-lead'), Form(Div(Label(self.RANGE_CONFIG['label'], style='min-width: 180px;'), range_input, number_input, style='display: flex; align-items: center; gap: 10px; margin: 1em 0;'), Button('Submit', type='submit', cls='primary'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')), Div(id=next_step_id), id=step_id)
            except Exception as e:
                logger.error(f'Error creating range selector: {str(e)}')
                logger.exception('Full traceback:')
                return Div(Card(H3(f'{step.show}'), P(f'Error creating range selector: {str(e)}', style=pip.ERROR_STYLE)), id=step_id)

    async def step_01_submit(self, request):
        """Handles POST request for range selection step."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        form = await request.form()
        value = form.get(step.done, '').strip()
        if not value:
            return P('Error: Please select a value', style=pip.ERROR_STYLE)
        try:
            value = int(value)
            if value < self.RANGE_CONFIG['min'] or value > self.RANGE_CONFIG['max']:
                return P(f"Error: Value must be between {self.RANGE_CONFIG['min']} and {self.RANGE_CONFIG['max']}", style=pip.ERROR_STYLE)
        except ValueError:
            return P('Error: Invalid value', style=pip.ERROR_STYLE)
        await pip.set_step_data(pipeline_id, step_id, value, steps)
        await self.message_queue.add(pip, self.step_messages.get(step_id, {}).get('complete', f'{step.show} complete: {value}'), verbatim=True)
        return Div(pip.revert_control(step_id=step_id, app_name=app_name, message=f'{step.show}: {value}', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
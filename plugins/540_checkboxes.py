import asyncio
from collections import namedtuple
from datetime import datetime

from fasthtml.common import *
from loguru import logger

ROLES = ['Components']
'\nPipulate Checkbox Workflow\nA workflow for managing and testing checkbox-based interactions.\n\nRULE NAVIGATION GUIDE:\n--------------------\n1. Core Widget Patterns:\n   - See: patterns/workflow-patterns.mdc\n   - Key sections: "Common Widget Patterns", "Widget State Management"\n   - Critical for understanding the immutable chain reaction pattern\n\n2. Implementation Guidelines:\n   - See: implementation/implementation-workflow.mdc\n   - Focus on: "Widget Implementation Steps", "Widget Testing Checklist"\n   - Essential for maintaining workflow integrity\n\n3. Common Pitfalls:\n   - See: patterns/workflow-patterns.mdc\n   - Review: "Common Widget Pitfalls", "Recovery Process"\n   - Critical for avoiding state management issues\n\n4. Widget Design Philosophy:\n   - See: philosophy/philosophy-core.mdc\n   - Key concepts: "State Management", "UI Construction"\n   - Important for maintaining consistent patterns\n\n5. Recovery Patterns:\n   - See: patterns/workflow-patterns.mdc\n   - Focus on: "Recovery Process", "Prevention Guidelines"\n   - Essential for handling workflow breaks\n\nCONVERSION POINTS:\n----------------\nWhen converting this template to a new widget:\n1. CUSTOMIZE_STEP_DEFINITION: Change \'done\' field to specific data field name\n2. CUSTOMIZE_FORM: Replace the Proceed button with specific form elements\n3. CUSTOMIZE_DISPLAY: Update the finalized state display for your widget\n4. CUSTOMIZE_COMPLETE: Enhance the completion state with widget display\n\nCRITICAL ELEMENTS TO PRESERVE:\n----------------------------\n- Chain reaction with next_step_id\n- Finalization state handling pattern\n- Revert control mechanism\n- Overall Div structure and ID patterns\n- LLM context updates for widget content\n'
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class CheckboxWorkflow:
    """
    Checkbox Workflow

    A workflow for managing and testing checkbox-based interactions in isolation.
    This workflow provides a focused environment for developing and testing checkbox
    functionality without the complexity of a full workflow implementation.
    """
    # Template compatibility markers
    # STEPS_LIST_INSERTION_POINT
    # STEP_METHODS_INSERTION_POINT
    
    # UI Constants for automation testing
    UI_CONSTANTS = {
        'CHECKBOX_INPUT': 'checkbox-widget-checkbox-input',
        'CHECKBOX_LABEL': 'checkbox-widget-checkbox-label',
        'FIELDSET': 'checkbox-widget-fieldset',
        'FINALIZE_BUTTON': 'checkbox-widget-finalize-button', 
        'UNLOCK_BUTTON': 'checkbox-widget-unlock-button',
        'NEXT_BUTTON': 'checkbox-widget-next-button',
        'REVERT_BUTTON': 'checkbox-widget-revert-button'
    }

    APP_NAME = 'checkbox_workflow'
    DISPLAY_NAME = 'Checkbox Widget'
    ENDPOINT_MESSAGE = 'Welcome to the Checkbox Widget! This is a focused environment for designing and testing checkbox-based interactions in isolation. Use this space to prototype and refine your checkbox designs without distractions.'
    TRAINING_PROMPT = 'This is a specialized workflow for designing and testing checkbox interactions in isolation. It provides a clean environment to focus on checkbox development without the complexity of a full workflow implementation.'
    SOURCE_TYPE = 'static'
    SOURCE_CONFIG = {'api_url': None, 'file_path': None, 'db_query': None, 'previous_step': None, 'value_field': 'value', 'label_field': 'label', 'group_field': 'group', 'description_field': 'description', 'options': [{'value': '1', 'label': 'Option 1', 'group': 'Group A', 'description': 'First option'}, {'value': '2', 'label': 'Option 2', 'group': 'Group A', 'description': 'Second option'}, {'value': '3', 'label': 'Option 3', 'group': 'Group B', 'description': 'Third option'}]}

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
        steps = [Step(id='step_01', done='checkbox_selection', show='Checkbox Selection', refill=True, transform=lambda prev_value: prev_value.strip() if prev_value else '')]
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
                return Card(H3('Workflow is locked.'), Form(Button(pip.UNLOCK_BUTTON_LABEL, type='submit', cls='secondary outline', data_testid='checkbox-widget-unlock-button', aria_label='Unlock checkbox workflow for editing'), hx_post=f'/{app_name}/unfinalize', hx_target=f'#{app_name}-container'), id=finalize_step.id)
            else:
                all_steps_complete = all((pip.get_step_data(pipeline_id, step.id, {}).get(step.done) for step in steps[:-1]))
                if all_steps_complete:
                    return Card(H3('All steps complete. Finalize?'), P('You can revert to any step and make changes.', cls='text-secondary'), Form(Button('Finalize 🔒', type='submit', cls='primary', data_testid='checkbox-widget-finalize-button', aria_label='Finalize checkbox workflow'), hx_post=f'/{app_name}/finalize', hx_target=f'#{app_name}-container'), id=finalize_step.id)
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

    async def step_01(self, request):
        """Handles GET request for checkbox selection step."""
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
        selected_values = step_data.get(step.done, [])
        if isinstance(selected_values, str):
            selected_values = [selected_values]
        logger.debug(f'Selected values: {selected_values}')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and selected_values:
            return Div(Card(H3(f'🔒 {step.show}'), P('Selected options:', cls='font-bold'), Ul(*[Li(value) for value in selected_values])), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif selected_values and state.get('_revert_target') != step_id:
            return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f"{step.show}: {', '.join(selected_values)}", steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        await self.message_queue.add(pip, self.step_messages.get(step_id, {}).get('input', f'Complete {step.show}'), verbatim=True)
        try:
            logger.debug('About to get options')
            raw_options = await self.get_options(pipeline_id)
            logger.debug(f'Got raw options: {raw_options}')
            options = [await self.format_option(option) for option in raw_options]
            logger.debug(f'Formatted options: {options}')
            grouped_options = {}
            for option in options:
                group = option['group']
                if group not in grouped_options:
                    grouped_options[group] = []
                grouped_options[group].append(option)
            logger.debug(f'Grouped options: {grouped_options}')
            checkbox_groups = []
            for group, group_options in grouped_options.items():
                group_checkboxes = []
                for option in group_options:
                    checkbox = Label(Input(type='checkbox', name=step.done, value=option['value'], checked=option['value'] in selected_values, title=option['description'] if option['description'] else None, data_testid='checkbox-widget-checkbox-input', aria_label=f'Checkbox for {option["label"]}'), f" {option['label']}", data_testid='checkbox-widget-checkbox-label')
                    group_checkboxes.append(checkbox)
                checkbox_groups.append(Fieldset(Legend(group), *group_checkboxes, data_testid='checkbox-widget-fieldset', aria_labelledby=f'fieldset-{group.lower().replace(" ", "-")}'))
            return Div(Card(H3(f'{step.show}'), Form(*checkbox_groups, Button('Submit', type='submit', cls='primary', data_testid='checkbox-widget-next-button', aria_label='Submit checkbox selections'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}', data_testid='checkbox-widget-form', aria_label='Checkbox selection form')), Div(id=next_step_id), id=step_id)
        except Exception as e:
            logger.error(f'Error getting options: {str(e)}')
            logger.exception('Full traceback:')
            return Div(Card(H3(f'{step.show}'), P(f'Error loading options: {str(e)}', cls='text-invalid')), id=step_id)

    async def step_01_submit(self, request):
        """Handles POST request for checkbox selection step."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        form = await request.form()
        values = form.getlist(step.done)
        if not values:
            return P('Error: Please select at least one option', cls='text-invalid')
        await self.pipulate.set_step_data(pipeline_id, step_id, values, steps)
        await self.message_queue.add(self.pipulate, self.step_messages.get(step_id, {}).get('complete', f"{step.show} complete: {', '.join(values)}"), verbatim=True)
        return Div(self.pipulate.display_revert_header(step_id=step_id, app_name=app_name, message=f"{step.show}: {', '.join(values)}", steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)

    async def get_options(self, pipeline_id):
        """Get options based on SOURCE_TYPE and SOURCE_CONFIG."""
        logger.debug(f'SOURCE_TYPE: {self.SOURCE_TYPE}')
        logger.debug(f'SOURCE_CONFIG: {self.SOURCE_CONFIG}')
        if self.SOURCE_TYPE == 'static':
            logger.debug('Getting static options')
            options = self.SOURCE_CONFIG.get('options', [])
            logger.debug(f'Retrieved options: {options}')
            if not options:
                raise ValueError('No options configured in SOURCE_CONFIG')
            return options
        elif self.SOURCE_TYPE == 'api':
            if not self.SOURCE_CONFIG['api_url']:
                raise ValueError('API URL not configured')
            return []
        elif self.SOURCE_TYPE == 'file':
            if not self.SOURCE_CONFIG['file_path']:
                raise ValueError('File path not configured')
            return []
        elif self.SOURCE_TYPE == 'db':
            if not self.SOURCE_CONFIG['db_query']:
                raise ValueError('Database query not configured')
            return []
        elif self.SOURCE_TYPE == 'previous_step':
            if not self.SOURCE_CONFIG['previous_step']:
                raise ValueError('Previous step not configured')
            return []
        else:
            raise ValueError(f'Unknown source type: {self.SOURCE_TYPE}')

    async def format_option(self, option):
        """Format an option for display."""
        logger.debug(f'Formatting option: {option}')
        value_field = self.SOURCE_CONFIG.get('value_field', 'value')
        label_field = self.SOURCE_CONFIG.get('label_field', 'label')
        group_field = self.SOURCE_CONFIG.get('group_field', 'group')
        description_field = self.SOURCE_CONFIG.get('description_field', 'description')
        logger.debug(f'Field names - value: {value_field}, label: {label_field}, group: {group_field}, description: {description_field}')
        value = option.get(value_field, '')
        label = option.get(label_field, value)
        group = option.get(group_field, 'Ungrouped')
        description = option.get(description_field, '')
        logger.debug(f'Extracted values - value: {value}, label: {label}, group: {group}, description: {description}')
        return {'value': value, 'label': label, 'group': group, 'description': description}

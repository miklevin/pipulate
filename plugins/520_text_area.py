import asyncio
from datetime import datetime
from fasthtml.common import *
from loguru import logger  
from common import Step, VALID_ROLES

ROLES = ['Components']  # See config.AVAILABLE_ROLES for all valid roles

# 📚 Widget conversion guide: helpers/docs_sync/widget_conversion_guide.md


class TextAreaWidget:
    """
    Text Area Widget Workflow

    A specialized workflow for handling multi-line text input with a textarea widget.
    Provides a clean interface for entering and managing longer text content.
    """
    # UI Constants for automation testing
    
    # Template compatibility markers
    # STEPS_LIST_INSERTION_POINT
    # STEP_METHODS_INSERTION_POINT

    UI_CONSTANTS = {
        'TEXTAREA_INPUT': 'text-area-widget-textarea-input',
        'FINALIZE_BUTTON': 'text-area-widget-finalize-button', 
        'UNLOCK_BUTTON': 'text-area-widget-unlock-button',
        'NEXT_BUTTON': 'text-area-widget-next-button',
        'REVERT_BUTTON': 'text-area-widget-revert-button'
    }

    APP_NAME = 'text_area_widget'
    DISPLAY_NAME = 'Text Area Widget'
    ENDPOINT_MESSAGE = 'Welcome to the Text Area Widget! This workflow provides a clean interface for entering and managing longer text content. Use the textarea to input multiple lines of text.'
    TRAINING_PROMPT = 'This is a specialized workflow for handling multi-line text input. It provides a clean interface for entering and managing longer text content.'

    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
        self.app = app
        self.app_name = app_name
        self.pipulate = pipulate
        self.pipeline = pipeline
        self.steps_indices = {}
        self.db = db
        pip = self.pipulate
        self.message_queue = pip.message_queue
        steps = [Step(id='step_01', done='text_area', show='Text Area', refill=True, transform=lambda prev_value: prev_value.strip() if prev_value else '')]
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
            self.step_messages[step.id] = {'input': f'{pip.fmt(step.id)}: Please enter {step.show}.', 'complete': f'{step.show} complete. Continue to next step.'}
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

    async def landing(self, request):
        """Generate the landing page using the standardized helper while maintaining WET explicitness."""
        pip = self.pipulate

        # Use centralized landing page helper - maintains WET principle by explicit call
        return pip.create_standard_landing_page(self)

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
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        pipeline_id = db.get('pipeline_id', 'unknown')
        finalize_step = steps[-1]
        finalize_data = pip.get_step_data(pipeline_id, finalize_step.id, {})
        if request.method == 'GET':
            if finalize_step.done in finalize_data:
                return Card(H3('Workflow is locked.'), Form(Button(pip.UNLOCK_BUTTON_LABEL, type='submit', cls='secondary outline', data_testid='text-area-widget-unlock-button', aria_label='Unlock text area for editing'), hx_post=f'/{app_name}/unfinalize', hx_target=f'#{app_name}-container'), id=finalize_step.id)
            else:
                all_steps_complete = all((pip.get_step_data(pipeline_id, step.id, {}).get(step.done) for step in steps[:-1]))
                if all_steps_complete:
                    return Card(H3('All steps complete. Finalize?'), P('You can revert to any step and make changes.', cls='text-secondary'), Form(Button('Finalize 🔒', type='submit', cls='primary', data_testid='text-area-widget-finalize-button', aria_label='Finalize text area workflow'), hx_post=f'/{app_name}/finalize', hx_target=f'#{app_name}-container'), id=finalize_step.id)
                else:
                    return Div(id=finalize_step.id)
        else:
            await pip.finalize_workflow(pipeline_id)
            await self.message_queue.add(pip, self.step_messages['finalize']['complete'], verbatim=True)
            return pip.run_all_cells(app_name, steps)

    async def unfinalize(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        pipeline_id = db.get('pipeline_id', 'unknown')
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, 'Workflow unfinalized! You can now revert to any step and make changes.', verbatim=True)
        return pip.run_all_cells(app_name, steps)

    async def get_suggestion(self, step_id, state):
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

    # --- START_STEP_BUNDLE: step_01 ---
    async def step_01(self, request):
        """ Handles GET request for Step 1: Displays textarea form or completed value. """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and user_val:
            locked_msg = f'🔒 Text area content is set to: {user_val}'
            await self.message_queue.add(pip, locked_msg, verbatim=True)
            return Div(Card(H3(f'🔒 {step.show}'), Pre(user_val, cls='code-block-container')), Div(id=next_step_id, hx_get=f'/{self.app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif user_val and state.get('_revert_target') != step_id:
            completed_msg = f'Step 1 is complete. You entered: {user_val}'
            await self.message_queue.add(pip, completed_msg, verbatim=True)
            text_widget = Pre(user_val, cls='code-block-container')
            content_container = pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show} Configured', widget=text_widget, steps=steps)
            return Div(content_container, Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'))
        else:
            if step.refill and user_val:
                display_value = user_val
            else:
                display_value = await self.get_suggestion(step_id, state)
            form_msg = 'Showing text area form. No text has been entered yet.'
            await self.message_queue.add(pip, form_msg, verbatim=True)
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            explanation = 'This is a text area widget for entering multiple lines of text. Use it to input longer content that may span multiple lines.'
            await self.message_queue.add(pip, explanation, verbatim=True)
            return Div(Card(H3(f'{pip.fmt(step.id)}: Enter {step.show}'), P(explanation, cls='text-secondary'), Form(pip.wrap_with_inline_button(Textarea(display_value, name=step.done, placeholder=f'Enter {step.show}', required=True, autofocus=True, cls='textarea-standard', data_testid='text-area-widget-textarea-input', aria_label='Multi-line text input area', aria_required='true', aria_labelledby=f'{step_id}-form-title', aria_describedby=f'{step_id}-form-instruction'), button_label='Next ▸'), hx_post=f'/{app_name}/{step.id}_submit', hx_target=f'#{step.id}')), Div(id=next_step_id), id=step.id)

    async def step_01_submit(self, request):
        """Process the submission for Step 1."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        if step.done == 'finalized':
            return await pip.handle_finalized_step(pipeline_id, step_id, steps, app_name, self)
        form = await request.form()
        user_val = form.get(step.done, '').strip()
        submit_msg = f'User submitted text: {user_val}'
        await self.message_queue.add(pip, submit_msg, verbatim=True)
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            error_msg = f'Text validation failed: {error_msg}'
            await self.message_queue.add(pip, error_msg, verbatim=True)
            return error_component
        processed_val = user_val
        await pip.set_step_data(pipeline_id, step_id, processed_val, steps)
        confirm_msg = f'{step.show}: {processed_val}'
        await self.message_queue.add(pip, confirm_msg, verbatim=True)
        if pip.check_finalize_needed(step_index, steps):
            finalize_msg = self.step_messages['finalize']['ready']
            await self.message_queue.add(pip, finalize_msg, verbatim=True)
        text_widget = Pre(processed_val, cls='code-block-container')
        content_container = pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show} Configured', widget=text_widget, steps=steps)
        return Div(content_container, Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
    # --- END_STEP_BUNDLE: step_01 ---

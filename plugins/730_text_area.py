import asyncio
from collections import namedtuple
from datetime import datetime

from fasthtml.common import *
from loguru import logger

ROLES = ['Components']
'\nText Area Widget Workflow\nA specialized workflow for handling multi-line text input with a textarea widget.\n\nRULE NAVIGATION GUIDE:\n--------------------\n1. Text Area Patterns:\n   - See: patterns/workflow-patterns.mdc\n   - Key sections: "Text Area Widget Pattern", "Multi-line Input"\n   - Critical for understanding text area implementation\n\n2. State Management:\n   - See: patterns/workflow-patterns.mdc\n   - Focus on: "Widget State Management", "Text Area State"\n   - Essential for proper text area state handling\n\n3. UI Construction:\n   - See: implementation/implementation-workflow.mdc\n   - Review: "Text Area UI Patterns", "Form Structure"\n   - Important for maintaining consistent text area UI\n\n4. Formatting Patterns:\n   - See: patterns/workflow-patterns.mdc\n   - Focus on: "Text Formatting", "Pre Tag Usage"\n   - Critical for text area display\n\n5. Recovery Process:\n   - See: patterns/workflow-patterns.mdc\n   - Review: "Recovery Process", "Text Area Recovery"\n   - Essential for handling text area workflow breaks\n\nIMPLEMENTATION NOTES:\n-------------------\n1. Text Area Specifics:\n   - Uses multi-line textarea with formatting\n   - Includes transform for text processing\n\n2. State Management:\n   - Stores text in \'text_area\' field\n   - Handles line breaks and whitespace\n   - Maintains text formatting\n\n3. UI Considerations:\n   - Minimum height for usability\n   - Monospace font for code\n   - Pre tag for formatting\n\n4. Common Pitfalls:\n   - Line break handling\n   - Whitespace preservation\n   - Formatting consistency\n'
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class TextAreaWidget:
    """
    Text Area Widget Workflow

    A specialized workflow for handling multi-line text input with a textarea widget.
    Provides a clean interface for entering and managing longer text content.
    """
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
            _, prefix, user_provided_id = pip.generate_pipeline_key(self, user_input)
            pipeline_id = f'{prefix}{user_provided_id}'
        db['pipeline_id'] = pipeline_id
        state, error = pip.initialize_if_missing(pipeline_id, {'app_name': app_name})
        if error:
            return error
        await self.message_queue.add(pip, f'Workflow ID: {pipeline_id}', verbatim=True, spaces_before=0)
        await self.message_queue.add(pip, f"Return later by selecting '{pipeline_id}' from the dropdown.", verbatim=True, spaces_before=0)
        return pip.rebuild(app_name, steps)

    async def finalize(self, request):
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
            return pip.rebuild(app_name, steps)

    async def unfinalize(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        pipeline_id = db.get('pipeline_id', 'unknown')
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, 'Workflow unfinalized! You can now revert to any step and make changes.', verbatim=True)
        return pip.rebuild(app_name, steps)

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
            return P('Error: No step specified', style=self.pipulate.get_style('error'))
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        state = pip.read_state(pipeline_id)
        state['_revert_target'] = step_id
        pip.write_state(pipeline_id, state)
        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        return pip.rebuild(app_name, steps)

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
            return Div(Card(H3(f'{pip.fmt(step.id)}: Enter {step.show}'), P(explanation, style=pip.get_style('muted')), Form(pip.wrap_with_inline_button(Textarea(display_value, name=step.done, placeholder=f'Enter {step.show}', required=True, autofocus=True, style='min-height: 200px; width: 100%; padding: 8px;', aria_required='true', aria_labelledby=f'{step_id}-form-title', aria_describedby=f'{step_id}-form-instruction'), button_label='Next ▸'), hx_post=f'/{app_name}/{step.id}_submit', hx_target=f'#{step.id}')), Div(id=next_step_id), id=step.id)

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

# File: plugins/830_simon_mcp.py
import asyncio
from collections import namedtuple
from datetime import datetime
from fasthtml.common import * # type: ignore
from loguru import logger
import inspect
from pathlib import Path
import re

ROLES = ['Components'] # Defines which user roles can see this plugin

Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None, None, None, False, None))

class SimonSaysMcpWidget:
    """
    Blank Placeholder Workflow
    A minimal template for creating new Pipulate workflows.
    It includes one placeholder step and the necessary structure for expansion.
    """
    APP_NAME = 'simon_mcp'
    DISPLAY_NAME = 'Simon Says MCP 🎪'
    ENDPOINT_MESSAGE = """Let's teach the LLM to make tool calls. Edit the prompt below to play Simon Says."""
    TRAINING_PROMPT = """This workflow is a game called 'Simon Says MCP'. The user will provide a detailed prompt to instruct the LLM on how to formulate a specific MCP request. Your role is to assist the user in refining these prompts and understanding the results."""

    # --- START_CLASS_ATTRIBUTES_BUNDLE ---
    # Additional class-level constants can be merged here by manage_class_attributes.py
    # --- END_CLASS_ATTRIBUTES_BUNDLE ---

    def __init__(self, app, pipulate, pipeline, db, app_name=None):
        self.app = app
        self.app_name = self.APP_NAME
        self.pipulate = pipulate
        self.pipeline = pipeline
        self.db = db
        pip = self.pipulate
        self.message_queue = pip.get_message_queue()

        # Access centralized UI constants through dependency injection
        self.ui = pip.get_ui_constants()

        # self.steps includes all data steps AND the system 'finalize' step at the end.
        # splice_workflow_step.py inserts new data steps BEFORE STEPS_LIST_INSERTION_POINT.
        self.steps = [
            Step(id='step_01', done='text_area', show='Text Area', refill=True, transform=lambda prev_value: prev_value.strip() if prev_value else ''),
            # --- STEPS_LIST_INSERTION_POINT ---
            Step(id='finalize', done='finalized', show='Finalize Workflow', refill=False)
        ]
        self.steps_indices = {step_obj.id: i for i, step_obj in enumerate(self.steps)}

        # Use centralized route registration helper
        pipulate.register_workflow_routes(self)

        self.step_messages = {}
        for step_obj in self.steps:
            if step_obj.id == 'finalize':
                self.step_messages['finalize'] = {
                    'ready': self.ui['MESSAGES']['ALL_STEPS_COMPLETE'],
                    'complete': f'Workflow finalized. Use {self.ui["BUTTON_LABELS"]["UNLOCK"]} to make changes.'
                }
            else:
                self.step_messages[step_obj.id] = {
                    'input': f'{step_obj.show}: Please provide the required input.',
                    'complete': f'{step_obj.show} is complete. Proceed to the next action.'
                }

    async def landing(self, request):
        """Generate the landing page using the standardized helper while maintaining WET explicitness."""
        pip = self.pipulate

        # Use centralized landing page helper - maintains WET principle by explicit call
        return pip.create_standard_landing_page(self)

    async def init(self, request):
        pip, db = self.pipulate, self.db
        internal_app_name = self.APP_NAME
        form = await request.form()
        user_input_key = form.get('pipeline_id', '').strip()

        if not user_input_key:
            pipeline_id, _, _ = pip.generate_pipeline_key(self)
        else:
            _, prefix_for_key_gen, _ = pip.generate_pipeline_key(self)
            if user_input_key.startswith(prefix_for_key_gen) and len(user_input_key.split('-')) == 3:
                pipeline_id = user_input_key
            else:
                 _, prefix, user_part = pip.generate_pipeline_key(self, user_input_key)
                 pipeline_id = f'{prefix}{user_part}'

        db['pipeline_id'] = pipeline_id
        state, error = pip.initialize_if_missing(pipeline_id, {'app_name': internal_app_name})
        if error: return error

        await self.message_queue.add(pip, self.ui['LANDING_PAGE']['INIT_MESSAGE_WORKFLOW_ID'].format(pipeline_id=pipeline_id), verbatim=True, spaces_before=0)
        await self.message_queue.add(pip, self.ui['LANDING_PAGE']['INIT_MESSAGE_RETURN_HINT'].format(pipeline_id=pipeline_id), verbatim=True, spaces_before=0)

        return pip.run_all_cells(internal_app_name, self.steps)

    async def finalize(self, request):
        pip, db, app_name = self.pipulate, self.db, self.APP_NAME
        # Use self.steps as it's the definitive list including 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')

        finalize_step_obj = next(s for s in self.steps if s.id == 'finalize')
        finalize_data = pip.get_step_data(pipeline_id, finalize_step_obj.id, {})

        if request.method == 'GET':
            if finalize_step_obj.done in finalize_data:
                return Card(H3(self.ui['MESSAGES']['WORKFLOW_LOCKED']), Form(Button(self.ui['BUTTON_LABELS']['UNLOCK'], type='submit', cls=self.ui['BUTTON_STYLES']['OUTLINE']), hx_post=f'/{app_name}/unfinalize', hx_target=f'#{app_name}-container'), id=finalize_step_obj.id)
            else:
                # Check if all data steps (all steps in self.steps *before* 'finalize') are complete
                all_data_steps_complete = all(pip.get_step_data(pipeline_id, step.id, {}).get(step.done) for step in self.steps if step.id != 'finalize')
                if all_data_steps_complete:
                    return Card(H3(self.ui['MESSAGES']['FINALIZE_QUESTION']), P(self.ui['MESSAGES']['FINALIZE_HELP'], cls='text-secondary'), Form(Button(self.ui['BUTTON_LABELS']['FINALIZE'], type='submit', cls=self.ui['BUTTON_STYLES']['PRIMARY']), hx_post=f'/{app_name}/finalize', hx_target=f'#{app_name}-container'), id=finalize_step_obj.id)
                else:
                    return Div(id=finalize_step_obj.id)
        elif request.method == 'POST':
            await pip.finalize_workflow(pipeline_id)
            await self.message_queue.add(pip, self.step_messages['finalize']['complete'], verbatim=True)
            return pip.run_all_cells(app_name, self.steps)

    async def unfinalize(self, request):
        pip, db, app_name = (self.pipulate, self.db, self.APP_NAME)
        pipeline_id = db.get('pipeline_id', 'unknown')
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, self.ui['MESSAGES']['WORKFLOW_UNLOCKED'], verbatim=True)
        return pip.run_all_cells(app_name, self.steps)

    async def get_suggestion(self, step_id, state):
        pip, db, current_steps = self.pipulate, self.db, self.steps
        step_obj = next((s for s in current_steps if s.id == step_id), None)
        if not step_obj or not step_obj.transform: return ''

        current_step_index = self.steps_indices.get(step_id)
        if current_step_index is None or current_step_index == 0: return ''

        prev_step_obj = current_steps[current_step_index - 1]
        prev_data = pip.get_step_data(db.get('pipeline_id', 'unknown'), prev_step_obj.id, {})
        prev_value = prev_data.get(prev_step_obj.done, '')

        return step_obj.transform(prev_value) if prev_value and callable(step_obj.transform) else ''

    async def handle_revert(self, request):
        pip, db, app_name = (self.pipulate, self.db, self.APP_NAME)
        current_steps_to_pass_helpers = self.steps # Use self.steps which includes 'finalize'
        form = await request.form()
        step_id_to_revert_to = form.get('step_id')
        pipeline_id = db.get('pipeline_id', 'unknown')

        if not step_id_to_revert_to:
            return P('Error: No step specified for revert.', style=pip.get_style('error'))

        await pip.clear_steps_from(pipeline_id, step_id_to_revert_to, current_steps_to_pass_helpers)
        state = pip.read_state(pipeline_id)
        state['_revert_target'] = step_id_to_revert_to
        pip.write_state(pipeline_id, state)

        message = await pip.get_state_message(pipeline_id, current_steps_to_pass_helpers, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        return pip.run_all_cells(app_name, current_steps_to_pass_helpers)

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
    # --- END_STEP_BUNDLE: step_01 ---

    # --- STEP_METHODS_INSERTION_POINT ---
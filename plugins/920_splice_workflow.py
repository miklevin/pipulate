import asyncio
from collections import namedtuple
from datetime import datetime

from fasthtml.common import *
from loguru import logger

ROLES = ['Components']
'\nPipulate Workflow Template\nA guide for creating multi-step workflows with proper chain reaction behavior.\n'
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class SpliceWorkflow:
    """
    Splice Workflow Template

    A demonstration workflow showing how to extend from a simple single-step workflow
    (like 70_blank_workflow.py) to a multi-step workflow with proper HTMX chain reactions.

    ## Critical Chain Reaction Pattern

    Pipulate workflows use an explicit HTMX triggering pattern where:

    1. Each step must explicitly trigger the next step in the sequence when completed
    2. This is done by returning a div with the next step's ID and hx_trigger="load"
    3. Removing or altering this pattern will break the workflow progression

    ## Steps Progression Mechanism:

    1. init(): Creates placeholder for step_01 with hx_trigger="load"
    2. step_01(): Loads and either:
       - If incomplete: Shows the input form
       - If complete: Shows completion state AND explicitly triggers step_02
    3. step_01_submit(): Processes data and returns a view that:
       - Shows the completion state for step_01
       - EXPLICITLY triggers step_02 with <Div id="step_02" hx_get="/app/step_02" hx_trigger="load">
    4. Each subsequent step follows the same pattern
    5. The last step triggers the finalize step

    This explicit triggering is more reliable than depending on HTMX event bubbling.
    """
    APP_NAME = 'splice'
    DISPLAY_NAME = 'Splice Workflow'
    ENDPOINT_MESSAGE = 'This is a splice workflow template. Enter an ID to start or resume your workflow.'
    TRAINING_PROMPT = 'You are an expert workflow developer. Your task is to implement a multi-step workflow with proper chain reaction behavior using HTMX.\n\nKey requirements:\n1. Each step must explicitly trigger the next step in sequence when completed\n2. Use div elements with hx_trigger="load" to trigger next steps\n3. Follow the pattern of showing completion state AND triggering next step\n4. Maintain explicit triggering rather than relying on event bubbling\n\nThe workflow should:\n- Initialize with a placeholder for step_01\n- Process each step\'s data appropriately\n- Show completion states\n- Trigger subsequent steps explicitly\n- Handle the finalization process\n\nRemember to:\n- Keep the chain reaction pattern intact\n- Use proper error handling\n- Maintain clear step progression\n- Follow HTMX best practices for workflow implementation'

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
        steps = [Step(id='step_01', done='placeholder', show='Step 1 Placeholder', refill=False), Step(id='step_02', done='placeholder', show='Step 2 Placeholder', refill=False), Step(id='step_03', done='placeholder', show='Step 3 Placeholder', refill=False)]
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
        """Handles the key submission, initializes state, and renders the step UI placeholders.

        CRITICAL: This method starts the chain reaction by triggering the first step.
        DO NOT modify the structure that adds the first step with hx_trigger="load".
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
        return pip.run_all_cells(app_name, steps)

    async def finalize(self, request):
        """Handles GET request to show Finalize button and POST request to lock the workflow.

        CRITICAL: This method MUST:
        1. Check if all steps are complete and show the finalize button if so
        2. Process finalization by locking the workflow
        3. Handle the finalized state display

        DO NOT modify this method's structure when extending a workflow.
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
            return P('Error: No step specified', style=self.pipulate.get_style('error'))
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        state = pip.read_state(pipeline_id)
        state['_revert_target'] = step_id
        pip.write_state(pipeline_id, state)
        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        await self.message_queue.add(pip, f'Reverted to {step_id}. All subsequent data has been cleared.', verbatim=True)
        return pip.run_all_cells(app_name, steps)

    async def step_01(self, request):
        """Handles GET request for Step 1.

        STEP PATTERN: Each step_XX method follows this pattern:
        1. Check if workflow is finalized -> Show locked state
        2. Check if step is complete -> Show completion with trigger to next step
        3. Otherwise -> Show input form

        CRITICAL: When step is complete, return a div that EXPLICITLY triggers the next step
        with <Div id="next_step_id" hx_get="/app_name/next_step_id" hx_trigger="load">

        LLM CONTEXT PATTERN:
        Keep the LLM informed about the step's state using pip.append_to_history():
        1. Finalized state: [WIDGET CONTENT] with (Finalized) marker
        2. Completed state: [WIDGET CONTENT] with (Completed) marker
        3. Input form state: [WIDGET STATE] showing form display
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        placeholder_value = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and placeholder_value:
            pip.append_to_history(f'[WIDGET CONTENT] {step.show} (Finalized):\n{placeholder_value}')
            return Div(Card(H3(f'🔒 {step.show}: Completed')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif placeholder_value and state.get('_revert_target') != step_id:
            pip.append_to_history(f'[WIDGET CONTENT] {step.show} (Completed):\n{placeholder_value}')
            return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: Complete', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        else:
            pip.append_to_history(f'[WIDGET STATE] {step.show}: Showing input form')
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            return Div(Card(H3(f'{step.show}'), P('This is a placeholder step. Click Proceed to continue to the next step.'), Form(Button('Next ▸', type='submit', cls='primary'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')), Div(id=next_step_id), id=step_id)

    async def step_01_submit(self, request):
        """Process the submission for Step 1.

        STEP PATTERN: Each step_XX_submit method follows this pattern:
        1. Process and validate form data
        2. Store state data with pip.set_step_data()
        3. Return completion view WITH explicit trigger to next step

        CRITICAL: The return MUST include:
        1. A Div with id="step_id" (preserve the original ID)
        2. A Div that explicitly triggers the next step with hx_trigger="load"

        LLM CONTEXT PATTERN:
        Keep the LLM informed about:
        1. The submitted content: [WIDGET CONTENT]
        2. The step completion: [WIDGET STATE]
        Use pip.append_to_history() to avoid cluttering the chat interface.
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        placeholder_value = 'completed'
        await pip.set_step_data(pipeline_id, step_id, placeholder_value, steps)
        pip.append_to_history(f'[WIDGET CONTENT] {step.show}:\n{placeholder_value}')
        pip.append_to_history(f'[WIDGET STATE] {step.show}: Step completed')
        await self.message_queue.add(pip, f'{step.show} complete.', verbatim=True)
        return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: Complete', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)

    async def step_02(self, request):
        """Handles GET request for Step 2.

        COPY THIS PATTERN: When adding new steps, follow this exact structure to maintain
        the chain reaction. The critical elements are:

        1. Computing the proper next_step_id
        2. Including the trigger to next step in completed states
        3. Maintaining the step_id on the outer div
        4. Keeping the LLM informed about widget state and content
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        placeholder_value = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and placeholder_value:
            pip.append_to_history(f'[WIDGET CONTENT] {step.show} (Finalized):\n{placeholder_value}')
            return Div(Card(H3(f'🔒 {step.show}: Completed')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif placeholder_value and state.get('_revert_target') != step_id:
            pip.append_to_history(f'[WIDGET CONTENT] {step.show} (Completed):\n{placeholder_value}')
            return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: Complete', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        else:
            pip.append_to_history(f'[WIDGET STATE] {step.show}: Showing input form')
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            return Div(Card(H3(f'{step.show}'), P('This is a placeholder step. Click Proceed to continue to the next step.'), Form(Button('Next ▸', type='submit', cls='primary'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')), Div(id=next_step_id), id=step_id)

    async def step_02_submit(self, request):
        """Process the submission for Step 2.

        COPY THIS PATTERN: When adding steps, follow this same structure with:
        1. Correct step_id and next_step_id calculation
        2. Data processing appropriate to the step
        3. Explicit trigger to the next step
        4. LLM context updates for content and state
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        placeholder_value = 'completed'
        await pip.set_step_data(pipeline_id, step_id, placeholder_value, steps)
        pip.append_to_history(f'[WIDGET CONTENT] {step.show}:\n{placeholder_value}')
        pip.append_to_history(f'[WIDGET STATE] {step.show}: Step completed')
        await self.message_queue.add(pip, f'{step.show} complete.', verbatim=True)
        return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: Complete', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)

    async def step_03(self, request):
        """Handles GET request for Step 3.

        SPLICING GUIDE: This shows how to add a third step following the exact same pattern.

        CRITICAL PATTERN:
        1. Each step computes the correct next_step_id (or 'finalize' if last step)
        2. Completed steps explicitly trigger the next step with hx_trigger="load"
        3. Input forms target the current step's container for proper replacement
        4. LLM context is maintained through all step states
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_03'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        placeholder_value = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and placeholder_value:
            pip.append_to_history(f'[WIDGET CONTENT] {step.show} (Finalized):\n{placeholder_value}')
            return Div(Card(H3(f'🔒 {step.show}: Completed')), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif placeholder_value and state.get('_revert_target') != step_id:
            pip.append_to_history(f'[WIDGET CONTENT] {step.show} (Completed):\n{placeholder_value}')
            return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: Complete', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        else:
            pip.append_to_history(f'[WIDGET STATE] {step.show}: Showing input form')
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            return Div(Card(H3(f'{step.show}'), P('This is a placeholder step. Click Proceed to continue to the next step.'), Form(Button('Next ▸', type='submit', cls='primary'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}')), Div(id=next_step_id), id=step_id)

    async def step_03_submit(self, request):
        """Process the submission for Step 3.

        TRANSITION TO FINALIZE:
        This step demonstrates the transition to the finalize step.
        The pattern is identical - the last step triggers finalize just like
        any other step would trigger the next step in sequence.

        LLM CONTEXT:
        Even in the final step, maintain consistent LLM context updates to
        ensure the LLM understands the complete workflow state.
        """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_03'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        placeholder_value = 'completed'
        await pip.set_step_data(pipeline_id, step_id, placeholder_value, steps)
        pip.append_to_history(f'[WIDGET CONTENT] {step.show}:\n{placeholder_value}')
        pip.append_to_history(f'[WIDGET STATE] {step.show}: Final step completed')
        await self.message_queue.add(pip, f'{step.show} complete.', verbatim=True)
        return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: Complete', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)

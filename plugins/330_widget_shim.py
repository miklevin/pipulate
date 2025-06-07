import asyncio
from collections import namedtuple
from datetime import datetime

from fasthtml.common import *
from loguru import logger

ROLES = ['Developer']  # Defines which user roles can see this plugin

"""
Pipulate Workflow Template
A minimal starter template for creating step-based Pipulate workflows.

RULE NAVIGATION GUIDE:
--------------------
1. Core Widget Patterns:
   - See: patterns/workflow-patterns.mdc
   - Key sections: "Common Widget Patterns", "Widget State Management"
   - Critical for understanding the immutable chain reaction pattern

2. Implementation Guidelines:
   - See: implementation/implementation-workflow.mdc
   - Focus on: "Widget Implementation Steps", "Widget Testing Checklist"
   - Essential for maintaining workflow integrity

3. Common Pitfalls:
   - See: patterns/workflow-patterns.mdc
   - Review: "Common Widget Pitfalls", "Recovery Process"
   - Critical for avoiding state management issues

4. Widget Design Philosophy:
   - See: philosophy/philosophy-core.mdc
   - Key concepts: "State Management", "UI Construction"
   - Important for maintaining consistent patterns

5. Recovery Patterns:
   - See: patterns/workflow-patterns.mdc
   - Focus on: "Recovery Process", "Prevention Guidelines"
   - Essential for handling workflow breaks

CONVERSION POINTS:
----------------
When converting this template to a new widget:
1. CUSTOMIZE_STEP_DEFINITION: Change 'done' field to specific data field name
2. CUSTOMIZE_FORM: Replace the Proceed button with specific form elements
3. CUSTOMIZE_DISPLAY: Update the finalized state display for your widget
4. CUSTOMIZE_COMPLETE: Enhance the completion state with widget display

CRITICAL ELEMENTS TO PRESERVE:
----------------------------
- Chain reaction with next_step_id
- Finalization state handling pattern
- Revert control mechanism
- Overall Div structure and ID patterns
- LLM context updates for widget content
"""

Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class WidgetDesigner:
    """
    Widget Shim Workflow

    A focused environment for designing and testing new widgets in isolation.
    """
    APP_NAME = 'design_widget'
    DISPLAY_NAME = 'Widget Shim 🫙'
    ENDPOINT_MESSAGE = 'Welcome to the Widget Shim! This is a focused environment for designing and testing new widgets in isolation. Use this space to prototype and refine your widget designs without distractions.'
    TRAINING_PROMPT = 'This is a specialized workflow for designing and testing widgets in isolation. It provides a clean environment to focus on widget development without the complexity of a full workflow implementation.'

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
        steps = [Step(id='step_01', done='placeholder', show='Step 1 Placeholder', refill=False)]
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
            return P('Error: No step specified', style=self.pipulate.get_style('error'))
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        state = pip.read_state(pipeline_id)
        state['_revert_target'] = step_id
        pip.write_state(pipeline_id, state)
        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        return pip.run_all_cells(app_name, steps)

    async def step_01(self, request):
        """Handles GET request for placeholder Step 1.

        Widget Conversion Points:
        1. CUSTOMIZE_STEP_DEFINITION: Change 'done' field to specific data field name
        2. CUSTOMIZE_FORM: Replace the Proceed button with specific form elements
        3. CUSTOMIZE_DISPLAY: Update the finalized state display for your widget
        4. CUSTOMIZE_COMPLETE: Enhance the completion state with widget display

        Critical Elements to Preserve:
        - Chain reaction with next_step_id
        - Finalization state handling pattern
        - Revert control mechanism
        - Overall Div structure and ID patterns
        - LLM context updates for widget content
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
        """Process the submission for placeholder Step 1.

        Chain Reaction Pattern:
        When a step completes, it MUST explicitly trigger the next step by including
        a div for the next step with hx-trigger="load". While this may seem redundant,
        it is more reliable than depending on HTMX event bubbling.

        LLM Context Pattern:
        Always keep the LLM informed about:
        1. What was submitted (widget content)
        2. Any transformations or processing applied
        3. The final state of the widget
        Use pip.append_to_history() for this to avoid cluttering the chat interface.
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

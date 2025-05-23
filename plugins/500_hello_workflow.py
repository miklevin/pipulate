from collections import namedtuple
from datetime import datetime

from fasthtml.common import *
from loguru import logger

ROLES = ['Core']

"""
Pipulate Workflow Template (Hello World Example)

This file serves as a starting point for creating linear, step-by-step Pipulate Workflows.
It demonstrates the core patterns and best practices for workflow development.

--- The Chain Reaction Pattern ---
Pipulate workflows use HTMX's chain reaction pattern to create a "Run All Cells" experience
similar to Jupyter Notebooks. Each step automatically triggers the next step's loading
until it encounters a step requiring user input.

The chain reaction is maintained through three distinct phases in each step:

1. Finalize Phase: Shows locked view of completed step, chains to next step
2. Revert Phase: Shows completed view with revert option, chains to next step
3. Get Input Phase: Shows input form, waits for user submission

The chain is maintained by including a Div with hx_trigger="load" in the response:

```python
# Explicit method:
return Div(
    Card(...),  # Current step content
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id
)

# Which can also be expressed using the convenience method:
return pip.chain_reverter(
    step_id=step_id,
    step_index=step_index,
    steps=steps,
    app_name=app_name,
    processed_val=value
)
```

Both methods achieve the same result - they create a UI showing the completed step and trigger loading of the next step. The `chain_reverter` method is preferred as it ensures consistent styling and behavior across all workflows.

--- Step Handler Pattern ---
Each step has a GET handler (`step_XX`) and POST handler (`step_XX_submit`):

1. GET Handler (`step_XX`):
   - Must implement all three phases (Finalize, Revert, Input)
   - Returns appropriate view based on state
   - Maintains chain reaction with hx_trigger="load"

2. POST Handler (`step_XX_submit`):
   - Processes form submission
   - Updates state
   - Returns completed view with next step trigger

--- State Management ---
Workflow state is managed through:

1. Step Data:
   - Each step stores its primary data in state[step_id][step.done]
   - Use pip.set_step_data() to save step values
   - Use pip.get_step_data() to read step values

2. Step Completion:
   - Track completed steps in state
   - Check completion with step_id in state
   - Handle reverting with state.get('_revert_target')

3. Finalization:
   - Lock workflow with state['finalize']['finalized']
   - Prevent modifications when finalized
   - Allow unfinalizing to make changes

--- Helper Methods ---
The Pipulate framework provides helper methods for common tasks:

1. UI Components:
   - pip.display_revert_header(): Standard revert header
   - pip.display_revert_widget(): For visual components
   - pip.chain_reverter(): Combines revert header with next step trigger

2. State Management:
   - pip.set_step_data(): Save step value and update completion
   - pip.get_step_data(): Read step data
   - pip.read_state(): Get entire workflow state
   - pip.write_state(): Save entire workflow state

3. Validation:
   - pip.validate_step_input(): Validate user input
   - pip.check_finalize_needed(): Check if workflow can be finalized

--- Best Practices ---
1. Always include hx_trigger="load" for chain progression
2. Use helper methods for consistent UI and state management
3. Handle all three phases in GET handlers
4. Validate input in POST handlers
5. Update state atomically
6. Provide clear user feedback
7. Handle errors gracefully
"""

Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class HelloFlow:
    """
    Hello World Workflow Example

    Demonstrates a simple two-step workflow asking for a name and generating a greeting.
    This example shows the core patterns and best practices for Pipulate workflows.

    Key Concepts:
    1. Chain Reaction Pattern: Each step automatically triggers the next
    2. Step Handler Pattern: GET/POST handlers with three phases
    3. State Management: Tracking completion and handling reverts
    4. UI Components: Using helper methods for consistent UI
    """
    APP_NAME = 'hello'
    DISPLAY_NAME = 'Hello Workflow'
    ENDPOINT_MESSAGE = 'Start a new Workflow. Keys are auto: PROFILE_Name-APP_Name-XX (just press Enter)...'
    TRAINING_PROMPT = 'hello_workflow.md'

    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
        """
        Initialize the workflow, define steps, and register routes.

        The steps list defines the workflow sequence:
        - step_01: Collect user's name
        - step_02: Generate greeting using name
        - finalize: Lock workflow when complete
        """
        self.app = app
        self.app_name = app_name
        self.pipulate = pipulate
        self.pipeline = pipeline
        self.steps_indices = {}
        self.db = db
        pip = self.pipulate
        self.message_queue = pip.message_queue

        # Define workflow steps
        steps = [
            Step(
                id='step_01',
                done='name',
                show='Your Name',
                refill=True  # Pre-fill on revert
            ),
            Step(
                id='step_02',
                done='greeting',
                show='Hello Message',
                refill=False,
                transform=lambda name: f'Hello {name}!'  # Transform previous step's output
            )
        ]

        # Register standard workflow routes
        routes = [
            (f'/{app_name}', self.landing),
            (f'/{app_name}/init', self.init, ['POST']),
            (f'/{app_name}/revert', self.handle_revert, ['POST']),
            (f'/{app_name}/finalize', self.finalize, ['GET', 'POST']),
            (f'/{app_name}/unfinalize', self.unfinalize, ['POST'])
        ]

        # Register step-specific routes
        self.steps = steps
        for step in steps:
            step_id = step.id
            routes.append((f'/{app_name}/{step_id}', getattr(self, step_id)))
            routes.append((f'/{app_name}/{step_id}_submit', getattr(self, f'{step_id}_submit'), ['POST']))

        # Register all routes
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ['GET']
            app.route(path, methods=method_list)(handler)

        # Define step messages for user feedback
        self.step_messages = {
            'finalize': {
                'ready': 'All steps complete. Ready to finalize workflow.',
                'complete': f'Workflow finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes.'
            }
        }
        for step in steps:
            self.step_messages[step.id] = {
                'input': f'{pip.fmt(step.id)}: Please enter {step.show}.',
                'complete': f'{step.show} complete. Continue to next step.'
            }

        # Add finalize step and create step indices
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

    async def landing(self, request):
        """ Renders the initial landing page with the key input form. """
        pip, pipeline, steps, app_name = (self.pipulate, self.pipeline, self.steps, self.app_name)
        context = pip.get_plugin_context(self)
        title = f'{self.DISPLAY_NAME or app_name.title()}'
        full_key, prefix, user_part = pip.generate_pipeline_key(self)
        default_value = full_key
        pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in pipeline() if record.pkey.startswith(prefix)]
        datalist_options = [f"{prefix}{record_key.replace(prefix, '')}" for record_key in matching_records]
        return Container(Card(H2(title), P(self.ENDPOINT_MESSAGE, style=pip.get_style('muted')), Form(pip.wrap_with_inline_button(Input(placeholder='Existing or new 🗝 here (Enter for auto)', name='pipeline_id', list='pipeline-ids', type='search', required=False, autofocus=True, value=default_value, _onfocus='this.setSelectionRange(this.value.length, this.value.length)', cls='contrast'), button_label=f'Enter 🔑', button_class='secondary'), pip.update_datalist('pipeline-ids', options=datalist_options if datalist_options else None), hx_post=f'/{app_name}/init', hx_target=f'#{app_name}-container')), Div(id=f'{app_name}-container'))

    async def init(self, request):
        """ Handles the key submission, initializes state, and renders the step UI placeholders. """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        form = await request.form()
        user_input = form.get('pipeline_id', '').strip()
        if not user_input:
            from starlette.responses import Response
            response = Response('')
            response.headers['HX-Refresh'] = 'true'
            return response
        context = pip.get_plugin_context(self)
        plugin_name = context['plugin_name'] or app_name
        profile_name = context['profile_name'] or 'default'
        profile_part = profile_name.replace(' ', '_')
        plugin_part = plugin_name.replace(' ', '_')
        expected_prefix = f'{profile_part}-{plugin_part}-'
        if user_input.startswith(expected_prefix):
            pipeline_id = user_input
        else:
            _, prefix, user_provided_id = pip.generate_pipeline_key(self, user_input)
            pipeline_id = f'{prefix}{user_provided_id}'
        db['pipeline_id'] = pipeline_id
        logger.debug(f'Using pipeline ID: {pipeline_id}')
        state, error = pip.initialize_if_missing(pipeline_id, {'app_name': app_name})
        if error:
            return error
        all_steps_complete = all((step.id in state and step.done in state[step.id] for step in steps[:-1]))
        is_finalized = 'finalize' in state and 'finalized' in state['finalize']
        await self.message_queue.add(pip, f'Workflow ID: {pipeline_id}', verbatim=True, spaces_before=0)
        await self.message_queue.add(pip, f"Return later by selecting '{pipeline_id}' from the dropdown.", verbatim=True, spaces_before=0)
        if all_steps_complete:
            status_msg = f'Workflow is complete and finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes.' if is_finalized else 'Workflow is complete but not finalized. Press Finalize to lock your data.'
            await self.message_queue.add(pip, status_msg, verbatim=True)
        elif not any((step.id in state for step in self.steps)):
            await self.message_queue.add(pip, 'Please complete each step in sequence. Your progress will be saved automatically.', verbatim=True)
        parsed = pip.parse_pipeline_key(pipeline_id)
        prefix = f"{parsed['profile_part']}-{parsed['plugin_part']}-"
        self.pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in self.pipeline() if record.pkey.startswith(prefix)]
        if pipeline_id not in matching_records:
            matching_records.append(pipeline_id)
        updated_datalist = pip.update_datalist('pipeline-ids', options=matching_records)
        return pip.rebuild(app_name, steps)

    async def finalize(self, request):
        """ Handles GET request to show Finalize button and POST request to lock the workflow. """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        pipeline_id = db.get('pipeline_id', 'unknown')
        finalize_step = steps[-1]
        finalize_data = pip.get_step_data(pipeline_id, finalize_step.id, {})
        if request.method == 'GET':
            if finalize_step.done in finalize_data:
                return Card(H3('Workflow is locked.'), P('Each step can do ANYTHING. With this you can change the world — or at least show how to in a workflow.', style=pip.get_style('muted')), Form(Button(pip.UNLOCK_BUTTON_LABEL, type='submit', cls='secondary outline'), hx_post=f'/{app_name}/unfinalize', hx_target=f'#{app_name}-container', hx_swap='outerHTML'), id=finalize_step.id)
            else:
                all_steps_complete = all((pip.get_step_data(pipeline_id, step.id, {}).get(step.done) for step in steps[:-1]))
                if all_steps_complete:
                    return Card(H3('All steps complete. Finalize?'), P('At the end they get locked. Or you can go back.', style=pip.get_style('muted')), Form(Button('Finalize 🔒', type='submit', cls='primary'), hx_post=f'/{app_name}/finalize', hx_target=f'#{app_name}-container', hx_swap='outerHTML'), id=finalize_step.id)
                else:
                    return Div(id=finalize_step.id)
        else:
            await pip.finalize_workflow(pipeline_id)
            await self.message_queue.add(pip, self.step_messages['finalize']['complete'], verbatim=True)
            return pip.rebuild(app_name, steps)

    async def unfinalize(self, request):
        """ Handles POST request to unlock the workflow. """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        pipeline_id = db.get('pipeline_id', 'unknown')
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, 'Workflow unfinalized! You can now revert to any step and make changes.', verbatim=True)
        return pip.rebuild(app_name, steps)

    async def get_suggestion(self, step_id, state):
        """ Gets a suggested input value for a step, often using the previous step's transformed output. """
        pip, db, steps = (self.pipulate, self.db, self.steps)
        step = next((s for s in steps if s.id == step_id), None)
        if not step or not step.transform:
            return ''
        prev_index = self.steps_indices[step_id] - 1
        if prev_index < 0:
            return ''
        prev_step = steps[prev_index]
        prev_data = pip.get_step_data(db['pipeline_id'], prev_step.id, {})
        prev_word = prev_data.get(prev_step.done, '')
        return step.transform(prev_word) if prev_word else ''

    async def handle_revert(self, request):
        """ Handles POST request to revert to a previous step, clearing subsequent step data. """
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

    async def step_01(self, request):
        """
        Handles GET request for Step 1: Displays input form or completed value.

        Implements the three phases:
        1. Finalize Phase: Shows locked view if workflow is finalized
        2. Revert Phase: Shows completed view with revert option
        3. Input Phase: Shows input form for new/updated value
        """
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

        # Phase 1: Finalize Phase - Show locked view
        if 'finalized' in finalize_data:
            locked_msg = f'🔒 Your name is set to: {user_val}'
            await self.message_queue.add(pip, locked_msg, verbatim=True)
            return Div(
                Card(H3(f'🔒 {step.show}: {user_val}')),
                Div(id=next_step_id, hx_get=f'/{self.app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )

        # Phase 2: Revert Phase - Show completed view with revert option
        elif user_val and state.get('_revert_target') != step_id:
            completed_msg = f'Step 1 is complete. You entered: {user_val}'
            await self.message_queue.add(pip, completed_msg, verbatim=True)
            return Div(
                pip.display_revert_header(
                    step_id=step_id,
                    app_name=app_name,
                    message=f'{step.show}: {user_val}',
                    steps=steps
                ),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load')
            )

        # Phase 3: Input Phase - Show input form
        else:
            display_value = user_val if step.refill and user_val else await self.get_suggestion(step_id, state)
            form_msg = 'Showing name input form. No name has been entered yet.'
            await self.message_queue.add(pip, form_msg, verbatim=True)
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            explanation = "Workflows are like Python Notebooks with no code. Let's collect some data..."
            await self.message_queue.add(pip, explanation, verbatim=True)
            return Div(
                Card(
                    H3(f'{pip.fmt(step.id)}: Enter {step.show}'),
                    P(explanation, style=pip.get_style('muted')),
                    Form(
                        pip.wrap_with_inline_button(
                            Input(
                                type='text',
                                name=step.done,
                                value=display_value,
                                placeholder=f'Enter {step.show}',
                                required=True,
                                autofocus=True,
                                _onfocus='this.setSelectionRange(this.value.length, this.value.length)'
                            ),
                            button_label='Next ▸'
                        ),
                        hx_post=f'/{app_name}/{step.id}_submit',
                        hx_target=f'#{step.id}'
                    )
                ),
                Div(id=next_step_id),  # Empty placeholder for next step
                id=step_id
            )

    async def step_01_submit(self, request):
        """
        Handle the submission of step 01.

        This method:
        1. Gets the user's input from the form
        2. Validates the input
        3. Updates the workflow state
        4. Returns a UI showing the completed step and triggering the next step
        """
        pipeline_id = self.db["pipeline_id"]
        form = await request.form()
        user_val = form.get(self.steps[0].done, "")

        # Validate input
        if not user_val:
            return P('Error: Please enter a value', style=self.pipulate.ERROR_STYLE)

        # Update state
        await self.pipulate.set_step_data(pipeline_id, "step_01", user_val, self.steps)

        # Update LLM context
        self.pipulate.append_to_history(f"[WIDGET CONTENT] {self.steps[0].show}:\n{user_val}")

        # Return completed view with next step trigger using chain_reverter
        return self.pipulate.chain_reverter("step_01", 0, self.steps, self.app_name, user_val)

    async def step_02(self, request):
        """ Handles GET request for Step 2: Displays input form or completed value. """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data:
            return Div(Card(H3(f'🔒 {step.show}: {user_val}')), Div(id=next_step_id, hx_get=f'/{self.app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        elif user_val and state.get('_revert_target') != step_id:
            return Div(pip.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: {user_val}', steps=steps), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'))
        else:
            display_value = user_val if step.refill and user_val else await self.get_suggestion(step_id, state)
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            return Div(Card(H3(f'{pip.fmt(step.id)}: Enter {step.show}'), P("That's it! Workflows just compel you from one step to the Next ▸", style=pip.get_style('muted')), Form(pip.wrap_with_inline_button(Input(type='text', name=step.done, value=display_value, placeholder=f'{step.show} (generated)', required=True, autofocus=True, _onfocus='this.setSelectionRange(this.value.length, this.value.length)'), button_label='Next ▸'), hx_post=f'/{app_name}/{step.id}_submit', hx_target=f'#{step.id}')), Div(id=next_step_id), id=step.id)

    async def step_02_submit(self, request):
        """ Handles POST submission for Step 2: Validates, saves state, returns navigation. """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get('pipeline_id', 'unknown')
        if step.done == 'finalized':
            return await pip.handle_finalized_step(pipeline_id, step_id, steps, app_name, self)
        form = await request.form()
        user_val = form.get(step.done, '')
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            return error_component
        processed_val = user_val
        await pip.set_step_data(pipeline_id, step_id, processed_val, steps)
        await self.message_queue.add(pip, f'{step.show}: {processed_val}', verbatim=True)
        if pip.check_finalize_needed(step_index, steps):
            await self.message_queue.add(pip, self.step_messages['finalize']['ready'], verbatim=True)
        return self.pipulate.chain_reverter(
            step_id=step_id,
            step_index=step_index,
            steps=steps,
            app_name=app_name,
            processed_val=processed_val
        )

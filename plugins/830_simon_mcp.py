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

# Import MODEL constant from server
from server import MODEL

class SimonSaysMcpWidget:
    """
    Simon Says MCP Workflow
    Educational tool for teaching users how to craft prompts that will make the LLM generate MCP tool calls.
    This workflow demonstrates the complete MCP interaction loop with full observability.
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
            Step(id='step_01', done='mcp_interaction', show='Simon Says Prompt', refill=True),
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
        pipeline_id = db.get('pipeline_id', 'unknown')
        finalize_step_obj = next(s for s in self.steps if s.id == 'finalize')
        finalize_data = pip.get_step_data(pipeline_id, finalize_step_obj.id, {})
        state = pip.read_state(pipeline_id)

        if request.method == 'GET':
            # STEP PHASE: Finalize (already finalized)
            if finalize_step_obj.done in finalize_data:
                return Card(
                    H3(self.ui['MESSAGES']['WORKFLOW_LOCKED']), 
                    Form(
                        Button(self.ui['BUTTON_LABELS']['UNLOCK'], type='submit', cls=self.ui['BUTTON_STYLES']['OUTLINE']), 
                        hx_post=f'/{app_name}/unfinalize', 
                        hx_target=f'#{app_name}-container'
                    ), 
                    id=finalize_step_obj.id
                )
            
            # Check if all data steps are complete  
            data_steps = [step for step in self.steps if step.id != 'finalize']
            all_data_steps_complete = True
            
            for step in data_steps:
                step_data = pip.get_step_data(pipeline_id, step.id, {})
                if not (step.done in step_data and step_data.get(step.done)):
                    all_data_steps_complete = False
                    break
            
            # STEP PHASE: Get Input (show finalize button when all steps complete)
            if all_data_steps_complete:
                return Card(
                    H3(self.ui['MESSAGES']['FINALIZE_QUESTION']), 
                    P(self.ui['MESSAGES']['FINALIZE_HELP'], cls='text-secondary'), 
                    Form(
                        Button(self.ui['BUTTON_LABELS']['FINALIZE'], type='submit', cls=self.ui['BUTTON_STYLES']['PRIMARY']), 
                        hx_post=f'/{app_name}/finalize', 
                        hx_target=f'#{app_name}-container'
                    ), 
                    id=finalize_step_obj.id
                )
            else:
                # Still waiting for steps to complete - show progress
                return Card(
                    H3("🔄 Workflow In Progress"),
                    P("Complete all steps to finalize this workflow"),
                    id=finalize_step_obj.id
                )
        
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
        """ Handles GET request for Step 1: Displays the Simon Says textarea form. """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id] # Ensure we have the index
        step = self.steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index + 1 < len(steps) else 'finalize'

        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        interaction_result = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})

        # Phase 1: Finalized View
        if 'finalized' in finalize_data and interaction_result:
            locked_content = pip.finalized_content(
                message=f"🔒 {step.show}: Interaction Complete",
                content=Pre(interaction_result, cls='code-block-container')
            )
            next_step_trigger = Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load')
            return Div(locked_content, next_step_trigger, id=step_id)

        # Phase 2: Revert View
        elif interaction_result and state.get('_revert_target') != step_id:
            revert_widget = pip.display_revert_widget(
                step_id=step_id, app_name=app_name, message=f"{step.show}: Interaction Log",
                widget=Pre(interaction_result, cls='code-block-container'),
                steps=steps
            )
            next_step_trigger = Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load')
            return Div(revert_widget, next_step_trigger, id=step_id)

        # Phase 3: Get Input View
        else:
            await self.message_queue.add(pip, "Let's play Simon Says with the LLM. Edit the prompt below and see if you can get it to make a tool call!", verbatim=True)
            
            simon_says_prompt = """You are a helpful assistant with a tool that can fetch random cat facts. To use the tool, you MUST stop generating conversational text and output an MCP request block.

Here is the only tool you have available:
- Tool Name: `get_cat_fact`
- Description: Fetches a random cat fact from an external API.
- Parameters: None

The user wants to learn something interesting about cats. Use the `get_cat_fact` tool by generating this EXACT MCP request block:
<mcp-request>
  <tool name="get_cat_fact" />
</mcp-request>

Do not say anything else. Just output the exact MCP block above."""
            display_value = interaction_result if step.refill and interaction_result else simon_says_prompt
            form_content = Form(
                Textarea(
                    display_value,
                    name="simon_says_prompt",
                    required=True,
                    style='min-height: 300px; width: 100%; font-family: monospace; white-space: pre; overflow-wrap: normal; overflow-x: auto;'
                ),
                Button('Play Simon Says ▸', type='submit', cls='primary', style='margin-top: 1rem;'),
                hx_post=f'/{app_name}/{step_id}_submit',
                hx_target=f'#{step_id}'
            )
            
            # This phase correctly breaks the chain, waiting for user input.
            return Div(
                Card(H3(f'🎪 {step.show}'), form_content),
                id=step_id
            )

    async def step_01_submit(self, request):
        """Process the 'Simon Says' prompt and trigger the LLM interaction."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]

        try:
            form = await request.form()
            prompt_text = form.get('simon_says_prompt', '').strip()
            
            if not prompt_text:
                error_msg = 'Please provide a prompt for the LLM interaction.'
                logger.error(f"Error in {app_name}/{step_id}: {error_msg}")
                return P(error_msg, style=pip.get_style('error'))

            # Show immediate feedback
            await pip.stream(f'🤖 Okay, Simon Says... I\'m sending your instructions to the LLM. Let\'s see what happens...', role='system')

            # Prepare messages for LLM interaction
            messages = [
                {'role': 'system', 'content': 'You are a helpful assistant capable of making tool calls when needed.'},
                {'role': 'user', 'content': prompt_text}
            ]

            # Process the LLM interaction through the Pipulate instance
            async for chunk in pip.process_llm_interaction(MODEL, messages):
                await pip.stream(chunk, verbatim=True, role='assistant', simulate_typing=False)

            # Store a summary for the revert state
            interaction_summary = f"--- Simon Says Prompt ---\n{prompt_text}\n\n--- Result ---\nCheck the chat panel and server logs for the detailed interaction and observability report."
            await pip.set_step_data(
                pipeline_id=db.get('pipeline_id', 'unknown'),
                step_id=step_id,
                step_value=interaction_summary,
                steps=steps
            )
            
            # Use chain_reverter to trigger the next step automatically
            return pip.chain_reverter(step_id, step_index, steps, app_name, f"LLM Interaction: '{prompt_text[:40]}...'")

        except Exception as e:
            error_msg = f'Error during MCP interaction processing: {str(e)}'
            logger.error(f"Error in step_01_submit: {error_msg}")
            await pip.stream(f'❌ Error: {error_msg}', role='system')
            return P(error_msg, style=pip.get_style('error'))
    # --- END_STEP_BUNDLE: step_01 ---

    # --- STEP_METHODS_INSERTION_POINT ---
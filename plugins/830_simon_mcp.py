# File: plugins/830_simon_mcp.py
import asyncio
from collections import namedtuple
from datetime import datetime
import json
from fasthtml.common import * # type: ignore
from starlette.responses import RedirectResponse
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
    Simon Says UI Flash Workflow
    Educational tool for teaching users how to craft prompts that will make the LLM flash UI elements for guidance.
    This workflow demonstrates the complete MCP interaction loop with UI element flashing capabilities.
    """
    APP_NAME = 'simon_mcp'
    DISPLAY_NAME = 'Simon Says UI Flash 🎪'
    ENDPOINT_MESSAGE = """Let's teach the LLM to flash UI elements for user guidance. Edit the prompt below to play Simon Says."""
    TRAINING_PROMPT = """This workflow is a game called 'Simon Says UI Flash'. The user will provide a detailed prompt to instruct the LLM on how to formulate MCP requests that flash specific UI elements. Your role is to assist the user in refining these prompts and understanding the results."""

    # --- START_CLASS_ATTRIBUTES_BUNDLE ---
    UI_CONSTANTS = {
        'SHARED': {
            'FONT_SIZE': '0.9rem',
            'FONT_FAMILY': 'monospace',
            'LINE_HEIGHT': '1.5',
            'PADDING': '0.75rem',
            'MIN_HEIGHT': '450px',
            'WIDTH': '100%',
            'WHITE_SPACE': 'pre-wrap',
            'OVERFLOW_WRAP': 'break-word',
            'BORDER_RADIUS': '4px'
        },
        'INPUT_STYLE': {
            'BORDER': '1px solid var(--pico-form-element-border-color)',
            'BACKGROUND_COLOR': 'var(--pico-form-element-background-color)'
        },
        'DISPLAY_STYLE': {
            'BORDER': '1px solid var(--pico-muted-border-color)',
            'BACKGROUND_COLOR': 'var(--pico-card-background-color)',
            'COLOR': 'var(--pico-color)'
        }
    }
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

        # CRITICAL: Auto-key generation pattern - return HX-Refresh for empty keys
        if not user_input_key:
            from starlette.responses import Response
            response = Response('')
            response.headers['HX-Refresh'] = 'true'
            return response

        # Handle user-provided keys
        _, prefix_for_key_gen, _ = pip.generate_pipeline_key(self)
        if user_input_key.startswith(prefix_for_key_gen) and len(user_input_key.split('-')) == 3:
            pipeline_id = user_input_key
        else:
             _, prefix, user_part = pip.generate_pipeline_key(self, user_input_key)
             pipeline_id = f'{prefix}{user_part}'

        db['pipeline_id'] = pipeline_id
        state, error = pip.initialize_if_missing(pipeline_id, {'app_name': internal_app_name})
        if error: return error

        # Skip verbose init messages for cleaner Simon Says demonstration
        pass

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
            # Skip finalize message for cleaner demonstration
            return pip.run_all_cells(app_name, self.steps)

    async def unfinalize(self, request):
        pip, db, app_name = (self.pipulate, self.db, self.APP_NAME)
        pipeline_id = db.get('pipeline_id', 'unknown')
        await pip.unfinalize_workflow(pipeline_id)
        # Skip unfinalize message for cleaner demonstration
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

        # Skip revert state messages for cleaner demonstration
        pass
        return pip.run_all_cells(app_name, current_steps_to_pass_helpers)

    def _get_base_style(self):
        """Generate base style shared by both input and display."""
        shared = self.UI_CONSTANTS['SHARED']
        return (f"min-height: {shared['MIN_HEIGHT']}; "
                f"width: {shared['WIDTH']}; "
                f"font-family: {shared['FONT_FAMILY']}; "
                f"font-size: {shared['FONT_SIZE']}; "
                f"line-height: {shared['LINE_HEIGHT']}; "
                f"padding: {shared['PADDING']}; "
                f"white-space: {shared['WHITE_SPACE']}; "
                f"overflow-wrap: {shared['OVERFLOW_WRAP']}; "
                f"border-radius: {shared['BORDER_RADIUS']}; ")

    def _get_textarea_style(self):
        """Generate textarea input style with form element colors."""
        base = self._get_base_style()
        input_style = self.UI_CONSTANTS['INPUT_STYLE']
        return (base + 
                f"border: {input_style['BORDER']}; "
                f"background-color: {input_style['BACKGROUND_COLOR']};")

    def _get_display_style(self):
        """Generate display style with readable card colors."""
        base = self._get_base_style()
        display_style = self.UI_CONSTANTS['DISPLAY_STYLE']
        return (base + 
                f"border: {display_style['BORDER']}; "
                f"background-color: {display_style['BACKGROUND_COLOR']}; "
                f"color: {display_style['COLOR']};")
                
    def _get_consistent_style(self):
        """Deprecated - use _get_display_style() or _get_textarea_style() instead."""
        return self._get_display_style()

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
                content=Pre(interaction_result, style=self._get_display_style())
            )
            next_step_trigger = Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load')
            return Div(locked_content, next_step_trigger, id=step_id)

        # Phase 2: Revert View
        elif interaction_result and state.get('_revert_target') != step_id:
            revert_widget = pip.display_revert_widget(
                step_id=step_id, app_name=app_name, message=f"{step.show}: Interaction Log",
                widget=Pre(interaction_result, style=self._get_display_style()),
                steps=steps
            )
            next_step_trigger = Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load')
            return Div(revert_widget, next_step_trigger, id=step_id)

        # Phase 3: Get Input View
        else:
            # Keep this message since it's the main instructional content
            await self.message_queue.add(pip, "🎪 Ready to play Simon Says UI Flash! Edit the prompt below to instruct the LLM to flash UI elements.", verbatim=True)
            
            # UI Elements Map for LLM training - based on actual server.py IDs
            ui_elements_map = {
                "navigation": {
                    "profile-id": "Profile dropdown summary - click to open profile selection menu",
                    "profile-dropdown-menu": "Profile dropdown container - shows all available profiles",
                    "app-id": "App dropdown summary - click to open app/workflow selection menu", 
                    "app-dropdown-menu": "App dropdown container - shows available apps/workflows",
                    "nav-plugin-search": "Plugin search input - type to find specific features",
                    "search-results-dropdown": "Search results dropdown - shows matching plugins",
                    "env-id": "Environment selector - switch between development/production modes",
                    "poke-summary": "Settings gear icon - hover to access system settings"
                },
                "chat": {
                    "chat-interface": "Entire chat panel - where conversation happens",
                    "msg-list": "Chat message list - scrollable conversation history",
                    "msg": "Chat input textarea - where users type messages to the LLM",
                    "send-btn": "Send message button - submits chat input to the LLM",
                    "stop-btn": "Stop streaming button - halts LLM responses mid-generation",
                    "input-group": "Chat input container - holds the textarea and buttons"
                },
                "layout": {
                    "nav-group": "Top navigation bar - contains all navigation elements",
                    "grid-left-content": "Left panel - contains the workflow interface",
                    "nav-flyout-panel": "Settings flyout panel - system configuration options",
                    "scroll-to-top-link": "Scroll to top button - returns to top of page"
                },
                "workflow_elements": {
                    "step_01": "First workflow step - usually data input or configuration",
                    "step_02": "Second workflow step - data processing or analysis", 
                    "finalize": "Finalize step - completes and locks the workflow"
                },
                "settings": {
                    "theme-switch-container": "Theme toggle - switch between light and dark modes",
                    "poke-dropdown-menu": "Settings dropdown - system configuration options"
                }
            }
            
            # Optimized UI Flash prompt for guaranteed success
            simon_says_prompt = f"""I need you to flash the chat message list to show the user where their conversation appears. Use this exact tool call:

<mcp-request>
  <tool name="ui_flash_element">
    <params>
      <element_id>msg-list</element_id>
      <message>This is where your conversation with the AI appears!</message>
      <delay>500</delay>
    </params>
  </tool>
</mcp-request>

Output only the MCP block above. Do not add any other text."""

            # Alternative: Cat fact baseline for testing MCP system
            cat_fact_prompt = """I need you to fetch a random cat fact to test the MCP system. Use this exact tool call:

<mcp-request>
  <tool name="get_cat_fact" />
</mcp-request>

Output only the MCP block above. Do not add any other text."""

            # Advanced UI Flash prompt with multiple options
            advanced_ui_prompt = f"""You are a UI guidance assistant. Flash ONE of these key interface elements to help the user:

GUARANTEED WORKING ELEMENTS:
- msg-list (chat conversation area)
- app-id (main app menu)  
- profile-id (profile selector)
- send-btn (chat send button)

Choose ONE element and use this EXACT format:

<mcp-request>
  <tool name="ui_flash_element">
    <params>
      <element_id>msg-list</element_id>
      <message>This is where your conversation appears!</message>
      <delay>500</delay>
    </params>
  </tool>
</mcp-request>

Replace 'msg-list' with your chosen element ID. Output ONLY the MCP block."""

            # Alternative prompt to list all elements first
            list_elements_prompt = """You are a helpful assistant with UI interaction tools. The user wants to see all available UI elements that can be flashed for guidance.

Here are the tools you have available:
- Tool Name: `ui_list_elements` - Lists all available UI elements you can flash
- Tool Name: `ui_flash_element` - Flashes a specific UI element by ID

Use the `ui_list_elements` tool to show all available elements by generating this EXACT MCP request block:

<mcp-request>
  <tool name="ui_list_elements" />
</mcp-request>

Do not say anything else. Just output the exact MCP block above."""

            # Choose which prompt to show based on step data
            step_data = pip.get_step_data(db.get('pipeline_id', 'unknown'), step_id, {})
            prompt_mode = step_data.get('prompt_mode', 'simple_flash')  # simple_flash, cat_fact, advanced_flash, list_elements
            
            if prompt_mode == 'cat_fact':
                display_value = interaction_result if step.refill and interaction_result else cat_fact_prompt
                button_text = 'Get Cat Fact ▸'
                button_style = 'margin-top: 1rem; background-color: var(--pico-color-orange-500);'
            elif prompt_mode == 'advanced_flash':
                display_value = interaction_result if step.refill and interaction_result else advanced_ui_prompt
                button_text = 'Flash UI Element (Advanced) ▸'
                button_style = 'margin-top: 1rem; background-color: var(--pico-color-blue-500);'
            elif prompt_mode == 'list_elements':
                display_value = interaction_result if step.refill and interaction_result else list_elements_prompt
                button_text = 'List UI Elements ▸'
                button_style = 'margin-top: 1rem; background-color: var(--pico-secondary-background);'
            else:  # simple_flash (default)
                display_value = interaction_result if step.refill and interaction_result else simon_says_prompt
                button_text = 'Flash Chat Area ▸'
                button_style = 'margin-top: 1rem;'
            form_content = Form(
                Textarea(
                    display_value,
                    name="simon_says_prompt",
                    required=True,
                    style=self._get_textarea_style()
                ),
                Div(
                    Button(button_text, type='submit', cls='primary', style=button_style, **{'hx-on:click': 'this.setAttribute("aria-busy", "true")'}),
                    Button(
                        '🔄 Switch Mode',
                        type='button',
                        cls='secondary',
                        style='margin-top: 1rem; margin-left: 1rem;',
                        hx_post=f'/{app_name}/{step_id}_toggle',
                        hx_target=f'#{step_id}'
                    ),
                    style='display: flex; align-items: center;'
                ),
                P(f"Current mode: {prompt_mode.replace('_', ' ').title()}", 
                  cls='text-secondary', 
                  style='margin-top: 0.5rem; font-size: 0.9em;'),
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
            raw_input = form.get('simon_says_prompt', '').strip()
            
            if not raw_input:
                error_msg = 'Please provide a prompt for the LLM interaction.'
                logger.error(f"Error in {app_name}/{step_id}: {error_msg}")
                return P(error_msg, style=pip.get_style('error'))
            
            # Extract clean prompt text, removing any previous formatting
            if '--- Simon Says Prompt ---' in raw_input:
                # Extract the actual prompt content between the markers
                lines = raw_input.split('\n')
                start_collecting = False
                prompt_lines = []
                
                for line in lines:
                    if line.strip() == '--- Simon Says Prompt ---':
                        start_collecting = True
                        continue
                    elif line.strip() == '--- Result ---':
                        break
                    elif start_collecting:
                        prompt_lines.append(line)
                
                prompt_text = '\n'.join(prompt_lines).strip()
            else:
                # No formatting present, use as-is
                prompt_text = raw_input

            # Show clean initiation message
            await pip.stream(f'🎪 Simon Says: Sending your prompt to the LLM...', role='system')

            # Prepare messages for LLM interaction
            messages = [
                {'role': 'system', 'content': 'You are a helpful assistant capable of making tool calls when needed.'},
                {'role': 'user', 'content': prompt_text}
            ]

            # Process the LLM interaction through the Pipulate instance
            mcp_result = None
            async for chunk in pip.process_llm_interaction(MODEL, messages):
                await pip.stream(chunk, verbatim=True, role='assistant', simulate_typing=False)
                # Capture the MCP result if it's a cat fact
                if 'Cat Fact Alert!' in chunk and 'Would you like another fact?' in chunk:
                    mcp_result = chunk
            
            # Add the MCP result to conversation history if we got one
            if mcp_result:
                await self.message_queue.add(pip, mcp_result, verbatim=True, role='assistant')

            # Store a summary for the revert state
            interaction_summary = f"--- Simon Says Prompt ---\n{prompt_text}\n\n--- Result ---\nCheck the chat panel and server logs for the detailed interaction and observability report."
            await pip.set_step_data(
                pipeline_id=db.get('pipeline_id', 'unknown'),
                step_id=step_id,
                step_value=interaction_summary,
                steps=steps
            )
            
            # Use display_revert_widget to show the full content, not just abbreviated label
            next_step_id = steps[step_index + 1].id if step_index + 1 < len(steps) else 'finalize'
            revert_widget = pip.display_revert_widget(
                step_id=step_id, 
                app_name=app_name, 
                message=f"{step.show}: Interaction Complete",
                widget=Pre(interaction_summary, style=self._get_display_style()),
                steps=steps
            )
            next_step_trigger = Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load')
            return Div(revert_widget, next_step_trigger, id=step_id)

        except Exception as e:
            error_msg = f'Error during MCP interaction processing: {str(e)}'
            logger.error(f"Error in step_01_submit: {error_msg}")
            await pip.stream(f'❌ Error: {error_msg}', role='system')
            return P(error_msg, style=pip.get_style('error'))
    # --- END_STEP_BUNDLE: step_01 ---

    async def step_01_toggle(self, request):
        """Cycle through different prompt modes."""
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        
        pipeline_id = db.get('pipeline_id', 'unknown')
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        current_mode = step_data.get('prompt_mode', 'simple_flash')
        
        # Cycle through modes: simple_flash -> cat_fact -> advanced_flash -> list_elements -> simple_flash
        mode_cycle = {
            'simple_flash': 'cat_fact',
            'cat_fact': 'advanced_flash', 
            'advanced_flash': 'list_elements',
            'list_elements': 'simple_flash'
        }
        
        next_mode = mode_cycle.get(current_mode, 'simple_flash')
        step_data['prompt_mode'] = next_mode
        await pip.set_step_data(pipeline_id, step_id, step_data, steps, clear_previous=False)
        
        # Redirect to the step to refresh the view
        return RedirectResponse(url=f'/{app_name}/{step_id}', status_code=303)

    # --- STEP_METHODS_INSERTION_POINT ---
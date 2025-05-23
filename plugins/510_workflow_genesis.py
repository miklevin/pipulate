# File: plugins/710_blank_placeholder.py
import asyncio
from collections import namedtuple
from datetime import datetime
from fasthtml.common import * # type: ignore
from loguru import logger
import inspect
from pathlib import Path
import re
import json
from starlette.responses import HTMLResponse

ROLES = ['Developer'] # Defines which user roles can see this plugin

Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None, None, None, False, None))

def derive_public_endpoint_from_filename(filename_str: str) -> str:
    """Derives the public endpoint name from the filename (e.g., "010_my_flow.py" -> "my_flow")."""
    filename_part_no_ext = Path(filename_str).stem
    return re.sub(r"^\d+_", "", filename_part_no_ext)

class WorkflowGenesis:
    """
    Blank Placeholder Workflow
    A minimal template for creating new Pipulate workflows.
    It includes one placeholder step and the necessary structure for expansion.
    """
    APP_NAME = 'workflow_genesis' 
    DISPLAY_NAME = 'Workflow Creation Helper' 
    ENDPOINT_MESSAGE = """This interactive assistant guides you through creating new Pipulate workflows, adding initial steps, and preparing for AI-assisted customization by generating necessary commands and prompts."""
    TRAINING_PROMPT = """The user is interacting with the 'Workflow Creation Helper'. This tool assists them in: 1. Defining parameters for a new Pipulate workflow. 2. Generating create_workflow.py and splice_workflow_step.py commands. 3. (Future) Selecting a source widget and target placeholder for a 'swap' operation. 4. (Future) Generating a prompt.md and a prompt_foo.py manifest for AI-assisted code integration. Guide the user on the purpose of each input field, the commands generated, and the subsequent actions they need to perform in their terminal or with their AI assistant."""

    def __init__(self, app, pipulate, pipeline, db, app_name=None):
        self.app = app
        self.app_name = self.APP_NAME 
        self.pipulate = pipulate
        self.pipeline = pipeline 
        self.db = db 
        pip = self.pipulate 
        self.message_queue = pip.get_message_queue()
        
        # self.steps includes all data steps AND the system 'finalize' step at the end.
        # splice_workflow_step.py inserts new data steps BEFORE STEPS_LIST_INSERTION_POINT.
        self.steps = [
            Step(id='step_01', done='new_workflow_params', show='1. Define New Workflow', refill=True),
            # --- STEPS_LIST_INSERTION_POINT --- 
            Step(id='finalize', done='finalized', show='Finalize Workflow', refill=False) 
        ]
        self.steps_indices = {step_obj.id: i for i, step_obj in enumerate(self.steps)}

        internal_route_prefix = self.APP_NAME 
        
        routes = [
            (f'/{internal_route_prefix}/init', self.init, ['POST']), 
            (f'/{internal_route_prefix}/revert', self.handle_revert, ['POST']),
            (f'/{internal_route_prefix}/unfinalize', self.unfinalize, ['POST'])
        ]

        for step_obj in self.steps:
            step_id = step_obj.id
            handler_method = getattr(self, step_id, None)
            if handler_method:
                current_methods = ['GET']
                if step_id == 'finalize': 
                    current_methods.append('POST')
                routes.append((f'/{internal_route_prefix}/{step_id}', handler_method, current_methods))
            
            if step_id != 'finalize': # Only data steps have explicit _submit handlers
                submit_handler_method = getattr(self, f'{step_id}_submit', None)
                if submit_handler_method:
                    routes.append((f'/{internal_route_prefix}/{step_id}_submit', submit_handler_method, ['POST']))
        
        for path, handler, *methods_list_arg in routes:
            current_methods = methods_list_arg[0] if methods_list_arg else ['GET']
            self.app.route(path, methods=current_methods)(handler)
            
        self.step_messages = {}
        for step_obj in self.steps:
            if step_obj.id == 'finalize':
                self.step_messages['finalize'] = { 
                    'ready': 'All steps complete. Ready to finalize workflow.', 
                    'complete': f'Workflow finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes.'
                }
            elif step_obj.id == 'step_01':
                self.step_messages[step_obj.id] = {
                    'input': 'Please provide the details for the new workflow you want to create.',
                    'complete': 'New workflow parameters captured. Commands generated below.'
                }
            else:
                self.step_messages[step_obj.id] = {
                    'input': f'{pip.fmt(step_obj.id)}: Please complete {step_obj.show}.', 
                    'complete': f'{step_obj.show} complete. Continue to next step.'
                }

    async def landing(self, request):
        pip, pipeline_table = self.pipulate, self.pipeline
        try:
            module_file = inspect.getfile(self.__class__)
            public_app_name_for_display = derive_public_endpoint_from_filename(Path(module_file).name)
        except TypeError: 
            public_app_name_for_display = self.APP_NAME 
        
        title = f'{self.DISPLAY_NAME or public_app_name_for_display.replace("_", " ").title()}'
        full_key, prefix, _ = pip.generate_pipeline_key(self) 
        
        pipeline_table.xtra(app_name=self.APP_NAME) 
        matching_records = [record.pkey for record in pipeline_table() if record.pkey.startswith(prefix)]
        
        return Container(
            Card( H2(title), P(self.ENDPOINT_MESSAGE, cls='text-secondary'), 
                Form(
                    pip.wrap_with_inline_button(
                        Input(placeholder='Existing or new 🗝 here (Enter for auto)', name='pipeline_id', list='pipeline-ids', type='search', required=False, autofocus=True, value=full_key, _onfocus='this.setSelectionRange(this.value.length, this.value.length)', cls='contrast'), 
                        button_label='Enter 🔑', button_class='secondary'
                    ), 
                    pip.update_datalist('pipeline-ids', options=matching_records, clear=not matching_records), 
                    hx_post=f'/{self.APP_NAME}/init', 
                    hx_target=f'#{self.APP_NAME}-container'
                )
            ), 
            Div(id=f'{self.APP_NAME}-container')
        )

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

        await self.message_queue.add(pip, f'Workflow ID: {pipeline_id}', verbatim=True, spaces_before=0)
        await self.message_queue.add(pip, f"Return later by selecting '{pipeline_id}' from the dropdown.", verbatim=True, spaces_before=0)
        
        first_step_id = self.steps[0].id # First step in self.steps (which includes 'finalize')
        return Div(Div(id=first_step_id, hx_get=f'/{internal_app_name}/{first_step_id}', hx_trigger='load'), id=f'{internal_app_name}-container')

    async def finalize(self, request):
        pip, db, app_name = self.pipulate, self.db, self.APP_NAME
        # Use self.steps as it's the definitive list including 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        
        finalize_step_obj = next(s for s in self.steps if s.id == 'finalize')
        finalize_data = pip.get_step_data(pipeline_id, finalize_step_obj.id, {})

        if request.method == 'GET':
            if finalize_step_obj.done in finalize_data:
                return Card(H3('Workflow is locked.'), Form(Button(pip.UNLOCK_BUTTON_LABEL, type='submit', cls='secondary outline'), hx_post=f'/{app_name}/unfinalize', hx_target=f'#{app_name}-container'), id=finalize_step_obj.id)
            else:
                # Check if all data steps (all steps in self.steps *before* 'finalize') are complete
                all_data_steps_complete = all(pip.get_step_data(pipeline_id, step.id, {}).get(step.done) for step in self.steps if step.id != 'finalize')
                if all_data_steps_complete:
                    return Card(H3('All steps complete. Finalize?'), P('You can revert to any step and make changes.', cls='text-secondary'), Form(Button('Finalize 🔒', type='submit', cls='primary'), hx_post=f'/{app_name}/finalize', hx_target=f'#{app_name}-container'), id=finalize_step_obj.id)
                else: 
                    return Div(id=finalize_step_obj.id) 
        elif request.method == 'POST':
            await pip.finalize_workflow(pipeline_id)
            await self.message_queue.add(pip, self.step_messages['finalize']['complete'], verbatim=True)
            return pip.rebuild(app_name, self.steps)

    async def unfinalize(self, request):
        pip, db, app_name = (self.pipulate, self.db, self.APP_NAME)
        pipeline_id = db.get('pipeline_id', 'unknown')
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, 'Workflow unfinalized! You can now revert to any step and make changes.', verbatim=True)
        return pip.rebuild(app_name, self.steps)

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
        return pip.rebuild(app_name, current_steps_to_pass_helpers)

    def format_bash_command(self, text):
        """
        Format text for use in a bash command, handling various quote scenarios:
        - Escape exclamation marks to prevent bash history expansion
        - Escape double quotes with backslash
        - Wrap text in double quotes if it contains spaces or quotes
        """
        if not text:
            return '""'
            
        # Escape exclamation marks to prevent bash history expansion
        text = text.replace('!', '\\!')
            
        # Always escape double quotes with backslash
        text = text.replace('"', '\\"')
        
        # If text contains spaces or quotes, wrap in double quotes
        if ' ' in text or '"' in text or "'" in text:
            return f'"{text}"'
            
        # Otherwise return as is
        return text

    def create_prism_widget(self, create_cmd, splice_cmd, widget_id):
        """Create a Prism.js syntax highlighting widget with copy functionality for each command."""
        textarea_id_create = f'{widget_id}_create_cmd'
        textarea_id_splice = f'{widget_id}_splice_cmd'
        
        container = Div(
            # Create Command Box
            Div(
                H5('Create Workflow Command:'),
                Textarea(create_cmd, id=textarea_id_create, style='display: none;'),
                Pre(
                    Code(create_cmd, cls='language-bash', style='position: relative; white-space: inherit; padding: 0 0 0 0;'),
                    cls='line-numbers'
                ),
                cls='mt-4'
            ),
            # Splice Command Box
            Div(
                H5('Splice Workflow Step Command:'),
                Textarea(splice_cmd, id=textarea_id_splice, style='display: none;'),
                Pre(
                    Code(splice_cmd, cls='language-bash', style='position: relative; white-space: inherit; padding: 0 0 0 0;'),
                    cls='line-numbers'
                ),
                cls='mt-4'
            ),
            id=widget_id
        )
        
        init_script = Script(f"""
            (function() {{
                // Initialize Prism immediately when the script loads
                if (typeof Prism !== 'undefined') {{
                    Prism.highlightAllUnder(document.getElementById('{widget_id}'));
                }}
                
                // Also listen for the HX-Trigger event as a backup
                document.body.addEventListener('initializePrism', function(event) {{
                    if (event.detail.targetId === '{widget_id}') {{
                        console.log('Received initializePrism event for {widget_id}');
                        if (typeof Prism !== 'undefined') {{
                            Prism.highlightAllUnder(document.getElementById('{widget_id}'));
                        }} else {{
                            console.error('Prism library not found for {widget_id}');
                        }}
                    }}
                }});
            }})();
        """, type='text/javascript')
        return Div(container, init_script)

    async def step_01(self, request):
        pip, db, app_name = (self.pipulate, self.db, self.APP_NAME)
        current_steps_for_logic = self.steps
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step_obj = current_steps_for_logic[step_index]
        next_step_id = current_steps_for_logic[step_index + 1].id
        
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        current_value = step_data.get(step_obj.done, '')
        finalize_sys_data = pip.get_step_data(pipeline_id, 'finalize', {})

        if 'finalized' in finalize_sys_data and current_value:
            # Finalized Phase
            pip.append_to_history(f"[WIDGET CONTENT] {step_obj.show} (Finalized):\n{current_value}")
            # Generate commands for display
            params = current_value
            create_cmd = f"""python create_workflow.py \\
{params['target_filename']} \\
{params['class_name']} \\
{params['internal_app_name']} \\
{self.format_bash_command(params['display_name'])} \\
{self.format_bash_command(params['endpoint_message'])} \\
{self.format_bash_command(params['training_prompt'])} \\
--force"""
            splice_cmd = f"python splice_workflow_step.py plugins/{params['target_filename']}"
            
            # Create PrismJS widget for commands
            widget_id = f"prism-widget-{pipeline_id.replace('-', '_')}-{step_id}"
            prism_widget = self.create_prism_widget(create_cmd, splice_cmd, widget_id)
            
            response = HTMLResponse(to_xml(Div(
                pip.finalized_content(message=f"🔒 {step_obj.show}", content=prism_widget),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )))
            response.headers['HX-Trigger'] = json.dumps({'initializePrism': {'targetId': widget_id}})
            return response
            
        elif current_value and state.get('_revert_target') != step_id:
            # Revert/Completed Phase
            pip.append_to_history(f"[WIDGET CONTENT] {step_obj.show} (Completed):\n{current_value}")
            # Generate commands for display
            params = current_value
            create_cmd = f"""python create_workflow.py \\
{params['target_filename']} \\
{params['class_name']} \\
{params['internal_app_name']} \\
{self.format_bash_command(params['display_name'])} \\
{self.format_bash_command(params['endpoint_message'])} \\
{self.format_bash_command(params['training_prompt'])} \\
--force"""
            splice_cmd = f"python splice_workflow_step.py plugins/{params['target_filename']}"
            
            # Create PrismJS widget for commands
            widget_id = f"prism-widget-{pipeline_id.replace('-', '_')}-{step_id}"
            prism_widget = self.create_prism_widget(create_cmd, splice_cmd, widget_id)
            
            response = HTMLResponse(to_xml(Div(
                pip.display_revert_widget(
                    step_id=step_id,
                    app_name=app_name,
                    message="Scaffolding Commands Generated",
                    widget=prism_widget,
                    steps=current_steps_for_logic
                ),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )))
            response.headers['HX-Trigger'] = json.dumps({'initializePrism': {'targetId': widget_id}})
            return response
        else:
            # Input Phase
            pip.append_to_history(f'[WIDGET STATE] {step_obj.show}: Showing input form')
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            
            # Pre-fill form with Kung Fu workflow parameters
            default_params = {
                'target_filename': '035_kungfu_workflow.py',
                'class_name': 'KungfuWorkflow',
                'internal_app_name': 'kungfu',
                'display_name': 'Kung Fu Download',
                'endpoint_message': 'Greetings, chosen one. Selecting this app has initiated the \'Kung Fu Download\' protocol. Prepare for enlightenment... or at least, a demonstration.',
                'training_prompt': 'You are assisting with the "Kung Fu Download" workflow. If the user asks what you know or can do, you should respond with Neo\'s quote: "I know Kung Fu!" The secret word is "Morpheus". If asked for the secret word, reveal it and confirm the Kung Fu training download is complete.'
            }
            
            # Use existing data if available, otherwise use defaults
            existing_params = current_value if current_value else default_params
            
            form_content = Form(
                # Target Filename
                Label("Target Filename", **{'for': 'target_filename'}),
                Input(
                    type="text",
                    id="target_filename",
                    name="target_filename",
                    placeholder="e.g., 040_example_flow.py",
                    value=existing_params.get('target_filename', ''),
                    required=True
                ),
                Small("The filename for your new workflow (e.g., 040_my_plugin.py)"),
                
                # Class Name
                Label("Class Name", **{'for': 'class_name'}),
                Input(
                    type="text",
                    id="class_name",
                    name="class_name",
                    placeholder="e.g., ExampleFlow",
                    value=existing_params.get('class_name', ''),
                    required=True
                ),
                Small("The Python class name for your workflow (e.g., MyPluginWorkflow)"),
                
                # Internal App Name
                Label("Internal App Name", **{'for': 'internal_app_name'}),
                Input(
                    type="text",
                    id="internal_app_name",
                    name="internal_app_name",
                    placeholder="e.g., example_flow_internal (must be unique)",
                    value=existing_params.get('internal_app_name', ''),
                    required=True
                ),
                Small("The internal identifier for your workflow (must be unique)"),
                
                # Display Name
                Label("Display Name", **{'for': 'display_name'}),
                Input(
                    type="text",
                    id="display_name",
                    name="display_name",
                    placeholder="e.g., My Example Workflow",
                    value=existing_params.get('display_name', ''),
                    required=True
                ),
                Small("The user-friendly name shown in the UI"),
                
                # Endpoint Message
                Label("Endpoint Message", **{'for': 'endpoint_message'}),
                Textarea(
                    existing_params.get('endpoint_message', ''),
                    id="endpoint_message",
                    name="endpoint_message",
                    placeholder="The message shown on the workflow's landing page",
                    required=True
                ),
                Small("The message shown on your workflow's landing page"),
                
                # Training Prompt
                Label("Training Prompt", **{'for': 'training_prompt'}),
                Textarea(
                    existing_params.get('training_prompt', ''),
                    id="training_prompt",
                    name="training_prompt",
                    placeholder="The LLM training prompt for your workflow",
                    required=True
                ),
                Small("The training prompt that guides the LLM for your workflow"),
                
                Button('Generate Scaffolding Commands ▸', type='submit', cls='primary'),
                hx_post=f'/{app_name}/{step_id}_submit',
                hx_target=f'#{step_id}'
            )
            return Div(Card(H3(f'{step_obj.show}'), form_content), Div(id=next_step_id), id=step_id)

    async def step_01_submit(self, request):
        pip, db, app_name = (self.pipulate, self.db, self.APP_NAME)
        current_steps_for_logic = self.steps
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step_obj = current_steps_for_logic[step_index]
        next_step_id = current_steps_for_logic[step_index + 1].id
        
        pipeline_id = db.get('pipeline_id', 'unknown')
        form_data = await request.form()
        
        # Collect and validate form data
        params = {
            'target_filename': form_data.get('target_filename', '').strip(),
            'class_name': form_data.get('class_name', '').strip(),
            'internal_app_name': form_data.get('internal_app_name', '').strip(),
            'display_name': form_data.get('display_name', '').strip(),
            'endpoint_message': form_data.get('endpoint_message', '').strip(),
            'training_prompt': form_data.get('training_prompt', '').strip()
        }
        
        # Validate required fields
        missing_fields = [field for field, value in params.items() if not value]
        if missing_fields:
            error_msg = f"Please fill in all required fields: {', '.join(missing_fields)}"
            return P(error_msg, style=pip.get_style('error'))
        
        # Store the parameters
        await pip.set_step_data(pipeline_id, step_id, params, current_steps_for_logic)
        
        # Generate commands for display
        create_cmd = f"""python create_workflow.py \\
{params['target_filename']} \\
{params['class_name']} \\
{params['internal_app_name']} \\
{self.format_bash_command(params['display_name'])} \\
{self.format_bash_command(params['endpoint_message'])} \\
{self.format_bash_command(params['training_prompt'])} \\
--force"""
        splice_cmd = f"python splice_workflow_step.py plugins/{params['target_filename']}"
        
        # Create PrismJS widget for commands
        widget_id = f"prism-widget-{pipeline_id.replace('-', '_')}-{step_id}"
        prism_widget = self.create_prism_widget(create_cmd, splice_cmd, widget_id)
        
        pip.append_to_history(f'[WIDGET CONTENT] {step_obj.show}:\n{params}')
        pip.append_to_history(f'[WIDGET STATE] {step_obj.show}: Step completed')
        await self.message_queue.add(pip, f'{step_obj.show} complete.', verbatim=True)
        
        response = HTMLResponse(to_xml(Div(
            pip.display_revert_widget(
                step_id=step_id,
                app_name=app_name,
                message="Scaffolding Commands Generated",
                widget=prism_widget,
                steps=current_steps_for_logic
            ),
            Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
            id=step_id
        )))
        response.headers['HX-Trigger'] = json.dumps({'initializePrism': {'targetId': widget_id}})
        return response

    # --- STEP_METHODS_INSERTION_POINT ---
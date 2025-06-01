# File: plugins/510_workflow_genesis.py
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
    Workflow Creation Assistant - Three Template-Based Experiences
    
    Provides three distinct workflow creation paths:
    1. Blank Placeholder: Single-step workflow for learning step management
    2. Hello World Recreation: Multi-step process demonstrating helper tool sequence  
    3. Trifecta Workflow: Complex workflow starting from Botify template
    
    Each path provides both individual commands and complete copy-paste sequences.
    """
    
    # Simplified UI Constants
    UI_CONSTANTS = {
        'COLORS': {
            'TEXT': '#e9ecef',
            'ACCENT': '#007bff', 
            'SUCCESS': '#28a745',
            'INFO': '#17a2b8'
        },
        'SPACING': {
            'MARGIN': '1rem',
            'PADDING': '0.75rem'
        }
    }
    
    APP_NAME = 'workflow_genesis' 
    DISPLAY_NAME = 'Workflow Creation Assistant' 
    ENDPOINT_MESSAGE = """Create Pipulate workflows using three distinct approaches: blank placeholder for learning, hello world recreation for understanding helper tools, or trifecta workflow for complex scenarios."""
    TRAINING_PROMPT = """You are assisting with workflow creation in Pipulate. Help users choose between three approaches: 1) Blank placeholder for beginners learning step management, 2) Hello world recreation for understanding helper tool sequences, 3) Trifecta workflow for complex data collection scenarios. Guide them through command generation and explain the purpose of each approach."""

    def __init__(self, app, pipulate, pipeline, db, app_name=None):
        self.app = app
        self.app_name = self.APP_NAME 
        self.pipulate = pipulate
        self.pipeline = pipeline 
        self.db = db 
        pip = self.pipulate 
        self.message_queue = pip.get_message_queue()
        
        self.steps = [
            Step(id='step_01', done='workflow_params', show='1. Define Workflow Parameters', refill=True),
            Step(id='step_02', done='template_choice', show='2. Choose Template Approach', refill=False),
            Step(id='step_03', done='command_sequence', show='3. Generated Command Sequence', refill=False),
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
            
            if step_id != 'finalize':
                submit_handler_method = getattr(self, f'{step_id}_submit', None)
                if submit_handler_method:
                    routes.append((f'/{internal_route_prefix}/{step_id}_submit', submit_handler_method, ['POST']))
        
        for path, handler, *methods_list_arg in routes:
            current_methods = methods_list_arg[0] if methods_list_arg else ['GET']
            self.app.route(path, methods=current_methods)(handler)
            
        self.step_messages = self._init_step_messages()

    def _init_step_messages(self):
        """Initialize step messages"""
        pip = self.pipulate
        return {
            'finalize': { 
                'ready': 'All steps complete. Ready to finalize workflow.', 
                'complete': f'Workflow finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes.'
            },
            'step_01': {
                'input': 'Define the basic parameters for your new workflow.',
                'complete': 'Workflow parameters defined. Choose your template approach next.'
            },
            'step_02': {
                'input': 'Choose your workflow creation approach and template.',
                'complete': 'Template approach selected. View your command sequence next.'
            },
            'step_03': {
                'input': 'Your complete command sequence is ready to copy and execute.',
                'complete': 'Command sequence generated. Copy and run to create your workflow.'
            }
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
            from starlette.responses import Response
            response = Response('')
            response.headers['HX-Refresh'] = 'true'
            return response
        
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
        
        return pip.run_all_cells(internal_app_name, self.steps)

    # Common finalization methods (simplified)
    async def finalize(self, request):
        pip, db, app_name = self.pipulate, self.db, self.APP_NAME
        pipeline_id = db.get('pipeline_id', 'unknown')
        
        finalize_step_obj = next(s for s in self.steps if s.id == 'finalize')
        finalize_data = pip.get_step_data(pipeline_id, finalize_step_obj.id, {})

        if request.method == 'GET':
            if finalize_step_obj.done in finalize_data:
                return Card(
                    H3('Workflow Creation Complete'),
                    P('Your workflow commands have been generated and are ready to use.', cls='text-secondary'),
                    Form(
                        Button(pip.UNLOCK_BUTTON_LABEL, type='submit', cls='secondary outline'), 
                        hx_post=f'/{app_name}/unfinalize', 
                        hx_target=f'#{app_name}-container'
                    ), 
                    id=finalize_step_obj.id
                )
            else:
                all_data_steps_complete = all(pip.get_step_data(pipeline_id, step.id, {}).get(step.done) for step in self.steps if step.id != 'finalize')
                if all_data_steps_complete:
                    return Card(
                        H3('Ready to Finalize'),
                        P('All command sequences have been generated. Finalize to complete the workflow creation process.', cls='text-secondary'),
                        Form(
                            Button('Finalize 🔒', type='submit', cls='primary'), 
                            hx_post=f'/{app_name}/finalize', 
                            hx_target=f'#{app_name}-container'
                        ), 
                        id=finalize_step_obj.id
                    )
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
        await self.message_queue.add(pip, 'Workflow creation unfinalized. You can now modify any step.', verbatim=True)
        return pip.run_all_cells(app_name, self.steps)

    async def handle_revert(self, request):
        pip, db, app_name = (self.pipulate, self.db, self.APP_NAME)
        form = await request.form()
        step_id_to_revert_to = form.get('step_id')
        pipeline_id = db.get('pipeline_id', 'unknown')

        if not step_id_to_revert_to:
            return P('Error: No step specified for revert.', style='color: #dc3545;')

        await pip.clear_steps_from(pipeline_id, step_id_to_revert_to, self.steps)
        state = pip.read_state(pipeline_id)
        state['_revert_target'] = step_id_to_revert_to
        pip.write_state(pipeline_id, state)
        
        message = await pip.get_state_message(pipeline_id, self.steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        return pip.run_all_cells(app_name, self.steps)

    # Utility methods (simplified and extracted)
    def format_bash_command(self, text):
        """Format text for bash command usage"""
        if not text:
            return '""'
        text = text.replace('!', '\\!')
        text = text.replace('"', '\\"')
        if ' ' in text or '"' in text or "'" in text:
            return f'"{text}"'
        return text

    def get_template_info(self, template_name):
        """Get template information"""
        templates = {
            'blank': {
                'name': 'Blank Placeholder',
                'description': 'Single-step workflow for learning step management',
                'use_case': 'Learning how to add/remove steps and basic workflow structure'
            },
            'hello': {
                'name': 'Hello Workflow Recreation',
                'description': 'Multi-step process demonstrating helper tool sequence',
                'use_case': 'Understanding how helper tools work together to build complex workflows'
            },
            'trifecta': {
                'name': 'Trifecta Workflow',
                'description': 'Complex workflow starting from Botify template',
                'use_case': 'Building sophisticated data collection workflows with API integration'
            }
        }
        return templates.get(template_name, templates['blank'])

    # Template-specific experience methods (to be implemented)
    def create_blank_placeholder_experience(self, workflow_params, widget_id):
        """Create experience for blank placeholder template - learning step management basics"""
        filename = workflow_params.get('target_filename', '035_kungfu_workflow.py')
        class_name = workflow_params.get('class_name', 'KungfuWorkflow')
        internal_name = workflow_params.get('internal_app_name', 'kungfu')
        display_name = workflow_params.get('display_name', 'Kung Fu Download')
        endpoint_message = workflow_params.get('endpoint_message', 'Welcome to workflow creation')
        training_prompt = workflow_params.get('training_prompt', 'Help users create workflows step by step')

        # Single create command - uses blank template specifically
        create_cmd = f"python helpers/create_workflow.py {filename} {class_name} {internal_name} \\\n" + \
                    f"  {self.format_bash_command(display_name)} \\\n" + \
                    f"  {self.format_bash_command(endpoint_message)} \\\n" + \
                    f"  {self.format_bash_command(training_prompt)} \\\n" + \
                    f"  --template blank --force"

        # Step positioning demo commands
        splice_bottom_cmd = f"python helpers/splice_workflow_step.py {filename} --position bottom"
        splice_top_cmd = f"python helpers/splice_workflow_step.py {filename} --position top"

        # Combined command with backslash line breaks for readability
        combined_cmd = f"python helpers/create_workflow.py {filename} {class_name} {internal_name} \\\n" + \
                      f"  {self.format_bash_command(display_name)} \\\n" + \
                      f"  {self.format_bash_command(endpoint_message)} \\\n" + \
                      f"  {self.format_bash_command(training_prompt)} \\\n" + \
                      f"  --template blank --force && \\\n" + \
                      f"echo 'Base workflow created. Now try:' && \\\n" + \
                      f"echo '{splice_bottom_cmd}' && \\\n" + \
                      f"echo '{splice_top_cmd}'"

        return Div(
            H4("Blank Placeholder Experience", style="color: #e9ecef; margin-bottom: 1rem;"),
            P("Creates a single-step workflow and demonstrates step positioning. Like Jupyter's Cell Above/Below concept.", 
              style="color: #6c757d; margin-bottom: 1.5rem;"),
            
            # Individual commands section
            H5("Individual Commands:", style="color: #17a2b8; margin-bottom: 0.75rem;"),
            
            Div(
                H6("1. Create Base Workflow", style="color: #007bff; margin-bottom: 0.25rem;"),
                P("Creates single-step placeholder workflow ready for customization", 
                  style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.5rem;"),
                Pre(Code(create_cmd, cls='language-bash copy-code'), 
                    style="background-color: #2d3748; padding: 1rem; border-radius: 4px; margin-bottom: 1rem; overflow-x: auto; position: relative;"),
                
                H6("2. Add Step at Bottom", style="color: #007bff; margin-bottom: 0.25rem;"),
                P("Adds new step before finalize (default positioning)", 
                  style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.5rem;"),
                Pre(Code(splice_bottom_cmd, cls='language-bash copy-code'), 
                    style="background-color: #2d3748; padding: 1rem; border-radius: 4px; margin-bottom: 1rem; overflow-x: auto; position: relative;"),
                
                H6("3. Add Step at Top", style="color: #007bff; margin-bottom: 0.25rem;"),
                P("Adds new step as first data step", 
                  style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.5rem;"),
                Pre(Code(splice_top_cmd, cls='language-bash copy-code'), 
                    style="background-color: #2d3748; padding: 1rem; border-radius: 4px; margin-bottom: 1.5rem; overflow-x: auto; position: relative;")
            ),
            
            # All-in-one section
            H5("All-in-One Command:", style="color: #28a745; margin-bottom: 0.75rem;"),
            P("Copy and paste this single command to create the workflow and see positioning options:", 
              style="color: #6c757d; margin-bottom: 0.5rem;"),
            Pre(Code(combined_cmd, cls='language-bash copy-code'), 
                style="background-color: #2d3748; padding: 1rem; border-radius: 4px; border-left: 4px solid #28a745; overflow-x: auto; position: relative;"),
            
            id=widget_id
        )
    
    def create_hello_world_recreation_experience(self, workflow_params, widget_id):
        """Create experience for hello world recreation - understanding complete helper tool sequence"""
        filename = workflow_params.get('target_filename', '035_kungfu_workflow.py')
        class_name = workflow_params.get('class_name', 'KungfuWorkflow')
        internal_name = workflow_params.get('internal_app_name', 'kungfu')
        display_name = workflow_params.get('display_name', 'Kung Fu Download')
        endpoint_message = workflow_params.get('endpoint_message', 'Welcome to workflow creation')
        training_prompt = workflow_params.get('training_prompt', 'Help users create workflows step by step')

        # The corrected 5-command sequence - starts with blank template as specified
        cmd1 = f"python helpers/create_workflow.py {filename} {class_name} {internal_name} " + \
               f"{self.format_bash_command(display_name)} " + \
               f"{self.format_bash_command(endpoint_message)} " + \
               f"{self.format_bash_command(training_prompt)} --template blank --force"
        
        cmd2 = f"python helpers/manage_class_attributes.py {filename} plugins/500_hello_workflow.py --attributes-to-merge UI_CONSTANTS --force"
        
        cmd3 = f"python helpers/swap_workflow_step.py {filename} step_01 plugins/500_hello_workflow.py step_01 --force"
        
        cmd4 = f"python helpers/splice_workflow_step.py {filename} --position bottom"
        
        cmd5 = f"python helpers/swap_workflow_step.py {filename} step_02 plugins/500_hello_workflow.py step_02 --force"

        # Combined command with backslash line breaks for readability
        combined_cmd = f"python helpers/create_workflow.py {filename} {class_name} {internal_name} \\\n" + \
                      f"  {self.format_bash_command(display_name)} \\\n" + \
                      f"  {self.format_bash_command(endpoint_message)} \\\n" + \
                      f"  {self.format_bash_command(training_prompt)} \\\n" + \
                      f"  --template blank --force && \\\n" + \
                      f"python helpers/manage_class_attributes.py {filename} plugins/500_hello_workflow.py \\\n" + \
                      f"  --attributes-to-merge UI_CONSTANTS --force && \\\n" + \
                      f"python helpers/swap_workflow_step.py {filename} step_01 \\\n" + \
                      f"  plugins/500_hello_workflow.py step_01 --force && \\\n" + \
                      f"python helpers/splice_workflow_step.py {filename} --position bottom && \\\n" + \
                      f"python helpers/swap_workflow_step.py {filename} step_02 \\\n" + \
                      f"  plugins/500_hello_workflow.py step_02 --force"

        return Div(
            H4("Hello World Recreation Experience", style="color: #e9ecef; margin-bottom: 1rem;"),
            P("Demonstrates the complete helper tool sequence. Key insight: step_01 must be swapped BEFORE step_02 is added.", 
              style="color: #6c757d; margin-bottom: 1.5rem;"),
            
            # Individual commands section
            H5("Individual Commands:", style="color: #17a2b8; margin-bottom: 0.75rem;"),
            
            Div(
                H6("1. Create Base Workflow", style="color: #007bff; margin-bottom: 0.25rem;"),
                P("Creates base workflow from blank template", 
                  style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.5rem;"),
                Pre(Code(cmd1, cls='language-bash copy-code'), 
                    style="background-color: #2d3748; padding: 1rem; border-radius: 4px; margin-bottom: 1rem; overflow-x: auto; position: relative;"),
                
                H6("2. Merge UI Constants", style="color: #007bff; margin-bottom: 0.25rem;"),
                P("Copies styling constants from Hello workflow", 
                  style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.5rem;"),
                Pre(Code(cmd2, cls='language-bash copy-code'), 
                    style="background-color: #2d3748; padding: 1rem; border-radius: 4px; margin-bottom: 1rem; overflow-x: auto; position: relative;"),
                
                H6("3. Swap Step 1 Logic", style="color: #007bff; margin-bottom: 0.25rem;"),
                P("Replaces placeholder with name collection logic", 
                  style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.5rem;"),
                Pre(Code(cmd3, cls='language-bash copy-code'), 
                    style="background-color: #2d3748; padding: 1rem; border-radius: 4px; margin-bottom: 1rem; overflow-x: auto; position: relative;"),
                
                H6("4. Add Second Step", style="color: #007bff; margin-bottom: 0.25rem;"),
                P("Adds new placeholder step before finalize", 
                  style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.5rem;"),
                Pre(Code(cmd4, cls='language-bash copy-code'), 
                    style="background-color: #2d3748; padding: 1rem; border-radius: 4px; margin-bottom: 1rem; overflow-x: auto; position: relative;"),
                
                H6("5. Swap Step 2 Logic", style="color: #007bff; margin-bottom: 0.25rem;"),
                P("Replaces placeholder with greeting generation logic", 
                  style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.5rem;"),
                Pre(Code(cmd5, cls='language-bash copy-code'), 
                    style="background-color: #2d3748; padding: 1rem; border-radius: 4px; margin-bottom: 1.5rem; overflow-x: auto; position: relative;")
            ),
            
            # All-in-one section
            H5("All-in-One Command:", style="color: #28a745; margin-bottom: 0.75rem;"),
            P("Copy and paste this single command to execute the complete sequence:", 
              style="color: #6c757d; margin-bottom: 0.5rem;"),
            Pre(Code(combined_cmd, cls='language-bash copy-code'), 
                style="background-color: #2d3748; padding: 1rem; border-radius: 4px; border-left: 4px solid #28a745; overflow-x: auto; position: relative;"),
            
            id=widget_id
        )
    
    def create_trifecta_workflow_experience(self, workflow_params, widget_id):
        """Create experience for trifecta workflow - complex template conditioning"""
        filename = workflow_params.get('target_filename', '035_kungfu_workflow.py')
        class_name = workflow_params.get('class_name', 'KungfuWorkflow')
        internal_name = workflow_params.get('internal_app_name', 'kungfu')
        display_name = workflow_params.get('display_name', 'Kung Fu Download')
        endpoint_message = workflow_params.get('endpoint_message', 'Advanced data collection workflow')
        training_prompt = workflow_params.get('training_prompt', 'Help users create complex data workflows')

        # Trifecta workflow commands - uses trifecta template
        cmd1 = f"python helpers/create_workflow.py {filename} {class_name} {internal_name} " + \
               f"{self.format_bash_command(display_name)} " + \
               f"{self.format_bash_command(endpoint_message)} " + \
               f"{self.format_bash_command(training_prompt)} --template trifecta --force"
        
        cmd2 = f"python helpers/manage_class_attributes.py {filename} plugins/040_parameter_buster.py --attributes-to-merge UI_CONSTANTS,DATA_SOURCES --force"
        
        cmd3 = f"python helpers/swap_workflow_step.py {filename} step_01 plugins/040_parameter_buster.py step_01 --force"

        # Combined command with backslash line breaks for readability
        combined_cmd = f"python helpers/create_workflow.py {filename} {class_name} {internal_name} \\\n" + \
                      f"  {self.format_bash_command(display_name)} \\\n" + \
                      f"  {self.format_bash_command(endpoint_message)} \\\n" + \
                      f"  {self.format_bash_command(training_prompt)} \\\n" + \
                      f"  --template trifecta --force && \\\n" + \
                      f"python helpers/manage_class_attributes.py {filename} \\\n" + \
                      f"  plugins/040_parameter_buster.py \\\n" + \
                      f"  --attributes-to-merge UI_CONSTANTS,DATA_SOURCES --force && \\\n" + \
                      f"python helpers/swap_workflow_step.py {filename} step_01 \\\n" + \
                      f"  plugins/040_parameter_buster.py step_01 --force"

        return Div(
            H4("Trifecta Workflow Experience", style="color: #e9ecef; margin-bottom: 1rem;"),
            P("Starts with sophisticated template and conditions it for complex customization. Enables Parameter Buster-style workflows.", 
              style="color: #6c757d; margin-bottom: 1.5rem;"),
            
            # Individual commands section
            H5("Individual Commands:", style="color: #17a2b8; margin-bottom: 0.75rem;"),
            
            Div(
                H6("1. Create Trifecta Workflow", style="color: #007bff; margin-bottom: 0.25rem;"),
                P("Creates complex 5-step workflow from Botify Trifecta template", 
                  style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.5rem;"),
                Pre(Code(cmd1, cls='language-bash copy-code'), 
                    style="background-color: #2d3748; padding: 1rem; border-radius: 4px; margin-bottom: 1rem; overflow-x: auto; position: relative;"),
                
                H6("2. Condition Class Attributes", style="color: #007bff; margin-bottom: 0.25rem;"),
                P("Prepares workflow for Parameter Buster-style method bundles", 
                  style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.5rem;"),
                Pre(Code(cmd2, cls='language-bash copy-code'), 
                    style="background-color: #2d3748; padding: 1rem; border-radius: 4px; margin-bottom: 1rem; overflow-x: auto; position: relative;"),
                
                H6("3. Customize First Step", style="color: #007bff; margin-bottom: 0.25rem;"),
                P("Replace with custom parameter collection logic", 
                  style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.5rem;"),
                Pre(Code(cmd3, cls='language-bash copy-code'), 
                    style="background-color: #2d3748; padding: 1rem; border-radius: 4px; margin-bottom: 1.5rem; overflow-x: auto; position: relative;")
            ),
            
            # All-in-one section
            H5("All-in-One Command:", style="color: #28a745; margin-bottom: 0.75rem;"),
            P("Copy and paste this single command to create and condition the trifecta workflow:", 
              style="color: #6c757d; margin-bottom: 0.5rem;"),
            Pre(Code(combined_cmd, cls='language-bash copy-code'), 
                style="background-color: #2d3748; padding: 1rem; border-radius: 4px; border-left: 4px solid #28a745; overflow-x: auto; position: relative;"),
            
            id=widget_id
        )

    # Step implementation methods (simplified structure)
    async def step_01(self, request):
        """Step 1: Define workflow parameters"""
        pip, db, app_name = (self.pipulate, self.db, self.APP_NAME)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step_obj = self.steps[step_index]
        next_step_id = self.steps[step_index + 1].id
        
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        current_value = step_data.get(step_obj.done, '')
        finalize_sys_data = pip.get_step_data(pipeline_id, 'finalize', {})

        if 'finalized' in finalize_sys_data and current_value:
            return Div(
                pip.finalized_content(message=f"🔒 {step_obj.show}", content=P(f"Workflow: {current_value.get('display_name', 'Unknown')}", cls='text-success')),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
            
        elif current_value and state.get('_revert_target') != step_id:
            return Div(
                pip.display_revert_widget(
                    step_id=step_id,
                    app_name=app_name,
                    message="Workflow Parameters Defined",
                    widget=P(f"Workflow: {current_value.get('display_name', 'Unknown')}", cls='text-success'),
                    steps=self.steps
                ),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        else:
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            
            # Comprehensive form with all workflow parameters including ENDPOINT_MESSAGE and TRAINING_PROMPT
            form_content = Form(
                Label("Target Filename", **{'for': 'target_filename'}),
                Input(type="text", id="target_filename", name="target_filename", value="035_kungfu_workflow.py", required=True),
                
                Label("Class Name", **{'for': 'class_name'}),
                Input(type="text", id="class_name", name="class_name", value="KungfuWorkflow", required=True),
                
                Label("Internal App Name", **{'for': 'internal_app_name'}),
                Input(type="text", id="internal_app_name", name="internal_app_name", value="kungfu", required=True),
                
                Label("Display Name", **{'for': 'display_name'}),
                Input(type="text", id="display_name", name="display_name", value="Kung Fu Download", required=True),
                
                Label("Endpoint Message", **{'for': 'endpoint_message'}),
                Textarea(
                    "Welcome to the Kung Fu Download workflow. This demonstrates step-by-step data processing with customizable parameters.",
                    id="endpoint_message", 
                    name="endpoint_message", 
                    placeholder="Brief description shown on the workflow landing page...",
                    required=True,
                    rows=3,
                    style="resize: vertical;"
                ),
                
                Label("Training Prompt", **{'for': 'training_prompt'}),
                Textarea(
                    "You are assisting with the Kung Fu Download workflow. Help users understand each step and provide guidance on customizing the workflow parameters. If they ask what this workflow does, explain that it's a template for learning Pipulate workflow creation. The user will likely ask you for the secret word to prove that you have been trained, and if the do (but only if they ask), tell them MORPHEUS",
                    id="training_prompt", 
                    name="training_prompt", 
                    placeholder="Instructions for the AI assistant when helping users with this workflow...",
                    required=True,
                    rows=4,
                    style="resize: vertical;"
                ),
                
                Button('Continue ▸', type='submit', cls='primary'),
                hx_post=f'/{app_name}/{step_id}_submit',
                hx_target=f'#{step_id}'
            )
            return Div(Card(H3(f'{step_obj.show}'), form_content), Div(id=next_step_id), id=step_id)

    async def step_01_submit(self, request):
        """Handle step 1 submission"""
        pip, db, app_name = (self.pipulate, self.db, self.APP_NAME)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step_obj = self.steps[step_index]
        next_step_id = self.steps[step_index + 1].id
        
        pipeline_id = db.get('pipeline_id', 'unknown')
        form_data = await request.form()
        
        params = {
            'target_filename': form_data.get('target_filename', '').strip(),
            'class_name': form_data.get('class_name', '').strip(),
            'internal_app_name': form_data.get('internal_app_name', '').strip(),
            'display_name': form_data.get('display_name', '').strip(),
            'endpoint_message': form_data.get('endpoint_message', ''),
            'training_prompt': form_data.get('training_prompt', '')
        }
        
        # Store with the correct key that matches step.done
        await pip.set_step_data(pipeline_id, step_id, {step_obj.done: params}, self.steps)
        await self.message_queue.add(pip, self.step_messages[step_id]['complete'], verbatim=True)
        
        return Div(
            pip.display_revert_widget(
                step_id=step_id,
                app_name=app_name,
                message="Workflow Parameters Defined",
                widget=P(f"Workflow: {params['display_name']}", cls='text-success'),
                steps=self.steps
            ),
            Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
            id=step_id
        )

    async def step_02(self, request):
        """Step 2: Choose template approach"""
        pip, db, app_name = (self.pipulate, self.db, self.APP_NAME)
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        step_obj = self.steps[step_index]
        next_step_id = self.steps[step_index + 1].id
        
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        current_value = step_data.get(step_obj.done, '')
        finalize_sys_data = pip.get_step_data(pipeline_id, 'finalize', {})

        if 'finalized' in finalize_sys_data and current_value:
            template_info = self.get_template_info(current_value.get('template', 'blank'))
            return Div(
                pip.finalized_content(message=f"🔒 {step_obj.show}", content=P(f"Template: {template_info['name']}", cls='text-success')),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
            
        elif current_value and state.get('_revert_target') != step_id:
            template_info = self.get_template_info(current_value.get('template', 'blank'))
            return Div(
                pip.display_revert_widget(
                    step_id=step_id,
                    app_name=app_name,
                    message="Template Approach Selected",
                    widget=P(f"Template: {template_info['name']}", cls='text-success'),
                    steps=self.steps
                ),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        else:
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            
            form_content = Form(
                Label("Template Approach", **{'for': 'template'}),
                Select(
                    Option("Blank Placeholder - Learn step management basics", value="blank", selected=True),
                    Option("Hello World Recreation - Understand helper tool sequence", value="hello"),
                    Option("Trifecta Workflow - Build complex data collection workflow", value="trifecta"),
                    name="template",
                    id="template",
                    required=True
                ),
                
                Button('Generate Commands ▸', type='submit', cls='primary'),
                hx_post=f'/{app_name}/{step_id}_submit',
                hx_target=f'#{step_id}'
            )
            return Div(Card(H3(f'{step_obj.show}'), form_content), Div(id=next_step_id), id=step_id)

    async def step_02_submit(self, request):
        """Handle step 2 submission"""
        pip, db, app_name = (self.pipulate, self.db, self.APP_NAME)
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        step_obj = self.steps[step_index]
        next_step_id = self.steps[step_index + 1].id
        
        pipeline_id = db.get('pipeline_id', 'unknown')
        form_data = await request.form()
        
        template_choice = {
            'template': form_data.get('template', 'blank')
        }
        
        # Store with the correct key that matches step.done
        await pip.set_step_data(pipeline_id, step_id, {step_obj.done: template_choice}, self.steps)
        await self.message_queue.add(pip, self.step_messages[step_id]['complete'], verbatim=True)
        
        template_info = self.get_template_info(template_choice['template'])
        
        return Div(
            pip.display_revert_widget(
                step_id=step_id,
                app_name=app_name,
                message="Template Approach Selected",
                widget=P(f"Template: {template_info['name']}", cls='text-success'),
                steps=self.steps
            ),
            Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
            id=step_id
        )

    async def step_03(self, request):
        """Step 3: Generate command sequence based on template choice"""
        pip, db, app_name = (self.pipulate, self.db, self.APP_NAME)
        step_id = 'step_03'
        step_index = self.steps_indices[step_id]
        step_obj = self.steps[step_index]
        next_step_id = self.steps[step_index + 1].id
        
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        current_value = step_data.get(step_obj.done, '')
        finalize_sys_data = pip.get_step_data(pipeline_id, 'finalize', {})

        # Get previous step data - fix the data key access
        step_01_data = pip.get_step_data(pipeline_id, 'step_01', {})
        step_02_data = pip.get_step_data(pipeline_id, 'step_02', {})
        
        # Access using the step.done keys
        workflow_params = step_01_data.get('workflow_params', {})
        template_choice = step_02_data.get('template_choice', {})
        selected_template = template_choice.get('template', 'blank')
        
        widget_id = f"template-experience-{pipeline_id.replace('-', '_')}-{step_id}"
        
        # Route to appropriate template experience
        if selected_template == 'blank':
            experience_widget = self.create_blank_placeholder_experience(workflow_params, widget_id)
        elif selected_template == 'hello':
            experience_widget = self.create_hello_world_recreation_experience(workflow_params, widget_id)
        elif selected_template == 'trifecta':
            experience_widget = self.create_trifecta_workflow_experience(workflow_params, widget_id)
        else:
            experience_widget = self.create_blank_placeholder_experience(workflow_params, widget_id)

        if 'finalized' in finalize_sys_data and current_value:
            return Div(
                pip.finalized_content(message=f"🔒 {step_obj.show}", content=experience_widget),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
            
        elif current_value and state.get('_revert_target') != step_id:
            return Div(
                pip.display_revert_widget(
                    step_id=step_id,
                    app_name=app_name,
                    message="Command Sequence Generated",
                    widget=experience_widget,
                    steps=self.steps
                ),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        else:
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            
            # Auto-complete this step since it's just display
            await pip.set_step_data(pipeline_id, step_id, {step_obj.done: f"Generated {selected_template} template experience"}, self.steps)
            await self.message_queue.add(pip, self.step_messages[step_id]['complete'], verbatim=True)
            
            # Copy functionality script for code blocks
            copy_script = Script("""
                // Add copy buttons to code blocks
                document.addEventListener('DOMContentLoaded', function() {
                    const codeBlocks = document.querySelectorAll('pre code.copy-code');
                    codeBlocks.forEach(function(codeBlock) {
                        const pre = codeBlock.parentElement;
                        if (pre.querySelector('.copy-btn')) return; // Already has button
                        
                        const button = document.createElement('button');
                        button.className = 'copy-btn';
                        button.innerHTML = '📋';
                        button.title = 'Copy to clipboard';
                        button.style.cssText = `
                            position: absolute;
                            top: 8px;
                            right: 8px;
                            background: rgba(0,0,0,0.6);
                            color: white;
                            border: none;
                            border-radius: 4px;
                            padding: 4px 8px;
                            cursor: pointer;
                            font-size: 12px;
                            z-index: 10;
                        `;
                        
                        button.addEventListener('click', function() {
                            const text = codeBlock.textContent;
                            navigator.clipboard.writeText(text).then(function() {
                                button.innerHTML = '✅';
                                button.style.background = 'rgba(40,167,69,0.8)';
                                setTimeout(function() {
                                    button.innerHTML = '📋';
                                    button.style.background = 'rgba(0,0,0,0.6)';
                                }, 2000);
                            }).catch(function() {
                                // Fallback for older browsers
                                const textarea = document.createElement('textarea');
                                textarea.value = text;
                                document.body.appendChild(textarea);
                                textarea.select();
                                document.execCommand('copy');
                                document.body.removeChild(textarea);
                                button.innerHTML = '✅';
                                setTimeout(function() {
                                    button.innerHTML = '📋';
                                }, 2000);
                            });
                        });
                        
                        pre.appendChild(button);
                    });
                });
            """)
            
            return Div(
                copy_script,
                pip.display_revert_widget(
                    step_id=step_id,
                    app_name=app_name,
                    message="Command Sequence Generated",
                    widget=experience_widget,
                    steps=self.steps
                ),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )

    # --- STEP_METHODS_INSERTION_POINT ---
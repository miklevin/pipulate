# File: plugins/515_dev_assistant.py
import asyncio
from collections import namedtuple
from datetime import datetime
from fasthtml.common import * # type: ignore
from loguru import logger
import inspect
from pathlib import Path
import re
import json
import os
from starlette.responses import HTMLResponse

ROLES = ['Developer'] # Defines which user roles can see this plugin

Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None, None, None, False, None))

def derive_public_endpoint_from_filename(filename_str: str) -> str:
    """Derives the public endpoint name from the filename (e.g., "010_my_flow.py" -> "my_flow")."""
    filename_part_no_ext = Path(filename_str).stem
    return re.sub(r"^\d+_", "", filename_part_no_ext)

class DevAssistant:
    """
    Pipulate Development Assistant
    
    Interactive debugging and development guidance tool that helps developers:
    - Validate workflow patterns against the Ultimate Pipulate Guide
    - Debug common implementation issues
    - Check plugin structure and naming conventions
    - Analyze workflow state and step progression
    - Provide pattern-specific recommendations
    - Check template suitability and marker compatibility
    
    This assistant implements the 25 critical patterns from the Ultimate Pipulate Guide
    and provides real-time validation and debugging assistance for Pipulate development.
    """
    APP_NAME = 'dev_assistant' 
    DISPLAY_NAME = 'Development Assistant' 
    ENDPOINT_MESSAGE = """Interactive debugging and development guidance for Pipulate workflows. Validate patterns, debug issues, check template suitability, and get expert recommendations based on the Ultimate Pipulate Implementation Guide and workflow creation helper system."""
    TRAINING_PROMPT = """You are the Pipulate Development Assistant. Help developers with: 1. Pattern validation against the 25 critical patterns from the Ultimate Guide. 2. Debugging workflow issues (auto-key generation, three-phase logic, chain reactions). 3. Plugin structure analysis and recommendations. 4. State management troubleshooting. 5. Template suitability and marker compatibility for helper tools. 6. Best practice guidance for workflow development. Always reference specific patterns from the Ultimate Guide and provide actionable debugging steps."""

    def __init__(self, app, pipulate, pipeline, db, app_name=None):
        self.app = app
        self.app_name = self.APP_NAME 
        self.pipulate = pipulate
        self.pipeline = pipeline 
        self.db = db 
        pip = self.pipulate 
        self.message_queue = pip.get_message_queue()
        
        self.steps = [
            Step(id='step_01', done='plugin_analysis', show='1. Plugin Analysis', refill=False),
            Step(id='step_02', done='pattern_validation', show='2. Pattern Validation', refill=False),
            Step(id='step_03', done='debug_assistance', show='3. Debug Assistance', refill=False),
            Step(id='step_04', done='recommendations', show='4. Recommendations', refill=False),
            Step(id='finalize', done='finalized', show='Finalize Analysis', refill=False) 
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

        await self.message_queue.add(pip, f'Development Assistant Session: {pipeline_id}', verbatim=True, spaces_before=0)
        
        first_step_id = self.steps[0].id
        return Div(Div(id=first_step_id, hx_get=f'/{internal_app_name}/{first_step_id}', hx_trigger='load'), id=f'{internal_app_name}-container')

    async def finalize(self, request):
        pip, db, app_name = self.pipulate, self.db, self.APP_NAME
        pipeline_id = db.get('pipeline_id', 'unknown')
        
        if request.method == 'POST':
            await pip.set_step_data(pipeline_id, 'finalize', {'finalized': True}, self.steps)
            await self.message_queue.add(pip, 'Development analysis session finalized.', verbatim=True)
            return pip.rebuild(app_name, self.steps)
        
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data:
            return Card(
                H3('🔒 Analysis Session Finalized'),
                P('This development analysis session is complete.'),
                Form(
                    Button('🔓 Unfinalize', type='submit', cls='secondary'),
                    hx_post=f'/{app_name}/unfinalize',
                    hx_target=f'#{app_name}-container'
                ),
                id='finalize'
            )
        else:
            return Card(
                H3('Finalize Development Analysis'),
                P('Complete this development analysis session.'),
                Form(
                    Button('🔒 Finalize', type='submit', cls='primary'),
                    hx_post=f'/{app_name}/finalize',
                    hx_target=f'#{app_name}-container'
                ),
                id='finalize'
            )

    async def unfinalize(self, request):
        pip, db, app_name = self.pipulate, self.db, self.APP_NAME
        pipeline_id = db.get('pipeline_id', 'unknown')
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, 'Development analysis session unlocked for editing.', verbatim=True)
        return pip.rebuild(app_name, self.steps)

    async def handle_revert(self, request):
        pip, db, app_name = self.pipulate, self.db, self.APP_NAME
        form = await request.form()
        step_id = form.get('step_id')
        pipeline_id = db.get('pipeline_id', 'unknown')
        
        if not step_id:
            return P('Error: No step specified for revert.', style=pip.get_style('error'))
        
        await pip.clear_steps_from(pipeline_id, step_id, self.steps)
        
        state = pip.read_state(pipeline_id)
        state['_revert_target'] = step_id
        pip.write_state(pipeline_id, state)
        
        await self.message_queue.add(pip, f'Reverted to {step_id} for re-analysis.', verbatim=True)
        
        return pip.rebuild(app_name, self.steps)

    def analyze_plugin_file(self, file_path):
        """Analyze a plugin file for common patterns, issues, and template suitability."""
        if not file_path.exists():
            return {"error": f"File not found: {file_path}"}
        
        content = file_path.read_text()
        filename = file_path.name
        analysis = {
            "file_path": str(file_path),
            "filename": filename,
            "patterns_found": [],
            "issues": [],
            "recommendations": [],
            "coding_assistant_prompts": [],  # New: Detailed fix instructions
            "template_suitability": {
                "as_template_source": False,
                "as_splice_target": False, 
                "as_swap_source": True,  # Default true, most workflows can be swap sources
                "as_swap_target": False,
                "missing_requirements": []
            }
        }
        
        # Check for auto-key generation pattern (Priority 1)
        if 'HX-Refresh' in content and 'not user_input' in content:
            analysis["patterns_found"].append("✅ Auto-key generation pattern detected")
        else:
            analysis["issues"].append("❌ Missing auto-key generation pattern (Priority 1)")
            analysis["recommendations"].append("Add HX-Refresh response for empty input in init() method")
            analysis["coding_assistant_prompts"].append(
                f"Add auto-key generation pattern to {filename}:\n"
                f"In the init() method, add this code after getting user_input_key:\n\n"
                f"```python\n"
                f"if not user_input_key:\n"
                f"    from starlette.responses import Response\n"
                f"    response = Response('')\n"
                f"    response.headers['HX-Refresh'] = 'true'\n"
                f"    return response\n"
                f"```\n\n"
                f"This should be placed right after the line: user_input_key = form.get('pipeline_id', '').strip()"
            )
        
        # Check for three-phase pattern (Priority 2)
        if 'finalized' in content and '_revert_target' in content:
            analysis["patterns_found"].append("✅ Three-phase step pattern detected")
        else:
            analysis["issues"].append("❌ Missing three-phase step pattern (Priority 2)")
            analysis["recommendations"].append("Implement finalize/revert/input phases in step handlers")
            analysis["coding_assistant_prompts"].append(
                f"Add three-phase step pattern to {filename}:\n"
                f"Update each step handler (step_01, step_02, etc.) to check three phases:\n\n"
                f"```python\n"
                f"# In each step_XX method, add these checks:\n"
                f"finalize_data = pip.get_step_data(pipeline_id, 'finalize', {{}})\n"
                f"if 'finalized' in finalize_data:\n"
                f"    # Return finalized view\n"
                f"    return Div(\n"
                f"        Card(H3(f'🔒 {{step.show}}: Complete')),\n"
                f"        Div(id=next_step_id, hx_get=f'/{{app_name}}/{{next_step_id}}', hx_trigger='load'),\n"
                f"        id=step_id\n"
                f"    )\n"
                f"elif user_val and state.get('_revert_target') != step_id:\n"
                f"    # Return completed view with revert option\n"
                f"    return pip.chain_reverter(step_id, step_index, steps, app_name, processed_val)\n"
                f"else:\n"
                f"    # Return input form\n"
                f"```"
            )
        
        # Check for chain reaction pattern (Priority 6)
        if 'hx_trigger=\'load\'' in content or 'hx_trigger="load"' in content:
            analysis["patterns_found"].append("✅ Chain reaction pattern detected")
        else:
            analysis["issues"].append("❌ Missing chain reaction pattern (Priority 6)")
            analysis["recommendations"].append("Add hx_trigger='load' to completed step views")
            analysis["coding_assistant_prompts"].append(
                f"Add chain reaction pattern to {filename}:\n"
                f"In step submit handlers, ensure the response includes hx_trigger='load':\n\n"
                f"```python\n"
                f"# In step_XX_submit methods, return:\n"
                f"return pip.chain_reverter(\n"
                f"    step_id=step_id,\n"
                f"    step_index=step_index,\n"
                f"    steps=steps,\n"
                f"    app_name=app_name,\n"
                f"    processed_val=processed_value\n"
                f")\n"
                f"```\n\n"
                f"Or manually create the pattern:\n"
                f"```python\n"
                f"return Div(\n"
                f"    pip.display_revert_header(step_id, app_name, steps, f'{{step.show}}: {{value}}'),\n"
                f"    Div(id=next_step_id, hx_get=f'/{{app_name}}/{{next_step_id}}', hx_trigger='load'),\n"
                f"    id=step_id\n"
                f")\n"
                f"```"
            )
        
        # Check for request parameter (Priority 7)
        if 'async def' in content and 'request' in content:
            analysis["patterns_found"].append("✅ Request parameter pattern detected")
        else:
            analysis["issues"].append("❌ Missing request parameters (Priority 7)")
            analysis["recommendations"].append("All route handlers must accept request parameter")
            analysis["coding_assistant_prompts"].append(
                f"Add request parameters to all route handlers in {filename}:\n"
                f"Update all method signatures to include request parameter:\n\n"
                f"```python\n"
                f"async def landing(self, request):  # Add request parameter\n"
                f"async def init(self, request):     # Add request parameter\n"
                f"async def step_01(self, request): # Add request parameter\n"
                f"async def step_01_submit(self, request): # Add request parameter\n"
                f"async def finalize(self, request): # Add request parameter\n"
                f"# ... and so on for all route handler methods\n"
                f"```\n\n"
                f"The request object provides access to form data, query params, and headers."
            )

        # Template Assembly Marker Analysis
        steps_insertion_marker = "--- STEPS_LIST_INSERTION_POINT ---"
        methods_insertion_marker = "--- STEP_METHODS_INSERTION_POINT ---"
        
        has_steps_marker = steps_insertion_marker in content
        has_methods_marker = methods_insertion_marker in content
        
        if has_steps_marker:
            analysis["patterns_found"].append("✅ STEPS_LIST_INSERTION_POINT marker found")
        else:
            analysis["template_suitability"]["missing_requirements"].append("STEPS_LIST_INSERTION_POINT marker")
            analysis["coding_assistant_prompts"].append(
                f"Add STEPS_LIST_INSERTION_POINT marker to {filename}:\n"
                f"In the self.steps definition, add the marker before the finalize step:\n\n"
                f"```python\n"
                f"self.steps = [\n"
                f"    Step(id='step_01', done='data_01', show='Step 1', refill=False),\n"
                f"    Step(id='step_02', done='data_02', show='Step 2', refill=False),\n"
                f"    # Add any other existing steps here\n"
                f"    {steps_insertion_marker}\n"
                f"    Step(id='finalize', done='finalized', show='Finalize Workflow', refill=False)\n"
                f"]\n"
                f"```\n\n"
                f"CRITICAL: The marker must be at the same indentation level as the Step definitions and placed immediately before the finalize step."
            )
            
        if has_methods_marker:
            analysis["patterns_found"].append("✅ STEP_METHODS_INSERTION_POINT marker found")  
        else:
            analysis["template_suitability"]["missing_requirements"].append("STEP_METHODS_INSERTION_POINT marker")
            analysis["coding_assistant_prompts"].append(
                f"Add STEP_METHODS_INSERTION_POINT marker to {filename}:\n"
                f"At the end of the class, after all existing step methods, add:\n\n"
                f"```python\n"
                f"class YourWorkflow:\n"
                f"    # ... existing methods ...\n"
                f"    \n"
                f"    async def existing_step_method(self, request):\n"
                f"        # ... existing implementation ...\n"
                f"        pass\n"
                f"    \n"
                f"    {methods_insertion_marker}\n"
                f"```\n\n"
                f"CRITICAL: The marker must be at class level (4 spaces indentation) and placed after all existing step methods but before the class ends."
            )

        # Standard class attributes check
        required_attributes = ["APP_NAME", "DISPLAY_NAME", "ENDPOINT_MESSAGE", "TRAINING_PROMPT"]
        missing_attributes = []
        
        for attr in required_attributes:
            if f'{attr} =' in content:
                analysis["patterns_found"].append(f"✅ {attr} attribute found")
            else:
                missing_attributes.append(attr)
                analysis["template_suitability"]["missing_requirements"].append(f"{attr} class attribute")
        
        if missing_attributes:
            analysis["coding_assistant_prompts"].append(
                f"Add missing class attributes to {filename}:\n"
                f"Add these attributes at the top of the class definition:\n\n"
                f"```python\n"
                f"class YourWorkflow:\n" +
                ''.join([
                    f"    {attr} = 'your_{attr.lower()}_value'  # Replace with appropriate value\n"
                    for attr in missing_attributes
                ]) +
                f"    \n"
                f"    def __init__(self, ...):\n"
                f"        # ... existing code ...\n"
                f"```\n\n"
                f"Replace the placeholder values:\n" +
                '\n'.join([
                    f"- {attr}: " + {
                        'APP_NAME': 'Internal workflow ID (stable, never change after deployment)',
                        'DISPLAY_NAME': 'User-facing workflow name',
                        'ENDPOINT_MESSAGE': 'Description shown on landing page',
                        'TRAINING_PROMPT': 'LLM context prompt for this workflow'
                    }.get(attr, 'Appropriate value for this attribute')
                    for attr in missing_attributes
                ])
            )
        
        # UI Constants check
        if 'UI_CONSTANTS' in content:
            analysis["patterns_found"].append("✅ UI_CONSTANTS for styling found")
        else:
            analysis["template_suitability"]["missing_requirements"].append("UI_CONSTANTS for styling consistency")
            analysis["coding_assistant_prompts"].append(
                f"Add UI_CONSTANTS to {filename}:\n"
                f"Add styling constants at the top of the class for consistent appearance:\n\n"
                f"```python\n"
                f"class YourWorkflow:\n"
                f"    # UI Constants - Centralized control for global appearance\n"
                f"    UI_CONSTANTS = {{\n"
                f"        'COLORS': {{\n"
                f"            'HEADER_TEXT': '#2c3e50',\n"
                f"            'BODY_TEXT': '#5a6c7d',\n"
                f"            'ACCENT_BLUE': '#007bff',\n"
                f"            'SUCCESS_GREEN': '#28a745',\n"
                f"        }},\n"
                f"        'BACKGROUNDS': {{\n"
                f"            'LIGHT_GRAY': '#f1f5f9',\n"
                f"            'LIGHT_BLUE': '#f0f8ff',\n"
                f"        }},\n"
                f"        'SPACING': {{\n"
                f"            'SECTION_PADDING': '0.75rem',\n"
                f"            'BORDER_RADIUS': '4px',\n"
                f"            'MARGIN_BOTTOM': '1rem',\n"
                f"        }}\n"
                f"    }}\n"
                f"    \n"
                f"    def __init__(self, ...):\n"
                f"        # ... existing code ...\n"
                f"```"
            )

        # Step method naming convention check
        step_methods = re.findall(r'async def (step_\d+)(?:_submit)?\(', content)
        if step_methods:
            analysis["patterns_found"].append(f"✅ Step methods found: {len(set(step_methods))} unique steps")
            # Check for proper step pairs (GET and POST handlers)
            step_numbers = set(re.findall(r'step_(\d+)', ' '.join(step_methods)))
            missing_handlers = []
            for num in step_numbers:
                has_get = f'step_{num}(' in content
                has_post = f'step_{num}_submit(' in content
                if has_get and has_post:
                    analysis["patterns_found"].append(f"✅ Step {num} has both GET and POST handlers")
                else:
                    missing_type = 'GET' if not has_get else 'POST'
                    analysis["issues"].append(f"❌ Step {num} missing {missing_type} handler")
                    missing_handlers.append((num, missing_type))
            
            if missing_handlers:
                handler_code = []
                for num, handler_type in missing_handlers:
                    if handler_type == 'GET':
                        handler_code.append(f"""
    async def step_{num}(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_{num}'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {{}})
        user_val = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {{}})
        
        if 'finalized' in finalize_data:
            return Div(
                Card(H3(f'🔒 {{step.show}}: Complete')),
                Div(id=next_step_id, hx_get=f'/{{app_name}}/{{next_step_id}}', hx_trigger='load'),
                id=step_id
            )
        elif user_val and state.get('_revert_target') != step_id:
            return pip.chain_reverter(step_id, step_index, steps, app_name, user_val)
        else:
            return Div(
                Card(
                    H3(f'{{step.show}}'),
                    P('Step implementation needed here.'),
                    Form(
                        # Add your form fields here
                        Button('Submit ▸', type='submit'),
                        hx_post=f'/{{app_name}}/{{step_id}}_submit',
                        hx_target=f'#{{step_id}}'
                    )
                ),
                Div(id=next_step_id),
                id=step_id
            )""")
                    else:  # POST handler
                        handler_code.append(f"""
    async def step_{num}_submit(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_{num}'
        step_index = self.steps_indices[step_id]
        pipeline_id = db.get('pipeline_id', 'unknown')
        
        form = await request.form()
        # Process form data here
        user_input = form.get('field_name', '').strip()
        
        # Store step data
        await pip.set_step_data(pipeline_id, step_id, user_input, steps)
        
        return pip.chain_reverter(step_id, step_index, steps, app_name, user_input)""")
                
                analysis["coding_assistant_prompts"].append(
                    f"Add missing step handlers to {filename}:\n"
                    f"Add these missing method(s):\n\n"
                    f"```python" + ''.join(handler_code) + "\n```"
                )
        
        # Finalize step check
        if 'finalize(' in content:
            analysis["patterns_found"].append("✅ Finalize step handler found")
        else:
            analysis["issues"].append("❌ Missing finalize step handler")
            analysis["recommendations"].append("Add finalize step handler for workflow completion")
            analysis["coding_assistant_prompts"].append(
                f"Add finalize step handler to {filename}:\n"
                f"Add this method to handle workflow finalization:\n\n"
                f"```python\n"
                f"async def finalize(self, request):\n"
                f"    pip, db, app_name = self.pipulate, self.db, self.APP_NAME\n"
                f"    pipeline_id = db.get('pipeline_id', 'unknown')\n"
                f"    \n"
                f"    if request.method == 'POST':\n"
                f"        await pip.set_step_data(pipeline_id, 'finalize', {{'finalized': True}}, self.steps)\n"
                f"        await self.message_queue.add(pip, 'Workflow finalized.', verbatim=True)\n"
                f"        return pip.rebuild(app_name, self.steps)\n"
                f"    \n"
                f"    finalize_data = pip.get_step_data(pipeline_id, 'finalize', {{}})\n"
                f"    if 'finalized' in finalize_data:\n"
                f"        return Card(\n"
                f"            H3('🔒 Workflow Finalized'),\n"
                f"            P('This workflow is complete.'),\n"
                f"            Form(\n"
                f"                Button('🔓 Unfinalize', type='submit', cls='secondary'),\n"
                f"                hx_post=f'/{{app_name}}/unfinalize',\n"
                f"                hx_target=f'#{{app_name}}-container'\n"
                f"            ),\n"
                f"            id='finalize'\n"
                f"        )\n"
                f"    else:\n"
                f"        return Card(\n"
                f"            H3('Finalize Workflow'),\n"
                f"            P('Complete this workflow.'),\n"
                f"            Form(\n"
                f"                Button('🔒 Finalize', type='submit', cls='primary'),\n"
                f"                hx_post=f'/{{app_name}}/finalize',\n"
                f"                hx_target=f'#{{app_name}}-container'\n"
                f"            ),\n"
                f"            id='finalize'\n"
                f"        )\n"
                f"```"
            )

        # Template Suitability Assessment
        suitability = analysis["template_suitability"]
        
        # Template Source Requirements: markers + attributes + UI_CONSTANTS
        if has_steps_marker and has_methods_marker and len(missing_attributes) == 0:
            suitability["as_template_source"] = True
            analysis["patterns_found"].append("🎯 SUITABLE AS TEMPLATE SOURCE")
        else:
            analysis["recommendations"].append("To use as template source: Add missing markers and class attributes")
            
        # Splice Target Requirements: both markers required
        if has_steps_marker and has_methods_marker:
            suitability["as_splice_target"] = True 
            analysis["patterns_found"].append("🔧 SUITABLE AS SPLICE TARGET")
        else:
            analysis["recommendations"].append("To use as splice target: Add both insertion point markers")
            
        # Swap Target Requirements: must have step methods to replace
        if step_methods:
            suitability["as_swap_target"] = True
            analysis["patterns_found"].append("🔄 SUITABLE AS SWAP TARGET") 
        else:
            suitability["as_swap_target"] = False
            analysis["recommendations"].append("To use as swap target: Add step methods with proper naming")

        # Atomic Transplantation Markers (Optional)
        atomic_markers = [
            "START_WORKFLOW_SECTION:",
            "SECTION_STEP_DEFINITION",
            "END_SECTION_STEP_DEFINITION", 
            "SECTION_STEP_METHODS",
            "END_SECTION_STEP_METHODS",
            "END_WORKFLOW_SECTION"
        ]
        
        found_atomic_markers = [marker for marker in atomic_markers if marker in content]
        if found_atomic_markers:
            analysis["patterns_found"].append(f"✅ Atomic transplantation markers: {len(found_atomic_markers)}/6")
            if len(found_atomic_markers) == 6:
                analysis["patterns_found"].append("🧬 SUITABLE FOR ATOMIC TRANSPLANTATION")
        
        return analysis

    async def step_01(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        # Get the actual plugin filename that was analyzed
        # The step_data structure is now: {'plugin_analysis': filename, 'analysis_results': {...}}
        user_val = step_data.get(step.done, '') if step_data else ''
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        
        if 'finalized' in finalize_data:
            return Div(
                Card(H3(f'🔒 {step.show}: Analysis Complete')),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        elif user_val and state.get('_revert_target') != step_id:
            return Div(
                pip.display_revert_header(step_id, app_name, steps, f'{step.show}: {user_val}'),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        else:
            # Get list of plugin files
            plugins_dir = Path("plugins")
            plugin_files = []
            if plugins_dir.exists():
                plugin_files = [f.name for f in plugins_dir.glob("*.py") if not f.name.startswith("__")]
            
            return Div(
                Card(
                    H3(f'{step.show}'),
                    P('Select a plugin file to analyze for pattern compliance and issues:'),
                    Form(
                        Select(
                            Option("Select a plugin file...", value="", selected=True),
                            *[Option(f, value=f) for f in sorted(plugin_files)],
                            name=step.done,
                            required=True
                        ),
                        Button('Analyze Plugin ▸', type='submit'),
                        hx_post=f'/{app_name}/{step_id}_submit',
                        hx_target=f'#{step_id}'
                    )
                ),
                Div(id=next_step_id),
                id=step_id
            )

    async def step_01_submit(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        pipeline_id = db.get('pipeline_id', 'unknown')
        
        form = await request.form()
        selected_file = form.get('plugin_analysis', '').strip()
        
        if not selected_file:
            return P('Please select a plugin file to analyze.', style=pip.get_style('error'))
        
        # Analyze the selected plugin
        file_path = Path("plugins") / selected_file
        analysis = self.analyze_plugin_file(file_path)
        
        # Store the filename as the step value, and analysis results separately
        await pip.set_step_data(pipeline_id, step_id, selected_file, steps)
        
        # Store analysis results in the step data
        state = pip.read_state(pipeline_id)
        if step_id not in state:
            state[step_id] = {}
        state[step_id]['analysis_results'] = analysis
        pip.write_state(pipeline_id, state)
        
        await self.message_queue.add(pip, f'Analyzed plugin: {selected_file}', verbatim=True)
        
        return pip.chain_reverter(step_id, step_index, steps, app_name, f'Analyzed: {selected_file}')

    async def step_02(self, request):
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
        
        # Get analysis from step 1
        step_01_data = pip.get_step_data(pipeline_id, 'step_01', {})
        analysis_results = step_01_data.get('analysis_results', {})
        
        if 'finalized' in finalize_data:
            return Div(
                Card(H3(f'🔒 {step.show}: Validation Complete')),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        elif user_val and state.get('_revert_target') != step_id:
            return Div(
                pip.display_revert_header(step_id, app_name, steps, f'{step.show}: Patterns Validated'),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        else:
            # Check if step 1 has been completed by looking for plugin_analysis
            if not step_01_data.get('plugin_analysis'):
                return Div(
                    Card(
                        H3(f'{step.show}'),
                        P('Please complete Plugin Analysis first.', style='color: orange;')
                    ),
                    Div(id=next_step_id),
                    id=step_id
                )
            
            # Display comprehensive pattern validation results
            patterns_found = analysis_results.get('patterns_found', [])
            issues = analysis_results.get('issues', [])
            template_suitability = analysis_results.get('template_suitability', {})
            coding_prompts = analysis_results.get('coding_assistant_prompts', [])
            filename = analysis_results.get('filename', 'unknown')
            
            # Create suitability status display
            suitability_items = []
            if template_suitability.get('as_template_source'):
                suitability_items.append(Li("🎯 Template Source: ✅ Ready", style='color: green;'))
            else:
                suitability_items.append(Li("🎯 Template Source: ❌ Missing requirements", style='color: red;'))
                
            if template_suitability.get('as_splice_target'):
                suitability_items.append(Li("🔧 Splice Target: ✅ Ready", style='color: green;'))
            else:
                suitability_items.append(Li("🔧 Splice Target: ❌ Missing markers", style='color: red;'))
                
            if template_suitability.get('as_swap_target'):
                suitability_items.append(Li("🔄 Swap Target: ✅ Ready", style='color: green;'))
            else:
                suitability_items.append(Li("🔄 Swap Target: ❌ No step methods", style='color: red;'))
                
            if template_suitability.get('as_swap_source'):
                suitability_items.append(Li("📤 Swap Source: ✅ Ready", style='color: green;'))
            else:
                suitability_items.append(Li("📤 Swap Source: ❌ No step methods", style='color: red;'))
            
            missing_reqs = template_suitability.get('missing_requirements', [])
            
            # Define widget ID for Prism targeting
            widget_id = f"dev-assistant-{pipeline_id.replace('-', '_')}-{step_id}"
            
            # Build coding assistant section
            coding_section = []
            if coding_prompts:
                coding_section.extend([
                    Details(
                        Summary(
                            H4('🤖 Coding Assistant Fix Instructions', style='display: inline; margin: 0;'),
                            style='cursor: pointer; padding: 1rem; background-color: #f8f9fa; border-radius: 4px; margin: 1rem 0;'
                        ),
                        Div(
                            P(f'Copy these detailed instructions for a coding assistant to fix {filename}:', 
                              style='margin-bottom: 1rem; font-weight: bold; color: #2c3e50;'),
                            Div(
                                *[
                                    Div(
                                        H5(f'Fix #{i+1}:', style='color: #007bff; margin-top: 1.5rem; margin-bottom: 0.5rem;'),
                                        Pre(
                                            Code(prompt, cls='language-markdown'),
                                            cls='line-numbers'
                                        ),
                                        style='margin-bottom: 1rem;'
                                    )
                                    for i, prompt in enumerate(coding_prompts)
                                ],
                                id=widget_id  # Add the widget ID here for Prism targeting
                            ),
                            style='padding: 1rem;'
                        ),
                        style='margin: 1rem 0;'
                    )
                ])
            
            response_content = Div(
                Card(
                    H3(f'{step.show}'),
                    H4('✅ Patterns Found:'),
                    Ul(*[Li(pattern) for pattern in patterns_found]) if patterns_found else P('No patterns detected.'),
                    H4('❌ Issues Found:'),
                    Ul(*[Li(issue, style='color: red;') for issue in issues]) if issues else P('No issues found!', style='color: green;'),
                    H4('🎯 Template & Helper Tool Compatibility:'),
                    Ul(*suitability_items),
                    H4('📋 Missing Requirements:') if missing_reqs else None,
                    Ul(*[Li(req, style='color: orange;') for req in missing_reqs]) if missing_reqs else None,
                    *coding_section,
                    Form(
                        Button('Continue to Debug Assistance ▸', type='submit'),
                        hx_post=f'/{app_name}/{step_id}_submit',
                        hx_target=f'#{step_id}'
                    )
                ),
                # Add Prism initialization script (following 850_prism.py pattern)
                Script(f"""
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
                """, type='text/javascript'),
                Div(id=next_step_id),
                id=step_id
            )
            
            # Return HTMLResponse with HX-Trigger for Prism initialization (following 850_prism.py pattern)
            response = HTMLResponse(to_xml(response_content))
            response.headers['HX-Trigger'] = json.dumps({'initializePrism': {'targetId': widget_id}})
            return response

    async def step_02_submit(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        pipeline_id = db.get('pipeline_id', 'unknown')
        
        await pip.set_step_data(pipeline_id, step_id, 'complete', steps)
        await self.message_queue.add(pip, 'Pattern validation completed.', verbatim=True)
        
        return pip.chain_reverter(step_id, step_index, steps, app_name, 'Patterns Validated')

    async def step_03(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_03'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        
        # Get analysis from step 1
        step_01_data = pip.get_step_data(pipeline_id, 'step_01', {})
        analysis_results = step_01_data.get('analysis_results', {})
        
        if 'finalized' in finalize_data:
            return Div(
                Card(H3(f'🔒 {step.show}: Debug Complete')),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        elif user_val and state.get('_revert_target') != step_id:
            return Div(
                pip.display_revert_header(step_id, app_name, steps, f'{step.show}: Debug Guidance Provided'),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        else:
            # Check if step 1 has been completed by looking for plugin_analysis
            if not step_01_data.get('plugin_analysis'):
                return Div(
                    Card(
                        H3(f'{step.show}'),
                        P('Please complete Plugin Analysis first.', style='color: orange;')
                    ),
                    Div(id=next_step_id),
                    id=step_id
                )
            
            recommendations = analysis_results.get('recommendations', [])
            coding_prompts = analysis_results.get('coding_assistant_prompts', [])
            filename = analysis_results.get('filename', 'unknown')
            
            debug_checklist = [
                "✅ Auto-key generation: Empty input returns HX-Refresh?",
                "✅ Three-phase logic: Correct order (finalized → revert → input)?",
                "✅ Chain reaction: All completed phases have hx_trigger='load'?",
                "✅ Request parameters: All handlers accept request?",
                "✅ State management: Using pip.get_step_data/set_step_data?",
                "✅ Step definition: Finalize step included in steps list?",
                "✅ Route registration: All routes properly registered in __init__?",
                "✅ File naming: Plugin file follows naming convention?",
                "✅ Template markers: Both insertion point markers present?",
                "✅ Class attributes: APP_NAME, DISPLAY_NAME, etc. defined?",
                "✅ UI Constants: Styling constants defined for consistency?"
            ]
            
            # Build implementation guidance section
            implementation_section = []
            if coding_prompts:
                implementation_section.extend([
                    H4('🛠️ Implementation Guidance:'),
                    P(f'For {filename}, detailed fix instructions are available in Step 2 (Pattern Validation).', 
                      style='color: #007bff; font-style: italic;'),
                    P('Each issue has been analyzed with specific code snippets and placement instructions for a coding assistant.',
                      style='color: #495057; margin-bottom: 1rem;'),
                    Details(
                        Summary('💡 Quick Implementation Tips', style='cursor: pointer; font-weight: bold; color: #2c3e50;'),
                        Ul(
                            Li('🔄 Use pip.chain_reverter() in submit handlers for automatic chain reactions'),
                            Li('🎯 Add both template markers for helper tool compatibility'),
                            Li('📝 Follow three-phase pattern: finalized → revert → input'),
                            Li('🔑 Always include request parameter in route handlers'),
                            Li('🎨 Define UI_CONSTANTS for consistent styling'),
                            Li('📋 Include all required class attributes for template use')
                        ),
                        style='margin: 1rem 0;'
                    )
                ])
            
            return Div(
                Card(
                    H3(f'{step.show}'),
                    H4('🔧 Debugging Checklist:'),
                    Ul(*[Li(item) for item in debug_checklist]),
                    *implementation_section,
                    H4('💡 General Recommendations:'),
                    Ul(*[Li(rec, style='color: blue;') for rec in recommendations]) if recommendations else P('No general recommendations.'),
                    Form(
                        Button('Continue to Final Recommendations ▸', type='submit'),
                        hx_post=f'/{app_name}/{step_id}_submit',
                        hx_target=f'#{step_id}'
                    )
                ),
                Div(id=next_step_id),
                id=step_id
            )

    async def step_03_submit(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_03'
        step_index = self.steps_indices[step_id]
        pipeline_id = db.get('pipeline_id', 'unknown')
        
        await pip.set_step_data(pipeline_id, step_id, 'complete', steps)
        await self.message_queue.add(pip, 'Debug assistance provided.', verbatim=True)
        
        return pip.chain_reverter(step_id, step_index, steps, app_name, 'Debug Guidance Provided')

    async def step_04(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_04'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        
        if 'finalized' in finalize_data:
            return Div(
                Card(H3(f'🔒 {step.show}: Recommendations Complete')),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        elif user_val and state.get('_revert_target') != step_id:
            return Div(
                pip.display_revert_header(step_id, app_name, steps, f'{step.show}: Expert Guidance Provided'),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        else:
            # Get analysis from step 1 for consistency
            step_01_data = pip.get_step_data(pipeline_id, 'step_01', {})
            analysis_results = step_01_data.get('analysis_results', {})
            coding_prompts = analysis_results.get('coding_assistant_prompts', [])
            filename = analysis_results.get('filename', 'unknown')
            
            # Check if step 1 has been completed by looking for plugin_analysis
            if not step_01_data.get('plugin_analysis'):
                return Div(
                    Card(
                        H3(f'{step.show}'),
                        P('Please complete Plugin Analysis first.', style='color: orange;')
                    ),
                    Div(id=next_step_id),
                    id=step_id
                )
            
            expert_recommendations = [
                "📚 Study the Ultimate Pipulate Guide patterns (all 25 priorities)",
                "🔧 Use the Workflow Genesis plugin for new workflow creation",
                "🧪 Test auto-key generation by hitting Enter on empty input",
                "🔄 Verify chain reactions work by completing steps in sequence",
                "📝 Follow the three-phase pattern in all step handlers",
                "🎯 Use pip.chain_reverter() helper in POST handlers",
                "🔍 Enable debug mode in server.py for detailed logging",
                "📖 Reference the helper scripts for workflow scaffolding"
            ]
            
            # Add implementation strategy section
            implementation_strategy = []
            if coding_prompts:
                implementation_strategy.extend([
                    H4('🤖 Implementation Strategy:'),
                    Div(
                        P(f'✨ This analysis has generated {len(coding_prompts)} detailed fix instruction(s) for {filename}',
                          style='color: #28a745; font-weight: bold; margin-bottom: 0.5rem;'),
                        P('These instructions in Step 2 are specifically designed for coding assistants and include:',
                          style='margin-bottom: 0.5rem;'),
                        Ul(
                            Li('📂 Exact filenames and placement locations'),
                            Li('💻 Complete code snippets ready to copy'),
                            Li('🎯 Specific implementation requirements'),
                            Li('🔧 Step-by-step modification instructions'),
                            Li('⚠️ Critical placement and indentation notes')
                        ),
                        P('💡 Copy the instructions from Step 2 and provide them to your coding assistant for precise implementation.',
                          style='color: #007bff; font-style: italic; margin-top: 1rem;'),
                        style='background-color: #f8f9fa; padding: 1rem; border-radius: 4px; border-left: 4px solid #28a745; margin: 1rem 0;'
                    )
                ])
            
            return Div(
                Card(
                    H3(f'{step.show}'),
                    *implementation_strategy,
                    H4('🎯 Expert Development Recommendations:'),
                    Ul(*[Li(rec) for rec in expert_recommendations]),
                    H4('📚 Key Resources:'),
                    Ul(
                        Li(A('Ultimate Pipulate Guide Part 1', href='/docs/guide1', target='_blank')),
                        Li(A('Ultimate Pipulate Guide Part 2', href='/docs/guide2', target='_blank')),
                        Li(A('Ultimate Pipulate Guide Part 3', href='/docs/guide3', target='_blank')),
                        Li('Workflow Genesis Plugin (510_workflow_genesis)'),
                        Li('Helper Scripts (create_workflow.py, splice_workflow_step.py)')
                    ),
                    H4('🚀 Next Steps:'),
                    Ol(
                        Li('Use the coding assistant prompts from Step 2 to fix identified issues'),
                        Li('Test the workflow after implementing fixes'),
                        Li('Re-run this analysis to verify improvements'),
                        Li('Consider using fixed workflow as template source for future workflows')
                    ),
                    Form(
                        Button('Complete Analysis ▸', type='submit'),
                        hx_post=f'/{app_name}/{step_id}_submit',
                        hx_target=f'#{step_id}'
                    )
                ),
                Div(id=next_step_id),
                id=step_id
            )

    async def step_04_submit(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_04'
        step_index = self.steps_indices[step_id]
        pipeline_id = db.get('pipeline_id', 'unknown')
        
        await pip.set_step_data(pipeline_id, step_id, 'complete', steps)
        await self.message_queue.add(pip, 'Expert recommendations provided. Development analysis complete.', verbatim=True)
        
        return pip.chain_reverter(step_id, step_index, steps, app_name, 'Expert Guidance Provided') 
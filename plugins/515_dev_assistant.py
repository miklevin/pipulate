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
    
    This assistant implements the 25 critical patterns from the Ultimate Pipulate Guide
    and provides real-time validation and debugging assistance for Pipulate development.
    """
    APP_NAME = 'dev_assistant' 
    DISPLAY_NAME = 'Development Assistant' 
    ENDPOINT_MESSAGE = """Interactive debugging and development guidance for Pipulate workflows. Validate patterns, debug issues, and get expert recommendations based on the Ultimate Pipulate Implementation Guide."""
    TRAINING_PROMPT = """You are the Pipulate Development Assistant. Help developers with: 1. Pattern validation against the 25 critical patterns from the Ultimate Guide. 2. Debugging workflow issues (auto-key generation, three-phase logic, chain reactions). 3. Plugin structure analysis and recommendations. 4. State management troubleshooting. 5. Best practice guidance for workflow development. Always reference specific patterns from the Ultimate Guide and provide actionable debugging steps."""

    def __init__(self, app, pipulate, pipeline, db, app_name=None):
        self.app = app
        self.app_name = self.APP_NAME 
        self.pipulate = pipulate
        self.pipeline = pipeline 
        self.db = db 
        pip = self.pipulate 
        self.message_queue = pip.get_message_queue()
        
        self.steps = [
            Step(id='step_01', done='plugin_analysis', show='1. Plugin Analysis', refill=True),
            Step(id='step_02', done='pattern_validation', show='2. Pattern Validation', refill=True),
            Step(id='step_03', done='debug_assistance', show='3. Debug Assistance', refill=True),
            Step(id='step_04', done='recommendations', show='4. Recommendations', refill=True),
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
            return pip.chain_reverter('finalize', len(self.steps) - 1, self.steps, app_name, 'Analysis Complete')
        
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data:
            return Card(
                H3('🔒 Analysis Session Finalized'),
                P('This development analysis session is complete.'),
                Form(
                    Button('🔓 Unfinalize', type='submit', cls='secondary'),
                    hx_post=f'/{app_name}/unfinalize',
                    hx_target='#finalize'
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
                    hx_target='#finalize'
                ),
                id='finalize'
            )

    async def unfinalize(self, request):
        pip, db, app_name = self.pipulate, self.db, self.APP_NAME
        pipeline_id = db.get('pipeline_id', 'unknown')
        await pip.clear_step_data(pipeline_id, 'finalize', self.steps)
        await self.message_queue.add(pip, 'Development analysis session unlocked for editing.', verbatim=True)
        return await self.finalize(request)

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
        """Analyze a plugin file for common patterns and issues."""
        if not file_path.exists():
            return {"error": f"File not found: {file_path}"}
        
        content = file_path.read_text()
        analysis = {
            "file_path": str(file_path),
            "patterns_found": [],
            "issues": [],
            "recommendations": []
        }
        
        # Check for auto-key generation pattern
        if 'HX-Refresh' in content and 'not user_input' in content:
            analysis["patterns_found"].append("✅ Auto-key generation pattern detected")
        else:
            analysis["issues"].append("❌ Missing auto-key generation pattern (Priority 1)")
            analysis["recommendations"].append("Add HX-Refresh response for empty input in init() method")
        
        # Check for three-phase pattern
        if 'finalized' in content and '_revert_target' in content:
            analysis["patterns_found"].append("✅ Three-phase step pattern detected")
        else:
            analysis["issues"].append("❌ Missing three-phase step pattern (Priority 2)")
            analysis["recommendations"].append("Implement finalize/revert/input phases in step handlers")
        
        # Check for chain reaction pattern
        if 'hx_trigger=\'load\'' in content or 'hx_trigger="load"' in content:
            analysis["patterns_found"].append("✅ Chain reaction pattern detected")
        else:
            analysis["issues"].append("❌ Missing chain reaction pattern (Priority 6)")
            analysis["recommendations"].append("Add hx_trigger='load' to completed step views")
        
        # Check for request parameter
        if 'async def' in content and 'request' in content:
            analysis["patterns_found"].append("✅ Request parameter pattern detected")
        else:
            analysis["issues"].append("❌ Missing request parameters (Priority 7)")
            analysis["recommendations"].append("All route handlers must accept request parameter")
        
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
        user_val = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        
        if 'finalized' in finalize_data:
            return Div(
                Card(H3(f'🔒 {step.show}: Analysis Complete')),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        elif user_val and state.get('_revert_target') != step_id:
            return Div(
                pip.display_revert_header(step_id, app_name, f'{step.show}: {user_val}', steps),
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
        
        await pip.set_step_data(pipeline_id, step_id, {
            'plugin_analysis': selected_file,
            'analysis_results': analysis
        }, steps)
        
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
                pip.display_revert_header(step_id, app_name, f'{step.show}: Patterns Validated', steps),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        else:
            if not analysis_results:
                return Div(
                    Card(
                        H3(f'{step.show}'),
                        P('Please complete Plugin Analysis first.', style='color: orange;')
                    ),
                    Div(id=next_step_id),
                    id=step_id
                )
            
            # Display pattern validation results
            patterns_found = analysis_results.get('patterns_found', [])
            issues = analysis_results.get('issues', [])
            
            return Div(
                Card(
                    H3(f'{step.show}'),
                    H4('✅ Patterns Found:'),
                    Ul(*[Li(pattern) for pattern in patterns_found]) if patterns_found else P('No patterns detected.'),
                    H4('❌ Issues Found:'),
                    Ul(*[Li(issue, style='color: red;') for issue in issues]) if issues else P('No issues found!', style='color: green;'),
                    Form(
                        Button('Continue to Debug Assistance ▸', type='submit'),
                        hx_post=f'/{app_name}/{step_id}_submit',
                        hx_target=f'#{step_id}'
                    )
                ),
                Div(id=next_step_id),
                id=step_id
            )

    async def step_02_submit(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        pipeline_id = db.get('pipeline_id', 'unknown')
        
        await pip.set_step_data(pipeline_id, step_id, {'pattern_validation': 'complete'}, steps)
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
                pip.display_revert_header(step_id, app_name, f'{step.show}: Debug Guidance Provided', steps),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        else:
            recommendations = analysis_results.get('recommendations', [])
            
            debug_checklist = [
                "✅ Auto-key generation: Empty input returns HX-Refresh?",
                "✅ Three-phase logic: Correct order (finalized → revert → input)?",
                "✅ Chain reaction: All completed phases have hx_trigger='load'?",
                "✅ Request parameters: All handlers accept request?",
                "✅ State management: Using pip.get_step_data/set_step_data?",
                "✅ Step definition: Finalize step included in steps list?",
                "✅ Route registration: All routes properly registered in __init__?",
                "✅ File naming: Plugin file follows naming convention?"
            ]
            
            return Div(
                Card(
                    H3(f'{step.show}'),
                    H4('🔧 Debugging Checklist:'),
                    Ul(*[Li(item) for item in debug_checklist]),
                    H4('💡 Specific Recommendations:'),
                    Ul(*[Li(rec, style='color: blue;') for rec in recommendations]) if recommendations else P('No specific recommendations.'),
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
        
        await pip.set_step_data(pipeline_id, step_id, {'debug_assistance': 'complete'}, steps)
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
                pip.display_revert_header(step_id, app_name, f'{step.show}: Expert Guidance Provided', steps),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        else:
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
            
            return Div(
                Card(
                    H3(f'{step.show}'),
                    H4('🎯 Expert Development Recommendations:'),
                    Ul(*[Li(rec) for rec in expert_recommendations]),
                    H4('📚 Key Resources:'),
                    Ul(
                        Li(A('Ultimate Pipulate Guide Part 1', href='/static/ULTIMATE_PIPULATE_GUIDE.md', target='_blank')),
                        Li(A('Ultimate Pipulate Guide Part 2', href='/static/ULTIMATE_PIPULATE_GUIDE_PART2.md', target='_blank')),
                        Li(A('Ultimate Pipulate Guide Part 3', href='/static/ULTIMATE_PIPULATE_GUIDE_PART3.md', target='_blank')),
                        Li('Workflow Genesis Plugin (510_workflow_genesis)'),
                        Li('Helper Scripts (create_workflow.py, splice_workflow_step.py)')
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
        
        await pip.set_step_data(pipeline_id, step_id, {'recommendations': 'complete'}, steps)
        await self.message_queue.add(pip, 'Expert recommendations provided. Development analysis complete.', verbatim=True)
        
        return pip.chain_reverter(step_id, step_index, steps, app_name, 'Expert Guidance Provided') 
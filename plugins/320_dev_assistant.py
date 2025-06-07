# File: plugins/320_dev_assistant.py
import asyncio
from collections import namedtuple
from datetime import datetime
from fasthtml.common import * # type: ignore
from fasthtml.common import to_xml
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
    DISPLAY_NAME = 'Development Assistant 🩺'
    ENDPOINT_MESSAGE = """Interactive debugging and development guidance for Pipulate workflows. Validate patterns, debug issues, check template suitability, and get expert recommendations based on the Ultimate Pipulate Implementation Guide and workflow creation helper system."""
    TRAINING_PROMPT = """You are the Pipulate Development Assistant. Help developers with: 1. Pattern validation against the 25 critical patterns from the Ultimate Guide. 2. Debugging workflow issues (auto-key generation, three-phase logic, chain reactions). 3. Plugin structure analysis and recommendations. 4. State management troubleshooting. 5. Template suitability and marker compatibility for helper tools. 6. Best practice guidance for workflow development. Always reference specific patterns from the Ultimate Guide and provide actionable debugging steps."""

    # UI Constants - Centralized color theme for consistent appearance
    UI_CONSTANTS = {
        'COLORS': {
            # Primary text colors
            'HEADER_TEXT': '#2c3e50',           # Dark blue-gray for headers
            'BODY_TEXT': '#CCCCCC',             # Muted gray for body text
            'SECONDARY_TEXT': '#495057',        # Slightly darker gray for secondary text

            # Semantic colors
            'SUCCESS_GREEN': '#28a745',         # Green for success indicators
            'ERROR_RED': '#dc3545',             # Red for errors and warnings
            'WARNING_YELLOW': '#ffc107',        # Yellow for warnings that need attention
            'INFO_BLUE': '#007bff',             # Blue for informational elements
            'INFO_TEAL': '#17a2b8',             # Teal for secondary info
            'ACCENT_ORANGE': '#fd7e14',         # Orange for special highlights
            'ACCENT_PURPLE': '#6f42c1',         # Purple for template analysis

            # Status colors (for success/error badges)
            'SUCCESS_TEXT': '#155724',          # Dark green text for success badges
            'WARNING_TEXT': '#856404',          # Dark yellow text for warning badges
            'ERROR_TEXT': '#721c24',            # Dark red text for error badges

            # Code display colors
            'CODE_BG_DARK': '#2d3748',          # Dark background for code blocks
            'CODE_TEXT_LIGHT': '#e2e8f0',       # Light text for dark code blocks
        },
        'BACKGROUNDS': {
            'LIGHT_GRAY': '#f8f9fa',           # General light gray background
            'SUCCESS_BG': '#d4edda',           # Light green background for success
            'WARNING_BG': '#fff3cd',           # Light yellow background for warnings
            'ERROR_BG': '#f8d7da',             # Light red background for errors

            # Transparent overlays for sections
            'SUCCESS_OVERLAY': 'rgba(40, 167, 69, 0.05)',    # Very light green overlay
            'WARNING_OVERLAY': 'rgba(255, 193, 7, 0.05)',    # Very light yellow overlay
        },
        'SPACING': {
            'BORDER_RADIUS': '4px',            # Standard border radius
            'SECTION_PADDING': '1rem',         # Standard section padding
            'SMALL_PADDING': '0.5rem',         # Small padding for badges
            'MARGIN_BOTTOM': '1rem',           # Standard bottom margin
            'SMALL_MARGIN': '0.5rem',          # Small margins
        }
    }

    def __init__(self, app, pipulate, pipeline, db, app_name=None):
        self.app = app
        self.app_name = self.APP_NAME
        self.pipulate = pipulate
        self.pipeline = pipeline
        self.db = db
        pip = self.pipulate
        self.message_queue = pip.get_message_queue()

        self.steps = [
            Step(id='step_01', done='plugin_analysis', show='1. Plugin Selection', refill=False),
            Step(id='step_02', done='comprehensive_analysis', show='2. Analysis & Recommendations', refill=False),
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

        return pip.run_all_cells(internal_app_name, self.steps)

    async def finalize(self, request):
        pip, db, app_name = self.pipulate, self.db, self.APP_NAME
        pipeline_id = db.get('pipeline_id', 'unknown')

        if request.method == 'POST':
            await pip.set_step_data(pipeline_id, 'finalize', {'finalized': True}, self.steps)
            await self.message_queue.add(pip, 'Development analysis session finalized.', verbatim=True)
            return pip.run_all_cells(app_name, self.steps)

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
        return pip.run_all_cells(app_name, self.steps)

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

        return pip.run_all_cells(app_name, self.steps)

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
            },
            "transplantation_analysis": {  # NEW: Detailed transplantation analysis
                "swappable_steps": [],
                "step_dependencies": {},
                "transplant_commands": [],
                "compatibility_warnings": []
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

        # Route Registration Analysis - Check for missing handlers that are being registered
        # ================================================================================
        route_registration_issues = []

        # Extract the route registration pattern from __init__ method
        init_method_match = re.search(r'def __init__\(.*?\n(.*?)(?=\n    def|\n    async def|\nclass|\Z)', content, re.DOTALL)
        if init_method_match:
            init_content = init_method_match.group(1)

            # Check for explicit finalize_submit registration pattern
            if 'finalize_submit' in init_content:
                if 'async def finalize_submit(' not in content:
                    route_registration_issues.append(
                        f"❌ CRITICAL: Route registration expects 'finalize_submit' method but it doesn't exist"
                    )
                    analysis["coding_assistant_prompts"].append(
                        f"Add missing finalize_submit method to {filename}:\n"
                        f"The route registration in __init__ is trying to register a finalize_submit handler but it doesn't exist.\n\n"
                        f"Add this method to the class:\n\n"
                        f"```python\n"
                        f"async def finalize_submit(self, request):\n"
                        f"    pip, db, app_name = self.pipulate, self.db, self.APP_NAME\n"
                        f"    pipeline_id = db.get('pipeline_id', 'unknown')\n"
                        f"    \n"
                        f"    await pip.set_step_data(pipeline_id, 'finalize', {{'finalized': True}}, self.steps)\n"
                        f"    await self.message_queue.add(pip, 'Workflow finalized.', verbatim=True)\n"
                        f"    return pip.run_all_cells(app_name, self.steps)\n"
                        f"```\n\n"
                        f"OR modify the route registration to not expect finalize_submit and handle POST in finalize() method instead."
                    )

            # Check for dynamic step registration that would create finalize_submit
            # Pattern: for step in steps: ... getattr(self, f'{step_id}_submit')
            if ('for step in steps:' in init_content or 'for step in self.steps:' in init_content) and 'getattr(self, f' in init_content and '_submit' in init_content:
                # Check if 'finalize' appears in the steps definition and would trigger finalize_submit registration
                if "Step(id='finalize'" in content or 'id="finalize"' in content:
                    # Check if finalize_submit would be expected but doesn't exist
                    # BUT: Modern workflows often handle POST in finalize() method instead of finalize_submit()
                    # So only flag this as an issue if there's no evidence of proper finalize() POST handling
                    has_finalize_submit = 'async def finalize_submit(' in content
                    has_finalize_method = 'async def finalize(' in content
                    finalize_handles_post = has_finalize_method and ('request.method' in content and 'POST' in content)

                    if not has_finalize_submit and not finalize_handles_post:
                        route_registration_issues.append(
                            f"❌ CRITICAL: Route registration expects 'finalize_submit' method but it doesn't exist"
                        )
                        analysis["coding_assistant_prompts"].append(
                            f"Add missing finalize_submit method to {filename}:\n"
                            f"The dynamic route registration loop creates a finalize_submit handler when 'finalize' is in steps, but the method doesn't exist.\n\n"
                            f"SOLUTION 1 - Add the missing method:\n"
                            f"```python\n"
                            f"async def finalize_submit(self, request):\n"
                            f"    pip, db, app_name = self.pipulate, self.db, self.app_name\n"
                            f"    pipeline_id = db.get('pipeline_id', 'unknown')\n"
                            f"    \n"
                            f"    await pip.set_step_data(pipeline_id, 'finalize', {{'finalized': True}}, self.steps)\n"
                            f"    await self.message_queue.add(pip, 'Workflow finalized.', verbatim=True)\n"
                            f"    return pip.run_all_cells(app_name, self.steps)\n"
                            f"```\n\n"
                            f"SOLUTION 2 - Exclude finalize from dynamic registration:\n"
                            f"```python\n"
                            f"for step in steps:\n"
                            f"    step_id = step.id\n"
                            f"    routes.append((f'/{{app_name}}/{{step_id}}', getattr(self, step_id)))\n"
                            f"    if step_id != 'finalize':  # Only data steps have explicit _submit handlers\n"
                            f"        routes.append((f'/{{app_name}}/{{step_id}}_submit', getattr(self, f'{{step_id}}_submit'), ['POST']))\n"
                            f"```\n\n"
                            f"SOLUTION 3 - Handle POST in finalize() method (RECOMMENDED):\n"
                            f"```python\n"
                            f"async def finalize(self, request):\n"
                            f"    pip, db, app_name = self.pipulate, self.db, self.app_name\n"
                            f"    pipeline_id = db.get('pipeline_id', 'unknown')\n"
                            f"    \n"
                            f"    if request.method == 'GET':\n"
                            f"        # Handle GET request (show finalize form)\n"
                            f"        return Card(H3('Ready to finalize?'), ...)\n"
                            f"    else:  # POST\n"
                            f"        # Handle finalization\n"
                            f"        await pip.finalize_workflow(pipeline_id)\n"
                            f"        return pip.run_all_cells(app_name, self.steps)\n"
                            f"```"
                        )

            # Check for step handler registration mismatches
            step_submit_patterns = re.findall(r'(\w+)_submit', init_content)
            for step_submit in step_submit_patterns:
                if f'async def {step_submit}_submit(' not in content:
                    route_registration_issues.append(
                        f"❌ Route registration expects '{step_submit}_submit' method but it doesn't exist"
                    )
                    analysis["coding_assistant_prompts"].append(
                        f"Add missing {step_submit}_submit method to {filename}:\n"
                        f"The route registration expects this handler but it doesn't exist.\n\n"
                        f"Add this method to the class:\n\n"
                        f"```python\n"
                        f"async def {step_submit}_submit(self, request):\n"
                        f"    pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)\n"
                        f"    step_id = '{step_submit}'\n"
                        f"    step_index = self.steps_indices[step_id]\n"
                        f"    pipeline_id = db.get('pipeline_id', 'unknown')\n"
                        f"    \n"
                        f"    form = await request.form()\n"
                        f"    # Process form data here\n"
                        f"    user_input = form.get('field_name', '').strip()\n"
                        f"    \n"
                        f"    # Store step data\n"
                        f"    await pip.set_step_data(pipeline_id, step_id, user_input, steps)\n"
                        f"    \n"
                        f"    return pip.chain_reverter(step_id, step_index, steps, app_name, user_input)\n"
                        f"```"
                    )

            # Check for getattr patterns that might fail
            getattr_patterns = re.findall(r'getattr\(self, [\'"]([^\'"]+)[\'"]', init_content)
            for method_name in getattr_patterns:
                if f'async def {method_name}(' not in content and f'def {method_name}(' not in content:
                    route_registration_issues.append(
                        f"❌ getattr() expects '{method_name}' method but it doesn't exist"
                    )

        # Add route registration issues to the main issues list
        if route_registration_issues:
            analysis["issues"].extend(route_registration_issues)
            analysis["recommendations"].append("Fix route registration mismatches - add missing handler methods")

        # Template Assembly Marker Analysis
        steps_insertion_marker = "--- STEPS_LIST_INSERTION_POINT ---"
        methods_insertion_marker = "--- STEP_METHODS_INSERTION_POINT ---"

        has_steps_marker = steps_insertion_marker in content
        has_methods_marker = methods_insertion_marker in content

        if has_steps_marker:
            analysis["patterns_found"].append("✅ STEPS_LIST_INSERTION_POINT marker found")
        else:
            analysis["template_suitability"]["missing_requirements"].append("STEPS_LIST_INSERTION_POINT marker")
            analysis["issues"].append("❌ Missing STEPS_LIST_INSERTION_POINT marker (template compatibility)")
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
            analysis["issues"].append("❌ Missing STEP_METHODS_INSERTION_POINT marker (template compatibility)")
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
                analysis["issues"].append(f"❌ Missing {attr} class attribute (template compatibility)")

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
            analysis["issues"].append("❌ Missing UI_CONSTANTS (template compatibility)")
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

        # NEW: COMPREHENSIVE TRANSPLANTATION ANALYSIS
        # ===========================================
        transplant_analysis = analysis["transplantation_analysis"]

        # Find all swappable step methods with proper markers
        swappable_steps = []
        step_dependencies = {}

        # Look for both SWAPPABLE_STEP and STEP_BUNDLE markers
        swappable_patterns = [
            r'# --- START_SWAPPABLE_STEP: (step_\d+) ---',
            r'# --- START_STEP_BUNDLE: (step_\d+) ---'
        ]

        for pattern in swappable_patterns:
            matches = re.findall(pattern, content)
            for step_id in matches:
                if step_id not in swappable_steps:
                    swappable_steps.append(step_id)

        # Find step methods even without markers (potential for transplantation after adding markers)
        step_method_pattern = r'async def (step_\d+)(?:_submit)?\('
        step_methods = re.findall(step_method_pattern, content)
        potential_steps = list(set(step_methods))  # Remove duplicates

        # Analyze each step for dependencies and transplantability
        for step_id in potential_steps:
            # Extract the step method content to analyze dependencies
            step_start_pattern = rf'async def {step_id}\('
            step_submit_pattern = rf'async def {step_id}_submit\('

            # Find the step method bounds
            step_content = ""
            lines = content.split('\n')

            in_step_method = False
            step_method_indent = None

            for i, line in enumerate(lines):
                if re.search(step_start_pattern, line):
                    in_step_method = True
                    step_method_indent = len(line) - len(line.lstrip())
                    step_content += line + '\n'
                elif in_step_method:
                    current_indent = len(line) - len(line.lstrip()) if line.strip() else 999
                    # Continue if we're still inside the method (proper indentation or empty line)
                    if line.strip() == '' or current_indent > step_method_indent:
                        step_content += line + '\n'
                    else:
                        # We've reached the next method
                        break

            # Also get the submit method if it exists
            if f'async def {step_id}_submit(' in content:
                in_submit_method = False
                submit_method_indent = None

                for i, line in enumerate(lines):
                    if re.search(step_submit_pattern, line):
                        in_submit_method = True
                        submit_method_indent = len(line) - len(line.lstrip())
                        step_content += line + '\n'
                    elif in_submit_method:
                        current_indent = len(line) - len(line.lstrip()) if line.strip() else 999
                        if line.strip() == '' or current_indent > submit_method_indent:
                            step_content += line + '\n'
                        else:
                            break

            # Analyze dependencies in the step content
            dependencies = []

            # Check for self.UPPER_CASE class constants
            class_constants = re.findall(r'self\.([A-Z][A-Z_]+)', step_content)
            dependencies.extend([f"self.{const}" for const in set(class_constants)])

            # Check for specialized methods or attributes
            specialized_methods = re.findall(r'self\.([a-z_]+[a-z0-9_]*)\(', step_content)
            specialized_attrs = re.findall(r'self\.([a-z_]+[a-z0-9_]*)', step_content)

            # Filter out common workflow methods that should be available everywhere
            common_methods = {
                'pipulate', 'db', 'steps', 'app_name', 'message_queue', 'steps_indices',
                'get_step_data', 'set_step_data', 'read_state', 'write_state'
            }

            specialized = set(specialized_methods + specialized_attrs) - common_methods
            dependencies.extend([f"self.{method}" for method in specialized])

            # Check for external imports or specialized functionality
            external_deps = []
            if 'matplotlib' in step_content.lower():
                external_deps.append('matplotlib library')
            if 'base64' in step_content.lower():
                external_deps.append('base64 encoding')
            if 'json' in step_content.lower():
                external_deps.append('JSON processing')
            if 'upload' in step_content.lower() or 'file' in step_content.lower():
                external_deps.append('file handling')
            if 'checkbox' in step_content.lower() or 'fieldset' in step_content.lower():
                external_deps.append('checkbox UI components')

            dependencies.extend(external_deps)

            step_dependencies[step_id] = {
                'class_dependencies': [dep for dep in dependencies if dep.startswith('self.')],
                'external_dependencies': [dep for dep in dependencies if not dep.startswith('self.')],
                'has_swappable_markers': step_id in swappable_steps,
                'self_contained': len([dep for dep in dependencies if dep.startswith('self.') and not any(common in dep for common in ['pipulate', 'db', 'steps', 'app_name'])]) == 0
            }

        # Generate transplant commands for each viable step
        transplant_commands = []
        compatibility_warnings = []

        source_filename = filename

        for step_id in potential_steps:
            step_info = step_dependencies.get(step_id, {})

            # Generate command for swapping this step to a target workflow
            command = f"python helpers/swap_workflow_step.py TARGET_FILE.py {step_id} plugins/{source_filename} {step_id} --force"

            compatibility_notes = []
            if not step_info.get('has_swappable_markers', False):
                compatibility_notes.append("⚠️ Needs swappable step markers added first")
            if not step_info.get('self_contained', True):
                compatibility_notes.append("⚠️ Has class dependencies that may not exist in target")
            if step_info.get('external_dependencies'):
                deps = ', '.join(step_info['external_dependencies'])
                compatibility_notes.append(f"⚠️ Requires: {deps}")

            transplant_commands.append({
                'step_id': step_id,
                'command': command,
                'compatibility': 'Good' if len(compatibility_notes) == 0 else 'Needs Work',
                'notes': compatibility_notes,
                'dependencies': step_info
            })

        # Store results
        transplant_analysis['swappable_steps'] = swappable_steps
        transplant_analysis['step_dependencies'] = step_dependencies
        transplant_analysis['transplant_commands'] = transplant_commands

        # Generate compatibility warnings
        if len(swappable_steps) == 0 and len(potential_steps) > 0:
            transplant_analysis['compatibility_warnings'].append(
                "No swappable step markers found. Add START_SWAPPABLE_STEP/END_SWAPPABLE_STEP markers to enable transplantation."
            )

        high_dependency_steps = [
            step_id for step_id, info in step_dependencies.items()
            if len(info.get('class_dependencies', [])) > 3
        ]
        if high_dependency_steps:
            transplant_analysis['compatibility_warnings'].append(
                f"Steps with many dependencies may not transplant cleanly: {', '.join(high_dependency_steps)}"
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

        return pip.chain_reverter(step_id, step_index, steps, app_name, user_input)\n""")

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
                f"        return pip.run_all_cells(app_name, self.steps)\n"
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

        # Enhanced Swap Source Assessment
        if transplant_commands:
            good_transplants = [cmd for cmd in transplant_commands if cmd['compatibility'] == 'Good']
            needs_work_transplants = [cmd for cmd in transplant_commands if cmd['compatibility'] == 'Needs Work']

            if good_transplants:
                analysis["patterns_found"].append(f"🔀 EXCELLENT SWAP SOURCE: {len(good_transplants)} ready-to-transplant step(s)")
            elif needs_work_transplants:
                analysis["patterns_found"].append(f"🔀 POTENTIAL SWAP SOURCE: {len(needs_work_transplants)} step(s) need preparation")
                suitability["as_swap_source"] = False  # Override default
                suitability["missing_requirements"].append("Swappable step markers and/or dependency resolution")
            else:
                suitability["as_swap_source"] = False
                analysis["issues"].append("❌ No viable steps for swapping found")

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
                Card(H3(f'🔒 {step.show}: Analysis Complete')),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        elif user_val and state.get('_revert_target') != step_id:
            return Div(
                pip.display_revert_header(step_id, app_name, steps, f'{step.show}: Complete'),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        else:
            # Check if step 1 has been completed by looking for plugin_analysis
            if not step_01_data.get('plugin_analysis'):
                return Div(
                    Card(
                        H3(f'{step.show}'),
                        P('Please complete Plugin Selection first.', style='color: orange;')
                    ),
                    Div(id=next_step_id),
                    id=step_id
                )

            # Get analysis data
            issues = analysis_results.get('issues', [])
            template_suitability = analysis_results.get('template_suitability', {})
            coding_prompts = analysis_results.get('coding_assistant_prompts', [])
            transplant_analysis = analysis_results.get('transplantation_analysis', {})
            filename = analysis_results.get('filename', 'unknown')

            # Focus on what needs fixing - issues first!
            functional_issues = [issue for issue in issues if not any(x in issue.lower() for x in ['marker', 'template', 'ui_constants'])]
            template_issues = [issue for issue in issues if any(x in issue.lower() for x in ['marker', 'template', 'ui_constants'])]

            # Quick status for capability overview
            has_functional_issues = bool(functional_issues)
            template_source_ready = template_suitability.get('as_template_source', False)
            transplant_commands = transplant_analysis.get('transplant_commands', [])
            ready_transplants = [cmd for cmd in transplant_commands if cmd.get('compatibility') == 'Good']

            # Define widget ID for Prism targeting
            widget_id = f"dev-assistant-{pipeline_id.replace('-', '_')}-{step_id}"

            response_content = Div(
                Card(
                    H3(f"Analysis: {filename}", style="margin-bottom: 1.5rem;"),

                    # WHAT NEEDS FIXING (Primary Focus)
                    (Div(
                        H4("🚨 ISSUES TO FIX", style=f"color: {self.UI_CONSTANTS['COLORS']['ERROR_RED']}; margin-bottom: 1rem; border-bottom: 2px solid {self.UI_CONSTANTS['COLORS']['ERROR_RED']}; padding-bottom: 0.5rem;"),
                        Div(
                            H5("❌ Functional Issues:", style="color: red; margin-bottom: 0.5rem;"),
                            Ul(*[Li(issue) for issue in functional_issues],
                               style="color: red; margin-bottom: 1rem;")
                        ) if functional_issues else None,
                        Div(
                            H5("📋 Template Issues:", style="color: orange; margin-bottom: 0.5rem;"),
                            Ul(*[Li(issue) for issue in template_issues],
                               style="color: orange; margin-bottom: 1rem;")
                        ) if template_issues else None,
                        (P("✅ No critical issues found!", style=f"color: {self.UI_CONSTANTS['COLORS']['SUCCESS_GREEN']}; font-weight: bold; font-size: 1.1rem;")
                         if not functional_issues and not template_issues else None),
                        style="margin-bottom: 2rem;"
                    ) if functional_issues or template_issues else Div(
                        H4("✅ NO ISSUES FOUND", style=f"color: {self.UI_CONSTANTS['COLORS']['SUCCESS_GREEN']}; margin-bottom: 1rem; border-bottom: 2px solid {self.UI_CONSTANTS['COLORS']['SUCCESS_GREEN']}; padding-bottom: 0.5rem;"),
                        P("This plugin appears to be correctly implemented!", style=f"color: {self.UI_CONSTANTS['COLORS']['SUCCESS_GREEN']}; font-weight: bold; font-size: 1.1rem;"),
                        style="margin-bottom: 2rem;"
                    )),

                    # CAPABILITIES (Secondary Info)
                    Div(
                        Details(
                            Summary(
                                H4('📊 Capabilities Summary', style='display: inline; margin: 0;'),
                                style=f'cursor: pointer; padding: {self.UI_CONSTANTS["SPACING"]["SECTION_PADDING"]}; background-color: {self.UI_CONSTANTS["BACKGROUNDS"]["LIGHT_GRAY"]}; border-radius: {self.UI_CONSTANTS["SPACING"]["BORDER_RADIUS"]}; margin: 1rem 0;'
                            ),
                            Div(
                                Div(f"🔧 Functional Plugin: {'✅ Good' if not has_functional_issues else '❌ Has Issues'}",
                                    style=f"color: {self.UI_CONSTANTS['COLORS']['SUCCESS_TEXT'] if not has_functional_issues else self.UI_CONSTANTS['COLORS']['ERROR_TEXT']}; background-color: {self.UI_CONSTANTS['BACKGROUNDS']['SUCCESS_BG'] if not has_functional_issues else self.UI_CONSTANTS['BACKGROUNDS']['ERROR_BG']}; padding: {self.UI_CONSTANTS['SPACING']['SMALL_PADDING']}; border-radius: {self.UI_CONSTANTS['SPACING']['BORDER_RADIUS']}; font-weight: bold; margin-bottom: {self.UI_CONSTANTS['SPACING']['SMALL_MARGIN']};"),
                                Div(f"📋 Template Source: {'✅ Ready' if template_source_ready else '❌ Needs Work'}",
                                    style=f"color: {self.UI_CONSTANTS['COLORS']['SUCCESS_TEXT'] if template_source_ready else self.UI_CONSTANTS['COLORS']['ERROR_TEXT']}; background-color: {self.UI_CONSTANTS['BACKGROUNDS']['SUCCESS_BG'] if template_source_ready else self.UI_CONSTANTS['BACKGROUNDS']['ERROR_BG']}; padding: {self.UI_CONSTANTS['SPACING']['SMALL_PADDING']}; border-radius: {self.UI_CONSTANTS['SPACING']['BORDER_RADIUS']}; font-weight: bold; margin-bottom: {self.UI_CONSTANTS['SPACING']['SMALL_MARGIN']};"),
                                Div(f"📤 Step Source: {'✅ ' + str(len(ready_transplants)) + ' ready' if ready_transplants else '❌ None ready'}",
                                    style=f"color: {self.UI_CONSTANTS['COLORS']['SUCCESS_TEXT'] if ready_transplants else self.UI_CONSTANTS['COLORS']['ERROR_TEXT']}; background-color: {self.UI_CONSTANTS['BACKGROUNDS']['SUCCESS_BG'] if ready_transplants else self.UI_CONSTANTS['BACKGROUNDS']['ERROR_BG']}; padding: {self.UI_CONSTANTS['SPACING']['SMALL_PADDING']}; border-radius: {self.UI_CONSTANTS['SPACING']['BORDER_RADIUS']}; font-weight: bold;"),
                                style='padding: 1rem;'
                            )
                        )
                    ),

                    # CODING FIXES (If issues exist)
                    (Details(
                        Summary(
                            H4('🤖 Coding Assistant Instructions', style='display: inline; margin: 0;'),
                            style=f'cursor: pointer; padding: {self.UI_CONSTANTS["SPACING"]["SECTION_PADDING"]}; background-color: {self.UI_CONSTANTS["BACKGROUNDS"]["LIGHT_GRAY"]}; border-radius: {self.UI_CONSTANTS["SPACING"]["BORDER_RADIUS"]}; margin: 1rem 0;'
                        ),
                        Div(
                            P(f'Copy these detailed instructions to fix {filename}:',
                              style=f'margin-bottom: 1rem; font-weight: bold; color: {self.UI_CONSTANTS["COLORS"]["HEADER_TEXT"]};'),
                            Div(
                                *[
                                    Div(
                                        H5(f'Fix #{i+1}:', style=f'color: {self.UI_CONSTANTS["COLORS"]["INFO_BLUE"]}; margin-top: 1.5rem; margin-bottom: 0.5rem;'),
                                        Pre(
                                            Code(prompt, cls='language-markdown'),
                                            cls='line-numbers'
                                        ),
                                        style='margin-bottom: 1rem;'
                                    )
                                    for i, prompt in enumerate(coding_prompts)
                                ],
                                id=widget_id
                            ),
                            style='padding: 1rem;'
                        ),
                        style='margin: 1rem 0;'
                    ) if coding_prompts else None),

                    # TRANSPLANTATION COMMANDS (If available)
                    (Details(
                        Summary(
                            H4('🔀 Step Transplantation', style='display: inline; margin: 0;'),
                            style=f'cursor: pointer; padding: {self.UI_CONSTANTS["SPACING"]["SECTION_PADDING"]}; background-color: {self.UI_CONSTANTS["BACKGROUNDS"]["LIGHT_GRAY"]}; border-radius: {self.UI_CONSTANTS["SPACING"]["BORDER_RADIUS"]}; margin: 1rem 0;'
                        ),
                        Div(
                            (Div(
                                H5('✅ Ready Commands:', style=f'color: {self.UI_CONSTANTS["COLORS"]["SUCCESS_GREEN"]}; margin-bottom: 0.75rem;'),
                                *[
                                    Div(
                                        Strong(f"{cmd['step_id']}: ", style=f'color: {self.UI_CONSTANTS["COLORS"]["INFO_BLUE"]};'),
                                        Code(cmd['command'], style=f'background-color: {self.UI_CONSTANTS["BACKGROUNDS"]["LIGHT_GRAY"]}; padding: 0.2rem 0.4rem; border-radius: 3px; font-size: 0.9rem;'),
                                        style='margin-bottom: 0.5rem; display: block;'
                                    )
                                    for cmd in ready_transplants
                                ]
                            ) if ready_transplants else P('No ready-to-transplant steps found.', style=f'color: {self.UI_CONSTANTS["COLORS"]["BODY_TEXT"]};')),
                            style='padding: 1rem;'
                        )
                    ) if transplant_commands else None),

                    Form(
                        Button('Complete Analysis ▸', type='submit'),
                        hx_post=f'/{app_name}/{step_id}_submit',
                        hx_target=f'#{step_id}'
                    )
                ),
                # Add Prism initialization script
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

            # Return HTMLResponse with HX-Trigger for Prism initialization
            response = HTMLResponse(to_xml(response_content))
            response.headers['HX-Trigger'] = json.dumps({'initializePrism': {'targetId': widget_id}})
            return response

    async def step_02_submit(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        pipeline_id = db.get('pipeline_id', 'unknown')

        await pip.set_step_data(pipeline_id, step_id, 'complete', steps)
        await self.message_queue.add(pip, 'Development analysis completed.', verbatim=True)

        return pip.chain_reverter(step_id, step_index, steps, app_name, 'Analysis Complete')


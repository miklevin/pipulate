import asyncio
import json
from collections import namedtuple
from datetime import datetime

from fasthtml.common import *
from loguru import logger
from starlette.responses import HTMLResponse

ROLES = ['Components']
'\nPipulate Markdown MarkedJS Widget Workflow\nA workflow for demonstrating the Markdown MarkedJS rendering widget.\n'
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class MarkdownWidget:
    """
    Markdown MarkedJS Widget Workflow

    Demonstrates rendering markdown content using MarkedJS.
    """
    APP_NAME = 'markdown_widget'
    DISPLAY_NAME = 'Markdown MarkedJS Widget'
    ENDPOINT_MESSAGE = 'This workflow demonstrates a Markdown (MarkedJS) rendering widget. Enter markdown content to see it rendered.'
    TRAINING_PROMPT = 'This workflow is for demonstrating and testing the Markdown MarkedJS widget. The user will input markdown text, and the system will render it as HTML.'

    # UI Constants for automation and accessibility
    UI_CONSTANTS = {
        "AUTOMATION_ATTRIBUTES": {
            "MARKDOWN_TEXTAREA": "markdown-widget-textarea",
            "RENDER_BUTTON": "markdown-widget-render-button",
            "RENDERED_OUTPUT": "markdown-widget-rendered-output",
            "WIDGET_CONTAINER": "markdown-widget-container",
            "SOURCE_ELEMENT": "markdown-widget-source"
        },
        "ARIA_LABELS": {
            "MARKDOWN_INPUT": "Enter markdown content for rendering",
            "RENDER_BUTTON": "Render markdown content as HTML",
            "RENDERED_OUTPUT": "Rendered markdown output display",
            "WIDGET_CONTAINER": "Markdown widget interface"
        },
        "COLORS": {
            "WIDGET_BORDER": "#e9ecef",
            "RENDERED_BACKGROUND": "#f8f9fa"
        },
        "SPACING": {
            "WIDGET_PADDING": "1rem",
            "BUTTON_MARGIN": "1vh 0"
        }
    }

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
        steps = [
            Step(id='step_01', done='markdown_content', show='Markdown Content', refill=True, transform=lambda prev_value: prev_value.strip() if prev_value else '')
            # --- STEPS_LIST_INSERTION_POINT ---
        ]
        routes = [(f'/{app_name}', self.landing), (f'/{app_name}/init', self.init, ['POST']), (f'/{app_name}/revert', self.handle_revert, ['POST']), (f'/{app_name}/finalize', self.finalize, ['GET', 'POST']), (f'/{app_name}/unfinalize', self.unfinalize, ['POST'])]
        self.steps = steps
        for step in steps:
            step_id = step.id
            routes.append((f'/{app_name}/{step_id}', getattr(self, step_id)))
            routes.append((f'/{app_name}/{step_id}_submit', getattr(self, f'{step_id}_submit'), ['POST']))
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ['GET']
            app.route(path, methods=method_list)(handler)
        self.step_messages = {'finalize': {'ready': 'All steps complete. Ready to finalize workflow.', 'complete': f'Workflow finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes.'}, 'step_01': {'input': 'Please enter Markdown content.', 'complete': 'Markdown content processed.'}}
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

    # --- STEP_METHODS_INSERTION_POINT ---

    async def landing(self, request):
        """Generate the landing page using the standardized helper while maintaining WET explicitness."""
        pip = self.pipulate

        # Use centralized landing page helper - maintains WET principle by explicit call
        return pip.create_standard_landing_page(self)

    async def init(self, request):
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
        plugin_name = app_name  # Use app_name directly to ensure consistency
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
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        pipeline_id = db.get('pipeline_id', 'unknown')
        finalize_step = steps[-1]
        finalize_data = pip.get_step_data(pipeline_id, finalize_step.id, {})
        if request.method == 'GET':
            if finalize_step.done in finalize_data:
                return Card(H3('Workflow is locked.'), Form(Button(pip.UNLOCK_BUTTON_LABEL, type='submit', cls='secondary outline', data_testid=self.UI_CONSTANTS["AUTOMATION_ATTRIBUTES"]["RENDER_BUTTON"] + "-unlock", aria_label=self.UI_CONSTANTS["ARIA_LABELS"]["RENDER_BUTTON"]), hx_post=f'/{app_name}/unfinalize', hx_target=f'#{app_name}-container', hx_swap='outerHTML'), id=finalize_step.id)
            else:
                all_steps_complete = all((pip.get_step_data(pipeline_id, step.id, {}).get(step.done) for step in steps[:-1]))
                if all_steps_complete:
                    return Card(H3('All steps complete. Finalize?'), P('You can revert to any step and make changes.', cls='text-secondary'), Form(Button('Finalize 🔒', type='submit', cls='primary', data_testid=self.UI_CONSTANTS["AUTOMATION_ATTRIBUTES"]["RENDER_BUTTON"] + "-finalize", aria_label="Finalize markdown workflow"), hx_post=f'/{app_name}/finalize', hx_target=f'#{app_name}-container', hx_swap='outerHTML'), id=finalize_step.id)
                else:
                    return Div(id=finalize_step.id)
        else:
            await pip.finalize_workflow(pipeline_id)
            await self.message_queue.add(pip, self.step_messages['finalize']['complete'], verbatim=True)
            return pip.run_all_cells(app_name, steps)

    async def unfinalize(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        pipeline_id = db.get('pipeline_id', 'unknown')
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, 'Workflow unfinalized! You can now revert to any step and make changes.', verbatim=True)
        return pip.run_all_cells(app_name, steps)

    async def get_suggestion(self, step_id, state):
        if step_id == 'step_01':
            return '# Markdown Example\nThis is a **bold statement** about _markdown_.\n\n## Features demonstrated:\n\n1. Headings (h1, h2)\n2. Formatted text (**bold**, _italic_)\n3. Ordered lists\n4. Unordered lists\n   - Nested item 1\n   - Nested item 2\n5. Code blocks\n\n### Code Example\n\n```python\ndef hello_world():\n    print("Hello from Markdown!")\n    for i in range(3):\n        print(f"Count: {i}")\n```\n\n> Blockquotes are also supported\n>\n>   - With nested lists\n>   - And formatting\n>     [Learn more about Markdown](https://www.markdownguide.org/)\n'
        return ''

    async def handle_revert(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        form = await request.form()
        step_id = form.get('step_id')
        pipeline_id = db.get('pipeline_id', 'unknown')
        if not step_id:
            return P('Error: No step specified', cls='text-invalid')
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        state = pip.read_state(pipeline_id)
        state['_revert_target'] = step_id
        pip.write_state(pipeline_id, state)
        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        return pip.run_all_cells(app_name, steps)

    def create_marked_widget(self, markdown_content, widget_id):
        # Ensure markdown_content is properly handled as text
        content_text = str(markdown_content) if markdown_content else ""
        
        widget = Div(
            # Use Pre element to preserve exact text content including newlines
            Pre(
                content_text, 
                id=f'{widget_id}_source', 
                cls='hidden',
                data_testid=self.UI_CONSTANTS["AUTOMATION_ATTRIBUTES"]["SOURCE_ELEMENT"],
                aria_label="Hidden markdown source content",
                style="white-space: pre-wrap; display: none;"
            ), 
            Div(
                id=f'{widget_id}_rendered', 
                cls='bg-light border markdown-body p-3 rounded-default',
                data_testid=self.UI_CONSTANTS["AUTOMATION_ATTRIBUTES"]["RENDERED_OUTPUT"],
                aria_label=self.UI_CONSTANTS["ARIA_LABELS"]["RENDERED_OUTPUT"],
                role="region",
                aria_live="polite"
            ), 
            Script(f"""
                document.addEventListener('htmx:afterOnLoad', function() {{
                    function renderMarkdown() {{
                        const source = document.getElementById('{widget_id}_source');
                        const target = document.getElementById('{widget_id}_rendered');
                        if (source && target) {{
                            // Use textContent to get the actual text, not innerHTML
                            const markdownText = source.textContent || source.innerText || '';
                            console.log('Rendering markdown:', markdownText.substring(0, 100) + '...');
                            
                            // Configure marked to work better with Prism
                            if (typeof marked !== 'undefined') {{
                                // Set up marked renderer to avoid conflicts with Prism
                                const renderer = new marked.Renderer();
                                const originalCode = renderer.code;
                                renderer.code = function(code, lang) {{
                                    // Robust code content handling - extract text from objects if needed
                                    let codeText;
                                    if (typeof code === 'string') {{
                                        codeText = code;
                                    }} else if (code && typeof code === 'object') {{
                                        // If it's an object, try to extract text content
                                        codeText = code.text || code.content || code.value || JSON.stringify(code);
                                    }} else {{
                                        codeText = String(code || '');
                                    }}
                                    
                                    // Escape HTML to prevent XSS and display issues
                                    codeText = codeText.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                                    
                                    if (lang) {{
                                        return `<pre><code class="language-${{lang}}">${{codeText}}</code></pre>`;
                                    }} else {{
                                        return `<pre><code>${{codeText}}</code></pre>`;
                                    }}
                                }};
                                
                                const html = marked.parse(markdownText, {{ renderer: renderer }});
                                target.innerHTML = html;
                                
                                // Apply Prism highlighting with enhanced debugging and retry logic
                                setTimeout(function() {{
                                    if (typeof Prism !== 'undefined') {{
                                        console.log('Applying Prism highlighting...');
                                        
                                        // Find all code blocks and ensure they have proper language classes
                                        const codeBlocks = target.querySelectorAll('pre code');
                                        codeBlocks.forEach(function(block, index) {{
                                            console.log(`Code block ${{index}}: classes = ${{block.className}}`);
                                            
                                            // If no language class but content looks like Python, add it
                                            if (!block.className.includes('language-') && 
                                                (block.textContent.includes('def ') || 
                                                 block.textContent.includes('import ') ||
                                                 block.textContent.includes('print('))) {{
                                                console.log('Auto-detecting Python code, adding language-python class');
                                                block.className = 'language-python';
                                            }}
                                        }});
                                        
                                        // Apply highlighting
                                        Prism.highlightAllUnder(target);
                                        console.log('Prism highlighting completed');
                                    }} else {{
                                        console.error('Prism is not available for syntax highlighting');
                                    }}
                                }}, 100);
                            }}
                        }}
                    }}
                    if (typeof marked !== 'undefined') {{
                        renderMarkdown();
                    }} else {{
                        console.error('marked.js is not loaded');
                    }}
                }});
                document.addEventListener('initMarked', function(event) {{
                    if (event.detail.widgetId === '{widget_id}') {{
                        setTimeout(function() {{
                            const source = document.getElementById('{widget_id}_source');
                            const target = document.getElementById('{widget_id}_rendered');
                            if (source && target && typeof marked !== 'undefined') {{
                                const markdownText = source.textContent || source.innerText || '';
                                console.log('Init rendering markdown:', markdownText.substring(0, 100) + '...');
                                
                                // Configure marked renderer
                                const renderer = new marked.Renderer();
                                renderer.code = function(code, lang) {{
                                    // Robust code content handling - extract text from objects if needed
                                    let codeText;
                                    if (typeof code === 'string') {{
                                        codeText = code;
                                    }} else if (code && typeof code === 'object') {{
                                        // If it's an object, try to extract text content
                                        codeText = code.text || code.content || code.value || JSON.stringify(code);
                                    }} else {{
                                        codeText = String(code || '');
                                    }}
                                    
                                    // Escape HTML to prevent XSS and display issues
                                    codeText = codeText.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                                    
                                    if (lang) {{
                                        return `<pre><code class="language-${{lang}}">${{codeText}}</code></pre>`;
                                    }} else {{
                                        return `<pre><code>${{codeText}}</code></pre>`;
                                    }}
                                }};
                                
                                const html = marked.parse(markdownText, {{ renderer: renderer }});
                                target.innerHTML = html;
                                
                                setTimeout(function() {{
                                    if (typeof Prism !== 'undefined') {{
                                        console.log('Init: Applying Prism highlighting...');
                                        
                                        // Find all code blocks and ensure they have proper language classes
                                        const codeBlocks = target.querySelectorAll('pre code');
                                        codeBlocks.forEach(function(block, index) {{
                                            console.log(`Init code block ${{index}}: classes = ${{block.className}}`);
                                            
                                            // If no language class but content looks like Python, add it
                                            if (!block.className.includes('language-') && 
                                                (block.textContent.includes('def ') || 
                                                 block.textContent.includes('import ') ||
                                                 block.textContent.includes('print('))) {{
                                                console.log('Init: Auto-detecting Python code, adding language-python class');
                                                block.className = 'language-python';
                                            }}
                                        }});
                                        
                                        // Apply highlighting
                                        Prism.highlightAllUnder(target);
                                        console.log('Init: Prism highlighting completed');
                                    }} else {{
                                        console.error('Init: Prism is not available for syntax highlighting');
                                    }}
                                }}, 100);
                            }}
                        }}, 100); // Delay to ensure DOM is ready
                    }}
                }});
            """), 
            cls='marked-widget',
            data_testid=self.UI_CONSTANTS["AUTOMATION_ATTRIBUTES"]["WIDGET_CONTAINER"],
            aria_label=self.UI_CONSTANTS["ARIA_LABELS"]["WIDGET_CONTAINER"]
        )
        return widget

    async def step_01(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and user_val:
            widget_id = f"marked-widget-{pipeline_id.replace('-', '_')}-{step_id}"
            marked_widget = self.create_marked_widget(user_val, widget_id)
            response = HTMLResponse(to_xml(Div(Card(H3(f'🔒 {step.show}'), marked_widget), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)))
            response.headers['HX-Trigger'] = json.dumps({'initMarked': {'widgetId': widget_id}})
            return response
        elif user_val and state.get('_revert_target') != step_id:
            widget_id = f"marked-widget-{pipeline_id.replace('-', '_')}-{step_id}"
            marked_widget = self.create_marked_widget(user_val, widget_id)
            content_container = pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show} Configured', widget=marked_widget, steps=steps)
            response = HTMLResponse(to_xml(Div(content_container, Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)))
            response.headers['HX-Trigger'] = json.dumps({'initMarked': {'widgetId': widget_id}})
            return response
        else:
            display_value = user_val if step.refill and user_val else await self.get_suggestion(step_id, state)
            await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
            explanation = 'Enter markdown content to be rendered. Example is pre-populated. The markdown will be rendered with support for headings, lists, bold/italic text, and code blocks.'
            await self.message_queue.add(pip, explanation, verbatim=True)
            return Div(Card(H3(f'{pip.fmt(step_id)}: Configure {step.show}'), P(explanation, cls='text-secondary'), Form(Div(Textarea(display_value, name=step.done, placeholder='Enter markdown content', required=True, rows=15, style='width: 100%; font-family: monospace;', data_testid=self.UI_CONSTANTS["AUTOMATION_ATTRIBUTES"]["MARKDOWN_TEXTAREA"], aria_label=self.UI_CONSTANTS["ARIA_LABELS"]["MARKDOWN_INPUT"], aria_describedby="markdown-help-text"), Div(Button('Render Markdown ▸', type='submit', cls='primary', data_testid=self.UI_CONSTANTS["AUTOMATION_ATTRIBUTES"]["RENDER_BUTTON"], aria_label=self.UI_CONSTANTS["ARIA_LABELS"]["RENDER_BUTTON"]), style='margin-top: 1vh; text-align: right;'), cls='w-full'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}'), P("Supports headings, lists, bold/italic text, code blocks, and links", id="markdown-help-text", cls='text-secondary')), Div(id=next_step_id), id=step_id)

    async def step_01_submit(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        form = await request.form()
        user_val = form.get(step.done, '').strip()
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            return error_component
        await pip.set_step_data(pipeline_id, step_id, user_val, steps)
        pip.append_to_history(f'[WIDGET CONTENT] {step.show}:\n{user_val}')
        widget_id = f"marked-widget-{pipeline_id.replace('-', '_')}-{step_id}"
        marked_widget = self.create_marked_widget(user_val, widget_id)
        content_container = pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: Markdown rendered with Marked.js', widget=marked_widget, steps=steps)
        response_content = Div(content_container, Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        response = HTMLResponse(to_xml(response_content))
        response.headers['HX-Trigger'] = json.dumps({'initMarked': {'widgetId': widget_id}})
        await self.message_queue.add(pip, f'{step.show} complete. Markdown rendered successfully.', verbatim=True)
        if pip.check_finalize_needed(step_index, steps):
            await self.message_queue.add(pip, self.step_messages['finalize']['ready'], verbatim=True)
        return response

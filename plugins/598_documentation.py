import logging
import time
import re
from pathlib import Path

from fastcore.xml import *
from fasthtml.common import *

ROLES = ['Tutorial']

logger = logging.getLogger(__name__)


class DocumentationPlugin:
    NAME = "documentation"
    DISPLAY_NAME = "Documentation"
    ENDPOINT_MESSAGE = "Displaying Pipulate documentation..."

    # Define the available documentation files - Featured guides first
    DOCS = {
        # Featured Ultimate Guides
        'guide1': {
            'title': 'Ultimate Pipulate Guide - Part 1: Core Patterns',
            'file': 'training/ULTIMATE_PIPULATE_GUIDE.md',
            'description': 'Essential patterns every developer must know',
            'category': 'featured',
            'priority': 1
        },
        'guide2': {
            'title': 'Ultimate Pipulate Guide - Part 2: Advanced Patterns', 
            'file': 'training/ULTIMATE_PIPULATE_GUIDE_PART2.md',
            'description': 'Advanced workflow and data handling patterns',
            'category': 'featured',
            'priority': 2
        },
        'guide3': {
            'title': 'Ultimate Pipulate Guide - Part 3: Expert Mastery',
            'file': 'training/ULTIMATE_PIPULATE_GUIDE_PART3.md', 
            'description': 'Expert-level patterns and advanced techniques',
            'category': 'featured',
            'priority': 3
        },
        'quick_ref': {
            'title': 'Quick Reference Card',
            'file': 'training/QUICK_REFERENCE.md',
            'description': 'Essential patterns and debugging checklist',
            'category': 'featured',
            'priority': 4
        },
        
        # Training Files
        'dev_assistant': {
            'title': 'Development Assistant Guide',
            'file': 'training/dev_assistant.md',
            'description': 'Using the development assistant plugin',
            'category': 'training'
        },
        'hello_workflow': {
            'title': 'Hello Workflow Tutorial',
            'file': 'training/hello_workflow.md',
            'description': 'Basic workflow creation tutorial',
            'category': 'training'
        },
        'system_prompt': {
            'title': 'System Prompt',
            'file': 'training/system_prompt.md',
            'description': 'LLM system prompt configuration',
            'category': 'training'
        },
        'tasks': {
            'title': 'Tasks Guide',
            'file': 'training/tasks.md',
            'description': 'Task management patterns',
            'category': 'training'
        },
        'widget_examples': {
            'title': 'Widget Examples',
            'file': 'training/widget_examples.md',
            'description': 'UI widget implementation examples',
            'category': 'training'
        },
        'botify_api_tutorial': {
            'title': 'Botify API Tutorial',
            'file': 'training/botify_api_tutorial.md',
            'description': 'Working with Botify API integration',
            'category': 'training'
        },
        'botify_workflow': {
            'title': 'Botify Workflow',
            'file': 'training/botify_workflow.md',
            'description': 'Botify-specific workflow patterns',
            'category': 'training'
        },
        
        # Rules Files
        'rule_philosophy': {
            'title': 'Philosophy',
            'file': '.cursor/rules/00_philosophy.mdc',
            'description': 'Core philosophy and principles',
            'category': 'rules'
        },
        'rule_architecture': {
            'title': 'Architecture Overview',
            'file': '.cursor/rules/01_architecture_overview.mdc',
            'description': 'High-level architecture and components',
            'category': 'rules'
        },
        'rule_environment': {
            'title': 'Environment & Installation',
            'file': '.cursor/rules/02_environment_and_installation.mdc',
            'description': 'Nix environment setup and installation',
            'category': 'rules'
        },
        'rule_workflow_core': {
            'title': 'Workflow Core',
            'file': '.cursor/rules/03_workflow_core.mdc',
            'description': 'Core workflow concepts and patterns',
            'category': 'rules'
        },
        'rule_chain_reaction': {
            'title': 'Chain Reaction Pattern',
            'file': '.cursor/rules/04_chain_reaction_pattern.mdc',
            'description': 'HTMX step progression patterns',
            'category': 'rules'
        },
        'rule_key_system': {
            'title': 'Key System',
            'file': '.cursor/rules/06_key_system.mdc',
            'description': 'Pipeline ID management system',
            'category': 'rules'
        },
        'rule_ui_htmx': {
            'title': 'UI & HTMX',
            'file': '.cursor/rules/07_ui_and_htmx.mdc',
            'description': 'UI patterns and HTMX integration',
            'category': 'rules'
        },
        'rule_llm_integration': {
            'title': 'LLM Integration',
            'file': '.cursor/rules/08_llm_integration.mdc',
            'description': 'Local LLM integration with Ollama',
            'category': 'rules'
        },
        'rule_data_operations': {
            'title': 'Data & File Operations',
            'file': '.cursor/rules/09_data_and_file_operations.mdc',
            'description': 'Data persistence and file handling',
            'category': 'rules'
        },
        'rule_browser_automation': {
            'title': 'Browser Automation',
            'file': '.cursor/rules/10_browser_automation.mdc',
            'description': 'Selenium browser automation patterns',
            'category': 'rules'
        },
        'rule_plugin_development': {
            'title': 'Plugin Development',
            'file': '.cursor/rules/11_plugin_development_guidelines.mdc',
            'description': 'Plugin development best practices',
            'category': 'rules'
        },
        'rule_server_overview': {
            'title': 'Server.py Overview',
            'file': '.cursor/rules/12_server_py_overview.mdc',
            'description': 'Server internals and core instances',
            'category': 'rules'
        },
        'rule_testing_debugging': {
            'title': 'Testing & Debugging',
            'file': '.cursor/rules/13_testing_and_debugging.mdc',
            'description': 'Testing and debugging techniques',
            'category': 'rules'
        },
        'rule_critical_environment': {
            'title': 'Critical Server Environment',
            'file': '.cursor/rules/00_CRITICAL_SERVER_ENVIRONMENT.mdc',
            'description': 'Critical server and environment rules',
            'category': 'rules'
        },
        'rule_meta_routing': {
            'title': 'Meta Rule Routing',
            'file': '.cursor/rules/meta_rule_routing.mdc',
            'description': 'Rule routing and organization guide',
            'category': 'rules'
        }
    }

    def __init__(self, app, pipulate, pipeline, db):
        logger.debug(f"DocumentationPlugin initialized with NAME: {self.NAME}")
        self.pipulate = pipulate
        self._has_streamed = False
        
        # Register routes for serving individual documents
        for doc_key in self.DOCS.keys():
            app.route(f'/docs/{doc_key}', methods=['GET'])(self.serve_document)
        
        # Register route for documentation browser
        app.route('/docs', methods=['GET'])(self.serve_browser)

    def markdown_to_html(self, markdown_content):
        """Convert markdown to HTML with enhanced formatting"""
        html = markdown_content
        
        # Headers with anchor links
        html = re.sub(r'^# (.*?)$', r'<h1 id="h1-\1">\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.*?)$', r'<h2 id="h2-\1">\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.*?)$', r'<h3 id="h3-\1">\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^#### (.*?)$', r'<h4 id="h4-\1">\1</h4>', html, flags=re.MULTILINE)
        
        # Code blocks with Prism syntax highlighting
        html = re.sub(r'```python\n(.*?)\n```', r'<pre><code class="language-python">\1</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'```bash\n(.*?)\n```', r'<pre><code class="language-bash">\1</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'```javascript\n(.*?)\n```', r'<pre><code class="language-javascript">\1</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'```json\n(.*?)\n```', r'<pre><code class="language-json">\1</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'```yaml\n(.*?)\n```', r'<pre><code class="language-yaml">\1</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'```dockerfile\n(.*?)\n```', r'<pre><code class="language-dockerfile">\1</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'```(.*?)\n(.*?)\n```', r'<pre><code class="language-text">\2</code></pre>', html, flags=re.DOTALL)
        
        # Inline code
        html = re.sub(r'`([^`]+)`', r'<code class="language-text">\1</code>', html)
        
        # Bold and italic
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
        
        # Alert boxes
        html = re.sub(r'🚨 \*\*(.*?)\*\*', r'<div class="alert alert-critical"><strong>🚨 \1</strong></div>', html)
        html = re.sub(r'✅ \*\*(.*?)\*\*', r'<div class="alert alert-success"><strong>✅ \1</strong></div>', html)
        html = re.sub(r'❌ \*\*(.*?)\*\*', r'<div class="alert alert-error"><strong>❌ \1</strong></div>', html)
        
        # Lists
        html = re.sub(r'^- (.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*?</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
        
        # Numbered lists
        html = re.sub(r'^\d+\. (.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        
        # Paragraphs
        lines = html.split('\n')
        in_code_block = False
        in_list = False
        processed_lines = []
        
        for line in lines:
            if line.strip().startswith('<pre>'):
                in_code_block = True
            elif line.strip().startswith('</pre>'):
                in_code_block = False
            elif line.strip().startswith('<ul>') or line.strip().startswith('<ol>'):
                in_list = True
            elif line.strip().startswith('</ul>') or line.strip().startswith('</ol>'):
                in_list = False
            elif not in_code_block and not in_list and line.strip() and not line.strip().startswith('<'):
                line = f'<p>{line}</p>'
            processed_lines.append(line)
        
        return '\n'.join(processed_lines)

    async def serve_browser(self, request):
        """Serve the documentation browser with tree view"""
        
        # Group documents by category
        featured_docs = []
        training_docs = []
        rules_docs = []
        
        for key, info in self.DOCS.items():
            category = info.get('category', 'other')
            if category == 'featured':
                featured_docs.append((key, info))
            elif category == 'training':
                training_docs.append((key, info))
            elif category == 'rules':
                rules_docs.append((key, info))
        
        # Sort featured by priority
        featured_docs.sort(key=lambda x: x[1].get('priority', 999))
        
        # Create tree view HTML
        tree_html = self.create_tree_view(featured_docs, training_docs, rules_docs)
        
        page_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Pipulate Documentation Browser</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    
    <!-- Prism CSS -->
    <link href="/static/prism.css" rel="stylesheet" />
    
    <!-- Tree view styles -->
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6; 
            margin: 0;
            padding: 0;
            background: #f8f9fa;
        }}
        
        .container {{
            display: grid;
            grid-template-columns: 300px 1fr;
            height: 100vh;
        }}
        
        .sidebar {{
            background: #fff;
            border-right: 1px solid #e9ecef;
            overflow-y: auto;
            padding: 20px;
        }}
        
        .content {{
            background: #fff;
            overflow-y: auto;
            padding: 30px;
        }}
        
        .tree {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        
        .tree-category {{
            margin-bottom: 20px;
        }}
        
        .tree-category > .tree-label {{
            font-weight: bold;
            color: #495057;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            display: block;
        }}
        
        .tree-item {{
            margin: 4px 0;
        }}
        
        .tree-link {{
            display: block;
            padding: 8px 12px;
            color: #0066cc;
            text-decoration: none;
            border-radius: 4px;
            transition: background-color 0.2s;
        }}
        
        .tree-link:hover {{
            background-color: #f8f9fa;
            text-decoration: none;
        }}
        
        .tree-link.featured {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            font-weight: 500;
        }}
        
        .tree-link.featured:hover {{
            background-color: #ffeaa7;
        }}
        
        .tree-description {{
            font-size: 0.8em;
            color: #6c757d;
            margin-top: 2px;
        }}
        
        .welcome {{
            text-align: center;
            color: #6c757d;
            margin-top: 100px;
        }}
        
        .welcome h2 {{
            color: #495057;
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .container {{
                grid-template-columns: 1fr;
                grid-template-rows: auto 1fr;
            }}
            
            .sidebar {{
                border-right: none;
                border-bottom: 1px solid #e9ecef;
                max-height: 200px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h3>📚 Documentation</h3>
            {tree_html}
        </div>
        <div class="content">
            <div class="welcome">
                <h2>Welcome to Pipulate Documentation</h2>
                <p>Select a document from the sidebar to view its content.</p>
                <p>Start with the <strong>Ultimate Pipulate Guides</strong> for comprehensive learning.</p>
            </div>
        </div>
    </div>
    
    <!-- Prism JS -->
    <script src="/static/prism.js"></script>
</body>
</html>"""
        
        return HTMLResponse(page_html)

    def create_tree_view(self, featured_docs, training_docs, rules_docs):
        """Create the tree view HTML structure"""
        html_parts = []
        
        # Featured section
        html_parts.append('<div class="tree-category">')
        html_parts.append('<span class="tree-label">🌟 Featured Guides</span>')
        html_parts.append('<ul class="tree">')
        for key, info in featured_docs:
            html_parts.append(f'''
                <li class="tree-item">
                    <a href="/docs/{key}" class="tree-link featured" target="content">
                        {info["title"]}
                    </a>
                    <div class="tree-description">{info["description"]}</div>
                </li>
            ''')
        html_parts.append('</ul>')
        html_parts.append('</div>')
        
        # Training section
        html_parts.append('<div class="tree-category">')
        html_parts.append('<span class="tree-label">📖 Training Guides</span>')
        html_parts.append('<ul class="tree">')
        for key, info in training_docs:
            html_parts.append(f'''
                <li class="tree-item">
                    <a href="/docs/{key}" class="tree-link" target="content">
                        {info["title"]}
                    </a>
                    <div class="tree-description">{info["description"]}</div>
                </li>
            ''')
        html_parts.append('</ul>')
        html_parts.append('</div>')
        
        # Rules section
        html_parts.append('<div class="tree-category">')
        html_parts.append('<span class="tree-label">⚙️ Framework Rules</span>')
        html_parts.append('<ul class="tree">')
        for key, info in rules_docs:
            html_parts.append(f'''
                <li class="tree-item">
                    <a href="/docs/{key}" class="tree-link" target="content">
                        {info["title"]}
                    </a>
                    <div class="tree-description">{info["description"]}</div>
                </li>
            ''')
        html_parts.append('</ul>')
        html_parts.append('</div>')
        
        return ''.join(html_parts)

    async def serve_document(self, request):
        """Serve individual documentation files with enhanced styling"""
        doc_key = request.path_params.get('doc_key') or request.url.path.split('/')[-1]
        
        if doc_key not in self.DOCS:
            return HTMLResponse("<h1>Document not found</h1>", status_code=404)
        
        doc_info = self.DOCS[doc_key]
        file_path = Path(doc_info['file'])
        
        if not file_path.exists():
            return HTMLResponse(f"<h1>File not found: {file_path}</h1>", status_code=404)
        
        try:
            content = file_path.read_text(encoding='utf-8')
            html_content = self.markdown_to_html(content)
            
            # Create navigation breadcrumb
            category = doc_info.get('category', 'other')
            category_name = {
                'featured': '🌟 Featured Guides',
                'training': '📖 Training Guides', 
                'rules': '⚙️ Framework Rules'
            }.get(category, 'Documentation')
            
            page_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{doc_info['title']} - Pipulate Documentation</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    
    <!-- Prism CSS -->
    <link href="/static/prism.css" rel="stylesheet" />
    
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6; 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px;
            background: #fafafa;
        }}
        
        .breadcrumb {{
            background: #fff;
            padding: 10px 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            font-size: 0.9em;
            color: #6c757d;
        }}
        
        .breadcrumb a {{
            color: #0066cc;
            text-decoration: none;
        }}
        
        .breadcrumb a:hover {{
            text-decoration: underline;
        }}
        
        .nav {{ 
            background: #fff; 
            padding: 15px 20px; 
            margin-bottom: 20px; 
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .nav h3 {{
            margin: 0 0 15px 0;
            color: #333;
        }}
        
        .nav-links {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
        }}
        
        .nav a {{ 
            color: #0066cc; 
            text-decoration: none;
            padding: 5px 10px;
            border-radius: 4px;
            transition: background-color 0.2s;
        }}
        
        .nav a:hover {{ 
            background-color: #f8f9fa;
            text-decoration: none;
        }}
        
        .current-doc {{ 
            font-weight: bold; 
            color: #333; 
            background-color: #e9ecef;
            padding: 5px 10px;
            border-radius: 4px;
        }}
        
        .content {{ 
            background: #fff; 
            padding: 30px; 
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        pre {{ 
            background: #f8f9fa; 
            padding: 20px; 
            border-radius: 6px; 
            overflow-x: auto;
            border-left: 4px solid #0066cc;
            margin: 20px 0;
        }}
        
        code:not([class*="language-"]) {{ 
            background: #f1f3f4; 
            padding: 2px 6px; 
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.9em;
        }}
        
        h1, h2, h3, h4 {{ 
            color: #333; 
            margin-top: 2em;
            margin-bottom: 1em;
        }}
        
        h1 {{ 
            border-bottom: 3px solid #0066cc; 
            padding-bottom: 10px; 
            margin-top: 0;
        }}
        
        h2 {{ 
            border-bottom: 2px solid #e9ecef; 
            padding-bottom: 8px; 
        }}
        
        h3 {{
            border-bottom: 1px solid #f1f3f4;
            padding-bottom: 5px;
        }}
        
        blockquote {{ 
            border-left: 4px solid #ddd; 
            margin: 20px 0; 
            padding-left: 20px; 
            color: #666;
            font-style: italic;
        }}
        
        .alert {{
            padding: 15px 20px;
            border-radius: 6px;
            margin: 20px 0;
            border-left: 4px solid;
        }}
        
        .alert-critical {{
            background: #fff5f5;
            border-left-color: #e53e3e;
            color: #742a2a;
        }}
        
        .alert-success {{
            background: #f0fff4;
            border-left-color: #38a169;
            color: #276749;
        }}
        
        .alert-error {{
            background: #fffaf0;
            border-left-color: #ed8936;
            color: #9c4221;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        
        th, td {{
            border: 1px solid #e9ecef;
            padding: 12px;
            text-align: left;
        }}
        
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}
            
            .content {{
                padding: 20px;
            }}
            
            .nav-links {{
                flex-direction: column;
                gap: 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="breadcrumb">
        <a href="/docs">📚 Documentation</a> → {category_name} → {doc_info['title']}
    </div>
    
    <div class="nav">
        <h3>Quick Navigation</h3>
        <div class="nav-links">
            <a href="/docs">🏠 Browser</a>
            <a href="/docs/guide1">📖 Part 1</a>
            <a href="/docs/guide2">📖 Part 2</a>
            <a href="/docs/guide3">📖 Part 3</a>
            <a href="/docs/quick_ref">⚡ Quick Ref</a>
        </div>
    </div>
    
    <div class="content">
        {html_content}
    </div>
    
    <!-- Prism JS -->
    <script src="/static/prism.js"></script>
    
    <!-- Auto-highlight code blocks -->
    <script>
        // Ensure Prism highlights all code blocks
        if (typeof Prism !== 'undefined') {{
            Prism.highlightAll();
        }}
        
        // Add copy buttons to code blocks
        document.querySelectorAll('pre code').forEach(function(block) {{
            const button = document.createElement('button');
            button.textContent = 'Copy';
            button.style.cssText = 'position: absolute; top: 5px; right: 5px; padding: 4px 8px; font-size: 12px; background: #0066cc; color: white; border: none; border-radius: 3px; cursor: pointer;';
            
            const pre = block.parentElement;
            pre.style.position = 'relative';
            pre.appendChild(button);
            
            button.addEventListener('click', function() {{
                navigator.clipboard.writeText(block.textContent).then(function() {{
                    button.textContent = 'Copied!';
                    setTimeout(function() {{
                        button.textContent = 'Copy';
                    }}, 2000);
                }});
            }});
        }});
    </script>
</body>
</html>"""
            
            return HTMLResponse(page_html)
            
        except Exception as e:
            logger.error(f"Error serving document {doc_key}: {str(e)}")
            return HTMLResponse(f"<h1>Error loading document: {str(e)}</h1>", status_code=500)

    async def landing(self, render_items=None):
        """Always appears in create_grid_left."""
        unique_id = f"docs-{int(time.time() * 1000)}"

        # Send the documentation info to the conversation history, but only once per session
        if self.pipulate is not None and not self._has_streamed:
            try:
                # First, send the verbatim redirect message
                await self.pipulate.stream(
                    self.ENDPOINT_MESSAGE,
                    verbatim=True,
                    role="system",
                    spaces_before=1,
                    spaces_after=1
                )

                # Then append the documentation info to history without displaying
                docs_message = "Available Documentation:\n"
                featured_docs = [(k, v) for k, v in self.DOCS.items() if v.get('category') == 'featured']
                featured_docs.sort(key=lambda x: x[1].get('priority', 999))
                
                for key, info in featured_docs:
                    docs_message += f"- {info['title']}: {info['description']}\n"
                
                docs_message += f"\nPlus {len([d for d in self.DOCS.values() if d.get('category') != 'featured'])} additional training guides and framework rules."
                
                self.pipulate.append_to_history(
                    f"[WIDGET CONTENT] Pipulate Documentation Browser\n{docs_message}",
                    role="system",
                    quiet=True
                )

                self._has_streamed = True
                logger.debug("Documentation info appended to conversation history")
            except Exception as e:
                logger.error(f"Error in documentation plugin: {str(e)}")

        # Create featured documentation links
        featured_docs = [(k, v) for k, v in self.DOCS.items() if v.get('category') == 'featured']
        featured_docs.sort(key=lambda x: x[1].get('priority', 999))
        
        featured_links = []
        for key, info in featured_docs:
            featured_links.append(
                Li(
                    A(
                        info['title'],
                        href=f"/docs/{key}",
                        target="_blank",
                        style="text-decoration: none; color: var(--pico-primary); font-weight: 500;"
                    ),
                    P(info['description'], style="margin: 0.25rem 0 0.75rem 0; font-size: 0.9em; color: var(--pico-muted-color);")
                )
            )

        return Div(
            H2("📚 Documentation Browser"),
            P("Essential guides and comprehensive documentation for Pipulate development."),
            
            # Featured guides
            H3("🌟 Featured Guides"),
            Ul(*featured_links, style="list-style: none; padding: 0; margin-bottom: 2rem;"),
            
            # Browse all button
            A(
                "🗂️ Browse All Documentation",
                href="/docs",
                target="_blank",
                style="display: inline-block; padding: 10px 20px; background: var(--pico-primary); color: white; text-decoration: none; border-radius: 6px; font-weight: 500;"
            ),
            
            P(
                f"Includes {len(self.DOCS)} total documents: Ultimate Guides, Quick Reference, Training materials, and Framework Rules.",
                style="margin-top: 1rem; font-size: 0.9em; color: var(--pico-muted-color);"
            ),
            
            id=unique_id
        ) 
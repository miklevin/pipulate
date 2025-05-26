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

    def __init__(self, app, pipulate, pipeline, db):
        logger.debug(f"DocumentationPlugin initialized with NAME: {self.NAME}")
        self.pipulate = pipulate
        self._has_streamed = False
        
        # Dynamically discover all documentation files
        self.DOCS = self.discover_documentation_files()
        
        # Register routes for serving individual documents
        for doc_key in self.DOCS.keys():
            app.route(f'/docs/{doc_key}', methods=['GET'])(self.serve_document)
        
        # Register route for documentation browser
        app.route('/docs', methods=['GET'])(self.serve_browser)

    def discover_documentation_files(self):
        """Dynamically discover all documentation files from training and rules directories"""
        docs = {}
        
        # Scan training directory
        training_dir = Path('training')
        if training_dir.exists():
            for file_path in training_dir.glob('*.md'):
                key, info = self.process_training_file(file_path)
                if key and info:
                    docs[key] = info
        
        # Scan cursor rules directory
        rules_dir = Path('.cursor/rules')
        if rules_dir.exists():
            for file_path in rules_dir.glob('*.mdc'):
                key, info = self.process_rules_file(file_path)
                if key and info:
                    docs[key] = info
        
        logger.info(f"Discovered {len(docs)} documentation files")
        return docs

    def process_training_file(self, file_path):
        """Process a training file and extract metadata"""
        filename = file_path.stem
        
        # Determine category and priority based on filename patterns
        category = 'training'
        priority = 100  # Default priority
        
        # Featured files get special treatment
        if 'ULTIMATE_PIPULATE_GUIDE' in filename:
            category = 'featured'
            if 'PART2' in filename:
                priority = 2
            elif 'PART3' in filename:
                priority = 3
            else:
                priority = 1  # Part 1
        elif 'QUICK_REFERENCE' in filename:
            category = 'featured'
            priority = 4
        
        # Generate title from filename or extract from file content
        title = self.generate_title_from_filename(filename)
        
        # Try to extract title and description from file content
        try:
            content = file_path.read_text(encoding='utf-8')
            extracted_title, description = self.extract_metadata_from_content(content, title)
            if extracted_title:
                title = extracted_title
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
            description = f"Documentation file: {filename}"
        
        key = self.generate_key_from_filename(filename, 'training')
        
        return key, {
            'title': title,
            'file': str(file_path),
            'description': description,
            'category': category,
            'priority': priority,
            'filename': filename
        }

    def process_rules_file(self, file_path):
        """Process a rules file and extract metadata"""
        filename = file_path.stem
        
        # Generate title from filename
        title = self.generate_title_from_filename(filename)
        
        # Try to extract title and description from file content
        try:
            content = file_path.read_text(encoding='utf-8')
            extracted_title, description = self.extract_metadata_from_content(content, title)
            if extracted_title:
                title = extracted_title
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
            description = f"Framework rule: {filename}"
        
        key = self.generate_key_from_filename(filename, 'rules')
        
        return key, {
            'title': title,
            'file': str(file_path),
            'description': description,
            'category': 'rules',
            'priority': self.get_rules_priority(filename),
            'filename': filename
        }

    def generate_title_from_filename(self, filename):
        """Generate a human-readable title from filename"""
        # Remove numeric prefixes and clean up
        title = re.sub(r'^\d+_', '', filename)
        title = re.sub(r'^[Xx][Xx]_', '', title)
        
        # Handle special cases
        title_mappings = {
            'ULTIMATE_PIPULATE_GUIDE': 'Ultimate Pipulate Guide - Part 1: Core Patterns',
            'ULTIMATE_PIPULATE_GUIDE_PART2': 'Ultimate Pipulate Guide - Part 2: Advanced Patterns',
            'ULTIMATE_PIPULATE_GUIDE_PART3': 'Ultimate Pipulate Guide - Part 3: Expert Mastery',
            'QUICK_REFERENCE': 'Quick Reference Card',
            'dev_assistant': 'Development Assistant Guide',
            'hello_workflow': 'Hello Workflow Tutorial',
            'system_prompt': 'System Prompt Configuration',
            'widget_examples': 'Widget Examples',
            'botify_api_tutorial': 'Botify API Tutorial',
            'botify_workflow': 'Botify Workflow Guide',
            '00_philosophy': 'Philosophy & Core Principles',
            '01_architecture_overview': 'Architecture Overview',
            '02_environment_and_installation': 'Environment & Installation',
            '03_workflow_core': 'Workflow Core Concepts',
            '04_chain_reaction_pattern': 'Chain Reaction Pattern',
            '06_key_system': 'Pipeline Key System',
            '07_ui_and_htmx': 'UI & HTMX Patterns',
            '08_llm_integration': 'LLM Integration',
            '09_data_and_file_operations': 'Data & File Operations',
            '10_browser_automation': 'Browser Automation',
            '11_plugin_development_guidelines': 'Plugin Development Guidelines',
            '12_server_py_overview': 'Server.py Overview',
            '13_testing_and_debugging': 'Testing & Debugging',
            '00_CRITICAL_SERVER_ENVIRONMENT': 'Critical Server Environment',
            'meta_rule_routing': 'Meta Rule Routing'
        }
        
        if filename in title_mappings:
            return title_mappings[filename]
        
        # Default: convert underscores to spaces and title case
        title = title.replace('_', ' ').title()
        return title

    def generate_key_from_filename(self, filename, category):
        """Generate a unique key for the document"""
        # Remove numeric prefixes and special characters
        clean_name = re.sub(r'^\d+_', '', filename)
        clean_name = re.sub(r'^[Xx][Xx]_', '', clean_name)
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', clean_name).lower()
        
        # Add category prefix to avoid collisions
        if category == 'training':
            return clean_name
        elif category == 'rules':
            return f"rule_{clean_name}"
        
        return clean_name

    def extract_metadata_from_content(self, content, default_title):
        """Extract title and description from file content"""
        lines = content.split('\n')
        title = default_title
        description = ""
        
        # Look for title in first few lines
        for i, line in enumerate(lines[:10]):
            line = line.strip()
            
            # Check for markdown headers
            if line.startswith('# '):
                title = line[2:].strip()
                # Clean up title
                title = re.sub(r'🚨\s*\*\*', '', title)
                title = re.sub(r'\*\*\s*🚨', '', title)
                title = title.replace('**', '').strip()
                break
            
            # Check for description patterns
            if line.startswith('## description:'):
                description = line[15:].strip()
                break
        
        # If no description found, look for first paragraph or summary
        if not description:
            for line in lines[:20]:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('```') and len(line) > 20:
                    description = line[:150] + ('...' if len(line) > 150 else '')
                    break
        
        # Fallback description
        if not description:
            if 'training' in str(content).lower():
                description = "Training guide and documentation"
            elif 'rule' in str(content).lower() or 'pattern' in str(content).lower():
                description = "Framework rules and patterns"
            else:
                description = "Documentation and guidelines"
        
        return title, description

    def get_rules_priority(self, filename):
        """Determine priority for rules files based on importance"""
        priority_map = {
            '00_CRITICAL_SERVER_ENVIRONMENT': 1,
            '00_philosophy': 2,
            '01_architecture_overview': 3,
            '03_workflow_core': 4,
            '04_chain_reaction_pattern': 5,
            '06_key_system': 6,
            '02_environment_and_installation': 7,
            '07_ui_and_htmx': 8,
            '11_plugin_development_guidelines': 9,
            '09_data_and_file_operations': 10,
            '08_llm_integration': 11,
            '10_browser_automation': 12,
            '12_server_py_overview': 13,
            '13_testing_and_debugging': 14,
            'meta_rule_routing': 15
        }
        
        return priority_map.get(filename, 100)

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

    def get_categorized_docs(self):
        """Get documents organized by category with proper sorting"""
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
        
        # Sort by priority, then by title
        featured_docs.sort(key=lambda x: (x[1].get('priority', 999), x[1]['title']))
        training_docs.sort(key=lambda x: x[1]['title'])
        rules_docs.sort(key=lambda x: (x[1].get('priority', 999), x[1]['title']))
        
        return featured_docs, training_docs, rules_docs

    async def serve_browser(self, request):
        """Serve the documentation browser with tree view"""
        
        # Get categorized documents
        featured_docs, training_docs, rules_docs = self.get_categorized_docs()
        
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
        
        .stats {{
            background: #e9ecef;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 0.9em;
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
            <div class="stats">
                📊 {len(self.DOCS)} documents discovered<br>
                🌟 {len(featured_docs)} featured guides<br>
                📖 {len(training_docs)} training files<br>
                ⚙️ {len(rules_docs)} framework rules
            </div>
            {tree_html}
        </div>
        <div class="content">
            <div class="welcome">
                <h2>Welcome to Pipulate Documentation</h2>
                <p>Select a document from the sidebar to view its content.</p>
                <p>Start with the <strong>Featured Guides</strong> for comprehensive learning.</p>
                <p><em>Documentation is automatically discovered from training/ and .cursor/rules/ directories.</em></p>
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
        if featured_docs:
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
        if training_docs:
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
        if rules_docs:
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
            
            # Get featured docs for quick navigation
            featured_docs, _, _ = self.get_categorized_docs()
            quick_nav_links = []
            for key, info in featured_docs[:4]:  # Show first 4 featured
                if key == doc_key:
                    quick_nav_links.append(f'<span class="current-doc">{info["title"][:20]}...</span>')
                else:
                    quick_nav_links.append(f'<a href="/docs/{key}">{info["title"][:20]}...</a>')
            
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
            {' '.join(quick_nav_links)}
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
                featured_docs, training_docs, rules_docs = self.get_categorized_docs()
                
                docs_message = f"Available Documentation ({len(self.DOCS)} files discovered):\n"
                
                if featured_docs:
                    docs_message += "\nFeatured Guides:\n"
                    for key, info in featured_docs:
                        docs_message += f"- {info['title']}: {info['description']}\n"
                
                docs_message += f"\nPlus {len(training_docs)} training guides and {len(rules_docs)} framework rules automatically discovered."
                
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
        featured_docs, training_docs, rules_docs = self.get_categorized_docs()
        
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
            
            # Featured guides (if any)
            *([H3("🌟 Featured Guides"), Ul(*featured_links, style="list-style: none; padding: 0; margin-bottom: 2rem;")] if featured_docs else []),
            
            # Browse all button
            A(
                "🗂️ Browse All Documentation",
                href="/docs",
                target="_blank",
                style="display: inline-block; padding: 10px 20px; background: var(--pico-primary); color: white; text-decoration: none; border-radius: 6px; font-weight: 500;"
            ),
            
            P(
                f"Automatically discovered {len(self.DOCS)} documents: {len(featured_docs)} featured guides, {len(training_docs)} training files, and {len(rules_docs)} framework rules.",
                style="margin-top: 1rem; font-size: 0.9em; color: var(--pico-muted-color);"
            ),
            
            id=unique_id
        ) 
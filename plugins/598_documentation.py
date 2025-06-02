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
    ENDPOINT_MESSAGE = "📚 Documentation Browser: When you view any document, its content is automatically added to my conversation history so you can ask me specific questions about it. Browse guides, training files, and framework rules - I'll have the full context to help you understand the content."

    def __init__(self, app, pipulate, pipeline, db):
        logger.debug(f"DocumentationPlugin initialized with NAME: {self.NAME}")
        self.pipulate = pipulate
        self._has_streamed = False
        
        # Dynamically discover all documentation files
        self.DOCS = self.discover_documentation_files()
        
        # Register routes for serving individual documents
        for doc_key in self.DOCS.keys():
            if doc_key == 'botify_api':
                # Special routes for paginated botify_api
                app.route(f'/docs/{doc_key}', methods=['GET'])(self.serve_botify_api_toc)
                app.route(f'/docs/{doc_key}/page/{{page_num}}', methods=['GET'])(self.serve_botify_api_page)
            else:
                app.route(f'/docs/{doc_key}', methods=['GET'])(self.serve_document)
        
        # Register route for documentation browser
        app.route('/docs', methods=['GET'])(self.serve_browser)
        
        # Register route for serving raw markdown content
        app.route('/docs/raw/{doc_key}', methods=['GET'])(self.serve_raw_markdown)

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
        elif filename == 'botify_api':
            category = 'featured'
            priority = 5  # After Quick Reference
        
        # Generate title from filename or extract from file content
        title = self.generate_title_from_filename(filename)
        
        # Try to extract title and description from file content
        try:
            content = file_path.read_text(encoding='utf-8')
            extracted_title, description = self.extract_metadata_from_content(content, title)
            # Only use extracted title if we don't have a specific mapping for this filename
            if extracted_title and filename not in ['ULTIMATE_PIPULATE_GUIDE', 'ULTIMATE_PIPULATE_GUIDE_PART2', 'ULTIMATE_PIPULATE_GUIDE_PART3', 'QUICK_REFERENCE', 'botify_api']:
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
            'botify_api': 'Botify API Bootcamp (Paginated)',
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
        """Convert markdown to HTML with proper Markdown semantics"""
        import html
        
        # Step 1: Protect code blocks by storing them and replacing with placeholders
        code_blocks = []
        placeholder_pattern = "CODEBLOCK_PLACEHOLDER_{}"
        
        def store_code_block(match):
            code_blocks.append(match.group(0))
            return placeholder_pattern.format(len(code_blocks) - 1)
        
        # Find and store all code blocks (any language)
        content = re.sub(r'```[a-zA-Z]*\s*\n.*?```', store_code_block, markdown_content, flags=re.DOTALL)
        
        # Step 2: Process block-level elements line by line
        lines = content.split('\n')
        processed_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Horizontal rules (must come before headers to avoid conflicts)
            if re.match(r'^-{3,}$', stripped) or re.match(r'^\*{3,}$', stripped) or re.match(r'^_{3,}$', stripped):
                processed_lines.append('<hr style="border: none; height: 2px; background: linear-gradient(to right, #e9ecef, #0066cc, #e9ecef); margin: 30px 0; border-radius: 1px;">')
                i += 1
            
            # Headers
            elif stripped.startswith('# '):
                header_text = stripped[2:].strip()
                header_id = self._slugify(header_text)
                processed_header = self._process_inline_markdown(header_text)
                processed_lines.append(f'<h1 id="{header_id}">{processed_header}</h1>')
                i += 1
            elif stripped.startswith('## '):
                header_text = stripped[3:].strip()
                header_id = self._slugify(header_text)
                processed_header = self._process_inline_markdown(header_text)
                processed_lines.append(f'<h2 id="{header_id}">{processed_header}</h2>')
                i += 1
            elif stripped.startswith('### '):
                header_text = stripped[4:].strip()
                header_id = self._slugify(header_text)
                processed_header = self._process_inline_markdown(header_text)
                processed_lines.append(f'<h3 id="{header_id}">{processed_header}</h3>')
                i += 1
            elif stripped.startswith('#### '):
                header_text = stripped[5:].strip()
                header_id = self._slugify(header_text)
                processed_header = self._process_inline_markdown(header_text)
                processed_lines.append(f'<h4 id="{header_id}">{processed_header}</h4>')
                i += 1
            
            # Blockquotes
            elif stripped.startswith('> '):
                blockquote_lines = []
                while i < len(lines) and lines[i].strip().startswith('> '):
                    # Remove the '> ' prefix and collect the content
                    quote_content = lines[i].strip()[2:]
                    blockquote_lines.append(quote_content)
                    i += 1
                
                # Process the blockquote content as markdown (recursively)
                blockquote_content = '\n'.join(blockquote_lines)
                processed_blockquote = self._process_inline_markdown(blockquote_content)
                processed_lines.append(f'<blockquote>{processed_blockquote}</blockquote>')
            
            # Unordered lists
            elif stripped.startswith('- ') or stripped.startswith('* ') or stripped.startswith('+ '):
                list_items = []
                while i < len(lines):
                    current_line = lines[i].strip()
                    if current_line.startswith('- ') or current_line.startswith('* ') or current_line.startswith('+ '):
                        item_content = current_line[2:].strip()
                        # Handle multi-line list items
                        i += 1
                        while i < len(lines) and lines[i].startswith('  ') and lines[i].strip():
                            item_content += ' ' + lines[i].strip()
                            i += 1
                        list_items.append(self._process_inline_markdown(item_content))
                    else:
                        break
                
                if list_items:
                    list_html = '<ul>' + ''.join(f'<li>{item}</li>' for item in list_items) + '</ul>'
                    processed_lines.append(list_html)
            
            # Ordered lists
            elif re.match(r'^\d+\. ', stripped):
                list_items = []
                while i < len(lines):
                    current_line = lines[i].strip()
                    if re.match(r'^\d+\. ', current_line):
                        item_content = re.sub(r'^\d+\. ', '', current_line)
                        # Handle multi-line list items
                        i += 1
                        while i < len(lines) and lines[i].startswith('  ') and lines[i].strip():
                            item_content += ' ' + lines[i].strip()
                            i += 1
                        list_items.append(self._process_inline_markdown(item_content))
                    else:
                        break
                
                if list_items:
                    list_html = '<ol>' + ''.join(f'<li>{item}</li>' for item in list_items) + '</ol>'
                    processed_lines.append(list_html)
            
            # Tables (pipe-delimited)
            elif '|' in stripped and len(stripped.split('|')) >= 3:
                # Look ahead to see if this is a table
                table_lines = []
                table_start = i
                
                # Collect potential table lines
                while i < len(lines):
                    current_line = lines[i].strip()
                    if not current_line:
                        break
                    if '|' in current_line and len(current_line.split('|')) >= 3:
                        table_lines.append(current_line)
                        i += 1
                    else:
                        break
                
                # Check if we have a valid table (at least header + separator + data)
                if len(table_lines) >= 2:
                    # Check if second line is a separator (contains dashes and pipes)
                    second_line = table_lines[1]
                    if re.match(r'^\s*\|[\s\-\|:]+\|\s*$', second_line):
                        # Process as table
                        table_html = self._process_table(table_lines)
                        processed_lines.append(table_html)
                    else:
                        # Not a table, backtrack and process as regular lines
                        i = table_start
                        processed_lines.append(line)
                        i += 1
                else:
                    # Not enough lines for a table, backtrack
                    i = table_start
                    processed_lines.append(line)
                    i += 1
            
            # Empty lines (potential paragraph breaks)
            elif not stripped:
                processed_lines.append('')
                i += 1
            
            # Code block placeholders (preserve as-is)
            elif re.match(r'^CODEBLOCK_PLACEHOLDER_\d+$', stripped):
                processed_lines.append(line)
                i += 1
            
            # Regular text lines (will be grouped into paragraphs later)
            else:
                processed_lines.append(line)
                i += 1
        
        # Step 3: Group consecutive non-empty, non-HTML lines into paragraphs
        final_lines = []
        i = 0
        
        while i < len(processed_lines):
            line = processed_lines[i]
            stripped = line.strip()
            
            # If it's an HTML element or empty line, keep as-is
            if not stripped or stripped.startswith('<') or re.match(r'^CODEBLOCK_PLACEHOLDER_\d+$', stripped):
                final_lines.append(line)
                i += 1
            else:
                # Start collecting paragraph content
                paragraph_lines = []
                while i < len(processed_lines):
                    current_line = processed_lines[i]
                    current_stripped = current_line.strip()
                    
                    # Stop if we hit an empty line, HTML element, or placeholder
                    if (not current_stripped or 
                        current_stripped.startswith('<') or 
                        re.match(r'^CODEBLOCK_PLACEHOLDER_\d+$', current_stripped)):
                        break
                    
                    # Handle hard line breaks (two spaces at end of line)
                    if current_line.rstrip().endswith('  '):
                        paragraph_lines.append(current_line.rstrip()[:-2] + '<br>')
                    else:
                        paragraph_lines.append(current_line.strip())
                    i += 1
                
                if paragraph_lines:
                    # Join lines with spaces and process inline markdown
                    paragraph_content = ' '.join(paragraph_lines)
                    processed_paragraph = self._process_inline_markdown(paragraph_content)
                    final_lines.append(f'<p>{processed_paragraph}</p>')
        
        # Step 4: Restore code blocks
        result = '\n'.join(final_lines)
        for i, code_block in enumerate(code_blocks):
            placeholder = placeholder_pattern.format(i)
            processed_block = self.process_code_block(code_block)
            # Use a more precise replacement to avoid partial matches
            if placeholder in result:
                result = result.replace(placeholder, processed_block, 1)  # Replace only first occurrence
        
        return result
    
    def _slugify(self, text):
        """Convert text to URL-friendly slug for header IDs"""
        import re
        # Remove HTML tags if any
        text = re.sub(r'<[^>]+>', '', text)
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')
    
    def _process_inline_markdown(self, text):
        """Process inline markdown elements (bold, italic, code, alerts, links)"""
        import html
        
        # Escape HTML first
        text = html.escape(text)
        
        # Alert boxes (process before bold/italic to avoid conflicts)
        # Handle patterns with trailing sirens: 🚨 **text** 🚨
        text = re.sub(r'🚨 \*\*(.*?)\*\* 🚨', r'<div class="alert alert-critical"><strong>🚨 \1 🚨</strong></div>', text)
        text = re.sub(r'✅ \*\*(.*?)\*\* ✅', r'<div class="alert alert-success"><strong>✅ \1 ✅</strong></div>', text)
        text = re.sub(r'❌ \*\*(.*?)\*\* ❌', r'<div class="alert alert-error"><strong>❌ \1 ❌</strong></div>', text)
        
        # Handle patterns without trailing emoji: 🚨 **text**
        text = re.sub(r'🚨 \*\*(.*?)\*\*', r'<div class="alert alert-critical"><strong>🚨 \1</strong></div>', text)
        text = re.sub(r'✅ \*\*(.*?)\*\*', r'<div class="alert alert-success"><strong>✅ \1</strong></div>', text)
        text = re.sub(r'❌ \*\*(.*?)\*\*', r'<div class="alert alert-error"><strong>❌ \1</strong></div>', text)
        
        # Markdown links [text](url) - process before inline code to avoid conflicts
        def process_link(match):
            link_text = match.group(1)
            link_url = match.group(2)
            # Check if it's a relative URL (starts with /) or absolute URL
            if link_url.startswith('/') or link_url.startswith('http'):
                return f'<a href="{link_url}">{link_text}</a>'
            else:
                # For other URLs, assume they need http:// prefix if not present
                if not link_url.startswith(('http://', 'https://', 'mailto:', 'ftp://')):
                    link_url = f'http://{link_url}'
                return f'<a href="{link_url}">{link_text}</a>'
        
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', process_link, text)
        
        # Inline code (process before bold/italic to avoid conflicts)
        text = re.sub(r'`([^`]+)`', r'<code class="language-text">\1</code>', text)
        
        # Bold and italic
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
        
        return text

    def _process_table(self, table_lines):
        """Process markdown table lines into HTML table"""
        if len(table_lines) < 2:
            return ''
        
        # Parse header row
        header_row = table_lines[0].strip()
        header_cells = [cell.strip() for cell in header_row.split('|') if cell.strip()]
        
        # Skip separator row (table_lines[1])
        
        # Parse data rows
        data_rows = []
        for line in table_lines[2:]:
            if line.strip():
                cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                # Pad cells to match header length
                while len(cells) < len(header_cells):
                    cells.append('')
                data_rows.append(cells[:len(header_cells)])  # Trim excess cells
        
        # Build HTML table
        html_parts = ['<table>']
        
        # Header
        html_parts.append('<thead>')
        html_parts.append('<tr>')
        for cell in header_cells:
            processed_cell = self._process_inline_markdown(cell)
            html_parts.append(f'<th>{processed_cell}</th>')
        html_parts.append('</tr>')
        html_parts.append('</thead>')
        
        # Body
        if data_rows:
            html_parts.append('<tbody>')
            for row in data_rows:
                html_parts.append('<tr>')
                for cell in row:
                    processed_cell = self._process_inline_markdown(cell)
                    html_parts.append(f'<td>{processed_cell}</td>')
                html_parts.append('</tr>')
            html_parts.append('</tbody>')
        
        html_parts.append('</table>')
        return ''.join(html_parts)

    def process_code_block(self, code_block):
        """Process a single code block and convert to HTML with proper escaping"""
        import html
        
        # Extract language and content
        match = re.match(r'```([a-zA-Z]*)\s*\n?(.*?)```', code_block, flags=re.DOTALL)
        if match:
            language = match.group(1) or 'text'
            content = match.group(2)
            # Properly escape HTML in code content
            escaped_content = html.escape(content)
            return f'<pre><code class="language-{language}">{escaped_content}</code></pre>'
        return html.escape(code_block)

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
                        <a href="/docs/{key}" class="tree-link featured">
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
                        <a href="/docs/{key}" class="tree-link">
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
                        <a href="/docs/{key}" class="tree-link">
                            {info["title"]}
                        </a>
                        <div class="tree-description">{info["description"]}</div>
                    </li>
                ''')
            html_parts.append('</ul>')
            html_parts.append('</div>')
        
        return ''.join(html_parts)

    async def serve_raw_markdown(self, request):
        """Serve raw markdown content for copying"""
        doc_key = request.path_params.get('doc_key') or request.url.path.split('/')[-1]
        
        if doc_key not in self.DOCS:
            return HTMLResponse("Document not found", status_code=404)
        
        doc_info = self.DOCS[doc_key]
        file_path = Path(doc_info['file'])
        
        if not file_path.exists():
            return HTMLResponse("File not found", status_code=404)
        
        try:
            content = file_path.read_text(encoding='utf-8')
            return Response(content, media_type='text/plain; charset=utf-8')
        except Exception as e:
            logger.error(f"Error serving raw markdown {doc_key}: {str(e)}")
            return HTMLResponse("Error reading file", status_code=500)

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
            
            # Add to conversation history if not already viewed
            doc_viewed_key = f'doc_viewed_{doc_key}'
            if doc_viewed_key not in self.db:
                # Add markdown content to conversation history
                from server import append_to_conversation
                context_message = f"The user is now viewing the documentation page '{doc_info['title']}'. Here is the content:\n\n{content}"
                append_to_conversation(context_message, role='system')
                
                # Notify user that the document is now available for questions
                if self.pipulate and hasattr(self.pipulate, 'message_queue'):
                    import asyncio
                    asyncio.create_task(self.pipulate.message_queue.add(
                        self.pipulate, 
                        f"📖 Document '{doc_info['title']}' has been loaded into my memory. I'm ready to answer questions about its content!",
                        verbatim=True,
                        role='system'
                    ))
                
                # Mark as viewed to prevent spam
                self.db[doc_viewed_key] = 'viewed'
            
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
        
        .copy-markdown-btn {{
            background: #28a745;
            color: white;
            border: none;
            padding: 5px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            transition: background-color 0.2s;
        }}
        
        .copy-markdown-btn:hover {{
            background: #218838;
        }}
        
        .copy-markdown-btn:active {{
            background: #1e7e34;
        }}
        
        .copy-markdown-btn.copying {{
            background: #ffc107;
            color: #212529;
        }}
        
        .copy-markdown-btn.success {{
            background: #20c997;
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
        
        /* Custom copy button styling - override Prism defaults */
        pre .copy-button {{
            position: absolute !important;
            top: 5px !important;
            right: 5px !important;
            padding: 4px 8px !important;
            font-size: 12px !important;
            background: #0066cc !important;
            color: white !important;
            border: none !important;
            border-radius: 3px !important;
            cursor: pointer !important;
            transition: background-color 0.2s ease !important;
            z-index: 10 !important;
        }}
        
        /* Disable Prism's default hover effects */
        pre .copy-button:hover {{
            background: #0052a3 !important;
            transform: none !important;
            box-shadow: none !important;
        }}
        
        /* Disable any Prism copy button pseudo-elements or overlays */
        pre .copy-button::before,
        pre .copy-button::after {{
            display: none !important;
        }}
        
        /* Ensure pre container is positioned for absolute button positioning */
        pre {{
            position: relative !important;
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
        
        /* Link styling */
        a {{
            color: #0066cc;
            text-decoration: none;
            transition: color 0.2s ease;
        }}
        
        a:hover {{
            color: #0052a3;
            text-decoration: underline;
        }}
        
        a:visited {{
            color: #5a6c7d;
        }}
        
        /* Links in content should be more prominent */
        .content a {{
            font-weight: 500;
            border-bottom: 1px solid transparent;
        }}
        
        .content a:hover {{
            border-bottom-color: #0066cc;
            text-decoration: none;
        }}
        
        blockquote {{ 
            border-left: 4px solid #ddd; 
            margin: 20px 0; 
            padding-left: 20px; 
            color: #666;
            font-style: italic;
        }}
        
        /* Enhanced blockquote styling */
        blockquote {{
            background: #f8f9fa;
            border-left: 5px solid #0066cc;
            margin: 25px 0;
            padding: 20px 25px;
            position: relative;
            font-style: italic;
            color: #495057;
            border-radius: 0 8px 8px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        blockquote::before {{
            content: '"';
            font-size: 4em;
            color: #0066cc;
            position: absolute;
            left: 10px;
            top: -10px;
            font-family: Georgia, serif;
            opacity: 0.3;
        }}
        
        blockquote p {{
            margin: 0;
            padding-left: 30px;
            line-height: 1.7;
        }}
        
        blockquote p:first-child {{
            margin-top: 0;
        }}
        
        blockquote p:last-child {{
            margin-bottom: 0;
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
            <button id="copy-markdown-btn" class="copy-markdown-btn">📋 Copy Markdown</button>
        </div>
    </div>
    
    <div class="content">
        {html_content}
    </div>
    
    <!-- Prism JS -->
    <script src="/static/prism.js"></script>
    
    <!-- Auto-highlight code blocks and Copy Markdown functionality -->
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            // Ensure Prism highlights all code blocks
            if (typeof Prism !== 'undefined') {{
                Prism.highlightAll();
            }}
            
            // Add copy buttons to code blocks
            document.querySelectorAll('pre code').forEach(function(block) {{
                const button = document.createElement('button');
                button.textContent = 'Copy';
                button.className = 'copy-button';
                
                const pre = block.parentElement;
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
            
            // Copy Markdown functionality - check if button exists
            const copyMarkdownBtn = document.getElementById('copy-markdown-btn');
            if (copyMarkdownBtn) {{
                copyMarkdownBtn.addEventListener('click', async function() {{
                    const button = this;
                    const originalText = button.textContent;
                    
                    try {{
                        // Show loading state
                        button.textContent = '⏳ Fetching...';
                        button.classList.add('copying');
                        button.disabled = true;
                        
                        // Fetch the raw markdown content
                        const response = await fetch('/docs/raw/{doc_key}');
                        if (!response.ok) {{
                            throw new Error('Failed to fetch markdown content');
                        }}
                        
                        const markdownContent = await response.text();
                        
                        // Copy to clipboard
                        await navigator.clipboard.writeText(markdownContent);
                        
                        // Show success state
                        button.textContent = '✅ Copied!';
                        button.classList.remove('copying');
                        button.classList.add('success');
                        
                        // Reset after 3 seconds
                        setTimeout(function() {{
                            button.textContent = originalText;
                            button.classList.remove('success');
                            button.disabled = false;
                        }}, 3000);
                        
                    }} catch (error) {{
                        console.error('Error copying markdown:', error);
                        
                        // Show error state
                        button.textContent = '❌ Error';
                        button.classList.remove('copying');
                        
                        // Reset after 3 seconds
                        setTimeout(function() {{
                            button.textContent = originalText;
                            button.disabled = false;
                        }}, 3000);
                    }}
                }});
            }}
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
            P(Strong("🧠 Smart Documentation Training:"), " When you view any document below, its content is automatically added to the LLM's conversation history. This means you can then ask the chatbot specific questions about that document's content, and it will have the full context to provide detailed answers."),
            
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

    def parse_botify_api_pages(self, content):
        """Parse the botify_api.md content into pages separated by 80 hyphens"""
        pages = []
        current_page = []
        lines = content.split('\n')
        
        for line in lines:
            if line.strip() == '-' * 80:
                # Found a page separator
                if current_page:
                    pages.append('\n'.join(current_page))
                    current_page = []
            else:
                current_page.append(line)
        
        # Add the last page if there's content
        if current_page:
            pages.append('\n'.join(current_page))
        
        return pages

    def extract_botify_api_toc(self, pages):
        """Extract table of contents from botify_api pages"""
        toc = []
        
        for page_num, page_content in enumerate(pages, 1):
            lines = page_content.split('\n')
            page_title = f"Page {page_num}"
            
            # Look for the first H1 heading in the page
            for line in lines:
                line = line.strip()
                if line.startswith('# ') and not line.startswith('```'):
                    page_title = line[2:].strip()
                    break
            
            # Get a brief description from the first paragraph
            description = ""
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('```') and len(line) > 20:
                    description = line[:100] + ('...' if len(line) > 100 else '')
                    break
            
            toc.append({
                'page_num': page_num,
                'title': page_title,
                'description': description or "Documentation content"
            })
        
        return toc

    async def serve_botify_api_toc(self, request):
        """Serve the table of contents for botify_api.md"""
        doc_info = self.DOCS['botify_api']
        file_path = Path(doc_info['file'])
        
        if not file_path.exists():
            return HTMLResponse("File not found", status_code=404)
        
        try:
            content = file_path.read_text(encoding='utf-8')
            pages = self.parse_botify_api_pages(content)
            toc = self.extract_botify_api_toc(pages)
            
            # Create table of contents HTML
            toc_items = []
            for item in toc:
                toc_items.append(f'''
                    <div class="toc-item">
                        <h3><a href="/docs/botify_api/page/{item['page_num']}">{item['title']}</a></h3>
                        <p class="toc-description">{item['description']}</p>
                        <span class="page-number">Page {item['page_num']} of {len(pages)}</span>
                    </div>
                ''')
            
            page_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Botify API Documentation - Table of Contents</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6; 
            max-width: 1000px; 
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
        
        .header {{
            background: #fff;
            padding: 30px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .header h1 {{
            color: #333;
            margin: 0 0 10px 0;
        }}
        
        .header .subtitle {{
            color: #666;
            font-size: 1.1em;
        }}
        
        .stats {{
            background: #e3f2fd;
            padding: 15px;
            border-radius: 6px;
            margin: 20px 0;
            text-align: center;
            color: #1565c0;
        }}
        
        .toc-container {{
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .toc-item {{
            padding: 20px;
            border-bottom: 1px solid #e9ecef;
            transition: background-color 0.2s;
        }}
        
        .toc-item:last-child {{
            border-bottom: none;
        }}
        
        .toc-item:hover {{
            background-color: #f8f9fa;
        }}
        
        .toc-item h3 {{
            margin: 0 0 8px 0;
        }}
        
        .toc-item h3 a {{
            color: #0066cc !important;
            text-decoration: none;
            font-size: 1.1em;
            font-weight: 600;
        }}
        
        .toc-item h3 a:hover {{
            color: #0052a3 !important;
            text-decoration: underline;
        }}
        
        .toc-item h3 a:visited {{
            color: #0066cc !important;
        }}
        
        .toc-description {{
            color: #666;
            margin: 8px 0;
            font-size: 0.95em;
        }}
        
        .page-number {{
            background: #e9ecef;
            color: #495057;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 500;
        }}
        
        .navigation {{
            background: #fff;
            padding: 15px 20px;
            margin-top: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .nav-button {{
            display: inline-block;
            padding: 10px 20px;
            background: #0066cc;
            color: white !important;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            transition: background-color 0.2s;
        }}
        
        .nav-button:hover {{
            background: #0052a3;
            color: white !important;
            text-decoration: none;
        }}
        
        .nav-button:visited {{
            color: white !important;
        }}
        
        .nav-button.toc {{
            background: #6c757d;
            color: white !important;
        }}
        
        .nav-button.toc:hover {{
            background: #545b62;
            color: white !important;
        }}
        
        .nav-button.toc:visited {{
            color: white !important;
        }}
        
        .nav-center {{
            text-align: center;
            color: #666;
        }}
        
        pre {{ 
            background: #f8f9fa; 
            padding: 20px; 
            border-radius: 6px; 
            overflow-x: auto;
            border-left: 4px solid #0066cc;
            margin: 20px 0;
        }}
        
        /* Custom copy button styling - override Prism defaults */
        pre .copy-button {{
            position: absolute !important;
            top: 5px !important;
            right: 5px !important;
            padding: 4px 8px !important;
            font-size: 12px !important;
            background: #0066cc !important;
            color: white !important;
            border: none !important;
            border-radius: 3px !important;
            cursor: pointer !important;
            transition: background-color 0.2s ease !important;
            z-index: 10 !important;
        }}
        
        /* Disable Prism's default hover effects */
        pre .copy-button:hover {{
            background: #0052a3 !important;
            transform: none !important;
            box-shadow: none !important;
        }}
        
        /* Disable any Prism copy button pseudo-elements or overlays */
        pre .copy-button::before,
        pre .copy-button::after {{
            display: none !important;
        }}
        
        /* Ensure pre container is positioned for absolute button positioning */
        pre {{
            position: relative !important;
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
        
        /* Link styling */
        a {{
            color: #0066cc;
            text-decoration: none;
            transition: color 0.2s ease;
        }}
        
        a:hover {{
            color: #0052a3;
            text-decoration: underline;
        }}
        
        a:visited {{
            color: #5a6c7d;
        }}
        
        /* Links in content should be more prominent */
        .content a {{
            font-weight: 500;
            border-bottom: 1px solid transparent;
        }}
        
        .content a:hover {{
            border-bottom-color: #0066cc;
            text-decoration: none;
        }}
        
        blockquote {{ 
            border-left: 4px solid #ddd; 
            margin: 20px 0; 
            padding-left: 20px; 
            color: #666;
            font-style: italic;
        }}
        
        /* Enhanced blockquote styling */
        blockquote {{
            background: #f8f9fa;
            border-left: 5px solid #0066cc;
            margin: 25px 0;
            padding: 20px 25px;
            position: relative;
            font-style: italic;
            color: #495057;
            border-radius: 0 8px 8px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        blockquote::before {{
            content: '"';
            font-size: 4em;
            color: #0066cc;
            position: absolute;
            left: 10px;
            top: -10px;
            font-family: Georgia, serif;
            opacity: 0.3;
        }}
        
        blockquote p {{
            margin: 0;
            padding-left: 30px;
            line-height: 1.7;
        }}
        
        blockquote p:first-child {{
            margin-top: 0;
        }}
        
        blockquote p:last-child {{
            margin-bottom: 0;
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
            .page-header {{
                flex-direction: column;
                gap: 10px;
                text-align: center;
            }}
            
            .navigation {{
                flex-direction: column;
                gap: 15px;
            }}
            
            .nav-center {{
                order: -1;
            }}
        }}
    </style>
</head>
<body>
    <div class="breadcrumb">
        <a href="/docs">📚 Documentation</a> → 📖 Training Guides → Botify API Documentation
    </div>
    
    <div class="header">
        <h1>📊 Botify API Documentation</h1>
        <p class="subtitle">Complete guide to the Botify API with practical examples</p>
        <div class="stats">
            📄 {len(pages)} pages • 📝 {len(content.split())} words • ⏱️ ~{len(content.split()) // 200} min read
        </div>
    </div>
    
    <div class="toc-container">
        {''.join(toc_items)}
    </div>
    
    <div class="navigation">
        <a href="/docs" class="nav-button">🏠 Back to Documentation</a>
        <a href="/docs/botify_api/page/1" class="nav-button">📖 Start Reading</a>
    </div>
</body>
</html>"""
            
            return HTMLResponse(page_html)
            
        except Exception as e:
            logger.error(f"Error serving botify_api TOC: {str(e)}")
            return HTMLResponse(f"Error loading document: {str(e)}", status_code=500)

    async def serve_botify_api_page(self, request):
        """Serve a specific page of botify_api.md"""
        page_num = int(request.path_params.get('page_num', 1))
        doc_info = self.DOCS['botify_api']
        file_path = Path(doc_info['file'])
        
        if not file_path.exists():
            return HTMLResponse("File not found", status_code=404)
        
        try:
            content = file_path.read_text(encoding='utf-8')
            pages = self.parse_botify_api_pages(content)
            
            if page_num < 1 or page_num > len(pages):
                return HTMLResponse("Page not found", status_code=404)
            
            page_content = pages[page_num - 1]
            
            # Add to conversation history if not already viewed
            api_page_viewed_key = f'botify_api_page_viewed_{page_num}'
            if api_page_viewed_key not in self.db:
                # Add markdown content to conversation history
                from server import append_to_conversation
                context_message = f"The user is now viewing page {page_num} of the Botify API documentation. Here is the content:\n\n{page_content}"
                append_to_conversation(context_message, role='system')
                
                # Get page title for better user notification
                lines = page_content.split('\n')
                page_title = f"Page {page_num}"
                for line in lines:
                    line = line.strip()
                    if line.startswith('# ') and not line.startswith('```'):
                        page_title = line[2:].strip()
                        break
                
                # Notify user that the document is now available for questions
                if self.pipulate and hasattr(self.pipulate, 'message_queue'):
                    import asyncio
                    asyncio.create_task(self.pipulate.message_queue.add(
                        self.pipulate, 
                        f"📖 Botify API Documentation '{page_title}' has been loaded into my memory. I'm ready to answer questions about its content!",
                        verbatim=True,
                        role='system'
                    ))
                
                # Mark as viewed to prevent spam
                self.db[api_page_viewed_key] = 'viewed'
            
            html_content = self.markdown_to_html(page_content)
            
            # Get page title
            lines = page_content.split('\n')
            page_title = f"Page {page_num}"
            for line in lines:
                line = line.strip()
                if line.startswith('# ') and not line.startswith('```'):
                    page_title = line[2:].strip()
                    break
            
            # Navigation buttons
            prev_button = ""
            next_button = ""
            
            if page_num > 1:
                prev_button = f'<a href="/docs/botify_api/page/{page_num - 1}" class="nav-button prev">← Previous</a>'
            
            if page_num < len(pages):
                next_button = f'<a href="/docs/botify_api/page/{page_num + 1}" class="nav-button next">Next →</a>'
            
            page_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{page_title} - Botify API Documentation</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=2">
    
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
            color: #0066cc !important;
            text-decoration: none;
            font-weight: 500;
        }}
        
        .breadcrumb a:hover {{
            color: #0052a3 !important;
            text-decoration: underline;
        }}
        
        .breadcrumb a:visited {{
            color: #0066cc !important;
        }}
        
        .page-header {{
            background: #fff;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .page-info {{
            color: #666;
        }}
        
        .copy-markdown-btn {{
            background: #28a745;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            transition: background-color 0.2s;
        }}
        
        .copy-markdown-btn:hover {{
            background: #218838;
        }}
        
        .copy-markdown-btn.copying {{
            background: #ffc107;
            color: #212529;
        }}
        
        .copy-markdown-btn.success {{
            background: #20c997;
        }}
        
        .content {{ 
            background: #fff; 
            padding: 30px; 
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        
        .navigation {{
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .nav-button {{
            display: inline-block;
            padding: 10px 20px;
            background: #0066cc;
            color: white !important;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            transition: background-color 0.2s;
        }}
        
        .nav-button:hover {{
            background: #0052a3;
            color: white !important;
            text-decoration: none;
        }}
        
        .nav-button:visited {{
            color: white !important;
        }}
        
        .nav-button.toc {{
            background: #6c757d;
            color: white !important;
        }}
        
        .nav-button.toc:hover {{
            background: #545b62;
            color: white !important;
        }}
        
        .nav-button.toc:visited {{
            color: white !important;
        }}
        
        .nav-center {{
            text-align: center;
            color: #666;
        }}
        
        pre {{ 
            background: #f8f9fa; 
            padding: 20px; 
            border-radius: 6px; 
            overflow-x: auto;
            border-left: 4px solid #0066cc;
            margin: 20px 0;
        }}
        
        /* Custom copy button styling - override Prism defaults */
        pre .copy-button {{
            position: absolute !important;
            top: 5px !important;
            right: 5px !important;
            padding: 4px 8px !important;
            font-size: 12px !important;
            background: #0066cc !important;
            color: white !important;
            border: none !important;
            border-radius: 3px !important;
            cursor: pointer !important;
            transition: background-color 0.2s ease !important;
            z-index: 10 !important;
        }}
        
        /* Disable Prism's default hover effects */
        pre .copy-button:hover {{
            background: #0052a3 !important;
            transform: none !important;
            box-shadow: none !important;
        }}
        
        /* Disable any Prism copy button pseudo-elements or overlays */
        pre .copy-button::before,
        pre .copy-button::after {{
            display: none !important;
        }}
        
        /* Ensure pre container is positioned for absolute button positioning */
        pre {{
            position: relative !important;
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
        
        /* Link styling */
        a {{
            color: #0066cc;
            text-decoration: none;
            transition: color 0.2s ease;
        }}
        
        a:hover {{
            color: #0052a3;
            text-decoration: underline;
        }}
        
        a:visited {{
            color: #5a6c7d;
        }}
        
        /* Links in content should be more prominent */
        .content a {{
            font-weight: 500;
            border-bottom: 1px solid transparent;
        }}
        
        .content a:hover {{
            border-bottom-color: #0066cc;
            text-decoration: none;
        }}
        
        blockquote {{ 
            border-left: 4px solid #ddd; 
            margin: 20px 0; 
            padding-left: 20px; 
            color: #666;
            font-style: italic;
        }}
        
        /* Enhanced blockquote styling */
        blockquote {{
            background: #f8f9fa;
            border-left: 5px solid #0066cc;
            margin: 25px 0;
            padding: 20px 25px;
            position: relative;
            font-style: italic;
            color: #495057;
            border-radius: 0 8px 8px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        blockquote::before {{
            content: '"';
            font-size: 4em;
            color: #0066cc;
            position: absolute;
            left: 10px;
            top: -10px;
            font-family: Georgia, serif;
            opacity: 0.3;
        }}
        
        blockquote p {{
            margin: 0;
            padding-left: 30px;
            line-height: 1.7;
        }}
        
        blockquote p:first-child {{
            margin-top: 0;
        }}
        
        blockquote p:last-child {{
            margin-bottom: 0;
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
            .page-header {{
                flex-direction: column;
                gap: 10px;
                text-align: center;
            }}
            
            .navigation {{
                flex-direction: column;
                gap: 15px;
            }}
            
            .nav-center {{
                order: -1;
            }}
        }}
    </style>
</head>
<body>
    <div class="breadcrumb">
        <a href="/docs">📚 Documentation</a> → 
        <a href="/docs/botify_api">Botify API</a> → 
        Page {page_num}
    </div>
    
    <div class="page-header">
        <div class="page-info">
            <strong>{page_title}</strong><br>
            Page {page_num} of {len(pages)}
        </div>
        <button id="copy-markdown-btn" class="copy-markdown-btn">📋 Copy Page Markdown</button>
    </div>
    
    <!-- Top Navigation -->
    <div class="navigation">
        <div>
            {prev_button}
        </div>
        <div class="nav-center">
            <a href="/docs/botify_api" class="nav-button toc">📋 Table of Contents</a>
        </div>
        <div>
            {next_button}
        </div>
    </div>
    
    <div class="content">
        {html_content}
    </div>
    
    <!-- Bottom Navigation -->
    <div class="navigation">
        <div>
            {prev_button}
        </div>
        <div class="nav-center">
            <a href="/docs/botify_api" class="nav-button toc">📋 Table of Contents</a>
        </div>
        <div>
            {next_button}
        </div>
    </div>
    
    <!-- Prism JS -->
    <script src="/static/prism.js"></script>
    
    <!-- Auto-highlight code blocks and Copy Markdown functionality -->
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            // Ensure Prism highlights all code blocks
            if (typeof Prism !== 'undefined') {{
                Prism.highlightAll();
            }}
            
            // Add copy buttons to code blocks
            document.querySelectorAll('pre code').forEach(function(block) {{
                const button = document.createElement('button');
                button.textContent = 'Copy';
                button.className = 'copy-button';
                
                const pre = block.parentElement;
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
            
            // Copy Page Markdown functionality
            const copyMarkdownBtn = document.getElementById('copy-markdown-btn');
            if (copyMarkdownBtn) {{
                copyMarkdownBtn.addEventListener('click', async function() {{
                    const button = this;
                    const originalText = button.textContent;
                    
                    try {{
                        // Show loading state
                        button.textContent = '⏳ Fetching...';
                        button.classList.add('copying');
                        button.disabled = true;
                        
                        // Get the raw page content
                        const pageContent = {repr(page_content)};
                        
                        // Copy to clipboard
                        await navigator.clipboard.writeText(pageContent);
                        
                        // Show success state
                        button.textContent = '✅ Copied!';
                        button.classList.remove('copying');
                        button.classList.add('success');
                        
                        // Reset after 3 seconds
                        setTimeout(function() {{
                            button.textContent = originalText;
                            button.classList.remove('success');
                            button.disabled = false;
                        }}, 3000);
                        
                    }} catch (error) {{
                        console.error('Error copying markdown:', error);
                        
                        // Show error state
                        button.textContent = '❌ Error';
                        button.classList.remove('copying');
                        
                        // Reset after 3 seconds
                        setTimeout(function() {{
                            button.textContent = originalText;
                            button.disabled = false;
                        }}, 3000);
                    }}
                }});
            }}
        }});
    </script>
</body>
</html>"""
            
            return HTMLResponse(page_html)
            
        except Exception as e:
            logger.error(f"Error serving botify_api page {page_num}: {str(e)}")
            return HTMLResponse(f"Error loading page: {str(e)}", status_code=500) 
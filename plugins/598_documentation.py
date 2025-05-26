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

    # Define the available documentation files
    DOCS = {
        'guide1': {
            'title': 'Ultimate Pipulate Guide - Part 1: Core Patterns',
            'file': 'training/ULTIMATE_PIPULATE_GUIDE.md',
            'description': 'Essential patterns every developer must know'
        },
        'guide2': {
            'title': 'Ultimate Pipulate Guide - Part 2: Advanced Patterns', 
            'file': 'training/ULTIMATE_PIPULATE_GUIDE_PART2.md',
            'description': 'Advanced workflow and data handling patterns'
        },
        'guide3': {
            'title': 'Ultimate Pipulate Guide - Part 3: Expert Mastery',
            'file': 'training/ULTIMATE_PIPULATE_GUIDE_PART3.md', 
            'description': 'Expert-level patterns and advanced techniques'
        }
    }

    def __init__(self, app, pipulate, pipeline, db):
        logger.debug(f"DocumentationPlugin initialized with NAME: {self.NAME}")
        self.pipulate = pipulate
        self._has_streamed = False
        
        # Register routes for serving individual documents
        for doc_key in self.DOCS.keys():
            app.route(f'/docs/{doc_key}', methods=['GET'])(self.serve_document)

    def markdown_to_html(self, markdown_content):
        """Convert markdown to HTML with basic formatting"""
        # This is a simple markdown converter - you could use a proper library like markdown or mistune
        html = markdown_content
        
        # Headers
        html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^#### (.*?)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        
        # Code blocks
        html = re.sub(r'```python\n(.*?)\n```', r'<pre><code class="language-python">\1</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'```bash\n(.*?)\n```', r'<pre><code class="language-bash">\1</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'```(.*?)\n(.*?)\n```', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)
        
        # Inline code
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
        
        # Bold and italic
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
        
        # Lists
        html = re.sub(r'^- (.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*?</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
        
        # Paragraphs
        lines = html.split('\n')
        in_code_block = False
        processed_lines = []
        
        for line in lines:
            if line.strip().startswith('<pre>'):
                in_code_block = True
            elif line.strip().startswith('</pre>'):
                in_code_block = False
            elif not in_code_block and line.strip() and not line.strip().startswith('<'):
                line = f'<p>{line}</p>'
            processed_lines.append(line)
        
        return '\n'.join(processed_lines)

    async def serve_document(self, request):
        """Serve individual documentation files"""
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
            
            # Create navigation links as HTML strings
            nav_links_html = []
            for key, info in self.DOCS.items():
                if key == doc_key:
                    nav_links_html.append(f'<span class="current-doc">{info["title"]}</span>')
                else:
                    nav_links_html.append(f'<a href="/docs/{key}" target="_blank">{info["title"]}</a>')
            
            # Create the full HTML page as a string
            page_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{doc_info['title']}</title>
    <meta charset="utf-8">
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6; 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px;
            background: #fafafa;
        }}
        .nav {{ 
            background: #fff; 
            padding: 15px; 
            margin-bottom: 20px; 
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .nav a {{ 
            margin-right: 20px; 
            color: #0066cc; 
            text-decoration: none;
        }}
        .nav a:hover {{ text-decoration: underline; }}
        .current-doc {{ 
            font-weight: bold; 
            color: #333; 
            margin-right: 20px;
        }}
        .content {{ 
            background: #fff; 
            padding: 30px; 
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        pre {{ 
            background: #f5f5f5; 
            padding: 15px; 
            border-radius: 4px; 
            overflow-x: auto;
            border-left: 4px solid #0066cc;
        }}
        code {{ 
            background: #f0f0f0; 
            padding: 2px 4px; 
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        }}
        h1, h2, h3, h4 {{ color: #333; }}
        h1 {{ border-bottom: 2px solid #0066cc; padding-bottom: 10px; }}
        h2 {{ border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
        blockquote {{ 
            border-left: 4px solid #ddd; 
            margin: 0; 
            padding-left: 20px; 
            color: #666;
        }}
        .alert {{ 
            background: #fff3cd; 
            border: 1px solid #ffeaa7; 
            padding: 15px; 
            border-radius: 4px; 
            margin: 15px 0;
        }}
    </style>
</head>
<body>
    <div class="nav">
        <h3>Pipulate Documentation</h3>
        {' '.join(nav_links_html)}
    </div>
    <div class="content">
        {html_content}
    </div>
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
                for key, info in self.DOCS.items():
                    docs_message += f"- {info['title']}: {info['description']}\n"
                
                self.pipulate.append_to_history(
                    f"[WIDGET CONTENT] Pipulate Documentation\n{docs_message}",
                    role="system",
                    quiet=True
                )

                self._has_streamed = True
                logger.debug("Documentation info appended to conversation history")
            except Exception as e:
                logger.error(f"Error in documentation plugin: {str(e)}")

        # Create documentation links
        doc_links = []
        for key, info in self.DOCS.items():
            doc_links.append(
                Li(
                    A(
                        info['title'],
                        href=f"/docs/{key}",
                        target="_blank",
                        style="text-decoration: none; color: var(--pico-primary);"
                    ),
                    P(info['description'], style="margin: 0.25rem 0 0.75rem 0; font-size: 0.9em; color: var(--pico-muted-color);")
                )
            )

        return Div(
            H2("📚 Documentation"),
            P("Essential guides for Pipulate development:"),
            Ul(*doc_links, style="list-style: none; padding: 0;"),
            id=unique_id
        ) 
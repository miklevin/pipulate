"""
Introduction Plugin - Extracted intro pages from original homepage

This plugin serves the 4-page introduction sequence that was originally
the homepage content before switching to the Roles app.
"""

from fasthtml.common import *
from pathlib import Path
import urllib.parse

class IntroductionPlugin:
    NAME = "introduction"
    DISPLAY_NAME = "Introduction 📖"
    ENDPOINT_MESSAGE = "📖 Introduction Guide: Learn about Pipulate's layout, features, and how to get started effectively. This comprehensive guide covers profiles, workflows, and the local LLM assistant."

    def __init__(self, app, pipulate, pipeline, db):
        self.app = app
        self.pipulate = pipulate
        self.pipeline = pipeline  
        self.db = db
        
        # Register routes
        app.route('/introduction', methods=['GET'])(self.serve_introduction)
        app.route('/introduction/page/{page_num}', methods=['GET'])(self.serve_page)

    def get_intro_page_content_html(self, page_num_str: str, app_name: str, model: str):
        """Returns HTML content for intro pages as raw HTML strings.
        Content is defined once and used for both UI display and LLM context.
        """
        page_num = int(page_num_str)
        
        pages = {
            1: {
                'title': f'Welcome to {app_name}',
                'intro': 'Layout:',
                'features': [
                    ('Breadcrumb Headline', f'Headline is {app_name} / Profile Name / APP Name.'),
                    ('PROFILE', 'Set up Client (aka Customer) profiles. Each is their own separate workspace.'),
                    ('APP', 'For each Client/Customer, try each APP (Parameter Buster for example).')
                ],
                'getting_started': 'Getting Started',
                'nav_help': f'Use DEV mode for practice. Use Prod mode in front of your Client or Customer.',
                'llm_help': f'The chat interface on the right is powered by a local LLM ({model}) to assist you. Click the "Next ▸" button to continue.'
            },
            2: {
                'experimenting_title': 'Positive First Experience',
                'experimenting_steps': [
                    'Start in DEV mode. Practice! Try stuff like resetting the entire database 🔄 (in 🤖). Experiment and get comfortable.',
                    'Add PROFILES. Rerrange them. Check and uncheck them. Changes are reflected instantly in the PROFILE menu.',
                    f'{app_name} is for running workflows. Try the Hello Workflow to get a feel for how they work.'
                ],
                'interface_title': 'Understanding the Interface',
                'interface_items': [
                    ('PROFILES', "Give Clients cute nicknames in Prod mode (Appliances, Sneakers, etc). Resetting database won't delete."),
                    ('APPS', "Try Parameter Buster on your Client. It's a big potential win.")
                ]
            },
            3: {
                'title': 'Tips for Effective Use',
                'tips': [
                    ('CONNECT', 'Set up your API keys to activate Botify-integrated workflows such as Parameter Buster.'),
                    ('DELETE', 'Workflows are disposable because they are so easily re-created. So if you lose a particular workflow, just make it again with the same inputs 🤯'),
                    ('SAVE', 'Anything you do that has side-effects like CSVs stays on your computer even when you delete the workflows. Browse direclty to files or attach new workflows to them by using the same input.'),
                    ('LOCK', 'Lock PROFILE to avoid showing other Client (Nick)names to each other.'),
                    ('BROWSE', 'Go look where things are saved.')
                ]
            },
            4: {
                'title': 'Local LLM Assistant',
                'llm_features': [
                    ('PRIVACY', 'All conversations stay on your machine. No data is sent to external servers.'),
                    ('CONTEXT', 'The LLM understands your current workflow and can help with specific tasks.'),
                    ('GUIDANCE', 'Ask questions about workflows, get help with API keys, or request explanations.'),
                    ('INTEGRATION', 'The LLM is aware of your current profile, environment, and active workflow.'),
                    ('REAL-TIME', 'Chat updates in real-time as you progress through workflows.')
                ],
                'usage_tips': [
                    'Try asking "What can I do with this workflow?" when starting a new one.',
                    'Ask for help with specific steps if you get stuck.',
                    'Request explanations of workflow outputs or data.',
                    'Get suggestions for next steps or alternative approaches.'
                ]
            }
        }
        
        page_data = pages.get(page_num)
        if not page_data:
            error_msg = f'Content for instruction page {page_num_str} not found.'
            content_html = f'<article style="min-height: 400px; display: flex; flex-direction: column; justify-content: flex-start;"><p>{error_msg}</p></article>'
            llm_context = f'The user is viewing an unknown page ({page_num_str}) which shows: {error_msg}'
            return (content_html, llm_context)
        
        card_style = 'min-height: 400px; display: flex; flex-direction: column; justify-content: flex-start; padding: 1rem; border: 1px solid var(--pico-muted-border-color); border-radius: 0.5rem;'
        
        if page_num == 1:
            features_html = ''.join([f'<li><strong>{name}:</strong> {desc}</li>' for name, desc in page_data['features']])
            content_html = f'''
            <article style="{card_style}">
                <h2>{page_data['title']}</h2>
                <h4>{page_data['intro']}</h4>
                <ol>{features_html}</ol>
                <h4>{page_data['getting_started']}</h4>
                <p>{page_data['nav_help']}</p>
                <p>{page_data['llm_help']}</p>
            </article>
            '''
            llm_context = f"The user is viewing the Introduction page which shows:\n\n{page_data['title']}\n\n{page_data['intro']}\n{chr(10).join((f'{i + 1}. {name}: {desc}' for i, (name, desc) in enumerate(page_data['features'])))}\n\n{page_data['getting_started']}\n{page_data['nav_help']}\n{page_data['llm_help']}"
            
        elif page_num == 2:
            steps_html = ''.join([f'<li>{step}</li>' for step in page_data['experimenting_steps']])
            items_html = ''.join([f'<li><strong>{name}:</strong> {desc}</li>' for name, desc in page_data['interface_items']])
            content_html = f'''
            <article style="{card_style}">
                <h3>{page_data['experimenting_title']}</h3>
                <ol>{steps_html}</ol>
                <h3>{page_data['interface_title']}</h3>
                <ul>{items_html}</ul>
            </article>
            '''
            llm_context = f"The user is viewing the Experimenting page which shows:\n\n{page_data['experimenting_title']}\n{chr(10).join((f'{i + 1}. {step}' for i, step in enumerate(page_data['experimenting_steps'])))}\n\n{page_data['interface_title']}\n{chr(10).join((f'• {name}: {desc}' for name, desc in page_data['interface_items']))}"
            
        elif page_num == 3:
            tips_html = ''.join([f'<li><strong>{name}:</strong> {desc}</li>' for name, desc in page_data['tips']])
            downloads_path = urllib.parse.quote(str(Path('downloads').absolute()))
            content_html = f'''
            <article style="{card_style}">
                <h3>{page_data['title']}</h3>
                <ol>{tips_html}</ol>
                <hr>
                <p>Try it now: <a href="/open-folder?path={downloads_path}">Open Downloads Folder</a></p>
            </article>
            '''
            llm_context = f"The user is viewing the Tips page which shows:\n\n{page_data['title']}\n{chr(10).join((f'{i + 1}. {name}: {desc}' for i, (name, desc) in enumerate(page_data['tips'])))}"
            
        elif page_num == 4:
            features_html = ''.join([f'<li><strong>{name}:</strong> {desc}</li>' for name, desc in page_data['llm_features']])
            tips_html = ''.join([f'<li>{tip}</li>' for tip in page_data['usage_tips']])
            content_html = f'''
            <article style="{card_style}">
                <h3>{page_data['title']}</h3>
                <p>Your local LLM ({model}) provides intelligent assistance throughout your workflow:</p>
                <ol>{features_html}</ol>
                <h4>How to Use the LLM</h4>
                <ul>{tips_html}</ul>
            </article>
            '''
            llm_context = f"The user is viewing the Local LLM Assistant page which shows:\n\n{page_data['title']}\n\nFeatures:\n{chr(10).join((f'{i + 1}. {name}: {desc}' for i, (name, desc) in enumerate(page_data['llm_features'])))}\n\nUsage Tips:\n{chr(10).join((f'• {tip}' for tip in page_data['usage_tips']))}"
        
        return (content_html, llm_context)

    async def serve_introduction(self, request):
        """Serve the main introduction page with navigation."""
        # Get app name and model from server settings
        from server import APP_NAME, MODEL
        
        # Default to page 1
        content_html, llm_context = self.get_intro_page_content_html("1", APP_NAME, MODEL)
        
        # Add LLM context
        await self.pipulate.stream(llm_context, verbatim=True)
        
        page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Introduction Guide - {APP_NAME}</title>
    <link rel="stylesheet" href="/static/pico.css">
    <link rel="stylesheet" href="/static/styles.css">
    <style>
        .container {{ max-width: 800px; margin: 0 auto; padding: 2rem; }}
        .nav-link {{ margin-right: 1rem; text-decoration: none; }}
        .nav-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📖 Introduction Guide</h1>
            <p>Learn about {APP_NAME}'s layout, features, and how to get started effectively.</p>
        </header>
        
        <nav style="margin-bottom: 2rem;">
            <a href="/introduction/page/1" class="nav-link">Page 1: Welcome</a>
            <a href="/introduction/page/2" class="nav-link">Page 2: Getting Started</a>
            <a href="/introduction/page/3" class="nav-link">Page 3: Tips</a>
            <a href="/introduction/page/4" class="nav-link">Page 4: LLM Assistant</a>
        </nav>
        
        <main>
            {content_html}
        </main>
        
        <footer style="margin-top: 3rem; text-align: center;">
            <p><a href="/">← Back to Main App</a></p>
        </footer>
    </div>
</body>
</html>"""
        
        return HTMLResponse(page_html)

    async def serve_page(self, request):
        """Serve a specific intro page."""
        page_num = request.path_params.get('page_num', '1')
        
        # Get app name and model from server settings  
        from server import APP_NAME, MODEL
        
        try:
            content_html, llm_context = self.get_intro_page_content_html(page_num, APP_NAME, MODEL)
            
            # Add LLM context
            await self.pipulate.stream(llm_context, verbatim=True)
            
            # Create navigation
            current_page = int(page_num)
            prev_page = current_page - 1 if current_page > 1 else None
            next_page = current_page + 1 if current_page < 4 else None
            
            prev_button = f'<a href="/introduction/page/{prev_page}" class="secondary">← Previous</a>' if prev_page else '<span></span>'
            next_button = f'<a href="/introduction/page/{next_page}" class="primary">Next →</a>' if next_page else '<span></span>'
            
            nav_buttons = f'''
            <div style="display: flex; justify-content: space-between; margin-bottom: 2rem;">
                {prev_button}
                {next_button}
            </div>
            '''
            
            page_navigation = ''
            for i in range(1, 5):
                weight_style = 'font-weight: bold;' if current_page == i else ''
                page_navigation += f'<a href="/introduction/page/{i}" style="{weight_style}">Page {i}</a>'
                if i < 4:
                    page_navigation += ' | '
            
            page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Introduction Guide - Page {page_num} - {APP_NAME}</title>
    <link rel="stylesheet" href="/static/pico.css">
    <link rel="stylesheet" href="/static/styles.css">
    <style>
        .container {{ max-width: 800px; margin: 0 auto; padding: 2rem; }}
        .secondary, .primary {{ 
            padding: 0.5rem 1rem; 
            text-decoration: none; 
            border-radius: 0.25rem; 
            display: inline-block;
        }}
        .secondary {{ 
            background-color: var(--pico-secondary-background); 
            color: var(--pico-secondary-color); 
        }}
        .primary {{ 
            background-color: var(--pico-primary-background); 
            color: var(--pico-primary-color); 
        }}
        .secondary:hover, .primary:hover {{ opacity: 0.8; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📖 Introduction Guide - Page {page_num}</h1>
            <nav style="margin-bottom: 1rem;">
                {page_navigation}
            </nav>
        </header>
        
        {nav_buttons}
        
        <main>
            {content_html}
        </main>
        
        {nav_buttons}
        
        <footer style="margin-top: 3rem; text-align: center;">
            <p><a href="/introduction">← Back to Introduction Overview</a> | <a href="/">← Back to Main App</a></p>
        </footer>
    </div>
</body>
</html>"""
            
            return HTMLResponse(page_html)
            
        except Exception as e:
            error_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Introduction Guide - Error</title>
    <link rel="stylesheet" href="/static/pico.css">
</head>
<body>
    <div class="container">
        <article>
            <h1>Error Loading Page</h1>
            <p>Error loading page {page_num}: {str(e)}</p>
            <p><a href="/introduction">← Back to Introduction Overview</a></p>
        </article>
    </div>
</body>
</html>"""
            return HTMLResponse(error_html, status_code=404)

    async def landing(self, render_items=None):
        """Landing page that redirects to the main introduction page."""
        return HTMLResponse('', status_code=302, headers={'Location': '/introduction'}) 
"""
Introduction Plugin - Extracted intro pages from original homepage

This plugin serves the 4-page introduction sequence that was originally
the homepage content before switching to the Roles app.
"""

import logging
from fasthtml.common import *
from pathlib import Path
import urllib.parse

ROLES = ['Tutorial']

logger = logging.getLogger(__name__)

class IntroductionPlugin:
    NAME = "introduction"
    DISPLAY_NAME = "Introduction 📖"
    ENDPOINT_MESSAGE = "📖 Introduction Guide: Learn about Pipulate's layout, features, and how to get started effectively. This comprehensive guide covers profiles, workflows, and the local LLM assistant."

    def __init__(self, app, pipulate, pipeline, db):
        logger.debug(f"IntroductionPlugin initialized with NAME: {self.NAME}")
        self.app = app
        self.pipulate = pipulate
        self.pipeline = pipeline  
        self.db = db
        self._has_streamed = False  # Flag to track if we've already streamed
        
        # Register routes for page navigation
        app.route('/introduction/page/{page_num}', methods=['GET', 'POST'])(self.serve_page)

    def get_intro_page_data(self, page_num: int, app_name: str, model: str):
        """Returns page data for intro pages."""
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
        return pages.get(page_num)

    def create_page_content(self, page_num: int, app_name: str, model: str):
        """Create FastHTML content for a specific page."""
        page_data = self.get_intro_page_data(page_num, app_name, model)
        
        if not page_data:
            return Card(
                H3("Page Not Found"),
                P(f"Introduction page {page_num} not found."),
                style="min-height: 300px;"
            )

        card_style = "min-height: 400px; margin-bottom: 2rem;"
        
        if page_num == 1:
            return Card(
                H2(page_data['title']),
                H4(page_data['intro']),
                Ol(*[Li(Strong(f'{name}:'), f' {desc}') for name, desc in page_data['features']]),
                H4(page_data['getting_started']),
                P(page_data['nav_help']),
                P(page_data['llm_help']),
                style=card_style
            )
            
        elif page_num == 2:
            return Card(
                H3(page_data['experimenting_title']),
                Ol(*[Li(step) for step in page_data['experimenting_steps']]),
                H3(page_data['interface_title']),
                Ul(*[Li(Strong(f'{name}:'), f' {desc}') for name, desc in page_data['interface_items']]),
                style=card_style
            )
            
        elif page_num == 3:
            return Card(
                H3(page_data['title']),
                Ol(*[Li(Strong(f'{name}:'), f' {desc}') for name, desc in page_data['tips']]),
                Hr(),
                P('Try it now: ', A('Open Downloads Folder', 
                                   href='/open-folder?path=' + urllib.parse.quote(str(Path('downloads').absolute())), 
                                   hx_get='/open-folder?path=' + urllib.parse.quote(str(Path('downloads').absolute())), 
                                   hx_swap='none')),
                style=card_style
            )
            
        elif page_num == 4:
            return Card(
                H3(page_data['title']),
                P(f'Your local LLM ({model}) provides intelligent assistance throughout your workflow:'),
                Ol(*[Li(Strong(f'{name}:'), f' {desc}') for name, desc in page_data['llm_features']]),
                H4('How to Use the LLM'),
                Ul(*[Li(tip) for tip in page_data['usage_tips']]),
                style=card_style
            )

    def create_llm_context(self, page_num: int, app_name: str, model: str):
        """Create LLM context for a specific page."""
        page_data = self.get_intro_page_data(page_num, app_name, model)
        
        if not page_data:
            return f'The user is viewing an unknown introduction page ({page_num}).'

        if page_num == 1:
            return f"The user is viewing the Introduction page which shows:\n\n{page_data['title']}\n\n{page_data['intro']}\n{chr(10).join((f'{i + 1}. {name}: {desc}' for i, (name, desc) in enumerate(page_data['features'])))}\n\n{page_data['getting_started']}\n{page_data['nav_help']}\n{page_data['llm_help']}"
        elif page_num == 2:
            return f"The user is viewing the Experimenting page which shows:\n\n{page_data['experimenting_title']}\n{chr(10).join((f'{i + 1}. {step}' for i, step in enumerate(page_data['experimenting_steps'])))}\n\n{page_data['interface_title']}\n{chr(10).join((f'• {name}: {desc}' for name, desc in page_data['interface_items']))}"
        elif page_num == 3:
            return f"The user is viewing the Tips page which shows:\n\n{page_data['title']}\n{chr(10).join((f'{i + 1}. {name}: {desc}' for i, (name, desc) in enumerate(page_data['tips'])))}"
        elif page_num == 4:
            return f"The user is viewing the Local LLM Assistant page which shows:\n\n{page_data['title']}\n\nFeatures:\n{chr(10).join((f'{i + 1}. {name}: {desc}' for i, (name, desc) in enumerate(page_data['llm_features'])))}\n\nUsage Tips:\n{chr(10).join((f'• {tip}' for tip in page_data['usage_tips']))}"

    async def serve_page(self, request):
        """Handle page navigation within the main app framework."""
        page_num = int(request.path_params.get('page_num', '1'))
        
        # Get app name and model from server settings
        from server import APP_NAME, MODEL
        
        # Store current page in database
        self.db['intro_current_page'] = str(page_num)
        
        # Create LLM context and add silently to conversation history
        llm_context = self.create_llm_context(page_num, APP_NAME, MODEL)
        if self.pipulate:
            self.pipulate.append_to_history(llm_context, role='system')
        
        # Return the updated content directly (same as landing method)
        return await self.landing()

    async def landing(self, render_items=None):
        """Always appears in create_grid_left."""
        # Get app name and model from server settings
        from server import APP_NAME, MODEL
        
        # Get current page from database, default to 1
        current_page = int(self.db.get('intro_current_page', '1'))
        
        # Send the intro message to conversation history, but only once per session
        if self.pipulate is not None and not self._has_streamed:
            try:
                # Add the endpoint message silently to conversation history
                self.pipulate.append_to_history(self.ENDPOINT_MESSAGE, role="system")

                # Then append the current page info to history
                llm_context = self.create_llm_context(current_page, APP_NAME, MODEL)
                self.pipulate.append_to_history(
                    f"[WIDGET CONTENT] Introduction Guide - Page {current_page}\n{llm_context}",
                    role="system"
                )

                self._has_streamed = True  # Set flag to prevent repeated streaming
                logger.debug("Introduction content appended to conversation history")
            except Exception as e:
                logger.error(f"Error in introduction plugin: {str(e)}")

        # Create page navigation
        nav_buttons = Div(
            *[
                A(f"Page {i}", 
                  href=f'/introduction/page/{i}',
                  cls="secondary outline" if i != current_page else "primary",
                  style="margin-right: 0.5rem; margin-bottom: 0.5rem; display: inline-block;"
                ) for i in range(1, 5)
            ],
            style="margin-bottom: 1rem;"
        )

        # Create navigation arrows (matching original server.py style)
        prev_button = Button(
            '◂ Previous', 
            hx_post=f'/introduction/page/{current_page - 1}' if current_page > 1 else '#',
            hx_target='#grid-left-content',
            hx_swap='innerHTML',
            cls='primary outline' if current_page == 1 else 'primary',
            style='min-width: 160px; width: 160px;',
            disabled=current_page == 1
        )
        
        next_button = Button(
            'Next ▸', 
            hx_post=f'/introduction/page/{current_page + 1}' if current_page < 4 else '#',
            hx_target='#grid-left-content',
            hx_swap='innerHTML',
            cls='primary outline' if current_page == 4 else 'primary',
            style='min-width: 160px; width: 160px;',
            disabled=current_page == 4
        )
        
        nav_arrows = Div(
            prev_button,
            next_button,
            style='display: flex; gap: 1rem; justify-content: center; margin-top: 1rem;'
        )

        # Create the current page content
        page_content = self.create_page_content(current_page, APP_NAME, MODEL)

        return Div(
            H2(f"📖 Introduction Guide - Page {current_page}"),
            nav_buttons,
            page_content,
            nav_arrows
        ) 
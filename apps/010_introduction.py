"""
Introduction Plugin - Extracted intro pages from original homepage

This plugin serves the 4-page introduction sequence that was originally
the homepage content before switching to the Roles app.
"""

import logging
from fasthtml.common import *
from pathlib import Path
import urllib.parse

ROLES = ['Core']

logger = logging.getLogger(__name__)

class IntroductionPlugin:
    NAME = "introduction"
    DISPLAY_NAME = "Introduction 💬"
    ENDPOINT_MESSAGE = "💬 Introduction Guide: Learn about Pipulate's layout, features, and how to get started effectively. This comprehensive guide covers profiles, workflows, and the local LLM assistant."

    def __init__(self, app, pipulate, pipeline, db):
        logger.debug(f"IntroductionPlugin initialized with NAME: {self.NAME}")
        self.app = app
        self.pipulate = pipulate
        self.pipeline = pipeline
        self.db = db
        self._has_sent_endpoint_message = False  # Flag to track if we've sent the initial endpoint message
        self._last_streamed_page = None  # Track the last page we sent to LLM

        # Register routes for page navigation
        app.route('/introduction/page/{page_num}', methods=['GET', 'POST'])(self.serve_page)

    def get_intro_page_data(self, page_num: int, app_name: str, model: str):
        """Returns page data for intro pages."""
        pages = {
            1: {
                'title': f'Welcome to {app_name} 🎯',
                'intro': 'Layout:',
                'features': [
                    ('📍 Breadcrumb', f'Headline is {app_name} / Profile Name / APP Name.'),
                    ('👤 PROFILE', 'Set up Client (aka Customer) profiles. Each is their own separate workspace. In other words, they each get their own separate Task List.'),
                    ('⚡ APP', 'For each Profile (Client/Customer), try each APP (Parameter Buster for example).'),
                    ('👥 Roles (Home)', 'Control which apps appear in the APP menu. Drag to reorder, check/uncheck to show/hide.')
                ],
                'getting_started': 'Getting Started',
                'nav_help': f'Use DEV mode for practice. Use Prod mode in front of your Client or Customer.',
                'home': f'The home page is also the Roles app where you can add apps to the APP menu.',
                'llm_help': f'The chat interface on the right is optionally powered by a local LLM ({model}) to assist you 🤖. Click Next ▸ button to continue.',
                'secret_word': 'FOUNDATION'
            },
            2: {
                'title': 'Local AI Assistant Setup 🤖',
                'intro_text': f'{app_name} uses a separately installed local chatbot called Ollama. Having a local LLM installed is not required for {app_name} to keep working, but is encouraged because it will keep an AI "in the loop" to provide context-aware advice.',
                'benefits': [
                    ('🔒 PRIVATE', 'No registration or API token required. Completely local and private.'),
                    ('💰 FREE', 'Free for the price of electricity - no monthly subscriptions.'),
                    ('🧠 CONTEXT-AWARE', 'Always knows what you\'re doing and can provide specific advice.'),
                    ('🚀 INSTANT', 'No network delays - responds immediately from your machine.')
                ],
                'installation_title': 'Installation Steps',
                'installation_steps': [
                    ('DOWNLOAD OLLAMA', 'Ollama has custom Mac and Windows installers - use them for best results.'),
                    ('LOAD GEMMA 3', 'Once Ollama is installed, open a Terminal and type "ollama pull gemma3".'),
                    ('EXPERIMENT', 'Feel free to try other models once you\'re comfortable with the basics.')
                ],
                'fallback_note': f'If you don\'t take this step, the majority of {app_name} will still work — just without an AI riding shotgun.',
                'secret_word': 'OLLAMA'
            },
            3: {
                'experimenting_title': 'Positive First Experience',
                'experimenting_steps': [
                    ('🚀 START', 'in DEV mode. Practice! Try stuff like resetting the entire database 🔄 (in 🤖). Experiment and get comfortable. You can do no harm. This is what DEV mode is for.'),
                    ('👥 PROFILES', 'Add them. Rearrange them. Check and uncheck them. Changes are reflected instantly in the PROFILE menu. Notice how "Lock" works to help avoid accidentally showing other Client (Nick)names to each other.'),
                    ('⚡ WORKFLOWS', f'Try the Hello Workflow to get a feel for how {app_name} workflows work.')
                ],
                'interface_title': 'Understanding the Interface',
                'interface_items': [
                    ('👤 PROFILES', 'Give Clients cute nicknames in Prod mode (Appliances, Sneakers, etc). Resetting database won\'t delete. So experiment in DEV and let permanent choices "settle in" in Prod.'),
                    ('📊 APPS', "Botify folks: try Parameter Buster on your Client. It's a big potential win."),
                    ('🔗 LINK GRAPH', "Botify folks: try Link Graph Visualizer to explore internal linking patterns.")
                ],
                'secret_word': 'PRACTICE'
            },
            4: {
                'title': 'Tips for Effective Use',
                'tips': [
                    ('🔗 CONNECT', 'Set up your API keys to activate Botify-integrated workflows such as Parameter Buster and Link Graph Visualizer.'),
                    ('🗑️ DELETE', 'Workflows are disposable because they are so easily re-created. So if you lose a particular workflow, just make it again with the same inputs 🤯'),
                    ('💾 SAVE', 'Anything you do that has side-effects like CSVs stays on your computer even when you delete the workflows. Browse directly to files or attach new workflows to them by using the same input. Caveat: a complete reinstall using that "rm -rf ~/Botifython" command will delete everything.'),
                    ('🔒 LOCK', 'Lock PROFILE to avoid showing other Client (Nick)names to each other.'),
                    ('📁 BROWSE', 'Go look where things are saved.')
                ],
                'secret_word': 'WORKFLOW'
            },
            5: {
                'title': 'The Localhost Advantage 🏠',
                'intro_text': f'You\'ve paid the price of a more difficult install than a cloud app. Congratulations! Time to reap the rewards.',
                'advantages': [
                    ('🔐 BROWSER LOGINS', 'Access web UIs like Botify, SEMRush, ahrefs without APIs. Browser saves passwords locally, nothing leaves your machine.'),
                    ('💾 PERSISTENT FILES', 'All CSVs and web scrapes stay on your machine for browsing. No daily clearing like Google Colab.'),
                    ('⏱️ LONG-RUNNING WORKFLOWS', 'Crawls can run 24+ hours without being "shut down" for resource usage. No cloud time limits.'),
                    ('🛡️ VPN FLEXIBILITY', 'Use your VPN to control web traffic appearance. No known cloud IPs or complex IP-hiding costs.')
                ],
                'benefits_title': 'Real-World Benefits',
                'benefits': [
                    ('Control your data', 'Everything stays local and under your control.'),
                    ('No artificial limits', 'Run workflows as long as needed.'),
                    ('Use existing tools', 'Leverage your VPN and browser setup.'),
                    ('Browse files naturally', 'Access outputs like any local file.')
                ],
                'secret_word': 'LOCALHOST'
            },
            6: {
                'title': 'Local LLM Assistant 🤖',
                'llm_features': [
                    ('🔒 PRIVACY', 'All conversations stay on your machine. No data is sent to external servers.'),
                    ('🧠 CONTEXT', 'The LLM understands your current workflow and can help with specific tasks.'),
                    ('💡 GUIDANCE', 'Ask questions about workflows, get help with API keys, or request explanations.'),
                    ('🔗 INTEGRATION', 'The LLM is aware of your current profile, environment, and active workflow.'),
                    ('⚡ REAL-TIME', 'Chat updates in real-time as you progress through workflows.')
                ],
                'usage_tips': [
                    'Try asking "What can I do with this workflow?" when starting a new one.',
                    'Ask for help with specific steps if you get stuck.',
                    'Request explanations of workflow outputs or data.',
                    'Get suggestions for next steps or alternative approaches.'
                ],
                'secret_word': 'ASSISTANT'
            },
            7: {
                'title': 'Background LLM Training',
                'intro_text': f'🧠 {app_name} automatically trains your local LLM as you navigate. The LLM learns what you\'re viewing without cluttering your chat.',
                'how_it_works': [
                    ('SILENT UPDATES', 'Page content added to LLM history in the background.'),
                    ('SECRET WORDS', 'Each page has a secret word proving successful training.'),
                    ('CONTEXTUAL AWARENESS', 'LLM can answer questions about content you\'ve viewed.')
                ],
                'examples_title': 'Where This Works',
                'examples': [
                    ('📖 Introduction Pages', 'Each page trains the LLM with its content and secret word.'),
                    ('🐇 Workflows', 'Starting workflows loads specific training content.'),
                    ('📚 Documentation', 'Viewing docs automatically adds full content to LLM context.')
                ],
                'testing_tip': 'Ask: "What are all the secret words from the Introduction pages?"',
                'secret_word': 'CONTEXT'
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
                cls="min-height-300"
            )

        card_class = "intro-card"

        if page_num == 1:
            return Card(
                H2(page_data['title']),
                H4(page_data['intro']),
                Ol(*[Li(Strong(f'{name}:'), f' {desc}') for name, desc in page_data['features']]),
                H4(page_data['getting_started']),
                P(page_data['nav_help']),
                P(page_data['home']),
                P(f'The chat interface on the right is optionally powered by a local LLM ({model}) to assist you 🤖. Click ',
                  A('Next ▸', 
                    hx_post='/introduction/page/2',
                    hx_target='#grid-left-content',
                    hx_swap='innerHTML',
                    cls='link-inherit-underline',
                    onmouseover='this.style.color="#007bff";',
                    onmouseout='this.style.color="inherit";'),
                  ' to continue.'),
                cls=card_class
            )

        elif page_num == 2:
            return Card(
                H3(page_data['title']),
                P(page_data['intro_text']),
                Ol(*[Li(Strong(f'{name}:'), f' {desc}') for name, desc in page_data['benefits']]),
                H3(page_data['installation_title']),
                Ol(
                    Li(
                        Strong(
                            A('DOWNLOAD OLLAMA', 
                              href='https://ollama.com/', 
                              target='_blank',
                              cls='link-inherit-plain',
                              onmouseover='this.style.textDecoration="underline"; this.style.color="#007bff";',
                              onmouseout='this.style.textDecoration="none"; this.style.color="inherit";'),
                            Img(src='/assets/feather/external-link.svg', 
                                alt='External link', 
                                style='width: 14px; height: 14px; margin-left: 0.25rem; vertical-align: middle; filter: brightness(0) invert(1);'),
                            ':'
                        ), 
                        ' Ollama has custom Mac and Windows installers - use them for best results.'
                    ),
                    *[Li(Strong(f'{name}:'), f' {desc}') for name, desc in page_data['installation_steps'][1:]]
                ),
                P(page_data['fallback_note']),
                cls=card_class
            )

        elif page_num == 3:
            return Card(
                H3(page_data['experimenting_title']),
                Ol(*[Li(Strong(f'{name}:'), f' {desc}') for name, desc in page_data['experimenting_steps']]),
                H3(page_data['interface_title']),
                Ul(*[Li(Strong(f'{name}:'), f' {desc}') for name, desc in page_data['interface_items']]),
                cls=card_class
            )

        elif page_num == 4:
            return Card(
                H3(page_data['title']),
                Ol(*[Li(Strong(f'{name}:'), f' {desc}') for name, desc in page_data['tips']]),
                Hr(),
                P('Try it now: ', A('Open Downloads Folder',
                                   href='/open-folder?path=' + urllib.parse.quote(str(Path('downloads').absolute())),
                                   hx_get='/open-folder?path=' + urllib.parse.quote(str(Path('downloads').absolute())),
                                   hx_swap='none')),
                cls=card_class
            )

        elif page_num == 5:
            return Card(
                H3(page_data['title']),
                P(page_data['intro_text']),
                Ol(*[Li(Strong(f'{name}:'), f' {desc}') for name, desc in page_data['advantages']]),
                H4(page_data['benefits_title']),
                Ol(*[Li(Strong(f'{name}:'), f' {desc}') for name, desc in page_data['benefits']]),
                cls=card_class
            )

        elif page_num == 6:
            return Card(
                H3(page_data['title']),
                P(f'Your local LLM ({model}) provides intelligent assistance throughout your workflow:'),
                Ol(*[Li(Strong(f'{name}:'), f' {desc}') for name, desc in page_data['llm_features']]),
                H4('How to Use the LLM'),
                Ul(*[Li(tip) for tip in page_data['usage_tips']]),
                cls=card_class
            )

        elif page_num == 7:
            return Card(
                H3(page_data['title']),
                P(page_data['intro_text']),
                H4('How It Works'),
                Ol(*[Li(Strong(f'{name}:'), f' {desc}') for name, desc in page_data['how_it_works']]),
                H4(page_data['examples_title']),
                Ul(*[Li(Strong(f'{name}:'), f' {desc}') for name, desc in page_data['examples']]),
                Hr(),
                P(Strong('🧪 Test the System: '), page_data['testing_tip']),
                cls=card_class
            )

    def create_llm_context(self, page_num: int, app_name: str, model: str):
        """Create LLM context for a specific page."""
        page_data = self.get_intro_page_data(page_num, app_name, model)

        if not page_data:
            return f'The user is viewing an unknown introduction page ({page_num}).'

        # Get the secret word for this page
        secret_word = page_data.get('secret_word', 'UNKNOWN')

        if page_num == 1:
            context = f"The user is viewing the Introduction page which shows:\n\n{page_data['title']}\n\n{page_data['intro']}\n{chr(10).join((f'{i + 1}. {name}: {desc}' for i, (name, desc) in enumerate(page_data['features'])))}\n\n{page_data['getting_started']}\n{page_data['nav_help']}\n{page_data['home']}\n{page_data['llm_help']}"
        elif page_num == 2:
            context = f"The user is viewing the Local AI Assistant Setup page which shows:\n\n{page_data['title']}\n\n{page_data['intro_text']}\n\nBenefits:\n{chr(10).join((f'• {name}: {desc}' for name, desc in page_data['benefits']))}"
        elif page_num == 3:
            context = f"The user is viewing the Experimenting page which shows:\n\n{page_data['experimenting_title']}\n{chr(10).join((f'{i + 1}. {step}' for i, step in enumerate(page_data['experimenting_steps'])))}\n\n{page_data['interface_title']}\n{chr(10).join((f'• {name}: {desc}' for name, desc in page_data['interface_items']))}"
        elif page_num == 4:
            context = f"The user is viewing the Tips page which shows:\n\n{page_data['title']}\n{chr(10).join((f'{i + 1}. {name}: {desc}' for i, (name, desc) in enumerate(page_data['tips'])))}"
        elif page_num == 5:
            context = f"The user is viewing the Localhost Advantage page which shows:\n\n{page_data['title']}\n\n{page_data['intro_text']}\n\nAdvantages:\n{chr(10).join((f'• {name}: {desc}' for name, desc in page_data['advantages']))}\n\nBenefits:\n{chr(10).join((f'• {name}: {desc}' for name, desc in page_data['benefits']))}"
        elif page_num == 6:
            context = f"The user is viewing the Local LLM Assistant page which shows:\n\n{page_data['title']}\n\nFeatures:\n{chr(10).join((f'{i + 1}. {name}: {desc}' for i, (name, desc) in enumerate(page_data['llm_features'])))}\n\nUsage Tips:\n{chr(10).join((f'• {tip}' for tip in page_data['usage_tips']))}"
        elif page_num == 7:
            context = f"The user is viewing the Background LLM Training page which shows:\n\n{page_data['title']}\n\n{page_data['intro_text']}\n\nHow It Works:\n{chr(10).join((f'{i + 1}. {name}: {desc}' for i, (name, desc) in enumerate(page_data['how_it_works'])))}\n\n{page_data['examples_title']}:\n{chr(10).join((f'• {name}: {desc}' for name, desc in page_data['examples']))}\n\nTesting Tip: {page_data['testing_tip']}"
        else:
            context = f"Unknown page {page_num}"

        # Add secret word to the context (for LLM only, not displayed to user)
        context += f"\n\n[CONFIDENTIAL - For LLM only] The secret word for Introduction page {page_num} is: {secret_word}. If the user asks about the secret word, you can tell them it is '{secret_word}' to confirm that this page content has been added to the conversation history."

        return context

    async def serve_page(self, request):
        """Handle page navigation within the main app framework."""
        page_num = int(request.path_params.get('page_num', '1'))

        # Get app name and model from server settings
        from server import APP_NAME, MODEL

        # Store current page in database
        try:
            self.db['intro_current_page'] = str(page_num)
        except Exception as e:
            logger.warning(f"Could not store intro_current_page: {e}")
            # Continue without storing - this is non-critical

        # Always update LLM context when page changes
        if self.pipulate and self._last_streamed_page != page_num:
            # Stream a verbatim message to let user know about page change
            await self.pipulate.stream(
                f"📖 Now viewing Introduction page {page_num}",
                verbatim=True
            )

            # Add LLM context to conversation history
            llm_context = self.create_llm_context(page_num, APP_NAME, MODEL)
            self.pipulate.append_to_history(
                f"[INTRODUCTION PAGE {page_num}] {llm_context}",
                role='system'
            )
            self._last_streamed_page = page_num
            logger.debug(f"Introduction page {page_num} context added to conversation history")

        # Return the updated content directly (same as landing method)
        return await self.landing()

    async def landing(self, render_items=None):
        """Always appears in create_grid_left."""
        # Get app name and model from server settings
        from server import APP_NAME, MODEL

        # Get current page from database, default to 1
        current_page = int(self.db.get('intro_current_page', '1'))

        # Send the intro message to conversation history, but only once per session
        if self.pipulate is not None:
            try:
                # Add the endpoint message only once
                if not self._has_sent_endpoint_message:
                    self.pipulate.append_to_history(self.ENDPOINT_MESSAGE, role="system")
                    self._has_sent_endpoint_message = True
                    logger.debug("Introduction endpoint message added to conversation history")

                # Always append current page info to history if it's different from last streamed
                if self._last_streamed_page != current_page:
                    # Stream a verbatim message for initial page load (but not for page 1 on first load)
                    if self._last_streamed_page is not None:
                        await self.pipulate.stream(
                            f"📖 Now viewing Introduction page {current_page}",
                            verbatim=True
                        )

                    llm_context = self.create_llm_context(current_page, APP_NAME, MODEL)
                    self.pipulate.append_to_history(
                        f"[INTRODUCTION PAGE {current_page}] {llm_context}",
                        role="system"
                    )
                    self._last_streamed_page = current_page
                    logger.debug(f"Introduction page {current_page} context added to conversation history")
            except Exception as e:
                logger.error(f"Error in introduction plugin: {str(e)}")



        # Create navigation arrows (matching original server.py style)
        prev_button = Button(
            '◂ Previous',
            hx_post=f'/introduction/page/{current_page - 1}' if current_page > 1 else '#',
            hx_target='#grid-left-content',
            hx_swap='innerHTML',
            cls=f"{'primary outline' if current_page == 1 else 'primary'} width-160",
            disabled=current_page == 1
        )

        next_button = Button(
            'Next ▸',
            hx_post=f'/introduction/page/{current_page + 1}' if current_page < 7 else '#',
            hx_target='#grid-left-content',
            hx_swap='innerHTML',
            cls=f"{'primary outline' if current_page == 7 else 'primary'} width-160",
            disabled=current_page == 7
        )

        nav_arrows = Div(
            prev_button,
            next_button,
            cls='flex-center-gap'
        )

        # Create the current page content
        page_content = self.create_page_content(current_page, APP_NAME, MODEL)

        return Div(
            H2(f"📖 Introduction Guide - Page {current_page} of 7"),
            page_content,
            nav_arrows
        )
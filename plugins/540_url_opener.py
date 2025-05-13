import asyncio
from collections import namedtuple
from datetime import datetime
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from fasthtml.common import * # type: ignore
from loguru import logger
from starlette.responses import HTMLResponse

"""
Pipulate Workflow Template
A minimal starter template for creating step-based Pipulate workflows.
"""

# Model for a workflow step
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class BlankWorkflow:
    """
    Blank Workflow Template
    
    A minimal starting point for creating new workflows.
    """
    # --- Workflow Configuration ---
    APP_NAME = "open_url"          # Must differ from filename to avoid navigation collisions
    DISPLAY_NAME = "URL Opener"     # User-friendly name shown in the UI
    ENDPOINT_MESSAGE = (            # Message shown on the workflow's landing page
        "Open any URL in your default browser using your existing profile and settings. "
        "Perfect for accessing pages that require login."
    )
    TRAINING_PROMPT = (
        "This workflow helps users open URLs in their default browser. "
        "It uses the widget_container pattern for consistent UI and provides "
        "a simple interface for URL input and Google search functionality."
    )
    PRESERVE_REFILL = True          # Whether to keep input values when reverting

    # --- Initialization ---
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

        # Define workflow steps
        steps = [
            Step(
                id='step_01',
                done='url',
                show='Enter URL',
                refill=True,  # Allow URL reuse
            ),
            Step(
                id='step_02',
                done='query',
                show='Google Search',
                refill=True,  # Allow query reuse
            ),
            Step(
                id='step_03',
                done='selenium_url',
                show='Selenium URL',
                refill=True,  # Allow URL reuse
            ),
        ]
        
        # Register standard workflow routes
        routes = [
            (f"/{app_name}", self.landing),
            (f"/{app_name}/init", self.init, ["POST"]),
            (f"/{app_name}/jump_to_step", self.jump_to_step, ["POST"]),
            (f"/{app_name}/revert", self.handle_revert, ["POST"]),
            (f"/{app_name}/finalize", self.finalize, ["GET", "POST"]),
            (f"/{app_name}/unfinalize", self.unfinalize, ["POST"]),
            (f"/{app_name}/reopen_url", self.reopen_url, ["POST"]),  # New route for reopening URLs
        ]

        # Register routes for each step
        self.steps = steps
        for step in steps:
            step_id = step.id
            routes.append((f"/{app_name}/{step_id}", getattr(self, step_id)))
            routes.append((f"/{app_name}/{step_id}_submit", getattr(self, f"{step_id}_submit"), ["POST"]))

        # Register all routes with the FastHTML app
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ["GET"]
            app.route(path, methods=method_list)(handler)

        # Define UI messages
        self.step_messages = {
            "finalize": {
                "ready": "All steps complete. Ready to finalize workflow.",
                "complete": f"Workflow finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes."
            }
        }

        # Create default messages for each step
        for step in steps:
            self.step_messages[step.id] = {
                "input": f"{pip.fmt(step.id)}: Please complete {step.show}.",
                "complete": f"{step.show} complete. Continue to next step."
            }

        # Add the finalize step internally
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

    # --- Core Workflow Engine Methods ---

    async def landing(self):
        """Renders the initial landing page with the key input form."""
        pip, pipeline, steps, app_name = self.pipulate, self.pipeline, self.steps, self.app_name
        title = f"{self.DISPLAY_NAME or app_name.title()}"
        full_key, prefix, user_part = pip.generate_pipeline_key(self)
        default_value = full_key
        pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in pipeline() if record.pkey.startswith(prefix)]
        datalist_options = [f"{prefix}{record_key.replace(prefix, '')}" for record_key in matching_records]

        return Container(
            Card(
                H2(title),
                P(self.ENDPOINT_MESSAGE, style="font-size: 0.9em; color: #666;"),
                Form(
                    pip.wrap_with_inline_button(
                        Input(
                            placeholder="Existing or new 🗝 here (Enter for auto)", name="pipeline_id",
                            list="pipeline-ids", type="search", required=False, autofocus=True,
                            value=default_value, _onfocus="this.setSelectionRange(this.value.length, this.value.length)",
                            cls="contrast"
                        ),
                        button_label=f"Enter 🔑", button_class="secondary"
                    ),
                    pip.update_datalist("pipeline-ids", options=datalist_options if datalist_options else None),
                    hx_post=f"/{app_name}/init", hx_target=f"#{app_name}-container"
                )
            ),
            Div(id=f"{app_name}-container")
        )

    async def init(self, request):
        """Handles the key submission, initializes state, and renders the step UI placeholders."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        user_input = form.get("pipeline_id", "").strip()

        if not user_input:
            from starlette.responses import Response
            response = Response("")
            response.headers["HX-Refresh"] = "true"
            return response

        context = pip.get_plugin_context(self)
        profile_name = context['profile_name'] or "default"
        plugin_name = context['plugin_name'] or app_name
        profile_part = profile_name.replace(" ", "_")
        plugin_part = plugin_name.replace(" ", "_")
        expected_prefix = f"{profile_part}-{plugin_part}-"

        if user_input.startswith(expected_prefix):
            pipeline_id = user_input
        else:
            _, prefix, user_provided_id = pip.generate_pipeline_key(self, user_input)
            pipeline_id = f"{prefix}{user_provided_id}"

        db["pipeline_id"] = pipeline_id

        state, error = pip.initialize_if_missing(pipeline_id, {"app_name": app_name})
        if error: return error

        await self.message_queue.add(pip, f"Workflow ID: {pipeline_id}", verbatim=True, spaces_before=0)
        await self.message_queue.add(pip, f"Return later by selecting '{pipeline_id}' from the dropdown.", verbatim=True, spaces_before=0)
        
        # Build UI starting with first step
        return Div(
            Div(id="step_01", hx_get=f"/{app_name}/step_01", hx_trigger="load"),
            id=f"{app_name}-container"
        )

    async def finalize(self, request):
        """Handles GET request to show Finalize button and POST request to lock the workflow."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        finalize_step = steps[-1]
        finalize_data = pip.get_step_data(pipeline_id, finalize_step.id, {})

        if request.method == "GET":
            if finalize_step.done in finalize_data:
                return Card(
                    H3("Workflow is locked."),
                    Form(
                        Button(pip.UNLOCK_BUTTON_LABEL, type="submit", cls="secondary outline"),
                        hx_post=f"/{app_name}/unfinalize", 
                        hx_target=f"#{app_name}-container"
                    ),
                    id=finalize_step.id
                )
            else:
                all_steps_complete = all(
                    pip.get_step_data(pipeline_id, step.id, {}).get(step.done) 
                    for step in steps[:-1]
                )
                if all_steps_complete:
                    return Card(
                        H3("All steps complete. Finalize?"),
                        P("You can revert to any step and make changes.", style="font-size: 0.9em; color: #666;"),
                        Form(
                            Button("Finalize 🔒", type="submit", cls="primary"),
                            hx_post=f"/{app_name}/finalize", 
                            hx_target=f"#{app_name}-container"
                        ),
                        id=finalize_step.id
                    )
                else:
                    return Div(id=finalize_step.id)
        else:
            await pip.finalize_workflow(pipeline_id)
            await self.message_queue.add(pip, self.step_messages["finalize"]["complete"], verbatim=True)
            return pip.rebuild(app_name, steps)

    async def unfinalize(self, request):
        """Handles POST request to unlock the workflow."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, "Workflow unfinalized! You can now revert to any step and make changes.", verbatim=True)
        return pip.rebuild(app_name, steps)

    async def jump_to_step(self, request):
        """Handles POST request from breadcrumb navigation to jump to a specific step."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        db["step_id"] = step_id
        return pip.rebuild(app_name, steps)

    async def get_suggestion(self, step_id, state):
        """Gets a suggested input value for a step, often using the previous step's transformed output."""
        pip, db, steps = self.pipulate, self.db, self.steps
        step = next((s for s in steps if s.id == step_id), None)
        if not step or not step.transform: return ""
        prev_index = self.steps_indices[step_id] - 1
        if prev_index < 0: return ""
        prev_step = steps[prev_index]
        prev_data = pip.get_step_data(db["pipeline_id"], prev_step.id, {})
        prev_value = prev_data.get(prev_step.done, "")
        return step.transform(prev_value) if prev_value else ""

    async def handle_revert(self, request):
        """Handles POST request to revert to a previous step, clearing subsequent step data."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        pipeline_id = db.get("pipeline_id", "unknown")
        if not step_id: return P("Error: No step specified", style=self.pipulate.get_style("error"))

        await pip.clear_steps_from(pipeline_id, step_id, steps)
        state = pip.read_state(pipeline_id)
        state["_revert_target"] = step_id
        pip.write_state(pipeline_id, state)

        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        return pip.rebuild(app_name, steps)

    async def reopen_url(self, request):
        """Handle reopening a URL with Selenium."""
        pip, db = self.pipulate, self.db
        form = await request.form()
        url = form.get("url", "").strip()
        
        if not url:
            return P("Error: URL is required", style=pip.get_style("error"))
        
        try:
            # Set up Chrome options
            chrome_options = Options()
            # chrome_options.add_argument("--headless")  # Commented out for visibility
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--new-window")  # Force new window
            chrome_options.add_argument("--start-maximized")  # Start maximized
            
            # Create a temporary profile directory
            import tempfile
            profile_dir = tempfile.mkdtemp()
            chrome_options.add_argument(f"--user-data-dir={profile_dir}")
            
            # Initialize the Chrome driver
            effective_os = os.environ.get("EFFECTIVE_OS", "unknown")
            await self.message_queue.add(pip, f"Current OS: {effective_os}", verbatim=True)
            
            if effective_os == "darwin":
                await self.message_queue.add(pip, "Using webdriver-manager for macOS", verbatim=True)
                service = Service(ChromeDriverManager().install())
            else:
                await self.message_queue.add(pip, "Using system Chrome for Linux", verbatim=True)
                service = Service()
            
            await self.message_queue.add(pip, "Initializing Chrome driver...", verbatim=True)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Open the URL
            await self.message_queue.add(pip, f"Reopening URL with Selenium: {url}", verbatim=True)
            driver.get(url)
            
            # Wait a moment to ensure the page loads
            await asyncio.sleep(2)
            
            # Get the page title to confirm it loaded
            title = driver.title
            await self.message_queue.add(pip, f"Page loaded successfully. Title: {title}", verbatim=True)
            
            # Close the browser
            driver.quit()
            await self.message_queue.add(pip, "Browser closed successfully", verbatim=True)
            
            # Clean up the temporary profile directory
            import shutil
            shutil.rmtree(profile_dir, ignore_errors=True)
            
            return P(f"Successfully reopened: {url}", style="color: green;")
            
        except Exception as e:
            error_msg = f"Error reopening URL with Selenium: {str(e)}"
            logger.error(error_msg)
            await self.message_queue.add(pip, error_msg, verbatim=True)
            return P(error_msg, style=pip.get_style("error"))

    # --- Placeholder Step Methods ---

    async def step_01(self, request):
        """Handles GET request for URL input step."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        url_value = step_data.get(step.done, "")

        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and url_value:
            return Div(
                Card(
                    H3(f"🔒 {step.show}"),
                    P(f"URL configured: ", B(url_value)),
                    Button(
                        "Open URL Again ▸",
                        type="button",
                        _onclick=f"window.open('{url_value}', '_blank')",
                        cls="secondary"
                    )
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
            
        # Check if step is complete and not being reverted to
        elif url_value and state.get("_revert_target") != step_id:
            content_container = pip.widget_container(
                step_id=step_id,
                app_name=app_name,
                message=f"{step.show}: {url_value}",
                widget=Div(
                    P(f"URL configured: ", B(url_value)),
                    Button(
                        "Open URL Again ▸",
                        type="button",
                        _onclick=f"window.open('{url_value}', '_blank')",
                        cls="secondary"
                    )
                ),
                steps=steps
            )
            return Div(
                content_container,
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        else:
            await self.message_queue.add(pip, "Enter the URL you want to open:", verbatim=True)
            
            # Use existing value if available, otherwise use default
            display_value = url_value if step.refill and url_value else "https://example.com/"
            
            return Div(
                Card(
                    H3(f"{step.show}"),
                    Form(
                        Input(
                            type="url",
                            name="url",
                            placeholder="https://example.com/",
                            required=True,
                            value=display_value,
                            cls="contrast"
                        ),
                        Button("Open URL ▸", type="submit", cls="primary"),
                        hx_post=f"/{app_name}/{step_id}_submit", 
                        hx_target=f"#{step_id}"
                    )
                ),
                Div(id=next_step_id),
                id=step_id
            )

    async def step_01_submit(self, request):
        """Process the URL submission and open the URL."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Get and validate URL
        form = await request.form()
        url = form.get("url", "").strip()
        
        if not url:
            return P("Error: URL is required", style=pip.get_style("error"))
        
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        
        # Store URL in state
        await pip.update_step_state(pipeline_id, step_id, url, steps)
        
        # Open URL immediately
        import webbrowser
        webbrowser.open(url)
        await self.message_queue.add(pip, f"Opening URL: {url}", verbatim=True)
        
        # Create widget with reopen button
        url_widget = Div(
            P(f"URL configured: ", B(url)),
            Button(
                "Open URL Again ▸",
                type="button",
                _onclick=f"window.open('{url}', '_blank')",
                cls="secondary"
            )
        )
        
        # Create content container
        content_container = pip.widget_container(
            step_id=step_id,
            app_name=app_name,
            message=f"{step.show}: {url}",
            widget=url_widget,
            steps=steps
        )
        
        # Return with chain reaction to next step
        return Div(
            content_container,
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )

    async def step_02(self, request):
        """Handles GET request for Google Search step."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_02"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        query_value = step_data.get(step.done, "")

        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and query_value:
            search_url = f"https://www.google.com/search?q={query_value}"
            return Div(
                Card(
                    H3(f"🔒 {step.show}"),
                    P(f"Search query: ", B(query_value)),
                    Button(
                        "Search Again ▸",
                        type="button",
                        _onclick=f"window.open('{search_url}', '_blank')",
                        cls="secondary"
                    )
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
            
        # Check if step is complete and not being reverted to
        elif query_value and state.get("_revert_target") != step_id:
            search_url = f"https://www.google.com/search?q={query_value}"
            content_container = pip.widget_container(
                step_id=step_id,
                app_name=app_name,
                message=f"{step.show}: {query_value}",
                widget=Div(
                    P(f"Search query: ", B(query_value)),
                    Button(
                        "Search Again ▸",
                        type="button",
                        _onclick=f"window.open('{search_url}', '_blank')",
                        cls="secondary"
                    )
                ),
                steps=steps
            )
            return Div(
                content_container,
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        else:
            await self.message_queue.add(pip, "Enter your Google search query:", verbatim=True)
            
            # Use existing value if available, otherwise use default
            display_value = query_value if step.refill and query_value else "example search"
            
            return Div(
                Card(
                    H3(f"{step.show}"),
                    Form(
                        Input(
                            type="text",
                            name="query",
                            placeholder="Enter search query",
                            required=True,
                            value=display_value,
                            cls="contrast"
                        ),
                        Button("Search ▸", type="submit", cls="primary"),
                        hx_post=f"/{app_name}/{step_id}_submit", 
                        hx_target=f"#{step_id}"
                    )
                ),
                Div(id=next_step_id),
                id=step_id
            )

    async def step_02_submit(self, request):
        """Process the search query submission and open Google search."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_02"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Get and validate query
        form = await request.form()
        query = form.get("query", "").strip()
        
        if not query:
            return P("Error: Search query is required", style=pip.get_style("error"))
        
        # Store query in state
        await pip.update_step_state(pipeline_id, step_id, query, steps)
        
        # Construct and open search URL
        search_url = f"https://www.google.com/search?q={query}"
        import webbrowser
        webbrowser.open(search_url)
        await self.message_queue.add(pip, f"Opening Google search: {query}", verbatim=True)
        
        # Create widget with search again button
        search_widget = Div(
            P(f"Search query: ", B(query)),
            Button(
                "Search Again ▸",
                type="button",
                _onclick=f"window.open('{search_url}', '_blank')",
                cls="secondary"
            )
        )
        
        # Create content container
        content_container = pip.widget_container(
            step_id=step_id,
            app_name=app_name,
            message=f"{step.show}: {query}",
            widget=search_widget,
            steps=steps
        )
        
        # Return with chain reaction to next step
        return Div(
            content_container,
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )

    async def step_03(self, request):
        """Handles GET request for Selenium URL step."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_03"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        url_value = step_data.get(step.done, "")

        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and url_value:
            return Div(
                Card(
                    H3(f"🔒 {step.show}"),
                    P(f"URL configured: ", B(url_value)),
                    Form(
                        Input(type="hidden", name="url", value=url_value),
                        Button(
                            "Open URL Again 🪄",
                            type="submit",
                            cls="secondary"
                        ),
                        hx_post=f"/{app_name}/reopen_url",
                        hx_target=f"#{step_id}-status"
                    ),
                    Div(id=f"{step_id}-status")
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )

        # Check if step is complete and not being reverted to
        elif url_value and state.get("_revert_target") != step_id:
            content_container = pip.widget_container(
                step_id=step_id,
                app_name=app_name,
                message=f"{step.show}: {url_value}",
                widget=Div(
                    P(f"URL configured: ", B(url_value)),
                    Form(
                        Input(type="hidden", name="url", value=url_value),
                        Button(
                            "Open URL Again 🪄",
                            type="submit",
                            cls="secondary"
                        ),
                        hx_post=f"/{app_name}/reopen_url",
                        hx_target=f"#{step_id}-status"
                    ),
                    Div(id=f"{step_id}-status")
                ),
                steps=steps
            )
            return Div(
                content_container,
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        else:
            await self.message_queue.add(pip, "Enter the URL you want to open with Selenium:", verbatim=True)
            
            # Use existing value if available, otherwise use default
            display_value = url_value if step.refill and url_value else "https://example.com/"
            
            return Div(
                Card(
                    H3(f"{step.show}"),
                    Form(
                        Input(
                            type="url",
                            name="url",
                            placeholder="https://example.com/",
                            required=True,
                            value=display_value,
                            cls="contrast"
                        ),
                        Button("Open URL 🪄", type="submit", cls="primary"),
                        hx_post=f"/{app_name}/{step_id}_submit", 
                        hx_target=f"#{step_id}"
                    )
                ),
                Div(id=next_step_id),
                id=step_id
            )

    async def step_03_submit(self, request):
        """Process the URL submission and open it with Selenium."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_03"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Get and validate URL
        form = await request.form()
        url = form.get("url", "").strip()
        
        if not url:
            return P("Error: URL is required", style=pip.get_style("error"))
        
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        
        # Store URL in state
        await pip.update_step_state(pipeline_id, step_id, url, steps)
        
        try:
            # Set up Chrome options
            chrome_options = Options()
            # chrome_options.add_argument("--headless")  # Commented out for visibility
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--new-window")  # Force new window
            chrome_options.add_argument("--start-maximized")  # Start maximized
            
            # Create a temporary profile directory
            import tempfile
            profile_dir = tempfile.mkdtemp()
            chrome_options.add_argument(f"--user-data-dir={profile_dir}")
            
            # Log the current OS and environment
            effective_os = os.environ.get("EFFECTIVE_OS", "unknown")
            await self.message_queue.add(pip, f"Current OS: {effective_os}", verbatim=True)
            
            # Initialize the Chrome driver
            if effective_os == "darwin":
                # On macOS, use webdriver-manager
                await self.message_queue.add(pip, "Using webdriver-manager for macOS", verbatim=True)
                service = Service(ChromeDriverManager().install())
            else:
                # On Linux, use system Chrome
                await self.message_queue.add(pip, "Using system Chrome for Linux", verbatim=True)
                service = Service()
            
            await self.message_queue.add(pip, "Initializing Chrome driver...", verbatim=True)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Open the URL
            await self.message_queue.add(pip, f"Opening URL with Selenium: {url}", verbatim=True)
            driver.get(url)
            
            # Wait a moment to ensure the page loads
            await asyncio.sleep(2)
            
            # Get the page title to confirm it loaded
            title = driver.title
            await self.message_queue.add(pip, f"Page loaded successfully. Title: {title}", verbatim=True)
            
            # Close the browser
            driver.quit()
            await self.message_queue.add(pip, "Browser closed successfully", verbatim=True)
            
            # Clean up the temporary profile directory
            import shutil
            shutil.rmtree(profile_dir, ignore_errors=True)
            
        except Exception as e:
            error_msg = f"Error opening URL with Selenium: {str(e)}"
            logger.error(error_msg)
            await self.message_queue.add(pip, error_msg, verbatim=True)
            return P(error_msg, style=pip.get_style("error"))
        
        # Create widget with reopen button
        url_widget = Div(
            P(f"URL configured: ", B(url)),
            Form(
                Input(type="hidden", name="url", value=url),
                Button(
                    "Open URL Again 🪄",
                    type="submit",
                    cls="secondary"
                ),
                hx_post=f"/{app_name}/reopen_url",
                hx_target=f"#{step_id}-status"
            ),
            Div(id=f"{step_id}-status")
        )
        
        # Create content container
        content_container = pip.widget_container(
            step_id=step_id,
            app_name=app_name,
            message=f"{step.show}: {url}",
            widget=url_widget,
            steps=steps
        )
        
        # Return with chain reaction to next step
        return Div(
            content_container,
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
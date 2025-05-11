import asyncio
from collections import namedtuple
from datetime import datetime
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse, quote
from seleniumwire import webdriver as wire_webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from starlette.responses import HTMLResponse, JSONResponse

from fasthtml.common import * # type: ignore
from loguru import logger

"""
Pipulate Browser Automation Workflow

This workflow demonstrates Selenium-based browser automation capabilities:
- Cross-platform Chrome automation (Linux/macOS)
- Clean browser sessions with temporary profiles
- Detailed status logging and error handling
- URL opening and verification
"""

def get_safe_path(url):
    """Convert URL to filesystem-safe path while maintaining reversibility."""
    parsed = urlparse(url)
    domain = parsed.netloc
    path = quote(parsed.path + ('?' + parsed.query if parsed.query else ''), safe='')
    return domain, path

def reconstruct_url(domain, path):
    """Reconstruct URL from filesystem components."""
    return f"https://{domain}{path}"

def ensure_crawl_dir(app_name, domain, date_slug):
    """Ensure crawl directory exists and return its path."""
    base_dir = os.path.join("downloads", app_name, domain, date_slug)
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

# Model for a workflow step
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class BrowserAutomation:
    """
    Browser Automation Workflow
    
    A workflow that demonstrates Selenium integration for browser automation tasks.
    This serves as the primary development ground for Pipulate's browser automation features.
    """
    # --- Workflow Configuration ---
    APP_NAME = "browser"              # Unique identifier for this workflow's routes and data
    DISPLAY_NAME = "Browser Automation" # User-friendly name shown in the UI
    ENDPOINT_MESSAGE = (            # Message shown on the workflow's landing page
        "Open URLs using Selenium for browser automation. "
        "This workflow demonstrates Pipulate's browser automation capabilities."
    )
    TRAINING_PROMPT = (
        "This workflow showcases browser automation using Selenium. "
        "It uses webdriver-manager for cross-platform compatibility and "
        "provides a foundation for developing more advanced automation features."
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
                done='placeholder',
                show='Placeholder Step',
                refill=True,
            ),
            Step(
                id='step_03',
                done='session_test_complete',
                show='Google Session Test',
                refill=False,
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
            (f"/{app_name}/reopen_url", self.reopen_url, ["POST"]),  # Route for reopening URLs
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

    async def step_01(self, request):
        """Handles GET request for Open URL step."""
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
                    H3(f"🔒 Open URL"),
                    P(f"URL opened (and closed): ", B(url_value)),
                    Div(id=f"{step_id}-status")
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )

        # Check if step is complete and not being reverted to
        if url_value and state.get("_revert_target") != step_id:
            content_container = pip.widget_container(
                step_id=step_id,
                app_name=app_name,
                message=f"Open URL: {url_value}",
                widget=Div(
                    P(f"URL opened (and closed): ", B(url_value)),
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
            display_value = url_value if step.refill and url_value else "https://example.com"
            return Div(
                Card(
                    H3("Open URL"),
                    Form(
                        Input(
                            type="url",
                            name="url",
                            placeholder="https://example.com",
                            required=True,
                            value=display_value,
                            cls="contrast"
                        ),
                        Button("Open URL", type="submit", cls="primary"),
                        hx_post=f"/{app_name}/{step_id}_submit", 
                        hx_target=f"#{step_id}"
                    )
                ),
                Div(id=next_step_id),
                id=step_id
            )

    async def step_01_submit(self, request):
        """Process the Open URL submission and open it with Selenium."""
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
            # Escape angle brackets for logging
            safe_error_msg = error_msg.replace("<", "&lt;").replace(">", "&gt;")
            await self.message_queue.add(pip, safe_error_msg, verbatim=True)
            return P(error_msg, style=pip.get_style("error"))

        # Create widget without reopen button
        url_widget = Div(
            P(f"URL opened (and closed): ", B(url)),
            Div(id=f"{step_id}-status")
        )

        # Create content container
        content_container = pip.widget_container(
            step_id=step_id,
            app_name=app_name,
            message=f"Open URL: {url}",
            widget=url_widget,
            steps=steps
        )

        # Return with chain reaction to next step
        return Div(
            content_container,
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )

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

    # Helper functions for crawl/save logic

    async def step_02(self, request):
        """Handles GET request for Crawl URL step (identical to Step 1, independent state, crawl semantics)."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_02"
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
                    H3(f"🔒 Crawl URL"),
                    P(f"URL crawled and saved: ", B(url_value)),
                    Div(id=f"{step_id}-status")
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )

        # Check if step is complete and not being reverted to
        if url_value and state.get("_revert_target") != step_id:
            content_container = pip.widget_container(
                step_id=step_id,
                app_name=app_name,
                message=f"Crawl URL: {url_value}",
                widget=Div(
                    P(f"URL crawled and saved: ", B(url_value)),
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
            await self.message_queue.add(pip, "Enter the URL you want to crawl:", verbatim=True)
            display_value = url_value if step.refill and url_value else "https://example.com"
            return Div(
                Card(
                    H3("Crawl URL"),
                    Form(
                        Input(
                            type="url",
                            name="url",
                            placeholder="https://example.com",
                            required=True,
                            value=display_value,
                            cls="contrast"
                        ),
                        Button("Crawl URL", type="submit", cls="primary"),
                        hx_post=f"/{app_name}/{step_id}_submit", 
                        hx_target=f"#{step_id}"
                    )
                ),
                Div(id=next_step_id),
                id=step_id
            )

    async def step_02_submit(self, request):
        """Process the Crawl URL submission, open with Selenium-wire, and save crawl data."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_02"
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

        try:
            # Set up Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--new-window")
            chrome_options.add_argument("--start-maximized")

            # Create a temporary profile directory
            import tempfile
            profile_dir = tempfile.mkdtemp()
            chrome_options.add_argument(f"--user-data-dir={profile_dir}")

            # Log the current OS and environment
            effective_os = os.environ.get("EFFECTIVE_OS", "unknown")
            await self.message_queue.add(pip, f"Current OS: {effective_os}", verbatim=True)

            # Initialize the Chrome driver (seleniumwire)
            if effective_os == "darwin":
                await self.message_queue.add(pip, "Using webdriver-manager for macOS", verbatim=True)
                service = Service(ChromeDriverManager().install())
            else:
                await self.message_queue.add(pip, "Using system Chrome for Linux", verbatim=True)
                service = Service()

            await self.message_queue.add(pip, "Initializing Chrome driver...", verbatim=True)
            driver = wire_webdriver.Chrome(service=service, options=chrome_options)

            # Open the URL
            await self.message_queue.add(pip, f"Crawling URL with Selenium: {url}", verbatim=True)
            driver.get(url)

            # Wait a moment to ensure the page loads
            await asyncio.sleep(2)

            # Get page data
            title = driver.title
            source = driver.page_source
            dom = driver.execute_script("return document.documentElement.outerHTML;")

            # Get response data from seleniumwire
            # Try to find the main request (handle redirects, trailing slashes, etc.)
            main_request = None
            for request in driver.requests:
                if request.response and request.url.startswith(url):
                    main_request = request
                    break
            # If not found, fallback to first request with a response
            if not main_request:
                for request in driver.requests:
                    if request.response:
                        main_request = request
                        break
            if main_request and main_request.response:
                headers = dict(main_request.response.headers)
                status = main_request.response.status_code
            else:
                headers = {}
                status = 200  # Default to 200 if we can't get the actual status

            # Prepare directory structure
            domain, path = get_safe_path(url)
            date_slug = datetime.now().strftime("%Y%m%d")
            base_dir = ensure_crawl_dir(app_name, domain, date_slug)
            crawl_dir = os.path.join(base_dir, path)
            os.makedirs(crawl_dir, exist_ok=True)

            # Save files
            with open(os.path.join(crawl_dir, "headers.json"), "w") as f:
                json.dump(headers, f, indent=2)
            with open(os.path.join(crawl_dir, "source.html"), "w") as f:
                f.write(source)
            with open(os.path.join(crawl_dir, "dom.html"), "w") as f:
                f.write(dom)

            # Close the browser
            driver.quit()
            await self.message_queue.add(pip, "Browser closed successfully", verbatim=True)

            # Clean up the temporary profile directory
            import shutil
            shutil.rmtree(profile_dir, ignore_errors=True)

            # Store crawl data in state (including reconstructed URL)
            reconstructed_url = reconstruct_url(domain, path)
            crawl_data = {
                "url": url,
                "title": title,
                "status": status,
                "save_path": crawl_dir,
                "timestamp": datetime.now().isoformat(),
                "reconstructed_url": reconstructed_url
            }
            await pip.update_step_state(pipeline_id, step_id, crawl_data, steps)
            await self.message_queue.add(pip, f"{step.show} complete.", verbatim=True)

            # Create widget with summary and reconstructed URL
            url_widget = Div(
                P(f"URL crawled and saved: ", B(url)),
                P(f"Title: {title}"),
                P(f"Status: {status}"),
                P(f"Saved to: {crawl_dir}"),
                P(f"Reconstructed URL: {reconstructed_url}", style="color: #666; font-size: 0.9em;"),
                Div(id=f"{step_id}-status")
            )

            # Create content container
            content_container = pip.widget_container(
                step_id=step_id,
                app_name=app_name,
                message=f"Crawl URL: {url}",
                widget=url_widget,
                steps=steps
            )

            # Return with chain reaction to next step
            return Div(
                content_container,
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )

        except Exception as e:
            error_msg = f"Error crawling URL with Selenium: {str(e)}"
            logger.error(error_msg)
            safe_error_msg = error_msg.replace("<", "&lt;").replace(">", "&gt;")
            await self.message_queue.add(pip, safe_error_msg, verbatim=True)
            return P(error_msg, style=pip.get_style("error")) 

    def _get_persistent_profile_dir(self, pipeline_id: str, profile_name: str = "google_session") -> str:
        """Get or create a persistent profile directory for Selenium."""
        from pathlib import Path
        # Ensure the base directory for profiles exists
        base_profiles_dir = Path("data") / self.app_name / "profiles"
        base_profiles_dir.mkdir(parents=True, exist_ok=True)
        
        # Sanitize pipeline_id for use as a directory name
        safe_pipeline_id = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in pipeline_id)
        
        profile_path = base_profiles_dir / safe_pipeline_id / profile_name
        profile_path.mkdir(parents=True, exist_ok=True)
        return str(profile_path)

    def _get_selenium_profile_paths(self, pipeline_id: str, desired_profile_leaf_name: str = "google_session") -> tuple[str, str]:
        """Get the user data directory and profile directory paths for Chrome.
        
        Returns a tuple of (user_data_dir_path, profile_directory_name) where:
        - user_data_dir_path is the parent directory for Chrome's user data
        - profile_directory_name is the specific profile to use within that directory
        """
        from pathlib import Path
        safe_pipeline_id = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in pipeline_id)
        
        # This directory will be the root for Chrome's user data for this pipeline instance.
        # It can contain multiple profiles, though we'll only use one.
        user_data_root_for_pipeline = Path("data") / self.app_name / "selenium_user_data" / safe_pipeline_id
        user_data_root_for_pipeline.mkdir(parents=True, exist_ok=True)
        
        # This is the name of the specific profile directory *within* user_data_root_for_pipeline.
        # e.g., data/browser/selenium_user_data/my_profile-browser-01/google_session/
        return str(user_data_root_for_pipeline), desired_profile_leaf_name

    async def step_03(self, request):
        """Handles GET request for Google session persistence test."""
        # Get pipeline ID from db for consistency
        pipeline_id = self.db.get("pipeline_id", "unknown")
        if not pipeline_id or pipeline_id == "unknown":
            return JSONResponse(
                status_code=400,
                content={"error": "No pipeline ID found in db"}
            )

        # Get profile paths using new helper
        user_data_dir, profile_dir = self._get_selenium_profile_paths(pipeline_id)
        
        return Div(
            Card(
                H3("Google Session Persistence Test"),
                P("Instructions:"),
                P("1. Click the button below to open Google in a new browser window"),
                P("2. Log in to your Google account"),
                P("3. Close the browser window when done"),
                P("4. Return here to check your session status"),
                Form(
                    Button("Open Google & Log In", type="submit", cls="primary"),
                    hx_post=f"/{self.app_name}/step_03_submit",
                    hx_target="#step_03"
                )
            ),
            id="step_03"
        )

    async def step_03_submit(self, request):
        """Handles POST request for Google session persistence test."""
        try:
            # Get pipeline ID from db for consistency
            pipeline_id = self.db.get("pipeline_id", "unknown")
            if not pipeline_id or pipeline_id == "unknown":
                return JSONResponse(
                    status_code=400,
                    content={"error": "No pipeline ID found in db"}
                )

            # Get profile paths using new helper
            user_data_dir, profile_dir = self._get_selenium_profile_paths(pipeline_id)
            
            # Configure Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
            chrome_options.add_argument(f"--profile-directory={profile_dir}")
            
            # Add stealth options to avoid detection
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            
            # Initialize Chrome driver
            driver = webdriver.Chrome(options=chrome_options)
            
            # Execute CDP commands to prevent detection
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                """
            })
            
            try:
                # Navigate to Google
                driver.get("https://www.google.com")
                
                # Wait for page to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "q"))
                )
                
                # Check if user is logged in by looking for profile picture
                try:
                    profile_pic = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "img[alt*='Google Account']"))
                    )
                    is_logged_in = True
                except TimeoutException:
                    is_logged_in = False
                
                # Update step data to mark completion
                step_data = self.pipulate.get_step_data(pipeline_id, "step_03", {})
                step_data["session_test_complete"] = True
                step_data["is_logged_in"] = is_logged_in
                step_data["user_data_dir"] = user_data_dir
                step_data["profile_dir"] = profile_dir
                
                # Update state
                state = self.pipulate.read_state(pipeline_id)
                state["step_03"] = step_data
                self.pipulate.write_state(pipeline_id, state)
                
                # Return updated UI with clearer instructions
                return Div(
                    Card(
                        H3("Google Session Persistence Test"),
                        P("Instructions:"),
                        P("1. A new browser window has opened with Google"),
                        P("2. Log in to your Google account in that window"),
                        P("3. After logging in, close the browser window"),
                        P("4. Return here and click the button below to check your session status"),
                        P(f"Current Status: {'Logged In' if is_logged_in else 'Not Logged In'}"),
                        Form(
                            Button("Check Login Status", type="submit", cls="primary"),
                            hx_post=f"/{self.app_name}/step_03_submit",
                            hx_target="#step_03"
                        )
                    ),
                    id="step_03"
                )
                
            except Exception as e:
                # If there's an error, make sure to close the browser
                driver.quit()
                raise e
                
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            ) 
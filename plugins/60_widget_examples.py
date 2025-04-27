import asyncio
import json
from collections import namedtuple
from datetime import datetime
from pathlib import Path

import pandas as pd
from fasthtml.common import * # type: ignore
from starlette.responses import HTMLResponse
from loguru import logger
from rich.console import Console
from rich.table import Table
from fastcore.xml import NotStr

"""
Pipulate Widget Examples

This workflow demonstrates various widget types that can be integrated into Pipulate Workflows:

1. Simple HTMX Widget: Basic HTML content with no JavaScript execution
2. Pandas Table Widget: HTML table from DataFrame
3. JavaScript Execution Widget: DOM manipulation via JavaScript in HTMX-injected content
4. Mermaid Diagram Renderer: Client-side rendering using mermaid.js
5. Code Syntax Highlighter: Syntax highlighting with Prism.js

This serves as a reference implementation for creating visualization widgets in Pipulate.

--- Design Pattern Note ---
This workflow uses a "Combined Step" pattern where each step handles both:
1. Data collection (input form)
2. Widget rendering (visualization)

In each step, user input is collected and immediately transformed into the 
corresponding visualization in the same card upon submission. This approach:
- Reduces the total number of workflow steps (5 instead of 10)
- Creates a clear cause-effect relationship within each step
- Simplifies navigation for the end user

An alternative "Separated Step" pattern would:
- Split each feature into separate input and display steps
- Use one step for data collection, followed by a step for visualization
- Result in 10 steps total (plus finalize)
- Potentially simplify each individual step's implementation
- Allow for more focused step responsibilities

When adapting this example for your own workflows, consider which pattern 
best suits your needs:
- Combined: When immediate visualization feedback is valuable
- Separated: When data collection and visualization are distinct concerns
             or when complex transformations occur between input and display
"""

# Model for a workflow step (Do not change)
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class WidgetExamples:
    """
    Widget Examples Workflow
    
    Demonstrates various widget types for Pipulate Workflows:
    1. Simple HTMX Widget - No JS execution
    2. Markdown Renderer (MarkedJS) - Client-side rendering using marked.js
    3. Mermaid Diagram Renderer - Client-side rendering using mermaid.js
    4. Pandas Table Widget - HTML table from DataFrame
    5. Code Syntax Highlighter - Syntax highlighting with Prism.js
    6. JavaScript Execution Widget - Running JS in HTMX-injected content
    
    Key Implementation Notes:
    - Widgets use pip.widget_container for consistent styling and DOM structure
    - JavaScript widgets use unique IDs for targeting in the DOM
    - Client-side libraries are loaded in server.py's hdrs tuple
    - HX-Trigger headers are used for reliable JS execution in HTMX-injected content
    
    --- Design Pattern: Combined vs. Separated Steps ---
    
    Current Implementation: "Combined Step" Pattern
    This workflow uses a pattern where each step handles both data collection
    and visualization in the same step. When the user submits an input form,
    the same card transforms to display the visualization widget.
    
    Key characteristics:
    - Each step_XX_submit handler creates and returns the widget immediately
    - Widgets are displayed in place of the input form after submission
    - The revert control shows the widget until user chooses to revert
    - This creates a compact 6-step workflow (plus finalize)
    
    Alternative Approach: "Separated Step" Pattern
    A different design would separate input collection and visualization:
    - One step for collecting input (e.g., step_01_data_input)
    - Next step for displaying the widget (e.g., step_02_display_widget)
    - This would result in 12 steps total (plus finalize)
    - Each step would have simpler, more focused responsibility
    
    Implementation Considerations:
    - When copying this example, you may want to separate complex input collection
      and visualization into discrete steps for clarity and maintainability
    - Use the transform parameter in the Step namedtuple to pass data between
      separated input and visualization steps
    - The current combined approach works well for simpler widgets where immediate
      feedback is valuable to the user
    """
    # --- Workflow Configuration ---
    APP_NAME = "widgets"
    DISPLAY_NAME = "Widget Examples"
    ENDPOINT_MESSAGE = (
        "This workflow demonstrates various widget types for Pipulate. "
        "Enter an ID to start or resume your workflow."
    )
    TRAINING_PROMPT = "Demonstrates various widget types in Pipulate Workflows"
    PRESERVE_REFILL = True

    # --- Initialization ---
    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
        """
        Initialize the workflow, define steps, and register routes.
        """
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
                done='simple_content',
                show='Simple HTMX Widget',
                refill=True,
            ),
            Step(
                id='step_02',
                done='markdown_content_step6',
                show='Markdown Renderer (MarkedJS)',
                refill=True,
            ),
            Step(
                id='step_03',
                done='markdown_content',
                show='Markdown Renderer',
                refill=True,
            ),
            Step(
                id='step_04',
                done='table_data',
                show='Pandas Table Widget',
                refill=True,
            ),
            Step(
                id='step_05',
                done='code_content',
                show='Code Syntax Highlighter',
                refill=True,
            ),
            Step(
                id='step_06',
                done='js_content',
                show='JavaScript Widget',
                refill=True,
            ),
        ]
        
        # Standard workflow routes
        routes = [
            (f"/{app_name}", self.landing),
            (f"/{app_name}/init", self.init, ["POST"]),
            (f"/{app_name}/jump_to_step", self.jump_to_step, ["POST"]),
            (f"/{app_name}/revert", self.handle_revert, ["POST"]),
            (f"/{app_name}/finalize", self.finalize, ["GET", "POST"]),
            (f"/{app_name}/unfinalize", self.unfinalize, ["POST"]),
        ]

        # Routes for each custom step
        self.steps = steps
        for step in steps:
            step_id = step.id
            routes.append((f"/{app_name}/{step_id}", getattr(self, step_id)))
            routes.append((f"/{app_name}/{step_id}_submit", getattr(self, f"{step_id}_submit"), ["POST"]))

        # Register routes with the FastHTML app
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ["GET"]
            app.route(path, methods=method_list)(handler)

        # Define UI messages
        self.step_messages = {
            "finalize": {
                "ready": "All steps complete. Ready to finalize workflow.",
                "complete": f"Workflow finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes."
            },
            "new": "Please complete each step to explore different widget types."
        }

        # Default messages for each step
        for step in steps:
            self.step_messages[step.id] = {
                "input": f"{pip.fmt(step.id)}: Enter content for {step.show}.",
                "complete": f"{step.show} complete. Continue to next step."
            }

        # Add finalize step
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

    # --- Core Workflow Engine Methods ---

    async def landing(self):
        """ Renders the initial landing page with the key input form. """
        pip, pipeline, steps, app_name = self.pipulate, self.pipeline, self.steps, self.app_name
        context = pip.get_plugin_context(self)
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
        """ Initialize the workflow state and redirect to the first step. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        user_input = form.get("pipeline_id", "").strip()

        if not user_input:
            from starlette.responses import Response
            response = Response("")
            response.headers["HX-Refresh"] = "true"
            return response

        # Generate or parse the unique pipeline ID
        context = pip.get_plugin_context(self)
        plugin_name = context['plugin_name'] or app_name
        profile_name = context['profile_name'] or "default"
        profile_part = profile_name.replace(" ", "_")
        plugin_part = plugin_name.replace(" ", "_")
        expected_prefix = f"{profile_part}-{plugin_part}-"

        if user_input.startswith(expected_prefix):
            pipeline_id = user_input
        else:
            _, prefix, user_provided_id = pip.generate_pipeline_key(self, user_input)
            pipeline_id = f"{prefix}{user_provided_id}"

        db["pipeline_id"] = pipeline_id
        logger.debug(f"Using pipeline ID: {pipeline_id}")

        # Initialize state if missing
        state, error = pip.initialize_if_missing(pipeline_id, {"app_name": app_name})
        if error: return error
        all_steps_complete = all(step.id in state and step.done in state[step.id] for step in steps[:-1])
        is_finalized = "finalize" in state and "finalized" in state["finalize"]

        # Add initial status messages
        await self.message_queue.add(pip, f"Workflow ID: {pipeline_id}", verbatim=True, spaces_before=0)
        await self.message_queue.add(pip, f"Return later by selecting '{pipeline_id}' from the dropdown.", verbatim=True, spaces_before=0)
        if all_steps_complete:
            status_msg = f"Workflow is complete and finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes." if is_finalized \
                else "Workflow is complete but not finalized. Press Finalize to lock your data."
            await self.message_queue.add(pip, status_msg, verbatim=True)
        elif not any(step.id in state for step in self.steps):
            await self.message_queue.add(pip, self.step_messages["new"], verbatim=True)

        # Update the datalist
        parsed = pip.parse_pipeline_key(pipeline_id)
        prefix = f"{parsed['profile_part']}-{parsed['plugin_part']}-"
        self.pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in self.pipeline() if record.pkey.startswith(prefix)]
        if pipeline_id not in matching_records: matching_records.append(pipeline_id)
        updated_datalist = pip.update_datalist("pipeline-ids", options=matching_records)

        # Rebuild the UI, triggering the first step load
        return pip.rebuild(app_name, steps)

    async def finalize(self, request):
        """ Handle GET/POST requests to finalize (lock) the workflow. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        finalize_step = steps[-1]
        finalize_data = pip.get_step_data(pipeline_id, finalize_step.id, {})

        if request.method == "GET":
            # Show locked view or finalize button
            if finalize_step.done in finalize_data:
                return Card(
                    H4("Workflow is locked."),
                    Form(
                        Button(pip.UNLOCK_BUTTON_LABEL, type="submit", cls="secondary outline"),
                        hx_post=f"/{app_name}/unfinalize", hx_target=f"#{app_name}-container", hx_swap="outerHTML"
                    ),
                    id=finalize_step.id
                )
            else:
                # Check if all steps are complete before offering finalize
                all_steps_complete = all(pip.get_step_data(pipeline_id, step.id, {}).get(step.done) for step in steps[:-1])
                if all_steps_complete:
                    return Card(
                        H4("All steps complete. Finalize?"),
                        P("You can revert to any step and make changes.", style="font-size: 0.9em; color: #666;"),
                        Form(
                            Button("Finalize", type="submit", cls="primary"),
                            hx_post=f"/{app_name}/finalize", hx_target=f"#{app_name}-container", hx_swap="outerHTML"
                        ),
                        id=finalize_step.id
                    )
                else:
                    return Div(id=finalize_step.id)
        else:  # POST request
            await pip.finalize_workflow(pipeline_id)
            await self.message_queue.add(pip, self.step_messages["finalize"]["complete"], verbatim=True)
            return pip.rebuild(app_name, steps)

    async def unfinalize(self, request):
        """ Handle POST request to unlock the workflow. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, "Workflow unfinalized! You can now revert to any step and make changes.", verbatim=True)
        return pip.rebuild(app_name, steps)

    async def jump_to_step(self, request):
        """ Handle POST request from breadcrumb navigation to jump to a step. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        db["step_id"] = step_id
        return pip.rebuild(app_name, steps)

    async def get_suggestion(self, step_id, state):
        """ Gets a suggested input value for a step, often using the previous step's transformed output. """
        pip, db, steps = self.pipulate, self.db, self.steps
        
        # Pre-populated examples for each widget type
        examples = {
            'step_01': """Simple HTML content example:
- Basic text formatting
- No complex HTML tags
- Plain content for demonstration
- Easy to modify

This is a sample widget that shows basic text content.
It works well with the HTMX updates and keeps things simple.""",
            
            'step_02': """# Markdown Example

This is a **bold statement** about _markdown_.

## Features demonstrated:

1. Headings (h1, h2)
2. Formatted text (**bold**, _italic_)
3. Ordered lists
4. Unordered lists
   - Nested item 1
   - Nested item 2
5. Code blocks

### Code Example

```python
def hello_world():
    print("Hello from Markdown!")
    for i in range(3):
        print(f"Count: {i}")
```

> Blockquotes are also supported
> - With nested lists
> - And formatting

[Learn more about Markdown](https://www.markdownguide.org/)
""",
            
            'step_03': """graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[Result 1]
    D --> F[Result 2]
    E --> G[End]
    F --> G""",
            
            'step_04': """[
    {"Name": "John", "Age": 32, "Role": "Developer", "Department": "Engineering"},
    {"Name": "Jane", "Age": 28, "Role": "Designer", "Department": "Product"},
    {"Name": "Bob", "Age": 45, "Role": "Manager", "Department": "Engineering"},
    {"Name": "Alice", "Age": 33, "Role": "PM", "Department": "Product"},
    {"Name": "Charlie", "Age": 40, "Role": "Architect", "Department": "Engineering"}
]""",
            
            'step_05': """function calculateFactorial(n) {
    // Base case: factorial of 0 or 1 is 1
    if (n <= 1) {
        return 1;
    }
    
    // Recursive case: n! = n * (n-1)!
    return n * calculateFactorial(n - 1);
}

// Example usage
for (let i = 0; i < 10; i++) {
    console.log(`Factorial of ${i} is ${calculateFactorial(i)}`);
}
""",

            'step_06': """// Simple counter example
let count = 0;
const countDisplay = document.createElement('div');
countDisplay.style.fontSize = '24px';
countDisplay.style.margin = '20px 0';
countDisplay.textContent = count;

const button = document.createElement('button');
button.textContent = 'Increment Count';
button.style.backgroundColor = '#9370DB';
button.style.borderColor = '#9370DB';
button.onclick = function() {
    count++;
    countDisplay.textContent = count;
};

widget.appendChild(countDisplay);
widget.appendChild(button);"""
        }
        
        # Return pre-populated example or empty string
        return examples.get(step_id, "")

    async def handle_revert(self, request):
        """ Handle POST request to revert to a previous step. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        pipeline_id = db.get("pipeline_id", "unknown")
        if not step_id: return P("Error: No step specified", style=pip.get_style("error"))

        # Clear state from the target step onwards
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        # Mark the target step for revert logic in GET handlers
        state = pip.read_state(pipeline_id)
        state["_revert_target"] = step_id
        pip.write_state(pipeline_id, state)

        # Add message and rebuild UI
        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        return pip.rebuild(app_name, steps)

    # --- Step 1: Simple HTMX Widget ---
    async def step_01(self, request):
        """ 
        Handles GET request for Step 1: Simple HTMX Widget.
        
        This method demonstrates the "Combined Step" pattern:
        1. If the step is incomplete or being reverted to, shows an input form
        2. If the step is complete, shows the widget with a revert control
        3. If workflow is finalized, shows a locked version of the widget
        
        In a "Separated Step" pattern, this would only handle input collection,
        and a separate step would display the widget.
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "")
        
        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and user_val:
            # Still show the widget but with a locked indicator
            simple_widget = Pre(
                user_val,
                style="padding: 1rem; background-color: var(--pico-code-background); border-radius: var(--pico-border-radius); overflow-x: auto; font-family: monospace;"
            )
            return Div(
                Card(
                    H4(f"🔒 {step.show}"),
                    simple_widget
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
            )
            
        # Check if step is complete and not reverting
        if user_val and state.get("_revert_target") != step_id:
            # Create the simple widget from the existing data
            simple_widget = Pre(
                user_val,
                style="padding: 1rem; background-color: var(--pico-code-background); border-radius: var(--pico-border-radius); overflow-x: auto; font-family: monospace;"
            )
            content_container = pip.widget_container(
                step_id=step_id,
                app_name=app_name,
                message=f"{step.show} Configured",
                widget=simple_widget,
                steps=steps
            )
            return Div(
                content_container,
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
            )
        else:
            # Show input form
            display_value = user_val if step.refill and user_val else await self.get_suggestion(step_id, state)
            await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
            
            return Div(
                Card(
                    H4(f"{pip.fmt(step_id)}: Configure {step.show}"),
                    P("Enter HTML content for the simple widget. Example is pre-populated."),
                    Form(
                        Div(
                            Textarea(
                                display_value,
                                name=step.done,
                                placeholder="Enter HTML content for the widget",
                                required=True,
                                rows=10,
                                style="width: 100%; font-family: monospace;"
                            ),
                            Div(
                                Button("Submit", type="submit", cls="primary"),
                                style="margin-top: 1vh; text-align: right;"
                            ),
                            style="width: 100%;"
                        ),
                        hx_post=f"/{app_name}/{step_id}_submit",
                        hx_target=f"#{step_id}"
                    )
                ),
                Div(id=next_step_id),
                id=step_id
            )

    async def step_01_submit(self, request):
        """ 
        Process the submission for Step 1.
        
        In the "Combined Step" pattern, this method:
        1. Validates the user input
        2. Saves the input to the workflow state
        3. Creates and returns the widget to display
        4. Sets up navigation to the next step
        
        This immediate transformation from input to widget in the same step
        creates a tight cause-effect relationship visible to the user.
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_01"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get("pipeline_id", "unknown")
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'

        # Get form data
        form = await request.form()
        user_val = form.get(step.done, "")

        # Validate input
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            return error_component

        # Save the value to state
        await pip.update_step_state(pipeline_id, step_id, user_val, steps)

        # Create a simple widget with the user's content in a Pre tag to preserve formatting
        simple_widget = Pre(
            user_val,
            style="padding: 1rem; background-color: var(--pico-code-background); border-radius: var(--pico-border-radius); overflow-x: auto; font-family: monospace;"
        )
        
        # Create content container with the widget
        content_container = pip.widget_container(
            step_id=step_id,
            app_name=app_name,
            message=f"{step.show}: Simple text content provided",
            widget=simple_widget,
            steps=steps
        )
        
        # Create full response structure
        response_content = Div(
            content_container,
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
        
        # Send confirmation message
        await self.message_queue.add(pip, f"{step.show} complete.", verbatim=True)

        # Return the HTMLResponse with the widget container
        return HTMLResponse(to_xml(response_content))

    # --- Step 2: Markdown Renderer using marked.js ---
    async def step_02(self, request):
        """
        Step 2 - Markdown Renderer using marked.js
        
        Allows the user to input markdown content that will be rendered
        using the marked.js library for a Jupyter notebook-like experience.
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_02"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "")
        
        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and user_val:
            # Show the markdown renderer in locked state
            try:
                widget_id = f"marked-widget-{pipeline_id.replace('-', '_')}-{step_id}"
                marked_widget = self.create_marked_widget(user_val, widget_id)
                
                # Create response with locked view
                response = HTMLResponse(
                    to_xml(
                        Div(
                            Card(
                                H4(f"🔒 {step.show}"),
                                marked_widget
                            ),
                            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                        )
                    )
                )
                
                # Add HX-Trigger to initialize Marked.js
                response.headers["HX-Trigger"] = json.dumps({
                    "initMarked": {
                        "widgetId": widget_id
                    }
                })
                
                return response
            except Exception as e:
                logger.error(f"Error creating Marked widget in locked view: {str(e)}")
                return Div(
                    Card(f"🔒 {step.show}: <content locked>"),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                )
            
        # Check if step is complete and not reverting
        if user_val and state.get("_revert_target") != step_id:
            # Create the marked widget from the existing content
            try:
                widget_id = f"marked-widget-{pipeline_id.replace('-', '_')}-{step_id}"
                marked_widget = self.create_marked_widget(user_val, widget_id)
                content_container = pip.widget_container(
                    step_id=step_id,
                    app_name=app_name,
                    message=f"{step.show} Configured",
                    widget=marked_widget,
                    steps=steps
                )
                
                # Create response with HTMX trigger
                response = HTMLResponse(
                    to_xml(
                        Div(
                            content_container,
                            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                        )
                    )
                )
                
                # Add HX-Trigger to initialize Marked.js
                response.headers["HX-Trigger"] = json.dumps({
                    "initMarked": {
                        "widgetId": widget_id
                    }
                })
                
                return response
            except Exception as e:
                # If there's an error creating the widget, revert to input form
                logger.error(f"Error creating Marked widget: {str(e)}")
                state["_revert_target"] = step_id
                pip.write_state(pipeline_id, state)
        
        # Show input form
        display_value = user_val if step.refill and user_val else await self.get_suggestion(step_id, state)
        await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
        
        return Div(
            Card(
                H4(f"{pip.fmt(step_id)}: Configure {step.show}"),
                P("Enter markdown content to be rendered. Example is pre-populated."),
                P("The markdown will be rendered with support for headings, lists, bold/italic text, and code blocks.", 
                  style="font-size: 0.8em; font-style: italic;"),
                Form(
                    Div(
                        Textarea(
                            display_value,
                            name=step.done,
                            placeholder="Enter markdown content",
                            required=True,
                            rows=15,
                            style="width: 100%; font-family: monospace;"
                        ),
                        Div(
                            Button("Submit", type="submit", cls="primary"),
                            style="margin-top: 1vh; text-align: right;"
                        ),
                        style="width: 100%;"
                    ),
                    hx_post=f"/{app_name}/{step_id}_submit",
                    hx_target=f"#{step_id}"
                )
            ),
            Div(id=next_step_id),
            id=step_id
        )

    async def step_02_submit(self, request):
        """
        Handle submission of markdown content in Step 2
        
        Takes the user's markdown input, creates a marked.js widget,
        and returns it as part of the response with MarkedJS initialization.
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_02"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get("pipeline_id", "unknown")
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'

        # Get form data
        form = await request.form()
        user_val = form.get(step.done, "")

        # Validate input
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            return error_component

        # Save the value to state
        await pip.update_step_state(pipeline_id, step_id, user_val, steps)
        
        # Generate unique widget ID for this step and pipeline
        widget_id = f"marked-widget-{pipeline_id.replace('-', '_')}-{step_id}"
        
        # Use the helper method to create a marked widget
        marked_widget = self.create_marked_widget(user_val, widget_id)
        
        # Create content container with the marked widget and initialization
        content_container = pip.widget_container(
            step_id=step_id,
            app_name=app_name,
            message=f"{step.show}: Markdown rendered with Marked.js",
            widget=marked_widget,
            steps=steps
        )
        
        # Create full response structure
        response_content = Div(
            content_container,
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
        
        # Create an HTMLResponse with the content
        response = HTMLResponse(to_xml(response_content))
        
        # Add HX-Trigger header to initialize Marked.js
        response.headers["HX-Trigger"] = json.dumps({
            "initMarked": {
                "widgetId": widget_id
            }
        })
        
        # Send confirmation message
        await self.message_queue.add(pip, f"{step.show} complete. Markdown rendered successfully.", verbatim=True)
        
        return response

    # --- Step 3: Mermaid Diagram Renderer ---
    async def step_03(self, request):
        """ Handles GET request for Step 3: Mermaid Diagram Renderer. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_03"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "")
        
        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and user_val:
            # Show the diagram in locked state
            try:
                widget_id = f"mermaid-widget-{pipeline_id.replace('-', '_')}-{step_id}"
                mermaid_widget = self.create_mermaid_widget(user_val, widget_id)
                
                # Create response with locked view
                response = HTMLResponse(
                    to_xml(
                        Div(
                            Card(
                                H4(f"🔒 {step.show}"),
                                mermaid_widget
                            ),
                            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                        )
                    )
                )
                
                # Add HX-Trigger to render the Mermaid diagram
                response.headers["HX-Trigger"] = json.dumps({
                    "renderMermaid": {
                        "targetId": f"{widget_id}_output",
                        "diagram": user_val
                    }
                })
                
                return response
            except Exception as e:
                logger.error(f"Error creating mermaid widget in locked view: {str(e)}")
                return Div(
                    Card(f"🔒 {step.show}: <content locked>"),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                )
            
        # Check if step is complete and not reverting
        if user_val and state.get("_revert_target") != step_id:
            # Create the mermaid diagram widget from the existing content
            try:
                widget_id = f"mermaid-widget-{pipeline_id.replace('-', '_')}-{step_id}"
                mermaid_widget = self.create_mermaid_widget(user_val, widget_id)
                content_container = pip.widget_container(
                    step_id=step_id,
                    app_name=app_name,
                    message=f"{step.show} Configured",
                    widget=mermaid_widget,
                    steps=steps
                )
                
                # Create response with HTMX trigger
                response = HTMLResponse(
                    to_xml(
                        Div(
                            content_container,
                            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                        )
                    )
                )
                
                # Add HX-Trigger to render the Mermaid diagram
                response.headers["HX-Trigger"] = json.dumps({
                    "renderMermaid": {
                        "targetId": f"{widget_id}_output",
                        "diagram": user_val
                    }
                })
                
                return response
            except Exception as e:
                # If there's an error creating the widget, revert to input form
                logger.error(f"Error creating mermaid widget: {str(e)}")
                state["_revert_target"] = step_id
                pip.write_state(pipeline_id, state)
        
        # Show input form
        display_value = user_val if step.refill and user_val else await self.get_suggestion(step_id, state)
        await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
        
        return Div(
            Card(
                H4(f"{pip.fmt(step_id)}: Configure {step.show}"),
                P("Enter Mermaid diagram syntax for the widget. Example is pre-populated."),
                P("Supports flowcharts, sequence diagrams, class diagrams, etc.", 
                  style="font-size: 0.8em; font-style: italic;"),
                Form(
                    Div(
                        Textarea(
                            display_value,
                            name=step.done,
                            placeholder="Enter Mermaid diagram syntax",
                            required=True,
                            rows=15,
                            style="width: 100%; font-family: monospace;"
                        ),
                        Div(
                            Button("Submit", type="submit", cls="primary"),
                            style="margin-top: 1vh; text-align: right;"
                        ),
                        style="width: 100%;"
                    ),
                    hx_post=f"/{app_name}/{step_id}_submit",
                    hx_target=f"#{step_id}"
                )
            ),
            Div(id=next_step_id),
            id=step_id
        )

    async def step_03_submit(self, request):
        """ 
        Process the submission for Step 3.
        
        This method demonstrates client-side widget rendering:
        1. Saves the Mermaid diagram syntax to state
        2. Creates a container with the diagram source
        3. Adds initialization JavaScript that runs when the content is inserted
        4. Uses HX-Trigger header as a backup initialization method
        
        Client-side initialization is particularly challenging in HTMX applications
        due to the timing of DOM updates. The implementation includes:
        - Timeout delay to ensure DOM is fully updated
        - Force repaint to prevent rendering glitches
        - Support for different Mermaid API versions
        - Comprehensive error handling
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_03"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get("pipeline_id", "unknown")
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'

        # Get form data
        form = await request.form()
        user_val = form.get(step.done, "")

        # Validate input
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            return error_component

        # Save the value to state
        await pip.update_step_state(pipeline_id, step_id, user_val, steps)
        
        # Generate unique widget ID for this step and pipeline
        widget_id = f"mermaid-widget-{pipeline_id.replace('-', '_')}-{step_id}"
        
        # Use the helper method to create a mermaid widget
        mermaid_widget = self.create_mermaid_widget(user_val, widget_id)
        
        # Create content container with the mermaid widget and initialization
        content_container = pip.widget_container(
            step_id=step_id,
            app_name=app_name,
            message=f"{step.show}: Client-side Mermaid diagram rendering",
            widget=mermaid_widget,
            steps=steps
        )
        
        # Create full response structure
        response_content = Div(
            content_container,
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
        
        # Create an HTMLResponse with the content
        response = HTMLResponse(to_xml(response_content))
        
        # Add HX-Trigger header to initialize Mermaid rendering
        # This is a backup mechanism in case the inline script doesn't work
        response.headers["HX-Trigger"] = json.dumps({
            "renderMermaid": {
                "targetId": f"{widget_id}_output",
                "diagram": user_val
            }
        })
        
        # Send confirmation message
        await self.message_queue.add(pip, f"{step.show} complete. Mermaid diagram rendered.", verbatim=True)
        
        return response

    # --- Step 4: Pandas Table Widget ---
    async def step_04(self, request):
        """ 
        Handles GET request for Step 4: Pandas Table Widget.
        
        This method follows the same "Combined Step" pattern as step_01.
        Note that when displaying an existing widget, we recreate it from
        the saved data rather than storing the rendered widget itself.
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "")
        
        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and user_val:
            try:
                # Still show the widget but with a locked indicator
                table_widget = self.create_pandas_table(user_val)
                return Div(
                    Card(
                        H4(f"🔒 {step.show}"),
                        table_widget
                    ),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                )
            except Exception as e:
                logger.error(f"Error creating table widget in finalized view: {str(e)}")
                return Div(
                    Card(f"🔒 {step.show}: <content locked>"),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                )
            
        # Check if step is complete and not reverting
        if user_val and state.get("_revert_target") != step_id:
            # Create the table widget from the existing data
            try:
                table_widget = self.create_pandas_table(user_val)
                content_container = pip.widget_container(
                    step_id=step_id,
                    app_name=app_name,
                    message=f"{step.show} Configured",
                    widget=table_widget,
                    steps=steps
                )
                return Div(
                    content_container,
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                )
            except Exception as e:
                # If there's an error creating the widget, revert to input form
                logger.error(f"Error creating table widget: {str(e)}")
                state["_revert_target"] = step_id
                pip.write_state(pipeline_id, state)
        
        # Show input form
        display_value = user_val if step.refill and user_val else await self.get_suggestion(step_id, state)
        await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
        
        return Div(
            Card(
                H4(f"{pip.fmt(step_id)}: Configure {step.show}"),
                P("Enter table data as JSON array of objects. Example is pre-populated."),
                P("Format: [{\"column1\": value1, \"column2\": value2}, {...}, ...]", 
                  style="font-size: 0.8em; font-style: italic;"),
                Form(
                    Div(
                        Textarea(
                            display_value,
                            name=step.done,
                            placeholder="Enter JSON array of objects for the DataFrame",
                            required=True,
                            rows=10,
                            style="width: 100%; font-family: monospace;"
                        ),
                        Div(
                            Button("Submit", type="submit", cls="primary"),
                            style="margin-top: 1vh; text-align: right;"
                        ),
                        style="width: 100%;"
                    ),
                    hx_post=f"/{app_name}/{step_id}_submit",
                    hx_target=f"#{step_id}"
                )
            ),
            Div(id=next_step_id),
            id=step_id
        )

    async def step_04_submit(self, request):
        """ 
        Process the submission for Step 4.
        
        This method demonstrates using pandas to generate an HTML table:
        1. Parses and validates the JSON input
        2. Creates a pandas DataFrame from the data
        3. Generates the HTML table using DataFrame.to_html()
        4. Embeds the raw HTML in a FastHTML component
        
        When using the "Combined Step" pattern with complex widgets, it's
        important to handle errors gracefully to avoid breaking the workflow.
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get("pipeline_id", "unknown")

        # Get form data
        form = await request.form()
        user_val = form.get(step.done, "")

        # Validate input
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            return error_component
            
        # Additional validation for JSON format
        try:
            json_data = json.loads(user_val)
            if not isinstance(json_data, list) or not json_data:
                return P("Invalid JSON: Must be a non-empty array of objects", style=pip.get_style("error"))
            if not all(isinstance(item, dict) for item in json_data):
                return P("Invalid JSON: All items must be objects (dictionaries)", style=pip.get_style("error"))
        except json.JSONDecodeError:
            return P("Invalid JSON format. Please check your syntax.", style=pip.get_style("error"))

        # Save the value to state
        await pip.update_step_state(pipeline_id, step_id, user_val, steps)

        # Create a pandas table from the JSON data
        try:
            data = json.loads(user_val)
            
            # Create a pandas DataFrame
            df = pd.DataFrame(data)
            
            # Generate HTML table with styling
            html_table = df.to_html(
                index=False,            # Don't include DataFrame index
                classes='table',        # Add a CSS class for styling
                border=0,               # Remove default HTML border attribute
                escape=True,            # Keep default HTML escaping for security
                justify='left'          # Align text to left
            )
            
            # Create a styled container for the table with responsive design
            table_container = Div(
                H5("Pandas DataFrame Table:"),
                # Add the HTML table with NotStr to prevent escaping
                Div(
                    NotStr(html_table),
                    style="overflow-x: auto; max-width: 100%;"
                ),
                style="margin-top: 1rem;"
            )
            
            # Send confirmation message
            await self.message_queue.add(pip, f"{step.show} complete. Table rendered successfully.", verbatim=True)
            
            # Create complete response with widget container
            response = HTMLResponse(to_xml(
                Div(
                    pip.widget_container(
                        step_id=step_id,
                        app_name=app_name,
                        message=f"{step.show}: Table rendered from pandas DataFrame",
                        widget=table_container,
                        steps=steps
                    ),
                    Div(id=f"{steps[step_index + 1].id}", hx_get=f"/{app_name}/{steps[step_index + 1].id}", hx_trigger="load"),
                    id=step_id
                )
            ))
            
            return response
            
        except Exception as e:
            logger.error(f"Error creating pandas table: {e}")
            return Div(NotStr(f"<div style='color: red;'>Error creating table: {str(e)}</div>"), _raw=True)

    # --- Step 5: Code Syntax Highlighter ---
    async def step_05(self, request):
        """ Handles GET request for Step 5: Code Syntax Highlighter. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_05"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "")
        
        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and user_val:
            # Show the syntax highlighter in locked state
            try:
                # Check if user specified a language in format: ```language\ncode```
                language = 'javascript'  # Default language
                code_to_display = user_val
                
                if user_val.startswith('```'):
                    # Try to extract language from markdown-style code block
                    first_line = user_val.split('\n', 1)[0].strip()
                    if len(first_line) > 3:
                        detected_lang = first_line[3:].strip()
                        if detected_lang:
                            language = detected_lang
                            # Remove the language specification line from the code
                            code_to_display = user_val.split('\n', 1)[1] if '\n' in user_val else user_val
                    
                    # Remove trailing backticks if present
                    if code_to_display.endswith('```'):
                        code_to_display = code_to_display.rsplit('```', 1)[0]
                
                # Generate unique widget ID for this step and pipeline
                widget_id = f"prism-widget-{pipeline_id.replace('-', '_')}-{step_id}"
                
                # Use the helper method to create a prism widget with detected language
                prism_widget = self.create_prism_widget(code_to_display, widget_id, language)
                
                # Create response with locked view
                response = HTMLResponse(
                    to_xml(
                        Div(
                            Card(
                                H4(f"🔒 {step.show} ({language})"),
                                prism_widget
                            ),
                            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                        )
                    )
                )
                
                # Add HX-Trigger header to initialize Prism highlighting
                response.headers["HX-Trigger"] = json.dumps({
                    "initializePrism": {
                        "targetId": widget_id
                    }
                })
                
                return response
            except Exception as e:
                logger.error(f"Error creating Prism widget in locked view: {str(e)}")
                return Div(
                    Card(f"🔒 {step.show}: <content locked>"),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                )
            
        # Check if step is complete and not reverting
        if user_val and state.get("_revert_target") != step_id:
            # Create the prism widget from the existing code
            try:
                # Check if user specified a language in format: ```language\ncode```
                language = 'javascript'  # Default language
                code_to_display = user_val
                
                if user_val.startswith('```'):
                    # Try to extract language from markdown-style code block
                    first_line = user_val.split('\n', 1)[0].strip()
                    if len(first_line) > 3:
                        detected_lang = first_line[3:].strip()
                        if detected_lang:
                            language = detected_lang
                            # Remove the language specification line from the code
                            code_to_display = user_val.split('\n', 1)[1] if '\n' in user_val else user_val
                    
                    # Remove trailing backticks if present
                    if code_to_display.endswith('```'):
                        code_to_display = code_to_display.rsplit('```', 1)[0]
                
                widget_id = f"prism-widget-{pipeline_id.replace('-', '_')}-{step_id}"
                prism_widget = self.create_prism_widget(code_to_display, widget_id, language)
                content_container = pip.widget_container(
                    step_id=step_id,
                    app_name=app_name,
                    message=f"{step.show}: Syntax highlighting with Prism.js ({language})",
                    widget=prism_widget,
                    steps=steps
                )
                
                response = HTMLResponse(
                    to_xml(
                        Div(
                            content_container,
                            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                        )
                    )
                )
                
                # Add HX-Trigger to initialize Prism highlighting
                response.headers["HX-Trigger"] = json.dumps({
                    "initializePrism": {
                        "targetId": widget_id
                    }
                })
                
                return response
            except Exception as e:
                # If there's an error creating the widget, revert to input form
                logger.error(f"Error creating Prism widget: {str(e)}")
                state["_revert_target"] = step_id
                pip.write_state(pipeline_id, state)
        
        # Show input form
        display_value = user_val if step.refill and user_val else await self.get_suggestion(step_id, state)
        await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
        
        return Div(
            Card(
                H4(f"{pip.fmt(step_id)}: Configure {step.show}"),
                P("Enter code to be highlighted with syntax coloring. JavaScript example is pre-populated."),
                P("The code will be displayed with syntax highlighting and a copy button.", 
                  style="font-size: 0.8em; font-style: italic;"),
                Form(
                    Div(
                        Textarea(
                            display_value,
                            name=step.done,
                            placeholder="Enter code for syntax highlighting",
                            required=True,
                            rows=15,
                            style="width: 100%; font-family: monospace;"
                        ),
                        Div(
                            Button("Submit", type="submit", cls="primary"),
                            style="margin-top: 1vh; text-align: right;"
                        ),
                        style="width: 100%;"
                    ),
                    hx_post=f"/{app_name}/{step_id}_submit",
                    hx_target=f"#{step_id}"
                )
            ),
            Div(id=next_step_id),
            id=step_id
        )

    async def step_05_submit(self, request):
        """ Process the submission for Step 5. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_05"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get("pipeline_id", "unknown")
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'

        # Get form data
        form = await request.form()
        user_val = form.get(step.done, "")

        # Check if user specified a language in format: ```language\ncode```
        language = 'javascript'  # Default language
        if user_val.startswith('```'):
            # Try to extract language from markdown-style code block
            first_line = user_val.split('\n', 1)[0].strip()
            if len(first_line) > 3:
                detected_lang = first_line[3:].strip()
                if detected_lang:
                    language = detected_lang
                    # Remove the language specification line from the code
                    user_val = user_val.split('\n', 1)[1] if '\n' in user_val else user_val
            
            # Remove trailing backticks if present
            if user_val.endswith('```'):
                user_val = user_val.rsplit('```', 1)[0]

        # Validate input
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            return error_component

        # Save the value to state
        await pip.update_step_state(pipeline_id, step_id, user_val, steps)
        
        # Generate unique widget ID for this step and pipeline
        widget_id = f"prism-widget-{pipeline_id.replace('-', '_')}-{step_id}"
        
        # Use the helper method to create a prism widget with detected language
        prism_widget = self.create_prism_widget(user_val, widget_id, language)
        
        # Create content container with the prism widget and initialization
        content_container = pip.widget_container(
            step_id=step_id,
            app_name=app_name,
            message=f"{step.show}: Syntax highlighting with Prism.js ({language})",
            widget=prism_widget,
            steps=steps
        )
        
        # Create full response structure
        response_content = Div(
            content_container,
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
        
        # Create an HTMLResponse with the content
        response = HTMLResponse(to_xml(response_content))
        
        # Add HX-Trigger header to initialize Prism highlighting
        response.headers["HX-Trigger"] = json.dumps({
            "initializePrism": {
                "targetId": widget_id
            }
        })
        
        # Send confirmation message
        await self.message_queue.add(pip, f"{step.show} complete. Code syntax highlighted with {language}.", verbatim=True)
        
        return response

    # --- Step 6: JavaScript Execution Widget ---
    async def step_06(self, request):
        """ Handles GET request for Step 6: JavaScript Widget. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_06"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "")
        
        # Check if workflow is finalized
        finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data and user_val:
            # Show the widget in locked state
            try:
                widget_id = f"js-widget-{pipeline_id}-{step_id}".replace("-", "_")
                target_id = f"{widget_id}_target"
                
                # Create a JavaScript widget for locked view with re-run button
                js_widget = Div(
                    # Container that will be manipulated by the JS code
                    P(
                        "JavaScript will execute here...", 
                        id=target_id, 
                        style="padding: 1.5rem; background-color: var(--pico-card-background-color); border-radius: var(--pico-border-radius); min-height: 100px;"
                    ),
                    # Keep the Re-run button even in locked state
                    Button(
                        "Re-run JavaScript", 
                        type="button", 
                        _onclick=f"runJsWidget('{widget_id}', `{user_val.replace('`', '\\`')}`, '{target_id}')",
                        style="margin-top: 1rem; background-color: #9370DB; border-color: #9370DB;"
                    ),
                    id=widget_id
                )
                
                # Create response with content in locked view
                response = HTMLResponse(
                    to_xml(
                        Div(
                            Card(
                                H4(f"🔒 {step.show}"),
                                js_widget
                            ),
                            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                        )
                    )
                )
                
                # Add HX-Trigger header to execute the JS code, even in locked state
                response.headers["HX-Trigger"] = json.dumps({
                    "runJavaScript": {
                        "widgetId": widget_id,
                        "code": user_val,
                        "targetId": target_id
                    }
                })
                
                return response
            except Exception as e:
                logger.error(f"Error creating JS widget in locked view: {str(e)}")
                return Div(
                    Card(f"🔒 {step.show}: <content locked>"),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                )
            
        # Check if step is complete and not reverting
        if user_val and state.get("_revert_target") != step_id:
            # Create the JS widget from the existing code
            try:
                widget_id = f"js-widget-{pipeline_id}-{step_id}".replace("-", "_")
                target_id = f"{widget_id}_target"
                
                # Create a simple container with just the target element and re-run button
                js_widget = Div(
                    # Container that will be manipulated by the JS code
                    P(
                        "JavaScript will execute here...", 
                        id=target_id, 
                        style="padding: 1.5rem; background-color: var(--pico-card-background-color); border-radius: var(--pico-border-radius); min-height: 100px;"
                    ),
                    # Button to re-run the JavaScript
                    Button(
                        "Re-run JavaScript", 
                        type="button", 
                        _onclick=f"runJsWidget('{widget_id}', `{user_val.replace('`', '\\`')}`, '{target_id}')",
                        style="margin-top: 1rem; background-color: #9370DB; border-color: #9370DB;"
                    ),
                    id=widget_id
                )
                
                # Create content container with the widget
                content_container = pip.widget_container(
                    step_id=step_id,
                    app_name=app_name,
                    message=f"{step.show} Configured",
                    widget=js_widget,
                    steps=steps
                )
                
                # Create response with HX-Trigger
                response = HTMLResponse(
                    to_xml(
                        Div(
                            content_container,
                            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                        )
                    )
                )
                
                # Add HX-Trigger header to execute the JS code
                response.headers["HX-Trigger"] = json.dumps({
                    "runJavaScript": {
                        "widgetId": widget_id,
                        "code": user_val,
                        "targetId": target_id
                    }
                })
                
                return response
                
            except Exception as e:
                # If there's an error creating the widget, revert to input form
                logger.error(f"Error creating JS widget: {str(e)}")
                state["_revert_target"] = step_id
                pip.write_state(pipeline_id, state)
        
        # Show input form
        display_value = user_val if step.refill and user_val else await self.get_suggestion(step_id, state)
        await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
        
        return Div(
            Card(
                H4(f"{pip.fmt(step_id)}: Configure {step.show}"),
                P("Enter JavaScript code for the widget. Example is pre-populated."),
                P("Use the 'widget' variable to access the container element.", 
                  style="font-size: 0.8em; font-style: italic;"),
                Form(
                    Div(
                        Textarea(
                            display_value,
                            name=step.done,
                            placeholder="Enter JavaScript code",
                            required=True,
                            rows=12,
                            style="width: 100%; font-family: monospace;"
                        ),
                        Div(
                            Button("Submit", type="submit", cls="primary"),
                            style="margin-top: 1vh; text-align: right;"
                        ),
                        style="width: 100%;"
                    ),
                    hx_post=f"/{app_name}/{step_id}_submit",
                    hx_target=f"#{step_id}"
                )
            ),
            Div(id=next_step_id),
            id=step_id
        )

    async def step_06_submit(self, request):
        """ Process the submission for Step 6. """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_06"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get("pipeline_id", "unknown")
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'

        # Get form data
        form = await request.form()
        user_val = form.get(step.done, "")

        # Validate input
        is_valid, error_msg, error_component = pip.validate_step_input(user_val, step.show)
        if not is_valid:
            return error_component

        # Save the value to state
        await pip.update_step_state(pipeline_id, step_id, user_val, steps)
        
        # Generate unique widget ID for this step and pipeline
        widget_id = f"js-widget-{pipeline_id}-{step_id}".replace("-", "_")
        target_id = f"{widget_id}_target"
        
        # Create a simple container with just the target element and re-run button
        js_widget = Div(
            # Container that will be manipulated by the JS code
            P(
                "JavaScript will execute here...", 
                id=target_id, 
                style="padding: 1.5rem; background-color: var(--pico-card-background-color); border-radius: var(--pico-border-radius); min-height: 100px;"
            ),
            # Button to re-run the JavaScript
            Button(
                "Re-run JavaScript", 
                type="button", 
                _onclick=f"runJsWidget('{widget_id}', `{user_val.replace('`', '\\`')}`, '{target_id}')",
                style="margin-top: 1rem; background-color: #9370DB; border-color: #9370DB;"
            ),
            id=widget_id
        )
        
        # Create content container with the widget
        content_container = pip.widget_container(
            step_id=step_id,
            app_name=app_name,
            message=f"{step.show}: Interactive JavaScript example",
            widget=js_widget,
            steps=steps
        )
        
        # Create full response structure
        response_content = Div(
            content_container,
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
        
        # Create an HTMLResponse with the content
        response = HTMLResponse(to_xml(response_content))
        
        # Add HX-Trigger header to execute the JS code
        response.headers["HX-Trigger"] = json.dumps({
            "runJavaScript": {
                "widgetId": widget_id,
                "code": user_val,
                "targetId": target_id
            }
        })
        
        # Send confirmation message
        await self.message_queue.add(pip, f"{step.show} complete. JavaScript executed.", verbatim=True)
        
        return response
    
    def create_marked_widget(self, markdown_content, widget_id):
        """
        Create a widget for rendering markdown content using marked.js
        
        Args:
            markdown_content: The markdown text to render
            widget_id: Unique ID for the widget
            
        Returns:
            Div element containing the widget
        """
        # Create a container for the markdown content
        widget = Div(
            # Hidden div containing the raw markdown content
            Div(
                markdown_content,
                id=f"{widget_id}_source",
                style="display: none;"
            ),
            # Container where the rendered HTML will be inserted
            Div(
                id=f"{widget_id}_rendered",
                cls="markdown-body p-3 border rounded bg-light"
            ),
            # JavaScript to initialize marked.js rendering
            Script(f"""
                document.addEventListener('htmx:afterOnLoad', function() {{
                    // Function to render markdown
                    function renderMarkdown() {{
                        const source = document.getElementById('{widget_id}_source');
                        const target = document.getElementById('{widget_id}_rendered');
                        if (source && target) {{
                            // Use marked.js to convert markdown to HTML
                            const html = marked.parse(source.textContent);
                            target.innerHTML = html;
                            // Apply syntax highlighting to code blocks if Prism is available
                            if (typeof Prism !== 'undefined') {{
                                Prism.highlightAllUnder(target);
                            }}
                        }}
                    }}
                    
                    // Check if marked.js is loaded
                    if (typeof marked !== 'undefined') {{
                        renderMarkdown();
                    }} else {{
                        console.error('marked.js is not loaded');
                    }}
                }});
                
                // Also listen for custom event from HX-Trigger
                document.addEventListener('initMarked', function(event) {{
                    if (event.detail.widgetId === '{widget_id}') {{
                        setTimeout(function() {{
                            const source = document.getElementById('{widget_id}_source');
                            const target = document.getElementById('{widget_id}_rendered');
                            if (source && target && typeof marked !== 'undefined') {{
                                const html = marked.parse(source.textContent);
                                target.innerHTML = html;
                                // Apply syntax highlighting to code blocks if Prism is available
                                if (typeof Prism !== 'undefined') {{
                                    Prism.highlightAllUnder(target);
                                }}
                            }}
                        }}, 100);
                    }}
                }});
            """),
            cls="marked-widget"
        )
        
        return widget

    # --- Helper Methods (Widget Creation) ---
    
    def create_pandas_table(self, data_str):
        """
        Create a pandas HTML table from JSON string data.
        
        This helper method encapsulates the widget creation logic, which:
        1. Makes the code more maintainable
        2. Allows reuse in both step_02 and step_02_submit
        3. Centralizes error handling
        
        When implementing complex widgets, consider using helper methods
        like this to separate widget creation logic from workflow logic.
        
        Note on FastHTML raw HTML handling:
        - Uses Div(NotStr(html_fragment), _raw=True) to embed raw HTML
        - NotStr prevents string escaping during XML rendering
        - _raw=True flag informs the component to accept unprocessed HTML
        """
        try:
            # Try parsing the JSON data
            data = json.loads(data_str)
            
            # Create a pandas DataFrame
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                # Data is a list of dictionaries (most common format)
                df = pd.DataFrame(data)
            elif isinstance(data, list) and all(isinstance(item, list) for item in data):
                # Data is a list of lists, with first row as headers
                headers = data[0]
                rows = data[1:]
                df = pd.DataFrame(rows, columns=headers)
            else:
                return Div(NotStr("<div style='color: red;'>Unsupported data format. Please provide a list of objects.</div>"), _raw=True)
            
            # Generate HTML table with styling
            html_table = df.to_html(
                index=False,            # Don't include DataFrame index
                classes='table',        # Add a CSS class for styling
                border=0,               # Remove default HTML border attribute
                escape=True,            # Keep default HTML escaping for security
                justify='left'          # Align text to left
            )
            
            # Create a styled container for the table with responsive design
            table_container = Div(
                H5("Pandas DataFrame Table:"),
                # Add the HTML table with NotStr to prevent escaping
                Div(
                    NotStr(html_table),
                    style="overflow-x: auto; max-width: 100%;"
                ),
                style="margin-top: 1rem;"
            )
            
            return table_container
            
        except Exception as e:
            logger.error(f"Error creating pandas table: {e}")
            return Div(NotStr(f"<div style='color: red;'>Error creating table: {str(e)}</div>"), _raw=True)

    def create_mermaid_widget(self, diagram_syntax, widget_id):
        """Create a mermaid diagram widget container."""
        # Create container for the widget
        container = Div(
            Div(
                # Container to render the mermaid diagram
                H5("Rendered Diagram:"),
                Div(
                    # This div with class="mermaid" will be targeted by the mermaid.js library
                    Div(
                        diagram_syntax,
                        cls="mermaid",
                        style="width: 100%; background-color: var(--pico-card-background-color); border-radius: var(--pico-border-radius); padding: 1rem;"
                    ),
                    id=f"{widget_id}_output"
                )
            ),
            id=widget_id
        )
        
        # Create a script to initialize and run mermaid on this container
        init_script = Script(
            f"""
            (function() {{
                // Give the DOM time to fully render before initializing Mermaid
                setTimeout(function() {{
                    // Initialize mermaid
                    if (typeof mermaid !== 'undefined') {{
                        try {{
                            mermaid.initialize({{ 
                                startOnLoad: false,  // Important - don't auto-init
                                theme: 'dark',       // Use dark theme for better visibility
                                securityLevel: 'loose',
                                flowchart: {{
                                    htmlLabels: true
                                }}
                            }});
                            
                            // Find all mermaid divs in this widget and render them
                            const container = document.getElementById('{widget_id}');
                            if (!container) return;
                            
                            const mermaidDiv = container.querySelector('.mermaid');
                            if (mermaidDiv) {{
                                // Force a repaint before initializing
                                void container.offsetWidth;
                                
                                // Render the diagram
                                if (typeof mermaid.run === 'function') {{
                                    // Newer Mermaid API
                                    mermaid.run({{ nodes: [mermaidDiv] }});
                                }} else {{
                                    // Older Mermaid API
                                    mermaid.init(undefined, mermaidDiv);
                                }}
                                console.log('Mermaid rendering successful');
                            }}
                        }} catch(e) {{
                            console.error("Mermaid rendering error:", e);
                        }}
                    }} else {{
                        console.error("Mermaid library not found. Make sure it's included in the page headers.");
                    }}
                }}, 300); // 300ms delay to ensure DOM is ready
            }})();
            """,
            type="text/javascript"
        )
        
        return Div(container, init_script)

    def create_prism_widget(self, code, widget_id, language='javascript'):
        """Create a Prism.js syntax highlighting widget with copy functionality.
        
        Args:
            code (str): The code to highlight
            widget_id (str): Unique ID for the widget
            language (str): The programming language for syntax highlighting (default: javascript)
        """
        # Generate a unique ID for the hidden textarea
        textarea_id = f"{widget_id}_raw_code"
        
        # Create container for the widget
        container = Div(
            Div(
                H5("Syntax Highlighted Code:"),
                # Add a hidden textarea to hold the raw code (much safer than trying to escape it for JS)
                Textarea(
                    code,
                    id=textarea_id,
                    style="display: none;"  # Hide the textarea
                ),
                # Add a simple copy button that reads from the hidden textarea
                Button(
                    "Copy Code", 
                    type="button",
                    _onclick=f"""
                        (function() {{
                            const textarea = document.getElementById('{textarea_id}');
                            navigator.clipboard.writeText(textarea.value)
                                .then(() => {{
                                    this.textContent = 'Copied!';
                                    setTimeout(() => this.textContent = 'Copy Code', 2000);
                                }})
                                .catch(err => {{
                                    console.error('Failed to copy:', err);
                                    this.textContent = 'Error';
                                    setTimeout(() => this.textContent = 'Copy Code', 2000);
                                }});
                        }})();
                    """,
                    style="margin-bottom: 10px; background-color: #9370DB; border-color: #9370DB;"
                ),
                # This pre/code structure is required for Prism.js
                Pre(
                    Code(
                        code,
                        cls=f"language-{language}"  # Language class for Prism
                    ),
                    cls="line-numbers"  # Enable line numbers
                ),
                style="margin-top: 1rem;"
            ),
            id=widget_id
        )
        
        # Create script to initialize Prism with debugging
        init_script = Script(
            f"""
            (function() {{
                console.log('Prism widget loaded, ID: {widget_id}');
                // Check if Prism is loaded
                if (typeof Prism === 'undefined') {{
                    console.error('Prism library not found');
                    return;
                }}
                
                // Attempt to manually trigger highlighting
                setTimeout(function() {{
                    try {{
                        console.log('Manually triggering Prism highlighting for {widget_id}');
                        Prism.highlightAllUnder(document.getElementById('{widget_id}'));
                    }} catch(e) {{
                        console.error('Error during manual Prism highlighting:', e);
                    }}
                }}, 300);
            }})();
            """,
            type="text/javascript"
        )
        
        return Div(container, init_script) 
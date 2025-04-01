import asyncio
from collections import namedtuple
from datetime import datetime
import os

from fasthtml.common import *
from loguru import logger

"""
Acquire a Botify API Key

This is the simplest possible workflow, not even having a step.
It only has a landing page and a finalize button. 
Landing page asks for a Botify API Key.
Finalize button does nothing.

"""

# This is the model for a Notebook cell or step (do not change)
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class BotifyConnect:  # <-- CHANGE THIS to your new WorkFlow name
    APP_NAME = "botify"  # <-- CHANGE THIS to something no other workflow is using
    DISPLAY_NAME = "Connect With Botify"  # <-- CHANGE THIS to value for User Interface
    ENDPOINT_MESSAGE = (  # <-- Shows when user switches to workflow landing page
        "Enter your Botify API token to connect with Botify. "
        "You can find your API token at https://app.botify.com/account"
    )
    TRAINING_PROMPT = "botify_workflow.md"  # markdown file from /training or plain text
    PRESERVE_REFILL = True  # <-- Whether to preserve refill values on revert

    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
        """
        Initialize the workflow.
        """
        self.app = app
        self.app_name = app_name
        self.pipulate = pipulate
        self.pipeline = pipeline
        self.steps_indices = {}
        self.db = db
        pip = self.pipulate
        
        # Customize the steps, it's like one step per cell in the Notebook
        steps = [
            # No steps for this workflow - just finalize
        ]

        # Defines routes for standard workflow method (do not change)
        routes = [
            (f"/{app_name}", self.landing),
            (f"/{app_name}/init", self.init, ["POST"]),
            (f"/{app_name}/jump_to_step", self.jump_to_step, ["POST"]),
            (f"/{app_name}/revert", self.handle_revert, ["POST"]),
            (f"/{app_name}/finalize", self.finalize, ["GET", "POST"]),
            (f"/{app_name}/unfinalize", self.unfinalize, ["POST"]),
        ]

        # Defines routes for each custom step (do not change)
        self.steps = steps
        for step in steps:
            step_id = step.id
            routes.append((f"/{app_name}/{step_id}", getattr(self, step_id)))
            routes.append((f"/{app_name}/{step_id}_submit", getattr(self, f"{step_id}_submit"), ["POST"]))

        # Register the routes (do not change)
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ["GET"]
            app.route(path, methods=method_list)(handler)

        # Define messages for finalize (you can change these)
        self.step_messages = {
            "finalize": {
                "ready": "Ready to save your Botify API token.",
                "complete": "Botify API token saved. Use Unfinalize to make changes."
            }
        }

        # Creates a default message for each step (you can change these)
        for step in steps:
            self.step_messages[step.id] = {
                "input": f"{pip.fmt(step.id)}: Please enter {step.show}.",
                "complete": f"{step.show} complete. Continue to next step."
            }

        # Add a finalize step to the workflow (do not change)
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

    async def landing(self):
        """
        This is the landing page for the workflow. It asks for a unique identifier.
        It is necessary for the workflow to function. Only change cosmetic elements.
        """
        pip, pipeline, steps, app_name = self.pipulate, self.pipeline, self.steps, self.app_name
        title = f"{self.DISPLAY_NAME or app_name.title()}"
        pipeline.xtra(app_name=app_name)
        existing_ids = [record.pkey for record in pipeline()]
        
        # Use the same method for consistency
        endpoint_message = self.get_endpoint_message()
            
        return Container(  # Get used to this return signature of FastHTML & HTMX
            Card(
                H2(title),
                P(endpoint_message),
                Form(
                    pip.wrap_with_inline_button(
                        Input(
                            placeholder="Paste your Botify API token here",  # You can change this placeholder
                            name="pipeline_id",
                            list="pipeline-ids",
                            type="text",
                            required=True,
                            autofocus=True,
                        ),
                        button_label="Connect to Botify API",  # You can change this button label
                        button_class="secondary"
                    ),
                    Datalist(*[Option(value=pid) for pid in existing_ids], id="pipeline-ids"),
                    hx_post=f"/{app_name}/init",
                    hx_target=f"#{app_name}-container"
                )
            ),
            Div(id=f"{app_name}-container")
        )

    async def init(self, request):
        """
        Process the landing page form submission.
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        pipeline_id = form.get("pipeline_id")
        if not pipeline_id:
            return await self.landing()
        db["pipeline_id"] = pipeline_id
        state, error = pip.initialize_if_missing(pipeline_id, {"app_name": app_name})
        if error:
            return error
        message = "API token received. Ready to finalize."
        await pip.stream(message, verbatim=True)
        cells = self.run_all_cells(steps, app_name)
        return Div(*cells, id=f"{app_name}-container")

    # Required methods for the workflow system, even if we don't have steps
    
    async def finalize(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "")
        finalize_step = steps[-1]
        finalize_data = pip.get_step_data(pipeline_id, finalize_step.id, {})
        logger.debug(f"Pipeline ID: {pipeline_id}")
        logger.debug(f"Finalize step: {finalize_step}")
        logger.debug(f"Finalize data: {finalize_data}")

        if request.method == "GET":
            if finalize_step.done in finalize_data:
                logger.debug("Pipeline is already finalized")
                return Card(
                    H3("Connection Complete"),
                    P("Botify API token is saved. Use Unfinalize to make changes."),
                    Form(
                        Button("Unfinalize", type="submit", style=pip.get_style("warning_button")),
                        hx_post=f"/{app_name}/unfinalize",
                        hx_target=f"#{app_name}-container",
                        hx_swap="outerHTML"
                    ),
                    id=finalize_step.id
                )

            # No other steps to check since we don't have any
            return Card(
                H3("Ready to finalize?"),
                P("Save your Botify API token?"),
                Form(
                    Button("Finalize", type="submit", style=pip.get_style("primary_button")),
                    hx_post=f"/{app_name}/finalize",
                    hx_target=f"#{app_name}-container",
                    hx_swap="outerHTML"
                ),
                id=finalize_step.id
            )
        else:
            # This is the POST request when they press the Finalize button
            state = pip.read_state(pipeline_id)
            state["finalize"] = {"finalized": True}
            state["updated"] = datetime.now().isoformat()
            pip.write_state(pipeline_id, state)

            # Write the token to a file in the current working directory
            try:
                with open("botify_token.txt", "w") as token_file:
                    token_file.write(pipeline_id)
                await pip.stream("Botify API token saved to botify_token.txt", verbatim=True)
            except Exception as e:
                await pip.stream(f"Error saving token to file: {type(e).__name__}", verbatim=True)

            # Return the updated UI
            return Div(*self.run_all_cells(steps, app_name), id=f"{app_name}-container")

    async def unfinalize(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        if "finalize" in state:
            del state["finalize"]
        pip.write_state(pipeline_id, state)

        # Delete the token file if it exists
        try:
            token_path = "botify_token.txt"
            if os.path.exists(token_path):
                os.remove(token_path)
                await pip.stream("Botify API token file has been deleted.", verbatim=True)
            else:
                await pip.stream("No Botify API token file found to delete.", verbatim=True)
        except Exception as e:
            await pip.stream(f"Error deleting token file: {type(e).__name__}", verbatim=True)

        # Send a message informing them they can revert to any step
        await pip.stream("Connection unfinalized. You can now update your Botify API token.", verbatim=True)

        cells = self.run_all_cells(steps, app_name)
        return Div(*cells, id=f"{app_name}-container")

    def run_all_cells(self, steps, app_name):
        """
        Starts HTMX chain reaction of all steps up to current.
        Equivalent to Running all Cells in a Jupyter Notebook.
        """
        cells = []
        for i, step in enumerate(steps):
            trigger = ("load" if i == 0 else f"stepComplete-{steps[i - 1].id} from:{steps[i - 1].id}")
            cells.append(
                Div(
                    id=step.id,
                    hx_get=f"/{app_name}/{step.id}",
                    hx_trigger=trigger,
                    hx_swap="outerHTML"
                )
            )
        return cells

    async def jump_to_step(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        db["step_id"] = step_id
        return pip.rebuild(app_name, steps)

    async def get_suggestion(self, step_id, state):
        pip, db, steps = self.pipulate, self.db, self.steps
        # If a transform function exists, use the previous step's output.
        step = next((s for s in steps if s.id == step_id), None)
        if not step or not step.transform:
            return ""
        prev_index = self.steps_indices[step_id] - 1
        if prev_index < 0:
            return ""
        prev_step_id = steps[prev_index].id
        prev_step = steps[prev_index]
        prev_data = pip.get_step_data(db["pipeline_id"], prev_step_id, {})
        prev_word = prev_data.get(prev_step.done, "")
        return step.transform(prev_word) if prev_word else ""

    async def handle_revert(self, request):
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        pipeline_id = db.get("pipeline_id", "unknown")
        if not step_id:
            return P("Error: No step specified", style=pip.get_style("error"))
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        state = pip.read_state(pipeline_id)
        state["_revert_target"] = step_id
        pip.write_state(pipeline_id, state)
        message = "Reverting to update your Botify API token."
        await pip.stream(message, verbatim=True)
        cells = self.run_all_cells(steps, app_name)
        return Div(*cells, id=f"{app_name}-container")

    def get_endpoint_message(self):
        """
        Dynamically determine the endpoint message based on token file existence.
        This is called by the server when displaying the message in the sidebar.
        """
        try:
            token_path = "botify_token.txt"
            if os.path.exists(token_path):
                with open(token_path, "r") as f:
                    token = f.read().strip()
                    if token:
                        return (
                            "You already have a Botify API token configured. "
                            "You can update it by entering a new token below. "
                            "You can find your API token at https://app.botify.com/account"
                        )
        except Exception:
            pass
            
        return self.ENDPOINT_MESSAGE

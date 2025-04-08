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

account_url = "https://app.botify.com/account"


class BotifyConnect:  # <-- CHANGE THIS to your new WorkFlow name
    APP_NAME = "botify"  # <-- CHANGE THIS to something no other workflow is using
    DISPLAY_NAME = "Connect With Botify"  # <-- CHANGE THIS to value for User Interface
    ENDPOINT_MESSAGE = (  # <-- Shows when user switches to workflow landing page
        "Enter your Botify API token to connect with Botify. "
        f"You can find your API token at {account_url}"
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
        # Use message queue from Pipulate for ordered message streaming
        self.message_queue = pip.message_queue
        
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
                "complete": f"Botify API token saved. Use {pip.UNLOCK_BUTTON_LABEL} to make changes."
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

    def get_endpoint_message(self):
        """
        Dynamically determine the endpoint message based on token file existence.
        
        This method checks if a Botify token file exists and returns an appropriate
        message for the user. It's called by the server when displaying the message
        in the sidebar.
        
        Returns:
            str: A message indicating whether a token exists and how to proceed
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
                            f"You can find your API token at {account_url}"
                        )
        except Exception:
            pass
            
        return self.ENDPOINT_MESSAGE

    async def landing(self):
        """
        This is the landing page for the workflow. It asks for a unique identifier.
        It is necessary for the workflow to function. Only change cosmetic elements.
        """
        pip, pipeline, steps, app_name = self.pipulate, self.pipeline, self.steps, self.app_name
        title = f"{self.DISPLAY_NAME or app_name.title()}"
        pipeline.xtra(app_name=app_name)
        existing_ids = [record.pkey for record in pipeline()]
        
        # Get the message text
        message_text = self.get_endpoint_message()
        
        # For the workflow UI, we can use FastHTML to create actual HTML elements
        # Create a fragment with the text and a link
        if "You can find your API token at" in message_text:
            parts = message_text.split("You can find your API token at")
            endpoint_message = P(
                parts[0] + "You can find your API token at ",
                A(account_url, href=account_url, target="_blank")
            )
        else:
            endpoint_message = P(message_text)
            
        return Container(  # Get used to this return signature of FastHTML & HTMX
            Card(
                H2(title),
                endpoint_message,
                Form(
                    pip.wrap_with_inline_button(
                        Input(
                            placeholder="Paste your Botify API token here",
                            name="pipeline_id",
                            list="pipeline-ids",
                            type="password",
                            required=True,
                            autofocus=True,
                        ),
                        button_label="Connect to Botify API",
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
        Process the landing page form submission and initialize the workflow.
        
        This method validates the Botify API token, initializes the pipeline state,
        and returns the UI with placeholders for the workflow steps. It handles
        token validation and provides appropriate feedback through the UI.
        
        Args:
            request: The HTTP request object
            
        Returns:
            FastHTML components representing the workflow UI
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
            
        # Always clear any existing "finalize" state when a new token is entered
        # This ensures we start with a clean slate and the proper Finalize button shows
        state = pip.read_state(pipeline_id)
        if "finalize" in state:
            del state["finalize"]
            state["updated"] = datetime.now().isoformat()
            pip.write_state(pipeline_id, state)
            logger.debug(f"Cleared finalize state for pipeline: {pipeline_id}")
        
        # Validate the token immediately after submission
        try:
            username = await self.validate_botify_token(pipeline_id)
            if username:
                # Make chat messages non-blocking
                await self.safe_stream(
                    f"Botify API token validated for user: {username}. Ready to finalize.", 
                    verbatim=True,
                    spaces_after=0  # Set to 0 to remove the extra line break
                )
                
                # Have the LLM greet the user with a short message - non-blocking
                formatted_username = pip.fmt(username)
                await self.safe_stream(
                    f"Greet {formatted_username} briefly as their Botify assistant and tell them to click Finalize to save their token. Keep your response under 40 words.",
                    verbatim=False,
                    role="system"
                )
            else:
                await self.safe_stream("⚠️ Invalid Botify API token. The finalize button won't work and the token won't be saved until it's valid.", verbatim=True)
        except Exception as e:
            await self.safe_stream(f"⚠️ Error validating token: {type(e).__name__}. Please check your token before finalizing.", verbatim=True)
        
        # Get placeholders for all steps
        placeholders = pip.run_all_cells(app_name, steps)
        return Div(*placeholders, id=f"{app_name}-container")

    # Required methods for the workflow system, even if we don't have steps
    
    async def finalize(self, request):
        """
        Finalize the workflow, saving the Botify API token.
        
        This method handles both GET requests (displaying finalization UI) and 
        POST requests (performing the actual finalization). The UI portions
        are intentionally kept WET to allow for full customization of the user
        experience, while core state management is handled by DRY helper methods.
        
        Customization Points:
        - GET response: The cards/UI shown before finalization
        - Token validation and storage logic
        - Confirmation message: What the user sees after token is saved
        
        Args:
            request: The HTTP request object
            
        Returns:
            UI components for either the finalization prompt or confirmation
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "")
        finalize_step = steps[-1]
        finalize_data = pip.get_step_data(pipeline_id, finalize_step.id, {})
        logger.debug(f"Pipeline ID: {pipeline_id}")
        logger.debug(f"Finalize step: {finalize_step}")
        logger.debug(f"Finalize data: {finalize_data}")

        # ───────── GET REQUEST: FINALIZATION UI (INTENTIONALLY WET) ─────────
        if request.method == "GET":
            if finalize_step.done in finalize_data:
                logger.debug("Pipeline is already finalized")
                return Card(
                    H3("Connection Complete"),
                    P(f"Botify API token is saved. Use {pip.UNLOCK_BUTTON_LABEL} to make changes."),
                    Form(
                        Button(
                            pip.UNLOCK_BUTTON_LABEL, 
                            type="submit", 
                            cls="secondary outline"  # PicoCSS secondary outline style - more subtle
                        ),
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
                    Button("Finalize", type="submit", cls="primary"),  # PicoCSS primary style
                    hx_post=f"/{app_name}/finalize",
                    hx_target=f"#{app_name}-container",
                    hx_swap="outerHTML"
                ),
                id=finalize_step.id
            )
        # ───────── END GET REQUEST ─────────
        else:
            # ───────── POST REQUEST: PERFORM FINALIZATION ─────────
            # First validate the token
            username = await self.validate_botify_token(pipeline_id)
            
            # If token is invalid, just update state and return to unfinalized state
            if not username:
                # Send message about invalid token
                await self.safe_stream("⚠️ Invalid Botify API token! Cannot finalize.", verbatim=True)
                
                # Make sure we're not finalized
                state = pip.read_state(pipeline_id)
                if "finalize" in state:
                    del state["finalize"]
                    state["updated"] = datetime.now().isoformat()
                    pip.write_state(pipeline_id, state)
                
                # Just rebuild the workflow, which will now show the unfinalized state
                return pip.rebuild(app_name, steps)
            
            # Token is valid, proceed with finalization
            # Update state using DRY helper
            state = pip.read_state(pipeline_id)
            state["finalize"] = {"finalized": True}
            state["updated"] = datetime.now().isoformat()
            pip.write_state(pipeline_id, state)

            # ───────── CUSTOM FINALIZATION UI (INTENTIONALLY WET) ─────────
            # Write the token to a file in the current working directory
            try:
                # Save token with a comment containing the username
                with open("botify_token.txt", "w") as token_file:
                    token_file.write(f"{pipeline_id}\n# username: {username}")
                    
                await self.safe_stream(f"Botify API token saved to botify_token.txt for user: {username}", verbatim=True, spaces_after=0)
                
                # Add the system prompt to inform users about Botify workflows
                await self.safe_stream(
                    "Tell the user they can now use any workflows requiring Botify API integration. Keep it short and helpful.",
                    verbatim=False,
                    role="system"
                )
            except Exception as e:
                await self.safe_stream(f"Error saving token file: {type(e).__name__}.", verbatim=True)

            # Return the updated UI
            return pip.rebuild(app_name, steps)
            # ───────── END CUSTOM FINALIZATION UI ─────────

    async def validate_botify_token(self, token):
        """
        Check if the Botify API token is valid and return the username if successful.
        
        This method makes an API request to the Botify authentication endpoint
        to validate the provided token and retrieve the associated username.
        
        Args:
            token: The Botify API token to validate
            
        Returns:
            str or None: The username if token is valid, None otherwise
        """
        import httpx
        
        url = "https://api.botify.com/v1/authentication/profile"
        headers = {"Authorization": f"Token {token}"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                # Extract username if the token is valid
                user_data = response.json()
                username = user_data["data"]["username"]
                return username
        except httpx.HTTPStatusError as e:
            logger.error(f"Authentication failed: {e}")
            return None
        except Exception as e:
            logger.error(f"API request error: {e}")
            return None

    async def unfinalize(self, request):
        """
        Unfinalize the workflow, allowing the Botify API token to be changed.
        
        This method removes the finalization flag from the workflow state,
        deletes the Botify API token file, and displays a confirmation message 
        to the user. The UI generation is intentionally kept WET for 
        customization.
        
        Customization Points:
        - Token file deletion logic
        - Confirmation message: What the user sees after unfinalizing
        
        Args:
            request: The HTTP request object
            
        Returns:
            UI components showing the workflow is unlocked
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Update state using DRY helper
        state = pip.read_state(pipeline_id)
        if "finalize" in state:
            del state["finalize"]
        pip.write_state(pipeline_id, state)

        # ───────── CUSTOM UNFINALIZATION UI (INTENTIONALLY WET) ─────────
        # Delete the token file if it exists
        try:
            token_path = "botify_token.txt"
            if os.path.exists(token_path):
                os.remove(token_path)
                await self.safe_stream("Botify API token file has been deleted.", verbatim=True)
            else:
                await self.safe_stream("No Botify API token file found to delete.", verbatim=True)
        except Exception as e:
            await self.safe_stream(f"Error deleting token file: {type(e).__name__}", verbatim=True)

        # Send a message informing them they can revert to any step
        await self.safe_stream("Connection unfinalized. You can now update your Botify API token.", verbatim=True)

        # Return the rebuilt UI
        return pip.rebuild(app_name, steps)
        # ───────── END CUSTOM UNFINALIZATION UI ─────────

    def run_all_cells(self, steps, app_name):
        """Generate placeholders for all steps through Pipulate helper."""
        return self.pipulate.run_all_cells(app_name, steps)

    async def jump_to_step(self, request):
        """
        Jump to a specific step in the workflow.
        
        This method updates the step_id in the database and rebuilds the UI
        to show the workflow from the selected step.
        
        Args:
            request: The HTTP request object containing the step_id
            
        Returns:
            FastHTML components showing the workflow from the selected step
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        db["step_id"] = step_id
        return pip.rebuild(app_name, steps)

    async def get_suggestion(self, step_id, state):
        """
        Get a suggestion value for a step based on transform function.
        
        If the step has a transform function, use the previous step's output
        to generate a suggested value.
        
        Args:
            step_id: The ID of the step to generate a suggestion for
            state: The current workflow state
            
        Returns:
            str: The suggested value or empty string if not applicable
        """
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
        """
        Handle reverting to a previous step in the workflow.
        
        This method clears state data from the specified step forward,
        marks the step as the revert target in the state, and rebuilds
        the workflow UI.
        
        Args:
            request: The HTTP request object containing the step_id
            
        Returns:
            FastHTML components representing the rebuilt workflow UI
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        pipeline_id = db.get("pipeline_id", "unknown")
        if not step_id:
            return P("Error: No step specified", style=self.pipulate.get_style("error"))
        await self.pipulate.clear_steps_from(pipeline_id, step_id, steps)
        state = self.pipulate.read_state(pipeline_id)
        state["_revert_target"] = step_id
        self.pipulate.write_state(pipeline_id, state)
        await self.safe_stream("Reverting to update your Botify API token.", verbatim=True)
        return self.pipulate.rebuild(app_name, steps)

    async def safe_stream(self, message, verbatim=False, role="user", spaces_before=None, spaces_after=1):
        """
        Safely stream messages, gracefully handling failures when Ollama/LLM is not available.
        
        For verbatim messages, this behaves exactly like the regular stream method.
        For LLM-processed messages (verbatim=False), it will fall back to a direct message
        if the LLM processing fails.
        
        Args:
            message: The message to stream
            verbatim: If True, send message as-is; if False, process with LLM
            role: The role for the message in the conversation history
            spaces_before: Number of line breaks to add before the message
            spaces_after: Number of line breaks to add after the message
            
        Returns:
            The original message
        """
        pip = self.pipulate
        
        try:
            # For verbatim messages, just use the message queue
            if verbatim:
                return await self.message_queue.add(
                    pip,
                    message, 
                    verbatim=True, 
                    role=role,
                    spaces_before=spaces_before,
                    spaces_after=spaces_after
                )
            
            # For LLM-processed messages, try the LLM but have a fallback
            try:
                return await self.message_queue.add(
                    pip,
                    message, 
                    verbatim=False, 
                    role=role,
                    spaces_before=spaces_before,
                    spaces_after=spaces_after
                )
            except Exception as e:
                logger.error(f"LLM processing failed: {str(e)}. Falling back to direct message.")
                # If LLM fails, just output a simpler message directly
                fallback_message = "Botify integration complete. You can now use the Botify API token in other workflows."
                if "Greet" in message:
                    fallback_message = "Welcome! Your Botify token is ready to be saved. Click Finalize to continue."
                
                return await self.message_queue.add(
                    pip,
                    fallback_message, 
                    verbatim=True,  # Force verbatim mode for the fallback
                    role=role,
                    spaces_before=spaces_before,
                    spaces_after=spaces_after
                )
        except Exception as e:
            # If everything fails, log the error but don't crash the workflow
            logger.error(f"Message streaming failed completely: {str(e)}")
            return message  # Return the original message but don't attempt to display it


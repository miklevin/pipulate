from fasthtml.common import *
from collections import namedtuple
from datetime import datetime
import asyncio
from loguru import logger

"""
Workflow Template

This file demonstrates the basic pattern for Pipulate workflows:
1. Define steps with optional transformations
2. Each step collects or processes data
3. Data flows from one step to the next
4. Steps can be reverted and the workflow can be finalized

To create your own workflow:
1. Copy this file and rename the class
2. Define your own steps
3. Implement custom validation and processing as needed
"""

# Each step represents one cell in our linear workflow.
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))

class HelloFlow:
    APP_NAME = "hello"
    DISPLAY_NAME = "Hello World"
    ENDPOINT_MESSAGE = "This simple workflow demonstrates a basic Hello World example. Enter an ID to start or resume your workflow."
    TRAINING_PROMPT = "Simple Hello World workflow."
    PRESERVE_REFILL = True
    
    def get_display_name(self):
        return self.DISPLAY_NAME

    def get_endpoint_message(self):
        return self.ENDPOINT_MESSAGE
        
    def get_training_prompt(self):
        return self.TRAINING_PROMPT

    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
        self.app = app
        self.pipulate = pipulate
        self.app_name = app_name
        self.pipeline = pipeline
        self.db = db
        steps = [
            Step(id='step_01', done='name', show='Your Name', refill=True),
            Step(id='step_02', done='greeting', show='Hello Message', refill=False, transform=lambda name: f"Hello {name}"),
            Step(id='finalize', done='finalized', show='Finalize', refill=False)
        ]
        self.STEPS = steps
        self.steps = {step.id: i for i, step in enumerate(self.STEPS)}
        self.STEP_MESSAGES = {
            "new": "Enter an ID to begin.",
            "finalize": {
                "ready": "All steps complete. Ready to finalize workflow.",
                "complete": "Workflow finalized. Use Unfinalize to make changes."
            }
        }
        # For each non-finalize step, set an input and completion message that reflects the cell order.
        for step in self.STEPS:
            if step.done != 'finalized':
                self.STEP_MESSAGES[step.id] = {
                    "input": f"{self.pipulate.fmt(step.id)}: Please enter {step.show}.",
                    "complete": f"{step.show} complete. Continue to next step."
                }
        # Register routes for all workflow methods.
        routes = [
            (f"/{app_name}", self.landing),
            (f"/{app_name}/init", self.init, ["POST"]),
            (f"/{app_name}/jump_to_step", self.jump_to_step, ["POST"]),
            (f"/{app_name}/revert", self.handle_revert, ["POST"]),
            (f"/{app_name}/finalize", self.finalize, ["GET", "POST"]),
            (f"/{app_name}/unfinalize", self.unfinalize, ["POST"]),
            # Individual step routes using new specific handlers
            (f"/{app_name}/step_01", self.step_01),
            (f"/{app_name}/step_01_submit", self.step_01_submit, ["POST"]),
            (f"/{app_name}/step_02", self.step_02),
            (f"/{app_name}/step_02_submit", self.step_02_submit, ["POST"]),
            (f"/{app_name}/finalize", self.finalize_explicit),
            (f"/{app_name}/finalize_submit", self.handle_step_submit, ["POST"])
        ]
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ["GET"]
            self.app.route(path, methods=method_list)(handler)

    # --- Core Workflow Methods (the cells) ---

    def validate_step(self, step_id: str, value: str) -> tuple[bool, str]:
        # Default validation: always valid.
        return True, ""

    async def process_step(self, step_id: str, value: str) -> str:
        # Default processing: return value unchanged.
        return value

    async def get_suggestion(self, step_id, state):
        # For HelloFlow, if a transform function exists, use the previous step's output.
        step = next((s for s in self.STEPS if s.id == step_id), None)
        if not step or not step.transform:
            return ""
        prev_index = self.steps[step_id] - 1
        if prev_index < 0:
            return ""
        prev_step_id = self.STEPS[prev_index].id
        prev_data = self.pipulate.get_step_data(self.db["pipeline_id"], prev_step_id, {})
        prev_word = prev_data.get("name", "")  # Use "name" for step_01
        return step.transform(prev_word) if prev_word else ""

    async def handle_revert(self, request):
        form = await request.form()
        step_id = form.get("step_id")
        pipeline_id = self.db.get("pipeline_id", "unknown")
        if not step_id:
            return P("Error: No step specified", style="color: red;")
        await self.pipulate.clear_steps_from(pipeline_id, step_id, self.STEPS)
        state = self.pipulate.read_state(pipeline_id)
        state["_revert_target"] = step_id
        self.pipulate.write_state(pipeline_id, state)
        message = await self.pipulate.get_state_message(pipeline_id, self.STEPS, self.STEP_MESSAGES)
        await self.pipulate.simulated_stream(message)
        placeholders = self.generate_step_placeholders(self.STEPS, self.app_name)
        return Div(*placeholders, id=f"{self.app_name}-container")

    async def landing(self):
        title = f"{self.DISPLAY_NAME or self.app_name.title()}: {len(self.STEPS) - 1} Steps + Finalize"
        self.pipeline.xtra(app_name=self.app_name)
        existing_ids = [record.url for record in self.pipeline()]
        return Container(
            Card(
                H2(title),
                P("Enter or resume a Pipeline ID:"),
                Form(
                    self.pipulate.wrap_with_inline_button(
                        Input(type="text", name="pipeline_id", placeholder="🗝 Old or existing ID here", required=True, autofocus=True, list="pipeline-ids"),
                        button_label=f"Start {self.DISPLAY_NAME} 🔑",
                        button_class="secondary"
                    ),
                    Datalist(*[Option(value=pid) for pid in existing_ids], id="pipeline-ids"),
                    hx_post=f"/{self.app_name}/init",
                    hx_target=f"#{self.app_name}-container"
                )
            ),
            Div(id=f"{self.app_name}-container")
        )

    async def init(self, request):
        form = await request.form()
        pipeline_id = form.get("pipeline_id", "untitled")
        self.db["pipeline_id"] = pipeline_id
        state, error = self.pipulate.initialize_if_missing(pipeline_id, {"app_name": self.app_name})
        if error:
            return error
            
        # After loading the state, check if all steps are complete
        all_steps_complete = True
        for step in self.STEPS[:-1]:  # Exclude finalize step
            if step.id not in state or step.done not in state[step.id]:
                all_steps_complete = False
                break
                
        # Check if workflow is finalized
        is_finalized = "finalize" in state and "finalized" in state["finalize"]
        
        # Add information about the workflow ID to conversation history
        id_message = f"Workflow ID: {pipeline_id}. You can use this ID to return to this workflow later."
        await self.pipulate.simulated_stream(id_message)
        
        # Add a small delay to ensure messages appear in the correct order
        await asyncio.sleep(0.5)
        
        # If all steps are complete, show an appropriate message
        if all_steps_complete:
            if is_finalized:
                await self.pipulate.simulated_stream(f"Workflow is complete and finalized. Use Unfinalize to make changes.")
            else:
                await self.pipulate.simulated_stream(f"Workflow is complete but not finalized. Press Finalize to lock your data.")
        else:
            # If it's a new workflow, add a brief explanation
            if not any(step.id in state for step in self.STEPS):
                await self.pipulate.simulated_stream("Please complete each step in sequence. Your progress will be saved automatically.")
        
        # Add another delay before loading the first step
        await asyncio.sleep(0.5)
        
        placeholders = self.generate_step_placeholders(self.STEPS, self.app_name)
        return Div(*placeholders, id=f"{self.app_name}-container")

    async def step_01(self, request):
        request.scope["path"] = f"/{self.app_name}/step_01"
        return await self.handle_step(request)

    async def step_01_submit(self, request):
        request.scope["path"] = f"/{self.app_name}/step_01_submit"
        return await self.handle_step_submit(request)

    async def step_02(self, request):
        request.scope["path"] = f"/{self.app_name}/step_02"
        return await self.handle_step(request)

    async def step_02_submit(self, request):
        request.scope["path"] = f"/{self.app_name}/step_02_submit"
        return await self.handle_step_submit(request)

    async def finalize_explicit(self, request):
        return await self.finalize(request)

    async def handle_step(self, request):
        step_id = request.url.path.split('/')[-1]
        step_index = self.steps[step_id]
        step = self.STEPS[step_index]
        next_step_id = self.STEPS[step_index + 1].id if step_index < len(self.STEPS) - 1 else None
        pipeline_id = self.db.get("pipeline_id", "unknown")
        state = self.pipulate.read_state(pipeline_id)
        step_data = self.pipulate.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "")
        
        if step.done == 'finalized':
            finalize_data = self.pipulate.get_step_data(pipeline_id, "finalize", {})
            if "finalized" in finalize_data:
                return Card(
                    H3("Pipeline Finalized"),
                    P("All steps are locked."),
                    Form(
                        Button("Unfinalize", type="submit", style="background-color: #f66;"),
                        hx_post=f"/{self.app_name}/unfinalize",
                        hx_target=f"#{self.app_name}-container",
                        hx_swap="outerHTML"
                    )
                )
            else:
                return Div(
                    Card(
                        H3("Finalize Pipeline"),
                        P("You can finalize this pipeline or go back to fix something."),
                        Form(
                            Button("Finalize All Steps", type="submit"),
                            hx_post=f"/{self.app_name}/finalize",
                            hx_target=f"#{self.app_name}-container",
                            hx_swap="outerHTML"
                        )
                    ),
                    id=step_id
                )
                
        finalize_data = self.pipulate.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data:
            return Div(
                Card(f"🔒 {step.show}: {user_val}"),
                Div(id=next_step_id, hx_get=f"/{self.app_name}/{next_step_id}", hx_trigger="load")
            )
            
        if user_val and state.get("_revert_target") != step_id:
            return Div(
                self.pipulate.revert_control(step_id=step_id, app_name=self.app_name, message=f"{step.show}: {user_val}", steps=self.STEPS),
                Div(id=next_step_id, hx_get=f"/{self.app_name}/{next_step_id}", hx_trigger="load")
            )
        else:
            display_value = user_val if (step.refill and user_val and self.PRESERVE_REFILL) else await self.get_suggestion(step_id, state)
                
            await self.pipulate.simulated_stream(self.STEP_MESSAGES[step_id]["input"])
            return Div(
                Card(
                    H3(f"{self.pipulate.fmt(step.id)}: Enter {step.show}"),
                    Form(
                        self.pipulate.wrap_with_inline_button(
                            Input(type="text", name=step.done, value=display_value, placeholder=f"Enter {step.show}", required=True, autofocus=True)
                        ),
                        hx_post=f"/{self.app_name}/{step.id}_submit",
                        hx_target=f"#{step.id}"
                    )
                ),
                Div(id=next_step_id),
                id=step.id
            )

    async def handle_step_submit(self, request):
        step_id = request.url.path.split('/')[-1].replace('_submit', '')
        step_index = self.steps[step_id]
        step = self.STEPS[step_index]
        pipeline_id = self.db.get("pipeline_id", "unknown")
        if step.done == 'finalized':
            state = self.pipulate.read_state(pipeline_id)
            state[step_id] = {step.done: True}
            self.pipulate.write_state(pipeline_id, state)
            message = await self.pipulate.get_state_message(pipeline_id, self.STEPS, self.STEP_MESSAGES)
            await self.pipulate.simulated_stream(message)
            placeholders = self.generate_step_placeholders(self.STEPS, self.app_name)
            return Div(*placeholders, id=f"{self.app_name}-container")
        
        form = await request.form()
        user_val = form.get(step.done, "")
        is_valid, error_msg = self.validate_step(step_id, user_val)
        if not is_valid:
            return P(error_msg, style="color: red;")
        
        processed_val = await self.process_step(step_id, user_val)
        next_step_id = self.STEPS[step_index + 1].id if step_index < len(self.STEPS) - 1 else None
        await self.pipulate.clear_steps_from(pipeline_id, step_id, self.STEPS)
        
        state = self.pipulate.read_state(pipeline_id)
        state[step_id] = {step.done: processed_val}
        if "_revert_target" in state:
            del state["_revert_target"]
        self.pipulate.write_state(pipeline_id, state)
        
        # Send the value confirmation
        await self.pipulate.simulated_stream(f"{step.show}: {processed_val}")
        
        # If this is the last regular step (before finalize), add a prompt to finalize
        if next_step_id == "finalize":
            await asyncio.sleep(0.1)  # Small delay for better readability
            await self.pipulate.simulated_stream("All steps complete! Please press the Finalize button below to save your data.")
        
        return Div(
            self.pipulate.revert_control(step_id=step_id, app_name=self.app_name, message=f"{step.show}: {processed_val}", steps=self.STEPS),
            Div(id=next_step_id, hx_get=f"/{self.app_name}/{next_step_id}", hx_trigger="load")
        )

    def generate_step_placeholders(self, steps, app_name):
        placeholders = []
        for i, step in enumerate(steps):
            trigger = "load" if i == 0 else f"stepComplete-{steps[i-1].id} from:{steps[i-1].id}"
            placeholders.append(Div(id=step.id, hx_get=f"/{app_name}/{step.id}", hx_trigger=trigger, hx_swap="outerHTML"))
        return placeholders

    async def delayed_greeting(self):
        await asyncio.sleep(2)
        await self.pipulate.simulated_stream("Enter an ID to begin.")

    # --- Finalization & Unfinalization ---
    async def finalize(self, request):
        pipeline_id = self.db.get("pipeline_id", "unknown")
        finalize_step = self.STEPS[-1]
        finalize_data = self.pipulate.get_step_data(pipeline_id, finalize_step.id, {})
        logger.debug(f"Pipeline ID: {pipeline_id}")
        logger.debug(f"Finalize step: {finalize_step}")
        logger.debug(f"Finalize data: {finalize_data}")
        
        if request.method == "GET":
            if finalize_step.done in finalize_data:
                logger.debug("Pipeline is already finalized")
                return Card(
                    H3("All Cards Complete"),
                    P("Pipeline is finalized. Use Unfinalize to make changes."),
                    Form(
                        Button("Unfinalize", type="submit", style="background-color: #f66;"),
                        hx_post=f"/{self.app_name}/unfinalize",
                        hx_target=f"#{self.app_name}-container",
                        hx_swap="outerHTML"
                    ),
                    style="color: green;",
                    id=finalize_step.id
                )
            
            # Check if all previous steps are complete
            non_finalize_steps = self.STEPS[:-1]
            all_steps_complete = all(
                self.pipulate.get_step_data(pipeline_id, step.id, {}).get(step.done)
                for step in non_finalize_steps
            )
            logger.debug(f"All steps complete: {all_steps_complete}")
            
            if all_steps_complete:
                return Card(
                    H3("Ready to finalize?"),
                    P("All data is saved. Lock it in?"),
                    Form(
                        Button("Finalize", type="submit"),
                        hx_post=f"/{self.app_name}/finalize",
                        hx_target=f"#{self.app_name}-container",
                        hx_swap="outerHTML"
                    ),
                    id=finalize_step.id
                )
            else:
                return Div(P("Nothing to finalize yet."), id=finalize_step.id)
        else:
            # This is the POST request when they press the Finalize button
            state = self.pipulate.read_state(pipeline_id)
            state["finalize"] = {"finalized": True}
            state["updated"] = datetime.now().isoformat()
            self.pipulate.write_state(pipeline_id, state)
            
            # Send a confirmation message
            await self.pipulate.simulated_stream("Workflow successfully finalized! Your data has been saved and locked.")
            
            # Return the updated UI
            return Div(*self.generate_step_placeholders(self.STEPS, self.app_name), id=f"{self.app_name}-container")

    async def unfinalize(self, request):
        pipeline_id = self.db.get("pipeline_id", "unknown")
        state = self.pipulate.read_state(pipeline_id)
        if "finalize" in state:
            del state["finalize"]
        self.pipulate.write_state(pipeline_id, state)
        
        # Send a message informing them they can revert to any step
        await self.pipulate.simulated_stream("Workflow unfinalized! You can now revert to any step and make changes.")
        
        placeholders = self.generate_step_placeholders(self.STEPS, self.app_name)
        return Div(*placeholders, id=f"{self.app_name}-container")

    async def jump_to_step(self, request):
        form = await request.form()
        step_id = form.get("step_id")
        self.db["step_id"] = step_id
        return self.pipulate.rebuild(self.app_name, self.STEPS)

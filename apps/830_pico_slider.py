# File: apps/830_pico_slider.py
import asyncio
from fasthtml.common import *  # type: ignore
from loguru import logger
from imports.crud import Step

ROLES = ['Developer']


class SliderPlaceholder:
    """
    PicoCSS Slider Workflow Template
    A clean Moviola range-slider template using HTMX to scrub through simulated diffs.
    """
    APP_NAME = 'pico_slider'
    DISPLAY_NAME = 'Pico Slider 🎚'
    ENDPOINT_MESSAGE = 'Welcome to the Pico Slider template. Drag the range slider to scrub through simulated timeline frames.'
    TRAINING_PROMPT = 'This template demonstrates an HTMX range input scrubbing dynamically across simulated diff frames with Prism syntax highlighting.'

    SIMULATED_FRAMES = [
        {
            'label': 'Frame 1 of 4 — Initial Scaffold',
            'hash': 'a1b2c3d',
            'summary': 'feat: Initialize minimal workflow skeleton',
            'diff': (
                "--- /dev/null\n"
                "+++ b/workflow.py\n"
                "@@ -0,0 +1,5 @@\n"
                "+class MinimalFlow:\n"
                "+    APP_NAME = 'minimal'\n"
                "+    def __init__(self, app, pipulate, pipeline, db):\n"
                "+        self.wand = pipulate\n"
            )
        },
        {
            'label': 'Frame 2 of 4 — Add Range Input',
            'hash': 'e4f5g6h',
            'summary': 'feat: Wire HTMX range slider with 50ms debounce',
            'diff': (
                "--- a/workflow.py\n"
                "+++ b/workflow.py\n"
                "@@ -3,3 +3,8 @@\n"
                "     def __init__(self, app, pipulate, pipeline, db):\n"
                "         self.wand = pipulate\n"
                "+        self.app.route(f'/{self.APP_NAME}/scrub', methods=['POST'])(self.scrub)\n"
                "+\n"
                "+    async def scrub(self, request):\n"
                "+        return Pre(Code('+ scrubbed frame', cls='language-diff'))\n"
            )
        },
        {
            'label': 'Frame 3 of 4 — Prism Tokenization',
            'hash': 'i7j8k9l',
            'summary': 'style: Re-trigger Prism diff highlighting on HTMX swap',
            'diff': (
                "--- a/workflow.py\n"
                "+++ b/workflow.py\n"
                "@@ -6,3 +6,6 @@\n"
                "     async def scrub(self, request):\n"
                "-        return Pre(Code('+ scrubbed frame', cls='language-diff'))\n"
                "+        return Div(\n"
                "+            Pre(Code('+ highlighted insertion\\n- removed old line', cls='language-diff')),\n"
                "+            Script(\"if (typeof Prism !== 'undefined') { Prism.highlightAllUnder(document.getElementById('pico-slider-viewport')); }\")\n"
                "+        )\n"
            )
        },
        {
            'label': 'Frame 4 of 4 — Lock & Finalize',
            'hash': 'm0n1o2p',
            'summary': 'chore: Seal template for downstream workflow cloning',
            'diff': (
                "--- a/workflow.py\n"
                "+++ b/workflow.py\n"
                "@@ -1,4 +1,5 @@\n"
                "+# Ready to clone into new Pipulate workflows\n"
                " class MinimalFlow:\n"
                "-    APP_NAME = 'minimal'\n"
                "+    APP_NAME = 'pico_slider'\n"
            )
        },
    ]

    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
        self.pipulate = pipulate
        self.app = app
        self.app_name = app_name
        self.pipeline = pipeline
        self.wand = pipulate
        wand = self.wand
        self.message_queue = wand.get_message_queue()
        self.ui = wand.get_ui_constants()

        self.steps = [
            Step(id='step_01', done='timeline_index', show='Timeline Scrubber', refill=False),
            # --- STEPS_LIST_INSERTION_POINT ---
            Step(id='finalize', done='finalized', show='Finalize Workflow', refill=False)
        ]
        self.steps_indices = {step_obj.id: i for i, step_obj in enumerate(self.steps)}

        pipulate.register_workflow_routes(self)
        self.app.route(f'/{self.app_name}/scrub_timeline', methods=['POST'])(self.scrub_timeline)

        self.step_messages = {
            'finalize': {
                'ready': self.ui['MESSAGES']['ALL_STEPS_COMPLETE'],
                'complete': f'Workflow finalized. Use {self.ui["BUTTON_LABELS"]["UNLOCK"]} to make changes.'
            },
            'step_01': {
                'input': 'Timeline Scrubber: Drag the slider to scrub through simulated frames.',
                'complete': 'Timeline Scrubber is complete. Proceed to finalize.'
            }
        }

    def _render_frame(self, index: int):
        frames = self.SIMULATED_FRAMES
        index = max(0, min(index, len(frames) - 1))
        frame = frames[index]
        diff_text = f"Frame:   {frame['label']} ({frame['hash']})\nSummary: {frame['summary']}\n\n{frame['diff']}"
        return Div(
            Pre(Code(diff_text, cls="language-diff"), cls="language-diff", style="margin-bottom: 0;"),
            Script("if (typeof Prism !== 'undefined') { Prism.highlightAllUnder(document.getElementById('pico-slider-viewport')); }"),
            id="pico-slider-viewport",
            style="margin-top: 1rem; background: var(--pico-code-background-color); padding: 1rem; border-radius: var(--pico-border-radius); max-height: 60vh; overflow-y: auto;"
        )

    async def landing(self, request):
        wand = self.wand
        return wand.create_standard_landing_page(self)

    async def init(self, request):
        wand, steps, app_name = self.wand, self.steps, self.app_name
        form = await request.form()
        user_input = form.get('pipeline_id', '').strip()
        if not user_input:
            from starlette.responses import Response
            response = Response('')
            response.headers['HX-Refresh'] = 'true'
            return response

        context = wand.get_plugin_context(self)
        profile_name = context['profile_name'] or 'default'
        profile_part = profile_name.replace(' ', '_')
        plugin_part = app_name.replace(' ', '_')
        expected_prefix = f'{profile_part}-{plugin_part}-'
        if user_input.startswith(expected_prefix):
            pipeline_id = user_input
        else:
            _, prefix, user_provided_id = wand.generate_pipeline_key(self, user_input)
            pipeline_id = f'{prefix}{user_provided_id}'

        wand.db['pipeline_id'] = pipeline_id
        state, error = wand.initialize_if_missing(pipeline_id, {'app_name': app_name})
        if error:
            return error

        all_steps_complete = all((step.id in state and step.done in state[step.id] for step in steps[:-1]))
        is_finalized = 'finalize' in state and 'finalized' in state['finalize']

        await self.message_queue.add(wand, f'{self.ui["EMOJIS"]["WORKFLOW"]} Workflow ID: {pipeline_id}', verbatim=True, spaces_before=0)

        if all_steps_complete:
            if is_finalized:
                status_msg = f'{self.ui["EMOJIS"]["LOCKED"]} Workflow is complete and finalized. Use {self.ui["BUTTON_LABELS"]["UNLOCK"]} to make changes.'
            else:
                status_msg = f'{self.ui["EMOJIS"]["SUCCESS"]} Workflow is complete but not finalized. Press Finalize to lock your data.'
            await self.message_queue.add(wand, status_msg, verbatim=True)
        elif not any((step.id in state for step in self.steps)):
            await self.message_queue.add(wand, f'{self.ui["EMOJIS"]["INPUT_FORM"]} Use the slider to explore the simulated timeline.', verbatim=True)

        parsed = wand.parse_pipeline_key(pipeline_id)
        prefix = f"{parsed['profile_part']}-{parsed['plugin_part']}-"
        self.pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in self.pipeline() if record.pkey.startswith(prefix)]
        if pipeline_id not in matching_records:
            matching_records.append(pipeline_id)
        wand.update_datalist('pipeline-ids', options=matching_records)
        return wand.run_all_cells(app_name, steps)

    async def scrub_timeline(self, request):
        """Intercepts the slider input event and returns the simulated diff payload dynamically."""
        form_data = await request.form()
        try:
            index = int(form_data.get('timeline_index', 0))
        except (ValueError, TypeError):
            index = 0
        return self._render_frame(index)

    # --- START_STEP_BUNDLE: step_01 ---
    async def step_01(self, request):
        wand, steps, app_name = self.wand, self.steps, self.app_name
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index + 1 < len(steps) else 'finalize'
        pipeline_id = wand.db.get('pipeline_id', 'unknown')
        state = wand.read_state(pipeline_id)
        step_data = wand.get_step_data(pipeline_id, step_id, {})
        current_value = step_data.get(step.done, "")
        finalize_data = wand.get_step_data(pipeline_id, "finalize", {})

        if "finalized" in finalize_data and current_value:
            return Div(
                Article(H3(f'{self.ui["EMOJIS"]["LOCKED"]} {step.show}: {current_value}')),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        elif current_value and state.get("_revert_target") != step_id:
            return Div(
                wand.display_revert_header(step_id=step_id, app_name=app_name, message=f"{step.show}: {current_value}", steps=steps),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        else:
            slider_max = str(len(self.SIMULATED_FRAMES) - 1)
            range_slider = Input(
                type="range",
                name="timeline_index",
                min="0",
                max=slider_max,
                value="0",
                hx_post=f"/{app_name}/scrub_timeline",
                hx_target="#pico-slider-viewport",
                hx_swap="outerHTML",
                hx_trigger="input delay:50ms"
            )

            return Div(
                Article(
                    H3(f"{step.show} (Template)"),
                    P("Drag the PicoCSS range slider to scrub through simulated diff frames via HTMX.", cls="text-secondary"),
                    Form(
                        range_slider,
                        self._render_frame(0),
                        Br(),
                        Button("Lock Selection & Proceed ▸", type="submit", cls=self.ui['BUTTON_STYLES']['PRIMARY']),
                        hx_post=f"/{app_name}/{step_id}_submit",
                        hx_target=f"#{step_id}"
                    )
                ),
                Div(id=next_step_id),
                id=step_id
            )

    async def step_01_submit(self, request):
        wand, steps, app_name = self.wand, self.steps, self.app_name
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = wand.db.get('pipeline_id', 'unknown')

        form_data = await request.form()
        selected_index = form_data.get('timeline_index', '0')
        value_to_save = f"Locked at frame index {selected_index}"

        await wand.set_step_data(pipeline_id, step_id, value_to_save, steps)
        wand.append_to_history(f"[WIDGET STATE] {step.show}: {value_to_save}")
        await self.message_queue.add(wand, f"{step.show} complete.", verbatim=True)

        return wand.chain_reverter(step_id, step_index, steps, app_name, value_to_save)
    # --- END_STEP_BUNDLE: step_01 ---

    # --- STEP_METHODS_INSERTION_POINT ---

    async def finalize(self, request):
        wand, steps, app_name = self.wand, self.steps, self.app_name
        pipeline_id = wand.db.get('pipeline_id', 'unknown')
        finalize_step = steps[-1]
        finalize_data = wand.get_step_data(pipeline_id, finalize_step.id, {})

        if request.method == 'GET':
            if finalize_step.done in finalize_data:
                return Article(
                    H3(self.ui['MESSAGES']['WORKFLOW_LOCKED'], id="workflow-locked-heading"),
                    Form(
                        Button(self.ui['BUTTON_LABELS']['UNLOCK'], type='submit', name='unlock_action', cls=self.ui['BUTTON_STYLES']['OUTLINE']),
                        hx_post=f'/{app_name}/unfinalize',
                        hx_target=f'#{app_name}-container'
                    ),
                    id=finalize_step.id
                )
            else:
                all_steps_complete = all(wand.get_step_data(pipeline_id, s.id, {}).get(s.done) for s in steps[:-1])
                if all_steps_complete:
                    return Article(
                        H3(self.ui['MESSAGES']['FINALIZE_QUESTION']),
                        P(self.ui['MESSAGES']['FINALIZE_HELP'], cls='text-secondary'),
                        Form(
                            Button(self.ui['BUTTON_LABELS']['FINALIZE'], type='submit', name='finalize_action', cls=self.ui['BUTTON_STYLES']['PRIMARY']),
                            hx_post=f'/{app_name}/finalize',
                            hx_target=f'#{app_name}-container'
                        ),
                        id=finalize_step.id
                    )
                else:
                    return Div(id=finalize_step.id)
        else:
            await wand.finalize_workflow(pipeline_id)
            await self.message_queue.add(wand, self.step_messages['finalize']['complete'], verbatim=True)
            return wand.run_all_cells(app_name, steps)

    async def unfinalize(self, request):
        wand, steps, app_name = self.wand, self.steps, self.app_name
        pipeline_id = wand.db.get('pipeline_id', 'unknown')
        await wand.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(wand, self.ui['MESSAGES']['WORKFLOW_UNLOCKED'], verbatim=True)
        return wand.run_all_cells(app_name, steps)

    async def get_suggestion(self, step_id, state):
        return ''

    async def handle_revert(self, request):
        wand, steps, app_name = self.wand, self.steps, self.app_name
        form = await request.form()
        step_id = form.get('step_id')
        pipeline_id = wand.db.get('pipeline_id', 'unknown')
        if not step_id:
            return P('Error: No step specified for revert.', cls='text-invalid')
        await wand.clear_steps_from(pipeline_id, step_id, steps)
        state = wand.read_state(pipeline_id)
        state['_revert_target'] = step_id
        wand.write_state(pipeline_id, state)
        message = await wand.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(wand, message, verbatim=True)
        return wand.run_all_cells(app_name, steps)

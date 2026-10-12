import asyncio
import hashlib
import json
import os
import zipfile
from pathlib import Path
from urllib.parse import urlparse, quote

from fasthtml.common import *
from loguru import logger
from starlette.responses import FileResponse, Response

from imports.crud import Step
from tools.scraper_tools import selenium_automation, generate_optics_subprocess

ROLES = ['Core', 'SEO']


class OpticsWorkflow:
    """
    911 LLM Optics Workflow: Zero-credential optical diffraction engine.
    Exposes RFC 9110 wire truth vs. hydrated DOM, structural diffs, and Link Lens
    in a verifiable 3-step FastHTML pipeline with sealed deed export.
    """
    APP_NAME = 'optics'
    DISPLAY_NAME = '911 LLM Optics 👁️'
    ENDPOINT_MESSAGE = 'Inspect DOM diffs, Link Lens, and RFC 9110 wire truth. Press Enter...'

    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
        self.pipulate = pipulate
        self.app = app
        self.app_name = app_name
        self.wand = pipulate
        wand = self.wand

        self.pipeline = pipeline
        self.steps_indices = {}
        self.message_queue = self.wand.get_message_queue()
        self.ui = self.wand.get_ui_constants()

        self.steps = [
            Step(
                id='step_01',
                done='url',
                show='Target URL',
                refill=True
            ),
            Step(
                id='step_02',
                done='captured',
                show='Capture & SIFT',
                refill=False
            ),
            Step(
                id='step_03',
                done='inspected',
                show='Optical Analysis',
                refill=False
            ),
            Step(id='finalize', done='finalized', show='Finalize & Deed', refill=False)
        ]

        self.steps_indices = {step.id: i for i, step in enumerate(self.steps)}
        pipulate.register_workflow_routes(self)

        self.step_messages = {
            'finalize': {
                'ready': f'{self.ui["EMOJIS"]["SUCCESS"]} All steps complete. Ready to finalize and seal the optics deed.',
                'complete': f'{self.ui["EMOJIS"]["COMPLETION"]} Workflow finalized. Verified deed ready for export.'
            }
        }
        for step in self.steps:
            if step.id != 'finalize':
                self.step_messages[step.id] = {
                    'input': f'{self.ui["EMOJIS"]["INPUT_FORM"]} {self.wand.fmt(step.id)}: Please enter {step.show}.',
                    'complete': f'{self.ui["EMOJIS"]["SUCCESS"]} {step.show} complete. Proceed to next step.'
                }

        # Dedicated route for downloading verified ZIP deed
        @self.app.get(f'/{self.app_name}/download/{{pipeline_id}}')
        async def download_deed(pipeline_id: str):
            state = self.wand.read_state(pipeline_id)
            out_dir_str = state.get('step_02', {}).get('captured', '')
            if not out_dir_str:
                return Response("Artifact directory not found", status_code=404)
            zip_path = Path(out_dir_str) / "optics_deed.zip"
            if zip_path.exists():
                return FileResponse(
                    str(zip_path),
                    filename=f"optics_deed_{pipeline_id}.zip",
                    media_type="application/zip"
                )
            return Response("Deed file not found", status_code=404)

    async def landing(self, request):
        return self.wand.create_standard_landing_page(self)

    async def init(self, request):
        wand, steps, app_name = (self.wand, self.steps, self.app_name)
        form = await request.form()
        user_input = form.get('pipeline_id', '').strip()
        if not user_input:
            response = Response('')
            response.headers['HX-Refresh'] = 'true'
            return response

        context = wand.get_plugin_context(self)
        profile_name = context.get('profile_name') or 'default'
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

        await self.message_queue.add(wand, f'{self.ui["EMOJIS"]["WORKFLOW"]} Optics Run ID: {pipeline_id}', verbatim=True, spaces_before=0)
        await self.message_queue.add(wand, f"{self.ui['EMOJIS']['KEY']} Access this audit anytime using '{pipeline_id}'.", verbatim=True, spaces_before=0)

        if all_steps_complete:
            if is_finalized:
                status_msg = f'{self.ui["EMOJIS"]["LOCKED"]} Optics audit is complete and finalized. Download deed below.'
            else:
                status_msg = f'{self.ui["EMOJIS"]["SUCCESS"]} Optics analysis ready. Finalize to seal the deed.'
            await self.message_queue.add(wand, status_msg, verbatim=True)
            self.wand.speak("Optics audit recovered.", wait=False)
        elif not any((step.id in state for step in self.steps)):
            await self.message_queue.add(wand, f'{self.ui["EMOJIS"]["INPUT_FORM"]} Step 1: Provide target URL to begin optical diffraction.', verbatim=True)
            self.wand.speak("Optics workflow initialized. Enter target URL to begin.", wait=False)

        parsed = wand.parse_pipeline_key(pipeline_id)
        prefix = f"{parsed['profile_part']}-{parsed['plugin_part']}-"
        self.pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in self.pipeline() if record.pkey.startswith(prefix)]
        if pipeline_id not in matching_records:
            matching_records.append(pipeline_id)
        wand.update_datalist('pipeline-ids', options=matching_records)
        return wand.run_all_cells(app_name, steps)

    async def finalize(self, request):
        wand, steps, app_name = (self.wand, self.steps, self.app_name)
        pipeline_id = wand.db.get('pipeline_id', 'unknown')
        finalize_step = steps[-1]
        finalize_data = wand.get_step_data(pipeline_id, finalize_step.id, {})

        if request.method == 'GET':
            if finalize_step.done in finalize_data:
                state = wand.read_state(pipeline_id)
                out_dir_str = state.get('step_02', {}).get('captured', '')
                zip_path = Path(out_dir_str) / "optics_deed.zip" if out_dir_str else None
                hash_str = "Unknown"
                if zip_path and zip_path.exists():
                    hash_str = hashlib.sha256(zip_path.read_bytes()).hexdigest()[:16]

                return Article(
                    H3(f'{self.ui["EMOJIS"]["LOCKED"]} Optical Deed Sealed'),
                    P(f"SHA-256 Digest: {hash_str}", cls='text-muted'),
                    Div(
                        A("📥 Download Verified Optics Deed (ZIP)", href=f'/{app_name}/download/{pipeline_id}', cls=self.ui['BUTTON_STYLES']['PRIMARY'], role='button'),
                        style='margin-bottom: 1rem;'
                    ),
                    Form(
                        Button(self.ui['BUTTON_LABELS']['UNLOCK'], type='submit', cls=self.ui['BUTTON_STYLES']['OUTLINE']),
                        hx_post=f'/{app_name}/unfinalize',
                        hx_target=f'#{app_name}-container',
                        hx_swap='outerHTML'
                    ),
                    id=finalize_step.id,
                    role='region'
                )
            else:
                all_steps_complete = all((wand.get_step_data(pipeline_id, step.id, {}).get(step.done) for step in steps[:-1]))
                if all_steps_complete:
                    return Article(
                        H3(f'{self.ui["EMOJIS"]["SUCCESS"]} Optical Analysis Complete. Seal Deed?'),
                        P("Finalizing will compile the ZIP deed, stamp the cryptographic hash, and lock the run.", cls='text-muted'),
                        Form(
                            Button(self.ui['BUTTON_LABELS']['FINALIZE'], type='submit', cls=self.ui['BUTTON_STYLES']['PRIMARY']),
                            hx_post=f'/{app_name}/finalize',
                            hx_target=f'#{app_name}-container',
                            hx_swap='outerHTML'
                        ),
                        id=finalize_step.id,
                        role='region'
                    )
                else:
                    return Div(id=finalize_step.id)
        else:
            # POST: Finalize workflow, build sealed ZIP
            state = wand.read_state(pipeline_id)
            out_dir_str = state.get('step_02', {}).get('captured', '')
            if out_dir_str and os.path.isdir(out_dir_str):
                out_dir = Path(out_dir_str)
                zip_path = out_dir / "optics_deed.zip"
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for fname in ["headers.json", "source.html", "hydrated_dom.html", "diff_simple_dom.txt", "diff_hierarchy.txt", "links.md", "seo.md"]:
                        fpath = out_dir / fname
                        if fpath.exists():
                            zf.write(fpath, arcname=fname)

            await wand.finalize_workflow(pipeline_id)
            await self.message_queue.add(wand, self.step_messages['finalize']['complete'], verbatim=True)
            self.wand.speak("The optics deed is now locked and sealed.", wait=False)
            return wand.run_all_cells(app_name, steps)

    async def unfinalize(self, request):
        wand, steps, app_name = (self.wand, self.steps, self.app_name)
        pipeline_id = wand.db.get('pipeline_id', 'unknown')
        await wand.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(wand, f'{self.ui["EMOJIS"]["UNLOCKED"]} Workflow unfinalized.', verbatim=True)
        self.wand.speak("Workflow unlocked.", wait=False)
        return wand.run_all_cells(app_name, steps)

    async def handle_revert(self, request):
        wand, steps, app_name = (self.wand, self.steps, self.app_name)
        form = await request.form()
        step_id = form.get('step_id')
        pipeline_id = wand.db.get('pipeline_id', 'unknown')
        if not step_id:
            return P('Error: No step specified', cls='text-invalid')
        await wand.clear_steps_from(pipeline_id, step_id, steps)
        state = wand.read_state(pipeline_id)
        state['_revert_target'] = step_id
        wand.write_state(pipeline_id, state)
        message = await wand.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(wand, f'{self.ui["EMOJIS"]["WARNING"]} Reverted to {step_id}. {message}', verbatim=True)
        return wand.run_all_cells(app_name, steps)

    async def get_suggestion(self, step_id, state):
        return ''

    # --- STEP 01: TARGET URL ---
    async def step_01(self, request):
        wand, steps, app_name = (self.wand, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = wand.db.get('pipeline_id', 'unknown')
        state = wand.read_state(pipeline_id)
        step_data = wand.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, '')
        finalize_data = wand.get_step_data(pipeline_id, 'finalize', {})

        if 'finalized' in finalize_data:
            return Div(
                Article(
                    H3(f'{self.ui["EMOJIS"]["LOCKED"]} {step.show}: {user_val}'),
                    role='region'
                ),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        elif user_val and state.get('_revert_target') != step_id:
            return Div(
                wand.display_revert_header(
                    step_id=step_id,
                    app_name=app_name,
                    message=f'{self.ui["EMOJIS"]["USER_INPUT"]} {step.show}: {user_val}',
                    steps=steps
                ),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        else:
            explanation = "Provide an HTTP/HTTPS URL to observe wire truth vs. hydrated DOM."
            return Div(
                Article(
                    H3(f'{self.ui["EMOJIS"]["USER_INPUT"]} {self.wand.fmt(step.id)}: Enter {step.show}'),
                    P(explanation, cls='text-muted'),
                    Label('Target URL:', _for='optics-step01-url-input'),
                    Form(
                        wand.wrap_with_inline_button(
                            Input(
                                type='url',
                                name=step.done,
                                value=user_val or 'https://mikelev.in/',
                                placeholder='https://example.com/',
                                required=True,
                                autofocus=True,
                                id='optics-step01-url-input',
                                aria_label='Target URL to inspect'
                            ),
                            button_label=self.ui['BUTTON_LABELS']['NEXT_STEP']
                        ),
                        hx_post=f'/{app_name}/{step_id}_submit',
                        hx_target=f'#{step_id}',
                        id='optics-step01-form'
                    ),
                    role='region'
                ),
                Div(id=next_step_id),
                id=step_id
            )

    async def step_01_submit(self, request):
        wand, steps, app_name = (self.wand, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = wand.db.get("pipeline_id", "unknown")

        form = await request.form()
        user_val = form.get(step.done, "").strip()
        if not user_val:
            error_msg = f'{self.ui["EMOJIS"]["ERROR"]} Please enter a valid URL'
            await self.message_queue.add(wand, error_msg, verbatim=True)
            return P(error_msg, cls='text-invalid')

        if not user_val.startswith(('http://', 'https://')):
            user_val = f'https://{user_val}'

        await wand.set_step_data(pipeline_id, step_id, user_val, steps)
        await self.message_queue.add(wand, f'{self.ui["EMOJIS"]["SUCCESS"]} Target set: {user_val}', verbatim=True)
        self.wand.speak("Target URL set. Ready for optical capture.", wait=False)
        self.wand.append_to_history(f"[WIDGET CONTENT] {step.show}:\n{user_val}")
        return wand.chain_reverter(step_id, step_index, steps, app_name, user_val)

    # --- STEP 02: CAPTURE & SIFT ---
    async def step_02(self, request):
        wand, steps, app_name = (self.wand, self.steps, self.app_name)
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = wand.db.get('pipeline_id', 'unknown')
        state = wand.read_state(pipeline_id)
        step_data = wand.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, '')
        finalize_data = wand.get_step_data(pipeline_id, 'finalize', {})

        target_url = wand.get_step_data(pipeline_id, 'step_01', {}).get('url', '')

        if 'finalized' in finalize_data:
            return Div(
                Article(
                    H3(f'{self.ui["EMOJIS"]["LOCKED"]} {step.show}: Captured & SIFTed'),
                    role='region'
                ),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        elif user_val and state.get('_revert_target') != step_id:
            return Div(
                wand.display_revert_header(
                    step_id=step_id,
                    app_name=app_name,
                    message=f'{self.ui["EMOJIS"]["SUCCESS"]} {step.show}: Artifacts Extracted',
                    steps=steps
                ),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        else:
            return Div(
                Article(
                    H3(f'{self.ui["EMOJIS"]["WORKFLOW"]} {self.wand.fmt(step.id)}: {step.show}'),
                    P(f"Target: {target_url}", cls='text-muted'),
                    P("Engage undetected browser to drain CDP performance log, capture wire response vs. hydrated DOM, and run the SIFT comparator.", cls='text-muted'),
                    Form(
                        Button("Engage Optics SIFT 👁️", type='submit', cls=self.ui['BUTTON_STYLES']['PRIMARY']),
                        hx_post=f'/{app_name}/{step_id}_submit',
                        hx_target=f'#{step_id}',
                        id='optics-step02-form'
                    ),
                    role='region'
                ),
                Div(id=next_step_id),
                id=step_id
            )

    async def step_02_submit(self, request):
        wand, steps, app_name = (self.wand, self.steps, self.app_name)
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = wand.db.get("pipeline_id", "unknown")

        target_url = wand.get_step_data(pipeline_id, 'step_01', {}).get('url', '')
        parsed = urlparse(target_url)
        domain = parsed.netloc or "unknown"
        slug = quote(parsed.path or "/", safe="").replace("/", "_")[:100] or "%2F"
        output_dir = Path("browser_cache/looking_at") / domain / slug
        output_dir.mkdir(parents=True, exist_ok=True)

        params = {
            "url": target_url,
            "domain": domain,
            "url_path_slug": slug,
            "take_screenshot": False,
            "headless": True,
            "is_notebook_context": False,
            "verbose": False,
            "persistent": False,
            "override_cache": True,
        }

        try:
            res = await selenium_automation(params)
        except Exception as e:
            logger.warning(f"Selenium capture failed: {e}; attempting HTTP fallback")
            res = {"success": False}

        if not res.get("success"):
            import urllib.request
            try:
                req = urllib.request.Request(
                    target_url,
                    headers={"User-Agent": "Mozilla/5.0 (Pipulate-Optics/1.0)", "Accept": "text/html,text/markdown;q=0.9"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw_html = resp.read().decode('utf-8', errors='replace')
                    headers_dict = {k.lower(): v for k, v in resp.headers.items()}
                (output_dir / "source.html").write_text(raw_html, encoding='utf-8')
                (output_dir / "hydrated_dom.html").write_text(raw_html, encoding='utf-8')
                (output_dir / "simple_source_html.html").write_text(raw_html, encoding='utf-8')
                (output_dir / "simple_hydrated_dom.html").write_text(raw_html, encoding='utf-8')
                (output_dir / "headers.json").write_text(json.dumps({
                    "url": target_url,
                    "final_url": target_url,
                    "source_provenance": "http_fallback",
                    "headers": headers_dict
                }, indent=2), encoding='utf-8')
                await generate_optics_subprocess(str(output_dir))
            except Exception as fb_err:
                error_msg = f'{self.ui["EMOJIS"]["ERROR"]} Capture failed: {fb_err}'
                await self.message_queue.add(wand, error_msg, verbatim=True)
                return P(error_msg, cls='text-invalid')

        stored_val = str(output_dir)
        await wand.set_step_data(pipeline_id, step_id, stored_val, steps)
        await self.message_queue.add(wand, f'{self.ui["EMOJIS"]["SUCCESS"]} Optics capture complete for {domain}', verbatim=True)
        self.wand.speak("Optics capture complete. Diff ready for inspection.", wait=False)
        return wand.chain_reverter(step_id, step_index, steps, app_name, stored_val)

    # --- STEP 03: OPTICAL ANALYSIS ---
    async def step_03(self, request):
        wand, steps, app_name = (self.wand, self.steps, self.app_name)
        step_id = 'step_03'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = wand.db.get('pipeline_id', 'unknown')
        state = wand.read_state(pipeline_id)
        step_data = wand.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, '')
        finalize_data = wand.get_step_data(pipeline_id, 'finalize', {})

        out_dir_str = wand.get_step_data(pipeline_id, 'step_02', {}).get('captured', '')
        out_dir = Path(out_dir_str) if out_dir_str else None

        if 'finalized' in finalize_data:
            return Div(
                Article(
                    H3(f'{self.ui["EMOJIS"]["LOCKED"]} {step.show}: Inspection Verified'),
                    role='region'
                ),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        elif user_val and state.get('_revert_target') != step_id:
            return Div(
                wand.display_revert_header(
                    step_id=step_id,
                    app_name=app_name,
                    message=f'{self.ui["EMOJIS"]["SUCCESS"]} {step.show}: Verified',
                    steps=steps
                ),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        else:
            # Read artifacts
            diff_text = "No diff artifact found."
            links_text = "No link lens found."
            provenance = "unknown"

            if out_dir and out_dir.exists():
                diff_path = out_dir / "diff_simple_dom.txt"
                if not diff_path.exists():
                    diff_path = out_dir / "diff_hierarchy.txt"
                if diff_path.exists():
                    diff_text = diff_path.read_text(encoding='utf-8')[:4000]

                links_path = out_dir / "links.md"
                if links_path.exists():
                    links_text = links_path.read_text(encoding='utf-8')[:2500]

                headers_path = out_dir / "headers.json"
                if headers_path.exists():
                    try:
                        h_data = json.loads(headers_path.read_text(encoding='utf-8'))
                        provenance = h_data.get("source_provenance", "wire")
                    except Exception:
                        pass

            return Div(
                Article(
                    H3(f'{self.ui["EMOJIS"]["GREETING"]} {self.wand.fmt(step.id)}: {step.show}'),
                    P(f"Wire Truth Provenance: {provenance.upper()}", cls='text-muted'),
                    H4("1. DOM Structural Diff (Source vs. Hydrated)"),
                    Pre(
                        Code(diff_text),
                        style='max-height: 250px; overflow-y: auto; background: #111; color: #50fa7b; padding: 0.75rem; border-radius: 4px;'
                    ),
                    H4("2. Link Lens (Anchor Accounting)"),
                    Pre(
                        Code(links_text),
                        style='max-height: 250px; overflow-y: auto; background: #111; color: #8be9fd; padding: 0.75rem; border-radius: 4px;'
                    ),
                    Form(
                        Button("Accept Optical Findings & Seal ▸", type='submit', cls=self.ui['BUTTON_STYLES']['PRIMARY']),
                        hx_post=f'/{app_name}/{step_id}_submit',
                        hx_target=f'#{step_id}',
                        id='optics-step03-form'
                    ),
                    role='region'
                ),
                Div(id=next_step_id),
                id=step_id
            )

    async def step_03_submit(self, request):
        wand, steps, app_name = (self.wand, self.steps, self.app_name)
        step_id = 'step_03'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = wand.db.get("pipeline_id", "unknown")

        stored_val = "verified"
        await wand.set_step_data(pipeline_id, step_id, stored_val, steps)
        await self.message_queue.add(wand, f'{self.ui["EMOJIS"]["SUCCESS"]} Optical analysis verified.', verbatim=True)
        self.wand.speak("Optical analysis accepted. Ready to seal deed.", wait=False)
        return wand.chain_reverter(step_id, step_index, steps, app_name, stored_val)

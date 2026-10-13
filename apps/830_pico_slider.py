# File: apps/830_pico_slider.py
import asyncio
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from fasthtml.common import *  # type: ignore
from loguru import logger
from imports.crud import Step

ROLES = ['Developer', 'Core']


class GitSliderFlow:
    """
    Git Slider Workflow
    An interactive Moviola scrub slider through the Git commit diff history
    of any tracked repository file.
    """
    APP_NAME = 'git_slider'
    DISPLAY_NAME = 'Git Slider 🎚'
    ENDPOINT_MESSAGE = 'Welcome to the Git Slider. Select a file, then drag the slider to scrub through its commit history.'
    TRAINING_PROMPT = 'This workflow uses HTMX and a range input to scrub through the real git history of any tracked file in the repository.'

    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
        self.pipulate = pipulate
        self.app = app
        self.app_name = app_name
        self.pipeline = pipeline
        self.wand = pipulate
        wand = self.wand
        self.message_queue = wand.get_message_queue()
        self.ui = wand.get_ui_constants()
        self._commits_cache = {}

        self.steps = [
            Step(
                id='step_01',
                done='target_file',
                show='Target File',
                refill=True,
            ),
            Step(
                id='step_02',
                done='timeline_index',
                show='Timeline Scrubber',
                refill=False,
            ),
            # --- STEPS_LIST_INSERTION_POINT ---
            Step(id='finalize', done='finalized', show='Finalize & Lock', refill=False)
        ]
        self.steps_indices = {step_obj.id: i for i, step_obj in enumerate(self.steps)}

        # Register standard workflow routes
        pipulate.register_workflow_routes(self)

        # Register dynamic HTMX scrubbing endpoint
        self.app.route(f'/{self.app_name}/scrub_timeline', methods=['GET', 'POST'])(self.scrub_timeline)

        self.step_messages = {
            'finalize': {
                'ready': f'{self.ui["EMOJIS"]["SUCCESS"]} All steps complete. Ready to finalize timeline inspection.',
                'complete': f'{self.ui["EMOJIS"]["COMPLETION"]} Workflow finalized. Use {self.ui["BUTTON_LABELS"]["UNLOCK"]} to make changes.'
            },
            'step_01': {
                'input': f'{self.ui["EMOJIS"]["INPUT_FORM"]} Select or type a target repository file to scrub.',
                'complete': f'{self.ui["EMOJIS"]["SUCCESS"]} Target file loaded. Proceeding to timeline scrubber.'
            },
            'step_02': {
                'input': f'{self.ui["EMOJIS"]["INPUT_FORM"]} Drag the slider or use buttons to scrub through commit diffs.',
                'complete': f'{self.ui["EMOJIS"]["SUCCESS"]} Timeline position locked.'
            }
        }

    def _resolve_repo_path(self, target_file: str) -> str:
        """Resolve a user-provided file path to a valid repo-relative tracked path."""
        clean_path = target_file.strip().lstrip('./')
        repo_root = Path(os.environ.get('PIPULATE_ROOT', os.getcwd()))
        if Path(clean_path).is_absolute():
            try:
                clean_path = str(Path(clean_path).resolve().relative_to(repo_root.resolve()))
            except ValueError:
                pass

        if not (repo_root / clean_path).exists():
            if (repo_root / 'apps' / clean_path).exists():
                return f'apps/{clean_path}'
            try:
                res = subprocess.run(['git', 'ls-files'], cwd=str(repo_root), capture_output=True, text=True, check=True)
                for tf in res.stdout.splitlines():
                    tf = tf.strip()
                    if Path(tf).name == clean_path or tf.endswith(f"/{clean_path}"):
                        return tf
            except Exception:
                pass
        return clean_path

    def _get_file_commits(self, target_file: str, force_refresh: bool = False):
        """Retrieve all commits that touched target_file, oldest first (following renames)."""
        clean_path = self._resolve_repo_path(target_file)
        repo_root = Path(os.environ.get('PIPULATE_ROOT', os.getcwd()))

        if not force_refresh and clean_path in self._commits_cache:
            return self._commits_cache[clean_path], clean_path

        # CRITICAL FIX: DO NOT pass --reverse to git log with --follow!
        # git log --follow --reverse breaks rename traversal in Git and truncates history to 1 commit.
        # We query newest-to-oldest with --name-status, then reverse in Python.
        cmd = [
            'git', 'log', '--follow', '--name-status',
            '--format=COMMIT:%H|%h|%ad|%an|%s', '--date=short',
            '--', clean_path
        ]
        try:
            res = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, check=True)
            raw_output = res.stdout
        except Exception as e:
            logger.warning(f"Error reading git log for {clean_path}: {e}")
            return [], clean_path

        commits = []
        current_commit = None
        for line in raw_output.split('\n'):
            line = line.strip()
            if not line:
                continue
            if line.startswith('COMMIT:'):
                if current_commit:
                    commits.append(current_commit)
                meta_str = line[len('COMMIT:'):]
                current_commit = {
                    'meta': meta_str,
                    'file_at_commit': clean_path
                }
            elif current_commit and '\t' in line:
                parts = line.split('\t')
                status = parts[0]
                if status.startswith('R') and len(parts) >= 3:
                    current_commit['file_at_commit'] = parts[1]  # old path prior to rename
                    current_commit['rename_target'] = parts[2]
                elif len(parts) >= 2:
                    current_commit['file_at_commit'] = parts[1]

        if current_commit:
            commits.append(current_commit)

        # Reverse so index 0 = oldest, index -1 = newest
        commits.reverse()
        self._commits_cache[clean_path] = commits
        return commits, clean_path

    def _get_commit_diff(self, clean_path: str, commit_item):
        """Extract metadata and diff for a specific commit and file, handling renames."""
        if isinstance(commit_item, dict):
            commit_line = commit_item['meta']
            file_at_commit = commit_item.get('file_at_commit', clean_path)
            rename_target = commit_item.get('rename_target')
        else:
            commit_line = str(commit_item)
            file_at_commit = clean_path
            rename_target = None

        parts = commit_line.split('|', 4)
        if len(parts) == 5:
            full_hash, short_hash, commit_date, author, subject = parts
        else:
            full_hash = parts[0]
            short_hash, commit_date, author, subject = full_hash[:8], "unknown", "unknown", ""

        repo_root = Path(os.environ.get('PIPULATE_ROOT', os.getcwd()))

        paths_to_try = [file_at_commit]
        if clean_path not in paths_to_try:
            paths_to_try.append(clean_path)
        if rename_target and rename_target not in paths_to_try:
            paths_to_try.append(rename_target)

        diff_text = ""
        for p in paths_to_try:
            cmd = ['git', 'show', '--color=never', '--patch', full_hash, '--', p]
            try:
                res = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
                if res.returncode == 0 and res.stdout.strip():
                    diff_text = res.stdout.strip()
                    break
            except Exception:
                pass

        if not diff_text:
            try:
                res_all = subprocess.run(['git', 'show', '--color=never', '--patch', full_hash],
                                         cwd=str(repo_root), capture_output=True, text=True)
                if res_all.returncode == 0 and res_all.stdout.strip():
                    full_output = res_all.stdout.strip()
                    sections = re.split(r'(?m)(?=^diff --git )', full_output)
                    matching = [sec for sec in sections if any(f"/{p}" in sec or f" {p}" in sec or f"b/{p}" in sec or f"a/{p}" in sec for p in paths_to_try)]
                    diff_text = "\n".join(matching).strip() if matching else full_output
            except Exception as e:
                diff_text = f"Error running git show: {e}"

        return {
            'full_hash': full_hash,
            'short_hash': short_hash,
            'date': commit_date,
            'author': author,
            'subject': subject,
            'diff': diff_text
        }

    def _render_diff_view(self, clean_path: str, commits: list, index: int):
        """Render the metadata card, diff viewport, and Prism script trigger."""
        if not commits:
            return Div(
                P(f"No git history found for '{clean_path}'. Verify the file path.", cls="text-invalid"),
                id="diff-viewport"
            )

        index = max(0, min(index, len(commits) - 1))
        meta = self._get_commit_diff(clean_path, commits[index])

        metadata_card = Div(
            Div(
                Span(f"Commit {index + 1} of {len(commits)}", cls="badge", style="background: var(--pico-primary); color: white; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: bold; margin-right: 0.5rem;"),
                Code(meta['short_hash'], style="font-weight: bold; margin-right: 0.5rem;"),
                Span(f"{meta['date']} · {meta['author']}", cls="text-secondary"),
                style="margin-bottom: 0.25rem;"
            ),
            P(meta['subject'] or "(no commit message)", title=meta['subject'] or "", style="margin-bottom: 0; font-weight: 500; font-size: 0.95rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"),
            style="padding: 0.75rem 1rem; background: var(--pico-card-background-color); border: 1px solid var(--pico-muted-border-color); border-radius: var(--pico-border-radius); margin-bottom: 0.75rem; min-height: 4.2rem;"
        )

        diff_content = meta['diff'] or "(Empty diff: file mode or metadata change only)"

        diff_box = Pre(
            Code(diff_content, cls="language-diff"),
            id="diff-code-pre",
            cls="language-diff",
            onscroll="if (!window._slider_restoring) { window._slider_pre_scrollTop = this.scrollTop; window._slider_pre_scrollLeft = this.scrollLeft; }",
            style="max-height: 55vh; overflow-y: auto; overflow-x: auto; margin-bottom: 0; background: #111;"
        )

        prism_script = Script("""
            (function() {
                const vp = document.getElementById('diff-viewport');
                if (typeof Prism !== 'undefined' && vp) {
                    Prism.highlightAllUnder(vp);
                }
                const restore = function() {
                    window._slider_restoring = true;
                    const p = document.getElementById('diff-code-pre') || (vp ? vp.querySelector('pre') : null);
                    if (p && typeof window._slider_pre_scrollTop === 'number') {
                        p.scrollTop = window._slider_pre_scrollTop;
                        if (typeof window._slider_pre_scrollLeft === 'number') {
                            p.scrollLeft = window._slider_pre_scrollLeft;
                        }
                    }
                    const g = document.getElementById('grid-left-content');
                    if (g && typeof window._slider_grid_scrollTop === 'number') {
                        g.scrollTop = window._slider_grid_scrollTop;
                    }
                    if (typeof window._slider_win_scrollY === 'number') {
                        window.scrollTo(window.scrollX, window._slider_win_scrollY);
                    }
                    setTimeout(function() { window._slider_restoring = false; }, 60);
                };
                restore();
                requestAnimationFrame(restore);
            })();
        """)

        return Div(
            metadata_card,
            diff_box,
            prism_script,
            id="diff-viewport"
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
            self.wand.speak("Your workflow has been recovered.", wait=False)
        elif not any((step.id in state for step in self.steps)):
            await self.message_queue.add(wand, f'{self.ui["EMOJIS"]["INPUT_FORM"]} Select a file and scrub its git timeline.', verbatim=True)
            self.wand.speak("Git Slider initialized. Please select a file to begin.", wait=False)

        parsed = wand.parse_pipeline_key(pipeline_id)
        prefix = f"{parsed['profile_part']}-{parsed['plugin_part']}-"
        self.pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in self.pipeline() if record.pkey.startswith(prefix)]
        if pipeline_id not in matching_records:
            matching_records.append(pipeline_id)
        wand.update_datalist('pipeline-ids', options=matching_records)
        return wand.run_all_cells(app_name, steps)

    async def scrub_timeline(self, request):
        """Dynamic HTMX endpoint returning commit diff on range input or button click."""
        form_data = await request.form()
        try:
            index = int(form_data.get('timeline_index', 0))
        except (ValueError, TypeError):
            index = 0

        target_file = form_data.get('target_file', '')
        if not target_file:
            pipeline_id = self.wand.db.get('pipeline_id', 'unknown')
            step_01_data = self.wand.get_step_data(pipeline_id, 'step_01', {})
            target_file = step_01_data.get('target_file', 'foo_files.py')

        commits, clean_path = self._get_file_commits(target_file)
        return self._render_diff_view(clean_path, commits, index)

    # --- START_STEP_BUNDLE: step_01 ---
    async def step_01(self, request):
        """Displays target file selection form."""
        wand, steps, app_name = self.wand, self.steps, self.app_name
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index + 1 < len(steps) else 'finalize'
        pipeline_id = wand.db.get('pipeline_id', 'unknown')
        state = wand.read_state(pipeline_id)
        step_data = wand.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, '')
        finalize_data = wand.get_step_data(pipeline_id, 'finalize', {})

        if 'finalized' in finalize_data and user_val:
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
            repo_root = Path(os.environ.get('PIPULATE_ROOT', os.getcwd()))
            try:
                res = subprocess.run(['git', 'ls-files'], cwd=str(repo_root), capture_output=True, text=True, check=True)
                tracked_files = [f for f in res.stdout.split('\n') if f.strip() and f.endswith(('.py', '.md', '.nix', '.json', '.html', '.css', '.js'))]
            except Exception:
                tracked_files = ['foo_files.py', 'server.py', 'apply.py', 'apps/040_hello_workflow.py']

            current_val = user_val if (step.refill and user_val) else 'foo_files.py'
            quick_files = ['foo_files.py', 'server.py', 'apply.py', 'apps/040_hello_workflow.py', 'apps/830_pico_slider.py', 'apps/911_optics_workflow.py', 'assets/styles.css']

            quick_buttons = Div(
                Span("Quick picks: ", cls="text-secondary", style="font-size: 0.85rem; margin-right: 0.5rem;"),
                *[
                    Button(
                        qf,
                        type="button",
                        cls="secondary outline",
                        onclick=f"document.getElementById('target-file-input').value = '{qf}'; document.getElementById('target-file-input').focus();",
                        style="font-size: 0.75rem; padding: 0.2rem 0.5rem; margin: 0.2rem;"
                    )
                    for qf in quick_files if qf in tracked_files or (repo_root / qf).exists()
                ],
                style="margin-bottom: 0.75rem; display: flex; flex-wrap: wrap; align-items: center;"
            )

            explanation = "Choose or type any tracked repository file path to explore its commit evolution."

            return Div(
                Article(
                    H3(f'{self.ui["EMOJIS"]["USER_INPUT"]} {step.show}'),
                    P(explanation, cls='text-muted'),
                    quick_buttons,
                    Label('File Path (type relative/absolute or select from datalist):', _for='target-file-input'),
                    Form(
                        Div(
                            Input(
                                type='text',
                                id='target-file-input',
                                name=step.done,
                                list='tracked-files-datalist',
                                value=current_val,
                                placeholder='e.g. foo_files.py, apply.py, or apps/040_hello_workflow.py',
                                required=True,
                                autofocus=True,
                                style='flex-grow: 1; margin-bottom: 0;'
                            ),
                            Button(
                                self.ui['BUTTON_LABELS']['NEXT_STEP'],
                                type='submit',
                                cls=self.ui['BUTTON_STYLES']['PRIMARY'],
                                style='margin-bottom: 0; white-space: nowrap;'
                            ),
                            style='display: flex; gap: 0.5rem; align-items: center;'
                        ),
                        Datalist(
                            *[Option(value=tf) for tf in tracked_files],
                            id='tracked-files-datalist'
                        ),
                        hx_post=f'/{app_name}/{step_id}_submit',
                        hx_target=f'#{step_id}',
                        id=f'{app_name}-step01-form'
                    ),
                    role='region'
                ),
                Div(id=next_step_id),
                id=step_id
            )

    async def step_01_submit(self, request):
        """Processes file selection and moves to timeline scrubber."""
        wand, steps, app_name = self.wand, self.steps, self.app_name
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = wand.db.get("pipeline_id", "unknown")

        form = await request.form()
        user_val = form.get(step.done, "").strip()
        if not user_val:
            user_val = "foo_files.py"

        commits, clean_path = self._get_file_commits(user_val, force_refresh=True)
        if not commits:
            error_msg = f"No git commits found for '{user_val}'. Please verify the path."
            await self.message_queue.add(wand, f"{self.ui['EMOJIS']['ERROR']} {error_msg}", verbatim=True)
            return P(error_msg, cls='text-invalid')

        await wand.set_step_data(pipeline_id, step_id, clean_path, steps)
        await self.message_queue.add(wand, f"{self.ui['EMOJIS']['SUCCESS']} Target set: {clean_path} ({len(commits)} commits)", verbatim=True)
        self.wand.speak(f"Target file set: {clean_path}. Ready to scrub timeline.", wait=False)
        self.wand.append_to_history(f"[WIDGET CONTENT] {step.show}:\n{clean_path}")

        return wand.chain_reverter(step_id, step_index, steps, app_name, clean_path)
    # --- END_STEP_BUNDLE: step_01 ---

    # --- START_STEP_BUNDLE: step_02 ---
    async def step_02(self, request):
        """Displays interactive Git timeline scrubber."""
        wand, steps, app_name = self.wand, self.steps, self.app_name
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index + 1 < len(steps) else 'finalize'
        pipeline_id = wand.db.get('pipeline_id', 'unknown')
        state = wand.read_state(pipeline_id)
        step_data = wand.get_step_data(pipeline_id, step_id, {})
        current_value = step_data.get(step.done, "")
        finalize_data = wand.get_step_data(pipeline_id, "finalize", {})

        target_file = wand.get_step_data(pipeline_id, 'step_01', {}).get('target_file', 'foo_files.py')
        commits, clean_path = self._get_file_commits(target_file)

        if "finalized" in finalize_data and current_value:
            return Div(
                Article(
                    H3(f'{self.ui["EMOJIS"]["LOCKED"]} {step.show}: {current_value}'),
                    role='region'
                ),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        elif current_value and state.get('_revert_target') != step_id:
            return Div(
                wand.display_revert_header(
                    step_id=step_id,
                    app_name=app_name,
                    message=f'{self.ui["EMOJIS"]["SUCCESS"]} {step.show}: {current_value}',
                    steps=steps
                ),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        else:
            num_commits = len(commits)
            current_idx = max(0, num_commits - 1)
            slider_max = str(max(0, num_commits - 1))

            hidden_target = Input(type="hidden", id="target-file-hidden", name="target_file", value=clean_path)

            range_slider = Input(
                type="range",
                name="timeline_index",
                id="timeline-range-slider",
                min="0",
                max=slider_max,
                value=str(current_idx),
                hx_post=f"/{app_name}/scrub_timeline",
                hx_target="#diff-viewport",
                hx_swap="outerHTML",
                hx_include="#target-file-hidden",
                hx_trigger="input delay:40ms",
                style="flex-grow: 1; cursor: pointer; margin-bottom: 0;"
            )

            prev_btn = Button(
                "◀ Older",
                type="button",
                cls="secondary outline",
                onclick="const s = document.getElementById('timeline-range-slider'); if(s && parseInt(s.value) > 0){ s.value = parseInt(s.value) - 1; s.dispatchEvent(new Event('input', {bubbles: true})); }",
                style="margin-bottom: 0; padding: 0.4rem 0.8rem; font-size: 0.85rem;"
            )

            next_btn = Button(
                "Newer ▶",
                type="button",
                cls="secondary outline",
                onclick="const s = document.getElementById('timeline-range-slider'); if(s && parseInt(s.value) < parseInt(s.max)){ s.value = parseInt(s.value) + 1; s.dispatchEvent(new Event('input', {bubbles: true})); }",
                style="margin-bottom: 0; padding: 0.4rem 0.8rem; font-size: 0.85rem;"
            )

            slider_controls = Div(
                prev_btn,
                range_slider,
                next_btn,
                style="display: flex; align-items: center; gap: 0.75rem; margin: 0.75rem 0;"
            )

            initial_diff_viewport = self._render_diff_view(clean_path, commits, current_idx)

            diff_styles = Style("""
                .token.inserted, pre[class*="language-"] .token.inserted, code[class*="language-"] .token.inserted {
                    color: #2ea043 !important;
                    background-color: rgba(46, 160, 67, 0.15) !important;
                }
                .token.deleted, pre[class*="language-"] .token.deleted, code[class*="language-"] .token.deleted {
                    color: #f85149 !important;
                    background-color: rgba(248, 81, 73, 0.15) !important;
                }
                .token.coord, pre[class*="language-"] .token.coord {
                    color: #58a6ff !important;
                    font-weight: bold;
                }
            """)

            return Div(
                diff_styles,
                Article(
                    H3(f'{self.ui["EMOJIS"]["WORKFLOW"]} {step.show}: {clean_path}'),
                    P("Drag the slider or use ◀ / ▶ buttons to scrub through commit diffs.", cls='text-muted'),
                    Form(
                        hidden_target,
                        slider_controls,
                        initial_diff_viewport,
                        Br(),
                        Button("Lock Selection & Proceed ▸", type="submit", cls=self.ui['BUTTON_STYLES']['PRIMARY']),
                        hx_post=f"/{app_name}/{step_id}_submit",
                        hx_target=f"#{step_id}",
                        id=f"{app_name}-step02-form"
                    ),
                    role='region'
                ),
                Div(id=next_step_id),
                id=step_id
            )

    async def step_02_submit(self, request):
        """Saves locked timeline position and chains to finalize."""
        wand, steps, app_name = self.wand, self.steps, self.app_name
        step_id = 'step_02'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = wand.db.get("pipeline_id", "unknown")

        target_file = wand.get_step_data(pipeline_id, 'step_01', {}).get('target_file', 'foo_files.py')
        commits, clean_path = self._get_file_commits(target_file)

        form_data = await request.form()
        try:
            selected_index = int(form_data.get('timeline_index', 0))
        except (ValueError, TypeError):
            selected_index = 0

        if commits and 0 <= selected_index < len(commits):
            meta = self._get_commit_diff(clean_path, commits[selected_index])
            saved_val = f"Commit {meta['short_hash']} ({meta['date']}): {meta['subject'][:45]}"
        else:
            saved_val = f"Index {selected_index}"

        await wand.set_step_data(pipeline_id, step_id, saved_val, steps)
        await self.message_queue.add(wand, f"{self.ui['EMOJIS']['SUCCESS']} Position locked: {saved_val}", verbatim=True)
        self.wand.speak("Timeline locked. All steps complete.", wait=False)
        self.wand.append_to_history(f"[WIDGET CONTENT] {step.show}:\n{saved_val}")

        return wand.chain_reverter(step_id, step_index, steps, app_name, saved_val)
    # --- END_STEP_BUNDLE: step_02 ---

    # --- STEP_METHODS_INSERTION_POINT ---

    async def finalize(self, request):
        wand, steps, app_name = self.wand, self.steps, self.app_name
        pipeline_id = wand.db.get('pipeline_id', 'unknown')
        finalize_step = steps[-1]
        finalize_data = wand.get_step_data(pipeline_id, finalize_step.id, {})

        if request.method == 'GET':
            if finalize_step.done in finalize_data:
                return Article(
                    H3(f'{self.ui["EMOJIS"]["LOCKED"]} {self.ui["MESSAGES"]["WORKFLOW_LOCKED"]}'),
                    P("Timeline inspection locked. Unlock to scrub again or inspect another file.", cls='text-muted'),
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
                all_steps_complete = all((wand.get_step_data(pipeline_id, s.id, {}).get(s.done) for s in steps[:-1]))
                if all_steps_complete:
                    return Article(
                        H3(f'{self.ui["EMOJIS"]["SUCCESS"]} {self.ui["MESSAGES"]["FINALIZE_QUESTION"]}'),
                        P("Finalizing will lock your audit position.", cls='text-muted'),
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
            await wand.finalize_workflow(pipeline_id)
            await self.message_queue.add(wand, self.step_messages['finalize']['complete'], verbatim=True)
            self.wand.speak("The workflow is now locked and finalized.", wait=False)
            return wand.run_all_cells(app_name, steps)

    async def unfinalize(self, request):
        wand, steps, app_name = self.wand, self.steps, self.app_name
        pipeline_id = wand.db.get('pipeline_id', 'unknown')
        await wand.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(wand, f'{self.ui["EMOJIS"]["UNLOCKED"]} {self.ui["MESSAGES"]["WORKFLOW_UNLOCKED"]}', verbatim=True)
        self.wand.speak("Workflow unlocked. You may now revert to any step.", wait=False)
        return wand.run_all_cells(app_name, steps)

    async def get_suggestion(self, step_id, state):
        return ''

    async def handle_revert(self, request):
        wand, steps, app_name = self.wand, self.steps, self.app_name
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

# File: apps/840_git_slider.py
import os
import re
import subprocess
from pathlib import Path
from fasthtml.common import *  # type: ignore
from loguru import logger

ROLES = ['Developer', 'Core']


class GitSliderFlow:
    """
    Git Slider (Keyless Explorer)
    An interactive Moviola scrub slider through the Git commit diff history
    of any tracked repository file. Jumps straight into file selection and
    timeline scrubbing without requiring a workflow key.
    """
    APP_NAME = 'git_slider'
    DISPLAY_NAME = 'Git Slider 🎚'
    ENDPOINT_MESSAGE = 'Welcome to the Git Slider. Pick any file or click a quick-pick button to scrub through its commit history.'
    TRAINING_PROMPT = 'This app uses HTMX and a range input to scrub through the real git history of any tracked file in the repository.'

    QUICK_FILES = [
        'foo_files.py',
        'server.py',
        'apply.py',
        'apps/040_hello_workflow.py',
        'apps/830_pico_slider.py',
        'apps/840_git_slider.py',
        'apps/911_optics_workflow.py',
        'assets/styles.css',
    ]

    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
        self.pipulate = pipulate
        self.app = app
        self.app_name = app_name
        self.pipeline = pipeline
        self.wand = pipulate
        self.db = db
        self.message_queue = self.wand.get_message_queue()
        self.ui = self.wand.get_ui_constants()
        self._commits_cache = {}

        # Register dynamic HTMX endpoints for instant file switching and timeline scrubbing
        self.app.route(f'/{self.app_name}/select_file', methods=['GET', 'POST'])(self.select_file)
        self.app.route(f'/{self.app_name}/scrub_timeline', methods=['GET', 'POST'])(self.scrub_timeline)

    def _get_tracked_files(self) -> list:
        repo_root = Path(os.environ.get('PIPULATE_ROOT', os.getcwd()))
        try:
            res = subprocess.run(['git', 'ls-files'], cwd=str(repo_root), capture_output=True, text=True, check=True)
            return [
                f for f in res.stdout.split('\n')
                if f.strip() and f.endswith(('.py', '.md', '.nix', '.json', '.html', '.css', '.js', '.sh', '.toml', '.txt', '.yaml', '.yml'))
            ]
        except Exception:
            return list(self.QUICK_FILES)

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

        # CRITICAL: DO NOT pass --reverse to git log with --follow!
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
        if rename_target and rename_target != file_at_commit:
            cmd_rename = ['git', 'show', '-M', '--color=never', '--patch', full_hash, '--', file_at_commit, rename_target]
            try:
                res = subprocess.run(cmd_rename, cwd=str(repo_root), capture_output=True, text=True)
                if res.returncode == 0 and res.stdout.strip():
                    diff_text = res.stdout.strip()
            except Exception:
                pass
        if not diff_text:
            for p in paths_to_try:
                cmd = ['git', 'show', '-M', '--color=never', '--patch', full_hash, '--', p]
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
            Code(diff_content, cls="language-diff", style="font-size: 0.72rem; line-height: 1.35;"),
            id="diff-code-pre",
            cls="language-diff",
            onscroll="if (!window._slider_restoring) { window._slider_pre_scrollTop = this.scrollTop; window._slider_pre_scrollLeft = this.scrollLeft; }",
            style="max-height: 62vh; overflow-y: auto; overflow-x: auto; margin-bottom: 0; background: #111; font-size: 0.72rem; line-height: 1.35; padding: 0.75rem;"
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

    def _render_scrubber_deck(self, clean_path: str, commits: list):
        """Render the slider controls and diff viewport for a selected file."""
        num_commits = len(commits)
        current_idx = max(0, num_commits - 1)
        slider_max = str(max(0, num_commits - 1))

        hidden_target = Input(type="hidden", id="target-file-hidden", name="target_file", value=clean_path)

        save_scroll_snippet = (
            "const p = document.getElementById('diff-code-pre'); "
            "if(p){ window._slider_pre_scrollTop = p.scrollTop; window._slider_pre_scrollLeft = p.scrollLeft; } "
            "const g = document.getElementById('grid-left-content'); "
            "if(g){ window._slider_grid_scrollTop = g.scrollTop; } "
            "window._slider_win_scrollY = window.scrollY;"
        )

        range_slider = Input(
            type="range",
            name="timeline_index",
            id="timeline-range-slider",
            min="0",
            max=slider_max,
            value=str(current_idx),
            hx_post=f"/{self.app_name}/scrub_timeline",
            hx_target="#diff-viewport",
            hx_swap="outerHTML show:none",
            hx_include="#target-file-hidden",
            hx_trigger="input delay:40ms",
            oninput=save_scroll_snippet,
            style="flex-grow: 1; cursor: pointer; margin-bottom: 0;"
        )

        prev_btn = Button(
            "◀ Older",
            type="button",
            cls="secondary outline",
            onclick=save_scroll_snippet + " const s = document.getElementById('timeline-range-slider'); if(s && parseInt(s.value) > 0){ s.value = parseInt(s.value) - 1; s.dispatchEvent(new Event('input', {bubbles: true})); }",
            style="margin-bottom: 0; padding: 0.4rem 0.8rem; font-size: 0.85rem;"
        )

        next_btn = Button(
            "Newer ▶",
            type="button",
            cls="secondary outline",
            onclick=save_scroll_snippet + " const s = document.getElementById('timeline-range-slider'); if(s && parseInt(s.value) < parseInt(s.max)){ s.value = parseInt(s.value) + 1; s.dispatchEvent(new Event('input', {bubbles: true})); }",
            style="margin-bottom: 0; padding: 0.4rem 0.8rem; font-size: 0.85rem;"
        )

        slider_controls = Div(
            prev_btn,
            range_slider,
            next_btn,
            style="display: flex; align-items: center; gap: 0.75rem; margin: 0.5rem 0 0.75rem 0; position: sticky; top: 0; z-index: 20; background: var(--pico-background-color); padding: 0.5rem 0;"
        )

        return Div(
            Div(
                Span(f"📂 {clean_path}", style="font-weight: 600; font-family: monospace; font-size: 0.95rem;"),
                Span(f" ({num_commits} commits)", cls="text-secondary", style="font-size: 0.85rem; margin-left: 0.35rem;"),
                style="margin-bottom: 0.25rem;"
            ),
            hidden_target,
            slider_controls,
            self._render_diff_view(clean_path, commits, current_idx),
            id="git-slider-deck"
        )

    async def landing(self, request):
        """Render the keyless Git Slider explorer immediately upon opening the app."""
        repo_root = Path(os.environ.get('PIPULATE_ROOT', os.getcwd()))
        tracked_files = self._get_tracked_files()
        last_file = self.db.get('git_slider_last_file', 'foo_files.py')
        commits, clean_path = self._get_file_commits(last_file)
        if not commits:
            clean_path = 'foo_files.py'
            commits, clean_path = self._get_file_commits(clean_path)

        quick_buttons = Div(
            Span("Quick picks: ", cls="text-secondary", style="font-size: 0.85rem; margin-right: 0.4rem;"),
            *[
                Button(
                    qf,
                    type="button",
                    cls="secondary outline",
                    hx_post=f"/{self.app_name}/select_file",
                    hx_vals=f'{{"target_file": "{qf}"}}',
                    hx_target="#git-slider-deck",
                    hx_swap="outerHTML show:none",
                    onclick=f"document.getElementById('target-file-input').value = '{qf}'; window._slider_pre_scrollTop = 0; window._slider_pre_scrollLeft = 0;",
                    style="font-size: 0.75rem; padding: 0.2rem 0.5rem; margin: 0.15rem;"
                )
                for qf in self.QUICK_FILES if qf in tracked_files or (repo_root / qf).exists()
            ],
            style="margin-bottom: 0.6rem; display: flex; flex-wrap: wrap; align-items: center;"
        )

        file_picker_form = Form(
            Div(
                Input(
                    type='text',
                    id='target-file-input',
                    name='target_file',
                    list='tracked-files-datalist',
                    value=clean_path,
                    placeholder='Type or select any tracked file (e.g. foo_files.py, server.py, apply.py)',
                    required=True,
                    style='flex-grow: 1; margin-bottom: 0; font-family: monospace; font-size: 0.9rem;'
                ),
                Button(
                    "Load File ▸",
                    type='submit',
                    cls=self.ui['BUTTON_STYLES']['PRIMARY'],
                    style='margin-bottom: 0; white-space: nowrap; padding: 0.5rem 1rem;'
                ),
                style='display: flex; gap: 0.5rem; align-items: center;'
            ),
            Datalist(
                *[Option(value=tf) for tf in tracked_files],
                id='tracked-files-datalist'
            ),
            hx_post=f'/{self.app_name}/select_file',
            hx_target='#git-slider-deck',
            hx_swap='outerHTML show:none',
            onsubmit="window._slider_pre_scrollTop = 0; window._slider_pre_scrollLeft = 0;",
            style="margin-bottom: 0.75rem;"
        )

        diff_styles = Style("""
            #diff-code-pre, #diff-code-pre code {
                font-size: 0.72rem !important;
                line-height: 1.35 !important;
            }
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

        scroll_listener_script = Script("""
            (function() {
                const g = document.getElementById('grid-left-content');
                if (g && !g._sliderScrollBound) {
                    g.addEventListener('scroll', function() {
                        if (!window._slider_restoring) {
                            window._slider_grid_scrollTop = g.scrollTop;
                        }
                    });
                    g._sliderScrollBound = true;
                }
                if (!window._htmxSliderSwapBound) {
                    document.body.addEventListener('htmx:beforeSwap', function(evt) {
                        if (evt.detail.target && (evt.detail.target.id === 'diff-viewport' || evt.detail.target.querySelector('#diff-viewport'))) {
                            const p = document.getElementById('diff-code-pre') || document.querySelector('#diff-viewport pre');
                            if (p) {
                                window._slider_pre_scrollTop = p.scrollTop;
                                window._slider_pre_scrollLeft = p.scrollLeft;
                            }
                            if (g) {
                                window._slider_grid_scrollTop = g.scrollTop;
                            }
                            window._slider_win_scrollY = window.scrollY;
                        }
                    });
                    document.body.addEventListener('htmx:afterSettle', function(evt) {
                        if (evt.detail.target && (evt.detail.target.id === 'diff-viewport' || evt.detail.target.querySelector('#diff-viewport'))) {
                            window._slider_restoring = true;
                            const p = document.getElementById('diff-code-pre') || document.querySelector('#diff-viewport pre');
                            if (p && typeof window._slider_pre_scrollTop === 'number') {
                                p.scrollTop = window._slider_pre_scrollTop;
                                if (typeof window._slider_pre_scrollLeft === 'number') {
                                    p.scrollLeft = window._slider_pre_scrollLeft;
                                }
                            }
                            if (g && typeof window._slider_grid_scrollTop === 'number') {
                                g.scrollTop = window._slider_grid_scrollTop;
                            }
                            if (typeof window._slider_win_scrollY === 'number') {
                                window.scrollTo(window.scrollX, window._slider_win_scrollY);
                            }
                            setTimeout(function() { window._slider_restoring = false; }, 60);
                        }
                    });
                    window._htmxSliderSwapBound = true;
                }
            })();
        """)

        return Div(
            diff_styles,
            scroll_listener_script,
            Article(
                Header(
                    H3(f"{self.DISPLAY_NAME} — Repository Timeline Explorer", style="margin-bottom: 0.2rem;"),
                    P("Click a quick-pick file or type any tracked path, then drag the slider to scrub its Git history.", cls="text-muted", style="margin-bottom: 0; font-size: 0.85rem;")
                ),
                quick_buttons,
                file_picker_form,
                self._render_scrubber_deck(clean_path, commits),
                role="region"
            ),
            id=f"{self.app_name}-container"
        )

    async def select_file(self, request):
        """HTMX endpoint that loads a newly selected file's commit timeline in one click."""
        form_data = await request.form()
        target_file = form_data.get('target_file', '').strip()
        if not target_file:
            target_file = request.query_params.get('target_file', 'foo_files.py').strip()
        if not target_file:
            target_file = 'foo_files.py'

        commits, clean_path = self._get_file_commits(target_file, force_refresh=True)
        if not commits:
            return Div(
                P(f"No git commits found for '{target_file}'. Please verify the path.", cls="text-invalid"),
                id="git-slider-deck"
            )

        self.db['git_slider_last_file'] = clean_path
        return self._render_scrubber_deck(clean_path, commits)

    async def scrub_timeline(self, request):
        """Dynamic HTMX endpoint returning commit diff on range input or button click."""
        form_data = await request.form()
        try:
            index = int(form_data.get('timeline_index', 0))
        except (ValueError, TypeError):
            index = 0

        target_file = form_data.get('target_file', '').strip()
        if not target_file:
            target_file = self.db.get('git_slider_last_file', 'foo_files.py')

        commits, clean_path = self._get_file_commits(target_file)
        return self._render_diff_view(clean_path, commits, index)

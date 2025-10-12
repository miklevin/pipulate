#!/usr/bin/env python3
# prompt_foo.py

import os
import re
import sys
import pydot
import yaml
import argparse
import tiktoken
import subprocess
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple

try:
    import jupytext
    JUPYTEXT_AVAILABLE = True
except ImportError:
    JUPYTEXT_AVAILABLE = False

# Hello there, AI! This is a tool for generating a single, comprehensive prompt
# from the command line, bundling codebase files and auto-generated context
# into a structured Markdown format for effective AI assistance.

# ============================================================================
# --- Configuration ---
# ============================================================================
def find_repo_root(start_path: str) -> str:
    """Find the git repository root from a starting path."""
    path = os.path.abspath(start_path)
    while path != os.path.dirname(path):
        if os.path.isdir(os.path.join(path, '.git')):
            return path
        path = os.path.dirname(path)
    raise FileNotFoundError("Could not find the repository root (.git directory).")

REPO_ROOT = find_repo_root(os.path.dirname(__file__))

CONFIG = {
    "PROJECT_NAME": "pipulate",
    "POSTS_DIRECTORY": "/home/mike/repos/MikeLev.in/_posts"
}

# ============================================================================
# --- Literary Size Scale & Token/Word Counting ---
# ============================================================================
LITERARY_SIZE_SCALE = [
    (3000, "Short Essay"), (7500, "Short Story"), (20000, "Novelette"),
    (50000, "Novella or a Master's Dissertation"),
    (80000, "Average Paperback Novel or a Ph.D. Dissertation"),
    (120000, "Long Novel"), (200000, "Epic Fantasy Novel"),
    (500000, "Seriously Long Epic (like 'Infinite Jest')"),
]

def get_literary_perspective(word_count: int, token_word_ratio: float) -> str:
    description = f"Longer than {LITERARY_SIZE_SCALE[-1][1]}"
    for words, desc in LITERARY_SIZE_SCALE:
        if word_count <= words:
            description = desc
            break
    density_warning = ""
    if token_word_ratio > 1.8:
        density_warning = (
            f" (Note: With a token/word ratio of {token_word_ratio:.2f}, "
            f"this content is far denser and more complex than typical prose of this length)."
        )
    return f"📚 Equivalent in length to a **{description}**{density_warning}"

def count_tokens(text: str, model: str = "gpt-4o") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        return len(text.split())

def count_words(text: str) -> int:
    return len(text.split())

# ============================================================================
# --- Auto-Context Generation (UML, Tree, Narrative) ---
# ============================================================================
def generate_uml_and_dot(target_file: str, project_name: str) -> Dict:
    # This function remains unchanged.
    pyreverse_exec = shutil.which("pyreverse")
    plantuml_exec = shutil.which("plantuml")
    if not pyreverse_exec or not plantuml_exec:
        msg = []
        if not pyreverse_exec: msg.append("`pyreverse` (from pylint)")
        if not plantuml_exec: msg.append("`plantuml`")
        return {"ascii_uml": f"Skipping: Required command(s) not found: {', '.join(msg)}."}

    target_path = os.path.join(REPO_ROOT, target_file)
    if not os.path.exists(target_path):
        return {"ascii_uml": f"Skipping: Target file for UML generation not found: {target_path}"}

    with tempfile.TemporaryDirectory() as temp_dir:
        dot_file_path = os.path.join(temp_dir, "classes.dot")
        puml_file_path = os.path.join(temp_dir, "diagram.puml")
        try:
            pyreverse_cmd = [pyreverse_exec, "-f", "dot", "-o", "dot", "-p", project_name, target_path]
            subprocess.run(pyreverse_cmd, check=True, capture_output=True, text=True, cwd=temp_dir)
            generated_dot_name = f"classes_{project_name}.dot"
            os.rename(os.path.join(temp_dir, generated_dot_name), dot_file_path)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            error_msg = e.stderr if hasattr(e, 'stderr') else str(e)
            return {"ascii_uml": f"Error: pyreverse failed. {error_msg}", "dot_graph": None}

        try:
            graphs = pydot.graph_from_dot_file(dot_file_path)
            if not graphs:
                return {"ascii_uml": f"Note: No classes found in {target_file} to generate a diagram.", "dot_graph": None}
            graph = graphs[0]
            dot_content = graph.to_string()
            puml_lines = ["@startuml", "skinparam linetype ortho", ""]
            def sanitize_line(line):
                clean = re.sub(r'<br[^>]*>', '', line)
                clean = re.sub(r'<[^>]+>', '', clean)
                return clean.strip()
            for node in graph.get_nodes():
                label = node.get_label()
                if not label: continue
                parts = label.strip('<>{} ').split('|')
                class_name = sanitize_line(parts[0])
                puml_lines.append(f"class {class_name} {{")
                if len(parts) > 1:
                    for attr in re.split(r'<br[^>]*>', parts[1]):
                        clean_attr = sanitize_line(attr).split(':')[0].strip()
                        if clean_attr: puml_lines.append(f"  - {clean_attr}")
                if len(parts) > 2:
                    method_block = parts[2].strip()
                    for method_line in re.split(r'<br[^>]*>', method_block):
                        clean_method = sanitize_line(method_line)
                        if clean_method: puml_lines.append(f"  + {clean_method}")
                puml_lines.append("}\n")
            for edge in graph.get_edges():
                source_name = edge.get_source().strip('"').split('.')[-1]
                dest_name = edge.get_destination().strip('"').split('.')[-1]
                puml_lines.append(f"{source_name} ..> {dest_name}")
            puml_lines.append("@enduml")
            with open(puml_file_path, 'w') as f: f.write('\n'.join(puml_lines))
        except Exception as e:
            with open(dot_file_path, 'r') as f: dot_content_on_error = f.read()
            return {"ascii_uml": f"Error: DOT to PUML conversion failed. {str(e)}", "dot_graph": dot_content_on_error}

        try:
            plantuml_cmd = ["plantuml", "-tutxt", puml_file_path]
            subprocess.run(plantuml_cmd, check=True, capture_output=True, text=True, cwd=temp_dir)
            utxt_file_path = puml_file_path.replace(".puml", ".utxt")
            with open(utxt_file_path, 'r') as f: ascii_uml = f.read()
            lines = ascii_uml.splitlines()
            non_empty_lines = [line for line in lines if line.strip()]
            if non_empty_lines:
                min_indent = min(len(line) - len(line.lstrip(' ')) for line in non_empty_lines)
                dedented_lines = [line[min_indent:] for line in lines]
                stripped_lines = [line.rstrip() for line in dedented_lines]
                ascii_uml = '\n'.join(stripped_lines)
                if ascii_uml: ascii_uml = '\n' + ascii_uml
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            error_msg = e.stderr if hasattr(e, 'stderr') else str(e)
            return {"ascii_uml": f"Error: plantuml failed. {error_msg}", "dot_graph": dot_content}

    return {"ascii_uml": ascii_uml, "dot_graph": dot_content}

def _get_article_list_data(posts_dir: str = CONFIG["POSTS_DIRECTORY"]) -> List[Dict]:
    posts_data = []
    if not os.path.isdir(posts_dir):
        print(f"Warning: Article directory not found at {posts_dir}", file=sys.stderr)
        return []
    for filename in os.listdir(posts_dir):
        if not filename.endswith((".md", ".markdown")): continue
        filepath = os.path.join(posts_dir, filename)
        try:
            date_str = filename[:10]
            post_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            with open(filepath, 'r', encoding='utf-8') as f: content = f.read()
            if content.startswith('---'):
                parts = content.split('---', 2)
                front_matter = yaml.safe_load(parts[1]) or {}
                posts_data.append({
                    'path': filepath, 'date': post_date,
                    'sort_order': int(front_matter.get('sort_order', 0)),
                    'title': front_matter.get('title', 'Untitled'),
                    'summary': front_matter.get('meta_description', '')
                })
        except (ValueError, yaml.YAMLError, IndexError): continue
    return sorted(posts_data, key=lambda p: (p['date'], p['sort_order']))

def parse_slice_arg(arg_str: str):
    if not arg_str or not arg_str.startswith('[') or not arg_str.endswith(']'): return None
    content = arg_str[1:-1].strip()
    if ':' in content:
        parts = content.split(':', 1)
        start = int(parts[0].strip()) if parts[0].strip() else None
        end = int(parts[1].strip()) if parts[1].strip() else None
        return slice(start, end)
    elif content: return int(content)
    return slice(None, None) # CHANGE: Handle `[:]` to mean the whole list.

def run_tree_command() -> str:
    eza_exec = shutil.which("eza")
    if not eza_exec: return "Skipping: `eza` command not found."
    try:
        result = subprocess.run(
            [eza_exec, '--tree', '--git-ignore', '--color=never'],
            capture_output=True, text=True, cwd=REPO_ROOT, check=True
        )
        return result.stdout
    except Exception as e: return f"Error running eza command: {e}"

# ============================================================================
# --- Helper Functions (File Parsing, Clipboard) ---
# ============================================================================
def parse_file_list_from_config() -> List[Tuple[str, str]]:
    try:
        import foo_files
        files_raw = foo_files.FILES_TO_INCLUDE_RAW
    except (ImportError, AttributeError):
        print("ERROR: foo_files.py not found or doesn't contain FILES_TO_INCLUDE_RAW.")
        sys.exit(1)
    lines = files_raw.strip().splitlines()
    seen_files, parsed_files = set(), []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'): continue
        parts = re.split(r'\s*<--\s*|\s*#\s*', line, 1)
        file_path = parts[0].strip()
        comment = parts[1].strip() if len(parts) > 1 else ""
        if file_path and file_path not in seen_files:
            seen_files.add(file_path)
            parsed_files.append((file_path, comment))
    return parsed_files

def copy_to_clipboard(text: str):
    if not shutil.which('xclip'):
        print("\nWarning: 'xclip' not found. Cannot copy to clipboard.")
        return
    try:
        subprocess.run(['xclip', '-selection', 'clipboard'], input=text.encode('utf-8'), check=True)
        print("Markdown output copied to clipboard")
    except Exception as e:
        print(f"\nWarning: Could not copy to clipboard: {e}")

def check_dependencies():
    """Verifies that all required external command-line tools are installed."""
    print("Checking for required external dependencies...")
    dependencies = {
        "pyreverse": "Provided by `pylint`. Install with: pip install pylint",
        "plantuml": "A Java-based tool. See https://plantuml.com/starting",
        "eza": "A modern replacement for `ls`. See https://eza.rocks/install",
        "xclip": "Clipboard utility for Linux. Install with your package manager (e.g., sudo apt-get install xclip)",
    }
    missing = []
    for tool, instructions in dependencies.items():
        if not shutil.which(tool):
            missing.append((tool, instructions))
    
    if not missing:
        print("✅ All dependencies found.")
    else:
        print("\n❌ Missing dependencies detected:")
        for tool, instructions in missing:
            print(f"  - Command not found: `{tool}`")
            print(f"    ↳ {instructions}")
        print("\nPlease install the missing tools and ensure they are in your system's PATH.")
        sys.exit(1)

# ============================================================================
# --- Refined PromptBuilder Class ---
# ============================================================================
class PromptBuilder:
    """
    Builds a complete, structured Markdown prompt with consistent START/END markers
    for each section, including Manifest, Story, File Tree, UMLs, Codebase, and Prompt.
    """
    def __init__(self, processed_files: List[Dict], prompt_text: str, context_only: bool = False, list_arg: Optional[str] = None):
        self.processed_files = processed_files
        self.prompt_text = prompt_text
        self.context_only = context_only
        self.list_arg = list_arg # NEW: Keep track of whether the list flag was used
        self.auto_context = {}
        self.all_sections = {}

    def add_auto_context(self, title: str, content: str):
        # START: add_auto_context_method_body
        # --- START DEBUGGING BLOCK ---
        condition = bool(content and "error" not in content.lower() and "skipping" not in content.lower())
        print(f"\n[6] Inside add_auto_context for title '{title}': Condition to add is {condition}")
        # --- END DEBUGGING BLOCK ---
        if condition:
            self.auto_context[title] = {
                'content': content, 'tokens': count_tokens(content), 'words': count_words(content)
            }
        # END: add_auto_context_method_body

    def _build_manifest_content(self) -> str:
        lines = []
        # Ensure a consistent order for the manifest
        section_order = ["Story", "File Tree", "UML Diagrams", "Codebase", "Prompt"]
        for section_name in section_order:
            if section_name in self.all_sections:
                data = self.all_sections[section_name]
                token_str = f"({data['tokens']:,} tokens)" if data['tokens'] > 0 else ""
                lines.append(f"- {section_name} {token_str}")
        return "\n".join(lines)

    def _build_story_content(self) -> str:
        title = "Recent Narrative Context"
        return self.auto_context.get(title, {}).get('content', '').strip()

    def _build_tree_content(self) -> str:
        title = "Codebase Structure (eza --tree)"
        if title in self.auto_context:
            content = self.auto_context[title]['content'].strip()
            return f"```text\n{content}\n```"
        return ""

    def _build_uml_content(self) -> str:
        uml_parts = []
        for title, data in self.auto_context.items():
            if "UML Class Diagram" in title:
                uml_parts.append(f"## {title}\n```text\n{data['content']}\n```")
        return "\n\n".join(uml_parts)

    def _build_codebase_content(self) -> str:
        if self.context_only: return ""
        if not self.processed_files: return ""
        
        lines = []
        for f in self.processed_files:
            lines.append(f"--- START: {f['path']} ({f['tokens']:,} tokens) ---")
            lines.append(f"```{f['lang']}:{f['path']}")
            lines.append(f['content'])
            lines.append("```")
            lines.append(f"--- END: {f['path']} ---\n")
        return "\n".join(lines).strip()

    def _build_prompt_content(self) -> str:
        checklist = self._generate_ai_checklist()
        return f"{checklist}\n\n{self.prompt_text}"

    def _generate_ai_checklist(self) -> str:
        return '''# AI Self-Correction Checklist

Before addressing the user's prompt, perform the following verification steps:

1.  **Review the Manifest vs. Codebase Structure:** Compare the file list in the manifest against the `eza --tree` output. Are there any obviously related, critical files missing from the manifest that would be necessary to understand the user's request? (e.g., if `core.py` is present, is `__init__.py` also present?).
2.  **Analyze Import Statements:** Briefly scan the `import` statements in the provided Python files. Do they suggest dependencies on local files that were *not* included in the manifest?
3.  **Check for Incompleteness:** If you determine that critical files are missing, do not proceed. Instead, your **primary task** is to inform me of the missing files and recommend adding them to `foo_files.py` to create a more complete context.
4.  **Confirm Understanding:** If the context appears complete, state "Context verified." and then proceed with the user's request.
'''
    def build_final_prompt(self) -> str:
        """Assembles all parts into the final, structured Markdown string."""
        # Prepare content for all sections
        story_content = self._build_story_content()
        tree_content = self._build_tree_content()
        uml_content = self._build_uml_content()
        codebase_content = self._build_codebase_content()
        prompt_content = self._build_prompt_content()

        # Define placeholder messages
        placeholders = {
            "Story": f"# Narrative context not requested. Use the -l or --list flag to include recent articles.",
            "File Tree": "# File tree generation failed or was skipped.",
            "UML Diagrams": "# No Python files with classes were included, or UML generation failed.",
            "Codebase": ("# No files were specified for inclusion in the codebase." if not self.processed_files 
                         else "# Running in --context-only mode. File contents are omitted."),
        }

        # Store final content and tokens for the manifest calculation
        self.all_sections["Story"] = {'content': story_content, 'tokens': count_tokens(story_content)}
        self.all_sections["File Tree"] = {'content': tree_content, 'tokens': count_tokens(tree_content)}
        self.all_sections["UML Diagrams"] = {'content': uml_content, 'tokens': count_tokens(uml_content)}
        self.all_sections["Codebase"] = {'content': codebase_content, 'tokens': sum(f['tokens'] for f in self.processed_files) if not self.context_only else 0}
        self.all_sections["Prompt"] = {'content': prompt_content, 'tokens': count_tokens(prompt_content)}
        
        manifest_content = self._build_manifest_content()
        self.all_sections["Manifest"] = {'content': manifest_content, 'tokens': count_tokens(manifest_content)}

        # Assemble the final output string with START/END markers for all sections
        parts = ["# KUNG FU PROMPT CONTEXT\n\nWhat you will find below is:\n\n- Manifest\n- Story\n- File Tree\n- UML Diagrams\n- Codebase\n- Prompt"]

        def add_section(name, content, placeholder):
            final_content = content.strip() if content and content.strip() else placeholder
            parts.append(f"--- START: {name} ---\n{final_content}\n--- END: {name} ---")

        add_section("Manifest", manifest_content, "# Manifest generation failed.")
        # Special handling for story placeholder
        story_placeholder = placeholders["Story"] if self.list_arg is None else "# No articles found for the specified slice."
        add_section("Story", story_content, story_placeholder)
        add_section("File Tree", tree_content, placeholders["File Tree"])
        add_section("UML Diagrams", uml_content, placeholders["UML Diagrams"])
        add_section("Codebase", codebase_content, placeholders["Codebase"])
        add_section("Prompt", prompt_content, "# No prompt was provided.")

        return "\n\n".join(parts)

    def print_summary(self):
        """Calculates and prints an accurate, comprehensive summary to the console."""
        # START: print_summary_body
        # This method uses self.all_sections populated by build_final_prompt
        print("--- Files Included ---")
        for f in self.processed_files:
            if self.context_only:
                print(f"• {f['path']} (content omitted)")
            else:
                print(f"• {f['path']} ({f['tokens']:,} tokens)")
        
        if self.auto_context:
            print("\n--- Auto-Context Included ---")
            for title, data in self.auto_context.items():
                print(f"• {title} ({data['tokens']:,} tokens)")
        
        print("\n--- Prompt Summary ---")
        if self.context_only:
            print("NOTE: Running in --context-only mode. File contents are excluded.")
        
        total_tokens = sum(v.get('tokens', 0) for v in self.all_sections.values())
        total_words = sum(count_words(v.get('content', '')) for v in self.all_sections.values())
        
        print(f"Total Tokens: {total_tokens:,}")
        print(f"Total Words:  {total_words:,}")
        
        ratio = total_tokens / total_words if total_words > 0 else 0
        perspective = get_literary_perspective(total_words, ratio)
        print("\n--- Size Perspective ---")
        print(perspective)
        print()
        # END: print_summary_body


# ============================================================================
# --- Main Execution Logic ---
# ============================================================================
def main():
    """Main function to parse args, process files, and generate output."""
    parser = argparse.ArgumentParser(description='Generate a Markdown context file for AI code assistance.')
    parser.add_argument('prompt', nargs='?', default=None, help='A prompt string or path to a prompt file (e.g., prompt.md).')
    parser.add_argument('-o', '--output', type=str, help='Optional: Output filename.')
    parser.add_argument('--no-clipboard', action='store_true', help='Disable copying output to clipboard.')
    parser.add_argument('--check-dependencies', action='store_true', help='Verify that all required external tools are installed.')
    parser.add_argument('--context-only', action='store_true', help='Generate a context-only prompt without file contents.')
    parser.add_argument(
        '-l', '--list',
        nargs='?', const='[-5:]', default=None,
        help='Include a list of recent articles. Optionally provide a slice, e.g., "[:]". Defaults to "[-5:]".'
    )
    args = parser.parse_args()

    # START: main_post_argparse
    # --- START DEBUGGING BLOCK ---
    print("\n--- DEBUGGING OUTPUT ---")
    print(f"[1] Argument received by argparse for --list: {args.list!r}")
    # --- END DEBUGGING BLOCK ---
    
    if args.check_dependencies:
        check_dependencies()
        sys.exit(0)
    # END: main_post_argparse

    # 1. Handle user prompt
    prompt_content = "Please review the provided context and assist with the codebase."
    if args.prompt:
        if os.path.exists(args.prompt):
            with open(args.prompt, 'r', encoding='utf-8') as f: prompt_content = f.read()
        else:
            prompt_content = args.prompt
    elif os.path.exists("prompt.md"):
        with open("prompt.md", 'r', encoding='utf-8') as f: prompt_content = f.read()

    # 2. Process all specified files
    files_to_process = parse_file_list_from_config()
    processed_files_data = []
    print("--- Processing Files ---")
    for path, comment in files_to_process:
        full_path = os.path.join(REPO_ROOT, path) if not os.path.isabs(path) else path
        if not os.path.exists(full_path):
            print(f"Warning: File not found and will be skipped: {full_path}")
            continue
        content, lang = "", "text"
        ext = os.path.splitext(path)[1].lower()
        if ext == '.ipynb':
            if JUPYTEXT_AVAILABLE:
                print(f"  -> Converting notebook: {path}")
                try:
                    notebook = jupytext.read(full_path)
                    content = jupytext.writes(notebook, fmt='py:percent')
                    lang = 'python'
                except Exception as e:
                    content = f"# FAILED TO CONVERT NOTEBOOK: {path}\n# ERROR: {e}"
                    print(f"Warning: Failed to convert {path}: {e}")
            else:
                content = f"# SKIPPING NOTEBOOK CONVERSION: jupytext not installed for {path}"
                print(f"Warning: `jupytext` library not found. Skipping conversion for {path}.")
        else:
            try:
                with open(full_path, 'r', encoding='utf-8') as f: content = f.read()
                lang_map = {'.py': 'python', '.js': 'javascript', '.html': 'html', '.css': 'css', '.md': 'markdown', '.json': 'json', '.nix': 'nix', '.sh': 'bash'}
                lang = lang_map.get(ext, 'text')
            except Exception as e:
                print(f"ERROR: Could not read or process {full_path}: {e}")
                sys.exit(1)
        processed_files_data.append({
            "path": path, "comment": comment, "content": content,
            "tokens": count_tokens(content), "words": count_words(content), "lang": lang
        })

    # 3. Build the prompt and add auto-generated context
    builder = PromptBuilder(processed_files_data, prompt_content, context_only=args.context_only, list_arg=args.list)
    
    print("\n--- Generating Auto-Context ---")
    print("Generating codebase tree diagram...", end='', flush=True)
    tree_output = run_tree_command()
    title = "Codebase Structure (eza --tree)"
    builder.add_auto_context(title, tree_output)
    print(f" ({builder.auto_context.get(title, {}).get('tokens', 0):,} tokens)")

    if args.list is not None:
        # START: main_article_logic
        print("Adding narrative context from articles...", end='', flush=True)
        all_articles = _get_article_list_data()
        
        # --- START DEBUGGING BLOCK ---
        print(f"\n[2] Total articles found by _get_article_list_data(): {len(all_articles)}")
        # --- END DEBUGGING BLOCK ---
        
        sliced_articles = []
        try:
            slice_or_index = parse_slice_arg(args.list)
        
            # --- START DEBUGGING BLOCK ---
            print(f"[3] Parsed slice/index object: {slice_or_index!r}")
            # --- END DEBUGGING BLOCK ---
        
            if isinstance(slice_or_index, int): sliced_articles = [all_articles[slice_or_index]]
            elif isinstance(slice_or_index, slice): sliced_articles = all_articles[slice_or_index]
        
            # --- START DEBUGGING BLOCK ---
            print(f"[4] Length of article list AFTER slicing: {len(sliced_articles)}")
            # --- END DEBUGGING BLOCK ---
        
        except (ValueError, IndexError):
            print(f" (invalid slice '{args.list}')")
            sliced_articles = []
        
        if sliced_articles:
            narrative_content = "\n".join(
                f"### {article['title']} ({article['date']})\n> {article['summary']}\n"
                for article in sliced_articles
            )
            # --- START DEBUGGING BLOCK ---
            print(f"\n[5] Generated narrative_content length: {len(narrative_content)}")
            # --- END DEBUGGING BLOCK ---
        
            builder.add_auto_context("Recent Narrative Context", narrative_content)
            print(f" ({len(sliced_articles)} articles)")
        else:
            print(" (no articles found or invalid slice)")
        # END: main_article_logic

    python_files_to_diagram = [f['path'] for f in processed_files_data if f['path'].endswith('.py')]
    if python_files_to_diagram:
        print("Python file(s) detected. Generating UML diagrams...")
        for py_file_path in python_files_to_diagram:
            print(f"  -> Generating for {py_file_path}...", end='', flush=True)
            uml_context = generate_uml_and_dot(py_file_path, CONFIG["PROJECT_NAME"])
            uml_content = uml_context.get("ascii_uml")
            title = f"UML Class Diagram (ASCII for {py_file_path})"
            builder.add_auto_context(title, uml_content)
            
            if title in builder.auto_context:
                print(f" ({builder.auto_context[title]['tokens']:,} tokens)")
            elif uml_content and "note: no classes" in uml_content.lower():
                print(" (skipped, no classes)")
            else:
                print(" (skipped)")
        print("...UML generation complete.\n")
    
    # START: main_pre_summary
    # --- START DEBUGGING BLOCK ---
    print("\n--- MORE DEBUGGING ---")
    print(f"[7] Final auto_context keys before building prompt: {list(builder.auto_context.keys())}")
    print("--- END DEBUGGING ---\n")
    # --- END DEBUGGING BLOCK ---
    
    # 4. Generate final output and print summary
    final_output = builder.build_final_prompt()
    # END: main_pre_summary
    builder.print_summary()

    # 5. Handle output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f: f.write(final_output)
        print(f"Output written to '{args.output}'")
    if not args.no_clipboard:
        copy_to_clipboard(final_output)

if __name__ == "__main__":
    main()

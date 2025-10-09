# prompt_foo.py (Corrected Synthesis)

import os
import re
import sys
import pydot
import argparse
import tiktoken
import subprocess
import tempfile
import shutil
from typing import Dict, List, Optional, Tuple

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

# Centralized configuration as recommended in Architectural Analysis (Section VI-B)
CONFIG = {
    "PROJECT_NAME": "pipulate"
}

# ============================================================================
# --- Accurate Literary Size Scale (Word Count Based) ---
# ============================================================================
LITERARY_SIZE_SCALE = [
    (3000, "Short Essay"),
    (7500, "Short Story"),
    (20000, "Novelette"),
    (50000, "Novella or a Master's Dissertation"),
    (80000, "Average Paperback Novel or a Ph.D. Dissertation"),
    (120000, "Long Novel"),
    (200000, "Epic Fantasy Novel"),
    (500000, "Seriously Long Epic (like 'Infinite Jest')"),
]

def get_literary_perspective(word_count: int, token_word_ratio: float) -> str:
    """Get a human-readable literary comparison for the codebase size."""
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

# ============================================================================
# --- Restored & Corrected: UML and DOT Context Generation ---
# ============================================================================
def generate_uml_and_dot(target_file: str, project_name: str) -> Dict:
    """Generates a UML ASCII diagram and a DOT dependency graph for a target Python file."""
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
        
        # --- Step 1: Run pyreverse ---
        try:
            pyreverse_cmd = [
                pyreverse_exec,
                "-f", "dot",
                "-o", "dot", # This format is just a prefix
                "-p", project_name,
                target_path
            ]
            subprocess.run(
                pyreverse_cmd,
                check=True,
                capture_output=True,
                text=True,
                cwd=temp_dir
            )
            generated_dot_name = f"classes_{project_name}.dot"
            os.rename(os.path.join(temp_dir, generated_dot_name), dot_file_path)

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            error_msg = e.stderr if hasattr(e, 'stderr') else str(e)
            return {"ascii_uml": f"Error: pyreverse failed. {error_msg}", "dot_graph": None}

        # --- Step 2: Convert DOT to PlantUML ---
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
                        if clean_attr:
                            puml_lines.append(f"  - {clean_attr}")

                if len(parts) > 2:
                    method_block = parts[2].strip()
                    for method_line in re.split(r'<br[^>]*>', method_block):
                        clean_method = sanitize_line(method_line)
                        if clean_method:
                            puml_lines.append(f"  + {clean_method}")

                puml_lines.append("}\n")

            for edge in graph.get_edges():
                source_name = edge.get_source().strip('"').split('.')[-1]
                dest_name = edge.get_destination().strip('"').split('.')[-1]
                puml_lines.append(f"{source_name} ..> {dest_name}")

            puml_lines.append("@enduml")
            with open(puml_file_path, 'w') as f:
                f.write('\n'.join(puml_lines))

        except Exception as e:
            with open(dot_file_path, 'r') as f:
                dot_content_on_error = f.read()
            return {"ascii_uml": f"Error: DOT to PUML conversion failed. {str(e)}", "dot_graph": dot_content_on_error}
 
        # --- Step 3: Run PlantUML ---
        try:
            plantuml_cmd = ["plantuml", "-tutxt", puml_file_path]
            subprocess.run(plantuml_cmd, check=True, capture_output=True, text=True, cwd=temp_dir)
            
            utxt_file_path = puml_file_path.replace(".puml", ".utxt")
            with open(utxt_file_path, 'r') as f:
                ascii_uml = f.read()
            
            # --- Normalize whitespace from plantuml output ---
            lines = ascii_uml.splitlines()
            non_empty_lines = [line for line in lines if line.strip()]
            
            if non_empty_lines:
                min_indent = min(len(line) - len(line.lstrip(' ')) for line in non_empty_lines)
                dedented_lines = [line[min_indent:] for line in lines]
                stripped_lines = [line.rstrip() for line in dedented_lines]
                ascii_uml = '\n'.join(stripped_lines)
                
                # Prepend a newline to "absorb the chop" from rendering
                if ascii_uml:
                    ascii_uml = '\n' + ascii_uml

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            error_msg = e.stderr if hasattr(e, 'stderr') else str(e)
            return {"ascii_uml": f"Error: plantuml failed. {error_msg}", "dot_graph": dot_content}

    return {"ascii_uml": ascii_uml, "dot_graph": dot_content}

# ============================================================================
# --- Helper Functions (Tokenizing, File Parsing, Clipboard) ---
# ============================================================================
def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Counts tokens in a text string using tiktoken."""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        return len(text.split())

def count_words(text: str) -> int:
    """Counts words in a text string."""
    return len(text.split())

def parse_file_list_from_config() -> List[Tuple[str, str]]:
    """Loads and parses the file list from foo_files.py."""
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
        if not line or line.startswith('#'):
            continue
        parts = re.split(r'\s*<--\s*|\s*#\s*', line, 1)
        file_path = parts[0].strip()
        comment = parts[1].strip() if len(parts) > 1 else ""

        if file_path and file_path not in seen_files:
            seen_files.add(file_path)
            parsed_files.append((file_path, comment))
    return parsed_files

def copy_to_clipboard(text: str):
    """Copies text to the system clipboard using 'xclip'."""
    if not shutil.which('xclip'):
        print("\nWarning: 'xclip' not found. Cannot copy to clipboard.")
        return
    try:
        subprocess.run(['xclip', '-selection', 'clipboard'], input=text.encode('utf-8'), check=True)
        print("Markdown output copied to clipboard")
    except Exception as e:
        print(f"\nWarning: Could not copy to clipboard: {e}")

def run_tree_command() -> str:
    """Runs the 'eza' command to generate a tree view that respects .gitignore."""
    eza_exec = shutil.which("eza")
    if not eza_exec:
        return "Skipping: `eza` command not found."
    
    try:
        result = subprocess.run(
            [eza_exec, '--tree', '--git-ignore', '--color=never'],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error running eza command: {e.stderr}"
    except Exception as e:
        return f"An unexpected error occurred while running eza: {str(e)}"

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
# --- Intelligent PromptBuilder Class ---
# ============================================================================
class PromptBuilder:
    """
    Builds a complete, structured Markdown prompt including file manifests,
    auto-generated context, file contents, and the user's final prompt.
    """
    def __init__(self, processed_files: List[Dict], prompt_text: str, context_only: bool = False):
        self.processed_files = processed_files
        self.prompt_text = prompt_text
        self.context_only = context_only
        self.auto_context = {}

    def add_auto_context(self, title: str, content: str):
        """Adds auto-generated context like UML diagrams to the prompt."""
        if content and "error" not in content.lower() and "skipping" not in content.lower():
            self.auto_context[title] = {
                'content': content,
                'tokens': count_tokens(content),
                'words': count_words(content)
            }

    def _generate_manifest_header(self) -> str:
        lines = ["# Codebase Context & Manifest", ""]
        for f in self.processed_files:
            purpose = f" ({f['comment']})" if f['comment'] else ""
            token_display = f" ({f['tokens']:,} tokens)" if not self.context_only else ""
            lines.append(f"- **{f['path']}**{purpose}{token_display}")
        return "\n".join(lines)

    def _generate_auto_context_section(self) -> str:
        if not self.auto_context:
            return ""
        lines = ["", "---", "", "# Auto-Generated Context", ""]
        if "Codebase Structure (eza --tree)" in self.auto_context:
            title = "Codebase Structure (eza --tree)"
            content = self.auto_context[title]['content']
            lines.append(f"## {title}")
            lines.append("```text")
            lines.append(content.strip())
            lines.append("```")
        
        for title, data in self.auto_context.items():
            if title != "Codebase Structure (eza --tree)":
                lines.append(f"## {title}")
                lines.append("```text")
                lines.append(data['content'])
                lines.append("```")
        return "\n".join(lines)

    def _generate_file_contents(self) -> str:
        lines = []
        for f in self.processed_files:
            lines.append(f"```{f['lang']}:{f['path']}")
            lines.append(f['content'])
            lines.append("```")
            lines.append(f"\n# End of {f['path']}\n")
        return "\n".join(lines)

    def _generate_ai_checklist(self) -> str:
        """Creates a standardized checklist for the AI to verify the prompt's context."""
        return '''
# AI Self-Correction Checklist

Before addressing the user's prompt, perform the following verification steps:

1.  **Review the Manifest vs. Codebase Structure:** Compare the file list in the manifest against the `eza --tree` output. Are there any obviously related, critical files missing from the manifest that would be necessary to understand the user's request? (e.g., if `core.py` is present, is `__init__.py` also present?).
2.  **Analyze Import Statements:** Briefly scan the `import` statements in the provided Python files. Do they suggest dependencies on local files that were *not* included in the manifest?
3.  **Check for Incompleteness:** If you determine that critical files are missing, do not proceed. Instead, your **primary task** is to inform me of the missing files and recommend adding them to `foo_files.py` to create a more complete context.
4.  **Confirm Understanding:** If the context appears complete, state "Context verified." and then proceed with the user's request.
'''

    def build_final_prompt(self) -> str:
        """Assembles all parts into the final Markdown string."""
        parts = [
            self._generate_manifest_header(),
            self._generate_auto_context_section(),
        ]

        if not self.context_only:
            parts.extend([
                "\n---\n\n# File Contents\n",
                self._generate_file_contents(),
            ])

        parts.extend([
            "---\n\n# User Prompt\n",
            self._generate_ai_checklist(),
            self.prompt_text
        ])
        
        return "\n".join(filter(None, parts))

    def print_summary(self):
        """Calculates and prints an accurate, comprehensive summary to the console."""
        # --- Calculate token counts for all components ---
        manifest_str = self._generate_manifest_header()
        manifest_tokens = count_tokens(manifest_str)
        manifest_words = count_words(manifest_str)
        
        prompt_tokens = count_tokens(self.prompt_text)
        prompt_words = count_words(self.prompt_text)

        checklist_str = self._generate_ai_checklist()
        checklist_tokens = count_tokens(checklist_str)
        checklist_words = count_words(checklist_str)

        auto_context_total_tokens = sum(v['tokens'] for v in self.auto_context.values())
        auto_context_total_words = sum(v['words'] for v in self.auto_context.values())

        file_content_total_tokens = sum(f['tokens'] for f in self.processed_files)
        file_content_total_words = sum(f['words'] for f in self.processed_files)

        # --- Display the breakdown ---
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

        # --- Calculate and display the final summary ---
        print("\n--- Prompt Summary ---")
        if self.context_only:
            print("NOTE: Running in --context-only mode. File contents are excluded.")
            total_tokens = manifest_tokens + auto_context_total_tokens + prompt_tokens + checklist_tokens
            total_words = manifest_words + auto_context_total_words + prompt_words + checklist_words
        else:
            total_tokens = manifest_tokens + auto_context_total_tokens + file_content_total_tokens + prompt_tokens + checklist_tokens
            total_words = manifest_words + auto_context_total_words + file_content_total_words + prompt_words + checklist_words

        print(f"Total Tokens: {total_tokens:,}")
        print(f"Total Words:  {total_words:,}")

        ratio = total_tokens / total_words if total_words > 0 else 0
        perspective = get_literary_perspective(total_words, ratio)
        print("\n--- Size Perspective ---")
        print(perspective)
        print()

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
    args = parser.parse_args()

    if args.check_dependencies:
        check_dependencies()
        sys.exit(0)

    # 1. Handle user prompt
    prompt_content = "Please review the provided context and assist with the codebase."
    if args.prompt:
        if os.path.exists(args.prompt):
            with open(args.prompt, 'r', encoding='utf-8') as f:
                prompt_content = f.read()
        else:
            prompt_content = args.prompt
    elif os.path.exists("prompt.md"):
        with open("prompt.md", 'r', encoding='utf-8') as f:
            prompt_content = f.read()

    # 2. Process all specified files
    files_to_process = parse_file_list_from_config()
    processed_files_data = []
    for path, comment in files_to_process:
        full_path = os.path.join(REPO_ROOT, path) if not os.path.isabs(path) else path
        if not os.path.exists(full_path):
            print(f"Warning: File not found and will be skipped: {full_path}")
            continue
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ext = os.path.splitext(path)[1].lower()
            lang_map = {'.py': 'python', '.js': 'javascript', '.html': 'html', '.css': 'css', '.md': 'markdown', '.json': 'json', '.nix': 'nix', '.sh': 'bash'}
            processed_files_data.append({
                "path": path, "comment": comment, "content": content,
                "tokens": count_tokens(content), "words": count_words(content),
                "lang": lang_map.get(ext, 'text')
            })
        except Exception as e:
            print(f"ERROR: Could not read or process {full_path}: {e}")
            sys.exit(1)

    # 3. Build the prompt and add auto-generated context
    builder = PromptBuilder(processed_files_data, prompt_content, context_only=args.context_only)
    
    # --- Add the Codebase Tree ---
    print("Generating codebase tree diagram...")
    tree_output = run_tree_command()
    builder.add_auto_context("Codebase Structure (eza --tree)", tree_output)
    print("...done.")

    # --- Generate UML for all included Python files ---
    python_files_to_diagram = [
        f['path'] for f in processed_files_data if f['path'].endswith('.py')
    ]

    if python_files_to_diagram:
        print("Python file(s) detected. Generating UML diagrams...")
        for py_file_path in python_files_to_diagram:
            print(f"  -> Generating for {py_file_path}...")
            uml_context = generate_uml_and_dot(
                target_file=py_file_path,
                project_name=CONFIG["PROJECT_NAME"]
            )
            builder.add_auto_context(
                f"UML Class Diagram (ASCII for {py_file_path})",
                uml_context.get("ascii_uml")
            )
        print("...UML generation complete.")
    
    # 4. Generate final output and print summary
    final_output = builder.build_final_prompt()
    builder.print_summary()

    # 5. Handle output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(final_output)
        print(f"Output written to '{args.output}'")
    if not args.no_clipboard:
        copy_to_clipboard(final_output)


if __name__ == "__main__":
    main()
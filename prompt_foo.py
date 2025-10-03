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
def generate_uml_and_dot(target_file="server.py", project_name="pipulate") -> Dict:
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

# ============================================================================
# --- Intelligent PromptBuilder Class ---
# ============================================================================
class PromptBuilder:
    """
    Builds a complete, structured Markdown prompt including file manifests,
    auto-generated context, file contents, and the user's final prompt.
    """
    def __init__(self, processed_files: List[Dict], prompt_text: str):
        self.processed_files = processed_files
        self.prompt_text = prompt_text
        self.auto_context = {}
        self.total_tokens = sum(f['tokens'] for f in processed_files) + count_tokens(prompt_text)
        self.total_words = sum(f['words'] for f in processed_files) + count_words(prompt_text)

    def add_auto_context(self, title: str, content: str):
        """Adds auto-generated context like UML diagrams to the prompt."""
        if content and "error" not in content.lower() and "skipping" not in content.lower():
            self.auto_context[title] = content
            self.total_tokens += count_tokens(content)
            self.total_words += count_words(content)

    def _generate_manifest_header(self) -> str:
        lines = ["# Codebase Context & Manifest", ""]
        for f in self.processed_files:
            purpose = f" ({f['comment']})" if f['comment'] else ""
            lines.append(f"- **{f['path']}**{purpose} ({f['tokens']:,} tokens)")
        return "\n".join(lines)

    def _generate_auto_context_section(self) -> str:
        if not self.auto_context:
            return ""
        lines = ["", "---", "", "# Auto-Generated Context", ""]
        for title, content in self.auto_context.items():
            lines.append(f"## {title}")
            lines.append("```text")
            lines.append(content.strip())
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

    def build_final_prompt(self) -> str:
        """Assembles all parts into the final Markdown string."""
        return "\n".join(filter(None, [
            self._generate_manifest_header(),
            self._generate_auto_context_section(),
            "\n---\n\n# File Contents\n",
            self._generate_file_contents(),
            "---\n\n# User Prompt\n",
            self.prompt_text
        ]))

    def print_summary(self):
        """Prints a comprehensive summary to the console."""
        print("--- Files Included ---")
        for f in self.processed_files:
            print(f"• {f['path']} ({f['tokens']:,} tokens)")
        print("\n--- Prompt Summary ---")
        print(f"Total Tokens: {self.total_tokens:,}")
        print(f"Total Words:  {self.total_words:,}")

        ratio = self.total_tokens / self.total_words if self.total_words > 0 else 0
        perspective = get_literary_perspective(self.total_words, ratio)
        print("\n--- Size Perspective ---")
        print(perspective)
        print()

# ============================================================================
# --- Main Execution Logic ---
# ============================================================================
# prompt_foo.py (Corrected main function)

def main():
    """Main function to parse args, process files, and generate output."""
    parser = argparse.ArgumentParser(description='Generate a Markdown context file for AI code assistance.')
    parser.add_argument('prompt', nargs='?', default=None, help='A prompt string or path to a prompt file (e.g., prompt.md).')
    parser.add_argument('-o', '--output', type=str, help='Optional: Output filename.')
    parser.add_argument('--no-clipboard', action='store_true', help='Disable copying output to clipboard.')
    args = parser.parse_args()

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
        # We'll use the original path (which might be absolute) for processing
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
                # Store the original path from foo_files.py for the check
                "path": path, "comment": comment, "content": content,
                "tokens": count_tokens(content), "words": count_words(content),
                "lang": lang_map.get(ext, 'text')
            })
        except Exception as e:
            print(f"ERROR: Could not read or process {full_path}: {e}")
            sys.exit(1)

    # 3. Build the prompt and add auto-generated context
    builder = PromptBuilder(processed_files_data, prompt_content)

    processed_paths = {f['path'] for f in processed_files_data}
    uml_trigger_files = {"server.py", "pipulate/core.py"}

    # Robust check using endswith()
    trigger_file = None
    for path in processed_paths:
        for trigger in uml_trigger_files:
            if path.endswith(trigger):
                trigger_file = trigger
                break
        if trigger_file:
            break

    if trigger_file:
        print(f"Key file '{trigger_file}' detected. Generating UML and DOT file context...")
        uml_context = generate_uml_and_dot(target_file=trigger_file)
        builder.add_auto_context(f"UML Class Diagram (ASCII for {trigger_file})", uml_context.get("ascii_uml"))
        print("...done.")
    
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

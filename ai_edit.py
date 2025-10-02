# ai_edit.py
import ast
import argparse
from pathlib import Path
import sys
import importlib.util

class CodeRefactorer:
    """
    Performs robust, deterministic code block replacements in Python files
    using sentinel comments and AST validation.
    """
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")
        self._original_content = self.file_path.read_text()
        self._new_content = self._original_content

    def _verify_syntax(self, code_to_check: str, block_name: str):
        try:
            ast.parse(code_to_check)
            print(f"    ✅ AST validation successful for block '{block_name}'.")
        except SyntaxError as e:
            print(f"    ❌ AST validation FAILED for block '{block_name}'. The proposed change would break the file.")
            error_line = code_to_check.splitlines()[e.lineno - 1]
            print(f"    Error near line {e.lineno}: {error_line.strip()}")
            print(f"    {' ' * (e.offset - 1)}^")
            print(f"    Reason: {e.msg}")
            raise e

    def replace_block(self, block_name: str, new_code: str):
        start_sentinel = f"# START: {block_name}"
        end_sentinel = f"# END: {block_name}"

        try:
            before_block, rest = self._new_content.split(start_sentinel, 1)
            old_block, after_block = rest.split(end_sentinel, 1)

            # Use textwrap.dedent to handle triple-quoted string indentation
            import textwrap
            new_code = textwrap.dedent(new_code).strip()

            base_indentation = before_block.split('\n')[-1]
            indented_new_code = "\n".join(
                f"{base_indentation}{line}" for line in new_code.split('\n')
            )

            content_with_replacement = (
                f"{before_block}{start_sentinel}\n"
                f"{indented_new_code}\n"
                f"{base_indentation}{end_sentinel}{after_block}"
            )

            self._verify_syntax(content_with_replacement, block_name)
            self._new_content = content_with_replacement
            print(f"  ✅ Block '{block_name}' in {self.file_path.name} is ready to be replaced.")

        except ValueError:
            print(f"  ⚠️  Could not find sentinels for block '{block_name}' in {self.file_path.name}. Skipping.")
        except Exception as e:
            print(f"  ❌ An error occurred while replacing block '{block_name}': {e}")
            raise

    def write_changes(self):
        if self._new_content != self._original_content:
            print(f"Writing changes to {self.file_path}...")
            self.file_path.write_text(self._new_content)
            print("  💾 File saved successfully.")
        else:
            print(f"🤷 No changes were made to {self.file_path}.")

def load_patches_from_module(patch_module_path: Path):
    """Dynamically imports a Python module and returns its 'patches' list."""
    try:
        module_name = patch_module_path.stem
        spec = importlib.util.spec_from_file_location(module_name, patch_module_path)
        patch_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(patch_module)
        return getattr(patch_module, 'patches')
    except AttributeError:
        print(f"Error: The patch file '{patch_module_path}' must define a list named 'patches'.")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading patch module '{patch_module_path}': {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Apply deterministic, AST-validated code patches from a Python module.")
    parser.add_argument("patch_file", help="Path to the Python file containing the 'patches' list.")
    args = parser.parse_args()

    patch_file_path = Path(args.patch_file)
    if not patch_file_path.exists():
        print(f"Error: Patch file not found at '{patch_file_path}'")
        sys.exit(1)

    patches = load_patches_from_module(patch_file_path)

    print(f"Applying patches from: {patch_file_path.name}")
    print("-" * 30)

    patches_by_file = {}
    for patch in patches:
        file = patch.get("file")
        if file not in patches_by_file:
            patches_by_file[file] = []
        patches_by_file[file].append(patch)

    for file_path_str, file_patches in patches_by_file.items():
        print(f"\nProcessing file: {file_path_str}")
        try:
            refactorer = CodeRefactorer(file_path_str)
            for patch in file_patches:
                block_name = patch.get("block_name")
                new_code = patch.get("new_code")
                if not block_name or new_code is None:
                    print(f"  ⚠️  Skipping invalid patch item: {patch}")
                    continue
                refactorer.replace_block(block_name, new_code)
            
            refactorer.write_changes()
        except (FileNotFoundError, SyntaxError) as e:
            print(f"\nProcess aborted for {file_path_str} due to a critical error: {e}")
            print("No changes have been written to this file.")
        except Exception as e:
            print(f"\nAn unexpected error occurred for {file_path_str}: {e}")
            
    print("\n" + "-" * 30)
    print("Refactoring process complete. Please review the changes with 'git diff'.")

if __name__ == "__main__":
    main()
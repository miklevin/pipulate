#!/usr/bin/env python3
import ast
import os
from pathlib import Path
import argparse

# --- Configuration ---
RENAME_MAP = {
    "revert_control": "display_revert_header",
    "widget_container": "display_revert_widget",
    "create_step_navigation": "chain_reverter"
}

# Files and directories to scan relative to project_root
# Matches the structure in your context
SCAN_TARGETS = [
    "server.py",
    "plugins",
    "helpers/create_workflow.py",
    "helpers/splice_workflow_step.py"
]

# Exclude this script itself and other refactoring/analysis scripts
EXCLUDED_FILES = [
    "refactor_pipulate_nav_methods.py", # This script
    "analyze_styles.py",
    "refactor_inline_style.py",
    "refactor_inline_styles_to_cls.py"
]

class PipulateMethodRenamer(ast.NodeTransformer):
    def __init__(self, rename_map):
        self.rename_map = rename_map
        self.modifications_made = False

    def visit_Attribute(self, node):
        """
        Visits Attribute nodes like 'pip.revert_control' or 'self.pipulate.revert_control'.
        """
        # Check if the attribute's name is one we want to rename
        if isinstance(node.attr, str) and node.attr in self.rename_map:
            original_name = node.attr
            new_name = self.rename_map[original_name]
            
            # Heuristic: Check if the object being called is likely 'pip' or 'self.pipulate'
            # This is a simple check; more robust checking might involve type analysis
            # or tracking variable assignments, which is much more complex with AST alone.
            is_pipulate_instance_call = False
            if isinstance(node.value, ast.Name) and node.value.id == 'pip': # e.g., pip.revert_control
                is_pipulate_instance_call = True
            elif isinstance(node.value, ast.Attribute) and \
                 isinstance(node.value.value, ast.Name) and \
                 node.value.value.id == 'self' and \
                 node.value.attr == 'pipulate': # e.g., self.pipulate.revert_control
                is_pipulate_instance_call = True
            elif isinstance(node.value, ast.Call) and \
                 hasattr(node.value.func, 'id') and \
                 node.value.func.id == 'getattr' : # getattr(self.pipulate, 'revert_control') - less common
                 # This case is harder to reliably detect and rename with simple AST.
                 # For now, we'll focus on direct attribute access.
                 pass


            if is_pipulate_instance_call:
                print(f"  - Renaming method call '{original_name}' to '{new_name}' at line {node.lineno}")
                node.attr = new_name
                self.modifications_made = True
            # else:
            #     print(f"  - Found attribute '{original_name}' but not on expected 'pip' or 'self.pipulate' instance at line {node.lineno}. Skipping.")


        # Also, we need to rename method *definitions* in the Pipulate class
        # This part is handled by visit_FunctionDef if methods are defined in server.py's Pipulate class
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """
        Visits FunctionDef nodes (method definitions).
        This is primarily for renaming the methods within the Pipulate class definition.
        """
        if node.name in self.rename_map:
            original_name = node.name
            new_name = self.rename_map[original_name]
            # Heuristic: Check if this function is likely a method of the 'Pipulate' class
            # This would typically involve checking the parent ClassDef node.
            # For simplicity, if this script is run carefully, we assume FunctionDefs
            # with these names in server.py are the target Pipulate class methods.
            # A more robust check would involve ensuring the parent of this FunctionDef
            # is a ClassDef named 'Pipulate'. This requires passing the parent to visit.
            # However, ast.NodeTransformer doesn't directly give parent access.
            # We'll rely on the file targeting for now (server.py for definitions).
            
            # A simple check for server.py to be more confident:
            if "server.py" in self.current_filepath_str: # Ensure this is specific enough
                print(f"  - Renaming method definition '{original_name}' to '{new_name}' at line {node.lineno}")
                node.name = new_name
                self.modifications_made = True
        return self.generic_visit(node)

def refactor_project_code(project_root_path: Path, scan_targets: list, rename_map: dict, dry_run: bool):
    print(f"Starting refactor in project root: {project_root_path}")
    total_files_modified = 0
    renamer = PipulateMethodRenamer(rename_map)

    files_to_process = []
    for target in scan_targets:
        target_path = project_root_path / target
        if target_path.is_file() and target_path.suffix == '.py':
            if target_path.name not in EXCLUDED_FILES:
                files_to_process.append(target_path)
        elif target_path.is_dir():
            for filepath in target_path.rglob("*.py"):
                if filepath.name not in EXCLUDED_FILES:
                    files_to_process.append(filepath)
        else:
            print(f"Warning: Scan target '{target}' not found or not a Python file/directory. Skipping.")

    print(f"\nFound {len(files_to_process)} Python files to scan.")

    for filepath in files_to_process:
        relative_filepath = filepath.relative_to(project_root_path)
        print(f"\nProcessing: {relative_filepath}")
        renamer.modifications_made = False # Reset for each file
        renamer.current_filepath_str = str(relative_filepath)


        try:
            original_content = filepath.read_text(encoding="utf-8")
            tree = ast.parse(original_content, filename=str(filepath))
            
            modified_tree = renamer.visit(tree)
            
            if renamer.modifications_made:
                total_files_modified += 1
                if not dry_run:
                    new_content = ast.unparse(modified_tree)
                    filepath.write_text(new_content, encoding="utf-8")
                    print(f"  SUCCESS: Modified and saved {relative_filepath}")
                else:
                    print(f"  DRY RUN: Would modify {relative_filepath}")
            else:
                print(f"  No changes needed in {relative_filepath}")

        except Exception as e:
            print(f"  ERROR processing {relative_filepath}: {e}")
            import traceback
            traceback.print_exc()

    print("\n--- Refactor Summary ---")
    if total_files_modified > 0:
        action = "would be" if dry_run else "were"
        print(f"{total_files_modified} file(s) {action} modified.")
        if dry_run:
            print("Run without --dry-run to apply changes.")
    else:
        print("No files required changes based on the rename map.")

def main():
    parser = argparse.ArgumentParser(
        description="Refactor Pipulate method names in Python files using AST.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="The root directory of the Pipulate project (default: current directory)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without actually modifying any files."
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    if not (project_root / "server.py").exists(): # Basic check
        print(f"Error: Could not find 'server.py' in the specified project root: {project_root}")
        print("Please ensure --project-root points to the Pipulate project directory.")
        return

    refactor_project_code(project_root, SCAN_TARGETS, RENAME_MAP, args.dry_run)

if __name__ == "__main__":
    main()

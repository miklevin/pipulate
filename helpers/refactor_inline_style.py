import ast
from pathlib import Path
import argparse
import re

# Files to typically scan (can be overridden by --files argument)
DEFAULT_SCAN_TARGETS = ["server.py", "plugins"]

class StyleRefactorer(ast.NodeTransformer):
    def __init__(self, target_style_string, new_class_name, target_python_constant_name=None):
        self.target_style_string = target_style_string.strip() if target_style_string else None
        self.new_class_name = new_class_name.strip()
        self.target_python_constant_name = target_python_constant_name.strip() if target_python_constant_name else None
        self.modifications_made_in_file = False
        self.current_filepath = ""

    def visit_Call(self, node):
        # Process arguments first to handle nested calls correctly
        super().generic_visit(node)

        new_keywords = list(node.keywords) # Make a mutable copy
        original_keywords_count = len(new_keywords)
        cls_keyword_index = -1
        style_keyword_to_remove_index = -1

        for i, keyword in enumerate(new_keywords):
            if keyword.arg == 'style':
                # Case 1: Target is a direct string literal
                if self.target_style_string and \
                   isinstance(keyword.value, ast.Constant) and \
                   isinstance(keyword.value.value, str) and \
                   keyword.value.value.strip() == self.target_style_string:
                    style_keyword_to_remove_index = i
                    break 
                # Case 2: Target is a Python constant
                elif self.target_python_constant_name and \
                     isinstance(keyword.value, ast.Name) and \
                     keyword.value.id == self.target_python_constant_name:
                    style_keyword_to_remove_index = i
                    break
        
        if style_keyword_to_remove_index != -1:
            self.modifications_made_in_file = True
            
            # Find existing cls keyword
            for i, kw in enumerate(new_keywords):
                if kw.arg == 'cls':
                    cls_keyword_index = i
                    break
            
            if cls_keyword_index != -1: # cls attribute exists
                cls_node = new_keywords[cls_keyword_index].value
                if isinstance(cls_node, ast.Constant) and isinstance(cls_node.value, str):
                    existing_classes = cls_node.value.split()
                    if self.new_class_name not in existing_classes:
                        existing_classes.append(self.new_class_name)
                    new_cls_value = " ".join(existing_classes)
                    new_keywords[cls_keyword_index] = ast.keyword(arg='cls', value=ast.Constant(value=new_cls_value))
                else:
                    # cls value is complex (e.g., f-string, variable)
                    # Create a new cls keyword with only the new class, and print a warning.
                    # This might lead to multiple cls attributes if the original was complex.
                    # The alternative is to not touch it, but that means the style isn't refactored.
                    # Adding a new one makes the intent clear for manual review.
                    new_keywords.append(ast.keyword(arg='cls', value=ast.Constant(value=self.new_class_name)))
                    func_name_for_log = getattr(node.func, 'id', getattr(node.func, 'attr', 'UnknownComponent'))
                    print(f"  [WARN] Existing 'cls' in {self.current_filepath}@{node.lineno} ({func_name_for_log}) is complex. Added a new 'cls' attribute. Manual review recommended.")

            else: # No existing cls attribute, add a new one
                new_keywords.append(ast.keyword(arg='cls', value=ast.Constant(value=self.new_class_name)))

            # Remove the original style keyword
            del new_keywords[style_keyword_to_remove_index]
            node.keywords = new_keywords
            
        return node

def refactor_project_styles(project_root, files_to_scan, target_style, new_class, target_constant=None, dry_run=False):
    project_root = Path(project_root).resolve()
    print(f"Project root: {project_root}")
    
    py_files = []
    for target in files_to_scan:
        target_path = project_root / target
        if target_path.is_file() and target_path.suffix == '.py':
            py_files.append(target_path)
        elif target_path.is_dir():
            py_files.extend(target_path.rglob("*.py"))
        else:
            print(f"  [WARN] Target '{target}' not found or not a Python file/directory. Skipping.")
            
    # Exclude the script itself and other specified helpers
    excluded_files = ["analyze_styles.py", "refactor_inline_style.py", "create_workflow.py", "splice_workflow_step.py"]
    py_files = [f for f in py_files if f.name not in excluded_files]

    print(f"\nScanning {len(py_files)} Python files...")
    total_modifications = 0

    refactorer = StyleRefactorer(target_style, new_class, target_constant)

    for filepath in py_files:
        refactorer.current_filepath = str(filepath.relative_to(project_root))
        refactorer.modifications_made_in_file = False # Reset for each file
        try:
            content = filepath.read_text(encoding="utf-8")
            tree = ast.parse(content)
            
            new_tree = refactorer.visit(tree)
            
            if refactorer.modifications_made_in_file:
                total_modifications += 1
                print(f"  Found and transformed in: {refactorer.current_filepath}")
                if not dry_run:
                    new_content = ast.unparse(new_tree)
                    filepath.write_text(new_content, encoding="utf-8")
                else:
                    print(f"    (Dry run - no changes written)")
        except Exception as e:
            print(f"  Error processing {refactorer.current_filepath}: {e}")

    if total_modifications > 0:
        print(f"\nRefactoring complete. {total_modifications} file(s) {'would be' if dry_run else 'were'} modified.")
    else:
        print("\nNo matching styles found to refactor with the given criteria.")

def add_css_class_to_file(css_file_path_str, new_class_name, new_class_definition, dry_run=False):
    css_file_path = Path(css_file_path_str)
    css_to_add = f"\n.{new_class_name} {{\n    {new_class_definition}\n}}\n"
    
    print(f"\n--- CSS Class to add to '{css_file_path.name}' ---")
    print(css_to_add.strip())

    if not dry_run:
        if not css_file_path.exists():
            print(f"  [WARN] CSS file '{css_file_path}' does not exist. Creating it.")
            try:
                css_file_path.parent.mkdir(parents=True, exist_ok=True)
                css_file_path.write_text(f"/* {APP_NAME} Custom Styles */\n", encoding="utf-8")
            except Exception as e:
                print(f"  [ERROR] Could not create CSS file: {e}")
                return

        try:
            current_css_content = css_file_path.read_text(encoding="utf-8")
            # Simple check to avoid duplicate class definitions (naïve, but good for 80/20)
            if f".{new_class_name} {{" not in current_css_content:
                with open(css_file_path, "a", encoding="utf-8") as f:
                    f.write(css_to_add)
                print(f"  Successfully appended class to '{css_file_path}'")
            else:
                print(f"  Class '.{new_class_name}' already seems to exist in '{css_file_path}'. Skipping addition.")
        except Exception as e:
            print(f"  [ERROR] Could not write to CSS file '{css_file_path}': {e}")
    else:
        print(f"  (Dry run - CSS file not modified)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refactor inline styles in FastHTML components.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--target-style", help="The exact inline style string to replace (e.g., 'color: red; font-weight: bold;')")
    group.add_argument("--target-constant", help="The name of the Python style constant to replace (e.g., 'MY_STYLE_VAR')")
    
    parser.add_argument("--new-class", required=True, help="The new CSS class name to use (e.g., 'text-error-bold')")
    parser.add_argument("--css-definition", help="The CSS definition for the new class (e.g., 'color: var(--pico-del-color); font-weight: bold;'). Required if not --dry-run and not --target-constant (unless --target-constant implies a known definition). If --target-style is used, this should be the CSS for the class.")
    
    parser.add_argument("--project-root", default=".", help="The root directory of the project.")
    parser.add_argument("--css-file-path", default="static/styles.css", help="Path to the CSS file to update.")
    parser.add_argument("--scan-targets", nargs='+', default=DEFAULT_SCAN_TARGETS, 
                        help=f"List of files or directories to scan (relative to project root). Defaults to: {' '.join(DEFAULT_SCAN_TARGETS)}")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without modifying files.")

    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    APP_NAME = project_root.name # Infer app name for comments

    if not args.dry_run and not args.css_definition and args.target_style:
        parser.error("--css-definition is required when using --target-style and not in --dry-run mode.")
    
    css_definition_to_add = args.css_definition
    if args.target_constant and not args.css_definition:
        print(f"[INFO] --target-constant ('{args.target_constant}') specified without --css-definition.")
        print(f"       Please ensure you manually define the class '.{args.new_class}' in '{args.css_file_path}'")
        print(f"       with the styles previously held by the '{args.target_constant}' constant, or re-run with --css-definition.")
        # Allow proceeding, as user might handle CSS manually for constants.

    if css_definition_to_add:
         # Basic formatting for definition: ensure semicolons and indentation
        css_definition_to_add = "; ".join(d.strip() for d in css_definition_to_add.split(';') if d.strip())
        if not css_definition_to_add.endswith(';'):
            css_definition_to_add += ';'
        add_css_class_to_file(project_root / args.css_file_path, args.new_class, css_definition_to_add, args.dry_run)
    elif not args.dry_run:
        print(f"\n[WARN] No CSS definition provided. The class '.{args.new_class}' will not be automatically added to '{args.css_file_path}'.")
        print(f"         Ensure it's defined manually if this is not a dry run.")


    refactor_project_styles(project_root, args.scan_targets, args.target_style, args.new_class, args.target_constant, args.dry_run)

    print("\nNext steps:")
    print("1. Review the changes (git diff).")
    print(f"2. Ensure the new class '.{args.new_class}' is correctly defined in '{args.css_file_path}'.")
    if args.target_constant and not args.dry_run:
        print(f"3. Manually review and consider removing or deprecating the Python constant '{args.target_constant}' if no longer needed.")
    print("4. Test the application visually.")
    print("5. Commit the changes if satisfied.")

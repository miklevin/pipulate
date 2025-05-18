import ast
from pathlib import Path
import argparse
import re

# Files to typically scan (can be overridden by --files argument)
DEFAULT_SCAN_TARGETS = ["server.py", "plugins"]
# List of known FastHTML component names that accept 'cls'
FASTHTML_COMPONENT_NAMES = {
    'Div', 'Button', 'Span', 'P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'A', 'Form', 'Input',
    'Li', 'Ul', 'Card', 'Grid', 'Container', 'Details', 'Summary', 'Label', 'Textarea',
    'Select', 'Option', 'Pre', 'Code', 'Hr', 'Script', 'Link', 'Meta', 'Title', 'Group',
    'Main', 'Header', 'Footer', 'Article', 'Nav', 'Aside', 'Section', 'Figure', 'Figcaption',
    'Blockquote', 'Table', 'Thead', 'Tbody', 'Tfoot', 'Tr', 'Th', 'Td', 'Fieldset', 'Legend'
}

class ClassRenamer(ast.NodeTransformer):
    def __init__(self, old_class_name, new_class_name):
        self.old_class_name = old_class_name.strip()
        self.new_class_name = new_class_name.strip()
        self.modifications_made_in_file = False
        self.current_filepath = ""

    def visit_Call(self, node):
        super().generic_visit(node) # Process children first

        func_name_str = ""
        if isinstance(node.func, ast.Name):
            func_name_str = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name_str = node.func.attr

        if func_name_str not in FASTHTML_COMPONENT_NAMES:
            return node

        cls_keyword_index = -1
        cls_value_node = None

        for i, kw in enumerate(node.keywords):
            if kw.arg == 'cls':
                cls_keyword_index = i
                cls_value_node = kw.value
                break
        
        if cls_value_node is None:
            return node

        modified_this_call = False

        if isinstance(cls_value_node, ast.Constant) and isinstance(cls_value_node.value, str):
            current_classes_str = cls_value_node.value
            current_classes_list = current_classes_str.split()
            
            if self.old_class_name in current_classes_list:
                new_classes_list = []
                for c in current_classes_list:
                    if c == self.old_class_name:
                        if self.new_class_name and self.new_class_name not in new_classes_list:
                            new_classes_list.append(self.new_class_name)
                    else:
                        if c not in new_classes_list: # Avoid duplicates if old_class was present multiple times
                             new_classes_list.append(c)
                
                final_cls_str = " ".join(sorted(list(set(new_classes_list)))) # Sort for consistency and uniqueness
                
                if not final_cls_str: # If all classes were removed (e.g. old was only one, new is empty)
                    node.keywords.pop(cls_keyword_index)
                    print(f"      Removed empty 'cls' attribute in {self.current_filepath} L{node.lineno} ({func_name_str})")
                else:
                    node.keywords[cls_keyword_index].value = ast.Constant(value=final_cls_str)
                
                modified_this_call = True
                self.modifications_made_in_file = True

        elif isinstance(cls_value_node, ast.JoinedStr): # f-string
            # Rudimentary support for f-strings: replace in literal parts only
            new_fstring_parts = []
            fstring_modified_here = False
            for part_node in cls_value_node.values:
                if isinstance(part_node, ast.Constant) and isinstance(part_node.value, str):
                    original_part_val = part_node.value
                    # Split string part by space to handle multiple classes within one literal part
                    part_classes = original_part_val.split()
                    if self.old_class_name in part_classes:
                        updated_part_classes = []
                        for c_part in part_classes:
                            if c_part == self.old_class_name:
                                if self.new_class_name and self.new_class_name not in updated_part_classes:
                                    updated_part_classes.append(self.new_class_name)
                            else:
                                if c_part not in updated_part_classes:
                                    updated_part_classes.append(c_part)
                        new_part_val = " ".join(sorted(list(set(updated_part_classes))))
                        if new_part_val != original_part_val:
                            fstring_modified_here = True
                        new_fstring_parts.append(ast.Constant(value=new_part_val))
                    else:
                        new_fstring_parts.append(part_node)
                else:
                    new_fstring_parts.append(part_node)
            
            if fstring_modified_here:
                # Filter out any Constant parts that became empty strings
                cls_value_node.values = [p for p in new_fstring_parts if not (isinstance(p, ast.Constant) and not p.value.strip())]
                if not cls_value_node.values: # If f-string becomes effectively empty
                    node.keywords.pop(cls_keyword_index)
                    print(f"      Removed empty f-string 'cls' attribute in {self.current_filepath} L{node.lineno} ({func_name_str})")
                else:
                     print(f"      Modified f-string 'cls' in {self.current_filepath} L{node.lineno} ({func_name_str}). Review manually: {ast.unparse(cls_value_node)}")
                modified_this_call = True
                self.modifications_made_in_file = True
            else:
                 # Check if old_class_name might be part of a FormattedValue (variable)
                contains_old_class_in_vars = False
                for part_node in cls_value_node.values:
                    if isinstance(part_node, ast.FormattedValue):
                        # This is a simple check; complex expressions are harder
                        if isinstance(part_node.value, ast.Name) and self.old_class_name in part_node.value.id:
                            contains_old_class_in_vars = True
                            break
                if not contains_old_class_in_vars : # Only print warning if no literal parts were changed
                    print(f"  [INFO] 'cls' in {self.current_filepath}@{node.lineno} ({func_name_str}) is an f-string. '{self.old_class_name}' not found in literal parts or no change made. Manual review advised if it could be in a variable: {ast.unparse(cls_value_node)}")


        elif isinstance(cls_value_node, ast.Name): # cls=SOME_VARIABLE
            print(f"  [WARN] 'cls' in {self.current_filepath}@{node.lineno} ({func_name_str}) uses variable '{cls_value_node.id}'. Cannot automatically refactor. Manual review needed.")
        
        # If we modified, ensure the AST is valid
        if modified_this_call:
            ast.fix_missing_locations(node)
            
        return node

def rename_class_in_python_code(filepath: Path, old_class: str, new_class: str, dry_run: bool):
    """Reads a Python file, renames CSS classes in cls attributes, and optionally writes back."""
    try:
        original_content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(original_content)
        
        transformer = ClassRenamer(old_class, new_class)
        transformer.current_filepath = str(filepath)
        
        modified_tree = transformer.visit(tree)
        
        if transformer.modifications_made_in_file:
            print(f"  Processed Python file: {filepath.name} (Found occurrences of '{old_class}')")
            if not dry_run:
                new_content = ast.unparse(modified_tree)
                filepath.write_text(new_content, encoding="utf-8")
                print(f"    -> Modified and SAVED {filepath.name}")
            else:
                print(f"    -> (Dry run) Would modify {filepath.name}")
            return True
        return False
    except Exception as e:
        print(f"  Error processing Python file {filepath}: {e}")
        return False

def rename_class_in_css_file_content(css_content: str, old_class: str, new_class: str) -> tuple[str, bool]:
    """Renames a CSS class within the given CSS content string."""
    # Regex to find .old_class that is not part of another class name
    # e.g., matches ".old-class" but not ".another-old-class" or ".old-class-extended"
    # Pattern: (?<![\w-])\.{old_class}(?![\w-])
    # (?<![\w-]): Negative lookbehind - not preceded by a word character or hyphen
    # \.         : Matches the literal dot
    # re.escape(old_class): The class name itself, with special characters escaped
    # (?![\w-]): Negative lookahead - not followed by a word character or hyphen
    
    pattern = r'(?<![\w-])\.' + re.escape(old_class) + r'(?![\w-])'
    compiled_regex = re.compile(pattern)
    
    if not new_class: # If new_class is empty, we are effectively commenting out the old class rules
        # This is a basic approach. More robust would be to find the whole rule block.
        # For now, let's just log and not modify CSS for deletion via this script.
        # Deletion should be a more careful manual process or a different script.
        print(f"  [INFO] New class name is empty. Renaming '{old_class}' to an empty class is not directly supported for CSS modification by this script. Please manually remove or update CSS rules for '{old_class}'.")
        return css_content, False

    modified_content, num_replacements = compiled_regex.subn(r'.' + new_class, css_content)
    
    return modified_content, num_replacements > 0

def process_project(project_root_str: str, files_to_scan_list: list, css_file_rel_path: str, old_class: str, new_class: str, dry_run: bool):
    project_root = Path(project_root_str).resolve()
    css_file_abs_path = project_root / css_file_rel_path

    print(f"\nProject root: {project_root}")
    print(f"Attempting to rename CSS class '{old_class}' to '{new_class}'")
    if dry_run:
        print("DRY RUN MODE: No files will be changed.")

    # 1. Process Python files
    print(f"\nScanning Python files in: {', '.join(files_to_scan_list)}")
    py_files_to_process = []
    for target_str in files_to_scan_list:
        target_path = project_root / target_str
        if target_path.is_file() and target_path.suffix == '.py':
            py_files_to_process.append(target_path)
        elif target_path.is_dir():
            py_files_to_process.extend(target_path.rglob("*.py"))
        else:
            print(f"  [WARN] Target '{target_str}' not found or not a Python file/directory. Skipping.")

    excluded_py_helpers = ["analyze_styles.py", "refactor_inline_style.py", "refactor_inline_styles_to_cls.py", "refactor_style_constants_to_css.py", "rename_css_class.py"]
    py_files_to_process = [f for f in py_files_to_process if f.name not in excluded_py_helpers]
    
    python_files_modified_count = 0
    if not py_files_to_process:
        print("No Python files found to process based on scan targets.")
    else:
        for py_file in py_files_to_process:
            if rename_class_in_python_code(py_file, old_class, new_class, dry_run):
                python_files_modified_count +=1
        if python_files_modified_count > 0:
             print(f"Python processing: {python_files_modified_count} file(s) had occurrences of '{old_class}' in 'cls' attributes.")
        else:
             print(f"Python processing: No occurrences of '{old_class}' found in 'cls' attributes in scanned files.")


    # 2. Process CSS file
    print(f"\nProcessing CSS file: {css_file_abs_path.relative_to(project_root)}")
    css_modified = False
    if not new_class:
        print("  [INFO] New class name is empty. Python 'cls' attributes updated to remove the old class.")
        print(f"         Please manually remove the CSS definition for '.{old_class}' from '{css_file_abs_path.name}' if it's no longer needed.")
    elif css_file_abs_path.exists():
        try:
            css_content_original = css_file_abs_path.read_text(encoding="utf-8")
            css_content_modified, css_made_change = rename_class_in_css_file_content(css_content_original, old_class, new_class)
            
            if css_made_change:
                css_modified = True
                print(f"  Found and targeted selectors for '.{old_class}' for renaming in CSS.")
                if not dry_run:
                    css_file_abs_path.write_text(css_content_modified, encoding="utf-8")
                    print(f"    -> Modified and SAVED CSS file: {css_file_abs_path.name}")
                else:
                    print(f"    -> (Dry run) Would modify CSS file: {css_file_abs_path.name}")
            else:
                print(f"  Selector '.{old_class}' not found or no changes made in CSS file: {css_file_abs_path.name}")
        except Exception as e:
            print(f"  Error processing CSS file {css_file_abs_path.name}: {e}")
    else:
        print(f"  [WARN] CSS file not found at {css_file_abs_path}. Cannot rename class in CSS.")

    print("\n--- Summary ---")
    if python_files_modified_count > 0 :
        print(f"Python files: Occurrences of '{old_class}' in 'cls' attributes {'would be' if dry_run else 'were'} updated in {python_files_modified_count} file(s).")
    else:
        print(f"Python files: No occurrences of '{old_class}' found in 'cls' attributes.")

    if new_class: # Only report CSS changes if we are renaming to something
        if css_modified:
            print(f"CSS file ('{css_file_abs_path.name}'): Selectors for '.{old_class}' {'would be' if dry_run else 'were'} renamed to '.{new_class}'.")
        else:
            print(f"CSS file ('{css_file_abs_path.name}'): Selector '.{old_class}' not found or no changes made.")
    
    if not dry_run and (python_files_modified_count > 0 or css_modified):
        print("\nReminder: Review changes with 'git diff' and test your application.")
        if css_modified and old_class != new_class:
             print(f"Consider if the CSS definition for the old class '.{old_class}' needs to be merged or removed if '.{new_class}' already existed with a different definition.")
    elif dry_run and (python_files_modified_count > 0 or css_modified):
        print("\nThis was a dry run. No files were actually changed.")
    else:
        print("\nNo applicable class names found to refactor with the given criteria.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rename CSS classes in Python FastHTML components and CSS files.")
    parser.add_argument("--old-class", required=True, help="The current CSS class name to replace (e.g., 'fs-0p8em').")
    parser.add_argument("--new-class", required=True, help="The new CSS class name (e.g., 'fs-0p9em' or 'note-font'). If renaming to an empty string to effectively delete from Python, be cautious and handle CSS manually.")
    
    parser.add_argument("--project-root", default=".", help="The root directory of the Pipulate project (default: current directory).")
    parser.add_argument("--css-file", default="static/styles.css", help="Path to the CSS file to update, relative to project root (default: 'static/styles.css').")
    parser.add_argument("--scan-targets", nargs='+', default=DEFAULT_SCAN_TARGETS,
                        help=f"List of Python files or directories to scan (relative to project root). Defaults to: {' '.join(DEFAULT_SCAN_TARGETS)}")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without modifying files.")
    
    args = parser.parse_args()

    if not args.old_class.strip():
        print("Error: --old-class cannot be empty.")
    elif not args.new_class.strip() :
        print("Error: --new-class cannot be empty for renaming. If you intend to remove the class, handle CSS manually and ensure Python code removes the class from `cls` attributes.")
    else:
        process_project(args.project_root, args.scan_targets, args.css_file, args.old_class, args.new_class, args.dry_run)
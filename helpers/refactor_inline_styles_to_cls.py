import ast
import os
from pathlib import Path
import re

# This map should be populated based on your analyze_styles.py output
# and the CSS classes you've added to static/styles.css.
# Keys are NORMALIZED inline style strings.
# Values are the corresponding CSS class(es).
STYLE_STRING_TO_CLS_MAP = {
    # From your Top 20 Common Style Strings & previous discussion:
    "color: #666; font-size: 0.9em;": "text-muted-lead", # Covers #1 and #16 from analysis
    "color: #666;": "text-pico-muted", # Style #19
    "color: red;": "text-error", # Style #11
    "cyan": "text-primary", # Style #20 (assuming it was used as style="cyan")
    "display: flex; align-items: center;": "d-flex align-items-center", # Common combo
    "display: none;": "d-none", # Style #9
    "font-size: 0.8em; font-style: italic;": "text-small-italic", # Style #7
    "font-weight: bold;": "fw-bold", # Style #13
    "green": "text-success", # Style #10 (assuming it was used as style="green")
    "margin-bottom: 0.5rem;": "mb-p5rem", # Style #3
    "margin-bottom: 10px;": "mb-10px", # Style #14
    "margin-bottom: 15px;": "mb-15px", # Style #18
    "margin-bottom: 1rem;": "mb-1rem", # Style #6
    "margin-top: 10px;": "mt-10px", # Style #17
    "margin-top: 1rem;": "mt-1rem", # Style #8
    "margin-top: 1vh; text-align: right;": "mt-1vh-text-right", # Style #4
    "padding: 10px; background: var(--pico-card-background-color); border-radius: 5px;": "custom-card-padding-bg", # Style #15
    "padding: 1rem; background-color: var(--pico-code-background); border-radius: var(--pico-border-radius); font-family: monospace; overflow-x: auto;": "code-block-container", # Style #12 (order normalized)
    "width: 100%;": "w-100", # Style #2
    "width: 100%; font-family: monospace;": "w-100 font-monospace", # Style #5

    # Additional common individual utilities that might appear alone in simple style attrs
    "font-family: monospace;": "font-monospace",
    "text-align: right;": "text-right",
    "display: block;": "d-block",
    "overflow-x: auto;": "overflow-x-auto",
    "align-items: center;": "align-items-center", # Often with d-flex
    "display: flex;": "d-flex",
    "padding: 1rem;": "p-1rem", # Pico uses var(--pico-spacing)
    "border-radius: var(--pico-border-radius);": "rounded",
    "border-radius: 5px;": "rounded-5px",
    "cursor: pointer;": "cursor-pointer",
    "list-style-type: none;": "list-style-none",
    "flex-grow: 1;": "flex-grow-1",
    "text-decoration: none;": "text-decoration-none",
    # Specific to Pipulate.revert_control default_style if it's not made a single class like .button-revert
    # For revert_control, a single class `.button-revert` as defined in styles.css is better.
    # If the full string for revert_control was very common, it would be here:
    # "align-items: center; background-color: var(--pico-del-color); border-radius: 4px; cursor: pointer; display: inline-flex; font-size: 0.85rem; line-height: 1; margin: 0; padding: 0.5rem 0.5rem;": "button-revert", # Example
}

def normalize_style_string_for_map(style_str: str) -> str:
    """
    Normalizes a style string for matching against STYLE_STRING_TO_CLS_MAP.
    - Converts to lowercase.
    - Strips leading/trailing whitespace from string and individual declarations.
    - Sorts declarations alphabetically to handle different ordering.
    - Ensures consistent spacing around ':' and ';'.
    """
    if not style_str or not isinstance(style_str, str):
        return ""
    
    s = style_str.strip().lower()
    declarations = [decl.strip() for decl in s.split(';') if decl.strip()]
    
    normalized_declarations = []
    for decl in declarations:
        parts = [p.strip() for p in decl.split(':', 1)]
        if len(parts) == 2:
            normalized_declarations.append(f"{parts[0]}:{parts[1]}")
            
    return '; '.join(sorted(normalized_declarations))


class InlineStyleToClsTransformer(ast.NodeTransformer):
    def __init__(self, style_map):
        super().__init__()
        self.style_map = {normalize_style_string_for_map(k): v for k, v in style_map.items()}
        self.modifications_count = 0
        self.current_filepath = ""

    def visit_Call(self, node):
        # Ensure we are looking at function calls (FastHTML components)
        # We'll rely on finding a 'style' keyword with a string literal.
        
        style_keyword_index = -1
        original_style_str_literal = None
        
        for i, kw in enumerate(node.keywords):
            if kw.arg == 'style':
                if isinstance(kw.value, ast.Constant) and isinstance(kw.value.s, str):
                    style_keyword_index = i
                    original_style_str_literal = kw.value.s
                    break # Found a literal style string
        
        if original_style_str_literal is not None:
            normalized_style = normalize_style_string_for_map(original_style_str_literal)
            
            if normalized_style in self.style_map:
                new_cls_to_add = self.style_map[normalized_style]
                self.modifications_count += 1
                # print(f"DEBUG: Matched style '{original_style_str_literal}' -> normalized '{normalized_style}' -> cls '{new_cls_to_add}' in {self.current_filepath} line {node.lineno}")

                # Remove the 'style' keyword
                node.keywords.pop(style_keyword_index)
                
                # Add or update 'cls' keyword
                cls_keyword_found = False
                for kw_idx, kw_cls in enumerate(node.keywords):
                    if kw_cls.arg == 'cls':
                        cls_keyword_found = True
                        if isinstance(kw_cls.value, ast.Constant) and isinstance(kw_cls.value.s, str):
                            existing_classes = kw_cls.value.s.split()
                            new_classes_list = new_cls_to_add.split()
                            # Add new classes, avoid duplicates
                            for nc in new_classes_list:
                                if nc not in existing_classes:
                                    existing_classes.append(nc)
                            node.keywords[kw_idx].value = ast.Constant(value=" ".join(existing_classes))
                        elif isinstance(kw_cls.value, ast.JoinedStr): # f-string
                            # Safest to append a new string part to the f-string for the new class
                            # This creates cls=f"{original_f_string_parts} new_class_name"
                            # It might result in slightly non-optimal f-strings but is safer.
                            kw_cls.value.values.append(ast.Constant(value=f" {new_cls_to_add}"))
                            print(f"INFO: Appended to existing f-string 'cls' attribute in {self.current_filepath} line {node.lineno}. Review: {ast.unparse(kw_cls.value)}")
                        else:
                            # cls value is a variable or complex expression, log and skip smart merging
                            print(f"WARNING: 'cls' attribute in {self.current_filepath} line {node.lineno} is a complex expression: {ast.unparse(kw_cls.value)}. Adding '{new_cls_to_add}' separately might lead to duplicate 'cls' args or require manual merge if a string expression.")
                            # One option: add it as a new keyword if AST allows, or just warn.
                            # For now, just warning. A more robust solution might involve trying to merge string expressions.
                        break
                
                if not cls_keyword_found:
                    node.keywords.append(ast.keyword(arg='cls', value=ast.Constant(value=new_cls_to_add)))
                    
                return ast.fix_missing_locations(node) # Important for AST consistency

        return self.generic_visit(node)

def process_file(filepath: Path, style_map: dict):
    print(f"Processing {filepath}...")
    try:
        original_content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(original_content)
        
        transformer = InlineStyleToClsTransformer(style_map)
        transformer.current_filepath = str(filepath) # For logging within transformer
        
        modified_tree = transformer.visit(tree)
        
        if transformer.modifications_count > 0:
            modified_code = ast.unparse(modified_tree)
            print(f"--- Modified code for {filepath} ({transformer.modifications_count} changes) ---")
            print(modified_code)
            print(f"--- End of {filepath} ---")
            
            # UNCOMMENT TO WRITE CHANGES TO FILES (MAKE SURE TO BACKUP FIRST!)
            # confirm = input(f"Apply {transformer.modifications_count} changes to {filepath}? (y/N): ")
            # if confirm.lower() == 'y':
            #     filepath.write_text(modified_code, encoding="utf-8")
            #     print(f"Changes written to {filepath}")
            # else:
            #     print(f"Changes for {filepath} NOT written.")
        else:
            print(f"No matching literal inline styles found in {filepath}")
            
    except Exception as e:
        print(f"Error processing file {filepath}: {e}")
        import traceback
        traceback.print_exc()

def main():
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent # Assumes script is in 'helpers'
    
    if project_root.name != 'pipulate': # Simple check
        print(f"Script may not be in the correct 'helpers' directory relative to 'pipulate' project root. Detected root: {project_root}")
        return

    print(f"Starting CSS refactoring. Project root: {project_root}")
    
    server_py_file = project_root / "server.py"
    plugins_path = project_root / "plugins"
    
    files_to_scan = [server_py_file]
    if plugins_path.is_dir():
        for item in plugins_path.iterdir():
            if item.is_file() and item.name.endswith(".py") and not item.name.startswith("__"):
                files_to_scan.append(item)
                
    for py_file in files_to_scan:
        if py_file.exists():
            process_file(py_file, STYLE_STRING_TO_CLS_MAP)
        else:
            print(f"File not found: {py_file}")
            
    print("\nRefactoring script finished. Review output above.")
    print("If you want to apply changes, uncomment the write section in 'process_file' function.")

if __name__ == "__main__":
    main()

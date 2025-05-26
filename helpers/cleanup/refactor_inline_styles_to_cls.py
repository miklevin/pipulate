import ast
import os
from pathlib import Path
import re

# List of known FastHTML component names that accept 'style' and 'cls'
# This helps the script to be more targeted.
FASTHTML_COMPONENT_NAMES = {
    'Div', 'Button', 'Span', 'P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'A', 'Form', 'Input',
    'Li', 'Ul', 'Card', 'Grid', 'Container', 'Details', 'Summary', 'Label', 'Textarea',
    'Select', 'Option', 'Pre', 'Code', 'Hr', 'Script', 'Link', 'Meta', 'Title', 'Group',
    'Main', 'Header', 'Footer', 'Article', 'Nav', 'Aside', 'Section', 'Figure', 'Figcaption',
    'Blockquote', 'Table', 'Thead', 'Tbody', 'Tfoot', 'Tr', 'Th', 'Td', 'Fieldset', 'Legend',
    # Add any custom FastHTML components you've created that follow the same pattern
}

# This map is based on your analysis and the CSS classes in static/styles.css
STYLE_STRING_TO_CLS_MAP = {
    "color: #666; font-size: 0.9em;": "text-muted-lead",
    "color: #666;": "text-pico-muted",
    "color: red;": "text-error",
    "cyan": "text-primary", # was style="cyan"
    "display: flex; align-items: center;": "d-flex align-items-center",
    "display: none;": "d-none",
    "font-size: 0.8em; font-style: italic;": "text-small-italic",
    "font-weight: bold;": "fw-bold",
    "green": "text-success", # was style="green"
    "margin-bottom: 0.5rem;": "mb-p5rem",
    "margin-bottom: 10px;": "mb-10px",
    "margin-bottom: 15px;": "mb-15px",
    "margin-bottom: 1rem;": "mb-1rem",
    "margin-top: 10px;": "mt-10px",
    "margin-top: 1rem;": "mt-1rem",
    "margin-top: 1vh; text-align: right;": "mt-1vh-text-right",
    "padding: 10px; background: var(--pico-card-background-color); border-radius: 5px;": "custom-card-padding-bg",
    "padding: 1rem; background-color: var(--pico-code-background); border-radius: var(--pico-border-radius); font-family: monospace; overflow-x: auto;": "code-block-container",
    "width: 100%;": "w-100",
    "width: 100%; font-family: monospace;": "w-100 font-monospace",
    "font-family: monospace;": "font-monospace",
    "text-align: right;": "text-right",
    "display: block;": "d-block",
    "overflow-x: auto;": "overflow-x-auto",
    "align-items: center;": "align-items-center",
    "display: flex;": "d-flex",
    "padding: 1rem;": "p-1rem",
    "border-radius: var(--pico-border-radius);": "rounded",
    "border-radius: 5px;": "rounded-5px",
    "cursor: pointer;": "cursor-pointer",
    "list-style-type: none;": "list-style-none", # Added from your render_profile example
    "flex-grow: 1;": "flex-grow-1", # Added from your render_profile example
    "text-decoration: none;": "text-decoration-none", # Added
    # From Pipulate.revert_control default_style (if it wasn't fully replaced by a single class)
    # This full string match is preferable if it's exact and common.
    "align-items: center; background-color: var(--pico-del-color); border-radius: 4px; cursor: pointer; display: inline-flex; font-size: 0.85rem; line-height: 1; margin: 0; padding: 0.5rem 0.5rem;": "button-revert",
    # Styles from Pipulate class that might be used directly as literals somewhere
    "font-size: 0.9em; color: var(--pico-muted-color);": "text-muted-lead", # Pipulate.MUTED_TEXT_STYLE
    "margin-top: 1vh; border-top: 1px solid var(--pico-muted-border-color); padding-top: 1vh;": "widget-content-area", # Pipulate.CONTENT_STYLE
    "margin-top: 0.5vh; padding: 0.5vh 0;": "widget-finalized-content", # Pipulate.FINALIZED_CONTENT_STYLE
    "padding: 1vh 0px 0px .5vw;": "menu-item-custom-padding", # Pipulate.MENU_ITEM_PADDING
    "white-space: nowrap; overflow: hidden; text-overflow: ellipsis;": "text-nowrap-ellipsis", # Global NOWRAP_STYLE
    "background-color: #ffdddd; color: #990000; padding: 10px; border-left: 5px solid #990000;": "id-conflict-error-box" # Pipulate.id_conflict_style()
}

def normalize_style_string_for_map(style_str: str) -> str:
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
    def __init__(self, style_map, fasthtml_components):
        super().__init__()
        self.style_map = {normalize_style_string_for_map(k): v for k, v in style_map.items()}
        self.fasthtml_components = fasthtml_components
        self.modifications_count = 0
        self.current_filepath = ""

    def visit_Call(self, node):
        func_name_str = ""
        if isinstance(node.func, ast.Name):
            func_name_str = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name_str = node.func.attr

        # Only proceed if it's a known FastHTML component
        if func_name_str not in self.fasthtml_components:
            return self.generic_visit(node)

        style_keyword_index = -1
        original_style_str_literal = None
        
        for i, kw in enumerate(node.keywords):
            if kw.arg == 'style':
                if isinstance(kw.value, ast.Constant) and isinstance(kw.value.s, str):
                    style_keyword_index = i
                    original_style_str_literal = kw.value.s
                    break 
        
        if original_style_str_literal is not None:
            normalized_style = normalize_style_string_for_map(original_style_str_literal)
            
            if normalized_style in self.style_map:
                new_cls_to_add = self.style_map[normalized_style]
                self.modifications_count += 1
                
                node.keywords.pop(style_keyword_index)
                
                cls_keyword_found_at = -1
                for i, kw_cls in enumerate(node.keywords):
                    if kw_cls.arg == 'cls':
                        cls_keyword_found_at = i
                        break
                
                if cls_keyword_found_at != -1:
                    cls_node = node.keywords[cls_keyword_found_at].value
                    if isinstance(cls_node, ast.Constant) and isinstance(cls_node.s, str):
                        existing_classes = cls_node.s.split()
                        new_classes_list = new_cls_to_add.split()
                        for nc in new_classes_list:
                            if nc not in existing_classes:
                                existing_classes.append(nc)
                        node.keywords[cls_keyword_found_at].value = ast.Constant(value=" ".join(sorted(list(set(existing_classes)))))
                    elif isinstance(cls_node, ast.JoinedStr): # f-string
                        cls_node.values.append(ast.Constant(value=f" {new_cls_to_add}"))
                        print(f"INFO: Appended to existing f-string 'cls' in {self.current_filepath} L{node.lineno}. Review: {ast.unparse(cls_node)}")
                    else:
                        print(f"WARNING: 'cls' in {self.current_filepath} L{node.lineno} is complex: {ast.unparse(cls_node)}. Could not merge '{new_cls_to_add}'.")
                else:
                    node.keywords.append(ast.keyword(arg='cls', value=ast.Constant(value=new_cls_to_add)))
                
                return ast.fix_missing_locations(node)

        return self.generic_visit(node)

def process_file(filepath: Path, style_map: dict, component_names: set):
    print(f"Processing {filepath}...")
    try:
        original_content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(original_content)
        
        transformer = InlineStyleToClsTransformer(style_map, component_names)
        transformer.current_filepath = str(filepath)
        
        modified_tree = transformer.visit(tree)
        ast.fix_missing_locations(modified_tree) # Ensure tree is valid after transformations
        
        if transformer.modifications_count > 0:
            modified_code = ast.unparse(modified_tree)
            print(f"--- Proposed modifications for {filepath} ({transformer.modifications_count} changes) ---")
            print(modified_code)
            print(f"--- End of {filepath} ---")
            
            confirm = input(f"Apply {transformer.modifications_count} changes to {filepath}? (y/N): ")
            if confirm.lower() == 'y':
                filepath.write_text(modified_code, encoding="utf-8")
                print(f"Changes WRITTEN to {filepath}")
            else:
                print(f"Changes for {filepath} NOT written.")
        else:
            print(f"No matching literal inline styles to refactor in {filepath}")
            
    except Exception as e:
        print(f"Error processing file {filepath}: {e}")
        import traceback
        traceback.print_exc()

def main():
    # Determine project root (assuming script is in pipulate/helpers)
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    
    if project_root.name != 'pipulate' and project_root.parent.name == 'pipulate' and project_root.name == 'helpers':
        # If script is run from pipulate/helpers/ via `python refactor_inline_styles_to_cls.py`
        project_root = project_root.parent
    elif project_root.name != 'pipulate':
         # If script is run from pipulate/ via `python helpers/refactor_inline_styles_to_cls.py`
        if (project_root / 'server.py').exists(): # Good heuristic for being in project root
             pass # project_root is correct
        else:
            print(f"Error: Script must be run from the 'pipulate' project root or its 'helpers' subdirectory.")
            print(f"Current detected root: {project_root}")
            return

    print(f"Starting CSS refactoring. Project root: {project_root}")
    
    server_py_file = project_root / "server.py"
    plugins_path = project_root / "plugins"
    
    files_to_scan = []
    if server_py_file.exists():
        files_to_scan.append(server_py_file)
    else:
        print(f"WARNING: server.py not found at {server_py_file}")
        
    if plugins_path.is_dir():
        for item in plugins_path.iterdir():
            if item.is_file() and item.name.endswith(".py") and not item.name.startswith("__"):
                files_to_scan.append(item)
    else:
        print(f"WARNING: Plugins directory not found at {plugins_path}")
                
    if not files_to_scan:
        print("No Python files found to process.")
        return
        
    print(f"\nFound {len(files_to_scan)} Python files to process:")
    for f in files_to_scan: print(f" - {f.relative_to(project_root)}")
    print("")

    for py_file in files_to_scan:
        process_file(py_file, STYLE_STRING_TO_CLS_MAP, FASTHTML_COMPONENT_NAMES)
        
    print("\nRefactoring script finished. Review output above.")
    print("If changes were not automatically applied, review the 'process_file' function to enable writing.")

if __name__ == "__main__":
    main()
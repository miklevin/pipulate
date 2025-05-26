import ast
import os
from pathlib import Path
import re

# List of known FastHTML component names
FASTHTML_COMPONENT_NAMES = {
    'Div', 'Button', 'Span', 'P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'A', 'Form', 'Input',
    'Li', 'Ul', 'Card', 'Grid', 'Container', 'Details', 'Summary', 'Label', 'Textarea',
    'Select', 'Option', 'Pre', 'Code', 'Hr', 'Script', 'Link', 'Meta', 'Title', 'Group',
    'Main', 'Header', 'Footer', 'Article', 'Nav', 'Aside', 'Section', 'Figure', 'Figcaption',
    'Blockquote', 'Table', 'Thead', 'Tbody', 'Tfoot', 'Tr', 'Th', 'Td', 'Fieldset', 'Legend'
}

# Map Python constant names/paths to CSS classes
# This map needs to be comprehensive for the constants you want to refactor.
# For attributes like 'self.ERROR_STYLE', the script will construct the string 'self.ERROR_STYLE'.
# For global constants, it will be just 'NOWRAP_STYLE'.
# For methods like 'self.id_conflict_style()', direct AST replacement is more complex.
# This script primarily targets direct variable/attribute references.
CONSTANT_TO_CLS_MAP = {
    "self.ERROR_STYLE": "text-error",
    "pipulate.ERROR_STYLE": "text-error", # If pipulate instance is passed and used
    "ERROR_STYLE": "text-error", # If used globally

    "self.SUCCESS_STYLE": "text-success",
    "pipulate.SUCCESS_STYLE": "text-success",
    "SUCCESS_STYLE": "text-success",

    "self.MUTED_TEXT_STYLE": "text-muted-lead",
    "pipulate.MUTED_TEXT_STYLE": "text-muted-lead",
    "MUTED_TEXT_STYLE": "text-muted-lead",

    "self.CONTENT_STYLE": "widget-content-area",
    "pipulate.CONTENT_STYLE": "widget-content-area",
    "CONTENT_STYLE": "widget-content-area",

    "self.FINALIZED_CONTENT_STYLE": "widget-finalized-content",
    "pipulate.FINALIZED_CONTENT_STYLE": "widget-finalized-content",
    "FINALIZED_CONTENT_STYLE": "widget-finalized-content",

    "self.MENU_ITEM_PADDING": "menu-item-custom-padding",
    "pipulate.MENU_ITEM_PADDING": "menu-item-custom-padding",
    "MENU_ITEM_PADDING": "menu-item-custom-padding",
    
    "NOWRAP_STYLE": "text-nowrap-ellipsis", # Global constant

    # Note: Handling method calls like self.id_conflict_style() is more complex
    # and might be better for targeted manual/AI refactoring.
    # This script focuses on direct constant/attribute usage.
    # If self.id_conflict_style() always returns the same string that maps to
    # "id-conflict-error-box", then that specific string should have been caught
    # by the first script if used as a literal: style=self.id_conflict_style()
    # If used as style=self.id_conflict_style, this script won't catch it by default
    # unless we add specific logic for Call nodes as style values.
}

class StyleConstantRefactorer(ast.NodeTransformer):
    def __init__(self, constant_map, fasthtml_components):
        super().__init__()
        self.constant_map = constant_map
        self.fasthtml_components = fasthtml_components
        self.modifications_count = 0
        self.current_filepath = ""

    def get_node_str_representation(self, node):
        """Helper to get a string representation of Name or Attribute nodes."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # Recursively build the attribute path (e.g., "self.ERROR_STYLE" or "pipulate.ERROR_STYLE")
            value_path = self.get_node_str_representation(node.value)
            if value_path:
                return f"{value_path}.{node.attr}"
            return node.attr
        return None

    def visit_Call(self, node):
        func_name_str = ""
        if isinstance(node.func, ast.Name):
            func_name_str = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name_str = node.func.attr

        if func_name_str not in self.fasthtml_components:
            return self.generic_visit(node)

        style_keyword_index = -1
        style_value_node = None
        
        for i, kw in enumerate(node.keywords):
            if kw.arg == 'style':
                style_keyword_index = i
                style_value_node = kw.value
                break
        
        if style_value_node is not None:
            # Check if style_value_node is ast.Name or ast.Attribute
            constant_path_str = self.get_node_str_representation(style_value_node)

            if constant_path_str and constant_path_str in self.constant_map:
                new_cls_to_add = self.constant_map[constant_path_str]
                self.modifications_count += 1
                # print(f"DEBUG: Matched constant '{constant_path_str}' -> cls '{new_cls_to_add}' in {self.current_filepath} line {node.lineno}")

                node.keywords.pop(style_keyword_index) # Remove style keyword
                
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
                    elif isinstance(cls_node, ast.JoinedStr):
                        cls_node.values.append(ast.Constant(value=f" {new_cls_to_add}"))
                        print(f"INFO: Appended to existing f-string 'cls' in {self.current_filepath} L{node.lineno}. Review: {ast.unparse(cls_node)}")
                    else:
                        print(f"WARNING: 'cls' in {self.current_filepath} L{node.lineno} is complex: {ast.unparse(cls_node)}. Could not merge '{new_cls_to_add}'.")
                else:
                    node.keywords.append(ast.keyword(arg='cls', value=ast.Constant(value=new_cls_to_add)))
                
                return ast.fix_missing_locations(node)

        return self.generic_visit(node)

def process_file_for_constants(filepath: Path, constant_map: dict, component_names: set):
    print(f"Processing {filepath} for style constants...")
    try:
        original_content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(original_content)
        
        transformer = StyleConstantRefactorer(constant_map, component_names)
        transformer.current_filepath = str(filepath)
        
        modified_tree = transformer.visit(tree)
        ast.fix_missing_locations(modified_tree)
        
        if transformer.modifications_count > 0:
            modified_code = ast.unparse(modified_tree)
            print(f"--- Proposed constant refactors for {filepath} ({transformer.modifications_count} changes) ---")
            print(modified_code)
            print(f"--- End of {filepath} ---")
            
            # confirm = input(f"Apply {transformer.modifications_count} constant changes to {filepath}? (y/N): ")
            # if confirm.lower() == 'y':
            #     filepath.write_text(modified_code, encoding="utf-8")
            #     print(f"Constant changes WRITTEN to {filepath}")
            # else:
            #     print(f"Constant changes for {filepath} NOT written.")
        else:
            print(f"No mapped style constant usages found in {filepath}")
            
    except Exception as e:
        print(f"Error processing file {filepath} for constants: {e}")
        import traceback
        traceback.print_exc()

def main_refactor_constants_script():
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    
    if project_root.name != 'pipulate' and project_root.parent.name == 'pipulate' and project_root.name == 'helpers':
        project_root = project_root.parent
    elif project_root.name != 'pipulate':
        if (project_root / 'server.py').exists():
             pass
        else:
            print(f"Error: Script must be run from the 'pipulate' project root or its 'helpers' subdirectory.")
            print(f"Current detected root: {project_root}")
            return

    print(f"Starting CSS constant refactoring. Project root: {project_root}")
    
    server_py_file = project_root / "server.py"
    plugins_path = project_root / "plugins"
    
    files_to_scan = [server_py_file]
    if plugins_path.is_dir():
        for item in plugins_path.iterdir():
            if item.is_file() and item.name.endswith(".py") and not item.name.startswith("__"):
                files_to_scan.append(item)
                
    if not files_to_scan:
        print("No Python files found to process.")
        return
        
    print(f"\nFound {len(files_to_scan)} Python files to process for constants:")
    for f in files_to_scan: print(f" - {f.relative_to(project_root)}")
    print("")

    for py_file in files_to_scan:
        if py_file.exists():
            process_file_for_constants(py_file, CONSTANT_TO_CLS_MAP, FASTHTML_COMPONENT_NAMES)
        else:
            print(f"File not found: {py_file}")
            
    print("\nConstant refactoring script finished. Review output above.")
    print("If you want to apply changes, uncomment the write section in 'process_file_for_constants' function.")
    print("After running, manually review and remove any unused constant definitions from server.py.")

if __name__ == "__main__":
    main_refactor_constants_script()

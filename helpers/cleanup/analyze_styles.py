import ast
import os
from pathlib import Path
from collections import Counter
import re

# Expand this list with all FastHTML component names used in your project
# This helps the script focus on relevant style attributes.
FASTHTML_COMPONENT_NAMES = {
    'Div', 'Button', 'Span', 'P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'A', 'Form', 'Input',
    'Li', 'Ul', 'Card', 'Grid', 'Container', 'Details', 'Summary', 'Label', 'Textarea',
    'Select', 'Option', 'Pre', 'Code', 'Hr', 'Script', 'Link', 'Meta', 'Title', 'Group',
    'Main', 'Header', 'Footer', 'Article', 'Nav', 'Aside', 'Section', 'Figure', 'Figcaption',
    'Blockquote', 'Table', 'Thead', 'Tbody', 'Tfoot', 'Tr', 'Th', 'Td', 'Fieldset', 'Legend'
    # Add any custom components if they also take a 'style' kwarg
}

class StyleFinder(ast.NodeVisitor):
    def __init__(self):
        self.styles_counter = Counter()
        self.style_locations = {} # Stores (file, line_no, component_name) for each style string
        self.current_file = ""

    def visit_Call(self, node):
        func_name = ''
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        # Check if the function call is likely a FastHTML component
        # Or, to be broader, check any function call that has a 'style' keyword argument.
        # For simplicity, we'll check if func_name is in our known set,
        # OR if 'style' is among its keywords.
        is_potential_component = func_name in FASTHTML_COMPONENT_NAMES
        has_style_kwarg = any(kw.arg == 'style' for kw in node.keywords)

        if is_potential_component or has_style_kwarg:
            for keyword in node.keywords:
                if keyword.arg == 'style':
                    style_value_node = keyword.value
                    style_str = None

                    if isinstance(style_value_node, ast.Constant) and isinstance(style_value_node.value, str):
                        style_str = style_value_node.value.strip()
                    elif isinstance(style_value_node, ast.Name): # style=SOME_PYTHON_CONSTANT
                        style_str = f"PYTHON_CONSTANT:{style_value_node.id}"
                    elif isinstance(style_value_node, ast.JoinedStr): # f-string
                        # Create a generic representation for f-strings
                        # This helps group them if their structure is similar
                        style_str_parts = []
                        for val_node in style_value_node.values:
                            if isinstance(val_node, ast.Constant):
                                style_str_parts.append(val_node.value)
                            elif isinstance(val_node, ast.FormattedValue):
                                style_str_parts.append(f"{{{getattr(val_node.value, 'id', 'expr')}}}") # Generic placeholder
                        style_str = f"F_STRING:{''.join(style_str_parts).strip()}"
                    
                    if style_str and style_str: # Ignore empty styles
                        self.styles_counter[style_str] += 1
                        location_key = (self.current_file, node.lineno, func_name or "UnknownComponent")
                        if style_str not in self.style_locations:
                            self.style_locations[style_str] = []
                        self.style_locations[style_str].append(location_key)
        self.generic_visit(node)

def analyze_project_styles(project_root_str):
    project_root = Path(project_root_str)
    finder = StyleFinder()
    
    # Files to analyze
    py_files_to_scan = []
    py_files_to_scan.extend(project_root.glob("plugins/**/*.py")) # Recursive for plugins
    py_files_to_scan.extend(project_root.glob("helpers/**/*.py")) # Recursive for helpers
    py_files_to_scan.append(project_root / "server.py")

    print(f"Scanning {len(py_files_to_scan)} Python files for inline styles...\n")

    for filepath in py_files_to_scan:
        if not filepath.is_file():
            continue
        # Exclude the analysis script itself or other non-UI generating helpers
        if filepath.name in ["analyze_styles.py", "create_workflow.py", "splice_workflow_step.py"]:
            continue
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                finder.current_file = str(filepath.relative_to(project_root))
                tree = ast.parse(content)
                finder.visit(tree)
        except Exception as e:
            print(f"Could not parse {filepath}: {e}")
            
    print("--- Analysis Complete ---")

    print(f"\n--- Top {min(20, len(finder.styles_counter))} Most Common Inline Style Strings/Representations ---")
    for i, (style, count) in enumerate(finder.styles_counter.most_common(20)):
        print(f"\n{i+1}. Style (Count: {count}):")
        if style.startswith("PYTHON_CONSTANT:"):
            print(f"   [PY_CONST] {style}")
        elif style.startswith("F_STRING:"):
            print(f"   [F_STRING] {style[9:]}") # Print the structure without "F_STRING:"
        else:
            print(f"   ```css\n   {style}\n   ```")
        
        # print("   First 3 Locations:")
        # for f, l, c_name in finder.style_locations.get(style, [])[:3]:
        #     print(f"     - {f}:L{l} (in {c_name or 'unknown'})")
    
    # Analysis of individual declarations
    declaration_counts = Counter()
    for style_str, num in finder.styles_counter.items():
        if style_str.startswith("PYTHON_CONSTANT:") or style_str.startswith("F_STRING:"):
            continue # Skip constants and f-strings for this part
        
        # Normalize: remove extra spaces around semicolons and colons
        style_str_normalized = re.sub(r'\s*;\s*', ';', style_str)
        style_str_normalized = re.sub(r'\s*:\s*', ':', style_str_normalized)
        
        declarations = [d.strip() for d in style_str_normalized.split(';') if d.strip()]
        for decl in declarations:
            declaration_counts[decl] += num # Weight by how many times the block appeared

    print(f"\n--- Top {min(20, len(declaration_counts))} Most Common Individual CSS Declarations ---")
    print("(These are good candidates for utility CSS classes in static/styles.css)")
    for i, (decl, count) in enumerate(declaration_counts.most_common(20)):
        if count > 1: # Only show if declaration is used more than once
             print(f"{i+1}. `{decl}` (Appears in style blocks ~{count} times)")

if __name__ == "__main__":
    # Assuming the script is in pipulate/ (project root) or pipulate/helpers/
    # Adjust CWD if running from a different location.
    current_script_path = Path(__file__).resolve()
    project_root_dir = current_script_path.parent # If in helpers/
    # If analyze_styles.py is in the project root itself, use:
    # project_root_dir = current_script_path.parent 

    # If you are sure that this script is inside the 'helpers' directory, one level below project root:
    if project_root_dir.name == "helpers" and project_root_dir.parent.name == "pipulate":
         project_root_dir = project_root_dir.parent
    elif project_root_dir.name == "pipulate": # If script is directly in pipulate/
        pass # project_root_dir is already correct
    else:
        print(f"Warning: Could not reliably determine project root from {current_script_path}. Assuming current directory.")
        project_root_dir = Path.cwd()


    print(f"Using project root: {project_root_dir}")
    analyze_project_styles(str(project_root_dir))

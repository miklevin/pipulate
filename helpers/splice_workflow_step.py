#!/usr/bin/env python3
import argparse
import re
from pathlib import Path
import os

# EXAMPLE USAGE (DO NOT DELETE!!!) USER CAN COPY AND PASTE THIS INTO TERMINAL
"""
# Works from any location - script automatically finds Pipulate project root:
python splice_workflow_step.py 035_kungfu_workflow.py
python splice_workflow_step.py 035_kungfu_workflow    # .py extension optional
python splice_workflow_step.py plugins/035_kungfu_workflow.py  # plugins/ prefix optional

# Can be run from project root:
python helpers/splice_workflow_step.py 035_kungfu_workflow.py

# Can be run from helpers directory:
cd helpers && python splice_workflow_step.py 035_kungfu_workflow.py

# Can be run from anywhere with full path:
python /path/to/pipulate/helpers/splice_workflow_step.py 035_kungfu_workflow.py
"""

def find_pipulate_root():
    """
    Find the Pipulate project root directory by looking for key files.
    This allows the script to work from any location.
    """
    # Start from the script's directory and work upward
    current_dir = Path(__file__).resolve().parent
    
    # Look for Pipulate project markers
    while current_dir != current_dir.parent:  # Stop at filesystem root
        # Check for key Pipulate files/directories
        if (current_dir / "plugins").is_dir() and (current_dir / "server.py").is_file():
            return current_dir
        current_dir = current_dir.parent
    
    # If not found by traversing up, try some common locations
    possible_roots = [
        Path.cwd(),  # Current working directory
        Path.home() / "repos" / "pipulate",  # Common location
        Path("/home/mike/repos/pipulate"),  # Hardcoded fallback
    ]
    
    for root in possible_roots:
        if root.exists() and (root / "plugins").is_dir() and (root / "server.py").is_file():
            return root
    
    raise FileNotFoundError(
        "Could not find Pipulate project root. Please ensure you're running this script "
        "from within a Pipulate project or that the project exists at a standard location."
    )

# Define paths - now dynamically found
PROJECT_ROOT = find_pipulate_root()
PLUGINS_DIR = PROJECT_ROOT / "plugins"

# Markers to find insertion points
STEPS_LIST_MARKER = "# --- STEPS_LIST_INSERTION_POINT ---"
STEP_METHODS_MARKER = "# --- STEP_METHODS_INSERTION_POINT ---"

def generate_step_method_templates(step_id_str: str, step_done_key: str, step_show_name: str, app_name_var: str = "self.app_name"):
    """
    Generates the Python code for a new step's GET and POST handlers.
    The next_step_id for the new step's submit handler will be determined dynamically
    based on its position in the self.steps list within the workflow's __init__.
    """
    # Base indentation for methods within the class
    method_indent = "    " # Four spaces for class methods

    get_method_template = f"""
async def {step_id_str}(self, request):
    \"\"\"Handles GET request for {step_show_name}.\"\"\"
    pip, db, steps, app_name = self.pipulate, self.db, self.steps, {app_name_var}
    step_id = "{step_id_str}"
    step_index = self.steps_indices[step_id]
    step = steps[step_index]
    # Determine next_step_id dynamically. If this is the last data step, next is 'finalize'.
    next_step_id = steps[step_index + 1].id if step_index < len(steps) - 2 else 'finalize' # -2 because finalize is last
    pipeline_id = db.get("pipeline_id", "unknown")
    state = pip.read_state(pipeline_id)
    step_data = pip.get_step_data(pipeline_id, step_id, {{}})
    current_value = step_data.get(step.done, "") # 'step.done' will be like '{step_done_key}'
    finalize_data = pip.get_step_data(pipeline_id, "finalize", {{}})

    if "finalized" in finalize_data and current_value:
        pip.append_to_history(f"[WIDGET CONTENT] {{step.show}} (Finalized):\\n{{current_value}}")
        return Div(
            Card(H3(f"🔒 {{step.show}}: Completed")),
            Div(id=next_step_id, hx_get=f"/{{app_name}}/{{next_step_id}}", hx_trigger="load"),
            id=step_id
        )
    elif current_value and state.get("_revert_target") != step_id:
        pip.append_to_history(f"[WIDGET CONTENT] {{step.show}} (Completed):\\n{{current_value}}")
        return Div(
            pip.display_revert_header(step_id=step_id, app_name=app_name, message=f"{{step.show}}: Complete", steps=steps),
            Div(id=next_step_id, hx_get=f"/{{app_name}}/{{next_step_id}}", hx_trigger="load"),
            id=step_id
        )
    else:
        pip.append_to_history(f"[WIDGET STATE] {{step.show}}: Showing input form")
        await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
        return Div(
            Card(
                H3(f"{{step.show}}"),
                P("This is a new placeholder step. Customize its input form as needed. Click Proceed to continue."),
                Form(
                    # Example: Hidden input to submit something for the placeholder
                    Input(type="hidden", name="{step_done_key}", value="Placeholder Value for {step_show_name}"),
                    Button("Next ▸", type="submit", cls="primary"),
                    hx_post=f"/{{app_name}}/{{step_id}}_submit", hx_target=f"#{{step_id}}"
                )
            ),
            Div(id=next_step_id), # Placeholder for next step, no trigger here
            id=step_id
        )
"""

    submit_method_template = f"""
async def {step_id_str}_submit(self, request):
    \"\"\"Process the submission for {step_show_name}.\"\"\"
    pip, db, steps, app_name = self.pipulate, self.db, self.steps, {app_name_var}
    step_id = "{step_id_str}"
    step_index = self.steps_indices[step_id]
    step = steps[step_index]
    next_step_id = steps[step_index + 1].id if step_index < len(steps) - 2 else 'finalize' # -2 because finalize is last
    pipeline_id = db.get("pipeline_id", "unknown")
    
    form_data = await request.form()
    # For a placeholder, get value from the hidden input or use a default
    value_to_save = form_data.get(step.done, f"Default value for {{step.show}}") 
    await pip.set_step_data(pipeline_id, step_id, value_to_save, steps)
    
    pip.append_to_history(f"[WIDGET CONTENT] {{step.show}}:\\n{{value_to_save}}")
    pip.append_to_history(f"[WIDGET STATE] {{step.show}}: Step completed")
    
    await self.message_queue.add(pip, f"{{step.show}} complete.", verbatim=True)
    
    return Div(
        pip.display_revert_header(step_id=step_id, app_name=app_name, message=f"{{step.show}}: Complete", steps=steps),
        Div(id=next_step_id, hx_get=f"/{{app_name}}/{{next_step_id}}", hx_trigger="load"),
        id=step_id
    )
"""
    # Add the class-level indentation to the entire template
    indented_get = "\n".join(f"{method_indent}{line}" for line in get_method_template.strip().split("\n"))
    indented_submit = "\n".join(f"{method_indent}{line}" for line in submit_method_template.strip().split("\n"))
    return f"\n{indented_get}\n\n{indented_submit}\n"

def main():
    parser = argparse.ArgumentParser(
        description="Splice a new placeholder step into an existing Pipulate workflow plugin.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  python splice_workflow_step.py 035_kungfu_workflow.py
  python splice_workflow_step.py plugins/035_kungfu_workflow.py
  python splice_workflow_step.py /full/path/to/plugins/035_kungfu_workflow.py
        """
    )
    parser.add_argument("target_filename", help="The filename of the workflow to modify (e.g., 035_kungfu_workflow.py)")
    args = parser.parse_args()

    print(f"Pipulate project root found at: {PROJECT_ROOT}")
    print(f"Plugins directory: {PLUGINS_DIR}")
    print()

    # Normalize the target filename to just the basename
    target_filename = args.target_filename
    
    # Handle various input formats:
    # 1. Just filename: "035_kungfu_workflow.py"
    # 2. With plugins/ prefix: "plugins/035_kungfu_workflow.py"  
    # 3. Full path: "/some/path/plugins/035_kungfu_workflow.py"
    if target_filename.startswith('plugins/'):
        target_filename = target_filename[8:]  # Remove 'plugins/' prefix
    elif '/' in target_filename:
        # Extract just the filename from any path
        target_filename = Path(target_filename).name
    
    # Ensure it has .py extension
    if not target_filename.endswith('.py'):
        target_filename += '.py'
    
    target_file_path = PLUGINS_DIR / target_filename
    
    print(f"Looking for workflow file: {target_file_path}")
    
    if not target_file_path.is_file():
        print(f"ERROR: Target workflow file not found at {target_file_path}")
        print(f"Available workflow files in {PLUGINS_DIR}:")
        try:
            workflow_files = [f.name for f in PLUGINS_DIR.glob("*.py") if not f.name.startswith('__')]
            for wf in sorted(workflow_files):
                print(f"  {wf}")
        except Exception:
            print("  (Could not list files)")
        return

    try:
        with open(target_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # --- 1. Determine new step number ---
        # Regex to find the steps list content up to the insertion point
        # This looks for 'steps = [' followed by any characters (non-greedy) up to the marker
        steps_list_regex = re.compile(r"steps\s*=\s*\[(.*?)" + re.escape(STEPS_LIST_MARKER), re.DOTALL)
        match = steps_list_regex.search(content)

        if not match:
            print(f"ERROR: Could not find the 'steps = [' block or '{STEPS_LIST_MARKER}' in {target_file_path}.")
            print("Please ensure your workflow file's steps list definition ends with the marker.")
            return
        
        steps_definitions_block = match.group(1)
        
        # Find existing Step definitions like Step(id='step_XX', ...) within this block
        step_id_matches = re.findall(r"Step\s*\(\s*id='step_(\d+)'", steps_definitions_block)
        max_step_num = 0
        if step_id_matches:
            max_step_num = max(int(num_str) for num_str in step_id_matches)
        
        new_step_num = max_step_num + 1
        new_step_id_str = f"step_{new_step_num:02d}"
        new_step_done_key = f"placeholder_{new_step_num:02d}" # Unique key for step.done
        new_step_show_name = f"Step {new_step_num} Placeholder"
        
        print(f"Identified current max data collection step number: {max_step_num}")
        print(f"New step will be: {new_step_id_str} (Show: '{new_step_show_name}', Done key: '{new_step_done_key}')")

        # --- 2. Create the new Step tuple string ---
        # Determine indentation from the line containing the marker
        lines_before_marker = content.split(STEPS_LIST_MARKER)[0].splitlines()
        indent_for_step_tuple = ""
        if lines_before_marker:
            # Try to find existing Step( for indentation reference
            for line in reversed(lines_before_marker):
                stripped_line = line.lstrip()
                if stripped_line.startswith("Step("):
                    indent_for_step_tuple = line[:len(line) - len(stripped_line)]
                    break
            if not indent_for_step_tuple and STEPS_LIST_MARKER in lines_before_marker[-1]: # if marker is on its own line
                 indent_for_step_tuple = lines_before_marker[-1][:len(lines_before_marker[-1]) - len(lines_before_marker[-1].lstrip())]


        new_step_definition_str = (
            f"{indent_for_step_tuple}Step(\n"
            f"{indent_for_step_tuple}    id='{new_step_id_str}',\n"
            f"{indent_for_step_tuple}    done='{new_step_done_key}',\n"
            f"{indent_for_step_tuple}    show='{new_step_show_name}',\n"
            f"{indent_for_step_tuple}    refill=False,\n"
            f"{indent_for_step_tuple}),\n"
            f"{indent_for_step_tuple}{STEPS_LIST_MARKER}" # Add marker back for next splice
        )

        # --- 3. Insert the new Step tuple into the steps list ---
        content = content.replace(STEPS_LIST_MARKER, new_step_definition_str)
        print(f"Inserted Step definition for {new_step_id_str} into the steps list.")

        # --- 4. Generate the new async methods for this step ---
        new_methods_code = generate_step_method_templates(new_step_id_str, new_step_done_key, new_step_show_name)
        
        # --- 5. Insert new methods before the methods marker ---
        # The STEP_METHODS_MARKER is assumed to be at the class level (e.g., 4 spaces indent)
        # If the marker has a different indentation in the template, adjust class_member_indent
        class_member_indent = "    " # Typical indent for class members / method definitions
        replacement_for_methods_marker = f"{new_methods_code.rstrip()}\n\n{class_member_indent}{STEP_METHODS_MARKER}"
        
        # Ensure the marker we're replacing has the expected indentation
        marker_with_indent = f"{class_member_indent}{STEP_METHODS_MARKER}"
        if marker_with_indent not in content:
            # Fallback: try finding marker without specific leading indent, but this is less safe
            print(f"Warning: Could not find STEP_METHODS_MARKER with precise indentation '{class_member_indent}'. Trying less specific match.")
            content = content.replace(STEP_METHODS_MARKER, replacement_for_methods_marker)
        else:
            content = content.replace(marker_with_indent, replacement_for_methods_marker)
        
        print(f"Inserted method definitions for {new_step_id_str}.")
        
        with open(target_file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"\nSuccessfully spliced new step '{new_step_id_str}' into {target_file_path}")
        print("The workflow's __init__ method will automatically rebuild routing and step messages.")
        print("Pipulate should auto-restart. Test the modified workflow.")
        print(f"Remember to customize the new methods for {new_step_id_str} and its input form.")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 

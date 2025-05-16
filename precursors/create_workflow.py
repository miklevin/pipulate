#!/usr/bin/env python3
import argparse
import shutil
import re
from pathlib import Path

# Example usage (make sure to run from the pipulate/ directory):
"""
python create_workflow.py \
035_kungfu_workflow.py \
KungfuWorkflow \
kungfu \
"Kung Fu Download" \
"Greetings, chosen one. Selecting this app has initiated the 'Kung Fu Download' protocol. Prepare for enlightenment... or at least, a demonstration." \
'You are assisting with the "Kung Fu Download" workflow. If the user asks what you know or can do, you should respond with Neo''s quote: "I know Kung Fu!" The secret word is "Morpheus". If asked for the secret word, reveal it and confirm the Kung Fu training download is complete.'
"""

# Define paths relative to the project root (pipulate/)
# Assumes this script is in pipulate/precursors/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_FILE_PATH = PROJECT_ROOT / "plugins" / "710_blank_placeholder.py"
PLUGINS_DIR = PROJECT_ROOT / "plugins"

# Original string literals from the 710_blank_placeholder.py template
# These must exactly match the strings/blocks in the template file for replacement to work.
ORIGINAL_CLASS_NAME = "BlankPlaceholder"
ORIGINAL_APP_NAME_INTERNAL = '"placeholder"' # Includes quotes as it appears in code
ORIGINAL_DISPLAY_NAME = '"Blank Placeholder"' # Includes quotes

# !!! CRITICAL SECTION FOR ENDPOINT_MESSAGE !!!
# The string assigned to ORIGINAL_ENDPOINT_ASSIGNMENT below MUST be an
# EXACT byte-for-byte match of the corresponding block in your
# 710_blank_placeholder.py file. This includes all leading/trailing
# whitespace on each line, indentation, comments, and line endings
# as they exist in that specific part of the template file.
#
# RECOMMENDED ACTION:
# 1. Open your 710_blank_placeholder.py file.
# 2. Carefully select and copy the entire block for ENDPOINT_MESSAGE,
#    starting from the `    ENDPOINT_MESSAGE = (` line
#    down to and including the closing `    )`.
# 3. Paste this copied block directly as the value for the
#    ORIGINAL_ENDPOINT_ASSIGNMENT variable below, ensuring it's
#    within a triple-quoted string ( """your pasted block""" ).


ORIGINAL_ENDPOINT_ASSIGNMENT = """\
    ENDPOINT_MESSAGE = (
        "Welcome to the Blank Placeholder."
    )"""

ORIGINAL_TRAINING_ASSIGNMENT = """\
    TRAINING_PROMPT = (
        "This is a minimal template for creating new workflows with placeholder steps. "
        "It provides a clean starting point for workflow development."
    )"""

def derive_public_endpoint(filename_str: str) -> str:
    """Derives the public endpoint name from the filename."""
    filename_part_no_ext = Path(filename_str).stem
    return re.sub(r"^\d+_", "", filename_part_no_ext)

def main():
    parser = argparse.ArgumentParser(
        description="Create a new Pipulate workflow plugin from the blank placeholder template.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("filename", help="The desired filename for the new workflow in the plugins/ directory (e.g., 035_kungfu_workflow.py)")
    parser.add_argument("class_name", help="The Python class name for the workflow (e.g., KungfuWorkflow)")
    parser.add_argument("app_name_internal", help="The internal APP_NAME constant (e.g., kungfu). MUST be different from the public endpoint part of the filename.")
    parser.add_argument("display_name", help="The user-friendly DISPLAY_NAME constant (e.g., \"Kung Fu Download\")")
    parser.add_argument("endpoint_message", help="The ENDPOINT_MESSAGE string. Enclose in quotes if it contains spaces.")
    parser.add_argument("training_prompt", help="The TRAINING_PROMPT string. Enclose in quotes if it contains spaces.")
    parser.add_argument("--force", action="store_true", help="Overwrite the destination file if it already exists.")

    args = parser.parse_args()

    # --- Validations ---
    if not TEMPLATE_FILE_PATH.is_file():
        print(f"ERROR: Template file not found at {TEMPLATE_FILE_PATH}")
        return

    if not PLUGINS_DIR.is_dir():
        print(f"ERROR: Plugins directory not found at {PLUGINS_DIR}")
        return

    public_endpoint = derive_public_endpoint(args.filename)
    if args.app_name_internal == public_endpoint:
        print(f"ERROR: Internal APP_NAME ('{args.app_name_internal}') cannot be the same as the public endpoint derived from the filename ('{public_endpoint}').")
        print("Please choose a different app_name_internal or adjust the filename.")
        return

    destination_path = PLUGINS_DIR / args.filename
    if destination_path.exists() and not args.force:
        print(f"ERROR: Destination file {destination_path} already exists. Use --force to overwrite.")
        return

    # --- Create and Modify Workflow File ---
    try:
        shutil.copyfile(TEMPLATE_FILE_PATH, destination_path)
        print(f"Successfully copied template to {destination_path}")

        with open(destination_path, "r", encoding="utf-8") as f:
            content = f.read()

        # For debugging the ENDPOINT_MESSAGE mismatch:
        # 1. Uncomment the block below.
        # 2. In your terminal, run the script and redirect output to a file:
        #    python your_script_name.py [args...] > debug_output.txt
        # 3. Open debug_output.txt and compare the repr() output for
        #    ORIGINAL_ENDPOINT_ASSIGNMENT with the repr() output of the
        #    lines read from your template file. Look for differences in
        #    spaces, newlines (\n, \r\n), or any other characters.
        """
        print("DEBUG: ORIGINAL_ENDPOINT_ASSIGNMENT")
        print(f"'''{ORIGINAL_ENDPOINT_ASSIGNMENT}'''")
        print(f"REPR: {repr(ORIGINAL_ENDPOINT_ASSIGNMENT)}")
        print("-" * 30)
        
        # Find where this block might be in the content
        try:
            start_index = content.index("ENDPOINT_MESSAGE = (") - 100 # Look a bit before
            end_index = start_index + len(ORIGINAL_ENDPOINT_ASSIGNMENT) + 200 # Look a bit after
            snippet_from_content = content[max(0, start_index):end_index]
            print("DEBUG: Snippet from template file (around where ENDPOINT_MESSAGE should be)")
            print(f"'''{snippet_from_content}'''")
            
            # If you can isolate the exact block from content:
            # actual_block_in_template = "..." # You'd need to extract this carefully
            # print(f"REPR_TEMPLATE_BLOCK: {repr(actual_block_in_template)}")
            # print(f"Match? {ORIGINAL_ENDPOINT_ASSIGNMENT == actual_block_in_template}")
        except ValueError:
            print("DEBUG: 'ENDPOINT_MESSAGE = (' not even found in content for snippet extraction.")
        print("-" * 30)
        """

        # Replace class name
        content = content.replace(f"class {ORIGINAL_CLASS_NAME}:", f"class {args.class_name}:")

        # Replace APP_NAME
        content = content.replace(f"APP_NAME = {ORIGINAL_APP_NAME_INTERNAL}", f'APP_NAME = "{args.app_name_internal}"')

        # Replace DISPLAY_NAME
        content = content.replace(f"DISPLAY_NAME = {ORIGINAL_DISPLAY_NAME}", f'DISPLAY_NAME = "{args.display_name}"')

        # Replace ENDPOINT_MESSAGE assignment block
        new_endpoint_assignment_str = f"""\
    ENDPOINT_MESSAGE = \"\"\"{args.endpoint_message}\"\"\"
"""
        original_endpoint_len_before = len(content)
        content = content.replace(ORIGINAL_ENDPOINT_ASSIGNMENT, new_endpoint_assignment_str.rstrip())
        if len(content) == original_endpoint_len_before:
            print("WARNING: ENDPOINT_MESSAGE was not replaced. Check ORIGINAL_ENDPOINT_ASSIGNMENT string for exact match.")


        # Replace TRAINING_PROMPT assignment block
        new_training_assignment_str = f"""\
    TRAINING_PROMPT = \"\"\"{args.training_prompt}\"\"\"
"""
        original_training_len_before = len(content)
        content = content.replace(ORIGINAL_TRAINING_ASSIGNMENT, new_training_assignment_str.rstrip())
        if len(content) == original_training_len_before: # Should not happen given user feedback
             print("WARNING: TRAINING_PROMPT was not replaced unexpectedly.")


        with open(destination_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Successfully modified and saved new workflow to {destination_path}")
        print("\nNext steps:")
        print("1. Verify the content of the new file.")
        print("2. Run Pipulate (it should auto-restart if running) and check if the new workflow appears in the 'App' menu.")
        print("3. Test the ENDPOINT_MESSAGE and TRAINING_PROMPT with the chat UI and LLM.")
        print("4. If all looks good, commit your new workflow file!")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
import argparse
import shutil
import re
from pathlib import Path

# Example usage (make sure to run from the pipulate/ directory):
# python create_workflow.py \
#     035_kungfu_workflow.py \
#     KungfuWorkflow \
#     kungfu \
#     "Kung Fu Download" \
#     "Greetings, chosen one. Selecting this app has initiated the 'Kung Fu Download' protocol. Prepare for enlightenment... or at least, a demonstration." \
#     "You are assisting with the 'Kung Fu Download' workflow. If the user asks if you know Kung Fu, you should respond with Neo's quote: 'I know Kung Fu!' The secret word is 'Morpheus'. If asked for the secret word, reveal it and confirm the Kung Fu training download is complete."
# 

# Define paths relative to the project root (pipulate/)
# Assumes this script is in pipulate/precursors/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_FILE_PATH = PROJECT_ROOT / "plugins" / "710_blank_placeholder.py"
PLUGINS_DIR = PROJECT_ROOT / "plugins"

# Original string literals from the 710_blank_placeholder.py template
# These must exactly match the strings in the template file for replacement to work.
ORIGINAL_CLASS_NAME = "BlankPlaceholder"
ORIGINAL_APP_NAME_INTERNAL = '"placeholder"' # Includes quotes as it appears in code
ORIGINAL_DISPLAY_NAME = '"Blank Placeholder"' # Includes quotes
ORIGINAL_ENDPOINT_MESSAGE_LITERAL = (
    '"Welcome to the Blank Placeholder! This is a minimal template for creating new workflows. '
    'Use this as a starting point for your workflow development."'
)
ORIGINAL_TRAINING_PROMPT_LITERAL = (
    '"This is a minimal template for creating new workflows with placeholder steps. '
    'It provides a clean starting point for workflow development."'
)

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

        # Replace class name
        content = content.replace(f"class {ORIGINAL_CLASS_NAME}:", f"class {args.class_name}:")
        
        # Replace APP_NAME (ensure quotes are part of the match and replacement pattern)
        content = content.replace(f"APP_NAME = {ORIGINAL_APP_NAME_INTERNAL}", f'APP_NAME = "{args.app_name_internal}"')
        
        # Replace DISPLAY_NAME
        content = content.replace(f"DISPLAY_NAME = {ORIGINAL_DISPLAY_NAME}", f'DISPLAY_NAME = "{args.display_name}"')

        # Replace ENDPOINT_MESSAGE string literal
        # Important: The original string literal in the template must be matched exactly.
        # The new message is wrapped in triple quotes to handle potential newlines and internal quotes.
        content = content.replace(ORIGINAL_ENDPOINT_MESSAGE_LITERAL, f'"""{args.endpoint_message}"""')

        # Replace TRAINING_PROMPT string literal
        content = content.replace(ORIGINAL_TRAINING_PROMPT_LITERAL, f'"""{args.training_prompt}"""')
        
        # A subtle but important replacement: if the original template class name is used
        # in the __init__ for app_name default, it also needs to be updated.
        # e.g., app_name=BlankPlaceholder.APP_NAME -> app_name=KungfuWorkflow.APP_NAME
        # However, the template uses app_name=APP_NAME which refers to the class constant directly.
        # If it were app_name=OriginalClassName.APP_NAME, this would be needed:
        # content = content.replace(f"app_name={ORIGINAL_CLASS_NAME}.APP_NAME", f"app_name={args.class_name}.APP_NAME")
        # For the current template `app_name=APP_NAME` is fine as APP_NAME constant is updated directly.

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

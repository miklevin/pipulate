#!/usr/bin/env python3
import argparse
import shutil
import re
from pathlib import Path

# Define paths relative to the project root (pipulate/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_FILE_PATH = PROJECT_ROOT / "plugins" / "710_blank_placeholder.py"
PLUGINS_DIR = PROJECT_ROOT / "plugins"

# --- Constants to match exact lines in the template ---
# These must include the leading indentation as it appears in 710_blank_placeholder.py
# Assuming 4 spaces for indentation within the class body. Adjust if necessary.
INDENTATION = "    "

ORIGINAL_CLASS_NAME_LINE = f"{INDENTATION}class BlankPlaceholder:" # Used for replacing the class declaration itself for the new name
# For class attributes, we match the whole line including indentation
ORIGINAL_APP_NAME_LINE = f"{INDENTATION}APP_NAME = 'placeholder'"
ORIGINAL_DISPLAY_NAME_LINE = f"{INDENTATION}DISPLAY_NAME = 'Blank Placeholder'"
ORIGINAL_ENDPOINT_MESSAGE_LINE = f"{INDENTATION}ENDPOINT_MESSAGE = 'Welcome to the Blank Placeholder.'"
ORIGINAL_TRAINING_PROMPT_LINE = (
    f"{INDENTATION}TRAINING_PROMPT = 'This is a minimal template for creating new workflows with placeholder steps. "
    "It provides a clean starting point for workflow development.'"
)
# The original class name itself, without the 'class' keyword, for other replacements if any.
ORIGINAL_CLASS_NAME_IDENTIFIER = "BlankPlaceholder"


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

    try:
        shutil.copyfile(TEMPLATE_FILE_PATH, destination_path)
        print(f"Successfully copied template to {destination_path}")

        with open(destination_path, "r", encoding="utf-8") as f:
            content = f.read()

        replacements_made = {
            "class_name": False,
            "app_name": False,
            "display_name": False,
            "endpoint_message": False,
            "training_prompt": False
        }

        # Replace class name declaration
        # This targets "class BlankPlaceholder:"
        new_class_declaration = f"{INDENTATION}class {args.class_name}:"
        if ORIGINAL_CLASS_NAME_LINE in content:
            content = content.replace(ORIGINAL_CLASS_NAME_LINE, new_class_declaration)
            replacements_made["class_name"] = True
        
        # Also replace any other occurrences of the class name identifier if needed (e.g., in comments or docstrings)
        # Be careful with this to avoid unintended replacements. For now, we focus on the main attributes.
        # Example: content = content.replace(ORIGINAL_CLASS_NAME_IDENTIFIER, args.class_name)


        # Replace APP_NAME line
        new_app_name_line = f"{INDENTATION}APP_NAME = '{args.app_name_internal}'" # Use single quotes for consistency
        if ORIGINAL_APP_NAME_LINE in content:
            content = content.replace(ORIGINAL_APP_NAME_LINE, new_app_name_line)
            replacements_made["app_name"] = True

        # Replace DISPLAY_NAME line
        new_display_name_line = f"{INDENTATION}DISPLAY_NAME = '{args.display_name}'" # Use single quotes
        if ORIGINAL_DISPLAY_NAME_LINE in content:
            content = content.replace(ORIGINAL_DISPLAY_NAME_LINE, new_display_name_line)
            replacements_made["display_name"] = True
        
        # Replace ENDPOINT_MESSAGE line
        # Using triple quotes for args.endpoint_message allows it to contain single/double quotes
        new_endpoint_message_line = f'{INDENTATION}ENDPOINT_MESSAGE = """{args.endpoint_message}"""'
        if ORIGINAL_ENDPOINT_MESSAGE_LINE in content:
            content = content.replace(ORIGINAL_ENDPOINT_MESSAGE_LINE, new_endpoint_message_line)
            replacements_made["endpoint_message"] = True

        # Replace TRAINING_PROMPT line
        new_training_prompt_line = f'{INDENTATION}TRAINING_PROMPT = """{args.training_prompt}"""'
        if ORIGINAL_TRAINING_PROMPT_LINE in content:
            content = content.replace(ORIGINAL_TRAINING_PROMPT_LINE, new_training_prompt_line)
            replacements_made["training_prompt"] = True

        with open(destination_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Successfully modified and saved new workflow to {destination_path}")
        
        for key, replaced in replacements_made.items():
            if not replaced:
                print(f"WARNING: {key.replace('_', ' ').title()} was not replaced. Check the corresponding ORIGINAL_ constant in create_workflow.py and compare it with the template file {TEMPLATE_FILE_PATH}.")

        print("\nNext steps:")
        print("1. Verify the content of the new file, especially the class name and constants.")
        print("2. Run Pipulate (it should auto-restart if running) and check if the new workflow appears in the 'App' menu with the correct DISPLAY_NAME.")
        print("3. Test the ENDPOINT_MESSAGE and TRAINING_PROMPT with the chat UI and LLM.")
        print("4. If all looks good, commit your new workflow file!")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
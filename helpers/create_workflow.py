#!/usr/bin/env python3
import argparse
import shutil
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_FILE_PATH = PROJECT_ROOT / "plugins" / "710_blank_placeholder.py"
PLUGINS_DIR = PROJECT_ROOT / "plugins"

# For the class declaration itself, assuming it's at the top level of the module (0 indentation)
ORIGINAL_CLASS_DECLARATION_REGEX = r"class\s+BlankPlaceholder\s*:"
# Attributes/methods *inside* the class will use this:
ATTRIBUTE_INDENTATION = "    " # Four spaces

# Exact string matches for attributes
ORIGINAL_APP_NAME_LINE = f"{ATTRIBUTE_INDENTATION}APP_NAME = 'placeholder'"
ORIGINAL_DISPLAY_NAME_LINE = f"{ATTRIBUTE_INDENTATION}DISPLAY_NAME = 'Blank Placeholder'"
ORIGINAL_ENDPOINT_MESSAGE_LINE = f"{ATTRIBUTE_INDENTATION}ENDPOINT_MESSAGE = 'Welcome to the Blank Placeholder. This is a starting point for your new workflow.'"
ORIGINAL_TRAINING_PROMPT_LINE = (
    f"{ATTRIBUTE_INDENTATION}TRAINING_PROMPT = 'This is a minimal workflow template. It has one placeholder step. The user will customize it.'"
)
ORIGINAL_CLASS_NAME_IDENTIFIER = "BlankPlaceholder" # For docstrings etc.


def derive_public_endpoint(filename_str: str) -> str:
    filename_part_no_ext = Path(filename_str).stem
    return re.sub(r"^\d+_", "", filename_part_no_ext)

def main():
    parser = argparse.ArgumentParser(
        description="Create a new Pipulate workflow plugin from the blank placeholder template.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("filename", help="Desired filename (e.g., 035_kungfu_workflow.py)")
    parser.add_argument("class_name", help="Python class name (e.g., KungfuWorkflow)")
    parser.add_argument("app_name_internal", help="Internal APP_NAME constant (e.g., kungfu_internal)")
    parser.add_argument("display_name", help="User-friendly DISPLAY_NAME (e.g., \"Kung Fu Download\")")
    parser.add_argument("endpoint_message", help="ENDPOINT_MESSAGE string.")
    parser.add_argument("training_prompt", help="TRAINING_PROMPT string.")
    parser.add_argument("--force", action="store_true", help="Overwrite if exists.")
    args = parser.parse_args()

    if not TEMPLATE_FILE_PATH.is_file():
        print(f"ERROR: Template file not found: {TEMPLATE_FILE_PATH}")
        return
    if not PLUGINS_DIR.is_dir():
        print(f"ERROR: Plugins directory not found: {PLUGINS_DIR}")
        return

    public_endpoint = derive_public_endpoint(args.filename)
    if args.app_name_internal == public_endpoint:
        print(f"WARNING: Internal APP_NAME ('{args.app_name_internal}') is the same as the public endpoint ('{public_endpoint}'). Consider making them different for clarity.")

    destination_path = PLUGINS_DIR / args.filename
    if destination_path.exists() and not args.force:
        print(f"ERROR: File {destination_path} already exists. Use --force.")
        return

    try:
        shutil.copyfile(TEMPLATE_FILE_PATH, destination_path)
        print(f"Copied template to {destination_path}")

        with open(destination_path, "r+", encoding="utf-8") as f:
            content = f.read()
            original_content = content # For checking if changes were made

            # Replace class name declaration using regex for flexibility with whitespace
            new_class_declaration = f"class {args.class_name}:"
            content, count = re.subn(ORIGINAL_CLASS_DECLARATION_REGEX, new_class_declaration, content, count=1)
            if count == 0:
                print(f"WARNING: Class declaration 'class BlankPlaceholder:' not found or not replaced.")
            
            # Replace attributes using exact string match (more reliable if template is fixed)
            replacements = [
                (ORIGINAL_APP_NAME_LINE, f"{ATTRIBUTE_INDENTATION}APP_NAME = '{args.app_name_internal}'"),
                (ORIGINAL_DISPLAY_NAME_LINE, f"{ATTRIBUTE_INDENTATION}DISPLAY_NAME = '{args.display_name}'"),
                (ORIGINAL_ENDPOINT_MESSAGE_LINE, f'{ATTRIBUTE_INDENTATION}ENDPOINT_MESSAGE = """{args.endpoint_message}"""'),
                (ORIGINAL_TRAINING_PROMPT_LINE, f'{ATTRIBUTE_INDENTATION}TRAINING_PROMPT = """{args.training_prompt}"""')
            ]
            
            for old, new in replacements:
                if old in content:
                    content = content.replace(old, new, 1)
                else:
                    print(f"WARNING: Pattern not found for attribute replacement: '{old}'")
            
            # Replace class name in docstring
            docstring_pattern = rf'("""\s*\n\s*)({ORIGINAL_CLASS_NAME_IDENTIFIER}\s+Workflow)'
            # Corrected replacement to preserve indentation after """
            new_docstring_replacement = rf'\1{args.class_name} Workflow'
            content, doc_count = re.subn(docstring_pattern, new_docstring_replacement, content, count=1, flags=re.MULTILINE)
            if doc_count == 0:
                 print(f"WARNING: Docstring for '{ORIGINAL_CLASS_NAME_IDENTIFIER} Workflow' not found or not replaced.")


            if content != original_content:
                f.seek(0)
                f.write(content)
                f.truncate()
                print(f"Successfully modified and saved: {destination_path}")
            else:
                print("No changes made to the file content. Please check replacement patterns and template.")

    except Exception as e:
        print(f"An error occurred during create_workflow: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
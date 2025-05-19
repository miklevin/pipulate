#!/usr/bin/env python3
import argparse
import os
from pathlib import Path

# Strings to search and replace
OLD_STRING = "context_foo.py"
NEW_STRING = "prompt_foo.py"

# Directories to skip
EXCLUDED_DIRS = {
    ".git",
    ".ipynb_checkpoints",
    "__pycache__",
    ".venv",
    "_site",
    ".gem",
    ".bundle",
    ".jekyll-cache",
    # Add any other directories you might want to exclude by default
    # For example, Pipulate specific build/cache dirs if any arise
}

def process_file(file_path: Path) -> bool:
    """
    Reads a file, replaces occurrences of OLD_STRING with NEW_STRING,
    and writes back to the file if changes were made.

    Args:
        file_path: Path object for the file to process.

    Returns:
        True if the file was modified, False otherwise.
    """
    try:
        # Read the file content
        content = file_path.read_text(encoding="utf-8")

        # Check if the old string exists
        if OLD_STRING not in content:
            return False

        # Perform the replacement
        new_content = content.replace(OLD_STRING, NEW_STRING)

        # Write the modified content back if it's different
        if new_content != content:
            file_path.write_text(new_content, encoding="utf-8")
            print(f"Modified: {file_path}")
            return True
        else:
            # This case should ideally not be hit if OLD_STRING was found,
            # but it's a safeguard.
            return False

    except UnicodeDecodeError:
        print(f"Skipped (not UTF-8): {file_path}")
        return False
    except IOError as e:
        print(f"Error processing file {file_path}: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred with file {file_path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description=f"Recursively search for '{OLD_STRING}' and replace with '{NEW_STRING}' in files.",
        epilog="Skips directories like .git, .venv, __pycache__, etc."
    )
    parser.add_argument(
        "target_directory",
        nargs="?",
        default=".",
        help="The directory to start searching from. Defaults to the current directory if not provided."
    )

    args = parser.parse_args()

    start_dir = Path(args.target_directory).resolve()

    if not start_dir.is_dir():
        print(f"Error: Target directory '{start_dir}' does not exist or is not a directory.")
        return

    print(f"Starting search and replace in: {start_dir}")
    print(f"Searching for: '{OLD_STRING}'")
    print(f"Replacing with: '{NEW_STRING}'")
    print(f"Excluded directories: {', '.join(EXCLUDED_DIRS)}\n")

    modified_files_count = 0

    for root, dirs, files in os.walk(start_dir, topdown=True):
        # Modify 'dirs' in-place to exclude specified directories from traversal
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        current_path = Path(root)
        for filename in files:
            file_path = current_path / filename
            if process_file(file_path):
                modified_files_count += 1

    print(f"\nFinished processing.")
    print(f"Total files modified: {modified_files_count}")

if __name__ == "__main__":
    main()
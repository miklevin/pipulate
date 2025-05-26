#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

# --- Configuration ---
# Assuming this script is in pipulate/helpers/
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
PLUGINS_DIR = PROJECT_ROOT / "plugins"

# Commands to run for each Python file
COMMANDS_TO_RUN = [
    "autopep8 --ignore E501,F405,F403,F541 --in-place {filepath}",
    "isort {filepath}",
]

# Files or directories within PLUGINS_DIR to exclude explicitly
EXCLUDE_PATTERNS = [
    "__pycache__", # Standard Python cache directory
    # Add other specific file names or directory names if needed
    # e.g., "my_experimental_plugin.py", "temp_files/"
]

def run_formatting_on_plugins():
    """
    Iterates through Python files in the PLUGINS_DIR and applies formatting commands.
    """
    if not PLUGINS_DIR.is_dir():
        print(f"Error: Plugins directory not found at '{PLUGINS_DIR}'")
        return

    print(f"Starting formatting process for Python files in: {PLUGINS_DIR}\n")
    processed_files = 0
    skipped_files = 0

    for item in PLUGINS_DIR.iterdir():
        # Skip explicitly excluded patterns
        if item.name in EXCLUDE_PATTERNS:
            print(f"Skipping excluded item: {item.name}")
            skipped_files +=1
            continue

        if item.is_file() and item.suffix == ".py":
            # Skip __init__.py files if they exist (often don't need this formatting)
            if item.name == "__init__.py":
                print(f"Skipping __init__.py file: {item.resolve()}")
                skipped_files +=1
                continue

            filepath_str = str(item.resolve())
            print(f"Processing: {item.name}...")
            processed_files += 1
            for cmd_template in COMMANDS_TO_RUN:
                command = cmd_template.format(filepath=filepath_str)
                try:
                    print(f"  Running: {command.split()[0]} on {item.name}")
                    # Using shell=False is generally safer if command components are controlled
                    # Using shell=True can be a security risk if paths are uncontrolled
                    # Here, filepath_str is constructed, so it's relatively safe, but being explicit is good.
                    result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
                    if result.stdout:
                        print(f"    Output: {result.stdout.strip()}")
                    if result.stderr:
                        print(f"    Stderr: {result.stderr.strip()}")
                except subprocess.CalledProcessError as e:
                    print(f"  Error running command on {item.name}: {command.split()[0]}")
                    print(f"    Return code: {e.returncode}")
                    print(f"    Stdout: {e.stdout.strip()}")
                    print(f"    Stderr: {e.stderr.strip()}")
                    # Optionally, decide if you want to stop on error or continue
            print(f"  Finished processing {item.name}\n")
        elif item.is_dir():
            # Currently, the prompt asks for a flat directory.
            # If recursive processing is needed later, this is where it would go.
            print(f"Skipping directory: {item.name} (script processes flat directory as per prompt)")
            skipped_files += 1


    print("--- Formatting Complete ---")
    print(f"Processed {processed_files} Python files.")
    if skipped_files > 0:
        print(f"Skipped {skipped_files} items (e.g., excluded patterns, __init__.py, or directories).")

if __name__ == "__main__":
    run_formatting_on_plugins()
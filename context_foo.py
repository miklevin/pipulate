import os
import sys

# --- Configuration from original script ---
repo_root = "/home/mike/repos/pipulate"  # Make sure this path is correct for your system
output_filename = "foo.txt"

pre_prompt = (
    "You are about to receive a large context dump from a local-first Python web framework called Pipulate. "
    "This framework intentionally uses server-side state and HTMX for UI updates, avoiding complex ORM or "
    "FastAPI patterns in favor of simplicity and observability. It transforms Jupyter notebook-style WET code "
    "into web applications while maintaining a consistent UI pattern. The framework uses a hybrid Nix+virtualenv "
    "approach for dependency management. Please keep these design choices in mind as you review the following files."
)

# Using a multi-line string with a leading backslash prevents an initial blank line.
file_list = """\
README.md
flake.nix
server.py
plugins/hello_workflow.py
training/hello_workflow.md
plugins/tasks.py
training/tasks.md
.cursorrules
""".splitlines()

post_prompt = (
    "Reinforce whatever was said in the prefacing prompt, "
    "plus explicit instructions of what's expected next."
)

# --- Core Logic to Create foo.txt ---
lines = []

# Add the pre-prompt and a separator
lines.append(pre_prompt)
lines.append("=" * 20 + " START CONTEXT " + "=" * 20)

# Process each file in the list
for relative_path in file_list:
    relative_path = relative_path.strip()
    if not relative_path:
        continue

    full_path = os.path.join(repo_root, relative_path)
    start_marker = f"# <<< START FILE: {full_path} >>>"
    end_marker = f"# <<< END FILE: {full_path} >>>"
    
    lines.append(start_marker)
    try:
        with open(full_path, 'r', encoding='utf-8') as infile:
            file_content = infile.read()
            lines.append(file_content)
    except FileNotFoundError:
        error_message = f"# --- ERROR: File not found: {full_path} ---"
        print(f"Warning: {error_message}")
        lines.append(error_message)
    except UnicodeDecodeError:
        error_message = f"# --- ERROR: Could not decode file as UTF-8: {full_path} ---"
        print(f"Warning: {error_message}")
        lines.append(error_message)
    except Exception as e:
        error_message = f"# --- ERROR: Could not read file {full_path}: {e} ---"
        print(f"Warning: {error_message}")
        lines.append(error_message)
    
    lines.append(end_marker)

# Add a separator and the post-prompt
lines.append("=" * 20 + " END CONTEXT " + "=" * 20)
lines.append(post_prompt)

# Combine all lines with actual newline characters
final_output_string = "\n".join(lines)

# Write the combined content to foo.txt
try:
    with open(output_filename, 'w', encoding='utf-8') as outfile:
        outfile.write(final_output_string)
    print(f"Successfully created '{output_filename}' with combined context.")
except Exception as e:
    print(f"Error writing to '{output_filename}': {e}")

# --- Clipboard Handling ---
print("\n--- Clipboard Instructions ---")
try:
    import pyperclip
    pyperclip.copy(final_output_string)
    print("Content successfully copied to clipboard using pyperclip.")
    print("You can now paste it.")
except ImportError:
    print("`pyperclip` library not found.")
    print("To install it: pip install pyperclip")
    print("Alternatively, use OS-specific commands below or manually copy from foo.txt.")
except Exception as e:
    print(f"An error occurred while using pyperclip: {e}")
    print("Try OS-specific commands or manually copy from foo.txt.")

# OS-specific clipboard instructions if pyperclip isn't available
if 'pyperclip' not in sys.modules:
    if sys.platform == "darwin":  # macOS
        print("\nOn macOS, you can try in your terminal:")
        print(f"  cat {output_filename} | pbcopy")
    elif sys.platform == "win32":  # Windows
        print("\nOn Windows, try in Command Prompt or PowerShell:")
        print(f"  type {output_filename} | clip")         # Command Prompt
        print(f"  Get-Content {output_filename} | Set-Clipboard")  # PowerShell
    else:  # Linux (assuming X11 with xclip or xsel)
        print("\nOn Linux, you can try in your terminal (requires xclip or xsel):")
        print(f"  cat {output_filename} | xclip -selection clipboard")
        print("  # or")
        print(f"  cat {output_filename} | xsel --clipboard --input")

print("\nScript finished.")

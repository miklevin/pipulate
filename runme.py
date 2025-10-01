# runme.py
import os
import re
from pathlib import Path

def refactor_file(file_path: Path):
    """
    Applies a series of regex substitutions to a single file.
    """
    print(f"Processing: {file_path.name}...")
    try:
        content = file_path.read_text()
        original_content = content

        # --- Define Refactoring Patterns ---
        # Each tuple is (search_pattern, replacement_pattern, description)
        patterns = [
            # Pattern 1: Update __init__ signature to accept 'db' but not store it on self.
            # This is a common pattern for most of your workflow apps.
            (
                r"(def __init__\(self, app, pipulate, pipeline, db, app_name=.*\):)",
                r"\1\n        self.pipulate = pipulate",
                "Inject pipulate instance in __init__"
            ),
            (
                r"self.db = db",
                "pip = self.pipulate",
                "Replace self.db assignment with pip alias"
            ),

            # Pattern 2: Fix the common variable unpacking pattern.
            (
                r"pip, db, steps, app_name = \(self\.pipulate, self\.db, self\.steps, self\.app_name\)",
                "pip, steps, app_name = (self.pipulate, self.steps, self.app_name)",
                "Fix main variable unpacking"
            ),
             (
                r"pip, db, steps, app_name = \(self\.pip, self\.db, self\.steps, self\.app_name\)",
                "pip, steps, app_name = (self.pip, self.steps, self.app_name)",
                "Fix alternate variable unpacking"
            ),
            
            # Pattern 3: Replace direct db.get() calls with pip.db.get()
            (
                r"pipeline_id = db\.get\('pipeline_id', 'unknown'\)",
                "pipeline_id = pip.db.get('pipeline_id', 'unknown')",
                "Replace db.get() for pipeline_id"
            ),
            
            # Pattern 4: Replace direct db['key'] access with pip.db['key']
            (
                r"db\['pipeline_id'\]",
                "pip.db['pipeline_id']",
                "Replace db['pipeline_id']"
            )
        ]

        total_replacements = 0
        for search, replace, desc in patterns:
            content, count = re.subn(search, replace, content, flags=re.MULTILINE)
            if count > 0:
                print(f"  ✅ Applied '{desc}': {count} replacement(s)")
                total_replacements += count
        
        if total_replacements == 0:
            print("  🤷 No changes made.")
        else:
            # Write back only if changes were made
            file_path.write_text(content)

    except Exception as e:
        print(f"  ❌ Error processing {file_path.name}: {e}")


def main():
    """
    Main function to find and refactor all Python files in the apps/ directory.
    """
    apps_dir = Path("./apps")
    if not apps_dir.is_dir():
        print(f"Error: 'apps' directory not found. Run this script from the project root.")
        return

    for file_path in apps_dir.glob("*.py"):
        # Skip __init__.py if it exists
        if file_path.name == "__init__.py":
            continue
        refactor_file(file_path)
    
    print("\nRefactoring complete. Please review the changes with 'git diff'.")

if __name__ == "__main__":
    main()

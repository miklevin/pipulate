#!/usr/bin/env python3
"""
Filename Reference Updater
===========================

A cleanup helper to systematically update hardwired references to old plugin 
filenames throughout the codebase after the role-based renaming.

Uses the same mapping as find_hardwired_references.py but applies the changes
in a controlled manner with backups and verification.

This script is designed to be a temporary cleanup tool that will itself
eventually be cleaned up.
"""

import os
import re
import shutil
from pathlib import Path
from collections import defaultdict
import fnmatch


# Mapping of old filename -> new filename (same as the reference finder)
FILENAME_MAPPINGS = {
    # Tutorial → 200-299 Range
    "520_widget_examples.py": "210_widget_examples.py",
    "600_roadmap.py": "220_roadmap.py",
    
    # Developer → 300-399 Range  
    "510_workflow_genesis.py": "310_workflow_genesis.py",
    "515_dev_assistant.py": "320_dev_assistant.py",
    "700_widget_shim.py": "330_widget_shim.py",
    
    # Workshop → 400-499 Range
    "530_botify_api_tutorial.py": "410_botify_api_tutorial.py",
    "535_botify_trifecta.py": "420_botify_trifecta.py",
    "540_tab_opener.py": "430_tab_opener.py",
    "550_browser_automation.py": "440_browser_automation.py",
    "560_stream_simulator.py": "450_stream_simulator.py",
    
    # Basic Form Components (500-599)
    "720_text_field.py": "510_text_field.py",
    "730_text_area.py": "520_text_area.py",
    "740_dropdown.py": "530_dropdown.py",
    "750_checkboxes.py": "540_checkboxes.py",
    "760_radios.py": "550_radios.py",
    "770_range.py": "560_range.py",
    "780_switch.py": "570_switch.py",
    "870_upload.py": "580_upload.py",
    
    # Content Display Components (600-699)
    "800_markdown.py": "610_markdown.py",
    "810_mermaid.py": "620_mermaid.py",
    "850_prism.py": "630_prism.py",
    "860_javascript.py": "640_javascript.py",
    
    # Data Visualization Components (700-799)
    "820_pandas.py": "710_pandas.py",
    "830_rich.py": "720_rich.py",
    "840_matplotlib.py": "730_matplotlib.py",
    
    # System Integration Components (800-899)
    "880_webbrowser.py": "810_webbrowser.py",
    "890_selenium.py": "820_selenium.py",
    
    # Development/Template Components (900-999)
    "710_blank_placeholder.py": "910_blank_placeholder.py",
    "715_splice_workflow.py": "920_splice_workflow.py",
}

# Also handle references without .py extension
FILENAME_MAPPINGS_NO_EXT = {
    old.replace('.py', ''): new.replace('.py', '')
    for old, new in FILENAME_MAPPINGS.items()
}

# File types to update
UPDATEABLE_EXTENSIONS = {
    '.py', '.md', '.txt', '.rst', '.yaml', '.yml', '.json', '.toml', '.cfg', '.ini',
    '.sh', '.bash', '.mdc'
}

# Directories to skip
SKIP_DIRECTORIES = {
    '__pycache__', '.git', '.pytest_cache', 'node_modules', '.venv', 'venv',
    '.mypy_cache', '.tox', 'dist', 'build', '.egg-info', '.coverage',
    'logs', 'downloads'
}

# Files to skip (don't auto-update these)
SKIP_FILES = {
    'find_hardwired_references.py',  # The analyzer script itself
    'update_filename_references.py',  # This script itself
    '.gitignore', '.gitattributes', 'LICENSE', 'CHANGELOG'
}

# Files that we should update but with extra caution
CAUTION_FILES = {
    'rename_plugins.sh',  # Old shell script - probably can be deleted
}


class ReferenceUpdater:
    """Updates hardwired references to old plugin filenames."""
    
    def __init__(self, create_backups=True):
        self.create_backups = create_backups
        self.updated_files = []
        self.skipped_files = []
        self.backup_dir = None
        self.changes_made = defaultdict(int)  # filename -> count of changes
        
        if create_backups:
            self.backup_dir = Path.cwd() / "backup_before_filename_update"
            self.backup_dir.mkdir(exist_ok=True)
        
    def should_skip_file(self, file_path):
        """Check if a file should be skipped during updating."""
        path = Path(file_path)
        
        # Skip if in excluded directories
        for part in path.parts:
            if part in SKIP_DIRECTORIES:
                return True
                
        # Skip if excluded filename
        if path.name in SKIP_FILES:
            return True
            
        # Skip if not an updateable extension
        if path.suffix not in UPDATEABLE_EXTENSIONS:
            return True
            
        return False
    
    def create_backup(self, file_path):
        """Create a backup of the file before modifying."""
        if not self.create_backups:
            return
            
        src_path = Path(file_path)
        backup_path = self.backup_dir / src_path.name
        
        # Handle duplicate names by adding numbers
        counter = 1
        while backup_path.exists():
            stem = src_path.stem
            suffix = src_path.suffix
            backup_path = self.backup_dir / f"{stem}_{counter}{suffix}"
            counter += 1
            
        shutil.copy2(src_path, backup_path)
        print(f"  💾 Backup created: {backup_path.name}")
    
    def update_file_references(self, file_path):
        """Update hardwired references in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                original_content = content
                
            changes_in_file = 0
            
            # Update references to filenames with .py extension
            for old_filename, new_filename in FILENAME_MAPPINGS.items():
                old_count = content.count(old_filename)
                if old_count > 0:
                    content = content.replace(old_filename, new_filename)
                    changes_in_file += old_count
                    self.changes_made[old_filename] += old_count
                    
            # Update references without .py extension (using word boundaries)
            for old_name, new_name in FILENAME_MAPPINGS_NO_EXT.items():
                pattern = r'\b' + re.escape(old_name) + r'\b'
                matches = re.findall(pattern, content)
                if matches:
                    content = re.sub(pattern, new_name, content)
                    changes_in_file += len(matches)
                    self.changes_made[f"{old_name} (no .py)"] += len(matches)
            
            # Only write if changes were made
            if content != original_content:
                self.create_backup(file_path)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                self.updated_files.append(file_path)
                print(f"  ✅ Updated: {Path(file_path).name} ({changes_in_file} changes)")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"  ❌ Error updating {file_path}: {e}")
            return False
    
    def update_directory(self, root_dir):
        """Recursively update references in a directory."""
        root_path = Path(root_dir)
        files_processed = 0
        
        for file_path in root_path.rglob('*'):
            if file_path.is_file() and not self.should_skip_file(file_path):
                files_processed += 1
                
                # Special handling for caution files
                if file_path.name in CAUTION_FILES:
                    print(f"  ⚠️  CAUTION FILE: {file_path.name} - review manually")
                    self.skipped_files.append(str(file_path))
                    continue
                
                print(f"\n📄 Processing: {file_path.name}")
                success = self.update_file_references(file_path)
                
                if not success and file_path.name not in CAUTION_FILES:
                    print(f"  ➡️  No changes needed")
                    
        return files_processed


def update_hardwired_references(project_root, create_backups=True):
    """Update all hardwired references throughout the codebase."""
    project_path = Path(project_root)
    
    if not project_path.exists() or not project_path.is_dir():
        print(f"Error: {project_root} does not exist or is not a directory")
        return
        
    print(f"🔄 Starting systematic filename reference updates...")
    print(f"Project root: {project_root}")
    print(f"Updating references for {len(FILENAME_MAPPINGS)} renamed files")
    
    if create_backups:
        print(f"📦 Creating backups in: backup_before_filename_update/")
    
    print(f"\n{'='*80}")
    
    updater = ReferenceUpdater(create_backups=create_backups)
    files_processed = updater.update_directory(project_path)
    
    # Summary report
    print(f"\n{'='*80}")
    print("UPDATE SUMMARY")
    print(f"{'='*80}")
    
    print(f"\n📊 STATISTICS:")
    print(f"Files processed:     {files_processed}")
    print(f"Files updated:       {len(updater.updated_files)}")
    print(f"Files skipped:       {len(updater.skipped_files)}")
    
    if updater.changes_made:
        print(f"\n🔄 CHANGES BY FILENAME:")
        print(f"{'='*50}")
        for filename, count in sorted(updater.changes_made.items()):
            print(f"  {filename:<35} → {count:>3} changes")
    
    if updater.updated_files:
        print(f"\n✅ FILES UPDATED ({len(updater.updated_files)}):")
        print(f"{'='*50}")
        for file_path in sorted(updater.updated_files):
            rel_path = Path(file_path).relative_to(project_path)
            print(f"  • {rel_path}")
    
    if updater.skipped_files:
        print(f"\n⚠️  CAUTION FILES SKIPPED ({len(updater.skipped_files)}):")
        print(f"{'='*50}")
        for file_path in sorted(updater.skipped_files):
            rel_path = Path(file_path).relative_to(project_path)
            print(f"  • {rel_path} - requires manual review")
    
    if create_backups and updater.backup_dir.exists():
        backup_files = list(updater.backup_dir.glob('*'))
        if backup_files:
            print(f"\n💾 BACKUPS CREATED ({len(backup_files)}):")
            print(f"{'='*50}")
            print(f"  Location: {updater.backup_dir}")
            for backup_file in sorted(backup_files):
                print(f"  • {backup_file.name}")
    
    print(f"\n🎯 NEXT STEPS:")
    print(f"{'='*50}")
    print("1. Review the changes made to ensure they're correct")
    print("2. Run the reference finder again to verify all updates")
    print("3. Test the application to ensure everything still works")
    if updater.skipped_files:
        print("4. Manually review and update the caution files listed above")
    if create_backups:
        print("5. Delete the backup directory once you're satisfied")
    
    print(f"\n{'='*80}")
    print("Reference update complete! 🎉")
    print("This helper script can be safely deleted once you're done.")
    print(f"{'='*80}")


def main():
    """Main function to run the reference updates."""
    # Determine project root (this script is in helpers/cleanup/)
    current_script_path = Path(__file__).resolve()
    
    # Navigate up to project root
    project_root = current_script_path.parent.parent.parent
    if project_root.name != "pipulate":
        print(f"Warning: Expected to be in pipulate project, but found: {project_root.name}")
        print(f"Script path: {current_script_path}")
        print("Continuing anyway...")
    
    print("🔄 Filename Reference Updater")
    print("=" * 80)
    print("This script will systematically update all hardwired references")
    print("to old plugin filenames throughout the codebase.")
    print()
    
    # Confirm before proceeding
    response = input("Continue with updates? [y/N]: ").strip().lower()
    if response not in ('y', 'yes'):
        print("Update cancelled.")
        return
    
    update_hardwired_references(project_root, create_backups=True)


if __name__ == "__main__":
    main() 
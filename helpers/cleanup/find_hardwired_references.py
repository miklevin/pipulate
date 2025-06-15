#!/usr/bin/env python3
"""
Hardwired Reference Finder
===========================

A one-off cleanup helper to find hardwired references to old plugin filenames
throughout the codebase after the role-based renaming.

Scans all files for references to the old plugin filenames and reports where
updates are needed.

This script is designed to be a temporary analysis tool that will itself
eventually be cleaned up.
"""

import os
import re
from pathlib import Path
from collections import defaultdict, Counter
import fnmatch


# Mapping of old filename -> new filename based on the renaming that was done
FILENAME_MAPPINGS = {
    # Tutorial → 200-299 Range
    "520_widget_examples.py": "210_widget_examples.py",
    "600_roadmap.py": "220_roadmap.py",
    
    # Developer → 300-399 Range  
    "510_workflow_genesis.py": "200_workflow_genesis.py",
    "515_dev_assistant.py": "320_dev_assistant.py",
    "700_widget_shim.py": "330_widget_shim.py",
    
    # Workshop → 400-499 Range
    "530_botify_api_tutorial.py": "410_botify_api_tutorial.py",
    "535_botify_quadfecta.py": "400_botify_quadfecta.py",
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
    "300_blank_placeholder.py": "300_blank_placeholder.py",
    "715_splice_workflow.py": "920_splice_workflow.py",
}

# Also check for references without .py extension
FILENAME_MAPPINGS_NO_EXT = {
    old.replace('.py', ''): new.replace('.py', '')
    for old, new in FILENAME_MAPPINGS.items()
}

# File types to scan
SCANNABLE_EXTENSIONS = {
    '.py', '.md', '.txt', '.rst', '.yaml', '.yml', '.json', '.toml', '.cfg', '.ini',
    '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd', '.html', '.css', '.js',
    '.tsx', '.jsx', '.ts', '.vue', '.svelte', '.mdc'
}

# Directories to skip
SKIP_DIRECTORIES = {
    '__pycache__', '.git', '.pytest_cache', 'node_modules', '.venv', 'venv',
    '.mypy_cache', '.tox', 'dist', 'build', '.egg-info', '.coverage',
    'logs', 'downloads'
}

# Files to skip
SKIP_FILES = {
    'find_hardwired_references.py',  # This script itself
    '.gitignore', '.gitattributes', 'LICENSE', 'CHANGELOG', 'requirements.txt'
}


class ReferenceScanner:
    """Scanner to find hardwired references to old plugin filenames."""
    
    def __init__(self):
        self.references = defaultdict(list)  # old_filename -> [(file_path, line_num, line_content, suggested_fix)]
        self.scanned_files = 0
        self.total_references = 0
        
    def should_skip_file(self, file_path):
        """Check if a file should be skipped during scanning."""
        path = Path(file_path)
        
        # Skip if in excluded directories
        for part in path.parts:
            if part in SKIP_DIRECTORIES:
                return True
                
        # Skip if excluded filename
        if path.name in SKIP_FILES:
            return True
            
        # Skip if not a scannable extension
        if path.suffix not in SCANNABLE_EXTENSIONS:
            return True
            
        return False
        
    def scan_file_for_references(self, file_path):
        """Scan a single file for hardwired references to old plugin filenames."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                # Check for references to old filenames (with .py)
                for old_filename, new_filename in FILENAME_MAPPINGS.items():
                    if old_filename in line:
                        suggested_fix = line.replace(old_filename, new_filename)
                        self.references[old_filename].append((
                            file_path, line_num, line.strip(), suggested_fix.strip()
                        ))
                        self.total_references += 1
                        
                # Check for references without .py extension
                for old_name, new_name in FILENAME_MAPPINGS_NO_EXT.items():
                    # Use word boundaries to avoid false positives
                    pattern = r'\b' + re.escape(old_name) + r'\b'
                    if re.search(pattern, line):
                        suggested_fix = re.sub(pattern, new_name, line)
                        display_old = f"{old_name} (no .py)"
                        self.references[display_old].append((
                            file_path, line_num, line.strip(), suggested_fix.strip()
                        ))
                        self.total_references += 1
                        
        except Exception as e:
            print(f"Warning: Could not scan {file_path}: {e}")
            
    def scan_directory(self, root_dir):
        """Recursively scan a directory for hardwired references."""
        root_path = Path(root_dir)
        
        for file_path in root_path.rglob('*'):
            if file_path.is_file() and not self.should_skip_file(file_path):
                self.scan_file_for_references(file_path)
                self.scanned_files += 1
                
                # Progress indicator for large codebases
                if self.scanned_files % 100 == 0:
                    print(f"  Scanned {self.scanned_files} files...")


def analyze_hardwired_references(project_root):
    """Analyze hardwired references throughout the codebase."""
    project_path = Path(project_root)
    
    if not project_path.exists() or not project_path.is_dir():
        print(f"Error: {project_root} does not exist or is not a directory")
        return
        
    print(f"Scanning {project_root} for hardwired plugin filename references...\n")
    
    scanner = ReferenceScanner()
    scanner.scan_directory(project_path)
    
    print(f"Scanned {scanner.scanned_files} files for hardwired references.\n")
    
    if not scanner.references:
        print("🎉 No hardwired references found! All references appear to be up to date.")
        return
        
    # Summary section
    print(f"{'='*80}")
    print("HARDWIRED REFERENCES FOUND")
    print(f"{'='*80}")
    
    # Statistics
    unique_old_files = len(scanner.references)
    total_refs = scanner.total_references
    
    print(f"\n📊 REFERENCE SUMMARY:")
    print(f"{'='*50}")
    print(f"Old filenames referenced: {unique_old_files}")
    print(f"Total references found:   {total_refs}")
    print(f"Files scanned:            {scanner.scanned_files}")
    
    # Detailed breakdown
    print(f"\n🔍 DETAILED BREAKDOWN:")
    print(f"{'='*50}")
    
    for old_filename in sorted(scanner.references.keys()):
        references = scanner.references[old_filename]
        new_filename = FILENAME_MAPPINGS.get(old_filename, "UNKNOWN")
        if "(no .py)" in old_filename:
            clean_old = old_filename.replace(" (no .py)", "")
            new_filename = FILENAME_MAPPINGS_NO_EXT.get(clean_old, "UNKNOWN")
            
        print(f"\n📄 {old_filename}")
        print(f"   → Should be: {new_filename}")
        print(f"   → Found in {len(references)} location(s):")
        
        for file_path, line_num, line_content, suggested_fix in references:
            rel_path = Path(file_path).relative_to(project_path)
            print(f"      📍 {rel_path}:{line_num}")
            print(f"         Current: {line_content}")
            if line_content != suggested_fix:
                print(f"         Suggest: {suggested_fix}")
            print()
    
    # Files requiring updates
    affected_files = set()
    for refs in scanner.references.values():
        for file_path, _, _, _ in refs:
            affected_files.add(file_path)
            
    print(f"\n📝 FILES REQUIRING UPDATES ({len(affected_files)}):")
    print(f"{'='*50}")
    
    for file_path in sorted(affected_files):
        rel_path = Path(file_path).relative_to(project_path)
        file_refs = sum(1 for refs in scanner.references.values() 
                       for ref_file, _, _, _ in refs if ref_file == file_path)
        print(f"   • {rel_path} ({file_refs} reference(s))")
    
    # Quick fix suggestions
    print(f"\n🛠️  QUICK FIX SUGGESTIONS:")
    print(f"{'='*50}")
    print("For bulk replacement, consider using:")
    print()
    
    for old_filename, new_filename in sorted(FILENAME_MAPPINGS.items()):
        print(f"  # Replace {old_filename} → {new_filename}")
        print(f"  find . -type f -name '*.py' -exec sed -i 's/{old_filename}/{new_filename}/g' {{}} +")
        print(f"  find . -type f -name '*.md' -exec sed -i 's/{old_filename}/{new_filename}/g' {{}} +")
        print()
    
    print("⚠️  WARNING: Review each change carefully before applying bulk replacements!")
    print("    Some references might be intentional (e.g., in documentation or comments).")


def main():
    """Main function to run the reference analysis."""
    # Determine project root (this script is in helpers/cleanup/)
    current_script_path = Path(__file__).resolve()
    
    # Navigate up to project root
    project_root = current_script_path.parent.parent.parent
    if project_root.name != "pipulate":
        print(f"Warning: Expected to be in pipulate project, but found: {project_root.name}")
        print(f"Script path: {current_script_path}")
        print("Continuing anyway...")
    
    print("🔍 Hardwired Reference Finder")
    print("=" * 80)
    print(f"Project root: {project_root}")
    print(f"Checking for references to {len(FILENAME_MAPPINGS)} renamed plugin files")
    print()
    
    analyze_hardwired_references(project_root)
    
    print(f"\n{'='*80}")
    print("Analysis complete! 🎯")
    print("This helper script can be safely deleted once you're done with the analysis.")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
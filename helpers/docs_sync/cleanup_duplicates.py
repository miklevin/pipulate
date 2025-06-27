#!/usr/bin/env python3
"""
ASCII Art Duplicate Cleanup Script

This script removes duplicate ASCII art blocks that have been created by 
previous sync bugs, keeping only the first occurrence of each block.
"""

import os
import re
from pathlib import Path

def cleanup_duplicates_in_file(file_path):
    """Clean up duplicate ASCII art blocks in a single file"""
    print(f"🔍 Checking: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes_made = False
    
    # Find all ASCII art markers
    marker_pattern = r'<!-- START_ASCII_ART: ([^>]+) -->'
    markers = set(re.findall(marker_pattern, content))
    
    for marker in markers:
        # Find all instances of this specific block
        block_pattern = rf'<!-- START_ASCII_ART: {re.escape(marker)} -->.*?<!-- END_ASCII_ART: {re.escape(marker)} -->'
        all_matches = list(re.finditer(block_pattern, content, re.DOTALL))
        
        if len(all_matches) > 1:
            print(f"  🧹 Deduplicating: {marker} (found {len(all_matches)} instances)")
            
            # Sort matches by position (reverse order to avoid position shifts during removal)
            sorted_matches = sorted(all_matches, key=lambda m: m.start(), reverse=True)
            
            # Remove all instances except the first (last in reverse-sorted list)
            for match_to_remove in sorted_matches[:-1]:
                content = content[:match_to_remove.start()] + content[match_to_remove.end():]
                changes_made = True
    
    if changes_made:
        # Write the cleaned content back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ Cleaned up duplicates in {file_path}")
        return True
    else:
        print(f"  ⚪ No duplicates found in {file_path}")
        return False

def main():
    """Main cleanup function"""
    print("🧹 ASCII Art Duplicate Cleanup Script")
    print("="*50)
    
    # Find Pipulate.com path
    pipulate_com_path = Path(__file__).parent.parent.parent / ".." / "Pipulate.com"
    
    if not pipulate_com_path.exists():
        print("❌ Pipulate.com directory not found!")
        return
    
    # Find all markdown files
    markdown_files = []
    skip_dirs = {'.git', '_site', '.bundle', 'node_modules', '.gem', '.jekyll-cache'}
    
    for root, dirs, files in os.walk(pipulate_com_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for file in files:
            if file.endswith('.md'):
                markdown_files.append(Path(root) / file)
    
    print(f"📁 Found {len(markdown_files)} markdown files to check")
    
    files_cleaned = 0
    for md_file in sorted(markdown_files):
        if cleanup_duplicates_in_file(md_file):
            files_cleaned += 1
    
    print(f"\n🎉 Cleanup complete!")
    print(f"   📊 Files cleaned: {files_cleaned}")
    print(f"   📁 Total files checked: {len(markdown_files)}")
    
    if files_cleaned > 0:
        print(f"\n💡 Next steps:")
        print(f"   1. Review the changes with 'git diff'")
        print(f"   2. Run 'python sync_ascii_art.py' to populate clean blocks")
        print(f"   3. Commit the cleaned files")

if __name__ == "__main__":
    main() 
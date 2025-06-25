#!/usr/bin/env python3
"""
Sync ASCII Art - One Command to Rule Them All

Updates all ASCII art blocks from pipulate/README.md to Pipulate.com
Walks through all markdown files and updates any markers it finds.

Usage: python helpers/sync_ascii_art.py
"""

import os
import re
from pathlib import Path
from ascii_art_parser import extract_ascii_art_blocks

def find_markdown_files(base_path):
    """Find all markdown files in Pipulate.com, avoiding cache directories"""
    base_path = Path(base_path)
    markdown_files = []
    
    # Skip these directories
    skip_dirs = {'.git', '_site', '.bundle', 'node_modules', '.gem', '.jekyll-cache'}
    
    for root, dirs, files in os.walk(base_path):
        # Remove skip directories from dirs list to avoid walking them
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.md'):
                markdown_files.append(Path(root) / file)
    
    return sorted(markdown_files)

def find_ascii_markers_in_file(file_path):
    """Find all ASCII art markers in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return []
    
    # Find all START_ASCII_ART markers
    pattern = r'<!-- START_ASCII_ART: ([^-]+) -->'
    matches = re.findall(pattern, content)
    return matches

def update_ascii_in_file(file_path, block_key, new_content):
    """Update a specific ASCII block in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return False
    
    # Pattern to match the entire ASCII block
    pattern = rf'<!-- START_ASCII_ART: {re.escape(block_key)} -->.*?<!-- END_ASCII_ART: {re.escape(block_key)} -->'
    
    # Replacement content
    replacement = f'<!-- START_ASCII_ART: {block_key} -->\n```\n{new_content}\n```\n<!-- END_ASCII_ART: {block_key} -->'
    
    # Check if pattern exists
    if not re.search(pattern, content, re.DOTALL):
        return False
    
    # Perform replacement
    new_file_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Only write if content actually changed
    if new_file_content != content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_file_content)
            return True
        except Exception as e:
            print(f"❌ Error writing {file_path}: {e}")
            return False
    
    return False  # No change needed

def main():
    """Main synchronization function"""
    print("🚀 Syncing ASCII art from pipulate/README.md to Pipulate.com...")
    
    # Get ASCII blocks from README.md
    readme_path = Path(__file__).parent.parent / "README.md"
    if not readme_path.exists():
        print(f"❌ README.md not found at {readme_path}")
        return
    
    print(f"📖 Reading ASCII blocks from {readme_path}")
    with open(readme_path, 'r', encoding='utf-8') as f:
        readme_content = f.read()
    
    ascii_block_data = extract_ascii_art_blocks(readme_content)
    
    if not ascii_block_data:
        print("❌ No ASCII blocks found in README.md")
        return
    
    # Convert to simple key -> art content mapping
    ascii_blocks = {key: data['art'] for key, data in ascii_block_data.items()}
    
    print(f"✅ Found {len(ascii_blocks)} ASCII blocks in README.md")
    for key in ascii_blocks.keys():
        print(f"   📦 {key}")
    
    # Find Pipulate.com path
    pipulate_com_path = Path(__file__).parent.parent.parent / "Pipulate.com"
    if not pipulate_com_path.exists():
        print(f"❌ Pipulate.com not found at {pipulate_com_path}")
        return
    
    print(f"\n🔍 Scanning markdown files in {pipulate_com_path}")
    markdown_files = find_markdown_files(pipulate_com_path)
    print(f"✅ Found {len(markdown_files)} markdown files")
    
    # Track updates
    total_updates = 0
    files_updated = 0
    
    # Process each markdown file
    for md_file in markdown_files:
        relative_path = md_file.relative_to(pipulate_com_path)
        ascii_markers = find_ascii_markers_in_file(md_file)
        
        if not ascii_markers:
            continue
        
        print(f"\n📄 {relative_path}")
        file_had_updates = False
        
        for marker in ascii_markers:
            if marker in ascii_blocks:
                # Update this block
                if update_ascii_in_file(md_file, marker, ascii_blocks[marker]):
                    print(f"   ✅ Updated: {marker}")
                    total_updates += 1
                    file_had_updates = True
                else:
                    print(f"   ⚪ No change: {marker}")
            else:
                print(f"   ❌ Block not found in README.md: {marker}")
        
        if file_had_updates:
            files_updated += 1
    
    print(f"\n🎉 Sync complete!")
    print(f"   📊 Files updated: {files_updated}")
    print(f"   🔄 Total blocks updated: {total_updates}")
    
    if total_updates == 0:
        print("   ✨ All ASCII art was already up to date!")

if __name__ == "__main__":
    main()

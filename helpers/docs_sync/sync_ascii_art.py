#!/usr/bin/env python3
"""
Sync ASCII Art - One Command to Rule Them All

Updates all ASCII art blocks from pipulate/README.md to Pipulate.com
Walks through all markdown files and updates any markers it finds.

Usage: python helpers/docs_sync/sync_ascii_art.py
"""

import os
import re
from pathlib import Path
from ascii_art_parser import extract_ascii_art_blocks

def main():
    """Main synchronization function"""
    print("🚀 Syncing ASCII art from pipulate/README.md to Pipulate.com...")
    
    # Get ASCII blocks from README.md (adjusted for docs_sync subfolder)
    readme_path = Path(__file__).parent.parent.parent / "README.md"
    with open(readme_path, 'r', encoding='utf-8') as f:
        readme_content = f.read()
    
    ascii_block_data = extract_ascii_art_blocks(readme_content)
    ascii_blocks = {key: data['art'] for key, data in ascii_block_data.items()}
    
    print(f"✅ Found {len(ascii_blocks)} ASCII blocks in README.md")
    
    # Find Pipulate.com path (adjusted for docs_sync subfolder)
    pipulate_com_path = Path(__file__).parent.parent.parent / ".." / "Pipulate.com"
    
    # Find all markdown files
    markdown_files = []
    skip_dirs = {'.git', '_site', '.bundle', 'node_modules', '.gem', '.jekyll-cache'}
    
    for root, dirs, files in os.walk(pipulate_com_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for file in files:
            if file.endswith('.md'):
                markdown_files.append(Path(root) / file)
    
    print(f"🔍 Found {len(markdown_files)} markdown files")
    
    total_updates = 0
    files_updated = 0
    
    # Process each file
    for md_file in sorted(markdown_files):
        # Find ASCII markers in the file
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all markers (corrected regex)
        marker_pattern = r'<!-- START_ASCII_ART: ([^>]+) -->'
        markers = re.findall(marker_pattern, content)
        
        if not markers:
            continue
            
        relative_path = md_file.relative_to(pipulate_com_path)
        print(f"\n�� {relative_path}")
        file_had_updates = False
        
        for marker in markers:
            if marker in ascii_blocks:
                # Check if update is needed
                block_pattern = rf'<!-- START_ASCII_ART: {re.escape(marker)} -->.*?<!-- END_ASCII_ART: {re.escape(marker)} -->'
                block_match = re.search(block_pattern, content, re.DOTALL)
                
                if block_match:
                    current_block = block_match.group(0)
                    art_pattern = r'```\n(.*?)\n```'
                    art_match = re.search(art_pattern, current_block, re.DOTALL)
                    
                    if art_match:
                        current_art = art_match.group(1)
                        new_art = ascii_blocks[marker]
                        
                        if current_art != new_art:
                            # Update needed!
                            replacement = f'<!-- START_ASCII_ART: {marker} -->\n```\n{new_art}\n```\n<!-- END_ASCII_ART: {marker} -->'
                            new_content = re.sub(block_pattern, replacement, content, flags=re.DOTALL)
                            
                            # Write the updated file
                            with open(md_file, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            
                            print(f"   ✅ Updated: {marker}")
                            total_updates += 1
                            file_had_updates = True
                            content = new_content  # Update content for next marker in same file
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

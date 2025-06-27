#!/usr/bin/env python3
"""
Bulletproof Idempotent ASCII Art Sync System

This guarantees true idempotence by using a clean, simple algorithm.
"""

import re
import pathlib
import argparse

def extract_ascii_blocks(readme_path):
    """Extract all ASCII art blocks from README.md"""
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pattern = r'<!-- START_ASCII_ART: ([^>]+) -->(.*?)<!-- END_ASCII_ART: \1 -->'
    matches = re.findall(pattern, content, re.DOTALL)
    
    ascii_blocks = {}
    for marker, block_content in matches:
        ascii_blocks[marker] = block_content.strip()
        
    print(f"✅ Extracted {len(ascii_blocks)} ASCII blocks from README.md")
    return ascii_blocks

def process_file_idempotent(file_path, ascii_blocks, dry_run=False):
    """Process a single file with guaranteed idempotent behavior"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # Find all START markers
    start_pattern = r'<!-- START_ASCII_ART: ([^>]+) -->'
    markers = list(set(re.findall(start_pattern, original_content)))
    
    if not markers:
        return {'updates': 0, 'markers': []}
    
    new_content = original_content
    updates_made = 0
    processed_markers = []
    
    for marker in markers:
        if marker not in ascii_blocks:
            continue
            
        # Create the replacement block
        replacement_block = f'<!-- START_ASCII_ART: {marker} -->\n{ascii_blocks[marker]}\n<!-- END_ASCII_ART: {marker} -->'
        
        # Pattern to match ALL instances of this marker block
        pattern = rf'<!-- START_ASCII_ART: {re.escape(marker)} -->.*?<!-- END_ASCII_ART: {re.escape(marker)} -->'
        
        # Find all matches
        matches = list(re.finditer(pattern, new_content, re.DOTALL))
        
        if matches:
            # Replace ALL instances with a single instance
            # Remove all matches first
            sorted_matches = sorted(matches, key=lambda m: m.start(), reverse=True)
            
            for match in sorted_matches:
                new_content = new_content[:match.start()] + new_content[match.end():]
            
            # Insert the clean block at the first position
            first_match_pos = sorted_matches[-1].start()
            new_content = new_content[:first_match_pos] + replacement_block + new_content[first_match_pos:]
            
            updates_made += 1
            processed_markers.append(marker)
    
    # Write file if changed
    if new_content != original_content and not dry_run:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
    
    return {
        'updates': updates_made if new_content != original_content else 0,
        'markers': processed_markers
    }

def main():
    parser = argparse.ArgumentParser(description='Bulletproof Idempotent ASCII Art Sync')
    parser.add_argument('target_dir', help='Target directory to sync')
    parser.add_argument('--readme', default='pipulate/README.md', help='Path to README.md')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    
    args = parser.parse_args()
    
    print("🛡️  BULLETPROOF IDEMPOTENT ASCII ART SYNC")
    print("=" * 50)
    
    # Extract ASCII blocks
    ascii_blocks = extract_ascii_blocks(pathlib.Path(args.readme))
    
    # Find markdown files
    target_path = pathlib.Path(args.target_dir)
    markdown_files = list(target_path.rglob('*.md'))
    print(f"🔍 Found {len(markdown_files)} markdown files")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE: No changes will be made")
    
    # Process each file
    total_updates = 0
    files_updated = 0
    
    for md_file in markdown_files:
        relative_path = md_file.relative_to(target_path)
        result = process_file_idempotent(md_file, ascii_blocks, args.dry_run)
        
        if result['updates'] > 0:
            files_updated += 1
            total_updates += result['updates']
            
            if args.dry_run:
                print(f"📄 {relative_path}: Would update {result['updates']} blocks")
            else:
                print(f"✅ {relative_path}: Updated {result['updates']} blocks")
    
    print(f"\n📊 SYNC SUMMARY:")
    print(f"   📄 Files processed: {len(markdown_files)}")
    print(f"   ✅ Files updated: {files_updated}")
    print(f"   🔄 Total blocks updated: {total_updates}")
    
    if total_updates == 0:
        print(f"\n✨ All ASCII art was already up to date! (System is idempotent)")
    
    return 0

if __name__ == '__main__':
    exit(main()) 
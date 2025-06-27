#!/usr/bin/env python3
"""
Manual cleanup script for the corrupted ASCII art file
"""

import re
from pathlib import Path

def clean_corrupted_file(file_path):
    """Clean a corrupted file by removing duplicate ASCII art content"""
    print(f"🔧 Manually cleaning: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_length = len(content)
    
    # Find all ASCII art markers in the file
    marker_pattern = r'<!-- START_ASCII_ART: ([^>]+) -->'
    markers = set(re.findall(marker_pattern, content))
    
    if not markers:
        print("❌ No ASCII art markers found!")
        return False
    
    print(f"📊 Original file: {original_length} characters")
    print(f"🎯 Found {len(markers)} unique ASCII art markers")
    
    # For each marker, keep only the first complete block
    for marker in markers:
        block_pattern = rf'<!-- START_ASCII_ART: {re.escape(marker)} -->.*?<!-- END_ASCII_ART: {re.escape(marker)} -->'
        all_matches = list(re.finditer(block_pattern, content, re.DOTALL))
        
        if len(all_matches) > 1:
            print(f"  🧹 Deduplicating marker '{marker}': found {len(all_matches)} complete blocks")
            
            # Sort matches by position (reverse order to avoid position shifts during removal)
            sorted_matches = sorted(all_matches, key=lambda m: m.start(), reverse=True)
            
            # Remove all instances except the first (last in reverse-sorted list)
            for match_to_remove in sorted_matches[:-1]:
                content = content[:match_to_remove.start()] + content[match_to_remove.end():]
    
    # Now remove any orphaned END markers (END markers without corresponding START markers)
    all_end_markers = re.findall(r'<!-- END_ASCII_ART: ([^>]+) -->', content)
    for marker in set(all_end_markers):
        # Count START and END markers for this specific marker
        start_count = len(re.findall(rf'<!-- START_ASCII_ART: {re.escape(marker)} -->', content))
        end_count = len(re.findall(rf'<!-- END_ASCII_ART: {re.escape(marker)} -->', content))
        
        if end_count > start_count:
            print(f"  🧹 Removing {end_count - start_count} orphaned END markers for '{marker}'")
            
            # Remove excess END markers
            end_pattern = rf'<!-- END_ASCII_ART: {re.escape(marker)} -->'
            end_matches = list(re.finditer(end_pattern, content))
            
            # Remove from the end, keeping only as many as we have START markers
            for i in range(len(end_matches) - start_count):
                match_to_remove = end_matches[-(i+1)]
                content = content[:match_to_remove.start()] + content[match_to_remove.end():]
    
    final_length = len(content)
    removed_chars = original_length - final_length
    
    if removed_chars > 0:
        print(f"🧹 Cleaned file: {final_length} characters (removed {removed_chars} characters)")
        
        # Write the cleaned file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ File cleaned successfully!")
        return True
    else:
        print("⚪ No duplicates found - file was already clean")
        return False

def clean_all_corrupted_files():
    """Clean all corrupted files in the Pipulate.com directory"""
    print("🧹 ASCII Art Corruption Cleanup Script")
    print("="*50)
    
    pipulate_com_path = Path(__file__).parent.parent.parent / ".." / "Pipulate.com"
    
    if not pipulate_com_path.exists():
        print("❌ Pipulate.com directory not found!")
        return
    
    # Find all markdown files and check for corruption
    corrupted_files = []
    for md_file in pipulate_com_path.rglob('*.md'):
        try:
            with open(md_file, 'r') as f:
                content = f.read()
            end_count = content.count('<!-- END_ASCII_ART:')
            if end_count > 5:  # Threshold for corruption
                corrupted_files.append((md_file, end_count))
        except:
            pass
    
    if not corrupted_files:
        print("✅ No corrupted files found!")
        return
    
    print(f"🚨 Found {len(corrupted_files)} corrupted files:")
    for file_path, end_count in corrupted_files:
        print(f"  📄 {file_path.relative_to(pipulate_com_path)}: {end_count} END markers")
    
    print("\n🔧 Cleaning corrupted files...")
    
    cleaned_count = 0
    for file_path, _ in corrupted_files:
        if clean_corrupted_file(file_path):
            cleaned_count += 1
        print()  # Empty line between files
    
    print(f"🎉 Cleanup complete!")
    print(f"   📊 Files cleaned: {cleaned_count}")
    print(f"   📁 Total files checked: {len(corrupted_files)}")

if __name__ == "__main__":
    clean_all_corrupted_files() 
#!/usr/bin/env python3
"""
ASCII Art Distribution System

Reads ASCII art blocks from README.md and distributes them to destination files
that contain START_ASCII_ART/END_ASCII_ART markers.
"""

import re
from pathlib import Path
from ascii_art_parser import extract_ascii_art_blocks

def distribute_ascii_art(source_file: str, destination_file: str, dry_run: bool = True):
    """
    Distribute ASCII art from source to destination file markers.
    
    Args:
        source_file: Path to source file (e.g., README.md)
        destination_file: Path to destination file with markers
        dry_run: If True, only show what would be changed
    """
    # Parse ASCII art from source
    print(f"📖 Parsing ASCII art from: {source_file}")
    
    # Read the source file content
    source_path = Path(source_file)
    if not source_path.exists():
        print(f"❌ Source file not found: {source_file}")
        return
    
    source_content = source_path.read_text()
    ascii_blocks = extract_ascii_art_blocks(source_content)
    print(f"✅ Found {len(ascii_blocks)} ASCII art blocks")
    
    # Debug: show what blocks we found
    if ascii_blocks:
        print("🔍 Available blocks:")
        for key in ascii_blocks.keys():
            print(f"   - {key}")
    else:
        print("⚠️  No blocks found - check parser logic")
    
    # Read destination file
    dest_path = Path(destination_file)
    if not dest_path.exists():
        print(f"❌ Destination file not found: {destination_file}")
        return
    
    content = dest_path.read_text()
    
    # Find all markers in destination file (HTML comments for Jekyll compatibility)
    marker_pattern = r'<!-- START_ASCII_ART: ([^\s]+) -->\n(.*?)\n<!-- END_ASCII_ART: \1 -->'
    markers = re.findall(marker_pattern, content, re.DOTALL)
    
    print(f"🎯 Found {len(markers)} ASCII art markers in destination")
    
    # Debug marker detection
    if not markers:
        print("🔍 Debugging marker detection...")
        # Look for START markers
        start_markers = re.findall(r'<!-- START_ASCII_ART: ([^-]+) -->', content)
        print(f"   Found {len(start_markers)} START markers: {start_markers}")
        
        # Look for END markers  
        end_markers = re.findall(r'<!-- END_ASCII_ART: ([^-]+) -->', content)
        print(f"   Found {len(end_markers)} END markers: {end_markers}")
        
        # Try a simpler pattern
        simple_pattern = r'<!-- START_ASCII_ART: ([^-]+) -->\n(.*?)\n<!-- END_ASCII_ART: [^-]+ -->'
        simple_markers = re.findall(simple_pattern, content, re.DOTALL)
        print(f"   Simple pattern found {len(simple_markers)} markers")
    
    changes_made = False
    new_content = content
    
    for marker_key, current_content in markers:
        # Find matching ASCII block
        if marker_key in ascii_blocks:
            block = ascii_blocks[marker_key]
            
            # Reconstruct the full ASCII art section
            new_ascii_section = f"""```
{block['art']}
```"""
            
            # Replace the marker section
            old_marker_section = f"<!-- START_ASCII_ART: {marker_key} -->\n{current_content}\n<!-- END_ASCII_ART: {marker_key} -->"
            new_marker_section = f"<!-- START_ASCII_ART: {marker_key} -->\n{new_ascii_section}\n<!-- END_ASCII_ART: {marker_key} -->"
            
            if current_content.strip() != new_ascii_section.strip():
                print(f"🔄 Updating marker: {marker_key}")
                new_content = new_content.replace(old_marker_section, new_marker_section)
                changes_made = True
            else:
                print(f"✅ Already up to date: {marker_key}")
        else:
            print(f"⚠️  No matching ASCII block found for marker: {marker_key}")
    
    if changes_made:
        if dry_run:
            print(f"\n🔍 DRY RUN - Would update: {destination_file}")
            print("Use --apply to make actual changes")
        else:
            dest_path.write_text(new_content)
            print(f"✅ Updated: {destination_file}")
    else:
        print("✅ No changes needed")

def main():
    """Test the distribution system"""
    import sys
    
    # Default paths
    source = "../README.md"
    destination = "../../Pipulate.com/about.md"
    
    # Check for --apply flag
    apply_changes = "--apply" in sys.argv
    
    print("🚀 ASCII Art Distribution System")
    print("=" * 50)
    
    distribute_ascii_art(source, destination, dry_run=not apply_changes)

if __name__ == "__main__":
    main() 
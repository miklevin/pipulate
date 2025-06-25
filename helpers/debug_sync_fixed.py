#!/usr/bin/env python3
import re
from pathlib import Path
from ascii_art_parser import extract_ascii_art_blocks

# Get ASCII blocks from README.md
readme_path = Path("../README.md")
with open(readme_path, 'r', encoding='utf-8') as f:
    readme_content = f.read()

ascii_block_data = extract_ascii_art_blocks(readme_content)
ascii_blocks = {key: data['art'] for key, data in ascii_block_data.items()}

# Check the specific block
block_key = 'not-on-my-machine-problem-fixed'
if block_key in ascii_blocks:
    print(f"Found block '{block_key}' in README.md")
    print(f"Length: {len(ascii_blocks[block_key])} characters")
    print("Content preview:")
    print(repr(ascii_blocks[block_key][:100]))
    print()
    
    # Check install.md
    install_path = Path("../Pipulate.com/install.md")
    with open(install_path, 'r', encoding='utf-8') as f:
        install_content = f.read()
    
    # Find the marker
    pattern = rf'<!-- START_ASCII_ART: {re.escape(block_key)} -->.*?<!-- END_ASCII_ART: {re.escape(block_key)} -->'
    match = re.search(pattern, install_content, re.DOTALL)
    
    if match:
        print("Found marker in install.md")
        # Extract just the ASCII content between ```
        marker_content = match.group(0)
        art_pattern = r'```\n(.*?)\n```'
        art_match = re.search(art_pattern, marker_content, re.DOTALL)
        
        if art_match:
            install_art = art_match.group(1)
            print(f"Install art length: {len(install_art)} characters")
            print("Install content preview:")
            print(repr(install_art[:100]))
            print()
            print("Are they equal?", ascii_blocks[block_key] == install_art)
            
            if ascii_blocks[block_key] != install_art:
                print("DIFFERENCE DETECTED!")
                # Show first different line
                readme_lines = ascii_blocks[block_key].split('\n')
                install_lines = install_art.split('\n')
                
                for i, (r_line, i_line) in enumerate(zip(readme_lines, install_lines)):
                    if r_line != i_line:
                        print(f"Line {i+1} differs:")
                        print(f"  README : {repr(r_line)}")
                        print(f"  Install: {repr(i_line)}")
                        break
        else:
            print("Could not extract ASCII art from marker content")
    else:
        print("Marker not found in install.md")
else:
    print(f"Block '{block_key}' not found in README.md")

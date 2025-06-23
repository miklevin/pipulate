#!/usr/bin/env python3
"""
Helper script to generate FILES_TO_INCLUDE_RAW content for prompt_foo.py
by enumerating actual directories and files.

Usage:
    python generate_files_list.py
    python prompt_foo.py --files  # (when integrated)
"""

import os
from pathlib import Path

def enumerate_directory(path, comment_prefix="# ", description="", defaults_uncommented=None):
    """Enumerate files in a directory, returning them as commented lines.
    
    Args:
        path: Directory path to enumerate
        comment_prefix: Prefix for commented lines  
        description: Section description
        defaults_uncommented: List of filenames that should be uncommented by default
    """
    lines = []
    if description:
        lines.append(f"\n## {description}")
    
    if defaults_uncommented is None:
        defaults_uncommented = []
    
    try:
        if os.path.exists(path):
            files = sorted(os.listdir(path))
            for file in files:
                file_path = os.path.join(path, file)
                if os.path.isfile(file_path):
                    # Check if this file should be uncommented by default
                    should_comment = file not in defaults_uncommented
                    prefix = comment_prefix if should_comment else ""
                    lines.append(f"{prefix}{file_path}")
        else:
            lines.append(f"{comment_prefix}# Directory not found: {path}")
    except Exception as e:
        lines.append(f"{comment_prefix}# Error reading {path}: {e}")
    
    return lines

def enumerate_specific_files(file_list, comment_prefix="# ", description=""):
    """Enumerate specific files, commenting them out."""
    lines = []
    if description:
        lines.append(f"\n## {description}")
    
    for file_path in file_list:
        if os.path.exists(file_path):
            lines.append(f"{comment_prefix}{file_path}")
        else:
            lines.append(f"{comment_prefix}{file_path}  # <-- NOT FOUND")
    
    return lines

def generate_files_list():
    """Generate the complete FILES_TO_INCLUDE_RAW content."""
    
    # Base repository paths
    base_paths = {
        'pipulate': '/home/mike/repos/pipulate',
        'mikelev': '/home/mike/repos/MikeLev.in',
        'pipulate_com': '/home/mike/repos/Pipulate.com'
    }
    
    lines = []
    
    # Header comment
    lines.extend([
        "",
        "# HI GEMINI! HERE'S SOME SUPER OVER-ARCHING CONTEXT OF THIS XML",
        "# THE STUFF IN THIS XML PAYLOAD IS STILL ONLY PART OF THE STORY", 
        "# BUT YOU CAN SEE ME PAIRING IT DOWN TO ~100K TOKENS FOR US NOW",
        ""
    ])
    
    # Core files (in pipulate root) - some uncommented by default
    lines.append("# CORE FILES & DOCS (Setting the stage)")
    core_files = [
        ("README.md", True),        # commented by default
        ("flake.nix", False),       # uncommented - useful
        ("requirements.txt", False), # uncommented - useful
        ("server.py", False),       # uncommented - useful  
        (".gitignore", True)        # commented by default
    ]
    for file, should_comment in core_files:
        full_path = f"{base_paths['pipulate']}/{file}"
        comment = "# " if should_comment else ""
        lines.append(f"{comment}{full_path}")
    
    # Common/shared files
    lines.extend(enumerate_specific_files([
        f"{base_paths['pipulate']}/plugins/common.py",
        f"{base_paths['pipulate_com']}/install.sh"
    ], description="COMMON/SHARED FILES"))
    
    # Current prompt necessities (placeholder - user fills this in)
    lines.append("\n## NECESSARY FOR CURRENT PROMPT")
    lines.append("# (Edit this section to include files needed for your specific prompt)")
    
    # Botify API documentation
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/training", 
        description="BOTIFY API DOCUMENTATION"
    ))
    
    # Static resources
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/static",
        description="STATIC RESOURCES"
    ))
    
    # Helper scripts
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/helpers",
        description="HELPER SCRIPTS"
    ))
    
    # Plugins
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/plugins", 
        description="PLUGINS"
    ))
    
    # Rules documentation - include all rules by default
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/.cursor/rules",
        description="DA RULES",
        defaults_uncommented=[
            "00_PIPULATE_MASTER_GUIDE.mdc",
            "01_CRITICAL_PATTERNS.mdc", 
            "02_CORE_CONCEPTS.mdc"
        ]
    ))
    
    # Training files - include some key ones by default
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/training",
        description="TRAINING FILES",
        defaults_uncommented=[
            "system_prompt.md",
            "debugging_transparency_system.md",
            "advanced_ai_guide.md"
        ]
    ))
    
    # Pipulate.com website
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate_com']}",
        description="PIPULATE.COM WEBSITE & GUIDE"
    ))
    
    # Pipulate.com guide files
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate_com']}/_guide",
        description="PIPULATE.COM GUIDE ARTICLES"
    ))
    
    # Recent blog posts (just list directory, user picks)
    lines.extend(enumerate_directory(
        f"{base_paths['mikelev']}/_posts",
        description="RECENT ARTICLES FROM MIKELEV.IN (Last 20 files shown)"
    ))
    
    return "\n".join(lines)

def main():
    """Main function to generate and output the files list."""
    print("Generating foo_files.py module...")
    print("=" * 60)
    
    content = generate_files_list()
    
    # Create a proper Python module
    module_content = f'''"""
Generated file list for prompt_foo.py
Auto-generated by generate_files_list.py - edit this file to uncomment desired files.
"""

FILES_TO_INCLUDE_RAW = """\\{content}
"""
'''
    
    # Write to foo_files.py in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "foo_files.py")
    
    with open(output_file, 'w') as f:
        f.write(module_content)
    
    print(f"Python module written to: {output_file}")
    print("\nTo use this:")
    print("1. Edit foo_files.py to uncomment the files you want to include")
    print("2. Run prompt_foo.py as usual - it will automatically import from foo_files.py")
    print("3. To regenerate the file list, run this script again")
    
    # Also show first few lines for verification
    print("\n" + "=" * 60)
    print("First few lines of generated foo_files.py:")
    print("=" * 60)
    lines = module_content.split('\n')[:15]
    for line in lines:
        print(line)

if __name__ == "__main__":
    main() 
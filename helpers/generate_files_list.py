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
from collections import namedtuple

# Named tuple for file entries with explicit labels
FileEntry = namedtuple('FileEntry', ['filename', 'double_comment', 'description'])

def should_exclude_file(file_path):
    """Check if a file should be excluded from the enumeration."""
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()
    
    # Specific files to exclude
    exclude_files = {
        'foo.txt',
        'foo_files.py', 
        'prompt.md',
        'template.md',
        'favicon.ico',
        'botify_token.txt'
    }
    
    # File extensions to exclude
    exclude_extensions = {
        '.svg',
        '.png', 
        '.ico',
        '.lock',
        '.jpg',
        '.jpeg',
        '.gif',
        '.webp',
        '.csv'
    }
    
    # Check specific filenames
    if file_name in exclude_files:
        return True
        
    # Check file extensions
    if file_ext in exclude_extensions:
        return True
        
    # Exclude backup files
    if file_name.endswith('.backup'):
        return True
        
    # Exclude hidden files (starting with .)
    if file_name.startswith('.') and file_name not in ['.gitignore']:
        return True
        
    return False

def should_skip_directory(dir_name):
    """Check if a directory should be skipped during recursive walking."""
    skip_dirs = {
        '__pycache__',
        '.ipynb_checkpoints',
        '.git',
        'node_modules',
        '.venv'
    }
    return dir_name in skip_dirs

def enumerate_directory(path, comment_prefix="# ", description="", defaults_uncommented=None, recursive=False):
    """Enumerate files in a directory, returning them as commented lines.
    
    Args:
        path: Directory path to enumerate
        comment_prefix: Prefix for commented lines  
        description: Section description
        defaults_uncommented: List of filenames that should be uncommented by default
        recursive: Whether to walk directories recursively
    """
    lines = []
    if description:
        lines.append(f"\n## {description}")
    
    if defaults_uncommented is None:
        defaults_uncommented = []
    
    try:
        if os.path.exists(path):
            if recursive:
                # Use os.walk for recursive directory traversal
                for root, dirs, files in os.walk(path):
                    # Skip unwanted directories in-place (modifies dirs list)
                    dirs[:] = [d for d in dirs if not should_skip_directory(d)]
                    
                    for file in sorted(files):
                        file_path = os.path.join(root, file)
                        
                        # Skip files that should be excluded
                        if should_exclude_file(file_path):
                            continue
                            
                        # Check if this file should be uncommented by default
                        should_comment = file not in defaults_uncommented
                        prefix = comment_prefix if should_comment else ""
                        lines.append(f"{prefix}{file_path}")
            else:
                # Non-recursive: only files in the immediate directory
                files = sorted(os.listdir(path))
                for file in files:
                    file_path = os.path.join(path, file)
                    if os.path.isfile(file_path):
                        # Skip files that should be excluded
                        if should_exclude_file(file_path):
                            continue
                            
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
        # Skip files that should be excluded
        if should_exclude_file(file_path):
            continue
            
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
        "",
        "# Or in other words...",
        "",
        "# Once upon a midnight dreary, I thought I'd let you think more clearly",
        "# About the quaint and curious volumes of code required for your given chore.",
        "# While curating git repo packaging picking context for your ransackaging",
        "# In this XML payload for you to parse in ways I hope you will adore.",
        ""
    ])
    
    # Core files (in pipulate root) - some uncommented by default
    lines.append("# CORE FILES & DOCS (Setting the stage)")
    core_files = [
        FileEntry("README.md", True, "Single source of truth"),
        FileEntry(".gitignore", True, "Lets data stay in the repo"),
        FileEntry("flake.nix", False, "IaC - Infrastructure as Code"),
        FileEntry("requirements.txt", False, "Python dependencies"),
        FileEntry("server.py", False, "Server entrypoint"),
        FileEntry("common.py", False, "CRUD base class"),
        FileEntry("mcp_tools.py", False, "MCP tools - AI assistant interface"),
    ]
    for entry in core_files:
        full_path = f"{base_paths['pipulate']}/{entry.filename}"
        if entry.double_comment:
            # Double comments for emphasized files
            lines.append(f"# {full_path}  # <-- {entry.description}")
        else:
            # Single comment with description
            lines.append(f"{full_path}  # {entry.description}")
    
    # PyPI release system files - all uncommented by default for version management
    lines.append("\n## PYPI RELEASE SYSTEM FILES")
    pypi_files = [
        FileEntry("__init__.py", False, "Package init with version"),
        FileEntry("cli.py", False, "CLI interface for PyPI package"),
        FileEntry("pyproject.toml", False, "Package configuration"),
        FileEntry("version_sync.py", False, "Version synchronization system"),
        FileEntry("VERSION_MANAGEMENT.md", False, "Version system docs"),
        FileEntry("TESTING_PYPI.md", False, "PyPI testing guide"),
        FileEntry("LICENSE", False, "MIT License for PyPI package"),
        FileEntry("PUBLISHING.md", False, "PyPI publishing documentation"),
    ]
    for entry in pypi_files:
        full_path = f"{base_paths['pipulate']}/{entry.filename}"
        if entry.double_comment:
            # Double comments for emphasized files
            lines.append(f"# {full_path}  # <-- {entry.description}")
        else:
            # Single comment with description (uncommented since these are active)
            lines.append(f"{full_path}  # {entry.description}")
    
    # Common/shared files
    lines.extend(enumerate_specific_files([
        f"{base_paths['pipulate_com']}/install.sh"
    ], description="COMMON/SHARED FILES"))
    
    # Current prompt necessities (placeholder - user fills this in)
    lines.append("\n## NECESSARY FOR CURRENT PROMPT")
    lines.append("# (Edit this section to include files needed for your specific prompt)")
    
    # External/add-on files frequently used for AI assistance
    external_files = [
        "/home/mike/repos/nixos/ai.py",
        "/home/mike/repos/nixos/autognome.py", 
        "/home/mike/repos/nixos/configuration.nix",
        "/home/mike/repos/nixos/init.lua"
    ]
    lines.extend(enumerate_specific_files(
        external_files,
        description="EXTERNAL/ADD-ON FILES (Frequently used with AI)"
    ))
    
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
    
    # Helper scripts - recursive to include subdirectories
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/helpers",
        description="HELPER SCRIPTS",
        recursive=True
    ))
    
    # Plugins
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/plugins", 
        description="PLUGINS"
    ))
    
    # Rules documentation
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/.cursor/rules",
        description="DA RULES"
    ))
    
    # Training files
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/training",
        description="TRAINING FILES"
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
        description="ARTICLES FROM MIKELEV.IN"
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
    lines = module_content.split('\n')[:19]
    for line in lines:
        print(line)

if __name__ == "__main__":
    main() 
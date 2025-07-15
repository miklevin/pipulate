#!/usr/bin/env python3
"""
Helper script to generate FILES_TO_INCLUDE_RAW content for prompt_foo.py
by enumerating actual directories and files.

Usage:
    python generate_files_list.py
    python prompt_foo.py --files  # (when integrated)
"""

import os
import re
import tiktoken
from pathlib import Path
from collections import namedtuple

# Named tuple for file entries with explicit labels
FileEntry = namedtuple('FileEntry', ['filename', 'double_comment', 'description'])

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count the number of tokens in a text string."""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        print(f"Warning: Could not count tokens for text: {e}")
        return 0

def get_file_token_count(file_path: str) -> int:
    """Get token count for a specific file."""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return count_tokens(content)
        return 0
    except Exception as e:
        print(f"Warning: Could not count tokens for {file_path}: {e}")
        return 0

def format_token_count(token_count: int) -> str:
    """Format token count with commas."""
    return f"{token_count:,}"

def parse_gitignore(repo_root):
    """Parse .gitignore file and return patterns to exclude."""
    gitignore_path = os.path.join(repo_root, '.gitignore')
    ignore_patterns = []
    
    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    # Convert gitignore pattern to regex pattern
                    pattern = line.replace('.', r'\.').replace('*', '.*')
                    # Handle directory patterns (ending with /)
                    if pattern.endswith('/'):
                        pattern = f"^{pattern}.*"
                    else:
                        pattern = f"^{pattern}$|^{pattern}/|/{pattern}$|/{pattern}/"
                    ignore_patterns.append(re.compile(pattern))
        except Exception as e:
            print(f"Warning: Error parsing .gitignore: {e}")
    
    return ignore_patterns

def should_exclude_file(file_path, ignore_patterns=None):
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
    
    # Check against gitignore patterns
    if ignore_patterns:
        for pattern in ignore_patterns:
            if pattern.search(file_path):
                return True
        
    return False

def should_skip_directory(dir_name, dir_path=None, ignore_patterns=None):
    """Check if a directory should be skipped during recursive walking."""
    skip_dirs = {
        '__pycache__',
        '.ipynb_checkpoints',
        '.git',
        'node_modules',
        '.venv'
    }
    
    # Basic directory name check
    if dir_name in skip_dirs:
        return True
    
    # Check against gitignore patterns if provided
    if ignore_patterns and dir_path:
        for pattern in ignore_patterns:
            if pattern.search(f"{dir_path}/"):
                return True
    
    return False

def enumerate_directory(path, comment_prefix="# ", description="", defaults_uncommented=None, recursive=False, ignore_patterns=None):
    """Enumerate files in a directory, returning them as commented lines.
    
    Args:
        path: Directory path to enumerate
        comment_prefix: Prefix for commented lines  
        description: Section description
        defaults_uncommented: List of filenames that should be uncommented by default
        recursive: Whether to walk directories recursively
        ignore_patterns: List of regex patterns from .gitignore
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
                    dirs[:] = [d for d in dirs if not should_skip_directory(d, os.path.join(root, d), ignore_patterns)]
                    
                    for file in sorted(files):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, os.path.dirname(path))
                        
                        # Skip files that should be excluded
                        if should_exclude_file(rel_path, ignore_patterns):
                            continue
                            
                        # Get token count for the file
                        token_count = get_file_token_count(file_path)
                        token_info = f"[{format_token_count(token_count)}]"
                        
                        # Check if this file should be uncommented by default
                        should_comment = file not in defaults_uncommented
                        prefix = comment_prefix if should_comment else ""
                        lines.append(f"{prefix}{file_path}  # {token_info}")
            else:
                # Non-recursive: only files in the immediate directory
                files = sorted(os.listdir(path))
                for file in files:
                    file_path = os.path.join(path, file)
                    if os.path.isfile(file_path):
                        rel_path = os.path.relpath(file_path, os.path.dirname(path))
                        
                        # Skip files that should be excluded
                        if should_exclude_file(rel_path, ignore_patterns):
                            continue
                            
                        # Get token count for the file
                        token_count = get_file_token_count(file_path)
                        token_info = f"[{format_token_count(token_count)}]"
                        
                        # Check if this file should be uncommented by default
                        should_comment = file not in defaults_uncommented
                        prefix = comment_prefix if should_comment else ""
                        lines.append(f"{prefix}{file_path}  # {token_info}")
        else:
            lines.append(f"{comment_prefix}# Directory not found: {path}")
    except Exception as e:
        lines.append(f"{comment_prefix}# Error reading {path}: {e}")
    
    return lines

def enumerate_specific_files(file_list, comment_prefix="# ", description="", ignore_patterns=None):
    """Enumerate specific files, commenting them out."""
    lines = []
    if description:
        lines.append(f"\n## {description}")
    
    for file_path in file_list:
        # Skip files that should be excluded
        if should_exclude_file(file_path, ignore_patterns):
            continue
            
        if os.path.exists(file_path):
            # Get token count for the file
            token_count = get_file_token_count(file_path)
            token_info = f"[{format_token_count(token_count)}]"
            lines.append(f"{comment_prefix}{file_path}  # {token_info}")
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
    
    # Parse .gitignore for more intelligent exclusions
    ignore_patterns = parse_gitignore(base_paths['pipulate'])
    
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
        FileEntry(".gitignore", False, "Lets data stay in the repo"),
        FileEntry("flake.nix", False, "IaC - Infrastructure as Code"),
        FileEntry("requirements.txt", False, "Python dependencies"),
        FileEntry("__init__.py", False, "Package init with version info - single source of truth"),
        FileEntry("config.py", False, "Centralized configuration - single source of truth"),
        FileEntry("server.py", False, "Server entrypoint"),
        FileEntry("common.py", False, "CRUD base class and shared utilities"),
        FileEntry("database.py", False, "Database utilities and DictLikeDB wrapper"),
        FileEntry("mcp_tools.py", False, "MCP tools - AI assistant interface"),
        FileEntry("cli.py", False, "CLI interface for PyPI package and local execution"),
        FileEntry("logging_utils.py", False, "Logging utilities and DebugConsole"),
        FileEntry("plugin_system.py", False, "Plugin discovery and loading system"),
        FileEntry("helpers/ascii_displays.py", True, "Externalized ASCII art functions"),
    ]

    # Not core but also important files
    important_files = [
        FileEntry("keychain.py", True, "AI Keychain - Persistent memory for Chip O'Theseus"),
        FileEntry("discover_mcp_tools.py", True, "MCP tool discovery and validation"),
        FileEntry("botify_extraction_demo.py", True, "Demo script showing Botify tools extraction success"),
        FileEntry("vulture_whitelist.py", True, "Dead code detection whitelist for development"),
        FileEntry("tools/__init__.py", False, "Modular tools package interface"),
    ]
    
    for entry in core_files:
        full_path = f"{base_paths['pipulate']}/{entry.filename}"
        
        # Get token count for the file
        token_count = get_file_token_count(full_path)
        token_info = f"[{format_token_count(token_count)}]"
        
        if entry.double_comment:
            # Double comments for emphasized files
            lines.append(f"# {full_path}  # <-- {entry.description} {token_info}")
        else:
            # Single comment with description
            lines.append(f"{full_path}  # {entry.description} {token_info}")
    
    # Add important files section
    for entry in important_files:
        full_path = f"{base_paths['pipulate']}/{entry.filename}"
        
        # Get token count for the file
        token_count = get_file_token_count(full_path)
        token_info = f"[{format_token_count(token_count)}]"
        
        if entry.double_comment:
            # Double comments for emphasized files
            lines.append(f"# {full_path}  # <-- {entry.description} {token_info}")
        else:
            # Single comment with description
            lines.append(f"{full_path}  # {entry.description} {token_info}")
    
    # Tools directory - modular MCP tools (NEW)
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/tools",
        description="MODULAR MCP TOOLS (Extracted for token optimization)",
        ignore_patterns=ignore_patterns
    ))
    
    # PyPI release system files - commented out by default
    lines.append("\n## PYPI RELEASE SYSTEM FILES")
    pypi_files = [
        FileEntry("__init__.py", True, "Package init with version"),
        FileEntry("cli.py", True, "CLI interface for PyPI package"),
        FileEntry("pyproject.toml", True, "Package configuration"),
        FileEntry("LICENSE", True, "MIT License for PyPI package"),
        # FileEntry("version_sync.py", True, "Version synchronization system"),
        # FileEntry("VERSION_MANAGEMENT.md", True, "Version system docs"),
        # FileEntry("TESTING_PYPI.md", True, "PyPI testing guide"),
        # FileEntry("PUBLISHING.md", True, "PyPI publishing documentation"),
    ]
    for entry in pypi_files:
        full_path = f"{base_paths['pipulate']}/{entry.filename}"
        
        # Get token count for the file
        token_count = get_file_token_count(full_path)
        token_info = f"[{format_token_count(token_count)}]"
        
        if entry.double_comment:
            # Double comments for emphasized files
            lines.append(f"# {full_path}  # <-- {entry.description} {token_info}")
        else:
            # Single comment with description (uncommented since these are active)
            lines.append(f"{full_path}  # {entry.description} {token_info}")
    

    
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
        description="EXTERNAL/ADD-ON FILES (Frequently used with AI)",
        ignore_patterns=ignore_patterns
    ))
    
    # AI Discovery directory (NEW) - recursive to include subdirectories
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/ai_discovery",
        description="AI DISCOVERY (AI Assistant Training & Progressive Discovery)",
        recursive=True,
        ignore_patterns=ignore_patterns
    ))
    
    # Botify API documentation
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/training", 
        description="IN-APP TRAINING FILES",
        ignore_patterns=ignore_patterns
    ))
    
    # Static resources
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/static",
        description="STATIC RESOURCES",
        ignore_patterns=ignore_patterns
    ))
    
    # Helper scripts - recursive to include subdirectories
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/helpers",
        description="HELPER SCRIPTS",
        recursive=True,
        ignore_patterns=ignore_patterns
    ))
    
    # Plugins
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/plugins", 
        description="PLUGINS",
        ignore_patterns=ignore_patterns
    ))
    
    # Rules documentation
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/.cursor/rules",
        description="DA RULES",
        ignore_patterns=ignore_patterns
    ))
    
    # Browser automation directory (NEW)
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/browser_automation",
        description="BROWSER AUTOMATION (Selenium Scripts & Templates)",
        ignore_patterns=ignore_patterns
    ))
    
    # Browser automation recipes - deliberately included
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate']}/browser_automation/automation_recipes",
        description="BROWSER AUTOMATION RECIPES",
        recursive=True,
        ignore_patterns=ignore_patterns
    ))
    
    # Pipulate.com website
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate_com']}",
        description="PIPULATE.COM WEBSITE & GUIDE",
        ignore_patterns=ignore_patterns
    ))
    
    # Pipulate.com guide files
    lines.extend(enumerate_directory(
        f"{base_paths['pipulate_com']}/_guide",
        description="PIPULATE.COM GUIDE ARTICLES",
        ignore_patterns=ignore_patterns
    ))
    
    # Recent blog posts (just list directory, user picks)
    lines.extend(enumerate_directory(
        f"{base_paths['mikelev']}/_posts",
        description="ARTICLES FROM MIKELEV.IN",
        ignore_patterns=ignore_patterns
    ))
    
    # Add suggestions for other directories to consider
    # lines.extend([
    #     "\n## POTENTIAL DIRECTORIES TO CONSIDER",
    #     "# The following directories might be worth including if they exist or are added later:",
    #     "# /home/mike/repos/pipulate/notebooks/  # Jupyter notebooks directory",
    #     "# /home/mike/repos/pipulate/examples/   # Example code and usage patterns",
    #     "# /home/mike/repos/pipulate/docs/       # Documentation files",
    #     "# /home/mike/repos/pipulate/tests/      # Test files and test fixtures",
    #     "# /home/mike/repos/pipulate/scripts/    # Utility scripts",
    #     "# /home/mike/repos/pipulate/templates/  # Template files",
    #     "# /home/mike/repos/pipulate/config/     # Configuration files"
    # ])
    
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

IMPORTANT NOTES:
1. Lines starting with # are commented out and will NOT be included in the prompt
2. Files matching patterns in .gitignore are automatically excluded
3. Add files needed for your current task under "NECESSARY FOR CURRENT PROMPT"
4. The AI discovery directory contains critical AI assistant training materials
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

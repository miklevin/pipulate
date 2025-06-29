#!/usr/bin/env python3
"""
Version Synchronization Script for Pipulate

This script ensures all version numbers across the codebase come from a single
source of truth: pipulate.__version__ in __init__.py

Files updated:
- pyproject.toml
- flake.nix  
- Pipulate.com/install.sh (if in workspace)

Usage:
    python -c "from pipulate.version_sync import sync_all_versions; sync_all_versions()"
    
Or run directly:
    python pipulate/version_sync.py
"""

import os
import re
import sys
from pathlib import Path

def get_version():
    """Get the version from __init__.py at project root"""
    # Script is at: pipulate/helpers/release/version_sync.py
    # __init__.py is at: pipulate/__init__.py
    # So we need to go up 2 levels from script location
    script_dir = Path(__file__).parent  # pipulate/helpers/release/
    project_root = script_dir.parent.parent  # pipulate/
    init_file = project_root / "__init__.py"
    
    if not init_file.exists():
        raise RuntimeError(f"Could not find __init__.py at {init_file}")
    
    content = init_file.read_text()
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if not match:
        raise RuntimeError(f"Could not find __version__ in {init_file}")
    
    return match.group(1)

def update_pyproject_toml(version):
    """Update version in pyproject.toml"""
    pyproject_file = Path("pyproject.toml")
    if not pyproject_file.exists():
        print(f"⚠️  {pyproject_file} not found, skipping...")
        return False
    
    content = pyproject_file.read_text()
    old_content = content
    
    # Update version line
    content = re.sub(
        r'version\s*=\s*["\'][^"\']+["\']',
        f'version = "{version}"',
        content
    )
    
    if content != old_content:
        pyproject_file.write_text(content)
        print(f"✅ Updated {pyproject_file}")
        return True
    else:
        print(f"ℹ️  {pyproject_file} already up to date")
        return False

def update_flake_nix(version):
    """Update version in flake.nix"""
    flake_file = Path("flake.nix")
    if not flake_file.exists():
        print(f"⚠️  {flake_file} not found, skipping...")
        return False
    
    content = flake_file.read_text()
    old_content = content
    
    # Update version line in flake.nix - preserve any subtitle
    # Pattern: version = "1.0.8 (JupyterLab Python Version Fix)";
    version_match = re.search(r'version\s*=\s*"([^"]*?)(?:\s*\([^)]+\))?"', content)
    if version_match:
        # Extract any subtitle in parentheses from current version
        current_version_line = version_match.group(0)
        subtitle_match = re.search(r'\(([^)]+)\)', current_version_line)
        
        if subtitle_match:
            # Preserve subtitle
            new_version = f'{version} ({subtitle_match.group(1)})'
        else:
            new_version = version
            
        content = re.sub(
            r'version\s*=\s*"[^"]*"',
            f'version = "{new_version}"',
            content
        )
    
    if content != old_content:
        flake_file.write_text(content)
        print(f"✅ Updated {flake_file}")
        return True
    else:
        print(f"ℹ️  {flake_file} already up to date")
        return False

def update_install_sh(version):
    """Update version in Pipulate.com/install.sh if it exists"""
    # Check for install.sh in common locations
    possible_paths = [
        Path("../Pipulate.com/install.sh"),  # If running from pipulate/ dir
        Path("Pipulate.com/install.sh"),     # If running from workspace root
        Path("install.sh")                   # If running from Pipulate.com dir
    ]
    
    install_file = None
    for path in possible_paths:
        if path.exists():
            install_file = path
            break
    
    if not install_file:
        print(f"⚠️  install.sh not found in expected locations, skipping...")
        return False
    
    content = install_file.read_text()
    old_content = content
    
    # Update VERSION line
    content = re.sub(
        r'VERSION\s*=\s*["\'][^"\']+["\']',
        f'VERSION="{version}"',
        content
    )
    
    if content != old_content:
        install_file.write_text(content)
        print(f"✅ Updated {install_file}")
        return True
    else:
        print(f"ℹ️  {install_file} already up to date")
        return False

def sync_all_versions():
    """Synchronize all version numbers from the single source of truth"""
    print("🔄 Synchronizing version numbers from single source of truth...")
    
    try:
        version = get_version()
        print(f"📋 Source version: {version}")
        print()
        
        updates = []
        updates.append(update_pyproject_toml(version))
        updates.append(update_flake_nix(version))
        updates.append(update_install_sh(version))
        
        print()
        if any(updates):
            print("✨ Version synchronization complete!")
            print("🔧 Files updated with unified version numbers")
        else:
            print("✨ All files already synchronized!")
            
    except Exception as e:
        print(f"❌ Error synchronizing versions: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sync_all_versions() 
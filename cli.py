#!/usr/bin/env python3
"""
Pipulate CLI - Simple installation and execution interface

Usage:
    pipulate install [app_name]   # Install with optional custom name
    pipulate run [app_name]       # Run existing installation  
    pipulate uninstall [app_name] # Clean uninstall for testing
    pipulate --help               # Show this help
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def check_nix_installed():
    """Check if Nix is already installed on the system."""
    try:
        result = subprocess.run(['nix', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Nix detected: {version}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    print("❌ Nix not found on system")
    return False


def install_nix():
    """Install Nix using the Determinate Systems installer."""
    print("🔧 Installing Nix (required for Pipulate environment)...")
    print("⚠️  This will install Nix package manager on your system.")
    
    response = input("Continue? [y/N]: ").lower().strip()
    if response != 'y':
        print("❌ Installation cancelled by user")
        sys.exit(1)
    
    try:
        cmd = [
            'curl', '--proto', '=https', '--tlsv1.2', '-sSf', '-L',
            'https://install.determinate.systems/nix',
            '|', 'sh', '-s', '--', 'install'
        ]
        
        # Use shell=True for pipe command
        cmd_str = ' '.join(cmd)
        result = subprocess.run(cmd_str, shell=True, check=True)
        
        print("✅ Nix installation complete!")
        print("⚠️  Please close this terminal and open a new one before continuing.")
        print("   Then run: pipulate install")
        sys.exit(0)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Nix installation failed: {e}")
        sys.exit(1)


def get_install_directory(app_name):
    """Get the installation directory for the app."""
    return Path.home() / app_name


def download_and_extract(app_name):
    """Download and extract Pipulate to the target directory."""
    target_dir = get_install_directory(app_name)
    
    # Remove existing installation if present
    if target_dir.exists():
        print(f"🗑️  Removing existing installation: {target_dir}")
        shutil.rmtree(target_dir)
    
    print(f"📦 Installing Pipulate to: {target_dir}")
    
    # Use the same installer script approach, but call it directly
    try:
        # Download and run the installer
        cmd = f'curl -L https://pipulate.com/install.sh | sh -s {app_name}'
        result = subprocess.run(cmd, shell=True, check=True)
        
        print(f"✅ Installation complete: {target_dir}")
        return target_dir
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        sys.exit(1)


def run_pipulate(app_name):
    """Run the installed Pipulate instance."""
    target_dir = get_install_directory(app_name)
    
    if not target_dir.exists():
        print(f"❌ No installation found at: {target_dir}")
        print(f"   Run: pipulate install {app_name}")
        sys.exit(1)
    
    print(f"🚀 Starting Pipulate from: {target_dir}")
    print("📋 Manual steps:")
    print(f"   cd {target_dir}")
    print("   nix develop")
    print()
    print("⚠️  Make sure your dev version is stopped first to avoid port conflicts!")
    
    # Change to the directory and run nix develop
    os.chdir(target_dir)
    try:
        # Use exec to replace the current process
        os.execvp('nix', ['nix', 'develop'])
    except FileNotFoundError:
        print("❌ Nix not found. Please install Nix first:")
        print("   curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install")
        sys.exit(1)


def uninstall_pipulate(app_name):
    """Clean uninstall of Pipulate (keeps Nix)."""
    target_dir = get_install_directory(app_name)
    
    if not target_dir.exists():
        print(f"ℹ️  No installation found at: {target_dir}")
        return
    
    print(f"🗑️  Uninstalling Pipulate from: {target_dir}")
    print("⚠️  This will remove the entire directory and all data!")
    
    response = input("Continue? [y/N]: ").lower().strip()
    if response != 'y':
        print("❌ Uninstall cancelled")
        return
    
    try:
        shutil.rmtree(target_dir)
        print("✅ Uninstall complete!")
        print("ℹ️  Nix remains installed for future use")
        print(f"   Ready for: pipulate install {app_name}")
        
    except Exception as e:
        print(f"❌ Uninstall failed: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Pipulate - Local-First AI SEO Software",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    pipulate install              # Install as 'pipulate'
    pipulate install mybotify     # Install as 'mybotify' 
    pipulate run mybotify         # Run existing installation
    pipulate uninstall mybotify   # Clean uninstall

Notes:
    - Nix is installed once and reused for all instances
    - Stop your dev version before running to avoid port conflicts
    - Uninstall removes the app directory but keeps Nix
        """
    )
    
    parser.add_argument('command', 
                       choices=['install', 'run', 'uninstall'],
                       help='Command to execute')
    
    parser.add_argument('app_name', 
                       nargs='?', 
                       default='pipulate',
                       help='Application name (default: pipulate)')
    
    args = parser.parse_args()
    
    print("🎯 Pipulate CLI - Local-First AI SEO Software")
    print()
    
    if args.command == 'install':
        # Check Nix first
        if not check_nix_installed():
            install_nix()
            # Will exit after Nix installation
        
        # Proceed with Pipulate installation
        download_and_extract(args.app_name)
        print()
        print("🎯 Installation complete! To run:")
        print(f"   pipulate run {args.app_name}")
        
    elif args.command == 'run':
        run_pipulate(args.app_name)
        
    elif args.command == 'uninstall':
        uninstall_pipulate(args.app_name)


if __name__ == '__main__':
    main() 
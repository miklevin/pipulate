#!/usr/bin/env python3
"""
Pipulate CLI - The PyPI Discovery Gateway

This module provides the `pipulate` command installed via `pip install pipulate`.
It handles both first-time installation and subsequent launches.

The flow:
1. pip install pipulate
2. pipulate  # First time: runs installation, subsequent: runs server
"""

import os
import sys
import subprocess
import platform
import shutil
import click
from pathlib import Path
import requests
import tempfile
import stat

# ANSI color codes for beautiful terminal output
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_banner():
    """Print the Pipulate banner"""
    banner = f"""
{Colors.CYAN}╔═════════════════════════════════════════════════════════════════════════╗{Colors.END}
{Colors.CYAN}║{Colors.END}  {Colors.PURPLE}🎭 PIPULATE: LOCAL-FIRST AI SEO SOFTWARE & DIGITAL WORKSHOP{Colors.END}            {Colors.CYAN}║{Colors.END}
{Colors.CYAN}║{Colors.END}  {Colors.BLUE}────────────────────────────────────────────────────────────────────────{Colors.END} {Colors.CYAN}║{Colors.END}
{Colors.CYAN}║{Colors.END}                                                                         {Colors.CYAN}║{Colors.END}
{Colors.CYAN}║{Colors.END}  {Colors.GREEN}💬 Chip O'Theseus: "Welcome to your sovereign computing environment!"{Colors.END}  {Colors.CYAN}║{Colors.END}
{Colors.CYAN}║{Colors.END}                                                                         {Colors.CYAN}║{Colors.END}
{Colors.CYAN}║{Colors.END}  {Colors.YELLOW}🌟 Where Python functions become HTML elements...{Colors.END}                      {Colors.CYAN}║{Colors.END}
{Colors.CYAN}║{Colors.END}  {Colors.YELLOW}🌟 Where workflows preserve your creative process...{Colors.END}                   {Colors.CYAN}║{Colors.END}
{Colors.CYAN}║{Colors.END}  {Colors.YELLOW}🌟 Where AI assists without cloud dependencies...{Colors.END}                      {Colors.CYAN}║{Colors.END}
{Colors.CYAN}╚═════════════════════════════════════════════════════════════════════════╝{Colors.END}
"""
    print(banner)

def check_nix_installed():
    """Check if Nix is installed"""
    return shutil.which('nix') is not None

def install_nix():
    """Install Nix using the Determinate Systems installer"""
    print(f"{Colors.BLUE}🔧 Installing Nix (required for Pipulate environment)...{Colors.END}")
    
    # Download and run the Nix installer
    install_cmd = [
        'curl', '--proto', '=https', '--tlsv1.2', '-sSf', '-L',
        'https://install.determinate.systems/nix', '|', 'sh', '-s', '--', 'install'
    ]
    
    try:
        # Use shell=True for the pipe
        result = subprocess.run(
            'curl --proto "=https" --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install',
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"{Colors.GREEN}✅ Nix installed successfully!{Colors.END}")
        print(f"{Colors.YELLOW}⚠️  Please close this terminal and open a new one before continuing.{Colors.END}")
        print(f"{Colors.YELLOW}⚠️  Then run 'pipulate' again to complete the installation.{Colors.END}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}❌ Failed to install Nix: {e}{Colors.END}")
        return False

def find_pipulate_installation():
    """Find existing Pipulate installation directory"""
    possible_dirs = [
        Path.home() / "pipulate",
        Path.home() / "Pipulate", 
        Path.home() / "Botifython",
        Path.cwd() / "pipulate"
    ]
    
    for dir_path in possible_dirs:
        if dir_path.exists() and (dir_path / "server.py").exists():
            return dir_path
    
    return None

def download_install_script(install_dir):
    """Download the Pipulate install script"""
    try:
        response = requests.get("https://pipulate.com/install.sh", timeout=30)
        response.raise_for_status()
        
        install_script = install_dir / "install.sh"
        install_script.write_text(response.text)
        
        # Make executable
        current_permissions = install_script.stat().st_mode
        install_script.chmod(current_permissions | stat.S_IEXEC)
        
        return install_script
    except Exception as e:
        print(f"{Colors.RED}❌ Failed to download install script: {e}{Colors.END}")
        return None

def run_pipulate_installation(install_name=None):
    """Run the full Pipulate installation"""
    if not install_name:
        install_name = "pipulate"
    
    home_dir = Path.home()
    install_dir = home_dir / install_name
    
    print(f"{Colors.BLUE}📦 Installing Pipulate to {install_dir}...{Colors.END}")
    
    # Create installation directory
    install_dir.mkdir(exist_ok=True)
    
    # Download and run install script
    install_script = download_install_script(install_dir)
    if not install_script:
        return False
    
    try:
        # Run the install script with the target directory
        result = subprocess.run([
            'bash', str(install_script), install_name
        ], cwd=home_dir, check=True, capture_output=True, text=True)
        
        print(f"{Colors.GREEN}✅ Pipulate installed successfully to {install_dir}!{Colors.END}")
        return install_dir
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}❌ Installation failed: {e}{Colors.END}")
        print(f"{Colors.RED}Output: {e.stdout}{Colors.END}")
        print(f"{Colors.RED}Error: {e.stderr}{Colors.END}")
        return False

def run_pipulate_server(pipulate_dir):
    """Run the Pipulate server"""
    print(f"{Colors.BLUE}🚀 Starting Pipulate server...{Colors.END}")
    
    try:
        # Change to pipulate directory and run nix develop
        result = subprocess.run([
            'nix', 'develop'
        ], cwd=pipulate_dir, check=False)
        
        return True
    except Exception as e:
        print(f"{Colors.RED}❌ Failed to start Pipulate: {e}{Colors.END}")
        return False

@click.command()
@click.option('--install-name', default=None, help='Custom installation directory name')
@click.option('--force-install', is_flag=True, help='Force fresh installation even if Pipulate exists')
def main(install_name, force_install):
    """
    Pipulate: Local-First AI SEO Software & Digital Workshop
    
    This command will:
    1. Check if Nix is installed (install if needed)
    2. Check if Pipulate is already installed (install if needed)  
    3. Launch Pipulate server
    """
    print_banner()
    
    # Check for existing installation unless forcing fresh install
    pipulate_dir = None
    if not force_install:
        pipulate_dir = find_pipulate_installation()
    
    if pipulate_dir and not force_install:
        print(f"{Colors.GREEN}📂 Found existing Pipulate installation at {pipulate_dir}{Colors.END}")
    else:
        # Check if Nix is installed
        if not check_nix_installed():
            print(f"{Colors.YELLOW}⚠️  Nix is required but not installed.{Colors.END}")
            if click.confirm("Install Nix now?"):
                if install_nix():
                    sys.exit(0)  # Exit so user can restart terminal
                else:
                    sys.exit(1)
            else:
                print(f"{Colors.RED}❌ Nix is required for Pipulate. Exiting.{Colors.END}")
                sys.exit(1)
        
        # Run installation
        pipulate_dir = run_pipulate_installation(install_name or "pipulate")
        if not pipulate_dir:
            sys.exit(1)
    
    # Launch Pipulate
    print(f"{Colors.CYAN}🎯 Your data. Your AI. Your machine. Your control.{Colors.END}")
    run_pipulate_server(pipulate_dir)

if __name__ == "__main__":
    main() 
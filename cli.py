#!/usr/bin/env python3
"""
Pipulate CLI - Beautiful installation and execution interface

Usage:
    pipulate install [app_name]   # Install with optional custom name
    pipulate run [app_name]       # Run existing installation  
    pipulate uninstall [app_name] # Clean uninstall for testing
    pipulate --help               # Show this help
"""

import os
import shutil
import subprocess
import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax

console = Console()

INSTALL_URL = "https://pipulate.com/install.sh"

def check_nix_installed():
    """Check if Nix is installed."""
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        task = progress.add_task(description="Checking for Nix...", total=None)
        try:
            result = subprocess.run(['nix', '--version'], capture_output=True, text=True, check=True, timeout=5)
            progress.stop()
            console.print(f"✅ Nix detected: [bold green]{result.stdout.strip()}[/bold green]")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            progress.stop()
            console.print("❌ Nix not found on your system.", style="yellow")
            return False

def install_nix():
    """Guides the user to install Nix."""
    console.print(Panel(
        "[bold yellow]Nix Package Manager is required.[/bold yellow]\n\nPipulate uses Nix to create a perfect, reproducible environment. This prevents the 'it works on my machine' problem.\n\nPlease run this command to install Nix, then run `pipulate install` again:",
        title="Nix Installation Required",
        border_style="yellow",
        expand=False
    ))
    nix_install_command = "curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install"
    console.print(Syntax(nix_install_command, "bash", theme="monokai", line_numbers=False))
    console.print("\n[bold]After installation, you MUST close and reopen your terminal before running `pipulate install` again.[/bold]")
    sys.exit(1)

def run_install_script(app_name):
    """Downloads and runs the main install.sh script."""
    target_dir = Path.home() / app_name
    if target_dir.exists():
        console.print(f"🗑️  Removing existing installation at [bold yellow]{target_dir}[/bold yellow] to ensure a clean install.")
        shutil.rmtree(target_dir)

    console.print(f"📦 Installing Pipulate into [cyan]~/{app_name}[/cyan]...")
    command = f"curl -L {INSTALL_URL} | sh -s {app_name}"

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="Running installer...", total=None)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        _, stderr = process.communicate()

    if process.returncode != 0:
        console.print(f"❌ Installation failed.", style="bold red")
        console.print(Panel(stderr, title="Error Details", border_style="red"))
        sys.exit(1)

    console.print(f"✅ Installation complete!")
    return target_dir

def run_pipulate(app_name):
    """Runs an existing Pipulate installation."""
    target_dir = Path.home() / app_name
    if not (target_dir.exists() and (target_dir / "flake.nix").is_file()):
        console.print(f"❌ No Pipulate installation found at [cyan]~/{app_name}[/cyan].")
        console.print(f"To install, run: [bold]pipulate install {app_name}[/bold]")
        sys.exit(1)

    console.print(f"🚀 Launching Pipulate from [cyan]{target_dir}[/cyan]...")
    try:
        os.chdir(target_dir)
        os.execvp("nix", ["nix", "develop"])
    except FileNotFoundError:
        console.print("❌ [bold red]Error: `nix` command not found.[/bold red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ An unexpected error occurred while launching: {e}", style="bold red")
        sys.exit(1)

def uninstall_pipulate(app_name):
    """Uninstall a Pipulate installation."""
    target_dir = Path.home() / app_name
    if not target_dir.exists():
        console.print(f"ℹ️  No installation found at [cyan]~/{app_name}[/cyan]. Nothing to do.")
        return

    if console.input(f"⚠️ This will permanently delete [bold red]{target_dir}[/bold red] and all its data. Continue? (y/N) ").lower() != 'y':
        console.print("❌ Uninstall cancelled.")
        return

    shutil.rmtree(target_dir)
    console.print(f"✅ Successfully uninstalled from [green]{target_dir}[/green].")

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Pipulate CLI - Installation and execution helper.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    # This setup makes 'install' the default if no command is given
    parser.add_argument("command", nargs="?", default="install", choices=['install', 'run', 'uninstall'],
                        help="The command to execute (defaults to 'install').")
    parser.add_argument("app_name", nargs="?", default="pipulate",
                        help="A custom name for the installation directory (e.g., 'mybotify'). Defaults to 'pipulate'.")

    args = parser.parse_args()

    console.print(Panel("🚀 [bold cyan]Pipulate :: The Local-First AI SEO & Automation Workshop[/bold cyan] 🚀", border_style="cyan"))

    if args.command == 'install':
        if not check_nix_installed():
            install_nix()
        run_install_script(args.app_name)
        console.print("\n✨ [bold]Setup is complete![/bold] Launching Pipulate for the first time...")
        console.print("[italic](This may take a few minutes as it builds the environment.)[/italic]")
        run_pipulate(args.app_name)

    elif args.command == 'run':
        run_pipulate(args.app_name)

    elif args.command == 'uninstall':
        uninstall_pipulate(args.app_name)

if __name__ == "__main__":
    main() 
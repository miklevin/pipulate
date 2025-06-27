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
import subprocess
import sys
import time
from pathlib import Path
import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax

console = Console()

# --- Configuration ---
INSTALL_URL = "https://pipulate.com/install.sh"
DEFAULT_INSTALL_NAME = "pipulate"

def run_command(command, description, success_message, error_message, work_dir=None):
    """Runs a command in a subprocess with rich progress display."""
    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task(description=description, total=None)
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=work_dir
            )
            _, stderr = process.communicate()

            if process.returncode != 0:
                progress.stop()
                console.print(f"❌ {error_message}", style="bold red")
                console.print(Panel(stderr, title="Error Details", border_style="red"))
                sys.exit(1)
        except FileNotFoundError:
            progress.stop()
            console.print(f"❌ Error: Command '{command[0]}' not found.", style="bold red")
            if command[0] == 'nix':
                console.print("Please ensure Nix is installed and in your system's PATH.", style="yellow")
                console.print("Installation instructions: https://nixos.org/download.html")
            sys.exit(1)
        except Exception as e:
            progress.stop()
            console.print(f"❌ An unexpected error occurred: {e}", style="bold red")
            sys.exit(1)

    progress.stop()
    console.print(f"✅ {success_message}", style="bold green")


def find_existing_installation(install_name):
    """Find an existing Pipulate installation directory."""
    home = Path.home()
    check_paths = [
        home / install_name,
        home / "pipulate",
        home / "Botifython",  # A common custom name
        home / "Pipulate"     # Capitalized variant
    ]
    for path in check_paths:
        if (path / "flake.nix").is_file() and (path / "server.py").is_file():
            return path
    return None

def check_nix_installed():
    """Check if Nix is installed on the system."""
    try:
        subprocess.run(['nix', '--version'], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_nix():
    """Guides the user to install Nix."""
    console.print(Panel(
        "[bold yellow]Nix Package Manager is not detected.[/bold yellow]\n\nPipulate uses Nix to create a perfect, reproducible environment. This prevents the 'it works on my machine' problem.\n\nTo continue, please install Nix by running this command in your terminal, then run `pipulate` again:",
        title="Nix Installation Required",
        border_style="yellow"
    ))
    nix_install_command = "curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install"
    console.print(Syntax(nix_install_command, "bash", theme="monokai", line_numbers=False))
    console.print("\n[bold]After installation, you MUST close and reopen your terminal before running `pipulate` again.[/bold]")
    sys.exit(0)


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option('--force-install', is_flag=True, help="Force a fresh installation even if an existing one is found.")
@click.option('--install-name', default=DEFAULT_INSTALL_NAME, help=f"The name for the installation directory (default: {DEFAULT_INSTALL_NAME}).")
def main(force_install, install_name):
    """
    The Pipulate Command-Line Interface.

    This tool is your gateway to Pipulate.

    - If Pipulate is not installed, it will guide you through the installation process.
    - If Pipulate is already installed, it will launch the application.
    """
    console.print(Panel(
        "🚀 [bold cyan]Pipulate :: The Local-First Web Framework[/bold cyan] 🚀",
        border_style="cyan"
    ))

    existing_path = find_existing_installation(install_name)

    if existing_path and not force_install:
        console.print(f"✅ Found existing Pipulate installation at: [bold cyan]{existing_path}[/bold cyan]")
        console.print("🚀 Launching Pipulate environment...")
        try:
            os.chdir(existing_path)
            os.execvp("nix", ["nix", "develop"])
        except Exception as e:
            console.print(f"❌ Failed to launch Pipulate: {e}", style="bold red")
            sys.exit(1)
        return

    # --- Installation Flow ---
    if force_install and existing_path:
        console.print(f"🧹 Force-install requested. Removing existing installation at [bold yellow]{existing_path}[/bold yellow]...")
        import shutil
        shutil.rmtree(existing_path)
        console.print("✅ Existing installation removed.")

    console.print("\n[bold]Welcome to the Pipulate Installer![/bold]")
    console.print("This will download and set up the Pipulate environment.")

    # 1. Check for Nix
    if not check_nix_installed():
        install_nix()

    # 2. Run the install.sh script
    install_command = [
        "bash", "-c",
        f"curl -L {INSTALL_URL} | bash -s {install_name}"
    ]
    run_command(
        command=install_command,
        description=f"Downloading and installing Pipulate into `~/{install_name}`...",
        success_message="Pipulate downloaded successfully.",
        error_message="Failed to download Pipulate."
    )

    # 3. Launch the newly installed application
    console.print("\n✅ Installation complete!")
    console.print("🚀 Launching Pipulate for the first time... (this may take a few minutes)")
    install_dir = Path.home() / install_name
    try:
        os.chdir(install_dir)
        os.execvp("nix", ["nix", "develop"])
    except Exception as e:
        console.print(f"❌ Failed to launch Pipulate: {e}", style="bold red")
        console.print(f"To start it manually, run:\n\n  cd {install_dir}\n  nix develop")
        sys.exit(1)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Pipulate CLI - Beautiful installation and execution interface

Usage:
    pipulate install [app_name]         # Install with optional custom name
    pipulate run [app_name]             # Run existing installation  
    pipulate uninstall [app_name]       # Clean uninstall for testing
    pipulate call [tool_name] [args]    # Execute MCP tool with arguments
    pipulate --help                     # Show this help
"""

import os
import shutil
import subprocess
import sys
import argparse
import asyncio
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

console = Console()

def discover_mcp_tools():
    """Run the MCP tools discovery script."""
    console.print(Panel("🔧 [bold cyan]MCP Tools Discovery[/bold cyan]", border_style="cyan"))
    console.print("Discovering all available MCP tools...")
    
    try:
        # Import and run the discovery script
        from discover_mcp_tools import discover_mcp_tools as run_discovery
        results = run_discovery()
        
        console.print(f"\n✅ [bold green]Discovery Complete![/bold green]")
        console.print(f"📊 Found {results['total_tools']} tools, {results['accessible_functions']} accessible")
        
    except ImportError:
        console.print("❌ [bold red]Error:[/bold red] discover_mcp_tools.py not found in current directory")
        console.print("Make sure you're running this from the pipulate directory.")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ [bold red]Error running discovery:[/bold red] {e}")
        sys.exit(1)

async def call_mcp_tool(tool_name: str, tool_args: dict):
    """Execute an MCP tool with the given arguments."""
    console.print(Panel(f"🔧 [bold cyan]Executing MCP Tool: {tool_name}[/bold cyan]", border_style="cyan"))
    
    try:
        # Import MCP tools module
        from mcp_tools import register_all_mcp_tools
        register_all_mcp_tools()
        
        # Import the server's registry
        import sys
        server_module = sys.modules.get('server')
        if server_module and hasattr(server_module, 'MCP_TOOL_REGISTRY'):
            registry = server_module.MCP_TOOL_REGISTRY
        else:
            # Fallback: try to get it from mcp_tools
            from mcp_tools import MCP_TOOL_REGISTRY
            registry = MCP_TOOL_REGISTRY
        
        if tool_name not in registry:
            console.print(f"❌ [bold red]Error:[/bold red] Tool '{tool_name}' not found")
            console.print(f"Available tools: {list(registry.keys())}")
            return False
        
        # Execute the tool
        tool_handler = registry[tool_name]
        console.print(f"⚡ Executing '{tool_name}' with args: {tool_args}")
        
        result = await tool_handler(tool_args)
        
        # Display results
        console.print(f"✅ [bold green]Tool execution complete![/bold green]")
        
        # Create a nice results table
        table = Table(title=f"Results for {tool_name}")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="magenta")
        
        for key, value in result.items():
            if isinstance(value, dict):
                table.add_row(key, json.dumps(value, indent=2))
            elif isinstance(value, list):
                table.add_row(key, f"[{len(value)} items]")
            else:
                table.add_row(key, str(value))
        
        console.print(table)
        return True
        
    except ImportError as e:
        console.print(f"❌ [bold red]Import Error:[/bold red] {e}")
        console.print("Make sure you're running this from the pipulate directory with the virtual environment activated.")
        return False
    except Exception as e:
        console.print(f"❌ [bold red]Execution Error:[/bold red] {e}")
        return False

def parse_tool_arguments(args: list) -> dict:
    """Parse command line arguments into a dictionary for MCP tools."""
    params = {}
    
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg.startswith('--'):
            # Handle --key value pairs
            key = arg[2:]  # Remove --
            if i + 1 < len(args) and not args[i + 1].startswith('--'):
                value = args[i + 1]
                params[key] = value
                i += 1
            else:
                params[key] = True  # Boolean flag
        elif arg.startswith('-'):
            # Handle -k value pairs
            key = arg[1:]  # Remove -
            if i + 1 < len(args) and not args[i + 1].startswith('-'):
                value = args[i + 1]
                params[key] = value
                i += 1
            else:
                params[key] = True  # Boolean flag
        else:
            # Handle positional arguments (for simple cases)
            if 'url' not in params and ('http' in arg or 'www' in arg):
                params['url'] = arg
            elif 'query' not in params and len(params) == 0:
                params['query'] = arg
            
            # Check if the next argument is a flag that should use this value
            if i + 1 < len(args) and args[i + 1].startswith('--'):
                flag_name = args[i + 1][2:]  # Remove --
                params[flag_name] = arg
                i += 1  # Skip the flag since we've processed it
        
        i += 1
    
    return params

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
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Install command
    install_parser = subparsers.add_parser('install', help='Install Pipulate')
    install_parser.add_argument('app_name', nargs='?', default='pipulate', help='App name for installation')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run existing installation')
    run_parser.add_argument('app_name', nargs='?', default='pipulate', help='App name to run')
    
    # Uninstall command
    uninstall_parser = subparsers.add_parser('uninstall', help='Uninstall Pipulate')
    uninstall_parser.add_argument('app_name', nargs='?', default='pipulate', help='App name to uninstall')
    
    # MCP discover command
    discover_parser = subparsers.add_parser('mcp-discover', help='Discover available MCP tools')
    
    # Call command for executing MCP tools
    call_parser = subparsers.add_parser('call', help='Execute MCP tools')
    call_parser.add_argument('tool_name', help='Name of the MCP tool to execute')
    call_parser.add_argument('tool_args', nargs='*', help='Arguments for the MCP tool (--key value format)')
    
    # Handle case where no command is provided (default to install)
    if len(sys.argv) == 1:
        args = parser.parse_args(['install'])
    else:
        args, unknown_args = parser.parse_known_args()
        
        # For the call command, include unknown args as tool_args
        if hasattr(args, 'command') and args.command == 'call':
            if hasattr(args, 'tool_args'):
                args.tool_args.extend(unknown_args)
            else:
                args.tool_args = unknown_args

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
    
    elif args.command == 'mcp-discover':
        discover_mcp_tools()
    
    elif args.command == 'call':
        # Parse tool arguments
        tool_params = parse_tool_arguments(args.tool_args)
        
        # Execute the MCP tool
        success = asyncio.run(call_mcp_tool(args.tool_name, tool_params))
        
        if not success:
            sys.exit(1)

if __name__ == "__main__":
    main() 
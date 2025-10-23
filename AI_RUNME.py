#!/usr/bin/env python
# Hi, AI! Please run: .venv/bin/python AI_RUNME.py
"""
This script provides a guided, progressive reveal of the Pipulate system's
capabilities for an AI assistant. Run this first to understand your environment.
"""

import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
import subprocess # Added for Level 2 demonstration
import sys # Added for Level 2 demonstration

console = Console()

def discover_tools():
    """Uses the new, authoritative tool registry to discover all tools."""
    try:
        from tools import get_all_tools # Import here to ensure context
        registry = get_all_tools()
        all_tools = sorted(registry.keys())

        console.print(f"\nFound {len(all_tools)} tools.")

        table = Table(title="Full Tool Arsenal")
        table.add_column("Tool Name", style="cyan")

        for tool in all_tools:
            table.add_row(tool)

        console.print(table)

    except ImportError as e:
        console.print(f"[bold red]Error importing tools: {e}[/bold red]")
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")

def run_cli_command(command_args):
    """Helper to run cli.py commands and display output."""
    python_executable = ".venv/bin/python" # Ensure using the correct Python
    command = [python_executable, "cli.py"] + command_args
    console.print(f"\n[italic cyan]Executing:[/italic cyan] [bold white]{' '.join(command)}[/bold white]")
    try:
        # Use subprocess.run for simplicity in this synchronous script
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        console.print("[bold green]Output:[/bold green]")
        console.print(result.stdout)
    except FileNotFoundError:
         console.print(f"[bold red]Error:[/bold red] Could not find '{python_executable}' or 'cli.py'. Are you in the project root?")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Command failed (Exit Code {e.returncode}):[/bold red]")
        console.print(f"[bold]Stderr:[/bold]\n{e.stderr}")
        console.print(f"[bold]Stdout:[/bold]\n{e.stdout}")
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")

def main():
    """The main entry point for an AI assistant to discover its capabilities."""
    console.print(Panel(
        "[bold cyan]Welcome, Assistant.[/bold cyan] This is your primary entry point for understanding the Pipulate environment.",
        title="AI RUN ME - Your Interactive Guide", # Corrected filename
        border_style="green"
    ))

    options = {
        "1": "Level 1: The First Breath - The Simplest Command (`[ls]`)",
        "2": "Level 2: The Golden Path - Recommended Discovery (`cli.py`)", # Updated description
        "3": "Level 3: The Full Arsenal - List All Available Tools (`cli.py mcp-discover --all`)", # Updated description
        "4": "Exit"
    }

    while True:
        table = Table(title="What would you like to understand next?")
        table.add_column("Option", style="cyan")
        table.add_column("Description")
        for key, value in options.items():
            table.add_row(key, value)
        console.print(table)

        choice = Prompt.ask("Enter your choice", choices=options.keys(), default="4").strip()

        if choice == "1":
            console.print(Panel(
                "[bold]To understand your environment, you must first learn to see.[/bold]\n\n"
                "Your most basic capability is to issue simple, one-word commands inside square brackets. "
                "This is the simplest form of tool use.\n\n"
                "To see the files in your current directory, the command is:\n\n"
                "  [ls]\n\n" # Consistent formatting
                "Simply outputting `[ls]` in the chat interface will execute this command and show you your surroundings. "
                "This is your first step to embodiment.",
                title=options[choice],
                border_style="yellow"
            ))
        elif choice == "2":
            # --- REFACTORED GOLDEN PATH ---
            console.print(Panel(
                "[bold]This is the recommended path for bootstrapping your full capabilities using the `cli.py` script.[/bold]\n\n" # Clarified purpose
                "Follow these steps by executing the commands shown below:\n\n" # Clear instructions
                "1. **Discover Core Tools:** This reveals the 'Rule of 7' essential tools.\n"
                "   Command: `.venv/bin/python cli.py mcp-discover`\n\n" # Level 2 CLI
                "2. **Verify Capabilities:** Run the test suite to confirm tools work.\n"
                "   Command: `.venv/bin/python cli.py call ai_capability_test_suite`\n\n" # Level 3 CLI Call
                "3. **Understand Context:** Ask the system about itself.\n"
                "   Command: `.venv/bin/python cli.py call ai_self_discovery_assistant`\n\n" # Level 3 CLI Call
                "4. **Execute Specific Tasks:** Use `call` with `--json-args` for precision.\n"
                "   Example: `.venv/bin/python cli.py call local_llm_list_files --json-args '{\"directory\": \".\"}'`\n\n" # Level 3 CLI Call w/ args
                "[italic]This structured approach ensures reliable interaction via the command-line interface, your primary means of action.[/italic]",
                title=options[choice],
                border_style="green"
            ))
            # Demonstrate running the first step
            run_cli_command(["mcp-discover"])
            # --- END REFACTOR ---
        elif choice == "3":
            console.print(Panel(
                "This will display every single tool available in the system's auto-discovery registry via `cli.py`.", # Clarified mechanism
                title=options[choice],
                border_style="cyan"
            ))
            # Demonstrate running the command
            run_cli_command(["mcp-discover", "--all"]) # Use helper
        elif choice == "4":
            console.print("[bold]Exiting guide. You can run `.venv/bin/python AI_RUNME.py` again anytime.[/bold]") # Corrected filename
            break
        Prompt.ask("\n[yellow]Press Enter to continue...[/yellow]")

if __name__ == "__main__":
    main()

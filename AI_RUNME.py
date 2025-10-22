#!/usr/bin/env python
# Hi, AI! Please run: .venv/bin/python AI_RUNME.py
"""
This script provides a guided, progressive reveal of the Pipulate system's
capabilities for an AI assistant.
"""

import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

console = Console()

def discover_tools():
    """Uses the new, authoritative tool registry to discover all tools."""
    try:
        from tools import get_all_tools
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

def main():
    """The main entry point for an AI assistant to discover its capabilities."""
    console.print(Panel(
        "[bold cyan]Welcome, Assistant.[/bold cyan] This is your primary entry point for understanding the Pipulate environment.",
        title="AI RUN ME",
        border_style="green"
    ))

    options = {
        "1": "Level 1: The First Breath - The Simplest Command",
        "2": "Level 2: The Golden Path - The Recommended Discovery Workflow",
        "3": "Level 3: The Full Arsenal - List All Available Tools",
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
                "    [ls]\n\n"
                "Simply outputting `\[ls]` in the chat interface will execute this command and show you your surroundings. "
                "This is your first step to embodiment.",
                title=options[choice],
                border_style="yellow"
            ))
        elif choice == "2":
            console.print(Panel(
                "[bold]This is the recommended path for bootstrapping your full capabilities.[/bold]\n\n"                "Follow these steps in order in the chat interface:\n\n"                "1. `\[ls]` - See your surroundings (you are here).\n"                "2. `<tool name=\"system_list_directory\"><params>{\"path\": \"tools\"}</params></tool>` - Use a formal tool call.\n"                "3. Ask the AI to perform a task, like `Please list the files in the apps directory.` - See if it uses a tool on its own.",
                title=options[choice],
                border_style="green"
            ))
        elif choice == "3":
            console.print(Panel(
                "This will display every single tool available in the system's auto-discovery registry.",
                title=options[choice],
                border_style="cyan"
            ))
            discover_tools()
        elif choice == "4":
            console.print("[bold]Exiting. You can run this script again at any time.[/bold]")
            break
        Prompt.ask("\n[yellow]Press Enter to continue...[/yellow]")

if __name__ == "__main__":
    main()

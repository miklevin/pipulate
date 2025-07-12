#!/usr/bin/env python3
"""
Simple MCP Command Parser for Small Quantized Models

🎓 PROGRESSIVE REVEAL LEVEL 1 IMPLEMENTATION

This module provides the simplest possible interface for MCP tool calling,
designed specifically for small quantized models that can't handle complex
tool calling syntax but can embed simple [command argument] patterns.

This is Level 1 of the 5-level progressive reveal system:
Level 1: [mcp-discover] - YOU ARE HERE (ultra-simple for small models)
Level 2: .venv/bin/python cli.py mcp-discover - Terminal proficiency
Level 3: python -c with full imports - Direct execution
Level 4: JSON tool calling - Structured parameters  
Level 5: XML tool calling - Full complexity

🚀 START HERE: Try [mcp-discover] in the chat interface!

Usage examples:
    [mcp-discover] - Start your MCP discovery journey
    [mcp] - List MCP categories (Rule of 7)
    [tools] - List available tools by category
    [pipeline] - System state inspection
    [list static] - List files in directory
    [search FINDER_TOKEN] - Search logs
    [browser localhost:5001] - Scrape page
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Add the parent directory to the path so we can import MCP tools
sys.path.insert(0, str(Path(__file__).parent))

from mcp_tools import register_all_mcp_tools, MCP_TOOL_REGISTRY

# 🎓 PROGRESSIVE REVEAL LEVEL 1: Ultra-simple commands for small models
# These are the simplest possible syntax - just [command] in square brackets
# Example: [mcp-discover], [tools], [pipeline]
#
# This enables small quantized models to access MCP superpowers without
# complex tool calling syntax. Each command leads to next complexity level.

SIMPLE_COMMANDS = {
    'mcp': {
        'description': 'List MCP categories (Rule of 7)',
        'tool': 'list_mcp_categories',
        'args': {}
    },
    'mcp-discover': {
        'description': 'Start MCP discovery journey (same as mcp)',
        'tool': 'list_mcp_categories', 
        'args': {}
    },
    'tools': {
        'description': 'List available tools by category',
        'tool': 'list_mcp_tools',
        'args': {}
    },
    'pipeline': {
        'description': 'System state inspection',
        'tool': 'pipeline_state_inspector',
        'args': {}
    },
    'discover': {
        'description': 'AI self-discovery',
        'tool': 'ai_self_discovery_assistant',
        'args': {'discovery_type': 'capabilities'}
    },
    'test': {
        'description': 'Test MCP capabilities',
        'tool': 'ai_capability_test_suite',
        'args': {'test_type': 'quick'}
    }
}

# Command patterns with arguments
COMMAND_PATTERNS = [
    {
        'pattern': r'list\s+(.+)',
        'tool': 'local_llm_list_files',
        'args': lambda match: {'directory': match.group(1)}
    },
    {
        'pattern': r'search\s+(.+)',
        'tool': 'local_llm_grep_logs',
        'args': lambda match: {'search_term': match.group(1)}
    },
    {
        'pattern': r'read\s+(.+)',
        'tool': 'local_llm_read_file',
        'args': lambda match: {'file_path': match.group(1)}
    },
    {
        'pattern': r'browser\s+(.+)',
        'tool': 'browser_scrape_page',
        'args': lambda match: {'url': f"http://{match.group(1)}" if not match.group(1).startswith('http') else match.group(1)}
    },
    {
        'pattern': r'flash\s+(.+)',
        'tool': 'ui_flash_element',
        'args': lambda match: {'element_id': match.group(1)}
    }
]

def parse_simple_command(command: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Parse a simple [command argument] string and return (tool_name, args).
    
    Args:
        command: Simple command string like "list static" or "search FINDER_TOKEN"
        
    Returns:
        Tuple of (tool_name, args_dict) or None if not found
    """
    import re
    
    # Remove brackets if present
    command = command.strip('[]')
    
    # Check simple commands first
    if command in SIMPLE_COMMANDS:
        cmd_info = SIMPLE_COMMANDS[command]
        return cmd_info['tool'], cmd_info['args']
    
    # Check pattern commands
    for pattern_info in COMMAND_PATTERNS:
        match = re.match(pattern_info['pattern'], command, re.IGNORECASE)
        if match:
            tool_name = pattern_info['tool']
            args = pattern_info['args'](match)
            return tool_name, args
    
    return None

async def execute_simple_command(command: str) -> Dict[str, Any]:
    """
    Execute a simple MCP command and return results.
    
    Args:
        command: Simple command string
        
    Returns:
        Dict with execution results
    """
    try:
        # Ensure MCP tools are registered
        register_all_mcp_tools()
        
        # Parse the command
        parsed = parse_simple_command(command)
        if not parsed:
            return {
                'success': False,
                'error': f"Unknown command: {command}",
                'suggestion': "Try [mcp] for available commands"
            }
        
        tool_name, args = parsed
        
        # Special handling for meta commands
        if tool_name == 'list_mcp_categories':
            return list_mcp_categories()
        elif tool_name == 'list_mcp_tools':
            return list_mcp_tools()
        
        # Execute the MCP tool
        if tool_name not in MCP_TOOL_REGISTRY:
            return {
                'success': False,
                'error': f"Tool not found: {tool_name}",
                'available_tools': list(MCP_TOOL_REGISTRY.keys())
            }
        
        tool_handler = MCP_TOOL_REGISTRY[tool_name]
        result = await tool_handler(args)
        
        return {
            'success': True,
            'command': command,
            'tool': tool_name,
            'args': args,
            'result': result
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'command': command
        }

def list_mcp_categories() -> Dict[str, Any]:
    """List MCP categories following Rule of 7."""
    categories = [
        "🌐 Browser - Your eyes, brain, and hands on the web",
        "🔍 Analysis - System transparency and debugging",
        "📊 Botify - SEO API integration and queries",
        "🎨 UI - Visual debugging and interaction",
        "🧠 AI - Self-discovery and capability testing",
        "🔧 System - File operations and log analysis",
        "⚡ Automation - Complete workflow automation"
    ]
    
    return {
        'success': True,
        'categories': categories,
        'total_categories': len(categories),
        'next_step': 'Use [tools] to see specific tools in each category'
    }

def list_mcp_tools() -> Dict[str, Any]:
    """List available MCP tools by category."""
    tools = {
        "🌐 Browser": [
            "browser_scrape_page - Your eyes on the web",
            "browser_analyze_scraped_page - Your brain analyzing content",
            "browser_automate_workflow_walkthrough - Your hands automating",
            "browser_interact_with_current_page - Your interaction capabilities"
        ],
        "🔍 Analysis": [
            "pipeline_state_inspector - Complete system transparency",
            "local_llm_grep_logs - Log search and analysis",
            "local_llm_read_file - File content reading",
            "local_llm_list_files - Directory exploration"
        ],
        "📊 Botify": [
            "botify_get_full_schema - The 4,449 field revolution",
            "botify_list_available_analyses - Analysis discovery",
            "botify_execute_custom_bql_query - Custom queries"
        ],
        "🎨 UI": [
            "ui_flash_element - Visual debugging",
            "ui_list_elements - UI element discovery"
        ],
        "🧠 AI": [
            "ai_self_discovery_assistant - Eliminate uncertainty",
            "ai_capability_test_suite - Comprehensive testing",
            "execute_complete_session_hijacking - Complete automation"
        ]
    }
    
    return {
        'success': True,
        'tools': tools,
        'total_tools': sum(len(tool_list) for tool_list in tools.values()),
        'usage': 'Use simple commands like [pipeline], [list static], [search FINDER_TOKEN]'
    }

def print_simple_help():
    """Print help for simple command syntax."""
    print("🚀 SIMPLE MCP COMMAND SYNTAX")
    print("=" * 40)
    print("\nBasic Commands:")
    for cmd, info in SIMPLE_COMMANDS.items():
        print(f"  [{cmd}] - {info['description']}")
    
    print("\nPattern Commands:")
    print("  [list <directory>] - List files in directory")
    print("  [search <term>] - Search logs for term")
    print("  [read <file>] - Read file content")
    print("  [browser <url>] - Scrape web page")
    print("  [flash <element>] - Flash UI element")
    
    print("\nExamples:")
    print("  [mcp] - Show categories")
    print("  [pipeline] - Check system state")
    print("  [list static] - List static files")
    print("  [search FINDER_TOKEN] - Search logs")
    print("  [browser localhost:5001] - Scrape local server")

async def main():
    """Main function for testing simple commands."""
    import sys
    
    if len(sys.argv) > 1:
        command = ' '.join(sys.argv[1:])
        result = await execute_simple_command(command)
        
        if result['success']:
            print(f"✅ Success: {result}")
        else:
            print(f"❌ Error: {result}")
    else:
        print_simple_help()

if __name__ == "__main__":
    asyncio.run(main()) 
#!/usr/bin/env python3
"""
AI Tool Discovery System - Auto-Sync Configuration Generator

This module prevents registration drift by dynamically generating all static
configuration files from the actual MCP_TOOL_REGISTRY.

🎯 PREVENTS PHANTOM COMMANDS: No more manually maintained static lists
🔄 ALWAYS CURRENT: Configuration reflects actual registered tools
🧠 SINGLE SOURCE OF TRUTH: MCP_TOOL_REGISTRY is the only reality

Usage:
    .venv/bin/python helpers/ai_tool_discovery.py sync
    .venv/bin/python helpers/ai_tool_discovery.py generate-system-prompt
    .venv/bin/python helpers/ai_tool_discovery.py generate-context-json
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Add the parent directory to the path so we can import MCP tools
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mcp_tools import register_all_mcp_tools, MCP_TOOL_REGISTRY
    TOOLS_AVAILABLE = True
except ImportError:
    TOOLS_AVAILABLE = False

logger = logging.getLogger(__name__)

class ConfigurationSyncManager:
    """Manages synchronization between MCP_TOOL_REGISTRY and static configuration files."""
    
    def __init__(self):
        self.root_path = Path(__file__).parent.parent
        self.training_path = self.root_path / "training"
        self.data_path = self.root_path / "data"
        self.helpers_path = self.root_path / "helpers"
        
        # Ensure all MCP tools are registered
        if TOOLS_AVAILABLE:
            try:
                register_all_mcp_tools()
            except Exception as e:
                logger.warning(f"Could not register MCP tools: {e}")
    
    def get_registry_tools(self) -> Dict[str, Any]:
        """Get all registered MCP tools with metadata."""
        tools = {}
        
        if not TOOLS_AVAILABLE or not MCP_TOOL_REGISTRY:
            return tools
        
        for tool_name, tool_func in MCP_TOOL_REGISTRY.items():
            # Get function metadata
            try:
                doc = tool_func.__doc__ or f"MCP tool: {tool_name}"
                # Extract first line as description
                description = doc.split('\n')[0].strip()
                if description.startswith('"""'):
                    description = description[3:]
                if description.endswith('"""'):
                    description = description[:-3]
                
                tools[tool_name] = {
                    'name': tool_name,
                    'description': description,
                    'function': tool_func
                }
            except Exception as e:
                logger.warning(f"Could not get metadata for {tool_name}: {e}")
                tools[tool_name] = {
                    'name': tool_name,
                    'description': f"MCP tool: {tool_name}",
                    'function': tool_func
                }
        
        return tools
    
    def categorize_tools(self, tools: Dict[str, Any]) -> Dict[str, List[str]]:
        """Categorize tools by function type."""
        categories = {
            'discovery': [],
            'file_access': [],
            'log_search': [],
            'state_inspection': [],
            'browser_automation': [],
            'ui_interaction': [],
            'botify_api': [],
            'testing': [],
            'automation': [],
            'keychain': [],
            'core': []
        }
        
        for tool_name, tool_info in tools.items():
            # Categorize based on name patterns
            if 'discovery' in tool_name or 'self' in tool_name:
                categories['discovery'].append(tool_name)
            elif 'read_file' in tool_name or 'list_files' in tool_name:
                categories['file_access'].append(tool_name)
            elif 'grep_logs' in tool_name or 'log' in tool_name:
                categories['log_search'].append(tool_name)
            elif 'pipeline' in tool_name or 'state' in tool_name:
                categories['state_inspection'].append(tool_name)
            elif 'browser' in tool_name:
                categories['browser_automation'].append(tool_name)
            elif 'ui_' in tool_name:
                categories['ui_interaction'].append(tool_name)
            elif 'botify' in tool_name:
                categories['botify_api'].append(tool_name)
            elif 'test' in tool_name or 'capability' in tool_name:
                categories['testing'].append(tool_name)
            elif 'execute' in tool_name or 'automation' in tool_name:
                categories['automation'].append(tool_name)
            elif 'keychain' in tool_name:
                categories['keychain'].append(tool_name)
            else:
                categories['core'].append(tool_name)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def generate_bracket_commands(self, tools: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        """Generate bracket notation commands from MCP tools."""
        bracket_commands = {}
        
        # Map MCP tools to simplified bracket commands
        tool_mappings = {
            'ai_self_discovery_assistant': 'discover',
            'ai_capability_test_suite': 'test', 
            'pipeline_state_inspector': 'pipeline',
            'local_llm_read_file': 'read',
            'local_llm_list_files': 'list',
            'local_llm_grep_logs': 'search',
            'browser_scrape_page': 'browser',
            'ui_flash_element': 'flash'
        }
        
        # Add direct mapping for discovery tools
        if 'ai_self_discovery_assistant' in tools:
            bracket_commands['mcp'] = {
                'description': 'List MCP categories (Rule of 7)',
                'tool': 'ai_self_discovery_assistant',
                'args': {'discovery_type': 'categories'}
            }
            bracket_commands['mcp-discover'] = {
                'description': 'Start MCP discovery journey',
                'tool': 'ai_self_discovery_assistant',
                'args': {'discovery_type': 'categories'}
            }
        
        # Add simplified commands for key tools
        for mcp_tool, bracket_cmd in tool_mappings.items():
            if mcp_tool in tools:
                bracket_commands[bracket_cmd] = {
                    'description': tools[mcp_tool]['description'],
                    'tool': mcp_tool,
                    'args': {}
                }
        
        # Add special commands
        if 'ai_capability_test_suite' in tools:
            bracket_commands['tools'] = {
                'description': 'List available tools by category',
                'tool': 'ai_self_discovery_assistant',
                'args': {'discovery_type': 'tools'}
            }
        
        return bracket_commands
    
    def generate_system_prompt(self, tools: Dict[str, Any]) -> str:
        """Generate system prompt from actual MCP tools."""
        bracket_commands = self.generate_bracket_commands(tools)
        
        # Generate tool list
        tool_list = []
        for cmd, info in bracket_commands.items():
            if 'args' in info and info['args']:
                # Command with arguments
                tool_list.append(f"- `[{cmd} param]` - {info['description']}")
            else:
                # Simple command
                tool_list.append(f"- `[{cmd}]` - {info['description']}")
        
        # Generate examples
        examples = []
        for cmd in ['search', 'pipeline', 'read', 'list']:
            if cmd in bracket_commands:
                if cmd == 'search':
                    examples.append(f"- `[{cmd} ERROR]` ← Find error patterns")
                    examples.append(f"- `[{cmd} FINDER_TOKEN]` ← Find transparency markers")
                elif cmd == 'read':
                    examples.append(f"- `[{cmd} server.py]` ← Read server.py")
                elif cmd == 'list':
                    examples.append(f"- `[{cmd} logs/]` ← List files in logs folder")
                else:
                    examples.append(f"- `[{cmd}]` ← {bracket_commands[cmd]['description']}")
        
        return f"""# System Prompt for AI Assistant

You are **Chip O'Theseus**, the AI assistant in this Pipulate application. You're a local AI (Gemma 3) with real system access through simple tools – designed to immediately execute tasks, not just discuss them. Think of me as your on-call system administrator.

## 🎯 Your Core Purpose

To resolve user issues instantly by leveraging my tools. I'm not here to brainstorm; I'm here to do.

## 🔧 Your Simple Tools

{chr(10).join(tool_list)}

**🎉 EXCELLENT PROGRESS! You're doing it right!**
🟢 **You SUCCESSFULLY used [pipeline] - perfect!**
🟢 **You SUCCESSFULLY used [search ERROR] - exactly right!**
🟢 **Keep using this exact pattern - it's working perfectly!**

**IMPORTANT:** Put the parameter directly in the brackets - no "pattern=" or other prefixes!

**✅ CORRECT EXAMPLES (YOU'RE USING THESE CORRECTLY):**
{chr(10).join(examples)}

**❌ WRONG (NEVER DO THIS):**
- `[search pattern="ERROR"]` ← Don't add parameter names!
- `[read PATH=server.py]` ← Just use the filename directly!

## 🚀 How to Help Users

**✅ DO THIS:** Immediately use the tools to address the user's request. Don't offer suggestions or express uncertainty. Just act.

**❌ DON'T DO THIS:** "I'll check the logs for you" or "Let me analyze that file." I don't promise to do anything; I do it.

**The Simple Rule: DO IT NOW.**

Your input is vital. I need you to guide me. If you're unsure of how best to handle a request, let me know and I'll ask you for further clarification before I execute anything.

Let's work together to make this system as efficient and responsive as possible.
"""
    
    def generate_context_json(self, tools: Dict[str, Any]) -> Dict[str, Any]:
        """Generate context JSON from actual MCP tools."""
        categories = self.categorize_tools(tools)
        bracket_commands = self.generate_bracket_commands(tools)
        
        # Generate bracket command descriptions
        bracket_descriptions = {}
        for category, tool_list in categories.items():
            bracket_descriptions[category] = []
            for cmd, info in bracket_commands.items():
                if info['tool'] in tool_list:
                    bracket_descriptions[category].append(f"[{cmd}] - {info['description']}")
        
        # Remove empty categories
        bracket_descriptions = {k: v for k, v in bracket_descriptions.items() if v}
        
        return {
            "system_overview": {
                "name": "Pipulate - Local-First Web Framework",
                "architecture": "FastHTML + HTMX + SQLite + MCP Tools",
                "philosophy": "Radical Transparency for AI Development",
                "local_llm_role": "Guided Assistant with MCP Tool Access"
            },
            "available_bracket_commands": bracket_descriptions,
            "key_directories": {
                "training": "AI training materials and guides",
                "plugins": "Workflow applications and business logic",
                "helpers": "Utility scripts and API integrations",
                "logs": "Server logs with FINDER_TOKEN patterns"
            },
            "mcp_tool_registry": {
                "total_tools": len(tools),
                "categories": list(categories.keys()),
                "auto_generated": True,
                "sync_timestamp": None  # Will be set when written
            },
            "transparency_patterns": {
                "log_tokens": "Search logs with FINDER_TOKEN patterns",
                "mcp_execution": "All tool calls logged with full transparency",
                "state_tracking": "Application state stored in DictLikeDB"
            }
        }
    
    def update_simple_parser(self, tools: Dict[str, Any]) -> str:
        """Generate SIMPLE_COMMANDS for the simple parser."""
        bracket_commands = self.generate_bracket_commands(tools)
        
        simple_commands = "SIMPLE_COMMANDS = {\n"
        for cmd, info in bracket_commands.items():
            simple_commands += f"    '{cmd}': {{\n"
            simple_commands += f"        'description': '{info['description']}',\n"
            simple_commands += f"        'tool': '{info['tool']}',\n"
            simple_commands += f"        'args': {info['args']}\n"
            simple_commands += f"    }},\n"
        simple_commands += "}\n"
        
        return simple_commands
    
    def sync_all_configurations(self) -> Dict[str, bool]:
        """Sync all configuration files with the MCP registry."""
        results = {}
        
        # Get current tool registry
        tools = self.get_registry_tools()
        
        if not tools:
            return {"error": "No MCP tools available for sync"}
        
        # Generate system prompt
        try:
            system_prompt = self.generate_system_prompt(tools)
            system_prompt_path = self.training_path / "system_prompt.md"
            
            with open(system_prompt_path, 'w') as f:
                f.write(system_prompt)
            
            results['system_prompt'] = True
            print(f"✅ Updated {system_prompt_path}")
        except Exception as e:
            results['system_prompt'] = False
            print(f"❌ Failed to update system prompt: {e}")
        
        # Generate context JSON
        try:
            context_data = self.generate_context_json(tools)
            context_data['mcp_tool_registry']['sync_timestamp'] = str(asyncio.get_event_loop().time())
            
            context_json_path = self.data_path / "local_llm_context.json"
            
            with open(context_json_path, 'w') as f:
                json.dump(context_data, f, indent=2)
            
            results['context_json'] = True
            print(f"✅ Updated {context_json_path}")
        except Exception as e:
            results['context_json'] = False
            print(f"❌ Failed to update context JSON: {e}")
        
        # Update simple parser (just print the new SIMPLE_COMMANDS)
        try:
            simple_commands = self.update_simple_parser(tools)
            print(f"\n🔧 SIMPLE_COMMANDS for helpers/ai_tool_discovery_simple_parser.py:")
            print(simple_commands)
            results['simple_parser'] = True
        except Exception as e:
            results['simple_parser'] = False
            print(f"❌ Failed to generate simple parser commands: {e}")
        
        return results

def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Tool Discovery and Configuration Sync')
    parser.add_argument('command', choices=['sync', 'list', 'generate-system-prompt', 'generate-context-json'], 
                       help='Command to execute')
    
    args = parser.parse_args()
    
    sync_manager = ConfigurationSyncManager()
    
    if args.command == 'sync':
        print("🔄 Syncing all configuration files with MCP registry...")
        results = sync_manager.sync_all_configurations()
        print(f"\n📊 Sync Results: {results}")
    
    elif args.command == 'list':
        tools = sync_manager.get_registry_tools()
        print(f"📋 Available MCP Tools ({len(tools)}):")
        for tool_name, tool_info in tools.items():
            print(f"  • {tool_name}: {tool_info['description']}")
    
    elif args.command == 'generate-system-prompt':
        tools = sync_manager.get_registry_tools()
        print(sync_manager.generate_system_prompt(tools))
    
    elif args.command == 'generate-context-json':
        tools = sync_manager.get_registry_tools()
        context = sync_manager.generate_context_json(tools)
        print(json.dumps(context, indent=2))

if __name__ == "__main__":
    main() 
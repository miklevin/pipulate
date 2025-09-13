#!/usr/bin/env python3
"""
MCP Tools Discovery Script - Fixes the broken discovery commands

This script properly discovers and lists all available MCP tools
without requiring the full server context.
"""

import asyncio
import inspect
import sys
import os
from pathlib import Path

def check_environment():
    """Check if we're in the correct environment"""
    print("🔍 ENVIRONMENT CHECK:")
    print(f"  Python executable: {sys.executable}")
    print(f"  Virtual env: {os.environ.get('VIRTUAL_ENV', 'Not detected')}")
    
    # Check if we're using the virtual environment
    # In nix environment, the executable points to nix store, but VIRTUAL_ENV should be set
    if os.environ.get('VIRTUAL_ENV') or '.venv' in sys.executable:
        print("  ✅ Using virtual environment")
        return True
    else:
        print("  ⚠️ Not using virtual environment - may have dependency issues")
        print("  💡 Try: .venv/bin/python discover_tools.py")
        return False

def discover_tools():
    """Discover all MCP tools available in mcp_tools.py"""
    
    # Import the mcp_tools module
    try:
        import tools.mcp_tools as mcp_tools
    except ImportError as e:
        print(f"❌ Error importing mcp_tools: {e}")
        print(f"💡 CRITICAL: You MUST use the virtual environment Python:")
        print(f"   .venv/bin/python discover_tools.py")
        print(f"   The 'python' command points to nix store, not .venv!")
        return {
            'total_tools': 0,
            'accessible_functions': 0,
            'categories': {},
            'error': str(e)
        }
    
    # Get all functions that are MCP tool handlers (test functions and main tools)
    mcp_tools = []
    for name, obj in inspect.getmembers(sys.modules['tools.mcp_tools']):
        if (callable(obj) and 
            not name.startswith('__') and
            ('test_' in name or 'ai_' in name or 'botify_' in name or 'browser_' in name or 
             'ui_' in name or 'local_llm_' in name or 'pipeline_' in name or 'execute_' in name)):
            mcp_tools.append(name)
    
    # Sort tools by category
    categories = {
        'Core Tools': [],
        'Botify API': [],
        'Local LLM': [],
        'Browser Automation': [],
        'UI Interaction': [],
        'AI Discovery': [],
        'Session Hijacking': []
    }
    
    for tool in sorted(mcp_tools):
        if tool in ['builtin_get_cat_fact', 'pipeline_state_inspector']:
            categories['Core Tools'].append(tool)
        elif tool.startswith('botify'):
            categories['Botify API'].append(tool)
        elif tool.startswith('local_llm'):
            categories['Local LLM'].append(tool)
        elif tool.startswith('browser'):
            categories['Browser Automation'].append(tool)
        elif tool.startswith('ui'):
            categories['UI Interaction'].append(tool)
        elif tool.startswith('ai_'):
            categories['AI Discovery'].append(tool)
        elif 'session' in tool.lower() or 'hijacking' in tool.lower() or tool.startswith('execute_'):
            categories['Session Hijacking'].append(tool)
        else:
            categories['Core Tools'].append(tool)
    
    # Print results
    print("🔧 MCP TOOLS DISCOVERY RESULTS")
    print("=" * 50)
    
    total_tools = 0
    for category, tools in categories.items():
        if tools:
            print(f"\n📂 {category} ({len(tools)} tools):")
            for tool in tools:
                # Display the tool name as-is (no underscores to remove)
                print(f"  • {tool}")
            total_tools += len(tools)
    
    print(f"\n🎯 TOTAL TOOLS DISCOVERED: {total_tools}")
    
    # Test if we can access the actual functions
    print(f"\n🧪 FUNCTION ACCESS TEST:")
    accessible_count = 0
    for tool in mcp_tools:
        try:
            func = getattr(sys.modules['tools.mcp_tools'], tool)
            if callable(func):
                accessible_count += 1
                print(f"  ✅ {tool}: Accessible")
            else:
                print(f"  ❌ {tool}: Not callable")
        except Exception as e:
            print(f"  ❌ {tool}: Error - {e}")
    
    print(f"\n🎯 ACCESSIBLE FUNCTIONS: {accessible_count}/{total_tools}")
    
    return {
        'total_tools': total_tools,
        'accessible_functions': accessible_count,
        'categories': categories
    }

def test_tool_registration():
    """Test if tools can be properly registered"""
    print(f"\n🔧 TOOL REGISTRATION TEST:")
    
    try:
        from tools.mcp_tools import register_all_mcp_tools, MCP_TOOL_REGISTRY
        
        # Try to register tools
        register_all_mcp_tools()
        
        # Check if registry exists
        if MCP_TOOL_REGISTRY:
            print(f"  ✅ MCP_TOOL_REGISTRY exists with {len(MCP_TOOL_REGISTRY)} entries")
            return True
        else:
            print(f"  ⚠️ MCP_TOOL_REGISTRY is None (expected when not in server context)")
            return False
            
    except Exception as e:
        print(f"  ❌ Registration failed: {e}")
        return False

def create_working_discovery_commands():
    """Create working discovery commands for the user"""
    print(f"\n💡 WORKING DISCOVERY COMMANDS:")
    print("=" * 50)
    
    print("""
# Command 1: List all MCP tool functions
.venv/bin/python discover_tools.py

# Command 2: Test specific tool (use exact function name)
.venv/bin/python -c "import asyncio; from tools.mcp_tools import test_environment_access; result = asyncio.run(test_environment_access()); print('Environment Test Result:', result)"

# Command 3: Test capability suite (shell-safe)
.venv/bin/python -c "import asyncio; from tools.mcp_tools import ai_capability_test_suite; result = asyncio.run(ai_capability_test_suite({'test_type': 'quick'})); print('Success Rate:', result.get('success_rate', 'N/A'), '%')"

# Command 4: Test self-discovery (shell-safe)
.venv/bin/python -c "import asyncio; from tools.mcp_tools import ai_self_discovery_assistant; result = asyncio.run(ai_self_discovery_assistant({'discovery_type': 'capabilities'})); print('Tools found:', result.get('total_tools_available', 'N/A'))"

# Command 5: Test environment access (no parameters needed)
.venv/bin/python -c "import asyncio; from tools.mcp_tools import test_environment_access; result = asyncio.run(test_environment_access()); print('Environment Test Result:', result)"
""")

if __name__ == "__main__":
    print("🚀 MCP TOOLS DISCOVERY SCRIPT")
    print("=" * 50)
    
    # Check environment first
    env_ok = check_environment()
    
    # Discover tools
    results = discover_tools()
    
    # Test registration
    registration_works = test_tool_registration()
    
    # Create working commands
    create_working_discovery_commands()
    
    print(f"\n✅ DISCOVERY COMPLETE!")
    if 'error' in results:
        print(f"❌ Error: {results['error']}")
        print(f"💡 Fix: Use .venv/bin/python discover_tools.py")
    else:
        print(f"📊 Summary: {results['total_tools']} tools found, {results['accessible_functions']} accessible")
        print(f"🔧 Registration: {'Working' if registration_works else 'Limited (expected)'}") 
"""
Tools package for Pipulate - Focused MCP tool modules

This package contains extracted MCP tools organized by domain for token optimization.
"""

# --- NEW: Proof-of-concept for automatic tool registration ---
AUTO_REGISTERED_TOOLS = {}

def auto_tool(func):
    """Decorator to prove that automatic registration is possible."""
    AUTO_REGISTERED_TOOLS[func.__name__] = func
    return func

# --- NEW: Simple alias registration for bracket commands ---
ALIAS_REGISTRY = {}

def alias(alias_name):
    """Decorator to map a simple [command] to a tool function."""
    def decorator(func):
        ALIAS_REGISTRY[alias_name] = func.__name__
        return func
    return decorator
# --- END NEW ---
# --- END NEW ---

import os
import importlib

# --- NEW: Automatic tool discovery and registration ---
def get_all_tools():
    """
    Dynamically imports all tool modules in this package and returns the
    dictionary of functions decorated with @auto_tool.
    """
    package_name = __name__
    package_path = os.path.dirname(__file__)

    for module_info in os.scandir(package_path):
        if module_info.is_file() and module_info.name.endswith('.py') and not module_info.name.startswith('__'):
            module_name = module_info.name[:-3]
            try:
                importlib.import_module(f".{module_name}", package=package_name)
            except ImportError as e:
                print(f"Could not import tool module: {module_name} - {e}")

    return AUTO_REGISTERED_TOOLS
# --- END NEW ---

__version__ = "1.0.0"

# Import shared constants to eliminate duplication
try:
    from .botify_tools import CORE_BOTIFY_TOOLS
    botify_exports = CORE_BOTIFY_TOOLS + ['get_botify_tools']
except ImportError:
    # Fallback if import fails
    botify_exports = ['get_botify_tools']

__all__ = botify_exports + [
    'execute_complete_session_hijacking',
    'browser_hijack_workflow_complete',
    'execute_automation_recipe',
    'execute_mcp_cli_command',
    'conversation_history_view',
    'conversation_history_clear',
    'get_advanced_automation_tools'
] 

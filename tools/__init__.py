"""
Tools package for Pipulate - Focused MCP tool modules

This package contains extracted MCP tools organized by domain for token optimization.
"""

# Re-export commonly used functions for convenience
try:
    from .botify_mcp_tools import (
        botify_ping,
        botify_list_projects,
        botify_simple_query,
        botify_get_full_schema,
        botify_list_available_analyses,
        botify_execute_custom_bql_query,
        get_botify_tools
    )
except ImportError:
    # If botify_mcp_tools isn't available, that's okay
    pass

try:
    from .advanced_automation_mcp_tools import (
        execute_complete_session_hijacking,
        browser_hijack_workflow_complete,
        execute_automation_recipe,
        execute_mcp_cli_command,
        conversation_history_view,
        conversation_history_clear,
        get_advanced_automation_tools
    )
except ImportError:
    # If advanced_automation_mcp_tools isn't available, that's okay
    pass

__version__ = "1.0.0"
__all__ = [
    'botify_ping',
    'botify_list_projects',
    'botify_simple_query',
    'botify_get_full_schema',
    'botify_list_available_analyses',
    'botify_execute_custom_bql_query',
    'get_botify_tools',
    'execute_complete_session_hijacking',
    'browser_hijack_workflow_complete',
    'execute_automation_recipe',
    'execute_mcp_cli_command',
    'conversation_history_view',
    'conversation_history_clear',
    'get_advanced_automation_tools'
] 
"""
🎯 MCP TOOLS PLAYGROUND

Beautiful, modular MCP tool development environment for regression hunting.
This is where sophisticated AI capabilities are born and tested before 
promotion to the main Pipulate system.

PROGRESSIVE INTELLIGENCE HIERARCHY:

Level 1 (Super-Brain Models):
    from tools import RegressionHunter
    hunter = RegressionHunter()
    result = hunter.find_breaking_commit(days_ago=7, test_pattern="FINDER_TOKEN: FEATURE_XYZ")

Level 2 (Smart Models):  
    from tools.golden_path_api import execute_tool
    result = execute_tool("find_regression", days_ago=7, pattern="FEATURE_XYZ")

Level 3 (Local LLMs):
    hunt_regression 7 FEATURE_XYZ

Philosophy: 
- Keep tools.py focused on orchestration
- Build sophisticated capabilities here
- Promote successful patterns to main system
- Make everything beautiful to read and understand
"""

# Level 1: Full capability imports for super-brain models
from .regression_hunter import RegressionHunter, BugHunt
from .log_analyzer import LogAnalyzer, LogPattern
from .git_time_machine import GitTimeMachine, CommitSnapshot
from .golden_path_api import execute_tool, available_tools, parse_command, get_api_help
from .release_api import ReleaseManager, commit_changes, auto_commit
from .commit_explorer import CommitExplorer, explore_commit, restore_commit
from .branch_manager import BranchManager, create_bughunt_branch, cleanup_branches

# Level 2: Simplified interface for smart models
__all__ = [
    'RegressionHunter',
    'BugHunt', 
    'LogAnalyzer',
    'LogPattern',
    'GitTimeMachine',
    'CommitSnapshot',
    'execute_tool',
    'available_tools',
    'parse_command',
    'get_api_help',
    'ReleaseManager',
    'commit_changes',
    'auto_commit',
    'CommitExplorer',
    'explore_commit',
    'restore_commit',
    'BranchManager',
    'create_bughunt_branch',
    'cleanup_branches'
]

# Level 3: Command signatures for local LLMs (documented for pattern matching)
"""
SIMPLE COMMAND PATTERNS:

hunt_regression <days_ago> <pattern>        # Find when feature broke
analyze_logs <pattern> [since_hours]        # Search log patterns  
check_commit <hash> <test_pattern>          # Test specific commit
list_commits <days_ago>                     # Get commit history
verify_feature <feature_name> [commit]      # Check if feature works

These patterns are detected and routed to appropriate tools.
""" 
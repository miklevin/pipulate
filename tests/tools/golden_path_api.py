#!/usr/bin/env python3
"""
🎯 GOLDEN PATH API: Beautiful Simplicity for All Intelligence Levels

Provides the progressive intelligence hierarchy interface for the MCP tools playground.
Makes sophisticated regression hunting accessible through simple, readable patterns.

DESIGN PHILOSOPHY:
- Level 1: Full power for super-brain models
- Level 2: Simple function calls for smart models  
- Level 3: Command pattern matching for local LLMs

This is the interface layer that makes complex tools beautiful to use.
"""
import re
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

# Import our sophisticated tools
from .regression_hunter import RegressionHunter, hunt_regression
from .release_api import parse_release_command
# Note: Other imports will be added as we create more tools

class GoldenPathAPI:
    """
    🎯 THE GOLDEN PATH API ORCHESTRATOR
    
    Provides beautiful, simple interfaces that hide complexity while
    preserving full capability for those who need it.
    """
    
    def __init__(self):
        self.tools = {
            'hunt_regression': self._hunt_regression,
            'find_regression': self._hunt_regression,  # Alias
            'analyze_logs': self._analyze_logs,
            'check_commit': self._check_commit,
            'list_commits': self._list_commits,
            'verify_feature': self._verify_feature,
            'commit_changes': self._commit_changes,
            'auto_commit': self._auto_commit,
        }
        
        # Pattern matching for Level 3 (local LLM) commands
        self.command_patterns = [
            (r'hunt_regression\s+(\d+)\s+(.+)', self._parse_hunt_regression),
            (r'find_regression\s+(\d+)\s+(.+)', self._parse_hunt_regression),
            (r'analyze_logs\s+(.+?)(?:\s+(\d+))?$', self._parse_analyze_logs),
            (r'check_commit\s+([a-f0-9]+)\s+(.+)', self._parse_check_commit),
            (r'list_commits\s+(\d+)', self._parse_list_commits),
            (r'verify_feature\s+(\w+)(?:\s+([a-f0-9]+))?', self._parse_verify_feature),
            (r'release_commit(?:\s+(.+))?', self._parse_release_commit),
            (r'release_dry_run', self._parse_release_dry_run),
            (r'release_status', self._parse_release_status),
        ]
    
    # Level 2: Simple function interface for smart models
    def _hunt_regression(self, days_ago: int, pattern: str = None, **kwargs) -> Dict[str, Any]:
        """Hunt for regressions using binary search."""
        return hunt_regression(days_ago, pattern)
    
    def _analyze_logs(self, pattern: str, since_hours: int = 24, **kwargs) -> Dict[str, Any]:
        """Analyze log files for patterns."""
        # TODO: Implement log analyzer
        return {
            "success": True,
            "pattern": pattern,
            "since_hours": since_hours,
            "message": "🚧 Log analyzer coming soon!"
        }
    
    def _check_commit(self, commit_hash: str, test_pattern: str, **kwargs) -> Dict[str, Any]:
        """Check if a specific commit passes a test."""
        hunter = RegressionHunter()
        
        # Checkout the commit and test
        if hunter.checkout_commit(commit_hash):
            result = hunter.test_log_pattern(test_pattern)
            hunter.restore_original_commit()
            
            return {
                "success": True,
                "commit_hash": commit_hash,
                "test_pattern": test_pattern,
                "test_result": result,
                "status": "PASS" if result else "FAIL"
            }
        else:
            return {
                "success": False,
                "error": f"Could not checkout commit {commit_hash}"
            }
    
    def _list_commits(self, days_ago: int, **kwargs) -> Dict[str, Any]:
        """List commits in time window."""
        hunter = RegressionHunter()
        commits = hunter.get_commits_for_days_ago(days_ago)
        
        return {
            "success": True,
            "days_ago": days_ago,
            "total_commits": len(commits),
            "commits": [
                {
                    "hash": c.hash,
                    "index": c.index,
                    "timestamp": c.timestamp.isoformat() if c.timestamp else None
                }
                for c in commits[:10]  # Limit to first 10 for readability
            ],
            "truncated": len(commits) > 10
        }
    
    def _verify_feature(self, feature_name: str, commit_hash: str = None, **kwargs) -> Dict[str, Any]:
        """Verify if a feature is working."""
        # TODO: Implement feature verification
        return {
            "success": True,
            "feature_name": feature_name,
            "commit_hash": commit_hash,
            "message": "🚧 Feature verification coming soon!"
        }
    
    def _commit_changes(self, message: str = None, **kwargs) -> Dict[str, Any]:
        """Commit changes using AI or custom message."""
        return parse_release_command(f"release_commit {message}" if message else "release_commit")
    
    def _auto_commit(self, **kwargs) -> Dict[str, Any]:
        """Auto-commit with AI-generated message."""
        return parse_release_command("release_commit")
    
    # Level 3: Command pattern parsing for local LLMs
    def _parse_hunt_regression(self, match) -> Dict[str, Any]:
        """Parse: hunt_regression <days_ago> <pattern>"""
        days_ago = int(match.group(1))
        pattern = match.group(2).strip()
        return self._hunt_regression(days_ago, pattern)
    
    def _parse_analyze_logs(self, match) -> Dict[str, Any]:
        """Parse: analyze_logs <pattern> [since_hours]"""
        pattern = match.group(1).strip()
        since_hours = int(match.group(2)) if match.group(2) else 24
        return self._analyze_logs(pattern, since_hours)
    
    def _parse_check_commit(self, match) -> Dict[str, Any]:
        """Parse: check_commit <hash> <test_pattern>"""
        commit_hash = match.group(1)
        test_pattern = match.group(2).strip()
        return self._check_commit(commit_hash, test_pattern)
    
    def _parse_list_commits(self, match) -> Dict[str, Any]:
        """Parse: list_commits <days_ago>"""
        days_ago = int(match.group(1))
        return self._list_commits(days_ago)
    
    def _parse_verify_feature(self, match) -> Dict[str, Any]:
        """Parse: verify_feature <feature_name> [commit]"""
        feature_name = match.group(1)
        commit_hash = match.group(2) if match.group(2) else None
        return self._verify_feature(feature_name, commit_hash)
    
    def _parse_release_commit(self, match) -> Dict[str, Any]:
        """Parse: release_commit [message]"""
        message = match.group(1).strip() if match.group(1) else None
        return parse_release_command(f"release_commit {message}" if message else "release_commit")
    
    def _parse_release_dry_run(self, match) -> Dict[str, Any]:
        """Parse: release_dry_run"""
        return parse_release_command("release_dry_run")
    
    def _parse_release_status(self, match) -> Dict[str, Any]:
        """Parse: release_status"""
        return parse_release_command("release_status")

# Global API instance
_api = GoldenPathAPI()

# Level 2: Direct function interface
def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    🎯 LEVEL 2 INTERFACE: Simple function calls
    
    Execute any tool with simple parameters.
    
    Examples:
        execute_tool("hunt_regression", days_ago=7, pattern="FEATURE_XYZ")
        execute_tool("list_commits", days_ago=3)
        execute_tool("check_commit", commit_hash="abc123", test_pattern="Server started")
    """
    if tool_name not in _api.tools:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}",
            "available_tools": list(_api.tools.keys())
        }
    
    try:
        return _api.tools[tool_name](**kwargs)
    except Exception as e:
        return {
            "success": False,
            "error": f"Tool execution failed: {str(e)}",
            "tool_name": tool_name,
            "parameters": kwargs
        }

def parse_command(command: str) -> Dict[str, Any]:
    """
    🎯 LEVEL 3 INTERFACE: Command pattern matching
    
    Parse simple command strings for local LLMs.
    
    Examples:
        parse_command("hunt_regression 7 FEATURE_XYZ")
        parse_command("list_commits 3")
        parse_command("check_commit abc123 Server started")
    """
    command = command.strip()
    
    # Try each pattern
    for pattern, parser in _api.command_patterns:
        match = re.match(pattern, command, re.IGNORECASE)
        if match:
            try:
                return parser(match)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Command parsing failed: {str(e)}",
                    "command": command
                }
    
    # No pattern matched
    return {
        "success": False,
        "error": f"Unknown command: {command}",
                    "available_commands": [
                "hunt_regression <days_ago> <pattern>",
                "analyze_logs <pattern> [since_hours]",
                "check_commit <hash> <test_pattern>",
                "list_commits <days_ago>",
                "verify_feature <feature_name> [commit]",
                "release_commit [message]",
                "release_dry_run",
                "release_status"
            ]
    }

def available_tools() -> List[str]:
    """Get list of available tools."""
    return list(_api.tools.keys())

# Level 1: Direct class access (imported via __init__.py)
# Super-brain models can import RegressionHunter directly for full control

def get_api_help() -> str:
    """Get comprehensive help for all API levels."""
    return """
🎯 GOLDEN PATH API HELP

LEVEL 1 (Super-Brain Models):
    from tools import RegressionHunter
    hunter = RegressionHunter()
    result = hunter.find_breaking_commit(days_ago=7, test_pattern="FEATURE_XYZ")

LEVEL 2 (Smart Models):
    from tools.golden_path_api import execute_tool
    result = execute_tool("hunt_regression", days_ago=7, pattern="FEATURE_XYZ")

LEVEL 3 (Local LLMs):
    from tools.golden_path_api import parse_command
    result = parse_command("hunt_regression 7 FEATURE_XYZ")

AVAILABLE TOOLS:
    - hunt_regression: Find when a feature broke using binary search
    - analyze_logs: Search log files for patterns
    - check_commit: Test if a specific commit passes a test
    - list_commits: Get commits in a time window
    - verify_feature: Check if a feature is working
    - commit_changes: Commit changes with AI or custom message
    - auto_commit: Auto-commit with AI-generated message

COMMAND PATTERNS:
    hunt_regression <days_ago> <pattern>
    analyze_logs <pattern> [since_hours]
    check_commit <hash> <test_pattern>
    list_commits <days_ago>
    verify_feature <feature_name> [commit]
    release_commit [message]
    release_dry_run
    release_status
""" 
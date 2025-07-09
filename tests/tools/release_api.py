#!/usr/bin/env python3
"""
🎯 RELEASE API: Golden Path for AI Commit System

Makes the AI commit system accessible through the progressive intelligence hierarchy.
Beautiful interfaces for all intelligence levels to trigger commits.

PROGRESSIVE INTELLIGENCE HIERARCHY:

Level 1 (Super-Brain Models):
    from tools import ReleaseManager
    manager = ReleaseManager()
    result = manager.commit_with_ai(message_override="Custom message")

Level 2 (Smart Models):  
    from tools.release_api import commit_changes
    result = commit_changes(message="Optional custom message")

Level 3 (Local LLMs):
    release_commit
    release_commit Custom message here
"""
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional

class ReleaseManager:
    """
    🎯 SOPHISTICATED RELEASE MANAGEMENT
    
    Provides programmatic access to the AI commit system with full capability.
    """
    
    def __init__(self, tests_dir: Path = None):
        self.tests_dir = tests_dir or Path(__file__).parent.parent
        self.release_script = self.tests_dir / "release.py"
        
    def commit_with_ai(self, message_override: str = None, no_push: bool = False) -> Dict[str, Any]:
        """
        Execute AI-assisted commit with full control.
        
        Args:
            message_override: Custom commit message (bypasses AI generation)
            no_push: Skip pushing to remote
            
        Returns:
            Dictionary with success status and details
        """
        try:
            cmd = [sys.executable, str(self.release_script)]
            
            if message_override:
                cmd.extend(["-m", message_override])
                
            if no_push:
                cmd.append("--no-push")
            
            result = subprocess.run(
                cmd,
                cwd=self.tests_dir,
                capture_output=True,
                text=True,
                check=False
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": " ".join(cmd) if 'cmd' in locals() else "Command construction failed"
            }
    
    def dry_run_commit(self) -> Dict[str, Any]:
        """Show what would be committed without actually committing."""
        try:
            # First check git status
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.tests_dir.parent,  # Run in pipulate dir
                capture_output=True,
                text=True,
                check=True
            )
            
            # Then run release script in dry-run mode
            result = subprocess.run(
                [sys.executable, str(self.release_script), "--dry-run"],
                cwd=self.tests_dir,
                capture_output=True,
                text=True,
                check=False
            )
            
            return {
                "success": True,
                "git_status": status_result.stdout,
                "dry_run_output": result.stdout,
                "changes_detected": bool(status_result.stdout.strip())
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_commit_status(self) -> Dict[str, Any]:
        """Get current git status and commit readiness."""
        try:
            # Check if there are staged changes
            staged_result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=self.tests_dir.parent,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Check if there are unstaged changes
            unstaged_result = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=self.tests_dir.parent,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Check if there are untracked files
            untracked_result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self.tests_dir.parent,
                capture_output=True,
                text=True,
                check=True
            )
            
            staged_files = staged_result.stdout.strip().split('\n') if staged_result.stdout.strip() else []
            unstaged_files = unstaged_result.stdout.strip().split('\n') if unstaged_result.stdout.strip() else []
            untracked_files = untracked_result.stdout.strip().split('\n') if untracked_result.stdout.strip() else []
            
            return {
                "success": True,
                "staged_files": staged_files,
                "unstaged_files": unstaged_files,
                "untracked_files": untracked_files,
                "ready_to_commit": len(staged_files) > 0 or len(unstaged_files) > 0 or len(untracked_files) > 0,
                "total_changes": len(staged_files) + len(unstaged_files) + len(untracked_files)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

# Level 2: Simplified interface for smart models
def commit_changes(message: str = None, no_push: bool = False) -> Dict[str, Any]:
    """
    🎯 LEVEL 2 INTERFACE: Simple commit function
    
    Commit changes using AI or custom message.
    
    Args:
        message: Optional custom commit message
        no_push: Skip pushing to remote
        
    Returns:
        Dictionary with success status and details
    """
    manager = ReleaseManager()
    return manager.commit_with_ai(message_override=message, no_push=no_push)

def dry_run() -> Dict[str, Any]:
    """Show what would be committed without actually committing."""
    manager = ReleaseManager()
    return manager.dry_run_commit()

def check_status() -> Dict[str, Any]:
    """Check current git status and commit readiness."""
    manager = ReleaseManager()
    return manager.get_commit_status()

# Level 3: Command pattern parsing for local LLMs
def parse_release_command(command: str) -> Dict[str, Any]:
    """
    🎯 LEVEL 3 INTERFACE: Command pattern matching
    
    Parse simple release commands for local LLMs.
    
    Examples:
        "release_commit" -> AI-generated commit
        "release_commit Custom message here" -> Custom message commit
        "release_dry_run" -> Dry run mode
        "release_status" -> Check git status
    """
    command = command.strip()
    
    if command == "release_commit":
        return commit_changes()
    elif command.startswith("release_commit "):
        message = command[15:].strip()  # Remove "release_commit "
        return commit_changes(message=message)
    elif command == "release_dry_run":
        return dry_run()
    elif command == "release_status":
        return check_status()
    else:
        return {
            "success": False,
            "error": f"Unknown release command: {command}",
            "available_commands": [
                "release_commit",
                "release_commit <message>",
                "release_dry_run", 
                "release_status"
            ]
        }

# Convenience aliases for common patterns
def auto_commit() -> Dict[str, Any]:
    """Auto-commit with AI-generated message."""
    return commit_changes()

def commit_with_message(message: str) -> Dict[str, Any]:
    """Commit with custom message."""
    return commit_changes(message=message) 
#!/usr/bin/env python3
"""
🎯 COMMIT EXPLORER: Manual Bug Hunt Probing

Simple interface for manual exploration of git history.
Provides "commits ago" language and transitions to binary search.

WORKFLOW:
1. Manual exploration: python tests.py 100 (100 commits ago)
2. Find rough boundaries through manual testing  
3. Get copy-paste command for binary search
4. Transition to automated hunting

DESIGN PHILOSOPHY:
- Simple numeric interface (no hash management)
- Server restart detection
- Copy-paste ready output
- Seamless transition to binary search
"""
import subprocess
import time
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

class CommitExplorer:
    """
    🎯 MANUAL COMMIT EXPLORATION ENGINE
    
    Simple interface for exploring git history without dealing with hashes.
    """
    
    def __init__(self, tests_dir: Path = None):
        self.tests_dir = tests_dir or Path(__file__).parent.parent
        self.pipulate_dir = self.tests_dir.parent
        self.original_commit = None
        
    def get_commit_by_offset(self, commits_ago: int) -> Optional[Dict[str, Any]]:
        """Get commit information by offset from HEAD."""
        try:
            # Get commit hash
            hash_result = subprocess.run(
                ['git', 'rev-parse', f'HEAD~{commits_ago}'],
                cwd=self.pipulate_dir,
                capture_output=True,
                text=True,
                check=True
            )
            commit_hash = hash_result.stdout.strip()
            
            # Get commit info
            info_result = subprocess.run(
                ['git', 'show', '--format="%H|%ct|%s|%an"', '--no-patch', commit_hash],
                cwd=self.pipulate_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse the output (remove quotes)
            info_line = info_result.stdout.strip().strip('"')
            if '|' in info_line:
                hash_str, timestamp_str, subject, author = info_line.split('|', 3)
                timestamp = datetime.fromtimestamp(int(timestamp_str))
                
                return {
                    'hash': hash_str,
                    'commits_ago': commits_ago,
                    'timestamp': timestamp,
                    'subject': subject,
                    'author': author,
                    'age_days': (datetime.now() - timestamp).days
                }
                
        except subprocess.CalledProcessError:
            pass
        
        return None
    
    def checkout_commit_by_offset(self, commits_ago: int) -> Dict[str, Any]:
        """
        Checkout a commit by offset and wait for server restart.
        
        Args:
            commits_ago: Number of commits back from HEAD
            
        Returns:
            Dictionary with checkout results and transition commands
        """
        try:
            # Store original commit if this is the first checkout
            if self.original_commit is None:
                result = subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    cwd=self.pipulate_dir,
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.original_commit = result.stdout.strip()
            
            # Get commit info before checkout
            commit_info = self.get_commit_by_offset(commits_ago)
            if not commit_info:
                return {
                    "success": False,
                    "error": f"Cannot find commit {commits_ago} commits ago",
                    "max_commits": self._get_total_commits()
                }
            
            # Checkout the commit
            subprocess.run(
                ['git', 'checkout', f'HEAD~{commits_ago}'],
                cwd=self.pipulate_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Calculate transition commands
            days_ago = commit_info['age_days']
            transition_command = f"python tests.py -{days_ago}"
            
            return {
                "success": True,
                "commits_ago": commits_ago,
                "commit_info": commit_info,
                "checkout_message": f"📍 Checked out commit {commits_ago} commits ago",
                "commit_details": f"   Hash: {commit_info['hash'][:8]}",
                "commit_age": f"   Age: {days_ago} days ago ({commit_info['timestamp'].strftime('%Y-%m-%d %H:%M')})",
                "commit_subject": f"   Subject: {commit_info['subject']}",
                "server_restart_note": "⏳ Server should auto-restart due to watchdog...",
                "wait_message": "   Wait a few seconds, then manually test the feature",
                "transition_command": transition_command,
                "transition_note": f"💡 When ready for binary search, run: {transition_command}",
                "restore_command": "python tests.py restore",
                "days_ago_equivalent": days_ago
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Failed to checkout commit: {e}",
                "stderr": e.stderr if hasattr(e, 'stderr') else ""
            }
    
    def restore_original_commit(self) -> Dict[str, Any]:
        """Return to the original commit."""
        if not self.original_commit:
            return {
                "success": False,
                "error": "No original commit stored"
            }
        
        try:
            subprocess.run(
                ['git', 'checkout', self.original_commit],
                cwd=self.pipulate_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            return {
                "success": True,
                "message": "🔙 Restored to original commit",
                "commit": self.original_commit[:8],
                "note": "Server should auto-restart..."
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Failed to restore: {e}"
            }
    
    def get_exploration_status(self) -> Dict[str, Any]:
        """Get current exploration status."""
        try:
            # Get current commit
            current_result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.pipulate_dir,
                capture_output=True,
                text=True,
                check=True
            )
            current_commit = current_result.stdout.strip()
            
            # Get current branch
            branch_result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=self.pipulate_dir,
                capture_output=True,
                text=True,
                check=True
            )
            current_branch = branch_result.stdout.strip()
            
            # Check if we're in detached HEAD state (exploring commits)
            in_exploration = not current_branch  # Empty branch name means detached HEAD
            
            # Get commit details
            info_result = subprocess.run(
                ['git', 'show', '--format="%ct|%s"', '--no-patch', 'HEAD'],
                cwd=self.pipulate_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            info_line = info_result.stdout.strip().strip('"')
            if '|' in info_line:
                timestamp_str, subject = info_line.split('|', 1)
                timestamp = datetime.fromtimestamp(int(timestamp_str))
                days_ago = (datetime.now() - timestamp).days
            else:
                timestamp = datetime.now()
                subject = "Unknown"
                days_ago = 0
            
            return {
                "success": True,
                "current_commit": current_commit[:8],
                "current_branch": current_branch or "DETACHED HEAD",
                "in_exploration": in_exploration,
                "commit_subject": subject,
                "commit_age_days": days_ago,
                "commit_timestamp": timestamp.strftime('%Y-%m-%d %H:%M'),
                "original_commit": self.original_commit[:8] if self.original_commit else None
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Failed to get status: {e}"
            }
    
    def _get_total_commits(self) -> int:
        """Get total number of commits in the repository."""
        try:
            result = subprocess.run(
                ['git', 'rev-list', '--count', 'HEAD'],
                cwd=self.pipulate_dir,
                capture_output=True,
                text=True,
                check=True
            )
            return int(result.stdout.strip())
        except:
            return 0
    
    def suggest_next_steps(self, current_commits_ago: int, feature_works: bool) -> Dict[str, Any]:
        """
        Suggest next exploration steps based on current findings.
        
        Args:
            current_commits_ago: Current position in history
            feature_works: Whether the feature works at current position
            
        Returns:
            Dictionary with suggested next steps
        """
        suggestions = []
        
        if feature_works:
            # Feature works here - try more recent commits
            if current_commits_ago > 50:
                next_test = current_commits_ago // 2
                suggestions.append(f"python tests.py {next_test}")
                suggestions.append(f"# Feature works at {current_commits_ago} commits ago - try {next_test}")
            elif current_commits_ago > 10:
                next_test = current_commits_ago - 10
                suggestions.append(f"python tests.py {next_test}")
                suggestions.append(f"# Feature works - getting closer, try {next_test}")
            else:
                next_test = max(1, current_commits_ago - 5)
                suggestions.append(f"python tests.py {next_test}")
                suggestions.append(f"# Very close - try {next_test}")
        else:
            # Feature broken here - try older commits
            if current_commits_ago < 50:
                next_test = current_commits_ago + 50
                suggestions.append(f"python tests.py {next_test}")
                suggestions.append(f"# Feature broken at {current_commits_ago} commits ago - try {next_test}")
            else:
                next_test = current_commits_ago + 100
                suggestions.append(f"python tests.py {next_test}")
                suggestions.append(f"# Still broken - go further back to {next_test}")
        
        return {
            "current_position": current_commits_ago,
            "feature_status": "WORKING" if feature_works else "BROKEN",
            "suggestions": suggestions,
            "next_command": suggestions[0] if suggestions else "python tests.py restore"
        }

# Convenience functions for golden path API integration
def explore_commit(commits_ago: int) -> Dict[str, Any]:
    """Explore a specific commit offset."""
    explorer = CommitExplorer()
    return explorer.checkout_commit_by_offset(commits_ago)

def restore_commit() -> Dict[str, Any]:
    """Restore to original commit."""
    explorer = CommitExplorer()
    return explorer.restore_original_commit()

def get_exploration_status() -> Dict[str, Any]:
    """Get current exploration status."""
    explorer = CommitExplorer()
    return explorer.get_exploration_status() 
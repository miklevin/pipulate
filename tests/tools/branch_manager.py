#!/usr/bin/env python3
"""
🎯 BRANCH MANAGER: BugHunt Workspace Management

Sophisticated branch management for bug hunting workflows.
Auto-generates branches, tracks bug hunt sessions, and handles cleanup.

DESIGN PHILOSOPHY:
- Low friction branch creation
- Auto-generated meaningful names  
- Easy cleanup to prevent bloat
- War story extraction before pruning
"""
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

class BugHuntSession:
    """Represents a bug hunting session with metadata."""
    def __init__(self, branch_name: str, created_at: str, issue_description: str = ""):
        self.branch_name = branch_name
        self.created_at = created_at
        self.issue_description = issue_description
        self.commits_tested = []
        self.findings = []
        self.resolved = False
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'branch_name': self.branch_name,
            'created_at': self.created_at,
            'issue_description': self.issue_description,
            'commits_tested': self.commits_tested,
            'findings': self.findings,
            'resolved': self.resolved
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BugHuntSession':
        session = cls(data['branch_name'], data['created_at'], data.get('issue_description', ''))
        session.commits_tested = data.get('commits_tested', [])
        session.findings = data.get('findings', [])
        session.resolved = data.get('resolved', False)
        return session

class BranchManager:
    """
    🎯 SOPHISTICATED BUGHUNT BRANCH MANAGEMENT
    
    Handles the complete lifecycle of bug hunting branches with minimal friction.
    """
    
    def __init__(self, tests_dir: Path = None):
        self.tests_dir = tests_dir or Path(__file__).parent.parent
        self.pipulate_dir = self.tests_dir.parent
        self.sessions_file = self.tests_dir / "bughunt_sessions.json"
        self.original_branch = None
        
    def get_current_branch(self) -> str:
        """Get the currently checked out branch."""
        try:
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=self.pipulate_dir,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "main"  # Fallback
    
    def generate_bughunt_branch_name(self) -> str:
        """Generate a unique bug hunt branch name."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"bughunt_{timestamp}"
    
    def create_bughunt_branch(self, issue_description: str = "") -> Dict[str, Any]:
        """
        Create a new bug hunt branch and switch to it.
        
        Args:
            issue_description: Optional description of what we're hunting
            
        Returns:
            Dictionary with branch creation results
        """
        try:
            # Store original branch if not already stored
            if self.original_branch is None:
                self.original_branch = self.get_current_branch()
            
            # Generate branch name
            branch_name = self.generate_bughunt_branch_name()
            
            # Create and checkout new branch
            subprocess.run(
                ['git', 'checkout', '-b', branch_name],
                cwd=self.pipulate_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Create session record
            session = BugHuntSession(
                branch_name=branch_name,
                created_at=datetime.now().isoformat(),
                issue_description=issue_description
            )
            
            # Save session
            self._save_session(session)
            
            return {
                "success": True,
                "branch_name": branch_name,
                "original_branch": self.original_branch,
                "message": f"🔍 Created bug hunt branch: {branch_name}"
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Failed to create branch: {e}",
                "stderr": e.stderr if hasattr(e, 'stderr') else ""
            }
    
    def list_bughunt_branches(self) -> Dict[str, Any]:
        """List all active bug hunt branches."""
        try:
            # Get all branches
            result = subprocess.run(
                ['git', 'branch'],
                cwd=self.pipulate_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Filter for bughunt branches
            all_branches = result.stdout.strip().split('\n')
            bughunt_branches = []
            
            for branch in all_branches:
                branch = branch.strip().replace('* ', '')  # Remove current marker
                if branch.startswith('bughunt_'):
                    bughunt_branches.append(branch)
            
            # Load session data
            sessions = self._load_sessions()
            
            # Combine branch list with session metadata
            branch_info = []
            for branch in bughunt_branches:
                session = next((s for s in sessions if s.branch_name == branch), None)
                branch_info.append({
                    'branch_name': branch,
                    'created_at': session.created_at if session else 'Unknown',
                    'issue_description': session.issue_description if session else '',
                    'resolved': session.resolved if session else False,
                    'commits_tested': len(session.commits_tested) if session else 0
                })
            
            return {
                "success": True,
                "total_branches": len(bughunt_branches),
                "branches": branch_info,
                "current_branch": self.get_current_branch()
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Failed to list branches: {e}"
            }
    
    def cleanup_resolved_branches(self, force: bool = False) -> Dict[str, Any]:
        """
        Clean up resolved bug hunt branches.
        
        Args:
            force: If True, delete all bughunt branches regardless of status
        """
        try:
            sessions = self._load_sessions()
            current_branch = self.get_current_branch()
            
            # Switch to original branch if we're on a bughunt branch
            if current_branch.startswith('bughunt_'):
                if self.original_branch:
                    subprocess.run(
                        ['git', 'checkout', self.original_branch],
                        cwd=self.pipulate_dir,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                else:
                    subprocess.run(
                        ['git', 'checkout', 'main'],
                        cwd=self.pipulate_dir,
                        capture_output=True,
                        text=True,
                        check=True
                    )
            
            # Find branches to delete
            branches_to_delete = []
            war_stories = []
            
            for session in sessions:
                if force or session.resolved:
                    branches_to_delete.append(session.branch_name)
                    
                    # Extract war story
                    if session.findings:
                        war_stories.append({
                            'branch_name': session.branch_name,
                            'issue_description': session.issue_description,
                            'findings': session.findings,
                            'resolved_at': datetime.now().isoformat()
                        })
            
            # Delete branches
            deleted_count = 0
            for branch_name in branches_to_delete:
                try:
                    subprocess.run(
                        ['git', 'branch', '-D', branch_name],
                        cwd=self.pipulate_dir,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    deleted_count += 1
                except subprocess.CalledProcessError:
                    pass  # Branch might not exist
            
            # Remove sessions for deleted branches
            remaining_sessions = [s for s in sessions if s.branch_name not in branches_to_delete]
            self._save_sessions(remaining_sessions)
            
            # Save war stories
            if war_stories:
                self._save_war_stories(war_stories)
            
            return {
                "success": True,
                "deleted_branches": deleted_count,
                "war_stories_extracted": len(war_stories),
                "remaining_branches": len(remaining_sessions),
                "current_branch": self.get_current_branch()
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Cleanup failed: {e}"
            }
    
    def mark_session_resolved(self, finding: str = "") -> Dict[str, Any]:
        """Mark current bug hunt session as resolved."""
        current_branch = self.get_current_branch()
        
        if not current_branch.startswith('bughunt_'):
            return {
                "success": False,
                "error": "Not currently on a bug hunt branch"
            }
        
        sessions = self._load_sessions()
        session = next((s for s in sessions if s.branch_name == current_branch), None)
        
        if session:
            session.resolved = True
            if finding:
                session.findings.append({
                    'timestamp': datetime.now().isoformat(),
                    'finding': finding
                })
            self._save_sessions(sessions)
            
            return {
                "success": True,
                "message": f"✅ Marked {current_branch} as resolved",
                "finding": finding
            }
        else:
            return {
                "success": False,
                "error": "Session not found"
            }
    
    def record_commit_test(self, commits_ago: int, test_result: bool, notes: str = "") -> Dict[str, Any]:
        """Record a commit test result in the current session."""
        current_branch = self.get_current_branch()
        
        if not current_branch.startswith('bughunt_'):
            return {"success": False, "error": "Not on a bug hunt branch"}
        
        sessions = self._load_sessions()
        session = next((s for s in sessions if s.branch_name == current_branch), None)
        
        if session:
            session.commits_tested.append({
                'commits_ago': commits_ago,
                'test_result': test_result,
                'timestamp': datetime.now().isoformat(),
                'notes': notes
            })
            self._save_sessions(sessions)
            
            return {
                "success": True,
                "message": f"📝 Recorded test: {commits_ago} commits ago = {'PASS' if test_result else 'FAIL'}"
            }
        else:
            return {"success": False, "error": "Session not found"}
    
    def _load_sessions(self) -> List[BugHuntSession]:
        """Load bug hunt sessions from file."""
        if not self.sessions_file.exists():
            return []
        
        try:
            with open(self.sessions_file, 'r') as f:
                data = json.load(f)
            return [BugHuntSession.from_dict(item) for item in data]
        except:
            return []
    
    def _save_session(self, session: BugHuntSession):
        """Save a single session."""
        sessions = self._load_sessions()
        # Remove existing session with same branch name
        sessions = [s for s in sessions if s.branch_name != session.branch_name]
        sessions.append(session)
        self._save_sessions(sessions)
    
    def _save_sessions(self, sessions: List[BugHuntSession]):
        """Save all sessions to file."""
        with open(self.sessions_file, 'w') as f:
            json.dump([s.to_dict() for s in sessions], f, indent=2)
    
    def _save_war_stories(self, war_stories: List[Dict[str, Any]]):
        """Save extracted war stories."""
        war_stories_file = self.tests_dir / "war_stories.json"
        
        existing_stories = []
        if war_stories_file.exists():
            try:
                with open(war_stories_file, 'r') as f:
                    existing_stories = json.load(f)
            except:
                pass
        
        existing_stories.extend(war_stories)
        
        with open(war_stories_file, 'w') as f:
            json.dump(existing_stories, f, indent=2)

# Convenience functions for golden path API integration
def create_bughunt_branch(description: str = "") -> Dict[str, Any]:
    """Create a new bug hunt branch."""
    manager = BranchManager()
    return manager.create_bughunt_branch(description)

def cleanup_branches(force: bool = False) -> Dict[str, Any]:
    """Clean up resolved bug hunt branches."""
    manager = BranchManager()
    return manager.cleanup_resolved_branches(force)

def list_bughunt_branches() -> Dict[str, Any]:
    """List active bug hunt branches."""
    manager = BranchManager()
    return manager.list_bughunt_branches() 
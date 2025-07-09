#!/usr/bin/env python3
"""
🎯 REGRESSION HUNTER: Binary Search Time Machine

Implements the sophisticated binary search algorithm for finding exact commits
where features broke. Uses BugHunt data structures for efficient navigation
through git history.

Key Innovation: Logarithmic time regression discovery instead of linear search.
"""
import subprocess
import sqlite3
import time
from collections import namedtuple
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Tuple

# The BugHunt data structure from our design document
BugHunt = namedtuple('BugHunt', ['hash', 'index', 'total', 'returns'], defaults=(None,))

class CommitSnapshot:
    """Represents a git commit with test results."""
    def __init__(self, hash: str, index: int, total: int, timestamp: datetime = None):
        self.hash = hash
        self.index = index  
        self.total = total
        self.timestamp = timestamp
        self.test_results = {}
        self.returns = None  # True/False test result
    
    def to_bughunt(self) -> BugHunt:
        """Convert to BugHunt namedtuple for binary search."""
        return BugHunt(
            hash=self.hash,
            index=self.index,
            total=self.total,
            returns=self.returns
        )

class RegressionHunter:
    """
    🎯 SOPHISTICATED REGRESSION HUNTING ENGINE
    
    Uses binary search to efficiently find the exact commit where a feature broke.
    Logarithmic time complexity means 1000+ commits can be searched in ~10 tests.
    """
    
    def __init__(self, tests_dir: Path = None):
        self.tests_dir = tests_dir or Path(__file__).parent.parent
        self.pipulate_dir = self.tests_dir.parent
        self.current_commit = None
        self.original_commit = None
        
    def get_commits_for_days_ago(self, days_ago: int) -> List[CommitSnapshot]:
        """Get all commits from current HEAD back to N days ago."""
        try:
            # Calculate the since date
            since_date = datetime.now() - timedelta(days=days_ago)
            since_str = since_date.strftime("%Y-%m-%d")
            
            # Get commit hashes with timestamps
            cmd = [
                'git', 'log', 
                f'--since={since_str}',
                '--pretty=format:%H|%ct',  # hash|timestamp
                '--reverse'  # Oldest first for correct indexing
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.pipulate_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            if not result.stdout.strip():
                return []
            
            commits = []
            lines = result.stdout.strip().split('\n')
            total = len(lines)
            
            for i, line in enumerate(lines):
                if '|' in line:
                    hash_str, timestamp_str = line.split('|')
                    timestamp = datetime.fromtimestamp(int(timestamp_str))
                    
                    commit = CommitSnapshot(
                        hash=hash_str,
                        index=i,
                        total=total,
                        timestamp=timestamp
                    )
                    commits.append(commit)
            
            return commits
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error getting commits: {e}")
            return []
    
    def checkout_commit(self, commit_hash: str) -> bool:
        """Safely checkout a specific commit."""
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
            
            # Checkout the target commit
            subprocess.run(
                ['git', 'checkout', commit_hash],
                cwd=self.pipulate_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            self.current_commit = commit_hash
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error checking out commit {commit_hash}: {e}")
            return False
    
    def restore_original_commit(self) -> bool:
        """Return to the original commit."""
        if self.original_commit:
            return self.checkout_commit(self.original_commit)
        return True
    
    def test_log_pattern(self, pattern: str, timeout_seconds: int = 30) -> bool:
        """
        Test if a pattern appears in server logs after restart.
        
        This is a common regression test - checking if specific features
        still initialize correctly on server startup.
        """
        try:
            # The server should auto-restart due to watchdog when we checkout commits
            # Wait a moment for restart to complete
            time.sleep(3)
            
            # Check for pattern in logs
            log_path = self.pipulate_dir / "logs" / "server.log"
            if not log_path.exists():
                return False
                
            with open(log_path, 'r') as f:
                log_content = f.read()
            
            return pattern in log_content
            
        except Exception as e:
            print(f"⚠️ Log pattern test failed: {e}")
            return False
    
    def test_database_table_exists(self, table_name: str) -> bool:
        """Test if a database table still exists."""
        try:
            # Find the database file
            data_dir = self.pipulate_dir / "data"
            db_files = list(data_dir.glob("*.db"))
            
            if not db_files:
                return False
                
            db_path = db_files[0]  # Use first database found
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
            
        except Exception as e:
            print(f"⚠️ Database test failed: {e}")
            return False
    
    def test_http_endpoint(self, endpoint: str, expected_status: int = 200) -> bool:
        """Test if an HTTP endpoint is working."""
        try:
            import requests
            
            url = f"http://localhost:5001{endpoint}"
            response = requests.get(url, timeout=10)
            
            return response.status_code == expected_status
            
        except Exception as e:
            print(f"⚠️ HTTP endpoint test failed: {e}")
            return False
    
    def binary_search_regression(
        self, 
        commits: List[CommitSnapshot], 
        test_function: Callable[[CommitSnapshot], bool]
    ) -> Tuple[Optional[CommitSnapshot], Optional[CommitSnapshot]]:
        """
        🎯 BINARY SEARCH ALGORITHM FOR REGRESSION HUNTING
        
        Find the exact boundary where a feature stops working.
        
        Returns:
            (last_good_commit, first_bad_commit) or (None, None) if no regression found
        """
        if not commits:
            return None, None
            
        print(f"🔍 Starting binary search on {len(commits)} commits...")
        
        left, right = 0, len(commits) - 1
        last_good = None
        first_bad = None
        
        while left <= right:
            mid = (left + right) // 2
            commit = commits[mid]
            
            print(f"🎯 Testing commit {mid+1}/{len(commits)}: {commit.hash[:8]}")
            
            # Checkout and test this commit
            if not self.checkout_commit(commit.hash):
                print(f"❌ Failed to checkout {commit.hash}")
                break
                
            # Run the test
            feature_works = test_function(commit)
            commit.returns = feature_works
            
            print(f"{'✅' if feature_works else '❌'} Commit {commit.hash[:8]}: {'WORKING' if feature_works else 'BROKEN'}")
            
            if feature_works:
                # Feature works - bug is after this commit
                last_good = commit
                left = mid + 1
            else:
                # Feature broken - bug is at or before this commit
                first_bad = commit
                right = mid - 1
        
        # Restore original commit
        self.restore_original_commit()
        
        return last_good, first_bad
    
    def find_breaking_commit(
        self, 
        days_ago: int, 
        test_pattern: str = None,
        test_function: Callable = None
    ) -> Dict[str, Any]:
        """
        🎯 MAIN REGRESSION HUNTING INTERFACE
        
        Find the exact commit where a feature broke using binary search.
        
        Args:
            days_ago: How many days back to search
            test_pattern: Log pattern to search for (if no custom test_function)
            test_function: Custom test function that takes CommitSnapshot and returns bool
            
        Returns:
            Dictionary with results including last_good, first_bad, total_commits, tests_run
        """
        print(f"🕰️ REGRESSION HUNT: Searching {days_ago} days of history")
        
        # Get commits for time window
        commits = self.get_commits_for_days_ago(days_ago)
        if not commits:
            return {
                "success": False,
                "error": f"No commits found in last {days_ago} days",
                "total_commits": 0
            }
        
        print(f"📅 Found {len(commits)} commits to search")
        
        # Define test function
        if test_function is None:
            if test_pattern:
                test_function = lambda commit: self.test_log_pattern(test_pattern)
            else:
                # Default test - just check if server starts
                test_function = lambda commit: self.test_log_pattern("Server started")
        
        # Execute binary search
        last_good, first_bad = self.binary_search_regression(commits, test_function)
        
        # Prepare results
        result = {
            "success": True,
            "total_commits": len(commits),
            "tests_run": sum(1 for c in commits if c.returns is not None),
            "efficiency": f"{len(commits)} commits searched in {sum(1 for c in commits if c.returns is not None)} tests",
            "time_window": f"{days_ago} days ago",
            "last_good": None,
            "first_bad": None
        }
        
        if last_good:
            result["last_good"] = {
                "hash": last_good.hash,
                "index": last_good.index,
                "timestamp": last_good.timestamp.isoformat() if last_good.timestamp else None
            }
        
        if first_bad:
            result["first_bad"] = {
                "hash": first_bad.hash,
                "index": first_bad.index,  
                "timestamp": first_bad.timestamp.isoformat() if first_bad.timestamp else None
            }
            
        if last_good and first_bad:
            result["regression_found"] = True
            result["investigation_command"] = f"git diff {last_good.hash} {first_bad.hash}"
        else:
            result["regression_found"] = False
            
        return result

# Convenience function for Level 2 API
def hunt_regression(days_ago: int, pattern: str = None) -> Dict[str, Any]:
    """Simplified interface for regression hunting."""
    hunter = RegressionHunter()
    return hunter.find_breaking_commit(days_ago, pattern) 
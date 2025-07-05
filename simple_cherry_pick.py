#!/usr/bin/env python3
"""
Simple Cherry-Pick Recovery Script
==================================

This script processes commits from failed_cherry_picks.log ONE AT A TIME.
When a conflict occurs, it stops and reports the commit for manual handling.
You can then resume from where it left off.

Usage:
    python simple_cherry_pick.py                    # Start from beginning
    python simple_cherry_pick.py --resume 42        # Resume from commit 42
    python simple_cherry_pick.py --start-from 10    # Start from commit 10

Conservative approach: Handle conflicts manually, one at a time.
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path

def run_git_command(cmd, timeout=10):
    """Run a git command with timeout and return (exit_code, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "Command timed out"

def load_commits():
    """Load commits from failed_cherry_picks.log"""
    if not Path('regressions/failed_cherry_picks.log').exists():
        print("❌ Error: failed_cherry_picks.log not found")
        sys.exit(1)
    
    with open('regressions/failed_cherry_picks.log', 'r') as f:
        lines = f.readlines()
    
    commits = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            # Parse: hash date message
            parts = line.split(' ', 2)
            if len(parts) >= 3:
                commit_hash = parts[0]
                commit_message = parts[2]
                commits.append((commit_hash, commit_message))
    
    return commits

def process_single_commit(commit_hash, commit_message, commit_num, total_commits):
    """Process a single commit"""
    print(f"\n{'='*60}")
    print(f"🎯 Processing commit {commit_num}/{total_commits}")
    print(f"Hash: {commit_hash}")
    print(f"Message: {commit_message}")
    print(f"{'='*60}")
    
    # Try cherry-pick
    exit_code, stdout, stderr = run_git_command(f"git cherry-pick {commit_hash}")
    
    if exit_code == 0:
        print(f"✅ SUCCESS: {commit_hash[:7]} applied cleanly")
        
        # Log success
        with open('simple_cherry_pick_success.log', 'a') as f:
            f.write(f"SUCCESS: {commit_hash} {commit_message}\n")
        
        return "success"
    
    elif "CONFLICT" in stderr:
        print(f"⚠️  CONFLICT detected in {commit_hash[:7]}")
        print(f"Details: {stderr}")
        
        # Show conflicted files
        exit_code, stdout, stderr = run_git_command("git status --porcelain")
        conflicted_files = [line[3:] for line in stdout.split('\n') if line.startswith('UU ')]
        print(f"Conflicted files: {conflicted_files}")
        
        print(f"\n📋 MANUAL INTERVENTION REQUIRED:")
        print(f"1. Resolve conflicts in: {', '.join(conflicted_files)}")
        print(f"2. Run: git add {' '.join(conflicted_files)}")
        print(f"3. Run: git cherry-pick --continue")
        print(f"4. Then run: python simple_cherry_pick.py --resume {commit_num + 1}")
        
        # Log for manual review
        with open('simple_cherry_pick_conflicts.log', 'a') as f:
            f.write(f"CONFLICT: {commit_hash} {commit_message} - Files: {', '.join(conflicted_files)}\n")
        
        return "conflict"
    
    else:
        print(f"❌ ERROR: {commit_hash[:7]} failed with: {stderr}")
        
        # Log error
        with open('simple_cherry_pick_errors.log', 'a') as f:
            f.write(f"ERROR: {commit_hash} {commit_message} - {stderr.strip()}\n")
        
        return "error"

def main():
    parser = argparse.ArgumentParser(description='Simple Cherry-Pick Recovery')
    parser.add_argument('--resume', type=int, help='Resume from commit number')
    parser.add_argument('--start-from', type=int, help='Start from commit number')
    args = parser.parse_args()
    
    # Load commits
    commits = load_commits()
    print(f"📋 Found {len(commits)} commits to process")
    
    # Determine starting point
    if args.resume:
        start_index = args.resume - 1
        print(f"🔄 Resuming from commit {args.resume}")
    elif args.start_from:
        start_index = args.start_from - 1
        print(f"🎯 Starting from commit {args.start_from}")
    else:
        start_index = 0
        print(f"🚀 Starting from the beginning")
    
    # Validate starting point
    if start_index >= len(commits):
        print(f"❌ Error: Starting point {start_index + 1} is beyond the number of commits ({len(commits)})")
        sys.exit(1)
    
    # Process commits one by one
    for i in range(start_index, len(commits)):
        commit_hash, commit_message = commits[i]
        commit_num = i + 1
        
        result = process_single_commit(commit_hash, commit_message, commit_num, len(commits))
        
        if result == "conflict":
            print(f"\n⏸️  STOPPED at commit {commit_num} due to conflict")
            print(f"After resolving, run: python simple_cherry_pick.py --resume {commit_num + 1}")
            break
        elif result == "error":
            print(f"\n❌ STOPPED at commit {commit_num} due to error")
            print(f"After fixing, run: python simple_cherry_pick.py --resume {commit_num + 1}")
            break
        elif result == "success":
            print(f"✅ Continuing to next commit...")
            continue
    
    else:
        print(f"\n🎉 ALL COMMITS PROCESSED SUCCESSFULLY!")
        print(f"✅ Success log: simple_cherry_pick_success.log")
        print(f"⚠️  Conflicts log: simple_cherry_pick_conflicts.log")
        print(f"❌ Errors log: simple_cherry_pick_errors.log")

if __name__ == "__main__":
    main() 
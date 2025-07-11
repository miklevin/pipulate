#!/usr/bin/env python3
"""
Patch-Based Recovery Script
===========================

This script recovers lost work by applying commits as patches instead of using cherry-pick.
This completely avoids the cherry-pick --continue command that causes terminal lockups.

Strategy:
1. Generate patches from each commit 
2. Apply patches using git apply
3. Create new commits manually
4. No cherry-pick commands = no lockup risk

Usage:
    python patch_based_recovery.py                    # Start from beginning
    python patch_based_recovery.py --resume 42        # Resume from commit 42
"""

import subprocess
import sys
import os
import argparse
import tempfile
from pathlib import Path

def run_command(cmd, timeout=10):
    """Run a command with timeout and return (exit_code, stdout, stderr)"""
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
            parts = line.split(' ', 2)
            if len(parts) >= 3:
                commit_hash = parts[0]
                commit_message = parts[2]
                commits.append((commit_hash, commit_message))
    
    return commits

def apply_commit_as_patch(commit_hash, commit_message, commit_num, total_commits):
    """Apply a single commit as a patch"""
    print(f"\n{'='*60}")
    print(f"📦 Processing commit {commit_num}/{total_commits} as patch")
    print(f"Hash: {commit_hash}")
    print(f"Message: {commit_message}")
    print(f"{'='*60}")
    
    # Create a temporary patch file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as patch_file:
        patch_path = patch_file.name
    
    try:
        # Generate patch from the commit
        exit_code, patch_content, stderr = run_command(f"git format-patch -1 --stdout {commit_hash}")
        
        if exit_code != 0:
            print(f"❌ ERROR: Failed to generate patch for {commit_hash[:7]}")
            print(f"Error: {stderr}")
            return "error"
        
        # Write patch to file
        with open(patch_path, 'w') as f:
            f.write(patch_content)
        
        print(f"📄 Generated patch: {len(patch_content)} bytes")
        
        # Clean the commit message (remove backticks if present) - needed for both success and conflict paths
        clean_message = commit_message.replace('```', '').strip()
        
        # Try to apply the patch
        exit_code, stdout, stderr = run_command(f"git apply --3way {patch_path}")
        
        if exit_code == 0:
            print(f"✅ Patch applied cleanly")
            
            # Stage all changes
            run_command("git add .")
            
            # Create commit with original message and author
            exit_code, author_info, _ = run_command(f"git log -1 --format='%an <%ae>' {commit_hash}")
            author = author_info.strip() if author_info else "Unknown Author <unknown@example.com>"
            
            exit_code, commit_date, _ = run_command(f"git log -1 --format='%ad' {commit_hash}")
            date = commit_date.strip() if commit_date else ""
            
            commit_cmd = f'git commit --author="{author}" -m "{clean_message}"'
            if date:
                commit_cmd += f' --date="{date}"'
            
            exit_code, stdout, stderr = run_command(commit_cmd)
            
            if exit_code == 0:
                print(f"✅ SUCCESS: Commit created successfully")
                
                # Log success
                with open('patch_recovery_success.log', 'a') as f:
                    f.write(f"SUCCESS: {commit_hash} {commit_message}\n")
                
                return "success"
            else:
                print(f"❌ ERROR: Failed to create commit")
                print(f"Error: {stderr}")
                return "error"
        
        else:
            print(f"⚠️  PATCH CONFLICT detected")
            print(f"Details: {stderr}")
            
            # Check for conflicted files
            exit_code, status_output, _ = run_command("git status --porcelain")
            conflicted_files = [line[3:] for line in status_output.split('\n') if 'UU ' in line or 'AA ' in line or 'DD ' in line]
            
            if conflicted_files:
                print(f"Conflicted files: {conflicted_files}")
                print(f"\n📋 MANUAL INTERVENTION REQUIRED:")
                print(f"1. Resolve conflicts in: {', '.join(conflicted_files)}")
                print(f"2. Run: git add {' '.join(conflicted_files)}")
                print(f"3. Run: git commit -m \"{clean_message}\"")
                print(f"4. Then run: python patch_based_recovery.py --resume {commit_num + 1}")
                
                # Log for manual review
                with open('patch_recovery_conflicts.log', 'a') as f:
                    f.write(f"CONFLICT: {commit_hash} {commit_message} - Files: {', '.join(conflicted_files)}\n")
                
                return "conflict"
            else:
                print(f"❌ ERROR: Patch failed to apply but no conflicts detected")
                print(f"Error: {stderr}")
                return "error"
    
    finally:
        # Clean up patch file
        try:
            os.unlink(patch_path)
        except:
            pass

def main():
    parser = argparse.ArgumentParser(description='Patch-Based Recovery')
    parser.add_argument('--resume', type=int, help='Resume from commit number')
    parser.add_argument('--start-from', type=int, help='Start from commit number')
    args = parser.parse_args()
    
    # Load commits
    commits = load_commits()
    print(f"📋 Found {len(commits)} commits to process as patches")
    
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
        
        result = apply_commit_as_patch(commit_hash, commit_message, commit_num, len(commits))
        
        if result == "conflict":
            print(f"\n⏸️  STOPPED at commit {commit_num} due to conflict")
            print(f"After resolving, run: python patch_based_recovery.py --resume {commit_num + 1}")
            break
        elif result == "error":
            print(f"\n❌ STOPPED at commit {commit_num} due to error")
            print(f"After fixing, run: python patch_based_recovery.py --resume {commit_num + 1}")
            break
        elif result == "success":
            print(f"✅ Continuing to next commit...")
            continue
    
    else:
        print(f"\n🎉 ALL COMMITS PROCESSED SUCCESSFULLY!")
        print(f"✅ Success log: patch_recovery_success.log")
        print(f"⚠️  Conflicts log: patch_recovery_conflicts.log")

if __name__ == "__main__":
    main() 
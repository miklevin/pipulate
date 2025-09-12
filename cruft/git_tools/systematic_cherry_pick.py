#!/usr/bin/env python3
"""
Systematic Cherry-Pick Recovery Script
=====================================

This script processes commits from failed_cherry_picks.log systematically,
handling conflicts conservatively and logging progress.

Strategy:
1. Read commits from failed_cherry_picks.log
2. For each commit:
   - Try cherry-pick
   - If success: continue to next
   - If conflict: analyze complexity
     - Simple conflicts (comments, small changes): try to resolve
     - Complex conflicts (major changes, new files): skip and log
3. Track progress and create logs for manual review

Conservative approach: When in doubt, skip it.
"""

import subprocess
import sys
import os
import re
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

def is_simple_conflict(file_path):
    """Check if a conflict is simple (comments, small changes) or complex"""
    if not Path(file_path).exists():
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find conflict markers
    conflict_sections = re.findall(r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> [a-f0-9]+', content, re.DOTALL)
    
    if not conflict_sections:
        return False
    
    # Check each conflict section
    for head_section, incoming_section in conflict_sections:
        # Skip if either section is very large (> 10 lines)
        if len(head_section.split('\n')) > 10 or len(incoming_section.split('\n')) > 10:
            return False
        
        # Skip if involves function definitions or class definitions
        if ('def ' in head_section or 'def ' in incoming_section or 
            'class ' in head_section or 'class ' in incoming_section):
            return False
        
        # Skip if involves imports
        if ('import ' in head_section or 'import ' in incoming_section or
            'from ' in head_section or 'from ' in incoming_section):
            return False
    
    return True

def resolve_simple_server_py_conflict():
    """Resolve simple conflicts in server.py by preferring incoming version"""
    try:
        with open('server.py', 'r') as f:
            content = f.read()
        
        # Replace the specific conflict pattern we've seen
        pattern = r'<<<<<<< HEAD\n# Initialize logger immediately after basic configuration\n=======\n\n# 🔧 FINDER_TOKEN: rotate_looking_at_directory moved to mcp_tools\.py to eliminate circular imports\n\n# Initialize logger BEFORE any functions that need it\n>>>>>>> [a-f0-9]+ \(```\)'
        
        replacement = '\n# 🔧 FINDER_TOKEN: rotate_looking_at_directory moved to mcp_tools.py to eliminate circular imports\n\n# Initialize logger BEFORE any functions that need it'
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            with open('server.py', 'w') as f:
                f.write(new_content)
            return True
        
        return False
    except Exception as e:
        print(f"Error resolving server.py conflict: {e}")
        return False

def process_commit(commit_hash, commit_message, progress_file):
    """Process a single commit"""
    print(f"\n🎯 Processing commit {commit_hash[:7]}: {commit_message}")
    
    # Try cherry-pick
    exit_code, stdout, stderr = run_git_command(f"git cherry-pick {commit_hash}")
    
    if exit_code == 0:
        print(f"✅ SUCCESS: {commit_hash[:7]} applied cleanly")
        
        # Log to progress file
        with open(progress_file, 'a') as f:
            f.write(f"SUCCESS: {commit_hash} {commit_message}\n")
        
        return "success"
    
    # Check if it's a conflict
    if "CONFLICT" in stderr:
        print(f"⚠️  CONFLICT detected in {commit_hash[:7]}")
        
        # Get list of conflicted files
        exit_code, stdout, stderr = run_git_command("git status --porcelain")
        conflicted_files = [line[3:] for line in stdout.split('\n') if line.startswith('UU ')]
        
        print(f"Conflicted files: {conflicted_files}")
        
        # Check if conflicts are simple
        simple_conflicts = all(is_simple_conflict(f) for f in conflicted_files)
        
        if simple_conflicts and len(conflicted_files) == 1 and conflicted_files[0] == 'server.py':
            print(f"🔧 Attempting to resolve simple server.py conflict...")
            
            if resolve_simple_server_py_conflict():
                # Stage the resolved file
                exit_code, stdout, stderr = run_git_command("git add server.py")
                if exit_code == 0:
                    # Complete the cherry-pick non-interactively
                    exit_code, stdout, stderr = run_git_command("git -c core.editor=true cherry-pick --continue")
                    if exit_code == 0:
                        print(f"✅ RESOLVED: {commit_hash[:7]} conflict resolved and applied")
                        
                        # Log to progress file
                        with open(progress_file, 'a') as f:
                            f.write(f"RESOLVED: {commit_hash} {commit_message}\n")
                        
                        return "resolved"
        
        # If we get here, skip the commit
        print(f"⏭️  SKIPPING: {commit_hash[:7]} - conflict too complex")
        
        # Abort the cherry-pick
        run_git_command("git cherry-pick --abort")
        
        # Log to needs_manual_review.log
        with open('needs_manual_review.log', 'a') as f:
            f.write(f"{commit_hash} Complex conflict - manual review needed\n")
        
        # Log to progress file
        with open(progress_file, 'a') as f:
            f.write(f"SKIPPED: {commit_hash} {commit_message} - Complex conflict\n")
        
        return "skipped"
    
    else:
        # Other error (not a conflict)
        print(f"❌ ERROR: {commit_hash[:7]} failed with: {stderr}")
        
        # Log to needs_manual_review.log
        with open('needs_manual_review.log', 'a') as f:
            f.write(f"{commit_hash} Git error: {stderr.strip()}\n")
        
        # Log to progress file
        with open(progress_file, 'a') as f:
            f.write(f"ERROR: {commit_hash} {commit_message} - Git error: {stderr.strip()}\n")
        
        return "error"

def main():
    """Main processing loop"""
    # Ensure we're in the right directory
    if not Path('regressions/failed_cherry_picks.log').exists():
        print("❌ Error: failed_cherry_picks.log not found")
        sys.exit(1)
    
    # Read the commits to process
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
    
    print(f"📋 Found {len(commits)} commits to process")
    
    # Create progress file
    progress_file = 'systematic_cherry_pick_progress.log'
    with open(progress_file, 'w') as f:
        f.write(f"# Systematic Cherry-Pick Progress Log\n")
        f.write(f"# Total commits to process: {len(commits)}\n\n")
    
    # Process each commit
    stats = {"success": 0, "resolved": 0, "skipped": 0, "error": 0}
    
    for i, (commit_hash, commit_message) in enumerate(commits, 1):
        print(f"\n{'='*60}")
        print(f"Processing commit {i}/{len(commits)}")
        
        result = process_commit(commit_hash, commit_message, progress_file)
        stats[result] += 1
        
        # Show running stats
        print(f"Stats: ✅{stats['success']} 🔧{stats['resolved']} ⏭️{stats['skipped']} ❌{stats['error']}")
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"🎯 FINAL SUMMARY:")
    print(f"✅ Success (applied cleanly): {stats['success']}")
    print(f"🔧 Resolved (conflicts resolved): {stats['resolved']}")
    print(f"⏭️  Skipped (too complex): {stats['skipped']}")
    print(f"❌ Errors (git failures): {stats['error']}")
    print(f"📁 Progress log: {progress_file}")
    print(f"📁 Manual review needed: needs_manual_review.log")

if __name__ == "__main__":
    main() 
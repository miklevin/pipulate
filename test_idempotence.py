#!/usr/bin/env python3
"""
Idempotence Test for ASCII Art Sync System

This script tests whether the sync_ascii_art.py script is idempotent by:
1. Running sync multiple times
2. Checking for changes after each run
3. Detecting any duplicate markers that appear
4. Providing detailed analysis of what's happening
"""

import subprocess
import pathlib
import hashlib
import sys

def get_file_hash(file_path):
    """Get SHA256 hash of file content"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        return f"ERROR: {e}"

def get_git_status():
    """Get git status information"""
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, cwd='/home/mike/repos/Pipulate.com')
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"

def get_git_diff_stats():
    """Get git diff statistics"""
    try:
        result = subprocess.run(['git', 'diff', '--stat'], 
                              capture_output=True, text=True, cwd='/home/mike/repos/Pipulate.com')
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"

def run_sync():
    """Run the sync script and capture output"""
    try:
        result = subprocess.run(['python', 'helpers/docs_sync/sync_ascii_art.py'], 
                              capture_output=True, text=True, cwd='/home/mike/repos/pipulate')
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def check_duplicate_markers():
    """Check for duplicate markers using our detection script"""
    try:
        result = subprocess.run(['python', 'helpers/docs_sync/fix_duplicate_markers.py', 
                               '/home/mike/repos/Pipulate.com', '--dry-run'], 
                              capture_output=True, text=True, cwd='/home/mike/repos/pipulate')
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def main():
    print("🧪 ASCII ART SYNC IDEMPOTENCE TEST")
    print("=" * 50)
    
    # Get baseline state
    pipulate_com_path = pathlib.Path('/home/mike/repos/Pipulate.com')
    test_files = [
        '_guide/2025-04-15-anatomy-of-a-workflow.md',
        '_guide/2025-04-16-kickstarting-your-workflow.md', 
        'about.md',
        'development.md'
    ]
    
    print(f"\n📊 BASELINE STATE:")
    initial_status = get_git_status()
    print(f"   Git status: {'Clean' if not initial_status else 'Modified'}")
    if initial_status:
        print(f"   Changes: {initial_status}")
    
    # Get initial file hashes
    initial_hashes = {}
    for file_path in test_files:
        full_path = pipulate_com_path / file_path
        initial_hashes[file_path] = get_file_hash(full_path)
        print(f"   {file_path}: {initial_hashes[file_path][:12]}...")
    
    # Check for initial duplicate markers
    print(f"\n🔍 INITIAL DUPLICATE MARKER CHECK:")
    dup_code, dup_out, dup_err = check_duplicate_markers()
    if "Files with issues: 0" in dup_out:
        print("   ✅ No duplicate markers found")
    else:
        print("   ⚠️  Duplicate markers detected:")
        lines = dup_out.split('\n')
        for line in lines:
            if 'Found and fixed issues' in line or 'Removed' in line:
                print(f"      {line}")
    
    # Run sync operations and test idempotence
    max_iterations = 3
    for iteration in range(1, max_iterations + 1):
        print(f"\n🔄 SYNC ITERATION {iteration}:")
        
        # Run sync
        sync_code, sync_out, sync_err = run_sync()
        if sync_code != 0:
            print(f"   ❌ Sync failed with code {sync_code}")
            if sync_err:
                print(f"   Error: {sync_err}")
            break
        
        # Check if files changed
        current_status = get_git_status()
        if current_status:
            print(f"   📝 Changes detected:")
            diff_stats = get_git_diff_stats()
            if diff_stats:
                print(f"      {diff_stats}")
            else:
                print(f"      {current_status}")
        else:
            print(f"   ✅ No changes detected (idempotent)")
        
        # Check file hashes
        hash_changes = []
        for file_path in test_files:
            full_path = pipulate_com_path / file_path
            current_hash = get_file_hash(full_path)
            if current_hash != initial_hashes[file_path]:
                hash_changes.append(file_path)
                initial_hashes[file_path] = current_hash  # Update for next iteration
        
        if hash_changes:
            print(f"   📄 Files with hash changes: {len(hash_changes)}")
            for file_path in hash_changes:
                print(f"      • {file_path}")
        
        # Check for duplicate markers after sync
        dup_code, dup_out, dup_err = check_duplicate_markers()
        if "Files with issues: 0" not in dup_out:
            print(f"   ⚠️  Duplicate markers created by sync:")
            lines = dup_out.split('\n')
            for line in lines:
                if 'Found and fixed issues' in line:
                    print(f"      {line}")
        
        # Extract sync statistics
        if "Total blocks updated:" in sync_out:
            for line in sync_out.split('\n'):
                if "Files updated:" in line or "Total blocks updated:" in line:
                    print(f"   📊 {line.strip()}")
        
        # If no changes, we've achieved idempotence
        if not current_status and not hash_changes:
            print(f"\n🎉 IDEMPOTENCE ACHIEVED after {iteration} iteration(s)")
            break
    else:
        print(f"\n❌ IDEMPOTENCE NOT ACHIEVED after {max_iterations} iterations")
        print("   The sync script continues to make changes on each run")
    
    # Final state summary
    print(f"\n📊 FINAL STATE:")
    final_status = get_git_status()
    if final_status:
        print(f"   Git status: Modified")
        final_diff = get_git_diff_stats()
        if final_diff:
            print(f"   Final changes: {final_diff}")
    else:
        print(f"   Git status: Clean")
    
    # Final duplicate marker check
    dup_code, dup_out, dup_err = check_duplicate_markers()
    if "Files with issues: 0" in dup_out:
        print("   ✅ No duplicate markers in final state")
    else:
        print("   ⚠️  Duplicate markers remain:")
        issues = dup_out.count('Found and fixed issues')
        print(f"      {issues} files with duplicate marker issues")
    
    return 0 if not final_status else 1

if __name__ == '__main__':
    exit(main()) 
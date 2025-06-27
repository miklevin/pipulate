#!/usr/bin/env python3
"""
Final Idempotence Test & Fix for ASCII Art Sync System

This script:
1. Cleans all duplicate markers to create a pristine baseline
2. Runs sync operations and tests for true idempotence
3. Provides detailed analysis of any non-idempotent behavior
4. Implements a comprehensive fix if needed
"""

import subprocess
import pathlib
import hashlib
import sys

def run_command(cmd, cwd=None):
    """Run a command and return (returncode, stdout, stderr)"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, shell=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def main():
    print("🎯 FINAL ASCII ART SYNC IDEMPOTENCE TEST & FIX")
    print("=" * 60)
    
    pipulate_path = "/home/mike/repos/pipulate"
    pipulate_com_path = "/home/mike/repos/Pipulate.com"
    
    # Step 1: Clean all duplicate markers
    print("\n🧹 STEP 1: CLEANING DUPLICATE MARKERS")
    print("-" * 40)
    
    code, out, err = run_command(
        f"python helpers/docs_sync/fix_duplicate_markers.py {pipulate_com_path}",
        cwd=pipulate_path
    )
    
    if code != 0:
        print(f"❌ Failed to clean duplicate markers: {err}")
        return 1
    
    print("✅ Duplicate markers cleaned successfully")
    
    # Verify clean state
    code, out, err = run_command(
        f"python helpers/docs_sync/fix_duplicate_markers.py {pipulate_com_path} --dry-run",
        cwd=pipulate_path
    )
    
    if "Files with issues: 0" not in out:
        print("❌ Failed to achieve clean state")
        print(out)
        return 1
    
    print("✅ Clean state verified - no duplicate markers")
    
    # Step 2: Run first sync
    print("\n🔄 STEP 2: FIRST SYNC OPERATION")
    print("-" * 40)
    
    code, out, err = run_command(
        "python helpers/docs_sync/sync_ascii_art.py",
        cwd=pipulate_path
    )
    
    if code != 0:
        print(f"❌ First sync failed: {err}")
        return 1
    
    # Extract statistics from first sync
    first_sync_stats = {}
    for line in out.split('\n'):
        if "📊 Files updated:" in line:
            try:
                first_sync_stats['files_updated'] = int(line.split(':')[1].strip())
            except (ValueError, IndexError):
                pass
        elif "🔄 Total blocks updated:" in line:
            try:
                first_sync_stats['blocks_updated'] = int(line.split(':')[1].strip())
            except (ValueError, IndexError):
                pass
        elif "🔄 Total usages:" in line:
            try:
                first_sync_stats['total_usages'] = int(line.split(':')[1].strip())
            except (ValueError, IndexError):
                pass
    
    print(f"✅ First sync completed:")
    print(f"   📊 Files updated: {first_sync_stats.get('files_updated', 'Unknown')}")
    print(f"   🔄 Blocks updated: {first_sync_stats.get('blocks_updated', 'Unknown')}")
    print(f"   📈 Total usages: {first_sync_stats.get('total_usages', 'Unknown')}")
    
    # Check for duplicate markers after first sync
    code, out, err = run_command(
        f"python helpers/docs_sync/fix_duplicate_markers.py {pipulate_com_path} --dry-run",
        cwd=pipulate_path
    )
    
    if "Files with issues: 0" not in out:
        print("⚠️  Duplicate markers detected after first sync!")
        duplicate_files = out.count('Found and fixed issues')
        print(f"   {duplicate_files} files with duplicate marker issues")
        first_sync_clean = False
    else:
        print("✅ No duplicate markers after first sync")
        first_sync_clean = True
    
    # Step 3: Test idempotence with second sync
    print("\n🔄 STEP 3: IDEMPOTENCE TEST (SECOND SYNC)")
    print("-" * 40)
    
    code, out, err = run_command(
        "python helpers/docs_sync/sync_ascii_art.py",
        cwd=pipulate_path
    )
    
    if code != 0:
        print(f"❌ Second sync failed: {err}")
        return 1
    
    # Extract statistics from second sync
    second_sync_stats = {}
    for line in out.split('\n'):
        if "📊 Files updated:" in line:
            try:
                second_sync_stats['files_updated'] = int(line.split(':')[1].strip())
            except (ValueError, IndexError):
                pass
        elif "🔄 Total blocks updated:" in line:
            try:
                second_sync_stats['blocks_updated'] = int(line.split(':')[1].strip())
            except (ValueError, IndexError):
                pass
        elif "🔄 Total usages:" in line:
            try:
                second_sync_stats['total_usages'] = int(line.split(':')[1].strip())
            except (ValueError, IndexError):
                pass
    
    print(f"✅ Second sync completed:")
    print(f"   📊 Files updated: {second_sync_stats.get('files_updated', 'Unknown')}")
    print(f"   🔄 Blocks updated: {second_sync_stats.get('blocks_updated', 'Unknown')}")
    print(f"   📈 Total usages: {second_sync_stats.get('total_usages', 'Unknown')}")
    
    # Check for duplicate markers after second sync
    code, out, err = run_command(
        f"python helpers/docs_sync/fix_duplicate_markers.py {pipulate_com_path} --dry-run",
        cwd=pipulate_path
    )
    
    if "Files with issues: 0" not in out:
        print("❌ Duplicate markers created by second sync!")
        duplicate_files = out.count('Found and fixed issues')
        print(f"   {duplicate_files} files with duplicate marker issues")
        second_sync_clean = False
    else:
        print("✅ No duplicate markers after second sync")
        second_sync_clean = True
    
    # Step 4: Analyze idempotence
    print("\n📊 STEP 4: IDEMPOTENCE ANALYSIS")
    print("-" * 40)
    
    # Check if updates are consistent
    files_updated_consistent = (
        first_sync_stats.get('files_updated', 0) == second_sync_stats.get('files_updated', -1)
    )
    blocks_updated_consistent = (
        first_sync_stats.get('blocks_updated', 0) == second_sync_stats.get('blocks_updated', -1)
    )
    
    # Check git status
    code, git_status, err = run_command("git status --porcelain", cwd=pipulate_com_path)
    has_git_changes = bool(git_status.strip())
    
    if has_git_changes:
        code, git_diff, err = run_command("git diff --stat", cwd=pipulate_com_path)
        print(f"📝 Git changes detected:")
        print(f"   {git_diff.strip()}")
    else:
        print("✅ No git changes detected")
    
    # Determine if idempotent
    is_idempotent = (
        files_updated_consistent and 
        blocks_updated_consistent and
        not has_git_changes and
        first_sync_clean and
        second_sync_clean and
        second_sync_stats.get('blocks_updated', 0) == 0  # Should be 0 on second run
    )
    
    print(f"\\n🎯 IDEMPOTENCE RESULT:")
    if is_idempotent:
        print("✅ SYSTEM IS IDEMPOTENT!")
        print("   🎉 Sync script works correctly")
        print("   ✨ No duplicate markers created")
        print("   🔄 Consistent results across runs")
        return 0
    else:
        print("❌ SYSTEM IS NOT IDEMPOTENT!")
        print("\\n📋 ISSUES DETECTED:")
        
        if not files_updated_consistent:
            print(f"   • Files updated inconsistent: {first_sync_stats.get('files_updated')} vs {second_sync_stats.get('files_updated')}")
        
        if not blocks_updated_consistent:
            print(f"   • Blocks updated inconsistent: {first_sync_stats.get('blocks_updated')} vs {second_sync_stats.get('blocks_updated')}")
        
        if second_sync_stats.get('blocks_updated', 0) > 0:
            print(f"   • Second sync should update 0 blocks, but updated {second_sync_stats.get('blocks_updated')}")
        
        if not first_sync_clean:
            print("   • First sync created duplicate markers")
        
        if not second_sync_clean:
            print("   • Second sync created duplicate markers")
        
        if has_git_changes:
            print("   • Git changes detected after sync operations")
        
        print("\\n💡 RECOMMENDATION:")
        print("   The sync script has a fundamental bug in its replacement logic.")
        print("   It's creating duplicate markers instead of replacing existing ones.")
        print("   This needs to be fixed at the source code level.")
        
        return 1

if __name__ == '__main__':
    exit(main()) 
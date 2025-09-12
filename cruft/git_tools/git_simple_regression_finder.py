#!/usr/bin/env python3
"""
Simple Git Regression Finder

A straightforward Python tool to iterate over git commits and spot when 
specific patterns changed in files. Perfect for Jupyter notebooks.

Usage:
    from git_simple_regression_finder import analyze_file_history
    
    # Show all commits that changed a file
    analyze_file_history("plugins/110_parameter_buster.py")
    
    # Find when "BQLv2" was added/removed
    find_pattern_changes("plugins/110_parameter_buster.py", "BQLv2")
"""

import subprocess


def get_file_at_commit(commit_hash, file_path):
    """
    Get file content at specific commit.
    
    Git command: git show COMMIT_HASH:FILE_PATH
    This shows the file content as it existed at that specific commit.
    """
    try:
        result = subprocess.run(['git', 'show', f'{commit_hash}:{file_path}'], 
                              capture_output=True, text=True, check=True)
        return result.stdout
    except:
        return None


def get_all_commits(file_path):
    """
    Get ALL commits that modified a file (no limit) with dates.
    
    Git command: git log --follow --format="%h %ad %s" --date=short -- FILE_PATH
    --follow: Track file even through renames
    --format: Custom format with hash, author date, subject
    --date=short: YYYY-MM-DD format
    -- FILE_PATH: Only show commits that touched this file
    """
    try:
        result = subprocess.run(['git', 'log', '--follow', '--format=%h %ad %s', '--date=short', '--', file_path], 
                              capture_output=True, text=True, check=True)
        commits = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split(' ', 2)
                if len(parts) >= 3:
                    hash_val = parts[0]
                    date_val = parts[1]
                    message = parts[2]
                    commits.append((hash_val, date_val, message))
        return commits
    except:
        return []


def get_commits(file_path, max_commits=30):
    """
    Get recent commits that modified a file (with limit) with dates.
    
    Git command: git log --format="%h %ad %s" --date=short -nMAX_COUNT -- FILE_PATH
    -n: Limit to MAX_COUNT most recent commits
    --format: Custom format with hash, author date, subject
    --date=short: YYYY-MM-DD format
    """
    try:
        result = subprocess.run(['git', 'log', '--format=%h %ad %s', '--date=short', f'-n{max_commits}', '--', file_path], 
                              capture_output=True, text=True, check=True)
        commits = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split(' ', 2)
                if len(parts) >= 3:
                    hash_val = parts[0]
                    date_val = parts[1]
                    message = parts[2]
                    commits.append((hash_val, date_val, message))
        return commits
    except:
        return []


def analyze_file_history(file_path):
    """
    Show ALL commits that changed a file - the main educational function.
    
    This is your starting point for regression hunting!
    
    Git equivalent: git log --follow --format="%h %ad %s" --date=short -- FILE_PATH
    """
    print(f"🔍 COMPLETE HISTORY ANALYSIS")
    print(f"📄 File: {file_path}")
    print("=" * 90)
    print("Git command equivalent: git log --follow --format='%h %ad %s' --date=short --", file_path)
    print("=" * 90)
    
    commits = get_all_commits(file_path)
    
    if not commits:
        print("❌ No commits found for this file")
        return []
    
    print(f"📊 Found {len(commits)} total commits that modified this file:")
    print()
    
    for i, (commit_hash, date_val, message) in enumerate(commits):
        # Get file size at this commit for context
        content = get_file_at_commit(commit_hash, file_path)
        size_info = f"({len(content)} chars)" if content else "(file missing)"
        
        print(f"{i+1:3}. {commit_hash} | {date_val} | {size_info:12} | {message}")
    
    print(f"\n✅ Analysis complete! Found {len(commits)} commits.")
    print("\n🎯 NEXT STEPS:")
    print("• Copy any hash to examine: get_file_at_commit('HASH', 'FILE_PATH')")
    print("• Compare two hashes: compare_commits('HASH1', 'HASH2', 'FILE_PATH')")
    print("• Search for patterns: find_pattern_changes('FILE_PATH', 'PATTERN')")
    
    return commits


def get_file_at_commit_display(commit_hash, file_path, max_lines=50):
    """
    Get and display file content at specific commit (truncated for readability).
    
    Git command: git show COMMIT_HASH:FILE_PATH
    """
    print(f"📄 File content at commit {commit_hash[:8]}:")
    print(f"📁 {file_path}")
    print("-" * 60)
    
    content = get_file_at_commit(commit_hash, file_path)
    if content:
        lines = content.split('\n')
        if len(lines) <= max_lines:
            print(content)
        else:
            print('\n'.join(lines[:max_lines]))
            print(f"\n... ({len(lines) - max_lines} more lines, {len(content)} total characters)")
            print(f"\n💡 To see full content: get_file_at_commit('{commit_hash}', '{file_path}')")
    else:
        print("❌ File not found at this commit")
    
    return content


def compare_commits(commit1, commit2, file_path):
    """
    Compare file content between two commits.
    
    Git command: git diff COMMIT1..COMMIT2 -- FILE_PATH
    """
    print(f"📝 COMPARING COMMITS")
    print(f"📄 File: {file_path}")
    print(f"🔄 {commit1[:8]} → {commit2[:8]}")
    print("=" * 60)
    print(f"Git command: git diff {commit1}..{commit2} -- {file_path}")
    print("=" * 60)
    
    try:
        result = subprocess.run(['git', 'diff', f'{commit1}..{commit2}', '--', file_path], 
                              capture_output=True, text=True, check=True)
        diff = result.stdout
        
        if diff:
            print(diff)
        else:
            print("❌ No differences found between these commits")
            
        return diff
    except Exception as e:
        print(f"❌ Error: {e}")
        return ""


def find_pattern_changes(file_path, pattern, max_commits=50):
    """
    Find when a pattern was added or removed from a file.
    
    This checks file content at each commit - no direct git equivalent,
    but uses: git show COMMIT:FILE for each commit
    """
    commits = get_commits(file_path, max_commits)
    print(f"🔍 PATTERN SEARCH")
    print(f"📄 File: {file_path}")
    print(f"🔎 Pattern: '{pattern}'")
    print("=" * 70)
    print(f"Checking {len(commits)} recent commits...")
    print("=" * 70)
    
    changes_found = 0
    
    for i, (commit_hash, date_val, message) in enumerate(commits):
        content = get_file_at_commit(commit_hash, file_path)
        if content is None:
            continue
            
        has_pattern = pattern in content
        
        # Check previous commit
        if i < len(commits) - 1:
            prev_hash, prev_date, prev_message = commits[i + 1]
            prev_content = get_file_at_commit(prev_hash, file_path)
            if prev_content:
                prev_has_pattern = pattern in prev_content
                
                if has_pattern != prev_has_pattern:
                    change_type = 'ADDED' if has_pattern else 'REMOVED'
                    print(f"{commit_hash[:8]} | {date_val} | {change_type:7} | {message[:45]}")
                    changes_found += 1
    
    if changes_found == 0:
        print("❌ No changes found for this pattern")
    else:
        print(f"\n✅ Found {changes_found} pattern changes")
    
    return changes_found


def show_recent_commits(file_path, count=10):
    """
    Show recent commits for a file.
    
    Git command: git log --format="%h %ad %s" --date=short -nCOUNT -- FILE_PATH
    """
    commits = get_commits(file_path, count)
    print(f"📊 RECENT {count} COMMITS")
    print(f"📄 File: {file_path}")
    print("=" * 70)
    print(f"Git command: git log --format='%h %ad %s' --date=short -n{count} -- {file_path}")
    print("=" * 70)
    
    for i, (commit_hash, date_val, message) in enumerate(commits):
        print(f"{i+1:2}. {commit_hash} | {date_val} | {message}")
    
    return commits


def find_size_changes(file_path, threshold_percent=20, max_commits=30):
    """
    Find commits where file size changed significantly.
    
    Uses git show COMMIT:FILE to get content size at each commit.
    """
    commits = get_commits(file_path, max_commits)
    print(f"📈 SIZE CHANGE ANALYSIS")
    print(f"📄 File: {file_path}")
    print(f"📊 Threshold: >{threshold_percent}% change")
    print("=" * 70)
    
    changes_found = 0
    
    for i, (commit_hash, date_val, message) in enumerate(commits):
        if i < len(commits) - 1:
            current_content = get_file_at_commit(commit_hash, file_path)
            prev_hash, prev_date, prev_message = commits[i + 1]
            prev_content = get_file_at_commit(prev_hash, file_path)
            
            if current_content and prev_content:
                current_size = len(current_content)
                prev_size = len(prev_content)
                
                if prev_size > 0:
                    change_percent = abs(current_size - prev_size) / prev_size * 100
                    
                    if change_percent > threshold_percent:
                        change_type = 'GREW' if current_size > prev_size else 'SHRANK'
                        print(f"{commit_hash[:8]} | {date_val} | {change_type:7} {change_percent:5.1f}% | {prev_size:5} → {current_size:5} | {message[:25]}")
                        changes_found += 1
    
    if changes_found == 0:
        print(f"❌ No size changes >{threshold_percent}% found")
    else:
        print(f"\n✅ Found {changes_found} significant size changes")
    
    return changes_found


# =============================================================================
# COPY/PASTE READY FUNCTIONS FOR JUPYTER NOTEBOOKS
# =============================================================================

def quick_analysis(filename):
    """
    One-stop function for quick file analysis. Perfect for Jupyter!
    
    Usage: quick_analysis("plugins/110_parameter_buster.py")
    """
    print("🚀 QUICK REGRESSION ANALYSIS")
    print("=" * 90)
    
    # 1. Show complete history
    analyze_file_history(filename)
    
    print("\n" + "="*90)
    
    # 2. Show recent commits with more detail
    show_recent_commits(filename, 10)
    
    print("\n" + "="*90)
    
    # 3. Look for size changes
    find_size_changes(filename, 15.0)


def hunt_errors(filename):
    """
    Hunt for error-related patterns in file history.
    
    Usage: hunt_errors("plugins/110_parameter_buster.py")
    """
    error_patterns = [
        "error",
        "Error", 
        "ERROR",
        "exception",
        "Exception",
        "failed",
        "Failed",
        "broken",
        "Broken",
        "NotImplementedError",
        "TODO",
        "FIXME",
        "hack",
        "Hack"
    ]
    
    print("🚨 ERROR PATTERN HUNT")
    print(f"📄 File: {filename}")
    print("=" * 70)
    
    total_changes = 0
    for pattern in error_patterns:
        changes = find_pattern_changes(filename, pattern, 30)
        total_changes += changes
        if changes > 0:
            print()  # Add spacing between found patterns
    
    print(f"\n🎯 SUMMARY: Found {total_changes} total error-related changes")


# Example usage that's copy/paste ready for Jupyter
if __name__ == "__main__":
    # Change this to any file you want to analyze
    target_file = "plugins/110_parameter_buster.py"
    
    print("🔍 Git Regression Finder - Educational Demo")
    print("=" * 90)
    print("Copy/paste any of these into a Jupyter notebook:")
    print()
    print(f"analyze_file_history('{target_file}')")
    print(f"quick_analysis('{target_file}')")
    print(f"hunt_errors('{target_file}')")
    print(f"find_pattern_changes('{target_file}', 'YOUR_PATTERN')")
    print(f"compare_commits('HASH1', 'HASH2', '{target_file}')")
    print()
    print("Running example analysis...")
    print("=" * 90)
    
    # Run the analysis
    analyze_file_history(target_file) 
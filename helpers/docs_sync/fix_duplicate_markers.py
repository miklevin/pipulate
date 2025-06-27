#!/usr/bin/env python3
"""
Fix Duplicate ASCII Art Markers

This script detects and fixes duplicate START/END markers that cause exponential 
duplication when sync_ascii_art.py runs.
"""

import re
import pathlib
import argparse

def clean_duplicate_markers(content):
    """Remove duplicate markers, keeping only valid single pairs"""
    
    # Find all markers with positions
    start_pattern = r'<!-- START_ASCII_ART: ([^>]+) -->'
    end_pattern = r'<!-- END_ASCII_ART: ([^>]+) -->'
    
    start_matches = list(re.finditer(start_pattern, content))
    end_matches = list(re.finditer(end_pattern, content))
    
    # Group by marker name
    start_by_marker = {}
    end_by_marker = {}
    
    for match in start_matches:
        marker = match.group(1)
        if marker not in start_by_marker:
            start_by_marker[marker] = []
        start_by_marker[marker].append(match)
    
    for match in end_matches:
        marker = match.group(1)
        if marker not in end_by_marker:
            end_by_marker[marker] = []
        end_by_marker[marker].append(match)
    
    # Find markers with duplicates
    issues = []
    fixes = []
    
    for marker in set(start_by_marker.keys()) | set(end_by_marker.keys()):
        start_count = len(start_by_marker.get(marker, []))
        end_count = len(end_by_marker.get(marker, []))
        
        if start_count > 1:
            issues.append(f"Duplicate START markers for '{marker}': {start_count} instances")
        if end_count > 1:
            issues.append(f"Duplicate END markers for '{marker}': {end_count} instances")
        if start_count != end_count:
            issues.append(f"Mismatched markers for '{marker}': {start_count} START vs {end_count} END")
    
    if not issues:
        return content, []
    
    # Strategy: Remove all instances of problematic markers and replace with clean placeholders
    for marker in set(start_by_marker.keys()) | set(end_by_marker.keys()):
        start_instances = start_by_marker.get(marker, [])
        end_instances = end_by_marker.get(marker, [])
        
        if len(start_instances) > 1 or len(end_instances) > 1:
            # Remove all instances of this marker
            marker_pattern = r'<!-- (?:START|END)_ASCII_ART: ' + re.escape(marker) + r' -->'
            
            # Count removals
            removed_count = len(re.findall(marker_pattern, content))
            content = re.sub(marker_pattern, '', content)
            
            # Clean up empty lines left behind
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
            
            fixes.append(f"Removed {removed_count} corrupted markers for '{marker}'")
            fixes.append(f"Added clean placeholder for '{marker}'")
            
            # Add a clean placeholder at the end of the content
            clean_placeholder = f"""
<!-- START_ASCII_ART: {marker} -->
[Placeholder - run sync_ascii_art.py to populate]
<!-- END_ASCII_ART: {marker} -->
"""
            content += clean_placeholder
    
    return content, fixes

def process_file(file_path, dry_run=False):
    """Process a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except Exception as e:
        return f"❌ Error reading {file_path}: {e}"
    
    cleaned_content, fixes = clean_duplicate_markers(original_content)
    
    if not fixes:
        return f"✅ {file_path.name}: No issues found"
    
    result = f"📄 {file_path.name}: Found and fixed issues"
    for fix in fixes:
        result += f"\n   • {fix}"
    
    if dry_run:
        result += "\n   🔍 DRY RUN: No changes made"
        return result
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        result += "\n   ✅ File updated successfully"
    except Exception as e:
        result += f"\n   ❌ Error writing file: {e}"
    
    return result

def main():
    parser = argparse.ArgumentParser(description='Fix duplicate ASCII art markers')
    parser.add_argument('target_directory', help='Directory to scan for markdown files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be fixed without making changes')
    
    args = parser.parse_args()
    
    target_path = pathlib.Path(args.target_directory)
    if not target_path.exists():
        print(f"❌ Directory not found: {target_path}")
        return 1
    
    markdown_files = list(target_path.rglob('*.md'))
    
    if not markdown_files:
        print(f"📄 No markdown files found in {target_path}")
        return 0
    
    print(f"🔍 Scanning {len(markdown_files)} markdown files...")
    if args.dry_run:
        print("🔍 DRY RUN MODE: No changes will be made")
    print()
    
    files_with_issues = 0
    
    for md_file in sorted(markdown_files):
        result = process_file(md_file, args.dry_run)
        if "Found and fixed issues" in result or "No issues found" in result:
            if "Found and fixed issues" in result:
                files_with_issues += 1
                print(result)
            # Only show clean files in verbose mode
        else:
            print(result)  # Show errors
    
    print()
    print("📊 SUMMARY:")
    print(f"   📄 Files scanned: {len(markdown_files)}")
    print(f"   ⚠️  Files with issues: {files_with_issues}")
    
    if files_with_issues > 0:
        if args.dry_run:
            print(f"   🔍 DRY RUN: {files_with_issues} files would be fixed")
        else:
            print(f"   ✅ Files cleaned successfully")
            print(f"   💡 Run sync_ascii_art.py to populate the cleaned markers")
    
    return 0

if __name__ == '__main__':
    exit(main()) 
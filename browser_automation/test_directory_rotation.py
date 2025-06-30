#!/usr/bin/env python3
"""
🔄 Directory Rotation Test Script

Test script to verify that the browser_automation/looking_at directory rotation
system works correctly. This script creates test files and demonstrates the
rotation behavior.

Usage:
    python test_directory_rotation.py

This will:
1. Create sample files in looking_at directory 
2. Demonstrate rotation with multiple runs
3. Show the history preservation working
4. Verify cleanup of old directories beyond limit
"""

import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# Configuration constants (matching server.py)
MAX_ROLLED_LOOKING_AT_DIRS = 10  # Keep last 10 AI perception states


def rotate_looking_at_directory(looking_at_path: Path = None, max_rolled_dirs: int = None) -> bool:
    """
    🔄 DIRECTORY ROTATION SYSTEM (Standalone Version)
    
    Rotates the browser_automation/looking_at directory before each new browser scrape.
    This preserves AI perception history across multiple look-at operations.
    
    Similar to log rotation but for entire directories:
    - looking_at becomes looking_at-1  
    - looking_at-1 becomes looking_at-2
    - etc. up to max_rolled_dirs
    - Oldest directories beyond limit are deleted
    
    Args:
        looking_at_path: Path to the looking_at directory (default: browser_automation/looking_at)
        max_rolled_dirs: Maximum number of historical directories to keep
        
    Returns:
        bool: True if rotation successful, False if failed
        
    This prevents AI assistants from losing sight of previously captured states
    and allows them to review their automation history for better decisions.
    """
    
    if looking_at_path is None:
        looking_at_path = Path('browser_automation') / 'looking_at'
    else:
        looking_at_path = Path(looking_at_path)
    
    if max_rolled_dirs is None:
        max_rolled_dirs = MAX_ROLLED_LOOKING_AT_DIRS

    try:
        # Ensure the parent directory exists
        looking_at_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Clean up old numbered directories beyond our limit
        for i in range(max_rolled_dirs + 1, 100):
            old_dir = looking_at_path.parent / f'{looking_at_path.name}-{i}'
            if old_dir.exists():
                try:
                    shutil.rmtree(old_dir)
                    print(f'🧹 FINDER_TOKEN: DIRECTORY_CLEANUP - Removed old directory: {old_dir.name}')
                except Exception as e:
                    print(f'⚠️ Failed to delete old directory {old_dir}: {e}')
        
        # Rotate existing directories: looking_at-1 → looking_at-2, etc.
        if looking_at_path.exists() and any(looking_at_path.iterdir()):  # Only rotate if directory exists and has contents
            for i in range(max_rolled_dirs - 1, 0, -1):
                old_path = looking_at_path.parent / f'{looking_at_path.name}-{i}'
                new_path = looking_at_path.parent / f'{looking_at_path.name}-{i + 1}'
                if old_path.exists():
                    try:
                        old_path.rename(new_path)
                        print(f'📁 FINDER_TOKEN: DIRECTORY_ROTATION - Rotated: {old_path.name} → {new_path.name}')
                    except Exception as e:
                        print(f'⚠️ Failed to rotate directory {old_path}: {e}')
            
            # Move current looking_at to looking_at-1
            try:
                archived_path = looking_at_path.parent / f'{looking_at_path.name}-1'
                looking_at_path.rename(archived_path)
                print(f'🎯 FINDER_TOKEN: DIRECTORY_ARCHIVE - Archived current perception: {looking_at_path.name} → {archived_path.name}')
            except Exception as e:
                print(f'⚠️ Failed to archive current {looking_at_path}: {e}')
                return False
        
        # Create fresh looking_at directory
        looking_at_path.mkdir(parents=True, exist_ok=True)
        print(f'✨ FINDER_TOKEN: DIRECTORY_REFRESH - Fresh perception directory ready: {looking_at_path}')
        
        return True
        
    except Exception as e:
        print(f'❌ FINDER_TOKEN: DIRECTORY_ROTATION_ERROR - Failed to rotate directories: {e}')
        return False


def create_test_files(looking_at_dir: Path, test_name: str):
    """Create test files in the looking_at directory"""
    looking_at_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test files similar to what browser automation creates
    test_data = {
        'test_name': test_name,
        'timestamp': datetime.now().isoformat(),
        'url': f'https://example.com/{test_name}',
        'title': f'Test Page {test_name}'
    }
    
    # headers.json
    with open(looking_at_dir / 'headers.json', 'w') as f:
        json.dump(test_data, f, indent=2)
    
    # simple_dom.html  
    with open(looking_at_dir / 'simple_dom.html', 'w') as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>Test {test_name}</title>
</head>
<body>
    <h1>Test Page: {test_name}</h1>
    <p>Created at: {test_data['timestamp']}</p>
    <div data-testid="test-element">Test content for {test_name}</div>
</body>
</html>""")
    
    # dom.html (fuller version)
    with open(looking_at_dir / 'dom.html', 'w') as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>Test {test_name}</title>
    <script>console.log('Test {test_name}');</script>
    <style>body {{ font-family: Arial; }}</style>
</head>
<body>
    <h1>Test Page: {test_name}</h1>
    <p>Created at: {test_data['timestamp']}</p>
    <div data-testid="test-element">Test content for {test_name}</div>
    <script>document.body.style.backgroundColor = 'lightblue';</script>
</body>
</html>""")
    
    # Test screenshot placeholder
    with open(looking_at_dir / 'screenshot.png', 'wb') as f:
        f.write(b'PNG_PLACEHOLDER_' + test_name.encode())
    
    print(f"📁 Created test files for: {test_name}")
    return list(looking_at_dir.iterdir())


def list_directory_structure(base_dir: Path):
    """List the current directory structure for visualization"""
    print("\n📋 Current Directory Structure:")
    print("=" * 50)
    
    if not base_dir.exists():
        print("❌ Base directory does not exist")
        return
    
    # List all looking_at directories
    directories = []
    for item in base_dir.iterdir():
        if item.is_dir() and item.name.startswith('looking_at'):
            directories.append(item)
    
    directories.sort(key=lambda x: x.name)
    
    for directory in directories:
        files = list(directory.iterdir()) if directory.exists() else []
        print(f"📁 {directory.name}/ ({len(files)} files)")
        
        # Show sample content from headers.json if it exists
        headers_file = directory / 'headers.json'
        if headers_file.exists():
            try:
                with open(headers_file, 'r') as f:
                    data = json.load(f)
                    test_name = data.get('test_name', 'unknown')
                    timestamp = data.get('timestamp', 'unknown')
                    print(f"   🎯 Test: {test_name} | Time: {timestamp[:19]}")
            except:
                print(f"   ⚠️ Could not read headers.json")
        
        for file in sorted(files)[:3]:  # Show first 3 files
            size = file.stat().st_size if file.exists() else 0
            print(f"   📄 {file.name} ({size} bytes)")
        if len(files) > 3:
            print(f"   ... and {len(files) - 3} more files")
    
    print("=" * 50)


def main():
    """Main test function"""
    print("🔄 DIRECTORY ROTATION TEST")
    print("=" * 60)
    
    base_dir = Path('browser_automation')
    looking_at_dir = base_dir / 'looking_at'
    
    print(f"📍 Testing directory rotation at: {looking_at_dir}")
    print(f"🔢 Maximum rolled directories: {MAX_ROLLED_LOOKING_AT_DIRS}")
    
    # Test sequence
    test_runs = [
        "initial",
        "second_run", 
        "third_run",
        "fourth_run",
        "fifth_run"
    ]
    
    for i, test_name in enumerate(test_runs):
        print(f"\n🚀 TEST RUN #{i+1}: {test_name}")
        print("-" * 40)
        
        # Create test files first
        test_files = create_test_files(looking_at_dir, test_name)
        print(f"✅ Created {len(test_files)} test files")
        
        # Show structure before rotation
        if i > 0:  # Skip for first run since there's nothing to show
            list_directory_structure(base_dir)
        
        # Wait a moment to make timestamps different
        time.sleep(1)
        
        # If this isn't the last run, rotate for next iteration
        if i < len(test_runs) - 1:
            print(f"\n🔄 Rotating directories before next test run...")
            rotation_success = rotate_looking_at_directory(looking_at_dir)
            
            if rotation_success:
                print("✅ Directory rotation successful")
            else:
                print("❌ Directory rotation failed")
        
    # Final structure
    print(f"\n🏁 FINAL DIRECTORY STRUCTURE")
    list_directory_structure(base_dir)
    
    print(f"\n🎯 SUMMARY:")
    print(f"- Executed {len(test_runs)} test runs")
    print(f"- Each run created files, then rotated directory")
    print(f"- Preserved history up to {MAX_ROLLED_LOOKING_AT_DIRS} previous states")
    print(f"- Older states beyond limit should be cleaned up")
    
    # Test accessing historical data
    print(f"\n📖 HISTORICAL DATA ACCESS TEST:")
    for i in range(1, min(4, MAX_ROLLED_LOOKING_AT_DIRS + 1)):
        historical_dir = base_dir / f'looking_at-{i}'
        if historical_dir.exists():
            headers_file = historical_dir / 'headers.json'
            if headers_file.exists():
                try:
                    with open(headers_file, 'r') as f:
                        data = json.load(f)
                        test_name = data.get('test_name', 'unknown')
                        print(f"  📚 looking_at-{i}: Contains '{test_name}' test data")
                except:
                    print(f"  ⚠️ looking_at-{i}: Headers file exists but unreadable")
            else:
                print(f"  📁 looking_at-{i}: Directory exists but no headers file")
        else:
            print(f"  ❌ looking_at-{i}: Directory does not exist")
    
    print(f"\n✨ Directory rotation test complete!")
    print(f"🔍 Use 'ls -la browser_automation/looking_at*' to see all directories")


if __name__ == "__main__":
    print(f"✅ Using standalone rotation function (MAX_DIRS: {MAX_ROLLED_LOOKING_AT_DIRS})")
    main() 
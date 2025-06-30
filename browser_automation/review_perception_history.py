#!/usr/bin/env python3
"""
🔍 Browser Automation Perception History Reviewer

Utility script for AI assistants to review their previous browser automation states
stored in the rotated looking_at directories. This helps AI assistants understand
their recent automation history and make better decisions.

Usage:
    python review_perception_history.py [options]
    
    --list                 List all available perception states
    --show N               Show detailed info for looking_at-N directory
    --compare N M          Compare two perception states  
    --recent N             Show the N most recent states (default: 3)
    --urls                 Show just the URLs from recent states
    --titles               Show just the page titles from recent states
    --summary              Show a compact summary of all states

Examples:
    python review_perception_history.py --recent 5
    python review_perception_history.py --show 2
    python review_perception_history.py --compare 1 3
    python review_perception_history.py --urls
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def find_perception_directories(base_dir: Path = None):
    """Find all available perception directories"""
    if base_dir is None:
        base_dir = Path('browser_automation')
    
    directories = []
    
    # Include current looking_at if it exists and has content
    current_dir = base_dir / 'looking_at'
    if current_dir.exists() and any(current_dir.iterdir()):
        directories.append(('current', current_dir))
    
    # Find all numbered directories
    for item in base_dir.iterdir():
        if item.is_dir() and item.name.startswith('looking_at-'):
            try:
                number = int(item.name.split('-')[1])
                directories.append((number, item))
            except (ValueError, IndexError):
                continue
    
    # Sort by number (current first, then 1, 2, 3...)
    directories.sort(key=lambda x: (0 if x[0] == 'current' else x[0]))
    
    return directories


def read_perception_metadata(directory: Path):
    """Read metadata from a perception directory"""
    metadata = {
        'directory': directory.name,
        'exists': directory.exists(),
        'file_count': 0,
        'timestamp': 'unknown',
        'url': 'unknown', 
        'title': 'unknown',
        'step': None,
        'test_name': None,
        'files': []
    }
    
    if not directory.exists():
        return metadata
    
    # Count files
    files = list(directory.iterdir())
    metadata['file_count'] = len(files)
    metadata['files'] = [f.name for f in files]
    
    # Try to read headers.json for metadata
    headers_file = directory / 'headers.json'
    if headers_file.exists():
        try:
            with open(headers_file, 'r') as f:
                data = json.load(f)
                metadata['timestamp'] = data.get('timestamp', 'unknown')
                metadata['url'] = data.get('url', 'unknown')
                metadata['title'] = data.get('title', 'unknown')
                metadata['step'] = data.get('step', None)
                metadata['test_name'] = data.get('test_name', None)
        except (json.JSONDecodeError, IOError):
            pass
    
    # Get directory modification time as fallback
    if metadata['timestamp'] == 'unknown':
        try:
            mtime = directory.stat().st_mtime
            metadata['timestamp'] = datetime.fromtimestamp(mtime).isoformat()
        except:
            pass
    
    return metadata


def list_all_states():
    """List all available perception states"""
    print("🔍 BROWSER AUTOMATION PERCEPTION HISTORY")
    print("=" * 60)
    
    directories = find_perception_directories()
    
    if not directories:
        print("❌ No perception directories found")
        print("💡 Run some browser automation to create perception history")
        return
    
    print(f"📊 Found {len(directories)} perception states:\n")
    
    for label, directory in directories:
        metadata = read_perception_metadata(directory)
        
        if label == 'current':
            print(f"🎯 CURRENT (looking_at/)")
        else:
            print(f"📚 HISTORY #{label} (looking_at-{label}/)")
        
        print(f"   📁 Files: {metadata['file_count']}")
        print(f"   🌐 URL: {metadata['url']}")
        print(f"   📄 Title: {metadata['title']}")
        print(f"   ⏰ Time: {metadata['timestamp'][:19] if metadata['timestamp'] != 'unknown' else 'unknown'}")
        
        if metadata['step']:
            print(f"   🔄 Step: {metadata['step']}")
        if metadata['test_name']:
            print(f"   🧪 Test: {metadata['test_name']}")
        
        print()


def show_detailed_state(state_number):
    """Show detailed information about a specific state"""
    directories = find_perception_directories()
    
    # Find the requested state
    target_dir = None
    if state_number == 0 or state_number == 'current':
        for label, directory in directories:
            if label == 'current':
                target_dir = directory
                break
    else:
        for label, directory in directories:
            if label == state_number:
                target_dir = directory
                break
    
    if target_dir is None:
        print(f"❌ Perception state {state_number} not found")
        print("💡 Use --list to see available states")
        return
    
    metadata = read_perception_metadata(target_dir)
    
    print(f"🔍 DETAILED VIEW: {metadata['directory']}")
    print("=" * 50)
    
    print(f"📁 Directory: {target_dir}")
    print(f"📊 File Count: {metadata['file_count']}")
    print(f"🌐 URL: {metadata['url']}")
    print(f"📄 Title: {metadata['title']}")
    print(f"⏰ Timestamp: {metadata['timestamp']}")
    
    if metadata['step']:
        print(f"🔄 Workflow Step: {metadata['step']}")
    if metadata['test_name']:
        print(f"🧪 Test Name: {metadata['test_name']}")
    
    print(f"\n📋 Files in directory:")
    for filename in sorted(metadata['files']):
        filepath = target_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"   📄 {filename} ({size:,} bytes)")
            
            # Show preview for text files
            if filename.endswith('.html') and size < 5000:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()[:200]
                        if len(content) == 200:
                            content += "..."
                        print(f"      📝 Preview: {content.replace(chr(10), ' ')}")
                except:
                    pass
        else:
            print(f"   ❌ {filename} (missing)")


def compare_states(state1, state2):
    """Compare two perception states"""
    directories = find_perception_directories()
    
    # Find both states
    dir1 = dir2 = None
    for label, directory in directories:
        if label == state1 or (state1 == 'current' and label == 'current'):
            dir1 = directory
        if label == state2 or (state2 == 'current' and label == 'current'):
            dir2 = directory
    
    if dir1 is None:
        print(f"❌ Perception state {state1} not found")
        return
    if dir2 is None:
        print(f"❌ Perception state {state2} not found")
        return
    
    meta1 = read_perception_metadata(dir1)
    meta2 = read_perception_metadata(dir2)
    
    print(f"🔍 COMPARING: {meta1['directory']} vs {meta2['directory']}")
    print("=" * 60)
    
    print(f"📊 STATE 1: {meta1['directory']}")
    print(f"   🌐 URL: {meta1['url']}")
    print(f"   📄 Title: {meta1['title']}")
    print(f"   ⏰ Time: {meta1['timestamp'][:19] if meta1['timestamp'] != 'unknown' else 'unknown'}")
    print(f"   📁 Files: {meta1['file_count']}")
    
    print(f"\n📊 STATE 2: {meta2['directory']}")
    print(f"   🌐 URL: {meta2['url']}")
    print(f"   📄 Title: {meta2['title']}")
    print(f"   ⏰ Time: {meta2['timestamp'][:19] if meta2['timestamp'] != 'unknown' else 'unknown'}")
    print(f"   📁 Files: {meta2['file_count']}")
    
    print(f"\n🔍 DIFFERENCES:")
    if meta1['url'] != meta2['url']:
        print(f"   🌐 URL changed: {meta1['url']} → {meta2['url']}")
    else:
        print(f"   ✅ Same URL: {meta1['url']}")
    
    if meta1['title'] != meta2['title']:
        print(f"   📄 Title changed: {meta1['title']} → {meta2['title']}")
    else:
        print(f"   ✅ Same title: {meta1['title']}")
    
    files1 = set(meta1['files'])
    files2 = set(meta2['files'])
    common_files = files1 & files2
    only_in_1 = files1 - files2
    only_in_2 = files2 - files1
    
    print(f"   📁 Common files: {len(common_files)}")
    if only_in_1:
        print(f"   ➖ Only in state 1: {', '.join(only_in_1)}")
    if only_in_2:
        print(f"   ➕ Only in state 2: {', '.join(only_in_2)}")


def show_recent_states(count=3):
    """Show the N most recent perception states"""
    directories = find_perception_directories()
    
    if not directories:
        print("❌ No perception states found")
        return
    
    # Take the first N directories (they're sorted with most recent first)
    recent = directories[:count]
    
    print(f"🕐 {len(recent)} MOST RECENT PERCEPTION STATES")
    print("=" * 50)
    
    for i, (label, directory) in enumerate(recent):
        metadata = read_perception_metadata(directory)
        
        if label == 'current':
            print(f"🎯 #{i+1} CURRENT")
        else:
            print(f"📚 #{i+1} HISTORY-{label}")
        
        print(f"   🌐 {metadata['url']}")
        print(f"   📄 {metadata['title']}")
        print(f"   ⏰ {metadata['timestamp'][:19] if metadata['timestamp'] != 'unknown' else 'unknown'}")
        print()


def show_urls_only():
    """Show just the URLs from recent states"""
    directories = find_perception_directories()
    
    print("🌐 RECENT URLS:")
    for label, directory in directories[:5]:  # Show top 5
        metadata = read_perception_metadata(directory)
        label_str = 'CURRENT' if label == 'current' else f'HIST-{label}'
        print(f"   {label_str}: {metadata['url']}")


def show_titles_only():
    """Show just the page titles from recent states"""
    directories = find_perception_directories()
    
    print("📄 RECENT TITLES:")
    for label, directory in directories[:5]:  # Show top 5
        metadata = read_perception_metadata(directory)
        label_str = 'CURRENT' if label == 'current' else f'HIST-{label}'
        print(f"   {label_str}: {metadata['title']}")


def show_summary():
    """Show a compact summary of all states"""
    directories = find_perception_directories()
    
    if not directories:
        print("❌ No perception states found")
        return
    
    print(f"📋 PERCEPTION HISTORY SUMMARY ({len(directories)} states)")
    print("=" * 60)
    
    for label, directory in directories:
        metadata = read_perception_metadata(directory)
        label_str = 'CURRENT' if label == 'current' else f'H{label}'
        
        # Truncate long URLs and titles
        url = metadata['url'][:40] + '...' if len(metadata['url']) > 40 else metadata['url']
        title = metadata['title'][:30] + '...' if len(metadata['title']) > 30 else metadata['title']
        time_str = metadata['timestamp'][:16] if metadata['timestamp'] != 'unknown' else 'unknown'
        
        print(f"{label_str:>7} | {time_str:>16} | {url:>43} | {title}")


def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Review browser automation perception history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python review_perception_history.py --list
  python review_perception_history.py --recent 5
  python review_perception_history.py --show 2
  python review_perception_history.py --compare 1 3
  python review_perception_history.py --urls
        """
    )
    
    parser.add_argument('--list', action='store_true', help='List all available perception states')
    parser.add_argument('--show', type=int, metavar='N', help='Show detailed info for state N')
    parser.add_argument('--compare', nargs=2, type=int, metavar=('N', 'M'), help='Compare states N and M')
    parser.add_argument('--recent', type=int, metavar='N', default=3, help='Show N most recent states')
    parser.add_argument('--urls', action='store_true', help='Show just URLs from recent states')
    parser.add_argument('--titles', action='store_true', help='Show just titles from recent states')
    parser.add_argument('--summary', action='store_true', help='Show compact summary of all states')
    
    args = parser.parse_args()
    
    # If no arguments, show recent states
    if len(sys.argv) == 1:
        show_recent_states(args.recent)
        return
    
    if args.list:
        list_all_states()
    elif args.show is not None:
        show_detailed_state(args.show)
    elif args.compare:
        compare_states(args.compare[0], args.compare[1])
    elif args.urls:
        show_urls_only()
    elif args.titles:
        show_titles_only()
    elif args.summary:
        show_summary()
    else:
        show_recent_states(args.recent)


if __name__ == "__main__":
    main() 
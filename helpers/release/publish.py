#!/usr/bin/env python3
"""
Pipulate Master Release Orchestrator

A comprehensive release pipeline that handles:
1. Version synchronization across all files
2. ASCII art documentation synchronization  
3. AI-generated commit messages via local LLM
4. Git operations and PyPI publishing

Usage:
  python helpers/release/publish.py --release -m "Custom message"
  python helpers/release/publish.py --release --force -m "Force republish"
  python helpers/release/publish.py --release --ai-commit  # Use AI for commit message
"""
import argparse
import subprocess
import sys
import re
import json
import requests
from pathlib import Path

# Rich table imports for beautiful output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("💡 Install 'rich' for beautiful table output: pip install rich")

# --- Configuration ---
try:
    PIPULATE_ROOT = Path(__file__).parent.parent.parent.resolve()
except FileNotFoundError:
    print("Error: Could not resolve script path.")
    sys.exit(1)

INIT_PY_PATH = PIPULATE_ROOT / "__init__.py"
# Add Pipulate.com path configuration
PIPULATE_COM_ROOT = PIPULATE_ROOT.parent / "Pipulate.com"

def run_command(cmd, cwd=PIPULATE_ROOT, capture=False, check=True, shell=False):
    """Runs a command and handles errors."""
    print(f"🏃 Running: {' '.join(cmd) if not shell else cmd} in {cwd}")
    try:
        result = subprocess.run(cmd, cwd=str(cwd), capture_output=capture, text=True, check=check, shell=shell)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(cmd) if not shell else cmd}", file=sys.stderr)
        sys.exit(1)

def get_current_version():
    """Gets the version from pipulate/__init__.py."""
    content = INIT_PY_PATH.read_text()
    match = re.search(r"__version__\s*=\s*[\"']([^\"']+)[\"']", content)
    if not match:
        raise RuntimeError("Could not find __version__ in __init__.py")
    return match.group(1)

def run_version_sync():
    """Runs the version synchronization script."""
    print("\n🔄 Step 1: Synchronizing versions across all files...")
    version_sync_script = PIPULATE_ROOT / "helpers" / "release" / "version_sync.py"
    if not version_sync_script.exists():
        print("❌ version_sync.py not found, skipping version sync")
        return False
    
    try:
        run_command(["python", str(version_sync_script)])
        print("✅ Version synchronization complete")
        return True
    except Exception as e:
        print(f"⚠️  Version sync failed: {e}")
        return False

def run_ascii_art_sync():
    """Runs the ASCII art documentation synchronization and captures statistics."""
    print("\n📚 Step 2: Synchronizing ASCII art documentation...")
    ascii_sync_script = PIPULATE_ROOT / "helpers" / "docs_sync" / "sync_ascii_art.py"
    if not ascii_sync_script.exists():
        print("❌ sync_ascii_art.py not found, skipping documentation sync")
        return False, None
    
    try:
        result = run_command([".venv/bin/python", str(ascii_sync_script)], capture=True)
        output = result.stdout
        
        # Parse statistics from output
        stats = parse_ascii_art_stats(output)
        
        print("✅ ASCII art documentation synchronization complete")
        return True, stats
    except Exception as e:
        print(f"⚠️  Documentation sync failed: {e}")
        return False, None

def parse_ascii_art_stats(output):
    """Parse ASCII art synchronization statistics from output."""
    stats = {
        'files_updated': 0,
        'total_blocks_updated': 0,
        'ascii_blocks_found': 0,
        'used_blocks': 0,
        'unused_blocks': 0,
        'coverage_percentage': 0.0,
        'heuristic_candidates': 0,
        'quality_candidates': 0,
        'unknown_markers': 0,
        'markdown_files_scanned': 0
    }
    
    try:
        import re
        
        # Extract key statistics using regex patterns
        patterns = {
            'files_updated': r'📊 Files updated:\s*(\d+)',
            'total_blocks_updated': r'🔄 Total blocks updated:\s*(\d+)',
            'ascii_blocks_found': r'✅ Found (\d+) ASCII blocks in README\.md',
            'markdown_files_scanned': r'🔍 Found (\d+) markdown files',
            'used_blocks': r'✅ Used blocks:\s*(\d+)',
            'unused_blocks': r'📝 Unused blocks:\s*(\d+)',
            'coverage_percentage': r'Used blocks:\s*\d+ \((\d+\.?\d*)%\)',
            'heuristic_candidates': r'Found (\d+) potential ASCII art blocks in naked fenced code blocks',
            'quality_candidates': r'HIGH-QUALITY CANDIDATES \((\d+)\)',
            'unknown_markers': r'UNKNOWN MARKERS FOUND \((\d+)\)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, output)
            if match:
                if key == 'coverage_percentage':
                    stats[key] = float(match.group(1))
                else:
                    stats[key] = int(match.group(1))
    
    except Exception as e:
        print(f"⚠️  Failed to parse ASCII art statistics: {e}")
    
    return stats

def display_ascii_art_stats(stats):
    """Display ASCII art synchronization statistics in a beautiful rich table."""
    if not RICH_AVAILABLE or not stats:
        # Fallback to simple text display
        if stats:
            print("\n📊 ASCII ART SYNC STATISTICS:")
            print(f"   📄 Markdown files scanned: {stats['markdown_files_scanned']}")
            print(f"   📦 ASCII blocks found: {stats['ascii_blocks_found']}")
            print(f"   ✅ Used blocks: {stats['used_blocks']}")
            print(f"   📝 Unused blocks: {stats['unused_blocks']}")
            print(f"   📊 Coverage: {stats['coverage_percentage']:.1f}%")
            print(f"   🔄 Files updated: {stats['files_updated']}")
            print(f"   🎯 Blocks updated: {stats['total_blocks_updated']}")
        return
    
    console = Console()
    
    # Create ASCII art statistics table
    table = Table(
        title="📚 ASCII Art Sync Statistics",
        box=box.ROUNDED,
        title_style="bold blue",
        header_style="bold cyan",
        show_header=True,
        show_lines=True,
        expand=True
    )
    
    table.add_column("Metric", style="bold yellow", width=25)
    table.add_column("Value", style="white", width=15)
    table.add_column("Status", justify="center", width=15)
    
    # Add rows with appropriate status indicators
    coverage = stats['coverage_percentage']
    coverage_status = "🎯 Excellent" if coverage >= 80 else "⚡ Good" if coverage >= 60 else "📈 Improving"
    coverage_color = "green" if coverage >= 80 else "yellow" if coverage >= 60 else "red"
    
    table.add_row(
        "📄 Markdown Files Scanned",
        str(stats['markdown_files_scanned']),
        "🔍 Complete"
    )
    
    table.add_row(
        "📦 ASCII Blocks Available", 
        str(stats['ascii_blocks_found']),
        "📚 Ready"
    )
    
    table.add_row(
        "✅ Blocks in Use",
        str(stats['used_blocks']),
        "🎨 Active"
    )
    
    table.add_row(
        "📝 Unused Blocks",
        str(stats['unused_blocks']),
        "💤 Dormant" if stats['unused_blocks'] > 0 else "✨ All Used"
    )
    
    table.add_row(
        "📊 Coverage Percentage",
        Text(f"{coverage:.1f}%", style=f"bold {coverage_color}"),
        coverage_status
    )
    
    if stats['files_updated'] > 0:
        table.add_row(
            "🔄 Files Updated",
            str(stats['files_updated']),
            "✅ Synced"
        )
        
        table.add_row(
            "🎯 Blocks Updated",
            str(stats['total_blocks_updated']),
            "🚀 Fresh"
        )
    else:
        table.add_row(
            "🔄 Files Updated",
            "0",
            "✨ Current"
        )
    
    # Add discovery statistics if present
    if stats['heuristic_candidates'] > 0:
        table.add_row(
            "🔍 New Candidates Found",
            str(stats['heuristic_candidates']),
            "🌟 Potential"
        )
        
        if stats['quality_candidates'] > 0:
            table.add_row(
                "⭐ Quality Candidates",
                str(stats['quality_candidates']),
                "🎨 Promote"
            )
    
    if stats['unknown_markers'] > 0:
        table.add_row(
            "❓ Unknown Markers",
            str(stats['unknown_markers']),
            "⚠️ Review"
        )
    
    # Create a panel around the table
    panel = Panel(
        table,
        title="📚 Documentation Sync Results",
        title_align="center",
        border_style="bright_blue",
        padding=(1, 2)
    )
    
    console.print("\n")
    console.print(panel)

def sync_install_sh():
    """Copies install.sh to Pipulate.com and commits if changed."""
    print("\n🔄 Step 3: Synchronizing install.sh to Pipulate.com...")
    source_path = PIPULATE_ROOT / "install.sh"
    dest_path = PIPULATE_COM_ROOT / "install.sh"

    if not PIPULATE_COM_ROOT.exists():
        print(f"⚠️  Warning: Pipulate.com repo not found at {PIPULATE_COM_ROOT}. Skipping install.sh sync.")
        return False

    if not source_path.exists():
        print(f"⚠️  Warning: Source install.sh not found at {source_path}. Skipping install.sh sync.")
        return False

    # Copy the file
    dest_path.write_text(source_path.read_text())
    print(f"📄 Copied {source_path.name} to {dest_path}")

    # Check if there are changes in the Pipulate.com repo
    try:
        status_result = run_command(['git', 'status', '--porcelain', str(dest_path.name)], cwd=PIPULATE_COM_ROOT, capture=True)
        if status_result.stdout.strip():
            print(f"📦 Changes detected in {dest_path.name}. Committing and pushing...")
            run_command(['git', 'add', str(dest_path.name)], cwd=PIPULATE_COM_ROOT)
            commit_msg = f"chore: Update install.sh from pipulate repo v{get_current_version()}"
            run_command(['git', 'commit', '-m', commit_msg], cwd=PIPULATE_COM_ROOT)
            run_command(['git', 'push'], cwd=PIPULATE_COM_ROOT)
            print("✅ Pushed install.sh update to Pipulate.com repo.")
            return True
        else:
            print("✅ install.sh is already up-to-date in Pipulate.com repo.")
            return False
    except Exception as e:
        print(f"⚠️  Install.sh sync failed: {e}")
        return False

def sync_breadcrumb_trail():
    """Syncs BREADCRUMB_TRAIL_DVCS.mdc to workspace root as DONT_WRITE_HERE.mdc with Cursor frontmatter."""
    print("\n🍞 Step 4: Synchronizing breadcrumb trail to workspace root...")
    
    # Define paths
    source_path = PIPULATE_ROOT / ".cursor" / "rules" / "BREADCRUMB_TRAIL_DVCS.mdc"
    workspace_root = PIPULATE_ROOT.parent
    dest_path = workspace_root / ".cursor" / "rules" / "BREADCRUMB_TRAIL.mdc"
    
    if not source_path.exists():
        print(f"⚠️  Warning: Source breadcrumb trail not found at {source_path}. Skipping breadcrumb sync.")
        return False
    
    # Create destination directory if it doesn't exist
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Read source content
    source_content = source_path.read_text()
    
    # Create destination content with Cursor frontmatter
    cursor_frontmatter = """---
description: 
globs: 
alwaysApply: true
---
"""
    
    dest_content = cursor_frontmatter + source_content
    
    # Check if content has changed
    content_changed = True
    if dest_path.exists():
        current_content = dest_path.read_text()
        content_changed = current_content != dest_content
    
    if content_changed:
        # Write the new content
        dest_path.write_text(dest_content)
        print(f"📄 Synced breadcrumb trail: {source_path.name} → {dest_path}")
        print(f"📍 Location: {dest_path}")
        print("✅ Breadcrumb trail updated at workspace root for Cursor 'Always include'.")
        return True
    else:
        print("✅ Breadcrumb trail is already up-to-date at workspace root.")
        return False

def get_ai_model_name():
    """Extract the model name from ai_commit.py."""
    ai_commit_script = PIPULATE_ROOT / "helpers" / "release" / "ai_commit.py"
    if not ai_commit_script.exists():
        return "AI Model"
    
    try:
        content = ai_commit_script.read_text()
        # Look for OLLAMA_MODEL = "model_name"
        import re
        match = re.search(r'OLLAMA_MODEL\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
        else:
            return "AI Model"
    except Exception:
        return "AI Model"

def get_ai_commit_message():
    """Gets an AI-generated commit message from local LLM."""
    print("🤖 Analyzing changes for AI commit message...")
    
    # Check if there are any changes (staged or unstaged)
    try:
        staged_result = run_command(['git', 'diff', '--staged'], capture=True)
        unstaged_result = run_command(['git', 'diff'], capture=True)
        if not staged_result.stdout.strip() and not unstaged_result.stdout.strip():
            print("❌ No changes found for AI commit message generation")
            return None, None
    except Exception as e:
        print(f"❌ Error checking git changes: {e}")
        return None, None
    
    # Get the model name
    model_name = get_ai_model_name()
    
    # Try to get AI commit message
    ai_commit_script = PIPULATE_ROOT / "helpers" / "release" / "ai_commit.py"
    if not ai_commit_script.exists():
        print("❌ ai_commit.py not found, skipping AI commit generation")
        return None, None
    
    try:
        result = run_command(["python", str(ai_commit_script)], capture=True)
        ai_message = result.stdout.strip()
        if ai_message:
            print(f"🤖 AI generated commit message:")
            print(f"   {ai_message}")
            return ai_message, model_name
        else:
            print("⚠️  AI commit script returned empty message")
            return None, None
    except Exception as e:
        print(f"⚠️  AI commit generation failed: {e}")
        print("💡 Make sure Ollama is running: ollama serve")
        return None, None

def display_beautiful_summary(commit_message, ai_generated=False, version=None, published=False, ai_model_name=None):
    """Display a beautiful rich table summary of the release."""
    if not RICH_AVAILABLE:
        # Fallback to simple text display
        print("\n" + "="*60)
        print("🎉 RELEASE SUMMARY")
        print("="*60)
        if ai_generated:
            model_display = f" ({ai_model_name})" if ai_model_name else ""
            print(f"🤖 AI-Generated Commit Message{model_display}:")
            print(f"   {commit_message}")
        else:
            print(f"📝 Commit Message: {commit_message}")
        if version:
            print(f"📦 Version: {version}")
        if published:
            print(f"🚀 Published to PyPI: ✅")
        print("="*60)
        return
    
    console = Console()
    
    # Create the main summary table
    table = Table(
        title="🎉 Pipulate Release Summary",
        box=box.ROUNDED,
        title_style="bold magenta",
        header_style="bold cyan",
        show_header=True,
        show_lines=True,
        expand=True
    )
    
    table.add_column("Component", style="bold yellow", width=20)
    table.add_column("Details", style="white", width=60)
    table.add_column("Status", justify="center", width=10)
    
    # Add commit message row with special styling for AI-generated
    if ai_generated:
        commit_text = Text(commit_message, style="italic green")
        ai_label = f"🤖 {ai_model_name} Message" if ai_model_name else "🤖 AI Commit Message"
        ai_status = f"✨ {ai_model_name}" if ai_model_name else "✨ AI"
        table.add_row(
            ai_label,
            commit_text,
            ai_status
        )
    else:
        table.add_row(
            "📝 Commit Message", 
            commit_message,
            "📝 Manual"
        )
    
    # Add version row if provided
    if version:
        table.add_row(
            "📦 Version",
            version,
            "✅ Set"
        )
    
    # Add PyPI status if published
    if published:
        table.add_row(
            "🚀 PyPI Release",
            f"https://pypi.org/project/pipulate/{version}/",
            "✅ Live"
        )
    
    # Add timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    table.add_row(
        "⏰ Completed",
        timestamp,
        "🎯 Done"
    )
    
    # Create a panel around the table for extra beauty
    panel = Panel(
        table,
        title="🎉 Release Pipeline Complete",
        title_align="center",
        border_style="bright_green",
        padding=(1, 2)
    )
    
    console.print("\n")
    console.print(panel)

def main():
    parser = argparse.ArgumentParser(description="Pipulate Master Release Orchestrator")
    parser.add_argument("--release", action="store_true", help="Perform a PyPI release")
    parser.add_argument("-m", "--message", type=str, help="Custom commit message")
    parser.add_argument("--force", action="store_true", help="Force operation even when no git changes detected")
    parser.add_argument("--ai-commit", action="store_true", help="Use AI to generate commit message")
    parser.add_argument("--skip-version-sync", action="store_true", help="Skip version synchronization")
    parser.add_argument("--skip-docs-sync", action="store_true", help="Skip documentation synchronization")
    parser.add_argument("--skip-install-sh-sync", action="store_true", help="Skip install.sh synchronization")
    parser.add_argument("--skip-breadcrumb-sync", action="store_true", help="Skip breadcrumb trail synchronization")
    
    args = parser.parse_args()
    
    print("🚀 Pipulate Master Release Orchestrator")
    print("=" * 50)
    
    current_version = get_current_version()
    print(f"📋 Current version: {current_version}")
    
    # === RELEASE PIPELINE PHASE 1: PREPARATION ===
    print("\n🔧 === RELEASE PIPELINE: PREPARATION PHASE ===")
    
    # Step 1: Version Synchronization
    if not args.skip_version_sync:
        version_sync_success = run_version_sync()
    else:
        print("\n⏭️  Skipping version synchronization (--skip-version-sync)")
        version_sync_success = True
    
    # Step 2: Documentation Synchronization  
    if not args.skip_docs_sync:
        docs_sync_success, ascii_art_stats = run_ascii_art_sync()
        if ascii_art_stats:
            display_ascii_art_stats(ascii_art_stats)
    else:
        print("\n⏭️  Skipping documentation synchronization (--skip-docs-sync)")
        docs_sync_success = True
        ascii_art_stats = None
    
    # Step 3: Install.sh Synchronization
    if not args.skip_install_sh_sync:
        install_sh_success = sync_install_sh()
    else:
        print("\n⏭️  Skipping install.sh synchronization (--skip-install-sh-sync)")
        install_sh_success = False
    
    # Step 4: Breadcrumb Trail Synchronization
    if not args.skip_breadcrumb_sync:
        breadcrumb_sync_success = sync_breadcrumb_trail()
    else:
        print("\n⏭️  Skipping breadcrumb trail synchronization (--skip-breadcrumb-sync)")
        breadcrumb_sync_success = False
    
    # === RELEASE PIPELINE PHASE 2: GIT OPERATIONS ===
    print("\n📝 === RELEASE PIPELINE: GIT OPERATIONS PHASE ===")
    
    # Check for git changes unless forcing
    has_changes = run_command(['git', 'status', '--porcelain'], capture=True).stdout.strip()
    
    if not has_changes and not args.force:
        print("\n✅ No changes to commit. Your repository is clean.")
        if args.release:
            print("💡 Use --force to proceed with PyPI republishing anyway.")
        else:
            print("💡 Use --force to proceed anyway, or make some changes first.")
        sys.exit(0)
    elif not has_changes and args.force:
        print("\n🚨 --force flag detected: Proceeding despite no git changes.")
        commit_message = args.message or "force: Manual republish without code changes"
        ai_generated_commit = False
        ai_model_name = None
    else:
        # We have changes, determine commit message
        if args.message:
            # User provided explicit message, use it
            commit_message = args.message
            ai_generated_commit = False
            ai_model_name = None
        else:
            # Default behavior: Try AI commit, fallback to standard message
            print("\n🤖 Generating AI commit message...")
            ai_message, model_name = get_ai_commit_message()
            if ai_message:
                commit_message = ai_message
                ai_generated_commit = True
                ai_model_name = model_name
            else:
                print("⚠️  Falling back to standard commit message")
                commit_message = "chore: Update project files"
                ai_generated_commit = False
                ai_model_name = None
    
    # Handle git operations
    if has_changes:
        print(f"\n📝 Commit message: {commit_message}")
        run_command(['git', 'commit', '-am', commit_message])
        run_command(['git', 'push'])
        print("✅ Pushed changes to remote repository.")
    elif args.force:
        print("🚨 --force flag: Skipping git commit (no changes to commit)")
        print("➡️  Proceeding directly to PyPI publishing...")
    
    # === RELEASE PIPELINE PHASE 3: PYPI PUBLISHING ===
    published_to_pypi = False
    if args.release:
        print("\n📦 === RELEASE PIPELINE: PYPI PUBLISHING PHASE ===")
        print(f"🏗️  Building and Publishing version {current_version} to PyPI...")
        print("🧹 Cleaning old build artifacts...")
        run_command("rm -rf dist/ build/ *.egg-info", shell=True)
        print("🛠️ Building package...")
        run_command([".venv/bin/python", '-m', 'build'])
        print("📦 Publishing to PyPI...")
        run_command([".venv/bin/python", '-m', 'twine', 'upload', 'dist/*'])
        print(f"\n🎉 Successfully published version {current_version} to PyPI! 🎉")
        print(f"📍 View at: https://pypi.org/project/pipulate/{current_version}/")
        published_to_pypi = True
    
    # === BEAUTIFUL SUMMARY DISPLAY ===
    print("\n" + "=" * 50)
    display_beautiful_summary(
        commit_message=commit_message,
        ai_generated=ai_generated_commit,
        version=current_version,
        published=published_to_pypi,
        ai_model_name=ai_model_name
    )

if __name__ == "__main__":
    main()

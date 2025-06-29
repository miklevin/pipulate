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

# --- Configuration ---
try:
    PIPULATE_ROOT = Path(__file__).parent.parent.parent.resolve()
except FileNotFoundError:
    print("Error: Could not resolve script path.")
    sys.exit(1)

INIT_PY_PATH = PIPULATE_ROOT / "__init__.py"

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
    """Runs the ASCII art documentation synchronization."""
    print("\n📚 Step 2: Synchronizing ASCII art documentation...")
    ascii_sync_script = PIPULATE_ROOT / "helpers" / "docs_sync" / "sync_ascii_art.py"
    if not ascii_sync_script.exists():
        print("❌ sync_ascii_art.py not found, skipping documentation sync")
        return False
    
    try:
        run_command(["python", str(ascii_sync_script)])
        print("✅ ASCII art documentation synchronization complete")
        return True
    except Exception as e:
        print(f"⚠️  Documentation sync failed: {e}")
        return False

def get_ai_commit_message():
    """Gets an AI-generated commit message from local LLM."""
    print("\n🤖 Step 3: Generating AI commit message...")
    
    # First, check if there are staged changes
    try:
        result = run_command(['git', 'diff', '--staged'], capture=True)
        if not result.stdout.strip():
            print("❌ No staged changes found for AI commit message generation")
            return None
    except Exception as e:
        print(f"❌ Error checking staged changes: {e}")
        return None
    
    # Try to get AI commit message
    ai_commit_script = PIPULATE_ROOT / "helpers" / "release" / "ai_commit.py"
    if not ai_commit_script.exists():
        print("❌ ai_commit.py not found, skipping AI commit generation")
        return None
    
    try:
        result = run_command(["python", str(ai_commit_script)], capture=True)
        ai_message = result.stdout.strip()
        if ai_message:
            print(f"🤖 AI generated commit message:")
            print(f"   {ai_message}")
            return ai_message
        else:
            print("⚠️  AI commit script returned empty message")
            return None
    except Exception as e:
        print(f"⚠️  AI commit generation failed: {e}")
        print("💡 Make sure Ollama is running: ollama serve")
        return None

def main():
    parser = argparse.ArgumentParser(description="Pipulate Master Release Orchestrator")
    parser.add_argument("--release", action="store_true", help="Perform a PyPI release")
    parser.add_argument("-m", "--message", type=str, help="Custom commit message")
    parser.add_argument("--force", action="store_true", help="Force operation even when no git changes detected")
    parser.add_argument("--ai-commit", action="store_true", help="Use AI to generate commit message")
    parser.add_argument("--skip-version-sync", action="store_true", help="Skip version synchronization")
    parser.add_argument("--skip-docs-sync", action="store_true", help="Skip documentation synchronization")
    
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
        docs_sync_success = run_ascii_art_sync()
    else:
        print("\n⏭️  Skipping documentation synchronization (--skip-docs-sync)")
        docs_sync_success = True
    
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
    else:
        # We have changes, determine commit message
        if args.ai_commit and not args.message:
            print("\n🤖 AI commit message requested...")
            run_command(['git', 'add', '.'])  # Stage changes for AI analysis
            ai_message = get_ai_commit_message()
            if ai_message:
                commit_message = ai_message
            else:
                print("⚠️  Falling back to standard commit message")
                commit_message = "chore: Update project files"
        else:
            commit_message = args.message or "chore: Update project files"
    
    # Handle git operations
    if has_changes:
        print(f"\n📝 Commit message: {commit_message}")
        run_command(['git', 'add', '.'])
        run_command(['git', 'commit', '-m', commit_message])
        run_command(['git', 'push'])
        print("✅ Pushed changes to remote repository.")
    elif args.force:
        print("🚨 --force flag: Skipping git commit (no changes to commit)")
        print("➡️  Proceeding directly to PyPI publishing...")
    
    # === RELEASE PIPELINE PHASE 3: PYPI PUBLISHING ===
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
    
    print("\n✨ Release pipeline complete! ✨")
    print("=" * 50)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Pipulate Publishing Orchestrator with Force Support

NEW: --force flag allows PyPI republishing even when no git changes exist.

Usage:
  - Force PyPI republish without git changes:
    python helpers/release/publish_with_force.py --release --force -m "Republish with fixed metadata"
"""
import argparse
import subprocess
import sys
import re
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

def main():
    parser = argparse.ArgumentParser(description="Pipulate Publishing Orchestrator with Force Support")
    parser.add_argument("--release", action="store_true", help="Perform a PyPI release")
    parser.add_argument("-m", "--message", type=str, help="Custom commit message")
    parser.add_argument("--force", action="store_true", help="Force operation even when no git changes detected")
    
    args = parser.parse_args()
    
    current_version = get_current_version()
    print(f"📋 Current version: {current_version}")
    
    # Check for git changes unless forcing
    has_changes = run_command(['git', 'status', '--porcelain'], capture=True).stdout.strip()
    
    if not has_changes and not args.force:
        print("\n✅ No changes to commit. Your repository is clean. Exiting.")
        print("💡 Use --force to proceed anyway (useful for PyPI republishing).")
        sys.exit(0)
    elif not has_changes and args.force:
        print("\n🚨 --force flag detected: Proceeding despite no git changes.")
        commit_message = args.message or "force: Manual republish without code changes"
    else:
        commit_message = args.message or "Standard update"
    
    # Handle git operations
    if has_changes:
        print(f"💬 Commit message: {commit_message}")
        run_command(['git', 'add', '.'])
        run_command(['git', 'commit', '-m', commit_message])
        run_command(['git', 'push'])
        print("✅ Pushed changes to remote repository.")
    elif args.force:
        print("🚨 --force flag: Skipping git commit (no changes to commit)")
        print("➡️  Proceeding directly to PyPI publishing...")
    
    # Handle PyPI release
    if args.release:
        print(f"\n--- Building and Publishing version {current_version} to PyPI ---")
        print("🧹 Cleaning old build artifacts...")
        run_command("rm -rf dist/ build/ *.egg-info", shell=True)
        print("🛠️ Building package...")
        run_command([sys.executable, '-m', 'build'])
        print("📦 Publishing to PyPI...")
        run_command([sys.executable, '-m', 'twine', 'upload', 'dist/*'])
        print(f"\n🎉 Successfully published version {current_version} to PyPI! 🎉")
    
    print("\n✨ Workflow complete! ✨")

if __name__ == "__main__":
    main()

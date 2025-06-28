#!/usr/bin/env python3
"""
Pipulate Publishing Orchestrator

A unified script to handle all aspects of committing, versioning,
and publishing the Pipulate package.

Usage:
  - For a standard commit (with AI-generated message):
    python helpers/release/publish.py

  - For a standard commit (with a custom message):
    python helpers/release/publish.py -m "docs: Update README with new diagrams"

  - For a full PyPI release (auto-bumps patch version):
    python helpers/release/publish.py --release -m "Add new browser automation feature"

  - For a minor or major release:
    python helpers/release/publish.py --release --level minor -m "Refactor core architecture"
"""
import argparse
import subprocess
import sys
import re
from pathlib import Path

# --- Configuration ---
# Define root paths assuming a standard repo structure: ~/repos/pipulate, ~/repos/Pipulate.com
try:
    PIPULATE_ROOT = Path(__file__).parent.parent.parent.resolve()
    PIPULATE_COM_ROOT = (PIPULATE_ROOT.parent / "Pipulate.com").resolve()
except FileNotFoundError:
    print("Error: Could not resolve script path. Ensure you are running from within the pipulate repo.")
    sys.exit(1)

INIT_PY_PATH = PIPULATE_ROOT / "pipulate" / "__init__.py"

# --- Helper Functions ---

def run_command(cmd, cwd=PIPULATE_ROOT, capture=False, check=True, shell=False):
    """Runs a command and handles errors."""
    print(f"🏃 Running: {' '.join(cmd) if not shell else cmd} in {cwd}")
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=capture,
            text=True,
            check=check,
            shell=shell
        )
        return result
    except FileNotFoundError:
        print(f"❌ Error: Command '{cmd[0] if not shell else cmd}' not found.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(cmd) if not shell else cmd}", file=sys.stderr)
        print(f"   Return Code: {e.returncode}", file=sys.stderr)
        if e.stdout:
            print(f"   STDOUT:\n{e.stdout}", file=sys.stderr)
        if e.stderr:
            print(f"   STDERR:\n{e.stderr}", file=sys.stderr)
        sys.exit(1)

def get_current_version():
    """Gets the version from pipulate/__init__.py."""
    content = INIT_PY_PATH.read_text()
    match = re.search(r"__version__\s*=\s*[\"']([^\"']+)[\"']", content)
    if not match:
        raise RuntimeError("Could not find __version__ in __init__.py")
    return match.group(1)

def bump_version(level='patch'):
    """Bumps the version in __init__.py."""
    current_version = get_current_version()
    major, minor, patch = map(int, current_version.split('.'))

    if level == 'major':
        major += 1
        minor = 0
        patch = 0
    elif level == 'minor':
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    new_version = f"{major}.{minor}.{patch}"
    print(f"⏫ Bumping version from {current_version} to {new_version}")

    content = INIT_PY_PATH.read_text()
    new_content = re.sub(
        r"(__version__\s*=\s*[\"'])[^\"']*(['\"])",
        f"\\1{new_version}\\2",
        content
    )
    INIT_PY_PATH.write_text(new_content)
    return new_version

def sync_versions():
    """Calls the main version_sync.py script."""
    script_path = PIPULATE_ROOT / "version_sync.py"
    run_command([sys.executable, str(script_path)])

def sync_docs():
    """Calls the ASCII art sync script."""
    script_path = PIPULATE_ROOT / "helpers" / "docs_sync" / "sync_ascii_art.py"
    run_command([sys.executable, str(script_path)])

def sync_install_sh():
    """Copies install.sh to Pipulate.com and commits if changed."""
    print("🔄 Syncing install.sh to Pipulate.com repo...")
    source_path = PIPULATE_ROOT / "install.sh"
    dest_path = PIPULATE_COM_ROOT / "install.sh"

    if not PIPULATE_COM_ROOT.exists():
        print(f"⚠️  Warning: Pipulate.com repo not found at {PIPULATE_COM_ROOT}. Skipping install.sh sync.")
        return

    # Copy the file
    dest_path.write_text(source_path.read_text())
    print(f"Copied {source_path.name} to {dest_path}")

    # Check if there are changes in the Pipulate.com repo
    status_result = run_command(['git', 'status', '--porcelain', str(dest_path.name)], cwd=PIPULATE_COM_ROOT, capture=True)
    if status_result.stdout.strip():
        print(f"📦 Changes detected in {dest_path.name}. Committing and pushing...")
        run_command(['git', 'add', str(dest_path.name)], cwd=PIPULATE_COM_ROOT)
        commit_msg = f"chore: Update install.sh from pipulate repo v{get_current_version()}"
        run_command(['git', 'commit', '-m', commit_msg], cwd=PIPULATE_COM_ROOT)
        run_command(['git', 'push'], cwd=PIPULATE_COM_ROOT)
        print("✅ Pushed install.sh update to Pipulate.com repo.")
    else:
        print("✅ install.sh is already up-to-date in Pipulate.com repo.")

def get_ai_commit_message():
    """Calls the AI commit helper to get a message."""
    print("🤖 Generating AI commit message (this might take a moment)...")
    script_path = PIPULATE_ROOT / "helpers" / "release" / "ai_commit.py"
    result = run_command([sys.executable, str(script_path)], capture=True)
    return result.stdout.strip()

def main():
    parser = argparse.ArgumentParser(
        description="Pipulate Publishing Orchestrator",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--release",
        action="store_true",
        help="Perform a full release: bump version, sync, build, and publish to PyPI."
    )
    parser.add_argument(
        "-m", "--message",
        type=str,
        help="Custom commit message. If not provided for a non-release, AI will generate one."
    )
    parser.add_argument(
        "--level",
        choices=['patch', 'minor', 'major'],
        default='patch',
        help="The version level to bump for a release (default: patch)."
    )
    args = parser.parse_args()

    # --- Step 1: Sync Documentation ---
    print("\n--- Step 1: Syncing Documentation ---")
    sync_docs()

    commit_message = args.message
    new_version = None

    if args.release:
        # --- Release Workflow ---
        print("\n--- Initiating Release Workflow ---")

        # Step 2: Bump and Sync Versions
        print("\n--- Step 2: Bumping and Syncing Versions ---")
        new_version = bump_version(args.level)
        sync_versions()

        # Step 3: Sync install.sh to Pipulate.com
        print("\n--- Step 3: Syncing install.sh to Website Repo ---")
        sync_install_sh()

        if not commit_message:
            print("❌ Error: A commit message (`-m`) is required for a release.", file=sys.stderr)
            sys.exit(1)
        commit_message = f"release: Version {new_version} - {commit_message}"

    else:
        # --- Standard Commit Workflow ---
        print("\n--- Initiating Standard Commit Workflow ---")
        # Check for staged changes before proceeding
        staged_files = run_command(['git', 'diff', '--name-only', '--staged'], capture=True).stdout.strip()
        all_files = run_command(['git', 'status', '--porcelain'], capture=True).stdout.strip()

        if not all_files:
            print("\n✅ No changes to commit. Your repository is clean. Exiting.")
            sys.exit(0)

        # Stage all changes
        run_command(['git', 'add', '.'])

        if not commit_message:
            commit_message = get_ai_commit_message()

    # --- Step 4: Commit and Push to Git ---
    print("\n--- Step 4: Committing and Pushing to Git ---")
    print(f"💬 Commit message: {commit_message}")
    run_command(['git', 'commit', '-m', commit_message])
    run_command(['git', 'push'])
    print("✅ Pushed changes to remote repository.")

    if args.release:
        # --- Step 5: Build and Publish to PyPI ---
        print("\n--- Step 5: Building and Publishing to PyPI ---")
        print("🧹 Cleaning old build artifacts...")
        run_command("rm -rf dist/ build/ *.egg-info", shell=True)
        print("🛠️ Building package...")
        run_command([sys.executable, '-m', 'build'])
        print("📦 Publishing to PyPI...")
        run_command([sys.executable, '-m', 'twine', 'upload', 'dist/*'])
        print(f"\n🎉 Successfully published version {new_version} to PyPI! 🎉")

    print("\n✨ Workflow complete! ✨")

if __name__ == "__main__":
    main() 
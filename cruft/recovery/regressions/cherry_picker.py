import subprocess
import os
from datetime import datetime

# --- Configuration ---
ACTIVE_HISTORY_FILE = 'history_active.txt'
LOST_HISTORY_FILE = 'history_lost.txt'
FAILED_LOG_FILE = 'failed_cherry_picks.log'

def run_command(command, suppress_errors=False):
    """Executes a shell command, returning its success status."""
    try:
        subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        if not suppress_errors:
            print(f"\n---! Command Failed: '{e.cmd}' !---")
            print(f"---  STDERR: ---\n{e.stderr.strip()}")
        return False

def parse_commit_line(line):
    """Parses a line to extract hash, date, and message."""
    try:
        parts = line.strip().split()
        commit_hash = parts[0]
        commit_date = datetime.strptime(parts[1], '%Y-%m-%d')
        commit_message = ' '.join(parts[2:])
        return {'hash': commit_hash, 'date': commit_date, 'message': line.strip()}
    except (ValueError, IndexError):
        return None

def main():
    """Main function to drive the automated cherry-pick process."""
    print("Starting automated cherry-pick session...")

    # Clear previous failed log if it exists
    if os.path.exists(FAILED_LOG_FILE):
        os.remove(FAILED_LOG_FILE)
        print(f"Removed old '{FAILED_LOG_FILE}'.")

    # --- 1. Read and Compare History Files ---
    try:
        with open(ACTIVE_HISTORY_FILE, 'r') as f:
            active_lines = {line.strip() for line in f}
        with open(LOST_HISTORY_FILE, 'r') as f:
            lost_lines = {line.strip() for line in f}
    except FileNotFoundError as e:
        print(f"\n❌ ERROR: Could not find '{e.filename}'. Please ensure it's in this directory.")
        return

    lost_only_lines = lost_lines.difference(active_lines)

    if not lost_only_lines:
        print("\n✅ No new commits found to process. You are all caught up!")
        return

    # --- 2. Parse and Sort Commits ---
    commits_to_pick = [parsed for line in lost_only_lines if (parsed := parse_commit_line(line))]
    commits_to_pick.sort(key=lambda x: x['date'])

    total_commits = len(commits_to_pick)
    succeeded_count = 0
    failed_count = 0
    print(f"\nFound {total_commits} unique commits to process.")

    # --- 3. Automated Cherry-Pick Loop ---
    for i, commit in enumerate(commits_to_pick, 1):
        commit_hash = commit['hash']
        print(f"\n({i}/{total_commits}) Attempting to apply {commit_hash}...")

        # --- 4. Execute Cherry-Pick ---
        if run_command(f"git cherry-pick {commit_hash}"):
            print(f"✅ Success: Applied {commit_hash}")
            succeeded_count += 1
        else:
            failed_count += 1
            print(f"❌ Failed: Could not apply {commit_hash}. Logging and skipping.")
            
            # Abort the failed cherry-pick to keep the branch clean
            run_command("git cherry-pick --abort", suppress_errors=True)
            
            # Log the failed commit
            with open(FAILED_LOG_FILE, 'a') as log_file:
                log_file.write(commit['message'] + '\n')

    # --- 5. Final Report ---
    print("\n" + "="*50)
    print("🎉 Automated cherry-pick session complete!")
    print(f"  - Successfully applied: {succeeded_count}")
    print(f"  - Failed to apply:    {failed_count}")
    print("="*50)

    if failed_count > 0:
        print(f"\nThe {failed_count} commits that could not be applied have been saved to:")
        print(f"  --> {FAILED_LOG_FILE}")
        print("\nYou can now manually cherry-pick from that list.")
    else:
        print("\nAll commits were applied successfully!")

if __name__ == "__main__":
    main()

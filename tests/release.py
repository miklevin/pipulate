#!/usr/bin/env python3
"""
🎯 TESTS DIRECTORY AI-ASSISTED COMMIT SYSTEM

Self-contained commit system for the regression hunting test harness.
Integrates with local Ollama LLM for intelligent commit messages.

Usage:
    python release.py                    # Auto-stage all changes, AI commit message
    python release.py -m "Custom msg"   # Manual commit message override
    python release.py --no-push         # Commit but don't push to remote
    python release.py --dry-run         # Show what would be committed without doing it

Features:
    - 🤖 AI-generated commit messages via local Ollama
    - 📝 Manual override capability  
    - 🔍 Automatic change detection and staging
    - 🚀 Optional push to remote
    - 🎯 Designed for incremental regression hunting development
"""
import subprocess
import requests
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Configuration for local LLM
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3"  # Fast model for commit messages

# Git commit prompt optimized for regression hunting context
COMMIT_PROMPT_TEMPLATE = """
You are a git commit message generator for a regression hunting test harness.

Write a conventional commit message in this EXACT format:
<type>(<scope>): <subject>

<body (optional, max 3 lines)>

RULES:
- Subject line: max 50 chars, imperative mood
- Types: feat, fix, docs, test, refactor, chore
- Scope: tests, harness, binary-search, automation
- Focus on WHAT changed, not HOW
- No explanations, analysis, or suggestions

Example good messages:
feat(harness): Add parameter system for time-bounded regression hunting
fix(tests): Correct template variable processing in form automation  
docs(tests): Add binary search algorithm documentation

Git diff:
{git_diff}

Generate ONLY the commit message:
"""

class TestsReleaseManager:
    """AI-assisted commit manager for the tests directory."""
    
    def __init__(self):
        self.tests_dir = Path(__file__).parent
        self.dry_run = False
        
    def log_message(self, message, level="INFO"):
        """Log messages with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def run_git_command(self, cmd, capture_output=True):
        """Run git command in tests directory."""
        try:
            result = subprocess.run(
                cmd, 
                cwd=self.tests_dir,
                capture_output=capture_output,
                text=True,
                check=True
            )
            return result
        except subprocess.CalledProcessError as e:
            self.log_message(f"Git command failed: {' '.join(cmd)}", "ERROR")
            self.log_message(f"Error: {e.stderr}", "ERROR")
            sys.exit(1)
    
    def check_git_status(self):
        """Check if there are any changes to commit."""
        try:
            # Check for staged changes
            staged_result = self.run_git_command(['git', 'diff', '--staged'])
            # Check for unstaged changes  
            unstaged_result = self.run_git_command(['git', 'diff'])
            # Check for untracked files
            untracked_result = self.run_git_command(['git', 'ls-files', '--others', '--exclude-standard'])
            
            has_staged = bool(staged_result.stdout.strip())
            has_unstaged = bool(unstaged_result.stdout.strip())
            has_untracked = bool(untracked_result.stdout.strip())
            
            return has_staged, has_unstaged, has_untracked
            
        except Exception as e:
            self.log_message(f"Error checking git status: {e}", "ERROR")
            return False, False, False
    
    def auto_stage_changes(self):
        """Automatically stage all changes for commit."""
        has_staged, has_unstaged, has_untracked = self.check_git_status()
        
        if not has_staged and not has_unstaged and not has_untracked:
            self.log_message("No changes found to stage", "INFO")
            return False
            
        # Stage all changes (modified, new, deleted)
        if has_unstaged or has_untracked:
            self.log_message("🔄 Auto-staging all changes...", "INFO")
            if not self.dry_run:
                self.run_git_command(['git', 'add', '.'], capture_output=False)
            self.log_message("✅ Changes staged successfully", "INFO")
            
        return True
    
    def get_staged_diff(self):
        """Get diff of staged changes for AI analysis."""
        try:
            result = self.run_git_command(['git', 'diff', '--staged'])
            if not result.stdout.strip():
                self.log_message("No staged changes found for diff", "ERROR")
                return None
            return result.stdout
        except Exception as e:
            self.log_message(f"Error getting staged diff: {e}", "ERROR")
            return None
    
    def generate_ai_commit_message(self, diff_content):
        """Generate commit message using local Ollama LLM."""
        self.log_message("🤖 Analyzing changes with local AI...", "INFO")
        
        prompt = COMMIT_PROMPT_TEMPLATE.format(git_diff=diff_content)
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,  # Low temperature for consistent output
                "top_p": 0.8,
            }
        }
        
        try:
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
            response.raise_for_status()
            response_data = response.json()
            ai_message = response_data.get("response", "").strip()
            
            if ai_message:
                self.log_message("✅ AI commit message generated", "INFO")
                return ai_message
            else:
                self.log_message("⚠️ AI returned empty message", "WARNING")
                return None
                
        except requests.exceptions.RequestException as e:
            self.log_message(f"AI commit generation failed: {e}", "ERROR")
            self.log_message("💡 Ensure Ollama is running: ollama serve", "INFO")
            self.log_message(f"💡 Ensure model is available: ollama pull {OLLAMA_MODEL}", "INFO")
            return None
    
    def perform_commit(self, commit_message, skip_push=False):
        """Perform git commit with the given message."""
        if not commit_message:
            self.log_message("No commit message provided", "ERROR")
            return False
            
        self.log_message(f"📝 Committing with message:", "INFO")
        self.log_message(f"    {commit_message}", "INFO")
        
        if not self.dry_run:
            try:
                # Perform the commit
                self.run_git_command(['git', 'commit', '-m', commit_message], capture_output=False)
                self.log_message("✅ Commit successful", "INFO")
                
                # Optional push to remote
                if not skip_push:
                    self.log_message("🚀 Pushing to remote...", "INFO")
                    self.run_git_command(['git', 'push'], capture_output=False)
                    self.log_message("✅ Push successful", "INFO")
                else:
                    self.log_message("⏸️ Skipping push (--no-push specified)", "INFO")
                    
                return True
                
            except Exception as e:
                self.log_message(f"Commit failed: {e}", "ERROR")
                return False
        else:
            self.log_message("🔍 DRY RUN: Would commit with above message", "INFO")
            if not skip_push:
                self.log_message("🔍 DRY RUN: Would push to remote", "INFO")
            return True
    
    def release_checkpoint(self, custom_message=None, skip_push=False, dry_run=False):
        """Main release function - commits current progress."""
        self.dry_run = dry_run
        
        self.log_message("🎯 Starting AI-assisted commit process...", "INFO")
        
        # Auto-stage changes
        if not self.auto_stage_changes():
            self.log_message("No changes to commit", "INFO")
            return True
            
        # Use custom message or generate AI message
        if custom_message:
            self.log_message("📝 Using provided custom message", "INFO")
            commit_message = custom_message
            ai_generated = False
        else:
            # Get staged diff for AI analysis
            diff_content = self.get_staged_diff()
            if not diff_content:
                return False
                
            # Generate AI commit message
            commit_message = self.generate_ai_commit_message(diff_content)
            if not commit_message:
                self.log_message("Falling back to default message", "WARNING")
                commit_message = "chore(tests): Update regression hunting test harness"
            ai_generated = True
        
        # Show commit preview
        if ai_generated:
            self.log_message("🤖 AI-Generated Commit Message:", "INFO") 
        else:
            self.log_message("📝 Custom Commit Message:", "INFO")
        self.log_message(f"    {commit_message}", "INFO")
        
        # Perform the commit
        success = self.perform_commit(commit_message, skip_push)
        
        if success:
            self.log_message("🎉 Release checkpoint complete!", "INFO")
            if ai_generated:
                self.log_message(f"🤖 Powered by {OLLAMA_MODEL} local AI", "INFO")
        
        return success

def main():
    """Command line interface for the tests release manager."""
    parser = argparse.ArgumentParser(
        description="🎯 Tests Directory AI-Assisted Commit System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python release.py                          # Auto-stage, AI commit, push
  python release.py -m "Custom message"     # Custom message override  
  python release.py --no-push               # Commit but don't push
  python release.py --dry-run               # Preview without executing
        """
    )
    
    parser.add_argument(
        '-m', '--message', 
        type=str, 
        help='Custom commit message (overrides AI generation)'
    )
    parser.add_argument(
        '--no-push', 
        action='store_true',
        help='Commit but do not push to remote'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true', 
        help='Show what would be done without executing'
    )
    
    args = parser.parse_args()
    
    # Create release manager and execute
    manager = TestsReleaseManager()
    success = manager.release_checkpoint(
        custom_message=args.message,
        skip_push=args.no_push,
        dry_run=args.dry_run
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 
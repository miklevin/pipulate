#!/usr/bin/env python3
"""
AI Commit Message Generator for Pipulate

This script uses a local LLM (via Ollama) to generate a conventional
commit message based on the currently staged git changes.

Usage:
    python helpers/release/ai_commit.py
"""
import subprocess
import requests
import json
import sys

# Configuration for the local LLM
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma:2b"  # Using a smaller, faster model for this task

COMMIT_PROMPT_TEMPLATE = """
You are an expert programmer and git contributor for the "Pipulate" project, a local-first AI SEO tool.
Your task is to write a concise, informative, and conventional commit message.

Analyze the following git diff and generate a commit message in the format:
<type>(<scope>): <subject>

<body>

The commit message should:
- Use a valid conventional commit type (e.g., feat, fix, docs, style, refactor, perf, test, chore, build).
- Have a brief, imperative subject line (max 50 chars).
- Provide a more detailed body explaining the "what" and "why" of the changes, if necessary.
- The entire response should be ONLY the commit message, with no extra text or explanations.

Here is the git diff of staged changes:
--- GIT DIFF START ---
{git_diff}
--- GIT DIFF END ---

Generate the commit message now.
"""

def get_staged_diff():
    """Gets the diff of currently staged files."""
    try:
        result = subprocess.run(
            ['git', 'diff', '--staged'],
            capture_output=True,
            text=True,
            check=True
        )
        if not result.stdout.strip():
            print("No staged changes found to generate a commit message.")
            sys.exit(0)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error getting git diff: {e.stderr}", file=sys.stderr)
        sys.exit(1)

def generate_commit_message(diff_content):
    """Sends the diff to a local LLM to generate a commit message."""
    prompt = COMMIT_PROMPT_TEMPLATE.format(git_diff=diff_content)
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,  # Low temperature for factual, consistent output
            "top_p": 0.8,
        }
    }
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
        response.raise_for_status()
        response_data = response.json()
        return response_data.get("response", "chore: Update project files").strip()
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Ollama API at {OLLAMA_API_URL}: {e}", file=sys.stderr)
        print("Please ensure Ollama is running and the model is available.", file=sys.stderr)
        print(f"To pull the model, run: ollama pull {OLLAMA_MODEL}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    staged_diff = get_staged_diff()
    commit_message = generate_commit_message(staged_diff)
    # Print only the commit message to stdout so it can be captured
    print(commit_message) 
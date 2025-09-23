#!/bin/bash
#
# Performs a "Time Lord Regeneration" for a Git branch.
# It renames the current experimental branch to a target branch (default: main),
# deletes the old remote experimental branch, and force-pushes the new
# target branch to become the new reality.
#
# Usage: ./scripts/regenerate.sh <experimental_branch_name>
# Example: ./scripts/regenerate.sh magicuser

# --- Configuration ---
# Exit immediately if a command fails
set -e
# The branch to become the new reality. Change this if you don't use 'main'.
TARGET_BRANCH="main"
# The name of your remote repository.
REMOTE="origin"

# --- Parameters & Sanity Checks ---
SOURCE_BRANCH=$1
if [[ -z "$SOURCE_BRANCH" ]]; then
  echo "❌ Spell Failed: You must provide the name of the current experimental branch."
  echo "Usage: $0 <experimental_branch_name>"
  exit 1
fi

CURRENT_GIT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_GIT_BRANCH" != "$SOURCE_BRANCH" ]]; then
  echo "❌ Spell Failed: You are on branch '$CURRENT_GIT_BRANCH', not '$SOURCE_BRANCH'."
  echo "Please 'git checkout $SOURCE_BRANCH' first."
  exit 1
fi

# --- The Incantation ---
echo "🔮 Initiating Time Lord Regeneration..."
echo "The current timeline ('$SOURCE_BRANCH') will become the new '$TARGET_BRANCH'."
echo ""

echo "Step 1/3: Renaming local branch to '$TARGET_BRANCH'..."
git branch -M "$SOURCE_BRANCH" "$TARGET_BRANCH"
echo "Local reality updated."
echo ""

echo "Step 2/3: Erasing old timeline ('$SOURCE_BRANCH') from remote..."
git push "$REMOTE" --delete "$SOURCE_BRANCH"
echo "Old remote timeline erased."
echo ""

echo "Step 3/3: Broadcasting the new reality to the world..."
git push -u --force "$REMOTE" "$TARGET_BRANCH"
echo ""

echo "✅ Regeneration complete! '$TARGET_BRANCH' is now the official timeline."
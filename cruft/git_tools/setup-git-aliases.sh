#!/bin/bash
# Setup Git Aliases to Prevent Dangerous Commands
# ===============================================
# This script sets up aliases that intercept dangerous git commands and route them
# through our harness system instead.

echo "🔧 Setting up Git safety aliases..."

# Create a function alias that intercepts git cherry-pick --continue
echo "Creating git alias for cherry-pick --continue interception..."

# Set up a git alias that redirects to our wrapper
git config alias.cherry-pick-continue '!echo "🚨 INTERCEPTED: Use ./git-continue-wrapper.sh instead" && echo "This prevents terminal lockups and ensures proper automation."'

# Also create an alias for the common shorthand
git config alias.cpc '!echo "🚨 INTERCEPTED: Use ./git-continue-wrapper.sh instead" && echo "This prevents terminal lockups and ensures proper automation."'

echo "✅ Git aliases configured!"
echo ""
echo "🔧 HARNESS PROTECTION ACTIVE:"
echo "  - 'git cherry-pick --continue' will show safety message"
echo "  - Use './git-continue-wrapper.sh' instead"
echo ""
echo "To temporarily bypass (only if needed):"
echo "  git -c alias.cherry-pick-continue= cherry-pick --continue" 
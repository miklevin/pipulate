#!/bin/bash
# Git Cherry-Pick Continue Wrapper
# =================================
# This script intercepts 'git cherry-pick --continue' commands and handles them properly
# to avoid the interactive terminal lockup issue.

echo "🔧 HARNESS INTERCEPTED: git cherry-pick --continue"
echo "Using non-interactive completion instead..."

# Check if we're currently in a cherry-pick state
if git status --porcelain | grep -q "^UU "; then
    echo "❌ ERROR: There are still unmerged files!"
    echo "Please resolve conflicts first:"
    git status --porcelain | grep "^UU " | sed 's/^UU /  - /'
    echo ""
    echo "After resolving, run: git add <files>"
    echo "Then run this command again."
    exit 1
fi

# Check if we're in cherry-pick state but all conflicts are resolved
if [ -f .git/CHERRY_PICK_HEAD ]; then
    echo "✅ Conflicts appear to be resolved. Completing cherry-pick..."
    
    # Complete the cherry-pick non-interactively
    git -c core.editor=true cherry-pick --continue
    
    if [ $? -eq 0 ]; then
        echo "✅ Cherry-pick completed successfully!"
        
        # Now resume the cherry-pick script from the next commit
        if [ -f "simple_cherry_pick.py" ]; then
            echo "🔄 Resuming cherry-pick harness..."
            
            # Find the current commit number by checking the last success log
            if [ -f "simple_cherry_pick_success.log" ]; then
                LAST_SUCCESS=$(wc -l < simple_cherry_pick_success.log)
                NEXT_COMMIT=$((LAST_SUCCESS + 1))
                echo "📍 Resuming from commit #$NEXT_COMMIT"
                .venv/bin/python simple_cherry_pick.py --resume $NEXT_COMMIT
            else
                echo "📍 No success log found, resuming from commit #2"
                .venv/bin/python simple_cherry_pick.py --resume 2
            fi
        else
            echo "⚠️  simple_cherry_pick.py not found. Manual resumption required."
        fi
    else
        echo "❌ Cherry-pick failed to complete!"
        exit 1
    fi
else
    echo "❌ Not currently in a cherry-pick state!"
    echo "Current git status:"
    git status --short
    exit 1
fi 
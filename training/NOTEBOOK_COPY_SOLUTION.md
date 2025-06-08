# Notebook Copy Solution: Preventing Git Conflicts

## Problem Statement

The Pipulate "magic cookie" installation system has an inherent conflict:
1. **Auto-Update Mechanism**: `git pull` runs on every `nix develop` to keep installations current
2. **Interactive Notebook**: JupyterLab automatically opens `helpers/botify/botify_api.ipynb` for editing
3. **Git Conflict**: Any notebook edits (even just running cells) modify the file and prevent `git pull` from succeeding

## Solution: Copy-on-First-Run

The implemented solution uses a "copy-on-first-run" approach:

### Key Components

1. **Original Notebook**: `helpers/botify/botify_api.ipynb`
   - Remains tracked by git
   - Receives updates via `git pull`
   - Never opened directly by users

2. **Local Copy**: `helpers/botify/botify_api_local.ipynb`
   - Created automatically on first run by copying the original
   - Ignored by git (via `.gitignore`)
   - This is what JupyterLab opens for user interaction

### Implementation Details

#### Modified Files

1. **`flake.nix`** - Updated version to 1.0.3 (Notebook Fix)
   - Added notebook path variables
   - Added `copy_notebook_if_needed()` function
   - Updated all JupyterLab startup commands to use local copy
   - Modified scripts: `start`, `run-jupyter`, `run-all`, and main startup

2. **`.gitignore`** - Added entry to ignore local copy
   ```
   # Ignore local notebook copies to prevent git conflicts
   helpers/botify/botify_api_local.ipynb
   ```

#### Copy Logic

```bash
copy_notebook_if_needed() {
  if [ -f "${originalNotebook}" ] && [ ! -f "${localNotebook}" ]; then
    echo "INFO: Creating a local, user-editable copy of the Botify API notebook..."
    echo "      Your work will be saved in '${localNotebook}' and will not interfere with updates."
    cp "${originalNotebook}" "${localNotebook}"
    echo "      To get future updates to the original notebook, you can delete '${localNotebook}'."
  fi
}
```

## Benefits

1. **Zero Git Conflicts**: User's notebook is untracked, so `git pull` always succeeds
2. **Preserves User Work**: Edits are safe in the local copy
3. **Maintains Updatability**: Original notebook can be updated from repository
4. **Minimally Invasive**: Small changes to existing infrastructure
5. **User-Friendly**: Automatic copying with clear messaging

## User Experience

### First Run
```
INFO: Creating a local, user-editable copy of the Botify API notebook...
      Your work will be saved in 'helpers/botify/botify_api_local.ipynb' and will not interfere with updates.
      To get future updates to the original notebook, you can delete 'helpers/botify/botify_api_local.ipynb'.
```

### Subsequent Runs
- JupyterLab opens the local copy automatically
- User's previous work is preserved
- No copying messages (copy already exists)

### Getting Template Updates
Users can get the latest version of the original notebook by:
1. Deleting their local copy: `rm helpers/botify/botify_api_local.ipynb`
2. Running `nix develop` again (or any startup script)
3. The copy function will create a fresh copy from the updated original

## Technical Verification

The solution has been tested and verified:

✅ Original notebook tracked by git: `helpers/botify/botify_api.ipynb`  
✅ Local copy ignored by git: `helpers/botify/botify_api_local.ipynb`  
✅ Copy function works on first run  
✅ Copy function doesn't duplicate on subsequent runs  
✅ Flake syntax validation passes  
✅ Git status clean (local copy properly ignored)  

## Future Considerations

### Template Distribution
When the original notebook receives updates:
- Existing users keep their local modifications
- New installations get the latest template
- Users who want updates can delete local copy to get fresh template

### Alternative Approaches Considered

1. **Git Stashing**: Rejected due to complexity and potential data loss
2. **Branching**: Too complex for end users
3. **Different Directory**: Would break existing documentation/workflows
4. **File Permissions**: Wouldn't prevent modification by Jupyter

The copy-on-first-run approach provides the optimal balance of simplicity, safety, and functionality.

## Implementation Status

🎉 **COMPLETE**: The solution is fully implemented and tested.

All JupyterLab startup paths now use the local copy:
- Default `nix develop` startup
- `run-jupyter` script
- `run-all` script  
- `start` script

The magic cookie auto-update system continues to work seamlessly without any git conflicts. 
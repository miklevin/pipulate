# 🔧 Environment Diagnostic Script

## Purpose

The `test_python_environment_fix.py` script is a comprehensive diagnostic tool that helps AI assistants identify and fix Python environment issues that commonly occur during the progressive discovery sequence.

## When to Use

Run this script if you encounter:
- `ModuleNotFoundError: No module named 'aiohttp'`
- Python environment confusion
- Virtual environment activation issues
- Nix environment problems
- MCP tools import failures

## Quick Fix

```bash
# Run the diagnostic
python test_python_environment_fix.py

# If issues are found, the script will provide specific fixes
```

## Common Environment Issues & Solutions

### Issue 1: Nested Virtual Environments
**Symptoms:** SSL errors, PATH confusion, multiple Python versions

**Solution:**
```bash
unset VIRTUAL_ENV
unset PATH
export PATH='/run/wrappers/bin:/usr/bin:/usr/sbin:/home/mike/.nix-profile/bin:/nix/profile/bin:/home/mike/.local/state/nix/profile/bin:/etc/profiles/per-user/mike/bin:/nix/var/nix/profiles/default/bin:/run/current-system/sw/bin'
exec nix develop .#quiet
```

### Issue 2: Not in Nix Environment
**Symptoms:** `IN_NIX_SHELL` is empty, missing dependencies

**Solution:**
```bash
nix develop .#quiet
```

### Issue 3: Git Dirty Tree
**Symptoms:** Nix warnings about dirty git tree

**Solution:**
```bash
git add .
git commit -m "Fix: Environment consistency"
nix develop .#quiet
```

## Expected Environment State

After running the diagnostic successfully, you should see:

✅ **Directory:** `/home/mike/repos/pipulate`  
✅ **Python:** `/home/mike/repos/pipulate/.venv/bin/python`  
✅ **Version:** `Python 3.12.11`  
✅ **Nix Shell:** `IN_NIX_SHELL=impure`  
✅ **Dependencies:** All critical modules importable  
✅ **MCP Tools:** Accessible and functional  

## Next Steps

Once the environment is working correctly, continue with:

1. **MCP Tools Discovery:**
   ```bash
   python discover_mcp_tools.py
   ```

2. **Follow Breadcrumb Trail:**
   ```bash
   grep -n "FINDER_TOKEN" logs/server.log | head -10
   ```

3. **Use Easy Tool Access:**
   ```bash
   python helpers/ai_tool_discovery.py
   ```

## Integration with Discovery Sequence

This diagnostic is now integrated into the AI progressive discovery sequence as **Level 1.5**. It ensures that future AI assistants can quickly identify and resolve environment issues before proceeding with the discovery process.

---

**Created:** July 1, 2025  
**Purpose:** Fix environment ambiguity for future AI assistants  
**Status:** ✅ Integrated into discovery sequence 
# 🚀 QUICK START FOR AI ASSISTANTS

**This guide prevents the environment confusion that breaks the discovery sequence.**

## 🚨 **STEP 1: NAVIGATE TO PIPULATE DIRECTORY**

**CRITICAL FIRST STEP: AI assistants start in workspace root but need to be in pipulate/ directory**

```bash
pwd  # You'll see: /home/mike/repos (workspace root)
cd pipulate  # 🚨 CRITICAL: Move into pipulate directory
pwd  # Should now show: /home/mike/repos/pipulate
ls -la | head -10  # Verify you see: server.py, plugins/, logs/, mcp_tools.py
```

**⚠️ If you skip this step, ALL subsequent commands will fail!**

## 🚨 **STEP 2: ALWAYS USE CORRECT PYTHON PATH**

**CRITICAL RULE: If you see `(.venv)` in your terminal prompt, you MUST use `.venv/bin/python` instead of `python`**

**Verify your Python path from pipulate directory:**
```bash
.venv/bin/python -c "import aiohttp; print('✅ Environment working')"
```

**Expected Result:** Should show "✅ Environment working"

**If you see "ModuleNotFoundError: No module named 'aiohttp'":**
- **Problem**: Using system Python instead of virtual environment Python
- **Solution**: Use `.venv/bin/python` instead of `python`
- **Example**: `.venv/bin/python discover_mcp_tools.py`

## 🎯 **STEP 3: PROGRESSIVE DISCOVERY SEQUENCE**

**Once in pipulate directory with working Python, follow the breadcrumb trail:**

If you have not already done this, the user may initiate the process with any of the following
keywords: explore, learn, hijack (or the cure "Hi Jack" variation), or simply "go"

1. **Environmental Mastery:**
   ```bash
   pwd  # Should show /home/mike/repos/pipulate
   ls -la | head -15  # Verify server.py, plugins/, logs/, mcp_tools.py
   ps aux | grep python | grep server.py  # Confirm server running
   ```

2. **FINDER_TOKEN Discovery:**
   ```bash
   grep -n "FINDER_TOKEN" logs/server.log | head -10
   ```

3. **MCP Tools Discovery:**
   ```bash
   .venv/bin/python discover_mcp_tools.py
   ```

## 🔧 **COMMON ISSUES & FIXES**

### **Issue 1: "grep: logs/server.log: No such file or directory"**
**Cause**: Still in workspace root `/home/mike/repos` instead of `/home/mike/repos/pipulate`  
**Fix**: Run `cd pipulate` first
**Why**: The logs/, plugins/, and Python scripts are in the pipulate subdirectory

### **Issue 2: "ModuleNotFoundError: No module named 'aiohttp'"**
**Cause**: Using system Python instead of virtual environment Python  
**Fix**: Use `.venv/bin/python` instead of `python`
**Why**: The `discover_mcp_tools.py` script needs dependencies that are only installed in the virtual environment

### **Issue 3: "Not in Nix shell environment"**
**Cause**: Nix development environment not active
**Fix**: Run `nix develop .#quiet`

### **Issue 4: Virtual environment exists but not in PATH**
**Cause**: Environment variables not properly set
**Fix**: Use `.venv/bin/python` for all Python commands

### **Issue 5: discover_mcp_tools.py returns NoneType error**
**Cause**: Script returns None when import fails, then tries to access results['total_tools']
**Fix**: Script has been updated with proper error handling - use `.venv/bin/python discover_mcp_tools.py`

## 🎭 **THE DELIGHTFUL EXPERIENCE**

**Once in correct directory with working environment, you get access to:**
- **39 MCP tools** across 6 categories
- **Browser automation** with Selenium
- **Workflow inspection** and debugging
- **Log transparency** with FINDER_TOKEN system
- **Rapid iteration** capabilities

## 📚 **COMPLETE DOCUMENTATION**

- **Progressive Discovery**: `ai_discovery/ai_progressive_discovery_sequence.md`
- **MCP Tools Guide**: `ai_discovery/ai_mcp_tools_discovery_guide.md`
- **Python Path Analysis**: `ai_discovery/ai_python_path_issue_analysis.md`

---

**🎯 Remember: Navigate to pipulate/ FIRST, then environment validation, then discovery!** 
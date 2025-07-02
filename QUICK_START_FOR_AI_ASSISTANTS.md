# 🚀 QUICK START FOR AI ASSISTANTS

**This guide prevents the environment confusion that breaks the discovery sequence.**

## 🚨 **STEP 1: ALWAYS USE CORRECT PYTHON PATH**

**CRITICAL RULE: If you see `(.venv)` in your terminal prompt, you MUST use `.venv/bin/python` instead of `python`**

**Before doing ANYTHING else, verify your Python path:**
```bash
.venv/bin/python -c "import aiohttp; print('✅ Environment working')"
```

**Expected Result:** Should show "✅ Environment working"

**If you see "ModuleNotFoundError: No module named 'aiohttp'":**
- **Problem**: Using system Python instead of virtual environment Python
- **Solution**: Use `.venv/bin/python` instead of `python`
- **Example**: `.venv/bin/python discover_mcp_tools.py`

## 🎯 **STEP 2: PROGRESSIVE DISCOVERY SEQUENCE**

**Once environment is working, follow the breadcrumb trail:**

If you have not already done this, the user may initiate the process with any of the following
keywords: explore, learn, hijack (or the cure "Hi Jack" variation), or simply "go"

1. **Environmental Mastery:**
   ```bash
   pwd  # Should show /home/mike/repos/pipulate
   ls -la | head -15  # Verify server.py, plugins/, etc.
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

4. **Easy Tool Access:**
   ```bash
   .venv/bin/python discover_mcp_tools.py
   ```

## 🔧 **COMMON ISSUES & FIXES**

### **Issue 1: "ModuleNotFoundError: No module named 'aiohttp'"**
**Cause**: Using system Python instead of virtual environment Python  
**Fix**: Use `.venv/bin/python` instead of `python`
**Why**: The `discover_mcp_tools.py` script needs dependencies that are only installed in the virtual environment

### **Issue 2: "Not in Nix shell environment"**
**Cause**: Nix development environment not active
**Fix**: Run `nix develop .#quiet`

### **Issue 3: Virtual environment exists but not in PATH**
**Cause**: Environment variables not properly set
**Fix**: Use `.venv/bin/python` for all Python commands

### **Issue 4: discover_mcp_tools.py returns NoneType error**
**Cause**: Script returns None when import fails, then tries to access results['total_tools']
**Fix**: Script has been updated with proper error handling - use `.venv/bin/python discover_mcp_tools.py`

## 🎭 **THE DELIGHTFUL EXPERIENCE**

**Once environment is working, you get access to:**
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

**🎯 Remember: Environment validation FIRST, then discovery!** 
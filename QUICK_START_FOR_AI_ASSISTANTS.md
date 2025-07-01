# 🚀 QUICK START FOR AI ASSISTANTS

**This guide prevents the environment confusion that breaks the discovery sequence.**

## 🚨 **STEP 1: ALWAYS VALIDATE ENVIRONMENT FIRST**

**Before doing ANYTHING else, run this diagnostic:**
```bash
python test_python_environment_fix.py
```

**Expected Result:** All checks should show ✅ PASS

**If you see "ModuleNotFoundError: No module named 'aiohttp'":**
- **Problem**: Virtual environment not properly activated
- **Solution**: Use `.venv/bin/python` instead of `python`
- **Example**: `.venv/bin/python discover_mcp_tools.py`

## 🎯 **STEP 2: PROGRESSIVE DISCOVERY SEQUENCE**

**Once environment is working, follow the breadcrumb trail:**

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
   .venv/bin/python helpers/ai_tool_discovery.py
   ```

## 🔧 **COMMON ISSUES & FIXES**

### **Issue 1: "ModuleNotFoundError: No module named 'aiohttp'"**
**Cause**: Using system Python instead of virtual environment Python
**Fix**: Use `.venv/bin/python` instead of `python`

### **Issue 2: "Not in Nix shell environment"**
**Cause**: Nix development environment not active
**Fix**: Run `nix develop .#quiet`

### **Issue 3: Virtual environment exists but not in PATH**
**Cause**: Environment variables not properly set
**Fix**: Use `.venv/bin/python` for all Python commands

## 🎭 **THE DELIGHTFUL EXPERIENCE**

**Once environment is working, you get access to:**
- **39 MCP tools** across 6 categories
- **Browser automation** with Selenium
- **Workflow inspection** and debugging
- **Log transparency** with FINDER_TOKEN system
- **Rapid iteration** capabilities

## 📚 **COMPLETE DOCUMENTATION**

- **Progressive Discovery**: `helpers/docs_sync/considerations/ai_progressive_discovery_sequence.md`
- **MCP Tools Guide**: `helpers/docs_sync/considerations/AI_MCP_TOOLS_DISCOVERY_GUIDE.md`
- **Environment Diagnostic**: `test_python_environment_fix.py`

---

**🎯 Remember: Environment validation FIRST, then discovery!** 
# Mike's Quick Guide: Taming server.py 

**Problem**: `server.py` is 73,771 tokens and breaking your 130K token budget for `foo_files.py`

**Solution**: Surgical refactoring into focused 129K token suite

## 🎯 The Plan

Break server.py into these focused files:
- `server.py` (~17K) - Core app setup  
- `pipeline.py` (~20K) - Pipulate class
- `routes.py` (~20K) - HTTP endpoints
- `plugin_system.py` (~8K) - Plugin management
- `logging_utils.py` (~5K) - Logging utilities
- `database.py` (~3K) - Database operations

**Total**: 129K tokens (perfect for your budget!)

## 🚀 Quick Start (3 Commands)

### 1. Create the plan
```bash
cd helpers/code_surgery
../../.venv/bin/python server_refactor_demo.py
```

This analyzes server.py and creates a refactoring plan at `/tmp/code_surgery/plans/refactor_server_*.json`

### 2. Execute the refactoring
```bash
../../.venv/bin/python code_slicer.py execute /tmp/code_surgery/plans/refactor_server_*.json
```

This performs the actual surgery with full git safety.

### 3. If something goes wrong
```bash
../../.venv/bin/python code_slicer.py rollback /tmp/code_surgery/plans/refactor_server_*.json
```

This restores everything to exactly how it was.

## 🛡️ Safety Features

- **Git checkpoint created automatically** before any changes
- **Complete rollback capability** if anything goes wrong
- **Idempotent operations** - can run multiple times safely
- **AST-based parsing** - respects Python structure perfectly
- **Import dependency management** - no broken imports

## 🔍 What The Tools Do

1. **Parse server.py into 264 atomic code blocks** using AST analysis
2. **Categorize blocks intelligently** (imports, classes, endpoints, utilities)
3. **Map blocks to target files** based on domain responsibility
4. **Calculate import dependencies** to prevent namespace issues
5. **Create git checkpoint** for safety
6. **Slice and reassemble** with surgical precision

## 📊 Expected Results

**Before**:
- server.py: 73,771 tokens (57% of your budget)
- Can't fit other important files

**After**:
- server.py: ~17,000 tokens (13% of budget)
- pipeline.py: ~20,000 tokens  
- routes.py: ~20,000 tokens
- plugin_system.py: ~8,000 tokens
- logging_utils.py: ~5,000 tokens
- database.py: ~3,000 tokens
- mcp_tools.py: 52,367 tokens (unchanged)
- common.py: 4,288 tokens (unchanged)

**Total**: ~129K tokens - right at your target!

## 🎯 Why This Works

- **Atomic boundaries**: Only cuts at safe top-level boundaries
- **Preserves functionality**: Each file remains a valid Python module
- **Maintains imports**: Dependency tracker ensures all imports work
- **Domain separation**: Related code stays together
- **Git safety**: Full rollback if anything breaks

## 🚨 Before You Start

1. **Commit your current work** - Start with a clean git state
2. **Work in a branch** - `git checkout -b refactor-server-py`
3. **Test after refactoring** - Run your tests to verify everything works

## 🐛 If Something Goes Wrong

The tools are designed to be bulletproof, but if you hit issues:

1. **Check git status** - The rollback should restore everything
2. **Look at the plan file** - It shows exactly what was attempted
3. **Run validation** - The tools validate before executing
4. **Start fresh** - Delete `/tmp/code_surgery` and try again

## 🎉 Success Criteria

After refactoring, you should have:
- ✅ server.py is now ~17K tokens instead of 73K
- ✅ All files together total ~129K tokens  
- ✅ Your foo_files.py selections fit the 130K budget
- ✅ The server still starts and works normally
- ✅ All imports resolve correctly
- ✅ Plugin system still works

## 💡 Pro Tips

- **The tools are deterministic** - same input = same output
- **Block IDs are stable** - based on content, not line numbers
- **Import management is automatic** - dependencies calculated for you
- **Temporary files self-assemble** - named so they could rebuild themselves

This solves your token budget problem while making the codebase more maintainable. The monolithic server.py becomes a focused suite of domain-specific modules.

**Ready? Let's slice and dice!** 🔪 
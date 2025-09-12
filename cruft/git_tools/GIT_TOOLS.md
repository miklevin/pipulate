# GIT_TOOLS.md - Git Automation & Recovery Tools

**Single source of truth for `/home/mike/repos/pipulate/helpers/git_tools/`**

---

## 🎯 **Purpose**

This directory contains Git-related automation tools, scripts, and utilities for managing Pipulate's git workflows, cherry-picking, and repository management.

---

## 📋 **Contents**

### **Cherry-Pick Automation**
- `simple_cherry_pick.py` - Simple cherry-pick operations
- `systematic_cherry_pick.py` - Systematic cherry-pick with progress tracking

### **Git Workflow Tools**
- `git_simple_regression_finder.py` - Find regressions in git history
- `git-continue-wrapper.sh` - Wrapper for continuing git operations
- `setup-git-aliases.sh` - Setup useful git aliases

### **Analysis & Documentation**
- `git_dependencies.ipynb` - Jupyter notebook for analyzing git dependencies

---

## 🔧 **Usage Patterns**

### **Cherry-Pick Operations**
```bash
# Simple cherry-pick
python helpers/git_tools/simple_cherry_pick.py

# Systematic with progress tracking
python helpers/git_tools/systematic_cherry_pick.py
```

### **Regression Hunting**
```bash
# Find when a regression was introduced
python helpers/git_tools/git_simple_regression_finder.py
```

### **Git Setup**
```bash
# Setup useful aliases
bash helpers/git_tools/setup-git-aliases.sh
```

---

## 🚨 **Golden Path Integration**

These tools are part of the anti-regression immune system:
- Used for safely banking wins in branches
- Systematic recovery from git conflicts
- Automated regression hunting

**All tools follow the conservative "bank small wins" philosophy.** 
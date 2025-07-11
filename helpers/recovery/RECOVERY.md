# RECOVERY.md - System Recovery Tools

**Single source of truth for `/home/mike/repos/pipulate/helpers/recovery/`**

---

## 🎯 **Purpose**

This directory contains recovery tools, backup systems, and utilities for restoring Pipulate to working states after issues or experiments.

---

## 📋 **Contents**

### **Recovery Scripts**
- `patch_based_recovery.py` - Patch-based system recovery
- `recovered_cli.py` - Recovered CLI implementation

### **Backup Systems**
- `server.py.backup` - Known-good server backup

---

## 🔧 **Usage Patterns**

### **System Recovery**
```bash
# Patch-based recovery
python helpers/recovery/patch_based_recovery.py

# Use recovered CLI
python helpers/recovery/recovered_cli.py
```

### **Emergency Procedures**
When the main system fails:
1. Check `server.py.backup` for last known good state
2. Use `patch_based_recovery.py` for systematic restoration
3. Leverage recovery logs in `/logs` for diagnosis

---

## 🚨 **Anti-Regression Philosophy**

These tools embody the core principle:
- **"Things go in ebbs and flows"** - Sometimes we need to step back
- **Conservative Recovery** - Bank wins, then safely restore
- **No State Loss** - Always preserve the path back to working state

**Recovery tools are the safety net that enables fearless experimentation.** 
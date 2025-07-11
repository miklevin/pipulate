# DIAGNOSTICS.md - System Diagnostic Tools

**Single source of truth for `/home/mike/repos/pipulate/helpers/diagnostics/`**

---

## 🎯 **Purpose**

This directory contains diagnostic tools for verifying system state, testing functionality, and validating the integrity of Pipulate's core systems.

---

## 📋 **Contents**

### **Conversation System Diagnostics**
- `diagnostic_conversation_loading.py` - Test conversation loading mechanisms
- `final_conversation_persistence_verification.py` - Verify conversation persistence

### **Validation Reports**
- `VALIDATION_REPORT.md` - System validation results and status

---

## 🔧 **Usage Patterns**

### **System Verification**
```bash
# Test conversation loading
python helpers/diagnostics/diagnostic_conversation_loading.py

# Verify persistence
python helpers/diagnostics/final_conversation_persistence_verification.py
```

### **Integration with MCP Tools**
These diagnostics complement MCP tools:
- `pipeline_state_inspector` - Real-time system state
- `ai_capability_test_suite` - Comprehensive capability testing

---

## 🚨 **Anti-Regression Role**

These tools are critical for:
- **Bedrock Testing** - Verifying core functionality never breaks
- **State Validation** - Ensuring system integrity
- **Regression Detection** - Catching breaks before they spread

**These tools embody the "know everything that's happening" philosophy.** 
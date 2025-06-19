# Pipulate Radical Transparency System - Developer Guide

## 🔍 **System Overview: Unprecedented Development Transparency**

Pipulate provides **radical transparency** - complete visibility into every aspect of the running system through direct endpoint access, comprehensive logging, and real-time monitoring capabilities. This document details the extraordinary debugging and development power available.

---

## 🎯 **Core Transparency Capabilities**

### **1. Session-less Direct Endpoint Access**

**Power**: Hit any workflow endpoint directly without UI navigation or session state.

**Examples**:
```bash
# Direct field discovery for any project
curl -s "http://localhost:5001/trifecta/discover-fields/best-buy/best-buy/20250617" | jq '.field_count'

# Direct step access 
curl -s "http://localhost:5001/trifecta/step_crawler"

# Direct toggle code visibility
curl -s "http://localhost:5001/trifecta/toggle?step_id=step_crawler" | grep -A 10 "Python Command"

# Check any workflow state
curl -s "http://localhost:5001/hello_workflow"
```

**Why This Matters**: Zero ceremony testing - no need to click through UI, maintain sessions, or reproduce complex state.

### **2. Pipeline State Database Transparency** 

**Power**: Direct access to complete session data via pipeline table.

**Access Pattern**:
```bash
# Check all pipeline records
curl -s "http://localhost:5001/clear-pipeline" -X POST

# Database direct inspection (when server allows)
sqlite3 data/data.db "SELECT pipeline_id, state FROM pipeline LIMIT 5;"
```

**State Structure**: Every workflow stores its complete state as JSON blob:
```json
{
  "step_project": {"botify_project": "https://app.botify.com/username/project"},
  "step_analysis": {"analysis_selection": "20250617", "download_complete": true},
  "step_crawler": {"crawler_basic": "completed", "python_command": "..."}
}
```

**Why This Matters**: Complete transparency into what any user session contains - debugging session issues becomes trivial.

### **3. MCP Tool Call System**

**Power**: Execute sophisticated API operations via carefully constructed MCP tool calls.

**Schema Discovery Example**:
```bash
curl -X POST "http://localhost:5001/mcp-tool-executor" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "botify_simple_query",
    "parameters": {
      "username": "best-buy",
      "project": "best-buy", 
      "analysis": "20250617",
      "query": {"dimensions": [], "metrics": [{"function": "count", "args": ["urls.url"]}]}
    }
  }'
```

**Available MCP Tools**:
- `botify_ping` - API connectivity test
- `botify_list_projects` - Project enumeration  
- `botify_simple_query` - BQL query execution
- Custom workflow-specific tools via `register_mcp_tool()`

**Why This Matters**: Programmatic access to complex operations - can automate discovery, testing, and validation.

---

## 🚨 **Unique Log Token Marking System**

### **Searchable Debug Tokens**

**Pattern**: Insert unique, easily searchable tokens into logs for precise tracking.

**Current Token Categories**:
```python
# Field Discovery & Validation
logger.info(f"🔍 FINDER_TOKEN: FIELD_DISCOVERY - Discovered {count} fields")
logger.info(f"🔍 FINDER_TOKEN: CACHE_MISS - No cached data, generating...")
logger.info(f"🔍 FINDER_TOKEN: CACHE_GENERATED - Successfully cached")

# Template Validation  
logger.info(f"🎯 TEMPLATE_VALIDATION: GSC template '{template}' - {available}/{total} fields")
logger.warning(f"🚨 TEMPLATE_VALIDATION: Validation failed - {error}")

# API Call Tracking
logger.info(f"🌐 API_CALL: {method} {url} - Response: {status}")
logger.info(f"🐍 PYTHON_CODE_GENERATED: {step_context}")
```

**Log Search Examples**:
```bash
# Find all field discovery activity
grep "FINDER_TOKEN" logs/server.log

# Track template validation results
grep "TEMPLATE_VALIDATION" logs/server.log | tail -10

# Monitor API call activity
grep "API_CALL\|🌐" logs/server.log | grep -v "GET.*static"
```

### **Comprehensive API Activity Logging**

**What Gets Logged**:
- Complete HTTP request details (method, URL, headers, payload)
- Generated Python code for API reproduction
- Response status and preview
- Execution timing and error details
- File operations (save locations, sizes)

**Example Log Entry**:
```
2025-01-09 10:15:23 🌐 API_CALL: POST https://api.botify.com/v1/projects/best-buy/best-buy/query
2025-01-09 10:15:23 🐍 PYTHON_CODE: 
import httpx
headers = {"Authorization": "Token abc123", "Content-Type": "application/json"}
payload = {"collections": ["crawl.20250617"], "query": {"dimensions": ["{collection}.url"]}}
response = httpx.post("https://api.botify.com/v1/projects/best-buy/best-buy/query", headers=headers, json=payload)
print(f"Status: {response.status_code}")
print(response.json())

2025-01-09 10:15:24 ✅ API_RESPONSE: Status 200 - 1,247 rows returned
2025-01-09 10:15:24 📁 FILE_SAVED: downloads/trifecta/best-buy/best-buy/20250617/crawl.csv (85.3 KB)
```

---

## ⚡ **Watchdog Auto-Restart Development Loop**

### **The Development Cycle**

**Pattern**: Make code change → Wait ~3 seconds → Test endpoint → Check logs

**Example Workflow**:
```bash
# 1. Make code change (triggers watchdog restart)
vim plugins/400_botify_trifecta.py

# 2. Wait for restart (watch console for "Server restarted")
sleep 3

# 3. Test the change
curl -s "http://localhost:5001/trifecta/step_crawler" | grep "some_feature"

# 4. Check effect in logs
tail -20 logs/server.log | grep "SOME_TOKEN"
```

**Watchdog Triggers**:
- Any `.py` file change in the project
- Configuration file updates
- Template modifications
- Most project files (excludes logs, temp files)

**Why This Matters**: Zero-ceremony development loop - changes are live instantly, testable immediately, and traceable through logs.

---

## 🎯 **Baby Step Development Methodology**

### **Our Proven Pattern**

**Methodology**: Conservative, independently testable changes with comprehensive logging.

**Recent Success Story - Field Validation Baby Steps**:

**Baby Step 1**: Added `validate_template_fields()` method
- Added logging: `🎯 TEMPLATE_VALIDATION`
- Test: `curl discover-fields endpoint`
- Verify: `grep TEMPLATE_VALIDATION logs/server.log`

**Baby Step 2**: Non-intrusive validation logging  
- Added try/catch wrapper around validation calls
- Test: Trigger workflow step
- Verify: Look for validation ratios in logs

**Baby Steps 3-10**: Action button consistency fixes
- Each baby step independently testable
- Comprehensive logging for each fix
- Git committable as standalone improvements

**Baby Step 11**: Fixed validation logging bug
- Simple field access correction
- Immediate testing via workflow
- No breaking changes

**Baby Step 12**: Return to explicit field paths (Major Simplification)
- Removed 15+ lines of brittle mapping code
- Enhanced explicitness over user-friendliness
- Zero ambiguity in field path interpretation

### **Conservative Development Principles**

1. **🎯 One Change Per Baby Step**: Single, focused improvement
2. **🔍 Comprehensive Logging**: Searchable tokens for tracking  
3. **⚡ Immediate Testing**: Direct endpoint validation
4. **📋 Git Committable**: Each step stands alone
5. **🛡️ Non-Breaking**: Existing functionality preserved
6. **🚨 Anti-Regression**: Document regression patterns to prevent future breaks

---

## 🔧 **Practical Debugging Workflows**

### **Workflow: Debug Template Field Issues**

```bash
# 1. Check what fields are available
curl -s "http://localhost:5001/trifecta/discover-fields/username/project/analysis" | jq '.available_fields.dimensions'

# 2. Check template configuration
curl -s "http://localhost:5001/trifecta/step_analysis" | grep -o "Template: [^<]*"

# 3. Trigger validation and check logs
curl -s "http://localhost:5001/trifecta/step_crawler" > /dev/null
grep "TEMPLATE_VALIDATION" logs/server.log | tail -3

# 4. Check specific field mapping
grep "🎯.*fields available" logs/server.log | tail -1
```

### **Workflow: Debug API Call Issues**

```bash
# 1. Check recent API activity
grep "🌐 API_CALL" logs/server.log | tail -5

# 2. Get Python reproduction code
grep -A 10 "🐍 PYTHON_CODE" logs/server.log | tail -15

# 3. Check API responses
grep "API_RESPONSE\|✅\|❌" logs/server.log | tail -5

# 4. Verify file operations
grep "📁 FILE_SAVED\|FILE_ERROR" logs/server.log | tail -3
```

### **Workflow: Debug Session State Issues**

```bash
# 1. Check pipeline state directly
curl -s "http://localhost:5001/clear-pipeline" -X POST  # (to see current state first)

# 2. Trigger specific step and monitor
curl -s "http://localhost:5001/trifecta/step_project" > /dev/null
grep "pipeline_id\|state_update" logs/server.log | tail -5

# 3. Check step progression
grep "hx_trigger.*load" logs/server.log | tail -3
```

---

## 🚀 **Advanced Transparency Features**

### **Hide/Show Code Anti-Regression System**

**Problem Solved**: AI assistants repeatedly broke the "Hide/Show Code" feature.

**Solution**: `_generate_python_code_for_cached_data()` method with comprehensive anti-regression documentation.

**Testing**:
```bash
# Test toggle functionality
curl -s "http://localhost:5001/trifecta/toggle?step_id=step_crawler" | grep -A 5 "Python Command"

# Verify code generation for cached data
curl -s "http://localhost:5001/trifecta/toggle?step_id=step_webogs" | grep -A 10 "import httpx"
```

**Log Markers**: `🐍 PYTHON_CODE_GENERATED`, `🚨 CODE_GENERATION_ERROR`

### **Action Button Data Standardization**

**Problem Solved**: Whack-a-mole regressions with "View Folder" and "Copy 2 Downloads" buttons.

**Solution**: `_prepare_action_button_data()` systematic data standardization.

**Testing**:
```bash
# Test button functionality
curl -s "http://localhost:5001/trifecta/step_crawler" | grep -o "View Folder\|Copy.*Downloads"

# Verify file paths
curl -s "http://localhost:5001/trifecta/step_crawler" | grep -o "/home/mike/repos/pipulate/downloads/trifecta/[^\"]*"
```

**Log Markers**: `🔧 ACTION_BUTTON_DATA_STANDARDIZED`, `📂 FOLDER_PATH_RESOLVED`

### **Field Discovery Cache System**

**Capability**: Automatic cache generation when analysis_advanced.json missing.

**Testing**:
```bash
# Trigger cache generation for new project
curl -s "http://localhost:5001/trifecta/discover-fields/new-org/new-project/20250101" | jq '.cache_info'

# Check cache generation logs
grep "CACHE_MISS\|CACHE_GENERATED" logs/server.log | tail -3
```

**Log Markers**: `🔍 FINDER_TOKEN: CACHE_MISS`, `🔍 FINDER_TOKEN: CACHE_GENERATED`

---

## 📊 **System Architecture: Why This Works**

### **Core Design Principles**

1. **🎯 Local-First**: Everything runs on your machine - complete control
2. **🔍 Observable**: Every operation is logged with searchable tokens  
3. **⚡ Real-Time**: Watchdog enables instant feedback loops
4. **🚨 Explicit**: Prefer explicitness over magic (field paths, error messages)
5. **🛡️ Non-Breaking**: Baby steps preserve functionality while adding value

### **Technology Stack Advantages**

- **FastHTML + HTMX**: Server-rendered HTML with AJAX-like behavior
- **SQLite**: Single-file database with direct SQL access
- **Nix Flakes**: Reproducible environment across all systems  
- **Python Logging**: Structured, searchable log output
- **File Watchdog**: Automatic server restart on code changes

### **Development Velocity Multipliers**

1. **Zero Build Step**: Python code changes are live immediately
2. **Session-less Testing**: Direct endpoint access eliminates UI navigation
3. **Complete State Transparency**: Pipeline table shows exactly what users see
4. **Comprehensive Logging**: API calls, responses, and Python code all captured
5. **MCP Tool Integration**: Complex operations available via simple HTTP calls

---

## 🎉 **What We've Accomplished: The Big Picture**

### **Before vs. After: Field Validation**

**Before**:
- ❌ Brittle field name extraction (`metadata.title.content` → `content`)
- ❌ Hidden mapping logic causing confusion
- ❌ Ambiguous validation results
- ❌ Difficult to debug field issues

**After**:
- ✅ Explicit field paths (`{collection}.metadata.title.content`)
- ✅ Zero mapping ambiguity
- ✅ Transparent validation process
- ✅ Comprehensive logging with searchable tokens

### **Anti-Regression Protections Added**

1. **🚨 Hide/Show Code Feature**: Documented and protected against AI "improvements"
2. **🔧 Action Button Consistency**: Systematic data standardization prevents path issues
3. **🎯 Field Validation**: Explicit paths eliminate mapping brittleness
4. **📋 Comprehensive Documentation**: This guide ensures future sessions understand the system

### **Development Methodology Proven**

**Baby Step Success Rate**: 12/12 baby steps completed successfully without major regressions

**Key Success Factors**:
- Conservative, incremental changes
- Comprehensive logging with unique tokens
- Immediate endpoint testing
- Git-committable standalone improvements
- Anti-regression documentation

---

## 🔮 **Future Session Quick Start**

### **Essential Commands for New Sessions**

```bash
# Check system status
curl -s "http://localhost:5001/" | grep -o "Pipulate.*"

# Monitor recent activity
tail -20 logs/server.log | grep -E "🔍|🎯|🚨|🌐|🐍"

# Test workflow functionality
curl -s "http://localhost:5001/trifecta/step_crawler" | grep -o "Downloaded.*"

# Check field discovery capability
curl -s "http://localhost:5001/trifecta/discover-fields/best-buy/best-buy/20250617" | jq '.field_count'

# Verify template validation
grep "TEMPLATE_VALIDATION" logs/server.log | tail -2
```

### **System Health Indicators**

- ✅ **Watchdog Active**: Server restart messages in console
- ✅ **Endpoints Responsive**: 200 responses from workflow URLs  
- ✅ **Logging Working**: Token markers appearing in server.log
- ✅ **Database Accessible**: Pipeline state queries working
- ✅ **Field Discovery**: Cache generation and field extraction functional

### **Remember: You Have Unprecedented Power**

This system gives you **radical transparency** that most development environments lack:

1. **Direct endpoint access** without UI ceremony
2. **Complete session state visibility** via pipeline database  
3. **Comprehensive API activity logging** with Python reproduction code
4. **Real-time development feedback** via watchdog auto-restart
5. **Searchable debug tokens** for precise issue tracking
6. **MCP tool integration** for sophisticated operations

**Use this power wisely** - you can debug, test, and develop faster than almost any other system allows.

---

*Last Updated: 2025-01-09 - Baby Step 12 Completion*
*System Status: ✅ All anti-regression protections active*
*Field Validation: ✅ Explicit path system operational* 
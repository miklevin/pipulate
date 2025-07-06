# 🎯 AI Static Initialization Constants

## 🔥 FUNDAMENTAL SYSTEM TRUTHS - NEVER QUESTION THESE

### **📍 Database Locations (ABSOLUTE CONSTANTS)**
```
CONVERSATION_DATABASE = "data/discussion.db"  # When running from pipulate directory
PIPELINE_DATABASE = "data/pipulate.db"       # When running from pipulate directory
BACKUP_DATABASE = "data/backup.db"           # When running from pipulate directory
```

### **🌐 Server Configuration (IMMUTABLE)**
```
SERVER_HOST = "localhost"
SERVER_PORT = 5001
SERVER_URL = "http://localhost:5001"
CHAT_ENDPOINT = "/chat"
MCP_ENDPOINT = "/mcp-tool-executor"
```

### **📁 Directory Structure (FIXED PATHS)**
```
WORKSPACE_ROOT = "/home/mike/repos"
PIPULATE_ROOT = "/home/mike/repos/pipulate"
AI_DISCOVERY_DIR = "pipulate/ai_discovery"
BROWSER_AUTOMATION_DIR = "pipulate/browser_automation"
LOGS_DIR = "pipulate/logs"
DATA_DIR = "pipulate/data"
STATIC_DIR = "pipulate/static"
```

### **🎭 Chat Interface Constants (UI SELECTORS)**
```
CHAT_TEXTAREA = 'textarea[name="msg"]'
CHAT_SUBMIT_BUTTON = 'button[type="submit"]'
CHAT_MESSAGES_CONTAINER = '.messages'
CHAT_INPUT_FORM = 'form'
```

### **⏰ LLM Streaming Timing (CRITICAL FOR BROWSER AUTOMATION)**
```
LLM_RESPONSE_INITIAL_WAIT = 3     # Wait for response to start
LLM_RESPONSE_STREAMING_WAIT = 15  # Wait for streaming to complete
LLM_RESPONSE_FINALIZATION_WAIT = 3 # Wait for conversation save
BROWSER_INTERACTION_DELAY = 2     # Delay between browser actions
SERVER_RESTART_WAIT = 8           # Wait for server restart
```

### **🔧 MCP Tool Registry (CORE TOOLS)**
```
ESSENTIAL_TOOLS = [
    "pipeline_state_inspector",
    "browser_scrape_page", 
    "browser_interact_with_current_page",
    "local_llm_grep_logs",
    "execute_shell_command",
    "server_reboot",
    "conversation_history_view",
    "conversation_history_stats"
]
```

### **🍞 Breadcrumb System (AI DISCOVERY)**
```
BREADCRUMB_MARKERS = [
    "AI_BREADCRUMB_01",
    "AI_BREADCRUMB_02", 
    "AI_BREADCRUMB_03",
    "AI_BREADCRUMB_04",
    "AI_BREADCRUMB_05",
    "AI_BREADCRUMB_06"
]
FINDER_TOKEN = "FINDER_TOKEN"
LOG_SEARCH_PATTERNS = ["🌐 NETWORK", "💾 FINDER_TOKEN", "🎭 AI_CREATIVE"]
```

### **⚡ Golden Path Commands (ENVIRONMENT AGNOSTIC)**
```
GOLDEN_PATH_BASE = "cd pipulate && .venv/bin/python cli.py call"
STATE_INSPECTOR = "cd pipulate && .venv/bin/python cli.py call pipeline_state_inspector"
LOG_SEARCH = "cd pipulate && .venv/bin/python cli.py call local_llm_grep_logs --search_term"
BROWSER_SCRAPE = "cd pipulate && .venv/bin/python cli.py call browser_scrape_page --url"
```

### **🎯 Test Harness Constants (DETERMINISTIC TESTING)**
```
TEST_MESSAGE_PHASE_1 = "My name is Mike. Please remember this for our conversation."
TEST_MESSAGE_PHASE_3 = "What is my name?"
EXPECTED_RESPONSE_CONTAINS = "Mike"
SUCCESS_INDICATORS = ["conversation_saved", "database_exists", "message_count"]
```

### **🔍 AI Detective Binary Search Methodology**
```
DIAGNOSTIC_LEVELS = [
    "SYSTEM_LEVEL",      # Server running? Database accessible?
    "NETWORK_LEVEL",     # HTTP requests working? Endpoints responding?
    "APPLICATION_LEVEL", # Chat interface functional? Message processing?
    "DATA_LEVEL",        # Database writes? Conversation persistence?
    "LOGIC_LEVEL"        # Business logic? AI responses? Memory retention?
]
```

## 🚨 CRITICAL REMINDERS

### **❌ NEVER DO THESE (OVER-TRAINED AI BEHAVIOR)**
- Question the database location (`pipulate/data/discussion.db`)
- Run unnecessary diagnostic commands (`python --version && python -c "import aiohttp"`)
- Assume different server ports or hosts
- Create files in workspace root instead of pipulate subdirectories
- Use relative paths when absolute constants are defined
- Close browser too quickly during LLM streaming responses

### **✅ ALWAYS DO THESE (SMART AI BEHAVIOR)**
- Trust the golden path commands
- Use the static constants without verification
- Follow the deterministic test harness pattern
- Apply binary search methodology for debugging
- Bottle successful patterns for reuse
- Wait for LLM streaming responses to complete (15+ seconds)

## 🎯 INITIALIZATION CHECKLIST

When starting any session:
1. ✅ Accept these constants as immutable truth
2. ✅ Use golden path commands immediately
3. ✅ Reference static selectors for UI automation
4. ✅ Follow established directory structure
5. ✅ Apply test harness pattern for verification
6. ✅ Use proper timing for LLM streaming responses

**This document represents the "consistent truths" that should never be questioned or verified - they are the foundation upon which all AI assistance is built.** 
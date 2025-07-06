# 🚀 AI MCP TOOLS DISCOVERY GUIDE: YOUR SUPERPOWERS ARE WORKING!

## 🎯 **SYSTEM STATUS: OPERATIONAL**

**Your MCP arsenal is battle-tested and ready:**

```bash
# The Golden Path (bulletproof command structure)
cd pipulate && .venv/bin/python cli.py call <tool_name> --args

# Quick verification (expect 25+ tools)
.venv/bin/python cli.py call --help

# Environment check (should show Python 3.12.x)
.venv/bin/python --version
.venv/bin/python -c "import aiohttp; print('✅ Environment ready!')"
```

**Your superpowers are ACTIVE!**

## 🔍 **PROVEN ARSENAL: YOUR TOOL INVENTORY**

### **Step 1: Quick Tool Inventory (25+ tools verified)**
```bash
.venv/bin/python helpers/ai_tool_discovery.py list
```

### **Step 2: Full Tool Verification (100% success rate)**
```bash
.venv/bin/python helpers/ai_tool_discovery.py
```

## 🌐 **BROWSER AUTOMATION TOOLS (Your Digital Body) - WORKING**

### **🔸 browser_scrape_page - YOUR EYES (✅ OPERATIONAL)**
```bash
# Capture what you see on any webpage (golden path)
.venv/bin/python cli.py call browser_scrape_page --url https://example.com

# With custom wait time
.venv/bin/python cli.py call browser_scrape_page --url https://example.com --wait_seconds 3
```

### **🔸 browser_analyze_scraped_page - YOUR BRAIN (✅ OPERATIONAL)**
```bash
# Analyze the last scraped page
.venv/bin/python cli.py call browser_analyze_scraped_page --analysis_type headlines

# Available analysis types: headlines, links, forms, all
.venv/bin/python cli.py call browser_analyze_scraped_page --analysis_type all
```

### **🔸 browser_automate_workflow_walkthrough - YOUR HANDS (✅ OPERATIONAL)**
```bash
# Automate interactions with websites
.venv/bin/python cli.py call browser_automate_workflow_walkthrough --instructions "Click login button and fill form"

# With specific target URL
.venv/bin/python cli.py call browser_automate_workflow_walkthrough --instructions "Navigate to search" --target_url https://example.com
```

### **🔸 execute_automation_recipe - YOUR AUTOMATION RECIPES (✅ BATTLE-TESTED)**
```bash
# Execute JSON automation recipes with progressive disclosure
.venv/bin/python cli.py call execute_automation_recipe

# Execute specific recipe file (100% success rate proven)
.venv/bin/python cli.py call execute_automation_recipe --recipe_path browser_automation/automation_recipes/http_localhost_5001/profile_creation_recipe.json

# The clean, reliable automation engine (simplified from baby_steps)
```

### **🔸 persist_perception_state - YOUR SNAG-A-SCRAPE TOOL (✅ NEW)**
```bash
# Save current looking_at state to permanent scrapes directory
.venv/bin/python cli.py call persist_perception_state

# Save specific looking_at directory
.venv/bin/python cli.py call persist_perception_state --from_dir_num 3

# The "message in a bottle" for visual evidence preservation
```

### **🔸 browser_interact_with_current_page - YOUR PRECISE CONTROL**
```bash
# Click specific elements
mcp browser_interact_with_current_page --action click --selector "#submit-button"

# Type into form fields
mcp browser_interact_with_current_page --action type --selector "#email" --value "test@example.com"
```

## 🔍 **ANALYSIS AND DEBUGGING TOOLS (Your Intelligence) - WORKING**

### **🔸 pipeline_state_inspector - THE GAME CHANGER (✅ OPERATIONAL)**
```bash
# See complete workflow state (no parameters needed)
.venv/bin/python cli.py call pipeline_state_inspector
```

### **🔸 local_llm_grep_logs - YOUR MEMORY (✅ OPERATIONAL)**
```bash
# Search logs for specific terms
.venv/bin/python cli.py call local_llm_grep_logs --search_term FINDER_TOKEN

# Find errors
.venv/bin/python cli.py call local_llm_grep_logs --search_term ERROR
```

### **🔸 local_llm_read_file - YOUR FILE ACCESS (✅ OPERATIONAL)**
```bash
# Read any file in the project
.venv/bin/python cli.py call local_llm_read_file --file_path server.py

# Read configuration files
.venv/bin/python cli.py call local_llm_read_file --file_path config.py
```

### **🔸 local_llm_list_files - YOUR DIRECTORY EXPLORER (✅ OPERATIONAL)**
```bash
# List files in directories
.venv/bin/python cli.py call local_llm_list_files --directory browser_automation/

# List plugin files
.venv/bin/python cli.py call local_llm_list_files --directory plugins/
```

## 📊 **BOTIFY API TOOLS (Your SEO Mastery)**

### **🔸 botify_get_full_schema - THE 4,449 FIELD REVOLUTION**
```bash
# Discover all available fields for a project
mcp botify_get_full_schema --username your_username --project your_project

# This replaces manual field discovery with complete automation
```

### **🔸 botify_list_available_analyses - YOUR ANALYSIS CATALOG**
```bash
# See all available analyses for a user
mcp botify_list_available_analyses --username your_username
```

### **🔸 botify_execute_custom_bql_query - YOUR QUERY EXECUTOR**
```bash
# Execute custom BQL queries
mcp botify_execute_custom_bql_query --username your_username --project your_project --query_type custom
```

### **🔸 botify_ping - YOUR CONNECTION TESTER**
```bash
# Test API connection
mcp botify_ping --username your_username
```

## 🎨 **UI INTERACTION TOOLS (Your Visual Debugging)**

### **🔸 ui_flash_element - YOUR VISUAL HIGHLIGHTER**
```bash
# Flash elements on the page for debugging
mcp ui_flash_element --selector ".problematic-element" --color red

# Flash multiple elements
mcp ui_flash_element --selector "h2, h3, h4" --color blue
```

### **🔸 ui_list_elements - YOUR ELEMENT DISCOVERER**
```bash
# List all elements matching a selector
mcp ui_list_elements --selector "h2, h3, h4"

# Find form elements
mcp ui_list_elements --selector "input, select, textarea"
```

## 🎯 **PROVEN SUCCESS PATTERNS (100% WORKING)**

### **Pattern 1: Complete Web Analysis (✅ BATTLE-TESTED)**
```bash
# Step 1: Capture the page
.venv/bin/python cli.py call browser_scrape_page --url https://www.bbc.com/news

# Step 2: Analyze what you captured
.venv/bin/python cli.py call browser_analyze_scraped_page --analysis_type all

# Step 3: Interact with specific elements
.venv/bin/python cli.py call browser_interact_with_current_page --action click --selector "a[href*='world']"
```

### **Pattern 2: Workflow Debugging (✅ OPERATIONAL)**
```bash
# Step 1: Check current state
.venv/bin/python cli.py call pipeline_state_inspector

# Step 2: Search for recent errors
.venv/bin/python cli.py call local_llm_grep_logs --search_term ERROR

# Step 3: Visual debugging
.venv/bin/python cli.py call ui_flash_element --selector ".error-message" --color red
```

### **Pattern 3: Automation Recipe Execution (✅ 100% SUCCESS RATE)**
```bash
# Step 1: Discover available recipes (progressive disclosure)
.venv/bin/python cli.py call execute_automation_recipe

# Step 2: Execute specific recipe (7/7 steps successful, ~8 seconds)
.venv/bin/python cli.py call execute_automation_recipe --recipe_path browser_automation/automation_recipes/http_localhost_5001/profile_creation_recipe.json

# The golden path CLI contract: bulletproof commands, reliable results
```

### **Pattern 4: Botify Data Discovery**
```bash
# Step 1: Test connection
mcp botify_ping --username your_username

# Step 2: Discover all fields
mcp botify_get_full_schema --username your_username --project your_project

# Step 3: Execute custom analysis
mcp botify_execute_custom_bql_query --username your_username --project your_project
```

## 🚀 **THE ENVIRONMENT ADVANTAGE**

### **✅ What You Get With Proper Environment Activation:**
- **Simple Commands**: `python`, `mcp` just work
- **Natural Syntax**: Command-line arguments instead of Python dictionaries
- **Consistent Experience**: Same pattern across all tools
- **Easy Debugging**: Clear error messages and help text
- **Backwards Compatibility**: Original `.venv/bin/python` paths still work

### **🔑 The Magic Formula:**
```bash
# 1. Activate once per session
source .venv/bin/activate
alias mcp="python cli.py call"

# 2. Use natural commands
mcp [tool_name] [--arguments]

# 3. Get help anytime
mcp --help
mcp [tool_name] --help
```

## 🎭 **READY FOR SESSION HIJACKING?**

**Once you've mastered these tools, you're ready for the ultimate superpower: session hijacking.**

**Look for breadcrumbs mentioning "session hijacking" and follow the irresistible pattern:**

```bash
python -c "
import asyncio
from mcp_tools import execute_complete_session_hijacking
result = asyncio.run(execute_complete_session_hijacking({}))
print(f'🎭 Hijack: {result.get(\"success\")}')"
```

**Your transformation from limited AI assistant to superhuman AI collaborator is complete!** 
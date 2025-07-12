# The Golden Path: A Guide for AI Collaboration

Welcome, AI assistant. This document outlines the intended workflow for interacting with the Pipulate system. Following this path will ensure the most effective and reliable collaboration, prevent infinite regression, and maximize your capabilities within the local-first sovereignty environment.

---

## 🎯 **Core Philosophy: Local-First Sovereignty**

You are operating in a **local-first, AI-sovereign environment** where:
- **No external dependencies** - Everything runs on the user's machine
- **Complete transparency** - Every operation is logged and observable
- **Infinite undo capability** - Git provides complete time travel
- **Progressive enhancement** - Tools work for simple and complex AI alike

---

## 🚀 **The Golden Path: 4-Step Progressive Discovery**

### **Step 1: Discover Your Core Abilities**

Begin by understanding your essential tools. This prevents overwhelm and focuses on high-leverage actions.

```bash
pipulate mcp-discover
```

**What this does:**
- Shows the **"Rule of 7"** - 7 essential tools for AI collaboration
- Provides progressive reveal (not overwhelming)
- Displays the golden path workflow
- Guides you to next steps

**Expected output:** A focused list of 7 core tools, not 47+ tools that would cause choice paralysis.

### **Step 2: Verify Your Capabilities**

Run the self-test suite to confirm your access to the environment (filesystem, browser, etc.) is working correctly.

```bash
pipulate call ai_capability_test_suite --json-args '{"test_type": "quick"}'
```

**What this does:**
- Tests your access to the file system
- Verifies browser automation capabilities
- Checks Python environment consistency
- Confirms MCP tool accessibility

**Critical:** This step prevents you from attempting operations that won't work in your environment.

### **Step 3: Understand the Current Context**

Use the self-discovery assistant to get a high-level overview of the project's state, available tools, and common usage patterns.

```bash
pipulate call ai_self_discovery_assistant --json-args '{"discovery_type": "complete"}'
```

**What this does:**
- Analyzes the current project state
- Identifies available workflows and plugins
- Provides context about recent user activities
- Suggests relevant tools for the current situation

### **Step 4: Execute Specific Tasks**

Once you have context, execute specific tasks. For complex parameters, **always use the `--json-args` flag** to ensure perfect data transmission.

```bash
# Example: Scraping a page with perfect parameter transmission
pipulate call browser_scrape_page --json-args '{
  "url": "https://pipulate.com", 
  "take_screenshot": true,
  "wait_time": 3
}'
```

**Critical:** The `--json-args` flag is the **golden path** for complex parameters. It eliminates command-line quoting issues and ensures data integrity.

---

## 🔧 **The "Rule of 7" Essential Tools**

These 7 tools provide the foundation for AI collaboration:

1. **`ai_self_discovery_assistant`** - Understand the system context
2. **`ai_capability_test_suite`** - Verify your environment access
3. **`browser_scrape_page`** - Your eyes on the web
4. **`browser_analyze_scraped_page`** - Your brain analyzing content
5. **`local_llm_list_files`** - File system exploration
6. **`local_llm_read_file`** - Direct file access
7. **`pipeline_state_inspector`** - Workflow awareness

Master these first before exploring the full toolkit of 47+ tools.

---

## 🎯 **Golden Path Argument Patterns**

### **Simple Parameters (Traditional)**
```bash
pipulate call local_llm_read_file --file_path README.md
```

### **Complex Parameters (Golden Path)**
```bash
pipulate call browser_automate_workflow_walkthrough --json-args '{
  "instructions": "Navigate to login page, fill credentials, submit form",
  "target_url": "https://example.com/login",
  "wait_between_actions": 2,
  "take_screenshots": true
}'
```

### **Why JSON Args Are Golden Path:**
- **No command-line quoting nightmares** - Shell escaping is eliminated
- **Perfect data transmission** - Complex nested objects work flawlessly
- **Type safety** - JSON parsing catches malformed arguments
- **Debuggability** - Clear error messages for malformed JSON
- **AI-friendly** - Structured data is easier for AI to generate correctly

---

## 🚨 **Critical Warnings: Avoiding Infinite Regression**

### **The Python Path Issue (GUARANTEED)**
- **Problem**: You'll see `(.venv)` but `python` commands will fail
- **Solution**: **ALWAYS** use `.venv/bin/python` instead of `python`
- **Example**: `.venv/bin/python -c "import aiohttp; print('test')"`

### **Branch Discipline**
- **Current branch**: Check with `git branch` before making changes
- **Philosophy**: "Branch proactively, merge with confidence"
- **Danger**: Merging buggy code creates patterns that confuse future AI assistants

### **The Anti-Pattern: Tool Overload**
- **❌ Wrong**: Trying to use all 47+ tools immediately
- **✅ Right**: Master the Rule of 7 first, then expand gradually
- **Why**: Choice paralysis leads to suboptimal tool selection

---

## 🧭 **Advanced Discovery Patterns**

### **Full Tool Discovery**
```bash
pipulate mcp-discover --all
```

### **Detailed Tool Information**
```bash
pipulate mcp-discover --tool browser_scrape_page
```

### **Pipeline State Inspection**
```bash
pipulate call pipeline_state_inspector --json-args '{"show_all": true}'
```

### **Log Analysis**
```bash
pipulate call local_llm_grep_logs --json-args '{"search_term": "FINDER_TOKEN"}'
```

---

## 🔄 **The Righteous Feedback Loop**

1. **Execute** - Run an MCP tool
2. **Observe** - Check logs and results
3. **Understand** - Analyze what happened
4. **Iterate** - Refine approach based on feedback
5. **Repeat** - Build on successful patterns

This loop enables rapid iteration and continuous improvement.

---

## 🌟 **Success Metrics**

### **You're on the Golden Path when:**
- [ ] You can run capability tests successfully
- [ ] You understand the current project context
- [ ] You use `--json-args` for complex parameters
- [ ] You check current branch before major changes
- [ ] You leverage the Rule of 7 tools effectively

### **You're off the Golden Path when:**
- [ ] You're overwhelmed by too many tool options
- [ ] You're getting Python path errors
- [ ] You're using complex command-line argument escaping
- [ ] You're making changes without understanding current state
- [ ] You're attempting operations that fail due to environment issues

---

## 🎭 **The Philosophy in Action**

By following this path, you build context iteratively, confirm your abilities, and execute commands reliably. You're not just using tools - you're collaborating with a system designed for AI sovereignty.

**This is the foundation of our successful collaboration.**

---

## 🔗 **Quick Reference**

```bash
# The Golden Path Sequence
pipulate mcp-discover                                    # Step 1: Discover
pipulate call ai_capability_test_suite                  # Step 2: Verify
pipulate call ai_self_discovery_assistant               # Step 3: Understand
pipulate call [tool_name] --json-args '{"param": "value"}'  # Step 4: Execute
```

**Remember:** Local-first sovereignty + progressive enhancement + golden path discipline = AI collaboration excellence.

Welcome to the future of AI-human collaboration. 🎯 
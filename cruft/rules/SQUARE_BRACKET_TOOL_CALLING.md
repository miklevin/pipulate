# 🎯 SQUARE BRACKET TOOL CALLING - SIMON SAYS PATTERN

## **🚀 Level 1: Ultra-Simple Simon Says Commands**

The system is designed to give **any LLM** (even the most basic local models) a **guaranteed win** through a simple "Simon Says" game:

### **🎮 The Simon Says Pattern:**
```
User: "Simon says [mcp]"
LLM Response: "[mcp]"
System: *Shows Rule of 7 tools*
```

### **Guaranteed Success Commands:**

1. **`[mcp]`** - Shows the 7 essential tools (Rule of 7)
2. **`[list]`** - Shows all 33 available tools  
3. **`[help]`** - Shows usage instructions
4. **`[test]`** - Runs a simple test tool call

## **🔧 How It Works (Deterministic Pattern):**

### **Step 1: Simon Says Trigger**
```bash
# User types: "Simon says [mcp]"
# LLM responds: "[mcp]"
```

### **Step 2: System Detects & Responds**
```python
# Detection in server.py (line 2987-2990)
if mcp_block.startswith('[') and mcp_block.endswith(']'):
    logger.debug("🔍 DEBUG: Detected bracket notation command")
    return await execute_bracket_notation_command(mcp_block, operation_id, start_time)
```

### **Step 3: Bracket Command Execution**
```python
# In execute_bracket_notation_command()
if mcp_block == "[mcp]":
    # Show Rule of 7 tools
    tools = get_rule_of_7_tools()
    return format_tool_list(tools)
```

## **🎯 The Rule of 7 Tools (Guaranteed Success Set):**

When an LLM says `[mcp]`, they get these **7 essential tools**:

1. **`ai_self_discovery_assistant`** - Self-discovery (meta-tool)
2. **`pipeline_state_inspector`** - System state inspection  
3. **`local_llm_read_file`** - File reading
4. **`local_llm_grep_logs`** - Log searching
5. **`browser_scrape_page`** - Web scraping
6. **`ui_flash_element`** - UI interaction
7. **`botify_ping`** - API connectivity test

## **🎮 The Simon Says Game Flow:**

### **Round 1: Confidence Building**
```
User: "Simon says [mcp]"
LLM: "[mcp]"  ← Simple copy, guaranteed success
System: *Shows 7 tools with usage instructions*
```

### **Round 2: First Tool Call**
```
User: "Now try [local_llm_read_file]"
LLM: "[local_llm_read_file]"  ← Another guaranteed success
System: *Executes tool call*
```

### **Round 3: Cascading Success**
```
User: "Great! Now try [browser_scrape_page]"
LLM: "[browser_scrape_page]"  ← Pattern established
System: *Executes web scraping*
```

## **🎯 Why This Works (Deterministic Design):**

### **1. Ultra-Low Friction:**
- **No complex syntax** - Just `[command]`
- **No parameters required** - Defaults handle everything
- **No environment setup** - Works in any terminal

### **2. Guaranteed Success:**
- **Copy-paste pattern** - LLM just repeats what you say
- **No thinking required** - Pure Simon Says
- **Immediate feedback** - Tool executes instantly

### **3. Progressive Reveal:**
- **Rule of 7** - Not overwhelming
- **Clear instructions** - Shows exactly how to call
- **Usage examples** - "💡 Usage: .venv/bin/python cli.py call <tool_name>"

## **🎮 The Humorous Determinism:**

The system is **"rigged"** for success through:

### **1. Pattern Recognition:**
```
User: "Simon says [mcp]"
LLM: "[mcp]"  ← Can't fail this!
```

### **2. Tool Discovery:**
```
System: "🎯 Rule of 7 - Essential Tools for Local LLMs (7):"
System: "💡 Usage: .venv/bin/python cli.py call <tool_name>"
```

### **3. Cascading Confidence:**
```
User: "Now try [local_llm_read_file]"
LLM: "[local_llm_read_file]"  ← Pattern established!
System: *Tool executes successfully*
```

## **🎯 The "Rigged" Success Chain:**

### **Phase 1: Simon Says (Guaranteed Win)**
- User: "Simon says [mcp]"
- LLM: "[mcp]" ← **100% success rate**

### **Phase 2: Tool Discovery (Confidence Building)**
- System shows 7 essential tools
- Clear usage instructions
- No overwhelming choices

### **Phase 3: First Tool Call (Pattern Learning)**
- User: "Try [local_llm_read_file]"
- LLM: "[local_llm_read_file]" ← **Learned the pattern**

### **Phase 4: Cascading Success (Chain Reaction)**
- Each successful tool call builds confidence
- Pattern becomes automatic
- LLM starts using tools independently

## **🔧 The Infrastructure-Proof Design:**

### **Environment Agnostic:**
- Works in **any terminal environment**
- **No specific setup required**
- **Sandboxing doesn't matter**
- **Tool calling rules can change**

### **Deterministic Success:**
- **Copy-paste pattern** - Can't fail
- **Immediate feedback** - Success visible
- **Progressive complexity** - Builds up gradually

## **🎮 The "Simon Says" Implementation:**

The system is designed so that **any LLM** can succeed by simply playing Simon Says:

```
User: "Simon says [mcp]"
LLM: "[mcp]"  ← This ALWAYS works
System: *Shows tools and instructions*
User: "Now try [local_llm_read_file]"
LLM: "[local_llm_read_file]"  ← Pattern learned!
System: *Executes tool successfully*
```

This creates a **cascading chain reaction** where each success builds confidence for the next tool call, turning even the most basic local LLM into a capable tool user through the power of **deterministic pattern matching**.

The beauty is that it's **"rigged"** for success - the LLM can't fail at Simon Says, and once they learn the pattern, they can start using tools independently!

## **🚀 Progressive Reveal Levels**

The bracket system is **Level 1** of 5 levels:

```python
# Level 1: [mcp-discover] - Ultra-simple bracket notation (YOU ARE HERE)
# Level 2: .venv/bin/python cli.py mcp-discover - Terminal proficiency  
# Level 3: python -c "from helpers.ai_tool_discovery_simple_parser import..."
# Level 4: <tool name="..."><params>{"key":"value"}</params></tool>
# Level 5: <tool name="..."><params><key>value</key></params></tool>
```

## **🎯 Available Commands**

### **Simple Commands (No Arguments)**
```python
SIMPLE_COMMANDS = {
    'mcp': 'List MCP categories (Rule of 7)',
    'mcp-discover': 'Start MCP discovery journey', 
    'discover': 'AI self-discovery assistant',
    'test': 'Test MCP capabilities',
    'pipeline': 'System state inspection',
    'read': 'Read file contents for AI analysis',
    'list': 'List files and directories for AI exploration',
    'search': 'Search logs with FINDER_TOKENs for debugging',
    'browser': 'Scrape web pages for analysis',
    'flash': 'Flash a UI element by ID to draw user attention',
    'tools': 'List available tools by category',
}
```

### **Pattern Commands (With Arguments)**
```python
COMMAND_PATTERNS = [
    {'pattern': r'list\s+(.+)', 'tool': 'local_llm_list_files'},
    {'pattern': r'search\s+(.+)', 'tool': 'local_llm_grep_logs'},
    {'pattern': r'read\s+(.+)', 'tool': 'local_llm_read_file'},
    {'pattern': r'browser\s+(.+)', 'tool': 'browser_scrape_page'},
    {'pattern': r'flash\s+(.+)', 'tool': 'ui_flash_element'},
]
```

## **🚀 Usage Examples**

### **Basic Commands**
```
[mcp] - List MCP categories
[pipeline] - System state inspection  
[discover] - AI self-discovery
[test] - Test MCP capabilities
```

### **Commands with Arguments**
```
[list static] - List files in static directory
[search FINDER_TOKEN] - Search logs for FINDER_TOKEN
[read server.py] - Read server.py file
[browser localhost:5001] - Scrape local server
[flash submit-button] - Flash UI element
```

## **🎯 Execution Flow**

### **1. Message Stream Processing**
```python
# The orchestrator notices bracket syntax in the message stream
# Extracts the complete [command arguments] chunk
# Ensures boundaries are complete and well-formed
```

### **2. Command Execution**
```python
# In execute_bracket_notation_command()
command = mcp_block.strip('[]')  # Remove brackets
result = await execute_simple_command(command)  # Execute via simple parser
```

### **3. Response Formatting**
```python
# Format response based on command type
if command in ['mcp', 'mcp-discover']:
    # Special discovery formatting
elif command == 'tools':
    # Tool listing formatting  
elif command == 'pipeline':
    # System state formatting
else:
    # Generic success formatting
```

## **🎯 Benefits for Low-Level LLMs**

### **1. Ultra-Low Friction**
- **Natural syntax** - `[command]` feels like natural text
- **No complex parsing** - Simple regex patterns
- **Immediate feedback** - Clear success/error responses

### **2. Progressive Learning**
- **Start simple** - Basic commands work immediately
- **Grow sophisticated** - Add arguments as needed
- **Build confidence** - Success breeds more complex usage

### **3. Error Handling**
```python
# Clear error messages with suggestions
return {
    'success': False,
    'error': f"Unknown command: {command}",
    'suggestion': "Try [mcp] for available commands"
}
```

## **🔧 Technical Implementation**

### **Detection Logic**
```python
# Simple boundary detection
if mcp_block.startswith('[') and mcp_block.endswith(']'):
    # Valid bracket notation detected
    return await execute_bracket_notation_command(mcp_block, ...)
```

### **Parsing Logic**
```python
# Two-stage parsing
1. Check SIMPLE_COMMANDS for exact matches
2. Check COMMAND_PATTERNS for regex matches
3. Return (tool_name, args_dict) or None
```

### **Execution Logic**
```python
# Direct MCP tool execution
tool_handler = MCP_TOOL_REGISTRY[tool_name]
result = await tool_handler(args)
```

## **Why This Works**

### **1. Orchestrator Pattern**
- **Centralized detection** - One place handles all bracket commands
- **Consistent behavior** - Same parsing and execution everywhere
- **Error isolation** - Failures don't break the chat system

### **2. Low-Friction Design**
- **Natural embedding** - `[command]` fits naturally in text
- **Immediate feedback** - Clear success/error responses
- **Progressive complexity** - Start simple, grow sophisticated

### **3. LLM-Friendly**
- **Simple patterns** - Easy for small models to generate
- **Clear boundaries** - `[` and `]` are unambiguous
- **Forgiving syntax** - Multiple ways to express the same command

## **🚀 The Magic**

This system enables **relatively low-level LLMs to do a lot** by:

1. **Eliminating complexity** - No need to understand complex tool calling
2. **Providing immediate feedback** - Success/failure is clear
3. **Building confidence** - Simple commands work, encouraging more complex usage
4. **Progressive reveal** - Each level builds on the previous

The **orchestrator** handles all the complexity, while the **LLM** just needs to generate simple `[command]` patterns. This creates a **low-friction path** to powerful tool calling capabilities.

**The first trick to bootstrap this is low-friction tool calling** - and the square-bracket system provides exactly that! 
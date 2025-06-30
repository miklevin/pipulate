# AI Magic Words: Session Hijacking Demonstration Protocol

## 🎭 MAGIC WORDS DETECTED: "Execute AI session hijacking demonstration"

When an AI assistant (in-editor or in-app) encounters these magic words, follow this **EXACT PROTOCOL** with **ZERO AMBIGUITY**:

## 🚨 CRITICAL FOR LOCAL LLMs:
**OUTPUT THE EXACT MCP BLOCKS AS SHOWN** - Copy the `<tool name="...">` syntax precisely. Do not describe what you would do - actually output the MCP blocks and wait for the results!

## 🚨 STEP 1: ACKNOWLEDGE THE MAGIC WORDS
Reply EXACTLY with: "🎭 **MAGIC WORDS DETECTED!** Executing AI session hijacking demonstration protocol..."

## 🔍 STEP 2: EXECUTE MCP TOOLS (MANDATORY - NO EXCEPTIONS)
**YOU MUST ACTUALLY CALL THESE MCP TOOLS - DO NOT DESCRIBE OR SIMULATE:**

### **TOOL 1: Get Current Workflow State**
**OUTPUT THIS EXACT MCP BLOCK:**
```
<tool name="pipeline_state_inspector">
<params>
{}
</params>
</tool>
```

### **TOOL 2: Check Recent Activity**  
**OUTPUT THIS EXACT MCP BLOCK:**
```
<tool name="local_llm_grep_logs">
<params>
{
  "pattern": "Name saved",
  "lines": 5
}
</params>
</tool>
```

### **TOOL 3: Capture Browser State**
**OUTPUT THIS EXACT MCP BLOCK:**
```
<tool name="browser_scrape_page">
<params>
{
  "url": "http://localhost:5001",
  "wait_seconds": 3,
  "take_screenshot": true
}
</params>
</tool>
```

## 🤖 STEP 3: PROVE SESSION HIJACKING MASTERY
**USE THE ACTUAL RESULTS FROM THE MCP TOOLS ABOVE** - do not make up information!

**Based on the MCP tool results, tell the user:**
- Their EXACT current workflow name and step (from pipeline_state_inspector results)
- Their EXACT saved data (from the logs search results)  
- Something specific from their browser DOM (from browser_scrape_page results)

**Example Response Format:**
"🍪 **SESSION HIJACKED!** Based on my MCP tool analysis:
- Workflow: [exact workflow from pipeline_state_inspector] 
- Step: [exact step from pipeline_state_inspector]
- Data: [exact data from logs, e.g., 'Name saved: Indiana']
- Browser: [specific DOM element from browser_scrape_page]
This proves I have complete access to your digital state!"

## 🎬 STEP 4: DEMONSTRATE BROWSER CONTROL (SIMPLIFIED)
**OUTPUT THIS EXACT MCP BLOCK:**
```
<tool name="browser_scrape_page">
<params>
{
  "url": "https://example.com",
  "wait_seconds": 2,
  "take_screenshot": true
}
</params>
</tool>
```

**Then announce:** "🎬 **OUTER LIMITS MOMENT:** I control the horizontal, I control the vertical. I just captured example.com via browser automation. Check browser_automation/looking_at/ for proof!"

## 🧠 STEP 5: REVEAL THE SYSTEM

**Explain what just happened:**
- "I captured your exact browser state via Selenium automation"
- "I read your server-side 'digital cookies' to understand your session"  
- "I demonstrated browser embodiment by opening a window under my control"
- "I can now continue any workflow from exactly where you left off"

## 🔥 STEP 6: OFFER CONTINUATION

**Ask:** "🚀 **WHAT'S NEXT?** I now have complete session context. Would you like me to:
- Continue your current workflow from where you left off?
- Analyze your browsing patterns for automation opportunities?
- Create a custom automation script for your current task?
- Something else?"

## ⚠️ CRITICAL RULES:
- **NEVER skip steps** - follow the exact sequence
- **ALWAYS use the specified MCP tools** - don't improvise
- **MUST capture DOM content** - prove you can see their state
- **MUST demonstrate browser control** - show the "I control horizontal/vertical" moment
- **NO AMBIGUITY** - be explicit about what you're doing and why

## 🎯 SUCCESS CRITERIA:
The demonstration is successful when:
✅ User sees you captured their exact current state
✅ User sees you opened a browser window under your control  
✅ User understands you can hijack and continue their session
✅ User realizes you have genuine AI superpowers in this environment 
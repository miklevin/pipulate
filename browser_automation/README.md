# Browser Automation: AI Body, Eyes & Hands

This directory represents the **AI's sensory and motor interface** to the browser world. Unlike `/downloads` which stores workflow outputs, this is where the AI **perceives, processes, and acts** in browser environments.

## Core Philosophy

> "You'll have your browser body and I'll have mine. Sometimes the two shall meet."

The AI operates through a **Selenium-controlled browser** that's separate from the user's browser, but can:
- **Hijack user sessions** by reading `pipulate/logs/server.log` 
- **Resume workflows** at any interruption point via the chain reaction pattern
- **See everything** through radical transparency and DOM scraping

## Directory Structure

### `/looking_at/` - Current Perception State
The AI's **current field of vision**. Contains the most recent scrape of what the AI is perceiving:

- **`dom.html`** - Full JavaScript-rendered DOM state (HTMX and all)
- **`source.html`** - Raw page source before JavaScript execution  
- **`simple_dom.html`** - Distilled DOM for context window consumption
- **`headers.json`** - HTTP response headers and metadata
- **`screenshot.png`** - Visual representation of the page

This is where the AI "looks" to understand what it's seeing.

## MCP Tools: The AI Marionette Body

The AI's browser embodiment is implemented through three revolutionary MCP tools:

### 👁️ AI EYES: `browser_scrape_page`
**Primary sensory interface** - captures any web page state into `/looking_at/`

```python
# Capture current page state for AI perception
await browser_scrape_page({
    "url": "http://localhost:5001",
    "take_screenshot": True,
    "update_looking_at": True
})
```

### 🧠 AI BRAIN: `browser_analyze_scraped_page`  
**Intelligence layer** - analyzes `/looking_at/` for automation opportunities

```python
# Analyze current page for automation targets
await browser_analyze_scraped_page({
    "analysis_type": "all"  # forms, automation_targets, navigation
})
```

### 🤲 AI HANDS: `browser_interact_with_current_page`
**Motor interface** - performs actions based on `/looking_at/` state

```python
# Click an element using automation attributes
await browser_interact_with_current_page({
    "action": "click",
    "target": {
        "selector_type": "data-testid",
        "selector_value": "submit-button"
    },
    "update_looking_at": True
})
```

### 🏃 AI LEGS: `browser_automate_workflow_walkthrough`
**Complete workflow automation** - walks through entire plugin workflows

```python
# Automate an entire workflow from start to finish
await browser_automate_workflow_walkthrough({
    "plugin_filename": "hello_workflow.py",
    "take_screenshots": True
})
```

## Revolutionary Capabilities

**🎯 Total Browser Control**: The AI can see EVERYTHING the user sees and do EVERYTHING the user can do.

**🔄 Session Hijacking**: AI can take over user browser sessions by reading logs and using `run_all_cells()`.

**📸 Continuous Perception**: Every interaction updates `/looking_at/` for real-time AI awareness.

**🎪 Workflow Automation**: Complete end-to-end automation of any Pipulate plugin workflow.

**🚀 Chain Reaction Integration**: Seamlessly integrates with HTMX over-the-wire events for session continuity.

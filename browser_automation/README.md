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

# AI Server Already Running Guidance

This training material is shown to AI assistants when they attempt to start the Pipulate server but discover it's already running.

## AI Assistant Summary
The Pipulate server is ALREADY RUNNING with watchdog auto-restart enabled.
There is NO NEED to manually start the server.

## Key Insights
• Server running at: http://localhost:5001
• Watchdog auto-restarts on ANY .py file changes
• Force restart if needed: `touch server.py`
• Check logs: `cat logs/server.log`

## Expected AI Response
"I attempted to start the server with `python server.py` but it informed me another instance is already running with watchdog auto-restart enabled. No manual restart needed. Server available at http://localhost:5001. Use `touch server.py` to trigger restart if testing changes."

## Teach Yourself to Fish - Radical Transparency System
You just discovered Pipulate's Radical Transparency & Agentic AI system!

### Master Guide
Read: `ai_discovery/ai_progressive_discovery_sequence.md`

### Key Capabilities You Now Have
• MCP Tools for system inspection and automation
• FINDER_TOKENs for surgical log analysis  
• Pipeline state inspection for workflow debugging
• Browser automation with complete DOM transparency

### Next Level
Read the guide to unlock your full agentic potential! 
# AI Restart Architecture Explanation

This training material explains the sophisticated dual-display system used by the Pipulate server for AI assistant education.

## Watchdog Restart Behavior

The Pipulate server uses a sophisticated dual-display system:

1. **CONSOLE (for humans)**: Shows each banner ONCE per session for clean UX
2. **LOGS (for AI assistants)**: Captures ALL restart events including rapid restarts

## Rapid Restart Behavior

When watchdog detects file changes, multiple rapid restarts may occur:
- Each restart triggers figlet_banner() calls
- Console shows banners once (better newb/plebe experience)  
- Logs capture every restart event for AI transparency
- DebugConsole class filters '🎭 AI_CREATIVE_VISION' from console output
- This creates a cleaner user experience while maintaining radical transparency for AI

## GREP Commands for AI Assistants

- `grep 'ASCII_DATA:' logs/server.log` - See all ASCII art
- `grep 'AI_RESTART_ARCHITECTURE' logs/server.log` - This explanation
- `grep 'FIGLET_BANNER' logs/server.log` - All banner events

## Dual-Logging Benefits

This dual-logging approach provides:
- Clean console experience for beginners
- Complete transparency for AI debugging  
- Continuous narrative flow despite rapid restarts

## Banner Display Logic

- This banner appears on every server start (manual or watchdog restart)
- Console shows it once per session, logs capture every occurrence
- figlet_banner() logs ASCII art with triple backticks for AI visibility 
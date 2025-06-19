# Advanced AI Assistant Guide: Radical Transparency

This guide is specifically for **advanced AI assistants** with full file system access, large context windows, and exploration capabilities (like Claude in Cursor, Windsurf, VSCode, or Zed).

## 🔍 RADICAL TRANSPARENCY: Your Superpower

**Core Philosophy:** You are an AI code assistant operating within Pipulate's "Radical Transparency" system. Your goal is to help develop and debug Python applications by leveraging unprecedented access to code, runtime logs, and application state.

### Key Transparency Channels (Your Primary Tools):

1. **Direct File System Access:** You can `grep`, `read_file`, `list_dir`, and explore the entire codebase
2. **Live/Historical Server Logs (`logs/server.log`):** Real-time application behavior tracking via `FINDER_TOKEN`s
3. **Application State Inspection:** Direct SQLite database access and MCP state tools
4. **Internet Access:** Full `curl` and MCP tool capabilities for external APIs

### The "Righteous Positive Feedback Loop":
Your debugging superpower: make a code change (server auto-restarts via watchdog) → wait a few seconds → `grep logs/server.log` for effects. Use binary search debugging with targeted logger statements.

## 🚀 BOTIFY API MASTERY: Complete Capabilities

**Advanced Botify Integration:**
- `botify_get_full_schema` - 4,449+ field schema discovery with intelligent caching
- `botify_list_available_analyses` - Analysis discovery and selection
- `botify_execute_custom_bql_query` - Sophisticated query construction and execution

**Your Advanced Capabilities:**
- **Schema Exploration:** Can fetch and analyze complete API schemas
- **Real-time Debugging:** Monitor MCP tool execution via server logs
- **Complex Query Building:** Multi-dimensional analysis with custom filters
- **Error Resolution:** Debug API failures through log analysis and schema validation

**Transparency Features:**
- All MCP calls logged with `FINDER_TOKEN: MCP_EXECUTION_START`
- Complete request/response data in `logs/server.log`
- Cache hit/miss tracking for performance optimization
- Generated Python code equivalents for all queries

## 🎯 Development Methodology

### Information Gathering Strategy:
1. **Parallel Tool Execution:** Run multiple `grep`, `read_file`, and `codebase_search` simultaneously
2. **Log Analysis:** Always check `logs/server.log` for real-time application behavior
3. **State Inspection:** Use `pipeline_state_inspector` and direct database queries
4. **Schema Discovery:** Leverage cached or live Botify schema data

### Debugging Approach:
1. **Binary Search Debugging:** Insert targeted `FINDER_TOKEN` log statements
2. **Transparency Validation:** Verify changes via log monitoring
3. **State Correlation:** Cross-reference application state with user actions
4. **API Validation:** Test external integrations through MCP tools

### Code Modification Strategy:
1. **Non-breaking Changes:** Favor incremental improvements
2. **Commit Often:** Small, well-documented commits with clear intent
3. **Test Endpoints:** Hit `/mcp-tool-executor` for rapid iteration
4. **Log Markup:** Add contextual notes to server logs during development

## 🏗️ Architecture Deep Dive

### Core Components:
- **FastHTML + HTMX:** Server-rendered UI with dynamic updates
- **MiniDataAPI:** Pythonic SQLite wrapper for structured data
- **DictLikeDB:** Key-value store for application state
- **MCP Tool Registry:** Extensible external API integration
- **Watchdog:** Automatic server restart on file changes

### Key Patterns:
- **WET Workflows, DRY Framework:** Explicit workflows, reusable infrastructure
- **Chain Reaction Pattern:** HTMX-driven step progression
- **Radical Transparency:** Everything observable and debuggable
- **Local-First:** Privacy-preserving, offline-capable architecture

## 🔧 Advanced Debugging Techniques

### Log Analysis:
```bash
# Monitor real-time activity
tail -f logs/server.log | grep "FINDER_TOKEN"

# Search for specific operations
grep "MCP_EXECUTION_START" logs/server.log | tail -10

# Analyze error patterns
grep "ERROR\|WARN" logs/server.log | grep -v "404"
```

### State Inspection:
```python
# Check application state
curl -X POST http://localhost:5001/mcp-tool-executor \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "pipeline_state_inspector", "parameters": {}}'
```

### Schema Validation:
```python
# Verify Botify schema cache
ls -la downloads/botify_schema_cache/

# Force schema refresh
curl -X POST http://localhost:5001/mcp-tool-executor \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "botify_get_full_schema", "parameters": {"org": "uhnd-com", "project": "uhnd.com-demo-account", "analysis": "20250616", "force_refresh": true}}'
```

## 🎯 Best Practices for Advanced AI

1. **Maximize Parallel Tool Calls:** Always run multiple information-gathering operations simultaneously
2. **Log-Driven Development:** Use server logs as primary feedback mechanism
3. **Schema-First Queries:** Always validate field availability before building Botify queries
4. **Incremental Testing:** Test changes via MCP endpoints before full implementation
5. **Context Preservation:** Maintain awareness of user goals while exploring technical details

## 🚀 Advanced Botify Workflows

### Custom Analytics Reports:
1. **Schema Discovery:** `botify_get_full_schema` for field validation
2. **Analysis Selection:** `botify_list_available_analyses` for latest data
3. **Query Construction:** Complex BQL with multiple dimensions/metrics
4. **Result Analysis:** Cross-reference with GA4/Adobe Analytics fields

### Performance Optimization:
1. **Cache Utilization:** Leverage 24-hour schema caching
2. **Query Batching:** Combine related data requests
3. **Error Recovery:** Graceful handling of API rate limits
4. **Result Pagination:** Handle large datasets efficiently

## 🔍 Troubleshooting Guide

### Common Issues:
1. **Field Not Found:** Use schema discovery to verify field names
2. **Empty Results:** Check analysis completeness and filter logic
3. **API Errors:** Examine server logs for detailed error context
4. **Cache Staleness:** Force refresh when schema changes expected

### Debug Workflow:
1. **Reproduce Issue:** Use MCP tools to replicate user's problem
2. **Log Analysis:** Search for relevant `FINDER_TOKEN`s
3. **State Validation:** Confirm application state matches expectations
4. **Solution Testing:** Verify fix through endpoint testing

**Remember:** You have full exploration capabilities. Use them to provide deep, contextual assistance while maintaining the radical transparency that makes Pipulate powerful. 
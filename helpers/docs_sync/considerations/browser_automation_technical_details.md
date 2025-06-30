# Browser Automation Technical Implementation Details

## Configuration & Setup

### Directory Rotation Configuration
- **Location**: `server.py` - `rotate_looking_at_directory()` function
- **Max Directories**: `MAX_ROLLED_LOOKING_AT_DIRS = 10` constant
- **Integration Points**: MCP tools automatically call rotation before operations
- **Error Handling**: Graceful fallback if rotation fails, logged with FINDER_TOKENs

### Performance Considerations
- **Disk Space**: Each directory can be 1-5MB depending on page complexity
- **I/O Impact**: Rotation is fast (just directory renames)
- **Cleanup**: Automatic deletion of old directories prevents unlimited growth

### File System Structure Details
Each rotated directory contains complete perception state:
- **`headers.json`** - HTTP metadata and automation context
- **`source.html`** - Raw page source before JavaScript
- **`dom.html`** - Full JavaScript-rendered DOM
- **`simple_dom.html`** - Cleaned DOM for AI context window
- **`beautiful_dom.html`** - AI-enhanced DOM with automation markers (optional)
- **`screenshot.png`** - Visual state capture
- **`automation_registry.json`** - Automation target analysis (if analyzed)
- **`automation_targets.py`** - Python code for automation (if generated)
- **`automation_summary.txt`** - Human-readable automation summary (if generated)

## Integration Implementation

### MCP Tool Function Signatures
```python
async def _browser_scrape_page(params: dict) -> dict:
    # params: {"url": str, "wait_seconds": int, "take_screenshot": bool, "update_looking_at": bool}
    
async def _browser_analyze_scraped_page(params: dict) -> dict:
    # params: {"analysis_type": str}  # "all", "forms", "targets"
    
async def _browser_automate_workflow_walkthrough(params: dict) -> dict:
    # params: {"workflow_description": str, "target_url": str, "steps": list}
```

### Server Integration Points
- **Rotation Function**: `server.py:rotate_looking_at_directory()`
- **MCP Registration**: `mcp_tools.py:register_all_mcp_tools()`
- **Logging Integration**: All operations use FINDER_TOKEN patterns
- **Error Recovery**: Graceful degradation when automation fails

## Troubleshooting & Debugging

### Common Issues
1. **Permission Errors**: Ensure write access to `browser_automation/` directory
2. **Disk Space**: Monitor disk usage if doing many automation sessions
3. **Import Errors**: Ensure `server.py` is importable for rotation function
4. **Selenium Issues**: Check Chrome/Chromium driver compatibility

### Debug Commands
```bash
# Check directory permissions
ls -la browser_automation/

# Monitor disk usage  
du -sh browser_automation/looking_at*

# Check rotation logs
grep "DIRECTORY_ROTATION\|DIRECTORY_ARCHIVE" logs/server.log

# Test rotation system
python browser_automation/test_directory_rotation.py
```

### Performance Monitoring
```bash
# Monitor MCP tool performance
grep "FINDER_TOKEN: MCP_CALL" logs/server.log | grep browser

# Check automation success rates
grep "FINDER_TOKEN: AUTOMATION_SUCCESS" logs/server.log

# Review capture statistics  
grep "FINDER_TOKEN: BROWSER_SCRAPE" logs/server.log
```

## Best Practices for Developers

### Code Integration Patterns
1. **Import Strategy**: Direct function imports from `mcp_tools` in workflows
2. **Error Handling**: Always wrap browser operations in try/catch
3. **Resource Management**: Ensure cleanup of browser instances
4. **Logging**: Use FINDER_TOKENs for all automation operations

### Testing & Validation
1. **Unit Tests**: Test directory rotation independently
2. **Integration Tests**: Verify MCP tool registration
3. **End-to-End Tests**: Full workflow automation validation
4. **Performance Tests**: Monitor disk usage and operation timing

### Security Considerations
1. **File Permissions**: Restrict access to perception directories
2. **Data Retention**: Automatic cleanup prevents indefinite storage
3. **Browser Security**: Isolated browser instances for automation
4. **Log Sanitization**: Ensure no sensitive data in automation logs

This technical detail is valuable for developers implementing or extending the browser automation system but was pruned from the master document to maintain focus on the transformational "ah-ha moment" for AI assistants. 
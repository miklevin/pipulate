# 🔄 Directory Rotation System Guide

## Overview
The browser automation directory rotation system preserves AI perception history across multiple browser automation sessions. Similar to log rotation, it maintains historical snapshots of what the AI "saw" during previous browser automation operations.

## How It Works

### Automatic Rotation
Before each new browser automation operation (`browser_scrape_page` or `browser_automate_workflow_walkthrough`), the system automatically:

1. **Archives Current State**: `looking_at/` → `looking_at-1/`
2. **Rotates History**: `looking_at-1/` → `looking_at-2/`, etc.
3. **Cleans Up Old States**: Directories beyond the limit (default: 10) are deleted
4. **Creates Fresh Directory**: New empty `looking_at/` for the current operation

### Directory Structure
```
browser_automation/
├── looking_at/          # Current perception state (latest)
├── looking_at-1/        # Previous state (1 operation ago)
├── looking_at-2/        # 2 operations ago
├── looking_at-3/        # 3 operations ago
└── ...                  # Up to MAX_ROLLED_LOOKING_AT_DIRS (default: 10)
```

### Configuration
- **Max Directories**: Controlled by `MAX_ROLLED_LOOKING_AT_DIRS` in `server.py` (default: 10)
- **Rotation Triggers**: 
  - `browser_scrape_page` MCP tool
  - `browser_automate_workflow_walkthrough` MCP tool

## Benefits for AI Assistants

### 1. **Perception History Access**
- Review what you were looking at in previous operations
- Compare current state with historical states
- Understand the progression of your automation sessions

### 2. **Better Decision Making**
- "I remember seeing a CAPTCHA in looking_at-2, let me check if it's still there"
- "The form structure changed since looking_at-1, I need to update my approach"
- "I successfully automated this workflow in looking_at-3, let me review what worked"

### 3. **Debugging & Learning**
- Analyze why automation failed by comparing before/after states
- Track changes in page structure over time
- Learn from successful automation patterns

## Usage Examples

### Quick Review Commands
```bash
# List all available perception states
ls -la browser_automation/looking_at*

# See what you're currently looking at
ls browser_automation/looking_at/

# See what you looked at previously
ls browser_automation/looking_at-1/

# Compare two states
diff browser_automation/looking_at-1/simple_dom.html browser_automation/looking_at-2/simple_dom.html
```

### Python Review Scripts
```bash
# Test the rotation system
cd pipulate
python browser_automation/test_directory_rotation.py

# Review perception history
python browser_automation/review_perception_history.py --list
python browser_automation/review_perception_history.py --recent 5
python browser_automation/review_perception_history.py --show 2
python browser_automation/review_perception_history.py --compare 1 3
```

### Manual Rotation (if needed)
```python
from server import rotate_looking_at_directory
from pathlib import Path

# Manually rotate directories
rotate_looking_at_directory(Path('browser_automation/looking_at'))
```

## File Contents in Each Directory

Each rotated directory contains the complete perception state from that automation session:

- **`headers.json`** - HTTP metadata and automation context
- **`source.html`** - Raw page source before JavaScript
- **`dom.html`** - Full JavaScript-rendered DOM
- **`simple_dom.html`** - Cleaned DOM for AI context window
- **`beautiful_dom.html`** - AI-enhanced DOM with automation markers
- **`screenshot.png`** - Visual state capture
- **`automation_registry.json`** - Automation target analysis
- **`automation_targets.py`** - Python code for automation
- **`automation_summary.txt`** - Human-readable automation summary

## AI Assistant Workflow Patterns

### Pattern 1: Comparative Analysis
```python
# Before taking action, check what changed
current_dom = read_file("browser_automation/looking_at/simple_dom.html")
previous_dom = read_file("browser_automation/looking_at-1/simple_dom.html")

if "CAPTCHA" in previous_dom and "CAPTCHA" not in current_dom:
    print("✅ CAPTCHA resolved since last check")
```

### Pattern 2: Automation Success Tracking
```python
# Review successful automation from history
success_metadata = json.load(open("browser_automation/looking_at-3/headers.json"))
if success_metadata.get("step") == "workflow_complete":
    print("📚 Found successful automation pattern in looking_at-3")
    # Analyze what worked
```

### Pattern 3: Progressive Debugging
```python
# Trace automation progression
for i in range(1, 6):  # Check last 5 states
    metadata_file = f"browser_automation/looking_at-{i}/headers.json"
    if os.path.exists(metadata_file):
        data = json.load(open(metadata_file))
        print(f"State {i}: {data.get('step', 'unknown')} at {data.get('url', 'unknown')}")
```

## Technical Details

### Rotation Function
- **Location**: `server.py` - `rotate_looking_at_directory()`
- **Parameters**: 
  - `looking_at_path`: Path to directory (default: `browser_automation/looking_at`)
  - `max_rolled_dirs`: Max historical directories (default: uses `MAX_ROLLED_LOOKING_AT_DIRS`)
- **Returns**: `bool` indicating success/failure

### Integration Points
- **MCP Tools**: Automatically called before browser operations
- **Logging**: All rotation operations logged with `FINDER_TOKEN` markers
- **Error Handling**: Graceful fallback if rotation fails

### Performance Considerations
- **Disk Space**: Each directory can be 1-5MB depending on page complexity
- **I/O Impact**: Rotation is fast (just directory renames)
- **Cleanup**: Automatic deletion of old directories prevents unlimited growth

## Troubleshooting

### Common Issues
1. **Permission Errors**: Ensure write access to `browser_automation/` directory
2. **Disk Space**: Monitor disk usage if doing many automation sessions
3. **Import Errors**: Ensure `server.py` is importable for rotation function

### Debug Commands
```bash
# Check directory permissions
ls -la browser_automation/

# Monitor disk usage
du -sh browser_automation/looking_at*

# Check rotation logs
grep "DIRECTORY_ROTATION\|DIRECTORY_ARCHIVE" logs/server.log
```

## Best Practices

### For AI Assistants
1. **Check History First**: Before assuming page state, review recent history
2. **Compare States**: Use diff tools to understand what changed
3. **Document Findings**: Note patterns you discover in the automation summaries
4. **Clean Reviews**: Periodically review and understand your automation history

### For Developers
1. **Monitor Disk Usage**: Watch for excessive disk consumption
2. **Adjust Retention**: Modify `MAX_ROLLED_LOOKING_AT_DIRS` based on needs
3. **Log Analysis**: Use `FINDER_TOKEN` logs to debug rotation issues
4. **Testing**: Run `test_directory_rotation.py` after system changes

---

**🎯 Key Insight**: This system transforms AI browser automation from "blind" exploration to "informed" decision-making based on historical context. Instead of starting fresh each time, AI assistants can now build on their previous understanding and avoid repeated mistakes. 
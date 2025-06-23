#!/bin/bash
# Safe consolidation workflow with built-in verification

set -e  # Exit on any error

echo "🛡️ SAFE CONSOLIDATION WORKFLOW"
echo "==============================="

# Function to create a checkpoint commit
create_checkpoint() {
    local message="$1"
    echo "📝 Creating checkpoint: $message"
    git add -A
    git commit -m "🔄 CHECKPOINT: $message" || echo "No changes to commit"
}

# Function to verify function consolidation
verify_consolidation() {
    local func_name="$1"
    echo "🔍 Verifying $func_name..."
    
    # Check exists in mcp_tools.py
    if ! grep -q "^async def $func_name" mcp_tools.py; then
        echo "❌ $func_name missing from mcp_tools.py"
        return 1
    fi
    
    # Check is registered
    if ! grep -q "register_mcp_tool.*$func_name" mcp_tools.py; then
        echo "❌ $func_name not registered in mcp_tools.py"
        return 1
    fi
    
    echo "✅ $func_name verified"
    return 0
}

# Function to test MCP tools still work
test_mcp_tools() {
    echo "🧪 Testing MCP tools functionality..."
    python3 -c "
from mcp_tools import register_all_mcp_tools, MCP_TOOL_REGISTRY
register_all_mcp_tools()
print(f'✅ {len(MCP_TOOL_REGISTRY)} tools registered successfully')
" || { echo "❌ MCP tools test failed"; return 1; }
}

# Function to measure line reduction
measure_progress() {
    local current_lines=$(wc -l < server.py)
    echo "📊 Current server.py: $current_lines lines"
    
    # Calculate reduction from baseline (8,225)
    local baseline=8225
    local reduction=$((baseline - current_lines))
    local percentage=$(( (reduction * 100) / baseline ))
    
    echo "📈 Total reduction: $reduction lines ($percentage%)"
}

# Safe consolidation steps for browser tools
consolidate_browser_tools() {
    echo "🌐 BROWSER TOOLS CONSOLIDATION"
    echo "=============================="
    
    # Step 1: Verify current state
    echo "Step 1: Pre-consolidation verification..."
    test_mcp_tools || { echo "❌ Current MCP tools broken"; return 1; }
    
    # Step 2: Create backup checkpoint
    create_checkpoint "Before browser tools consolidation"
    
    # Step 3: Add browser tools to mcp_tools.py (AI assistant does this)
    echo "Step 3: Ready for AI assistant to add browser tools to mcp_tools.py"
    echo "       Use: ADD functions → TEST → REMOVE from server.py"
    
    # Step 4: Instructions for verification after each addition
    echo "Step 4: After each addition, run:"
    echo "       ./test_mcp_tools_integration.sh"
    echo "       git add -A && git commit -m 'Added _function_name to mcp_tools.py'"
    
    echo "Step 5: After successful removal, run:"
    echo "       ./safe_consolidation_workflow.sh verify"
}

# Verification mode
verify_final_state() {
    echo "🔍 FINAL VERIFICATION"
    echo "===================="
    
    test_mcp_tools || { echo "❌ MCP tools broken"; return 1; }
    measure_progress
    
    # Check for remaining tools in server.py
    echo "🔍 Checking for remaining MCP tools in server.py..."
    if grep -q "^async def _.*(" server.py; then
        echo "📋 Remaining tools to consolidate:"
        grep "^async def _.*(" server.py | sed 's/async def //; s/(.*/:/'
    else
        echo "✅ No MCP tools remaining in server.py!"
    fi
    
    echo "✅ Final verification complete"
}

# Main workflow
case "${1:-help}" in
    "browser")
        consolidate_browser_tools
        ;;
    "verify")
        verify_final_state
        ;;
    "test")
        test_mcp_tools
        measure_progress
        ;;
    "help"|*)
        echo "Safe Consolidation Workflow"
        echo "=========================="
        echo "Usage:"
        echo "  $0 browser  # Start browser tools consolidation"
        echo "  $0 verify   # Verify final consolidation state"
        echo "  $0 test     # Test current MCP tools state"
        echo ""
        echo "Current status:"
        measure_progress
        ;;
esac

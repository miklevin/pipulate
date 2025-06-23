#!/bin/bash
# Simple verification before removing functions from server.py

verify_function_exists_in_both() {
    local func_name=$1
    echo "🔍 Verifying $func_name exists in both files..."
    
    # Check if function exists in server.py
    if ! grep -q "^async def $func_name" server.py; then
        echo "❌ $func_name NOT found in server.py"
        return 1
    fi
    
    # Check if function exists in mcp_tools.py  
    if ! grep -q "^async def $func_name" mcp_tools.py; then
        echo "❌ $func_name NOT found in mcp_tools.py"
        return 1
    fi
    
    # Check if function is registered in mcp_tools.py
    if ! grep -q "register_mcp_tool.*$func_name" mcp_tools.py; then
        echo "❌ $func_name NOT registered in mcp_tools.py"
        return 1
    fi
    
    echo "✅ $func_name verified in both files"
    return 0
}

# Usage: verify multiple functions
if [ $# -eq 0 ]; then
    echo "Usage: $0 <function_name1> [function_name2] ..."
    echo "Example: $0 _botify_ping _botify_list_projects"
    exit 1
fi

echo "🛡️ PRE-CONSOLIDATION VERIFICATION"
echo "=================================="

all_good=true
for func in "$@"; do
    if ! verify_function_exists_in_both "$func"; then
        all_good=false
    fi
done

echo "=================================="
if $all_good; then
    echo "🎉 ALL FUNCTIONS VERIFIED - Safe to proceed with removal from server.py"
    exit 0
else
    echo "⚠️ VERIFICATION FAILED - DO NOT remove functions yet!"
    exit 1
fi

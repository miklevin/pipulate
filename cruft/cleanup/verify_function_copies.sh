#!/bin/bash
# Extract function from server.py and mcp_tools.py for comparison
extract_function() {
    local file=$1
    local func_name=$2
    local start_line=$(grep -n "^async def $func_name" "$file" | cut -d: -f1)
    if [ -z "$start_line" ]; then
        echo "Function $func_name not found in $file"
        return 1
    fi
    
    # Find the end of the function (next function or end of file)
    local next_func=$(tail -n +$((start_line + 1)) "$file" | grep -n "^async def\|^def\|^class " | head -1 | cut -d: -f1)
    if [ -z "$next_func" ]; then
        # Function goes to end of file
        tail -n +$start_line "$file"
    else
        local end_line=$((start_line + next_func - 1))
        sed -n "${start_line},${end_line}p" "$file"
    fi
}

# Compare a function between server.py and mcp_tools.py
compare_function() {
    local func_name=$1
    echo "🔍 Comparing function: $func_name"
    
    extract_function "server.py" "$func_name" > /tmp/server_func.txt
    extract_function "mcp_tools.py" "$func_name" > /tmp/mcp_func.txt
    
    if diff -u /tmp/server_func.txt /tmp/mcp_func.txt; then
        echo "✅ $func_name: IDENTICAL"
        return 0
    else
        echo "❌ $func_name: DIFFERENCES FOUND!"
        return 1
    fi
}

# Usage: ./verify_function_copies.sh _function_name
if [ $# -eq 1 ]; then
    compare_function "$1"
else
    echo "Usage: $0 <function_name>"
    echo "Example: $0 _botify_get_full_schema"
fi

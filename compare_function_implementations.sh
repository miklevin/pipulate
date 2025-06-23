#!/bin/bash
# Compare exact function implementations between files

compare_implementations() {
    local func_name=$1
    echo "🔍 COMPARING IMPLEMENTATIONS: $func_name"
    echo "=========================================="
    
    # Extract function from server.py
    awk "/^async def $func_name\\(/,/^(async def |def |class |^$)/ { 
        if (/^(async def |def |class )/ && !/^async def $func_name\\(/) exit; 
        if (NF > 0 || prev_empty) print; 
        prev_empty = (NF == 0) 
    }" server.py > /tmp/server_${func_name}.py
    
    # Extract function from mcp_tools.py
    awk "/^async def $func_name\\(/,/^(async def |def |class |^$)/ { 
        if (/^(async def |def |class )/ && !/^async def $func_name\\(/) exit; 
        if (NF > 0 || prev_empty) print; 
        prev_empty = (NF == 0) 
    }" mcp_tools.py > /tmp/mcp_${func_name}.py
    
    # Count lines
    server_lines=$(wc -l < /tmp/server_${func_name}.py)
    mcp_lines=$(wc -l < /tmp/mcp_${func_name}.py)
    
    echo "📊 server.py: $server_lines lines"
    echo "📊 mcp_tools.py: $mcp_lines lines"
    
    # Compare with diff
    if diff -q /tmp/server_${func_name}.py /tmp/mcp_${func_name}.py > /dev/null; then
        echo "✅ IDENTICAL IMPLEMENTATIONS"
        rm /tmp/server_${func_name}.py /tmp/mcp_${func_name}.py
        return 0
    else
        echo "❌ DIFFERENCES FOUND:"
        echo "----------------------------------------"
        diff -u /tmp/server_${func_name}.py /tmp/mcp_${func_name}.py | head -50
        echo "----------------------------------------"
        echo "⚠️ Files saved for inspection:"
        echo "   server.py version: /tmp/server_${func_name}.py"
        echo "   mcp_tools.py version: /tmp/mcp_${func_name}.py"
        return 1
    fi
}

# Usage
if [ $# -eq 0 ]; then
    echo "Usage: $0 <function_name>"
    echo "Example: $0 _browser_scrape_page"
    exit 1
fi

compare_implementations "$1"

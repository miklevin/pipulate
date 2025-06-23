#!/bin/bash
# Git-based verification of MCP tool consolidation

set -e  # Exit on any error

# Function to extract function content from git history
extract_function_from_git() {
    local file=$1
    local func_name=$2
    local commit=$3
    
    # Get the function from a specific commit
    git show "$commit:$file" | awk "
    /^async def $func_name\(/ { found=1; print }
    found && /^async def [^$func_name]/ && !/^async def $func_name\(/ { exit }
    found && /^def [^_]/ { exit }
    found && /^class / { exit }
    found && found { print }
    " 2>/dev/null || echo "Function $func_name not found in $file at $commit"
}

# Function to verify consolidation between commits
verify_consolidation() {
    local func_name=$1
    local before_commit=$2
    local after_commit=${3:-HEAD}
    
    echo "🔍 Verifying consolidation of: $func_name"
    echo "📋 Before commit: $before_commit"
    echo "📋 After commit: $after_commit"
    echo
    
    # Extract function from server.py before consolidation
    echo "📄 Extracting from server.py (before)..."
    extract_function_from_git "server.py" "$func_name" "$before_commit" > /tmp/before_server.txt
    
    # Extract function from mcp_tools.py after consolidation
    echo "📄 Extracting from mcp_tools.py (after)..."
    extract_function_from_git "mcp_tools.py" "$func_name" "$after_commit" > /tmp/after_mcp.txt
    
    # Compare the functions
    echo "⚖️  Comparing function content..."
    if diff -u /tmp/before_server.txt /tmp/after_mcp.txt; then
        echo "✅ $func_name: IDENTICAL - No regressions detected!"
        return 0
    else
        echo "❌ $func_name: DIFFERENCES FOUND - Potential regression!"
        echo
        echo "🔍 Detailed diff:"
        diff -u /tmp/before_server.txt /tmp/after_mcp.txt || true
        return 1
    fi
}

# Function to verify ALL consolidations in a range
verify_all_consolidations() {
    local before_commit=$1
    local after_commit=${2:-HEAD}
    
    echo "🔍 COMPREHENSIVE CONSOLIDATION VERIFICATION"
    echo "============================================"
    echo "📋 Verifying all MCP tools between: $before_commit → $after_commit"
    echo
    
    # List of all functions we've consolidated
    local functions=(
        "_builtin_get_cat_fact"
        "_pipeline_state_inspector" 
        "_botify_ping"
        "_botify_list_projects"
        "_botify_simple_query"
        "_local_llm_read_file"
        "_local_llm_grep_logs"
        "_local_llm_list_files"
        "_local_llm_get_context"
        "_ui_flash_element"
        "_ui_list_elements"
        "_botify_get_full_schema"
        "_botify_list_available_analyses"
        "_botify_execute_custom_bql_query"
    )
    
    local success=0
    local total=${#functions[@]}
    
    for func in "${functions[@]}"; do
        echo "----------------------------------------"
        if verify_consolidation "$func" "$before_commit" "$after_commit"; then
            ((success++))
        fi
        echo
    done
    
    echo "============================================"
    echo "📊 VERIFICATION SUMMARY:"
    echo "✅ Verified: $success/$total functions"
    if [ $success -eq $total ]; then
        echo "🎉 ALL FUNCTIONS VERIFIED - No regressions detected!"
        return 0
    else
        echo "⚠️  REGRESSIONS DETECTED - Review differences above"
        return 1
    fi
}

# Usage examples
case "${1:-help}" in
    "single")
        if [ $# -lt 3 ]; then
            echo "Usage: $0 single <function_name> <before_commit> [after_commit]"
            exit 1
        fi
        verify_consolidation "$2" "$3" "$4"
        ;;
    "all")
        if [ $# -lt 2 ]; then
            echo "Usage: $0 all <before_commit> [after_commit]"
            exit 1
        fi
        verify_all_consolidations "$2" "$3"
        ;;
    "help"|*)
        echo "Git-based MCP Tool Consolidation Verifier"
        echo "========================================"
        echo "Usage:"
        echo "  $0 single <function_name> <before_commit> [after_commit]"
        echo "  $0 all <before_commit> [after_commit]"
        echo
        echo "Examples:"
        echo "  $0 single _botify_ping HEAD~1 HEAD"
        echo "  $0 all HEAD~5  # Verify all since 5 commits ago"
        echo "  $0 all 8a1b2c3d  # Verify all since specific commit"
        ;;
esac

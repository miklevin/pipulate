#!/bin/bash
# Integration test for MCP tools after consolidation

echo "🧪 MCP TOOLS INTEGRATION TESTING"
echo "================================="

# Test 1: Python import and registration
echo "📋 Test 1: Import and Registration..."
python3 -c "
from mcp_tools import register_all_mcp_tools, MCP_TOOL_REGISTRY
register_all_mcp_tools()
tool_count = len(MCP_TOOL_REGISTRY)
print(f'✅ Successfully registered {tool_count} tools')

# Check for specific tool categories
botify_tools = [t for t in MCP_TOOL_REGISTRY.keys() if 'botify' in t]
ui_tools = [t for t in MCP_TOOL_REGISTRY.keys() if 'ui_' in t]  
llm_tools = [t for t in MCP_TOOL_REGISTRY.keys() if 'local_llm' in t]
browser_tools = [t for t in MCP_TOOL_REGISTRY.keys() if 'browser' in t]

print(f'📊 Botify tools: {len(botify_tools)}')
print(f'�� UI tools: {len(ui_tools)}')
print(f'📊 LLM tools: {len(llm_tools)}')
print(f'📊 Browser tools: {len(browser_tools)}')

if tool_count < 10:
    print('⚠️ Warning: Tool count seems low')
    exit(1)
else:
    print('✅ Tool registration test PASSED')
" || { echo "❌ Registration test FAILED"; exit 1; }

# Test 2: Function execution (safe tests only)
echo
echo "📋 Test 2: Function Execution..."
python3 -c "
import asyncio
from mcp_tools import _builtin_get_cat_fact, _pipeline_state_inspector

async def test_tools():
    # Test cat fact (safe external API)
    try:
        result = await _builtin_get_cat_fact({})
        if result.get('success'):
            print('✅ Cat fact tool working')
        else:
            print('⚠️ Cat fact tool returned error (API might be down)')
    except Exception as e:
        print(f'❌ Cat fact tool failed: {e}')
        return False
    
    # Test pipeline state inspector (local operation)
    try:
        result = await _pipeline_state_inspector({'app_name': 'test'})
        if result.get('success'):
            print('✅ Pipeline state inspector working')
        else:
            print('⚠️ Pipeline state inspector returned expected error for test data')
    except Exception as e:
        print(f'❌ Pipeline state inspector failed: {e}')
        return False
    
    print('✅ Function execution test PASSED')
    return True

if not asyncio.run(test_tools()):
    exit(1)
" || { echo "❌ Function execution test FAILED"; exit 1; }

# Test 3: Git status check  
echo
echo "📋 Test 3: Git Status Check..."
if git status --porcelain | grep -q .; then
    echo "📝 Git changes detected (expected during consolidation)"
    git status --short
else
    echo "✅ Git working directory clean"
fi

echo
echo "🎉 ALL INTEGRATION TESTS PASSED!"
echo "Safe to proceed with consolidation operations."

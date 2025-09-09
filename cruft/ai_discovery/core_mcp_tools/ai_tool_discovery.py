#!/usr/bin/env python3
"""
AI Tool Discovery Script - Immediate MCP Tool Access Verification

This script helps AI assistants discover and test their MCP tool access
without any scaffolding or confusion.

Usage: python helpers/ai_tool_discovery.py
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_tools import (
    browser_scrape_page,
    browser_analyze_scraped_page,
    pipeline_state_inspector,
    local_llm_grep_logs,
    ui_flash_element,
    botify_get_full_schema,
    execute_automation_recipe
)

async def test_mcp_tools():
    """Test all available MCP tools to verify access."""
    
    print("🎯 AI MCP TOOLS DISCOVERY & VERIFICATION")
    print("=" * 50)
    
    # Test 1: Browser Scraping
    print("\n🌐 Testing browser_scrape_page...")
    try:
        result = await browser_scrape_page({
            'url': 'https://httpbin.org/get',
            'wait_seconds': 1,
            'take_screenshot': False
        })
        print("✅ browser_scrape_page: SUCCESS")
        print(f"   Captured: {result.get('url', 'Unknown URL')}")
    except Exception as e:
        print(f"❌ browser_scrape_page: FAILED - {e}")
    
    # Test 2: Pipeline State Inspection
    print("\n🔍 Testing pipeline_state_inspector...")
    try:
        result = await pipeline_state_inspector({})
        print("✅ pipeline_state_inspector: SUCCESS")
        print(f"   Active pipelines: {len(result.get('active_pipelines', []))}")
    except Exception as e:
        print(f"❌ pipeline_state_inspector: FAILED - {e}")
    
    # Test 3: Log Analysis
    print("\n📋 Testing local_llm_grep_logs...")
    try:
        result = await local_llm_grep_logs({
            'search_term': 'FINDER_TOKEN',
            'max_results': 5
        })
        print("✅ local_llm_grep_logs: SUCCESS")
        print(f"   Found {len(result.get('matches', []))} log entries")
    except Exception as e:
        print(f"❌ local_llm_grep_logs: FAILED - {e}")
    
    # Test 4: UI Element Flashing
    print("\n🎨 Testing ui_flash_element...")
    try:
        result = await ui_flash_element({
            'selector': 'body',
            'color': 'blue',
            'duration': 1
        })
        print("✅ ui_flash_element: SUCCESS")
    except Exception as e:
        print(f"❌ ui_flash_element: FAILED - {e}")
    
    # Test 5: Automation Recipe Execution
    print("\n🤖 Testing execute_automation_recipe...")
    try:
        result = await execute_automation_recipe({})
        print("✅ execute_automation_recipe: SUCCESS")
        print(f"   Available recipes: {len(result.get('available_recipes', []))}")
    except Exception as e:
        print(f"❌ execute_automation_recipe: FAILED - {e}")
    
    print("\n" + "=" * 50)
    print("🎭 TOOL ACCESS VERIFICATION COMPLETE")
    print("\n📚 Next Steps:")
    print("1. Read: helpers/docs_sync/considerations/AI_MCP_TOOLS_DISCOVERY_GUIDE.md")
    print("2. Use tools directly: await browser_scrape_page({'url': 'https://example.com'})")
    print("3. No scaffolding needed - direct function calls work!")

def list_available_tools():
    """List all available MCP tools."""
    
    print("📋 AVAILABLE MCP TOOLS")
    print("=" * 30)
    
    tools = [
        ("🌐 Browser Tools", [
            "browser_scrape_page",
            "browser_analyze_scraped_page", 
            "browser_automate_workflow_walkthrough",
            "browser_interact_with_current_page",
            "execute_automation_recipe"
        ]),
        ("🔍 Analysis Tools", [
            "pipeline_state_inspector",
            "local_llm_grep_logs",
            "local_llm_read_file",
            "local_llm_list_files"
        ]),
        ("📊 Botify Tools", [
            "botify_get_full_schema",
            "botify_list_available_analyses",
            "botify_execute_custom_bql_query"
        ]),
        ("🎨 UI Tools", [
            "ui_flash_element",
            "ui_list_elements"
        ])
    ]
    
    for category, tool_list in tools:
        print(f"\n{category}:")
        for tool in tool_list:
            print(f"  - {tool}")
    
    print(f"\nTotal: {sum(len(tools) for _, tools in tools)} MCP tools available")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_available_tools()
    else:
        asyncio.run(test_mcp_tools()) 
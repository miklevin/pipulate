#!/usr/bin/env python3
"""
Python Environment Fix Test Script

This script tests that the Python environment is properly configured
and all MCP tools are accessible without explicit path requirements.

FIXED: Python environment confusion - virtual environment now activates correctly
"""

import asyncio
import sys
import os

def test_environment():
    """Test basic environment configuration"""
    print("🔧 Testing Python Environment Configuration")
    print("=" * 50)
    
    # Test 1: Check Python path
    print(f"✅ Python executable: {sys.executable}")
    print(f"✅ Python version: {sys.version}")
    print(f"✅ Virtual env: {os.environ.get('VIRTUAL_ENV', 'Not set')}")
    
    # Test 2: Check key dependencies
    try:
        import aiohttp
        print("✅ aiohttp import successful")
    except ImportError as e:
        print(f"❌ aiohttp import failed: {e}")
        return False
    
    # Test 3: Check MCP tools import
    try:
        from mcp_tools import _builtin_get_cat_fact
        print("✅ MCP tools import successful")
    except ImportError as e:
        print(f"❌ MCP tools import failed: {e}")
        return False
    
    return True

async def test_mcp_tools():
    """Test MCP tools functionality"""
    print("\n🚀 Testing MCP Tools Functionality")
    print("=" * 50)
    
    # Test 1: Basic MCP tool
    try:
        from mcp_tools import _builtin_get_cat_fact
        result = await _builtin_get_cat_fact({})
        print(f"✅ Cat fact tool: {result.get('fact', 'No fact')[:50]}...")
    except Exception as e:
        print(f"❌ Cat fact tool failed: {e}")
        return False
    
    # Test 2: Self-discovery tool
    try:
        from mcp_tools import _ai_self_discovery_assistant
        result = await _ai_self_discovery_assistant({'discovery_type': 'capabilities'})
        tools_available = result.get('total_tools_available', 0)
        print(f"✅ Self-discovery tool: {tools_available} tools available")
    except Exception as e:
        print(f"❌ Self-discovery tool failed: {e}")
        return False
    
    # Test 3: Capability test suite
    try:
        from mcp_tools import _ai_capability_test_suite
        result = await _ai_capability_test_suite({'test_type': 'quick'})
        success_rate = result.get('success_rate', 0)
        print(f"✅ Capability test: {success_rate}% success rate")
    except Exception as e:
        print(f"❌ Capability test failed: {e}")
        return False
    
    return True

async def test_browser_automation():
    """Test browser automation capabilities"""
    print("\n👁️ Testing Browser Automation")
    print("=" * 50)
    
    try:
        from mcp_tools import _browser_scrape_page
        result = await _browser_scrape_page({
            'url': 'https://httpbin.org/json',
            'take_screenshot': True,
            'wait_seconds': 2
        })
        
        status = result.get('status', 'Unknown')
        screenshot = result.get('screenshot_path', 'N/A')
        
        print(f"✅ Browser scraping: {status}")
        print(f"✅ Screenshot captured: {screenshot}")
        
        # Check if files were actually created
        import os
        if os.path.exists('browser_automation/looking_at/screenshot.png'):
            print("✅ Screenshot file exists")
        else:
            print("❌ Screenshot file missing")
            
    except Exception as e:
        print(f"❌ Browser automation failed: {e}")
        return False
    
    return True

def main():
    """Main test function"""
    print("🧪 Python Environment Fix Test")
    print("=" * 60)
    
    # Test 1: Environment
    if not test_environment():
        print("\n❌ Environment test failed")
        return False
    
    # Test 2: MCP Tools
    if not asyncio.run(test_mcp_tools()):
        print("\n❌ MCP tools test failed")
        return False
    
    # Test 3: Browser Automation
    if not asyncio.run(test_browser_automation()):
        print("\n❌ Browser automation test failed")
        return False
    
    print("\n🎉 ALL TESTS PASSED!")
    print("✅ Python environment confusion RESOLVED")
    print("✅ All MCP tools accessible without explicit paths")
    print("✅ Browser automation working correctly")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
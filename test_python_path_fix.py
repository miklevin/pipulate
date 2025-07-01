#!/usr/bin/env python3
"""
Python Path Fix Verification Script

This script helps AI assistants verify they're using the correct Python path
and that all dependencies are available in the virtual environment.

Usage:
    .venv/bin/python test_python_path_fix.py
"""

import sys
import importlib

def test_python_path():
    """Test that we're using the correct Python executable."""
    print("🔧 PYTHON PATH VERIFICATION")
    print("=" * 50)
    
    expected_path = "/home/mike/repos/pipulate/.venv/bin/python"
    actual_path = sys.executable
    
    print(f"Expected: {expected_path}")
    print(f"Actual:   {actual_path}")
    
    if expected_path in actual_path:
        print("✅ Using correct Python path!")
        return True
    else:
        print("❌ Using wrong Python path!")
        print("💡 Solution: Use .venv/bin/python instead of python")
        return False

def test_dependencies():
    """Test that all required dependencies are available."""
    print("\n📦 DEPENDENCY VERIFICATION")
    print("=" * 50)
    
    required_packages = [
        'aiohttp',      # Essential for MCP tools
        'uvicorn',      # Web server
        'selenium',     # Browser automation
        'requests',     # HTTP requests
        'sqlite3',      # Built-in database
        'asyncio',      # Built-in async support
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("💡 Solution: Use .venv/bin/python to access virtual environment packages")
        return False
    else:
        print("\n✅ All dependencies available!")
        return True

def test_mcp_tools():
    """Test that MCP tools can be imported."""
    print("\n🛠️ MCP TOOLS VERIFICATION")
    print("=" * 50)
    
    try:
        from mcp_tools import ai_self_discovery_assistant, ai_capability_test_suite
        print("✅ MCP tools import successful!")
        
        # Test a simple async function
        import asyncio
        
        async def test_discovery():
            try:
                result = await ai_self_discovery_assistant({'discovery_type': 'capabilities'})
                tools_available = result.get('total_tools_available', 0)
                print(f"✅ MCP tools working! Available: {tools_available}")
                return True
            except Exception as e:
                print(f"❌ MCP tools test failed: {e}")
                return False
        
        success = asyncio.run(test_discovery())
        return success
        
    except ImportError as e:
        print(f"❌ MCP tools import failed: {e}")
        print("💡 Solution: Use .venv/bin/python to access virtual environment packages")
        return False

def main():
    """Run all verification tests."""
    print("🚀 PYTHON PATH FIX VERIFICATION")
    print("=" * 60)
    print("This script verifies that you're using the correct Python path")
    print("and that all dependencies are available.\n")
    
    tests = [
        ("Python Path", test_python_path),
        ("Dependencies", test_dependencies),
        ("MCP Tools", test_mcp_tools),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:15} {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ You're using the correct Python path")
        print("✅ All dependencies are available")
        print("✅ MCP tools are working")
        print("\n🚀 Ready for AI superpowers discovery!")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("💡 Solution: Always use .venv/bin/python instead of python")
        print("💡 Example: .venv/bin/python test_python_path_fix.py")
    
    print("=" * 60)

if __name__ == "__main__":
    main() 
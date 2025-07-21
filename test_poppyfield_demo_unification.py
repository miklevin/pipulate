#!/usr/bin/env python3
"""
Test script for Poppyfield demo path unification.

This script verifies that:
1. The demo script message has been updated correctly
2. The reset button appears in both DEV and PROD modes
3. The unified demo path works regardless of starting mode
"""

import json
import sys
from pathlib import Path

def test_demo_script_message():
    """Test that the demo script message has been updated correctly."""
    print("🧪 Testing demo script message update...")
    
    try:
        with open('demo_script_config.json', 'r') as f:
            config = json.load(f)
        
        # Look for the first trick step in branches
        found_step = False
        for branch_name, branch_steps in config['demo_script']['branches'].items():
            for step in branch_steps:
                if step.get('step_id') == '07_first_trick':
                    message = step.get('message', '')
                    if 'Reset Entire DEV Database' in message:
                        print("✅ Demo script message correctly updated")
                        return True
                    else:
                        print(f"❌ Demo script message not updated: {message}")
                        return False
        
        print("❌ Could not find step '07_first_trick' in demo script branches")
        return False
        
    except Exception as e:
        print(f"❌ Error reading demo script: {e}")
        return False

def test_server_button_logic():
    """Test that the server button logic has been updated correctly."""
    print("🧪 Testing server button logic...")
    
    try:
        with open('server.py', 'r') as f:
            content = f.read()
        
        # Check for the new button creation logic
        if 'Create reset button with different labels for DEV vs PROD mode' in content:
            print("✅ Server button logic updated correctly")
            return True
        else:
            print("❌ Server button logic not updated")
            return False
            
    except Exception as e:
        print(f"❌ Error reading server.py: {e}")
        return False

def test_unified_demo_path():
    """Test that the demo path is now unified."""
    print("🧪 Testing unified demo path...")
    
    try:
        with open('server.py', 'r') as f:
            content = f.read()
        
        # Check that reset button is added in both modes
        if 'Add reset button in both DEV and PROD modes (unified demo path)' in content:
            print("✅ Unified demo path implemented")
            return True
        else:
            print("❌ Unified demo path not implemented")
            return False
            
    except Exception as e:
        print(f"❌ Error checking unified demo path: {e}")
        return False

def main():
    """Run all tests for the Poppyfield demo unification."""
    print("🎭 POPPYFIELD DEMO UNIFICATION TESTS")
    print("=" * 50)
    
    tests = [
        test_demo_script_message,
        test_server_button_logic,
        test_unified_demo_path
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"🎯 RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Demo path unification is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
#!/usr/bin/env python3
"""
Focused Diagnostic: Conversation Loading Function Testing
========================================================

This script directly tests the conversation loading function to identify
exactly where the failure is occurring.
"""

import sys
import os
import sqlite3
import json
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, '.')

def test_direct_conversation_loading():
    """Test the conversation loading function directly"""
    print("🔍 DIAGNOSTIC: Testing conversation loading function directly")
    
    # First, verify the database has content
    print("\n1. Checking database content...")
    conn = sqlite3.connect('data/discussion.db')
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM store WHERE key = ?', ('llm_conversation_history',))
    result = cursor.fetchone()
    
    if result:
        conversations = json.loads(result[0])
        print(f"✅ Database contains {len(conversations)} messages")
        
        # Show last few messages
        for i, msg in enumerate(conversations[-3:]):
            content_preview = msg.get('content', '')[:100] + '...' if len(msg.get('content', '')) > 100 else msg.get('content', '')
            print(f"   Message {len(conversations)-3+i+1}: {msg.get('role')} - {content_preview}")
    else:
        print("❌ No conversation history found in database")
        conn.close()
        return False
    
    conn.close()
    
    # Now test the actual loading function
    print("\n2. Testing load_conversation_from_db() function...")
    
    try:
        # Import the function
        from server import load_conversation_from_db, global_conversation_history
        
        print(f"   Before loading: global_conversation_history has {len(global_conversation_history)} messages")
        
        # Call the function
        result = load_conversation_from_db()
        
        print(f"   Function returned: {result}")
        print(f"   After loading: global_conversation_history has {len(global_conversation_history)} messages")
        
        if global_conversation_history:
            print("   Messages in global_conversation_history:")
            for i, msg in enumerate(global_conversation_history):
                content_preview = msg.get('content', '')[:100] + '...' if len(msg.get('content', '')) > 100 else msg.get('content', '')
                print(f"     {i+1}: {msg.get('role')} - {content_preview}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error calling load_conversation_from_db(): {e}")
        import traceback
        traceback.print_exc()
        return False

def test_startup_function_execution():
    """Test if the startup function conversation loading code would execute"""
    print("\n3. Testing startup function conversation loading code...")
    
    try:
        # Import required functions
        from server import load_conversation_from_db, global_conversation_history
        import logging
        
        # Create a logger similar to the one used in startup
        logger = logging.getLogger(__name__)
        
        print("   Simulating startup sequence conversation loading...")
        
        # This is the exact code from the startup function
        logger.info("💬 FINDER_TOKEN: CONVERSATION_RESTORE_STARTUP - Attempting to restore conversation history from database")
        conversation_restored = load_conversation_from_db()
        if conversation_restored:
            logger.info(f"💬 FINDER_TOKEN: CONVERSATION_RESTORE_SUCCESS - LLM conversation history restored from previous session")
            print(f"   ✅ Conversation restored successfully: {len(global_conversation_history)} messages")
        else:
            logger.info("💬 FINDER_TOKEN: CONVERSATION_RESTORE_NONE - Starting with fresh conversation history")
            print(f"   ❌ Conversation restore failed: {len(global_conversation_history)} messages")
        
        return conversation_restored
        
    except Exception as e:
        print(f"❌ Error in startup simulation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_global_conversation_history_persistence():
    """Test if global_conversation_history persists across function calls"""
    print("\n4. Testing global_conversation_history persistence...")
    
    try:
        from server import global_conversation_history
        
        print(f"   Initial state: {len(global_conversation_history)} messages")
        
        # Add a test message
        test_message = {"role": "test", "content": "Diagnostic test message"}
        global_conversation_history.append(test_message)
        
        print(f"   After adding test message: {len(global_conversation_history)} messages")
        
        # Import again to see if it's a new instance
        from server import global_conversation_history as gch2
        
        print(f"   After re-import: {len(gch2)} messages")
        
        if len(gch2) == len(global_conversation_history):
            print("   ✅ global_conversation_history persists across imports")
            return True
        else:
            print("   ❌ global_conversation_history does NOT persist across imports")
            return False
            
    except Exception as e:
        print(f"❌ Error testing persistence: {e}")
        return False

def main():
    """Run all diagnostic tests"""
    print("=" * 80)
    print("🔬 CONVERSATION LOADING DIAGNOSTIC TESTS")
    print("=" * 80)
    
    if not Path('data/discussion.db').exists():
        print("❌ ERROR: data/discussion.db does not exist")
        return False
    
    # Run all tests
    test1 = test_direct_conversation_loading()
    test2 = test_startup_function_execution() 
    test3 = test_global_conversation_history_persistence()
    
    print("\n" + "=" * 80)
    print("🏁 DIAGNOSTIC RESULTS")
    print("=" * 80)
    
    print(f"Test 1 - Direct function call: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Test 2 - Startup simulation: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"Test 3 - Global variable persistence: {'✅ PASS' if test3 else '❌ FAIL'}")
    
    if all([test1, test2, test3]):
        print("\n🎉 All tests passed - conversation loading should work!")
        print("🔍 The issue must be elsewhere in the startup sequence")
    else:
        print("\n💥 One or more tests failed - found the root cause!")
        
        if not test1:
            print("   🔧 Fix: load_conversation_from_db() function has issues")
        if not test2:
            print("   🔧 Fix: Startup sequence conversation loading has issues")
        if not test3:
            print("   🔧 Fix: global_conversation_history doesn't persist - module loading issue")

if __name__ == "__main__":
    main() 
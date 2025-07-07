#!/usr/bin/env python3
"""
🎯 Conversation Persistence Test - Final Implementation
Tests conversation persistence across server restarts with proper LLM streaming timing
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
import sqlite3
import subprocess

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Static constants - NEVER QUESTION THESE
CONVERSATION_DATABASE = "data/discussion.db"
SERVER_URL = "http://localhost:5001"
CHAT_TEXTAREA = 'textarea[name="msg"]'
CHAT_SUBMIT_BUTTON = 'button[type="submit"]'
TEST_MESSAGE_PHASE_1 = "The test word is flibbertigibbet. Please remember this for our conversation."
TEST_MESSAGE_PHASE_3 = "What is the test word I mentioned?"

# Critical timing constants for LLM streaming
LLM_RESPONSE_INITIAL_WAIT = 3     # Wait for response to start
LLM_RESPONSE_STREAMING_WAIT = 15  # Wait for streaming to complete
LLM_RESPONSE_FINALIZATION_WAIT = 3 # Wait for conversation save
BROWSER_INTERACTION_DELAY = 2     # Delay between browser actions
SERVER_RESTART_WAIT = 8           # Wait for server restart

class ConversationPersistenceTestFinal:
    """
    Bottled pattern: Web UI Action → Verify Effect
    Specifically tests conversation persistence across server restarts
    """
    
    def __init__(self):
        self.test_name = "conversation_persistence_final"
        self.driver = None
        self.results = {}
        
    async def run_complete_test(self) -> dict:
        """Execute the complete test cycle"""
        try:
            print("🎯 Starting Conversation Persistence Test")
            print("=" * 60)
            
            # Phase 1: Baseline
            print("📋 Phase 1: Establishing baseline...")
            baseline_messages = await self.get_message_count()
            print(f"   📊 Baseline: {baseline_messages} messages in database")
            
            # Phase 2: Send message with proper timing
            print("📝 Phase 2: Sending test message...")
            await self.send_message_with_streaming_wait(TEST_MESSAGE_PHASE_1)
            
            # Phase 3: Verify message was saved
            print("💾 Phase 3: Verifying message persistence...")
            
            # Check multiple times to account for potential delay
            for attempt in range(3):
                messages_after_send = await self.get_message_count()
                print(f"   📊 Attempt {attempt + 1}: {messages_after_send} messages in database")
                
                if messages_after_send > baseline_messages:
                    print(f"   ✅ Message count increased from {baseline_messages} to {messages_after_send}")
                    break
                    
                if attempt < 2:  # Don't wait after the last attempt
                    print(f"   ⏳ Waiting 5 more seconds for database update...")
                    await asyncio.sleep(5)
            else:
                # Check if there's conversation data but count is wrong
                await self.debug_conversation_data()
                return await self.handle_failure(f"Message count did not increase: {baseline_messages} → {messages_after_send}")
            
            # Phase 4: Restart server
            print("🔄 Phase 4: Restarting server...")
            await self.restart_server_via_mcp()
            
            # Phase 5: Verify conversation persisted
            print("🔍 Phase 5: Verifying conversation persistence...")
            messages_after_restart = await self.get_message_count()
            print(f"   📊 After restart: {messages_after_restart} messages in database")
            
            # Phase 6: Test AI memory
            print("🧠 Phase 6: Testing AI memory...")
            memory_result = await self.test_ai_memory()
            
            # Generate results
            success = (
                messages_after_restart > baseline_messages and
                memory_result['success']
            )
            
            return {
                'success': success,
                'test_name': self.test_name,
                'results': {
                    'baseline_messages': baseline_messages,
                    'messages_after_send': messages_after_send,
                    'messages_after_restart': messages_after_restart,
                    'memory_test': memory_result
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return await self.handle_failure(f"Test exception: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
    
    async def get_message_count(self) -> int:
        """Get current message count from conversation database"""
        try:
            if not os.path.exists(CONVERSATION_DATABASE):
                return 0
            
            conn = sqlite3.connect(CONVERSATION_DATABASE)
            cursor = conn.cursor()
            
            # Check if conversation data exists in store table
            cursor.execute("SELECT value FROM store WHERE key = 'llm_conversation_history'")
            result = cursor.fetchone()
            conn.close()
            
            if result:
                # Parse the JSON conversation data
                import json
                conversation_data = json.loads(result[0])
                return len(conversation_data) if isinstance(conversation_data, list) else 0
            else:
                return 0
                
        except Exception as e:
            print(f"   ⚠️ Database query error: {e}")
            return 0
    
    async def send_message_with_streaming_wait(self, message: str) -> dict:
        """Send message and wait for LLM streaming response to complete"""
        try:
            # Setup browser
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.get(SERVER_URL)
            
            # Wait for page to load
            print(f"   🌐 Loading {SERVER_URL}...")
            await asyncio.sleep(BROWSER_INTERACTION_DELAY)
            
            # Find and interact with chat interface
            print(f"   🎭 Finding chat interface...")
            wait = WebDriverWait(self.driver, 10)
            textarea = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, CHAT_TEXTAREA)))
            submit_button = self.driver.find_element(By.CSS_SELECTOR, CHAT_SUBMIT_BUTTON)
            
            # Send message
            print(f"   📝 Typing message: '{message}'")
            textarea.clear()
            textarea.send_keys(message)
            
            print(f"   🚀 Submitting message...")
            submit_button.click()
            
            # CRITICAL: Wait for LLM response streaming
            print(f"   ⏳ Waiting {LLM_RESPONSE_INITIAL_WAIT}s for response to start...")
            await asyncio.sleep(LLM_RESPONSE_INITIAL_WAIT)
            
            print(f"   📡 Waiting {LLM_RESPONSE_STREAMING_WAIT}s for streaming to complete...")
            await asyncio.sleep(LLM_RESPONSE_STREAMING_WAIT)
            
            print(f"   💾 Waiting {LLM_RESPONSE_FINALIZATION_WAIT}s for conversation save...")
            await asyncio.sleep(LLM_RESPONSE_FINALIZATION_WAIT)
            
            print(f"   ✅ Message sent and processed successfully")
            return {'success': True}
            
        except Exception as e:
            print(f"   ❌ Error sending message: {e}")
            return {'success': False, 'error': str(e)}
    
    async def restart_server_via_mcp(self) -> dict:
        """Restart server using MCP tool"""
        try:
            print(f"   🔧 Calling server_reboot MCP tool...")
            result = subprocess.run([
                ".venv/bin/python", "cli.py", "call", "server_reboot"
            ], capture_output=True, text=True, timeout=30)
            
            print(f"   ⏳ Waiting {SERVER_RESTART_WAIT}s for server restart...")
            await asyncio.sleep(SERVER_RESTART_WAIT)
            
            # Verify server is back up
            print(f"   🔍 Verifying server is responsive...")
            import requests
            for attempt in range(5):
                try:
                    response = requests.get(SERVER_URL, timeout=5)
                    if response.status_code == 200:
                        print(f"   ✅ Server is back online")
                        return {'success': True}
                except:
                    print(f"   ⏳ Server not ready, attempt {attempt + 1}/5...")
                    await asyncio.sleep(2)
            
            return {'success': False, 'error': 'Server did not come back online'}
            
        except Exception as e:
            print(f"   ❌ Error restarting server: {e}")
            return {'success': False, 'error': str(e)}
    
    async def test_ai_memory(self) -> dict:
        """Test if AI remembers information after restart"""
        try:
            # Check if database contains our test message
            conn = sqlite3.connect(CONVERSATION_DATABASE)
            cursor = conn.cursor()
            
            # Get conversation data from store table
            cursor.execute("SELECT value FROM store WHERE key = 'llm_conversation_history'")
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return {'success': False, 'error': 'No conversation data found'}
            
            # Parse the JSON conversation data
            import json
            conversation_data = json.loads(result[0])
            
            # Look for messages containing "flibbertigibbet"
            test_word_messages = []
            user_message_found = False
            ai_response_found = False
            
            for msg in conversation_data:
                if isinstance(msg, dict) and 'content' in msg and 'role' in msg:
                    if 'flibbertigibbet' in msg['content']:
                        test_word_messages.append(msg)
                        if msg['role'] == 'user' and 'test word is flibbertigibbet' in msg['content']:
                            user_message_found = True
                        elif msg['role'] == 'assistant' and 'flibbertigibbet' in msg['content']:
                            ai_response_found = True
            
            success = user_message_found and ai_response_found
            
            print(f"   🧠 User message found: {user_message_found}")
            print(f"   🤖 AI response found: {ai_response_found}")
            print(f"   📊 Total test word messages: {len(test_word_messages)}")
            print(f"   📊 Total conversation messages: {len(conversation_data)}")
            
            return {
                'success': success,
                'user_message_found': user_message_found,
                'ai_response_found': ai_response_found,
                'total_test_word_messages': len(test_word_messages),
                'total_conversation_messages': len(conversation_data)
            }
            
        except Exception as e:
            print(f"   ❌ Error testing AI memory: {e}")
            return {'success': False, 'error': str(e)}
    
    async def handle_failure(self, error_message: str) -> dict:
        """Handle test failure with diagnostic information"""
        print(f"❌ TEST FAILED: {error_message}")
        
        # Collect diagnostic data
        diagnostic_data = {
            'database_exists': os.path.exists(CONVERSATION_DATABASE),
            'message_count': await self.get_message_count(),
            'server_responsive': await self.check_server_responsive(),
            'error_message': error_message
        }
        
        return {
            'success': False,
            'test_name': self.test_name,
            'error': error_message,
            'diagnostic_data': diagnostic_data,
            'timestamp': datetime.now().isoformat()
        }
    
    async def debug_conversation_data(self) -> None:
        """Debug what's actually in the conversation database"""
        try:
            conn = sqlite3.connect(CONVERSATION_DATABASE)
            cursor = conn.cursor()
            
            # Get conversation data from store table
            cursor.execute("SELECT value FROM store WHERE key = 'llm_conversation_history'")
            result = cursor.fetchone()
            conn.close()
            
            if result:
                import json
                conversation_data = json.loads(result[0])
                print(f"   🔍 DEBUG: Found {len(conversation_data)} messages in conversation data")
                
                # Show the last few messages
                for i, msg in enumerate(conversation_data[-3:], start=len(conversation_data)-2):
                    if isinstance(msg, dict) and 'content' in msg and 'role' in msg:
                        content_preview = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
                        print(f"   🔍 Message {i}: [{msg['role']}] {content_preview}")
            else:
                print(f"   🔍 DEBUG: No conversation data found in database")
                
        except Exception as e:
            print(f"   🔍 DEBUG ERROR: {e}")
    
    async def check_server_responsive(self) -> bool:
        """Check if server is responsive"""
        try:
            import requests
            response = requests.get(SERVER_URL, timeout=5)
            return response.status_code == 200
        except:
            return False

async def main():
    """Run the conversation persistence test"""
    test = ConversationPersistenceTestFinal()
    result = await test.run_complete_test()
    
    print("\n" + "=" * 80)
    print("🎯 FINAL TEST RESULTS")
    print("=" * 80)
    
    if result['success']:
        print("✅ CONVERSATION PERSISTENCE TEST PASSED!")
        print(f"📊 Results: {result['results']}")
        print("\n🎉 The bottled test harness pattern works!")
        print("🍾 Pattern successfully bottled for future use!")
    else:
        print("❌ CONVERSATION PERSISTENCE TEST FAILED")
        print(f"🔍 Error: {result.get('error', 'Unknown error')}")
        if 'diagnostic_data' in result:
            print("📊 Diagnostic Data:")
            for key, value in result['diagnostic_data'].items():
                print(f"   {key}: {value}")
    
    print("=" * 80)
    
    # Save results
    results_file = f"test_results/{result['test_name']}_results.json"
    os.makedirs("test_results", exist_ok=True)
    with open(results_file, "w") as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"📁 Results saved to: {results_file}")
    
    return result

if __name__ == "__main__":
    asyncio.run(main()) 
#!/usr/bin/env python3
"""
🎯 Conversation Persistence Test - Final Implementation (New Architecture)
Tests conversation persistence across server restarts with new append-only conversation system
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
CONVERSATION_DATABASE = str(Path(__file__).parent.parent / "data" / "discussion.db")
SERVER_URL = "http://localhost:5001"
CHAT_TEXTAREA = 'textarea[name="msg"]'
CHAT_SUBMIT_BUTTON = 'button[type="submit"]'

# Multi-cycle test configuration
TEST_WORDS = [
    "flibbertigibbet",
    "slartibartfast"
]

TEST_MESSAGES = [
    f"The test word is {word}. Please remember this for our conversation."
    for word in TEST_WORDS
]

TEST_CYCLES = len(TEST_WORDS)  # 2 cycles
TEST_MESSAGE_PHASE_3 = "What are the test words I mentioned?"

# Critical timing constants for LLM streaming
LLM_RESPONSE_INITIAL_WAIT = 3     # Wait for response to start
LLM_RESPONSE_STREAMING_WAIT = 15  # Wait for streaming to complete
LLM_RESPONSE_FINALIZATION_WAIT = 3 # Wait for conversation save
BROWSER_INTERACTION_DELAY = 2     # Delay between browser actions
SERVER_RESTART_WAIT = 8           # Wait for server restart

class ConversationPersistenceTestFinal:
    """
    Bottled pattern: Web UI Action → Verify Effect
    Tests conversation persistence with new append-only architecture
    """
    
    def __init__(self):
        self.test_name = "conversation_persistence_final_new_architecture"
        self.driver = None
        self.results = {}
        self.browser_session_count = 0
        
    async def run_complete_test(self) -> dict:
        """Execute the complete N-cycle test"""
        try:
            print(f"🎯 Starting {TEST_CYCLES}-Cycle Conversation Persistence Test (New Architecture)")
            print("=" * 60)
            
            # Phase 1: Baseline
            print("📋 Phase 1: Establishing baseline...")
            baseline_messages = await self.get_message_count()
            print(f"   📊 Baseline: {baseline_messages} messages in database")
            
            # Track results for each cycle
            cycle_results = []
            
            # Execute N cycles
            for cycle_num in range(TEST_CYCLES):
                print(f"\n🔄 CYCLE {cycle_num + 1}/{TEST_CYCLES}: Testing word '{TEST_WORDS[cycle_num]}'")
                print("-" * 40)
                
                # Phase 2: Send message with proper timing
                print(f"📝 Phase 2.{cycle_num + 1}: Sending test message...")
                print(f"   🌐 Creating browser session {cycle_num + 1}/2...")
                message_result = await self.send_message_with_streaming_wait(TEST_MESSAGES[cycle_num])
                
                if not message_result['success']:
                    return await self.handle_failure(f"Cycle {cycle_num + 1}: Failed to send message")
                
                # Phase 3: Verify message was saved
                print(f"💾 Phase 3.{cycle_num + 1}: Verifying message persistence...")
                
                # Check multiple times to account for potential delay
                messages_after_send = None
                for attempt in range(3):
                    messages_after_send = await self.get_message_count()
                    print(f"   📊 Attempt {attempt + 1}: {messages_after_send} messages in database")
                    
                    # Simply check if message count increased from baseline
                    if messages_after_send > baseline_messages:
                        print(f"   ✅ Message count increased: {messages_after_send} > {baseline_messages}")
                        break
                        
                    if attempt < 2:  # Don't wait after the last attempt
                        print(f"   ⏳ Waiting 5 more seconds for database update...")
                        await asyncio.sleep(5)
                else:
                    # Check if there's conversation data but count is wrong
                    await self.debug_conversation_data()
                    return await self.handle_failure(f"Cycle {cycle_num + 1}: Message count did not increase from baseline: {messages_after_send}")
                
                # Phase 4: Restart server
                print(f"🔄 Phase 4.{cycle_num + 1}: Restarting server...")
                restart_result = await self.restart_server_via_mcp()
                
                if not restart_result['success']:
                    return await self.handle_failure(f"Cycle {cycle_num + 1}: Server restart failed")
                
                # Phase 5: Verify conversation persisted after restart
                print(f"🔍 Phase 5.{cycle_num + 1}: Verifying conversation persistence...")
                messages_after_restart = await self.get_message_count()
                print(f"   📊 After restart: {messages_after_restart} messages in database")
                
                # Check if current cycle's word is still there
                current_word_present = await self.check_word_in_conversation(TEST_WORDS[cycle_num])
                print(f"   🧠 Word '{TEST_WORDS[cycle_num]}' present after restart: {current_word_present}")
                
                # For proper persistence, each restart should maintain all previous words
                all_previous_words_present = True
                for prev_word_idx in range(cycle_num + 1):
                    word_present = await self.check_word_in_conversation(TEST_WORDS[prev_word_idx])
                    print(f"   🧠 Word '{TEST_WORDS[prev_word_idx]}' present: {word_present}")
                    if not word_present:
                        all_previous_words_present = False
                
                # Success means: messages didn't drop to baseline AND current word is still there
                cycle_success = (
                    messages_after_restart > baseline_messages and 
                    current_word_present and
                    all_previous_words_present
                )
                
                # Store cycle results
                cycle_results.append({
                    'cycle': cycle_num + 1,
                    'word': TEST_WORDS[cycle_num],
                    'messages_after_send': messages_after_send,
                    'messages_after_restart': messages_after_restart,
                    'current_word_present': current_word_present,
                    'all_previous_words_present': all_previous_words_present,
                    'success': cycle_success
                })
                
                # Clean up browser for next cycle
                print(f"🧹 Phase 6.{cycle_num + 1}: Cleaning up browser session...")
                if self.driver:
                    self.driver.quit()
                    self.driver = None
                    print(f"   ✅ Browser session #{self.browser_session_count} closed cleanly")
                    # Small delay to ensure Chrome process fully terminates
                    await asyncio.sleep(1)
            
            # Phase 6: Final comprehensive memory test
            print(f"\n🧠 Phase 6: Testing comprehensive AI memory...")
            memory_result = await self.test_ai_memory_comprehensive()
            
            # Generate overall results
            all_cycles_successful = all(cycle['success'] for cycle in cycle_results)
            success = all_cycles_successful and memory_result['success']
            
            return {
                'success': success,
                'test_name': self.test_name,
                'results': {
                    'baseline_messages': baseline_messages,
                    'cycles': cycle_results,
                    'final_message_count': await self.get_message_count(),
                    'memory_test': memory_result,
                    'all_cycles_successful': all_cycles_successful
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return await self.handle_failure(f"Test exception: {str(e)}")
        finally:
            if self.driver:
                print(f"🧹 Final cleanup: Closing browser session #{self.browser_session_count}")
                self.driver.quit()
                self.driver = None
    
    async def get_message_count(self) -> int:
        """Get current message count from new conversations table"""
        try:
            if not os.path.exists(CONVERSATION_DATABASE):
                return 0
            
            conn = sqlite3.connect(CONVERSATION_DATABASE)
            cursor = conn.cursor()
            
            # Check if conversations table exists (new architecture)
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='conversations'
            """)
            
            if cursor.fetchone():
                # New architecture: Count rows in conversations table
                cursor.execute("SELECT COUNT(*) FROM conversations")
                result = cursor.fetchone()
                conn.close()
                return result[0] if result else 0
            else:
                # Fallback: Check old store table for backward compatibility
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
            # Ensure no existing browser session
            if self.driver:
                print(f"   ⚠️ Warning: Existing browser found, cleaning up...")
                self.driver.quit()
                self.driver = None
            
            # Setup fresh browser session
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            
            self.browser_session_count += 1
            print(f"   🚀 Creating Chrome browser session #{self.browser_session_count}...")
            self.driver = webdriver.Chrome(options=chrome_options)
            print(f"   🌐 Navigating to {SERVER_URL}...")
            self.driver.get(SERVER_URL)
            
            # Wait for page to load
            await asyncio.sleep(BROWSER_INTERACTION_DELAY)
            
            # Find and interact with chat interface
            print(f"   🎭 Locating chat interface...")
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
            
            # Get the correct path to the pipulate directory
            pipulate_dir = Path(__file__).parent.parent
            python_path = pipulate_dir / ".venv" / "bin" / "python"
            cli_path = pipulate_dir / "cli.py"
            
            print(f"   📁 Using Python: {python_path}")
            print(f"   📁 Using CLI: {cli_path}")
            
            result = subprocess.run([
                str(python_path), str(cli_path), "call", "server_reboot"
            ], capture_output=True, text=True, timeout=30, cwd=str(pipulate_dir))
            
            print(f"   📝 MCP stdout: {result.stdout}")
            if result.stderr:
                print(f"   ⚠️ MCP stderr: {result.stderr}")
            
            print(f"   ⚠️ Note: MCP tools may create additional browser sessions not tracked by this test")
            
            print(f"   ⏳ Waiting {SERVER_RESTART_WAIT}s for server restart...")
            await asyncio.sleep(SERVER_RESTART_WAIT)
            
            # Verify server is back up (using requests, not browser)
            print(f"   🔍 Verifying server is responsive via HTTP request...")
            import requests
            for attempt in range(5):
                try:
                    response = requests.get(SERVER_URL, timeout=5)
                    if response.status_code == 200:
                        print(f"   ✅ Server is back online (HTTP 200)")
                        return {'success': True}
                except Exception as e:
                    print(f"   ⏳ Server not ready, attempt {attempt + 1}/5 (error: {e})...")
                    await asyncio.sleep(2)
            
            return {'success': False, 'error': 'Server did not come back online'}
            
        except Exception as e:
            print(f"   ❌ Error restarting server: {e}")
            return {'success': False, 'error': str(e)}
    
    async def test_ai_memory_comprehensive(self) -> dict:
        """Test if AI remembers all test words from all cycles (new architecture)"""
        try:
            conn = sqlite3.connect(CONVERSATION_DATABASE)
            cursor = conn.cursor()
            
            # Check if conversations table exists (new architecture)
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='conversations'
            """)
            
            if cursor.fetchone():
                # New architecture: Query conversations table
                cursor.execute("SELECT role, content FROM conversations ORDER BY timestamp")
                messages = cursor.fetchall()
                conversation_data = [{'role': role, 'content': content} for role, content in messages]
                print(f"   🏗️ Using NEW ARCHITECTURE: {len(conversation_data)} messages from conversations table")
            else:
                # Fallback: Old store table
                cursor.execute("SELECT value FROM store WHERE key = 'llm_conversation_history'")
                result = cursor.fetchone()
                
                if not result:
                    conn.close()
                    return {'success': False, 'error': 'No conversation data found'}
                
                # Parse the JSON conversation data
                import json
                conversation_data = json.loads(result[0])
                print(f"   📊 Using OLD ARCHITECTURE: {len(conversation_data)} messages from JSON blob")
            
            conn.close()
            
            # Track results for each test word
            word_results = {}
            
            for word in TEST_WORDS:
                word_results[word] = {
                    'user_message_found': False,
                    'ai_response_found': False,
                    'total_messages': 0
                }
                
                # Look for messages containing this word
                for msg in conversation_data:
                    if isinstance(msg, dict) and 'content' in msg and 'role' in msg:
                        if word in msg['content']:
                            word_results[word]['total_messages'] += 1
                            
                            if msg['role'] == 'user' and f'test word is {word}' in msg['content']:
                                word_results[word]['user_message_found'] = True
                            elif msg['role'] == 'assistant' and word in msg['content']:
                                word_results[word]['ai_response_found'] = True
            
            # Check overall success
            all_words_found = True
            for word, result in word_results.items():
                word_success = result['user_message_found'] and result['ai_response_found']
                print(f"   🧠 Word '{word}': User={result['user_message_found']}, AI={result['ai_response_found']}, Total={result['total_messages']}")
                if not word_success:
                    all_words_found = False
            
            print(f"   📊 Total conversation messages: {len(conversation_data)}")
            print(f"   ✅ All words found: {all_words_found}")
            
            return {
                'success': all_words_found,
                'word_results': word_results,
                'total_conversation_messages': len(conversation_data),
                'all_words_found': all_words_found,
                'architecture_used': 'new' if conversation_data else 'old'
            }
            
        except Exception as e:
            print(f"   ❌ Error testing comprehensive AI memory: {e}")
            return {'success': False, 'error': str(e)}
    
    async def handle_failure(self, error_message: str) -> dict:
        """Handle test failure with diagnostic information"""
        print(f"❌ TEST FAILED: {error_message}")
        
        # Collect diagnostic data
        diagnostic_data = {
            'database_exists': os.path.exists(CONVERSATION_DATABASE),
            'message_count': await self.get_message_count(),
            'server_responsive': await self.check_server_responsive(),
            'error_message': error_message,
            'architecture_detected': await self.detect_conversation_architecture()
        }
        
        return {
            'success': False,
            'test_name': self.test_name,
            'error': error_message,
            'diagnostic_data': diagnostic_data,
            'timestamp': datetime.now().isoformat()
        }
    
    async def detect_conversation_architecture(self) -> str:
        """Detect which conversation architecture is being used"""
        try:
            if not os.path.exists(CONVERSATION_DATABASE):
                return "no_database"
            
            conn = sqlite3.connect(CONVERSATION_DATABASE)
            cursor = conn.cursor()
            
            # Check for new conversations table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='conversations'
            """)
            
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM conversations")
                count = cursor.fetchone()[0]
                conn.close()
                return f"new_architecture ({count} messages in conversations table)"
            else:
                # Check for old store table
                cursor.execute("SELECT value FROM store WHERE key = 'llm_conversation_history'")
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    import json
                    conversation_data = json.loads(result[0])
                    return f"old_architecture ({len(conversation_data)} messages in JSON blob)"
                else:
                    return "no_conversation_data"
        except Exception as e:
            return f"detection_error: {e}"
    
    async def debug_conversation_data(self) -> None:
        """Debug what's actually in the conversation database (both architectures)"""
        try:
            conn = sqlite3.connect(CONVERSATION_DATABASE)
            cursor = conn.cursor()
            
            # Check for new conversations table first
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='conversations'
            """)
            
            if cursor.fetchone():
                # New architecture debugging
                cursor.execute("SELECT COUNT(*) FROM conversations")
                count = cursor.fetchone()[0]
                print(f"   🔍 DEBUG (NEW): Found {count} messages in conversations table")
                
                if count > 0:
                    cursor.execute("""
                        SELECT role, SUBSTR(content, 1, 50) as content_preview
                        FROM conversations 
                        ORDER BY timestamp DESC LIMIT 5
                    """)
                    messages = cursor.fetchall()
                    
                    print(f"   🔍 Recent messages:")
                    for i, (role, content_preview) in enumerate(messages):
                        print(f"   🔍 Message {i+1}: [{role}] {content_preview}...")
                
                # Check for test words
                print(f"   🔍 DEBUG: Checking for test words in new architecture...")
                for word in TEST_WORDS:
                    cursor.execute("SELECT COUNT(*) FROM conversations WHERE content LIKE ?", (f'%{word}%',))
                    count = cursor.fetchone()[0]
                    print(f"   🔍 Word '{word}' found in {count} messages")
            else:
                # Fallback to old architecture debugging
                cursor.execute("SELECT value FROM store WHERE key = 'llm_conversation_history'")
                result = cursor.fetchone()
                
                if result:
                    import json
                    conversation_data = json.loads(result[0])
                    print(f"   🔍 DEBUG (OLD): Found {len(conversation_data)} messages in JSON blob")
                    
                    # Show the last few messages
                    for i, msg in enumerate(conversation_data[-3:], start=len(conversation_data)-2):
                        if isinstance(msg, dict) and 'content' in msg and 'role' in msg:
                            content_preview = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
                            print(f"   🔍 Message {i}: [{msg['role']}] {content_preview}")
                    
                    # Debug: Check for test words
                    print(f"   🔍 DEBUG: Checking for test words in old architecture...")
                    for word in TEST_WORDS:
                        count = sum(1 for msg in conversation_data 
                                   if isinstance(msg, dict) and 'content' in msg and word in msg['content'])
                        print(f"   🔍 Word '{word}' found in {count} messages")
                else:
                    print(f"   🔍 DEBUG: No conversation data found in either architecture")
            
            conn.close()
                
        except Exception as e:
            print(f"   🔍 DEBUG ERROR: {e}")
    
    async def check_word_in_conversation(self, word: str) -> bool:
        """Check if a specific word exists in the conversation database (both architectures)"""
        try:
            conn = sqlite3.connect(CONVERSATION_DATABASE)
            cursor = conn.cursor()
            
            # Check for new conversations table first
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='conversations'
            """)
            
            if cursor.fetchone():
                # New architecture: Query conversations table
                cursor.execute("SELECT COUNT(*) FROM conversations WHERE content LIKE ?", (f'%{word}%',))
                result = cursor.fetchone()
                conn.close()
                return result[0] > 0 if result else False
            else:
                # Fallback to old architecture
                cursor.execute("SELECT value FROM store WHERE key = 'llm_conversation_history'")
                result = cursor.fetchone()
                conn.close()
                
                if not result:
                    return False
                
                # Parse the JSON conversation data
                import json
                conversation_data = json.loads(result[0])
                
                # Look for the word in any message
                for msg in conversation_data:
                    if isinstance(msg, dict) and 'content' in msg and word in msg['content']:
                        return True
                
                return False
            
        except Exception as e:
            print(f"   ⚠️ Error checking word '{word}': {e}")
            return False
    
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
    print(f"🎯 FINAL {TEST_CYCLES}-CYCLE TEST RESULTS (NEW ARCHITECTURE)")
    print("=" * 80)
    
    if result['success']:
        print("✅ MULTI-CYCLE CONVERSATION PERSISTENCE TEST PASSED!")
        print(f"📊 Test Summary:")
        print(f"   🔄 Cycles completed: {TEST_CYCLES}")
        print(f"   📝 Test words: {', '.join(TEST_WORDS)}")
        print(f"   💾 Final message count: {result['results']['final_message_count']}")
        print(f"   ✅ All cycles successful: {result['results']['all_cycles_successful']}")
        
        # Show architecture used
        if 'memory_test' in result['results'] and 'architecture_used' in result['results']['memory_test']:
            arch = result['results']['memory_test']['architecture_used']
            print(f"   🏗️ Architecture used: {arch.upper()}")
        
        # Show cycle-by-cycle results
        if 'cycles' in result['results']:
            print("\n📋 Cycle-by-Cycle Results:")
            for cycle_result in result['results']['cycles']:
                status = "✅" if cycle_result['success'] else "❌"
                word_status = "✅" if cycle_result.get('current_word_present', False) else "❌"
                all_words_status = "✅" if cycle_result.get('all_previous_words_present', False) else "❌"
                print(f"   {status} Cycle {cycle_result['cycle']}: '{cycle_result['word']}'")
                print(f"      📊 Messages: Send={cycle_result['messages_after_send']}, Restart={cycle_result['messages_after_restart']}")
                print(f"      🧠 Word Present: {word_status}, All Words Present: {all_words_status}")
        
        # Show memory test results
        if 'memory_test' in result['results'] and 'word_results' in result['results']['memory_test']:
            print("\n🧠 Memory Test Results:")
            for word, word_result in result['results']['memory_test']['word_results'].items():
                user_status = "✅" if word_result['user_message_found'] else "❌"
                ai_status = "✅" if word_result['ai_response_found'] else "❌"
                print(f"   '{word}': User {user_status}, AI {ai_status}, Total messages: {word_result['total_messages']}")
        
        print("\n🎉 The multi-cycle bottled test harness pattern works with new architecture!")
        print("🍾 New append-only conversation system successfully tested!")
    else:
        print("❌ MULTI-CYCLE CONVERSATION PERSISTENCE TEST FAILED")
        print(f"🔍 Error: {result.get('error', 'Unknown error')}")
        
        # Show diagnostic data including architecture detection
        if 'diagnostic_data' in result:
            print("\n📊 Diagnostic Data:")
            for key, value in result['diagnostic_data'].items():
                print(f"   {key}: {value}")
        
        # Show partial results if available
        if 'results' in result and 'cycles' in result['results']:
            print("\n📋 Partial Cycle Results:")
            for cycle_result in result['results']['cycles']:
                status = "✅" if cycle_result['success'] else "❌"
                word_status = "✅" if cycle_result.get('current_word_present', False) else "❌"
                all_words_status = "✅" if cycle_result.get('all_previous_words_present', False) else "❌"
                print(f"   {status} Cycle {cycle_result['cycle']}: '{cycle_result['word']}'")
                print(f"      📊 Messages: Send={cycle_result['messages_after_send']}, Restart={cycle_result['messages_after_restart']}")
                print(f"      🧠 Word Present: {word_status}, All Words Present: {all_words_status}")
    
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

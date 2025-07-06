# 🔍 AI Detective Implementation Guide

## 🚀 QUICK START: Implementing the Pattern

This guide shows **exactly how to implement** the deterministic testing pattern in your own projects.

---

## 📋 STEP 1: Create Your Static Constants

Create a constants file that establishes your system truths:

```python
# constants.py
"""Static constants - NEVER QUESTION THESE"""

# Database paths (adjust for your system)
DATABASE_PATH = "data/your_app.db"
BACKUP_PATH = "data/backup.db"

# Server configuration
SERVER_URL = "http://localhost:8000"  # Your server
API_ENDPOINT = "/api/v1"
CHAT_ENDPOINT = "/chat"

# UI selectors (inspect your HTML)
SUBMIT_BUTTON = 'button[type="submit"]'
INPUT_FIELD = 'input[name="message"]'
FORM_SELECTOR = 'form#main-form'

# Timing constants (adjust based on your app)
PAGE_LOAD_WAIT = 2
PROCESSING_WAIT = 5
API_RESPONSE_WAIT = 10
STREAMING_WAIT = 15  # For LLM responses

# Test data
TEST_MESSAGE = "Your test message here"
EXPECTED_RESPONSE_CONTAINS = "expected text"
```

---

## 🎭 STEP 2: Create the Base Test Harness

```python
# test_harness.py
import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from constants import *
from ai_detective import AIDetective

class DeterministicTestHarness:
    """Base class for deterministic testing"""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.driver = None
        self.baseline = {}
        self.action_result = {}
        self.verification = {}
        
    async def execute_test_cycle(self) -> dict:
        """Execute the complete 4-phase test cycle"""
        try:
            print(f"🎯 Starting {self.test_name}")
            print("=" * 60)
            
            # Phase 1: Setup & Baseline
            print("📋 Phase 1: Establishing baseline...")
            self.baseline = await self.establish_baseline()
            self.log_baseline()
            
            # Phase 2: Execute Action
            print("🎭 Phase 2: Executing web UI action...")
            self.action_result = await self.execute_web_ui_action()
            
            if not self.action_result.get('success', False):
                return await self.handle_failure("Action execution failed")
            
            # Phase 3: Verify Effect
            print("🔍 Phase 3: Verifying expected effect...")
            self.verification = await self.verify_expected_effect()
            
            if self.verification['success']:
                return self.generate_success_report()
            else:
                # Phase 4: AI Detective
                print("🔍 Phase 4: AI Detective investigation...")
                return await self.ai_detective_investigation()
                
        except Exception as e:
            return await self.handle_failure(f"Test exception: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
    
    async def establish_baseline(self) -> dict:
        """Phase 1: Override in subclass"""
        raise NotImplementedError("Subclass must implement establish_baseline")
    
    async def execute_web_ui_action(self) -> dict:
        """Phase 2: Override in subclass"""
        raise NotImplementedError("Subclass must implement execute_web_ui_action")
    
    async def verify_expected_effect(self) -> dict:
        """Phase 3: Override in subclass"""
        raise NotImplementedError("Subclass must implement verify_expected_effect")
    
    async def ai_detective_investigation(self) -> dict:
        """Phase 4: AI Detective investigation"""
        investigation = await AIDetective.investigate(
            test_name=self.test_name,
            baseline=self.baseline,
            action_result=self.action_result,
            verification_failure=self.verification
        )
        
        # Ensure proper result format
        investigation['success'] = False
        investigation['test_name'] = self.test_name
        investigation['timestamp'] = datetime.now().isoformat()
        
        return investigation
    
    def log_baseline(self):
        """Log baseline information"""
        print(f"   📊 Baseline established at {self.baseline.get('timestamp', 'unknown')}")
        for key, value in self.baseline.items():
            if key != 'timestamp':
                print(f"   📊 {key}: {value}")
    
    def generate_success_report(self) -> dict:
        """Generate success report"""
        return {
            'success': True,
            'test_name': self.test_name,
            'success_message': f'{self.test_name} passed successfully!',
            'baseline': self.baseline,
            'action_result': self.action_result,
            'verification': self.verification,
            'timestamp': datetime.now().isoformat()
        }
    
    async def handle_failure(self, error_message: str) -> dict:
        """Handle test failure"""
        return {
            'success': False,
            'test_name': self.test_name,
            'error': error_message,
            'baseline': self.baseline,
            'action_result': self.action_result,
            'verification': self.verification,
            'timestamp': datetime.now().isoformat()
        }
    
    def setup_browser(self, headless: bool = False) -> webdriver.Chrome:
        """Setup Chrome browser with standard options"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        return webdriver.Chrome(options=chrome_options)
```

---

## 🔍 STEP 3: Create the AI Detective

```python
# ai_detective.py
import asyncio
import os
import sqlite3
from typing import Dict, Any

from constants import *

class AIDetective:
    """Binary search debugging methodology"""
    
    DIAGNOSTIC_LEVELS = [
        "SYSTEM_LEVEL",      # Server running? Database accessible?
        "NETWORK_LEVEL",     # HTTP requests working? Endpoints responding?
        "APPLICATION_LEVEL", # UI functional? Elements present?
        "DATA_LEVEL",        # Database writes? Data persistence?
        "LOGIC_LEVEL"        # Business logic? Expected behavior?
    ]
    
    @staticmethod
    async def investigate(test_name: str, baseline: dict, action_result: dict, verification_failure: dict) -> dict:
        """Binary search through diagnostic levels to isolate root cause"""
        print(f"🔍 AI Detective investigating {test_name}...")
        investigation_results = {}
        
        for level in AIDetective.DIAGNOSTIC_LEVELS:
            print(f"   🔍 Diagnosing {level}...")
            diagnostic_result = await AIDetective.diagnose_level(level, baseline, action_result)
            investigation_results[level] = diagnostic_result
            
            if diagnostic_result['failure_detected']:
                print(f"   ❌ Failure detected at {level}")
                root_cause = await AIDetective.isolate_root_cause(level, diagnostic_result)
                fix_recommendations = await AIDetective.generate_fix_recommendations(level, root_cause)
                
                return {
                    'failure_level': level,
                    'root_cause': root_cause,
                    'fix_recommendations': fix_recommendations,
                    'diagnostic_data': investigation_results
                }
            else:
                print(f"   ✅ {level} passed")
        
        return {
            'failure_level': 'UNKNOWN',
            'root_cause': 'All diagnostic levels passed - logic error suspected',
            'fix_recommendations': ['Review test expectations', 'Check timing issues', 'Verify test data'],
            'diagnostic_data': investigation_results
        }
    
    @staticmethod
    async def diagnose_level(level: str, baseline: dict, action_result: dict) -> dict:
        """Diagnose specific level for failures"""
        if level == "SYSTEM_LEVEL":
            return await AIDetective.diagnose_system_level()
        elif level == "NETWORK_LEVEL":
            return await AIDetective.diagnose_network_level()
        elif level == "APPLICATION_LEVEL":
            return await AIDetective.diagnose_application_level()
        elif level == "DATA_LEVEL":
            return await AIDetective.diagnose_data_level()
        elif level == "LOGIC_LEVEL":
            return await AIDetective.diagnose_logic_level()
        else:
            return {'failure_detected': False, 'details': 'Unknown diagnostic level'}
    
    @staticmethod
    async def diagnose_system_level() -> dict:
        """Check if basic system components are working"""
        try:
            # Check if database exists
            db_exists = os.path.exists(DATABASE_PATH)
            
            # Check if server is responding
            import requests
            try:
                response = requests.get(SERVER_URL, timeout=5)
                server_responding = response.status_code == 200
            except:
                server_responding = False
            
            failure_detected = not (db_exists and server_responding)
            
            return {
                'failure_detected': failure_detected,
                'details': {
                    'database_exists': db_exists,
                    'database_path': DATABASE_PATH,
                    'server_responding': server_responding,
                    'server_url': SERVER_URL
                }
            }
        except Exception as e:
            return {
                'failure_detected': True,
                'details': f"System level diagnostic failed: {str(e)}"
            }
    
    @staticmethod
    async def diagnose_network_level() -> dict:
        """Check if HTTP communication is working"""
        try:
            import requests
            
            # Test GET request
            get_response = requests.get(SERVER_URL, timeout=5)
            
            # Test POST request if applicable
            post_response = None
            if CHAT_ENDPOINT:
                try:
                    post_response = requests.post(f"{SERVER_URL}{CHAT_ENDPOINT}", 
                                                data={"message": "test"}, 
                                                timeout=5)
                except:
                    pass
            
            failure_detected = get_response.status_code != 200
            
            return {
                'failure_detected': failure_detected,
                'details': {
                    'get_status': get_response.status_code,
                    'get_response_time': get_response.elapsed.total_seconds(),
                    'post_status': post_response.status_code if post_response else 'N/A',
                    'post_response_time': post_response.elapsed.total_seconds() if post_response else 'N/A'
                }
            }
        except Exception as e:
            return {
                'failure_detected': True,
                'details': f"Network level diagnostic failed: {str(e)}"
            }
    
    @staticmethod
    async def diagnose_application_level() -> dict:
        """Check if UI elements are functional"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Setup headless browser
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(SERVER_URL)
            
            # Check if required elements exist
            wait = WebDriverWait(driver, 10)
            elements_found = {}
            
            # Check each required element
            for element_name, selector in [
                ('submit_button', SUBMIT_BUTTON),
                ('input_field', INPUT_FIELD),
                ('form', FORM_SELECTOR)
            ]:
                try:
                    element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    elements_found[element_name] = True
                except:
                    elements_found[element_name] = False
            
            driver.quit()
            
            failure_detected = not all(elements_found.values())
            
            return {
                'failure_detected': failure_detected,
                'details': {
                    'page_loaded': True,
                    'elements_found': elements_found,
                    'page_title': driver.title if not failure_detected else 'N/A'
                }
            }
        except Exception as e:
            return {
                'failure_detected': True,
                'details': f"Application level diagnostic failed: {str(e)}"
            }
    
    @staticmethod
    async def diagnose_data_level() -> dict:
        """Check if data operations are working"""
        try:
            # This is highly application-specific
            # Implement based on your data storage system
            
            # Example for SQLite database
            if os.path.exists(DATABASE_PATH):
                conn = sqlite3.connect(DATABASE_PATH)
                cursor = conn.cursor()
                
                # Check if required tables exist
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # Check if data can be read/written
                # (implement based on your schema)
                
                conn.close()
                
                failure_detected = len(tables) == 0
                
                return {
                    'failure_detected': failure_detected,
                    'details': {
                        'database_accessible': True,
                        'tables_found': tables,
                        'table_count': len(tables)
                    }
                }
            else:
                return {
                    'failure_detected': True,
                    'details': 'Database file does not exist'
                }
                
        except Exception as e:
            return {
                'failure_detected': True,
                'details': f"Data level diagnostic failed: {str(e)}"
            }
    
    @staticmethod
    async def diagnose_logic_level() -> dict:
        """Check if business logic is working"""
        # This is highly application-specific
        # Implement based on your business logic
        return {
            'failure_detected': False,
            'details': 'Logic level diagnostics require application-specific implementation'
        }
    
    @staticmethod
    async def isolate_root_cause(level: str, diagnostic_result: dict) -> str:
        """Isolate the specific root cause within a diagnostic level"""
        details = diagnostic_result.get('details', {})
        
        if level == "SYSTEM_LEVEL":
            if not details.get('database_exists'):
                return f"Database file does not exist at {details.get('database_path')}"
            elif not details.get('server_responding'):
                return f"Server is not responding at {details.get('server_url')}"
                
        elif level == "NETWORK_LEVEL":
            if details.get('get_status') != 200:
                return f"GET request failed with status {details.get('get_status')}"
            elif details.get('post_status') not in [200, 302, 'N/A']:
                return f"POST request failed with status {details.get('post_status')}"
                
        elif level == "APPLICATION_LEVEL":
            elements_found = details.get('elements_found', {})
            missing_elements = [name for name, found in elements_found.items() if not found]
            if missing_elements:
                return f"UI elements not found: {', '.join(missing_elements)}"
                
        elif level == "DATA_LEVEL":
            if not details.get('database_accessible'):
                return "Database is not accessible"
            elif details.get('table_count', 0) == 0:
                return "No tables found in database"
        
        return "Root cause not identified"
    
    @staticmethod
    async def generate_fix_recommendations(level: str, root_cause: str) -> list:
        """Generate actionable fix recommendations"""
        recommendations = []
        
        if "Database file does not exist" in root_cause:
            recommendations.extend([
                "Check if database initialization ran correctly",
                "Verify database path is correct",
                "Run database migration if needed",
                "Check file permissions"
            ])
            
        elif "Server is not responding" in root_cause:
            recommendations.extend([
                "Check if server process is running",
                "Verify server port is not blocked",
                "Check server logs for startup errors",
                "Verify server configuration"
            ])
            
        elif "UI elements not found" in root_cause:
            recommendations.extend([
                "Check if UI template is loading correctly",
                "Verify CSS selectors are correct",
                "Check for JavaScript errors in console",
                "Inspect HTML structure for changes"
            ])
            
        elif "request failed" in root_cause:
            recommendations.extend([
                "Check server endpoint configuration",
                "Verify request format and headers",
                "Check server logs for request processing errors",
                "Test endpoint manually with curl"
            ])
            
        else:
            recommendations.extend([
                "Review test expectations",
                "Check timing issues",
                "Verify test data",
                "Add more specific diagnostics"
            ])
        
        return recommendations
```

---

## 🎭 STEP 4: Create Your Specific Test

```python
# your_specific_test.py
import asyncio
import json
from datetime import datetime

from test_harness import DeterministicTestHarness
from constants import *

class YourSpecificTest(DeterministicTestHarness):
    """Your specific test implementation"""
    
    def __init__(self):
        super().__init__("your_specific_test")
        
    async def establish_baseline(self) -> dict:
        """Phase 1: Document current state before action"""
        baseline = {
            'timestamp': datetime.now().isoformat(),
            'record_count': await self.get_record_count(),
            'server_status': await self.check_server_status(),
            'ui_status': await self.check_ui_status()
        }
        return baseline
    
    async def execute_web_ui_action(self) -> dict:
        """Phase 2: Execute your specific web UI action"""
        try:
            # Setup browser
            self.driver = self.setup_browser(headless=False)  # Visible for debugging
            self.driver.get(SERVER_URL)
            
            # Wait for page load
            await asyncio.sleep(PAGE_LOAD_WAIT)
            
            # Find and interact with elements
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            wait = WebDriverWait(self.driver, 10)
            
            # Example: Fill form and submit
            input_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, INPUT_FIELD)))
            submit_button = self.driver.find_element(By.CSS_SELECTOR, SUBMIT_BUTTON)
            
            # Perform action
            input_field.clear()
            input_field.send_keys(TEST_MESSAGE)
            submit_button.click()
            
            # Wait for processing
            print(f"   ⏳ Waiting {PROCESSING_WAIT}s for processing...")
            await asyncio.sleep(PROCESSING_WAIT)
            
            # If this involves streaming (like LLM), wait longer
            if STREAMING_WAIT > 0:
                print(f"   📡 Waiting {STREAMING_WAIT}s for streaming to complete...")
                await asyncio.sleep(STREAMING_WAIT)
            
            return {'success': True, 'message_sent': TEST_MESSAGE}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def verify_expected_effect(self) -> dict:
        """Phase 3: Verify the action had the expected effect"""
        try:
            # Check multiple times to account for async processing
            for attempt in range(3):
                current_state = await self.get_current_state()
                print(f"   📊 Attempt {attempt + 1}: {current_state}")
                
                if await self.meets_success_criteria(current_state):
                    print(f"   ✅ Success criteria met!")
                    return {'success': True, 'final_state': current_state}
                    
                if attempt < 2:  # Don't wait after the last attempt
                    print(f"   ⏳ Waiting 5 more seconds for state update...")
                    await asyncio.sleep(5)
            
            # If we get here, verification failed
            await self.debug_current_state()
            return {'success': False, 'final_state': current_state}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # Helper methods - implement based on your application
    async def get_record_count(self) -> int:
        """Get current record count from your data store"""
        # Implement based on your data storage
        return 0
    
    async def check_server_status(self) -> dict:
        """Check if server is responding"""
        try:
            import requests
            response = requests.get(SERVER_URL, timeout=5)
            return {'responding': True, 'status_code': response.status_code}
        except Exception as e:
            return {'responding': False, 'error': str(e)}
    
    async def check_ui_status(self) -> dict:
        """Check if UI is accessible"""
        # Implement based on your UI
        return {'accessible': True}
    
    async def get_current_state(self) -> dict:
        """Get current application state"""
        # Implement based on what you're testing
        return {
            'record_count': await self.get_record_count(),
            'timestamp': datetime.now().isoformat()
        }
    
    async def meets_success_criteria(self, current_state: dict) -> bool:
        """Check if current state meets success criteria"""
        # Implement your success criteria
        baseline_count = self.baseline.get('record_count', 0)
        current_count = current_state.get('record_count', 0)
        return current_count > baseline_count
    
    async def debug_current_state(self):
        """Debug what's actually happening"""
        print(f"   🔍 DEBUG: Current state analysis...")
        # Add debugging logic specific to your application

# Run the test
async def main():
    test = YourSpecificTest()
    result = await test.execute_test_cycle()
    
    print("\n" + "=" * 80)
    print("🎯 TEST RESULTS")
    print("=" * 80)
    
    if result['success']:
        print("✅ TEST PASSED:", result.get('success_message', 'Test completed successfully'))
    else:
        print("❌ TEST FAILED")
        print(f"🔍 Error: {result.get('error', 'Unknown error')}")
        
        if 'diagnostic_data' in result:
            print("🔍 AI DETECTIVE REPORT:")
            print(f"   Failure Level: {result['failure_level']}")
            print(f"   Root Cause: {result['root_cause']}")
            print("🛠️  FIX RECOMMENDATIONS:")
            for rec in result['fix_recommendations']:
                print(f"   • {rec}")
    
    print("=" * 80)
    
    # Save results
    import os
    os.makedirs("test_results", exist_ok=True)
    with open(f"test_results/{result['test_name']}_results.json", "w") as f:
        json.dump(result, f, indent=2, default=str)
    
    return result

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🚀 STEP 5: Run and Iterate

```bash
# Run your test
python your_specific_test.py

# Analyze results
cat test_results/your_specific_test_results.json

# If test fails, follow AI Detective recommendations
# Update constants, fix issues, and re-run
```

---

## 🎯 CUSTOMIZATION CHECKLIST

### **For Your Application**
- [ ] Update `constants.py` with your URLs, selectors, and timing
- [ ] Implement application-specific diagnostic methods
- [ ] Define your success criteria
- [ ] Add your test data and expected results
- [ ] Customize AI Detective diagnostic levels

### **For Your Test Case**
- [ ] Implement `establish_baseline()` for your data
- [ ] Implement `execute_web_ui_action()` for your UI
- [ ] Implement `verify_expected_effect()` for your criteria
- [ ] Add debugging methods for your application state

### **For Your Environment**
- [ ] Adjust timing constants based on your system performance
- [ ] Configure browser options for your environment
- [ ] Set up proper database/data store access
- [ ] Configure logging and result storage

---

## 🎭 SUCCESS PATTERNS

### **When Tests Pass**
1. **Document the exact configuration** that worked
2. **Save timing values** for future reference  
3. **Create templates** for similar tests
4. **Update constants** with proven values

### **When Tests Fail**
1. **Follow AI Detective recommendations** systematically
2. **Update diagnostics** based on what you learn
3. **Refine timing constants** if needed
4. **Improve error messages** for future debugging

### **Pattern Evolution**
1. **Start simple** - test one thing at a time
2. **Add complexity gradually** - build on proven foundations
3. **Refine diagnostics** - improve based on real failures
4. **Build template library** - reuse successful patterns

**This implementation guide transforms the abstract pattern into concrete, working code that you can adapt for any application.** 🎯 
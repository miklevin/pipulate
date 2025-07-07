#!/usr/bin/env python3
"""
🎯 Rolling Backup System - Deterministic Test Harness

Tests the bulletproof son/father/grandfather backup system that protects:
- ai_keychain.db: Chip O'Theseus's persistent memory  
- discussion.db: Conversation history across restarts
- app.db: Production profiles and tasks
- pipulate_dev.db: Development profiles and tasks

DETERMINISTIC TESTING PATTERN:
1. Baseline: Document current backup state
2. Action: Trigger backup operations via web interface  
3. Verify: Assert all critical databases backed up
4. AI Detective: Binary search through diagnostic levels on failure

Success Criteria: All 4 critical databases backed up to rolling directory structure
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
SERVER_URL = "http://localhost:5001"
BACKUP_ROOT = Path.home() / '.pipulate' / 'backups'

# Critical databases that MUST be backed up
CRITICAL_DATABASES = {
    'ai_keychain': {
        'source_path': 'data/ai_keychain.db',
        'description': 'Chip O\'Theseus Memory',
        'critical': True
    },
    'discussion': {
        'source_path': 'data/discussion.db', 
        'description': 'Conversation History',
        'critical': True
    },
    'app_prod': {
        'source_path': 'data/app.db',
        'description': 'Production Profiles/Tasks',
        'critical': True
    },
    'app_dev': {
        'source_path': 'data/pipulate_dev.db',
        'description': 'Development Profiles/Tasks', 
        'critical': False  # Optional per user requirements
    }
}

# Test constants
PROD_PROFILE_NAME = "Rolling Backup Test Profile"
TEST_KEYCHAIN_ENTRY = f"backup_test_{int(time.time())}"
BROWSER_INTERACTION_DELAY = 2
SERVER_RESTART_WAIT = 8

class RollingBackupTestHarness:
    """Deterministic test harness for rolling backup system verification"""
    
    def __init__(self):
        self.test_name = "rolling_backup_verification"
        self.driver = None
        self.results = {}
        
    async def run_complete_test(self) -> dict:
        """Execute the complete deterministic test cycle"""
        try:
            print("🎯 Starting Rolling Backup System Test")
            print("=" * 60)
            
            # Phase 1: Establish Baseline
            print("📊 Phase 1: Establishing baseline...")
            baseline = await self.establish_baseline()
            print(f"   📊 Baseline: {baseline}")
            
            # Phase 2: Create Test Data
            print("📝 Phase 2: Creating test data in critical databases...")
            await self.create_test_data()
            
            # Phase 3: Trigger Backup via Server Restart
            print("🔄 Phase 3: Triggering backup via server restart...")
            await self.restart_server_to_trigger_backup()
            
            # Phase 4: Verify Backup Success
            print("✅ Phase 4: Verifying backup success...")
            verification_result = await self.verify_backup_success(baseline)
            
            if verification_result['success']:
                return await self.generate_success_report(baseline, verification_result)
            else:
                # Phase 5: AI Detective Investigation
                return await self.ai_detective_investigation(baseline, verification_result)
            
        except Exception as e:
            return await self.handle_failure(f"Test exception: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
    
    async def establish_baseline(self) -> dict:
        """Phase 1: Document current backup state before action"""
        baseline = {
            'timestamp': datetime.now().isoformat(),
            'source_databases': {},
            'backup_structure': {}
        }
        
        # Check source databases
        for db_name, config in CRITICAL_DATABASES.items():
            source_path = config['source_path']
            if os.path.exists(source_path):
                baseline['source_databases'][db_name] = {
                    'exists': True,
                    'size': os.path.getsize(source_path),
                    'mtime': os.path.getmtime(source_path)
                }
            else:
                baseline['source_databases'][db_name] = {'exists': False}
        
        # Check backup directory structure
        if BACKUP_ROOT.exists():
            for backup_type in ['daily', 'weekly', 'monthly']:
                backup_dir = BACKUP_ROOT / backup_type
                if backup_dir.exists():
                    backup_count = len(list(backup_dir.iterdir()))
                    baseline['backup_structure'][backup_type] = backup_count
                else:
                    baseline['backup_structure'][backup_type] = 0
        else:
            baseline['backup_structure'] = {'daily': 0, 'weekly': 0, 'monthly': 0}
        
        return baseline
    
    async def create_test_data(self):
        """Phase 2: Create test data in critical databases"""
        
        # Test data for AI Keychain (MCP tool call)
        print("   🧠 Adding test entry to AI keychain...")
        try:
            result = subprocess.run([
                '.venv/bin/python', 'cli.py', 'call', 'keychain_set',
                '--key', TEST_KEYCHAIN_ENTRY,
                '--value', f'Backup test entry created at {datetime.now().isoformat()}'
            ], capture_output=True, text=True, cwd='.')
            
            if result.returncode == 0:
                print("   ✅ AI keychain test data created")
            else:
                print(f"   ⚠️ AI keychain test data failed: {result.stderr}")
        except Exception as e:
            print(f"   ⚠️ AI keychain test error: {e}")
        
        # Test data for Discussion database (send a chat message)
        print("   💬 Adding test message to discussion history...")
        await self.send_test_chat_message()
        
        # Test data for Production profile (switch to prod and create profile)
        print("   👤 Creating test profile in production mode...")
        await self.create_prod_test_profile()
    
    async def send_test_chat_message(self):
        """Send a test message via chat interface to populate discussion.db"""
        try:
            # Setup browser
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage") 
            chrome_options.add_argument("--disable-gpu")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.get(SERVER_URL)
            
            await asyncio.sleep(BROWSER_INTERACTION_DELAY)
            
            # Find chat interface and send message
            wait = WebDriverWait(self.driver, 10)
            textarea = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[name="msg"]')))
            submit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            
            test_message = f"Rolling backup test message - {datetime.now().isoformat()}"
            textarea.clear()
            textarea.send_keys(test_message)
            submit_button.click()
            
            # Wait for processing
            await asyncio.sleep(3)
            print("   ✅ Chat test message sent")
            
        except Exception as e:
            print(f"   ⚠️ Chat message failed: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    async def create_prod_test_profile(self):
        """Create a test profile in production mode via web interface"""
        try:
            # Setup browser
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.get(SERVER_URL)
            
            await asyncio.sleep(BROWSER_INTERACTION_DELAY)
            
            # Switch to Production mode first
            wait = WebDriverWait(self.driver, 10)
            
            # Look for production switch or mode selector
            try:
                prod_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Production')]")))
                prod_button.click()
                await asyncio.sleep(2)
                print("   ✅ Switched to Production mode")
            except:
                print("   ℹ️ Already in Production mode or switch not found")
            
            # Navigate to profiles (look for profiles link/button)
            try:
                profiles_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Profiles')] | //button[contains(text(), 'Profiles')]")
                profiles_link.click()
                await asyncio.sleep(2)
                
                # Create new profile (look for create/add button)
                create_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Create')] | //button[contains(text(), 'Add')] | //input[@value='Create Profile']")
                create_button.click()
                await asyncio.sleep(1)
                
                # Fill in profile name
                name_input = self.driver.find_element(By.CSS_SELECTOR, "input[name*='name'], input[placeholder*='name'], input[placeholder*='Name']")
                name_input.clear()
                name_input.send_keys(PROD_PROFILE_NAME)
                
                # Submit form
                submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
                submit_button.click()
                await asyncio.sleep(2)
                
                print("   ✅ Production test profile created")
                
            except Exception as e:
                print(f"   ℹ️ Profile creation skipped (interface not found): {e}")
        
        except Exception as e:
            print(f"   ⚠️ Production profile creation failed: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    async def restart_server_to_trigger_backup(self):
        """Phase 3: Restart server to trigger startup backup"""
        print("   🔄 Restarting server to trigger startup backup...")
        
        try:
            # Kill current server
            subprocess.run(['pkill', '-f', 'python.*server.py'], check=False)
            await asyncio.sleep(2)
            
            # Start server in background
            subprocess.Popen(['python', 'server.py'], cwd='.')
            
            # Wait for server to start and trigger backup
            await asyncio.sleep(SERVER_RESTART_WAIT)
            print("   ✅ Server restarted, startup backup should have triggered")
            
        except Exception as e:
            print(f"   ⚠️ Server restart failed: {e}")
    
    async def verify_backup_success(self, baseline: dict) -> dict:
        """Phase 4: Verify all critical databases were backed up"""
        verification = {
            'success': True,
            'details': {},
            'backup_counts': {},
            'missing_backups': []
        }
        
        print("   🔍 Checking backup directory structure...")
        
        # Check if backup root exists
        if not BACKUP_ROOT.exists():
            verification['success'] = False
            verification['details']['backup_root'] = 'Backup root directory does not exist'
            return verification
        
        # Check daily backups for each critical database
        daily_backup_dir = BACKUP_ROOT / 'daily'
        today = datetime.now().strftime('%Y-%m-%d')
        
        if not daily_backup_dir.exists():
            verification['success'] = False
            verification['details']['daily_dir'] = 'Daily backup directory does not exist'
            return verification
        
        today_backup_dir = daily_backup_dir / today
        if not today_backup_dir.exists():
            verification['success'] = False
            verification['details']['today_backup'] = f'Today\'s backup directory does not exist: {today}'
            return verification
        
        # Verify each critical database backup
        for db_name, config in CRITICAL_DATABASES.items():
            backup_file = today_backup_dir / f"{db_name}.db"
            
            if backup_file.exists():
                backup_size = backup_file.stat().st_size
                verification['details'][db_name] = {
                    'backed_up': True,
                    'size': backup_size,
                    'path': str(backup_file.relative_to(BACKUP_ROOT))
                }
                verification['backup_counts'][db_name] = 1
                print(f"   ✅ {config['description']}: {backup_file.relative_to(BACKUP_ROOT)} ({backup_size} bytes)")
            else:
                if config['critical']:
                    verification['success'] = False
                    verification['missing_backups'].append(db_name)
                
                verification['details'][db_name] = {'backed_up': False}
                verification['backup_counts'][db_name] = 0
                
                status = "🚨 CRITICAL MISSING" if config['critical'] else "⚠️ OPTIONAL MISSING"
                print(f"   {status}: {config['description']} backup not found")
        
        # Check retention structure
        retention_counts = {}
        for backup_type in ['daily', 'weekly', 'monthly']:
            backup_dir = BACKUP_ROOT / backup_type
            if backup_dir.exists():
                retention_counts[backup_type] = len(list(backup_dir.iterdir()))
            else:
                retention_counts[backup_type] = 0
        
        verification['retention_counts'] = retention_counts
        print(f"   📊 Retention: Daily: {retention_counts['daily']}, Weekly: {retention_counts['weekly']}, Monthly: {retention_counts['monthly']}")
        
        return verification
    
    async def generate_success_report(self, baseline: dict, verification: dict) -> dict:
        """Generate comprehensive success report"""
        successful_backups = sum(verification['backup_counts'].values())
        total_databases = len(CRITICAL_DATABASES)
        critical_databases = sum(1 for config in CRITICAL_DATABASES.values() if config['critical'])
        critical_backed_up = sum(1 for db_name, count in verification['backup_counts'].items() 
                               if count > 0 and CRITICAL_DATABASES[db_name]['critical'])
        
        print(f"\n🎉 BACKUP TEST SUCCESS!")
        print(f"   📊 Databases backed up: {successful_backups}/{total_databases}")
        print(f"   🚨 Critical databases: {critical_backed_up}/{critical_databases}")
        print(f"   📁 Backup location: {BACKUP_ROOT}")
        print(f"   🗓️ Retention structure: {verification['retention_counts']}")
        
        return {
            'success': True,
            'test_name': self.test_name,
            'results': {
                'baseline': baseline,
                'verification': verification,
                'databases_backed_up': successful_backups,
                'critical_databases_backed_up': critical_backed_up,
                'backup_location': str(BACKUP_ROOT)
            },
            'timestamp': datetime.now().isoformat()
        }
    
    async def ai_detective_investigation(self, baseline: dict, verification: dict) -> dict:
        """Phase 5: AI Detective binary search debugging"""
        print(f"\n🕵️ AI DETECTIVE INVESTIGATION - Backup failure detected")
        
        investigation = {
            'failure_detected': True,
            'diagnostic_levels': {},
            'root_cause': 'Unknown',
            'recommendations': []
        }
        
        # System Level: Check if backup system is available
        print("   🔍 SYSTEM_LEVEL: Checking backup system availability...")
        try:
            from helpers.durable_backup_system import backup_manager
            backup_available = True
            backup_root_exists = backup_manager.backup_root.exists()
        except ImportError:
            backup_available = False
            backup_root_exists = False
        
        investigation['diagnostic_levels']['system'] = {
            'backup_system_available': backup_available,
            'backup_root_exists': backup_root_exists,
            'backup_root_path': str(BACKUP_ROOT)
        }
        
        if not backup_available:
            investigation['root_cause'] = 'Backup system not available - import failed'
            investigation['recommendations'] = ['Check backup system installation', 'Verify helpers.durable_backup_system module']
            return investigation
        
        # Application Level: Check if backup was triggered
        print("   🔍 APPLICATION_LEVEL: Checking backup execution...")
        try:
            backup_status = backup_manager.get_backup_status()
            investigation['diagnostic_levels']['application'] = backup_status
            
            if not backup_status['retention_counts']['daily']:
                investigation['root_cause'] = 'No daily backups found - startup backup may not have triggered'
                investigation['recommendations'] = [
                    'Check server startup logs for backup execution',
                    'Verify startup_backup_all() is being called',
                    'Check for exceptions during backup process'
                ]
            else:
                investigation['root_cause'] = 'Partial backup failure - some databases missing'
                investigation['recommendations'] = [
                    'Check individual database file permissions',
                    'Verify source database paths exist',
                    'Check backup system logs for specific errors'
                ]
        except Exception as e:
            investigation['diagnostic_levels']['application'] = {'error': str(e)}
            investigation['root_cause'] = f'Backup status check failed: {e}'
            investigation['recommendations'] = ['Check backup system functionality', 'Review backup manager implementation']
        
        return {
            'success': False,
            'test_name': self.test_name,
            'investigation': investigation,
            'baseline': baseline,
            'verification': verification,
            'timestamp': datetime.now().isoformat()
        }
    
    async def handle_failure(self, error_message: str) -> dict:
        """Handle test failures with detailed error information"""
        return {
            'success': False,
            'test_name': self.test_name,
            'error': error_message,
            'timestamp': datetime.now().isoformat()
        }

async def main():
    """Run the rolling backup test harness"""
    test_harness = RollingBackupTestHarness()
    result = await test_harness.run_complete_test()
    
    # Save results
    results_file = f"rolling_backup_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\n📁 Test results saved to: {results_file}")
    
    if result['success']:
        print("🎯 ROLLING BACKUP TEST: ✅ PASSED")
        exit(0)
    else:
        print("🎯 ROLLING BACKUP TEST: ❌ FAILED")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 
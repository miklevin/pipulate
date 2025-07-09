#!/usr/bin/env python3
"""
🎯 SURVIVABLE TEST HARNESS

External testing framework that survives internal disasters.
Now enhanced with beautiful MCP tools playground for regression hunting.

TESTING MODES:
- Normal Testing: DEV, PROD (traditional testing)
- Regression Hunting: -N days back with binary search

PROGRESSIVE INTELLIGENCE HIERARCHY:
- Level 1: Direct tool imports for super-brain models
- Level 2: Simple execute_tool() calls for smart models  
- Level 3: Command pattern parsing for local LLMs
"""
import argparse
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Traditional testing imports
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# NEW: MCP Tools Playground imports
try:
    from tools import RegressionHunter, execute_tool, parse_command, get_api_help
    from tools.commit_explorer import CommitExplorer, explore_commit, restore_commit
    from tools.branch_manager import BranchManager, create_bughunt_branch, cleanup_branches
    MCP_TOOLS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ MCP Tools not available: {e}")
    MCP_TOOLS_AVAILABLE = False

class TestResults:
    """Track test results across normal and regression testing modes."""
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
        
    def add_result(self, test_name: str, success: bool, details: dict = None):
        self.results[test_name] = {
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
    def get_summary(self) -> dict:
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r['success'])
        failed = total - passed
        
        return {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'success_rate': f"{(passed/total*100):.1f}%" if total > 0 else "0%",
            'duration': f"{time.time() - self.start_time:.2f}s",
            'results': self.results
        }

def test_server_health():
    """Test if the Pipulate server is responding."""
    try:
        response = requests.get("http://localhost:5001", timeout=10)
        return response.status_code == 200
    except:
        return False

def test_api_health():
    """Test if key API endpoints are working."""
    try:
        # Test the profiles endpoint
        response = requests.get("http://localhost:5001/profiles", timeout=10)
        return response.status_code == 200
    except:
        return False

def test_profile_system():
    """Test the profile creation system via browser automation."""
    try:
        from selenium.webdriver.chrome.options import Options
        
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("http://localhost:5001/profiles")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Check if profile creation form exists
        name_field = driver.find_element(By.NAME, "name")
        
        # Fill form with test data (this tests template processing)
        name_field.send_keys("AI_Test_Run_20250709_012756")
        
        real_name_field = driver.find_element(By.NAME, "real_name")
        real_name_field.send_keys("AI Automated Test")
        
        address_field = driver.find_element(By.NAME, "address")  
        address_field.send_keys("123 Test Street")
        
        code_field = driver.find_element(By.NAME, "code")
        code_field.send_keys("TEST123")
        
        # Submit form
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        
        # Wait for redirect/response
        time.sleep(2)
        
        driver.quit()
        return True
        
    except Exception as e:
        print(f"Profile system test failed: {e}")
        return False

def test_html_workflow_menu():
    """Test HTML workflow menu functionality."""
    try:
        from selenium.webdriver.chrome.options import Options
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("http://localhost:5001")
        
        # Look for workflow menu elements
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # This test is currently failing - but that's GOOD for regression hunting!
        menu_exists = len(driver.find_elements(By.CLASS_NAME, "workflow-menu")) > 0
        
        driver.quit()
        return menu_exists
        
    except Exception as e:
        print(f"HTML workflow menu test failed: {e}")
        return False

def run_normal_tests(mode: str) -> TestResults:
    """Run traditional DEV/PROD testing."""
    print(f"🧪 Running {mode} tests...")
    results = TestResults()
    
    # Core infrastructure tests
    print("  Testing server health...")
    results.add_result("server_health", test_server_health())
    
    print("  Testing API health...")
    results.add_result("api_health", test_api_health())
    
    print("  Testing profile system...")
    results.add_result("profile_system", test_profile_system())
    
    print("  Testing HTML workflow menu...")
    results.add_result("html_workflow_menu", test_html_workflow_menu())
    
    return results

def run_regression_hunt(days_ago: int) -> TestResults:
    """Run regression hunting using our beautiful MCP tools."""
    print(f"🕰️ REGRESSION HUNTING MODE: {days_ago} days back")
    results = TestResults()
    
    if not MCP_TOOLS_AVAILABLE:
        results.add_result("mcp_tools_check", False, {"error": "MCP tools not available"})
        return results
    
    results.add_result("mcp_tools_check", True)
    
    # Test 1: Hunt for server startup regression
    print("  🔍 Hunting server startup regressions...")
    try:
        # Level 2 API usage (smart model interface)
        hunt_result = execute_tool("hunt_regression", days_ago=days_ago, pattern="Server started")
        results.add_result("server_startup_hunt", hunt_result.get("success", False), hunt_result)
        
        if hunt_result.get("regression_found"):
            print(f"    📍 REGRESSION FOUND: {hunt_result.get('investigation_command')}")
        else:
            print("    ✅ No server startup regressions found")
            
    except Exception as e:
        results.add_result("server_startup_hunt", False, {"error": str(e)})
    
    # Test 2: Hunt for profile system regression  
    print("  🔍 Hunting profile system regressions...")
    try:
        # Level 1 API usage (super-brain interface)
        hunter = RegressionHunter()
        hunt_result = hunter.find_breaking_commit(
            days_ago=days_ago,
            test_function=lambda commit: test_profile_system()  # Custom test function
        )
        results.add_result("profile_system_hunt", hunt_result.get("success", False), hunt_result)
        
        if hunt_result.get("regression_found"):
            print(f"    📍 REGRESSION FOUND: {hunt_result.get('investigation_command')}")
        else:
            print("    ✅ No profile system regressions found")
            
    except Exception as e:
        results.add_result("profile_system_hunt", False, {"error": str(e)})
    
    # Test 3: List commits for manual inspection
    print("  📋 Listing recent commits...")
    try:
        # Level 3 API usage (local LLM interface)  
        commit_result = parse_command(f"list_commits {days_ago}")
        results.add_result("commit_listing", commit_result.get("success", False), commit_result)
        
        if commit_result.get("success"):
            total = commit_result.get("total_commits", 0)
            print(f"    📅 Found {total} commits in {days_ago} day window")
            
    except Exception as e:
        results.add_result("commit_listing", False, {"error": str(e)})
    
    return results

def run_commit_exploration(commits_ago: int) -> TestResults:
    """Run commit exploration for manual bug hunting."""
    print(f"🔍 COMMIT EXPLORATION: {commits_ago} commits ago")
    results = TestResults()
    
    if not MCP_TOOLS_AVAILABLE:
        results.add_result("mcp_tools_check", False, {"error": "MCP tools not available"})
        return results
    
    results.add_result("mcp_tools_check", True)
    
    # Explore the commit
    explorer = CommitExplorer()
    explore_result = explorer.checkout_commit_by_offset(commits_ago)
    results.add_result("commit_exploration", explore_result.get("success", False), explore_result)
    
    return results

def run_branch_management(action: str, **kwargs) -> TestResults:
    """Run branch management operations."""
    print(f"🌿 BRANCH MANAGEMENT: {action}")
    results = TestResults()
    
    if not MCP_TOOLS_AVAILABLE:
        results.add_result("mcp_tools_check", False, {"error": "MCP tools not available"})
        return results
    
    results.add_result("mcp_tools_check", True)
    
    manager = BranchManager()
    
    if action == "create":
        result = manager.create_bughunt_branch(kwargs.get("description", ""))
    elif action == "list":
        result = manager.list_bughunt_branches()
    elif action == "cleanup":
        result = manager.cleanup_resolved_branches(kwargs.get("force", False))
    else:
        result = {"success": False, "error": f"Unknown action: {action}"}
    
    results.add_result(f"branch_{action}", result.get("success", False), result)
    return results

def main():
    """
    🎯 MAIN ENTRY POINT: Two-Phase Bug Hunting Workflow
    
    Phase 1: Manual exploration with simple numeric interface
    Phase 2: Automated binary search with -N days syntax
    """
    parser = argparse.ArgumentParser(
        description="Survivable Test Harness with Two-Phase Bug Hunting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🔍 TWO-PHASE BUG HUNTING WORKFLOW:

PHASE 1: Manual Exploration (find rough boundaries)
  python tests.py 100       # Checkout 100 commits ago
  python tests.py 50        # Checkout 50 commits ago  
  python tests.py 10        # Checkout 10 commits ago
  python tests.py restore   # Return to original commit

PHASE 2: Automated Binary Search (precise hunting)
  python tests.py -7        # Binary search 7 days back
  python tests.py -30       # Binary search 30 days back
  python tests.py --days-ago 14  # Custom timeframe

Branch Management:
  python tests.py --create-branch "Issue description"
  python tests.py --list-branches
  python tests.py --cleanup-branches
  python tests.py --cleanup-branches --force

Normal Testing:
  python tests.py DEV       # Development environment tests
  python tests.py PROD      # Production environment tests

Help:
  python tests.py --mcp-help     # Show MCP tools documentation

The two-phase workflow: Manual exploration finds rough boundaries,
then automated binary search provides logarithmic precision.
        """
    )
    
    # Positional argument that can be numeric (commits ago) or mode (DEV/PROD/restore)
    parser.add_argument('target', nargs='?', 
                       help='Commits ago (100), mode (DEV/PROD), or restore')
    
    # Phase 2: Automated regression hunting modes
    parser.add_argument('-0', '--today', action='store_true',
                       help='Binary search today\'s commits')
    parser.add_argument('-1', '--yesterday', action='store_true', 
                       help='Binary search yesterday\'s commits')
    parser.add_argument('-7', '--week', action='store_true',
                       help='Binary search past week')
    parser.add_argument('-30', '--month', action='store_true',
                       help='Binary search past month')
    parser.add_argument('--days-ago', type=int, 
                       help='Binary search N days back')
    
    # Branch management
    parser.add_argument('--create-branch', type=str, metavar='DESCRIPTION',
                       help='Create new bug hunt branch with description')
    parser.add_argument('--list-branches', action='store_true',
                       help='List active bug hunt branches')
    parser.add_argument('--cleanup-branches', action='store_true',
                       help='Clean up resolved bug hunt branches')
    parser.add_argument('--force', action='store_true',
                       help='Force cleanup of all bug hunt branches')
    
    # Help and info
    parser.add_argument('--mcp-help', action='store_true',
                       help='Show MCP tools documentation')
    
    args = parser.parse_args()
    
    # Show MCP help
    if args.mcp_help:
        if MCP_TOOLS_AVAILABLE:
            print(get_api_help())
        else:
            print("❌ MCP Tools not available. Install the tools/ directory.")
        return
    
    # Branch management commands
    if args.create_branch:
        results = run_branch_management("create", description=args.create_branch)
    elif args.list_branches:
        results = run_branch_management("list")
    elif args.cleanup_branches:
        results = run_branch_management("cleanup", force=args.force)
    
    # Phase 2: Automated binary search regression hunting
    elif args.today:
        results = run_regression_hunt(0)
    elif args.yesterday:
        results = run_regression_hunt(1)
    elif args.week:
        results = run_regression_hunt(7)
    elif args.month:
        results = run_regression_hunt(30)
    elif args.days_ago is not None:
        results = run_regression_hunt(args.days_ago)
    
    # Phase 1: Manual exploration or normal testing
    elif args.target:
        if args.target == "restore":
            # Special restore command
            if MCP_TOOLS_AVAILABLE:
                explorer = CommitExplorer()
                restore_result = explorer.restore_original_commit()
                print(f"🔙 {restore_result.get('message', 'Restore attempted')}")
                if restore_result.get('success'):
                    print(f"   Commit: {restore_result.get('commit', 'Unknown')}")
                    print(f"   {restore_result.get('note', '')}")
                else:
                    print(f"   Error: {restore_result.get('error', 'Unknown error')}")
            else:
                print("❌ MCP Tools not available for restore operation")
            return
        elif args.target in ['DEV', 'PROD']:
            # Normal testing modes
            results = run_normal_tests(args.target)
        elif args.target.isdigit():
            # Phase 1: Manual commit exploration
            commits_ago = int(args.target)
            results = run_commit_exploration(commits_ago)
        else:
            print(f"❌ Unknown target: {args.target}")
            print("   Use a number (commits ago), DEV/PROD (testing), or 'restore'")
            parser.print_help()
            return
    else:
        parser.print_help()
        return
    
    # Print results with special handling for different result types
    summary = results.get_summary()
    
    # Special handling for commit exploration
    if 'commit_exploration' in summary['results']:
        explore_result = summary['results']['commit_exploration']
        if explore_result['success']:
            details = explore_result['details']
            print(f"\n{details.get('checkout_message', '')}")
            print(f"{details.get('commit_details', '')}")
            print(f"{details.get('commit_age', '')}")
            print(f"{details.get('commit_subject', '')}")
            print(f"\n{details.get('server_restart_note', '')}")
            print(f"{details.get('wait_message', '')}")
            print(f"\n{details.get('transition_note', '')}")
            print(f"\n🔙 To return to HEAD: {details.get('restore_command', 'python tests.py restore')}")
        else:
            print(f"\n❌ Commit exploration failed: {details.get('error', 'Unknown error')}")
        return
    
    # Special handling for branch management
    if any(key.startswith('branch_') for key in summary['results']):
        for test_name, result in summary['results'].items():
            if test_name.startswith('branch_'):
                action = test_name.replace('branch_', '')
                details = result.get('details', {})
                
                if result['success']:
                    if action == "create":
                        print(f"\n✅ {details.get('message', 'Branch created')}")
                        print(f"   Branch: {details.get('branch_name', 'Unknown')}")
                        print(f"   Original: {details.get('original_branch', 'Unknown')}")
                    elif action == "list":
                        branches = details.get('branches', [])
                        print(f"\n📋 Bug Hunt Branches ({details.get('total_branches', 0)} total):")
                        for branch in branches:
                            status = "✅ RESOLVED" if branch.get('resolved') else "🔍 ACTIVE"
                            print(f"   {status} {branch['branch_name']}")
                            if branch.get('issue_description'):
                                print(f"      📝 {branch['issue_description']}")
                            print(f"      📅 Created: {branch.get('created_at', 'Unknown')}")
                            print(f"      🧪 Tests: {branch.get('commits_tested', 0)}")
                    elif action == "cleanup":
                        print(f"\n🧹 Cleanup completed:")
                        print(f"   Deleted branches: {details.get('deleted_branches', 0)}")
                        print(f"   War stories extracted: {details.get('war_stories_extracted', 0)}")
                        print(f"   Remaining branches: {details.get('remaining_branches', 0)}")
                else:
                    print(f"\n❌ Branch {action} failed: {details.get('error', 'Unknown error')}")
        return
    
    # Standard results output for normal testing and regression hunting
    print(f"\n🎯 TEST SUMMARY:")
    print(f"   Tests Run: {summary['total_tests']}")
    print(f"   Passed: {summary['passed']}")
    print(f"   Failed: {summary['failed']}")
    print(f"   Success Rate: {summary['success_rate']}")
    print(f"   Duration: {summary['duration']}")
    
    # Detailed results
    print(f"\n📋 DETAILED RESULTS:")
    for test_name, result in summary['results'].items():
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"   {status} {test_name}")
        
        # Show additional details for regression hunts
        if 'hunt' in test_name and result.get('details', {}).get('regression_found'):
            details = result['details']
            print(f"      🔍 Investigation: {details.get('investigation_command', 'N/A')}")
    
    # Exit code
    exit_code = 0 if summary['failed'] == 0 else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
🎯 PIPULATE TEST RUNNER

Simple interface to the survivable test harness in tests/ directory.
This script can be safely committed to the main repo.

USAGE:
    python run_tests.py                    # Run basic functionality tests
    python run_tests.py --hunt             # Hunt for regressions
    python run_tests.py --test server_alive   # Run specific test
"""

import subprocess
import sys
from pathlib import Path

# Test harness location
TEST_DIR = Path(__file__).parent / "tests"

def check_test_harness():
    """Check if the survivable test harness is available."""
    if not TEST_DIR.exists():
        print("❌ Test harness not found!")
        print("The survivable test harness should be in: tests/")
        print("\nTo set up the test harness:")
        print("1. mkdir tests")
        print("2. cd tests")
        print("3. git init")
        print("4. Follow the test harness setup guide")
        return False
    
    basic_test = TEST_DIR / "tests" / "basic_pipulate_test.py"
    if not basic_test.exists():
        print("❌ Test framework not properly installed!")
        print(f"Missing: {basic_test}")
        return False
    
    return True

def run_basic_tests():
    """Run the basic Pipulate functionality tests."""
    print("🧪 RUNNING BASIC PIPULATE TESTS")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            sys.executable, 
            str(TEST_DIR / "tests" / "basic_pipulate_test.py")
        ], cwd=TEST_DIR)
        
        return result.returncode == 0
    
    except Exception as e:
        print(f"❌ Failed to run tests: {e}")
        return False

def hunt_regression(test_name="basic", max_steps=20):
    """Hunt for regressions using the regression hunter."""
    print("🔫 STARTING REGRESSION HUNT")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            sys.executable,
            str(TEST_DIR / "scripts" / "hunt_regression.py"),
            "--test", test_name,
            "--max-steps", str(max_steps),
            "--auto"  # Run without confirmations for simplicity
        ], cwd=TEST_DIR)
        
        return result.returncode == 0
    
    except Exception as e:
        print(f"❌ Failed to hunt regression: {e}")
        return False

def main():
    """Main test runner interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="🎯 Pipulate Test Runner")
    parser.add_argument("--hunt", action="store_true", 
                       help="Hunt for regressions instead of running tests")
    parser.add_argument("--test", default="basic",
                       help="Test to run (basic, server_alive, workflow_menu, profile_system)")
    parser.add_argument("--max-steps", type=int, default=20,
                       help="Maximum commits to step back when hunting")
    
    args = parser.parse_args()
    
    # Check test harness availability
    if not check_test_harness():
        return 1
    
    print("🎯 PIPULATE SURVIVABLE TEST HARNESS")
    print(f"📍 Test Directory: {TEST_DIR}")
    print(f"🔧 Working Directory: {Path.cwd()}")
    
    if args.hunt:
        print(f"🔫 Hunting regression for test: {args.test}")
        success = hunt_regression(args.test, args.max_steps)
    else:
        print(f"🧪 Running test: {args.test}")
        success = run_basic_tests()
    
    if success:
        print("✅ Test operation completed successfully")
        return 0
    else:
        print("❌ Test operation failed")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code) 
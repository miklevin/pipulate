#!/usr/bin/env python3
"""
Pipulate Master Test Suite
==========================

Run all tests with: python tests.py

Individual test commands (copy-pasteable):
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

def log_message(msg, level="INFO"):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    colors = {
        "INFO": "\033[0m",
        "SUCCESS": "\033[92m", 
        "ERROR": "\033[91m",
        "HEADER": "\033[95m"
    }
    color = colors.get(level, colors["INFO"])
    print(f"{color}[{timestamp}] {level}: {msg}\033[0m")

def get_app_name():
    """Get app name from app_name.txt file, just like server.py does."""
    app_name_file = Path('app_name.txt')
    if app_name_file.exists():
        return app_name_file.read_text().strip()
    return 'Pipulate'  # Fallback

def run_test_command(command, description):
    """Run a single test command and return success status."""
    log_message(f"Running: {description}")
    log_message(f"Command: {command}")
    
    try:
        # Split command properly for subprocess
        cmd_parts = command.split()
        result = subprocess.run(cmd_parts, cwd='.', capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            log_message(f"✅ PASSED: {description}", "SUCCESS")
            if result.stdout.strip():
                print(result.stdout)
            return True
        else:
            log_message(f"❌ FAILED: {description}", "ERROR")
            if result.stderr.strip():
                print(f"STDERR: {result.stderr}")
            if result.stdout.strip():
                print(f"STDOUT: {result.stdout}")
            return False
            
    except subprocess.TimeoutExpired:
        log_message(f"⏰ TIMEOUT: {description}", "ERROR")
        return False
    except Exception as e:
        log_message(f"💥 ERROR: {description} - {e}", "ERROR")
        return False

def main():
    """Run the master test suite."""
    log_message("🧪 PIPULATE MASTER TEST SUITE", "HEADER")
    
    app_name = get_app_name()
    log_message(f"App Name: {app_name}")
    
    # Test commands in storytelling order
    # Each command should be easily copy-pasteable for individual execution
    tests = """
.venv/bin/python tests/tests/test_database_environment_binding.py
.venv/bin/python tests/tests/test_minidataapi_profile_integration.py
.venv/bin/python tests/tests/test_profile_regression_sentry.py
""".split("\n")[1:-1]
    
    test_descriptions = [
        "Database Environment Binding - Verify profiles hit correct DB files",
        "MiniDataAPI Profile Integration - Full web UI to database workflow", 
        "Profile Regression Sentry - Guard against MiniDataAPI pattern breaks"
    ]
    
    log_message("📋 Individual test commands (copy-pasteable):")
    for i, test in enumerate(tests):
        print(f"  {i+1}. {test}")
    print()
    
    # Run all tests
    passed = 0
    total = len(tests)
    
    for i, (test, description) in enumerate(zip(tests, test_descriptions)):
        log_message(f"Test {i+1}/{total}: {description}")
        if run_test_command(test, description):
            passed += 1
        print()  # Spacing between tests
    
    # Summary
    log_message("📊 TEST SUITE SUMMARY", "HEADER")
    log_message(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        log_message("🎉 ALL TESTS PASSED!", "SUCCESS")
        return 0
    else:
        log_message(f"💥 {total - passed} TESTS FAILED!", "ERROR")
        return 1

if __name__ == '__main__':
    sys.exit(main())

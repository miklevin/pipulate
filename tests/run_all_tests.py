#!/usr/bin/env python3
"""
🎯 Pipulate Deterministic Test Suite Runner

REGRESSION PROTECTION SYSTEM:
- Run all deterministic tests in sequence
- Collect and verify test results
- Prevent regression on critical features
- Generate test reports for transparency

CURRENT DETERMINISTIC TESTS:
1. Conversation Persistence - Cross-restart memory
2. Rolling Backup System - Son/father/grandfather protection

SUCCESS CRITERIA: All tests must pass for production deployment
"""

import subprocess
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# Test registry - add new tests here
DETERMINISTIC_TESTS = [
    {
        "name": "Conversation Persistence",
        "file": "conversation_persistence_test_final.py",
        "description": "Verifies conversation history survives server restarts",
        "critical": True
    },
    {
        "name": "Rolling Backup System", 
        "file": "rolling_backup_test_deterministic.py",
        "description": "Validates son/father/grandfather backup protection",
        "critical": True
    }
]

def run_test(test_config):
    """Execute a single deterministic test and collect results."""
    print(f"\n🧪 Running: {test_config['name']}")
    print(f"📄 File: {test_config['file']}")
    print(f"📝 Description: {test_config['description']}")
    print("-" * 60)
    
    start_time = time.time()
    
    try:
        # Execute the test script
        result = subprocess.run(
            [sys.executable, test_config['file']],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout per test
        )
        
        execution_time = time.time() - start_time
        
        # Parse test result
        success = result.returncode == 0
        
        test_result = {
            "name": test_config['name'],
            "file": test_config['file'],
            "description": test_config['description'],
            "critical": test_config['critical'],
            "success": success,
            "execution_time": execution_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
            "timestamp": datetime.now().isoformat()
        }
        
        # Display result
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"\n{status} - {test_config['name']} ({execution_time:.2f}s)")
        
        if not success:
            print(f"❌ Error output:")
            print(result.stderr)
            
        return test_result
        
    except subprocess.TimeoutExpired:
        test_result = {
            "name": test_config['name'],
            "file": test_config['file'],
            "description": test_config['description'],
            "critical": test_config['critical'],
            "success": False,
            "execution_time": 120.0,
            "stdout": "",
            "stderr": "Test timed out after 120 seconds",
            "return_code": -1,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"❌ TIMEOUT - {test_config['name']} (120s)")
        return test_result
        
    except Exception as e:
        test_result = {
            "name": test_config['name'],
            "file": test_config['file'],
            "description": test_config['description'],
            "critical": test_config['critical'],
            "success": False,
            "execution_time": time.time() - start_time,
            "stdout": "",
            "stderr": f"Test execution failed: {str(e)}",
            "return_code": -2,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"❌ EXCEPTION - {test_config['name']}: {e}")
        return test_result

def main():
    """Run the complete deterministic test suite."""
    start_time = datetime.now()
    results = []
    
    print("🎯 PIPULATE DETERMINISTIC TEST SUITE")
    print("=" * 60)
    print(f"📅 Test run started: {start_time}")
    print(f"🧪 Total tests: {len(DETERMINISTIC_TESTS)}")
    
    # Execute all tests
    for test_config in DETERMINISTIC_TESTS:
        test_result = run_test(test_config)
        results.append(test_result)
    
    # Generate summary
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])
    failed_tests = total_tests - passed_tests
    critical_failures = sum(1 for r in results if not r['success'] and r['critical'])
    
    total_time = time.time() - start_time.timestamp()
    
    print("\n" + "=" * 60)
    print("🎯 TEST SUITE SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {passed_tests}/{total_tests}")
    print(f"❌ Failed: {failed_tests}/{total_tests}")
    print(f"🚨 Critical Failures: {critical_failures}")
    print(f"⏱️ Total Time: {total_time:.2f}s")
    
    # Overall result
    overall_success = failed_tests == 0
    overall_status = "🎉 ALL TESTS PASSED" if overall_success else "🚨 TEST FAILURES DETECTED"
    print(f"\n{overall_status}")
    
    # Critical failure warning
    if critical_failures > 0:
        print("🚨 CRITICAL FAILURES DETECTED - PRODUCTION DEPLOYMENT BLOCKED")
    
    # Generate report
    report = {
        "test_run_summary": {
            "timestamp": start_time.isoformat(),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "critical_failures": critical_failures,
            "total_execution_time": total_time,
            "overall_success": overall_success
        },
        "test_results": results
    }
    
    # Save report to file
    report_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"📊 Detailed report saved: {report_file}")
    
    # Exit with error code if any tests failed
    if not overall_success:
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()

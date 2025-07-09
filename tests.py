#!/usr/bin/env python3
"""
🎯 PIPULATE SOPHISTICATED TEST INTERFACE

This file delegates to the sophisticated testing system in tests/ directory.
The oversimplified version has been replaced with proper browser automation tests.

USAGE:
    python tests.py DEV    # Run in development mode
    python tests.py PROD   # Run in production mode  
    python tests.py        # Defaults to DEV mode

SOPHISTICATION RESTORED:
- ✅ Full Selenium browser automation via /browser_automation system
- ✅ Independent git repository for regression hunting (/tests)
- ✅ Screenshot capture and results framework
- ✅ Multiple test types (basic, advanced, regression hunting)
- ✅ Environment switching (DEV/PROD) with real database verification
"""

import sys
import subprocess
import os
from pathlib import Path

# CRITICAL: Always use .venv/bin/python for Nix environment
# When running from tests/ subdirectory, need to go up one level
PYTHON_EXECUTABLE = "../.venv/bin/python"

class SophisticatedTestInterface:
    """Interface to the sophisticated testing system."""
    
    def __init__(self):
        self.tests_dir = Path("tests")
        self.mode = "DEV"  # Default to safe mode
        
    def verify_sophisticated_system(self) -> bool:
        """Verify the sophisticated test system is available."""
        required_files = [
            "tests/tests/basic_pipulate_test.py",
            "tests/tests/test_database_environment_binding.py", 
            "tests/config/test_config.py",
            "tests/scripts/hunt_regression.py"
        ]
        
        missing = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing.append(file_path)
        
        if missing:
            print("❌ SOPHISTICATED TEST SYSTEM INCOMPLETE:")
            for file in missing:
                print(f"   Missing: {file}")
            return False
            
        print("✅ SOPHISTICATED TEST SYSTEM VERIFIED")
        return True
    
    def run_basic_tests(self) -> bool:
        """Run basic Pipulate functionality tests."""
        print(f"🧪 RUNNING BASIC TESTS (Mode: {self.mode})")
        print("=" * 60)
        
        cmd = [
            PYTHON_EXECUTABLE, 
            "tests/basic_pipulate_test.py"
        ]
        
        try:
            result = subprocess.run(cmd, cwd=self.tests_dir, capture_output=True, text=True)
            
            print("STDOUT:")
            print(result.stdout)
            
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"❌ Failed to run basic tests: {e}")
            return False
    
    def run_environment_binding_test(self) -> bool:
        """Run database environment binding test with browser automation."""
        print(f"🧪 RUNNING DATABASE ENVIRONMENT BINDING TEST (Mode: {self.mode})")
        print("=" * 60)
        
        cmd = [
            PYTHON_EXECUTABLE, 
            "tests/test_database_environment_binding.py",
            self.mode,
            "--headless=false"  # Visible for confidence building
        ]
        
        try:
            result = subprocess.run(cmd, cwd=self.tests_dir, capture_output=True, text=True)
            
            print("STDOUT:")
            print(result.stdout)
            
            if result.stderr:
                print("STDERR:")  
                print(result.stderr)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"❌ Failed to run environment binding test: {e}")
            return False
    
    def run_profile_integration_test(self) -> bool:
        """Run MiniDataAPI profile integration test."""
        print(f"🧪 RUNNING MINIDATAAPI PROFILE INTEGRATION TEST (Mode: {self.mode})")
        print("=" * 60)
        
        cmd = [
            PYTHON_EXECUTABLE,
            "tests/test_minidataapi_profile_integration.py", 
            self.mode,
            "--headless=false"
        ]
        
        try:
            result = subprocess.run(cmd, cwd=self.tests_dir, capture_output=True, text=True)
            
            print("STDOUT:")
            print(result.stdout)
            
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"❌ Failed to run profile integration test: {e}")
            return False
    
    def run_regression_sentry_test(self) -> bool:
        """Run regression sentry test."""
        print(f"🧪 RUNNING PROFILE REGRESSION SENTRY TEST (Mode: {self.mode})")
        print("=" * 60)
        
        cmd = [
            PYTHON_EXECUTABLE,
            "tests/test_profile_regression_sentry.py",
            self.mode, 
            "--headless=false"
        ]
        
        try:
            result = subprocess.run(cmd, cwd=self.tests_dir, capture_output=True, text=True)
            
            print("STDOUT:")
            print(result.stdout)
            
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"❌ Failed to run regression sentry test: {e}")
            return False
    
    def run_all_tests(self) -> dict:
        """Run the complete sophisticated test suite."""
        print("🚀 PIPULATE SOPHISTICATED TEST SUITE")
        print("=" * 60)
        print(f"Mode: {self.mode}")
        print(f"Browser Automation: VISIBLE (headless=false) for confidence building")
        print("Test System: SOPHISTICATED with Selenium automation")
        print("=" * 60)
        
        if not self.verify_sophisticated_system():
            return {"success": False, "error": "Sophisticated test system not available"}
        
        results = {
            "mode": self.mode,
            "tests": {},
            "summary": {"passed": 0, "failed": 0, "total": 0}
        }
        
        # Define test suite
        test_suite = [
            ("basic_tests", "Basic Pipulate Functionality", self.run_basic_tests),
            ("environment_binding", "Database Environment Binding", self.run_environment_binding_test),  
            ("profile_integration", "MiniDataAPI Profile Integration", self.run_profile_integration_test),
            ("regression_sentry", "Profile Regression Sentry", self.run_regression_sentry_test)
        ]
        
        # Execute tests
        for test_id, description, test_func in test_suite:
            print(f"\n{'='*20} {description} {'='*20}")
            
            try:
                success = test_func()
                results["tests"][test_id] = {
                    "description": description,
                    "success": success
                }
                
                if success:
                    results["summary"]["passed"] += 1
                    print(f"✅ {description} PASSED")
                else:
                    results["summary"]["failed"] += 1
                    print(f"❌ {description} FAILED")
                    
            except Exception as e:
                results["tests"][test_id] = {
                    "description": description,
                    "success": False,
                    "error": str(e)
                }
                results["summary"]["failed"] += 1
                print(f"💥 {description} CRASHED: {e}")
            
            results["summary"]["total"] += 1
        
        # Final summary
        print("\n" + "=" * 60)
        print("🎯 SOPHISTICATED TEST SUITE SUMMARY")
        print(f"✅ Passed: {results['summary']['passed']}")
        print(f"❌ Failed: {results['summary']['failed']}")
        print(f"📊 Total: {results['summary']['total']}")
        print(f"📋 Mode: {results['mode']}")
        
        success_rate = (results['summary']['passed'] / results['summary']['total'] * 100) if results['summary']['total'] > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if results['summary']['failed'] == 0:
            print("🎉 ALL TESTS PASSED!")
            results["overall_success"] = True
        else:
            print("⚠️  SOME TESTS FAILED")
            results["overall_success"] = False
        
        return results

def main():
    """Main entry point for sophisticated test interface."""
    
    # Parse command line arguments
    mode = "DEV"  # Default to safe development mode
    if len(sys.argv) > 1:
        mode = sys.argv[1].upper()
        if mode not in ["DEV", "PROD"]:
            print(f"❌ Invalid mode: {mode}. Use DEV or PROD.")
            return 1
    
    # Initialize and run tests
    test_interface = SophisticatedTestInterface()
    test_interface.mode = mode
    
    # Run the sophisticated test suite
    results = test_interface.run_all_tests()
    
    # Return appropriate exit code
    return 0 if results.get("overall_success", False) else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

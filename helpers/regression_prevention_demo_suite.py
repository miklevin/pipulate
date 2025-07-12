#!/usr/bin/env python3
"""
🎯 REGRESSION PREVENTION DEMO SUITE
The Most Fun MCP Tool Regression Prevention System Ever Built!

This suite tests:
1. Endpoint message functionality (our golden working state)
2. Core MCP tools functionality
3. Browser automation capabilities
4. UI flash elements
5. Keychain persistence
6. Critical server functionality

Starting from the YELLOWBRICKROAD tagged commit (8249072)
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
from datetime import datetime

class RegressionPreventionDemo:
    def __init__(self):
        self.results = []
        self.test_count = 0
        self.pass_count = 0
        self.fail_count = 0
        self.start_time = time.time()
        self.server_url = "http://localhost:5001"
        
    def log_result(self, test_name: str, status: str, details: str = "", data: Any = None):
        """Log test result with fun emojis"""
        emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        self.test_count += 1
        if status == "PASS":
            self.pass_count += 1
        elif status == "FAIL":
            self.fail_count += 1
            
        print(f"{emoji} {test_name}: {status}")
        if details:
            print(f"   📝 {details}")
        print()

    def run_mcp_tool(self, tool_name: str, args: List[str] = None) -> Dict[str, Any]:
        """Run an MCP tool and return results"""
        if args is None:
            args = []
        
        cmd = ["python3", "cli.py", "call", tool_name] + args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Tool execution timed out",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    def test_git_state(self):
        """Test that we're on the correct git commit"""
        try:
            result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
            current_commit = result.stdout.strip()
            
            # Check for yellowbrickroad tag
            tag_result = subprocess.run(["git", "tag", "--points-at", "HEAD"], capture_output=True, text=True)
            has_yellowbrickroad = "yellowbrickroad" in tag_result.stdout
            
            if has_yellowbrickroad:
                self.log_result("Git State Check", "PASS", f"On yellowbrickroad tagged commit: {current_commit[:8]}")
            else:
                self.log_result("Git State Check", "WARN", f"Not on yellowbrickroad tag. Current: {current_commit[:8]}")
                
        except Exception as e:
            self.log_result("Git State Check", "FAIL", f"Git check failed: {e}")

    def test_server_running(self):
        """Test that the server is running and responding"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            if response.status_code == 200:
                self.log_result("Server Health Check", "PASS", "Server is running and responding")
            else:
                self.log_result("Server Health Check", "FAIL", f"Server returned status {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.log_result("Server Health Check", "FAIL", f"Server not responding: {e}")

    def test_endpoint_messages(self):
        """Test that endpoint messages are working (our golden functionality)"""
        try:
            # Check if we can reach the main page
            response = requests.get(self.server_url, timeout=5)
            if response.status_code == 200:
                # Look for JavaScript that handles endpoint messages
                page_content = response.text
                if "tempMessage" in page_content and "msg-list" in page_content:
                    self.log_result("Endpoint Messages Structure", "PASS", "Page contains endpoint message handling code")
                else:
                    self.log_result("Endpoint Messages Structure", "FAIL", "Page missing endpoint message handling")
            else:
                self.log_result("Endpoint Messages Structure", "FAIL", f"Could not load main page: {response.status_code}")
        except Exception as e:
            self.log_result("Endpoint Messages Structure", "FAIL", f"Endpoint message test failed: {e}")

    def test_mcp_tools_basic(self):
        """Test basic MCP tool functionality"""
        # Test cat fact (simple tool)
        result = self.run_mcp_tool("get_cat_fact")
        if result["success"] and "fact" in result["stdout"].lower():
            self.log_result("MCP Tool: Cat Fact", "PASS", "Cat fact tool working")
        else:
            self.log_result("MCP Tool: Cat Fact", "FAIL", f"Cat fact failed: {result['stderr']}")

    def test_mcp_tools_advanced(self):
        """Test advanced MCP tool functionality"""
        # Test pipeline state inspector
        result = self.run_mcp_tool("pipeline_state_inspector")
        if result["success"]:
            self.log_result("MCP Tool: Pipeline State", "PASS", "Pipeline state inspector working")
        else:
            self.log_result("MCP Tool: Pipeline State", "FAIL", f"Pipeline state failed: {result['stderr']}")
        
        # Test UI flash element
        result = self.run_mcp_tool("ui_list_elements")
        if result["success"]:
            self.log_result("MCP Tool: UI Elements", "PASS", "UI element lister working")
        else:
            self.log_result("MCP Tool: UI Elements", "FAIL", f"UI elements failed: {result['stderr']}")

    def test_keychain_functionality(self):
        """Test keychain persistence (critical for AI memory)"""
        test_key = "regression_test_key"
        test_value = "yellowbrickroad_demo_value"
        
        # Set a test value
        result = self.run_mcp_tool("keychain_set", [test_key, test_value])
        if result["success"]:
            # Try to get it back
            result = self.run_mcp_tool("keychain_get", [test_key])
            if result["success"] and test_value in result["stdout"]:
                self.log_result("Keychain Persistence", "PASS", "Keychain set/get working")
                # Clean up
                self.run_mcp_tool("keychain_delete", [test_key])
            else:
                self.log_result("Keychain Persistence", "FAIL", "Keychain get failed")
        else:
            self.log_result("Keychain Persistence", "FAIL", f"Keychain set failed: {result['stderr']}")

    def test_file_operations(self):
        """Test file reading capabilities"""
        # Test reading this file
        result = self.run_mcp_tool("local_llm_read_file", ["--file_path", __file__])
        if result["success"] and "RegressionPreventionDemo" in result["stdout"]:
            self.log_result("File Operations", "PASS", "File reading working")
        else:
            self.log_result("File Operations", "FAIL", f"File reading failed: {result['stderr']}")

    def test_session_hijacking_demo(self):
        """Test the famous session hijacking demo (if available)"""
        result = self.run_mcp_tool("execute_complete_session_hijacking")
        if result["success"]:
            self.log_result("Session Hijacking Demo", "PASS", "Session hijacking demo executed successfully")
        else:
            self.log_result("Session Hijacking Demo", "FAIL", f"Session hijacking failed: {result['stderr']}")

    def generate_report(self):
        """Generate a comprehensive test report"""
        duration = time.time() - self.start_time
        
        print("=" * 60)
        print("🎯 REGRESSION PREVENTION DEMO SUITE REPORT")
        print("=" * 60)
        print(f"📊 Total Tests: {self.test_count}")
        print(f"✅ Passed: {self.pass_count}")
        print(f"❌ Failed: {self.fail_count}")
        print(f"⏱️ Duration: {duration:.2f}s")
        print(f"🏆 Success Rate: {(self.pass_count/self.test_count*100):.1f}%")
        print()
        
        if self.fail_count > 0:
            print("❌ FAILED TESTS:")
            for result in self.results:
                if result["status"] == "FAIL":
                    print(f"  • {result['test']}: {result['details']}")
            print()
        
        # Save detailed report
        report_file = f"regression_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": self.test_count,
                    "passed": self.pass_count,
                    "failed": self.fail_count,
                    "duration": duration,
                    "success_rate": self.pass_count/self.test_count*100
                },
                "results": self.results
            }, f, indent=2)
        
        print(f"📄 Detailed report saved: {report_file}")
        
        if self.fail_count == 0:
            print("🎉 ALL TESTS PASSED! The yellowbrickroad is still golden! 🌟")
        else:
            print(f"⚠️ {self.fail_count} tests failed. Check the report for details.")

    def run_all_tests(self):
        """Run the complete regression prevention demo suite"""
        print("🚀 Starting Regression Prevention Demo Suite...")
        print("🌟 Testing from YELLOWBRICKROAD tagged commit")
        print("=" * 60)
        print()
        
        self.test_git_state()
        self.test_server_running()
        self.test_endpoint_messages()
        self.test_mcp_tools_basic()
        self.test_mcp_tools_advanced()
        self.test_keychain_functionality()
        self.test_file_operations()
        self.test_session_hijacking_demo()
        
        self.generate_report()
        
        return self.fail_count == 0

def main():
    """Run the regression prevention demo suite"""
    demo = RegressionPreventionDemo()
    success = demo.run_all_tests()
    
    if success:
        print("\n🎯 REGRESSION PREVENTION DEMO: SUCCESS!")
        print("🌟 The yellowbrickroad remains golden!")
        sys.exit(0)
    else:
        print("\n❌ REGRESSION PREVENTION DEMO: ISSUES DETECTED!")
        print("🔧 Review the report and fix any regressions.")
        sys.exit(1)

if __name__ == "__main__":
    main()

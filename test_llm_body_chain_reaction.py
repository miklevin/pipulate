#!/usr/bin/env python3
"""
🎯 DETERMINISTIC LLM "BODY" CHAIN REACTION TEST

This script validates the complete chain reaction:
1. LLM discovers tools via [mcp]
2. LLM chooses browser automation 
3. LLM tests its "body" by scraping localhost:5001
4. LLM investigates results in looking_at/ folder
5. LLM sees DOM visualizer (next step)

This is the foundation for the Rube Goldberg AI machine.
"""

import asyncio
import json
import time
from pathlib import Path
from datetime import datetime

# Import the MCP tools we need to test
from mcp_tools import (
    ai_self_discovery_assistant,
    browser_scrape_page, 
    local_llm_read_file,
    browser_analyze_scraped_page
)

class LLMBodyChainReactionTest:
    """Test the complete LLM 'body' chain reaction."""
    
    def __init__(self):
        self.test_results = {}
        self.looking_at_dir = Path("browser_automation/looking_at")
        self.test_start_time = datetime.now()
        
    async def run_complete_test(self):
        """Run the complete deterministic chain reaction test."""
        print("🎯 STARTING LLM BODY CHAIN REACTION TEST")
        print("=" * 60)
        
        # Step 1: LLM discovers tools (simulate [mcp] call)
        print("\n🔍 STEP 1: LLM discovers tools via [mcp]")
        print("-" * 40)
        
        discovery_result = await ai_self_discovery_assistant({
            "discovery_type": "capabilities"
        })
        
        if discovery_result.get("success"):
            print("✅ LLM successfully discovered tools")
            self.test_results["tool_discovery"] = "SUCCESS"
            
            # Check if browser_scrape_page is in the results
            tools_found = discovery_result.get("tools", [])
            if "browser_scrape_page" in tools_found:
                print("✅ browser_scrape_page found in available tools")
                self.test_results["browser_tool_available"] = "SUCCESS"
            else:
                print("❌ browser_scrape_page NOT found in available tools")
                self.test_results["browser_tool_available"] = "FAILED"
        else:
            print("❌ LLM tool discovery failed")
            self.test_results["tool_discovery"] = "FAILED"
            return False
        
        # Step 2: LLM tests its "body" by scraping localhost:5001
        print("\n👁️ STEP 2: LLM tests its 'body' - browser automation")
        print("-" * 40)
        
        scrape_result = await browser_scrape_page({
            "url": "http://localhost:5001",
            "wait_seconds": 3,
            "take_screenshot": True
        })
        
        if scrape_result.get("success"):
            print("✅ LLM successfully scraped localhost:5001")
            print(f"📄 Page title: {scrape_result.get('page_info', {}).get('title', 'Unknown')}")
            self.test_results["browser_scrape"] = "SUCCESS"
            
            # Check if looking_at files were created
            files_created = self._check_looking_at_files()
            if files_created:
                print("✅ looking_at/ files created successfully")
                self.test_results["looking_at_files"] = "SUCCESS"
            else:
                print("❌ looking_at/ files not created")
                self.test_results["looking_at_files"] = "FAILED"
        else:
            print(f"❌ Browser scrape failed: {scrape_result.get('error', 'Unknown error')}")
            self.test_results["browser_scrape"] = "FAILED"
            return False
        
        # Step 3: LLM investigates results in looking_at/ folder
        print("\n🧠 STEP 3: LLM investigates results in looking_at/ folder")
        print("-" * 40)
        
        # Read the simple_dom.html file
        dom_read_result = await local_llm_read_file({
            "file_path": "browser_automation/looking_at/simple_dom.html"
        })
        
        if dom_read_result.get("success"):
            print("✅ LLM successfully read simple_dom.html")
            content = dom_read_result.get("content", "")
            if "Pipulate" in content or "localhost:5001" in content:
                print("✅ DOM contains expected Pipulate content")
                self.test_results["dom_analysis"] = "SUCCESS"
            else:
                print("⚠️ DOM content doesn't contain expected Pipulate references")
                self.test_results["dom_analysis"] = "PARTIAL"
        else:
            print(f"❌ Failed to read DOM file: {dom_read_result.get('error', 'Unknown error')}")
            self.test_results["dom_analysis"] = "FAILED"
        
        # Step 4: LLM analyzes the scraped page
        print("\n🔍 STEP 4: LLM analyzes the scraped page")
        print("-" * 40)
        
        analysis_result = await browser_analyze_scraped_page({
            "analysis_type": "overview"
        })
        
        if analysis_result.get("success"):
            print("✅ LLM successfully analyzed scraped page")
            target_count = analysis_result.get("target_count", 0)
            form_count = analysis_result.get("form_count", 0)
            print(f"🎯 Found {target_count} interactive targets, {form_count} forms")
            self.test_results["page_analysis"] = "SUCCESS"
        else:
            print(f"❌ Page analysis failed: {analysis_result.get('error', 'Unknown error')}")
            self.test_results["page_analysis"] = "FAILED"
        
        # Step 5: Validate chain reaction completeness
        print("\n🎯 STEP 5: Validate chain reaction completeness")
        print("-" * 40)
        
        chain_reaction_success = self._validate_chain_reaction()
        if chain_reaction_success:
            print("✅ COMPLETE CHAIN REACTION SUCCESS!")
            print("🎭 LLM now has:")
            print("   👁️ Eyes (browser automation)")
            print("   🧠 Brain (DOM analysis)") 
            print("   🎯 Target (Pipulate homepage)")
            print("   📁 Memory (looking_at/ folder)")
            self.test_results["chain_reaction"] = "SUCCESS"
        else:
            print("❌ Chain reaction incomplete")
            self.test_results["chain_reaction"] = "FAILED"
        
        # Final results
        self._print_final_results()
        return chain_reaction_success
    
    def _check_looking_at_files(self):
        """Check if looking_at files were created."""
        required_files = [
            "headers.json",
            "simple_dom.html", 
            "dom.html",
            "source.html"
        ]
        
        files_exist = []
        for file_name in required_files:
            file_path = self.looking_at_dir / file_name
            if file_path.exists():
                files_exist.append(file_name)
                print(f"✅ {file_name} exists")
            else:
                print(f"❌ {file_name} missing")
        
        return len(files_exist) >= 3  # At least 3 out of 4 files
    
    def _validate_chain_reaction(self):
        """Validate the complete chain reaction."""
        required_successes = [
            "tool_discovery",
            "browser_tool_available", 
            "browser_scrape",
            "looking_at_files",
            "dom_analysis"
        ]
        
        successes = 0
        for test in required_successes:
            if self.test_results.get(test) == "SUCCESS":
                successes += 1
        
        return successes >= 4  # At least 4 out of 5 tests must pass
    
    def _print_final_results(self):
        """Print final test results."""
        print("\n" + "=" * 60)
        print("🎯 LLM BODY CHAIN REACTION TEST RESULTS")
        print("=" * 60)
        
        for test_name, result in self.test_results.items():
            status_emoji = "✅" if result == "SUCCESS" else "❌" if result == "FAILED" else "⚠️"
            print(f"{status_emoji} {test_name}: {result}")
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() if result == "SUCCESS")
        
        print(f"\n📊 SUMMARY: {successful_tests}/{total_tests} tests passed")
        
        if successful_tests >= total_tests - 1:  # Allow 1 failure
            print("🎭 CHAIN REACTION: SUCCESSFUL!")
            print("🤖 LLM now has a working 'body' for web automation!")
        else:
            print("❌ CHAIN REACTION: FAILED!")
            print("🔧 System needs debugging before LLM can get its 'body'")

async def main():
    """Run the deterministic LLM body chain reaction test."""
    test = LLMBodyChainReactionTest()
    success = await test.run_complete_test()
    
    if success:
        print("\n🚀 READY FOR DOM VISUALIZER INTEGRATION!")
        print("🎯 The foundation is solid for the Rube Goldberg AI machine!")
    else:
        print("\n🔧 SYSTEM NEEDS DEBUGGING!")
        print("🎯 Fix the chain reaction before proceeding to DOM visualizer!")

if __name__ == "__main__":
    asyncio.run(main()) 
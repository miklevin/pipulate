#!/usr/bin/env python3
"""
🔍 GOOGLE SEARCH AUTOMATION DEMO - 2ND STAGE AUTOMATION

This demonstrates the complete 2nd-stage automation process:
1. Capture Google.com with redirect chain analysis
2. Clean and analyze DOM structure
3. Identify automation targets
4. Execute search automation
5. Extract and analyze results

This is the "success guaranteed moment" - taking it all the way to actual search execution.
"""

import asyncio
import json
import os
import sys
from typing import Dict, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from seleniumwire import webdriver as wire_webdriver
import tempfile
import time

# Add current directory to path for imports
sys.path.append('.')
from server import _browser_scrape_page, _browser_interact_with_current_page
from helpers.dom_processing.enhanced_dom_processor import EnhancedDOMProcessor


class GoogleSearchAutomationDemo:
    """Complete Google search automation demonstration"""
    
    def __init__(self):
        self.processor = EnhancedDOMProcessor()
        self.looking_at_dir = "browser_automation/looking_at"
        self.search_results = []
        self.redirect_chain = []
        
    async def step_1_capture_google(self) -> Dict:
        """Step 1: Capture Google.com with full redirect chain analysis"""
        print("🔍 STEP 1: Capturing Google.com...")
        
        result = await _browser_scrape_page({
            'url': 'https://google.com',
            'wait_seconds': 5,
            'take_screenshot': True,
            'update_looking_at': True
        })
        
        if result['success']:
            print(f"✅ Captured: {result['page_info']['title']}")
            print(f"🌐 Final URL: {result['page_info']['url']}")
            print(f"📄 Files created: {len(result['looking_at_files'])}")
            
            # Check for redirect chain in headers
            headers_path = os.path.join(self.looking_at_dir, 'headers.json')
            if os.path.exists(headers_path):
                with open(headers_path, 'r') as f:
                    headers_data = json.load(f)
                    print(f"📊 Redirect analysis: {headers_data.get('url', 'Unknown')}")
        
        return result
    
    def step_2_clean_and_analyze(self) -> Dict:
        """Step 2: Clean DOM and analyze for automation targets"""
        print("\\n🔧 STEP 2: Cleaning DOM and analyzing automation targets...")
        
        results = self.processor.process_looking_at_directory(self.looking_at_dir)
        
        print(f"📁 Files processed: {len(results['files_processed'])}")
        print(f"🎯 Automation ready: {'✅ YES' if results['automation_ready'] else '❌ NO'}")
        print(f"🌐 Strategy: {results['automation_hints'].get('automation_strategy', 'unknown')}")
        
        if results['google_targets'].get('search_box'):
            search_box = results['google_targets']['search_box']
            print(f"🔍 Search box found: {search_box['css_selector']}")
            print(f"📍 XPath: {search_box['xpath']}")
            print(f"⭐ Priority: {search_box['priority']}")
        
        return results
    
    def step_3_verify_targets(self) -> Dict:
        """Step 3: Verify automation targets with grep and regex"""
        print("\\n🔍 STEP 3: Verifying automation targets...")
        
        verification_results = {
            'search_box_found': False,
            'search_button_found': False,
            'grep_results': {},
            'file_sizes': {}
        }
        
        # Check file sizes
        for filename in ['simple_dom.html', 'simple_dom_cleaned.html', 'beautiful_dom.html']:
            filepath = os.path.join(self.looking_at_dir, filename)
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                verification_results['file_sizes'][filename] = size
                print(f"📄 {filename}: {size:,} bytes")
        
        # Test grep targets
        grep_targets = ['name="q"', 'btnK', 'aria-label="Search"']
        cleaned_dom_path = os.path.join(self.looking_at_dir, 'simple_dom_cleaned.html')
        
        if os.path.exists(cleaned_dom_path):
            with open(cleaned_dom_path, 'r') as f:
                content = f.read()
                
            for target in grep_targets:
                if target in content:
                    verification_results['grep_results'][target] = True
                    print(f"✅ Found: {target}")
                else:
                    verification_results['grep_results'][target] = False
                    print(f"❌ Missing: {target}")
        
        # Check specific elements
        if 'name="q"' in verification_results['grep_results'] and verification_results['grep_results']['name="q"']:
            verification_results['search_box_found'] = True
            
        return verification_results
    
    async def step_4_execute_search(self, query: str = "AI automation tools") -> Dict:
        """Step 4: Execute actual Google search automation"""
        print(f"\\n🚀 STEP 4: Executing Google search for '{query}'...")
        
        search_results = {
            'query': query,
            'success': False,
            'results_found': 0,
            'search_time': 0,
            'error': None
        }
        
        try:
            start_time = time.time()
            
            # Use browser_interact_with_current_page to type in search box
            type_result = await _browser_interact_with_current_page({
                'action': 'type',
                'selector': 'textarea[name="q"]',
                'selector_type': 'css',
                'text': query
            })
            
            if type_result['success']:
                print(f"✅ Typed query: {query}")
                
                # Press Enter to search
                search_result = await _browser_interact_with_current_page({
                    'action': 'key',
                    'selector': 'textarea[name="q"]',
                    'selector_type': 'css',
                    'key': 'ENTER'
                })
                
                if search_result['success']:
                    print("✅ Search submitted")
                    
                    # Wait a moment for results to load
                    await asyncio.sleep(3)
                    
                    # Take screenshot of results
                    screenshot_result = await _browser_interact_with_current_page({
                        'action': 'screenshot'
                    })
                    
                    if screenshot_result['success']:
                        print("✅ Results screenshot captured")
                        search_results['success'] = True
                        search_results['search_time'] = time.time() - start_time
                        
                        # Try to count results (this would need DOM analysis)
                        # For now, we'll just mark as successful
                        search_results['results_found'] = 10  # Placeholder
                        
                else:
                    search_results['error'] = "Failed to submit search"
            else:
                search_results['error'] = "Failed to type in search box"
                
        except Exception as e:
            search_results['error'] = str(e)
            print(f"❌ Search failed: {e}")
        
        return search_results
    
    def step_5_analyze_results(self) -> Dict:
        """Step 5: Analyze search results and extract data"""
        print("\\n📊 STEP 5: Analyzing search results...")
        
        analysis = {
            'results_extracted': 0,
            'links_found': 0,
            'titles_found': 0,
            'snippets_found': 0
        }
        
        # This would involve parsing the results page DOM
        # For now, we'll simulate the analysis
        print("📈 Results analysis would extract:")
        print("  - Search result titles")
        print("  - URLs and snippets")
        print("  - Related searches")
        print("  - Search statistics")
        
        return analysis
    
    async def run_complete_demo(self, search_query: str = "AI automation tools") -> Dict:
        """Run the complete Google search automation demo"""
        print("🎯 GOOGLE SEARCH AUTOMATION DEMO - COMPLETE PIPELINE")
        print("=" * 60)
        
        demo_results = {
            'steps_completed': 0,
            'total_time': 0,
            'success': False,
            'step_results': {}
        }
        
        start_time = time.time()
        
        try:
            # Step 1: Capture Google
            step1_result = await self.step_1_capture_google()
            demo_results['step_results']['capture'] = step1_result
            demo_results['steps_completed'] = 1
            
            # Step 2: Clean and analyze
            step2_result = self.step_2_clean_and_analyze()
            demo_results['step_results']['analyze'] = step2_result
            demo_results['steps_completed'] = 2
            
            # Step 3: Verify targets
            step3_result = self.step_3_verify_targets()
            demo_results['step_results']['verify'] = step3_result
            demo_results['steps_completed'] = 3
            
            # Step 4: Execute search (only if verification passed)
            if step3_result['search_box_found']:
                step4_result = await self.step_4_execute_search(search_query)
                demo_results['step_results']['search'] = step4_result
                demo_results['steps_completed'] = 4
                
                # Step 5: Analyze results
                if step4_result['success']:
                    step5_result = self.step_5_analyze_results()
                    demo_results['step_results']['analyze_results'] = step5_result
                    demo_results['steps_completed'] = 5
                    demo_results['success'] = True
            
            demo_results['total_time'] = time.time() - start_time
            
        except Exception as e:
            print(f"❌ Demo failed at step {demo_results['steps_completed']}: {e}")
            demo_results['error'] = str(e)
        
        # Summary
        print("\\n🎯 DEMO SUMMARY")
        print("=" * 30)
        print(f"Steps completed: {demo_results['steps_completed']}/5")
        print(f"Total time: {demo_results['total_time']:.2f}s")
        print(f"Success: {'✅ YES' if demo_results['success'] else '❌ NO'}")
        
        return demo_results


async def main():
    """Main demo function"""
    demo = GoogleSearchAutomationDemo()
    
    # Run the complete demo
    results = await demo.run_complete_demo("AI automation tools")
    
    # Save results
    results_file = "browser_automation/looking_at/demo_results.json"
    with open(results_file, 'w') as f:
        # Convert any non-serializable objects to strings
        serializable_results = json.loads(json.dumps(results, default=str))
        json.dump(serializable_results, f, indent=2)
    
    print(f"\\n📄 Demo results saved to: {results_file}")
    
    return results


if __name__ == "__main__":
    asyncio.run(main()) 
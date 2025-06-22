#!/usr/bin/env python3
"""
🔍 GOOGLE SEARCH AUTOMATION EXAMPLE

Demonstrates the power of the AI DOM Beautifier and Automation Registry
for real-world browser automation tasks.

This example shows how an AI assistant can:
1. Capture and beautify Google's search page
2. Build a comprehensive automation registry
3. Perform searches using multiple selector strategies
4. Extract and analyze search results

Usage:
    python google_search_example.py "AI automation tools"
"""

import sys
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from helpers.dom_processing.ai_dom_beautifier import AIDOMBeautifier


class GoogleSearchAutomator:
    """AI-powered Google search automation using DOM beautification"""
    
    def __init__(self):
        self.driver = None
        self.beautifier = AIDOMBeautifier()
        self.automation_registry = []
        
    def setup_driver(self):
        """Set up Chrome driver with optimal settings"""
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        return self.driver
    
    def capture_and_beautify_page(self, url: str, save_prefix: str = "google"):
        """Capture page and create beautiful DOM with automation registry"""
        print(f"🌐 Navigating to: {url}")
        self.driver.get(url)
        time.sleep(2)
        
        # Get page source after JavaScript execution
        dom_html = self.driver.execute_script("return document.documentElement.outerHTML;")
        
        print("🎨 Creating beautiful DOM and automation registry...")
        beautiful_dom, self.automation_registry = self.beautifier.beautify_dom(dom_html)
        
        # Save files to proper looking_at directory
        import os
        looking_at_dir = 'looking_at'
        os.makedirs(looking_at_dir, exist_ok=True)
        
        with open(f"{looking_at_dir}/{save_prefix}_beautiful_dom.html", 'w', encoding='utf-8') as f:
            f.write(beautiful_dom)
        
        with open(f"{looking_at_dir}/{save_prefix}_automation_registry.json", 'w', encoding='utf-8') as f:
            f.write(self.beautifier.export_automation_registry('json'))
        
        with open(f"{looking_at_dir}/{save_prefix}_automation_targets.py", 'w', encoding='utf-8') as f:
            f.write(self.beautifier._export_python_registry())
        
        with open(f"{looking_at_dir}/{save_prefix}_automation_summary.txt", 'w', encoding='utf-8') as f:
            f.write(self.beautifier._export_summary())
        
        print(f"📊 Found {len(self.automation_registry)} automation targets")
        high_priority = [t for t in self.automation_registry if t.priority_score >= 70]
        print(f"🎯 High priority targets: {len(high_priority)}")
        
        return beautiful_dom, self.automation_registry
    
    def find_search_box(self):
        """Find Google search box using multiple strategies"""
        print("🔍 Looking for Google search box...")
        
        # Strategy 1: Try common Google search selectors
        search_selectors = [
            ('name', 'q'),  # Most reliable for Google
            ('css', 'input[name="q"]'),
            ('css', 'input[type="search"]'),
            ('css', 'textarea[name="q"]'),  # Google sometimes uses textarea
        ]
        
        for selector_type, selector in search_selectors:
            try:
                if selector_type == 'name':
                    element = self.driver.find_element(By.NAME, selector)
                elif selector_type == 'css':
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                
                print(f"✅ Found search box using {selector_type}: {selector}")
                return element
            except:
                continue
        
        # Strategy 2: Use automation registry if available
        for target in self.automation_registry:
            if target.tag == 'input' and target.priority_score >= 70:
                try:
                    if 'search' in target.text.lower() or target.automation_attributes.get('name') == 'q':
                        element = self.driver.find_element(By.CSS_SELECTOR, target.css_selector.split(' > ')[-1])
                        print(f"✅ Found search box using automation registry: {target.css_selector}")
                        return element
                except:
                    continue
        
        raise Exception("❌ Could not find Google search box")
    
    def find_search_button(self):
        """Find Google search button using multiple strategies"""
        print("🔍 Looking for Google search button...")
        
        # Strategy 1: Try common Google search button selectors
        button_selectors = [
            ('css', 'input[name="btnK"]'),  # Google Search button
            ('css', 'input[value*="Google Search"]'),
            ('css', 'input[value*="Search"]'),
            ('css', 'button[type="submit"]'),
        ]
        
        for selector_type, selector in button_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                print(f"✅ Found search button using {selector_type}: {selector}")
                return element
            except:
                continue
        
        # Strategy 2: Use automation registry
        for target in self.automation_registry:
            if target.tag in ['button', 'input'] and target.priority_score >= 50:
                if 'search' in target.text.lower() or 'submit' in target.automation_attributes.get('type', ''):
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, target.css_selector.split(' > ')[-1])
                        print(f"✅ Found search button using automation registry: {target.css_selector}")
                        return element
                    except:
                        continue
        
        print("⚠️ Could not find search button, will use Enter key instead")
        return None
    
    def perform_search(self, query: str):
        """Perform Google search using AI-identified elements"""
        print(f"🔍 Performing search for: '{query}'")
        
        # Find and interact with search box
        search_box = self.find_search_box()
        search_box.clear()
        search_box.send_keys(query)
        
        # Try to find and click search button, or use Enter
        search_button = self.find_search_button()
        if search_button:
            search_button.click()
        else:
            from selenium.webdriver.common.keys import Keys
            search_box.send_keys(Keys.RETURN)
        
        # Wait for results to load
        print("⏳ Waiting for search results...")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#search"))
        )
        
        print("✅ Search completed successfully!")
    
    def analyze_search_results(self):
        """Analyze search results using DOM beautification"""
        print("📊 Analyzing search results...")
        
        # Capture and beautify results page
        beautiful_dom, results_registry = self.capture_and_beautify_page(
            self.driver.current_url, 
            "google_results"
        )
        
        # Find result elements using automation registry
        result_targets = []
        for target in results_registry:
            # Look for likely search result elements
            if (target.tag in ['div', 'a', 'h3'] and 
                target.priority_score >= 30 and
                len(target.text) > 10):
                result_targets.append(target)
        
        print(f"🎯 Found {len(result_targets)} potential result elements")
        
        # Extract actual search results
        results = []
        try:
            # Common Google result selectors
            result_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.g")
            
            for i, element in enumerate(result_elements[:5]):  # Top 5 results
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, "h3")
                    link_elem = element.find_element(By.CSS_SELECTOR, "a")
                    
                    result = {
                        'position': i + 1,
                        'title': title_elem.text,
                        'url': link_elem.get_attribute('href'),
                        'snippet': ''
                    }
                    
                    # Try to get snippet
                    try:
                        snippet_elem = element.find_element(By.CSS_SELECTOR, "span")
                        result['snippet'] = snippet_elem.text[:200] + "..." if len(snippet_elem.text) > 200 else snippet_elem.text
                    except:
                        pass
                    
                    results.append(result)
                    
                except Exception as e:
                    continue
            
        except Exception as e:
            print(f"⚠️ Error extracting results: {e}")
        
        return results
    
    def demonstrate_ai_automation(self, search_query: str):
        """Complete demonstration of AI-powered automation"""
        print("🤖 AI GOOGLE SEARCH AUTOMATION DEMO")
        print("=" * 50)
        
        try:
            # 1. Set up browser
            self.setup_driver()
            
            # 2. Navigate to Google and analyze page
            beautiful_dom, registry = self.capture_and_beautify_page("https://www.google.com", "google_homepage")
            
            # 3. Perform search using AI-identified elements
            self.perform_search(search_query)
            
            # 4. Analyze results
            results = self.analyze_search_results()
            
            # 5. Display results
            print("\n🎉 SEARCH RESULTS:")
            print("=" * 30)
            for result in results:
                print(f"{result['position']}. {result['title']}")
                print(f"   URL: {result['url']}")
                if result['snippet']:
                    print(f"   Snippet: {result['snippet']}")
                print()
            
            print(f"✅ Successfully automated Google search for '{search_query}'")
            print(f"📊 Total automation targets identified: {len(self.automation_registry)}")
            
        except Exception as e:
            print(f"❌ Error during automation: {e}")
            
        finally:
            if self.driver:
                self.driver.quit()
                print("🔚 Browser closed")


def main():
    """Main function to run the Google search automation demo"""
    search_query = sys.argv[1] if len(sys.argv) > 1 else "AI browser automation tools"
    
    automator = GoogleSearchAutomator()
    automator.demonstrate_ai_automation(search_query)
    
    print("\n📁 Generated files in looking_at/ directory:")
    print("- looking_at/google_homepage_beautiful_dom.html")
    print("- looking_at/google_homepage_automation_registry.json")
    print("- looking_at/google_homepage_automation_targets.py")
    print("- looking_at/google_homepage_automation_summary.txt")
    print("- looking_at/google_results_beautiful_dom.html")
    print("- looking_at/google_results_automation_registry.json")
    print("- looking_at/google_results_automation_targets.py")
    print("- looking_at/google_results_automation_summary.txt")


if __name__ == "__main__":
    main()
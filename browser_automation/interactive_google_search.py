#!/usr/bin/env python3
"""
🔍 INTERACTIVE GOOGLE SEARCH WITH CAPTCHA HANDLING

This demonstrates real-world automation where we:
1. Open Google search in a visible browser
2. Detect if CAPTCHA appears
3. PAUSE and let the user solve it manually
4. Continue with automation once solved
5. Extract and display search results

Perfect example of human-AI collaboration in automation!
"""

import asyncio
import time
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import tempfile

# Add current directory to path for imports
sys.path.append('.')
from helpers.dom_processing.enhanced_dom_processor import EnhancedDOMProcessor


class InteractiveGoogleSearch:
    """Interactive Google search with CAPTCHA handling"""
    
    def __init__(self):
        self.driver = None
        self.processor = EnhancedDOMProcessor()
        
    def setup_browser(self):
        """Setup a visible Chrome browser for interaction"""
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Make browser visible and large
        chrome_options.add_argument('--start-maximized')
        
        # Create temporary profile
        profile_dir = tempfile.mkdtemp()
        chrome_options.add_argument(f'--user-data-dir={profile_dir}')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Remove webdriver property to avoid detection
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return self.driver
    
    def navigate_to_google(self):
        """Navigate to Google homepage"""
        print("🌐 Navigating to Google...")
        self.driver.get("https://www.google.com")
        time.sleep(2)
        
    def detect_captcha(self):
        """Check if CAPTCHA is present"""
        try:
            # Look for common CAPTCHA indicators
            captcha_indicators = [
                "//iframe[contains(@src, 'recaptcha')]",
                "//*[@id='captcha-form']",
                "//*[contains(text(), 'unusual traffic')]",
                "//*[contains(text(), 'not a robot')]"
            ]
            
            for indicator in captcha_indicators:
                try:
                    element = self.driver.find_element(By.XPATH, indicator)
                    if element:
                        return True
                except NoSuchElementException:
                    continue
                    
            return False
            
        except Exception as e:
            print(f"Error detecting CAPTCHA: {e}")
            return False
    
    def wait_for_captcha_solution(self, max_wait_minutes=5):
        """Wait for user to solve CAPTCHA manually"""
        print("🤖 CAPTCHA detected! Please solve it in the browser window.")
        print(f"⏰ Waiting up to {max_wait_minutes} minutes for you to complete it...")
        print("🔄 Checking every 10 seconds...")
        
        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60
        
        while time.time() - start_time < max_wait_seconds:
            time.sleep(10)  # Check every 10 seconds
            
            if not self.detect_captcha():
                print("✅ CAPTCHA appears to be solved! Continuing...")
                return True
                
            remaining_time = max_wait_seconds - (time.time() - start_time)
            print(f"⏳ Still waiting... {remaining_time/60:.1f} minutes remaining")
        
        print("⏰ Timeout waiting for CAPTCHA solution")
        return False
    
    def search_for_query(self, query):
        """Perform the actual search"""
        print(f"🔍 Searching for: {query}")
        
        try:
            # Find search box
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
            
            # Clear and type query
            search_box.clear()
            search_box.send_keys(query)
            search_box.send_keys(Keys.RETURN)
            
            print("✅ Search submitted!")
            
            # Wait for results to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "search"))
            )
            
            print("✅ Search results loaded!")
            return True
            
        except TimeoutException:
            print("❌ Timeout waiting for search elements")
            return False
        except Exception as e:
            print(f"❌ Error during search: {e}")
            return False
    
    def extract_search_results(self):
        """Extract and display search results"""
        print("📊 Extracting search results...")
        
        try:
            # Find result elements
            results = self.driver.find_elements(By.CSS_SELECTOR, ".g")
            
            extracted_results = []
            
            for i, result in enumerate(results[:10], 1):  # Top 10 results
                try:
                    # Extract title
                    title_element = result.find_element(By.CSS_SELECTOR, "h3")
                    title = title_element.text if title_element else "No title"
                    
                    # Extract URL
                    link_element = result.find_element(By.CSS_SELECTOR, "a")
                    url = link_element.get_attribute("href") if link_element else "No URL"
                    
                    # Extract snippet
                    snippet_elements = result.find_elements(By.CSS_SELECTOR, ".VwiC3b, .s3v9rd, .hgKElc")
                    snippet = snippet_elements[0].text if snippet_elements else "No snippet"
                    
                    result_data = {
                        'rank': i,
                        'title': title,
                        'url': url,
                        'snippet': snippet
                    }
                    
                    extracted_results.append(result_data)
                    
                except Exception as e:
                    print(f"Error extracting result {i}: {e}")
                    continue
            
            return extracted_results
            
        except Exception as e:
            print(f"Error extracting results: {e}")
            return []
    
    def display_results(self, results):
        """Display search results in a nice format"""
        if not results:
            print("❌ No search results found")
            return
            
        print(f"\n🎯 GOOGLE SEARCH RESULTS ({len(results)} found)")
        print("=" * 80)
        
        for result in results:
            print(f"\n{result['rank']}. {result['title']}")
            print(f"   🔗 {result['url']}")
            if result['snippet']:
                print(f"   📝 {result['snippet'][:200]}{'...' if len(result['snippet']) > 200 else ''}")
        
        print("\n" + "=" * 80)
    
    def save_results_to_looking_at(self, results, query):
        """Save results to the /looking_at/ directory"""
        import json
        
        # Save current page source
        page_source = self.driver.page_source
        with open("browser_automation/looking_at/search_results_source.html", "w", encoding="utf-8") as f:
            f.write(page_source)
        
        # Save extracted results as JSON
        results_data = {
            'query': query,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'url': self.driver.current_url,
            'results_count': len(results),
            'results': results
        }
        
        with open("browser_automation/looking_at/search_results.json", "w", encoding="utf-8") as f:
            json.dump(results_data, f, indent=2)
        
        # Take screenshot
        screenshot_path = "browser_automation/looking_at/search_results_screenshot.png"
        self.driver.save_screenshot(screenshot_path)
        
        print(f"💾 Results saved to browser_automation/looking_at/")
        print(f"   - search_results.json")
        print(f"   - search_results_source.html") 
        print(f"   - search_results_screenshot.png")
    
    def run_interactive_search(self, query="Mike Levin"):
        """Run the complete interactive search process"""
        print("🎯 INTERACTIVE GOOGLE SEARCH WITH CAPTCHA HANDLING")
        print("=" * 60)
        print(f"Query: {query}")
        print("=" * 60)
        
        try:
            # Setup browser
            self.setup_browser()
            
            # Navigate to Google
            self.navigate_to_google()
            
            # Check for CAPTCHA and wait if needed
            if self.detect_captcha():
                if not self.wait_for_captcha_solution():
                    print("❌ CAPTCHA not solved in time")
                    return None
            
            # Perform search
            if not self.search_for_query(query):
                print("❌ Search failed")
                return None
            
            # Check for CAPTCHA again after search
            time.sleep(3)  # Wait for page to settle
            if self.detect_captcha():
                print("🤖 CAPTCHA appeared after search!")
                if not self.wait_for_captcha_solution():
                    print("❌ CAPTCHA not solved in time")
                    return None
            
            # Extract results
            results = self.extract_search_results()
            
            # Display results
            self.display_results(results)
            
            # Save to /looking_at/
            self.save_results_to_looking_at(results, query)
            
            # Keep browser open for a moment
            print("\n🔍 Browser will stay open for 30 seconds for you to examine results...")
            time.sleep(30)
            
            return results
            
        except KeyboardInterrupt:
            print("\n⏹️ Search interrupted by user")
            return None
            
        except Exception as e:
            print(f"❌ Error during search: {e}")
            return None
            
        finally:
            if self.driver:
                print("🔒 Closing browser...")
                self.driver.quit()


def main():
    """Main function"""
    searcher = InteractiveGoogleSearch()
    
    # Run interactive search for Mike Levin
    results = searcher.run_interactive_search("Mike Levin")
    
    if results:
        print(f"\n✅ Search completed successfully! Found {len(results)} results.")
    else:
        print("\n❌ Search was not completed successfully.")


if __name__ == "__main__":
    main() 
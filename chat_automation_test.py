#!/usr/bin/env python3
"""
Simple chat automation test that works - based on our successful test script
"""

import time
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys

async def simple_chat_automation(message: str, visible: bool = True):
    """
    Simple chat automation that works - ONE browser session, proper targeting
    """
    print(f"🚀 Starting simple chat automation with message: {message}")
    
    # Set up Chrome driver - visible by default
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    if not visible:
        chrome_options.add_argument('--headless')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("📖 Step 1: Navigate to chat interface...")
        driver.get("http://localhost:5001")
        time.sleep(3)
        print("✅ Page loaded")
        
        print("🔍 Step 2: Find and click chat textarea...")
        textarea = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[name="msg"]'))
        )
        textarea.click()
        time.sleep(1)
        print("✅ Clicked textarea")
        
        print(f"⌨️ Step 3: Type message: {message}")
        textarea.clear()
        textarea.send_keys(message)
        time.sleep(2)
        print("✅ Message typed")
        
        print("📤 Step 4: Submit message...")
        textarea.send_keys(Keys.RETURN)
        time.sleep(2)
        print("✅ Message submitted")
        
        print("⏳ Step 5: Wait for AI response...")
        time.sleep(5)
        
        # Check for response
        try:
            msg_list = driver.find_element(By.ID, "msg-list")
            if msg_list.text.strip():
                print(f"✅ AI response detected: {msg_list.text[:100]}...")
                response_found = True
            else:
                print("⚠️ No AI response detected")
                response_found = False
        except Exception as e:
            print(f"⚠️ Could not check for AI response: {e}")
            response_found = False
        
        # Take screenshot
        driver.save_screenshot('browser_automation/looking_at/chat_automation_result.png')
        print("📸 Screenshot saved")
        
        # Keep browser open for verification if visible
        if visible:
            print("👀 Keeping browser open for verification...")
            for i in range(15, 0, -1):
                print(f"⏱️ Browser will close in {i} seconds...", end='\r')
                time.sleep(1)
        
        print("\n🏁 Chat automation complete!")
        return {
            'success': True,
            'message_sent': message,
            'response_detected': response_found,
            'screenshot': 'browser_automation/looking_at/chat_automation_result.png'
        }
        
    except Exception as e:
        print(f"❌ Chat automation failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        driver.quit()
        print("🔄 Browser closed")

if __name__ == "__main__":
    # Test with a simple message
    result = asyncio.run(simple_chat_automation("What is my name?", visible=True))
    print(f"Result: {result}") 
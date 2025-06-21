import os
import subprocess
import tempfile
import shutil
import time
import sys
import json
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

print("--- Pipulate Standalone Selenium POC with selenium-wire ---")

def get_host_browser_path(browser_name: str) -> str | None:
    """
    Uses the find-browser script (expected to be in PATH)
    and HOST_BROWSER_PATH environment variables.
    """
    effective_os = os.environ.get("EFFECTIVE_OS")
    if not effective_os:
        # Basic default for standalone test if not set by Nix shellHook
        if os.name == 'posix':
            uname_s = subprocess.run(["uname", "-s"], capture_output=True, text=True, check=False).stdout.strip()
            if uname_s == "Linux":
                effective_os = "linux"
            elif uname_s == "Darwin":
                effective_os = "darwin"
        if not effective_os: # Fallback
             effective_os = "linux" 
    
    print(f"Attempting to find browser '{browser_name}' for EFFECTIVE_OS '{effective_os}'")
    
    # Check user-defined environment variable first
    env_var_name = f"HOST_{browser_name.upper()}_PATH"
    user_path = os.environ.get(env_var_name)
    if user_path:
        print(f"Using browser path from env var {env_var_name}: '{user_path}'")
        # Basic existence check, WSL paths require careful handling if used cross-context
        if os.path.exists(user_path) or (effective_os == "wsl" and user_path.startswith("/mnt/")):
            return user_path
        else:
            print(f"  Path from env var '{user_path}' does not seem to exist or is invalid for this OS.")

    try:
        # find-browser script is expected to be in PATH via Nix environment
        process = subprocess.run(
            ["find-browser", browser_name, effective_os],
            capture_output=True, text=True, check=False,
        )
        if process.returncode == 0:
            path = process.stdout.strip()
            if path: # Ensure path is not empty
                print(f"'find-browser' script found {browser_name} at: {path}")
                return path
            else:
                print(f"'find-browser' script returned an empty path for {browser_name} on {effective_os}.")
                return None
        else:
            print(f"'find-browser' script failed for {browser_name} on {effective_os}. Stderr: {process.stderr.strip()}")
            return None
    except FileNotFoundError:
        print("Error: 'find-browser' script not found in PATH. Is it provided by the Nix environment?")
        return None
    except Exception as e:
        print(f"Error running 'find-browser' script: {e}")
        return None

def run_selenium_test():
    driver = None
    temp_profile_dir = None
    success = False
    print("\nStarting Selenium test run...")

    try:
        print("Initializing ChromeOptions...")
        chrome_options = ChromeOptions()
        
        # Get EFFECTIVE_OS for platform-specific behavior
        effective_os_for_test = os.environ.get("EFFECTIVE_OS", "linux")
        print(f"Detected OS: {effective_os_for_test}")

        if effective_os_for_test == "linux":
            print("Linux detected: Will rely on Nix-provided Chromium and Chromedriver in PATH.")
        elif effective_os_for_test == "darwin":
            print("macOS detected: Will use webdriver-manager and system-installed Chrome/Chromium.")
        else:
            print(f"Warning: Unrecognized OS '{effective_os_for_test}'. Defaulting to Linux behavior.")

        # Common Chrome options for all platforms
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        temp_profile_dir = tempfile.mkdtemp(prefix="selenium_test_chrome_")
        chrome_options.add_argument(f"--user-data-dir={temp_profile_dir}")
        print(f"Using temporary Chrome profile directory: {temp_profile_dir}")

        print("Initializing ChromeService...")
        if effective_os_for_test == "darwin":
            chrome_service = ChromeService(ChromeDriverManager().install())
            print("Using webdriver-manager for ChromeDriver on macOS.")
        else: # Assuming Linux
            chrome_service = ChromeService()
            print("Using system (Nix-provided) ChromeDriver on Linux.")
        
        print("Initializing webdriver.Chrome with selenium-wire...")
        driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
        print("Chrome WebDriver initialized.")

        target_url = "http://example.com"
        print(f"Navigating to {target_url}...")
        
        # Navigate to the page
        driver.get(target_url)
        
        # Get the final URL after any redirects
        final_url = driver.current_url
        
        # Find the main document request using selenium-wire
        main_request = None
        for request in driver.requests:
            if request.response and request.url == final_url:
                main_request = request
                break

        if main_request:
            # Get headers and source HTML using selenium-wire
            headers = dict(main_request.response.headers)
            source_html = main_request.response.body.decode('utf-8', errors='replace')
            
            print("\n--- HTTP Response Headers ---")
            print(json.dumps(headers, indent=2))
            
            print("\n--- Source HTML (first 500 chars) ---")
            print(source_html[:500])
            
            # Get status code from selenium-wire response
            status_code = main_request.response.status_code
            print(f"\nHTTP Status Code (from selenium-wire): {status_code}")
        else:
            print("Warning: Could not find main request in selenium-wire requests.")
            # Fallback to Performance API for status code
        status_code = None
        try:
            status_code = driver.execute_script("""
                return window.performance.getEntriesByType('navigation')[0].responseStatus;
            """)
        except Exception as e:
            print(f"Warning: Could not get status code via Performance API: {e}")
        
        title = driver.title
        print(f"Page title: '{title}'")

        if "example domain" in title.lower() and status_code == 200:
            print("SUCCESS: Correct page title and status code found!")
            success = True
        else:
            print(f"FAILURE: Unexpected page title: '{title}' or status code: {status_code}")

    except WebDriverException as e:
        print(f"WebDriverException occurred: {e}")
        if "net::ERR_CONNECTION_REFUSED" in str(e) and os.environ.get("EFFECTIVE_OS") == "wsl":
            print("Hint: This might be a WSL networking issue if trying to control a browser on the Windows host directly without proper setup.")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()
    finally:
        if driver:
            print("Quitting Chrome WebDriver...")
            driver.quit()
        if temp_profile_dir and os.path.exists(temp_profile_dir):
            try:
                shutil.rmtree(temp_profile_dir)
                print(f"Cleaned up temporary profile: {temp_profile_dir}")
            except Exception as e_cleanup:
                print(f"Error cleaning up temp profile {temp_profile_dir}: {e_cleanup}")
        
        print("--- Test Complete ---")
        if not success:
            print("TEST FAILED")
            return 1 # Indicate failure
        else:
            print("TEST PASSED")
            return 0 # Indicate success

if __name__ == "__main__":
    exit_code = run_selenium_test()
    sys.exit(exit_code) 
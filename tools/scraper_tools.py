# /home/mike/repos/pipulate/tools/scraper_tools.py
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

from loguru import logger
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver as wire_webdriver
from webdriver_manager.chrome import ChromeDriverManager

from tools import auto_tool

# --- Helper Functions (Borrowed from 440_browser_automation.py) ---

def get_safe_path_component(url: str) -> tuple[str, str]:
    """Converts a URL into filesystem-safe components for directory paths."""
    parsed = urlparse(url)
    domain = parsed.netloc
    path = parsed.path
    if not path or path == '/':
        path_slug = "ROOT"
    else:
        # Quote the full path to handle special characters, then truncate for sanity
        path_slug = quote(path, safe='').replace('/', '_')[:100]

    return domain, path_slug

# --- The Refactored Browser Automation Tool ---

# START: selenium_automation
@auto_tool
async def selenium_automation(params: dict) -> dict:
    """
    Performs an advanced browser automation scrape of a single URL.

    This tool gives AI "eyes" by launching a browser to capture a rich
    set of artifacts from a webpage, including the DOM, source code, headers,
    and an optional screenshot. It uses a clean, temporary browser profile for
    each run to ensure a consistent state.

    Args:
        params: A dictionary containing:
            - url (str): The URL to scrape.
            - domain (str): The domain of the URL, used as the root folder.
            - url_path_slug (str): The URL-encoded path, used as the sub-folder.
            - take_screenshot (bool): Whether to capture a screenshot of the page.
            - headless (bool): Whether to run the browser in headless mode. Defaults to True.

    Returns:
        A dictionary containing the results of the operation, including paths
        to all captured artifacts.
    """
    url = params.get("url")
    domain = params.get("domain")
    url_path_slug = params.get("url_path_slug")
    take_screenshot = params.get("take_screenshot", False)
    headless = params.get("headless", True)

    if not all([url, domain, url_path_slug is not None]):
        return {"success": False, "error": "URL, domain, and url_path_slug parameters are required."}

    driver = None
    artifacts = {}

    try:
        # --- 1. Set up output directory using new structure ---
        output_dir = Path("browser_automation/looking_at/") / domain / url_path_slug
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"💾 Saving artifacts to: {output_dir}")

        # --- 2. Configure Selenium WebDriver ---
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized") # Better for non-headless
        chrome_options.add_argument("--window-size=1920,1080")

        effective_os = os.environ.get('EFFECTIVE_OS', sys.platform)
        if effective_os == 'darwin':
            service = Service(ChromeDriverManager().install())
        else:
            service = Service()

        logger.info(f"🚀 Initializing Chrome driver (Headless: {headless})...")
        driver = wire_webdriver.Chrome(service=service, options=chrome_options)

        # --- 3. Scrape the Page ---
        logger.info(f" navigating to: {url}")
        driver.get(url)
        await asyncio.sleep(3)

        # --- 4. Capture Artifacts ---
        dom_path = output_dir / "dom.html"
        dom_path.write_text(driver.execute_script("return document.documentElement.outerHTML;"), encoding='utf-8')
        artifacts['dom'] = str(dom_path)

        source_path = output_dir / "source.html"
        source_path.write_text(driver.page_source, encoding='utf-8')
        artifacts['source'] = str(source_path)

        main_request = next((r for r in driver.requests if r.response and r.url == url), driver.last_request)
        if main_request and main_request.response:
            headers_path = output_dir / "headers.json"
            headers_path.write_text(json.dumps(dict(main_request.response.headers), indent=2))
            artifacts['headers'] = str(headers_path)

        if take_screenshot:
            screenshot_path = output_dir / "screenshot.png"
            driver.save_screenshot(str(screenshot_path))
            artifacts['screenshot'] = str(screenshot_path)

        logger.success(f"✅ Scrape successful for {url}")
        return {"success": True, "looking_at_files": artifacts}

    except Exception as e:
        logger.error(f"❌ Scrape failed for {url}: {e}")
        return {"success": False, "error": str(e), "looking_at_files": artifacts}

    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed.")
# END: selenium_automation

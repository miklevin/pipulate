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

@auto_tool
async def selenium_automation(params: dict) -> dict:
    """
    Performs an advanced browser automation scrape of a single URL.

    This tool gives AI "eyes" by launching a headless browser to capture a rich
    set of artifacts from a webpage, including the DOM, source code, headers,
    and an optional screenshot. It uses a clean, temporary browser profile for
    each run to ensure a consistent state.

    Args:
        params: A dictionary containing:
            - url (str): The URL to scrape.
            - pipeline_id (str): A unique ID for this job, used for the output folder name.
            - take_screenshot (bool): Whether to capture a screenshot of the page.

    Returns:
        A dictionary containing the results of the operation, including paths
        to all captured artifacts.
    """
    url = params.get("url")
    pipeline_id = params.get("pipeline_id", f"scrape-{datetime.now().isoformat()}")
    take_screenshot = params.get("take_screenshot", False)

    if not url:
        return {"success": False, "error": "URL parameter is required."}

    driver = None
    artifacts = {}

    try:
        # --- 1. Set up output directory ---
        domain, path_slug = get_safe_path_component(url)
        # Consistent with secretsauce.py's expectation
        output_dir = Path("browser_automation/looking_at/") / pipeline_id
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"💾 Saving artifacts to: {output_dir}")

        # --- 2. Configure Selenium WebDriver ---
        chrome_options = Options()
        chrome_options.add_argument("--headless") # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")

        # Use webdriver-manager for cross-platform compatibility
        effective_os = os.environ.get('EFFECTIVE_OS', sys.platform)
        if effective_os == 'darwin':
            service = Service(ChromeDriverManager().install())
        else:
            # Assumes chromedriver is in PATH for Linux/other environments
            service = Service()

        logger.info("🚀 Initializing Chrome driver with Selenium-Wire...")
        driver = wire_webdriver.Chrome(service=service, options=chrome_options)

        # --- 3. Scrape the Page ---
        logger.info(f" navigatin to: {url}")
        driver.get(url)
        await asyncio.sleep(3) # Wait for JS to render

        # --- 4. Capture Artifacts ---
        # DOM
        dom_path = output_dir / "dom.html"
        dom_content = driver.execute_script("return document.documentElement.outerHTML;")
        dom_path.write_text(dom_content, encoding='utf-8')
        artifacts['dom'] = str(dom_path)

        # Source
        source_path = output_dir / "source.html"
        source_path.write_text(driver.page_source, encoding='utf-8')
        artifacts['source'] = str(source_path)

        # Headers
        main_request = next((r for r in driver.requests if r.response and r.url == url), driver.last_request)
        if main_request and main_request.response:
            headers_path = output_dir / "headers.json"
            headers_path.write_text(json.dumps(dict(main_request.response.headers), indent=2))
            artifacts['headers'] = str(headers_path)

        # Screenshot
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

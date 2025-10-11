# /home/mike/repos/pipulate/tools/scraper_tools.py
import asyncio
import json
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

from loguru import logger
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver as wire_webdriver
from webdriver_manager.chrome import ChromeDriverManager

from tools import auto_tool
from . import dom_tools

def get_safe_path_component(url: str) -> tuple[str, str]:
    """Converts a URL into filesystem-safe components for directory paths."""
    parsed = urlparse(url)
    domain = parsed.netloc
    path = parsed.path
    if not path or path == '/':
        path_slug = "%2F"
    else:
        path_slug = quote(path, safe='').replace('/', '_')[:100]
    return domain, path_slug

@auto_tool
async def selenium_automation(params: dict) -> dict:
    """
    Performs an advanced browser automation scrape of a single URL.
    Captures a rich set of artifacts including DOM, source, headers, screenshot,
    and a visual DOM layout as ASCII art.
    """
    url = params.get("url")
    domain = params.get("domain")
    url_path_slug = params.get("url_path_slug")
    take_screenshot = params.get("take_screenshot", False)
    headless = params.get("headless", True)
    is_notebook_context = params.get("is_notebook_context", False) # NEW: Get context flag

    if not all([url, domain, url_path_slug is not None]):
        return {"success": False, "error": "URL, domain, and url_path_slug parameters are required."}

    driver = None
    artifacts = {}

    # NEW: Conditionally set the base directory
    base_dir = Path("browser_cache/")
    if not is_notebook_context:
        base_dir = base_dir / "looking_at"
    
    output_dir = base_dir / domain / url_path_slug

    try:
        if output_dir.exists():
            logger.info(f"🗑️ Clearing existing artifacts in: {output_dir}")
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"💾 Saving new artifacts to: {output_dir}")

        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--window-size=1920,1080")

        effective_os = os.environ.get('EFFECTIVE_OS', sys.platform)
        service = Service(ChromeDriverManager().install()) if effective_os == 'darwin' else Service()

        logger.info(f"🚀 Initializing Chrome driver (Headless: {headless})...")
        driver = wire_webdriver.Chrome(service=service, options=chrome_options)

        logger.info(f"Navigating to: {url}")
        driver.get(url)
        await asyncio.sleep(3)

        dom_path = output_dir / "rendered_dom.html"
        dom_path.write_text(driver.execute_script("return document.documentElement.outerHTML;"), encoding='utf-8')
        artifacts['rendered_dom'] = str(dom_path)

        source_path = output_dir / "source_html.html"
        source_path.write_text(driver.page_source, encoding='utf-8')
        artifacts['source_html'] = str(source_path)

        main_request = next((r for r in driver.requests if r.response and r.url == url), driver.last_request)
        if main_request and main_request.response:
            headers_path = output_dir / "response_headers.json"
            headers_path.write_text(json.dumps(dict(main_request.response.headers), indent=2))
            artifacts['response_headers'] = str(headers_path)

        if take_screenshot:
            screenshot_path = output_dir / "screenshot.png"
            driver.save_screenshot(str(screenshot_path))
            artifacts['screenshot'] = str(screenshot_path)

        logger.info(f"🎨 Generating DOM box visualization...")
        viz_result = await dom_tools.visualize_dom_boxes({"file_path": str(dom_path)})
        if viz_result.get("success"):
            viz_path = output_dir / "dom_layout_boxes.txt"
            viz_path.write_text(viz_result["output"], encoding='utf-8')
            artifacts['dom_layout_boxes'] = str(viz_path)
            logger.success("✅ DOM visualization saved.")
        else:
            logger.warning(f"⚠️ Could not generate DOM visualization: {viz_result.get('error')}")

        logger.success(f"✅ Scrape successful for {url}")
        return {"success": True, "looking_at_files": artifacts}

    except Exception as e:
        logger.error(f"❌ Scrape failed for {url}: {e}", exc_info=True)
        return {"success": False, "error": str(e), "looking_at_files": artifacts}

    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed.")
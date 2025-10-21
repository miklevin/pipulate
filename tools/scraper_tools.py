# /home/mike/repos/pipulate/tools/scraper_tools.py
import asyncio
import json
import os
import sys
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse
import random
import time

from loguru import logger
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

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
    Performs an advanced browser automation scrape of a single URL using undetected-chromedriver.
    Checks for cached data before initiating a new scrape.
    ...
    """
    url = params.get("url")
    domain = params.get("domain")
    url_path_slug = params.get("url_path_slug")
    take_screenshot = params.get("take_screenshot", False)
    headless = params.get("headless", True)
    is_notebook_context = params.get("is_notebook_context", False)
    persistent = params.get("persistent", False)
    profile_name = params.get("profile_name", "default")
    verbose = params.get("verbose", True)
    delay_range = params.get("delay_range")

    if not all([url, domain, url_path_slug is not None]):
        return {"success": False, "error": "URL, domain, and url_path_slug parameters are required."}

    base_dir = Path("browser_cache/")
    if not is_notebook_context:
        base_dir = base_dir / "looking_at"
    
    output_dir = base_dir / domain / url_path_slug
    artifacts = {}

    # --- IDEMPOTENCY CHECK ---
    # Check if the primary artifact (rendered_dom.html) already exists.
    dom_path = output_dir / "rendered_dom.html"
    if dom_path.exists():
        if verbose:
            logger.info(f"✅ Using cached data from: {output_dir}")
        
        # Gather paths of existing artifacts
        for artifact_name in ["rendered_dom.html", "source_html.txt", "screenshot.png", "dom_layout_boxes.txt", "dom_hierarchy.txt", "accessibility_tree.json", "accessibility_tree_summary.txt"]:
            artifact_path = output_dir / artifact_name
            if artifact_path.exists():
                 artifacts[Path(artifact_name).stem] = str(artifact_path)

        return {"success": True, "looking_at_files": artifacts, "cached": True}

    # --- Fuzzed Delay Logic (only runs if not cached) ---
    if delay_range and isinstance(delay_range, (tuple, list)) and len(delay_range) == 2:
        min_delay, max_delay = delay_range
        if isinstance(min_delay, (int, float)) and isinstance(max_delay, (int, float)) and min_delay <= max_delay:
            delay = random.uniform(min_delay, max_delay)
            if verbose:
                logger.info(f"⏳ Waiting for {delay:.3f} seconds before next request...")
            await asyncio.sleep(delay)
        else:
            logger.warning(f"⚠️ Invalid delay_range provided: {delay_range}. Must be a tuple of two numbers (min, max).")

    driver = None
    profile_path = None
    temp_profile = False

    # --- Find the browser executable path (Platform-Specific) ---
    effective_os = os.environ.get("EFFECTIVE_OS") # This is set by your flake.nix
    browser_path = None
    driver_path = None

    if effective_os == "linux":
        if verbose: logger.info("🐧 Linux platform detected. Looking for Nix-provided Chromium...")
        browser_path = shutil.which("chromium")
        driver_path = shutil.which("undetected-chromedriver")
        if not browser_path:
            browser_path = shutil.which("chromium-browser")
        
        if not browser_path:
            logger.error("❌ Could not find Nix-provided chromium or chromium-browser.")
            return {"success": False, "error": "Chromium executable not found in Nix environment."}
        if not driver_path:
            logger.error("❌ Could not find Nix-provided 'undetected-chromedriver'.")
            return {"success": False, "error": "undetected-chromedriver not found in Nix environment."}

    elif effective_os == "darwin":
        if verbose: logger.info("🍏 macOS platform detected. Looking for host-installed Google Chrome...")
        # On macOS, we rely on the user's host-installed Google Chrome.
        # undetected-chromedriver will use webdriver-manager to find/download the driver.
        browser_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        driver_path = None # This tells uc to find/download the driver automatically

        if not Path(browser_path).exists():
            # Fallback for Chrome Canary
            browser_path_canary = "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary"
            if Path(browser_path_canary).exists():
                browser_path = browser_path_canary
                if verbose: logger.info("  -> Google Chrome not found, using Google Chrome Canary.")
            else:
                logger.error(f"❌ Google Chrome not found at default path: {browser_path}")
                logger.error("   Please install Google Chrome on your Mac to continue.")
                return {"success": False, "error": "Google Chrome not found on macOS."}
        
        # Check if webdriver-manager is installed (it's a dependency of undetected-chromedriver)
        try:
            import webdriver_manager
    Gtk: Gtk-WARNING **: 20:34:04.992: cannot open display:
        except ImportError:
            logger.error("❌ 'webdriver-manager' package not found.")
            logger.error("   Please add 'webdriver-manager' to requirements.txt and re-run 'nix develop'.")
            return {"success": False, "error": "webdriver-manager Python package missing."}
    
    else:
        logger.error(f"❌ Unsupported EFFECTIVE_OS: '{effective_os}'. Check flake.nix.")
        return {"success": False, "error": "Unsupported operating system."}

    if verbose: 
        logger.info(f"🔍 Using browser executable at: {browser_path}")
        if driver_path:
            logger.info(f"🔍 Using driver executable at: {driver_path}")
        else:
            logger.info(f"🔍 Using driver executable from webdriver-manager (uc default).")

    try:
        # Create directory only if we are actually scraping
        output_dir.mkdir(parents=True, exist_ok=True)
        if verbose: logger.info(f"💾 Saving new artifacts to: {output_dir}")

        options = uc.ChromeOptions()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")
        options.add_argument("--window-size=1920,1080")

        if persistent:
            profile_path = Path(f"data/uc_profiles/{profile_name}")
            profile_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"🔒 Using persistent profile: {profile_path}")
        else:
            profile_path = tempfile.mkdtemp(prefix='pipulate_automation_')
            temp_profile = True
            logger.info(f"👻 Using temporary profile: {profile_path}")
        
        logger.info(f"🚀 Initializing undetected-chromedriver (Headless: {headless})...")
        driver = uc.Chrome(options=options, 
                           user_data_dir=str(profile_path), 
                           browser_executable_path=browser_path,
                           driver_executable_path=driver_path)

        logger.info(f"Navigating to: {url}")
        driver.get(url)

        try:
            if verbose: logger.info("Waiting for security challenge to trigger a reload (Stage 1)...")
            initial_body = driver.find_element(By.TAG_NAME, 'body')
            WebDriverWait(driver, 20).until(EC.staleness_of(initial_body))
            if verbose: logger.success("✅ Page reload detected!")
            
            if verbose: logger.info("Waiting for main content to appear after reload (Stage 2)...")
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
            if verbose: logger.success("✅ Main content located!")
        except Exception as e:
            if verbose: logger.warning(f"Did not detect a page reload for security challenge. Proceeding anyway. Error: {e}")

        # --- Capture Core Artifacts ---
        dom_path = output_dir / "rendered_dom.html"
        dom_path.write_text(driver.execute_script("return document.documentElement.outerHTML;"), encoding='utf-8')
        artifacts['rendered_dom'] = str(dom_path)
        
        source_path = output_dir / "source_html.txt"
        source_path.write_text(driver.page_source, encoding='utf-8')
        artifacts['source_html'] = str(source_path)

        if take_screenshot:
            screenshot_path = output_dir / "screenshot.png"
            driver.save_screenshot(str(screenshot_path))
            artifacts['screenshot'] = str(screenshot_path)

        # --- Generate Visualization Artifacts ---
        if verbose: logger.info(f"🎨 Generating DOM box visualization...")
        viz_result = await dom_tools.visualize_dom_boxes({"file_path": str(dom_path), "verbose": False})
        if viz_result.get("success"):
            viz_path = output_dir / "dom_layout_boxes.txt"
            viz_path.write_text(viz_result["output"], encoding='utf-8')
            artifacts['dom_layout_boxes'] = str(viz_path)
        
        if verbose: logger.info(f"🌳 Generating DOM hierarchy visualization...")
        hierarchy_viz_result = await dom_tools.visualize_dom_hierarchy({"file_path": str(dom_path), "verbose": False})
        if hierarchy_viz_result.get("success"):
            hierarchy_viz_path = output_dir / "dom_hierarchy.txt"
            hierarchy_viz_path.write_text(hierarchy_viz_result["output"], encoding='utf-8')
            artifacts['dom_hierarchy'] = str(hierarchy_viz_path)
            
        # --- Generate Accessibility Tree Artifact ---
        if verbose: logger.info("🌲 Extracting accessibility tree...")
        try:
            driver.execute_cdp_cmd("Accessibility.enable", {})
            ax_tree_result = driver.execute_cdp_cmd("Accessibility.getFullAXTree", {})
            ax_tree = ax_tree_result.get("nodes", [])
            ax_tree_path = output_dir / "accessibility_tree.json"
            ax_tree_path.write_text(json.dumps({"success": True, "node_count": len(ax_tree), "accessibility_tree": ax_tree}, indent=2), encoding='utf-8')
            artifacts['accessibility_tree'] = str(ax_tree_path)

            summary_result = await dom_tools.summarize_accessibility_tree({"file_path": str(ax_tree_path)})
            if summary_result.get("success"):
                summary_path = output_dir / "accessibility_tree_summary.txt"
                summary_path.write_text(summary_result["output"], encoding='utf-8')
                artifacts['accessibility_tree_summary'] = str(summary_path)
        except Exception as ax_error:
            logger.warning(f"⚠️ Could not extract accessibility tree: {ax_error}")

        logger.success(f"✅ Scrape successful for {url}")
        return {"success": True, "looking_at_files": artifacts, "cached": False}

    except Exception as e:
        logger.error(f"❌ Scrape failed for {url}: {e}", exc_info=True)
        return {"success": False, "error": str(e), "looking_at_files": artifacts}

    finally:
        if driver:
            driver.quit()
            if verbose: logger.info("Browser closed.")
        if temp_profile and profile_path and os.path.exists(profile_path):
             shutil.rmtree(profile_path)
             if verbose: logger.info(f"Cleaned up temporary profile: {profile_path}")

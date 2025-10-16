# /home/mike/repos/pipulate/tools/scraper_tools.py
import faulthandler
faulthandler.enable()

import asyncio
import json
import os
import sys
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

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
    Supports persistent profiles to maintain sessions across runs.
    Captures artifacts including DOM, source, headers, screenshot, and visual DOM layouts.
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

    if not all([url, domain, url_path_slug is not None]):
        return {"success": False, "error": "URL, domain, and url_path_slug parameters are required."}

    driver = None
    artifacts = {}
    profile_path = None
    temp_profile = False



    # --- Find the browser executable path ---
    browser_path = shutil.which("chromium")
    driver_path = shutil.which("undetected-chromedriver")
    if not browser_path:
        # Fallback for different naming conventions
        browser_path = shutil.which("chromium-browser")

    if not browser_path:
        logger.error("❌ Could not find chromium or chromium-browser executable in the environment's PATH.")
        return {"success": False, "error": "Chromium executable not found. Is it correctly configured in your flake.nix?"}

    if not driver_path:
        logger.error("❌ Could not find 'undetected-chromedriver' executable in the environment's PATH.")
        return {"success": False, "error": "The undetected-chromedriver binary was not found. Is it in your flake.nix?"}
    
    if verbose: 
        logger.info(f"🔍 Found browser executable at: {browser_path}")
        logger.info(f"🔍 Found driver executable at: {driver_path}")


    base_dir = Path("browser_cache/")
    if not is_notebook_context:
        base_dir = base_dir / "looking_at"
    
    output_dir = base_dir / domain / url_path_slug

    try:
        if output_dir.exists():
            if verbose: logger.info(f"🗑️ Clearing existing artifacts in: {output_dir}")
            shutil.rmtree(output_dir)
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
        
        source_path = output_dir / "source_html.text"
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
        return {"success": True, "looking_at_files": artifacts}

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

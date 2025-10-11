# patch.py
patches = [
    {
        "file": "/home/mike/repos/pipulate/tools/scraper_tools.py",
        "block_name": "selenium_automation",
        "new_code": """
        @auto_tool
        async def selenium_automation(params: dict) -> dict:
            \"\"\"
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
            \"\"\"
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
                output_dir = Path("browser_cache/looking_at/") / domain / url_path_slug
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
        """
    },
    {
        "file": "/home/mike/repos/pipulate/pipulate/core.py",
        "block_name": "scrape_method",
        "new_code": """
        async def scrape(self, url: str, take_screenshot: bool = False, mode: str = 'selenium', headless: bool = True, **kwargs):
            \"\"\"
            Gives AI "eyes" by performing browser automation or HTTP requests to scrape a URL.

            This method is the primary entrypoint for scraping and supports multiple modes.
            The default mode is 'selenium' which uses a full browser.

            Args:
                url (str): The URL to scrape.
                take_screenshot (bool): Whether to capture a screenshot (selenium mode only). Defaults to False.
                mode (str): The scraping mode to use ('selenium', 'requests', etc.). Defaults to 'selenium'.
                headless (bool): Whether to run the browser in headless mode (selenium mode only). Defaults to True.
                **kwargs: Additional parameters to pass to the underlying automation tool.

            Returns:
                dict: The result from the scraper tool, including paths to captured artifacts.
            \"\"\"
            from tools.scraper_tools import selenium_automation
            from urllib.parse import urlparse, quote
            from datetime import datetime

            logger.info(f"👁️‍🗨️ Initiating scrape for: {url} (Mode: {mode}, Headless: {headless})")

            # --- New Directory Logic ---
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            path = parsed_url.path or '/'
            # Use quote with an empty safe string to encode everything, including slashes
            url_path_slug = quote(path, safe='')

            params = {
                "url": url,
                "domain": domain,
                "url_path_slug": url_path_slug,
                "take_screenshot": take_screenshot,
                "headless": headless,
                **kwargs # Pass through any other params
            }

            if mode == 'selenium':
                try:
                    result = await selenium_automation(params)
                    return result
                except Exception as e:
                    logger.error(f"❌ Advanced scrape failed for {url}: {e}")
                    return {"success": False, "error": str(e)}
            else:
                logger.warning(f"Scrape mode '{mode}' is not yet implemented.")
                return {"success": False, "error": f"Mode '{mode}' not implemented."}
        """
    },
    {
        "file": "/home/mike/repos/pipulate/Notebooks/Client_Work/faquilizer2/secretsauce.py",
        "block_name": "test_advanced_scrape",
        "new_code": """
        async def test_advanced_scrape(job: str, headless: bool = False):
            \"\"\"
            NEW (Optional Test): Scrapes the FIRST URL from the list using the advanced
            pip.scrape() browser automation to capture a full set of artifacts.
            \"\"\"
            print("\\n--- 🧪 Starting Advanced Scrape Test Flight ---")
            urls_to_process = pip.get(job, URL_LIST_STEP, [])
            if not urls_to_process:
                print("  -> No URLs found to test. Skipping.")
                return
            url_to_test = urls_to_process[0]
            print(f"  -> Target: {url_to_test}")
            print(f"  -> Headless Mode: {headless}")

            # This is the call to the powerful, Selenium-based scraper
            # exposed through the pipulate library, now with headless toggle.
            result = await pip.scrape(url=url_to_test, take_screenshot=True, headless=headless)

            if result.get('success'):
                print(f"  -> ✅ Success! Advanced scrape complete.")
                files_created = result.get('looking_at_files', {})
                print("  -> Artifacts captured in 'browser_cache/looking_at/':")
                for key, path in files_created.items():
                    if path:
                        print(f"       - {key}: {path}")
            else:
                print(f"  -> ❌ Failed: {result.get('error')}")
            print("--- 🧪 Test Flight Complete ---\\n")
        """
    }
]
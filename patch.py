# patch.py
patches = [
    {
        "file": "pipulate/core.py",
        "block_name": "pipulate_init",
        "new_code": """
    def __init__(self, pipeline_table=None, db=None, friendly_names=None, append_func=None, get_profile_id_func=None, get_profile_name_func=None, model=None, chat_instance=None, db_path=None):
        self.chat = chat_instance
        self.friendly_names = friendly_names
        self.append_to_conversation = append_func
        self.get_current_profile_id = get_profile_id_func
        self.get_profile_name = get_profile_name_func
        self.model = model
        self.message_queue = self.OrderedMessageQueue()
        self.is_notebook_context = bool(db_path) # Flag for notebook context
        
        if db_path:
            # Standalone/Notebook Context: Create our "Parallel Universe" DB using fastlite directly
            from fastlite import Database
            from loguru import logger
            logger.info(f"Pipulate initializing in standalone mode with db: {db_path}")
        
            # 1. Create a database connection using fastlite.Database
            db_conn = Database(db_path)
        
            # 2. Access the table handles via the .t property
            l_store = db_conn.t.store
            l_pipeline = db_conn.t.pipeline
            # Note: We don't need to explicitly create tables; fastlite handles it.
        
            self.pipeline_table = l_pipeline
            # The second argument `Store` from fast_app isn't needed by DictLikeDB.
            self.db = DictLikeDB(l_store, None)
        
            # In standalone mode, some features that rely on the server are stubbed out
            if self.append_to_conversation is None: self.append_to_conversation = lambda msg, role: print(f"[{role}] {msg}")
            if self.get_current_profile_id is None: self.get_current_profile_id = lambda: 'standalone'
            if self.get_profile_name is None: self.get_profile_name = lambda: 'standalone'
        
        else:
            # Server Context: Use the objects passed in from server.py
            from loguru import logger
            logger.info("Pipulate initializing in server mode.")
            self.pipeline_table = pipeline_table
            self.db = db
"""
    },
    {
        "file": "pipulate/core.py",
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
            "is_notebook_context": self.is_notebook_context, # Pass the context flag
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
    }
]
# patch.py
# This patch adds the .scrape() method to the Pipulate class in core.py.

patches = [
    {
        "file": "pipulate/core.py",
        "block_name": "notebook_api_methods",
        "new_code": """
    def read(self, job: str) -> dict:
        \"\"\"Reads the entire state dictionary for a given job (pipeline_id).\"\"\"
        state = self.read_state(job)
        state.pop('created', None)
        state.pop('updated', None)
        return state
    
    def write(self, job: str, state: dict):
        \"\"\"Writes an entire state dictionary for a given job (pipeline_id).\"\"\"
        existing_state = self.read_state(job)
        if 'created' in existing_state:
            state['created'] = existing_state['created']
        self.write_state(job, state)

    def set(self, job: str, step: str, value: any):
        \"\"\"Sets a key-value pair within a job's state for notebook usage.\"\"\"
        state = self.read_state(job)
        if not state:
            state = {'created': self.get_timestamp()}

        state[step] = value
        state['updated'] = self.get_timestamp()

        payload = {
            'pkey': job,
            'app_name': 'notebook',
            'data': json.dumps(state),
            'created': state.get('created', state['updated']),
            'updated': state['updated']
        }
        self.pipeline_table.upsert(payload, pk='pkey')
    
    def get(self, job: str, step: str, default: any = None) -> any:
        \"\"\"Gets a value for a key within a job's state.\"\"\"
        state = self.read_state(job)
        return state.get(step, default)

    async def scrape(self, url: str, take_screenshot: bool = False, **kwargs):
        \"\"\"
        Gives AI "eyes" by performing advanced browser automation to scrape a URL.

        This method acts as a simplified bridge to the powerful browser automation
        tools, allowing for direct, on-demand scraping from notebooks or other clients.

        Args:
            url (str): The URL to scrape.
            take_screenshot (bool): Whether to capture a screenshot of the page.
            **kwargs: Additional parameters to pass to the underlying automation tool.

        Returns:
            dict: The result from the browser automation tool, typically including
                  paths to captured artifacts like DOM, source, and screenshot.
        \"\"\"
        from tools.advanced_automation_tools import browser_hijack_workflow_complete
        from urllib.parse import urlparse
        from datetime import datetime

        logger.info(f"👁️‍🗨️ Initiating advanced scrape for: {url}")

        # Create a transient, descriptive pipeline_id for this one-off scrape.
        # This allows us to use the workflow hijacking tool for a simple scrape.
        domain = urlparse(url).netloc
        timestamp = datetime.now().strftime('%H%M%S')
        scrape_pipeline_id = f"scrape-{domain.replace('.', '-')}-{timestamp}"

        params = {
            "url": url,
            "pipeline_id": scrape_pipeline_id,
            "take_screenshot": take_screenshot,
            **kwargs  # Pass through any other params
        }

        try:
            # We call the 'workflow_hijack' tool, but in this context, it's just
            # navigating and capturing artifacts. We bypass the form-filling parts
            # by providing a unique, non-existent pipeline_id.
            result = await browser_hijack_workflow_complete(params)
            return result
        except Exception as e:
            logger.error(f"❌ Advanced scrape failed for {url}: {e}")
            return {"success": False, "error": str(e)}
"""
    }
]
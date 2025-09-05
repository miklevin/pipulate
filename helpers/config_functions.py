# ============================================================================
# SHARED CONFIG FUNCTIONS - Extracted for reuse across modules
# ============================================================================
"""
Shared configuration functions and constants that are used by multiple modules.
These were originally in config.py but are now shared to avoid circular imports.
"""

# URL validation patterns - used in multiple MCP tools for security
INVALID_URL_PATTERNS = [
    'data:',
    'about:',
    'chrome:',
    'file:',
    'javascript:',
    'mailto:',
    'tel:',
    'ftp:'
]

# Botify API helper functions
def get_botify_headers(api_token):
    """Get standard Botify API headers."""
    return {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json"
    }

# Browser automation helper functions
def get_chrome_options():
    """Get standard Chrome options for browser automation."""
    from selenium.webdriver.chrome.options import Options
    chrome_options = Options()

    # VISIBLE BROWSER - The popup is a FEATURE, not a bug!
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--new-window')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')

    return chrome_options

# Common script templates for browser automation
def get_browser_script_imports():
    """Get common import block for generated browser automation scripts."""
    import os
    return f'''import json
import os
import time
import sys
from datetime import datetime
from urllib.parse import urlparse

# Add current directory to path to import modules
sys.path.insert(0, '{os.getcwd()}')'''

# System constants
SERVER_HOST = "localhost"
SERVER_PORT = 5001
SERVER_URL = "http://localhost:5001"
CHAT_ENDPOINT = "/chat"
MCP_ENDPOINT = "/mcp-tool-executor"

# Plugin role system
AVAILABLE_ROLES = {
    'Core': 'Core system functionality and essential workflows',
    'Developer': 'Development tools and debugging utilities',
    'Components': 'UI widget examples and form components',
    'Botify Employee': 'Botify API workflows and data extraction',
    'Tutorial': 'Learning materials and documentation',
    'Workshop': 'Experimental and workshop content'
}

# ============================================================================
# END SHARED CONFIG FUNCTIONS
# ============================================================================

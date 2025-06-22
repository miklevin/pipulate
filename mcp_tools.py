"""
MCP Tools Module - AI Assistant Interface

This module contains all Model Context Protocol (MCP) tools that provide
programmatic interfaces for AI assistant interactions with Pipulate.

Extracted from server.py to improve maintainability and enable
enhanced stealth browser automation capabilities.
"""

import os
import json
import time
import random
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

# Get logger from server context
logger = logging.getLogger(__name__)

# 🔧 FINDER_TOKEN: MCP_TOOLS_CORE - AI ASSISTANT INTERFACE

async def _builtin_get_cat_fact(params: dict) -> dict:
    """
    MCP Tool: Get a random cat fact for testing MCP functionality.
    
    Args:
        params: {} (no parameters required)
    
    Returns:
        dict: {"fact": "Random cat fact", "success": True}
    """
    import random
    
    cat_facts = [
        "Cats have 32 muscles in each ear.",
        "A group of cats is called a clowder.",
        "Cats can't taste sweetness.",
        "A cat's purr vibrates at 25-50 Hz, which can heal bones.",
        "Cats sleep 12-16 hours per day."
    ]
    
    return {
        "success": True,
        "fact": random.choice(cat_facts),
        "timestamp": datetime.now().isoformat()
    }

async def _pipeline_state_inspector(params: dict) -> dict:
    """
    MCP Tool: PIPELINE STATE INSPECTOR - The debugging game changer.
    
    Complete workflow state visibility for AI assistants.
    This is THE tool for understanding what's happening in any workflow.
    
    Args:
        params: {
            "pipeline_id": "hello_001",     # Optional: specific pipeline
            "app_name": "hello",            # Optional: filter by app
            "show_data": True,              # Optional: include step data
            "format": "detailed"            # Optional: "summary" | "detailed"
        }
    
    Returns:
        dict: Complete pipeline state with step data and metadata
    """
    logger.info(f"🔧 FINDER_TOKEN: MCP_PIPELINE_INSPECTOR_START - {params}")
    
    try:
        # Import from server context - use globals to avoid circular import
        import sys
        server_module = sys.modules.get('server')
        if server_module:
            pipeline_table = server_module.pipeline_table
        else:
            # Fallback import if server module not in sys.modules yet
            from server import pipeline_table
        
        pipeline_id = params.get('pipeline_id')
        app_name = params.get('app_name')
        show_data = params.get('show_data', True)
        format_type = params.get('format', 'detailed')
        
        # Get all pipeline records
        all_pipelines = list(pipeline_table())
        
        # Filter by pipeline_id if specified
        if pipeline_id:
            all_pipelines = [p for p in all_pipelines if p.pipeline_id == pipeline_id]
        
        # Filter by app_name if specified
        if app_name:
            all_pipelines = [p for p in all_pipelines if p.pipeline_id.startswith(app_name)]
        
        if not all_pipelines:
            return {
                "success": True,
                "message": "No pipelines found matching criteria",
                "criteria": {"pipeline_id": pipeline_id, "app_name": app_name},
                "total_pipelines": 0
            }
        
        # Process pipeline data
        pipeline_data = []
        for pipeline in all_pipelines:
            try:
                # Parse the state JSON
                state = json.loads(pipeline.state) if pipeline.state else {}
                
                pipeline_info = {
                    "pipeline_id": pipeline.pipeline_id,
                    "created": pipeline.created,
                    "updated": pipeline.updated,
                    "finalized": getattr(pipeline, 'finalized', False),
                    "step_count": len(state) if isinstance(state, dict) else 0
                }
                
                if show_data and format_type == 'detailed':
                    pipeline_info["state"] = state
                elif show_data and format_type == 'summary':
                    # Just show step names and completion status
                    if isinstance(state, dict):
                        step_summary = {}
                        for step_id, step_data in state.items():
                            if isinstance(step_data, dict):
                                step_summary[step_id] = {
                                    "completed": step_data.get('done', False),
                                    "has_data": bool(step_data.get('data'))
                                }
                            else:
                                step_summary[step_id] = {"raw_data": str(step_data)[:100]}
                        pipeline_info["step_summary"] = step_summary
                
                pipeline_data.append(pipeline_info)
                
            except json.JSONDecodeError as e:
                pipeline_data.append({
                    "pipeline_id": pipeline.pipeline_id,
                    "error": f"Invalid JSON in state: {str(e)}",
                    "raw_state": pipeline.state[:200] if pipeline.state else None
                })
        
        result = {
            "success": True,
            "total_pipelines": len(pipeline_data),
            "pipelines": pipeline_data,
            "query_params": {
                "pipeline_id": pipeline_id,
                "app_name": app_name,
                "show_data": show_data,
                "format": format_type
            }
        }
        
        logger.info(f"🎯 FINDER_TOKEN: MCP_PIPELINE_INSPECTOR_SUCCESS - Found {len(pipeline_data)} pipelines")
        return result
        
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: MCP_PIPELINE_INSPECTOR_ERROR - {e}")
        return {"success": False, "error": str(e)}

async def _local_llm_read_file(params: dict) -> dict:
    """
    MCP Tool: Read file contents for AI analysis.
    
    Args:
        params: {
            "file_path": "path/to/file.py",     # Required: file to read
            "start_line": 1,                    # Optional: start line number
            "end_line": 100,                    # Optional: end line number
            "max_lines": 500                    # Optional: max lines to read
        }
    
    Returns:
        dict: File contents and metadata
    """
    logger.info(f"🔧 FINDER_TOKEN: MCP_READ_FILE_START - {params.get('file_path')}")
    
    try:
        file_path = params.get('file_path')
        if not file_path:
            return {"success": False, "error": "file_path parameter is required"}
        
        # Security check - ensure file is within project
        abs_path = os.path.abspath(file_path)
        project_root = os.path.abspath('.')
        if not abs_path.startswith(project_root):
            return {"success": False, "error": "File access outside project directory not allowed"}
        
        if not os.path.exists(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}
        
        start_line = params.get('start_line', 1)
        end_line = params.get('end_line')
        max_lines = params.get('max_lines', 500)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        # Apply line range if specified
        if start_line > 1 or end_line:
            start_idx = max(0, start_line - 1)
            end_idx = min(total_lines, end_line) if end_line else total_lines
            lines = lines[start_idx:end_idx]
        
        # Apply max_lines limit
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            truncated = True
        else:
            truncated = False
        
        content = ''.join(lines)
        
        result = {
            "success": True,
            "file_path": file_path,
            "content": content,
            "total_lines": total_lines,
            "lines_returned": len(lines),
            "truncated": truncated,
            "start_line": start_line,
            "end_line": end_line or total_lines
        }
        
        logger.info(f"🎯 FINDER_TOKEN: MCP_READ_FILE_SUCCESS - {file_path} ({len(lines)} lines)")
        return result
        
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: MCP_READ_FILE_ERROR - {e}")
        return {"success": False, "error": str(e)}

async def _local_llm_grep_logs(params: dict) -> dict:
    """
    MCP Tool: Search logs with FINDER_TOKENs for debugging.
    
    Args:
        params: {
            "pattern": "FINDER_TOKEN: MCP_CALL",  # Required: search pattern
            "file_path": "logs/server.log",       # Optional: specific log file
            "max_results": 50,                    # Optional: max results
            "context_lines": 2                    # Optional: lines before/after
        }
    
    Returns:
        dict: Search results with matches and context
    """
    logger.info(f"🔧 FINDER_TOKEN: MCP_GREP_LOGS_START - Pattern: {params.get('pattern')}")
    
    try:
        pattern = params.get('pattern')
        if not pattern:
            return {"success": False, "error": "pattern parameter is required"}
        
        file_path = params.get('file_path', 'logs/server.log')
        max_results = params.get('max_results', 50)
        context_lines = params.get('context_lines', 2)
        
        if not os.path.exists(file_path):
            return {"success": False, "error": f"Log file not found: {file_path}"}
        
        # Use grep for efficient searching
        try:
            cmd = ['grep', '-n']
            if context_lines > 0:
                cmd.extend(['-C', str(context_lines)])
            cmd.extend([pattern, file_path])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                # Limit results
                if len(lines) > max_results:
                    lines = lines[:max_results]
                    truncated = True
                else:
                    truncated = False
                
                matches = []
                for line in lines:
                    if ':' in line:
                        parts = line.split(':', 2)
                        if len(parts) >= 2:
                            line_num = parts[0]
                            content = ':'.join(parts[1:])
                            matches.append({
                                "line_number": line_num,
                                "content": content.strip()
                            })
                
                return {
                    "success": True,
                    "pattern": pattern,
                    "file_path": file_path,
                    "total_matches": len(matches),
                    "matches": matches,
                    "truncated": truncated
                }
            else:
                return {
                    "success": True,
                    "pattern": pattern,
                    "file_path": file_path,
                    "total_matches": 0,
                    "matches": [],
                    "message": "No matches found"
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Grep search timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "grep command not available"}
        
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: MCP_GREP_LOGS_ERROR - {e}")
        return {"success": False, "error": str(e)}

async def _local_llm_list_files(params: dict) -> dict:
    """
    MCP Tool: List files and directories for exploration.
    
    Args:
        params: {
            "directory": "plugins/",        # Optional: directory to list
            "pattern": "*.py",              # Optional: file pattern
            "recursive": False,             # Optional: recursive listing
            "max_files": 100               # Optional: max files to return
        }
    
    Returns:
        dict: File listing with metadata
    """
    logger.info(f"🔧 FINDER_TOKEN: MCP_LIST_FILES_START - Directory: {params.get('directory', '.')}")
    
    try:
        directory = params.get('directory', '.')
        pattern = params.get('pattern', '*')
        recursive = params.get('recursive', False)
        max_files = params.get('max_files', 100)
        
        if not os.path.exists(directory):
            return {"success": False, "error": f"Directory not found: {directory}"}
        
        files = []
        
        if recursive:
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    if len(files) >= max_files:
                        break
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path)
                    
                    try:
                        stat = os.stat(file_path)
                        files.append({
                            "path": rel_path,
                            "name": filename,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "is_directory": False
                        })
                    except OSError:
                        continue
        else:
            try:
                for entry in os.listdir(directory):
                    if len(files) >= max_files:
                        break
                    
                    entry_path = os.path.join(directory, entry)
                    
                    try:
                        stat = os.stat(entry_path)
                        files.append({
                            "path": entry_path,
                            "name": entry,
                            "size": stat.st_size if not os.path.isdir(entry_path) else None,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "is_directory": os.path.isdir(entry_path)
                        })
                    except OSError:
                        continue
            except PermissionError:
                return {"success": False, "error": f"Permission denied accessing directory: {directory}"}
        
        # Sort by name
        files.sort(key=lambda x: (not x['is_directory'], x['name'].lower()))
        
        result = {
            "success": True,
            "directory": directory,
            "total_files": len(files),
            "files": files,
            "truncated": len(files) >= max_files
        }
        
        logger.info(f"🎯 FINDER_TOKEN: MCP_LIST_FILES_SUCCESS - {directory} ({len(files)} files)")
        return result
        
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: MCP_LIST_FILES_ERROR - {e}")
        return {"success": False, "error": str(e)}

# 🎭 FINDER_TOKEN: ENHANCED_STEALTH_BROWSER_AUTOMATION - THE GOOGLE SEARCH BREAKTHROUGH
async def _browser_stealth_search(params: dict) -> dict:
    """
    MCP Tool: STEALTH SEARCH - Perform searches with proven bot detection evasion.
    
    This tool incorporates all the proven stealth techniques from the successful
    Google "ai seo software" search that bypassed CAPTCHA and extracted results.
    
    Features:
    - Undetected ChromeDriver integration
    - CDP script injection for navigator property cloaking
    - Human-like typing with realistic delays
    - Random mouse movements and scrolling
    - Half-screen window positioning
    - Result extraction with multiple selector fallbacks
    
    Args:
        params: {
            "search_engine": "google",           # Required: "google" (more engines coming)
            "query": "ai seo software",          # Required: search query
            "max_results": 10,                   # Optional: max results to extract
            "take_screenshot": True,             # Optional: capture visual proof
            "save_page_source": True,            # Optional: save full page HTML
            "human_behavior": True               # Optional: simulate human interactions
        }
    
    Returns:
        dict: Search results with titles, URLs, and file locations
    """
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import TimeoutException, WebDriverException
    
    # Try importing stealth libraries
    try:
        import undetected_chromedriver as uc
        UNDETECTED_AVAILABLE = True
    except ImportError:
        UNDETECTED_AVAILABLE = False
    
    try:
        from selenium_stealth import stealth
        STEALTH_AVAILABLE = True
    except ImportError:
        STEALTH_AVAILABLE = False
    
    logger.info(f"🎭 FINDER_TOKEN: STEALTH_SEARCH_START - Query: {params.get('query')}")
    
    try:
        # Extract parameters
        search_engine = params.get('search_engine', 'google').lower()
        query = params.get('query')
        if not query:
            return {"success": False, "error": "Query parameter is required"}
            
        max_results = params.get('max_results', 10)
        take_screenshot = params.get('take_screenshot', True)
        save_page_source = params.get('save_page_source', True)
        human_behavior = params.get('human_behavior', True)
        
        # Set up directories
        browser_automation_dir = 'browser_automation'
        temp_scripts_dir = os.path.join(browser_automation_dir, 'temp_scripts')
        os.makedirs(temp_scripts_dir, exist_ok=True)
        
        # Create timestamp for file naming
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Configure search URL
        if search_engine == 'google':
            search_url = "https://www.google.com"
        else:
            return {"success": False, "error": f"Search engine '{search_engine}' not supported yet"}
        
        # Enhanced stealth browser setup
        logger.info("🎭 FINDER_TOKEN: STEALTH_SETUP - Initializing enhanced bot detection evasion")
        
        if UNDETECTED_AVAILABLE:
            # Use undetected-chromedriver for maximum stealth
            options = uc.ChromeOptions()
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins-discovery')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Half-screen window for human-like appearance
            options.add_argument('--window-size=960,1080')
            options.add_argument('--window-position=0,0')
            
            driver = uc.Chrome(options=options, version_main=None)
            
        else:
            # Fallback to standard Chrome with advanced stealth
            options = webdriver.ChromeOptions()
            
            # Core stealth options
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins-discovery")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-features=VizDisplayCompositor")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            
            # Experimental options for stealth
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # User agent spoofing
            options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Half-screen window for human-like appearance
            options.add_argument('--window-size=960,1080')
            options.add_argument('--window-position=0,0')
            
            driver = webdriver.Chrome(options=options)
            
            # CDP script injection for advanced stealth
            stealth_script = """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            window.chrome = {
                runtime: {},
            };
            
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: () => Promise.resolve({ state: 'granted' }),
                }),
            });
            """
            
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': stealth_script
            })
            
            # Apply selenium-stealth if available
            if STEALTH_AVAILABLE:
                stealth(driver,
                        languages=["en-US", "en"],
                        vendor="Google Inc.",
                        platform="Linux",
                        webgl_vendor="Intel Inc.",
                        renderer="Intel Iris OpenGL Engine",
                        fix_hairline=True,
                )
        
        try:
            # Navigate to search engine
            logger.info(f"🌐 FINDER_TOKEN: STEALTH_NAVIGATE - {search_url}")
            driver.get(search_url)
            
            if human_behavior:
                # Human-like behavior simulation
                time.sleep(random.uniform(0.5, 1.5))
                
                # Random mouse movements
                actions = ActionChains(driver)
                for _ in range(2):
                    x = random.randint(100, 400)
                    y = random.randint(100, 300)
                    actions.move_by_offset(x, y)
                    actions.perform()
                    time.sleep(random.uniform(0.3, 0.8))
                
                # Random scrolling
                driver.execute_script(f"window.scrollTo(0, {random.randint(50, 200)});")
                time.sleep(random.uniform(0.5, 1.0))
            
            # Find search box with multiple selector fallbacks
            wait = WebDriverWait(driver, 10)
            search_selectors = [
                "input[name='q']",
                "textarea[name='q']",
                "#APjFqb",
                ".gLFyf"
            ]
            
            search_box = None
            for selector in search_selectors:
                try:
                    search_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    logger.info(f"🎯 FINDER_TOKEN: SEARCH_BOX_FOUND - Selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not search_box:
                return {"success": False, "error": "Search box not found"}
            
            # Clear and type search query with human-like delays
            search_box.clear()
            time.sleep(random.uniform(0.2, 0.5))
            
            # Type with realistic human delays
            for char in query:
                search_box.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            time.sleep(random.uniform(0.5, 1.0))
            
            # Submit search
            search_box.send_keys(Keys.RETURN)
            
            # Wait for results to load
            time.sleep(3)
            
            # Check for CAPTCHA or blocking
            page_source = driver.page_source.lower()
            if any(indicator in page_source for indicator in ['captcha', 'unusual traffic', 'blocked']):
                logger.warning("🤖 FINDER_TOKEN: CAPTCHA_DETECTED - Bot detection triggered")
                
                if take_screenshot:
                    screenshot_file = os.path.join(temp_scripts_dir, f"captcha_{timestamp}.png")
                    driver.save_screenshot(screenshot_file)
                
                return {
                    "success": False, 
                    "error": "CAPTCHA or bot detection triggered",
                    "screenshot": screenshot_file if take_screenshot else None
                }
            
            # Extract search results with multiple selector fallbacks
            results = []
            result_selectors = [
                "div.g",
                ".g",
                "[data-sokoban-container]",
                ".yuRUbf"
            ]
            
            search_results = []
            for selector in result_selectors:
                try:
                    search_results = driver.find_elements(By.CSS_SELECTOR, selector)
                    if search_results:
                        logger.info(f"🎯 FINDER_TOKEN: RESULTS_FOUND - {len(search_results)} results with selector: {selector}")
                        break
                except:
                    continue
            
            # Extract result information
            for i, result in enumerate(search_results[:max_results]):
                try:
                    # Try to extract title and URL
                    title_elem = result.find_element(By.CSS_SELECTOR, "h3")
                    title = title_elem.text if title_elem else "No title"
                    
                    link_elem = result.find_element(By.CSS_SELECTOR, "a")
                    url = link_elem.get_attribute("href") if link_elem else "No URL"
                    
                    results.append({
                        "position": i + 1,
                        "title": title,
                        "url": url
                    })
                except Exception as e:
                    logger.warning(f"⚠️ FINDER_TOKEN: RESULT_EXTRACTION_ERROR - Position {i+1}: {str(e)}")
                    continue
            
            # Save files
            files_created = {}
            
            if take_screenshot:
                screenshot_file = os.path.join(temp_scripts_dir, f"search_results_{timestamp}.png")
                driver.save_screenshot(screenshot_file)
                files_created['screenshot'] = screenshot_file
            
            if save_page_source:
                source_file = os.path.join(temp_scripts_dir, f"search_source_{timestamp}.html")
                with open(source_file, 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                files_created['page_source'] = source_file
            
            result_data = {
                "success": True,
                "search_engine": search_engine,
                "query": query,
                "results_found": len(results),
                "results": results,
                "files_created": files_created,
                "timestamp": timestamp
            }
            
            logger.info(f"✅ FINDER_TOKEN: STEALTH_SEARCH_SUCCESS - {len(results)} results extracted for '{query}'")
            return result_data
            
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: STEALTH_SEARCH_ERROR - {e}")
        return {"success": False, "error": str(e)}

# MCP Tool Registry - Will be populated by register_mcp_tool calls
MCP_TOOLS = {}

def register_mcp_tool(tool_name: str, handler_func):
    """Register an MCP tool with the global registry."""
    MCP_TOOLS[tool_name] = handler_func
    logger.info(f"🔧 FINDER_TOKEN: MCP_TOOL_REGISTERED - {tool_name}")

# Register all MCP tools
def register_all_mcp_tools():
    """Register all MCP tools in the global registry."""
    
    # Core testing and utilities
    register_mcp_tool("builtin_get_cat_fact", _builtin_get_cat_fact)
    
    # Pipeline and state inspection
    register_mcp_tool("pipeline_state_inspector", _pipeline_state_inspector)
    
    # File and log operations
    register_mcp_tool("local_llm_read_file", _local_llm_read_file)
    register_mcp_tool("local_llm_grep_logs", _local_llm_grep_logs)
    register_mcp_tool("local_llm_list_files", _local_llm_list_files)
    
    # Enhanced stealth browser automation
    register_mcp_tool("browser_stealth_search", _browser_stealth_search)
    
    logger.info(f"🎯 FINDER_TOKEN: MCP_TOOLS_REGISTERED - {len(MCP_TOOLS)} tools available") 
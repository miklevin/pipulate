# patch.py
# This patch fixes hardcoded '.venv/bin/python' paths in advanced_automation_tools.py
# by replacing them with the dynamic and robust `sys.executable`.

patches = [
    {
        "file": "tools/advanced_automation_tools.py",
        "block_name": "browser_hijack_workflow_complete",
        "new_code": """
async def browser_hijack_workflow_complete(params: dict) -> dict:
    \"\"\"
    MCP Tool: COMPLETE WORKFLOW HIJACKING - Navigate + Enter + Chain Reaction + Capture
    
    🎭 "HI JACK" MAGIC WORDS PATTERN - The Irresistible Simple Way
    ═══════════════════════════════════════════════════════════════════════════════════
    SIMPLEST METHOD: Just type "Hi Jack" in chat → Complete hijacking happens automatically
    
    PROGRAMMATIC METHOD for AI understanding:
    python -c "
    import asyncio
    from tools.mcp_tools import browser_hijack_workflow_complete
    result = asyncio.run(browser_hijack_workflow_complete({
        'url': 'http://localhost:5001/hello_workflow',
        'pipeline_id': 'Default_Profile-hello-16'
    }))
    print(f'🎭 Hijack: {result.get(\\"success\\")}')"
    
    This is the common pattern for all session hijacking that handles:
    1. Navigate to workflow URL (e.g., http://localhost:5001/hello_workflow)
    2. Fill in pipeline key input field  
    3. Press Enter to trigger HTMX chain reaction
    4. Wait for chain reaction to complete (all hx_trigger="load" steps)
    5. Capture final workflow state (DOM + screenshot)
    
    This captures the POST-ENTER workflow state, not just the landing page form.
    
    Args:
        params: {
            "url": "http://localhost:5001/hello_workflow",  # Required: Workflow URL
            "pipeline_id": "Default_Profile-hello-16",      # Required: Pipeline key to enter
            "take_screenshot": True                         # Optional: capture visual state
        }
        
        Timing: Uses centralized WorkflowHijackTiming configuration ({WorkflowHijackTiming.total_browser_time()}s total)
        To adjust timing: Change WorkflowHijackTiming class values or apply_timing_preset("lightning"/"fast"/"dramatic")
    
    Returns:
        dict: {
            "success": True,
            "workflow_hijacked": True,
            "chain_reaction_completed": True,
            "url": "http://localhost:5001/hello_workflow",
            "pipeline_id": "Default_Profile-hello-16",
            "looking_at_files": {
                "screenshot": "browser_automation/looking_at/screenshot.png",
                "dom": "browser_automation/looking_at/dom.html",
                "simple_dom": "browser_automation/looking_at/simple_dom.html"
            },
            "hijacking_steps": [
                {"step": "navigation", "status": "success"},
                {"step": "pipeline_key_entry", "status": "success"},
                {"step": "form_submission", "status": "success"},
                {"step": "chain_reaction_wait", "status": "success"},
                {"step": "final_state_capture", "status": "success"}
            ]
        }
    \"\"\"
    import json
    import os
    import asyncio
    import subprocess
    import tempfile
    from datetime import datetime
    from pathlib import Path
    from urllib.parse import urlparse
    import sys  # <-- ADDED IMPORT

    logger.info(f"🎭 FINDER_TOKEN: MCP_WORKFLOW_HIJACK_START - URL: {params.get('url')}, Pipeline: {params.get('pipeline_id')}")
    
    try:
        url = params.get('url')
        pipeline_id = params.get('pipeline_id')
        take_screenshot = params.get('take_screenshot', True)
        
        # Show current timing configuration
        logger.info(f"⏰ FINDER_TOKEN: TIMING_CONFIG - {WorkflowHijackTiming.get_timing_summary()}")
        
        # === VALIDATION ===
        if not url:
            return {"success": False, "error": "URL parameter is required"}
        if not pipeline_id:
            return {"success": False, "error": "pipeline_id parameter is required"}
        
        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            return {"success": False, "error": f"URL must start with http:// or https://. Got: {url}"}
        
        logger.info(f"✅ FINDER_TOKEN: WORKFLOW_HIJACK_VALIDATION_PASSED - URL: {url}, Pipeline: {pipeline_id}")
        
        # === DIRECTORY ROTATION ===
        rotation_success = rotate_looking_at_directory(
            looking_at_path=Path('browser_automation/looking_at'),
            max_rolled_dirs=MAX_ROLLED_LOOKING_AT_DIRS
        )
        
        looking_at_dir = 'browser_automation/looking_at'
        os.makedirs(looking_at_dir, exist_ok=True)
        
        hijacking_steps = []
        
        # === SUBPROCESS WORKFLOW HIJACKING TO AVOID THREADING ISSUES ===
        timing = WorkflowHijackTiming
        page_load_wait = timing.PAGE_LOAD_WAIT
        form_delay = timing.FORM_INTERACTION_DELAY  
        post_wait = timing.POST_REQUEST_WAIT
        chain_wait = timing.CHAIN_REACTION_WAIT
        stabilization = timing.FINAL_STABILIZATION
        human_view = timing.HUMAN_OBSERVATION
        total_time = timing.total_browser_time()
        
        from config import get_browser_script_imports
        hijack_script = f'''
{get_browser_script_imports()}

def run_workflow_hijacking():
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, NoSuchElementException
        from seleniumwire import webdriver as wire_webdriver
        
        target_url = "{url}"
        target_pipeline_id = "{pipeline_id}"
        print(f"🎭 SUBPROCESS: Starting workflow hijacking for {{target_url}} with pipeline {{target_pipeline_id}}")
        
        import tempfile
        from config import get_chrome_options
        chrome_options = get_chrome_options()
        
        profile_dir = tempfile.mkdtemp(prefix='pipulate_workflow_hijack_')
        chrome_options.add_argument(f'--user-data-dir={{profile_dir}}')
        
        driver = wire_webdriver.Chrome(options=chrome_options)
        
        try:
            print(f"🌐 SUBPROCESS: Step 1 - Navigating to {{target_url}}")
            driver.get(target_url)
            time.sleep({page_load_wait})
            print(f"✅ SUBPROCESS: Navigation completed")
            
            print(f"🔑 SUBPROCESS: Step 2 - Looking for pipeline key input field")
            
            pipeline_input = None
            selectors = [
                'input[name="pipeline_id"]', 'input[placeholder*="pipeline"]',
                'input[placeholder*="key"]', 'input[type="text"]',
                '#pipeline_id', '.pipeline-input'
            ]
            
            for selector in selectors:
                try:
                    pipeline_input = driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"✅ SUBPROCESS: Found pipeline input using selector: {{selector}}")
                    break
                except NoSuchElementException:
                    continue
            
            if not pipeline_input:
                return {{"success": False, "error": "Could not find pipeline key input field", "page_title": driver.title, "current_url": driver.current_url}}
            
            pipeline_input.clear()
            pipeline_input.send_keys(target_pipeline_id)
            print(f"🔑 SUBPROCESS: Filled pipeline key: {{target_pipeline_id}}")
            time.sleep({form_delay})
            
            print(f"⚡ SUBPROCESS: Step 3 - Pressing Enter to trigger HTMX chain reaction")
            pipeline_input.send_keys(Keys.RETURN)
            
            print(f"📤 SUBPROCESS: Step 3.5 - Waiting {post_wait}s for POST request + HTMX response...")
            time.sleep({post_wait})
            
            print(f"🔄 SUBPROCESS: Step 4 - Waiting {chain_wait} seconds for HTMX chain reaction to complete")
            
            for i in range({chain_wait}):
                time.sleep(1)
                if i % 2 == 0:
                    try:
                        steps = driver.find_elements(By.CSS_SELECTOR, '[id*="step_"], .card h3, .card h2')
                        print(f"🔄 SUBPROCESS: Chain reaction progress - {{len(steps)}} workflow elements detected")
                    except:
                        print(f"🔄 SUBPROCESS: Chain reaction progress - {{i+1}}/{chain_wait} seconds")
            
            print(f"✅ SUBPROCESS: Chain reaction wait completed")
            
            print(f"⏳ SUBPROCESS: Allowing {stabilization} seconds for workflow stabilization...")
            time.sleep({stabilization})
            
            print(f"📸 SUBPROCESS: Step 5 - Capturing final workflow state")
            
            page_title = driver.title
            current_url = driver.current_url
            
            with open("{looking_at_dir}/source.html", "w", encoding="utf-8") as f: f.write(driver.page_source)
            dom_content = driver.execute_script("return document.documentElement.outerHTML;")
            with open("{looking_at_dir}/dom.html", "w", encoding="utf-8") as f: f.write(dom_content)
            
            simple_dom = f\"\"\"<html>
<head><title>{{page_title}}</title></head>
<body>
{{dom_content}}
</body>
</html>\"\"\"
            
            with open("{looking_at_dir}/simple_dom.html", "w", encoding="utf-8") as f: f.write(simple_dom)
            
            screenshot_saved = False
            if {take_screenshot}:
                driver.save_screenshot("{looking_at_dir}/screenshot.png")
                screenshot_saved = True
            
            headers_data = {{"url": current_url, "original_url": target_url, "title": page_title, "pipeline_id": target_pipeline_id, "timestamp": datetime.now().isoformat(), "hijacking_type": "complete_workflow_chain_reaction", "chain_reaction_wait_seconds": {chain_wait}, "total_browser_time_seconds": {total_time}, "screenshot_taken": screenshot_saved, "status": "success"}}
            
            with open("{looking_at_dir}/headers.json", "w") as f: json.dump(headers_data, f, indent=2)
            
            print(f"👁️ SUBPROCESS: Displaying final state for {human_view} seconds...")
            time.sleep({human_view})
            
            return {{"success": True, "workflow_hijacked": True, "chain_reaction_completed": True, "url": current_url, "original_url": target_url, "pipeline_id": target_pipeline_id, "title": page_title, "timestamp": datetime.now().isoformat(), "screenshot_saved": screenshot_saved}}
            
        finally:
            driver.quit()
            import shutil
            try: shutil.rmtree(profile_dir)
            except: pass
                
    except Exception as e:
        return {{"success": False, "error": str(e)}}

if __name__ == "__main__":
    result = run_workflow_hijacking()
    print(f"SUBPROCESS_RESULT:{{json.dumps(result)}}")
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as script_file:
            script_file.write(hijack_script)
            script_path = script_file.name
        
        try:
            logger.info(f"🔄 FINDER_TOKEN: SUBPROCESS_WORKFLOW_HIJACK_START - Running complete workflow hijacking")
            
            process = await asyncio.create_subprocess_exec(
                sys.executable, script_path,  # <-- FIXED
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {"success": False, "error": "Workflow hijacking timed out after 120 seconds"}
            
            output = stdout.decode('utf-8')
            error_output = stderr.decode('utf-8')
            
            if process.returncode != 0:
                logger.error(f"❌ FINDER_TOKEN: SUBPROCESS_WORKFLOW_HIJACK_ERROR - Return code: {process.returncode}")
                logger.error(f"❌ FINDER_TOKEN: SUBPROCESS_WORKFLOW_HIJACK_STDERR - {error_output}")
                return {"success": False, "error": f"Workflow hijacking subprocess failed: {error_output}"}
            
            result_line = None
            for line in output.split('\\n'):
                if line.startswith('SUBPROCESS_RESULT:'):
                    result_line = line.replace('SUBPROCESS_RESULT:', '')
                    break
            
            if result_line:
                try:
                    subprocess_result = json.loads(result_line)
                    if subprocess_result.get('success'):
                        return {"success": True, "workflow_hijacked": True, "chain_reaction_completed": True, "url": subprocess_result.get('url'), "original_url": url, "pipeline_id": pipeline_id, "title": subprocess_result.get('title'), "timestamp": subprocess_result.get('timestamp'), "looking_at_files": {"headers": f"{looking_at_dir}/headers.json", "source": f"{looking_at_dir}/source.html", "dom": f"{looking_at_dir}/dom.html", "simple_dom": f"{looking_at_dir}/simple_dom.html", "screenshot": f"{looking_at_dir}/screenshot.png" if take_screenshot else None}, "hijacking_steps": [{"step": "navigation", "status": "success", "details": {"url": url}}, {"step": "pipeline_key_entry", "status": "success", "details": {"pipeline_id": pipeline_id}}, {"step": "form_submission", "status": "success", "details": {"method": "enter_key"}}, {"step": "chain_reaction_wait", "status": "success", "details": {"wait_seconds": chain_wait}}, {"step": "final_state_capture", "status": "success", "details": {"files_saved": 4 + (1 if take_screenshot else 0)}}]}
                    else:
                        return {"success": False, "error": subprocess_result.get('error', 'Unknown subprocess error')}
                except json.JSONDecodeError as e:
                    logger.error(f"❌ FINDER_TOKEN: SUBPROCESS_JSON_DECODE_ERROR - {e}")
                    return {"success": False, "error": f"Failed to parse subprocess result: {e}"}
            else:
                logger.error(f"❌ FINDER_TOKEN: SUBPROCESS_NO_RESULT - No result line found in output")
                return {"success": False, "error": "No result found in subprocess output"}
                
        finally:
            try: os.unlink(script_path)
            except: pass
        
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: MCP_WORKFLOW_HIJACK_ERROR - {e}")
        return {"success": False, "error": f"Workflow hijacking failed: {str(e)}"}
"""
    },
    {
        "file": "tools/advanced_automation_tools.py",
        "block_name": "execute_mcp_cli_command",
        "new_code": """
async def execute_mcp_cli_command(params: dict) -> dict:
    \"\"\"
    Execute MCP CLI commands for local LLM access to the unified interface.
    
    This enables the local LLM to use the same CLI interface as external AI assistants.
    The local LLM can execute commands like: mcp execute_automation_recipe --recipe_path ...
    
    Args:
        params (dict): Parameters for CLI command execution
            - tool_name (str): Name of the MCP tool to execute
            - arguments (dict, optional): Key-value pairs for CLI arguments
            - raw_command (str, optional): Raw CLI command to execute
    
    Returns:
        dict: Results of CLI command execution
    \"\"\"
    import subprocess
    import os
    import asyncio
    import sys  # <-- ADDED IMPORT
    
    try:
        # Get parameters
        tool_name = params.get('tool_name')
        arguments = params.get('arguments', {})
        raw_command = params.get('raw_command')
        
        # Build the CLI command
        if raw_command:
            cmd_parts = raw_command.split()
        elif tool_name:
            cmd_parts = [sys.executable, "cli.py", "call", tool_name] # <-- FIXED
            for key, value in arguments.items():
                cmd_parts.extend([f"--{key}", str(value)])
        else:
            cmd_parts = [sys.executable, "helpers/ai_tool_discovery.py", "list"] # <-- FIXED
        
        process = await asyncio.create_subprocess_exec(
            *cmd_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.getcwd()
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise Exception("Command execution timed out after 30 seconds")
        
        stdout_text = stdout.decode('utf-8') if stdout else ""
        stderr_text = stderr.decode('utf-8') if stderr else ""
        
        return {"success": process.returncode == 0, "command": " ".join(cmd_parts), "stdout": stdout_text, "stderr": stderr_text, "return_code": process.returncode, "tool_name": tool_name or "discovery", "interface_type": "cli_unified", "description": "Local LLM executed CLI command via unified interface"}
        
    except Exception as e:
        return {"success": False, "error": str(e), "tool_name": params.get('tool_name', 'unknown'), "interface_type": "cli_unified", "description": "CLI command execution failed"}
"""
    },
    {
        "file": "tools/advanced_automation_tools.py",
        "block_name": "server_reboot",
        "new_code": """
async def server_reboot(params: dict) -> dict:
    \"\"\"
    Gracefully reboot the Pipulate server using the watchdog system.
    
    This tool performs an elegant server restart by:
    1. Checking if the server is currently running
    2. If running, touching server.py to trigger watchdog restart
    3. If not running, falling back to direct start
    4. Verifying the server responds after restart
    
    Args:
        params: Dictionary (no parameters required)
        
    Returns:
        dict: Result of the reboot operation with server verification
    \"\"\"
    try:
        import subprocess
        import asyncio
        import os
        import aiohttp
        from pathlib import Path
        import sys  # <-- ADDED IMPORT
        
        check_process = subprocess.run(['pgrep', '-f', 'python server.py'], capture_output=True, text=True)
        server_was_running = check_process.returncode == 0
        server_pids = check_process.stdout.strip().split('\\n') if server_was_running else []
        
        if server_was_running:
            server_py_path = Path('server.py')
            if server_py_path.exists():
                server_py_path.touch()
                restart_method = "watchdog_triggered"
                restart_details = f"Touched server.py to trigger watchdog restart (PIDs: {', '.join(server_pids)})"
            else:
                return {"success": False, "error": "server.py not found in current directory", "current_directory": os.getcwd(), "message": "Cannot trigger watchdog restart - server.py missing"}
        else:
            start_result = subprocess.Popen([sys.executable, 'server.py'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=os.getcwd(), start_new_session=True) # <-- FIXED
            restart_method = "direct_start"
            restart_details = f"Server was not running, started directly (PID: {start_result.pid})"
        
        await asyncio.sleep(8 if server_was_running else 3)
        
        server_responding = False
        response_status = None
        response_error = None
        
        max_attempts = 5 if server_was_running else 3
        for attempt in range(max_attempts):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get('http://localhost:5001/', timeout=aiohttp.ClientTimeout(total=5)) as response:
                        response_status = response.status
                        if response.status == 200:
                            server_responding = True
                            break
            except Exception as e:
                response_error = str(e)
                if attempt < max_attempts - 1:
                    await asyncio.sleep(1.5 if server_was_running else 2)
        
        return {"success": server_responding, "message": "Server reboot completed successfully" if server_responding else "Server reboot failed - server not responding", "restart_method": restart_method, "restart_details": restart_details, "server_was_running": server_was_running, "server_responding": server_responding, "response_status": response_status, "response_error": response_error, "status": "Graceful restart via watchdog - verified responding" if server_responding and server_was_running else "Direct start - verified responding" if server_responding else "Restart attempted but server not responding"}
        
    except Exception as e:
        return {"success": False, "error": str(e), "message": "Failed to reboot server"}
"""
    }
]
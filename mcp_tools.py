"""
MCP Tools Module - AI Assistant Interface

This module contains all Model Context Protocol (MCP) tools that provide
programmatic interfaces for AI assistant interactions with Pipulate.

Consolidated from server.py to improve maintainability and provide a
clean separation of concerns for AI-focused functionality.

# 🔧 FINDER_TOKEN: MCP_TOOLS_CONSOLIDATED - ALL TOOLS IN ONE PLACE
"""

import os
import json
import time
import random
import asyncio
import subprocess
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

# Get logger from server context
logger = logging.getLogger(__name__)

# ================================================================
# HELPER FUNCTIONS
# ================================================================

def _read_botify_api_token() -> str:
    """Read Botify API token from the standard token file location.
    
    Returns the token string or None if file doesn't exist or can't be read.
    This follows the same pattern used by all other Botify integrations.
    """
    try:
        token_file = "helpers/botify/botify_token.txt"
        if not os.path.exists(token_file):
            return None
        with open(token_file) as f:
            content = f.read().strip()
            token = content.split('\n')[0].strip()
        return token
    except Exception:
        return None

# ================================================================
# CORE MCP TOOLS
# ================================================================

async def _builtin_get_cat_fact(params: dict) -> dict:
    """Built-in cat fact tool - demonstrates the MCP tool pattern."""
    try:
        async with aiohttp.ClientSession() as session:
            external_url = "https://catfact.ninja/fact"
            async with session.get(external_url) as response:
                if response.status == 200:
                    cat_fact_result = await response.json()
                    return {
                        "status": "success",
                        "result": cat_fact_result,
                        "external_api_url": external_url,
                        "external_api_method": "GET",
                        "external_api_status": response.status
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"External API returned status {response.status}",
                        "external_api_url": external_url,
                        "external_api_method": "GET",
                        "external_api_status": response.status
                    }
    except Exception as e:
        # Fallback to local cat facts if API fails
        cat_facts = [
            "Cats have 32 muscles in each ear.",
            "A group of cats is called a clowder.",
            "Cats can't taste sweetness.",
            "A cat's purr vibrates at 25-50 Hz, which can heal bones.",
            "Cats sleep 12-16 hours per day."
        ]
        return {
            "status": "success",
            "fact": random.choice(cat_facts),
            "timestamp": datetime.now().isoformat(),
            "source": "local_fallback"
        }

async def _pipeline_state_inspector(params: dict) -> dict:
    """
    MCP Tool: PIPELINE STATE INSPECTOR - The debugging game changer.
    
    Complete workflow state visibility for AI assistants.
    This is THE tool for understanding what's happening in any workflow.
    """
    logger.info(f"🔧 FINDER_TOKEN: MCP_PIPELINE_INSPECTOR_START - {params}")
    
    try:
        # Use dynamic import to avoid circular dependency
        import sys
        server_module = sys.modules.get('server')
        if server_module and hasattr(server_module, 'pipeline_table'):
            pipeline_table = server_module.pipeline_table
        else:
            # Alternative: use the database directly if pipeline_table not available
            try:
                from fastlite import database
                db = database('data/data.db')
                pipeline_table = db.pipeline
            except Exception:
                return {
                    "success": False,
                    "error": "Pipeline table not accessible - server may not be fully initialized"
                }
        
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

# ================================================================
# BOTIFY API MCP TOOLS
# ================================================================

async def _botify_ping(params: dict) -> dict:
    """Test Botify API connectivity and authentication."""
    api_token = _read_botify_api_token()
    if not api_token:
        return {
            "status": "error", 
            "message": "Botify API token not found. Please ensure helpers/botify/botify_token.txt exists.",
            "token_location": "helpers/botify/botify_token.txt"
        }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Use the user endpoint as a simple ping/auth test
            external_url = "https://api.botify.com/v1/user"
            headers = {"Authorization": f"Token {api_token}"}
            
            async with session.get(external_url, headers=headers) as response:
                if response.status == 200:
                    user_data = await response.json()
                    return {
                        "status": "success",
                        "result": {
                            "message": "Botify API connection successful",
                            "user": user_data.get("login", "unknown"),
                            "organizations": len(user_data.get("organizations", []))
                        },
                        "external_api_url": external_url,
                        "external_api_method": "GET",
                        "external_api_status": response.status
                    }
                else:
                    error_text = await response.text()
                    return {
                        "status": "error",
                        "message": f"Botify API authentication failed: {response.status}",
                        "error_details": error_text,
                        "external_api_url": external_url,
                        "external_api_method": "GET",
                        "external_api_status": response.status
                    }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Network error: {str(e)}",
            "external_api_url": external_url if 'external_url' in locals() else None,
            "external_api_method": "GET"
        }

async def _botify_list_projects(params: dict) -> dict:
    """List all projects for the authenticated user."""
    api_token = _read_botify_api_token()
    if not api_token:
        return {
            "status": "error", 
            "message": "Botify API token not found. Please ensure helpers/botify/botify_token.txt exists.",
            "token_location": "helpers/botify/botify_token.txt"
        }
    
    try:
        async with aiohttp.ClientSession() as session:
            external_url = "https://api.botify.com/v1/projects"
            headers = {"Authorization": f"Token {api_token}"}
            
            async with session.get(external_url, headers=headers) as response:
                if response.status == 200:
                    projects_data = await response.json()
                    projects = projects_data.get("results", [])
                    
                    # Format for easy consumption
                    formatted_projects = []
                    for project in projects:
                        formatted_projects.append({
                            "slug": project.get("slug"),
                            "name": project.get("name"),
                            "url": project.get("url"),
                            "organization": project.get("organization", {}).get("name"),
                            "active": project.get("active", False)
                        })
                    
                    return {
                        "status": "success",
                        "result": {
                            "projects": formatted_projects,
                            "total_count": len(formatted_projects)
                        },
                        "external_api_url": external_url,
                        "external_api_method": "GET",
                        "external_api_status": response.status
                    }
                else:
                    error_text = await response.text()
                    return {
                        "status": "error",
                        "message": f"Failed to fetch projects: {response.status}",
                        "error_details": error_text,
                        "external_api_url": external_url,
                        "external_api_method": "GET",
                        "external_api_status": response.status
                    }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Network error: {str(e)}",
            "external_api_url": external_url if 'external_url' in locals() else None,
            "external_api_method": "GET"
        }

# Additional Botify tools will be added in subsequent edits...

# ================================================================
# MCP TOOL REGISTRY AND REGISTRATION
# ================================================================

# MCP Tool Registry - Will be populated by register_mcp_tool calls
MCP_TOOL_REGISTRY = {}

def register_mcp_tool(tool_name: str, handler_func):
    """Register an MCP tool with the global registry."""
    logger.info(f"🔧 MCP REGISTRY: Registering tool '{tool_name}'")
    MCP_TOOL_REGISTRY[tool_name] = handler_func
    
    # Also register with server if available
    import sys
    server_module = sys.modules.get('server')
    if server_module and hasattr(server_module, 'register_mcp_tool'):
        server_module.register_mcp_tool(tool_name, handler_func)

def register_all_mcp_tools():
    """Register all MCP tools with the server."""
    logger.info("🔧 FINDER_TOKEN: MCP_TOOLS_REGISTRATION_START")
    
    # Core tools
    register_mcp_tool("get_cat_fact", _builtin_get_cat_fact)
    register_mcp_tool("pipeline_state_inspector", _pipeline_state_inspector)
    
    # Botify API tools  
    register_mcp_tool("botify_ping", _botify_ping)
    register_mcp_tool("botify_list_projects", _botify_list_projects)
    register_mcp_tool("botify_simple_query", _botify_simple_query)
    
    # Local LLM tools
    register_mcp_tool("local_llm_read_file", _local_llm_read_file)
    register_mcp_tool("local_llm_grep_logs", _local_llm_grep_logs)
    register_mcp_tool("local_llm_list_files", _local_llm_list_files)
    register_mcp_tool("local_llm_get_context", _local_llm_get_context)
    
    # UI interaction tools (commented out until functions are defined below)
    # register_mcp_tool("ui_flash_element", _ui_flash_element)  
    # register_mcp_tool("ui_list_elements", _ui_list_elements)
    
    # More tools will be registered as we add them...
    
    logger.info(f"🎯 FINDER_TOKEN: MCP_TOOLS_REGISTRATION_COMPLETE - {len(MCP_TOOL_REGISTRY)} tools registered")

# Additional Botify tools from server.py
async def _botify_simple_query(params: dict) -> dict:
    """Execute a simple BQL query against Botify API."""
    api_token = _read_botify_api_token()
    if not api_token:
        return {
            "status": "error",
            "message": "Botify API token not found. Please ensure helpers/botify/botify_token.txt exists.",
            "token_location": "helpers/botify/botify_token.txt"
        }
    
    org_slug = params.get("org_slug") 
    project_slug = params.get("project_slug")
    analysis_slug = params.get("analysis_slug")
    query = params.get("query")
    
    # Validate required parameters
    missing_params = []
    if not org_slug: missing_params.append("org_slug") 
    if not project_slug: missing_params.append("project_slug")
    if not analysis_slug: missing_params.append("analysis_slug")
    if not query: missing_params.append("query")
    
    if missing_params:
        return {
            "status": "error", 
            "message": f"Missing required parameters: {', '.join(missing_params)}",
            "required_params": ["org_slug", "project_slug", "analysis_slug", "query"]
        }
    
    try:
        async with aiohttp.ClientSession() as session:
            external_url = f"https://api.botify.com/v1/projects/{org_slug}/{project_slug}/query"
            headers = {
                "Authorization": f"Token {api_token}",
                "Content-Type": "application/json"
            }
            
            # Build the BQL query payload
            payload = {
                "query": query,
                "analysis": analysis_slug,
                "size": params.get("size", 100)  # Default to 100 results
            }
            
            async with session.post(external_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    query_result = await response.json()
                    return {
                        "status": "success",
                        "result": query_result,
                        "external_api_url": external_url,
                        "external_api_method": "POST", 
                        "external_api_status": response.status,
                        "external_api_payload": payload
                    }
                else:
                    error_text = await response.text()
                    return {
                        "status": "error",
                        "message": f"BQL query failed: {response.status}",
                        "error_details": error_text,
                        "external_api_url": external_url,
                        "external_api_method": "POST",
                        "external_api_status": response.status,
                        "external_api_payload": payload
                    }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Network error: {str(e)}",
            "external_api_url": external_url if 'external_url' in locals() else None,
            "external_api_method": "POST"
        }

# Local LLM tools for file system operations
async def _local_llm_read_file(params: dict) -> dict:
    """Read file contents for AI analysis."""
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
    """Search logs with FINDER_TOKENs for debugging."""
    logger.info(f"🔧 FINDER_TOKEN: MCP_GREP_LOGS_START - {params.get('pattern')}")
    
    try:
        pattern = params.get('pattern')
        if not pattern:
            return {"success": False, "error": "pattern parameter is required"}
        
        file_path = params.get('file_path', 'logs/server.log')
        max_results = params.get('max_results', 50)
        context_lines = params.get('context_lines', 2)
        
        if not os.path.exists(file_path):
            return {"success": False, "error": f"Log file not found: {file_path}"}
        
        # Use grep command for efficient searching
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
                
                return {
                    "success": True,
                    "pattern": pattern,
                    "file_path": file_path,
                    "matches": lines,
                    "match_count": len(lines),
                    "truncated": truncated,
                    "context_lines": context_lines
                }
            else:
                return {
                    "success": True,
                    "pattern": pattern,
                    "file_path": file_path,
                    "matches": [],
                    "match_count": 0,
                    "message": "No matches found"
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Grep operation timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "grep command not found"}
            
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: MCP_GREP_LOGS_ERROR - {e}")
        return {"success": False, "error": str(e)}

async def _local_llm_list_files(params: dict) -> dict:
    """List files and directories for AI exploration."""
    logger.info(f"🔧 FINDER_TOKEN: MCP_LIST_FILES_START - {params.get('directory', '.')}")
    
    try:
        directory = params.get('directory', '.')
        pattern = params.get('pattern', '*')
        include_hidden = params.get('include_hidden', False)
        max_files = params.get('max_files', 100)
        
        # Security check
        abs_path = os.path.abspath(directory)
        project_root = os.path.abspath('.')
        if not abs_path.startswith(project_root):
            return {"success": False, "error": "Directory access outside project not allowed"}
        
        if not os.path.exists(directory):
            return {"success": False, "error": f"Directory not found: {directory}"}
        
        files = []
        dirs = []
        
        try:
            entries = os.listdir(directory)
            for entry in entries:
                if not include_hidden and entry.startswith('.'):
                    continue
                    
                full_path = os.path.join(directory, entry)
                relative_path = os.path.relpath(full_path)
                
                if os.path.isdir(full_path):
                    dirs.append({
                        "name": entry,
                        "path": relative_path,
                        "type": "directory"
                    })
                else:
                    file_size = os.path.getsize(full_path)
                    files.append({
                        "name": entry,
                        "path": relative_path,
                        "type": "file",
                        "size": file_size,
                        "modified": os.path.getmtime(full_path)
                    })
            
            # Sort and limit results
            dirs.sort(key=lambda x: x['name'])
            files.sort(key=lambda x: x['name'])
            
            all_entries = dirs + files
            if len(all_entries) > max_files:
                all_entries = all_entries[:max_files]
                truncated = True
            else:
                truncated = False
            
            return {
                "success": True,
                "directory": directory,
                "entries": all_entries,
                "total_count": len(all_entries),
                "directories": len(dirs),
                "files": len(files),
                "truncated": truncated
            }
            
        except PermissionError:
            return {"success": False, "error": f"Permission denied accessing: {directory}"}
            
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: MCP_LIST_FILES_ERROR - {e}")
        return {"success": False, "error": str(e)}

async def _local_llm_get_context(params: dict) -> dict:
    """Local LLM helper: Get pre-seeded system context for immediate capability awareness"""
    try:
        from pathlib import Path
        import json
        
        context_file = Path('data/local_llm_context.json')
        
        if not context_file.exists():
            return {
                "success": False,
                "error": "Context file not found - system may still be initializing",
                "suggestion": "Wait a few seconds and try again"
            }
        
        with open(context_file, 'r') as f:
            context_data = json.load(f)
        
        logger.info(f"🔍 FINDER_TOKEN: LOCAL_LLM_CONTEXT_ACCESS - Context retrieved for local LLM")
        
        return {
            "success": True,
            "context": context_data,
            "usage_note": "This context provides system overview and available tools for local LLM assistance"
        }
        
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: LOCAL_LLM_CONTEXT_ERROR - {e}")
        return {
            "success": False,
            "error": str(e),
            "suggestion": "Try using other MCP tools or ask user for specific information"
        } 

async def _ui_flash_element(params: dict) -> dict:
    """Flash a UI element by ID to draw user attention.
    
    Args:
        params: Dict containing:
            - element_id: The DOM ID of the element to flash
            - message: Optional message to display in chat
            - delay: Optional delay in milliseconds (default: 0)
    
    Returns:
        Dict with success status and details
    """
    element_id = params.get('element_id', '').strip()
    message = params.get('message', '').strip()
    delay = params.get('delay', 0)
    
    if not element_id:
        return {
            "success": False,
            "error": "element_id is required"
        }
    
    try:
        # Create JavaScript to flash the element 10 times for teaching emphasis
        flash_script = f"""
        <script>
        console.log('🔔 UI Flash script received for element: {element_id} (10x teaching mode)');
        setTimeout(() => {{
            const element = document.getElementById('{element_id}');
            console.log('🔔 Element lookup result:', element);
            if (element) {{
                console.log('🔔 Element found, applying 10x flash effect for teaching');
                
                let flashCount = 0;
                const maxFlashes = 10; // Hardcoded for teaching emphasis
                
                function doFlash() {{
                    if (flashCount >= maxFlashes) {{
                        console.log('🔔 10x Flash sequence completed for: {element_id}');
                        return;
                    }}
                    
                    // Remove and add class for flash effect
                    element.classList.remove('menu-flash');
                    element.offsetHeight; // Force reflow
                    element.classList.add('menu-flash');
                    
                    flashCount++;
                    console.log(`🔔 Flash ${{flashCount}}/10 for: {element_id}`);
                    
                    // Schedule next flash after this one completes
                    setTimeout(() => {{
                        element.classList.remove('menu-flash');
                        // Small gap between flashes for visibility
                        setTimeout(doFlash, 100);
                    }}, 600);
                }}
                
                // Start the 10x flash sequence
                doFlash();
                
            }} else {{
                console.warn('⚠️ Element not found: {element_id}');
                console.log('🔔 Available elements with IDs:', Array.from(document.querySelectorAll('[id]')).map(el => el.id));
            }}
        }}, {delay});
        </script>
        """
        
        # Send the script via chat - use global chat instance
        # The chat instance is available globally after server startup
        import sys
        server_module = sys.modules.get('server')
        if server_module and hasattr(server_module, 'chat'):
            chat = getattr(server_module, 'chat')
            if chat:
                logger.info(f"🔔 UI FLASH: Broadcasting script via global chat for element: {element_id}")
                # Send script to execute the flash
                await chat.broadcast(flash_script)
                
                # Send optional message
                if message:
                    await chat.broadcast(message)
            else:
                logger.warning(f"🔔 UI FLASH: Global chat not available for element: {element_id}")
        else:
            logger.error(f"🔔 UI FLASH: No chat instance available for element: {element_id}")
        
        return {
            "success": True,
            "element_id": element_id,
            "message": message if message else f"Flashed element: {element_id} (10x teaching mode)",
            "delay": delay
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to flash element: {str(e)}"
        }

async def _ui_list_elements(params: dict) -> dict:
    """List common UI element IDs that can be flashed for user guidance.
    
    Returns:
        Dict with categorized UI element IDs and descriptions
    """
    try:
        ui_elements = {
            "navigation": {
                "profile-id": "Profile dropdown menu summary",
                "app-id": "App dropdown menu summary", 
                "nav-plugin-search": "Plugin search input field",
                "search-results-dropdown": "Plugin search results dropdown"
            },
            "chat": {
                "msg-list": "Chat message list container",
                "msg": "Chat input textarea",
                "send-btn": "Send message button",
                "stop-btn": "Stop streaming button"
            },
            "common_workflow_elements": {
                "Note": "These IDs are dynamically generated per workflow:",
                "Examples": [
                    "step_01", "step_02", "step_03", "finalize",
                    "input_data", "process_data", "output_data"
                ]
            },
            "profile_roles": {
                "profiles-list": "Profile list container",
                "roles-list": "Roles list container",
                "default-button": "Reset to default roles button"
            }
        }
        
        return {
            "success": True,
            "ui_elements": ui_elements,
            "note": "Use ui_flash_element tool with any of these IDs to guide users"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to list UI elements: {str(e)}"
        }

async def _browser_analyze_scraped_page(params: dict) -> dict:
    """
    MCP Tool: AI BRAIN - Analyze current /looking_at/ page state for automation opportunities.
    
    Analyzes the current page state captured in /browser_automation/looking_at/
    to identify automation targets, form elements, and interaction opportunities.
    
    Args:
        params: {
            "analysis_type": "form_elements" | "navigation" | "automation_targets" | "all",
            "use_backup_id": "domain_com_2025-01-11_14-30-15"  # Optional: analyze backup instead
        }
    
    Returns:
        dict: Analysis results with actionable automation data
    """
    logger.info(f"🔧 FINDER_TOKEN: MCP_BROWSER_ANALYZE_START - Analysis: {params.get('analysis_type', 'automation_targets')}")
    
    try:
        analysis_type = params.get('analysis_type', 'automation_targets')
        backup_id = params.get('use_backup_id')
        
        # Determine which HTML file to analyze
        if backup_id:
            # Analyze backup file
            html_file = f"downloads/browser_scrapes/{backup_id}/simple_dom.html"
            if not os.path.exists(html_file):
                return {"success": False, "error": f"Backup HTML not found for backup_id: {backup_id}"}
        else:
            # Analyze current /looking_at/ state
            html_file = "browser_automation/looking_at/simple_dom.html"
            if not os.path.exists(html_file):
                return {"success": False, "error": "No current page state found. Use browser_scrape_page first to capture page state."}
        
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
        except ImportError:
            return {"success": False, "error": "BeautifulSoup not available for HTML parsing"}
        
        if analysis_type == "form_elements":
            # Find all forms and their elements
            forms = []
            for form in soup.find_all('form'):
                form_data = {
                    'id': form.get('id'),
                    'action': form.get('action'),
                    'method': form.get('method', 'GET'),
                    'elements': []
                }
                
                for element in form.find_all(['input', 'button', 'select', 'textarea']):
                    element_data = {
                        'tag': element.name,
                        'type': element.get('type'),
                        'id': element.get('id'),
                        'name': element.get('name'),
                        'aria_label': element.get('aria-label'),
                        'data_testid': element.get('data-testid'),
                        'placeholder': element.get('placeholder'),
                        'text': element.get_text(strip=True)
                    }
                    form_data['elements'].append(element_data)
                    
                forms.append(form_data)
                
            result = {
                "success": True,
                "analysis_type": analysis_type,
                "forms": forms,
                "form_count": len(forms)
            }
            
        elif analysis_type == "automation_targets":
            # Find all elements with automation-friendly attributes
            targets = []
            for element in soup.find_all():
                if element.get('id') or element.get('data-testid') or element.get('aria-label'):
                    target = {
                        'tag': element.name,
                        'id': element.get('id'),
                        'data_testid': element.get('data-testid'),
                        'aria_label': element.get('aria-label'),
                        'role': element.get('role'),
                        'text': element.get_text(strip=True)[:100],  # First 100 chars
                        'selector_priority': 'high' if element.get('data-testid') else 'medium' if element.get('id') else 'low'
                    }
                    targets.append(target)
                    
            result = {
                "success": True,
                "analysis_type": analysis_type,
                "automation_targets": targets,
                "target_count": len(targets),
                "high_priority_targets": len([t for t in targets if t['selector_priority'] == 'high'])
            }
            
        elif analysis_type == "all":
            # Comprehensive analysis - all types
            all_results = {}
            
            # Forms analysis
            forms = []
            for form in soup.find_all('form'):
                form_data = {
                    'id': form.get('id'),
                    'action': form.get('action'),
                    'method': form.get('method', 'GET'),
                    'elements': []
                }
                
                for element in form.find_all(['input', 'button', 'select', 'textarea']):
                    element_data = {
                        'tag': element.name,
                        'type': element.get('type'),
                        'id': element.get('id'),
                        'name': element.get('name'),
                        'aria_label': element.get('aria-label'),
                        'data_testid': element.get('data-testid'),
                        'placeholder': element.get('placeholder'),
                        'text': element.get_text(strip=True)
                    }
                    form_data['elements'].append(element_data)
                    
                forms.append(form_data)
            
            # Automation targets
            targets = []
            for element in soup.find_all():
                if element.get('id') or element.get('data-testid') or element.get('aria-label'):
                    target = {
                        'tag': element.name,
                        'id': element.get('id'),
                        'data_testid': element.get('data-testid'),
                        'aria_label': element.get('aria-label'),
                        'role': element.get('role'),
                        'text': element.get_text(strip=True)[:100],
                        'selector_priority': 'high' if element.get('data-testid') else 'medium' if element.get('id') else 'low'
                    }
                    targets.append(target)
            
            result = {
                "success": True,
                "analysis_type": "comprehensive",
                "forms": forms,
                "form_count": len(forms),
                "automation_targets": targets,
                "target_count": len(targets),
                "high_priority_targets": len([t for t in targets if t['selector_priority'] == 'high']),
                "analyzed_file": html_file
            }
            
        else:
            result = {"success": False, "error": f"Unknown analysis_type: {analysis_type}"}
            
        logger.info(f"🎯 FINDER_TOKEN: MCP_BROWSER_ANALYZE_SUCCESS - {result.get('target_count', 0)} targets, {result.get('form_count', 0)} forms")
        return result
        
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: MCP_BROWSER_ANALYZE_ERROR - {e}")
        return {"success": False, "error": str(e)}


async def _browser_scrape_page(params: dict) -> dict:
    """
    MCP Tool: AI EYES - Scrape a web page and save to /looking_at/ for AI perception.
    
    This is the AI's primary sensory interface - captures current browser state
    into the /browser_automation/looking_at/ directory for AI analysis.
    
    Saves to /looking_at/:
    - headers.json - HTTP headers and metadata
    - source.html - Raw page source before JavaScript  
    - dom.html - Full JavaScript-rendered DOM state (HTMX and all)
    - simple_dom.html - Distilled DOM for context window consumption
    - screenshot.png - Visual representation (if enabled)
    
    Args:
        params: {
            "url": "https://example.com",  # Required: URL to scrape
            "wait_seconds": 3,             # Optional: wait for JS to load
            "take_screenshot": True,       # Optional: capture visual state
            "update_looking_at": True      # Optional: update /looking_at/ directory
        }
    
    Returns:
        dict: {
            "success": True,
            "url": "https://example.com",
            "looking_at_files": {
                "headers": "browser_automation/looking_at/headers.json",
                "source": "browser_automation/looking_at/source.html", 
                "dom": "browser_automation/looking_at/dom.html",
                "simple_dom": "browser_automation/looking_at/simple_dom.html",
                "screenshot": "browser_automation/looking_at/screenshot.png"
            },
            "page_info": {
                "title": "Page Title",
                "url": "https://example.com",
                "timestamp": "2025-01-11T14:30:15"
            }
        }
    """
    import json
    import os
    import time
    from datetime import datetime
    from urllib.parse import urlparse

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from seleniumwire import webdriver as wire_webdriver
    
    logger.info(f"🔧 FINDER_TOKEN: MCP_BROWSER_SCRAPE_START - URL: {params.get('url')}")
    
    try:
        url = params.get('url')
        wait_seconds = params.get('wait_seconds', 3)
        take_screenshot = params.get('take_screenshot', True)
        update_looking_at = params.get('update_looking_at', True)
        
        if not url:
            return {"success": False, "error": "URL parameter is required"}
            
        # Set up the /looking_at/ directory - AI's primary perception interface
        looking_at_dir = 'browser_automation/looking_at'
        os.makedirs(looking_at_dir, exist_ok=True)
        
        # Also create timestamped backup in downloads for history
        parsed = urlparse(url)
        domain_safe = parsed.netloc.replace('.', '_').replace(':', '_')
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        scrape_id = f"{domain_safe}_{timestamp}"
        backup_dir = os.path.join('downloads/browser_scrapes', scrape_id)
        os.makedirs(backup_dir, exist_ok=True)
        
        # Set up Selenium Wire for header capture
        chrome_options = Options()
        # Use headless unless screenshot is requested
        if not take_screenshot:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        driver = wire_webdriver.Chrome(options=chrome_options)
        
        try:
            # Navigate and wait
            driver.get(url)
            time.sleep(wait_seconds)
            
            # Capture page info
            page_title = driver.title
            final_url = driver.current_url
            
            # 1. Capture HTTP headers and metadata
            headers_data = {
                'url': final_url,
                'title': page_title,
                'timestamp': datetime.now().isoformat(),
                'request_headers': {},
                'response_headers': {},
                'status_code': None
            }
            
            for request in driver.requests:
                if request.url == url:
                    headers_data.update({
                        'request_headers': dict(request.headers),
                        'response_headers': dict(request.response.headers) if request.response else {},
                        'status_code': request.response.status_code if request.response else None
                    })
                    break
            
            # 2. Capture page source (before JavaScript execution)
            source_html = driver.page_source
                
            # 3. Capture post-JavaScript DOM (full HTMX state)
            dom_html = driver.execute_script("return document.documentElement.outerHTML;")
                
            # 4. Create simplified DOM for AI context window consumption
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(dom_html, 'html.parser')
                
                # Remove unwanted elements that clutter AI context
                for tag in soup(['script', 'style', 'noscript', 'meta', 'link']):
                    tag.decompose()
                    
                # Keep only automation-friendly attributes
                for element in soup.find_all():
                    attrs_to_keep = {}
                    for attr, value in element.attrs.items():
                        if attr in ['id', 'role', 'data-testid', 'name', 'type', 'href', 'src'] or attr.startswith('aria-'):
                            attrs_to_keep[attr] = value
                    element.attrs = attrs_to_keep
                    
                simple_dom_html = str(soup)
            except ImportError:
                # Fallback if BeautifulSoup not available
                simple_dom_html = dom_html
            
            # 5. Take screenshot if requested
            screenshot_file = None
            if take_screenshot:
                screenshot_file = os.path.join(looking_at_dir, 'screenshot.png')
                driver.save_screenshot(screenshot_file)
                # Also save backup
                driver.save_screenshot(os.path.join(backup_dir, 'screenshot.png'))
            
            # Save all files to /looking_at/ directory (AI's primary perception)
            looking_at_files = {}
            
            if update_looking_at:
                # Headers
                headers_file = os.path.join(looking_at_dir, 'headers.json')
                with open(headers_file, 'w') as f:
                    json.dump(headers_data, f, indent=2)
                looking_at_files['headers'] = headers_file
                
                # Source HTML
                source_file = os.path.join(looking_at_dir, 'source.html')
                with open(source_file, 'w', encoding='utf-8') as f:
                    f.write(source_html)
                looking_at_files['source'] = source_file
                
                # DOM HTML
                dom_file = os.path.join(looking_at_dir, 'dom.html')
                with open(dom_file, 'w', encoding='utf-8') as f:
                    f.write(dom_html)
                looking_at_files['dom'] = dom_file
                
                # Simple DOM
                simple_dom_file = os.path.join(looking_at_dir, 'simple_dom.html')
                with open(simple_dom_file, 'w', encoding='utf-8') as f:
                    f.write(simple_dom_html)
                looking_at_files['simple_dom'] = simple_dom_file
                
                # Create beautiful DOM with automation registry using AI DOM Beautifier
                try:
                    from ai_dom_beautifier import AIDOMBeautifier
                    beautifier = AIDOMBeautifier()
                    beautiful_dom, automation_registry = beautifier.beautify_dom(simple_dom_html)
                    
                    # Save beautified DOM and automation registry
                    beautiful_dom_file = os.path.join(looking_at_dir, 'beautiful_dom.html')
                    with open(beautiful_dom_file, 'w', encoding='utf-8') as f:
                        f.write(beautiful_dom)
                    looking_at_files['beautiful_dom'] = beautiful_dom_file
                    
                    automation_registry_file = os.path.join(looking_at_dir, 'automation_registry.json')
                    with open(automation_registry_file, 'w', encoding='utf-8') as f:
                        f.write(beautifier.export_automation_registry('json'))
                    looking_at_files['automation_registry'] = automation_registry_file
                    
                    automation_targets_file = os.path.join(looking_at_dir, 'automation_targets.py')
                    with open(automation_targets_file, 'w', encoding='utf-8') as f:
                        f.write(beautifier._export_python_registry())
                    looking_at_files['automation_targets'] = automation_targets_file
                    
                    automation_summary_file = os.path.join(looking_at_dir, 'automation_summary.txt')
                    with open(automation_summary_file, 'w', encoding='utf-8') as f:
                        f.write(beautifier._export_summary())
                    looking_at_files['automation_summary'] = automation_summary_file
                    
                    high_priority_count = len([t for t in automation_registry if t.priority_score >= 70])
                    logger.info(f"🎯 FINDER_TOKEN: AUTOMATION_REGISTRY_CREATED - Found {len(automation_registry)} targets, {high_priority_count} high priority")
                    
                except Exception as e:
                    logger.warning(f"⚠️ FINDER_TOKEN: AUTOMATION_REGISTRY_FAILED - {e}")
                    # Continue without automation registry if there's an error
                
                if screenshot_file:
                    looking_at_files['screenshot'] = screenshot_file
            
            # Also save backup copies for history
            with open(os.path.join(backup_dir, 'headers.json'), 'w') as f:
                json.dump(headers_data, f, indent=2)
            with open(os.path.join(backup_dir, 'source.html'), 'w', encoding='utf-8') as f:
                f.write(source_html)
            with open(os.path.join(backup_dir, 'dom.html'), 'w', encoding='utf-8') as f:
                f.write(dom_html)
            with open(os.path.join(backup_dir, 'simple_dom.html'), 'w', encoding='utf-8') as f:
                f.write(simple_dom_html)
                
        finally:
            driver.quit()
            
        result = {
            "success": True,
            "url": final_url,
            "looking_at_files": looking_at_files,
            "backup_id": scrape_id,
            "backup_dir": backup_dir,
            "page_info": {
                "title": page_title,
                "url": final_url,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        logger.info(f"🎯 FINDER_TOKEN: MCP_BROWSER_SCRAPE_SUCCESS - AI can now see: {final_url}")
        logger.info(f"🎯 FINDER_TOKEN: MCP_BROWSER_PERCEPTION_UPDATE - Files in /looking_at/: {list(looking_at_files.keys())}")
        return result
        
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: MCP_BROWSER_SCRAPE_ERROR - {e}")
        return {"success": False, "error": str(e)}


async def _browser_automate_workflow_walkthrough(params: dict) -> dict:
    """
    MCP Tool: AI HANDS - Complete Workflow Automation Walkthrough
    
    This is the AI's motor interface - uses browser automation to walk through
    entire plugin workflows from start to finish. Updates /looking_at/ directory
    at each step for continuous AI perception.
    
    The ultimate test of automation readiness - actually USING the improved components
    and providing real-time feedback on automation success/failure.
    """
    try:
        import tempfile
        import time
        from pathlib import Path

        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
        
        plugin_filename = params.get("plugin_filename", "")
        base_url = params.get("base_url", "http://localhost:5001")
        take_screenshots = params.get("take_screenshots", True)
        
        if not plugin_filename:
            return {"success": False, "error": "plugin_filename is required"}
            
        logger.info(f"🚀 FINDER_TOKEN: WORKFLOW_AUTOMATION_START | Starting workflow walkthrough for {plugin_filename}")
        
        # Set up Chrome with visible browser
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(options=options)
        driver.maximize_window()
        
        screenshots = []
        workflow_steps = []
        
        # Helper function to update /looking_at/ during automation
        def update_looking_at_state(step_name: str):
            """Update /looking_at/ directory with current browser state"""
            try:
                looking_at_dir = 'browser_automation/looking_at'
                os.makedirs(looking_at_dir, exist_ok=True)
                
                # Capture current state
                current_url = driver.current_url
                page_title = driver.title
                source_html = driver.page_source
                dom_html = driver.execute_script("return document.documentElement.outerHTML;")
                
                # Save state files
                state_data = {
                    'step': step_name,
                    'url': current_url,
                    'title': page_title,
                    'timestamp': datetime.now().isoformat()
                }
                
                with open(os.path.join(looking_at_dir, 'headers.json'), 'w') as f:
                    json.dump(state_data, f, indent=2)
                    
                with open(os.path.join(looking_at_dir, 'source.html'), 'w', encoding='utf-8') as f:
                    f.write(source_html)
                    
                with open(os.path.join(looking_at_dir, 'dom.html'), 'w', encoding='utf-8') as f:
                    f.write(dom_html)
                
                # Create simple DOM
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(dom_html, 'html.parser')
                    for tag in soup(['script', 'style', 'noscript', 'meta', 'link']):
                        tag.decompose()
                    for element in soup.find_all():
                        attrs_to_keep = {}
                        for attr, value in element.attrs.items():
                            if attr in ['id', 'role', 'data-testid', 'name', 'type', 'href', 'src'] or attr.startswith('aria-'):
                                attrs_to_keep[attr] = value
                        element.attrs = attrs_to_keep
                    simple_dom_html = str(soup)
                except:
                    simple_dom_html = dom_html
                    
                with open(os.path.join(looking_at_dir, 'simple_dom.html'), 'w', encoding='utf-8') as f:
                    f.write(simple_dom_html)
                
                # Take screenshot
                driver.save_screenshot(os.path.join(looking_at_dir, 'screenshot.png'))
                
                logger.info(f"🎯 FINDER_TOKEN: AUTOMATION_PERCEPTION_UPDATE - Step: {step_name}, URL: {current_url}")
                
            except Exception as e:
                logger.warning(f"⚠️ FINDER_TOKEN: AUTOMATION_PERCEPTION_ERROR - {e}")
        
        try:
            # Step 1: Navigate to the plugin
            plugin_name = plugin_filename.replace('.py', '').replace('_', '-')
            # Remove numeric prefix for URL
            if plugin_name[0].isdigit():
                plugin_name = '-'.join(plugin_name.split('-')[1:])
            
            plugin_url = f"{base_url}/{plugin_name}"
            logger.info(f"🌐 FINDER_TOKEN: WORKFLOW_NAVIGATION | Navigating to {plugin_url}")
            
            driver.get(plugin_url)
            
            # Update /looking_at/ with landing page state
            update_looking_at_state("landing")
            
            if take_screenshots:
                screenshot_path = f"workflow_step_01_landing.png"
                driver.save_screenshot(screenshot_path)
                screenshots.append(screenshot_path)
                logger.info(f"📸 FINDER_TOKEN: WORKFLOW_SCREENSHOT | Captured landing page")
            
            # Step 2: Wait for page load and look for pipeline input
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            workflow_steps.append({
                "step": "landing",
                "status": "success",
                "description": "Successfully loaded plugin landing page"
            })
            
            # Step 3: Look for and fill pipeline ID input
            try:
                pipeline_input = driver.find_element(By.NAME, "pipeline_id")
                pipeline_id = f"automation-test-{int(time.time())}"
                pipeline_input.clear()
                pipeline_input.send_keys(pipeline_id)
                
                logger.info(f"📝 FINDER_TOKEN: WORKFLOW_INPUT | Entered pipeline ID: {pipeline_id}")
                
                # Submit the form
                submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
                submit_button.click()
                
                workflow_steps.append({
                    "step": "init",
                    "status": "success", 
                    "description": f"Initialized workflow with ID: {pipeline_id}"
                })
                
                # Wait for workflow to load
                time.sleep(3)
                
                # Update /looking_at/ with initialized state
                update_looking_at_state("initialized")
                
                if take_screenshots:
                    screenshot_path = f"workflow_step_02_initialized.png"
                    driver.save_screenshot(screenshot_path)
                    screenshots.append(screenshot_path)
                    
            except Exception as e:
                logger.warning(f"⚠️ FINDER_TOKEN: WORKFLOW_INIT_SKIP | No pipeline input found, continuing: {e}")
                workflow_steps.append({
                    "step": "init",
                    "status": "skipped",
                    "description": "No pipeline initialization needed"
                })
            
            # Step 4: Look for file input and upload test file
            try:
                # Look for file input using our automation attribute
                file_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='file-upload-widget-file-input']")
                logger.info(f"📁 FINDER_TOKEN: WORKFLOW_FILE_INPUT | Found file input with automation attribute")
                
                # Create a test file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                    temp_file.write(f"Test file content for automation walkthrough\\nGenerated at: {time.ctime()}\\nPlugin: {plugin_filename}")
                    test_file_path = temp_file.name
                
                # Upload the test file
                file_input.send_keys(test_file_path)
                logger.info(f"📤 FINDER_TOKEN: WORKFLOW_FILE_UPLOAD | Uploaded test file: {test_file_path}")
                
                # Look for upload button using automation attribute
                upload_button = driver.find_element(By.CSS_SELECTOR, "[data-testid='file-upload-widget-upload-button']")
                upload_button.click()
                logger.info(f"🎯 FINDER_TOKEN: WORKFLOW_SUBMIT | Clicked upload button")
                
                # Wait for processing
                time.sleep(5)
                
                # Update /looking_at/ with post-upload state
                update_looking_at_state("file_uploaded")
                
                if take_screenshots:
                    screenshot_path = f"workflow_step_03_uploaded.png"
                    driver.save_screenshot(screenshot_path)
                    screenshots.append(screenshot_path)
                
                workflow_steps.append({
                    "step": "file_upload",
                    "status": "success",
                    "description": f"Successfully uploaded file using automation attributes"
                })
                
                # Clean up test file
                try:
                    Path(test_file_path).unlink()
                except:
                    pass
                    
            except Exception as e:
                logger.warning(f"⚠️ FINDER_TOKEN: WORKFLOW_FILE_SKIP | File upload step failed: {e}")
                workflow_steps.append({
                    "step": "file_upload",
                    "status": "failed",
                    "description": f"File upload failed: {str(e)}"
                })
            
            # Final state update and screenshot
            update_looking_at_state("workflow_complete")
            
            if take_screenshots:
                screenshot_path = f"workflow_final_state.png"
                driver.save_screenshot(screenshot_path)
                screenshots.append(screenshot_path)
            
            logger.info(f"✅ FINDER_TOKEN: WORKFLOW_AUTOMATION_SUCCESS | Completed walkthrough of {plugin_filename}")
            
            return {
                "success": True,
                "plugin": plugin_filename,
                "workflow_steps": workflow_steps,
                "screenshots": screenshots,
                "total_steps": len(workflow_steps),
                "successful_steps": len([s for s in workflow_steps if s["status"] == "success"])
            }
            
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: WORKFLOW_AUTOMATION_ERROR | {e}")
        return {"success": False, "error": str(e)}


# Register UI tools NOW that functions are defined
register_mcp_tool("ui_flash_element", _ui_flash_element)
register_mcp_tool("ui_list_elements", _ui_list_elements)

async def _botify_get_full_schema(params: dict) -> dict:
    """Discover complete Botify API schema using the true_schema_discoverer.py module.
    
    This tool fetches the comprehensive schema from Botify's official datamodel endpoints,
    providing access to all 4,449+ fields for building advanced queries. Implements intelligent
    caching for instant access to support "radical transparency" AI context bootstrapping.
    """
    # Read API token from standard location (never pass as parameter)
    api_token = _read_botify_api_token()
    if not api_token:
        return {
            "status": "error",
            "message": "Botify API token not found. Please ensure helpers/botify/botify_token.txt exists.",
            "token_location": "helpers/botify/botify_token.txt"
        }
    
    org = params.get("org")
    project = params.get("project")
    analysis = params.get("analysis")
    force_refresh = params.get("force_refresh", False)
    
    # Validate required parameters (token no longer required as param)
    missing_params = []
    if not org: missing_params.append("org")
    if not project: missing_params.append("project")
    if not analysis: missing_params.append("analysis")
    
    if missing_params:
        return {
            "status": "error",
            "message": f"Missing required parameters: {', '.join(missing_params)}",
            "required_params": ["org", "project", "analysis"]
        }
    
    # Implement intelligent caching for instant schema access
    try:
        import json
        from datetime import datetime, timedelta
        from pathlib import Path

        # Define cache file path
        cache_dir = Path("downloads/botify_schema_cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{org}_{project}_{analysis}_schema.json"
        
        # Check if cached file exists and is recent (within 24 hours)
        if cache_file.exists() and not force_refresh:
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                
                # Check cache age
                cache_timestamp = datetime.fromisoformat(cached_data.get("cache_metadata", {}).get("cached_at", "1970-01-01"))
                cache_age = datetime.now() - cache_timestamp
                
                if cache_age < timedelta(hours=24):
                    # Return fresh cached data
                    cached_data["cache_metadata"]["cache_hit"] = True
                    cached_data["cache_metadata"]["cache_age_hours"] = round(cache_age.total_seconds() / 3600, 2)
                    
                    return {
                        "status": "success",
                        "result": cached_data,
                        "external_api_method": "GET",
                        "summary": {
                            "total_fields_discovered": cached_data.get("total_fields_discovered", 0),
                            "collections_discovered": len(cached_data.get("collections_discovered", [])),
                            "discovery_timestamp": cached_data.get("project_info", {}).get("discovery_timestamp"),
                            "cache_used": True,
                            "cache_age_hours": round(cache_age.total_seconds() / 3600, 2)
                        }
                    }
            except (json.JSONDecodeError, KeyError, ValueError):
                # Cache file corrupted, proceed with fresh discovery
                pass
        
        # Perform live schema discovery
        from helpers.botify.true_schema_discoverer import \
            BotifySchemaDiscoverer

        # Create discoverer instance
        discoverer = BotifySchemaDiscoverer(org, project, analysis, api_token)
        
        # Execute the discovery
        schema_results = await discoverer.discover_complete_schema()
        
        # Add cache metadata
        schema_results["cache_metadata"] = {
            "cached_at": datetime.now().isoformat(),
            "cache_hit": False,
            "org": org,
            "project": project,
            "analysis": analysis
        }
        
        # Save to cache for future use
        try:
            with open(cache_file, 'w') as f:
                json.dump(schema_results, f, indent=2)
        except Exception as cache_error:
            # Don't fail the main operation if caching fails
            logger.warning(f"Failed to save schema cache: {cache_error}")
        
        return {
            "status": "success",
            "result": schema_results,
            "external_api_method": "GET",
            "summary": {
                "total_fields_discovered": schema_results.get("total_fields_discovered", 0),
                "collections_discovered": len(schema_results.get("collections_discovered", [])),
                "discovery_timestamp": schema_results.get("project_info", {}).get("discovery_timestamp"),
                "cache_used": False,
                "cache_saved": cache_file.exists()
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Schema discovery error: {str(e)}",
            "org": org,
            "project": project,
            "analysis": analysis
        }

async def _botify_list_available_analyses(params: dict) -> dict:
    """List available analyses from the local analyses.json file.
    
    This tool reads the cached analyses data to help LLMs select the correct
    analysis_slug for queries without requiring live API calls.
    """
    username = params.get("username", "michaellevin-org")
    project_name = params.get("project_name", "mikelev.in")
    
    try:
        # Construct the path to the analyses.json file
        from pathlib import Path
        analyses_path = Path(f"downloads/quadfecta/{username}/{project_name}/analyses.json")
        
        if not analyses_path.exists():
            return {
                "status": "error",
                "message": f"Analyses file not found at {analyses_path}",
                "file_path": str(analyses_path)
            }
        
        # Read and parse the analyses file
        with open(analyses_path, 'r') as f:
            import json
            analyses_data = json.load(f)
        
        # Extract simplified analysis info for LLM consumption
        analyses_list = []
        for analysis in analyses_data.get("results", []):
            analyses_list.append({
                "slug": analysis.get("slug"),
                "name": analysis.get("name"),
                "date_finished": analysis.get("date_finished"),
                "urls_done": analysis.get("urls_done", 0),
                "status": analysis.get("status"),
                "id": analysis.get("id")
            })
        
        # Sort by date_finished (most recent first)
        analyses_list.sort(key=lambda x: x.get("date_finished", ""), reverse=True)
        
        return {
            "status": "success",
            "result": {
                "analyses": analyses_list,
                "total_count": len(analyses_list),
                "file_path": str(analyses_path),
                "most_recent": analyses_list[0] if analyses_list else None
            },
            "summary": {
                "total_analyses": len(analyses_list),
                "file_checked": str(analyses_path)
            }
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Error reading analyses: {str(e)}",
            "username": username,
            "project_name": project_name,
            "attempted_path": str(analyses_path) if 'analyses_path' in locals() else None
        }

async def _botify_execute_custom_bql_query(params: dict) -> dict:
    """Execute a custom BQL query with full parameter control.
    
    This is the core 'query wizard' tool that enables LLMs to construct and execute
    sophisticated BQL queries with custom dimensions, metrics, and filters.
    """
    # Read API token from standard location (never pass as parameter)
    api_token = _read_botify_api_token()
    if not api_token:
        return {
            "status": "error",
            "message": "Botify API token not found. Please ensure helpers/botify/botify_token.txt exists.",
            "token_location": "helpers/botify/botify_token.txt"
        }
    
    org_slug = params.get("org_slug")
    project_slug = params.get("project_slug") 
    analysis_slug = params.get("analysis_slug")
    query_json = params.get("query_json")
    
    # Validate required parameters (token no longer required as param)
    missing_params = []
    if not org_slug: missing_params.append("org_slug")
    if not project_slug: missing_params.append("project_slug")
    if not analysis_slug: missing_params.append("analysis_slug")
    if not query_json: missing_params.append("query_json")
    
    if missing_params:
        return {
            "status": "error",
            "message": f"Missing required parameters: {', '.join(missing_params)}",
            "required_params": ["org_slug", "project_slug", "analysis_slug", "query_json"]
        }
    
    # Validate query_json structure
    if not isinstance(query_json, dict):
        return {
            "status": "error", 
            "message": "query_json must be a dictionary containing the BQL query structure"
        }
    
    try:
        async with aiohttp.ClientSession() as session:
            external_url = f"https://api.botify.com/v1/projects/{org_slug}/{project_slug}/query"
            headers = {
                "Authorization": f"Token {api_token}",
                "Content-Type": "application/json"
            }
            
            # Build the complete payload with analysis
            payload = dict(query_json)  # Copy the query structure
            payload["analysis"] = analysis_slug
            
            # Set default size if not specified
            if "size" not in payload:
                payload["size"] = 100
            
            async with session.post(external_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    query_result = await response.json()
                    
                    # Extract result summary for easier consumption
                    result_summary = {
                        "total_results": len(query_result.get("results", [])),
                        "has_pagination": "next" in query_result,
                        "query_size_requested": payload.get("size", 100)
                    }
                    
                    return {
                        "status": "success",
                        "result": query_result,
                        "result_summary": result_summary,
                        "external_api_url": external_url,
                        "external_api_method": "POST",
                        "external_api_status": response.status,
                        "external_api_payload": payload,
                        "query_info": {
                            "org": org_slug,
                            "project": project_slug,
                            "analysis": analysis_slug,
                            "query_type": "custom_bql"
                        }
                    }
                else:
                    error_text = await response.text()
                    return {
                        "status": "error",
                        "message": f"Custom BQL query failed: {response.status}",
                        "error_details": error_text,
                        "external_api_url": external_url,
                        "external_api_method": "POST",
                        "external_api_status": response.status,
                        "external_api_payload": payload,
                        "query_info": {
                            "org": org_slug,
                            "project": project_slug,
                            "analysis": analysis_slug
                        }
                    }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Network error: {str(e)}",
            "external_api_url": external_url if 'external_url' in locals() else None,
            "external_api_method": "POST",
            "query_info": {
                "org": org_slug,
                "project": project_slug,
                "analysis": analysis_slug
            }
        }

# Register remaining Botify tools NOW that functions are defined
register_mcp_tool("botify_get_full_schema", _botify_get_full_schema)
register_mcp_tool("botify_list_available_analyses", _botify_list_available_analyses)
register_mcp_tool("botify_execute_custom_bql_query", _botify_execute_custom_bql_query)
register_mcp_tool("browser_analyze_scraped_page", _browser_analyze_scraped_page)
register_mcp_tool("browser_scrape_page", _browser_scrape_page)
register_mcp_tool("browser_automate_workflow_walkthrough", _browser_automate_workflow_walkthrough)



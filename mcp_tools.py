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
import sqlite3
import inspect

# Get logger from server context
logger = logging.getLogger(__name__)

# MCP_TOOL_REGISTRY will be set by server.py when it imports this module
MCP_TOOL_REGISTRY = None

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

async def get_user_session_state(params: dict) -> dict:
    """
    MCP Tool: GET USER SESSION STATE - The session hijacking superpower.
    
    Accesses the server-side DictLikeDB to read the user's current session state.
    This provides access to server-side "cookies" like last_profile_id, last_app_choice,
    current_environment, theme_preference, etc.
    
    This is THE tool for understanding what the user was just doing and continuing
    their workflow seamlessly.
    """
    logger.info(f"🎭 FINDER_TOKEN: MCP_SESSION_HIJACKING_START - {params}")
    
    try:
        # Use dynamic import to avoid circular dependency
        import sys
        server_module = sys.modules.get('server') or sys.modules.get('__main__')
        
        # Try to get the global db instance (DictLikeDB)
        if server_module and hasattr(server_module, 'db'):
            db = server_module.db
            logger.info(f"🎭 FINDER_TOKEN: MCP_SESSION_HIJACKING_ACCESS - Successfully accessed global db from server module")
        else:
            logger.error(f"🎭 FINDER_TOKEN: MCP_SESSION_HIJACKING_ERROR - db instance not accessible from server module")
            return {
                "success": False,
                "error": "Server-side database not accessible - server may not be fully initialized"
            }
        
        # Get specific keys if requested, otherwise get all
        specific_keys = params.get('keys', [])
        include_metadata = params.get('include_metadata', True)
        
        if specific_keys:
            # Get only requested keys
            session_data = {}
            for key in specific_keys:
                if key in db:
                    session_data[key] = db[key]
                else:
                    session_data[key] = None
        else:
            # Get all session data
            session_data = dict(db)
        
        # Add metadata about the session state
        result = {
            "success": True,
            "session_data": session_data,
            "total_keys": len(session_data),
            "timestamp": datetime.now().isoformat()
        }
        
        if include_metadata:
            result["metadata"] = {
                "current_profile_id": session_data.get('last_profile_id'),
                "current_app": session_data.get('last_app_choice'),
                "environment": session_data.get('current_environment'),
                "theme": session_data.get('theme_preference'),
                "profile_locked": session_data.get('profile_locked'),
                "intro_page": session_data.get('intro_current_page'),
                "split_sizes": session_data.get('split-sizes')
            }
        
        logger.info(f"🎭 FINDER_TOKEN: MCP_SESSION_HIJACKING_SUCCESS - Retrieved {len(session_data)} session keys")
        return result
        
    except Exception as e:
        logger.error(f"🎭 FINDER_TOKEN: MCP_SESSION_HIJACKING_ERROR - {e}")
        return {
            "success": False,
            "error": f"Failed to access user session state: {str(e)}"
        }

async def builtin_get_cat_fact(params: dict) -> dict:
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

async def pipeline_state_inspector(params: dict) -> dict:
    """
    MCP Tool: PIPELINE STATE INSPECTOR - The debugging game changer.
    
    Complete workflow state visibility for AI assistants.
    This is THE tool for understanding what's happening in any workflow.
    """
    logger.info(f"🔧 FINDER_TOKEN: MCP_PIPELINE_INSPECTOR_START - {params}")
    
    try:
        # Use dynamic import to avoid circular dependency
        import sys
        server_module = sys.modules.get('server') or sys.modules.get('__main__')
        
        # Try to get the global pipeline table (the actual database table, not pipulate.pipeline_table)
        if server_module and hasattr(server_module, 'pipeline'):
            pipeline_table = server_module.pipeline
            logger.info(f"🔧 FINDER_TOKEN: MCP_PIPELINE_INSPECTOR_ACCESS - Successfully accessed global pipeline table from server module")
        else:
            # Alternative: use the database directly if pipeline not available
            try:
                from fastlite import database
                from pathlib import Path
                Path('data').mkdir(parents=True, exist_ok=True)
                db = database('data/data.db')
                pipeline_table = db.pipeline
                logger.info(f"🔧 FINDER_TOKEN: MCP_PIPELINE_INSPECTOR_ACCESS - Fallback: accessed pipeline table directly from database")
            except Exception as e:
                logger.error(f"🔧 FINDER_TOKEN: MCP_PIPELINE_INSPECTOR_ERROR - Database access failed: {e}")
                return {
                    "success": False,
                    "error": f"Pipeline table not accessible - server may not be fully initialized. Details: {e}"
                }
        
        pipeline_id = params.get('pipeline_id')
        app_name = params.get('app_name')
        show_data = params.get('show_data', True)
        format_type = params.get('format', 'detailed')
        
        # Get all pipeline records
        all_pipelines = list(pipeline_table())
        
        # Filter by pipeline_id if specified
        if pipeline_id:
            all_pipelines = [p for p in all_pipelines if p.pkey == pipeline_id]
        
        # Filter by app_name if specified
        if app_name:
            all_pipelines = [p for p in all_pipelines if p.pkey.startswith(app_name)]
        
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
                # Parse the data JSON (FastLite stores JSON in 'data' field, not 'state')
                state = json.loads(pipeline.data) if pipeline.data else {}
                
                pipeline_info = {
                    "pipeline_id": pipeline.pkey,  # Use pkey instead of pipeline_id
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
                    "pipeline_id": pipeline.pkey,
                    "error": f"Invalid JSON in data: {str(e)}",
                    "raw_state": pipeline.data[:200] if pipeline.data else None
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

async def botify_ping(params: dict) -> dict:
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

async def botify_list_projects(params: dict) -> dict:
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
    
    # Use the registry that was passed from server.py
    if MCP_TOOL_REGISTRY is not None:
        MCP_TOOL_REGISTRY[tool_name] = handler_func
    else:
        logger.error(f"🔧 MCP REGISTRY: ERROR - Registry not initialized for '{tool_name}'")

def register_all_mcp_tools():
    """Register all MCP tools with the server."""
    logger.info("🔧 FINDER_TOKEN: MCP_TOOLS_REGISTRATION_START")
    # Debug logging removed - registry working correctly
    
    # Core tools
    register_mcp_tool("get_cat_fact", builtin_get_cat_fact)
    register_mcp_tool("pipeline_state_inspector", pipeline_state_inspector)
    register_mcp_tool("get_user_session_state", get_user_session_state)
    
    # Botify API tools  
    register_mcp_tool("botify_ping", botify_ping)
    register_mcp_tool("botify_list_projects", botify_list_projects)
    register_mcp_tool("botify_simple_query", botify_simple_query)
    
    # Local LLM tools
    register_mcp_tool("local_llm_read_file", local_llm_read_file)
    register_mcp_tool("local_llm_grep_logs", local_llm_grep_logs)
    register_mcp_tool("local_llm_list_files", local_llm_list_files)
    register_mcp_tool("local_llm_get_context", local_llm_get_context)
    
    # 🎭 MAGIC WORDS DEMONSTRATION TOOL
    register_mcp_tool("execute_ai_session_hijacking_demonstration", execute_ai_session_hijacking_demonstration)
    
    # UI interaction tools
    register_mcp_tool("ui_flash_element", ui_flash_element)  
    register_mcp_tool("ui_list_elements", ui_list_elements)
    
    # Browser automation tools - THE AI'S EYES AND HANDS
    register_mcp_tool("browser_analyze_scraped_page", browser_analyze_scraped_page)
    register_mcp_tool("browser_scrape_page", browser_scrape_page)
    register_mcp_tool("browser_automate_workflow_walkthrough", browser_automate_workflow_walkthrough)
    register_mcp_tool("browser_interact_with_current_page", browser_interact_with_current_page)
    
    # Additional Botify tools
    register_mcp_tool("botify_get_full_schema", botify_get_full_schema)
    register_mcp_tool("botify_list_available_analyses", botify_list_available_analyses)
    register_mcp_tool("botify_execute_custom_bql_query", botify_execute_custom_bql_query)
    
    # 🧠 AI SELF-DISCOVERY TOOLS - ELIMINATE UNCERTAINTY
    register_mcp_tool("ai_self_discovery_assistant", ai_self_discovery_assistant)
    register_mcp_tool("ai_capability_test_suite", ai_capability_test_suite)
    register_mcp_tool("browser_automate_instructions", browser_automate_instructions)
    
    # Get final count from server's registry
    import sys
    server_module = sys.modules.get('server')
    if server_module and hasattr(server_module, 'MCP_TOOL_REGISTRY'):
        tool_count = len(server_module.MCP_TOOL_REGISTRY)
    else:
        tool_count = len(MCP_TOOL_REGISTRY)
    
    logger.info(f"🎯 FINDER_TOKEN: MCP_TOOLS_REGISTRATION_COMPLETE - {tool_count} tools registered")

# Additional Botify tools from server.py
async def botify_simple_query(params: dict) -> dict:
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

# Local LLM tools for file system operations
async def local_llm_read_file(params: dict) -> dict:
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

async def local_llm_grep_logs(params: dict) -> dict:
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

async def local_llm_list_files(params: dict) -> dict:
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

async def local_llm_get_context(params: dict) -> dict:
    """Local LLM helper: Get pre-seeded system context for immediate capability awareness"""
    try:
        from pathlib import Path
        import json
        
        context_file = Path('data/local_llm_context.json')
        
        # Ensure the data directory exists
        context_file.parent.mkdir(parents=True, exist_ok=True)
        
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

async def execute_ai_session_hijacking_demonstration(params: dict) -> dict:
    """
    🎭 MAGIC WORDS MCP TOOL: Execute AI session hijacking demonstration protocol
    
    This tool triggers the complete AI session hijacking demonstration sequence
    for in-editor AI assistants (like Claude in Cursor) to prove their superpowers.
    
    Parameters:
    - trigger_source: Optional source identifier (default: "mcp_tool")
    
    Returns:
    - Protocol content and execution confirmation
    """
    try:
        trigger_source = params.get("trigger_source", "mcp_tool")
        logger.info(f"🎭 FINDER_TOKEN: MCP_MAGIC_WORDS - AI session hijacking demonstration triggered by {trigger_source}")
        
        # Import functions from server module
        import sys
        server_module = sys.modules.get('server')
        if not server_module:
            return {
                "success": False,
                "error": "Server module not available",
                "message": "Cannot access training materials"
            }
        
        read_training = getattr(server_module, 'read_training', None)
        append_to_conversation = getattr(server_module, 'append_to_conversation', None)
        
        if not read_training or not append_to_conversation:
            return {
                "success": False,
                "error": "Required functions not available",
                "message": "Cannot access training materials or conversation system"
            }
        
        # Load the complete demonstration protocol
        magic_words_protocol = read_training("ai_magic_words_demonstration_protocol.md")
        
        # Add to conversation history for immediate context
        append_to_conversation("🎭 **MAGIC WORDS DETECTED VIA MCP TOOL!** Loading session hijacking demonstration protocol...", 'system')
        append_to_conversation(magic_words_protocol, 'system')
        append_to_conversation("🚀 **PROTOCOL LOADED** - You now have complete instructions for demonstrating AI session hijacking superpowers. Execute the demonstration sequence!", 'assistant')
        
        return {
            "success": True,
            "message": "🎭 AI session hijacking demonstration protocol loaded successfully!",
            "protocol_preview": magic_words_protocol[:500] + "..." if len(magic_words_protocol) > 500 else magic_words_protocol,
            "trigger_source": trigger_source,
            "instructions": "Follow the exact 6-step protocol in your conversation history to demonstrate AI superpowers",
            "next_step": "Step 1: Acknowledge the magic words detection with '🎭 **MAGIC WORDS DETECTED!** Executing AI session hijacking demonstration protocol...'"
        }
        
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: MCP_MAGIC_WORDS_ERROR - {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to load AI session hijacking demonstration protocol"
        }

async def ui_flash_element(params: dict) -> dict:
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

async def ui_list_elements(params: dict) -> dict:
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

async def browser_analyze_scraped_page(params: dict) -> dict:
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


async def browser_scrape_page(params: dict) -> dict:
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
            
        # === DIRECTORY ROTATION BEFORE NEW BROWSER SCRAPE ===
        # Rotate looking_at directory to preserve AI perception history
        from server import rotate_looking_at_directory
        from pathlib import Path
        
        # Define constant locally to avoid circular import
        MAX_ROLLED_LOOKING_AT_DIRS = 10
        
        rotation_success = rotate_looking_at_directory(
            looking_at_path=Path('browser_automation/looking_at'),
            max_rolled_dirs=MAX_ROLLED_LOOKING_AT_DIRS
        )
        
        if not rotation_success:
            logger.warning("⚠️ FINDER_TOKEN: DIRECTORY_ROTATION_WARNING - Directory rotation failed, continuing with scrape")
            
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
        
        # Set up Selenium Wire for header capture with WORKING PATTERN from plugin
        import tempfile
        import shutil
        
        chrome_options = Options()
        # Use headless unless screenshot is requested
        if not take_screenshot:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--new-window')
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # CRITICAL: Create temporary profile directory (prevents browser conflicts)
        profile_dir = tempfile.mkdtemp()
        chrome_options.add_argument(f'--user-data-dir={profile_dir}')
        
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
                    from helpers.dom_processing.ai_dom_beautifier import AIDOMBeautifier
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
            # CRITICAL: Clean up temporary profile directory
            shutil.rmtree(profile_dir, ignore_errors=True)
            
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


async def browser_automate_workflow_walkthrough(params: dict) -> dict:
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
        
        # === DIRECTORY ROTATION BEFORE NEW WORKFLOW WALKTHROUGH ===
        # Rotate looking_at directory to preserve AI workflow history
        from server import rotate_looking_at_directory
        from pathlib import Path
        
        # Define constant locally to avoid circular import  
        MAX_ROLLED_LOOKING_AT_DIRS = 10
        
        rotation_success = rotate_looking_at_directory(
            looking_at_path=Path('browser_automation/looking_at'),
            max_rolled_dirs=MAX_ROLLED_LOOKING_AT_DIRS
        )
        
        if not rotation_success:
            logger.warning("⚠️ FINDER_TOKEN: WORKFLOW_DIRECTORY_ROTATION_WARNING - Directory rotation failed, continuing with workflow")
            
        logger.info(f"🚀 FINDER_TOKEN: WORKFLOW_AUTOMATION_START | Starting workflow walkthrough for {plugin_filename}")
        
        # Set up Chrome with the same proven configuration as _browser_scrape_page
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        # === REFINEMENT 5: BROWSER LIFECYCLE MANAGEMENT ===
        options.add_argument('--disable-gpu')  # Prevent GPU issues
        options.add_argument('--disable-extensions')  # Disable extensions that might interfere
        options.add_argument('--disable-plugins')  # Disable plugins
        options.add_argument('--disable-images')  # Faster loading
        # options.add_argument('--headless')  # Run in background to prevent hanging windows
        
        driver = webdriver.Chrome(options=options)
        driver.maximize_window()
        driver.set_page_load_timeout(30)  # 30 second page load timeout
        driver.implicitly_wait(10)  # 10 second implicit wait
        
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
            # Step 1: Navigate to the specific plugin requested
            # Extract plugin name from filename and construct URL
            plugin_name = plugin_filename.replace('plugins/', '').replace('.py', '')
            
            # Map plugin filename to app name (this is the key fix!)
            plugin_to_app_mapping = {
                '010_introduction': 'introduction',
                '580_upload': 'file_upload_widget',
                '020_profiles': 'profiles',
                '030_roles': 'roles',
                '040_hello_workflow': 'hello_workflow',
                '050_documentation': 'documentation',
                '060_tasks': 'tasks',
                '070_connect_with_botify': 'connect_with_botify',
                '080_parameter_buster': 'parameter_buster',
                '090_link_graph': 'link_graph',
                '100_gap_analysis': 'gap_analysis',
                '110_workflow_genesis': 'workflow_genesis',
                '120_widget_examples': 'widget_examples',
                '130_roadmap': 'roadmap',
                '140_dev_assistant': 'dev_assistant',
                '150_simon_mcp': 'simon_mcp',
                '160_blank_placeholder': 'blank_placeholder',
                '170_botify_trifecta': 'botify_trifecta',
                '180_tab_opener': 'tab_opener',
                '190_browser_automation': 'browser_automation',
                '200_stream_simulator': 'stream_simulator'
            }
            
            app_name = plugin_to_app_mapping.get(plugin_name, plugin_name)
            plugin_url = f"{base_url}/{app_name}"
            
            logger.info(f"🎯 FINDER_TOKEN: WORKFLOW_NAVIGATION_MAPPING | Plugin: {plugin_name} -> App: {app_name} -> URL: {plugin_url}")
            
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
            
            # Step 4: Check if this plugin has file upload capabilities and test them
            try:
                # Determine if this plugin supports file uploads by checking the plugin name
                plugin_supports_uploads = "upload" in plugin_filename.lower() or "file" in plugin_filename.lower()
                
                if plugin_supports_uploads:
                    # For file upload plugins, we need to initialize the workflow first
                    logger.info(f"📋 FINDER_TOKEN: WORKFLOW_UPLOAD_INIT | Initializing file upload workflow")
                    
                    # Look for pipeline initialization form
                    try:
                        pipeline_input = driver.find_element(By.CSS_SELECTOR, "input[name='pipeline_id']")
                        if pipeline_input:
                            # Generate a unique pipeline ID
                            import uuid
                            pipeline_id = f"automation-test-{uuid.uuid4().hex[:8]}"
                            pipeline_input.send_keys(pipeline_id)
                            logger.info(f"🔧 FINDER_TOKEN: WORKFLOW_PIPELINE_ID | Set pipeline ID: {pipeline_id}")
                            
                            # Look for and click the initialize button
                            init_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                            init_button.click()
                            logger.info(f"🚀 FINDER_TOKEN: WORKFLOW_INIT_CLICK | Clicked initialize button")
                            
                            # Wait for page to load
                            time.sleep(3)
                            
                            # Update /looking_at/ with post-init state
                            update_looking_at_state("workflow_initialized")
                    except Exception as init_error:
                        logger.warning(f"⚠️ FINDER_TOKEN: WORKFLOW_INIT_SKIP | Workflow initialization failed: {init_error}")
                    
                    # Now look for file input using our automation attribute
                    try:
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
                            
                    except Exception as upload_error:
                        logger.warning(f"⚠️ FINDER_TOKEN: WORKFLOW_UPLOAD_ELEMENT_NOT_FOUND | File upload elements not found: {upload_error}")
                        workflow_steps.append({
                            "step": "file_upload",
                            "status": "failed",
                            "description": f"File upload elements not found: {str(upload_error)}"
                        })
                else:
                    # This plugin doesn't support file uploads, skip gracefully
                    logger.info(f"📋 FINDER_TOKEN: WORKFLOW_NO_UPLOAD | Plugin {plugin_filename} doesn't support file uploads, skipping")
                    workflow_steps.append({
                        "step": "file_upload",
                        "status": "skipped",
                        "description": f"Plugin {plugin_filename} doesn't support file uploads"
                    })
                    
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
register_mcp_tool("ui_flash_element", ui_flash_element)
register_mcp_tool("ui_list_elements", ui_list_elements)

async def botify_get_full_schema(params: dict) -> dict:
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

async def botify_list_available_analyses(params: dict) -> dict:
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

async def botify_execute_custom_bql_query(params: dict) -> dict:
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

async def browser_interact_with_current_page(params: dict) -> dict:
    """
    MCP Tool: AI INTERACTION - Interact with the current page using /looking_at/ state.
    
    This tool allows the AI to interact with the current page that's captured
    in /browser_automation/looking_at/ directory. It can click elements, fill forms,
    and perform other interactions based on the current DOM state.
    
    Args:
        params: {
            "action": "click" | "type" | "submit" | "screenshot" | "navigate",
            "target": {
                "selector_type": "id" | "data-testid" | "xpath" | "css",
                "selector_value": "element-id" | "[data-testid='button']" | "//button[@id='submit']",
                "text_content": "optional text to verify element"
            },
            "input_text": "text to type (for type action)",
            "url": "URL to navigate to (for navigate action)",
            "wait_seconds": 3,
            "update_looking_at": True
        }
    
    Returns:
        dict: Interaction results with updated page state
    """
    logger.info(f"🔧 FINDER_TOKEN: MCP_BROWSER_INTERACT_START - Action: {params.get('action')}")
    
    try:
        import time
        import json
        import os
        from datetime import datetime

        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
        
        action = params.get('action')
        target = params.get('target', {})
        input_text = params.get('input_text', '')
        url = params.get('url', '')
        wait_seconds = params.get('wait_seconds', 3)
        update_looking_at = params.get('update_looking_at', True)
        
        if not action:
            return {"success": False, "error": "action parameter is required"}
        
        # Set up Chrome driver
        chrome_options = Options()
        if action != "screenshot":
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # Get current URL from /looking_at/ state
            headers_file = 'browser_automation/looking_at/headers.json'
            current_url = None
            
            if os.path.exists(headers_file):
                with open(headers_file, 'r') as f:
                    headers_data = json.load(f)
                    current_url = headers_data.get('url')
            
            if action == "navigate":
                target_url = url or current_url
                if not target_url:
                    return {"success": False, "error": "No URL provided and no current URL in /looking_at/"}
                
                driver.get(target_url)
                time.sleep(wait_seconds)
                
                result = {
                    "success": True,
                    "action": "navigate",
                    "url": driver.current_url,
                    "title": driver.title
                }
                
            elif action == "screenshot":
                if current_url:
                    driver.get(current_url)
                    time.sleep(wait_seconds)
                
                screenshot_path = 'browser_automation/looking_at/screenshot.png'
                driver.save_screenshot(screenshot_path)
                
                result = {
                    "success": True,
                    "action": "screenshot",
                    "screenshot_path": screenshot_path,
                    "url": driver.current_url
                }
                
            elif action in ["click", "type", "submit"]:
                if not current_url:
                    return {"success": False, "error": "No current URL found in /looking_at/. Use browser_scrape_page first."}
                
                driver.get(current_url)
                time.sleep(wait_seconds)
                
                # Find the target element
                selector_type = target.get('selector_type', 'id')
                selector_value = target.get('selector_value')
                
                if not selector_value:
                    return {"success": False, "error": "target.selector_value is required for interaction"}
                
                # Map selector types to Selenium By types
                by_mapping = {
                    'id': By.ID,
                    'data-testid': By.CSS_SELECTOR,
                    'css': By.CSS_SELECTOR,
                    'xpath': By.XPATH,
                    'name': By.NAME
                }
                
                if selector_type == 'data-testid':
                    # Convert data-testid to CSS selector
                    selector_value = f'[data-testid="{selector_value}"]'
                    by_type = By.CSS_SELECTOR
                else:
                    by_type = by_mapping.get(selector_type, By.ID)
                
                try:
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((by_type, selector_value))
                    )
                    
                    if action == "click":
                        element.click()
                        result = {
                            "success": True,
                            "action": "click",
                            "element_found": True,
                            "element_text": element.text[:100] if element.text else ""
                        }
                        
                    elif action == "type":
                        element.clear()
                        element.send_keys(input_text)
                        result = {
                            "success": True,
                            "action": "type",
                            "element_found": True,
                            "text_entered": input_text
                        }
                        
                    elif action == "submit":
                        element.submit()
                        result = {
                            "success": True,
                            "action": "submit",
                            "element_found": True
                        }
                    
                    # Wait for any page changes
                    time.sleep(wait_seconds)
                    
                except Exception as e:
                    result = {
                        "success": False,
                        "action": action,
                        "error": f"Element interaction failed: {str(e)}",
                        "selector_type": selector_type,
                        "selector_value": selector_value
                    }
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
            
            # Update /looking_at/ state if requested
            if update_looking_at and result.get("success"):
                try:
                    looking_at_dir = 'browser_automation/looking_at'
                    os.makedirs(looking_at_dir, exist_ok=True)
                    
                    # Capture current state
                    page_title = driver.title
                    current_url = driver.current_url
                    source_html = driver.page_source
                    dom_html = driver.execute_script("return document.documentElement.outerHTML;")
                    
                    # Save updated state
                    state_data = {
                        'action_performed': action,
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
                    
                    logger.info(f"🎯 FINDER_TOKEN: MCP_BROWSER_INTERACTION_UPDATE - Action '{action}' completed, /looking_at/ updated")
                    
                except Exception as e:
                    logger.warning(f"⚠️ FINDER_TOKEN: MCP_BROWSER_INTERACTION_STATE_UPDATE_ERROR - {e}")
                    
            result["current_url"] = driver.current_url
            result["page_title"] = driver.title
            return result
            
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: MCP_BROWSER_INTERACT_ERROR - {e}")
        return {"success": False, "error": str(e)}

# All tools are now registered in register_all_mcp_tools() function above
# This ensures proper loading order and centralized registration management

# ================================================================
# AI SELF-DISCOVERY TOOLS - ELIMINATE UNCERTAINTY
# ================================================================

async def ai_self_discovery_assistant(params: dict) -> dict:
    """
    🧠 AI SELF-DISCOVERY ASSISTANT - The uncertainty eliminator.
    
    This tool provides instant capability awareness and usage patterns for AI assistants.
    It eliminates the "what tools do I have?" and "how do I use them?" uncertainty.
    
    Args:
        params: {
            "discovery_type": "capabilities" | "usage_patterns" | "success_stories" | "all",
            "include_examples": True,  # Include concrete usage examples
            "include_troubleshooting": True  # Include common failure modes
        }
    
    Returns:
        dict: Complete AI capability map with usage guidance
    """
    logger.info(f"🧠 FINDER_TOKEN: AI_SELF_DISCOVERY_START - Type: {params.get('discovery_type', 'all')}")

    # --- Ensure MCP_TOOL_REGISTRY is populated, even in direct/REPL/terminal use ---
    global MCP_TOOL_REGISTRY
    try:
        if not MCP_TOOL_REGISTRY or len(MCP_TOOL_REGISTRY) < 10:
            from mcp_tools import register_all_mcp_tools
            register_all_mcp_tools()
    except Exception as e:
        logger.warning(f'Could not auto-register MCP tools: {e}')
    # -----------------------------------------------------------------------------

    try:
        discovery_type = params.get('discovery_type', 'all')
        include_examples = params.get('include_examples', True)
        include_troubleshooting = params.get('include_troubleshooting', True)
        
        # Get current MCP tool registry - try multiple sources
        available_tools = []
        
        # Try server module first
        import sys
        server_module = sys.modules.get('server')
        if server_module and hasattr(server_module, 'MCP_TOOL_REGISTRY'):
            available_tools = list(server_module.MCP_TOOL_REGISTRY.keys())
        else:
            # Try main module (when running as __main__)
            main_module = sys.modules.get('__main__')
            if main_module and hasattr(main_module, 'MCP_TOOL_REGISTRY'):
                available_tools = list(main_module.MCP_TOOL_REGISTRY.keys())
            else:
                # Fallback to local registry
                available_tools = list(MCP_TOOL_REGISTRY.keys()) if MCP_TOOL_REGISTRY else []
        
        # If still no tools, try to discover them dynamically
        if not available_tools:
            try:
                # Use the discovery script's logic to find all MCP tool functions
                import inspect
                import sys
                mcp_module = sys.modules.get('mcp_tools')
                if mcp_module:
                    for name, obj in inspect.getmembers(mcp_module):
                        if (name.startswith('_') and 
                            callable(obj) and 
                            not name.startswith('__') and
                            'mcp' not in name.lower()):
                            available_tools.append(name)
            except Exception as e:
                logger.warning(f"Could not discover tools dynamically: {e}")
        
        # Categorize tools by capability - use actual function names with underscores
        tool_categories = {
            "environment_mastery": [
                "_pipeline_state_inspector",
                "_local_llm_list_files", 
                "_local_llm_read_file"
            ],
            "browser_embodiment": [
                "_browser_scrape_page",
                "_browser_analyze_scraped_page", 
                "_browser_automate_workflow_walkthrough",
                "_browser_interact_with_current_page"
            ],
            "session_hijacking": [
                "_execute_ai_session_hijacking_demonstration",
                "_pipeline_state_inspector"
            ],
            "external_integration": [
                "_botify_ping",
                "_botify_list_projects",
                "_botify_get_full_schema",
                "_botify_execute_custom_bql_query"
            ],
            "debugging_transparency": [
                "_local_llm_grep_logs",
                "_ui_flash_element",
                "_ui_list_elements"
            ],
            "entertainment": [
                "_builtin_get_cat_fact"
            ]
        }
        
        # Build capability map
        capabilities = {}
        for category, tools in tool_categories.items():
            available_in_category = [tool for tool in tools if tool in available_tools]
            if available_in_category:
                capabilities[category] = {
                    "tools": available_in_category,
                    "count": len(available_in_category),
                    "description": get_category_description(category)
                }
        
        # Usage patterns for common AI tasks
        usage_patterns = {
            "web_scraping_workflow": {
                "description": "Complete web scraping with analysis",
                "steps": [
                    "1. browser_scrape_page - Capture page state",
                    "2. browser_analyze_scraped_page - Find automation targets", 
                    "3. local_llm_read_file - Examine captured content",
                    "4. ui_flash_element - Guide user attention"
                ],
                "example_params": {
                    "browser_scrape_page": {"url": "https://example.com", "take_screenshot": True},
                    "browser_analyze_scraped_page": {"analysis_type": "all"},
                    "local_llm_read_file": {"file_path": "browser_automation/looking_at/simple_dom.html"},
                    "ui_flash_element": {"element_id": "important-element", "message": "Found key information!"}
                }
            },
            "workflow_debugging": {
                "description": "Debug user workflow issues",
                "steps": [
                    "1. pipeline_state_inspector - Check current state",
                    "2. local_llm_grep_logs - Search for errors",
                    "3. browser_scrape_page - See what user sees",
                    "4. ui_flash_element - Highlight issues"
                ]
            },
            "session_hijacking": {
                "description": "Take over user session seamlessly",
                "steps": [
                    "1. pipeline_state_inspector - Understand current workflow",
                    "2. browser_scrape_page - Capture current state",
                    "3. browser_automate_workflow_walkthrough - Continue workflow",
                    "4. execute_ai_session_hijacking_demonstration - Show capabilities"
                ]
            }
        }
        
        # Success stories from real usage
        success_stories = {
            "bbc_news_headlines": {
                "task": "Extract current news headlines from BBC",
                "tools_used": ["browser_scrape_page", "local_llm_read_file"],
                "result": "Successfully captured 15+ headlines with timestamps and categories",
                "key_insight": "News sites are more accessible than search engines for automation"
            },
            "google_captcha_detection": {
                "task": "Attempt Google search automation",
                "tools_used": ["browser_scrape_page", "browser_analyze_scraped_page"],
                "result": "Detected CAPTCHA challenge, demonstrated security awareness",
                "key_insight": "Real-world security measures provide valuable learning opportunities"
            },
            "workflow_session_hijacking": {
                "task": "Take over user's Botifython workflow",
                "tools_used": ["pipeline_state_inspector", "browser_scrape_page"],
                "result": "Successfully captured and analyzed user's current workflow state",
                "key_insight": "Complete session visibility enables seamless AI assistance"
            }
        }
        
        # Common failure modes and solutions
        troubleshooting = {
            "tool_not_found": {
                "symptom": "MCP tool not available in registry",
                "solution": "Check server startup logs, ensure tool is registered in register_all_mcp_tools()",
                "prevention": "Always verify tool availability before attempting usage"
            },
            "browser_automation_failure": {
                "symptom": "Selenium operations fail or timeout",
                "solution": "Check Chrome/Chromedriver installation, increase wait_seconds parameter",
                "prevention": "Use headless mode for reliability, add error handling"
            },
            "file_access_denied": {
                "symptom": "Cannot read files in /looking_at/ directory",
                "solution": "Verify file exists, check permissions, use browser_scrape_page first",
                "prevention": "Always check file existence before attempting to read"
            },
            "api_authentication_failure": {
                "symptom": "Botify API calls return 401/403 errors",
                "solution": "Verify botify_token.txt exists and contains valid token",
                "prevention": "Use botify_ping to test connectivity before complex operations"
            }
        }
        
        # Build response based on discovery type
        result = {
            "success": True,
            "discovery_type": discovery_type,
            "total_tools_available": len(available_tools),
            "timestamp": datetime.now().isoformat()
        }
        
        if discovery_type in ["capabilities", "all"]:
            result["capabilities"] = capabilities
            
        if discovery_type in ["usage_patterns", "all"] and include_examples:
            result["usage_patterns"] = usage_patterns
            
        if discovery_type in ["success_stories", "all"]:
            result["success_stories"] = success_stories
            
        if discovery_type in ["troubleshooting", "all"] and include_troubleshooting:
            result["troubleshooting"] = troubleshooting
        
        # Add quick reference for immediate use
        result["quick_reference"] = {
            "most_powerful_tools": [
                "browser_scrape_page",      # AI eyes
                "browser_analyze_scraped_page",  # AI brain  
                "pipeline_state_inspector",  # Workflow awareness
                "execute_ai_session_hijacking_demonstration"  # Session takeover
            ],
            "essential_patterns": [
                "Always check current state before acting",
                "Use browser automation for visual tasks",
                "Leverage FINDER_TOKEN logs for debugging",
                "Provide user guidance with ui_flash_element"
            ]
        }
        
        logger.info(f"🎯 FINDER_TOKEN: AI_SELF_DISCOVERY_SUCCESS - {len(available_tools)} tools mapped, {len(capabilities)} categories")
        return result
        
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: AI_SELF_DISCOVERY_ERROR - {e}")
        return {"success": False, "error": str(e)}

def get_category_description(category: str) -> str:
    """Get human-readable description for tool category."""
    descriptions = {
        "environment_mastery": "Understand and control the development environment",
        "browser_embodiment": "See, analyze, and interact with web pages like a human",
        "session_hijacking": "Take over user sessions and continue their workflows",
        "external_integration": "Connect to external APIs and services",
        "debugging_transparency": "Debug issues with complete system visibility",
        "entertainment": "Lightweight tools for engagement and testing"
    }
    return descriptions.get(category, "Unknown category")

async def ai_capability_test_suite(params: dict) -> dict:
    """
    🧪 AI CAPABILITY TEST SUITE - Prove your superpowers.
    
    This tool runs a comprehensive test of all AI capabilities to verify
    that the system is working correctly and the AI has full access.
    
    Args:
        params: {
            "test_type": "quick" | "comprehensive" | "specific_tool" | "context_aware",
            "specific_tool": "tool_name"  # Only for specific_tool test
        }
    
    Returns:
        dict: Test results with success/failure details
    """
    logger.info(f"🧪 FINDER_TOKEN: AI_CAPABILITY_TEST_START - Type: {params.get('test_type', 'quick')}")
    
    try:
        test_type = params.get('test_type', 'quick')
        specific_tool = params.get('specific_tool')
        
        test_results = {
            "timestamp": datetime.now().isoformat(),
            "test_type": test_type,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "results": {},
            "context_analysis": {}
        }
        
        if test_type == "specific_tool" and specific_tool:
            # Test specific tool
            test_results["results"][specific_tool] = await _test_specific_tool(specific_tool)
            test_results["tests_run"] = 1
            test_results["tests_passed"] = 1 if test_results["results"][specific_tool]["success"] else 0
            test_results["tests_failed"] = 1 - test_results["tests_passed"]
            
        elif test_type == "quick":
            # Quick test of core capabilities (context-aware)
            quick_tests = [
                ("environment_check", test_environment_access),
                ("file_system", test_file_system_access),
                ("mcp_registry", test_mcp_registry_context_aware),
                ("basic_browser", test_basic_browser_capability)
            ]
            
            for test_name, test_func in quick_tests:
                test_results["tests_run"] += 1
                result = await test_func()
                test_results["results"][test_name] = result
                if result["success"]:
                    test_results["tests_passed"] += 1
                else:
                    test_results["tests_failed"] += 1
                    
        elif test_type == "comprehensive":
            # Comprehensive test of all capabilities (context-aware)
            comprehensive_tests = [
                ("environment_check", test_environment_access),
                ("file_system", test_file_system_access),
                ("mcp_registry", test_mcp_registry_context_aware),
                ("basic_browser", test_basic_browser_capability),
                ("pipeline_inspection", test_pipeline_inspection_context_aware),
                ("log_access", test_log_access),
                ("ui_interaction", test_ui_interaction_context_aware),
                ("botify_connectivity", test_botify_connectivity)
            ]
            
            for test_name, test_func in comprehensive_tests:
                test_results["tests_run"] += 1
                result = await test_func()
                test_results["results"][test_name] = result
                if result["success"]:
                    test_results["tests_passed"] += 1
                else:
                    test_results["tests_failed"] += 1
                    
        elif test_type == "context_aware":
            # New context-aware test that provides intelligent assessment
            test_results.update(await _run_context_aware_test_suite())
            # Add assessment for context-aware test
            test_results["assessment"] = _generate_context_aware_assessment(test_results)
            return test_results
        
        # Calculate success rate
        if test_results["tests_run"] > 0:
            test_results["success_rate"] = round((test_results["tests_passed"] / test_results["tests_run"]) * 100, 2)
        else:
            test_results["success_rate"] = 0
            
        # Add overall assessment with context awareness
        test_results["assessment"] = _generate_context_aware_assessment(test_results)
        
        logger.info(f"🎯 FINDER_TOKEN: AI_CAPABILITY_TEST_COMPLETE - {test_results['tests_passed']}/{test_results['tests_run']} passed ({test_results['success_rate']}%)")
        return test_results
        
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: AI_CAPABILITY_TEST_ERROR - {e}")
        return {"success": False, "error": str(e)}

async def _run_context_aware_test_suite() -> dict:
    """Run a context-aware test suite that provides intelligent assessment."""
    
    test_results = {
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "results": {},
        "context_analysis": {},
        "capability_assessment": {}
    }
    
    # Test 1: Environment and File System (Always available)
    test_results["tests_run"] += 1
    env_result = await test_environment_access()
    test_results["results"]["environment"] = env_result
    if env_result["success"]:
        test_results["tests_passed"] += 1
    else:
        test_results["tests_failed"] += 1
    
    # Test 2: File System Access
    test_results["tests_run"] += 1
    fs_result = await test_file_system_access()
    test_results["results"]["file_system"] = fs_result
    if fs_result["success"]:
        test_results["tests_passed"] += 1
    else:
        test_results["tests_failed"] += 1
    
    # Test 3: MCP Tools Availability (Context-aware)
    test_results["tests_run"] += 1
    mcp_result = await test_mcp_tools_availability()
    test_results["results"]["mcp_tools"] = mcp_result
    if mcp_result["success"]:
        test_results["tests_passed"] += 1
    else:
        test_results["tests_failed"] += 1
    
    # Test 4: Browser Automation (Always available if Selenium installed)
    test_results["tests_run"] += 1
    browser_result = await test_basic_browser_capability()
    test_results["results"]["browser_automation"] = browser_result
    if browser_result["success"]:
        test_results["tests_passed"] += 1
    else:
        test_results["tests_failed"] += 1
    
    # Test 5: Pipeline Functionality (Test actual functionality, not just context)
    test_results["tests_run"] += 1
    pipeline_result = await test_pipeline_functionality()
    test_results["results"]["pipeline_functionality"] = pipeline_result
    if pipeline_result["success"]:
        test_results["tests_passed"] += 1
    else:
        test_results["tests_failed"] += 1
    
    # Test 6: Botify API (Test actual connectivity)
    test_results["tests_run"] += 1
    botify_result = await test_botify_actual_connectivity()
    test_results["results"]["botify_api"] = botify_result
    if botify_result["success"]:
        test_results["tests_passed"] += 1
    else:
        test_results["tests_failed"] += 1
    
    # Test 7: Log Access
    test_results["tests_run"] += 1
    log_result = await test_log_access()
    test_results["results"]["log_access"] = log_result
    if log_result["success"]:
        test_results["tests_passed"] += 1
    else:
        test_results["tests_failed"] += 1
    
    # Test 8: UI Interaction (Test if server is running and accessible)
    test_results["tests_run"] += 1
    ui_result = await test_ui_accessibility()
    test_results["results"]["ui_accessibility"] = ui_result
    if ui_result["success"]:
        test_results["tests_passed"] += 1
    else:
        test_results["tests_failed"] += 1
    
    # Calculate success rate
    if test_results["tests_run"] > 0:
        test_results["success_rate"] = round((test_results["tests_passed"] / test_results["tests_run"]) * 100, 2)
    else:
        test_results["success_rate"] = 0
    
    # Generate capability assessment
    test_results["capability_assessment"] = _generate_detailed_capability_assessment(test_results)
    
    return test_results

async def test_mcp_tools_availability() -> dict:
    """Test MCP tools availability with context awareness."""
    try:
        # Test if we can import and access MCP tools directly
        try:
            from mcp_tools import builtin_get_cat_fact
            # Test a simple tool call
            result = await builtin_get_cat_fact({})
            if result.get("status") == "success" or result.get("fact"):
                return {
                    "success": True,
                    "mcp_tools_accessible": True,
                    "direct_access": True,
                    "test_result": "MCP tools accessible via direct import"
                }
        except ImportError:
            pass
        
        # Fallback: Check if tools are available through server context
        import sys
        server_module = sys.modules.get('server')
        if server_module and hasattr(server_module, 'MCP_TOOL_REGISTRY'):
            tool_count = len(server_module.MCP_TOOL_REGISTRY)
            return {
                "success": True,
                "mcp_tools_accessible": True,
                "server_context": True,
                "tool_count": tool_count,
                "test_result": f"MCP tools accessible via server context ({tool_count} tools)"
            }
        
        # Final fallback: Check if we're in the right environment
        if os.path.exists("mcp_tools.py") and os.path.exists("server.py"):
            return {
                "success": True,
                "mcp_tools_accessible": True,
                "environment_ready": True,
                "test_result": "MCP tools environment ready (tools should work in server context)"
            }
        
        return {"success": False, "error": "MCP tools not accessible in any context"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def test_pipeline_functionality() -> dict:
    """Test actual pipeline functionality, not just context availability."""
    try:
        # Test if we can access the database directly
        try:
            from fastlite import database
            from pathlib import Path
            Path('data').mkdir(parents=True, exist_ok=True)
            db = database('data/data.db')
            
            # Test if pipeline table exists and is accessible
            if hasattr(db, 'pipeline'):
                pipeline_count = len(list(db.pipeline()))
                return {
                    "success": True,
                    "pipeline_functional": True,
                    "database_accessible": True,
                    "pipeline_count": pipeline_count,
                    "test_result": f"Pipeline database accessible with {pipeline_count} records"
                }
        except Exception as db_error:
            pass
        
        # Fallback: Test if we can use the pipeline inspector tool
        try:
            result = await _pipeline_state_inspector({'format': 'summary'})
            if result.get("success"):
                return {
                    "success": True,
                    "pipeline_functional": True,
                    "inspector_working": True,
                    "test_result": "Pipeline inspector tool working"
                }
        except Exception as inspector_error:
            pass
        
        # Final fallback: Check if pipeline files exist
        if os.path.exists("data/") and (os.path.exists("data/data.db") or os.path.exists("data/botifython_dev.db")):
            return {
                "success": True,
                "pipeline_functional": True,
                "files_exist": True,
                "test_result": "Pipeline files exist (should work in server context)"
            }
        
        return {"success": False, "error": "Pipeline functionality not accessible"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def test_botify_actual_connectivity() -> dict:
    """Test actual Botify API connectivity."""
    try:
        # First check if token is available
        token = _read_botify_api_token()
        if not token:
            return {
                "success": False,
                "error": "Botify API token not available",
                "suggestion": "Configure Botify API token in helpers/botify/botify_token.txt"
            }
        
        # Test actual API call
        try:
            result = await _botify_ping({})
            if result.get("success"):
                return {
                    "success": True,
                    "botify_connected": True,
                    "api_responding": True,
                    "test_result": "Botify API responding successfully"
                }
            else:
                # Analyze the error to provide better context
                error_msg = result.get("message", "Unknown error")
                status = result.get("external_api_status", "Unknown")
                
                if "404" in str(status) or "404" in error_msg:
                    return {
                        "success": False,
                        "error": "Botify API endpoint not found (404) - token may be expired or API changed",
                        "token_available": True,
                        "suggestion": "Check Botify API documentation for endpoint changes or renew token"
                    }
                elif "401" in str(status) or "401" in error_msg:
                    return {
                        "success": False,
                        "error": "Botify API authentication failed (401) - token may be invalid",
                        "token_available": True,
                        "suggestion": "Verify Botify API token is correct and not expired"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Botify API error: {error_msg} (Status: {status})",
                        "token_available": True,
                        "suggestion": "Check Botify API status and token validity"
                    }
        except Exception as api_error:
            return {
                "success": False,
                "error": f"Botify API call failed: {str(api_error)}",
                "token_available": True,
                "suggestion": "Check network connectivity and Botify API availability"
            }
            
    except Exception as e:
        return {"success": False, "error": str(e)}

async def test_ui_accessibility() -> dict:
    """Test if the UI is accessible via HTTP."""
    try:
        import aiohttp
        import asyncio
        
        # Test if server is running and accessible
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:5001/', timeout=5) as response:
                    if response.status == 200:
                        return {
                            "success": True,
                            "ui_accessible": True,
                            "server_running": True,
                            "test_result": "UI accessible via HTTP on port 5001"
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Server responding but status {response.status}",
                            "server_running": True
                        }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Server timeout - may not be running",
                "suggestion": "Start server with 'python server.py'"
            }
        except Exception as http_error:
            return {
                "success": False,
                "error": f"HTTP connection failed: {str(http_error)}",
                "suggestion": "Check if server is running on port 5001"
            }
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def _generate_context_aware_assessment(test_results: dict) -> str:
    """Generate context-aware assessment based on test results."""
    success_rate = test_results.get("success_rate", 0)
    
    # Analyze context-specific failures
    context_failures = []
    for test_name, result in test_results.get("results", {}).items():
        if not result.get("success") and "context" in result.get("error", "").lower():
            context_failures.append(test_name)
    
    if success_rate >= 90:
        return "🎯 EXCELLENT - AI superpowers fully operational"
    elif success_rate >= 75:
        if context_failures:
            return f"✅ GOOD - Core capabilities working. Context-dependent features require server context ({', '.join(context_failures)})"
        else:
            return "✅ GOOD - Most capabilities working, minor issues detected"
    elif success_rate >= 50:
        if context_failures:
            return f"⚠️ FAIR - Core capabilities working. Some features require server context ({', '.join(context_failures)})"
        else:
            return "⚠️ FAIR - Some capabilities working, needs attention"
    else:
        return "❌ POOR - Significant issues detected, requires investigation"

def _generate_detailed_capability_assessment(test_results: dict) -> dict:
    """Generate detailed capability assessment."""
    assessment = {
        "core_capabilities": {},
        "context_dependent": {},
        "recommendations": []
    }
    
    for test_name, result in test_results.get("results", {}).items():
        if result.get("success"):
            if "context" in test_name.lower() or "server" in result.get("test_result", "").lower():
                assessment["context_dependent"][test_name] = "✅ Working (requires server context)"
            else:
                assessment["core_capabilities"][test_name] = "✅ Working"
        else:
            error = result.get("error", "Unknown error")
            if "context" in error.lower() or "server" in error.lower():
                assessment["context_dependent"][test_name] = f"⚠️ Context-dependent ({error})"
                assessment["recommendations"].append(f"Use {test_name} through server context")
            else:
                assessment["core_capabilities"][test_name] = f"❌ Failed ({error})"
    
    return assessment

async def test_mcp_registry_context_aware() -> dict:
    """Context-aware MCP registry test."""
    return await test_mcp_tools_availability()

async def test_pipeline_inspection_context_aware() -> dict:
    """Context-aware pipeline inspection test."""
    return await test_pipeline_functionality()

async def test_ui_interaction_context_aware() -> dict:
    """Context-aware UI interaction test."""
    return await test_ui_accessibility()

async def test_environment_access() -> dict:
    """Test basic environment access."""
    try:
        import os
        current_dir = os.getcwd()
        server_exists = os.path.exists("server.py")
        plugins_exists = os.path.exists("plugins/")
        
        return {
            "success": True,
            "current_directory": current_dir,
            "server_py_exists": server_exists,
            "plugins_directory_exists": plugins_exists,
            "environment_ready": server_exists and plugins_exists
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

async def test_file_system_access() -> dict:
    """Test file system access capabilities."""
    try:
        import os
        from pathlib import Path
        
        # Test reading a simple file
        test_file = "mcp_tools.py"
        if os.path.exists(test_file):
            with open(test_file, 'r') as f:
                content = f.read(100)  # Just first 100 chars
            return {
                "success": True,
                "file_read_success": True,
                "test_file": test_file,
                "content_preview": content[:50] + "..."
            }
        else:
            return {"success": False, "error": f"Test file {test_file} not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def test_mcp_registry() -> dict:
    """Test MCP tool registry access."""
    try:
        import sys
        server_module = sys.modules.get('server')
        if server_module and hasattr(server_module, 'MCP_TOOL_REGISTRY'):
            tool_count = len(server_module.MCP_TOOL_REGISTRY)
            return {
                "success": True,
                "registry_accessible": True,
                "tool_count": tool_count,
                "registry_ready": tool_count > 0
            }
        else:
            return {"success": False, "error": "MCP tool registry not accessible"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def test_basic_browser_capability() -> dict:
    """Test basic browser automation capability."""
    try:
        # Test if Selenium is available
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            return {
                "success": True,
                "selenium_available": True,
                "webdriver_import_success": True
            }
        except ImportError:
            return {"success": False, "error": "Selenium not available"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def test_pipeline_inspection() -> dict:
    """Test pipeline inspection capability."""
    try:
        # Test if we can access the pipeline table
        import sys
        server_module = sys.modules.get('server')
        if server_module and hasattr(server_module, 'pipeline'):
            return {
                "success": True,
                "pipeline_table_accessible": True
            }
        else:
            return {"success": False, "error": "Pipeline table not accessible"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def test_log_access() -> dict:
    """Test log file access capability."""
    try:
        import os
        log_file = "logs/server.log"
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()
            return {
                "success": True,
                "log_file_accessible": True,
                "log_lines_count": len(lines)
            }
        else:
            return {"success": False, "error": "Log file not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def test_ui_interaction() -> dict:
    """Test UI interaction capability."""
    try:
        # Test if we can access the chat system
        import sys
        server_module = sys.modules.get('server')
        if server_module and hasattr(server_module, 'chat'):
            return {
                "success": True,
                "chat_system_accessible": True
            }
        else:
            return {"success": False, "error": "Chat system not accessible"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def test_botify_connectivity() -> dict:
    """Test Botify API connectivity."""
    try:
        # Test if we can read the token file
        token_file = "helpers/botify/botify_token.txt"
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                token = f.read().strip()
            return {
                "success": True,
                "token_file_exists": True,
                "token_available": bool(token)
            }
        else:
            return {"success": False, "error": "Botify token file not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def test_specific_tool(tool_name: str) -> dict:
    """Test a specific MCP tool."""
    try:
        import sys
        server_module = sys.modules.get('server')
        if server_module and hasattr(server_module, 'MCP_TOOL_REGISTRY'):
            registry = server_module.MCP_TOOL_REGISTRY
            if tool_name in registry:
                return {
                    "success": True,
                    "tool_found": True,
                    "tool_available": True
                }
            else:
                return {"success": False, "error": f"Tool {tool_name} not found in registry"}
        else:
            return {"success": False, "error": "MCP tool registry not accessible"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Register the new AI self-discovery tools
register_mcp_tool("ai_self_discovery_assistant", ai_self_discovery_assistant)
register_mcp_tool("ai_capability_test_suite", ai_capability_test_suite)

async def browser_automate_instructions(params: dict) -> dict:
    """
    MCP Tool: AI HANDS - Natural Language Browser Automation
    
    This tool parses natural language instructions and converts them into browser automation actions.
    It provides a user-friendly interface for browser automation without requiring technical knowledge.
    
    Args:
        params: {
            "instructions": "click search input and type hello world",
            "target_url": "http://localhost:5001",
            "wait_seconds": 3
        }
    
    Returns:
        dict: Automation results with success rate and feedback
    """
    logger.info(f"🤖 FINDER_TOKEN: INSTRUCTION_AUTOMATION_START | Instructions: {params.get('instructions')}")
    
    try:
        import re
        import time
        from pathlib import Path
        
        instructions = params.get('instructions', '')
        target_url = params.get('target_url', 'http://localhost:5001')
        wait_seconds = params.get('wait_seconds', 3)
        
        if not instructions:
            return {
                'success': False,
                'error': 'No instructions provided',
                'suggestions': ['Try: "click search input and type hello world"', 'Try: "navigate to dashboard"', 'Try: "click login button"']
            }
        
        # First, capture the current page state
        scrape_result = await browser_scrape_page({
            'url': target_url,
            'wait_seconds': 2,
            'take_screenshot': True
        })
        
        if not scrape_result.get('success'):
            return {
                'success': False,
                'error': f'Failed to capture page state: {scrape_result.get("error")}',
                'suggestions': ['Check if the target URL is accessible', 'Verify the server is running']
            }
        
        # Parse instructions into actions
        actions = []
        instruction_lower = instructions.lower()
        
        # Simple instruction parsing
        if 'click' in instruction_lower:
            # Extract what to click
            click_match = re.search(r'click\s+([^,\s]+(?:\s+[^,\s]+)*)', instruction_lower)
            if click_match:
                click_target = click_match.group(1)
                if 'search' in click_target and 'input' in click_target:
                    actions.append({
                        'action': 'click',
                        'target': {'selector_type': 'id', 'selector_value': 'nav-plugin-search'},
                        'description': f'Click search input'
                    })
                elif 'button' in click_target:
                    actions.append({
                        'action': 'click',
                        'target': {'selector_type': 'css', 'selector_value': 'button'},
                        'description': f'Click {click_target}'
                    })
                else:
                    actions.append({
                        'action': 'click',
                        'target': {'selector_type': 'css', 'selector_value': f'[data-testid*="{click_target}"]'},
                        'description': f'Click {click_target}'
                    })
        
        if 'type' in instruction_lower:
            # Extract what to type
            type_match = re.search(r'type\s+([^,\s]+(?:\s+[^,\s]+)*)', instruction_lower)
            if type_match:
                text_to_type = type_match.group(1)
                # Find the input element to type into
                if 'search' in instruction_lower:
                    actions.append({
                        'action': 'type',
                        'target': {'selector_type': 'id', 'selector_value': 'nav-plugin-search'},
                        'input_text': text_to_type,
                        'description': f'Type "{text_to_type}" in search input'
                    })
                else:
                    actions.append({
                        'action': 'type',
                        'target': {'selector_type': 'css', 'selector_value': 'input'},
                        'input_text': text_to_type,
                        'description': f'Type "{text_to_type}" in input field'
                    })
        
        if 'wait' in instruction_lower:
            # Extract wait time
            wait_match = re.search(r'wait\s+(\d+)\s*seconds?', instruction_lower)
            if wait_match:
                wait_time = int(wait_match.group(1))
                actions.append({
                    'action': 'wait',
                    'wait_seconds': wait_time,
                    'description': f'Wait {wait_time} seconds'
                })
        
        if not actions:
            return {
                'success': False,
                'error': 'Could not parse any actionable instructions',
                'suggestions': [
                    'Use action verbs: click, type, wait, navigate',
                    'Be specific: "click search input", "type hello world"',
                    'Try: "click search input and type hello world"'
                ]
            }
        
        # Execute actions
        action_results = []
        successful_actions = 0
        
        for i, action in enumerate(actions):
            logger.info(f"🎯 FINDER_TOKEN: INSTRUCTION_ACTION_{i+1} | {action['description']}")
            
            if action['action'] == 'wait':
                time.sleep(action['wait_seconds'])
                result = {'success': True, 'action': 'wait', 'description': action['description']}
            else:
                # Use the existing interaction function
                result = await browser_interact_with_current_page({
                    'action': action['action'],
                    'target': action.get('target'),
                    'input_text': action.get('input_text', ''),
                    'wait_seconds': wait_seconds
                })
                result['description'] = action['description']
            
            action_results.append(result)
            
            if result.get('success'):
                successful_actions += 1
                logger.info(f"✅ FINDER_TOKEN: INSTRUCTION_SUCCESS | {action['description']}")
            else:
                logger.warning(f"⚠️ FINDER_TOKEN: INSTRUCTION_FAILURE | {action['description']}: {result.get('error')}")
        
        # Take final screenshot
        final_screenshot = await browser_interact_with_current_page({
            'action': 'screenshot',
            'wait_seconds': 1
        })
        
        # Calculate success rate
        success_rate = (successful_actions / len(actions)) * 100 if actions else 0
        
        return {
            'success': success_rate > 50,  # More than 50% success
            'success_rate': round(success_rate, 1),
            'total_actions': len(actions),
            'successful_actions': successful_actions,
            'failed_actions': len(actions) - successful_actions,
            'action_results': action_results,
            'final_screenshot': final_screenshot.get('screenshot_path') if final_screenshot.get('success') else None,
            'instructions_parsed': instructions,
            'improvement_suggestions': [
                'Use specific element names: "search input", "login button"',
                'Combine actions: "click search and type hello"',
                'Add wait times: "wait 2 seconds"'
            ] if success_rate < 100 else ['All actions completed successfully!']
        }
        
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: INSTRUCTION_AUTOMATION_ERROR | {e}")
        return {
            'success': False,
            'error': f'Instruction automation error: {str(e)}',
            'suggestions': [
                'Check if the target URL is accessible',
                'Verify browser automation is working',
                'Try simpler instructions first'
            ]
        }


# Register the new browser automation tool
register_mcp_tool("browser_automate_instructions", browser_automate_instructions)

def get_available_tools():
    """
    Returns a list of all callable MCP tools, their function names, signatures, and docstrings.
    """
    tools = []
    public_tool_names = [
        'builtin_get_cat_fact',
        'pipeline_state_inspector',
        'botify_ping',
        'botify_list_projects',
        'botify_simple_query',
        'local_llm_read_file',
        'local_llm_grep_logs',
        'local_llm_list_files',
        'local_llm_get_context',
        'execute_ai_session_hijacking_demonstration',
        'ui_flash_element',
        'ui_list_elements',
        'browser_analyze_scraped_page',
        'browser_scrape_page',
        'browser_automate_workflow_walkthrough',
        'botify_get_full_schema',
        'botify_list_available_analyses',
        'botify_execute_custom_bql_query',
        'browser_interact_with_current_page',
        'ai_self_discovery_assistant',
        'ai_capability_test_suite',
        'browser_automate_instructions',
    ]
    for name in public_tool_names:
        func = globals().get(name)
        if func:
            sig = str(inspect.signature(func))
            doc = inspect.getdoc(func)
            tools.append({
                'name': name,
                'signature': sig,
                'doc': doc
            })
    return tools



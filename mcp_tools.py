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
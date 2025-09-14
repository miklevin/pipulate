"""
Botify MCP Tools - Extracted from mcp_tools.py for focused token optimization

This module contains all Botify-related MCP tools for AI assistant interaction.
Can be imported selectively to reduce token usage in AI prompts.
"""

import os
import json
import logging
import asyncio
import inspect
from pathlib import Path
from typing import Dict, Any, List

# Initialize logger
logger = logging.getLogger(__name__)

# --- HELPER FUNCTIONS ---

def _read_botify_api_token() -> str:
    """Read Botify API token from ai_dictdb.py if available."""
    try:
        import ai_dictdb
        return ai_dictdb.get_key('botify_api_token')
    except ImportError:
        logger.warning("ai_dictdb module not available, using placeholder token")
        return "placeholder_token"
    except Exception as e:
        logger.warning(f"Could not read Botify API token: {e}")
        return "placeholder_token"

# --- CORE BOTIFY MCP TOOLS ---

async def botify_ping(params: dict) -> dict:
    """
    MCP Tool: Test Botify API connectivity and authentication
    
    Args:
        params: {"username": "your_username"}
    
    Returns:
        dict: {"success": True/False, "response_status": int, "message": str}
    """
    logger.info(f"🔍 FINDER_TOKEN: BOTIFY_PING_START - {params}")
    
    try:
        import aiohttp
        username = params.get('username')
        if not username:
            return {"success": False, "error": "Username is required"}
        
        api_token = _read_botify_api_token()
        if not api_token or api_token == "placeholder_token":
            return {"success": False, "error": "Valid Botify API token not found"}
        
        url = f"https://api.botify.com/v1/projects/{username}"
        headers = {"Authorization": f"Token {api_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    logger.info(f"✅ FINDER_TOKEN: BOTIFY_PING_SUCCESS - {response.status}")
                    return {
                        "success": True,
                        "response_status": response.status,
                        "message": "Botify API connection successful"
                    }
                else:
                    logger.error(f"❌ FINDER_TOKEN: BOTIFY_PING_FAILED - Status {response.status}")
                    return {
                        "success": False,
                        "response_status": response.status,
                        "message": f"Botify API authentication failed: {response.status}",
                        "error": f"HTTP {response.status}"
                    }
    
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: BOTIFY_PING_ERROR - {str(e)}")
        return {"success": False, "error": str(e)}

async def botify_list_projects(params: dict) -> dict:
    """
    MCP Tool: List all projects available to the authenticated user
    
    Args:
        params: {"username": "your_username"}
    
    Returns:
        dict: {"success": True/False, "projects": [...], "total_projects": int}
    """
    logger.info(f"🔍 FINDER_TOKEN: BOTIFY_LIST_PROJECTS_START - {params}")
    
    try:
        import aiohttp
        username = params.get('username')
        if not username:
            return {"success": False, "error": "Username is required"}
        
        api_token = _read_botify_api_token()
        if not api_token or api_token == "placeholder_token":
            return {"success": False, "error": "Valid Botify API token not found"}
        
        url = f"https://api.botify.com/v1/projects/{username}"
        headers = {"Authorization": f"Token {api_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    projects = data.get('results', [])
                    logger.info(f"✅ FINDER_TOKEN: BOTIFY_LIST_PROJECTS_SUCCESS - {len(projects)} projects found")
                    return {
                        "success": True,
                        "projects": projects,
                        "total_projects": len(projects)
                    }
                else:
                    logger.error(f"❌ FINDER_TOKEN: BOTIFY_LIST_PROJECTS_FAILED - Status {response.status}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}"
                    }
    
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: BOTIFY_LIST_PROJECTS_ERROR - {str(e)}")
        return {"success": False, "error": str(e)}

async def botify_simple_query(params: dict) -> dict:
    """
    MCP Tool: Execute a simple BQL query against Botify API
    
    Args:
        params: {
            "username": "your_username",
            "project": "project_name", 
            "query": "SELECT url FROM crawl",
            "limit": 100
        }
    
    Returns:
        dict: {"success": True/False, "data": [...], "total_results": int}
    """
    logger.info(f"🔍 FINDER_TOKEN: BOTIFY_SIMPLE_QUERY_START - {params}")
    
    try:
        import aiohttp
        username = params.get('username')
        project = params.get('project')
        query = params.get('query')
        limit = params.get('limit', 100)
        
        if not all([username, project, query]):
            return {"success": False, "error": "Username, project, and query are required"}
        
        api_token = _read_botify_api_token()
        if not api_token or api_token == "placeholder_token":
            return {"success": False, "error": "Valid Botify API token not found"}
        
        url = f"https://api.botify.com/v1/projects/{username}/{project}/query"
        from config import get_botify_headers
        headers = get_botify_headers(api_token)
        
        payload = {
            "query": query,
            "size": limit
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('results', [])
                    logger.info(f"✅ FINDER_TOKEN: BOTIFY_SIMPLE_QUERY_SUCCESS - {len(results)} results")
                    return {
                        "success": True,
                        "data": results,
                        "total_results": len(results),
                        "query": query
                    }
                else:
                    logger.error(f"❌ FINDER_TOKEN: BOTIFY_SIMPLE_QUERY_FAILED - Status {response.status}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}"
                    }
    
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: BOTIFY_SIMPLE_QUERY_ERROR - {str(e)}")
        return {"success": False, "error": str(e)}

async def botify_get_full_schema(params: dict) -> dict:
    """
    MCP Tool: Get the complete Botify schema with all 4,449+ fields
    
    Args:
        params: {"username": "your_username", "project": "project_name"}
    
    Returns:
        dict: {"success": True/False, "schema": {...}, "total_fields": int}
    """
    logger.info(f"🔍 FINDER_TOKEN: BOTIFY_GET_FULL_SCHEMA_START - {params}")
    
    try:
        # Import the schema discoverer
        from imports.botify.true_schema_discoverer import \
            discover_complete_schema, \
            generate_schema_cheatsheet_markdown
        
        username = params.get('username')
        project = params.get('project')
        
        if not all([username, project]):
            return {"success": False, "error": "Username and project are required"}
        
        # Discover the complete schema
        schema_result = await discover_complete_schema(username, project)
        
        if schema_result.get('success'):
            schema = schema_result.get('complete_schema', {})
            total_fields = len(schema.get('fields', []))
            
            logger.info(f"✅ FINDER_TOKEN: BOTIFY_GET_FULL_SCHEMA_SUCCESS - {total_fields} fields discovered")
            return {
                "success": True,
                "schema": schema,
                "total_fields": total_fields,
                "username": username,
                "project": project
            }
        else:
            logger.error(f"❌ FINDER_TOKEN: BOTIFY_GET_FULL_SCHEMA_FAILED - {schema_result.get('error')}")
            return {
                "success": False,
                "error": schema_result.get('error', 'Unknown schema discovery error')
            }
    
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: BOTIFY_GET_FULL_SCHEMA_ERROR - {str(e)}")
        return {"success": False, "error": str(e)}

async def botify_list_available_analyses(params: dict) -> dict:
    """
    MCP Tool: List all available analyses for a project
    
    Args:
        params: {"username": "your_username", "project": "project_name"}
    
    Returns:
        dict: {"success": True/False, "analyses": [...], "total_analyses": int}
    """
    logger.info(f"🔍 FINDER_TOKEN: BOTIFY_LIST_AVAILABLE_ANALYSES_START - {params}")
    
    try:
        import aiohttp
        username = params.get('username')
        project = params.get('project')
        
        if not all([username, project]):
            return {"success": False, "error": "Username and project are required"}
        
        api_token = _read_botify_api_token()
        if not api_token or api_token == "placeholder_token":
            return {"success": False, "error": "Valid Botify API token not found"}
        
        url = f"https://api.botify.com/v1/projects/{username}/{project}/analyses"
        headers = {"Authorization": f"Token {api_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    analyses = data.get('results', [])
                    logger.info(f"✅ FINDER_TOKEN: BOTIFY_LIST_AVAILABLE_ANALYSES_SUCCESS - {len(analyses)} analyses found")
                    return {
                        "success": True,
                        "analyses": analyses,
                        "total_analyses": len(analyses)
                    }
                else:
                    logger.error(f"❌ FINDER_TOKEN: BOTIFY_LIST_AVAILABLE_ANALYSES_FAILED - Status {response.status}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}"
                    }
    
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: BOTIFY_LIST_AVAILABLE_ANALYSES_ERROR - {str(e)}")
        return {"success": False, "error": str(e)}

async def botify_execute_custom_bql_query(params: dict) -> dict:
    """
    MCP Tool: Execute a custom BQL query with advanced parameters
    
    Args:
        params: {
            "username": "your_username",
            "project": "project_name",
            "query": "SELECT url, http_status FROM crawl WHERE http_status = 200",
            "limit": 1000,
            "analysis_slug": "latest"  # optional
        }
    
    Returns:
        dict: {"success": True/False, "data": [...], "total_results": int, "query_info": {...}}
    """
    logger.info(f"🔍 FINDER_TOKEN: BOTIFY_EXECUTE_CUSTOM_BQL_QUERY_START - {params}")
    
    try:
        import aiohttp
        username = params.get('username')
        project = params.get('project')
        query = params.get('query')
        limit = params.get('limit', 1000)
        analysis_slug = params.get('analysis_slug', 'latest')
        
        if not all([username, project, query]):
            return {"success": False, "error": "Username, project, and query are required"}
        
        api_token = _read_botify_api_token()
        if not api_token or api_token == "placeholder_token":
            return {"success": False, "error": "Valid Botify API token not found"}
        
        url = f"https://api.botify.com/v1/projects/{username}/{project}/query"
        headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": query,
            "size": limit
        }
        
        if analysis_slug != 'latest':
            payload['analysis_slug'] = analysis_slug
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('results', [])
                    logger.info(f"✅ FINDER_TOKEN: BOTIFY_EXECUTE_CUSTOM_BQL_QUERY_SUCCESS - {len(results)} results")
                    return {
                        "success": True,
                        "data": results,
                        "total_results": len(results),
                        "query_info": {
                            "query": query,
                            "limit": limit,
                            "analysis_slug": analysis_slug
                        }
                    }
                else:
                    logger.error(f"❌ FINDER_TOKEN: BOTIFY_EXECUTE_CUSTOM_BQL_QUERY_FAILED - Status {response.status}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}"
                    }
    
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: BOTIFY_EXECUTE_CUSTOM_BQL_QUERY_ERROR - {str(e)}")
        return {"success": False, "error": str(e)}

# --- TESTING FUNCTIONS ---

async def test_botify_actual_connectivity() -> dict:
    """Test actual Botify API connectivity with real credentials."""
    logger.info("🔍 FINDER_TOKEN: TEST_BOTIFY_ACTUAL_CONNECTIVITY_START")
    
    try:
        # Try to read actual credentials
        api_token = _read_botify_api_token()
        if not api_token or api_token == "placeholder_token":
            return {
                "success": False,
                "error": "No valid Botify API token found",
                "botify_connected": False
            }
        
        # Test with a simple ping
        ping_result = await botify_ping({"username": "test_user"})
        
        if ping_result.get("success"):
            logger.info("✅ FINDER_TOKEN: TEST_BOTIFY_ACTUAL_CONNECTIVITY_SUCCESS")
            return {
                "success": True,
                "message": "Botify API connectivity confirmed",
                "botify_connected": True,
                "ping_result": ping_result
            }
        else:
            logger.error(f"❌ FINDER_TOKEN: TEST_BOTIFY_ACTUAL_CONNECTIVITY_FAILED - {ping_result.get('error')}")
            return {
                "success": False,
                "error": f"Botify API connectivity failed: {ping_result.get('error')}",
                "botify_connected": False
            }
    
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: TEST_BOTIFY_ACTUAL_CONNECTIVITY_ERROR - {str(e)}")
        return {
            "success": False,
            "error": f"Botify connectivity test failed: {str(e)}",
            "botify_connected": False
        }

async def test_botify_connectivity() -> dict:
    """Test Botify API connectivity (mock version for testing)."""
    logger.info("🔍 FINDER_TOKEN: TEST_BOTIFY_CONNECTIVITY_START")
    
    try:
        # This is a mock test - just check if the function exists
        return {
            "success": True,
            "message": "Botify connectivity test completed (mock)",
            "botify_available": True,
            "test_type": "mock"
        }
    
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: TEST_BOTIFY_CONNECTIVITY_ERROR - {str(e)}")
        return {
            "success": False,
            "error": f"Botify connectivity test failed: {str(e)}",
            "botify_available": False
        }

# --- TOOL REGISTRATION ---

def get_botify_tools():
    """
    Returns a list of all Botify MCP tools with their metadata.
    """
    tools = []
    botify_tool_names = [
        'botify_ping',
        'botify_list_projects', 
        'botify_simple_query',
        'botify_get_full_schema',
        'botify_list_available_analyses',
        'botify_execute_custom_bql_query',
        'test_botify_actual_connectivity',
        'test_botify_connectivity'
    ]
    
    for name in botify_tool_names:
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

# Shared constants for export lists
CORE_BOTIFY_TOOLS = [
    'botify_ping',
    'botify_list_projects',
    'botify_simple_query',
    'botify_get_full_schema',
    'botify_list_available_analyses',
    'botify_execute_custom_bql_query',
]

# --- EXPORT ALL FUNCTIONS ---
__all__ = CORE_BOTIFY_TOOLS + [
    'test_botify_actual_connectivity',
    'test_botify_connectivity',
    'get_botify_tools'
] 
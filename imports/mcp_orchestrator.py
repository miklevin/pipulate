"""
MCP Orchestrator - The core logic for parsing and executing formal MCP tool calls.
This module provides the plumbing to handle the final step of the progressive
enhancement ladder: full, spec-compliant MCP tool usage.
"""
import re
import json
import asyncio
import tools
from loguru import logger

def parse_mcp_request(response_text: str) -> tuple | None:
    """
    Parses the raw text from an LLM to find a formal MCP tool call.

    Args:
        response_text: The full response from the LLM.

    Returns:
        A tuple containing (tool_name, inner_content) if a tool call is found,
        otherwise None.
    """
    # Regex to find <tool> tags, capturing the name and the inner content.
    # re.DOTALL allows '.' to match newlines, which is crucial for multi-line params.
    match = re.search(r'<tool\s+name="([^"]+)">(.*?)</tool>', response_text, re.DOTALL)
    if match:
        tool_name = match.group(1)
        inner_content = match.group(2)
        logger.info(f"MCP PARSER: Found potential tool call for '{tool_name}'.")
        return tool_name, inner_content
    return None

async def execute_mcp_tool(tool_name: str, inner_content: str) -> str:
    """
    Executes a tool call and returns the formatted XML output.

    Args:
        tool_name: The name of the tool to execute.
        inner_content: The content inside the <tool> tag, including <params>.

    Returns:
        A string containing the <tool_output> XML block.
    """
    params = {}
    try:
        # Extract the content of the <params> tag, expecting a JSON object
        params_match = re.search(r'<params>\s*(\{.*?\})\s*</params>', inner_content, re.DOTALL)
        if params_match:
            params_str = params_match.group(1).strip()
            # The content is expected to be JSON
            params = json.loads(params_str)
            logger.info(f"MCP EXECUTOR: Parsed params for '{tool_name}': {params}")
        else:
            logger.warning(f"MCP EXECUTOR: No <params> tag found for tool '{tool_name}'. Executing with empty params.")

        # Get the tool registry
        registry = tools.get_all_tools()
        tool_function = registry.get(tool_name)

        if not tool_function:
            error_message = f"Tool '{tool_name}' not found in registry."
            logger.error(f"MCP EXECUTOR: {error_message}")
            result = {"success": False, "error": error_message}
        else:
            # Execute the tool
            logger.info(f"MCP EXECUTOR: Executing tool '{tool_name}'.")
            result = await tool_function(params)
            logger.info(f"MCP EXECUTOR: Tool '{tool_name}' executed successfully.")

    except json.JSONDecodeError as e:
        error_message = f"Invalid JSON in <params> for tool '{tool_name}': {e}"
        logger.error(f"MCP EXECUTOR: {error_message}")
        result = {"success": False, "error": error_message}
    except Exception as e:
        error_message = f"An unexpected error occurred while executing tool '{tool_name}': {e}"
        logger.error(f"MCP EXECUTOR: {error_message}", exc_info=True)
        result = {"success": False, "error": error_message}

    # Wrap the result in <tool_output> tags, ensuring it's a valid JSON string inside
    output_json = json.dumps(result, indent=2)
    return f"<tool_output>\n{output_json}\n</tool_output>"

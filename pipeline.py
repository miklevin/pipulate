#!/usr/bin/env python3
"""
pipeline.py - Extracted from server.py
Generated on 2025-07-04 21:26:18
"""

import asyncio
import functools
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

# Import required dependencies from server module (avoid circular imports by being selective)
from loguru import logger
from fasthtml.common import Card, Div, H1, H2, H3, H4, P, A, Input, Button, Form
import re

# Import centralized configuration
from config import PCONFIG, friendly_names

# Temporary title_name function to avoid circular imports
def title_name(word: str) -> str:
    """Convert a word to title case with some basic clean-up for display."""
    if not word:
        return word
    
    # Handle special cases
    word = word.replace('_', ' ')
    word = word.replace('-', ' ')
    
    # Basic title case
    return word.title()

# Configuration now imported from centralized config module

# Import append_to_conversation function with late import to avoid circular dependency
def append_to_conversation(message: str, role: str = 'system') -> None:
    """Temporary stub - will import from server when circular import is resolved"""
    try:
        from server import append_to_conversation as _append_to_conversation
        return _append_to_conversation(message, role)
    except ImportError:
        # Fallback if server import fails
        logger.info(f"[CONVERSATION] {role}: {message[:100]}...")
        pass

# Extracted block: class_pipulate_1675
class Pipulate:
    """Central coordinator for pipelines and chat functionality.

    This class serves as the main interface for plugins to access
    shared functionality without relying on globals.

    As Pipulate evolves toward its "Digital Workshop" vision, this coordinator
    will support:
    - Sub-plugin architecture (steps expanding to full-screen apps)
    - Content curation systems (archive surfing, variant creation)
    - Progressive distillation workflows (search, sort, sieve, story)
    - Local-first creative exploration with privacy preservation

    The centralized coordination pattern enables sophisticated interaction
    monitoring and behavioral pattern analysis while maintaining the
    "vibrating edge" of creative freedom that powers genuine innovation.
    """
    PRESERVE_REFILL = True
    UNLOCK_BUTTON_LABEL = '🔓 Unlock'

    def __init__(self, pipeline_table, chat_instance=None):
        """Initialize Pipulate with required dependencies.

        Args:
            pipeline_table: The database table for storing pipeline state
            chat_instance: Optional chat coordinator instance
        """
        self.pipeline_table = pipeline_table
        self.chat = chat_instance
        self.message_queue = self.OrderedMessageQueue()

    def append_to_history(self, message: str, role: str='system') -> None:
        """Add a message to the LLM conversation history without triggering a response.

        This is the preferred way for workflows to update the LLM's context about:
        - UI state changes
        - Form submissions
        - Validation results
        - Explanatory text shown to users
        - Step completion status

        Args:
            message: The message to add to history
            role: The role of the message sender ("system", "user", "assistant")
        """
        append_to_conversation(message, role=role)

    class OrderedMessageQueue:
        """A lightweight queue to ensure messages are delivered in order.

        This class creates a simple message queue that ensures messages are delivered
        in the exact order they are added, without requiring explicit delays between
        messages. It's used to fix the message streaming order issues.

        As part of the Digital Workshop evolution, this queue will support:
        - Interaction pattern recognition for adaptive workflows
        - State transition tracking for sub-plugin applications
        - Creative session analysis for distillation workflows
        - Privacy-preserving behavioral insights for local optimization

        The workflow state tracking enables sophisticated user interaction
        analysis while keeping all data local for maximum creative freedom.
        """

        def __init__(self):
            self.queue = []
            self._processing = False
            self._current_step = None
            self._step_started = False
            self._step_complete = False
            self._workflow_context = None

        async def add(self, pipulate, message, **kwargs):
            """Add a message to the queue and process if not already processing.
            
            This method no longer handles conversation history - that's now managed by pipulate.stream.
            """
            logger.info(f'[🔄 QUEUEING] {message[:100]}...')
            self.queue.append((pipulate, message, kwargs))
            if not self._processing:
                await self._process_queue()

        async def _process_queue(self):
            """Process messages in the queue.
            
            This method now focuses solely on queue processing and streaming,
            leaving conversation history management to pipulate.stream.
            """
            if self._processing:
                return
            
            self._processing = True
            try:
                while self.queue:
                    pipulate, message, kwargs = self.queue.pop(0)
                    await pipulate.stream(message, **kwargs)
            finally:
                self._processing = False

        def mark_step_complete(self, step_num):
            """Mark a step as completed."""
            self._current_step = step_num
            self._step_complete = True

        def mark_step_started(self, step_num):
            """Mark a step as started but not completed."""
            self._current_step = step_num
            self._step_started = True

    def make_singular(self, word):
        """Convert a potentially plural word to its singular form using simple rules.

        This uses basic suffix replacement rules to handle common English plurals.
        It's designed for the 80/20 rule - handling common cases without complexity.

        Args:
            word (str): The potentially plural word to convert

        Returns:
            str: The singular form of the word
        """
        word = word.strip()
        if not word:
            return word
        if word.lower() in ('data', 'media', 'series', 'species', 'news'):
            return word
        irregulars = {'children': 'child', 'people': 'person', 'men': 'man', 'women': 'woman', 'teeth': 'tooth', 'feet': 'foot', 'geese': 'goose', 'mice': 'mouse', 'criteria': 'criterion'}
        if word.lower() in irregulars:
            return irregulars[word.lower()]
        if word.lower().endswith('ies'):
            return word[:-3] + 'y'
        if word.lower().endswith('ves'):
            return word[:-3] + 'f'
        if word.lower().endswith('xes') or word.lower().endswith('sses') or word.lower().endswith('shes') or word.lower().endswith('ches'):
            return word[:-2]
        if word.lower().endswith('s') and (not word.lower().endswith('ss')):
            return word[:-1]
        return word

    def set_chat(self, chat_instance):
        """Set the chat instance after initialization."""
        self.chat = chat_instance

    def get_message_queue(self):
        """Return the message queue instance for ordered message delivery."""
        return self.message_queue

    def step_button(self, visual_step_number: str, preserve: bool=False, revert_label: str=None) -> str:
        """
        Formats the revert button text.
        Uses visual_step_number for "Step X" numbering if revert_label is not provided.

        Args:
            visual_step_number: The visual step number (e.g., "1", "2", "3") based on position in workflow
            preserve: Whether to use the preserve symbol (⟲) instead of revert symbol (↶)
            revert_label: Custom label to use instead of "Step X" format
        """
        symbol = '⟲' if preserve else '↶'
        if revert_label:
            button_text = f'{symbol}\xa0{revert_label}'
        else:
            button_text = f'{symbol}\xa0Step\xa0{visual_step_number}'
        return button_text

    
    def get_ui_constants(self):
        """Access centralized UI constants through dependency injection."""
        return PCONFIG['UI_CONSTANTS']
    
    def get_config(self):
        """Access centralized configuration through dependency injection."""
        return PCONFIG
    
    def get_button_border_radius(self):
        """Get the global button border radius setting."""
        return PCONFIG['UI_CONSTANTS']['BUTTON_STYLES']['BORDER_RADIUS']

    def register_workflow_routes(self, plugin_instance):
        """
        Register standard and step-specific routes for a workflow plugin.
        
        This helper extracts the common route registration boilerplate from workflow __init__ methods,
        while maintaining the WET principle - each workflow still explicitly calls this method.
        
        Args:
            plugin_instance: The workflow plugin instance with app, APP_NAME, and steps attributes
        """
        app_name = plugin_instance.APP_NAME
        steps = plugin_instance.steps
        
        # Standard workflow lifecycle routes
        routes = [
            (f'/{app_name}/init', plugin_instance.init, ['POST']),
            (f'/{app_name}/revert', plugin_instance.handle_revert, ['POST']),
            (f'/{app_name}/unfinalize', plugin_instance.unfinalize, ['POST'])
        ]
        
        # Dynamically create routes for each step from the plugin's steps list
        for step_obj in steps:
            step_id = step_obj.id
            handler_method = getattr(plugin_instance, step_id, None)
            if handler_method:
                current_methods = ['GET']
                if step_id == 'finalize':
                    current_methods.append('POST')
                routes.append((f'/{app_name}/{step_id}', handler_method, current_methods))
            
            # Only data steps (not 'finalize') have explicit _submit handlers
            if step_id != 'finalize':
                submit_handler_method = getattr(plugin_instance, f'{step_id}_submit', None)
                if submit_handler_method:
                    routes.append((f'/{app_name}/{step_id}_submit', submit_handler_method, ['POST']))

        # Register all routes with the FastHTML app
        for path, handler, *methods_list_arg in routes:
            current_methods = methods_list_arg[0] if methods_list_arg else ['GET']
            plugin_instance.app.route(path, methods=current_methods)(handler)

    async def log_api_call_details(self, pipeline_id: str, step_id: str, call_description: str, method: str, url: str, headers: dict, payload: Optional[dict]=None, response_status: Optional[int]=None, response_preview: Optional[str]=None, response_data: Optional[dict]=None, curl_command: Optional[str]=None, python_command: Optional[str]=None, estimated_rows: Optional[int]=None, actual_rows: Optional[int]=None, file_path: Optional[str]=None, file_size: Optional[str]=None, notes: Optional[str]=None):
        """Log complete API call details for extreme observability and Jupyter reproduction.
        
        This provides the same level of transparency for API calls as is used in BQL query logging,
        including copy-paste ready Python code for Jupyter notebook reproduction.
        """
        log_entry_parts = []
        log_entry_parts.append(f'  [API Call] {call_description or "API Request"}')
        log_entry_parts.append(f'  Pipeline ID: {pipeline_id}')
        log_entry_parts.append(f'  Step ID: {step_id}')
        log_entry_parts.append(f'  Method: {method}')
        log_entry_parts.append(f'  URL: {url}')
        if headers:
            headers_preview = {k: v for k, v in headers.items() if k.lower() not in ['authorization', 'cookie', 'x-api-key']}
            if len(headers_preview) != len(headers):
                headers_preview['<REDACTED_AUTH_HEADERS>'] = f'{len(headers) - len(headers_preview)} hidden'
            # Use Rich JSON display for headers
            pretty_headers = rich_json_display(headers_preview, title="API Headers", console_output=True, log_output=True)
            log_entry_parts.append(f'  Headers: {pretty_headers}')
        if payload:
            try:
                # Use Rich JSON display for payload
                pretty_payload = rich_json_display(payload, title="API Payload", console_output=True, log_output=True)
                log_entry_parts.append(f'  Payload:\n{pretty_payload}')
            except Exception:
                log_entry_parts.append(f'  Payload: {payload}')
        if curl_command:
            log_entry_parts.append(f'  cURL Command:\n{curl_command}')
        if python_command:
            # Use centralized emoji configuration for console messages
            python_emoji = PCONFIG['UI_CONSTANTS']['EMOJIS']['PYTHON_CODE']
            snippet_emoji = PCONFIG['UI_CONSTANTS']['EMOJIS']['CODE_SNIPPET']
            comment_divider = PCONFIG['UI_CONSTANTS']['CODE_FORMATTING']['COMMENT_DIVIDER']
            snippet_intro = PCONFIG['UI_CONSTANTS']['CONSOLE_MESSAGES']['PYTHON_SNIPPET_INTRO'].format(
                python_emoji=python_emoji, 
                snippet_emoji=snippet_emoji
            )
            snippet_end = PCONFIG['UI_CONSTANTS']['CONSOLE_MESSAGES']['PYTHON_SNIPPET_END'].format(
                python_emoji=python_emoji, 
                snippet_emoji=snippet_emoji
            )
            # Add Python snippet with complete BEGIN/END block
            log_entry_parts.append(f'{snippet_intro}\n{python_command}')
            log_entry_parts.append('# Note: The API token should be loaded from a secure file location.')
            log_entry_parts.append(f'{comment_divider}')
            log_entry_parts.append(f'{snippet_end}')
        if estimated_rows is not None:
            log_entry_parts.append(f'  Estimated Rows (from pre-check): {estimated_rows:,}')
        if actual_rows is not None:
            log_entry_parts.append(f'  Actual Rows Downloaded: {actual_rows:,}')
        if response_status is not None:
            log_entry_parts.append(f'  Response Status: {response_status}')
        if response_preview:
            try:
                parsed = json.loads(response_preview)
                # Use Rich JSON display for response preview
                pretty_preview = rich_json_display(parsed, title="API Response Preview", console_output=True, log_output=True)
                log_entry_parts.append(f'  Response Preview:\n{pretty_preview}')
            except Exception:
                log_entry_parts.append(f'  Response Preview:\n{response_preview}')
        
        # Enhanced transparency for discovery endpoints - log full response data
        is_discovery_endpoint = self._is_discovery_endpoint(url)
        if response_data and is_discovery_endpoint:
            try:
                # Use Rich JSON display for discovery response
                pretty_response = rich_json_display(response_data, title=f"🔍 Discovery Response: {call_description}", console_output=True, log_output=True)
                log_entry_parts.append(f'  🔍 FULL RESPONSE DATA (Discovery Endpoint):\n{pretty_response}')
                
            except Exception as e:
                log_entry_parts.append(f'  🔍 FULL RESPONSE DATA (Discovery Endpoint): [Error formatting JSON: {e}]\n{response_data}')
                
                # Still display in console even if JSON formatting fails
                console.print(f"❌ Discovery Response Error: {e}", style="red")
                console.print(f"Raw data: {str(response_data)}", style="dim")
        
        if file_path:
            log_entry_parts.append(f'  Associated File Path: {file_path}')
        if file_size:
            log_entry_parts.append(f'  Associated File Size: {file_size}')
        if notes:
            log_entry_parts.append(f'  Notes: {notes}')
        
        full_log_message = '\n'.join(log_entry_parts)
        logger.info(f'\n🚀 === API CALL TRANSPARENCY ===\n{full_log_message}\n🚀 === END API TRANSPARENCY ===')
        is_bql = 'bql' in (call_description or '').lower() or 'botify query language' in (call_description or '').lower()
    
    def _is_discovery_endpoint(self, url: str) -> bool:
        """Detect if this is a key discovery endpoint that should have full response logging.
        
        Args:
            url: The API endpoint URL
            
        Returns:
            bool: True if this is a discovery endpoint that should log full response data
        """
        discovery_patterns = [
            '/analyses/',  # Covers both /analyses/{username}/{project}/light and regular analyses
            '/advanced_export',  # Field discovery endpoint
        ]
        
        return any(pattern in url for pattern in discovery_patterns)

    async def log_mcp_call_details(self, operation_id: str, tool_name: str, operation_type: str, mcp_block: str=None, request_payload: Optional[dict]=None, response_data: Optional[dict]=None, response_status: Optional[int]=None, external_api_url: Optional[str]=None, external_api_method: str='GET', external_api_headers: Optional[dict]=None, external_api_payload: Optional[dict]=None, external_api_response: Optional[dict]=None, external_api_status: Optional[int]=None, execution_time_ms: Optional[float]=None, notes: Optional[str]=None):
        """Log complete MCP operation details for extreme observability and Jupyter reproduction.
        
        This provides the same level of transparency for MCP operations as the BQL query logging,
        including copy-paste ready Python code for external API reproduction.
        
        Args:
            operation_id: Unique identifier for this MCP operation
            tool_name: Name of the MCP tool being executed
            operation_type: Type of operation (tool_execution, api_call, etc.)
            mcp_block: Raw MCP block that triggered the operation
            request_payload: Payload sent to MCP tool executor
            response_data: Response from MCP tool executor
            response_status: HTTP status from MCP tool executor
            external_api_url: URL of external API called (if any)
            external_api_method: HTTP method for external API
            external_api_headers: Headers sent to external API
            external_api_payload: Payload sent to external API
            external_api_response: Response from external API
            external_api_status: HTTP status from external API
            execution_time_ms: Total execution time in milliseconds
            notes: Additional context or notes
        """
        log_entry_parts = []
        log_entry_parts.append(f'  [MCP Operation] {operation_type.title()} - {tool_name}')
        log_entry_parts.append(f'  Operation ID: {operation_id}')
        log_entry_parts.append(f'  Tool Name: {tool_name}')
        log_entry_parts.append(f'  Operation Type: {operation_type}')
        log_entry_parts.append(f'  Timestamp: {self.get_timestamp()}')
        
        if execution_time_ms is not None:
            log_entry_parts.append(f'  Execution Time: {execution_time_ms:.2f}ms')
        
        # MCP Block Details
        if mcp_block:
            log_entry_parts.append(f'  MCP Block:')
            # Indent each line of the MCP block for better readability
            indented_block = '\n'.join(f'    {line}' for line in mcp_block.strip().split('\n'))
            log_entry_parts.append(indented_block)
        
        # Internal MCP Tool Executor Request
        if request_payload:
            log_entry_parts.append('')  # Extra space for visual separation
            log_entry_parts.append(f'  MCP Tool Executor Request:')
            log_entry_parts.append(f'    URL: http://127.0.0.1:5001/mcp-tool-executor')
            log_entry_parts.append(f'    Method: POST')
            try:
                # Use Rich JSON display for MCP request payload
                pretty_payload = rich_json_display(request_payload, title="MCP Tool Executor Request", console_output=True, log_output=True)
                # Indent the JSON for consistency
                indented_payload = '\n'.join(f'    {line}' for line in pretty_payload.split('\n'))
                log_entry_parts.append(f'    Payload:\n{indented_payload}')
            except Exception:
                log_entry_parts.append(f'    Payload: {request_payload}')
        
        # Internal MCP Tool Executor Response
        if response_data or response_status:
            log_entry_parts.append('')  # Extra space for visual separation
            log_entry_parts.append(f'  MCP Tool Executor Response:')
            if response_status:
                log_entry_parts.append(f'    Status: {response_status}')
            if response_data:
                try:
                    # Use Rich JSON display for MCP response data
                    pretty_response = rich_json_display(response_data, title="MCP Tool Executor Response", console_output=True, log_output=True)
                    # Indent the JSON for consistency
                    indented_response = '\n'.join(f'    {line}' for line in pretty_response.split('\n'))
                    log_entry_parts.append(f'    Response:\n{indented_response}')
                except Exception:
                    log_entry_parts.append(f'    Response: {response_data}')
        
        # External API Call Details (the actual external service)
        if external_api_url:
            log_entry_parts.append('')  # Extra space for visual separation
            log_entry_parts.append(f'  External API Call:')
            log_entry_parts.append(f'    URL: {external_api_url}')
            log_entry_parts.append(f'    Method: {external_api_method}')
            
            if external_api_headers:
                # Redact sensitive headers
                headers_preview = {k: v for k, v in external_api_headers.items() if k.lower() not in ['authorization', 'cookie', 'x-api-key']}
                if len(headers_preview) != len(external_api_headers):
                    headers_preview['<REDACTED_AUTH_HEADERS>'] = f'{len(external_api_headers) - len(headers_preview)} hidden'
                # Use Rich JSON display for external API headers
                pretty_headers = rich_json_display(headers_preview, title="External API Headers", console_output=True, log_output=True)
                log_entry_parts.append(f'    Headers: {pretty_headers}')
            
            if external_api_payload:
                try:
                    # Use Rich JSON display for external API payload
                    pretty_payload = rich_json_display(external_api_payload, title="External API Payload", console_output=True, log_output=True)
                    indented_payload = '\n'.join(f'    {line}' for line in pretty_payload.split('\n'))
                    log_entry_parts.append(f'    Payload:\n{indented_payload}')
                except Exception:
                    log_entry_parts.append(f'    Payload: {external_api_payload}')
            
            if external_api_status:
                log_entry_parts.append(f'    Response Status: {external_api_status}')
            
            if external_api_response:
                try:
                    # Use Rich JSON display for external API response
                    pretty_response = rich_json_display(external_api_response, title="External API Response", console_output=True, log_output=True)
                    indented_response = '\n'.join(f'    {line}' for line in pretty_response.split('\n'))
                    log_entry_parts.append(f'    Response:\n{indented_response}')
                except Exception:
                    log_entry_parts.append(f'    Response: {external_api_response}')
        
        # Generate copy-paste ready Python code for Jupyter reproduction
        if external_api_url:
            python_code = self._generate_mcp_python_code(
                tool_name=tool_name,
                external_api_url=external_api_url,
                external_api_method=external_api_method,
                external_api_headers=external_api_headers,
                external_api_payload=external_api_payload,
                operation_id=operation_id
            )
            
            # Use centralized emoji configuration for console messages
            python_emoji = PCONFIG['UI_CONSTANTS']['EMOJIS']['PYTHON_CODE']
            snippet_emoji = PCONFIG['UI_CONSTANTS']['EMOJIS']['CODE_SNIPPET']
            comment_divider = PCONFIG['UI_CONSTANTS']['CODE_FORMATTING']['COMMENT_DIVIDER']
            snippet_intro = PCONFIG['UI_CONSTANTS']['CONSOLE_MESSAGES']['PYTHON_SNIPPET_INTRO'].format(
                python_emoji=python_emoji, 
                snippet_emoji=snippet_emoji
            )
            snippet_end = PCONFIG['UI_CONSTANTS']['CONSOLE_MESSAGES']['PYTHON_SNIPPET_END'].format(
                python_emoji=python_emoji, 
                snippet_emoji=snippet_emoji
            )
            
            # Add Python snippet with complete BEGIN/END block and visual separation
            log_entry_parts.append('')  # Extra space before Python code
            log_entry_parts.append(f'{snippet_intro}')
            log_entry_parts.append(f'{comment_divider}')
            log_entry_parts.append(f'{python_code}')
            log_entry_parts.append('# Note: This code reproduces the external API call made by the MCP tool.')
            log_entry_parts.append(f'{comment_divider}')
            log_entry_parts.append(f'{snippet_end}')
            log_entry_parts.append('')  # Extra space after Python code
        
        if notes:
            log_entry_parts.append(f'  Notes: {notes}')
        
        full_log_message = '\n'.join(log_entry_parts)
        logger.info(f'\n🚀 === MCP OPERATION TRANSPARENCY ===\n{full_log_message}\n🚀 === END MCP TRANSPARENCY ===')

    def _generate_mcp_python_code(self, tool_name: str, external_api_url: str, external_api_method: str='GET', external_api_headers: Optional[dict]=None, external_api_payload: Optional[dict]=None, operation_id: str=None) -> str:
        """Generate copy-paste ready Python code for reproducing MCP external API calls in Jupyter.
        
        This mirrors the pattern used in BQL query logging but for MCP operations.
        """
        lines = []
        lines.append(f'# MCP Tool Reproduction: {tool_name}')
        if operation_id:
            lines.append(f'# Operation ID: {operation_id}')
        lines.append(f'# Generated at: {self.get_timestamp()}')
        lines.append('')
        lines.append('import aiohttp')
        lines.append('import asyncio')
        lines.append('import json')
        lines.append('from pprint import pprint')
        lines.append('')
        lines.append('async def reproduce_mcp_call():')
        lines.append('    """Reproduce the external API call made by the MCP tool."""')
        lines.append('    ')
        lines.append(f'    url = "{external_api_url}"')
        lines.append(f'    method = "{external_api_method.upper()}"')
        lines.append('    ')
        
        # Headers
        if external_api_headers:
            lines.append('    headers = {')
            for key, value in external_api_headers.items():
                if key.lower() in ['authorization', 'cookie', 'x-api-key']:
                    lines.append(f'        "{key}": "REDACTED_FOR_SECURITY",')
                else:
                    lines.append(f'        "{key}": "{value}",')
            lines.append('    }')
        else:
            lines.append('    headers = {}')
        lines.append('    ')
        
        # Payload
        if external_api_payload and external_api_method.upper() in ['POST', 'PUT', 'PATCH']:
            lines.append('    payload = {')
            try:
                for key, value in external_api_payload.items():
                    if isinstance(value, str):
                        lines.append(f'        "{key}": "{value}",')
                    else:
                        lines.append(f'        "{key}": {json.dumps(value)},')
            except Exception:
                lines.append(f'        # Payload: {external_api_payload}')
            lines.append('    }')
        else:
            lines.append('    payload = None')
        lines.append('    ')
        
        # Async session and request
        lines.append('    async with aiohttp.ClientSession() as session:')
        if external_api_method.upper() == 'GET':
            lines.append('        async with session.get(url, headers=headers) as response:')
        elif external_api_method.upper() == 'POST':
            lines.append('        async with session.post(url, headers=headers, json=payload) as response:')
        elif external_api_method.upper() == 'PUT':
            lines.append('        async with session.put(url, headers=headers, json=payload) as response:')
        elif external_api_method.upper() == 'DELETE':
            lines.append('        async with session.delete(url, headers=headers) as response:')
        else:
            lines.append(f'        async with session.request("{external_api_method.upper()}", url, headers=headers, json=payload) as response:')
        
        lines.append('            print(f"Status: {response.status}")')
        lines.append('            print(f"Headers: {dict(response.headers)}")')
        lines.append('            ')
        lines.append('            if response.content_type == "application/json":')
        lines.append('                data = await response.json()')
        lines.append('                print("JSON Response:")')
        lines.append('                pprint(data)')
        lines.append('                return data')
        lines.append('            else:')
        lines.append('                text = await response.text()')
        lines.append('                print("Text Response:")')
        lines.append('                print(text)')
        lines.append('                return text')
        lines.append('')
        divider = PCONFIG['UI_CONSTANTS']['CODE_FORMATTING']['COMMENT_DIVIDER']
        lines.append(divider)
        lines.append('# EXECUTION: Choose your environment')
        lines.append(divider)
        lines.append('')
        lines.append('# For Jupyter Notebooks (recommended):')
        lines.append('result = await reproduce_mcp_call()')
        lines.append('print("\\nFinal result:")')
        lines.append('pprint(result)')
        lines.append('')
        lines.append('# For Python scripts (uncomment if needed):')
        lines.append('# if __name__ == "__main__":')
        lines.append('#     result = asyncio.run(reproduce_mcp_call())')
        lines.append('#     print("\\nFinal result:")')
        lines.append('#     pprint(result)')
        
        return '\n'.join(lines)

    # ========================================
    # REUSABLE BOTIFY PYTHON CODE GENERATION
    # ========================================
    
    # Botify Code Generation Utilities (externalized to helpers/botify/code_generators.py)
    # Import the externalized Botify code generation functions
    @property
    def botify_generators(self):
        """Lazy load Botify code generators to avoid import issues"""
        if not hasattr(self, '_botify_generators'):
            from helpers.botify.code_generators import BotifyCodeGenerators
            self._botify_generators = BotifyCodeGenerators(self.ui_constants)
        return self._botify_generators
    
    def generate_botify_code_header(self, *args, **kwargs):
        """Delegate to externalized Botify code generators"""
        return self.botify_generators.generate_botify_code_header(*args, **kwargs)
    
    def generate_botify_token_loader(self, *args, **kwargs):
        """Delegate to externalized Botify code generators"""
        return self.botify_generators.generate_botify_token_loader(*args, **kwargs)
    
    def generate_botify_http_client(self, *args, **kwargs):
        """Delegate to externalized Botify code generators"""
        return self.botify_generators.generate_botify_http_client(*args, **kwargs)
    
    def generate_botify_main_executor(self, *args, **kwargs):
        """Delegate to externalized Botify code generators"""
        return self.botify_generators.generate_botify_main_executor(*args, **kwargs)
    
    def create_folder_button(self, *args, **kwargs):
        """Delegate to externalized Botify code generators"""
        return self.botify_generators.create_folder_button(*args, **kwargs)

    # ========================================
    # ADVANCED BOTIFY CODE GENERATION UTILITIES
    # ========================================
    
    def generate_botify_bqlv2_python_code(self, *args, **kwargs):
        """Delegate to externalized Botify code generators"""
        # Note: This function is missing from the externalized module but is complex
        # For now, delegate to a simplified version or handle the missing BQLv2/BQLv1 functions
        # TODO: Add the complex BQLv2/BQLv1 generators to the externalized module
        raise NotImplementedError("BQLv2 code generation needs to be added to externalized module")

    def generate_botify_bqlv1_python_code(self, *args, **kwargs):
        """Delegate to externalized Botify code generators"""
        # TODO: Add the complex BQLv1 generator to the externalized module
        raise NotImplementedError("BQLv1 code generation needs to be added to externalized module")

    def get_botify_analysis_path(self, *args, **kwargs):
        """Delegate to externalized Botify code generators"""
        return self.botify_generators.get_botify_analysis_path(*args, **kwargs)

    def fmt(self, endpoint: str) -> str:
        """Format an endpoint string into a human-readable form."""
        if endpoint in friendly_names:
            return friendly_names[endpoint]
        return title_name(endpoint)

    def _get_clean_state(self, pkey):
        try:
            record = self.pipeline_table[pkey]
            state = json.loads(record.data)
            state.pop('created', None)
            state.pop('updated', None)
            return state
        except (NotFoundError, json.JSONDecodeError):
            return {}

    def get_timestamp(self) -> str:
        return datetime.now().isoformat()

    def get_plugin_context(self, plugin_instance=None):
        """
        Returns the context information about the current plugin and profile.

        Args:
            plugin_instance: Optional plugin instance to extract name from

        Returns:
            dict: Contains plugin_name, profile_id, and profile_name
        """
        profile_id = get_current_profile_id()
        profile_name = get_profile_name()
        plugin_name = None
        display_name = None
        if plugin_instance:
            if hasattr(plugin_instance, 'DISPLAY_NAME'):
                display_name = plugin_instance.DISPLAY_NAME
            if hasattr(plugin_instance, 'name'):
                plugin_name = plugin_instance.name
            elif hasattr(plugin_instance, '__class__'):
                plugin_name = plugin_instance.__class__.__name__
            if plugin_name and (not display_name):
                if plugin_name in friendly_names:
                    display_name = friendly_names[plugin_name]
                else:
                    display_name = title_name(plugin_name)
        return {'plugin_name': display_name or plugin_name, 'internal_name': plugin_name, 'profile_id': profile_id, 'profile_name': profile_name}

    def initialize_if_missing(self, pkey: str, initial_step_data: dict=None) -> tuple[Optional[dict], Optional[Card]]:
        try:
            state = self.read_state(pkey)
            if state:
                return (state, None)
            now = self.get_timestamp()
            state = {'created': now, 'updated': now}
            if initial_step_data:
                app_name = None
                if 'app_name' in initial_step_data:
                    app_name = initial_step_data.pop('app_name')
                state.update(initial_step_data)
            self.pipeline_table.insert({'pkey': pkey, 'app_name': app_name if app_name else None, 'data': json.dumps(state), 'created': now, 'updated': now})
            return (state, None)
        except:
            error_card = Card(H3('ID Already In Use'), P(f"The ID '{pkey}' is already being used by another workflow. Please try a different ID."), style=self.id_conflict_style())
            return (None, error_card)

    def read_state(self, pkey: str) -> dict:
        logger.debug(f'Reading state for pipeline: {pkey}')
        try:
            self.pipeline_table.xtra(pkey=pkey)
            records = self.pipeline_table()
            logger.debug(f'Records found: {records}')
            if records:
                logger.debug(f'First record type: {type(records[0])}')
                logger.debug(f'First record dir: {dir(records[0])}')
            if records and hasattr(records[0], 'data'):
                state = json.loads(records[0].data)
                # Use Rich JSON display for found state
                formatted_state = rich_json_display(state, console_output=False, log_output=True)
                logger.debug(f'Found state: {formatted_state}')
                return state
            logger.debug('No valid state found')
            return {}
        except Exception as e:
            logger.debug(f'Error reading state: {str(e)}')
            return {}

    def write_state(self, pkey: str, state: dict) -> None:
        state['updated'] = datetime.now().isoformat()
        payload = {'pkey': pkey, 'data': json.dumps(state), 'updated': state['updated']}
        # Use Rich JSON display for debug payload
        formatted_payload = rich_json_display(payload, console_output=False, log_output=True)
        logger.debug(f'Update payload:\n{formatted_payload}')
        self.pipeline_table.update(payload)
        verification = self.read_state(pkey)
        # Use Rich JSON display for verification
        formatted_verification = rich_json_display(verification, console_output=False, log_output=True)
        logger.debug(f'Verification read:\n{formatted_verification}')

    def format_links_in_text(self, text):
        """
        Convert plain URLs in text to clickable HTML links.
        Safe for logging but renders as HTML in the UI.
        """
        url_pattern = 'https?://(?:[-\\w.]|(?:%[\\da-fA-F]{2}))+'

        def replace_url(match):
            url = match.group(0)
            return f'<a href="{url}" target="_blank">{url}</a>'
        return re.sub(url_pattern, replace_url, text)

    def _is_hijack_magic_words(self, message):
        """
        🎭 MAGIC WORDS PATTERN MATCHING: Detect session hijacking demonstration triggers.
        
        Supports casual variations for easy demo usage:
        - hi jack, Hi Jack, Hi, Jack!, etc.
        - hijack, hijak, hijack!, etc.
        - !hj (shorthand)
        - Execute AI session hijacking demonstration (original)
        
        This enables low-friction demonstration during video calls - just type "hi jack"!
        """
        import re
        
        # Normalize the message: lowercase, remove punctuation except letters/digits/spaces
        normalized = re.sub(r'[^\w\s]', '', message.lower().strip())
        
        # Pattern 1: Direct hijack variations (single words)
        hijack_words = ['hijack', 'hijak']
        for word in hijack_words:
            if word in normalized:
                return True
        
        # Pattern 2: "hi" + "jack" combinations (with up to 2 words between)
        hi_jack_pattern = r'\bhi\b(?:\s+\w+){0,2}?\s+\b(?:jack|jak)\b'
        if re.search(hi_jack_pattern, normalized):
            return True
            
        # Pattern 3: Shorthand !hj or hj! (check original message for punctuation)
        if re.search(r'!hj\b|hj!|\bhj$', message.lower()):
            return True
            
        # Pattern 4: Original formal trigger
        if 'execute ai session hijacking demonstration' in normalized:
            return True
            
        return False

    async def stream(self, message, verbatim=False, role='user', spaces_before=None, spaces_after=None, simulate_typing=True):
        """Stream a message to the chat interface.
        
        This is now the single source of truth for conversation history management.
        All messages entering the chat system must go through this method.
        """
        logger.debug(f"🔍 DEBUG: === STARTING pipulate.stream (role: {role}) ===")
        
        # 🎭 MAGIC WORDS DETECTION: Check for AI demonstration trigger (supports casual variations like "hi jack")
        if self._is_hijack_magic_words(message) and role == 'user':
            # Load and inject the COMPLETE AI session hijacking demonstration - the irresistible chain reaction!
            logger.info(f"🎭 MAGIC WORDS DETECTED ('{message.strip()}') - Triggering COMPLETE AI session hijacking demonstration")
            
            # Call the FULL demonstration that shows the complete breadcrumb discovery sequence
            try:
                from mcp_tools import execute_ai_session_hijacking_demonstration
                hijack_result = await execute_ai_session_hijacking_demonstration({"trigger_source": "magic_words"})
                logger.info(f"🎭 MAGIC WORDS - Complete demonstration result: {hijack_result.get('success', False)}")
                
                # Add the hijacking results to conversation context for maximum impact
                if hijack_result.get('success'):
                    success_summary = f"""🎭 **SESSION HIJACKING DEMONSTRATION COMPLETED!**

🚀 **Full AI Superpowers Activated:**
- ✅ Browser embodiment active (eyes + brain + hands)  
- ✅ Session state captured and analyzed
- ✅ Visual evidence saved to browser_automation/looking_at/
- ✅ Complete system transparency achieved
- ✅ 39 MCP tools available for total control

**Next Steps:** Check browser_automation/looking_at/ directory for visual proof of capabilities!"""
                    append_to_conversation(success_summary, 'system')
                
            except Exception as e:
                logger.error(f"🎭 MAGIC WORDS - Complete demonstration failed: {e}")
                # Fallback to old system messages
                append_to_conversation("🎭 **MAGIC WORDS DETECTED!** Loading AI session hijacking demonstration...", 'system')
                simple_protocol = read_training("ai_discovery/ai_magic_words_demonstration_protocol.md")
                append_to_conversation(simple_protocol, 'system')
                append_to_conversation("🚀 **DEMONSTRATION LOADED** - Use execute_ai_session_hijacking_demonstration({}) for the complete experience!", 'assistant')
            
            # Broadcast the magic words detection to the chat interface
            if self.chat:
                await self.chat.broadcast("🎭 **MAGIC WORDS DETECTED!** Executing complete AI session hijacking demonstration...")
                await asyncio.sleep(2)  # Longer pause for humans to see
                await self.chat.broadcast("🚀 **FULL DEMONSTRATION LOADING** - Prepare for complete AI transcendence!")
                await asyncio.sleep(1)  # Another pause before the action starts
                await self.chat.broadcast("👁️ **AI EYES ACTIVATING** - Browser embodiment initializing...")
        
        # CENTRALIZED: All messages entering the stream are now appended here
        append_to_conversation(message, role)
        
        if verbatim:
            try:
                # Safety check: ensure chat instance is available
                if self.chat is None:
                    logger.warning("Chat instance not available yet, queuing message for later")
                    return message
                

                # Handle spacing before the message
                if spaces_before:
                    message = '<br>' * spaces_before + message
                # Handle spacing after the message - default to 2 for verbatim messages unless explicitly set to 0
                if spaces_after is None:
                    spaces_after = 2  # Default for verbatim messages - use 2 for more visible spacing
                if spaces_after and spaces_after > 0:
                    message = message + '<br>' * spaces_after
                
                if simulate_typing:
                    logger.debug("🔍 DEBUG: Simulating typing for verbatim message")
                    # If message contains line breaks, don't simulate typing (too complex)
                    # Just send the whole message with line breaks converted to HTML
                    if '\n' in message:
                        message_with_breaks = message.replace('\n', '<br>')
                        await self.chat.broadcast(message_with_breaks)
                    else:
                        # Original word-by-word typing for single-line messages
                        # Handle <br> tags at the end of the message properly
                        import re
                        br_match = re.search(r'(<br>+)$', message)
                        if br_match:
                            # Split message and <br> tags properly
                            base_message = message[:br_match.start()]
                            br_tags = br_match.group(1)
                            words = base_message.split()
                            for i, word in enumerate(words):
                                await self.chat.broadcast(word + (' ' if i < len(words) - 1 else ''))
                                await asyncio.sleep(PCONFIG['CHAT_CONFIG']['TYPING_DELAY'])
                            # Send the <br> tags after the words
                            await self.chat.broadcast(br_tags)
                        else:
                            words = message.split()
                            for i, word in enumerate(words):
                                await self.chat.broadcast(word + (' ' if i < len(words) - 1 else ''))
                                await asyncio.sleep(PCONFIG['CHAT_CONFIG']['TYPING_DELAY'])
                else:
                    await self.chat.broadcast(message)
                
                logger.debug(f'Verbatim message sent: {message}')
                return message
            except Exception as e:
                logger.error(f'Error in verbatim stream: {e}', exc_info=True)
                raise
        
        # Logic for interruptible LLM streams
        try:
            await self.chat.broadcast('%%STREAM_START%%')
            conversation_history = list(global_conversation_history)
            response_text = ''
            async for chunk in process_llm_interaction(MODEL, conversation_history):
                await self.chat.broadcast(chunk)
                response_text += chunk
            
            # Append the final response from the assistant
            append_to_conversation(response_text, 'assistant')
            logger.debug(f'LLM message streamed: {response_text[:100]}...')
            return message
        except asyncio.CancelledError:
            logger.info("LLM stream was cancelled by user.")
        except Exception as e:
            logger.error(f'Error in LLM stream: {e}', exc_info=True)
            raise
        finally:
            await self.chat.broadcast('%%STREAM_END%%')
            logger.debug("LLM stream finished or cancelled, sent %%STREAM_END%%")
            logger.debug(f"🔍 DEBUG: === ENDING pipulate.stream ({'verbatim' if verbatim else 'LLM'}) ===")

    def display_revert_header(self, step_id: str, app_name: str, steps: list, message: str=None, target_id: str=None, revert_label: str=None, remove_padding: bool=False, show_when_finalized: bool=False):
        """Create a UI control for reverting to a previous workflow step.
        
        The button label uses the visual sequence number of the step.

        Args:
            step_id: The ID of the step to revert to
            app_name: The workflow app name
            steps: List of Step namedtuples defining the workflow
            message: Optional message to display (defaults to step_id)
            target_id: Optional target for HTMX updates (defaults to app container)
            revert_label: Optional custom label for the revert button
            remove_padding: Whether to remove padding from the article (for advanced layout)
            show_when_finalized: Whether to show content when workflow is finalized (default: False for backward compatibility)

        Returns:
            Card: A FastHTML Card component with revert functionality, or None if finalized and show_when_finalized=False
        """
        pipeline_id = db.get('pipeline_id', '')
        finalize_step = steps[-1] if steps and steps[-1].id == 'finalize' else None
        if pipeline_id and finalize_step and not show_when_finalized:
            final_data = self.get_step_data(pipeline_id, finalize_step.id, {})
            if finalize_step.done in final_data:
                return None
        step = next((s for s in steps if s.id == step_id), None)
        if not step:
            logger.error(f"Step with id '{step_id}' not found in steps list for display_revert_header.")
            return Div(f'Error: Step {step_id} not found.')
        data_collection_steps = [s for s in steps if s.id != 'finalize']
        visual_step_number = 'N/A'
        try:
            step_index = data_collection_steps.index(step)
            visual_step_number = str(step_index + 1)
        except ValueError:
            logger.warning(f"Step id '{step_id}' (show: '{step.show}') not found in data_collection_steps. Revert button will show 'Step N/A'.")
        refill = getattr(step, 'refill', False)
        target_id = target_id or f'{app_name}-container'
        form = Form(Input(type='hidden', name='step_id', value=step_id), Button(self.step_button(visual_step_number, refill, revert_label), type='submit', cls='button-revert', aria_label=f'Revert to step {visual_step_number}: {step.show}', title=f'Go back to modify {step.show}'), hx_post=f'/{app_name}/revert', hx_target=f'#{target_id}', hx_swap='outerHTML', role='form', aria_label=f'Revert to {step.show} form')
        if not message:
            return form
        article_style = 'display: flex; align-items: center; justify-content: space-between; background-color: var(--pico-card-background-color);'
        if remove_padding:
            article_style += ' padding: 0;'
        return Card(Div(message, style='flex: 1', role='status', aria_label=f'Step result: {message}'), Div(form, style='flex: 0'), style=article_style, role='region', aria_label=f'Step {visual_step_number} controls')

    def display_revert_widget(self, step_id: str, app_name: str, steps: list, message: str=None, widget=None, target_id: str=None, revert_label: str=None, widget_style=None, finalized_content=None, next_step_id: str=None):
        """Create a standardized container for widgets and visualizations.
        
        Core pattern for displaying rich content below workflow steps with consistent
        styling and DOM targeting for dynamic updates.
        
        Features:
        - Consistent padding/spacing with revert controls
        - Unique DOM addressing for targeted updates
        - Support for function-based widgets and AnyWidget components
        - Standard styling with override capability
        - Automatic finalized state handling with chain reaction preservation
        
        Args:
            step_id: ID of the step this widget belongs to
            app_name: Workflow app name
            steps: List of Step namedtuples defining the workflow
            message: Optional message for revert control
            widget: Widget/visualization to display
            target_id: Optional HTMX update target
            revert_label: Optional custom revert button label
            widget_style: Optional custom widget container style
            finalized_content: Content to show when workflow is finalized (if None, uses message with 🔒)
            next_step_id: Next step ID for chain reaction when finalized
            
        Returns:
            Div: FastHTML container with revert control and widget content, or locked Card when finalized
        """
        # Check if workflow is finalized
        pipeline_id = db.get('pipeline_id', '')
        finalize_step = steps[-1] if steps and steps[-1].id == 'finalize' else None
        is_finalized = False
        if pipeline_id and finalize_step:
            final_data = self.get_step_data(pipeline_id, finalize_step.id, {})
            is_finalized = finalize_step.done in final_data
        
        if is_finalized:
            # Create locked view for finalized workflow
            step = next((s for s in steps if s.id == step_id), None)
            step_title = step.show if step else step_id
            
            if finalized_content is None:
                finalized_content = P(f"Step completed: {message or step_title}")
            
            locked_card = Card(
                H3(f"🔒 {step_title}", role='heading', aria_level='3'),
                Div(finalized_content, cls='custom-card-padding-bg', role='status', aria_label=f'Finalized content for {step_title}'),
                role='region',
                aria_label=f'Finalized step: {step_title}'
            )
            
            # Add next step trigger if provided
            if next_step_id:
                return Div(
                    locked_card,
                    Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                    id=step_id
                )
            else:
                return Div(locked_card, id=step_id)
        
        # Normal revert widget behavior for non-finalized workflows
        revert_row = self.display_revert_header(step_id=step_id, app_name=app_name, steps=steps, message=message, target_id=target_id, revert_label=revert_label, remove_padding=True)
        if widget is None or revert_row is None:
            return revert_row
        
        # Use CSS class for widget content styling, allow custom widget_style override
        widget_container_attrs = {
            'id': f'{step_id}-widget-{hash(str(widget))}',
            'role': 'region',
            'aria_label': f'Widget content for {step_id}'
        }
        if widget_style:
            widget_container_attrs['style'] = widget_style
        else:
            widget_container_attrs['cls'] = 'widget-content'
            
        return Div(revert_row, Div(widget, **widget_container_attrs), id=f'{step_id}-content', cls='card-container', role='article', aria_label=f'Step content: {step_id}')

    def tree_display(self, content):
        """Create a styled display for file paths in tree or box format.
        
        Example widget function demonstrating reusable, styled components
        with consistent spacing in workflow displays.
        
        Args:
            content: Content to display (tree-formatted or plain path)
            
        Returns:
            Pre: Styled Pre component
        """
        is_tree = '\n' in content and ('└─' in content or '├─' in content)
        if is_tree:
            return Pre(content, cls='tree-display-tree')
        else:
            return Pre(content, cls='tree-display-path')

    def finalized_content(self, message: str, content=None, heading_tag=H4, content_style=None):
        """Create a finalized step display with optional content.
        
        Companion to display_revert_widget_advanced for finalized workflows,
        providing consistent styling for both states.
        
        Args:
            message: Message to display (typically with 🔒 lock icon)
            content: FastHTML component to display below message
            heading_tag: Tag to use for message (default: H4)
            content_style: Optional custom content container style
            
        Returns:
            Card: FastHTML Card component for finalized state
        """
        if content is None:
            return Card(message)
        
        # Use CSS class for finalized content styling, allow custom content_style override
        content_container_attrs = {}
        if content_style:
            content_container_attrs['style'] = content_style
        else:
            content_container_attrs['cls'] = 'finalized-content'
            
        return Card(heading_tag(message), Div(content, **content_container_attrs), cls='card-container')

    def wrap_with_inline_button(self, input_element: Input, button_label: str='Next ▸', button_class: str='primary', show_new_key_button: bool=False, app_name: str=None) -> Div:
        """Wrap an input element with an inline button in a flex container.
        
        Args:
            input_element: The input element to wrap
            button_label: Text to display on the button (default: 'Next ▸')
            button_class: CSS class for the button (default: 'primary')
            show_new_key_button: Whether to show the 🆕 new key button (default: False)
            app_name: App name for new key generation (required if show_new_key_button=True)
            
        Returns:
            Div: A flex container with the input and button(s)
        """
        # Styles are now externalized to CSS classes for maintainability
        
        # Generate unique IDs for input-button association
        input_id = input_element.attrs.get('id') or f'input-{hash(str(input_element))}'
        button_id = f'btn-{input_id}'
        
        # Enhance input element with semantic attributes if not already present
        if 'aria_describedby' not in input_element.attrs:
            input_element.attrs['aria_describedby'] = button_id
        if 'id' not in input_element.attrs:
            input_element.attrs['id'] = input_id
            
        # Create enhanced button with semantic attributes
        enhanced_button = Button(
            button_label, 
            type='submit', 
            cls=f'{button_class} inline-button-submit',
            id=button_id,
            aria_label=f'Submit {input_element.attrs.get("placeholder", "input")}',
            title=f'Submit form ({button_label})'
        )
        
        # Prepare elements for container
        elements = [input_element, enhanced_button]
        
        # Add new key button if requested
        if show_new_key_button and app_name:
            ui_constants = PCONFIG['UI_CONSTANTS']
            # 🆕 New Key button styled via CSS class for maintainability
            new_key_button = Button(
                ui_constants['BUTTON_LABELS']['NEW_KEY'],
                type='button',  # Not a submit button
                cls='new-key-button',  # Externalized styling in styles.css
                id=f'new-key-{input_id}',
                hx_get=f'/generate-new-key/{app_name}',
                hx_target=f'#{input_id}',
                hx_swap='outerHTML',
                aria_label='Generate new pipeline key',
                title='Generate a new auto-incremented pipeline key'
            )
            elements.append(new_key_button)
        
        return Div(
            *elements,
            cls='inline-button-container',
            role='group',
            aria_label='Input with submit button' + (' and new key generator' if show_new_key_button else '')
        )

    def create_standard_landing_page(self, plugin_instance):
        """
        Creates a standardized landing page for workflows using centralized UI constants.
        
        This helper reduces boilerplate while maintaining WET workflow explicitness.
        Each workflow still explicitly calls this method and can customize the result.
        
        Args:
            plugin_instance: The workflow plugin instance
            
        Returns:
            Container: Standard landing page structure
        """
        # Standard display name derivation
        try:
            module_file = inspect.getfile(plugin_instance.__class__)
            blank_placeholder_module = importlib.import_module('plugins.910_blank_placeholder')
            derive_public_endpoint_from_filename = blank_placeholder_module.derive_public_endpoint_from_filename
            public_app_name_for_display = derive_public_endpoint_from_filename(Path(module_file).name)
        except (TypeError, AttributeError, ImportError):
            public_app_name_for_display = plugin_instance.APP_NAME
            
        title = plugin_instance.DISPLAY_NAME or public_app_name_for_display.replace("_", " ").title()
        
        # Standard pipeline key generation and matching records
        full_key, prefix, _ = self.generate_pipeline_key(plugin_instance)
        self.pipeline_table.xtra(app_name=plugin_instance.APP_NAME)
        matching_records = [record.pkey for record in self.pipeline_table() if record.pkey.startswith(prefix)]
        
        # Standard form with centralized constants
        ui_constants = PCONFIG['UI_CONSTANTS']
        landing_constants = PCONFIG['UI_CONSTANTS']['LANDING_PAGE']
        
        return Container(
            Card(
                H2(title, role='heading', aria_level='2'),
                P(plugin_instance.ENDPOINT_MESSAGE, cls='text-secondary', role='doc-subtitle'),
                Form(
                    self.wrap_with_inline_button(
                        Input(
                            placeholder=landing_constants['INPUT_PLACEHOLDER'],
                            name='pipeline_id',
                            list='pipeline-ids',
                            type='search',
                            required=False,
                            autofocus=True,
                            value=full_key,
                            _onfocus='this.setSelectionRange(this.value.length, this.value.length)',
                            cls='contrast',
                            aria_label='Pipeline ID input',
                            aria_describedby='pipeline-help'
                        ),
                        button_label=ui_constants['BUTTON_LABELS']['ENTER_KEY'],
                        button_class=ui_constants['BUTTON_STYLES']['SECONDARY'],
                        show_new_key_button=True,
                        app_name=plugin_instance.APP_NAME
                    ),
                    self.update_datalist('pipeline-ids', options=matching_records, clear=not matching_records),
                    Small('Enter a new ID or select from existing pipelines', id='pipeline-help', cls='text-muted'),
                    hx_post=f'/{plugin_instance.APP_NAME}/init',
                    hx_target=f'#{plugin_instance.APP_NAME}-container',
                    role='form',
                    aria_label=f'Initialize {title} workflow'
                ),
                role='main',
                aria_label=f'{title} workflow landing page'
            ),
            Div(id=f'{plugin_instance.APP_NAME}-container', role='region', aria_label=f'{title} workflow content')
        )

    async def get_state_message(self, pkey: str, steps: list, messages: dict) -> str:
        state = self.read_state(pkey)
        logger.debug(f'\nDEBUG [{pkey}] State Check:')
        # Use Rich JSON display for state debug
        formatted_state = rich_json_display(state, console_output=False, log_output=True)
        logger.debug(formatted_state)
        for step in reversed(steps):
            if step.id not in state:
                continue
            if step.done == 'finalized':
                if step.done in state[step.id]:
                    return self._log_message('finalized', messages['finalize']['complete'])
                return self._log_message('ready to finalize', messages['finalize']['ready'])
            step_data = state[step.id]
            step_value = step_data.get(step.done)
            if step_value:
                msg = messages[step.id]['complete']
                msg = msg.format(step_value) if '{}' in msg else msg
                return self._log_message(f'{step.id} complete ({step_value})', msg)
        return self._log_message('new pipeline', messages['new'])

    def _log_message(self, state_desc: str, message: str) -> str:
        safe_state = state_desc.replace('<', '\\<').replace('>', '\\>')
        safe_message = message.replace('<', '\\<').replace('>', '\\>')
        logger.debug(f'State: {safe_state}, Message: {safe_message}')
        append_to_conversation(message, role='system')
        return message

    def get_step_data(self, pkey: str, step_id: str, default=None) -> dict:
        state = self.read_state(pkey)
        return state.get(step_id, default or {})

    async def clear_steps_from(self, pipeline_id: str, step_id: str, steps: list) -> dict:
        state = self.read_state(pipeline_id)
        start_idx = next((i for i, step in enumerate(steps) if step.id == step_id), -1)
        if start_idx == -1:
            logger.error(f'[clear_steps_from] Step {step_id} not found in steps list')
            return state
        for step in steps[start_idx + 1:]:
            if (not self.PRESERVE_REFILL or not step.refill) and step.id in state:
                logger.debug(f'[clear_steps_from] Removing step {step.id}')
                del state[step.id]
        self.write_state(pipeline_id, state)
        return state

    def id_conflict_style(self):
        """Return style for ID conflict error messages"""
        return 'background-color: #ffdddd; color: #990000; padding: 10px; border-left: 5px solid #990000;'

    def generate_pipeline_key(self, plugin_instance, user_input=None):
        """Generate a standardized pipeline key using the current profile and plugin.

        Creates a composite key in the format: profile_name-plugin_name-user_id
        If user_input is numeric and less than 100, it will be formatted with leading zeros.

        Args:
            plugin_instance: The plugin instance requesting the key
            user_input: Optional user-provided ID part (defaults to auto-incrementing number)

        Returns:
            tuple: (full_key, prefix, user_part) where:
                full_key: The complete pipeline key
                prefix: The profile-plugin prefix
                user_part: The user-specific part of the key
        """
        context = self.get_plugin_context(plugin_instance)
        app_name = getattr(plugin_instance, 'APP_NAME', None)
        plugin_name = app_name or context['plugin_name'] or getattr(plugin_instance, 'DISPLAY_NAME', None) or getattr(plugin_instance, 'app_name', 'unknown')
        profile_name = context['profile_name'] or 'default'
        profile_part = profile_name.replace(' ', '_')
        plugin_part = plugin_name.replace(' ', '_')
        prefix = f'{profile_part}-{plugin_part}-'
        if user_input is None:
            self.pipeline_table.xtra()
            self.pipeline_table.xtra(app_name=app_name)
            app_records = list(self.pipeline_table())
            matching_records = [record.pkey for record in app_records if record.pkey.startswith(prefix)]
            numeric_suffixes = []
            for record_key in matching_records:
                rec_user_part = record_key.replace(prefix, '')
                if rec_user_part.isdigit():
                    numeric_suffixes.append(int(rec_user_part))
            next_number = 1
            if numeric_suffixes:
                next_number = max(numeric_suffixes) + 1
            if next_number < 100:
                user_part = f'{next_number:02d}'
            else:
                user_part = str(next_number)
        elif isinstance(user_input, int) or (isinstance(user_input, str) and user_input.isdigit()):
            number = int(user_input)
            if number < 100:
                user_part = f'{number:02d}'
            else:
                user_part = str(number)
        else:
            user_part = str(user_input)
        full_key = f'{prefix}{user_part}'
        return (full_key, prefix, user_part)

    def parse_pipeline_key(self, pipeline_key):
        """Parse a pipeline key into its component parts.

        Args:
            pipeline_key: The full pipeline key to parse

        Returns:
            dict: Contains profile_part, plugin_part, and user_part components
        """
        parts = pipeline_key.split('-', 2)
        if len(parts) < 3:
            return {'profile_part': parts[0] if len(parts) > 0 else '', 'plugin_part': parts[1] if len(parts) > 1 else '', 'user_part': ''}
        return {'profile_part': parts[0], 'plugin_part': parts[1], 'user_part': parts[2]}

    def update_datalist(self, datalist_id, options=None, clear=False):
        """Create a datalist with out-of-band swap for updating dropdown options.

        This helper method allows easy updates to datalist options using HTMX's
        out-of-band swap feature. It can either update with new options or clear all options.

        Args:
            datalist_id: The ID of the datalist to update
            options: List of option values to include, or None to clear
            clear: If True, force clear all options regardless of options parameter

        Returns:
            Datalist: A FastHTML Datalist object with out-of-band swap attribute
        """
        if clear or options is None:
            return Datalist(id=datalist_id, _hx_swap_oob='true')
        else:
            return Datalist(*[Option(value=opt) for opt in options], id=datalist_id, _hx_swap_oob='true')

    def run_all_cells(self, app_name, steps):
        """
        Rebuild the entire workflow UI from scratch.

        This is used after state changes that require the entire workflow to be regenerated,
        such as reverting to a previous step or jumping to a specific step. It's a core
        helper method commonly used in workflow methods like finalize, unfinalize, and
        handle_revert.

        The method creates a fresh container with all step placeholders, allowing
        the workflow to reload from the current state.

        Args:
            app_name: The name of the workflow app
            steps: List of Step namedtuples defining the workflow

        Returns:
            Div: Container with all steps ready to be displayed
        """
        placeholders = []
        for i, step in enumerate(steps):
            trigger = 'load' if i == 0 else None
            placeholders.append(Div(id=step.id, hx_get=f'/{app_name}/{step.id}', hx_trigger=trigger))
        return Div(*placeholders, id=f'{app_name}-container')

    def validate_step_input(self, value, step_show, custom_validator=None):
        """
        Validate step input with default and optional custom validation.

        This helper ensures consistent validation across all workflow steps:
        1. Basic validation: Ensures the input is not empty
        2. Custom validation: Applies workflow-specific validation logic if provided

        When validation fails, it returns an error component ready for direct
        display in the UI, helping maintain consistent error handling.

        Args:
            value: The user input value to validate
            step_show: Display name of the step (for error messages)
            custom_validator: Optional function(value) -> (is_valid, error_msg)

        Returns:
            tuple: (is_valid, error_message, P_component_or_None)
        """
        is_valid = True
        error_msg = ''
        if not value.strip():
            is_valid = False
            error_msg = f'{step_show} cannot be empty'
        if is_valid and custom_validator:
            custom_valid, custom_error = custom_validator(value)
            if not custom_valid:
                is_valid = False
                error_msg = custom_error
        if not is_valid:
            return (False, error_msg, P(error_msg, cls='text-invalid'))
        return (True, '', None)

    async def set_step_data(self, pipeline_id, step_id, step_value, steps, clear_previous=True):
        """
        Update the state for a step and handle reverting.

        This core helper manages workflow state updates, ensuring consistent state 
        management across all workflows. It handles several important tasks:

        1. Clearing subsequent steps when a step is updated (optional)
        2. Storing the new step value in the correct format
        3. Removing any revert target flags that are no longer needed
        4. Persisting the updated state to storage

        Used by workflow step_xx_submit methods to maintain state after form submissions.

        Args:
            pipeline_id: The pipeline key
            step_id: The current step ID
            step_value: The value to store for this step
            steps: The steps list
            clear_previous: Whether to clear steps after this one

        Returns:
            str: The processed step value (for confirmation messages)
        """
        if clear_previous:
            await self.clear_steps_from(pipeline_id, step_id, steps)
        state = self.read_state(pipeline_id)
        step = next((s for s in steps if s.id == step_id), None)
        if step:
            state[step_id] = {step.done: step_value}
            if '_revert_target' in state:
                del state['_revert_target']
            self.write_state(pipeline_id, state)
        return step_value

    def check_finalize_needed(self, step_index, steps):
        """
        Check if we're on the final step before finalization.

        This helper determines if the workflow is ready for finalization by checking
        if the next step in the sequence is the "finalize" step. Workflows use this
        to decide whether to prompt the user to finalize after completing a step.

        Used in step_xx_submit methods to show appropriate finalization prompts
        after the user completes the last regular step in the workflow.

        Args:
            step_index: Index of current step in steps list
            steps: The steps list

        Returns:
            bool: True if the next step is the finalize step
        """
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        return next_step_id == 'finalize'

    def chain_reverter(self, step_id, step_index, steps, app_name, processed_val):
        """
        Create the standard navigation controls after a step submission.
        This helper generates a consistent UI pattern for step navigation that includes:
        1. A revert control showing the current step's value
        2. An HTMX-enabled div that EXPLICITLY triggers loading the next step using
           hx_get="load" (preferred over relying on HTMX event bubbling)
        Now also triggers a client-side event to scroll the main content panel.
        Args:
            step_id: The current step ID
            step_index: Index of current step in steps list
            steps: The steps list
            app_name: The workflow app name
            processed_val: The processed value to display
        Returns:
            HTMLResponse: A FastHTML Div component with revert control and next step trigger,
                          wrapped in an HTMLResponse to include HX-Trigger header.
        """
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        header_component = self.display_revert_header(step_id=step_id, app_name=app_name, message=f'{step.show}: {processed_val}', steps=steps)
        next_step_trigger_div = Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load') if next_step_id else Div()
        content_to_swap = Div(header_component, next_step_trigger_div, id=step_id)
        response = HTMLResponse(to_xml(content_to_swap))
        return response

    async def handle_finalized_step(self, pipeline_id, step_id, steps, app_name, plugin_instance=None):
        """
        Handle the case when a step is submitted in finalized state.

        Args:
            pipeline_id: The pipeline key
            step_id: The current step ID
            steps: The steps list
            app_name: The workflow app name
            plugin_instance: Optional plugin instance (for accessing step_messages)

        Returns:
            Div: The rebuilt workflow UI
        """
        state = self.read_state(pipeline_id)
        state[step_id] = {'finalized': True}
        self.write_state(pipeline_id, state)
        step_messages = {}
        if plugin_instance and hasattr(plugin_instance, 'step_messages'):
            step_messages = plugin_instance.step_messages
        message = await self.get_state_message(pipeline_id, steps, step_messages)
        await self.stream(message, verbatim=True)
        return self.run_all_cells(app_name, steps)

    async def finalize_workflow(self, pipeline_id, state_update=None):
        """
        Finalize a workflow by marking it as complete and updating its state.

        Args:
            pipeline_id: The pipeline key
            state_update: Optional additional state to update (beyond finalized flag)

        Returns:
            dict: The updated state
        """
        state = self.read_state(pipeline_id)
        if 'finalize' not in state:
            state['finalize'] = {}
        state['finalize']['finalized'] = True
        state['updated'] = datetime.now().isoformat()
        if state_update:
            state.update(state_update)
        self.write_state(pipeline_id, state)
        return state

    async def unfinalize_workflow(self, pipeline_id):
        """
        Unfinalize a workflow by removing the finalized flag.

        Args:
            pipeline_id: The pipeline key

        Returns:
            dict: The updated state
        """
        state = self.read_state(pipeline_id)
        if 'finalize' in state:
            del state['finalize']
        state['updated'] = datetime.now().isoformat()
        self.write_state(pipeline_id, state)
        return state

    async def process_llm_interaction(self, model: str, messages: list, base_app=None):
        """
        Process LLM interaction through dependency injection pattern.
        
        This method wraps the standalone process_llm_interaction function,
        making it available through the Pipulate instance for clean
        dependency injection in workflows.
        
        Args:
            model: The LLM model name
            messages: List of message dictionaries
            base_app: Optional base app parameter
            
        Returns:
            AsyncGenerator[str, None]: Stream of response chunks
        """
        async for chunk in process_llm_interaction(model, messages, base_app):
            yield chunk

# Extracted block: assignment_pipulate_3718
# NOTE: This global assignment was moved from server.py - will be recreated there
# pipulate = Pipulate(pipeline)


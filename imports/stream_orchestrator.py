import asyncio
import json
import re
from loguru import logger
# NOTE: No top-level imports from 'tools' or 'server' to prevent circular dependencies.

async def stream_orchestrator(pipulate_instance, chat_instance, message, **kwargs):
    """
    The core logic for handling user messages, detecting tool calls, and deciding whether to invoke the LLM.
    Externalized from server.py to make the system more modular and safer for AI edits.
    """
    # JIT Import: Import tool registries inside the function to avoid circular dependencies at startup.
    from tools import get_all_tools, ALIAS_REGISTRY
    MCP_TOOL_REGISTRY = get_all_tools()

    # Get necessary functions/variables from the pipulate instance
    append_to_conversation = pipulate_instance.append_to_conversation_from_instance
    PCONFIG = pipulate_instance.get_config()
    role = kwargs.get('role', 'user')

    logger.debug(f"ORCHESTRATOR: Intercepted message (role: {role})")

    if role == 'user':
        append_to_conversation(message, 'user')
        simple_command_match = re.match(r'^\s*\[([^\]]+)\]\s*$', message)
        if simple_command_match:
            full_command_string = simple_command_match.group(1).strip()
            command_parts = full_command_string.split(maxsplit=1)
            command_alias = command_parts[0]
            command_args_str = command_parts[1] if len(command_parts) > 1 else ""
            logger.info(f"ORCHESTRATOR: Simple command detected: [{full_command_string}]")

            tool_name = ALIAS_REGISTRY.get(command_alias)
            if tool_name and tool_name in MCP_TOOL_REGISTRY:
                params = {}
                if command_args_str:
                    if tool_name == 'system_list_directory':
                        params['path'] = command_args_str
                    elif tool_name == 'execute_shell_command':
                        params['command'] = command_args_str
                    else:
                        params['args'] = command_args_str
                
                tool_handler = MCP_TOOL_REGISTRY[tool_name]
                tool_output = await tool_handler(params)
                
                formatted_output = "```\n"
                if tool_output.get('success'):
                    if 'stdout' in tool_output:
                        formatted_output += tool_output.get('stdout') or "[No output]"
                    elif 'directories' in tool_output:
                        dirs = '\n'.join([f"📁 {d}" for d in tool_output.get('directories', [])])
                        files = '\n'.join([f"📄 {f}" for f in tool_output.get('files', [])])
                        formatted_output += f"Directory: {tool_output.get('path', '.')}\n\n{dirs}\n{files}"
                    else:
                        formatted_output += json.dumps(tool_output, indent=2)
                else:
                    formatted_output += f"Error: {tool_output.get('error', 'Unknown error')}"
                formatted_output += "\n```"
                
                await pipulate_instance.stream(formatted_output, role='tool', verbatim=True)
                return

    if kwargs.get('verbatim'):
        append_to_conversation(message, role)
        try:
            words = message.replace('\n', '<br>').split()
            for i, word in enumerate(words):
                await chat_instance.broadcast(word + (' ' if i < len(words) - 1 else ''))
                await asyncio.sleep(PCONFIG['CHAT_CONFIG']['TYPING_DELAY'])
            return message
        except Exception as e:
            logger.error(f'ORCHESTRATOR: Error in verbatim stream: {e}', exc_info=True)
            raise
            
    # If it was a regular user message (not a handled command), proceed to the LLM
    await pipulate_instance._handle_llm_stream()
    return message
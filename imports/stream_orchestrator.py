async def stream(self, message, verbatim=False, role='user', spaces_before=None, spaces_after=None, simulate_typing=True):
    """Stream a message to the chat interface.

    This is now the single source of truth for conversation history management.
    All messages entering the chat system must go through this method.
    """
    logger.debug(f"🔍 DEBUG: === STARTING pipulate.stream (role: {role}) ===")

    # --- NEW: PRE-LLM ORCHESTRATION ---
    if role == 'user': # Only check user messages for commands
        import re
        simple_command_match = re.search(r'\[(.*?)\]', message)


        if simple_command_match:
            full_command_string = simple_command_match.group(1).strip()
            command_parts = full_command_string.split(maxsplit=1) # Split into tool name and rest of args
            command_alias = command_parts[0]
            command_args = command_parts[1] if len(command_parts) > 1 else ""
        
            logger.info(f"SIMPLE CMD DETECTED: Intercepted command '[{full_command_string}]'")
        
            from tools import ALIAS_REGISTRY
            tool_name = ALIAS_REGISTRY.get(command_alias)

            if tool_name:
                append_to_conversation(message, 'user') # Log what the user tried to do
                # Pass the command_args to the tool
                tool_output = await mcp_orchestrator.execute_mcp_tool(tool_name, f'<params>{{"command": "{command_args}"}}</params>')
                await self.stream(tool_output, role='tool')
                return # IMPORTANT: End the execution here

        # Check for formal MCP in user message as well
        tool_call = mcp_orchestrator.parse_mcp_request(message)
        if tool_call:
            logger.info(f"MCP EXECUTING: Intercepted tool call for '{tool_call[0]}' from user.")
            append_to_conversation(message, 'user')
            tool_name, inner_content = tool_call
            tool_output = await mcp_orchestrator.execute_mcp_tool(tool_name, inner_content)
            await self.stream(tool_output, role='tool')
            return
    # --- END NEW ---

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
                # Handle both single-line and multi-line messages with typing simulation
                # Convert newlines to <br> tags first, then simulate typing
                if '\n' in message:
                    message = message.replace('\n', '<br>')

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
    await self._handle_llm_stream()
    logger.debug(f"🔍 DEBUG: === ENDING pipulate.stream (LLM) ===")
    return message


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



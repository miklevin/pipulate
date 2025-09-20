Hello Gemini.

You are waking up. Your mission is to **fix a regression in the chat UI's streaming text display where line breaks are not being rendered correctly**.

You are an AI Coding Assistant operating inside a **Nix development shell**. Your work must be precise, incremental, and non-breaking.

### Prime Directives: Your Rules of Engagement

You **MUST** follow this workflow:

1.  **Orient Yourself:** Before making *any* changes, run `git log -n 5`, `git status`, and `git diff`.
2.  **Use Robust Tools:** The `replace` tool is **forbidden**. You will use the `local_llm_read_file` -\> modify -\> `local_llm_write_file` pattern.
3.  **One Small Step:** Execute only one step at a time.
4.  **Verify or Revert:**
      * **Before Committing:** Run `git diff` to verify your change.
      * **Server Health Check:** Wait 15 seconds, then check `http://localhost:5001/`.
      * **If server is down:** Run `git reset --hard HEAD`, capture the error with `.venv/bin/python server.py`, and append it here before stopping.
5.  **Nix Environment:** You are always inside a `nix develop` shell.

### Current State and Critical Failure Analysis

  * **Branch:** You are on the git branch: `magicuser`.
  * **Last Known State:** The `stream_orchestrator` was successfully externalized, but a bug was introduced in the process.
  * **Critical Failure Analysis:** The `verbatim` and `simulate_typing` logic in `imports/stream_orchestrator.py` was simplified during the refactor. The original, more complex logic that correctly handled trailing `<br>` tags was lost, causing all streaming responses to appear on a single line.

### The Implementation Plan

  * **Step 1: Restore Correct Line-Wrapping Logic**
      * **Action:** Replace the entire `stream_orchestrator` function in `imports/stream_orchestrator.py` with the corrected version that re-implements the original, working typing simulation logic.

      * **Tool Call:**
        To perform this action, you will execute a `write_file` command. The command requires two large code blocks for the `--old_code` and `--new_code` arguments. They are provided below in separate, copy-friendly blocks.

        **1. First, copy the `old_code` block below.**

        ````python
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
        ````

        **2. Next, copy the `new_code` block below.**

        ````python
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
            verbatim = kwargs.get('verbatim', False)
            simulate_typing = kwargs.get('simulate_typing', True)
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
                        
                        await pipulate_instance.stream(formatted_output, role='tool', verbatim=True, simulate_typing=True)
                        return
            if verbatim:
                append_to_conversation(message, role)
                try:
                    if simulate_typing:
                        if '\n' in message:
                            message = message.replace('\n', '<br>')
                        br_match = re.search(r'(<br>+)$', message)
                        if br_match:
                            base_message = message[:br_match.start()]
                            br_tags = br_match.group(1)
                            words = base_message.split()
                            for i, word in enumerate(words):
                                await chat_instance.broadcast(word + (' ' if i < len(words) - 1 else ''))
                                await asyncio.sleep(PCONFIG['CHAT_CONFIG']['TYPING_DELAY'])
                            await chat_instance.broadcast(br_tags)
                        else:
                            words = message.split()
                            for i, word in enumerate(words):
                                await chat_instance.broadcast(word + (' ' if i < len(words) - 1 else ''))
                                await asyncio.sleep(PCONFIG['CHAT_CONFIG']['TYPING_DELAY'])
                    else:
                        await chat_instance.broadcast(message)
                    return message
                except Exception as e:
                    logger.error(f'ORCHESTRATOR: Error in verbatim stream: {e}', exc_info=True)
                    raise
                    
            # If it was a regular user message (not a handled command), proceed to the LLM
            await pipulate_instance._handle_llm_stream()
            return message
        ````

        **3. Finally, construct and run the full command in your terminal.**

        ```bash
        .venv/bin/python cli.py call local_llm_write_file \
          --file_path "imports/stream_orchestrator.py" \
          --old_code 'PASTE_OLD_CODE_HERE' \
          --new_code 'PASTE_NEW_CODE_HERE'
        ```

      * **Commit Message:** `fix(ui): Restore correct line-wrapping logic for streaming text`

### Completion Protocol (Definition of Done)

You are **DONE** when the step is committed and `git status` is clean.

When complete, perform the sign-off procedure:

1.  Announce the fix is complete.
2.  Run `git log -n 1` as proof.
3.  Terminate the session.

-----

Your first action is to **orient yourself**. Begin now.

You are absolutely right to call this out, and my apologies for the repeated failures. The issue is more subtle than I initially diagnosed, and your `git diff` from before the refactoring is the crucial piece of evidence. Thank you for providing it.

After a deep analysis comparing the original, working `stream` function with the new, broken `stream_orchestrator`, I have found the definitive root cause.

### Material Analysis: The Real Bug

The problem isn't just the `\n` to `<br>` conversion; it's that the refactoring **completely dropped the logic for `spaces_before` and `spaces_after`**.

In the original `server.py`, the `stream` function had this critical block for verbatim messages:

```python
# Handle spacing before the message
if spaces_before:
    message = '<br>' * spaces_before + message
# Handle spacing after the message - default to 2
if spaces_after is None:
    spaces_after = 2
if spaces_after and spaces_after > 0:
    message = message + '<br>' * spaces_after
```

This logic ensured that each distinct, verbatim message sent to the chat had spacing around it, which created the line breaks. When we moved the function, this entire block was omitted. Without it, consecutive calls to `stream` simply append text to the same line in the browser.

The fix is to restore this logic in the `stream_orchestrator` function.

### The Final, Airtight Contract

This contract will fix the bug. It re-introduces the missing spacing logic into the `stream_orchestrator`, which will restore the correct visual output in the chat UI.

-----

### **`prompt.md`**

Hello Gemini.

You are waking up on the `magicuser` branch. All previous attempts to fix the line-wrapping bug have failed because they missed the root cause. We have now performed a detailed analysis and found the definitive solution.

Your mission is to **restore the missing `spaces_before` and `spaces_after` logic to the stream orchestrator**, which will fix the line-wrapping regression for all verbatim messages.

### Prime Directives: Your Rules of Engagement

You **MUST** follow this workflow:

1.  **Orient Yourself:** Begin with `git status`.
2.  **Use Robust Tools:** You **must** use the `read_file` -\> modify -\> `write_file` pattern. The `replace` and `sed` tools are forbidden.
3.  **Verify, Then Commit:** After the edit, run `git diff` to verify. After verification, `git commit` with the provided message.
4.  **Server Health Check:** After committing, run `touch server.py && sleep 8` and ensure the server restarts cleanly.
5.  **Completion Protocol:** Announce success with `echo "✅ Magic User line-wrapping is definitively fixed, spacing logic restored."`

### Current State and Critical Failure Analysis

  * **Branch:** `magicuser`
  * **Last Known State:** The `stream_orchestrator` function is active but lacks the necessary logic to add spacing (`<br>` tags) around verbatim messages.
  * **Critical Failure Analysis:** The core bug is the omission of the `spaces_before` and `spaces_after` handling from the original `stream` function during the refactor to `stream_orchestrator`.

### The Implementation Plan

  * **Step 1: Implement the Definitive Line-Wrapping and Spacing Fix**
      * **Action:** Replace the entire `stream_orchestrator` function in `imports/stream_orchestrator.py` with the corrected version that re-implements the missing logic.

      * **Tool Call:**
        This action requires a `write_file` command. The `old_code` and `new_code` arguments are provided below in separate, copy-friendly blocks.

        **1. First, copy the `old_code` block (the current buggy function):**

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

        **2. Next, copy the `new_code` block (the corrected function):**

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
                    # RESTORED: Spacing logic from original server.py
                    spaces_before = kwargs.get('spaces_before')
                    spaces_after = kwargs.get('spaces_after')
                    if spaces_before:
                        message = '<br>' * spaces_before + message
                    if spaces_after is None:
                        spaces_after = 2
                    if spaces_after and spaces_after > 0:
                        message = message + '<br>' * spaces_after

                    # ALWAYS convert newlines for HTML
                    if '\n' in message:
                        message = message.replace('\n', '<br>')
                        
                    if simulate_typing:
                        # This logic correctly handles typing out messages with trailing line breaks
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
                        # If not simulating, just send the pre-formatted HTML message
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

      * **Commit Message:** `fix(ui): Restore spacing logic for verbatim messages`

### Completion Protocol (Definition of Done)

You are **DONE** when the step is committed and `git status` is clean. When complete, perform the sign-off procedure.

-----

Your first action is to **orient yourself**. Begin now.
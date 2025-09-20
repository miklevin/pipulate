Hello Gemini.

You are waking up on the `magicuser` branch. Your mission is to refactor the simple tool-calling mechanism to be a general-purpose system and, most critically, to **close the feedback loop** by streaming the tool's output back to the user in the chat interface. A previous attempt on this branch failed, so we are starting fresh from a clean state.

**The Unbreakable Laws of Physics:**

1.  **Nix Environment:** You are **always** in a `nix develop` shell. You will **never** use `pip install`.
2.  **Robust Edits:** You will **never** use `sed` for multi-line insertions or complex edits. You will **always** use the `read_file` -\> modify -\> `write_file` pattern for file modifications. Simple, single-line `sed` insertions are permitted. You will **never** use the `replace` tool.
3.  **Verify, Then Commit:** After every file modification, run `git diff` to verify the change was exactly what you intended. After verification, `git commit` with the provided message.
4.  **One Small Step:** Execute only one step at a time.
5.  **Server Health Check:** After every commit, run `touch server.py && sleep 8`. If the server log shows an error, you **MUST** immediately stop and report the failure.
6.  **Definition of Done:** The mission is complete when all steps are committed, `git status` is clean, and the server restarts successfully.
7.  **Completion Protocol:** Announce success with `echo "✅ Magic User protocol complete. The feedback loop is closed."`

### The Implementation Plan

#### **Step 1: Make Core Tools Aliasable**

We need to add the `@alias` decorator so the new system can discover our simple bracket commands.

  * **Action 1: Read `tools/system_tools.py`**
    ```bash
    .venv/bin/python cli.py call local_llm_read_file --file_path "tools/system_tools.py"
    ```
  * **Action 2: Apply the `@alias` decorators.**
    ```bash
    .venv/bin/python cli.py call local_llm_write_file --file_path "tools/system_tools.py" --old_code """@auto_tool
    ```

async def system\_list\_directory(params: dict) -\> dict:""" --new\_code """@auto\_tool
@alias("ls")
async def system\_list\_directory(params: dict) -\> dict:"""
.venv/bin/python cli.py call local\_llm\_write\_file --file\_path "tools/system\_tools.py" --old\_code """@auto\_tool
async def execute\_shell\_command(params: dict) -\> dict:""" --new\_code """@auto\_tool
@alias("shell")
async def execute\_shell\_command(params: dict) -\> dict:"""
\`\`\`

  * **Verification:**
    ```bash
    git diff
    ```
  * **Commit:**
    ```bash
    git commit -am "feat(tools): Add aliases for core system commands ls and shell"
    ```

#### **Step 2: Add Necessary Imports to `server.py`**

The new logic requires the tool registries.

  * **Action:**
    ```bash
    sed -i "/from watchdog.observers import Observer/a from tools import ALIAS_REGISTRY, MCP_TOOL_REGISTRY" server.py
    ```
  * **Verification:**
    ```bash
    git diff
    ```
  * **Commit:**
    ```bash
    git commit -am "feat(mcp): Add imports for generalized bracket command handling"
    ```

#### **Step 3: Refactor `pipulate.stream` to Generalize Tool Calls**

This is the core of the mission. We will replace the entire `pipulate.stream` method with a new, more intelligent version.

  * **Action 1: Read the current `server.py` file.**
    ```bash
    .venv/bin/python cli.py call local_llm_read_file --file_path "server.py"
    ```
  * **Action 2: Replace the entire `stream` function with the new, generalized logic.**
    *You must find the exact boundaries of the `async def stream(...)` function from the file content you just read to use as the `old_code` value.*
    ````bash
    .venv/bin/python cli.py call local_llm_write_file --file_path "server.py" --old_code """
    async def stream(self, message, verbatim=False, role='user', spaces_before=None, spaces_after=None, simulate_typing=True):
    # ... PASTE THE ENTIRE CURRENT FUNCTION BODY HERE, FROM THE FILE YOU JUST READ ...
        await self._handle_llm_stream()
        logger.debug(f"🔍 DEBUG: === ENDING pipulate.stream (LLM) ===")
        return message
    """ --new_code """
    async def stream(self, message, verbatim=False, role='user', spaces_before=None, spaces_after=None, simulate_typing=True):
        \"\"\"Stream a message to the chat interface.
        This is now the single source of truth for conversation history management.
        All messages entering the chat system must go through this method.
        \"\"\"
        logger.debug(f"🔍 DEBUG: === STARTING pipulate.stream (role: {role}) ===")
        # --- NEW: GENERALIZED BRACKET COMMAND ORCHESTRATION ---
        if role == 'user': # Only check user messages for simple commands
            simple_command_match = re.match(r'^\s*\[([^\]]+)\]\s*$', message) # Match if the *entire* message is a command
            if simple_command_match:
                full_command_string = simple_command_match.group(1).strip()
                command_parts = full_command_string.split(maxsplit=1)
                command_alias = command_parts[0]
                command_args_str = command_parts[1] if len(command_parts) > 1 else ""
                logger.info(f"SIMPLE CMD DETECTED: Intercepted command '[{full_command_string}]' from user.")
                append_to_conversation(message, 'user') # Log what the user typed
                tool_name = ALIAS_REGISTRY.get(command_alias)
                if tool_name and tool_name in MCP_TOOL_REGISTRY:
                    params = {}
                    if command_args_str:
                        # Simple convention: first arg maps to primary parameter
                        if tool_name == 'system_list_directory':
                            params['path'] = command_args_str
                        elif tool_name == 'execute_shell_command':
                            params['command'] = command_args_str
                        else: # A generic fallback
                            params['args'] = command_args_str
                    
                    # Execute the tool
                    tool_handler = MCP_TOOL_REGISTRY[tool_name]
                    tool_output = await tool_handler(params)
                    
                    # Format the output nicely for the chat
                    formatted_output = f"```\n"
                    if tool_output.get('success'):
                        if 'stdout' in tool_output: # Shell command output
                            formatted_output += tool_output.get('stdout') or "[No output]"
                        elif 'directories' in tool_output: # ls output
                            dirs = '\n'.join([f"📁 {d}" for d in tool_output.get('directories', [])])
                            files = '\n'.join([f"📄 {f}" for f in tool_output.get('files', [])])
                            formatted_output += f"Directory listing for: {tool_output.get('path', '.')}\n\n{dirs}\n{files}"
                        else:
                            formatted_output += json.dumps(tool_output, indent=2)
                    else:
                        formatted_output += f"Error executing [{command_alias}]:\n{tool_output.get('error', 'Unknown error')}"
                    formatted_output += "\n```"
                    
                    # CRITICAL: Stream the tool's output back to the user
                    await self.stream(formatted_output, role='tool', verbatim=True)
                    return # IMPORTANT: End the execution here to prevent sending to LLM
        # --- END MODIFICATION ---
        # The rest of the function remains the same...
        append_to_conversation(message, role)
        if verbatim:
            try:
                if self.chat is None:
                    logger.warning("Chat instance not available yet, queuing message for later")
                    return message
                if spaces_before:
                    message = '<br>' * spaces_before + message
                if spaces_after is None:
                    spaces_after = 2
                if spaces_after and spaces_after > 0:
                    message = message + '<br>' * spaces_after
                if simulate_typing:
                    logger.debug("🔍 DEBUG: Simulating typing for verbatim message")
                    if '\n' in message:
                        message = message.replace('\n', '<br>')
                    import re
                    br_match = re.search(r'(<br>+)$', message)
                    if br_match:
                        base_message = message[:br_match.start()]
                        br_tags = br_match.group(1)
                        words = base_message.split()
                        for i, word in enumerate(words):
                            await self.chat.broadcast(word + (' ' if i < len(words) - 1 else ''))
                            await asyncio.sleep(PCONFIG['CHAT_CONFIG']['TYPING_DELAY'])
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
        await self._handle_llm_stream()
        logger.debug(f"🔍 DEBUG: === ENDING pipulate.stream (LLM) ===")
        return message
    """
    ````
  * **Verification:**
    ```bash
    git diff
    ```
  * **Commit:**
    ```bash
    git commit -am "feat(mcp): Generalize bracket commands and close feedback loop
    ```

Refactors the `pipulate.stream` method to handle simple, bracketed tool calls in a generic and robust way.

  - Replaces the hardcoded `[ls]` check with a dynamic lookup in the `ALIAS_REGISTRY`.
  - Implements a simple argument parser for commands like `[ls tools]`.
  - Executes the aliased tool via the `MCP_TOOL_REGISTRY`.
  - Formats the tool's output into a markdown code block.
  - **Crucially, streams the formatted result back to the chat UI, providing immediate feedback to the user and closing the loop.**
  - Short-circuits the LLM, preventing the command from being processed as conversational text."
    ```
    
    ```

#### **Step 4: Final Verification**

Restart the server and confirm the changes were successful and non-breaking.

  * **Action:**
    ```bash
    touch server.py && sleep 8
    ```
  * **Expected Output:** The server should restart cleanly with no errors in the console.

Now, execute the `Completion Protocol`.

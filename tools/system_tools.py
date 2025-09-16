"""
A plugin that provides basic system-level tools.
"""
import os
import asyncio
from tools import auto_tool, alias

@auto_tool
@alias("ls")
async def system_list_directory(params: dict) -> dict:
    """
    Lists the contents of a specified directory.
    A simple wrapper around os.listdir().

    Args:
        params: A dictionary that may contain:
            - path (str): The directory path to list. Defaults to '.'.
    """
    path = params.get('path', '.')
    try:
        # Security check: ensure path is within the project
        abs_path = os.path.abspath(os.path.join(os.getcwd(), path))
        if not abs_path.startswith(os.getcwd()):
            return {"success": False, "error": "Directory access outside project root is not allowed."}

        if not os.path.isdir(path):
            return {"success": False, "error": f"Path is not a valid directory: {path}"}

        entries = os.listdir(path)
        files = [e for e in entries if os.path.isfile(os.path.join(path, e))]
        dirs = [e for e in entries if os.path.isdir(os.path.join(path, e))]

        return {
            "success": True,
            "path": path,
            "directories": sorted(dirs),
            "files": sorted(files)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@auto_tool
@alias("shell")
async def execute_shell_command(params: dict) -> dict:
    """
    Executes a shell command and returns its stdout, stderr, and exit code.
    This tool provides the AI with the ability to interact directly with the underlying operating system.

    Args:
        params: A dictionary containing:
            - command (str): The shell command to execute.
            - cwd (str, optional): The current working directory for the command. Defaults to the project root.
            - timeout (int, optional): Maximum time in seconds to wait for the command to complete. Defaults to 60.
    """
    command = params.get('command')
    cwd = params.get('cwd', '.')
    timeout = params.get('timeout', 60)

    if not command:
        return {"success": False, "error": "'command' parameter is required."}

    try:
        # Security check: ensure cwd is within the project
        abs_cwd = os.path.abspath(os.path.join(os.getcwd(), cwd))
        if not abs_cwd.startswith(os.getcwd()):
            return {"success": False, "error": "Current working directory access outside project root is not allowed."}

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=abs_cwd
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

        return {
            "success": True,
            "command": command,
            "stdout": stdout.decode().strip(),
            "stderr": stderr.decode().strip(),
            "exit_code": process.returncode
        }
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return {"success": False, "error": f"Command timed out after {timeout} seconds.", "command": command}
    except Exception as e:
        return {"success": False, "error": str(e), "command": command}

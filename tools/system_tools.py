"""
A plugin that provides basic system-level tools.
"""
import os
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

# Create new file: tools/keychain_tools.py
"""
MCP Tools: AI Keychain (Persistent Memory)
Tools for interacting with the AI's long-term, persistent memory, which
survives application restarts.
"""
import logging
from tools import auto_tool, alias
from imports.ai_dictdb import keychain_instance
logger = logging.getLogger(__name__)

@auto_tool
@alias("note")
async def keychain_set(params: dict) -> dict:
    """Saves a persistent key-value message for future AI instances.
    This is THE tool for leaving "messages in a bottle" for your future selves.
    Unlike temporary application state (db, pipeline), this ai_dictdb survives
    application resets and lives outside the normal application lifecycle.
    Args:
        params: Dict containing:
            - key: The unique key to store the message under
            - value: The message/data to store (will be converted to string)
    Returns:
        Dict with success status and confirmation details
    """
    logger.info(f"🧠 FINDER_TOKEN: KEYCHAIN_SET_START - {params.get('key', 'NO_KEY')}")
    try:
        key = params.get('key')
        value = params.get('value')
        if not key:
            return {
                "success": False,
                "error": "The 'key' parameter is required",
                "usage": "keychain_set({'key': 'your_key', 'value': 'your_message'})"
            }
        if value is None:
            return {
                "success": False,
                "error": "The 'value' parameter is required",
                "usage": "keychain_set({'key': 'your_key', 'value': 'your_message'})"
            }
        value_str = str(value)
        keychain_instance[key] = value_str
        logger.info(f"🧠 FINDER_TOKEN: KEYCHAIN_SET_SUCCESS - Key '{key}' stored with {len(value_str)} characters")
        return {
            "success": True,
            "key": key,
            "message": f"Message stored in persistent ai_dictdb under key '{key}'",
            "value_length": len(value_str),
            "total_keys": keychain_instance.count(),
            "usage_note": "This message will persist across application resets and be available to future AI instances"
        }
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: KEYCHAIN_SET_ERROR - {e}")
        return {
            "success": False,
            "error": str(e),
            "recovery_suggestion": "Check ai_dictdb database permissions and disk space"
        }

@auto_tool
async def keychain_get(params: dict) -> dict:
    """Retrieves a persistent message from the ai_dictdb by key."""
    logger.info(f"🧠 FINDER_TOKEN: KEYCHAIN_GET_START - {params.get('key', 'NO_KEY')}")
    try:
        key = params.get('key')
        if not key:
            return { "success": False, "error": "The 'key' parameter is required" }
        value = keychain_instance.get(key)
        if value is not None:
            logger.info(f"🧠 FINDER_TOKEN: KEYCHAIN_GET_SUCCESS - Key '{key}' found with {len(value)} characters")
            return { "success": True, "key": key, "value": value }
        else:
            logger.info(f"🧠 FINDER_TOKEN: KEYCHAIN_GET_NOT_FOUND - Key '{key}' not found")
            return { "success": False, "error": f"Key '{key}' not found in ai_dictdb" }
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: KEYCHAIN_GET_ERROR - {e}")
        return { "success": False, "error": str(e) }

@auto_tool
async def keychain_delete(params: dict) -> dict:
    """Deletes a message from the persistent ai_dictdb."""
    logger.info(f"🧠 FINDER_TOKEN: KEYCHAIN_DELETE_START - {params.get('key', 'NO_KEY')}")
    try:
        key = params.get('key')
        if not key:
            return { "success": False, "error": "The 'key' parameter is required" }
        if key in keychain_instance:
            del keychain_instance[key]
            logger.info(f"🧠 FINDER_TOKEN: KEYCHAIN_DELETE_SUCCESS - Key '{key}' deleted")
            return { "success": True, "message": f"Key '{key}' deleted from persistent ai_dictdb" }
        else:
            logger.info(f"🧠 FINDER_TOKEN: KEYCHAIN_DELETE_NOT_FOUND - Key '{key}' not found")
            return { "success": False, "error": f"Key '{key}' not found in ai_dictdb" }
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: KEYCHAIN_DELETE_ERROR - {e}")
        return { "success": False, "error": str(e) }

@auto_tool
@alias("notes")
async def keychain_list_keys(params: dict) -> dict:
    """Lists all keys currently in the persistent AI ai_dictdb."""
    logger.info("🧠 FINDER_TOKEN: KEYCHAIN_LIST_KEYS_START")
    try:
        keys = keychain_instance.keys()
        logger.info(f"🧠 FINDER_TOKEN: KEYCHAIN_LIST_KEYS_SUCCESS - Found {len(keys)} keys")
        return { "success": True, "keys": keys, "count": len(keys) }
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: KEYCHAIN_LIST_KEYS_ERROR - {e}")
        return { "success": False, "error": str(e) }

@auto_tool
async def keychain_get_all(params: dict) -> dict:
    """Retrieves all key-value pairs from the ai_dictdb."""
    logger.info("🧠 FINDER_TOKEN: KEYCHAIN_GET_ALL_START")
    try:
        items = dict(keychain_instance.items())
        limit = params.get('limit')
        if limit and isinstance(limit, int) and limit > 0:
            items = dict(list(items.items())[:limit])
        logger.info(f"🧠 FINDER_TOKEN: KEYCHAIN_GET_ALL_SUCCESS - Retrieved {len(items)} items")
        return { "success": True, "ai_dictdb": items, "count": len(items) }
    except Exception as e:
        logger.error(f"❌ FINDER_TOKEN: KEYCHAIN_GET_ALL_ERROR - {e}")
        return { "success": False, "error": str(e) }

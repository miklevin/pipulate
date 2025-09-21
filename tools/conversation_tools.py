# Create new file: tools/conversation_tools.py
"""
MCP Tools: Conversation History
Tools for viewing and managing the append-only conversation history.
"""
import logging
from tools import auto_tool
try:
    from imports.append_only_conversation import get_conversation_system
except ImportError:
    get_conversation_system = None
logger = logging.getLogger(__name__)

@auto_tool
async def conversation_history_view(params: dict) -> dict:
    """View the recent conversation history."""
    if not get_conversation_system:
        return {"success": False, "error": "Conversation system not available"}
    try:
        conv_system = get_conversation_system()
        history = conv_system.get_conversation_list()
        limit = params.get('limit', 20)
        return {
            "success": True,
            "history": history[-limit:],
            "total_messages": len(history)
        }
    except Exception as e:
        logger.error(f"❌ Error fetching conversation history: {e}")
        return {"success": False, "error": str(e)}

@auto_tool
async def conversation_history_stats(params: dict) -> dict:
    """Get statistics about the current conversation."""
    if not get_conversation_system:
        return {"success": False, "error": "Conversation system not available"}
    try:
        conv_system = get_conversation_system()
        stats = conv_system.get_conversation_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        logger.error(f"❌ Error fetching conversation stats: {e}")
        return {"success": False, "error": str(e)}

@auto_tool
async def conversation_history_clear(params: dict) -> dict:
    """
    Clears the current conversation history after creating a backup.
    This action is irreversible from the UI but can be restored from backups.
    """
    if not get_conversation_system:
        return {"success": False, "error": "Conversation system not available"}
    try:
        conv_system = get_conversation_system()
        cleared_count = conv_system.clear_conversation(create_backup=True)
        return {
            "success": True,
            "message": f"Successfully cleared and archived {cleared_count} messages."
        }
    except Exception as e:
        logger.error(f"❌ Error clearing conversation: {e}")
        return {"success": False, "error": str(e)}
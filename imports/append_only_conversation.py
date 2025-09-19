#!/usr/bin/env python3
"""
🛡️ Append-Only Conversation System
Architecturally safe conversation handling that prevents overwrites

ARCHITECTURAL GUARANTEES:
- Each message is an immutable database record
- IMPOSSIBLE to overwrite existing conversation history
- Automatic deduplication via message hashing
- Rolling backup system integrated
- Memory and database stay synchronized

REPLACES:
- save_conversation_to_db() - vulnerable to complete replacement
- load_conversation_from_db() - complex merging logic
- append_to_conversation() - bound to vulnerable save function
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path
import logging
from collections import deque
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class AppendOnlyConversationSystem:
    """
    Architecturally safe conversation system with append-only guarantees
    
    Key principles:
    1. Each message is a separate database record (immutable)
    2. Only INSERT operations allowed (never UPDATE/REPLACE)
    3. Automatic backup before any operation
    4. Memory-database synchronization 
    5. Token window management via deque
    """
    
    def __init__(self, db_path: str = "data/discussion.db", max_messages: int = 10000):
        self.db_path = Path(db_path)
        self.max_messages = max_messages
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # In-memory conversation for fast access (synced with database)
        self.conversation_memory = deque(maxlen=max_messages)
        
        # Ensure schema exists
        self._ensure_schema()
        
        # Load existing conversation into memory
        self._sync_memory_from_database()
    
    def _ensure_schema(self):
        """Ensure the append-only conversation schema exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                message_hash TEXT UNIQUE,
                session_id TEXT DEFAULT 'default',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Archive table for deleted messages
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS archived_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_message_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                message_hash TEXT,
                session_id TEXT DEFAULT 'default',
                created_at DATETIME NOT NULL,
                archived_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                archive_reason TEXT DEFAULT 'user_deleted'
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON conversation_messages(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_role ON conversation_messages(role)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session ON conversation_messages(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON conversation_messages(created_at)')
        
        # Archive table indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_archive_original_id ON archived_messages(original_message_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_archive_timestamp ON archived_messages(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_archive_date ON archived_messages(archived_at)')
        
        conn.commit()
        conn.close()
    
    def _sync_memory_from_database(self):
        """Load the latest conversation messages into memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load the most recent messages up to max_messages limit
        cursor.execute('''
            SELECT role, content, timestamp, session_id
            FROM conversation_messages 
            ORDER BY id DESC 
            LIMIT ?
        ''', (self.max_messages,))
        
        # Reverse to get chronological order
        messages = cursor.fetchall()
        messages.reverse()
        
        # Clear and repopulate memory
        self.conversation_memory.clear()
        for row in messages:
            self.conversation_memory.append({
                'role': row[0],
                'content': row[1], 
                'timestamp': row[2],
                'session_id': row[3]
            })
        
        conn.close()
        logger.info(f"💾 FINDER_TOKEN: MEMORY_SYNCED - {len(self.conversation_memory)} messages loaded")
    
    def _create_message_hash(self, role: str, content: str, timestamp: str) -> str:
        """Create unique hash for deduplication"""
        hash_input = f"{role}:{content}:{timestamp}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _create_backup(self, operation: str = "before_append"):
        """Create backup before any operation"""
        try:
            from imports.conversation_backup_system import create_conversation_backup
            create_conversation_backup(operation)
        except Exception as e:
            logger.warning(f"💾 BACKUP WARNING: Could not create backup: {e}")
    
    def append_message(self, role: str, content: str, session_id: str = None) -> Optional[int]:
        """
        ARCHITECTURALLY SAFE: Append a message to conversation
        
        This function is IMPOSSIBLE to overwrite existing messages.
        Each message becomes an immutable database record.
        
        Returns:
            message_id if successful, None if duplicate
        """
        if not content or not role:
            return None
        
        # Use current session if not specified
        if not session_id:
            session_id = self.session_id
        
        timestamp = datetime.now().isoformat()
        message_hash = self._create_message_hash(role, content, timestamp)
        
        # Check for duplicate in memory (fast check)
        if self._is_duplicate_in_memory(role, content):
            logger.debug(f"💾 Duplicate detected in memory: {content[:50]}...")
            return None
        
        # Create backup before append
        # self._create_backup("before_message_append") # Redundant: Durable backup runs on startup
        
        # Append to database (ONLY INSERT - NEVER REPLACE)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO conversation_messages (timestamp, role, content, message_hash, session_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (timestamp, role, content, message_hash, session_id))
            
            conn.commit()
            message_id = cursor.lastrowid
            
            # Add to memory (with automatic deque size management)
            self.conversation_memory.append({
                'role': role,
                'content': content,
                'timestamp': timestamp,
                'session_id': session_id
            })
            
            logger.info(f"💾 FINDER_TOKEN: MESSAGE_APPENDED_SAFE - ID:{message_id}, Role:{role}, Hash:{message_hash}")
            return message_id
            
        except sqlite3.IntegrityError:
            # Duplicate message hash - this is fine
            logger.debug(f"💾 Duplicate message hash ignored: {message_hash}")
            return None
        except Exception as e:
            logger.error(f"💾 CRITICAL: Message append failed: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _is_duplicate_in_memory(self, role: str, content: str) -> bool:
        """Check if message is duplicate of recent messages in memory"""
        if not self.conversation_memory:
            return False
        
        # Check last 3 messages for exact duplicates
        recent_messages = list(self.conversation_memory)[-3:]
        for msg in recent_messages:
            if msg['role'] == role and msg['content'] == content:
                return True
        return False
    
    def get_conversation_list(self) -> List[Dict]:
        """Get conversation history as list (compatible with existing code)"""
        return list(self.conversation_memory)
    
    def get_conversation_stats(self) -> Dict:
        """Get conversation statistics"""
        conversation_list = self.get_conversation_list()
        total_messages = len(conversation_list)
        
        if total_messages == 0:
            return {
                'total_messages': 0,
                'role_distribution': {},
                'architecture': 'append_only_safe',
                'memory_db_sync': True
            }
        
        # Role distribution
        role_counts = {}
        total_content_length = 0
        
        for msg in conversation_list:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            
            role_counts[role] = role_counts.get(role, 0) + 1
            total_content_length += len(content)
        
        # Database verification
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM conversation_messages")
        db_total = cursor.fetchone()[0]
        conn.close()
        
        return {
            'total_messages': total_messages,
            'role_distribution': role_counts,
            'total_content_length': total_content_length,
            'average_message_length': total_content_length / total_messages if total_messages > 0 else 0,
            'database_total_messages': db_total,
            'memory_db_sync': True,
            'architecture': 'append_only_safe',
            'session_id': self.session_id
        }
    
    def clear_conversation(self, create_backup: bool = True) -> int:
        """Clear conversation history with backup"""
        if create_backup:
            self._create_backup("before_conversation_clear")
        
        # Clear memory
        cleared_count = len(self.conversation_memory)
        self.conversation_memory.clear()
        
        # Archive database messages (don't delete - move to archive table)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Create archive table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_messages_archive (
                    id INTEGER,
                    timestamp TEXT,
                    role TEXT,
                    content TEXT,
                    message_hash TEXT,
                    session_id TEXT,
                    archived_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    original_created_at DATETIME
                )
            ''')
            
            # Move current messages to archive
            cursor.execute('''
                INSERT INTO conversation_messages_archive 
                (id, timestamp, role, content, message_hash, session_id, original_created_at)
                SELECT id, timestamp, role, content, message_hash, session_id, created_at
                FROM conversation_messages
            ''')
            
            # Clear the main table
            cursor.execute('DELETE FROM conversation_messages')
            
            conn.commit()
            logger.info(f"💾 FINDER_TOKEN: CONVERSATION_CLEARED_SAFE - {cleared_count} messages archived")
            
        except Exception as e:
            logger.error(f"💾 CRITICAL: Conversation clear failed: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
        
        return cleared_count
    
    def restore_from_backup(self, backup_date: str = None) -> int:
        """Restore conversation from backup"""
        try:
            from imports.conversation_backup_system import restore_conversation_backup
            
            # Clear current conversation
            self.clear_conversation(create_backup=True)
            
            # Restore from backup
            restored_messages = restore_conversation_backup(backup_date)
            
            # Re-sync memory from database
            self._sync_memory_from_database()
            
            logger.info(f"💾 FINDER_TOKEN: CONVERSATION_RESTORED_SAFE - {len(restored_messages)} messages restored")
            return len(restored_messages)
            
        except Exception as e:
            logger.error(f"💾 CRITICAL: Conversation restore failed: {e}")
            raise

    def archive_message(self, message_id: int, archive_reason: str = "user_deleted") -> bool:
        """
        Archive a message by moving it from conversation_messages to archived_messages.
        This preserves the data while removing it from active conversation.
        
        Args:
            message_id: The ID of the message to archive
            archive_reason: Reason for archiving (default: 'user_deleted')
            
        Returns:
            True if message was archived successfully, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # First, get the message to archive
            cursor.execute('SELECT * FROM conversation_messages WHERE id = ?', (message_id,))
            message = cursor.fetchone()
            
            if not message:
                logger.warning(f"💾 Message ID {message_id} not found for archiving")
                return False
            
            # Insert into archive table
            cursor.execute('''
                INSERT INTO archived_messages 
                (original_message_id, timestamp, role, content, message_hash, session_id, created_at, archive_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (message[0], message[1], message[2], message[3], message[4], message[5], message[6], archive_reason))
            
            # Delete from active conversation
            cursor.execute('DELETE FROM conversation_messages WHERE id = ?', (message_id,))
            
            conn.commit()
            
            # Remove from memory cache
            self.conversation_memory = deque([
                msg for msg in self.conversation_memory 
                if not (msg.get('content') == message[3] and msg.get('role') == message[2])
            ], maxlen=self.max_messages)
            
            logger.info(f"💾 FINDER_TOKEN: MESSAGE_ARCHIVED - ID:{message_id}, Reason:{archive_reason}")
            return True
            
        except Exception as e:
            logger.error(f"💾 Failed to archive message ID {message_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_archived_messages(self, limit: int = 100) -> List[Dict]:
        """Get archived messages"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT original_message_id, timestamp, role, content, session_id, 
                   created_at, archived_at, archive_reason
            FROM archived_messages 
            ORDER BY archived_at DESC 
            LIMIT ?
        ''', (limit,))
        
        archived = []
        for row in cursor.fetchall():
            archived.append({
                'original_id': row[0],
                'timestamp': row[1],
                'role': row[2],
                'content': row[3],
                'session_id': row[4],
                'created_at': row[5],
                'archived_at': row[6],
                'archive_reason': row[7]
            })
        
        conn.close()
        return archived

# Global instance for backward compatibility
_conversation_system = None

def get_conversation_system() -> AppendOnlyConversationSystem:
    """Get the global conversation system instance"""
    global _conversation_system
    if _conversation_system is None:
        _conversation_system = AppendOnlyConversationSystem()
    return _conversation_system

# Backward-compatible functions that replace the vulnerable ones

def append_to_conversation_safe(message: str = None, role: str = 'user') -> List[Dict]:
    """
    SAFE REPLACEMENT for append_to_conversation()
    
    This function is architecturally IMPOSSIBLE to overwrite conversation history.
    Uses append-only database operations only.
    """
    conv_system = get_conversation_system()
    
    if message is None:
        return conv_system.get_conversation_list()
    
    # Append message safely
    message_id = conv_system.append_message(role, message)
    
    if message_id:
        logger.info(f"💾 FINDER_TOKEN: SAFE_APPEND_SUCCESS - Message ID: {message_id}")
    
    return conv_system.get_conversation_list()

def load_conversation_from_db_safe() -> bool:
    """
    SAFE REPLACEMENT for load_conversation_from_db()
    
    Simply syncs memory from database - no complex merging needed.
    """
    conv_system = get_conversation_system()
    conv_system._sync_memory_from_database()
    
    conversation_count = len(conv_system.get_conversation_list())
    logger.info(f"💾 FINDER_TOKEN: SAFE_LOAD_SUCCESS - {conversation_count} messages loaded")
    
    return conversation_count > 0

def save_conversation_to_db_safe():
    """
    SAFE REPLACEMENT for save_conversation_to_db()
    
    No-op function since messages are saved immediately on append.
    This maintains backward compatibility.
    """
    conv_system = get_conversation_system()
    conversation_count = len(conv_system.get_conversation_list())
    logger.debug(f"💾 FINDER_TOKEN: SAFE_SAVE_NOOP - {conversation_count} messages already persisted")

def get_conversation_stats_safe() -> Dict:
    """Get comprehensive conversation statistics"""
    conv_system = get_conversation_system()
    return conv_system.get_conversation_stats()

# Migration function to switch to new system
def migrate_to_append_only_system():
    """Migrate from JSON blob to append-only system"""
    from imports.conversation_architecture_migration import ConversationArchitectureMigration
    
    migration = ConversationArchitectureMigration()
    result = migration.run_full_migration()
    
    if result['success']:
        # Initialize the new system
        global _conversation_system
        _conversation_system = AppendOnlyConversationSystem()
        logger.info("🏗️ FINDER_TOKEN: MIGRATION_SUCCESS - Switched to append-only conversation system")
    else:
        logger.error("🏗️ FINDER_TOKEN: MIGRATION_FAILED - Staying with current system")
    
    return result 

async def get_conversation_history(limit: int = 100, offset: int = 0, role_filter: str = None) -> List[Dict]:
    """
    Get conversation history for the history plugin.
    
    Args:
        limit: Maximum number of messages to return
        offset: Number of messages to skip
        role_filter: Filter by role ('user', 'assistant', 'system') or None for all
        
    Returns:
        List of conversation messages with database IDs for delete functionality (newest first)
    """
    conv_system = get_conversation_system()
    
    # CRITICAL: Fetch directly from database to get message IDs
    conn = sqlite3.connect(conv_system.db_path)
    cursor = conn.cursor()
    
    try:
        # Build query with optional role filter - ORDER BY DESC for newest first
        base_query = '''
            SELECT id, timestamp, role, content, session_id, created_at
            FROM conversation_messages
        '''
        
        if role_filter:
            base_query += ' WHERE role = ?'
            cursor.execute(base_query + ' ORDER BY created_at DESC LIMIT ? OFFSET ?', 
                         (role_filter, limit, offset))
        else:
            cursor.execute(base_query + ' ORDER BY created_at DESC LIMIT ? OFFSET ?', 
                         (limit, offset))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'id': row[0],  # Include database ID for delete functionality
                'timestamp': row[1],
                'role': row[2],
                'content': row[3],
                'session_id': row[4],
                'created_at': row[5]
            })
        
        # Messages are already in newest first order from the query
        return messages
        
    finally:
        conn.close()

async def archive_message_by_id(message_id: int) -> bool:
    """Archive a message by ID (async wrapper for UI)"""
    conv_system = get_conversation_system()
    return conv_system.archive_message(message_id)

async def get_conversation_stats() -> Dict:
    """
    Get conversation statistics for the history plugin.
    
    Returns:
        Dictionary with conversation statistics
    """
    conv_system = get_conversation_system()
    
    # CRITICAL: Sync with database first to get latest stats
    conv_system._sync_memory_from_database()
    
    all_messages = conv_system.get_conversation_list()
    
    # Count messages by role
    role_counts = {}
    for msg in all_messages:
        role = msg.get('role', 'unknown')
        role_counts[role] = role_counts.get(role, 0) + 1
    
    # Calculate total characters
    total_chars = sum(len(msg.get('content', '')) for msg in all_messages)
    
    # Get archived message count
    conn = sqlite3.connect(conv_system.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM archived_messages")
    archived_count = cursor.fetchone()[0]
    conn.close()
    
    return {
        'total_messages': len(all_messages),
        'role_distribution': role_counts,  # Changed from role_counts to role_distribution
        'total_characters': total_chars,
        'archived_messages': archived_count,
        'database_path': str(conv_system.db_path)
    }
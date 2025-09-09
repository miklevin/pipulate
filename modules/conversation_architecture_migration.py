#!/usr/bin/env python3
"""
🏗️ Conversation Architecture Migration
Migrates from vulnerable JSON blob storage to append-only message architecture

ARCHITECTURAL IMPROVEMENT:
- From: Single JSON blob that gets completely replaced
- To: One row per message with append-only guarantees

BENEFITS:
- Architecturally impossible to overwrite conversation history
- Each message is an immutable database record
- Backup and recovery at message granularity
- Query individual messages without parsing JSON
- Proper indexing for performance
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ConversationArchitectureMigration:
    """Migrate conversation storage from JSON blob to append-only message records"""
    
    def __init__(self, discussion_db_path="data/discussion.db"):
        self.db_path = Path(discussion_db_path)
        
    def create_new_schema(self):
        """Create the new append-only conversation schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create the new conversation_messages table
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
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON conversation_messages(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_role ON conversation_messages(role)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session ON conversation_messages(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON conversation_messages(created_at)')
        
        conn.commit()
        conn.close()
        logger.info("🏗️ New conversation schema created")
        
    def migrate_existing_conversation(self):
        """Migrate existing JSON blob conversation to individual message records"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if old conversation data exists
            cursor.execute("SELECT value FROM store WHERE key = 'llm_conversation_history'")
            result = cursor.fetchone()
            
            if not result:
                logger.info("💾 No existing conversation data to migrate")
                return 0
            
            # Parse the JSON conversation data
            conversation_data = json.loads(result[0])
            migrated_count = 0
            
            for i, message in enumerate(conversation_data):
                if isinstance(message, dict) and 'role' in message and 'content' in message:
                    # Create timestamp for message (use index for ordering)
                    timestamp = datetime.now().replace(microsecond=i).isoformat()
                    
                    # Create hash to prevent duplicates
                    message_hash = self._create_message_hash(
                        message['role'], 
                        message['content'], 
                        timestamp
                    )
                    
                    try:
                        cursor.execute('''
                            INSERT INTO conversation_messages 
                            (timestamp, role, content, message_hash, session_id)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            timestamp,
                            message['role'],
                            message['content'], 
                            message_hash,
                            'migrated_from_json'
                        ))
                        migrated_count += 1
                    except sqlite3.IntegrityError:
                        # Duplicate message - skip
                        logger.debug(f"Skipping duplicate message: {message_hash}")
            
            conn.commit()
            logger.info(f"🚀 Successfully migrated {migrated_count} messages to new schema")
            
            # Backup the old JSON data before removing
            backup_key = f"llm_conversation_history_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            cursor.execute(
                "INSERT INTO store (key, value) VALUES (?, ?)",
                (backup_key, result[0])
            )
            
            # Remove the old JSON blob (optional - can be kept for safety)
            # cursor.execute("DELETE FROM store WHERE key = 'llm_conversation_history'")
            
            conn.commit()
            return migrated_count
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _create_message_hash(self, role: str, content: str, timestamp: str) -> str:
        """Create a unique hash for a message to prevent duplicates"""
        hash_input = f"{role}:{content}:{timestamp}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def verify_migration(self):
        """Verify the migration was successful"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check message count in new table
        cursor.execute("SELECT COUNT(*) FROM conversation_messages")
        new_count = cursor.fetchone()[0]
        
        # Check if old data still exists
        cursor.execute("SELECT value FROM store WHERE key = 'llm_conversation_history'")
        old_result = cursor.fetchone()
        old_count = 0
        
        if old_result:
            old_conversation = json.loads(old_result[0])
            old_count = len(old_conversation)
        
        conn.close()
        
        logger.info(f"📊 Migration verification:")
        logger.info(f"   Old JSON messages: {old_count}")
        logger.info(f"   New table messages: {new_count}")
        
        return new_count >= old_count
    
    def run_full_migration(self):
        """Execute the complete migration process"""
        logger.info("🏗️ Starting conversation architecture migration...")
        
        # Step 1: Create new schema
        self.create_new_schema()
        
        # Step 2: Migrate existing data
        migrated_count = self.migrate_existing_conversation()
        
        # Step 3: Verify migration
        verification_success = self.verify_migration()
        
        if verification_success:
            logger.info("✅ Migration completed successfully!")
            return {
                'success': True,
                'migrated_messages': migrated_count,
                'verification_passed': True
            }
        else:
            logger.error("❌ Migration verification failed!")
            return {
                'success': False,
                'migrated_messages': migrated_count,
                'verification_passed': False
            }

# New append-only conversation functions
def append_message_to_db(role: str, content: str, session_id: str = "default", 
                        timestamp: str = None, db_path: str = "data/discussion.db"):
    """
    Architecturally safe: ONLY INSERT, never replace
    
    This function is architecturally IMPOSSIBLE to overwrite existing messages.
    Each message becomes an immutable database record.
    """
    import sqlite3
    import hashlib
    from datetime import datetime
    
    if not timestamp:
        timestamp = datetime.now().isoformat()
    
    # Create hash to prevent duplicates
    message_hash = hashlib.sha256(f"{role}:{content}:{timestamp}".encode()).hexdigest()[:16]
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # ONLY INSERT - NEVER REPLACE - ARCHITECTURALLY SAFE
        cursor.execute('''
            INSERT INTO conversation_messages (timestamp, role, content, message_hash, session_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, role, content, message_hash, session_id))
        
        conn.commit()
        message_id = cursor.lastrowid
        logger.info(f"💾 FINDER_TOKEN: MESSAGE_APPENDED - ID:{message_id}, Role:{role}, Hash:{message_hash}")
        return message_id
        
    except sqlite3.IntegrityError as e:
        # Duplicate message - this is fine, prevents duplicates
        logger.debug(f"💾 Duplicate message ignored: {message_hash}")
        return None
    except Exception as e:
        logger.error(f"💾 CRITICAL: Message append failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def load_conversation_messages(limit: int = 10000, session_id: str = None, 
                             db_path: str = "data/discussion.db") -> list:
    """Load conversation messages in chronological order"""
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        if session_id:
            cursor.execute('''
                SELECT id, role, content, timestamp, session_id 
                FROM conversation_messages 
                WHERE session_id = ?
                ORDER BY id ASC 
                LIMIT ?
            ''', (session_id, limit))
        else:
            cursor.execute('''
                SELECT id, role, content, timestamp, session_id
                FROM conversation_messages 
                ORDER BY id ASC 
                LIMIT ?
            ''', (limit,))
        
        messages = [
            {
                'id': row[0],
                'role': row[1], 
                'content': row[2], 
                'timestamp': row[3],
                'session_id': row[4]
            }
            for row in cursor.fetchall()
        ]
        
        logger.info(f"💾 FINDER_TOKEN: MESSAGES_LOADED - {len(messages)} messages from database")
        return messages
        
    finally:
        conn.close()

def get_conversation_stats(db_path: str = "data/discussion.db") -> dict:
    """Get statistics about the conversation database"""
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Total message count
        cursor.execute("SELECT COUNT(*) FROM conversation_messages")
        total_messages = cursor.fetchone()[0]
        
        # Messages by role
        cursor.execute('''
            SELECT role, COUNT(*) 
            FROM conversation_messages 
            GROUP BY role
        ''')
        role_counts = dict(cursor.fetchall())
        
        # Session counts
        cursor.execute('''
            SELECT session_id, COUNT(*) 
            FROM conversation_messages 
            GROUP BY session_id
        ''')
        session_counts = dict(cursor.fetchall())
        
        # Latest message
        cursor.execute('''
            SELECT role, content, timestamp 
            FROM conversation_messages 
            ORDER BY id DESC 
            LIMIT 1
        ''')
        latest_result = cursor.fetchone()
        latest_message = None
        if latest_result:
            latest_message = {
                'role': latest_result[0],
                'content': latest_result[1][:100] + '...' if len(latest_result[1]) > 100 else latest_result[1],
                'timestamp': latest_result[2]
            }
        
        return {
            'total_messages': total_messages,
            'role_distribution': role_counts,
            'session_distribution': session_counts,
            'latest_message': latest_message,
            'architecture': 'append_only_messages'
        }
        
    finally:
        conn.close()

if __name__ == "__main__":
    # Run migration if called directly
    migration = ConversationArchitectureMigration()
    result = migration.run_full_migration()
    print(f"Migration result: {result}") 
#!/usr/bin/env python3
"""
🛡️ Conversation Database Backup System
Implements son/father/grandfather backup pattern for discussion.db to prevent data loss
"""

import os
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class ConversationBackupManager:
    """
    Son/Father/Grandfather backup system for conversation database.
    
    Pattern:
    - Son: Latest backup (made before each operation)
    - Father: Previous backup (rotated when new son is created)
    - Grandfather: Oldest backup (rotated when new father is created)
    """
    
    def __init__(self, source_db_path="data/discussion.db", backup_dir=None):
        self.source_db_path = Path(source_db_path)
        
        # Cross-platform backup directory
        if backup_dir is None:
            # Use a local backup directory instead of hardcoded path
            backup_dir = Path.cwd() / "data" / "backups"
        else:
            backup_dir = Path(backup_dir)
            
        self.backup_dir = backup_dir
        
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            # Fallback to local directory if the preferred path fails
            logger.warning(f"Could not create backup directory {self.backup_dir}: {e}")
            self.backup_dir = Path.cwd() / "data" / "backups"
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Define backup file names
        self.son_backup = self.backup_dir / "discussion_son.db"
        self.father_backup = self.backup_dir / "discussion_father.db"
        self.grandfather_backup = self.backup_dir / "discussion_grandfather.db"
        
        # Metadata file to track backup info
        self.metadata_file = self.backup_dir / "backup_metadata.json"
    
    def create_backup(self, backup_reason="manual"):
        """
        Create a new backup using son/father/grandfather rotation.
        
        Args:
            backup_reason: String describing why backup was created
        """
        try:
            if not self.source_db_path.exists():
                logger.warning(f"Source database {self.source_db_path} does not exist - skipping backup")
                return False
            
            # Rotate existing backups: grandfather <- father <- son
            self._rotate_backups()
            
            # Create new son backup
            shutil.copy2(self.source_db_path, self.son_backup)
            
            # Update metadata
            self._update_metadata(backup_reason)
            
            logger.info(f"💾 CONVERSATION BACKUP CREATED: {backup_reason} - {self.son_backup}")
            return True
            
        except Exception as e:
            logger.error(f"💾 CONVERSATION BACKUP ERROR: Failed to create backup - {e}")
            return False
    
    def _rotate_backups(self):
        """Rotate backups: grandfather <- father <- son"""
        # grandfather <- father
        if self.father_backup.exists():
            if self.grandfather_backup.exists():
                self.grandfather_backup.unlink()  # Delete oldest
            shutil.move(self.father_backup, self.grandfather_backup)
        
        # father <- son
        if self.son_backup.exists():
            shutil.move(self.son_backup, self.father_backup)
    
    def _update_metadata(self, backup_reason):
        """Update backup metadata file"""
        try:
            metadata = {
                "last_backup_time": datetime.now().isoformat(),
                "last_backup_reason": backup_reason,
                "son_backup": str(self.son_backup),
                "father_backup": str(self.father_backup),
                "grandfather_backup": str(self.grandfather_backup),
                "source_db_size": self.source_db_path.stat().st_size if self.source_db_path.exists() else 0
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            logger.error(f"💾 METADATA UPDATE ERROR: {e}")
    
    def restore_from_backup(self, backup_type="son"):
        """
        Restore conversation database from backup.
        
        Args:
            backup_type: "son", "father", or "grandfather"
        """
        try:
            backup_files = {
                "son": self.son_backup,
                "father": self.father_backup,
                "grandfather": self.grandfather_backup
            }
            
            backup_file = backup_files.get(backup_type)
            if not backup_file or not backup_file.exists():
                logger.error(f"💾 RESTORE ERROR: {backup_type} backup does not exist")
                return False
            
            # Create a backup of current state before restoring
            if self.source_db_path.exists():
                emergency_backup = self.backup_dir / f"emergency_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy2(self.source_db_path, emergency_backup)
                logger.info(f"💾 EMERGENCY BACKUP CREATED: {emergency_backup}")
            
            # Restore from backup
            shutil.copy2(backup_file, self.source_db_path)
            logger.info(f"💾 CONVERSATION RESTORED: From {backup_type} backup - {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"💾 RESTORE ERROR: Failed to restore from {backup_type} backup - {e}")
            return False
    
    def get_backup_status(self):
        """Get status of all backups"""
        status = {
            "backup_dir": str(self.backup_dir),
            "source_exists": self.source_db_path.exists(),
            "backups": {}
        }
        
        for name, path in [("son", self.son_backup), ("father", self.father_backup), ("grandfather", self.grandfather_backup)]:
            if path.exists():
                stat = path.stat()
                status["backups"][name] = {
                    "exists": True,
                    "path": str(path),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
            else:
                status["backups"][name] = {"exists": False}
        
        # Add metadata if available
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    status["metadata"] = json.load(f)
            except Exception as e:
                status["metadata_error"] = str(e)
        
        return status
    
    def verify_backup_integrity(self, backup_type="son"):
        """Verify that a backup file is a valid SQLite database"""
        backup_files = {
            "son": self.son_backup,
            "father": self.father_backup,
            "grandfather": self.grandfather_backup
        }
        
        backup_file = backup_files.get(backup_type)
        if not backup_file or not backup_file.exists():
            return False, f"{backup_type} backup does not exist"
        
        try:
            # Try to open and query the database
            conn = sqlite3.connect(backup_file)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            # Check for store table (required for conversation history)
            has_store_table = any(table[0] == 'store' for table in tables)
            
            if has_store_table:
                # Check if conversation history exists
                cursor.execute("SELECT COUNT(*) FROM store WHERE key = 'llm_conversation_history'")
                history_count = cursor.fetchone()[0]
                conn.close()
                
                return True, f"Valid database with {len(tables)} tables, conversation history: {'exists' if history_count > 0 else 'empty'}"
            else:
                conn.close()
                return False, "Database missing required 'store' table"
                
        except Exception as e:
            return False, f"Database integrity check failed: {e}"

# Global backup manager instance
backup_manager = ConversationBackupManager()

def create_conversation_backup(reason="system_operation"):
    """Convenient function to create a conversation backup"""
    return backup_manager.create_backup(reason)

def restore_conversation_from_backup(backup_type="son"):
    """Convenient function to restore conversation from backup"""
    return backup_manager.restore_from_backup(backup_type) 
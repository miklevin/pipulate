"""
🎯 DURABLE DATA BACKUP SYSTEM

Cross-platform backup solution that ensures client data (Profiles, Tasks, AI Keychain)
survives complete Pipulate repo deletion and reinstallation.

Key Features:
- 📁 Cross-platform backup location: ~/.pipulate/backups/
- 🔄 Idempotent backup operations (same file rewritten per time window)
- ⚡ Conflict resolution: Newer wins
- 🗑️ Soft deletes: Mark invisible instead of hard delete
- 🔗 AI Keychain integration for Chip O'Theseus memory persistence
- 📊 Profile & Task table backup with Gantt field preservation

Architecture:
- Backup files: ~/.pipulate/backups/{table_name}_{date_window}.db
- Time windows: Daily granularity for efficiency
- Auto-sync on startup: Restore data after fresh install
"""

import os
import sqlite3
import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger


class DurableBackupManager:
    """
    🎯 Manages durable backups for Pipulate data that survive repo deletion.
    
    Backup Strategy:
    - Daily backup files: ~/.pipulate/backups/{table}_{YYYY-MM-DD}.db
    - Idempotent: Rewrite same day's backup file
    - Conflict Resolution: timestamp_updated wins (newer data preferred)
    - Soft Deletes: Add 'deleted_at' field, filter in queries
    """
    
    def __init__(self, backup_root: Optional[str] = None):
        """Initialize backup manager with cross-platform backup directory."""
        if backup_root:
            self.backup_root = Path(backup_root)
        else:
            # 🎯 Cross-platform: ~/.pipulate/backups/
            home = Path.home()
            self.backup_root = home / '.pipulate' / 'backups'
        
        # Ensure backup directory exists
        self.backup_root.mkdir(parents=True, exist_ok=True)
        logger.info(f"🗃️ Durable backup root: {self.backup_root}")
        
        # Track which tables need backup
        self.backup_tables = {
            'profile': {
                'primary_key': 'id',
                'timestamp_field': 'updated_at',
                'soft_delete_field': 'deleted_at'
            },
            'tasks': {  # From the task plugin
                'primary_key': 'id', 
                'timestamp_field': 'updated_at',
                'soft_delete_field': 'deleted_at'
            }
        }
    
    def get_backup_filename(self, table_name: str, date: Optional[datetime] = None) -> Path:
        """Generate backup filename for table and date."""
        if not date:
            date = datetime.now()
        date_str = date.strftime('%Y-%m-%d')
        return self.backup_root / f"{table_name}_{date_str}.db"
    
    def ensure_soft_delete_schema(self, db_path: str, table_name: str):
        """Ensure table has soft delete fields (updated_at, deleted_at)."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Check if soft delete fields exist
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Use proper SQLite-compatible defaults for ALTER TABLE
            if 'updated_at' not in columns:
                # SQLite ALTER TABLE requires constant defaults, not functions
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN updated_at TEXT DEFAULT ''")
                logger.info(f"✅ Added updated_at to {table_name}")
            
            if 'deleted_at' not in columns:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN deleted_at TEXT DEFAULT NULL")
                logger.info(f"✅ Added deleted_at to {table_name}")
                
            conn.commit()
        except Exception as e:
            logger.error(f"❌ Error adding soft delete fields to {table_name}: {e}")
        finally:
            conn.close()
    

    
    def backup_table(self, source_db_path: str, table_name: str) -> bool:
        """
        📁 Backup a table to the durable storage.
        
        Returns True if backup successful, False otherwise.
        """
        try:
            # Get today's backup file
            backup_file = self.get_backup_filename(table_name)
            
            # Create backup database if it doesn't exist
            if not backup_file.exists():
                # Copy entire database structure first time
                shutil.copy2(source_db_path, backup_file)
                logger.info(f"🎯 Created initial backup: {backup_file}")
                return True
            
            # 🎯 SIMPLE UNIDIRECTIONAL BACKUP - No complex merge logic
            return self._simple_unidirectional_backup(source_db_path, backup_file, table_name)
        
        except Exception as e:
            logger.error(f"❌ Backup failed for {table_name}: {e}")
            return False
    
    def _simple_unidirectional_backup(self, source_db_path: str, backup_db: Path, table_name: str) -> bool:
        """
        📋 Simple unidirectional backup - just copy current data to backup.
        
        No merge logic, no conflict resolution - just a snapshot backup.
        """
        source_conn = sqlite3.connect(source_db_path)
        backup_conn = sqlite3.connect(str(backup_db))
        
        try:
            # Get current records from source
            source_cursor = source_conn.cursor()
            source_cursor.execute(f"SELECT * FROM {table_name}")
            source_rows = source_cursor.fetchall()
            
            # Get column names
            source_cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in source_cursor.fetchall()]
            
            # Clear and repopulate backup table (snapshot backup)
            backup_cursor = backup_conn.cursor()
            backup_cursor.execute(f"DELETE FROM {table_name}")
            
            # Insert all current records from source
            if source_rows:
                placeholders = ', '.join(['?' for _ in columns])
                backup_cursor.executemany(
                    f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})",
                    source_rows
                )
            
            backup_conn.commit()
            logger.info(f"✅ Successfully backed up {table_name} ({len(source_rows)} records)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Simple backup failed for {table_name}: {e}")
            return False
        finally:
            source_conn.close()
            backup_conn.close()
    
    
    




    def auto_backup_all(self, main_db_path: str, keychain_db_path: str, discussion_db_path: str = "data/discussion.db") -> Dict[str, bool]:
        """
        🚀 Perform complete backup of all durable data.
        
        Files are backed up with their original names so they can be manually 
        dragged back into place for restoration.
        """
        results = {}
        
        # 🎯 SIMPLE FILE COPY BACKUP - Original filenames for easy manual restore
        try:
            # Backup main database with original filename
            main_backup_file = self.backup_root / "data.db"
            
            if os.path.exists(main_db_path):
                # Log current database state before backup
                logger.info(f"🔍 BACKUP DEBUG: About to backup {main_db_path} to {main_backup_file}")
                logger.info(f"🔍 BACKUP DEBUG: Source file size: {os.path.getsize(main_db_path)} bytes")
                logger.info(f"🔍 BACKUP DEBUG: Source file modified: {datetime.fromtimestamp(os.path.getmtime(main_db_path))}")
                
                # Simple file copy with original filename
                shutil.copy2(main_db_path, main_backup_file)
                logger.info(f"✅ Main database backed up to: {main_backup_file}")
                results['data.db'] = True
            else:
                logger.warning(f"⚠️ Main database not found at {main_db_path}")
                results['data.db'] = False
        
        except Exception as e:
            logger.error(f"❌ Main database backup failed: {e}")
            results['data.db'] = False
        
        # Backup AI keychain with original filename
        try:
            if os.path.exists(keychain_db_path):
                keychain_backup_file = self.backup_root / "ai_keychain.db"
                shutil.copy2(keychain_db_path, keychain_backup_file)
                logger.info(f"🧠 AI Keychain backed up to: {keychain_backup_file}")
                results['ai_keychain.db'] = True
            else:
                logger.warning(f"⚠️ AI keychain not found at {keychain_db_path}")
                results['ai_keychain.db'] = False
        except Exception as e:
            logger.error(f"❌ AI Keychain backup failed: {e}")
            results['ai_keychain.db'] = False
        
        # Backup discussion database with original filename
        try:
            if os.path.exists(discussion_db_path):
                discussion_backup_file = self.backup_root / "discussion.db"
                shutil.copy2(discussion_db_path, discussion_backup_file)
                logger.info(f"💬 Discussion database backed up to: {discussion_backup_file}")
                results['discussion.db'] = True
            else:
                logger.warning(f"⚠️ Discussion database not found at {discussion_db_path}")
                results['discussion.db'] = False
        except Exception as e:
            logger.error(f"❌ Discussion database backup failed: {e}")
            results['discussion.db'] = False
        
        successful_backups = sum(1 for success in results.values() if success)
        total = len(results)
        logger.info(f"🎯 Simple file backup complete: {successful_backups}/{total} successful")
        logger.info(f"🔍 BACKUP DEBUG: Backup results: {results}")
        logger.info(f"📁 BACKUP LOCATION: {self.backup_root} - Files can be manually dragged back to restore")
        
        return results


    
    def cleanup_old_backups(self, keep_days: int = 30):
        """
        🧹 Clean up backup files older than specified days.
        """
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        for backup_file in self.backup_root.glob("*.db"):
            try:
                # Extract date from filename
                name_parts = backup_file.stem.split('_')
                if len(name_parts) >= 2:
                    date_str = name_parts[-1]  # Last part should be YYYY-MM-DD
                    file_date = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    if file_date < cutoff_date:
                        backup_file.unlink()
                        logger.info(f"🧹 Cleaned up old backup: {backup_file}")
                        
            except (ValueError, IndexError) as e:
                logger.warning(f"⚠️ Could not parse backup file date: {backup_file}")
    
    def get_backup_counts(self) -> Dict[str, int]:
        """
        📊 Get counts of records in backup files for clear UI labeling.
        
        Returns dict like: {'profile': 5, 'tasks': 23, 'ai_keychain': 1}
        """
        counts = {}
        
        for table_name in self.backup_tables.keys():
            backup_file = self.get_backup_filename(table_name)
            if backup_file.exists():
                try:
                    conn = sqlite3.connect(str(backup_file))
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    counts[table_name] = cursor.fetchone()[0]
                    conn.close()
                except Exception as e:
                    logger.warning(f"⚠️ Could not count {table_name} in backup: {e}")
                    counts[table_name] = 0
            else:
                counts[table_name] = 0
        
        # Add AI keychain count
        keychain_backup = self.backup_root / f"ai_keychain_{datetime.now().strftime('%Y-%m-%d')}.db"
        if keychain_backup.exists():
            counts['ai_keychain'] = 1  # Keychain is just one file
        else:
            counts['ai_keychain'] = 0
            
        return counts
    
    def get_current_db_counts(self, main_db_path: str) -> Dict[str, int]:
        """
        📊 Get counts of records in current database for clear UI labeling.
        
        Returns dict like: {'profile': 1, 'tasks': 0, 'ai_keychain': 1}
        """
        counts = {}
        
        try:
            conn = sqlite3.connect(main_db_path)
            cursor = conn.cursor()
            
            for table_name in self.backup_tables.keys():
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    counts[table_name] = cursor.fetchone()[0]
                except Exception as e:
                    logger.warning(f"⚠️ Could not count {table_name} in current DB: {e}")
                    counts[table_name] = 0
            
            conn.close()
        except Exception as e:
            logger.error(f"❌ Could not access current database: {e}")
            for table_name in self.backup_tables.keys():
                counts[table_name] = 0
        
        # AI keychain is separate file
        counts['ai_keychain'] = 1 if os.path.exists('data/ai_keychain.db') else 0
        
        return counts


# 🎯 GLOBAL INSTANCE for easy import
backup_manager = DurableBackupManager() 
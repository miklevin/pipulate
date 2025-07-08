"""
🎯 DURABLE DATA BACKUP SYSTEM

Cross-platform backup solution that ensures client data (Profiles, Tasks, AI Keychain)
survives complete Pipulate repo deletion and reinstallation.

Key Features:
- 📁 Cross-platform backup location: ~/.pipulate/backups/
- 🗓️ Son/Father/Grandfather backup strategy with original filenames
- ⚡ Daily (Son): 7 days retention - Triggered on every server startup
- 📅 Weekly (Father): 4 weeks retention - For future implementation  
- 🗓️ Monthly (Grandfather): 12 months retention - For future implementation
- 🔗 AI Keychain integration for Chip O'Theseus memory persistence
- 📊 Profile & Task table backup with Gantt field preservation

Architecture:
- Latest backups: ~/.pipulate/backups/{original_filename}.db
- Dated backups: ~/.pipulate/backups/{original_filename}_{YYYY-MM-DD}.db
- Time windows: Daily granularity for efficiency
- Auto-sync on startup: Manual restore by drag-and-drop
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
    
    Son/Father/Grandfather Backup Strategy:
    - Latest: ~/.pipulate/backups/{original_filename}.db (always current)
    - Daily (Son): ~/.pipulate/backups/{original_filename}_{YYYY-MM-DD}.db (7 days retention)
    - Weekly (Father): Future implementation (4 weeks retention)
    - Monthly (Grandfather): Future implementation (12 months retention)
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

    def get_original_filename(self, source_path: str) -> str:
        """Extract original filename from source path."""
        return Path(source_path).name
    
    def get_dated_filename(self, original_filename: str, date: Optional[datetime] = None) -> str:
        """Generate dated filename: original_name_YYYY-MM-DD.db"""
        if not date:
            date = datetime.now()
        
        # Split filename and extension
        name_part = Path(original_filename).stem
        ext_part = Path(original_filename).suffix
        
        date_str = date.strftime('%Y-%m-%d')
        return f"{name_part}_{date_str}{ext_part}"
    
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
        🚀 Son/Father/Grandfather backup strategy.
        
        For each database file:
        1. Create/update latest backup with original filename
        2. Create dated backup for daily (son) retention
        3. Clean up old daily backups (7-day retention)
        
        Directory structure:
        ~/.pipulate/backups/
        ├── pipulate.db (latest)
        ├── pipulate_2025-01-08.db (dated)
        ├── ai_keychain.db (latest)
        ├── ai_keychain_2025-01-08.db (dated)
        ├── discussion.db (latest)
        └── discussion_2025-01-08.db (dated)
        """
        results = {}
        backup_date = datetime.now()
        
        # Database files to backup
        backup_files = [
            (main_db_path, "Main database"),
            (keychain_db_path, "AI Keychain"), 
            (discussion_db_path, "Discussion database")
        ]
        
        for source_path, description in backup_files:
            try:
                if not os.path.exists(source_path):
                    logger.warning(f"⚠️ {description} not found at {source_path}")
                    results[source_path] = False
                    continue
                
                # Get original filename and create backup paths
                original_filename = self.get_original_filename(source_path)
                latest_backup_path = self.backup_root / original_filename
                dated_backup_path = self.backup_root / self.get_dated_filename(original_filename, backup_date)
                
                # Log current database state before backup
                logger.info(f"🔍 BACKUP DEBUG: About to backup {source_path}")
                logger.info(f"🔍 BACKUP DEBUG: Source file size: {os.path.getsize(source_path)} bytes")
                logger.info(f"🔍 BACKUP DEBUG: Source file modified: {datetime.fromtimestamp(os.path.getmtime(source_path))}")
                
                # 1. Create/update latest backup (original filename)
                shutil.copy2(source_path, latest_backup_path)
                logger.info(f"✅ {description} latest backup: {latest_backup_path}")
                
                # 2. Create dated backup (only if it doesn't exist for today)
                if not dated_backup_path.exists():
                    shutil.copy2(source_path, dated_backup_path)
                    logger.info(f"📅 {description} dated backup: {dated_backup_path}")
                else:
                    logger.info(f"📅 {description} dated backup already exists for today: {dated_backup_path}")
                
                results[source_path] = True
                
            except Exception as e:
                logger.error(f"❌ {description} backup failed: {e}")
                results[source_path] = False
        
        # 3. Clean up old daily (son) backups - 7 day retention
        self.cleanup_daily_backups(keep_days=7)
        
        successful_backups = sum(1 for success in results.values() if success)
        total = len(results)
        logger.info(f"🎯 Son/Father/Grandfather backup complete: {successful_backups}/{total} successful")
        logger.info(f"🔍 BACKUP DEBUG: Backup results: {results}")
        logger.info(f"📁 BACKUP LOCATION: {self.backup_root}")
        logger.info(f"📋 RESTORE INFO: Drag-and-drop files from backup directory to restore manually")
        
        return results

    def cleanup_daily_backups(self, keep_days: int = 7):
        """
        🧹 Clean up daily (son) backup files older than specified days.
        
        Removes only dated files (filename_YYYY-MM-DD.db), preserves latest files.
        """
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        for backup_file in self.backup_root.glob("*_????-??-??.db"):
            try:
                # Extract date from filename (last 10 characters before .db)
                filename = backup_file.stem
                if len(filename) >= 10:
                    date_str = filename[-10:]  # Last 10 chars should be YYYY-MM-DD
                    try:
                        file_date = datetime.strptime(date_str, '%Y-%m-%d')
                        
                        if file_date < cutoff_date:
                            backup_file.unlink()
                            logger.info(f"🧹 Cleaned up old daily backup: {backup_file}")
                    except ValueError:
                        # Not a valid date format, skip
                        continue
                        
            except Exception as e:
                logger.warning(f"⚠️ Error cleaning backup file {backup_file}: {e}")
    
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
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
    
    def _table_has_backup_fields(self, db_path: str, table_name: str) -> bool:
        """Check if table has backup timestamp fields."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]
            return 'updated_at' in columns
        except Exception:
            return False
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
            
            # Check if table has backup fields for advanced merge
            if self._table_has_backup_fields(source_db_path, table_name):
                # Advanced merge with conflict resolution
                return self._merge_table_data(source_db_path, backup_file, table_name)
            else:
                # Basic backup: simple table copy for tables without backup fields
                return self._basic_table_backup(source_db_path, backup_file, table_name)
            
        except Exception as e:
            logger.error(f"❌ Backup failed for {table_name}: {e}")
            return False
    
    def _basic_table_backup(self, source_db_path: str, backup_db: Path, table_name: str) -> bool:
        """
        📋 Basic table backup without timestamp-based conflict resolution.
        
        Used for tables that don't have backup fields yet.
        """
        source_conn = sqlite3.connect(source_db_path)
        backup_conn = sqlite3.connect(str(backup_db))
        
        try:
            # Get table config
            table_config = self.backup_tables.get(table_name, {})
            pk_field = table_config.get('primary_key', 'id')
            
            # Clear and repopulate backup table (simple strategy)
            backup_cursor = backup_conn.cursor()
            backup_cursor.execute(f"DELETE FROM {table_name}")
            
            # Copy all current records from source
            source_cursor = source_conn.cursor()
            source_cursor.execute(f"SELECT * FROM {table_name}")
            source_rows = source_cursor.fetchall()
            
            # Get column names
            source_cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in source_cursor.fetchall()]
            
            # Insert all records
            if source_rows:
                placeholders = ', '.join(['?' for _ in columns])
                backup_cursor.executemany(
                    f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})",
                    source_rows
                )
            
            backup_conn.commit()
            logger.info(f"✅ Successfully backed up {table_name} (basic mode: {len(source_rows)} records)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Basic backup failed for {table_name}: {e}")
            return False
        finally:
            source_conn.close()
            backup_conn.close()
    
    def _merge_table_data(self, source_db: str, backup_db: Path, table_name: str) -> bool:
        """
        🔄 Merge table data using conflict resolution: newer updated_at wins.
        
        Only called for tables that have backup fields.
        """
        source_conn = sqlite3.connect(source_db)
        backup_conn = sqlite3.connect(str(backup_db))
        
        try:
            # Get table config
            table_config = self.backup_tables.get(table_name, {})
            pk_field = table_config.get('primary_key', 'id')
            timestamp_field = table_config.get('timestamp_field', 'updated_at')
            
            # Get column names first
            source_cursor = source_conn.cursor()
            source_cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in source_cursor.fetchall()]
            
            # Safety check: ensure timestamp field exists
            if timestamp_field not in columns:
                logger.warning(f"⚠️ Timestamp field {timestamp_field} not found in {table_name}, falling back to basic backup")
                return self._basic_table_backup(source_db, backup_db, table_name)
            
            # Get all records from source (including soft-deleted)
            source_cursor.execute(f"SELECT * FROM {table_name}")
            source_rows = source_cursor.fetchall()
            
            # Merge each record
            backup_cursor = backup_conn.cursor()
            for row in source_rows:
                row_dict = dict(zip(columns, row))
                pk_value = row_dict[pk_field]
                source_timestamp = row_dict.get(timestamp_field, '')
                
                # Check if record exists in backup
                backup_cursor.execute(
                    f"SELECT {timestamp_field} FROM {table_name} WHERE {pk_field} = ?", 
                    (pk_value,)
                )
                backup_result = backup_cursor.fetchone()
                
                if not backup_result:
                    # New record - insert
                    placeholders = ', '.join(['?' for _ in columns])
                    backup_cursor.execute(
                        f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})",
                        row
                    )
                    logger.debug(f"📝 Inserted new record {pk_value} into backup")
                else:
                    backup_timestamp = backup_result[0]
                    # 🎯 CONFLICT RESOLUTION: Newer timestamp wins
                    if source_timestamp > backup_timestamp:
                        # Update backup with newer source data
                        set_clause = ', '.join([f"{col} = ?" for col in columns if col != pk_field])
                        values = [row_dict[col] for col in columns if col != pk_field]
                        backup_cursor.execute(
                            f"UPDATE {table_name} SET {set_clause} WHERE {pk_field} = ?",
                            values + [pk_value]
                        )
                        logger.debug(f"🔄 Updated record {pk_value} with newer data")
            
            backup_conn.commit()
            logger.info(f"✅ Successfully merged {table_name} data to backup")
            return True
            
        except Exception as e:
            logger.error(f"❌ Merge failed for {table_name}: {e}")
            return False
        finally:
            source_conn.close()
            backup_conn.close()
    
    def restore_table(self, target_db_path: str, table_name: str) -> bool:
        """
        🔄 Restore table from backup to current database.
        
        Used during fresh installs to restore client data.
        """
        try:
            backup_file = self.get_backup_filename(table_name)
            if not backup_file.exists():
                logger.warning(f"⚠️ No backup found for {table_name}")
                return False
            
            # Ensure target has soft delete schema
            self.ensure_soft_delete_schema(target_db_path, table_name)
            
            # Merge backup data into target (backup is source of truth)
            return self._merge_table_data(str(backup_file), Path(target_db_path), table_name)
            
        except Exception as e:
            logger.error(f"❌ Restore failed for {table_name}: {e}")
            return False
    
    def backup_ai_keychain(self, keychain_db_path: str) -> bool:
        """
        🧠 Backup Chip O'Theseus AI Keychain for memory persistence.
        """
        try:
            backup_file = self.backup_root / f"ai_keychain_{datetime.now().strftime('%Y-%m-%d')}.db"
            
            if backup_file.exists():
                # Merge keychain data (keychain has its own conflict resolution)
                logger.info(f"🧠 Merging AI keychain to existing backup")
                shutil.copy2(keychain_db_path, backup_file)
            else:
                # Initial backup
                shutil.copy2(keychain_db_path, backup_file)
                logger.info(f"🧠 Created AI keychain backup: {backup_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ AI Keychain backup failed: {e}")
            return False
    
    def restore_ai_keychain(self, target_keychain_path: str) -> bool:
        """
        🧠 Restore Chip O'Theseus AI Keychain from backup.
        """
        try:
            backup_file = self.backup_root / f"ai_keychain_{datetime.now().strftime('%Y-%m-%d')}.db"
            if not backup_file.exists():
                # Try yesterday's backup
                yesterday = datetime.now() - timedelta(days=1)
                backup_file = self.backup_root / f"ai_keychain_{yesterday.strftime('%Y-%m-%d')}.db"
            
            if backup_file.exists():
                shutil.copy2(backup_file, target_keychain_path)
                logger.info(f"🧠 Restored AI keychain from: {backup_file}")
                return True
            else:
                logger.warning("⚠️ No AI keychain backup found")
                return False
                
        except Exception as e:
            logger.error(f"❌ AI Keychain restore failed: {e}")
            return False
    
    def auto_backup_all(self, main_db_path: str, keychain_db_path: str) -> Dict[str, bool]:
        """
        🚀 Perform complete backup of all durable data.
        
        Called periodically to ensure data durability.
        """
        results = {}
        
        # Backup main tables
        for table_name in self.backup_tables.keys():
            results[table_name] = self.backup_table(main_db_path, table_name)
        
        # Backup AI keychain
        if os.path.exists(keychain_db_path):
            results['ai_keychain'] = self.backup_ai_keychain(keychain_db_path)
        
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        logger.info(f"🎯 Auto-backup complete: {successful}/{total} successful")
        
        return results
    
    def auto_restore_all(self, main_db_path: str, keychain_db_path: str) -> Dict[str, bool]:
        """
        🔄 Restore all data from backups.
        
        Called on fresh installs to restore client data.
        """
        results = {}
        
        # Restore main tables
        for table_name in self.backup_tables.keys():
            results[table_name] = self.restore_table(main_db_path, table_name)
        
        # Restore AI keychain
        results['ai_keychain'] = self.restore_ai_keychain(keychain_db_path)
        
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        logger.info(f"🔄 Auto-restore complete: {successful}/{total} successful")
        
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
    
    def explicit_backup_all(self, main_db_path: str, keychain_db_path: str) -> Dict[str, bool]:
        """
        📤 EXPLICIT BACKUP: Save current database state TO backup files.
        
        This OVERWRITES backup files with current data. No restore logic.
        Use when you want to save your current work.
        """
        results = {}
        
        # Backup main tables
        for table_name in self.backup_tables.keys():
            results[table_name] = self.backup_table(main_db_path, table_name)
        
        # Backup AI keychain
        if os.path.exists(keychain_db_path):
            results['ai_keychain'] = self.backup_ai_keychain(keychain_db_path)
        
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        logger.info(f"📤 Explicit backup complete: {successful}/{total} successful")
        
        return results
    
    def explicit_restore_all(self, main_db_path: str, keychain_db_path: str) -> Dict[str, bool]:
        """
        📥 EXPLICIT RESTORE: Load backup data INTO current database.
        
        This OVERWRITES current data with backup. No backup logic.
        Use when you want to restore from a previous backup.
        """
        results = {}
        
        # Restore main tables
        for table_name in self.backup_tables.keys():
            results[table_name] = self.restore_table(main_db_path, table_name)
        
        # Restore AI keychain
        results['ai_keychain'] = self.restore_ai_keychain(keychain_db_path)
        
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        logger.info(f"📥 Explicit restore complete: {successful}/{total} successful")
        
        return results


# 🎯 GLOBAL INSTANCE for easy import
backup_manager = DurableBackupManager() 
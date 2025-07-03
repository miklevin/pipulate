"""
🎯 DURABLE DATA BACKUP SYSTEM - REVOLUTIONARY EDITION

Cross-platform backup solution that ensures client data (Profiles, Tasks, AI Keychain)
survives complete Pipulate repo deletion and reinstallation.

🔥 REVOLUTIONARY FEATURES:
- 📁 Date-hierarchical structure: ~/.pipulate/backups/YYYY/MM/DD/{table}.db
- 🚫 NEVER overwrites - each day gets its own backup directory
- 🔍 Intelligent cleanup: 7 daily, 4 weekly (Sundays), 12 monthly (1st) retention
- 📊 Enhanced return values: Record counts instead of boolean flags
- ⚡ Automatic cleanup after each backup operation
- 🔗 AI Keychain integration for Chip O'Theseus memory persistence
- 📈 Gantt field preservation for professional client work

Architecture Evolution:
- OLD: ~/.pipulate/backups/{table}_{date}.db (flat, overwrites)
- NEW: ~/.pipulate/backups/YYYY/MM/DD/{table}.db (hierarchical, preserves history)
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
    🎯 Revolutionary backup manager that creates a comprehensive data archeology system.
    
    NEW Backup Strategy:
    - Hierarchical structure: ~/.pipulate/backups/YYYY/MM/DD/{table}.db
    - Never overwrites: Each day gets its own directory
    - Intelligent retention: Strategic cleanup preserving key snapshots
    - Record counting: Functions return actual record counts for UI feedback
    """
    
    def __init__(self, backup_root: Optional[str] = None):
        """Initialize backup manager with revolutionary hierarchical directory structure."""
        if backup_root:
            self.backup_root = Path(backup_root)
        else:
            # 🎯 Cross-platform: ~/.pipulate/backups/
            home = Path.home()
            self.backup_root = home / '.pipulate' / 'backups'
        
        # Ensure backup directory exists
        self.backup_root.mkdir(parents=True, exist_ok=True)
        logger.info(f"🗃️ Revolutionary backup root: {self.backup_root}")
        
        # Track which tables need backup
        self.backup_tables = {
            'profile': {
                'primary_key': 'id',
                'timestamp_field': 'updated_at',
                'soft_delete_field': 'deleted_at'
            },
            'tasks': {  # From the task plugin with Gantt fields
                'primary_key': 'id', 
                'timestamp_field': 'updated_at',
                'soft_delete_field': 'deleted_at'
            }
        }
    
    def get_backup_path(self, table_name: str, date: Optional[datetime] = None) -> Path:
        """
        🔥 REVOLUTIONARY: Generate hierarchical backup path YYYY/MM/DD/{table}.db
        
        This creates a date-hierarchical structure that never overwrites and
        enables sophisticated cleanup strategies.
        """
        if not date:
            date = datetime.now()
        
        # Create YYYY/MM/DD directory structure
        year_dir = self.backup_root / f"{date.year:04d}"
        month_dir = year_dir / f"{date.month:02d}"
        day_dir = month_dir / f"{date.day:02d}"
        
        # Ensure directory exists
        day_dir.mkdir(parents=True, exist_ok=True)
        
        return day_dir / f"{table_name}.db"
    
    def _get_latest_backup_path(self, table_name: str) -> Optional[Path]:
        """
        🔍 Find the most recent backup file across all dates.
        
        Searches the hierarchical structure to find the latest backup.
        """
        if not self.backup_root.exists():
            return None
        
        latest_date = None
        latest_path = None
        
        # Search through YYYY directories
        for year_dir in sorted(self.backup_root.iterdir(), reverse=True):
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue
                
            # Search through MM directories
            for month_dir in sorted(year_dir.iterdir(), reverse=True):
                if not month_dir.is_dir() or not month_dir.name.isdigit():
                    continue
                    
                # Search through DD directories
                for day_dir in sorted(month_dir.iterdir(), reverse=True):
                    if not day_dir.is_dir() or not day_dir.name.isdigit():
                        continue
                    
                    backup_file = day_dir / f"{table_name}.db"
                    if backup_file.exists():
                        # Parse date for comparison
                        try:
                            year = int(year_dir.name)
                            month = int(month_dir.name)
                            day = int(day_dir.name)
                            file_date = datetime(year, month, day)
                            
                            if latest_date is None or file_date > latest_date:
                                latest_date = file_date
                                latest_path = backup_file
                        except ValueError:
                            continue
        
        return latest_path
    
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
    
    def backup_table(self, source_db_path: str, table_name: str) -> int:
        """
        🔥 REVOLUTIONARY: Backup table to hierarchical structure and return record count.
        
        Returns number of records backed up (0 if failed).
        """
        try:
            # Get today's backup path (hierarchical)
            backup_file = self.get_backup_path(table_name)
            
            # Create backup database if it doesn't exist
            if not backup_file.exists():
                # Copy entire database structure first time
                shutil.copy2(source_db_path, backup_file)
                
                # Count records in the backup
                record_count = self._count_table_records(str(backup_file), table_name)
                relative_path = backup_file.relative_to(self.backup_root)
                logger.info(f"🎯 Created initial backup: {relative_path} ({record_count} records)")
                return record_count
            
            # Check if table has backup fields for advanced merge
            if self._table_has_backup_fields(source_db_path, table_name):
                # Advanced merge with conflict resolution
                return self._merge_table_data(source_db_path, backup_file, table_name)
            else:
                # Basic backup: simple table copy for tables without backup fields
                return self._basic_table_backup(source_db_path, backup_file, table_name)
            
        except Exception as e:
            logger.error(f"❌ Backup failed for {table_name}: {e}")
            return 0
    
    def _count_table_records(self, db_path: str, table_name: str) -> int:
        """Count records in a table."""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0
    
    def _basic_table_backup(self, source_db_path: str, backup_db: Path, table_name: str) -> int:
        """
        📋 Basic table backup returning record count.
        
        Used for tables that don't have backup fields yet.
        """
        source_conn = sqlite3.connect(source_db_path)
        backup_conn = sqlite3.connect(str(backup_db))
        
        try:
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
            relative_path = backup_db.relative_to(self.backup_root)
            logger.info(f"✅ Basic backup: {relative_path} ({len(source_rows)} records)")
            return len(source_rows)
            
        except Exception as e:
            logger.error(f"❌ Basic backup failed for {table_name}: {e}")
            return 0
        finally:
            source_conn.close()
            backup_conn.close()
    
    def _merge_table_data(self, source_db: str, backup_db: Path, table_name: str) -> int:
        """
        🔄 Merge table data with conflict resolution, return record count.
        
        Only called for tables that have backup fields.
        """
        source_conn = sqlite3.connect(source_db)
        backup_conn = sqlite3.connect(str(backup_db))
        
        try:
            table_config = self.backup_tables.get(table_name, {})
            pk_field = table_config.get('primary_key', 'id')
            timestamp_field = table_config.get('timestamp_field', 'updated_at')
            
            # Get all source data
            source_cursor = source_conn.cursor()
            source_cursor.execute(f"SELECT * FROM {table_name}")
            source_rows = source_cursor.fetchall()
            
            # Get column names
            source_cursor.execute(f"PRAGMA table_info({table_name})")
            column_info = source_cursor.fetchall()
            columns = [col[1] for col in column_info]
            
            # Build column mapping
            pk_index = columns.index(pk_field) if pk_field in columns else 0
            timestamp_index = columns.index(timestamp_field) if timestamp_field in columns else None
            
            backup_cursor = backup_conn.cursor()
            records_processed = 0
            
            for row in source_rows:
                pk_value = row[pk_index]
                
                if timestamp_index is not None:
                    # Conflict resolution: check if backup has newer data
                    backup_cursor.execute(
                        f"SELECT {timestamp_field} FROM {table_name} WHERE {pk_field} = ?",
                        (pk_value,)
                    )
                    backup_row = backup_cursor.fetchone()
                    
                    if backup_row and backup_row[0] > row[timestamp_index]:
                        # Backup has newer data, skip this record
                        continue
                
                # Insert or replace record
                placeholders = ', '.join(['?' for _ in columns])
                backup_cursor.execute(
                    f"INSERT OR REPLACE INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})",
                    row
                )
                records_processed += 1
            
            backup_conn.commit()
            
            # Get final count
            final_count = self._count_table_records(str(backup_db), table_name)
            relative_path = backup_db.relative_to(self.backup_root)
            logger.info(f"🔄 Advanced merge: {relative_path} (processed {records_processed}, total {final_count})")
            return final_count
            
        except Exception as e:
            logger.error(f"❌ Advanced merge failed for {table_name}: {e}")
            return 0
        finally:
            source_conn.close()
            backup_conn.close()
    
    def restore_table(self, target_db_path: str, table_name: str) -> int:
        """
        📥 Restore table from most recent backup, return record count.
        
        Finds the latest backup across the hierarchical structure.
        """
        try:
            # Find the most recent backup
            latest_backup = self._get_latest_backup_path(table_name)
            if not latest_backup or not latest_backup.exists():
                logger.warning(f"⚠️ No backup found for {table_name}")
                return 0
            
            # Check if table has backup fields for advanced merge
            if self._table_has_backup_fields(target_db_path, table_name):
                return self._merge_table_data(str(latest_backup), Path(target_db_path), table_name)
            else:
                return self._basic_table_restore(str(latest_backup), target_db_path, table_name)
            
        except Exception as e:
            logger.error(f"❌ Restore failed for {table_name}: {e}")
            return 0
    
    def _basic_table_restore(self, backup_db_path: str, target_db_path: str, table_name: str) -> int:
        """Basic table restore returning record count."""
        backup_conn = sqlite3.connect(backup_db_path)
        target_conn = sqlite3.connect(target_db_path)
        
        try:
            # Get all backup data
            backup_cursor = backup_conn.cursor()
            backup_cursor.execute(f"SELECT * FROM {table_name}")
            backup_rows = backup_cursor.fetchall()
            
            # Get column names
            backup_cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in backup_cursor.fetchall()]
            
            # Clear target and restore from backup
            target_cursor = target_conn.cursor()
            target_cursor.execute(f"DELETE FROM {table_name}")
            
            if backup_rows:
                placeholders = ', '.join(['?' for _ in columns])
                target_cursor.executemany(
                    f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})",
                    backup_rows
                )
            
            target_conn.commit()
            
            relative_path = Path(backup_db_path).relative_to(self.backup_root)
            logger.info(f"📥 Basic restore: {relative_path} ({len(backup_rows)} records)")
            return len(backup_rows)
            
        except Exception as e:
            logger.error(f"❌ Basic restore failed for {table_name}: {e}")
            return 0
        finally:
            backup_conn.close()
            target_conn.close()
    
    def backup_ai_keychain(self, keychain_db_path: str) -> int:
        """
        🧠 Backup AI Keychain with hierarchical structure, return record count.
        
        Preserves Chip O'Theseus memory across complete system reinstalls.
        """
        try:
            if not Path(keychain_db_path).exists():
                logger.info("🧠 No AI Keychain found to backup")
                return 0
            
            # Get today's backup path for AI keychain
            backup_file = self.get_backup_path('ai_keychain')
            
            # Copy the entire keychain database
            shutil.copy2(keychain_db_path, backup_file)
            
            # Count total key-value pairs
            conn = sqlite3.connect(str(backup_file))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            total_records = 0
            for table_row in tables:
                table_name = table_row[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                total_records += count
            
            conn.close()
            
            relative_path = backup_file.relative_to(self.backup_root)
            logger.info(f"🧠 AI Keychain backup: {relative_path} ({total_records} total records)")
            return total_records
            
        except Exception as e:
            logger.error(f"❌ AI Keychain backup failed: {e}")
            return 0
    
    def restore_ai_keychain(self, target_keychain_path: str) -> int:
        """
        🧠 Restore AI Keychain from most recent backup, return record count.
        
        Restores Chip O'Theseus memory from hierarchical backup structure.
        """
        try:
            # Find the most recent keychain backup
            latest_backup = self._get_latest_backup_path('ai_keychain')
            if not latest_backup or not latest_backup.exists():
                logger.info("🧠 No AI Keychain backup found")
                return 0
            
            # Ensure target directory exists
            Path(target_keychain_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Copy backup to target location
            shutil.copy2(latest_backup, target_keychain_path)
            
            # Count records
            conn = sqlite3.connect(target_keychain_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            total_records = 0
            for table_row in tables:
                table_name = table_row[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                total_records += count
            
            conn.close()
            
            relative_path = latest_backup.relative_to(self.backup_root)
            logger.info(f"🧠 AI Keychain restore: {relative_path} ({total_records} total records)")
            return total_records
            
        except Exception as e:
            logger.error(f"❌ AI Keychain restore failed: {e}")
            return 0
    
    def auto_backup_all(self, main_db_path: str, keychain_db_path: str) -> Dict[str, int]:
        """
        🔄 Automatic backup of all tables with cleanup, return record counts.
        
        Called by server on startup and periodically.
        """
        results = {}
        
        # Backup main tables
        for table_name in self.backup_tables.keys():
            results[table_name] = self.backup_table(main_db_path, table_name)
        
        # Backup AI keychain
        results['ai_keychain'] = self.backup_ai_keychain(keychain_db_path)
        
        # Automatic cleanup after backup
        self.cleanup_old_backups()
        
        successful = sum(1 for count in results.values() if count > 0)
        total_records = sum(results.values())
        logger.info(f"🔄 Auto backup complete: {successful}/{len(results)} tables, {total_records} total records")
        
        return results
    
    def auto_restore_all(self, main_db_path: str, keychain_db_path: str) -> Dict[str, int]:
        """
        📥 Automatic restore of all tables, return record counts.
        
        Called by server on startup after fresh install.
        """
        results = {}
        
        # Restore main tables
        for table_name in self.backup_tables.keys():
            results[table_name] = self.restore_table(main_db_path, table_name)
        
        # Restore AI keychain
        results['ai_keychain'] = self.restore_ai_keychain(keychain_db_path)
        
        successful = sum(1 for count in results.values() if count > 0)
        total_records = sum(results.values())
        logger.info(f"📥 Auto restore complete: {successful}/{len(results)} tables, {total_records} total records")
        
        return results
    
    def cleanup_old_backups(self):
        """
        🔥 REVOLUTIONARY: Intelligent cleanup with sophisticated retention policy.
        
        Retention Strategy:
        - Keep last 7 daily backups
        - Keep last 4 weekly backups (Sundays)  
        - Keep last 12 monthly backups (1st of month)
        - Delete everything else
        """
        try:
            if not self.backup_root.exists():
                return
            
            today = datetime.now()
            files_to_delete = []
            
            # Collect all backup dates with their files
            backup_dates = {}
            
            for year_dir in self.backup_root.iterdir():
                if not year_dir.is_dir() or not year_dir.name.isdigit():
                    continue
                    
                for month_dir in year_dir.iterdir():
                    if not month_dir.is_dir() or not month_dir.name.isdigit():
                        continue
                        
                    for day_dir in month_dir.iterdir():
                        if not day_dir.is_dir() or not day_dir.name.isdigit():
                            continue
                        
                        try:
                            year = int(year_dir.name)
                            month = int(month_dir.name)
                            day = int(day_dir.name)
                            backup_date = datetime(year, month, day)
                            
                            # Store date and its directory for cleanup decisions
                            backup_dates[backup_date] = day_dir
                        except ValueError:
                            continue
            
            # Sort dates newest to oldest
            sorted_dates = sorted(backup_dates.keys(), reverse=True)
            
            # Determine which dates to keep
            keep_dates = set()
            
            # Keep last 7 daily backups
            for i, date in enumerate(sorted_dates[:7]):
                keep_dates.add(date)
            
            # Keep last 4 weekly backups (Sundays)
            sunday_count = 0
            for date in sorted_dates:
                if date.weekday() == 6:  # Sunday
                    keep_dates.add(date)
                    sunday_count += 1
                    if sunday_count >= 4:
                        break
            
            # Keep last 12 monthly backups (1st of month)
            monthly_count = 0
            for date in sorted_dates:
                if date.day == 1:  # First of month
                    keep_dates.add(date)
                    monthly_count += 1
                    if monthly_count >= 12:
                        break
            
            # Mark directories for deletion
            deleted_count = 0
            for date, day_dir in backup_dates.items():
                if date not in keep_dates:
                    try:
                        shutil.rmtree(day_dir)
                        deleted_count += 1
                        
                        # Clean up empty parent directories
                        month_dir = day_dir.parent
                        year_dir = month_dir.parent
                        
                        if not any(month_dir.iterdir()):
                            month_dir.rmdir()
                            if not any(year_dir.iterdir()):
                                year_dir.rmdir()
                                
                    except Exception as e:
                        logger.warning(f"⚠️ Could not delete {day_dir}: {e}")
            
            kept_count = len(keep_dates)
            logger.info(f"🧹 Cleanup complete: kept {kept_count} backup dates, deleted {deleted_count}")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
    
    def get_backup_counts(self) -> Dict[str, int]:
        """
        📊 Get count of backup directories for UI display.
        
        Returns count of unique backup dates, not individual files.
        """
        try:
            if not self.backup_root.exists():
                return {'backup_dates': 0, 'total_files': 0}
            
            backup_dates = set()
            total_files = 0
            
            for year_dir in self.backup_root.iterdir():
                if not year_dir.is_dir() or not year_dir.name.isdigit():
                    continue
                    
                for month_dir in year_dir.iterdir():
                    if not month_dir.is_dir() or not month_dir.name.isdigit():
                        continue
                        
                    for day_dir in month_dir.iterdir():
                        if not day_dir.is_dir() or not day_dir.name.isdigit():
                            continue
                        
                        try:
                            year = int(year_dir.name)
                            month = int(month_dir.name)
                            day = int(day_dir.name)
                            backup_date = datetime(year, month, day)
                            backup_dates.add(backup_date)
                            
                            # Count files in this date directory
                            for file in day_dir.iterdir():
                                if file.is_file() and file.suffix == '.db':
                                    total_files += 1
                                    
                        except ValueError:
                            continue
            
            return {
                'backup_dates': len(backup_dates),
                'total_files': total_files
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting backup counts: {e}")
            return {'backup_dates': 0, 'total_files': 0}
    
    def get_current_db_counts(self, main_db_path: str) -> Dict[str, int]:
        """📊 Get record counts from current database for UI display."""
        try:
            if not Path(main_db_path).exists():
                return {}
            
            counts = {}
            conn = sqlite3.connect(main_db_path)
            cursor = conn.cursor()
            
            for table_name in self.backup_tables.keys():
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    counts[table_name] = cursor.fetchone()[0]
                except Exception:
                    counts[table_name] = 0
            
            conn.close()
            return counts
            
        except Exception as e:
            logger.error(f"❌ Error getting current DB counts: {e}")
            return {}
    
    def explicit_backup_all(self, main_db_path: str, keychain_db_path: str) -> Dict[str, int]:
        """
        💾 Explicit backup triggered by user, return record counts.
        
        Like auto_backup_all but with different logging for UI feedback.
        """
        results = {}
        
        # Backup main tables
        for table_name in self.backup_tables.keys():
            results[table_name] = self.backup_table(main_db_path, table_name)
        
        # Backup AI keychain
        results['ai_keychain'] = self.backup_ai_keychain(keychain_db_path)
        
        # Automatic cleanup
        self.cleanup_old_backups()
        
        successful = sum(1 for count in results.values() if count > 0)
        total_records = sum(results.values())
        logger.info(f"💾 Explicit backup complete: {successful}/{len(results)} tables, {total_records} total records")
        
        return results
    
    def explicit_restore_all(self, main_db_path: str, keychain_db_path: str) -> Dict[str, int]:
        """
        📥 Explicit restore triggered by user, return record counts.
        
        Use when you want to restore from a previous backup.
        """
        results = {}
        
        # Restore main tables
        for table_name in self.backup_tables.keys():
            results[table_name] = self.restore_table(main_db_path, table_name)
        
        # Restore AI keychain
        results['ai_keychain'] = self.restore_ai_keychain(keychain_db_path)
        
        successful = sum(1 for count in results.values() if count > 0)
        total_records = sum(results.values())
        logger.info(f"📥 Explicit restore complete: {successful}/{len(results)} tables, {total_records} total records")
        
        return results


# 🎯 GLOBAL INSTANCE for easy import
backup_manager = DurableBackupManager() 
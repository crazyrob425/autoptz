"""
Cloud Backup Manager

Orchestrates backup and sync of all AI-Stalker data to Google Cloud services.
Supports:
- Settings and configurations (JSON)
- Camera registry (SQLite database)
- Facial recognition database
- Camera photos and recordings
- Trigger zone definitions
"""

import json
import logging
import shutil
import sqlite3
from typing import Optional, Dict, List, Any
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
import threading
from enum import Enum

logger = logging.getLogger(__name__)


class BackupStatus(Enum):
    """Backup operation status"""
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class BackupData:
    """Backup metadata"""
    timestamp: str
    backup_id: str
    total_size_mb: float
    files_count: int
    status: str
    items: Dict[str, Any]  # Per-item status


class CloudBackupManager:
    """
    Manages backup and restoration of AI-Stalker data to/from Google Cloud.
    """

    def __init__(self, oauth_manager=None, data_dir: Optional[str] = None):
        """
        Initialize backup manager.
        
        Args:
            oauth_manager: GoogleOAuthManager instance for auth
            data_dir: Base directory containing data to backup
        """
        self.oauth_manager = oauth_manager
        self.data_dir = Path(data_dir or Path.home() / ".autoptz")
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.backup_status = BackupStatus.IDLE
        self.last_backup: Optional[BackupData] = None
        self.backup_history: List[BackupData] = []

    def get_backup_items(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all items available for backup.
        
        Returns:
            Dict mapping item names to metadata
        """
        items = {}

        # Settings
        settings_file = self.data_dir / "settings.json"
        if settings_file.exists():
            items['settings'] = {
                'path': str(settings_file),
                'type': 'config',
                'size_mb': settings_file.stat().st_size / (1024 * 1024),
                'backed_up': False,
            }

        # Camera Registry (SQLite)
        registry_file = self.data_dir / "camera_registry.db"
        if registry_file.exists():
            items['camera_registry'] = {
                'path': str(registry_file),
                'type': 'database',
                'size_mb': registry_file.stat().st_size / (1024 * 1024),
                'backed_up': False,
            }

        # Facial Recognition Database
        face_db = self.data_dir / "face_recognition.db"
        if face_db.exists():
            items['facial_recognition'] = {
                'path': str(face_db),
                'type': 'database',
                'size_mb': face_db.stat().st_size / (1024 * 1024),
                'backed_up': False,
            }

        # Trainer/Face Dataset
        trainer_dir = self.data_dir / "trainer"
        if trainer_dir.exists():
            total_size = sum(f.stat().st_size for f in trainer_dir.rglob('*') if f.is_file())
            items['trainer_dataset'] = {
                'path': str(trainer_dir),
                'type': 'directory',
                'size_mb': total_size / (1024 * 1024),
                'file_count': len(list(trainer_dir.rglob('*'))),
                'backed_up': False,
            }

        # Recordings
        recordings_dir = self.data_dir / "recordings"
        if recordings_dir.exists():
            total_size = sum(f.stat().st_size for f in recordings_dir.rglob('*') if f.is_file())
            items['recordings'] = {
                'path': str(recordings_dir),
                'type': 'directory',
                'size_mb': total_size / (1024 * 1024),
                'file_count': len(list(recordings_dir.rglob('*'))),
                'backed_up': False,
            }

        # Camera Photos
        photos_dir = self.data_dir / "photos"
        if photos_dir.exists():
            total_size = sum(f.stat().st_size for f in photos_dir.rglob('*') if f.is_file())
            items['photos'] = {
                'path': str(photos_dir),
                'type': 'directory',
                'size_mb': total_size / (1024 * 1024),
                'file_count': len(list(photos_dir.rglob('*'))),
                'backed_up': False,
            }

        # Trigger Zones Config
        zones_file = self.data_dir / "trigger_zones.json"
        if zones_file.exists():
            items['trigger_zones'] = {
                'path': str(zones_file),
                'type': 'config',
                'size_mb': zones_file.stat().st_size / (1024 * 1024),
                'backed_up': False,
            }

        return items

    def create_local_backup(self, item_names: Optional[List[str]] = None) -> Optional[BackupData]:
        """
        Create local backup of specified items.
        
        Args:
            item_names: List of item names to backup. None = all items
            
        Returns:
            BackupData with metadata, or None if failed
        """
        try:
            self.backup_status = BackupStatus.IN_PROGRESS

            all_items = self.get_backup_items()
            items_to_backup = item_names or list(all_items.keys())

            backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / backup_id
            backup_path.mkdir(parents=True, exist_ok=True)

            total_size = 0
            files_count = 0
            items_status = {}

            for item_name in items_to_backup:
                if item_name not in all_items:
                    logger.warning(f"Item not found: {item_name}")
                    continue

                item_info = all_items[item_name]
                src_path = Path(item_info['path'])

                try:
                    if src_path.is_file():
                        # Copy file
                        dest = backup_path / src_path.name
                        shutil.copy2(src_path, dest)
                        size = dest.stat().st_size
                        total_size += size
                        files_count += 1
                        items_status[item_name] = {
                            'status': 'success',
                            'size_mb': size / (1024 * 1024),
                        }

                    elif src_path.is_dir():
                        # Copy directory
                        dest = backup_path / src_path.name
                        shutil.copytree(src_path, dest, dirs_exist_ok=True)
                        size = sum(f.stat().st_size for f in dest.rglob('*') if f.is_file())
                        total_size += size
                        files_count += len(list(dest.rglob('*')))
                        items_status[item_name] = {
                            'status': 'success',
                            'size_mb': size / (1024 * 1024),
                            'file_count': len(list(dest.rglob('*'))),
                        }

                except Exception as e:
                    logger.error(f"Failed to backup {item_name}: {e}")
                    items_status[item_name] = {'status': 'failed', 'error': str(e)}

            # Create manifest
            manifest = {
                'timestamp': datetime.now().isoformat(),
                'backup_id': backup_id,
                'total_size_mb': total_size / (1024 * 1024),
                'files_count': files_count,
                'items': items_status,
            }

            with open(backup_path / "manifest.json", 'w') as f:
                json.dump(manifest, f, indent=2)

            backup_data = BackupData(
                timestamp=manifest['timestamp'],
                backup_id=backup_id,
                total_size_mb=manifest['total_size_mb'],
                files_count=files_count,
                status=BackupStatus.COMPLETED.value,
                items=items_status,
            )

            self.last_backup = backup_data
            self.backup_history.append(backup_data)
            self.backup_status = BackupStatus.COMPLETED

            logger.info(f"✓ Local backup created: {backup_id} ({manifest['total_size_mb']:.1f} MB)")
            return backup_data

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            self.backup_status = BackupStatus.FAILED
            return None

    def restore_from_backup(self, backup_id: str, items_to_restore: Optional[List[str]] = None) -> bool:
        """
        Restore data from a local backup.
        
        Args:
            backup_id: ID of backup to restore from
            items_to_restore: List of item names to restore. None = all items
            
        Returns:
            True if restore successful
        """
        try:
            backup_path = self.backup_dir / backup_id
            if not backup_path.exists():
                logger.error(f"Backup not found: {backup_id}")
                return False

            # Load manifest
            manifest_file = backup_path / "manifest.json"
            if not manifest_file.exists():
                logger.error(f"Manifest not found in backup: {backup_id}")
                return False

            with open(manifest_file, 'r') as f:
                manifest = json.load(f)

            items = items_to_restore or list(manifest['items'].keys())

            for item_name in items:
                if item_name not in manifest['items']:
                    logger.warning(f"Item not in backup: {item_name}")
                    continue

                src = backup_path / item_name
                if not src.exists():
                    logger.warning(f"Backup item not found: {item_name}")
                    continue

                dest = Path(manifest['items'][item_name].get('path', self.data_dir / item_name))
                dest.parent.mkdir(parents=True, exist_ok=True)

                try:
                    if src.is_file():
                        shutil.copy2(src, dest)
                    elif src.is_dir():
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(src, dest)

                    logger.info(f"Restored: {item_name}")

                except Exception as e:
                    logger.error(f"Failed to restore {item_name}: {e}")
                    return False

            logger.info(f"✓ Restore completed from backup: {backup_id}")
            return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    def list_backups(self) -> List[BackupData]:
        """List all available local backups"""
        backups = []

        for backup_dir in sorted(self.backup_dir.iterdir(), reverse=True):
            if not backup_dir.is_dir():
                continue

            manifest_file = backup_dir / "manifest.json"
            if manifest_file.exists():
                try:
                    with open(manifest_file, 'r') as f:
                        manifest = json.load(f)
                    
                    backup_data = BackupData(
                        timestamp=manifest['timestamp'],
                        backup_id=manifest['backup_id'],
                        total_size_mb=manifest['total_size_mb'],
                        files_count=manifest['files_count'],
                        status=BackupStatus.COMPLETED.value,
                        items=manifest['items'],
                    )
                    backups.append(backup_data)

                except Exception as e:
                    logger.warning(f"Failed to load backup manifest: {e}")

        return backups

    def delete_backup(self, backup_id: str) -> bool:
        """Delete a local backup"""
        try:
            backup_path = self.backup_dir / backup_id
            if backup_path.exists():
                shutil.rmtree(backup_path)
                logger.info(f"Deleted backup: {backup_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False

    def get_status_summary(self) -> Dict[str, Any]:
        """Get current backup status summary"""
        return {
            'status': self.backup_status.value,
            'last_backup': asdict(self.last_backup) if self.last_backup else None,
            'total_backups': len(self.backup_history),
            'backup_location': str(self.backup_dir),
            'total_backup_size_mb': sum(
                b.total_size_mb for b in self.backup_history
            ),
        }

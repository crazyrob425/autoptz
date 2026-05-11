"""
Failsafe Node

Implements automated failsafe backup and restore with data cloning.
Periodically backs up all AI-Stalker data to cloud for recovery in case of data loss.
"""

import json
import logging
import threading
import time
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class FailsafeConfig:
    """Failsafe node configuration"""
    enabled: bool = True
    backup_interval_hours: int = 6
    auto_sync_to_cloud: bool = True
    max_local_backups: int = 5
    on_backup_complete: Optional[Callable] = None
    on_backup_error: Optional[Callable] = None


class FailsafeNode:
    """
    Automated failsafe system for AI-Stalker data protection.
    
    Features:
    - Periodic local backups
    - Automatic cloud sync
    - Data cloning to multiple cloud services
    - Recovery from backups
    - Health monitoring
    """

    def __init__(
        self,
        backup_manager,
        oauth_manager=None,
        config: Optional[FailsafeConfig] = None
    ):
        """
        Initialize failsafe node.
        
        Args:
            backup_manager: CloudBackupManager instance
            oauth_manager: GoogleOAuthManager instance (optional)
            config: FailsafeConfig with settings
        """
        self.backup_manager = backup_manager
        self.oauth_manager = oauth_manager
        self.config = config or FailsafeConfig()

        self.is_running = False
        self.backup_thread: Optional[threading.Thread] = None
        self.last_backup_time: Optional[datetime] = None
        self.last_sync_time: Optional[datetime] = None
        self.sync_errors: int = 0
        self.health_status = "healthy"

    def start(self) -> bool:
        """Start failsafe monitoring"""
        if self.is_running:
            logger.warning("Failsafe already running")
            return False

        if not self.config.enabled:
            logger.info("Failsafe disabled in config")
            return False

        self.is_running = True
        self.backup_thread = threading.Thread(
            target=self._backup_loop,
            daemon=True
        )
        self.backup_thread.start()

        logger.info("✓ Failsafe node started")
        return True

    def stop(self) -> bool:
        """Stop failsafe monitoring"""
        if not self.is_running:
            return False

        self.is_running = False

        if self.backup_thread:
            self.backup_thread.join(timeout=5)

        logger.info("✓ Failsafe node stopped")
        return True

    def _backup_loop(self):
        """Main backup loop (runs in thread)"""
        while self.is_running:
            try:
                now = datetime.now()

                # Check if it's time for backup
                if self.last_backup_time is None or \
                   (now - self.last_backup_time).total_seconds() >= \
                   self.config.backup_interval_hours * 3600:
                    
                    self._perform_backup()

                # Check if it's time for cloud sync
                if self.config.auto_sync_to_cloud and self.oauth_manager and \
                   self.oauth_manager.is_authenticated():
                    
                    if self.last_sync_time is None or \
                       (now - self.last_sync_time).total_seconds() >= 3600:  # Hourly sync
                        
                        self._perform_cloud_sync()

            except Exception as e:
                logger.error(f"Failsafe loop error: {e}")
                self.sync_errors += 1
                if self.sync_errors > 5:
                    self.health_status = "degraded"

            # Sleep before next check (5 minutes)
            time.sleep(300)

    def _perform_backup(self):
        """Perform local backup"""
        try:
            logger.info("Failsafe: Starting backup...")

            backup_data = self.backup_manager.create_local_backup()

            if backup_data:
                self.last_backup_time = datetime.now()
                self.sync_errors = 0
                self.health_status = "healthy"

                logger.info(f"Failsafe backup completed: {backup_data.backup_id}")

                # Cleanup old backups
                self._cleanup_old_backups()

                # Trigger callback
                if self.config.on_backup_complete:
                    self.config.on_backup_complete(backup_data)

            else:
                logger.warning("Failsafe backup failed")
                self.health_status = "degraded"
                
                if self.config.on_backup_error:
                    self.config.on_backup_error("Backup creation failed")

        except Exception as e:
            logger.error(f"Failsafe backup error: {e}")
            self.health_status = "degraded"

            if self.config.on_backup_error:
                self.config.on_backup_error(str(e))

    def _perform_cloud_sync(self):
        """Sync latest backup to Google Cloud"""
        try:
            if not self.oauth_manager or not self.oauth_manager.is_authenticated():
                logger.debug("Cloud sync skipped: not authenticated")
                return

            backups = self.backup_manager.list_backups()
            if not backups:
                logger.debug("No backups to sync")
                return

            latest_backup = backups[0]
            backup_path = self.backup_manager.backup_dir / latest_backup.backup_id

            logger.info(f"Failsafe: Syncing backup to Google Cloud: {latest_backup.backup_id}")

            # Upload to Google Drive
            from logic.cloud.google_drive_sync import GoogleDriveSync
            
            drive_sync = GoogleDriveSync(self.oauth_manager)
            if drive_sync.upload_backup(backup_path, latest_backup.backup_id):
                self.last_sync_time = datetime.now()
                logger.info(f"✓ Cloud sync completed: {latest_backup.backup_id}")
            else:
                logger.warning("Cloud sync failed")
                self.health_status = "degraded"

        except ImportError:
            logger.debug("Google Drive sync module not available")
        except Exception as e:
            logger.error(f"Cloud sync error: {e}")
            self.health_status = "degraded"

    def _cleanup_old_backups(self):
        """Remove old backups, keeping only max_local_backups"""
        try:
            backups = self.backup_manager.list_backups()

            if len(backups) > self.config.max_local_backups:
                to_delete = len(backups) - self.config.max_local_backups

                for backup in backups[-to_delete:]:
                    self.backup_manager.delete_backup(backup.backup_id)
                    logger.debug(f"Cleaned up old backup: {backup.backup_id}")

        except Exception as e:
            logger.warning(f"Backup cleanup failed: {e}")

    def manual_backup_now(self) -> bool:
        """Trigger immediate backup (outside of schedule)"""
        try:
            logger.info("Failsafe: Manual backup triggered")
            self._perform_backup()
            return True
        except Exception as e:
            logger.error(f"Manual backup failed: {e}")
            return False

    def manual_sync_now(self) -> bool:
        """Trigger immediate cloud sync (outside of schedule)"""
        try:
            logger.info("Failsafe: Manual sync triggered")
            self._perform_cloud_sync()
            return True
        except Exception as e:
            logger.error(f"Manual sync failed: {e}")
            return False

    def get_health_status(self) -> Dict[str, Any]:
        """Get failsafe health status"""
        backups = self.backup_manager.list_backups()

        return {
            'enabled': self.config.enabled,
            'running': self.is_running,
            'health': self.health_status,
            'last_backup': self.last_backup_time.isoformat() if self.last_backup_time else None,
            'last_sync': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'sync_errors': self.sync_errors,
            'total_backups': len(backups),
            'total_backup_size_mb': sum(b.total_size_mb for b in backups),
            'backup_interval_hours': self.config.backup_interval_hours,
            'auto_sync_enabled': self.config.auto_sync_to_cloud,
            'cloud_authenticated': self.oauth_manager and self.oauth_manager.is_authenticated() if self.oauth_manager else False,
        }

    def restore_from_latest(self) -> bool:
        """Restore from latest available backup"""
        try:
            backups = self.backup_manager.list_backups()
            if not backups:
                logger.error("No backups available for restore")
                return False

            latest = backups[0]
            logger.info(f"Restoring from latest backup: {latest.backup_id}")

            return self.backup_manager.restore_from_backup(latest.backup_id)

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

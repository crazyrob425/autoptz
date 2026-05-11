"""
Google Drive Sync

Upload and download backups to/from Google Drive.
Uses Google Drive API for file operations.
"""

import json
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import io

logger = logging.getLogger(__name__)


class GoogleDriveSync:
    """
    Manages backup sync to Google Drive.
    
    Creates folder structure:
    /My Drive/AutoPTZ/
        ├── backups/
        │   ├── 20240511_120000/
        │   │   ├── camera_registry.db
        │   │   ├── facial_recognition.db
        │   │   ├── manifest.json
        │   │   └── ...
        └── settings/
"""

    def __init__(self, oauth_manager):
        """
        Initialize Google Drive sync.
        
        Args:
            oauth_manager: GoogleOAuthManager instance
        """
        self.oauth_manager = oauth_manager
        self.root_folder_name = "AutoPTZ"
        self.root_folder_id = None

        if oauth_manager and oauth_manager.is_authenticated():
            self._init_drive_client()

    def _init_drive_client(self):
        """Initialize Google Drive API client"""
        try:
            from googleapiclient.discovery import build

            credentials = self.oauth_manager.get_credentials()
            self.drive_service = build('drive', 'v3', credentials=credentials)
            
            # Ensure root folder exists
            self._ensure_root_folder()

        except ImportError:
            logger.warning("google-api-python-client not available")
            self.drive_service = None
        except Exception as e:
            logger.error(f"Failed to init Drive client: {e}")
            self.drive_service = None

    def _ensure_root_folder(self):
        """Ensure /AutoPTZ/ folder exists in Google Drive"""
        try:
            if not self.drive_service:
                return

            # Search for existing AutoPTZ folder
            query = f"name='{self.root_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=1
            ).execute()

            if results.get('files'):
                self.root_folder_id = results['files'][0]['id']
                logger.debug(f"Found existing AutoPTZ folder: {self.root_folder_id}")
                return

            # Create root folder if doesn't exist
            file_metadata = {
                'name': self.root_folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }

            folder = self.drive_service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()

            self.root_folder_id = folder.get('id')
            logger.info(f"Created AutoPTZ folder: {self.root_folder_id}")

        except Exception as e:
            logger.error(f"Failed to ensure root folder: {e}")

    def upload_backup(self, backup_path: Path, backup_id: str) -> bool:
        """
        Upload a backup to Google Drive.
        
        Args:
            backup_path: Local path to backup directory
            backup_id: ID of backup
            
        Returns:
            True if successful
        """
        try:
            if not self.drive_service or not self.root_folder_id:
                logger.warning("Google Drive not initialized")
                return False

            if not backup_path.exists():
                logger.error(f"Backup path not found: {backup_path}")
                return False

            # Create backup folder in Drive
            backup_folder_id = self._create_drive_folder(
                backup_id,
                self.root_folder_id
            )

            if not backup_folder_id:
                logger.error("Failed to create backup folder in Drive")
                return False

            # Upload all files from backup
            file_count = 0
            for local_file in backup_path.rglob('*'):
                if local_file.is_file():
                    self._upload_file_to_drive(local_file, backup_folder_id)
                    file_count += 1

            logger.info(f"✓ Uploaded {file_count} files to Google Drive: {backup_id}")
            return True

        except Exception as e:
            logger.error(f"Backup upload failed: {e}")
            return False

    def download_backup(self, backup_id: str, download_path: Path) -> bool:
        """
        Download a backup from Google Drive.
        
        Args:
            backup_id: ID of backup to download
            download_path: Local path to download to
            
        Returns:
            True if successful
        """
        try:
            if not self.drive_service or not self.root_folder_id:
                logger.warning("Google Drive not initialized")
                return False

            download_path.mkdir(parents=True, exist_ok=True)

            # Find backup folder in Drive
            query = f"name='{backup_id}' and mimeType='application/vnd.google-apps.folder' and trashed=false and '{self.root_folder_id}' in parents"
            results = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id)',
                pageSize=1
            ).execute()

            if not results.get('files'):
                logger.error(f"Backup not found in Drive: {backup_id}")
                return False

            backup_folder_id = results['files'][0]['id']

            # Download all files from backup folder
            file_count = self._download_folder_from_drive(
                backup_folder_id,
                download_path
            )

            logger.info(f"✓ Downloaded {file_count} files from Google Drive: {backup_id}")
            return True

        except Exception as e:
            logger.error(f"Backup download failed: {e}")
            return False

    def _create_drive_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """Create a folder in Google Drive"""
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
            }

            if parent_id:
                file_metadata['parents'] = [parent_id]

            folder = self.drive_service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()

            return folder.get('id')

        except Exception as e:
            logger.error(f"Failed to create Drive folder: {e}")
            return None

    def _upload_file_to_drive(self, file_path: Path, parent_id: Optional[str] = None) -> Optional[str]:
        """Upload a file to Google Drive"""
        try:
            from googleapiclient.http import MediaFileUpload

            file_metadata = {'name': file_path.name}

            if parent_id:
                file_metadata['parents'] = [parent_id]

            media = MediaFileUpload(str(file_path), resumable=True)

            file_obj = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            return file_obj.get('id')

        except Exception as e:
            logger.debug(f"Failed to upload file: {file_path.name}: {e}")
            return None

    def _download_folder_from_drive(self, folder_id: str, download_path: Path) -> int:
        """Download all files from a Drive folder recursively"""
        try:
            file_count = 0

            query = f"'{folder_id}' in parents and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType)',
                pageSize=100
            ).execute()

            for item in results.get('files', []):
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    # Recursively download subfolder
                    subfolder_path = download_path / item['name']
                    subfolder_path.mkdir(parents=True, exist_ok=True)
                    
                    file_count += self._download_folder_from_drive(item['id'], subfolder_path)

                else:
                    # Download file
                    self._download_file_from_drive(item['id'], item['name'], download_path)
                    file_count += 1

            return file_count

        except Exception as e:
            logger.error(f"Failed to download Drive folder: {e}")
            return 0

    def _download_file_from_drive(self, file_id: str, file_name: str, download_path: Path) -> bool:
        """Download a file from Google Drive"""
        try:
            file_path = download_path / file_name
            request = self.drive_service.files().get_media(fileId=file_id)

            with open(file_path, 'wb') as f:
                f.write(request.execute())

            logger.debug(f"Downloaded: {file_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to download file {file_name}: {e}")
            return False

    def list_backups_in_drive(self) -> List[Dict[str, Any]]:
        """List all backups in Google Drive"""
        try:
            if not self.drive_service or not self.root_folder_id:
                return []

            query = f"'{self.root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, createdTime, size)',
                pageSize=50,
                orderBy='createdTime desc'
            ).execute()

            backups = []
            for item in results.get('files', []):
                backups.append({
                    'id': item['id'],
                    'name': item['name'],
                    'created': item.get('createdTime'),
                    'size': item.get('size', 'unknown'),
                })

            return backups

        except Exception as e:
            logger.error(f"Failed to list Drive backups: {e}")
            return []

    def delete_backup_from_drive(self, backup_id: str) -> bool:
        """Delete a backup from Google Drive"""
        try:
            if not self.drive_service or not self.root_folder_id:
                return False

            query = f"name='{backup_id}' and mimeType='application/vnd.google-apps.folder' and trashed=false and '{self.root_folder_id}' in parents"
            results = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id)',
                pageSize=1
            ).execute()

            if not results.get('files'):
                logger.warning(f"Backup not found for deletion: {backup_id}")
                return False

            folder_id = results['files'][0]['id']

            # Recursively delete all files in folder
            self._delete_folder_from_drive(folder_id)

            logger.info(f"Deleted backup from Drive: {backup_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete Drive backup: {e}")
            return False

    def _delete_folder_from_drive(self, folder_id: str) -> bool:
        """Recursively delete a folder and contents from Google Drive"""
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id)',
                pageSize=100
            ).execute()

            for item in results.get('files', []):
                self._delete_folder_from_drive(item['id'])

            self.drive_service.files().delete(fileId=folder_id).execute()
            return True

        except Exception as e:
            logger.error(f"Failed to delete Drive folder: {e}")
            return False

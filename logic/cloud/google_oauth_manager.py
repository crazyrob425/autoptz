"""
Google OAuth Manager

Handles Google OAuth 2.0 authentication flow and token management.
Supports login, logout, token refresh, and credential persistence.
"""

import json
import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

logger = logging.getLogger(__name__)


class GoogleOAuthManager:
    """
    Manages Google OAuth 2.0 authentication for AI-Stalker.
    
    Supports:
    - Google Drive API
    - Google Cloud Storage
    - Google Photos Library API
    """

    # Google API Scopes
    SCOPES = [
        'https://www.googleapis.com/auth/drive.file',  # Google Drive
        'https://www.googleapis.com/auth/photoslibrary',  # Google Photos
        'https://www.googleapis.com/auth/cloud-platform',  # Google Cloud
    ]

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize OAuth manager.
        
        Args:
            config_dir: Directory to store credentials.json and token.pickle
        """
        self.config_dir = Path(config_dir or os.path.expanduser("~/.autoptz/cloud"))
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.credentials_file = self.config_dir / "google_credentials.json"
        self.token_file = self.config_dir / "google_token.pickle"
        self.user_info_file = self.config_dir / "user_info.json"

        self.credentials = None
        self.user_info = None

        # Load existing credentials if available
        self._load_credentials()

    def ensure_credentials_file(self, client_id: str, client_secret: str) -> bool:
        """
        Ensure credentials.json exists (Google Cloud OAuth2 credentials).
        
        User must:
        1. Create OAuth2 app in Google Cloud Console
        2. Download credentials.json
        3. Save to ~/.autoptz/cloud/google_credentials.json
        
        Args:
            client_id: OAuth client ID (from credentials.json)
            client_secret: OAuth client secret (from credentials.json)
            
        Returns:
            True if credentials file exists or was created
        """
        if self.credentials_file.exists():
            return True

        # Create minimal credentials file structure
        creds_data = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"],
            }
        }

        with open(self.credentials_file, 'w') as f:
            json.dump(creds_data, f, indent=2)

        logger.info(f"Created credentials file: {self.credentials_file}")
        return True

    def authenticate(self) -> bool:
        """
        Run OAuth authentication flow.
        Opens browser for user to authorize.
        
        Returns:
            True if authentication successful
        """
        if not self.credentials_file.exists():
            logger.error(
                f"Google credentials file not found: {self.credentials_file}\n"
                f"Please download OAuth2 credentials from Google Cloud Console and place at:\n"
                f"{self.credentials_file}"
            )
            return False

        try:
            # Create OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_file),
                self.SCOPES
            )

            # Run authentication (opens browser)
            self.credentials = flow.run_local_server(port=8080, open_browser=True)

            # Save credentials
            self._save_credentials()

            # Fetch and save user info
            self._fetch_user_info()

            logger.info(f"✓ Successfully authenticated as {self.user_info.get('email', 'Unknown')}")
            return True

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated with valid credentials"""
        if self.credentials is None:
            return False

        if self.credentials.expired and self.credentials.refresh_token:
            try:
                self._refresh_credentials()
            except Exception as e:
                logger.warning(f"Token refresh failed: {e}")
                return False

        return True

    def get_user_email(self) -> Optional[str]:
        """Get authenticated user's email"""
        if not self.is_authenticated():
            return None
        return self.user_info.get('email')

    def logout(self) -> bool:
        """Logout and clear credentials"""
        try:
            self.credentials = None
            self.user_info = None

            if self.token_file.exists():
                self.token_file.unlink()

            if self.user_info_file.exists():
                self.user_info_file.unlink()

            logger.info("Successfully logged out")
            return True

        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False

    def _load_credentials(self):
        """Load credentials from token.pickle if exists"""
        if not self.token_file.exists():
            return

        try:
            with open(self.token_file, 'rb') as f:
                self.credentials = pickle.load(f)

            # Load user info
            if self.user_info_file.exists():
                with open(self.user_info_file, 'r') as f:
                    self.user_info = json.load(f)

            logger.info(f"Loaded cached credentials for {self.user_info.get('email', 'Unknown')}")

        except Exception as e:
            logger.warning(f"Failed to load cached credentials: {e}")
            self.credentials = None
            self.user_info = None

    def _save_credentials(self):
        """Save credentials to token.pickle"""
        try:
            with open(self.token_file, 'wb') as f:
                pickle.dump(self.credentials, f)
            logger.info("Credentials saved")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    def _refresh_credentials(self):
        """Refresh expired credentials"""
        if not self.credentials or not self.credentials.refresh_token:
            raise ValueError("Cannot refresh: no refresh token available")

        self.credentials.refresh(Request())
        self._save_credentials()
        logger.info("Credentials refreshed")

    def _fetch_user_info(self):
        """Fetch and save user info from Google API"""
        try:
            from google.auth.transport.requests import Request as AuthRequest
            import urllib.request
            import urllib.error

            # Get user info from Google People API
            headers = {'Authorization': f'Bearer {self.credentials.token}'}
            url = 'https://www.googleapis.com/oauth2/v2/userinfo'

            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request) as response:
                self.user_info = json.loads(response.read().decode())

            # Save user info
            with open(self.user_info_file, 'w') as f:
                json.dump(self.user_info, f, indent=2)

            logger.info(f"User info fetched: {self.user_info.get('email')}")

        except Exception as e:
            logger.warning(f"Failed to fetch user info: {e}")
            self.user_info = {}

    def get_credentials(self) -> Optional[Credentials]:
        """Get current credentials object (for API clients)"""
        if self.is_authenticated():
            return self.credentials
        return None

    def get_token(self) -> Optional[str]:
        """Get current access token"""
        if self.is_authenticated():
            return self.credentials.token
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Export auth state as dict"""
        return {
            "authenticated": self.is_authenticated(),
            "user_email": self.get_user_email(),
            "user_name": self.user_info.get('name') if self.user_info else None,
            "user_picture": self.user_info.get('picture') if self.user_info else None,
        }

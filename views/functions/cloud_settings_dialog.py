"""
Cloud Settings Dialog

UI for managing Google OAuth login and cloud backup settings.
Provides controls for authentication, backup management, and failsafe configuration.
"""

import logging
from typing import Optional, Callable
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QWidget, QTextEdit, QComboBox, QSpinBox, QCheckBox, QListWidget,
    QListWidgetItem, QMessageBox, QProgressBar, QFrame, QGroupBox,
)
from PySide6.QtCore import Qt, Signal, QThread, Slot
from PySide6.QtGui import QFont, QColor

logger = logging.getLogger(__name__)


class BackupListWorker(QThread):
    """Worker thread to list backups"""
    backups_ready = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, backup_manager):
        super().__init__()
        self.backup_manager = backup_manager

    def run(self):
        try:
            backups = self.backup_manager.list_backups()
            self.backups_ready.emit(backups)
        except Exception as e:
            self.error_occurred.emit(str(e))


class BackupWorker(QThread):
    """Worker thread to perform backup"""
    progress = Signal(str)
    backup_complete = Signal(object)  # BackupData
    error_occurred = Signal(str)

    def __init__(self, backup_manager, items: Optional[list] = None):
        super().__init__()
        self.backup_manager = backup_manager
        self.items = items

    def run(self):
        try:
            self.progress.emit("Starting backup...")
            backup_data = self.backup_manager.create_local_backup(self.items)

            if backup_data:
                self.progress.emit(f"✓ Backup completed: {backup_data.backup_id}")
                self.backup_complete.emit(backup_data)
            else:
                self.error_occurred.emit("Backup creation failed")

        except Exception as e:
            self.error_occurred.emit(str(e))


class CloudSettingsDialog(QDialog):
    """
    Cloud Settings Dialog
    
    Manages:
    - Google OAuth login/logout
    - Backup creation and restoration
    - Failsafe configuration
    - Cloud sync settings
    """

    backup_updated = Signal()

    def __init__(self, oauth_manager=None, backup_manager=None, failsafe_node=None, parent=None):
        super().__init__(parent)
        self.oauth_manager = oauth_manager
        self.backup_manager = backup_manager
        self.failsafe_node = failsafe_node

        self.setWindowTitle("Cloud Settings & Backup")
        self.setGeometry(100, 100, 800, 600)
        self.setup_ui()
        self.refresh_auth_status()

    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)

        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Authentication
        self.auth_tab = self._create_auth_tab()
        self.tabs.addTab(self.auth_tab, "Google Account")

        # Tab 2: Backups
        self.backup_tab = self._create_backup_tab()
        self.tabs.addTab(self.backup_tab, "Local Backups")

        # Tab 3: Failsafe
        self.failsafe_tab = self._create_failsafe_tab()
        self.tabs.addTab(self.failsafe_tab, "Failsafe Node")

        # Tab 4: Cloud Sync
        self.sync_tab = self._create_sync_tab()
        self.tabs.addTab(self.sync_tab, "Cloud Sync")

        # Bottom buttons
        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_all)
        btn_layout.addWidget(refresh_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _create_auth_tab(self) -> QWidget:
        """Create authentication tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Status group
        status_group = QGroupBox("Authentication Status")
        status_layout = QVBoxLayout(status_group)

        self.auth_status_label = QLabel("Not authenticated")
        self.auth_status_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        status_layout.addWidget(self.auth_status_label)

        self.user_email_label = QLabel()
        status_layout.addWidget(self.user_email_label)

        layout.addWidget(status_group)

        # Action buttons
        btn_layout = QHBoxLayout()

        self.login_btn = QPushButton("Login with Google")
        self.login_btn.clicked.connect(self._on_login)
        btn_layout.addWidget(self.login_btn)

        self.logout_btn = QPushButton("Logout")
        self.logout_btn.clicked.connect(self._on_logout)
        self.logout_btn.setEnabled(False)
        btn_layout.addWidget(self.logout_btn)

        layout.addLayout(btn_layout)

        # Info
        info_label = QLabel(
            "🔒 Login with your Google account to enable:\n"
            "• Cloud backup sync to Google Drive\n"
            "• Automatic failsafe backups\n"
            "• Data recovery across devices\n\n"
            "Your data is encrypted and securely stored."
        )
        info_label.setStyleSheet("color: #666; font-size: 11px; margin-top: 20px;")
        layout.addWidget(info_label)

        layout.addStretch()
        return widget

    def _create_backup_tab(self) -> QWidget:
        """Create backup tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("Local Backups:"))

        # Backup list
        self.backup_list = QListWidget()
        layout.addWidget(self.backup_list)

        # Control buttons
        ctrl_layout = QHBoxLayout()

        new_backup_btn = QPushButton("Create Backup Now")
        new_backup_btn.clicked.connect(self._on_create_backup)
        ctrl_layout.addWidget(new_backup_btn)

        restore_btn = QPushButton("Restore Selected")
        restore_btn.clicked.connect(self._on_restore_backup)
        ctrl_layout.addWidget(restore_btn)

        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self._on_delete_backup)
        ctrl_layout.addWidget(delete_btn)

        layout.addLayout(ctrl_layout)

        # Backup details
        layout.addWidget(QLabel("Backup Details:"))

        self.backup_details = QTextEdit()
        self.backup_details.setReadOnly(True)
        self.backup_details.setMaximumHeight(150)
        layout.addWidget(self.backup_details)

        return widget

    def _create_failsafe_tab(self) -> QWidget:
        """Create failsafe configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Status
        layout.addWidget(QLabel("Failsafe Status:"))

        self.failsafe_status = QTextEdit()
        self.failsafe_status.setReadOnly(True)
        self.failsafe_status.setMaximumHeight(100)
        layout.addWidget(self.failsafe_status)

        # Configuration group
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout(config_group)

        # Enable failsafe
        self.failsafe_enabled = QCheckBox("Enable automatic failsafe backups")
        self.failsafe_enabled.setChecked(True)
        self.failsafe_enabled.stateChanged.connect(self._on_failsafe_toggle)
        config_layout.addWidget(self.failsafe_enabled)

        # Backup interval
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Backup interval (hours):"))
        self.backup_interval = QSpinBox()
        self.backup_interval.setRange(1, 24)
        self.backup_interval.setValue(6)
        interval_layout.addWidget(self.backup_interval)
        interval_layout.addStretch()
        config_layout.addLayout(interval_layout)

        # Auto sync to cloud
        self.auto_sync = QCheckBox("Auto-sync backups to Google Drive")
        self.auto_sync.setChecked(True)
        config_layout.addWidget(self.auto_sync)

        layout.addWidget(config_group)

        # Manual controls
        ctrl_layout = QHBoxLayout()

        manual_backup_btn = QPushButton("Backup Now")
        manual_backup_btn.clicked.connect(self._on_failsafe_backup)
        ctrl_layout.addWidget(manual_backup_btn)

        manual_sync_btn = QPushButton("Sync to Cloud")
        manual_sync_btn.clicked.connect(self._on_failsafe_sync)
        ctrl_layout.addWidget(manual_sync_btn)

        layout.addLayout(ctrl_layout)

        layout.addStretch()
        return widget

    def _create_sync_tab(self) -> QWidget:
        """Create cloud sync tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("Cloud Backups (Google Drive):"))

        self.cloud_backup_list = QListWidget()
        layout.addWidget(self.cloud_backup_list)

        # Controls
        ctrl_layout = QHBoxLayout()

        refresh_cloud_btn = QPushButton("Refresh Cloud Backups")
        refresh_cloud_btn.clicked.connect(self._on_refresh_cloud)
        ctrl_layout.addWidget(refresh_cloud_btn)

        download_btn = QPushButton("Download Selected")
        download_btn.clicked.connect(self._on_download_backup)
        ctrl_layout.addWidget(download_btn)

        delete_cloud_btn = QPushButton("Delete from Cloud")
        delete_cloud_btn.clicked.connect(self._on_delete_cloud_backup)
        ctrl_layout.addWidget(delete_cloud_btn)

        layout.addLayout(ctrl_layout)

        # Status
        layout.addWidget(QLabel("Sync Status:"))

        self.sync_status = QTextEdit()
        self.sync_status.setReadOnly(True)
        self.sync_status.setMaximumHeight(100)
        layout.addWidget(self.sync_status)

        return widget

    @Slot()
    def _on_login(self):
        """Handle Google login"""
        if not self.oauth_manager:
            QMessageBox.warning(self, "Error", "OAuth manager not initialized")
            return

        if self.oauth_manager.authenticate():
            QMessageBox.information(self, "Success", "Successfully logged in!")
            self.refresh_auth_status()
        else:
            QMessageBox.warning(self, "Error", "Login failed. Check console for details.")

    @Slot()
    def _on_logout(self):
        """Handle logout"""
        if self.oauth_manager and self.oauth_manager.logout():
            QMessageBox.information(self, "Success", "Logged out successfully")
            self.refresh_auth_status()

    @Slot()
    def _on_create_backup(self):
        """Create backup"""
        if not self.backup_manager:
            QMessageBox.warning(self, "Error", "Backup manager not initialized")
            return

        worker = BackupWorker(self.backup_manager)
        worker.progress.connect(self._on_backup_progress)
        worker.backup_complete.connect(self._on_backup_complete)
        worker.error_occurred.connect(self._on_backup_error)
        worker.start()

    @Slot()
    def _on_restore_backup(self):
        """Restore selected backup"""
        if not self.backup_manager:
            return

        items = self.backup_list.selectedItems()
        if not items:
            QMessageBox.warning(self, "Error", "No backup selected")
            return

        backup_id = items[0].text().split()[0]
        
        reply = QMessageBox.question(
            self, "Confirm Restore",
            f"Restore from backup: {backup_id}?\nThis will overwrite current data.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.backup_manager.restore_from_backup(backup_id):
                QMessageBox.information(self, "Success", "Restore completed")
                self.backup_updated.emit()
            else:
                QMessageBox.warning(self, "Error", "Restore failed")

    @Slot()
    def _on_delete_backup(self):
        """Delete selected backup"""
        if not self.backup_manager:
            return

        items = self.backup_list.selectedItems()
        if not items:
            QMessageBox.warning(self, "Error", "No backup selected")
            return

        backup_id = items[0].text().split()[0]

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete backup: {backup_id}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.backup_manager.delete_backup(backup_id)
            self.refresh_backups()

    @Slot()
    def _on_failsafe_backup(self):
        """Manual failsafe backup"""
        if not self.failsafe_node:
            QMessageBox.warning(self, "Error", "Failsafe not initialized")
            return

        if self.failsafe_node.manual_backup_now():
            QMessageBox.information(self, "Success", "Backup completed")
            self.refresh_backups()
        else:
            QMessageBox.warning(self, "Error", "Backup failed")

    @Slot()
    def _on_failsafe_sync(self):
        """Manual cloud sync"""
        if not self.failsafe_node:
            QMessageBox.warning(self, "Error", "Failsafe not initialized")
            return

        if not self.oauth_manager or not self.oauth_manager.is_authenticated():
            QMessageBox.warning(self, "Error", "Not authenticated with Google")
            return

        if self.failsafe_node.manual_sync_now():
            QMessageBox.information(self, "Success", "Sync completed")
        else:
            QMessageBox.warning(self, "Error", "Sync failed")

    @Slot()
    def _on_refresh_cloud(self):
        """Refresh cloud backup list"""
        try:
            from logic.cloud.google_drive_sync import GoogleDriveSync

            if not self.oauth_manager or not self.oauth_manager.is_authenticated():
                QMessageBox.warning(self, "Error", "Not authenticated")
                return

            drive_sync = GoogleDriveSync(self.oauth_manager)
            backups = drive_sync.list_backups_in_drive()

            self.cloud_backup_list.clear()
            for backup in backups:
                item = QListWidgetItem(f"{backup['name']} - {backup.get('created', 'Unknown')}")
                self.cloud_backup_list.addItem(item)

            self.sync_status.setText(f"Found {len(backups)} backups in Google Drive")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to list cloud backups: {str(e)}")

    @Slot()
    def _on_download_backup(self):
        """Download backup from cloud"""
        QMessageBox.information(self, "Info", "Download functionality coming soon")

    @Slot()
    def _on_delete_cloud_backup(self):
        """Delete backup from cloud"""
        QMessageBox.information(self, "Info", "Cloud delete functionality coming soon")

    @Slot()
    def _on_failsafe_toggle(self):
        """Toggle failsafe enabled state"""
        if self.failsafe_node:
            if self.failsafe_enabled.isChecked():
                self.failsafe_node.start()
            else:
                self.failsafe_node.stop()

    @Slot(str)
    def _on_backup_progress(self, message: str):
        """Handle backup progress"""
        self.backup_details.setText(message)

    @Slot(object)
    def _on_backup_complete(self, backup_data):
        """Handle backup completion"""
        QMessageBox.information(self, "Success", f"Backup created: {backup_data.backup_id}")
        self.refresh_backups()

    @Slot(str)
    def _on_backup_error(self, error_msg: str):
        """Handle backup error"""
        QMessageBox.warning(self, "Error", f"Backup failed: {error_msg}")

    def refresh_auth_status(self):
        """Update authentication status display"""
        if self.oauth_manager and self.oauth_manager.is_authenticated():
            email = self.oauth_manager.get_user_email()
            self.auth_status_label.setText("✓ Authenticated")
            self.auth_status_label.setStyleSheet("color: #51cf66; font-weight: bold;")
            self.user_email_label.setText(f"Logged in as: {email}")
            self.login_btn.setEnabled(False)
            self.logout_btn.setEnabled(True)
        else:
            self.auth_status_label.setText("Not authenticated")
            self.auth_status_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
            self.user_email_label.setText("")
            self.login_btn.setEnabled(True)
            self.logout_btn.setEnabled(False)

    def refresh_backups(self):
        """Refresh local backup list"""
        if not self.backup_manager:
            return

        backups = self.backup_manager.list_backups()
        self.backup_list.clear()

        for backup in backups:
            item_text = f"{backup.backup_id} - {backup.total_size_mb:.1f} MB ({backup.files_count} files)"
            item = QListWidgetItem(item_text)
            self.backup_list.addItem(item)

    def refresh_failsafe_status(self):
        """Refresh failsafe status display"""
        if not self.failsafe_node:
            return

        status = self.failsafe_node.get_health_status()
        status_text = f"""
Status: {status['health'].upper()}
Running: {'Yes' if status['running'] else 'No'}
Last Backup: {status['last_backup'] or 'Never'}
Last Sync: {status['last_sync'] or 'Never'}
Total Backups: {status['total_backups']}
Total Size: {status['total_backup_size_mb']:.1f} MB
Cloud Sync: {'Enabled' if status['auto_sync_enabled'] else 'Disabled'}
        """.strip()

        self.failsafe_status.setText(status_text)

    def refresh_all(self):
        """Refresh all displays"""
        self.refresh_auth_status()
        self.refresh_backups()
        self.refresh_failsafe_status()

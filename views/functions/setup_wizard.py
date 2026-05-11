"""
Setup Wizard UI

Interactive multi-step wizard using AI to guide camera setup.
Presents conversation interface with camera discovery and configuration.
"""

import logging
from typing import Optional, Callable
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QScrollArea, QWidget, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QListWidget, QListWidgetItem, QTabWidget, QProgressBar,
    QMessageBox, QFrame, QScrollBar
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, Slot
from PySide6.QtGui import QFont, QColor, QTextCursor

logger = logging.getLogger(__name__)


class SetupWizardWorker(QThread):
    """Worker thread for AI wizard operations"""
    response_ready = Signal(str, list)  # message, tool_calls
    error_occurred = Signal(str)
    progress_updated = Signal(str)

    def __init__(self, ai_controller, user_message: str):
        super().__init__()
        self.ai_controller = ai_controller
        self.user_message = user_message

    def run(self):
        """Run wizard step in background"""
        try:
            import asyncio

            # Run async operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            if hasattr(self.ai_controller, 'start_wizard_conversation'):
                response = loop.run_until_complete(
                    self.ai_controller.start_wizard_conversation(self.user_message)
                )
            else:
                response = self.ai_controller.start(self.user_message)

            loop.close()

            # Emit response
            self.response_ready.emit(response.content, response.tool_calls or [])

        except Exception as e:
            logger.error(f"Wizard error: {e}")
            self.error_occurred.emit(str(e))


class CameraListItem(QFrame):
    """Custom widget for displaying discovered camera in list"""

    def __init__(self, camera_data: dict, parent=None):
        super().__init__(parent)
        self.camera_data = camera_data
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("border: 1px solid #ddd; border-radius: 5px; padding: 8px;")

        layout = QVBoxLayout(self)

        # IP and protocol
        info_label = QLabel(
            f"<b>{camera_data.get('ip', 'Unknown')}</b> ({camera_data.get('protocol', 'Unknown')})"
        )
        layout.addWidget(info_label)

        # Confidence
        if camera_data.get('confidence'):
            confidence = int(camera_data['confidence'] * 100)
            conf_label = QLabel(f"Confidence: {confidence}%")
            conf_label.setStyleSheet("color: #666; font-size: 11px;")
            layout.addWidget(conf_label)


class SetupWizardDialog(QDialog):
    """
    AI-Guided Camera Setup Wizard
    Multi-step interactive dialog for camera discovery and configuration.
    """

    wizard_complete = Signal(dict)  # Emits final configuration

    def __init__(self, ai_controller=None, mcp_server=None, parent=None):
        super().__init__(parent)
        self.ai_controller = ai_controller
        self.mcp_server = mcp_server
        self.setup_data = {}
        self.worker = None

        self.setWindowTitle("Camera Setup Wizard")
        self.setGeometry(100, 100, 900, 700)
        self.setup_ui()

    def setup_ui(self):
        """Setup wizard UI"""
        layout = QVBoxLayout(self)

        # Tab widget for different phases
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Discovery
        self.discovery_tab = self._create_discovery_tab()
        self.tabs.addTab(self.discovery_tab, "Discovery")

        # Tab 2: Capabilities
        self.capabilities_tab = self._create_capabilities_tab()
        self.tabs.addTab(self.capabilities_tab, "Capabilities")

        # Tab 3: Configuration
        self.config_tab = self._create_config_tab()
        self.tabs.addTab(self.config_tab, "Configuration")

        # Tab 4: Summary
        self.summary_tab = self._create_summary_tab()
        self.tabs.addTab(self.summary_tab, "Summary")

        # Bottom: Conversation area
        layout.addWidget(QLabel("AI Assistant Guide:"))

        self.conversation_display = QTextEdit()
        self.conversation_display.setReadOnly(True)
        self.conversation_display.setMaximumHeight(150)
        layout.addWidget(self.conversation_display)

        # User input
        input_layout = QHBoxLayout()
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Type your response or question...")
        input_layout.addWidget(self.user_input)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._on_send_message)
        input_layout.addWidget(self.send_btn)

        layout.addLayout(input_layout)

        # Control buttons
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Wizard")
        self.start_btn.clicked.connect(self._on_start_wizard)
        btn_layout.addWidget(self.start_btn)

        self.next_btn = QPushButton("Next ➜")
        self.next_btn.clicked.connect(self._on_next_step)
        btn_layout.addWidget(self.next_btn)

        self.finish_btn = QPushButton("Finish")
        self.finish_btn.clicked.connect(self._on_finish_wizard)
        btn_layout.addWidget(self.finish_btn)

        layout.addLayout(btn_layout)

    def _create_discovery_tab(self) -> QWidget:
        """Create discovery phase tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("Discovered Cameras:"))

        self.discovery_list = QListWidget()
        layout.addWidget(self.discovery_list)

        # Scan button
        scan_btn = QPushButton("Scan for Cameras")
        scan_btn.clicked.connect(self._on_scan_cameras)
        layout.addWidget(scan_btn)

        # Subnet input (optional)
        subnet_layout = QHBoxLayout()
        subnet_layout.addWidget(QLabel("Subnet (optional):"))
        self.subnet_input = QLineEdit()
        self.subnet_input.setPlaceholderText("e.g., 192.168.1.0/24")
        subnet_layout.addWidget(self.subnet_input)
        layout.addLayout(subnet_layout)

        layout.addStretch()
        return widget

    def _create_capabilities_tab(self) -> QWidget:
        """Create capabilities phase tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("Camera Capabilities:"))

        self.capabilities_display = QTextEdit()
        self.capabilities_display.setReadOnly(True)
        layout.addWidget(self.capabilities_display)

        # Probe button
        probe_btn = QPushButton("Probe Selected Camera")
        probe_btn.clicked.connect(self._on_probe_camera)
        layout.addWidget(probe_btn)

        layout.addStretch()
        return widget

    def _create_config_tab(self) -> QWidget:
        """Create configuration phase tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Sensitivity section
        layout.addWidget(QLabel("Detection Sensitivity:"))

        sens_layout = QVBoxLayout()

        # Face confidence
        face_layout = QHBoxLayout()
        face_layout.addWidget(QLabel("Face Confidence Threshold:"))
        self.face_confidence = QDoubleSpinBox()
        self.face_confidence.setRange(0.0, 1.0)
        self.face_confidence.setSingleStep(0.05)
        self.face_confidence.setValue(0.7)
        face_layout.addWidget(self.face_confidence)
        face_layout.addStretch()
        sens_layout.addLayout(face_layout)

        # Motion threshold
        motion_layout = QHBoxLayout()
        motion_layout.addWidget(QLabel("Motion Threshold:"))
        self.motion_threshold = QDoubleSpinBox()
        self.motion_threshold.setRange(0.0, 1.0)
        self.motion_threshold.setSingleStep(0.05)
        self.motion_threshold.setValue(0.2)
        motion_layout.addWidget(self.motion_threshold)
        motion_layout.addStretch()
        sens_layout.addLayout(motion_layout)

        # Recording enabled
        self.recording_enabled = QCheckBox("Enable Recording on Detection")
        self.recording_enabled.setChecked(True)
        sens_layout.addWidget(self.recording_enabled)

        layout.addLayout(sens_layout)

        # Trigger zone section
        layout.addWidget(QLabel("Trigger Zones:"))

        zone_layout = QVBoxLayout()

        zone_name_layout = QHBoxLayout()
        zone_name_layout.addWidget(QLabel("Zone Name:"))
        self.zone_name = QLineEdit()
        self.zone_name.setPlaceholderText("e.g., 'Entrance', 'Parking Lot'")
        zone_name_layout.addWidget(self.zone_name)
        zone_layout.addLayout(zone_name_layout)

        # Zone type
        zone_type_layout = QHBoxLayout()
        zone_type_layout.addWidget(QLabel("Zone Type:"))
        self.zone_type = QComboBox()
        self.zone_type.addItems(["Rectangle", "Polygon", "Circle"])
        zone_type_layout.addWidget(self.zone_type)
        zone_layout.addStretch()
        zone_layout.addLayout(zone_type_layout)

        # Detection type
        detect_layout = QHBoxLayout()
        detect_layout.addWidget(QLabel("Detect:"))
        self.detection_type = QComboBox()
        self.detection_type.addItems(["Face", "Motion", "Person"])
        detect_layout.addWidget(self.detection_type)
        detect_layout.addStretch()
        zone_layout.addLayout(detect_layout)

        # Action on detect
        action_layout = QHBoxLayout()
        action_layout.addWidget(QLabel("Action:"))
        self.action_on_detect = QComboBox()
        self.action_on_detect.addItems(["Record", "Alert", "PTZ Focus", "Webhook"])
        action_layout.addWidget(self.action_on_detect)
        action_layout.addStretch()
        zone_layout.addLayout(action_layout)

        layout.addLayout(zone_layout)

        # Add zone button
        add_zone_btn = QPushButton("Add Trigger Zone")
        add_zone_btn.clicked.connect(self._on_add_trigger_zone)
        layout.addWidget(add_zone_btn)

        layout.addStretch()
        return widget

    def _create_summary_tab(self) -> QWidget:
        """Create summary/completion tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("Setup Summary:"))

        self.summary_display = QTextEdit()
        self.summary_display.setReadOnly(True)
        layout.addWidget(self.summary_display)

        # Save settings button
        save_btn = QPushButton("Save Configuration")
        save_btn.clicked.connect(self._on_save_config)
        layout.addWidget(save_btn)

        layout.addStretch()
        return widget

    @Slot()
    def _on_start_wizard(self):
        """Start wizard conversation"""
        if not self.ai_controller:
            QMessageBox.warning(self, "Error", "AI Controller not initialized")
            return

        self.start_btn.setEnabled(False)
        self._add_ai_message("🤖 Starting camera setup wizard...\nI'll help you discover, configure, and optimize your camera setup.")

        self._run_wizard_step("Let's start by discovering what cameras are available on your network.")

    @Slot()
    def _on_next_step(self):
        """Continue to next wizard step"""
        # Determine context based on current tab
        current_tab = self.tabs.currentIndex()

        if current_tab == 0:  # Discovery
            self._run_wizard_step("I've reviewed the discovered cameras. Let's probe their capabilities.")
        elif current_tab == 1:  # Capabilities
            self._run_wizard_step("Now let's configure detection sensitivity and trigger zones.")
        elif current_tab == 2:  # Config
            self._run_wizard_step("Let's create a summary of the setup.")
        else:
            self._run_wizard_step("Setup complete!")

    @Slot()
    def _on_scan_cameras(self):
        """Trigger camera discovery"""
        self._run_wizard_step("Please scan my network for available cameras.")

    @Slot()
    def _on_probe_camera(self):
        """Probe selected camera capabilities"""
        self._run_wizard_step("Please probe the capabilities of the discovered cameras.")

    @Slot()
    def _on_add_trigger_zone(self):
        """Add trigger zone via AI"""
        zone_name = self.zone_name.text()
        if not zone_name:
            QMessageBox.warning(self, "Error", "Please enter a zone name")
            return

        self._run_wizard_step(
            f"Add a trigger zone named '{zone_name}' that detects {self.detection_type.currentText().lower()}"
        )

    @Slot()
    def _on_send_message(self):
        """Send user message"""
        message = self.user_input.text().strip()
        if not message:
            return

        self.user_input.clear()
        self._add_user_message(message)
        self._run_wizard_step(message)

    @Slot()
    def _on_finish_wizard(self):
        """Finalize wizard"""
        self._run_wizard_step("I'm done with the setup. Please provide a final summary and save everything.")

    @Slot()
    def _on_save_config(self):
        """Save configuration"""
        summary = self.ai_controller.get_setup_summary() if self.ai_controller else {}
        self.setup_data = summary
        self.wizard_complete.emit(self.setup_data)
        QMessageBox.information(self, "Success", "Camera configuration saved!")

    def _run_wizard_step(self, user_message: str):
        """Run wizard step in background thread"""
        if not self.ai_controller:
            self._add_ai_message("Error: AI controller not available")
            return

        self.worker = SetupWizardWorker(self.ai_controller, user_message)
        self.worker.response_ready.connect(self._on_response_ready)
        self.worker.error_occurred.connect(self._on_wizard_error)
        self.worker.start()

    @Slot(str, list)
    def _on_response_ready(self, message: str, tool_calls: list):
        """Handle AI response"""
        self._add_ai_message(message)

        # Display tool calls
        if tool_calls:
            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "unknown")
                self._add_ai_message(f"🔧 Calling tool: {tool_name}")

    @Slot(str)
    def _on_wizard_error(self, error_msg: str):
        """Handle wizard error"""
        self._add_ai_message(f"❌ Error: {error_msg}")

    def _add_ai_message(self, message: str):
        """Add AI message to conversation display"""
        cursor = self.conversation_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.conversation_display.setTextCursor(cursor)

        self.conversation_display.insertPlainText(f"AI: {message}\n\n")

    def _add_user_message(self, message: str):
        """Add user message to conversation display"""
        cursor = self.conversation_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.conversation_display.setTextCursor(cursor)

        self.conversation_display.insertPlainText(f"You: {message}\n\n")


def launch_setup_wizard(parent=None, ai_controller=None, mcp_server=None):
    """
    Convenience function to launch setup wizard.
    
    Returns:
        Wizard dialog instance (or None if creation failed)
    """
    try:
        wizard = SetupWizardDialog(ai_controller, mcp_server, parent)
        return wizard
    except Exception as e:
        logger.error(f"Failed to create wizard: {e}")
        return None

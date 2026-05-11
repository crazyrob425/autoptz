import pickle
from multiprocessing import Manager
# from multiprocess import managers
import os
from functools import partial
from urllib.parse import urlparse
from PySide6 import QtCore, QtWidgets
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import QMainWindow
import watchdog.events
import watchdog.observers
import shared.constants as constants
from logic.camera_search.search_ndi import get_ndi_sources
from logic.camera_search.auto_discovery import CameraAutoDiscovery
from logic.camera_search.credential_manager import CameraCredentialManager
from logic.camera_search.camera_registry import CameraRegistry
from libraries.visca.move_visca_ptz import ViscaPTZ
from logic.camera_search.get_serial_cameras import COMPorts
from shared.message_prompts import show_info_messagebox
from views.functions.show_dialogs_ui import ShowDialog
from views.functions.assign_network_ptz_ui import AssignNetworkPTZDlg
from views.functions.ip_credentials_dialog import IPCredentialsDialog
from views.functions.network_scan_worker import NetworkScanWorker
from views.homepage.flow_layout import FlowLayout
from views.homepage.overview import GridOverview
from views.homepage.recorded_library import RecordedLibrary
from PySide6.QtWidgets import QStackedWidget, QWidget
from shared.watch_trainer_directory import WatchTrainer
from views.widgets.camera_widget import CameraWidget

# AI Setup Wizard imports (gracefully optional)
try:
    from logic.ai_setup.mcp_camera_server import CameraSetupMCPServer
    from logic.ai_setup.wizard_ai_controller import WizardAIController
    from views.functions.setup_wizard import launch_setup_wizard
    AI_WIZARD_AVAILABLE = True
except ImportError as e:
    AI_WIZARD_AVAILABLE = False
    import logging
    logging.debug(f"AI Setup Wizard not available: {e}")

# Cloud Services imports (gracefully optional)
try:
    from logic.cloud.google_oauth_manager import GoogleOAuthManager
    from logic.cloud.cloud_backup_manager import CloudBackupManager
    from logic.cloud.failsafe_node import FailsafeNode, FailsafeConfig
    from views.functions.cloud_settings_dialog import CloudSettingsDialog
    CLOUD_SERVICES_AVAILABLE = True
except ImportError as e:
    CLOUD_SERVICES_AVAILABLE = False
    import logging
    logging.debug(f"Cloud Services not available: {e}")


class AutoPTZ_MainWindow(QMainWindow):
    """
    Configures and Handles the AutoPTZ MainWindow UI
    """

    def __init__(self, *args, **kwargs):

        # setting up the UI and QT Threading
        super(AutoPTZ_MainWindow, self).__init__(*args, **kwargs)
        self.manager = Manager()
        self.active_camera_widgets = []
        self.view_mode_auto = True
        self.network_camera_urls = set()
        self.credential_manager = CameraCredentialManager()
        self.camera_registry = CameraRegistry()
        self.scan_thread = None
        self.scan_worker = None
        self.scan_progress_dialog = None

        # Initialize cloud services
        if CLOUD_SERVICES_AVAILABLE:
            try:
                self.oauth_manager = GoogleOAuthManager()
                self.backup_manager = CloudBackupManager(
                    oauth_manager=self.oauth_manager,
                    data_dir=constants.TRAINER_PATH if hasattr(constants, 'TRAINER_PATH') else None
                )
                failsafe_config = FailsafeConfig(
                    enabled=True,
                    backup_interval_hours=6,
                    auto_sync_to_cloud=True,
                    max_local_backups=5,
                )
                self.failsafe_node = FailsafeNode(
                    backup_manager=self.backup_manager,
                    oauth_manager=self.oauth_manager,
                    config=failsafe_config
                )
                # Start failsafe monitoring
                self.failsafe_node.start()
            except Exception as e:
                import logging
                logging.warning(f"Failed to initialize cloud services: {e}")
                self.oauth_manager = None
                self.backup_manager = None
                self.failsafe_node = None
        else:
            self.oauth_manager = None
            self.backup_manager = None
            self.failsafe_node = None

        # self.manager = managers.SharedMemoryManager()
        # self.manager.ShareableList(sequence=[])

        # setting up main window
        self.setObjectName("AI_Stalker")
        self.resize(200, 450)
        self.setAutoFillBackground(False)
        self.setTabShape(QtWidgets.QTabWidget.TabShape.Rounded)
        self.setDockNestingEnabled(False)

        # base window widget
        self.central_widget = QtWidgets.QWidget(self)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,
                                            QtWidgets.QSizePolicy.Policy.Preferred)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(
            self.central_widget.sizePolicy().hasHeightForWidth())
        self.central_widget.setSizePolicy(size_policy)
        self.central_widget.setObjectName("central_widget")
        self.gridLayout = QtWidgets.QGridLayout(self.central_widget)
        self.gridLayout.setObjectName("gridLayout")
        self.setCentralWidget(self.central_widget)

        # left tab menus
        self.formTabWidget = QtWidgets.QTabWidget(self.central_widget)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,
                                            QtWidgets.QSizePolicy.Policy.Preferred)
        size_policy.setHeightForWidth(
            self.formTabWidget.sizePolicy().hasHeightForWidth())
        self.formTabWidget.setSizePolicy(size_policy)
        self.formTabWidget.setObjectName("formTabWidget")

        # auto tab menu
        self.selectedCamPage = QtWidgets.QWidget(self)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,
                                            QtWidgets.QSizePolicy.Policy.Preferred)
        size_policy.setHeightForWidth(
            self.selectedCamPage.sizePolicy().hasHeightForWidth())
        self.selectedCamPage.setSizePolicy(size_policy)
        self.selectedCamPage.setMinimumSize(QtCore.QSize(163, 0))
        self.selectedCamPage.setMaximumSize(QtCore.QSize(16777215, 428))
        self.selectedCamPage.setObjectName("selectedCamPage")
        self.formLayout = QtWidgets.QFormLayout(self.selectedCamPage)
        self.formLayout.setLabelAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeading | QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.formLayout.setFormAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeading | QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.formLayout.setObjectName("formLayout")
        self.select_face_dropdown = QtWidgets.QComboBox(self.selectedCamPage)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                            QtWidgets.QSizePolicy.Policy.Fixed)
        size_policy.setHeightForWidth(
            self.select_face_dropdown.sizePolicy().hasHeightForWidth())
        self.select_face_dropdown.setSizePolicy(size_policy)
        self.select_face_dropdown.setObjectName("select_face_dropdown")
        self.select_face_dropdown.setEnabled(False)
        self.select_face_dropdown.currentTextChanged.connect(
            self.selected_face_change)
        self.select_face_dropdown.addItem('')
        self.update_face_dropdown(event="")

        # assign usb PTZ to Serial Camera Source
        self.assign_network_ptz_btn = QtWidgets.QPushButton(
            self.selectedCamPage)
        self.assign_network_ptz_btn.setGeometry(QtCore.QRect(10, 380, 150, 32))
        self.assign_network_ptz_btn.setObjectName("assign_network_ptz_btn")
        self.assign_network_ptz_btn.hide()
        self.unassign_network_ptz_btn = QtWidgets.QPushButton(
            self.selectedCamPage)
        self.unassign_network_ptz_btn.setGeometry(
            QtCore.QRect(0, 380, 162, 32))
        self.unassign_network_ptz_btn.setObjectName("unassign_usb_ptz_btn")
        self.unassign_network_ptz_btn.hide()
        self.assign_network_ptz_btn.clicked.connect(
            self.assign_network_ptz_dlg)
        self.unassign_network_ptz_btn.clicked.connect(
            self.unassign_network_ptz)

        self.formLayout.setWidget(
            2, QtWidgets.QFormLayout.ItemRole.SpanningRole, self.select_face_dropdown)
        self.enable_track = QtWidgets.QCheckBox(self.selectedCamPage)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                            QtWidgets.QSizePolicy.Policy.Fixed)
        size_policy.setHeightForWidth(
            self.enable_track.sizePolicy().hasHeightForWidth())
        self.enable_track.setSizePolicy(size_policy)
        self.enable_track.setChecked(False)
        self.enable_track.setEnabled(False)
        self.enable_track.setAutoRepeat(False)
        self.enable_track.setAutoExclusive(False)
        self.enable_track.stateChanged.connect(self.enable_track_change)
        self.enable_track.setObjectName("enable_track")
        self.formLayout.setWidget(
            3, QtWidgets.QFormLayout.ItemRole.LabelRole, self.enable_track)
        self.select_face_label = QtWidgets.QLabel(self.selectedCamPage)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,
                                            QtWidgets.QSizePolicy.Policy.Preferred)
        size_policy.setHeightForWidth(
            self.select_face_label.sizePolicy().hasHeightForWidth())
        self.select_face_label.setSizePolicy(size_policy)
        self.select_face_label.setObjectName("select_face_label")
        self.formLayout.setWidget(
            1, QtWidgets.QFormLayout.ItemRole.LabelRole, self.select_face_label)
        self.formTabWidget.addTab(self.selectedCamPage, "")

        # manual control tab menu
        self.manualControlPage = QtWidgets.QWidget()
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,
                                            QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        size_policy.setHeightForWidth(
            self.manualControlPage.sizePolicy().hasHeightForWidth())
        self.manualControlPage.setSizePolicy(size_policy)
        self.manualControlPage.setMinimumSize(QtCore.QSize(163, 0))
        self.manualControlPage.setMaximumSize(QtCore.QSize(16777215, 428))
        self.manualControlPage.setObjectName("manualControlPage")
        self.select_camera_label = QtWidgets.QLabel(self.manualControlPage)
        self.select_camera_label.setGeometry(QtCore.QRect(10, 30, 101, 21))
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,
                                            QtWidgets.QSizePolicy.Policy.Preferred)
        size_policy.setHeightForWidth(
            self.select_camera_label.sizePolicy().hasHeightForWidth())
        self.select_camera_label.setSizePolicy(size_policy)
        self.select_camera_label.setObjectName("select_camera_label")
        self.select_camera_dropdown = QtWidgets.QComboBox(
            self.manualControlPage)
        self.select_camera_dropdown.setGeometry(QtCore.QRect(9, 51, 151, 26))
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                            QtWidgets.QSizePolicy.Policy.Fixed)
        size_policy.setHeightForWidth(
            self.select_camera_dropdown.sizePolicy().hasHeightForWidth())
        self.select_camera_dropdown.setSizePolicy(size_policy)
        self.select_camera_dropdown.setObjectName("select_camera_dropdown")
        self.select_camera_dropdown.addItem("")

        # add all the USB devices to the dropdown menu
        data_list = COMPorts.get_com_ports().data
        for port in data_list:
            if "USB" in port.description:
                print(port.device, port.description, data_list.index(port))
                self.select_camera_dropdown.addItem(port.device)

        self.select_camera_dropdown.currentTextChanged.connect(
            self.set_manual_control)

        # manual control buttons
        self.gridLayoutWidget = QtWidgets.QWidget(self.manualControlPage)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(0, 100, 162, 131))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.controller_layout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        # self.controller_layout.setSizeConstraint(QtWidgets.QLayout.SetNoConstraint)
        self.controller_layout.setContentsMargins(0, 0, 0, 0)
        self.controller_layout.setObjectName("controllerLayout")
        self.down_right_btn = QtWidgets.QPushButton(self.gridLayoutWidget)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                            QtWidgets.QSizePolicy.Policy.Maximum)
        size_policy.setHeightForWidth(
            self.down_right_btn.sizePolicy().hasHeightForWidth())
        self.down_right_btn.setSizePolicy(size_policy)
        self.down_right_btn.setIconSize(QtCore.QSize(10, 10))
        self.down_right_btn.setFlat(False)
        self.down_right_btn.setObjectName("down_right_btn")
        self.controller_layout.addWidget(self.down_right_btn, 2, 2, 1, 1)
        self.up_btn = QtWidgets.QPushButton(self.gridLayoutWidget)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                            QtWidgets.QSizePolicy.Policy.Maximum)
        size_policy.setHeightForWidth(
            self.up_btn.sizePolicy().hasHeightForWidth())
        self.up_btn.setSizePolicy(size_policy)
        self.up_btn.setIconSize(QtCore.QSize(10, 10))
        self.up_btn.setObjectName("up_btn")
        self.controller_layout.addWidget(self.up_btn, 0, 1, 1, 1)
        self.up_left_btn = QtWidgets.QPushButton(self.gridLayoutWidget)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                            QtWidgets.QSizePolicy.Policy.Maximum)
        size_policy.setHeightForWidth(
            self.up_left_btn.sizePolicy().hasHeightForWidth())
        self.up_left_btn.setSizePolicy(size_policy)
        self.up_left_btn.setIconSize(QtCore.QSize(10, 10))
        self.up_left_btn.setObjectName("up_left_btn")
        self.controller_layout.addWidget(self.up_left_btn, 0, 0, 1, 1)
        self.left_btn = QtWidgets.QPushButton(self.gridLayoutWidget)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                            QtWidgets.QSizePolicy.Policy.Maximum)
        size_policy.setHeightForWidth(
            self.left_btn.sizePolicy().hasHeightForWidth())
        self.left_btn.setSizePolicy(size_policy)
        self.left_btn.setIconSize(QtCore.QSize(10, 10))
        self.left_btn.setObjectName("left_btn")
        self.controller_layout.addWidget(self.left_btn, 1, 0, 1, 1)
        self.down_left_btn = QtWidgets.QPushButton(self.gridLayoutWidget)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                            QtWidgets.QSizePolicy.Policy.Maximum)
        size_policy.setHeightForWidth(
            self.down_left_btn.sizePolicy().hasHeightForWidth())
        self.down_left_btn.setSizePolicy(size_policy)
        self.down_left_btn.setIconSize(QtCore.QSize(10, 10))
        self.down_left_btn.setObjectName("down_left_btn")
        self.controller_layout.addWidget(self.down_left_btn, 2, 0, 1, 1)
        self.up_right_btn = QtWidgets.QPushButton(self.gridLayoutWidget)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                            QtWidgets.QSizePolicy.Policy.Maximum)
        size_policy.setHeightForWidth(
            self.up_right_btn.sizePolicy().hasHeightForWidth())
        self.up_right_btn.setSizePolicy(size_policy)
        self.up_right_btn.setIconSize(QtCore.QSize(10, 10))
        self.up_right_btn.setObjectName("up_right_btn")
        self.controller_layout.addWidget(self.up_right_btn, 0, 2, 1, 1)
        self.right_btn = QtWidgets.QPushButton(self.gridLayoutWidget)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                            QtWidgets.QSizePolicy.Policy.Maximum)
        size_policy.setHeightForWidth(
            self.right_btn.sizePolicy().hasHeightForWidth())
        self.right_btn.setSizePolicy(size_policy)
        self.right_btn.setIconSize(QtCore.QSize(10, 10))
        self.right_btn.setObjectName("right_btn")
        self.controller_layout.addWidget(self.right_btn, 1, 2, 1, 1)
        self.down_btn = QtWidgets.QPushButton(self.gridLayoutWidget)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                            QtWidgets.QSizePolicy.Policy.Maximum)
        size_policy.setHeightForWidth(
            self.down_btn.sizePolicy().hasHeightForWidth())
        self.down_btn.setSizePolicy(size_policy)
        self.down_btn.setIconSize(QtCore.QSize(10, 10))
        self.down_btn.setObjectName("down_btn")
        self.controller_layout.addWidget(self.down_btn, 2, 1, 1, 1)
        self.home_btn = QtWidgets.QPushButton(self.gridLayoutWidget)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                            QtWidgets.QSizePolicy.Policy.Maximum)
        size_policy.setHeightForWidth(
            self.home_btn.sizePolicy().hasHeightForWidth())
        self.home_btn.setSizePolicy(size_policy)
        self.home_btn.setIconSize(QtCore.QSize(10, 10))
        self.home_btn.setObjectName("home_btn")
        self.controller_layout.addWidget(self.home_btn, 1, 1, 1, 1)
        self.horizontalLayoutWidget = QtWidgets.QWidget(self.manualControlPage)
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(0, 240, 161, 32))
        self.horizontalLayoutWidget.setObjectName("horizontalLayoutWidget")
        self.zoom_layout = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget)
        self.zoom_layout.setContentsMargins(0, 0, 0, 0)
        self.zoom_layout.setObjectName("zoom_layout")
        self.zoom_in_btn = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                            QtWidgets.QSizePolicy.Policy.Preferred)
        size_policy.setHeightForWidth(
            self.zoom_in_btn.sizePolicy().hasHeightForWidth())
        self.zoom_in_btn.setSizePolicy(size_policy)
        self.zoom_in_btn.setObjectName("zoom_in_btn")
        self.zoom_layout.addWidget(self.zoom_in_btn)
        self.zoom_out_btn = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                            QtWidgets.QSizePolicy.Policy.Preferred)
        size_policy.setHeightForWidth(
            self.zoom_out_btn.sizePolicy().hasHeightForWidth())
        self.zoom_out_btn.setSizePolicy(size_policy)
        self.zoom_out_btn.setObjectName("zoom_out_btn")
        self.zoom_layout.addWidget(self.zoom_out_btn)
        self.horizontalLayoutWidget_2 = QtWidgets.QWidget(
            self.manualControlPage)
        self.horizontalLayoutWidget_2.setGeometry(
            QtCore.QRect(0, 280, 161, 32))
        self.horizontalLayoutWidget_2.setObjectName("horizontalLayoutWidget_2")
        self.focus_layout = QtWidgets.QHBoxLayout(
            self.horizontalLayoutWidget_2)
        self.focus_layout.setContentsMargins(0, 0, 0, 0)
        self.focus_layout.setObjectName("focus_layout")
        self.focus_plus_btn = QtWidgets.QPushButton(
            self.horizontalLayoutWidget_2)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                            QtWidgets.QSizePolicy.Policy.Preferred)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(
            self.focus_plus_btn.sizePolicy().hasHeightForWidth())
        self.focus_plus_btn.setSizePolicy(size_policy)
        self.focus_plus_btn.setObjectName("focus_plus_btn")
        self.focus_layout.addWidget(self.focus_plus_btn)
        self.focus_minus_btn = QtWidgets.QPushButton(
            self.horizontalLayoutWidget_2)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                            QtWidgets.QSizePolicy.Policy.Preferred)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(
            self.focus_minus_btn.sizePolicy().hasHeightForWidth())
        self.focus_minus_btn.setSizePolicy(size_policy)
        self.focus_minus_btn.setObjectName("focus_minus_btn")
        self.focus_layout.addWidget(self.focus_minus_btn)
        self.horizontalLayoutWidget_3 = QtWidgets.QWidget(
            self.manualControlPage)
        self.horizontalLayoutWidget_3.setGeometry(
            QtCore.QRect(0, 320, 161, 32))
        self.horizontalLayoutWidget_3.setObjectName("horizontalLayoutWidget_3")
        self.menu_layout = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget_3)
        self.menu_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_layout.setObjectName("menu_layout")
        self.menu_btn = QtWidgets.QPushButton(self.horizontalLayoutWidget_3)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                            QtWidgets.QSizePolicy.Policy.Preferred)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(
            self.menu_btn.sizePolicy().hasHeightForWidth())
        self.menu_btn.setSizePolicy(size_policy)
        self.menu_btn.setObjectName("menu_btn")
        self.menu_layout.addWidget(self.menu_btn)
        self.reset_btn = QtWidgets.QPushButton(self.horizontalLayoutWidget_3)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                            QtWidgets.QSizePolicy.Policy.Preferred)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(
            self.reset_btn.sizePolicy().hasHeightForWidth())
        self.reset_btn.setSizePolicy(size_policy)
        self.reset_btn.setObjectName("reset_btn")
        self.menu_layout.addWidget(self.reset_btn)

        # assign usb PTZ to Serial Camera Source
        self.assign_usb_ptz_btn = QtWidgets.QPushButton(self.manualControlPage)
        self.assign_usb_ptz_btn.setGeometry(QtCore.QRect(10, 380, 141, 32))
        self.assign_usb_ptz_btn.setObjectName("assign_usb_ptz_btn")
        self.assign_usb_ptz_btn.hide()
        self.unassign_usb_ptz_btn = QtWidgets.QPushButton(
            self.manualControlPage)
        self.unassign_usb_ptz_btn.setGeometry(QtCore.QRect(10, 380, 141, 32))
        self.unassign_usb_ptz_btn.setObjectName("unassign_usb_ptz_btn")
        self.unassign_usb_ptz_btn.hide()
        self.assign_usb_ptz_btn.clicked.connect(self.assign_usb_ptz_dlg)
        self.unassign_usb_ptz_btn.clicked.connect(self.unassign_usb_ptz)
        self.formTabWidget.addTab(self.manualControlPage, "")

        self.gridLayout.addWidget(self.formTabWidget, 0, 0, 3, 1)

        # enabled cameras view (stack: flow layout / overview / library)
        self.camera_stack = QStackedWidget()

        # flow layout wrapper
        flow_wrapper = QWidget()
        flow_layout = FlowLayout()
        flow_wrapper.setLayout(flow_layout)
        self.flowLayout = flow_layout

        # overview and library views
        self.overview = GridOverview()
        self.recorded_library = RecordedLibrary()

        # add pages to stack
        self.camera_stack.addWidget(flow_wrapper)
        self.camera_stack.addWidget(self.overview)
        self.camera_stack.addWidget(self.recorded_library)

        # default to flow layout
        self.camera_stack.setCurrentIndex(0)
        self.gridLayout.addWidget(self.camera_stack, 0, 1, 1, 1)

        # quick view switch buttons
        self.switch_overview_btn = QtWidgets.QPushButton('Overview')
        self.switch_library_btn = QtWidgets.QPushButton('Library')
        self.switch_grid_btn = QtWidgets.QPushButton('Grid')
        self.view_count_label = QtWidgets.QLabel('Views:')
        self.view_count_combo = QtWidgets.QComboBox()
        self.view_count_combo.addItems(['Auto', '1', '4', '6', '9', '12'])
        self.view_count_combo.setCurrentText('Auto')
        self.view_count_combo.currentTextChanged.connect(self.handle_view_count_change)
        self.switch_overview_btn.clicked.connect(lambda: self.camera_stack.setCurrentWidget(self.overview))
        self.switch_library_btn.clicked.connect(lambda: self.camera_stack.setCurrentWidget(self.recorded_library))
        self.switch_grid_btn.clicked.connect(lambda: self.camera_stack.setCurrentIndex(0))
        self.menu_layout.addWidget(self.switch_grid_btn)
        self.menu_layout.addWidget(self.switch_overview_btn)
        self.menu_layout.addWidget(self.switch_library_btn)
        self.menu_layout.addWidget(self.view_count_label)
        self.menu_layout.addWidget(self.view_count_combo)

        # handling camera window sizing
        self.screen_width = self.screen().availableGeometry().width()
        self.screen_height = self.screen().availableGeometry().height()

        # Create Dialog Object
        self.dialogs = ShowDialog()

        # Top Menu
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 705, 24))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuSource = QtWidgets.QMenu(self.menubar)
        self.menuSource.setObjectName("menuSource")
        self.menuFacial_Recognition = QtWidgets.QMenu(self.menubar)
        self.menuFacial_Recognition.setObjectName("menuFacial_Recognition")
        self.menuHelp = QtWidgets.QMenu(self.menubar)
        self.menuHelp.setObjectName("menuHelp")
        self.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)
        self.actionOpen = QtWidgets.QWidgetAction(self)
        self.actionOpen.setObjectName("actionOpen")
        self.actionSave = QtWidgets.QWidgetAction(self)
        self.actionSave.setObjectName("actionSave")
        self.actionSave_as = QtWidgets.QWidgetAction(self)
        self.actionSave_as.setObjectName("actionSave_as")
        self.actionClose = QtWidgets.QWidgetAction(self)
        self.actionClose.setObjectName("actionClose")
        self.actionAdd_IP = QtWidgets.QWidgetAction(self)
        self.actionAdd_IP.setObjectName("actionAdd_IP")
        self.actionAdd_IP.triggered.connect(self.start_auto_scan_async)
        self.actionManage_IP_Credentials = QtWidgets.QWidgetAction(self)
        self.actionManage_IP_Credentials.setObjectName("actionManage_IP_Credentials")
        self.actionManage_IP_Credentials.triggered.connect(self.open_credentials_dialog)
        
        # Setup Wizard action
        if AI_WIZARD_AVAILABLE:
            self.actionSetupWizard = QtWidgets.QWidgetAction(self)
            self.actionSetupWizard.setObjectName("actionSetupWizard")
            self.actionSetupWizard.triggered.connect(self.launch_setup_wizard_dialog)
        
        self.menuAdd_NDI = QtWidgets.QMenu(self)
        self.menuAdd_NDI.setObjectName("menuAdd_NDI")
        self.menuAdd_Hardware = QtWidgets.QMenu(self)
        self.menuAdd_Hardware.setObjectName("menuAdd_Hardware")
        self.menuAdd_IP_Cameras = QtWidgets.QMenu(self)
        self.menuAdd_IP_Cameras.setObjectName("menuAdd_IP_Cameras")
        self.actionEdit = QtWidgets.QWidgetAction(self)
        self.actionEdit.setObjectName("actionEdit")
        self.actionContact = QtWidgets.QWidgetAction(self)
        self.actionContact.setObjectName("actionContact")
        self.actionAbout = QtWidgets.QWidgetAction(self)
        self.actionAbout.setObjectName("actionAbout")
        
        # Cloud Settings action
        if CLOUD_SERVICES_AVAILABLE:
            self.actionCloudSettings = QtWidgets.QWidgetAction(self)
            self.actionCloudSettings.setObjectName("actionCloudSettings")
            self.actionCloudSettings.triggered.connect(self.open_cloud_settings_dialog)
        
        self.actionAdd_Face = QtWidgets.QWidgetAction(self)
        self.actionAdd_Face.setObjectName("actionAdd_Face")
        self.actionAdd_Face.triggered.connect(
            partial(self.dialogs.add_face))

        self.actionRemove_Face = QtWidgets.QWidgetAction(self)
        self.actionRemove_Face.setObjectName("actionRemove_Face")
        self.actionRemove_Face.triggered.connect(
            partial(self.dialogs.remove_face))
        self.actionReset_Database = QtWidgets.QWidgetAction(self)
        self.actionReset_Database.setObjectName("actionReset_Database")
        self.actionReset_Database.triggered.connect(
            partial(self.dialogs.reset_database))
        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionSave)
        self.menuFile.addAction(self.actionSave_as)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionClose)
        self.menuSource.addAction(self.actionAdd_IP)
        self.menuSource.addMenu(self.menuAdd_NDI)
        self.menuSource.addMenu(self.menuAdd_Hardware)
        self.menuSource.addMenu(self.menuAdd_IP_Cameras)
        self.menuSource.addSeparator()
        self.menuSource.addAction(self.actionManage_IP_Credentials)
        if AI_WIZARD_AVAILABLE:
            self.menuSource.addAction(self.actionSetupWizard)
        self.menuSource.addAction(self.actionEdit)
        self.menuFacial_Recognition.addAction(self.actionAdd_Face)
        self.menuFacial_Recognition.addAction(self.actionRemove_Face)
        self.menuFacial_Recognition.addSeparator()
        self.menuFacial_Recognition.addAction(self.actionReset_Database)
        self.menuHelp.addAction(self.actionAbout)
        if CLOUD_SERVICES_AVAILABLE:
            self.menuHelp.addSeparator()
            self.menuHelp.addAction(self.actionCloudSettings)
        self.menuHelp.addSeparator()
        self.menuHelp.addAction(self.actionContact)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuSource.menuAction())
        self.menubar.addAction(self.menuFacial_Recognition.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        self.findNDISources()
        self.findHardwareSources()
        if os.path.exists(constants.TRAINER_PATH) is False:
            os.mkdir(constants.TRAINER_PATH)
        self.watch_trainer = WatchTrainer(self.update_face_dropdown)

        observer = watchdog.observers.Observer()
        observer.schedule(self.watch_trainer,
                          path=constants.TRAINER_PATH, recursive=True)
        observer.start()

        # registry health / reconnect loop
        self.registry_health_timer = QtCore.QTimer(self)
        self.registry_health_timer.timeout.connect(self.run_registry_health_check)
        self.registry_health_timer.start(20000)

        # bootstrap previously enabled cameras from registry
        self.bootstrap_registry_cameras(max_count=12)

        self.translateUi(self)
        self.apply_default_view_count()
        QtCore.QMetaObject.connectSlotsByName(self)

    def open_credentials_dialog(self):
        dlg = IPCredentialsDialog(self.credential_manager, self)
        dlg.exec()

    def launch_setup_wizard_dialog(self):
        """Launch AI-guided camera setup wizard"""
        if not AI_WIZARD_AVAILABLE:
            show_info_messagebox(info_message="Setup Wizard requires additional dependencies.\nPlease install: pip install anthropic mcp")
            return

        try:
            # Ensure env keys are available even when started from alternate launchers.
            project_env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
            user_env = os.path.expanduser('~/.autoptz/.env')
            for env_path in (project_env, user_env):
                if os.path.exists(env_path):
                    try:
                        with open(env_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if not line or line.startswith('#') or '=' not in line:
                                    continue
                                k, v = line.split('=', 1)
                                os.environ.setdefault(k.strip(), v.strip().strip('"'))
                    except Exception:
                        pass

            openai_key = os.getenv("OPENAI_API_KEY")
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            if not openai_key and not anthropic_key:
                show_info_messagebox(
                    info_message=(
                        "No AI API key found.\n"
                        "Set OPENAI_API_KEY in d:/aistalker/.env (recommended) "
                        "or set ANTHROPIC_API_KEY."
                    )
                )
                return

            # Initialize MCP server with camera operations
            mcp_server = CameraSetupMCPServer()

            # Initialize AI controller
            ai_controller = WizardAIController(
                api_key=openai_key or anthropic_key,
                provider='openai' if openai_key else 'anthropic',
                mcp_server=mcp_server
            )

            # Launch wizard dialog
            wizard = launch_setup_wizard(
                parent=self,
                ai_controller=ai_controller,
                mcp_server=mcp_server
            )

            if wizard:
                wizard.exec()
                # Optionally handle wizard results here
                setup_data = wizard.setup_data
                if setup_data:
                    self.statusbar.showMessage("Camera setup wizard completed", 5000)

        except Exception as e:
            import logging
            logging.exception("Setup wizard error")
            show_info_messagebox(info_message=f"Setup wizard error: {str(e)}")

    def open_cloud_settings_dialog(self):
        """Open cloud settings and backup management dialog"""
        if not CLOUD_SERVICES_AVAILABLE:
            show_info_messagebox(info_message="Cloud Services requires additional dependencies.\nPlease install: pip install google-auth-oauthlib google-api-python-client google-cloud-storage")
            return

        try:
            dialog = CloudSettingsDialog(
                oauth_manager=self.oauth_manager,
                backup_manager=self.backup_manager,
                failsafe_node=self.failsafe_node,
                parent=self
            )

            dialog.backup_updated.connect(self._on_backup_updated)
            dialog.exec()

        except Exception as e:
            import logging
            logging.exception("Cloud settings error")
            show_info_messagebox(info_message=f"Cloud settings error: {str(e)}")

    def _on_backup_updated(self):
        """Handle backup update (e.g., after restore)"""
        self.statusbar.showMessage("Backup updated - you may need to restart for full effect", 5000)

    def start_auto_scan_async(self):
        """Start cancellable async network scan and auto-onboard cameras."""
        if self.scan_thread is not None:
            show_info_messagebox(info_message="A scan is already running.")
            return

        self.scan_progress_dialog = QtWidgets.QProgressDialog("Scanning local network...", "Cancel", 0, 0, self)
        self.scan_progress_dialog.setWindowTitle("Network Camera Discovery")
        self.scan_progress_dialog.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        self.scan_progress_dialog.setMinimumDuration(0)

        self.scan_thread = QtCore.QThread(self)
        self.scan_worker = NetworkScanWorker(credential_manager=self.credential_manager)
        self.scan_worker.moveToThread(self.scan_thread)

        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.progress.connect(self.on_scan_progress)
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.failed.connect(self.on_scan_failed)
        self.scan_worker.cancelled.connect(self.on_scan_cancelled)

        self.scan_progress_dialog.canceled.connect(self.scan_worker.cancel)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.failed.connect(self.scan_thread.quit)
        self.scan_worker.cancelled.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(self._cleanup_scan_thread)

        self.scan_thread.start()

    def _cleanup_scan_thread(self):
        self.scan_thread = None
        self.scan_worker = None
        if self.scan_progress_dialog is not None:
            self.scan_progress_dialog.close()
            self.scan_progress_dialog = None

    def on_scan_progress(self, message, value, total):
        if self.scan_progress_dialog is None:
            return
        if total > 0:
            self.scan_progress_dialog.setRange(0, total)
            self.scan_progress_dialog.setValue(value)
        else:
            self.scan_progress_dialog.setRange(0, 0)
        self.scan_progress_dialog.setLabelText(message)

    def on_scan_failed(self, error_message):
        self.statusbar.showMessage("Auto-discovery failed", 5000)
        show_info_messagebox(info_message=f"Discovery failed: {error_message}")

    def on_scan_cancelled(self):
        self.statusbar.showMessage("Auto-discovery cancelled", 5000)

    def on_scan_finished(self, found):
        self.auto_add_network_cameras(found)

    def _default_view_count_for_camera_total(self, camera_count):
        if camera_count <= 1:
            return 1
        if camera_count <= 4:
            return 4
        if camera_count <= 6:
            return 6
        if camera_count <= 9:
            return 9
        return 12

    def apply_default_view_count(self):
        if not self.view_mode_auto:
            return
        default_count = self._default_view_count_for_camera_total(len(self.active_camera_widgets))
        self.overview.set_visible_slots(default_count)

    def handle_view_count_change(self, value):
        if value == 'Auto':
            self.view_mode_auto = True
            self.apply_default_view_count()
            return

        self.view_mode_auto = False
        try:
            self.overview.set_visible_slots(int(value))
        except ValueError:
            self.overview.set_visible_slots(1)

    def findHardwareSources(self):
        """Adds camera sources to the Hardware source list"""
        available_cameras = QMediaDevices.videoInputs()

        for index, cam in enumerate(available_cameras):
            menu_item = QtWidgets.QWidgetAction(self)
            menu_item.setText(cam.description())
            menu_item.setCheckable(True)
            menu_item.triggered.connect(self.create_lambda(
                src=index, menu_item=menu_item, isNDI=False))
            self.menuAdd_Hardware.addAction(menu_item)

    def findNDISources(self):
        """Adds NDI sources to the NDI source list"""
        constants.NDI_SOURCE_LIST = get_ndi_sources()
        for index, cam in enumerate(constants.NDI_SOURCE_LIST):
            menu_item = QtWidgets.QWidgetAction(self)
            menu_item.setText(cam.ndi_name)
            menu_item.setCheckable(True)
            menu_item.triggered.connect(self.create_lambda(
                src=cam, menu_item=menu_item, isNDI=True))
            self.menuAdd_NDI.addAction(menu_item)

    def create_lambda(self, src, menu_item, isNDI):
        """
        Fixes MenuItem late assignment for Camera Sources by returning lambda statement
        :param src:
        :param menu_item:
        :param isNDI:
        :return:
        """
        return lambda: self.addCameraWidget(source=src, menu_item=menu_item, isNDI=isNDI, manager=self.manager)

    def addCameraWidget(self, source, menu_item, manager, isNDI=False):
        """Add NDI/Serial camera source from the menu to the FlowLayout"""

        if isinstance(source, str) and source in self.network_camera_urls:
            return

        camera_widget = CameraWidget(source=source, width=self.screen_width // 3, height=self.screen_height // 3,
                                     isNDI=isNDI, manager=self.manager)
        if isNDI is False and isinstance(source, int):
            constants.RUNNING_HARDWARE_CAMERA_WIDGETS.append(camera_widget)
        if isinstance(source, str):
            self.network_camera_urls.add(source)
        camera_widget.change_selection_signal.connect(self.updateElements)
        menu_item.triggered.disconnect()
        menu_item.triggered.connect(
            lambda index=source, item=menu_item: self.deleteCameraWidget(source=index, menu_item=item,
                                                                         camera_widget=camera_widget))
        self.watch_trainer.add_camera(camera_widget=camera_widget)
        self.flowLayout.addWidget(camera_widget)
        self.active_camera_widgets.append(camera_widget)
        self.overview.set_camera_widgets(self.active_camera_widgets)
        self.apply_default_view_count()
        camera_widget.show()

    def deleteCameraWidget(self, source, menu_item, camera_widget):
        """Remove NDI/Serial camera source from camera FlowLayout"""
        menu_item.triggered.disconnect()
        menu_item.triggered.connect(
            lambda index=source, item=menu_item: self.addCameraWidget(source=index, menu_item=item, manager=self.manager))
        self.watch_trainer.remove_camera(camera_widget=camera_widget)
        if camera_widget in constants.RUNNING_HARDWARE_CAMERA_WIDGETS:
            if camera_widget.ptz_controller is not None:
                constants.IN_USE_USB_PTZ_DEVICES.remove(
                    camera_widget.ptz_controller)
            constants.RUNNING_HARDWARE_CAMERA_WIDGETS.remove(camera_widget)
        if constants.CURRENT_ACTIVE_CAM_WIDGET == camera_widget:
            constants.CURRENT_ACTIVE_CAM_WIDGET = None
            self.updateElements()
        if camera_widget in self.active_camera_widgets:
            self.active_camera_widgets.remove(camera_widget)
        if isinstance(source, str) and source in self.network_camera_urls:
            self.network_camera_urls.remove(source)
        self.overview.set_camera_widgets(self.active_camera_widgets)
        self.apply_default_view_count()
        camera_widget.stop()
        camera_widget.deleteLater()

    def auto_add_network_cameras(self, found=None):
        """Auto-add discoverable IP cameras from provided discovery results."""
        if found is None:
            discovery = CameraAutoDiscovery()
            found = discovery.discover(credential_manager=self.credential_manager)

        if not found:
            self.statusbar.showMessage("No network cameras discovered", 5000)
            show_info_messagebox(info_message="No network cameras were discovered on local subnets.")
            return

        added = 0
        listed = 0
        for cam in found:
            rtsp_url = cam.get("onvif_stream_uri") or cam.get("suggested_rtsp_url")

            menu_item = QtWidgets.QWidgetAction(self)
            menu_item.setCheckable(True)
            menu_item.setText(f"{cam['label']} [{cam['communication_method']} | {cam['confidence']}]")

            if rtsp_url:
                menu_item.triggered.connect(self.create_lambda(
                    src=rtsp_url, menu_item=menu_item, isNDI=False))
            else:
                # non-RTSP candidates are listed but not auto-addable yet
                menu_item.setEnabled(False)

            self.menuAdd_IP_Cameras.addAction(menu_item)
            listed += 1

            # Auto-add immediately for low-friction onboarding
            if rtsp_url and rtsp_url not in self.network_camera_urls:
                self.addCameraWidget(source=rtsp_url, menu_item=menu_item, manager=self.manager, isNDI=False)
                added += 1
                self.camera_registry.upsert_camera(
                    ip=cam.get("ip", ""),
                    label=cam.get("label", rtsp_url),
                    rtsp_url=rtsp_url,
                    communication_method=cam.get("communication_method", "RTSP"),
                    confidence=cam.get("confidence", 0.5),
                    reconnect_policy='aggressive',
                )

            # Keep UI manageable: auto-add up to 12 discovered feeds in one pass
            if added >= 12:
                break

        self.statusbar.showMessage(f"Auto-discovery complete: added {added} / listed {listed} network camera candidates", 8000)
        show_info_messagebox(info_message=f"Discovery complete. Added {added} IP cameras automatically and listed {listed} candidates.")

    @staticmethod
    def _rtsp_host_port(rtsp_url):
        try:
            parsed = urlparse(rtsp_url)
            host = parsed.hostname
            port = parsed.port or 554
            return host, port
        except Exception:
            return None, None

    @staticmethod
    def _tcp_check(host, port, timeout=0.5):
        import socket
        if not host or not port:
            return False
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            return sock.connect_ex((host, port)) == 0
        except Exception:
            return False
        finally:
            try:
                sock.close()
            except Exception:
                pass

    def bootstrap_registry_cameras(self, max_count=12):
        """On startup, rehydrate enabled cameras from persistent registry."""
        enabled = self.camera_registry.list_enabled()
        count = 0
        for cam in enabled:
            rtsp_url = cam.get("rtsp_url")
            if not rtsp_url or rtsp_url in self.network_camera_urls:
                continue

            menu_item = QtWidgets.QWidgetAction(self)
            menu_item.setCheckable(True)
            menu_item.setText(f"{cam.get('label', 'IP Cam')} [{cam.get('communication_method', 'RTSP')} | {cam.get('confidence', 0)}]")
            menu_item.triggered.connect(self.create_lambda(
                src=rtsp_url, menu_item=menu_item, isNDI=False))
            self.menuAdd_IP_Cameras.addAction(menu_item)

            self.addCameraWidget(source=rtsp_url, menu_item=menu_item, manager=self.manager, isNDI=False)
            count += 1
            if count >= max_count:
                break

    def run_registry_health_check(self):
        """Periodic health checks and reconnect behavior based on registry policy."""
        try:
            enabled = self.camera_registry.list_enabled()
        except Exception:
            # Fail-safe: never let health timer crash or spam traces.
            return

        for cam in enabled:
            try:
                rtsp_url = cam.get("rtsp_url")
                host, port = self._rtsp_host_port(rtsp_url)
                healthy = self._tcp_check(host, port)

                if healthy:
                    self.camera_registry.update_health(rtsp_url, status="online")
                else:
                    self.camera_registry.update_health(rtsp_url, status="offline", last_error="TCP connect failed")

                # reconnect policy: re-add when healthy and not currently loaded
                if healthy and cam.get("reconnect_policy") == "aggressive" and rtsp_url not in self.network_camera_urls:
                    menu_item = QtWidgets.QWidgetAction(self)
                    menu_item.setCheckable(True)
                    menu_item.setText(f"{cam.get('label', 'IP Cam')} [{cam.get('communication_method', 'RTSP')} | {cam.get('confidence', 0)}]")
                    menu_item.triggered.connect(self.create_lambda(
                        src=rtsp_url, menu_item=menu_item, isNDI=False))
                    self.menuAdd_IP_Cameras.addAction(menu_item)
                    self.addCameraWidget(source=rtsp_url, menu_item=menu_item, manager=self.manager, isNDI=False)
            except Exception:
                continue

    def updateElements(self):
        """
        Update UI elements like FaceDropDownMenu and Enable Track Checkbox when a CameraWidget is activated/deactivated
        """
        if constants.CURRENT_ACTIVE_CAM_WIDGET is None:
            print("No Camera Source is active")
            self.select_face_dropdown.setEnabled(False)
            self.select_face_dropdown.setCurrentText('')
            self.enable_track.setEnabled(False)
            self.enable_track.setChecked(False)
            self.assign_network_ptz_btn.hide()
            self.unassign_network_ptz_btn.hide()
            self.assign_usb_ptz_btn.hide()
            self.unassign_usb_ptz_btn.hide()
        else:
            print(f"{constants.CURRENT_ACTIVE_CAM_WIDGET.objectName()} is active")
            self.select_face_dropdown.setEnabled(True)
            if constants.CURRENT_ACTIVE_CAM_WIDGET.tracked_name is None:
                print("no tracked name")
                self.select_face_dropdown.setCurrentText('')
                self.enable_track.blockSignals(True)
                self.enable_track.setEnabled(False)
                self.enable_track.setChecked(False)
                self.enable_track.blockSignals(False)
            else:
                self.select_face_dropdown.setCurrentText(
                    constants.CURRENT_ACTIVE_CAM_WIDGET.tracked_name)
                self.enable_track.blockSignals(True)
                self.enable_track.setChecked(True)
                self.enable_track.blockSignals(False)
                if constants.CURRENT_ACTIVE_CAM_WIDGET.is_tracking is False:
                    self.enable_track.blockSignals(True)
                    self.enable_track.setChecked(False)
                    self.enable_track.blockSignals(False)
                    print(
                        f"a tracked name is {constants.CURRENT_ACTIVE_CAM_WIDGET.tracked_name} but tracking is disabled")
                else:
                    self.enable_track.blockSignals(True)
                    self.enable_track.setChecked(True)
                    self.enable_track.blockSignals(False)
                    print(
                        f"a tracked name is {constants.CURRENT_ACTIVE_CAM_WIDGET.tracked_name} and tracking is enabled")
            if constants.CURRENT_ACTIVE_CAM_WIDGET.isNDI and constants.CURRENT_ACTIVE_CAM_WIDGET.ptz_controller is None:
                self.unassign_network_ptz_btn.hide()
                self.assign_network_ptz_btn.show()
            elif constants.CURRENT_ACTIVE_CAM_WIDGET.isNDI and constants.CURRENT_ACTIVE_CAM_WIDGET.ptz_controller is not None:
                self.unassign_network_ptz_btn.show()
                self.assign_network_ptz_btn.hide()
            else:
                self.assign_network_ptz_btn.hide()
                self.assign_network_ptz_btn.hide()

                self.refreshUSBBtn()

    def selected_face_change(self):
        """
        Update Current Active CameraWidget's Tracked Name and UI
        """
        if constants.CURRENT_ACTIVE_CAM_WIDGET is not None:
            if self.select_face_dropdown.currentText() == '':
                constants.CURRENT_ACTIVE_CAM_WIDGET.set_tracked_name(None)
                self.enable_track.setEnabled(False)
                self.enable_track.setChecked(False)
            else:
                constants.CURRENT_ACTIVE_CAM_WIDGET.set_tracked_name(
                    self.select_face_dropdown.currentText())
                self.enable_track.setEnabled(True)

    def enable_track_change(self):
        """
        Update Current Active CameraWidget's Enable/Disable Tracking and UI
        """
        if constants.CURRENT_ACTIVE_CAM_WIDGET is not None:
            print(f'setting track button for {self.enable_track.isChecked()}')
            constants.CURRENT_ACTIVE_CAM_WIDGET.reset_tracking()

    def update_face_dropdown(self, event):
        """
        Update Face Dropdown List when faces are added or removed
        """
        current_text_temp = self.select_face_dropdown.currentText()
        self.select_face_dropdown.clear()
        self.select_face_dropdown.addItem('')

        known_face_encodings = {'encodings': [], 'names': []}

        # Load the known face encodings
        if os.path.exists(constants.ENCODINGS_PATH):
            with open(constants.ENCODINGS_PATH, "rb") as f:
                known_face_encodings = pickle.load(f)

        # Add the names to the dropdown
        for name in set(known_face_encodings['names']):
            self.select_face_dropdown.addItem(name)

        if self.select_face_dropdown.findText(current_text_temp) != -1:
            self.select_face_dropdown.setCurrentText(current_text_temp)

    def set_manual_control(self, device):
        """Initializing manual camera control. ONLY USB devices for now."""
        for cam in constants.IN_USE_USB_PTZ_DEVICES:
            if cam.id == device:
                constants.CURRENT_ACTIVE_PTZ_DEVICE = cam
                self.unassign_usb_ptz_btn.show()
                break
        if constants.CURRENT_ACTIVE_PTZ_DEVICE is None:
            constants.CURRENT_ACTIVE_PTZ_DEVICE = ViscaPTZ(device_id=device)

        # shows button depending on if device has already been assigned to a camera source
        if device != "":
            # Enable Button Commands
            self.up_left_btn.clicked.connect(
                constants.CURRENT_ACTIVE_PTZ_DEVICE.move_left_up)
            self.up_btn.clicked.connect(
                constants.CURRENT_ACTIVE_PTZ_DEVICE.move_up)
            self.up_right_btn.clicked.connect(
                constants.CURRENT_ACTIVE_PTZ_DEVICE.move_right_up)
            self.left_btn.clicked.connect(
                constants.CURRENT_ACTIVE_PTZ_DEVICE.move_left)
            self.right_btn.clicked.connect(
                constants.CURRENT_ACTIVE_PTZ_DEVICE.move_right)
            self.down_left_btn.clicked.connect(
                constants.CURRENT_ACTIVE_PTZ_DEVICE.move_left_down)
            self.down_btn.clicked.connect(
                constants.CURRENT_ACTIVE_PTZ_DEVICE.move_down)
            self.down_right_btn.clicked.connect(
                constants.CURRENT_ACTIVE_PTZ_DEVICE.move_right_down)
            self.home_btn.clicked.connect(
                constants.CURRENT_ACTIVE_PTZ_DEVICE.move_home)
            self.zoom_in_btn.clicked.connect(
                constants.CURRENT_ACTIVE_PTZ_DEVICE.zoom_in)
            self.zoom_out_btn.clicked.connect(
                constants.CURRENT_ACTIVE_PTZ_DEVICE.zoom_out)
            self.menu_btn.clicked.connect(
                constants.CURRENT_ACTIVE_PTZ_DEVICE.menu)
            self.reset_btn.clicked.connect(
                constants.CURRENT_ACTIVE_PTZ_DEVICE.reset)
        else:
            # Disable Button Commands
            constants.CURRENT_ACTIVE_PTZ_DEVICE = None
            try:
                self.up_left_btn.clicked.disconnect()
                self.up_btn.clicked.disconnect()
                self.up_right_btn.clicked.disconnect()
                self.left_btn.clicked.disconnect()
                self.right_btn.clicked.disconnect()
                self.down_left_btn.clicked.disconnect()
                self.down_btn.clicked.disconnect()
                self.down_right_btn.clicked.disconnect()
                self.home_btn.clicked.disconnect()
                self.zoom_in_btn.clicked.disconnect()
                self.zoom_out_btn.clicked.disconnect()
                self.menu_btn.clicked.disconnect()
                self.reset_btn.clicked.disconnect()
            except Exception as e:
                print(e)

        self.refreshUSBBtn()

    def assign_usb_ptz_dlg(self):
        """Launch the Assign USB PTZ to Camera Source dialog."""
        if not constants.RUNNING_HARDWARE_CAMERA_WIDGETS:
            show_info_messagebox(
                info_message="Please add a Hardware Camera Source")
        elif constants.CURRENT_ACTIVE_CAM_WIDGET is None:
            show_info_messagebox(
                info_message="Please select a Hardware Camera Source")
        else:
            constants.CURRENT_ACTIVE_CAM_WIDGET.set_ptz(
                control=constants.CURRENT_ACTIVE_PTZ_DEVICE, isUSB=True)
            constants.IN_USE_USB_PTZ_DEVICES.append(
                constants.CURRENT_ACTIVE_PTZ_DEVICE)
            constants.ASSIGNED_USB_PTZ_CAMERA_WIDGETS.append(
                constants.CURRENT_ACTIVE_CAM_WIDGET)
            self.assign_usb_ptz_btn.hide()
            self.unassign_usb_ptz_btn.show()

    def unassign_usb_ptz(self):
        """Allow User to Unassign current USB PTZ device from Camera Source"""
        if constants.CURRENT_ACTIVE_CAM_WIDGET is None:
            show_info_messagebox(
                info_message="Please select the Hardware Camera Source")
        else:
            constants.CURRENT_ACTIVE_CAM_WIDGET.set_ptz(control=None)
            constants.IN_USE_USB_PTZ_DEVICES.remove(
                constants.CURRENT_ACTIVE_PTZ_DEVICE)

    def closeEvent(self, event):
        """Handle application close event - cleanup resources"""
        try:
            # Stop failsafe node if available
            if CLOUD_SERVICES_AVAILABLE and hasattr(self, 'failsafe_node') and self.failsafe_node:
                self.failsafe_node.stop()
        except Exception as e:
            import logging
            logging.error(f"Error stopping failsafe node: {e}")
        
        # Clean up scan thread if running
        try:
            self._cleanup_scan_thread()
        except Exception as e:
            import logging
            logging.error(f"Error cleaning up scan thread: {e}")
        
        event.accept()

    def assign_network_ptz_dlg(self):
        """Launch the Assign Network PTZ to Camera Source dialog."""
        if constants.CURRENT_ACTIVE_CAM_WIDGET is None:
            print("Need to select or add a camera")
        else:
            dlg = AssignNetworkPTZDlg(
                self, camera=constants.CURRENT_ACTIVE_CAM_WIDGET)
            dlg.closeEvent = self.refreshNetworkBtn
            dlg.exec()

    def unassign_network_ptz(self):
        """Allow User to Unassign current Network PTZ device from Camera Source"""
        constants.CURRENT_ACTIVE_CAM_WIDGET.set_ptz(control=None)
        self.unassign_network_ptz_btn.hide()
        self.assign_network_ptz_btn.show()

    def refreshUSBBtn(self, event=None):
        """Check is USB PTZ is assigned and change assignment button if so"""
        if constants.CURRENT_ACTIVE_PTZ_DEVICE is not None:
            if constants.CURRENT_ACTIVE_CAM_WIDGET is not None:
                if constants.CURRENT_ACTIVE_CAM_WIDGET.ptz_controller is not None:
                    if constants.CURRENT_ACTIVE_PTZ_DEVICE == constants.CURRENT_ACTIVE_CAM_WIDGET.ptz_controller:
                        self.unassign_usb_ptz_btn.show()
                        return
                self.assign_usb_ptz_btn.hide()
                self.unassign_usb_ptz_btn.hide()
            if constants.CURRENT_ACTIVE_PTZ_DEVICE not in constants.IN_USE_USB_PTZ_DEVICES:
                self.assign_usb_ptz_btn.show()
        else:
            self.assign_usb_ptz_btn.hide()
            self.unassign_usb_ptz_btn.hide()

    def refreshNetworkBtn(self, event):
        """Check is Network PTZ is assigned and change assignment button if so"""
        if constants.CURRENT_ACTIVE_CAM_WIDGET is not None:
            self.unassign_network_ptz_btn.show()
            self.assign_network_ptz_btn.hide()
        else:
            self.assign_network_ptz_btn.show()
            self.unassign_network_ptz_btn.hide()

    def translateUi(self, AutoPTZ):
        """Translate Menu, Buttons, and Labels through localization"""
        _translate = QtCore.QCoreApplication.translate
        AutoPTZ.setWindowTitle(_translate("AutoPTZ", "AI-Stalker"))
        self.enable_track.setText(_translate("AutoPTZ", "Enable Tracking"))
        self.select_face_label.setText(_translate("AutoPTZ", "Select Face"))
        self.assign_network_ptz_btn.setText(
            _translate("AutoPTZ", "Assign Network PTZ"))
        self.unassign_network_ptz_btn.setText(
            _translate("AutoPTZ", "Unassign Network PTZ"))
        self.formTabWidget.setTabText(self.formTabWidget.indexOf(
            self.selectedCamPage), _translate("AutoPTZ", "Auto"))
        self.select_camera_label.setText(
            _translate("AutoPTZ", "Select Camera"))
        self.down_right_btn.setText(_translate("AutoPTZ", "↘"))
        self.up_btn.setText(_translate("AutoPTZ", "↑"))
        self.up_left_btn.setText(_translate("AutoPTZ", "↖"))
        self.left_btn.setText(_translate("AutoPTZ", "←"))
        self.down_left_btn.setText(_translate("AutoPTZ", "↙"))
        self.up_right_btn.setText(_translate("AutoPTZ", "↗"))
        self.right_btn.setText(_translate("AutoPTZ", "→"))
        self.down_btn.setText(_translate("AutoPTZ", "↓"))
        self.home_btn.setText(_translate("AutoPTZ", "⌂"))
        self.zoom_in_btn.setText(_translate("AutoPTZ", "Zoom +"))
        self.zoom_out_btn.setText(_translate("AutoPTZ", "Zoom -"))
        self.focus_plus_btn.setText(_translate("AutoPTZ", "Focus +"))
        self.focus_minus_btn.setText(_translate("AutoPTZ", "Focus -"))
        self.menu_btn.setText(_translate("AutoPTZ", "Menu"))
        self.reset_btn.setText(_translate("AutoPTZ", "Reset"))
        self.assign_usb_ptz_btn.setText(
            _translate("AutoPTZ", "Assign USB PTZ"))
        self.unassign_usb_ptz_btn.setText(
            _translate("AutoPTZ", "Unassign USB PTZ"))
        self.formTabWidget.setTabText(self.formTabWidget.indexOf(self.manualControlPage),
                                      _translate("AutoPTZ", "Manual"))
        self.menuFile.setTitle(_translate("AutoPTZ", "File"))
        self.menuSource.setTitle(_translate("AutoPTZ", "Sources"))
        self.menuFacial_Recognition.setTitle(
            _translate("AutoPTZ", "Facial Recognition"))
        self.menuHelp.setTitle(_translate("AutoPTZ", "Help"))
        self.actionOpen.setText(_translate("AutoPTZ", "Open"))
        self.actionSave.setText(_translate("AutoPTZ", "Save"))
        self.actionSave_as.setText(_translate("AutoPTZ", "Save As"))
        self.actionClose.setText(_translate("AutoPTZ", "Close"))
        self.actionAdd_IP.setText(_translate("AutoPTZ", "Auto Add Network Cameras"))
        self.menuAdd_NDI.setTitle(_translate("AutoPTZ", "Add NDI"))
        self.menuAdd_Hardware.setTitle(_translate("AutoPTZ", "Add Hardware"))
        self.menuAdd_IP_Cameras.setTitle(_translate("AutoPTZ", "Add IP Cameras"))
        self.actionManage_IP_Credentials.setText(_translate("AutoPTZ", "Manage IP Credentials"))
        if AI_WIZARD_AVAILABLE:
            self.actionSetupWizard.setText(_translate("AutoPTZ", "🤖 AI Setup Wizard"))
        self.actionEdit.setText(_translate("AutoPTZ", "Edit Setup"))
        self.actionContact.setText(_translate("AutoPTZ", "Contact"))
        self.actionAbout.setText(_translate("AutoPTZ", "About"))
        if CLOUD_SERVICES_AVAILABLE:
            self.actionCloudSettings.setText(_translate("AutoPTZ", "☁️ Cloud Backup & Settings"))
        self.actionAdd_Face.setText(_translate("AutoPTZ", "Add Face"))
        self.actionRemove_Face.setText(_translate("AutoPTZ", "Remove Face"))
        self.actionReset_Database.setText(
            _translate("AutoPTZ", "Reset Database"))

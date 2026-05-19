from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QLabel, QComboBox, QTextEdit, QGroupBox, QSplitter
from PySide6.QtCore import Qt
from logic.recording.recorder import Recorder
from logic.image_processing.facial_recognition import FacialRecognition
import shared.constants as constants


class RecordedLibrary(QWidget):
    """Visitations dashboard with search, filters, and event detail viewer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.recorder = Recorder()
        self.layout = QVBoxLayout(self)

        self.visitations_group = QGroupBox('Visitations Snapshot', self)
        visitations_layout = QVBoxLayout(self.visitations_group)
        self.visitations_present_label = QLabel('Present now: Loading...', self)
        self.visitations_today_label = QLabel('Today: Loading...', self)
        self.visitations_recent_label = QLabel('Recent check-ins/check-outs will appear here.', self)
        self.visitations_present_label.setWordWrap(True)
        self.visitations_today_label.setWordWrap(True)
        self.visitations_recent_label.setWordWrap(True)
        self.visitations_refresh_btn = QPushButton('Refresh Visitations', self)
        self.visitations_refresh_btn.clicked.connect(self.refresh_visitations_summary)
        visitations_layout.addWidget(self.visitations_present_label)
        visitations_layout.addWidget(self.visitations_today_label)
        visitations_layout.addWidget(self.visitations_recent_label)
        visitations_layout.addWidget(self.visitations_refresh_btn)

        self.person_history_group = QGroupBox('Person Visitations History', self)
        person_layout = QVBoxLayout(self.person_history_group)
        self.person_selector = QComboBox(self)
        self.person_selector.currentIndexChanged.connect(self.refresh_person_history)
        self.profile_rename_row = QHBoxLayout()
        self.profile_name_edit = QLineEdit(self)
        self.profile_name_edit.setPlaceholderText('Rename selected profile...')
        self.rename_profile_btn = QPushButton('Rename Profile', self)
        self.rename_profile_btn.clicked.connect(self.rename_selected_profile)
        self.profile_rename_row.addWidget(self.profile_name_edit)
        self.profile_rename_row.addWidget(self.rename_profile_btn)
        self.person_history_text = QTextEdit(self)
        self.person_history_text.setReadOnly(True)
        self.person_history_refresh_btn = QPushButton('Refresh Person History', self)
        self.person_history_refresh_btn.clicked.connect(self.refresh_person_history)
        person_layout.addWidget(QLabel('Person:'))
        person_layout.addWidget(self.person_selector)
        person_layout.addLayout(self.profile_rename_row)
        person_layout.addWidget(self.person_history_text)
        person_layout.addWidget(self.person_history_refresh_btn)

        self.camera_summary_group = QGroupBox('Camera Visitations Summary', self)
        camera_layout = QVBoxLayout(self.camera_summary_group)
        self.camera_selector = QComboBox(self)
        self.camera_selector.currentIndexChanged.connect(self.refresh_camera_summary)
        self.camera_summary_text = QTextEdit(self)
        self.camera_summary_text.setReadOnly(True)
        self.camera_summary_refresh_btn = QPushButton('Refresh Camera Summary', self)
        self.camera_summary_refresh_btn.clicked.connect(self.refresh_camera_summary)
        camera_layout.addWidget(QLabel('Camera:'))
        camera_layout.addWidget(self.camera_selector)
        camera_layout.addWidget(self.camera_summary_text)
        camera_layout.addWidget(self.camera_summary_refresh_btn)

        # Search bar
        top = QHBoxLayout()
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText('Search by name, notes, event...')
        self.search_input.returnPressed.connect(self.perform_search)
        self.search_btn = QPushButton('Search', self)
        self.search_btn.clicked.connect(self.perform_search)
        top.addWidget(self.search_input)
        top.addWidget(self.search_btn)

        # Filters
        filters = QHBoxLayout()
        self.camera_filter = QComboBox(self)
        self.camera_filter.addItem('All Cameras')
        self.camera_filter.currentIndexChanged.connect(self.on_filter_changed)
        self.event_filter = QComboBox(self)
        self.event_filter.addItem('All Events')
        self.event_filter.currentIndexChanged.connect(self.on_filter_changed)
        self.refresh_btn = QPushButton('Refresh', self)
        self.refresh_btn.clicked.connect(self.refresh_filters)
        filters.addWidget(QLabel('Camera:'))
        filters.addWidget(self.camera_filter)
        filters.addWidget(QLabel('Event:'))
        filters.addWidget(self.event_filter)
        filters.addWidget(self.refresh_btn)

        # Results list and detail view with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.results = QListWidget(self)
        self.results.itemSelectionChanged.connect(self.on_event_selected)
        
        # Detail pane
        detail_group = QGroupBox('Event Details', self)
        detail_layout = QVBoxLayout(detail_group)
        self.detail_text = QTextEdit(self)
        self.detail_text.setReadOnly(True)
        detail_layout.addWidget(self.detail_text)
        
        # Stats pane
        stats_group = QGroupBox('Event Statistics', self)
        stats_layout = QVBoxLayout(stats_group)
        self.stats_label = QLabel('Loading statistics...', self)
        stats_layout.addWidget(self.stats_label)

        splitter.addWidget(self.results)
        detail_splitter = QSplitter(Qt.Orientation.Vertical)
        detail_splitter.addWidget(detail_group)
        detail_splitter.addWidget(stats_group)
        splitter.addWidget(detail_splitter)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        self.layout.addLayout(top)
        self.layout.addLayout(filters)
        self.layout.addWidget(self.visitations_group)
        self.layout.addWidget(self.person_history_group)
        self.layout.addWidget(self.camera_summary_group)
        self.layout.addWidget(splitter)

        # load some initial entries and populate filters
        self.refresh_filters()
        self.perform_search()
        self.refresh_visitations_summary()
        self.refresh_person_filters()
        self.refresh_camera_filters()

    def refresh_filters(self):
        """Refresh available cameras and event types from database"""
        # Get all unique cameras
        all_records = self.recorder.search_records(limit=10000)
        cameras = set()
        events = set()
        for r in all_records:
            if r['camera']:
                cameras.add(r['camera'])
            if r['event_type']:
                events.add(r['event_type'])
        
        # Update camera filter
        current_camera = self.camera_filter.currentText()
        self.camera_filter.blockSignals(True)
        self.camera_filter.clear()
        self.camera_filter.addItem('All Cameras')
        for cam in sorted(cameras):
            self.camera_filter.addItem(cam)
        if current_camera != 'All Cameras' and current_camera in cameras:
            self.camera_filter.setCurrentText(current_camera)
        self.camera_filter.blockSignals(False)
        
        # Update event filter
        current_event = self.event_filter.currentText()
        self.event_filter.blockSignals(True)
        self.event_filter.clear()
        self.event_filter.addItem('All Events')
        for evt in sorted(events):
            self.event_filter.addItem(evt)
        if current_event != 'All Events' and current_event in events:
            self.event_filter.setCurrentText(current_event)
        self.event_filter.blockSignals(False)
        
        # Update stats
        self.update_stats()

    def refresh_person_filters(self):
        """Refresh people dropdown from visitation records."""
        current_person = self.person_selector.currentText() if self.person_selector.count() else ''
        people = []
        attendance_manager = getattr(constants, 'ATTENDANCE_MANAGER', None)
        if attendance_manager is not None:
            people = attendance_manager.get_people()
        else:
            records = self.recorder.search_records(event_type='check-in', limit=10000)
            people = sorted({r.get('person_name') for r in records if r.get('person_name')})

        for name in FacialRecognition.get_known_names():
            if name not in people:
                people.append(name)
        people = sorted({p for p in people if p}, key=lambda x: x.lower())

        self.person_selector.blockSignals(True)
        self.person_selector.clear()
        self.person_selector.addItem('All People')
        for person in people:
            self.person_selector.addItem(person)
        if current_person and current_person in people:
            self.person_selector.setCurrentText(current_person)
        self.person_selector.blockSignals(False)

    def rename_selected_profile(self):
        """Rename the selected profile in both face encodings and visitation history."""
        old_name = self.person_selector.currentText()
        new_name = self.profile_name_edit.text().strip()
        if not old_name or old_name == 'All People' or not new_name:
            return
        if old_name == new_name:
            return

        renamed_face = FacialRecognition.rename_label(old_name, new_name)
        attendance_manager = getattr(constants, 'ATTENDANCE_MANAGER', None)
        renamed_history = False
        if attendance_manager is not None:
            renamed_history = attendance_manager.rename_person(old_name, new_name)

        if renamed_face or renamed_history:
            self.profile_name_edit.clear()
            self.refresh_person_filters()
            self.refresh_visitations_summary()
            self.refresh_person_history()
            self.perform_search()
            self.detail_text.setPlainText(f'Renamed {old_name} to {new_name}.')


    def refresh_camera_filters(self):
        """Refresh camera dropdown from visitation records."""
        current_camera = self.camera_selector.currentText() if self.camera_selector.count() else ''
        cameras = []
        attendance_manager = getattr(constants, 'ATTENDANCE_MANAGER', None)
        if attendance_manager is not None:
            camera_summaries = attendance_manager.get_camera_summary()
            cameras = [row.get('camera') for row in camera_summaries if row.get('camera')]
        else:
            records = self.recorder.search_records(event_type='check-in', limit=10000)
            cameras = sorted({r.get('camera') for r in records if r.get('camera')})

        self.camera_selector.blockSignals(True)
        self.camera_selector.clear()
        self.camera_selector.addItem('All Cameras')
        for camera in cameras:
            self.camera_selector.addItem(camera)
        if current_camera and current_camera in cameras:
            self.camera_selector.setCurrentText(current_camera)
        self.camera_selector.blockSignals(False)

    def on_filter_changed(self):
        """Called when filter selection changes"""
        self.perform_search()

    def on_event_selected(self):
        """Called when an event is selected in the list"""
        current_item = self.results.currentItem()
        if current_item:
            event_data = current_item.data(Qt.ItemDataRole.UserRole)
            if event_data:
                detail_text = f"""
Event ID: {event_data.get('id', 'N/A')}
Timestamp: {event_data.get('timestamp', 'N/A')}
Camera: {event_data.get('camera', 'N/A')}
Event Type: {event_data.get('event_type', 'N/A')}
Person: {event_data.get('person_name', 'Unknown')}
MAC Address: {event_data.get('mac_addr', 'N/A')}
BLE Tag: {event_data.get('ble_tag', 'N/A')}
Phone: {event_data.get('phone', 'N/A')}
Notes: {event_data.get('notes', 'N/A')}
"""
                self.detail_text.setText(detail_text)

    def update_stats(self):
        """Update event statistics display"""
        all_records = self.recorder.search_records(limit=10000)
        event_counts = {}
        for r in all_records:
            evt_type = r['event_type']
            event_counts[evt_type] = event_counts.get(evt_type, 0) + 1
        
        stats_text = "Event Type Statistics:\n\n"
        for evt_type in sorted(event_counts.keys()):
            stats_text += f"• {evt_type}: {event_counts[evt_type]} events\n"
        stats_text += f"\nTotal Events: {len(all_records)}"
        
        self.stats_label.setText(stats_text)

    def refresh_visitations_summary(self):
        """Show current present people and today's visitation counts."""
        attendance_manager = getattr(constants, 'ATTENDANCE_MANAGER', None)
        if attendance_manager is None:
            self.visitations_present_label.setText('Present now: visitations manager unavailable')
            self.visitations_today_label.setText('Today: visitations manager unavailable')
            self.visitations_recent_label.setText('Open the app through the main window to enable live visitation tracking.')
            return

        snapshot = attendance_manager.get_status_snapshot()
        present = snapshot.get('present', [])
        summary = snapshot.get('summary', {})

        present_text = ', '.join(
            f"{row.get('person_name')} @ {row.get('last_camera') or 'unknown camera'}"
            for row in present
        ) or 'Nobody currently marked present.'

        self.visitations_present_label.setText(f"Present now: {present_text}")
        self.visitations_today_label.setText(
            f"Today ({summary.get('date', 'N/A')}): {summary.get('check_ins', 0)} check-ins, {summary.get('check_outs', 0)} check-outs, {summary.get('total_events', 0)} total events"
        )

        recent_records = [r for r in summary.get('records', []) if r.get('event_type') in {'check-in', 'check-out'}][:5]
        if recent_records:
            recent_text = 'Recent visitation events:\n' + '\n'.join(
                f"• [{row.get('timestamp')}] {row.get('person_name') or 'Unknown'} - {row.get('event_type')}"
                for row in recent_records
            )
        else:
            recent_text = 'Recent visitation events: none yet.'
        self.visitations_recent_label.setText(recent_text)

    def refresh_person_history(self, *_):
        """Show the selected person's visitation history."""
        attendance_manager = getattr(constants, 'ATTENDANCE_MANAGER', None)
        if attendance_manager is None:
            self.person_history_text.setPlainText('Visitations manager unavailable.')
            return

        person_name = self.person_selector.currentText()
        if not person_name or person_name == 'All People':
            self.person_history_text.setPlainText('Choose a person to see their visitation history.')
            self.profile_name_edit.setText('')
            return

        self.profile_name_edit.setText(person_name)

        history = attendance_manager.get_person_history(person_name, limit=50)
        if not history:
            self.person_history_text.setPlainText(f'No visitation history found for {person_name}.')
            return

        lines = [f'Visitation history for {person_name}:', '']
        for row in history:
            lines.append(
                f"• [{row.get('timestamp')}] {row.get('event_type')} @ {row.get('camera') or 'unknown camera'}"
            )
            notes = row.get('notes')
            if notes:
                lines.append(f"  - {notes}")
        self.person_history_text.setPlainText('\n'.join(lines))

    def refresh_camera_summary(self, *_):
        """Show a camera-wise visitation summary."""
        attendance_manager = getattr(constants, 'ATTENDANCE_MANAGER', None)
        if attendance_manager is None:
            self.camera_summary_text.setPlainText('Visitations manager unavailable.')
            return

        camera_name = self.camera_selector.currentText()
        if not camera_name or camera_name == 'All Cameras':
            summaries = attendance_manager.get_camera_summary()
            if not summaries:
                self.camera_summary_text.setPlainText('No camera visitation data yet.')
                return

            lines = ['Camera visitation summary:', '']
            for row in summaries:
                lines.append(
                    f"• {row.get('camera')}: {row.get('check_ins', 0)} check-ins, {row.get('check_outs', 0)} check-outs, {row.get('total_events', 0)} total events"
                )
            self.camera_summary_text.setPlainText('\n'.join(lines))
            return

        summaries = attendance_manager.get_camera_summary(camera=camera_name)
        if not summaries:
            self.camera_summary_text.setPlainText(f'No visitation data found for {camera_name}.')
            return

        row = summaries[0]
        lines = [
            f'Camera visitation summary for {camera_name}:',
            '',
            f"Check-ins: {row.get('check_ins', 0)}",
            f"Check-outs: {row.get('check_outs', 0)}",
            f"Total events: {row.get('total_events', 0)}",
            f"Last event: {row.get('last_event_at') or 'N/A'}",
            '',
            'Recent events:'
        ]
        recent_events = row.get('recent_events', [])
        for event in recent_events:
            lines.append(
                f"• [{event.get('timestamp')}] {event.get('person_name') or 'Unknown'} - {event.get('event_type')}"
            )
        self.camera_summary_text.setPlainText('\n'.join(lines))

    def perform_search(self):
        q = self.search_input.text().strip()
        camera = None if self.camera_filter.currentIndex() == 0 else self.camera_filter.currentText()
        event_type = None if self.event_filter.currentIndex() == 0 else self.event_filter.currentText()
        rows = self.recorder.search_records(query=q, camera=camera, event_type=event_type, limit=500)
        self.results.clear()
        self.detail_text.clear()
        for r in rows:
            item = QListWidgetItem(f"[{r['timestamp']}] {r['camera']} - {r['event_type']} - {r.get('person_name') or 'Unknown'}")
            item.setData(Qt.ItemDataRole.UserRole, r)
            self.results.addItem(item)
        self.refresh_visitations_summary()
        self.refresh_person_filters()
        self.refresh_camera_filters()

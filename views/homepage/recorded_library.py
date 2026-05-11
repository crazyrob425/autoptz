from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QLabel, QComboBox, QTextEdit, QGroupBox, QSplitter
from PySide6.QtCore import Qt
from logic.recording.recorder import Recorder


class RecordedLibrary(QWidget):
    """Recorded events library with search, filters, and event detail viewer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.recorder = Recorder()
        self.layout = QVBoxLayout(self)

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
        self.layout.addWidget(splitter)

        # load some initial entries and populate filters
        self.refresh_filters()
        self.perform_search()

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

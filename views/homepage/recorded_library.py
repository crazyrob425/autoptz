from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QLabel, QComboBox
from PySide6.QtCore import Qt
from logic.recording.recorder import Recorder


class RecordedLibrary(QWidget):
    """Simple recorded library UI with search and filters backed by Recorder."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.recorder = Recorder()
        self.layout = QVBoxLayout(self)

        # Search bar
        top = QHBoxLayout()
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText('Search by name, notes, event...')
        self.search_btn = QPushButton('Search', self)
        self.search_btn.clicked.connect(self.perform_search)
        top.addWidget(self.search_input)
        top.addWidget(self.search_btn)

        # Filters
        filters = QHBoxLayout()
        self.camera_filter = QComboBox(self)
        self.camera_filter.addItem('All Cameras')
        self.event_filter = QComboBox(self)
        self.event_filter.addItem('All Events')
        filters.addWidget(QLabel('Camera:'))
        filters.addWidget(self.camera_filter)
        filters.addWidget(QLabel('Event:'))
        filters.addWidget(self.event_filter)

        # Results list
        self.results = QListWidget(self)

        self.layout.addLayout(top)
        self.layout.addLayout(filters)
        self.layout.addWidget(self.results)

        # load some initial entries
        self.perform_search()

    def perform_search(self):
        q = self.search_input.text().strip()
        camera = None if self.camera_filter.currentIndex() == 0 else self.camera_filter.currentText()
        event_type = None if self.event_filter.currentIndex() == 0 else self.event_filter.currentText()
        rows = self.recorder.search_records(query=q, camera=camera, event_type=event_type, limit=500)
        self.results.clear()
        for r in rows:
            item = QListWidgetItem(f"[{r['timestamp']}] {r['camera']} - {r['event_type']} - {r.get('person_name') or 'Unknown'}")
            item.setData(Qt.ItemDataRole.UserRole, r)
            self.results.addItem(item)

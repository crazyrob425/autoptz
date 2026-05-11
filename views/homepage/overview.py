from PySide6.QtWidgets import QWidget, QLabel, QGridLayout
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
import shared.constants as constants


class GridOverview(QWidget):
    """Responsive grid overview showing up to 12 camera snapshots."""

    def __init__(self, parent=None, slots=12):
        super().__init__(parent)
        self.slots = slots
        self.visible_slots = 1
        self.camera_widgets = []
        self.layout = QGridLayout(self)
        self.layout.setSpacing(8)
        self.labels = []
        for i in range(self.slots):
            lbl = QLabel(self)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setText(f"Camera {i + 1}")
            lbl.setStyleSheet('background:#111; color:#ddd; border-radius:6px;')
            lbl.setMinimumSize(160, 90)
            self.labels.append(lbl)

        self._relayout_labels()

        # timer to refresh snapshots
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(500)

    def set_visible_slots(self, count):
        count = max(1, min(self.slots, int(count)))
        if self.visible_slots == count:
            return
        self.visible_slots = count
        self._relayout_labels()

    def set_camera_widgets(self, widgets):
        self.camera_widgets = list(widgets)

    def _columns_for_visible_count(self, count):
        # Keep large counts readable and responsive
        if count <= 1:
            return 1
        if count <= 4:
            return 2
        if count <= 6:
            return 3
        return 4

    def _relayout_labels(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item and item.widget():
                item.widget().setParent(self)

        columns = self._columns_for_visible_count(self.visible_slots)

        for i, lbl in enumerate(self.labels):
            if i < self.visible_slots:
                lbl.show()
                r = i // columns
                c = i % columns
                self.layout.addWidget(lbl, r, c)
            else:
                lbl.hide()

    def refresh(self):
        cams = self.camera_widgets if self.camera_widgets else list(constants.RUNNING_HARDWARE_CAMERA_WIDGETS)
        for i in range(self.visible_slots):
            lbl = self.labels[i]
            if i < len(cams):
                cam = cams[i]
                try:
                    if cam.shared_camera_frames:
                        frame = cam.shared_camera_frames[-1]
                        if frame is not None:
                            # convert BGR to RGB
                            img = frame[:, :, ::-1]
                            h, w, ch = img.shape
                            bytes_per_line = ch * w
                            qimg = QImage(img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                            pix = QPixmap.fromImage(qimg).scaled(lbl.width(), lbl.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                            lbl.setPixmap(pix)
                            continue
                except Exception:
                    pass
            # fallback
            lbl.setPixmap(QPixmap())
            lbl.setText(f"Camera {i + 1}")

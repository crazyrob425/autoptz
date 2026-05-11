from PySide6.QtWidgets import QWidget, QLabel, QGridLayout
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
import shared.constants as constants
import numpy as np


class GridOverview(QWidget):
    """Responsive grid overview showing up to 12 camera snapshots."""

    def __init__(self, parent=None, slots=12):
        super().__init__(parent)
        self.slots = slots
        self.layout = QGridLayout(self)
        self.labels = []
        for i in range(self.slots):
            lbl = QLabel(self)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setText(f"Camera {i+1}")
            lbl.setStyleSheet('background:#111; color:#ddd; border-radius:6px;')
            lbl.setMinimumSize(160, 90)
            self.labels.append(lbl)
            r = i // 4
            c = i % 4
            self.layout.addWidget(lbl, r, c)

        # timer to refresh snapshots
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(500)

    def refresh(self):
        cams = list(constants.RUNNING_HARDWARE_CAMERA_WIDGETS)
        for i in range(self.slots):
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
            lbl.setText(lbl.text())

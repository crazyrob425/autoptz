import json
import os
import time

from PySide6 import QtCore, QtGui, QtWidgets

import shared.constants as constants


class FloorMapCanvas(QtWidgets.QWidget):
    camera_moved = QtCore.Signal(str, dict)
    floor_moved = QtCore.Signal(str, dict)
    floor_selected = QtCore.Signal(str)
    camera_selected = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(420)
        self.setMouseTracking(True)
        self._layout_model = {"version": 1, "floors": [], "cameras": {}}
        self._camera_widgets = []
        self._selected_floor_id = None
        self._selected_camera_id = None
        self._drag_mode = None
        self._drag_offset = QtCore.QPointF(0, 0)
        self._last_mouse_pos = QtCore.QPointF(0, 0)

    def set_layout_model(self, layout_model):
        self._layout_model = layout_model or {"version": 1, "floors": [], "cameras": {}}
        self.update()

    def set_camera_widgets(self, camera_widgets):
        self._camera_widgets = list(camera_widgets or [])
        self.update()

    def _canvas_rect(self):
        margin = 16
        return QtCore.QRectF(margin, margin, max(1, self.width() - margin * 2), max(1, self.height() - margin * 2))

    def _floor_rect(self, floor):
        canvas = self._canvas_rect()
        size = max(0.08, min(0.9, float(floor.get('size', 0.34))))
        w = canvas.width() * size
        h = w
        x = canvas.left() + canvas.width() * float(floor.get('x', 0.1))
        y = canvas.top() + canvas.height() * float(floor.get('y', 0.1))
        return QtCore.QRectF(x, y, w, h)

    def _camera_point(self, camera):
        canvas = self._canvas_rect()
        x = canvas.left() + canvas.width() * float(camera.get('x', 0.5))
        y = canvas.top() + canvas.height() * float(camera.get('y', 0.5))
        return QtCore.QPointF(x, y)

    def _active_floors(self):
        return self._layout_model.get('floors', []) or []

    def _camera_items(self):
        return self._layout_model.get('cameras', {}) or {}

    def _camera_color(self, camera):
        if not camera.get('present', True):
            return QtGui.QColor(130, 130, 130)
        if camera.get('motion', False):
            return QtGui.QColor(220, 60, 60)
        return QtGui.QColor(60, 180, 95)

    def _find_floor_at(self, pos):
        for floor in reversed(self._active_floors()):
            if self._floor_rect(floor).contains(pos):
                return floor
        return None

    def _find_camera_at(self, pos):
        for camera_id, camera in reversed(list(self._camera_items().items())):
            if self._camera_point(camera).manhattanLength() >= 0:
                point = self._camera_point(camera)
                if QtCore.QLineF(point, pos).length() <= 14:
                    return camera_id, camera
        return None, None

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QtGui.QColor(22, 24, 28))
        canvas = self._canvas_rect()
        painter.setPen(QtGui.QPen(QtGui.QColor(50, 55, 65), 1, QtCore.Qt.PenStyle.DashLine))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(30, 33, 39)))
        painter.drawRoundedRect(canvas, 10, 10)

        # subtle grid
        painter.save()
        painter.setClipRect(canvas)
        painter.setPen(QtGui.QPen(QtGui.QColor(40, 45, 52), 1))
        grid = 40
        x = int(canvas.left())
        while x < canvas.right():
            painter.drawLine(x, int(canvas.top()), x, int(canvas.bottom()))
            x += grid
        y = int(canvas.top())
        while y < canvas.bottom():
            painter.drawLine(int(canvas.left()), y, int(canvas.right()), y)
            y += grid
        painter.restore()

        for floor in self._active_floors():
            rect = self._floor_rect(floor)
            selected = floor.get('id') == self._selected_floor_id
            pen = QtGui.QPen(QtGui.QColor(118, 161, 255) if selected else QtGui.QColor(180, 180, 190), 3)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
            painter.setPen(QtGui.QPen(QtGui.QColor(245, 245, 245), 1))
            painter.drawText(rect.adjusted(8, 8, -8, -8), QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft, floor.get('name', 'Floor'))

        for camera_id, camera in self._camera_items().items():
            point = self._camera_point(camera)
            radius = 10 if camera_id == self._selected_camera_id else 8
            color = self._camera_color(camera)
            painter.setPen(QtGui.QPen(QtGui.QColor(14, 14, 16), 2))
            painter.setBrush(QtGui.QBrush(color))
            painter.drawEllipse(point, radius, radius)
            painter.setPen(QtGui.QPen(QtGui.QColor(250, 250, 250), 1))
            painter.drawText(QtCore.QRectF(point.x() + 12, point.y() - 12, 150, 22), QtCore.Qt.AlignmentFlag.AlignLeft, camera.get('label', camera_id))

    def mousePressEvent(self, event):
        pos = event.position()
        self._last_mouse_pos = pos
        camera_id, camera = self._find_camera_at(pos)
        if camera_id:
            self._selected_camera_id = camera_id
            self._selected_floor_id = camera.get('floor_id')
            self._drag_mode = 'camera'
            self._drag_offset = pos - self._camera_point(camera)
            self.camera_selected.emit(camera_id)
            self.update()
            return

        floor = self._find_floor_at(pos)
        if floor:
            self._selected_floor_id = floor.get('id')
            self._selected_camera_id = None
            self._drag_mode = 'floor'
            rect = self._floor_rect(floor)
            self._drag_offset = pos - rect.topLeft()
            self.floor_selected.emit(floor.get('id'))
            self.update()
            return

        self._selected_camera_id = None
        self._selected_floor_id = None
        self._drag_mode = None
        self.update()

    def mouseMoveEvent(self, event):
        if not self._drag_mode:
            return
        pos = event.position()
        if self._drag_mode == 'camera' and self._selected_camera_id:
            camera = self._camera_items().get(self._selected_camera_id)
            if not camera:
                return
            canvas = self._canvas_rect()
            x = (pos.x() - canvas.left()) / canvas.width()
            y = (pos.y() - canvas.top()) / canvas.height()
            camera['x'] = max(0.02, min(0.98, x))
            camera['y'] = max(0.02, min(0.98, y))
            self.camera_moved.emit(self._selected_camera_id, camera)
            self.update()
        elif self._drag_mode == 'floor' and self._selected_floor_id:
            floor = next((f for f in self._active_floors() if f.get('id') == self._selected_floor_id), None)
            if not floor:
                return
            canvas = self._canvas_rect()
            size = max(0.08, min(0.9, float(floor.get('size', 0.34))))
            floor['x'] = max(0.0, min(1.0 - size, (pos.x() - canvas.left()) / canvas.width()))
            floor['y'] = max(0.0, min(1.0 - size, (pos.y() - canvas.top()) / canvas.height()))
            self.floor_moved.emit(self._selected_floor_id, floor)
            self.update()

    def mouseReleaseEvent(self, event):
        self._drag_mode = None


class FloorMapView(QtWidgets.QWidget):
    layout_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout_path = constants.MAP_LAYOUT_PATH
        self._layout_model = self._load_layout()
        self._camera_widgets = []
        self._camera_connections = {}

        self.setObjectName('floor_map_view')
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        controls = QtWidgets.QHBoxLayout()
        self.edit_toggle = QtWidgets.QCheckBox('Edit Layout')
        self.edit_toggle.setChecked(True)
        self.add_floor_btn = QtWidgets.QPushButton('Add Floor')
        self.place_camera_btn = QtWidgets.QPushButton('Place Camera')
        self.set_threshold_btn = QtWidgets.QPushButton('Set Threshold')
        self.remove_floor_btn = QtWidgets.QPushButton('Remove Floor')
        self.refresh_btn = QtWidgets.QPushButton('Refresh')
        self.status_label = QtWidgets.QLabel('Drop cameras into place, then flip Edit Layout off for monitoring.')
        self.status_label.setWordWrap(True)
        controls.addWidget(self.edit_toggle)
        controls.addWidget(self.add_floor_btn)
        controls.addWidget(self.place_camera_btn)
        controls.addWidget(self.set_threshold_btn)
        controls.addWidget(self.remove_floor_btn)
        controls.addWidget(self.refresh_btn)
        controls.addStretch(1)
        root.addLayout(controls)
        root.addWidget(self.status_label)

        self.canvas = FloorMapCanvas(self)
        root.addWidget(self.canvas, 1)

        legend = QtWidgets.QHBoxLayout()
        for label, color in [('Motion', '#dc3c3c'), ('Idle', '#3cb45f'), ('Offline', '#828282')]:
            swatch = QtWidgets.QLabel('  ')
            swatch.setFixedSize(18, 18)
            swatch.setStyleSheet(f'background: {color}; border-radius: 9px;')
            legend.addWidget(swatch)
            legend.addWidget(QtWidgets.QLabel(label))
        legend.addStretch(1)
        root.addLayout(legend)

        self.add_floor_btn.clicked.connect(self.add_floor)
        self.place_camera_btn.clicked.connect(self.place_camera_dialog)
        self.set_threshold_btn.clicked.connect(self.set_motion_threshold_dialog)
        self.remove_floor_btn.clicked.connect(self.remove_selected_floor)
        self.refresh_btn.clicked.connect(self.refresh_layout)
        self.canvas.camera_moved.connect(self._on_camera_moved)
        self.canvas.floor_moved.connect(self._on_floor_moved)
        self.canvas.camera_selected.connect(self._on_camera_selected)
        self.canvas.floor_selected.connect(self._on_floor_selected)

        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.timeout.connect(self._tick_motion_decay)
        self._refresh_timer.start(250)

        if not self._layout_model.get('floors'):
            self.add_floor()

        self.canvas.set_layout_model(self._layout_model)

    def _load_layout(self):
        if os.path.exists(self._layout_path):
            try:
                with open(self._layout_path, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                    payload.setdefault('version', 1)
                    payload.setdefault('floors', [])
                    payload.setdefault('cameras', {})
                    return payload
            except Exception:
                pass
        return {'version': 1, 'floors': [], 'cameras': {}}

    def _save_layout(self):
        try:
            os.makedirs(os.path.dirname(self._layout_path), exist_ok=True)
            with open(self._layout_path, 'w', encoding='utf-8') as f:
                json.dump(self._layout_model, f, indent=2)
        except Exception as e:
            self.status_label.setText(f'Layout save failed: {e}')

    def refresh_layout(self):
        self._layout_model = self._load_layout()
        if not self._layout_model.get('floors'):
            self._layout_model['floors'] = [{'id': 'floor-1', 'name': 'Floor 1', 'x': 0.12, 'y': 0.12, 'size': 0.34}]
        self._sync_camera_entries(self._camera_widgets)
        self.canvas.set_layout_model(self._layout_model)
        self.status_label.setText('Layout refreshed.')

    def _new_floor_id(self):
        existing = {floor.get('id') for floor in self._layout_model.get('floors', [])}
        index = 1
        while f'floor-{index}' in existing:
            index += 1
        return f'floor-{index}'

    def add_floor(self):
        floors = self._layout_model.setdefault('floors', [])
        floors.append({'id': self._new_floor_id(), 'name': f'Floor {len(floors) + 1}', 'x': 0.12, 'y': 0.12, 'size': 0.34})
        self.canvas.set_layout_model(self._layout_model)
        self._save_layout()
        self.status_label.setText('Added a new floor outline.')

    def remove_selected_floor(self):
        selected = self.canvas._selected_floor_id
        if not selected:
            return
        floors = self._layout_model.get('floors', [])
        self._layout_model['floors'] = [floor for floor in floors if floor.get('id') != selected]
        for camera in self._layout_model.get('cameras', {}).values():
            if camera.get('floor_id') == selected:
                camera['floor_id'] = ''
        self.canvas._selected_floor_id = None
        self.canvas.set_layout_model(self._layout_model)
        self._save_layout()
        self.status_label.setText('Removed selected floor.')

    def set_camera_widgets(self, camera_widgets):
        self._camera_widgets = list(camera_widgets or [])
        self._sync_camera_entries(self._camera_widgets)
        self.canvas.set_camera_widgets(self._camera_widgets)
        self._save_layout()

    def _camera_key(self, camera_widget):
        return camera_widget.objectName() or f'camera-{id(camera_widget)}'

    def _assign_default_floor(self):
        floors = self._layout_model.get('floors', [])
        return floors[0].get('id') if floors else ''

    def _sync_camera_entries(self, camera_widgets):
        cameras = self._layout_model.setdefault('cameras', {})
        default_floor = self._assign_default_floor()
        active_ids = set()
        for index, camera_widget in enumerate(camera_widgets or []):
            camera_id = self._camera_key(camera_widget)
            active_ids.add(camera_id)
            camera_entry = cameras.get(camera_id, {})
            camera_entry.setdefault('x', 0.3 + (index % 4) * 0.12)
            camera_entry.setdefault('y', 0.3 + (index // 4) * 0.12)
            camera_entry.setdefault('motion', False)
            camera_entry.setdefault('motion_until', 0.0)
            camera_entry.setdefault('motion_threshold', float(getattr(constants, 'MOTION_THRESHOLD', 0.03)))
            camera_entry['label'] = camera_widget.text() or camera_id
            camera_entry['present'] = True
            if not camera_entry.get('floor_id'):
                camera_entry['floor_id'] = default_floor
            cameras[camera_id] = camera_entry
            # If the camera widget supports motion threshold attribute, set it so detection uses it
            try:
                setattr(camera_widget, 'motion_threshold', float(camera_entry.get('motion_threshold', getattr(constants, 'MOTION_THRESHOLD', 0.03))))
            except Exception:
                pass
        for camera_id, camera_entry in cameras.items():
            if camera_id not in active_ids:
                camera_entry['present'] = False

    def _on_camera_moved(self, camera_id, camera_data):
        self._layout_model.setdefault('cameras', {})[camera_id] = camera_data
        self._save_layout()
        self.layout_changed.emit()

    def _on_floor_moved(self, floor_id, floor_data):
        for idx, floor in enumerate(self._layout_model.get('floors', [])):
            if floor.get('id') == floor_id:
                self._layout_model['floors'][idx] = floor_data
                break
        self._save_layout()
        self.layout_changed.emit()

    def _on_camera_selected(self, camera_id):
        self.status_label.setText(f'Selected camera: {camera_id}')

    def place_camera_dialog(self):
        cams = list(self._camera_widgets or [])
        if not cams:
            self.status_label.setText('No active cameras to place.')
            return
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle('Place Camera on Map')
        layout = QtWidgets.QFormLayout(dlg)
        combo = QtWidgets.QComboBox()
        for w in cams:
            combo.addItem(self._camera_key(w))
        layout.addRow('Camera', combo)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addRow(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return
        cam_id = combo.currentText()
        # place at center of selected floor or canvas center
        floor = next((f for f in self._layout_model.get('floors', []) if f.get('id') == self.canvas._selected_floor_id), None)
        if floor:
            size = max(0.08, min(0.9, float(floor.get('size', 0.34))))
            cam_x = float(floor.get('x', 0.5)) + size / 2
            cam_y = float(floor.get('y', 0.5)) + size / 2
        else:
            cam_x = 0.5
            cam_y = 0.5
        cam_entry = self._layout_model.setdefault('cameras', {}).setdefault(cam_id, {})
        cam_entry['x'] = max(0.02, min(0.98, cam_x))
        cam_entry['y'] = max(0.02, min(0.98, cam_y))
        cam_entry['present'] = True
        cam_entry.setdefault('label', cam_id)
        cam_entry.setdefault('motion', False)
        cam_entry.setdefault('motion_until', 0.0)
        cam_entry.setdefault('motion_threshold', float(getattr(constants, 'MOTION_THRESHOLD', 0.03)))
        self.canvas.set_layout_model(self._layout_model)
        self._save_layout()
        self.status_label.setText(f'Placed {cam_id} on map.')

    def set_motion_threshold_dialog(self):
        cams = list(self._layout_model.get('cameras', {}).keys())
        if not cams:
            self.status_label.setText('No cameras found in layout.')
            return
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle('Set Motion Threshold')
        layout = QtWidgets.QFormLayout(dlg)
        combo = QtWidgets.QComboBox()
        for cid in cams:
            combo.addItem(cid)
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(0.0, 1.0)
        spin.setSingleStep(0.01)
        selected_cam = self._layout_model.get('cameras', {}).get(combo.currentText())
        spin.setValue(float(selected_cam.get('motion_threshold', getattr(constants, 'MOTION_THRESHOLD', 0.03))) if selected_cam else float(getattr(constants, 'MOTION_THRESHOLD', 0.03)))
        def on_cam_changed(idx):
            cid = combo.itemText(idx)
            val = float(self._layout_model.get('cameras', {}).get(cid, {}).get('motion_threshold', getattr(constants, 'MOTION_THRESHOLD', 0.03)))
            spin.setValue(val)
        combo.currentIndexChanged.connect(on_cam_changed)
        layout.addRow('Camera', combo)
        layout.addRow('Threshold (0-1)', spin)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addRow(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return
        cid = combo.currentText()
        val = float(spin.value())
        self._layout_model.setdefault('cameras', {})[cid] = self._layout_model.setdefault('cameras', {}).get(cid, {})
        self._layout_model['cameras'][cid]['motion_threshold'] = val
        # Propagate to active widget if present
        for w in self._camera_widgets:
            if self._camera_key(w) == cid:
                try:
                    setattr(w, 'motion_threshold', val)
                except Exception:
                    pass
        self._save_layout()
        self.status_label.setText(f'Set threshold {val:.2f} for {cid}')

    def _on_floor_selected(self, floor_id):
        self.status_label.setText(f'Selected floor: {floor_id}')

    def update_camera_motion(self, camera_id, is_moving):
        camera = self._layout_model.setdefault('cameras', {}).get(camera_id)
        if camera is None:
            camera = {'x': 0.5, 'y': 0.5, 'label': camera_id, 'floor_id': self._assign_default_floor(), 'present': True}
            self._layout_model['cameras'][camera_id] = camera
        camera['motion'] = bool(is_moving)
        camera['motion_until'] = time.time() + constants.MOTION_HOLD_SECONDS if is_moving else 0.0
        self.canvas.set_layout_model(self._layout_model)
        self.layout_changed.emit()

    def _tick_motion_decay(self):
        changed = False
        now = time.time()
        for camera in self._layout_model.get('cameras', {}).values():
            if camera.get('motion') and camera.get('motion_until', 0.0) and now > camera.get('motion_until', 0.0):
                camera['motion'] = False
                camera['motion_until'] = 0.0
                changed = True
        if changed:
            self.canvas.set_layout_model(self._layout_model)

    def register_camera_widget(self, camera_widget):
        if camera_widget in self._camera_widgets:
            return
        self._camera_widgets.append(camera_widget)
        self._sync_camera_entries(self._camera_widgets)
        self.canvas.set_camera_widgets(self._camera_widgets)
        self.canvas.set_layout_model(self._layout_model)
        self._save_layout()

    def unregister_camera_widget(self, camera_widget):
        if camera_widget in self._camera_widgets:
            self._camera_widgets.remove(camera_widget)
        camera_id = self._camera_key(camera_widget)
        if camera_id in self._layout_model.get('cameras', {}):
            self._layout_model['cameras'][camera_id]['present'] = False
        self.canvas.set_camera_widgets(self._camera_widgets)
        self.canvas.set_layout_model(self._layout_model)
        self._save_layout()

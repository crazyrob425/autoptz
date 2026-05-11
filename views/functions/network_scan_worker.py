from PySide6 import QtCore
from logic.camera_search.auto_discovery import CameraAutoDiscovery


class NetworkScanWorker(QtCore.QObject):
    progress = QtCore.Signal(str, int, int)
    finished = QtCore.Signal(list)
    failed = QtCore.Signal(str)
    cancelled = QtCore.Signal()

    def __init__(self, credential_manager=None):
        super().__init__()
        self._cancelled = False
        self.credential_manager = credential_manager

    def cancel(self):
        self._cancelled = True

    def _should_cancel(self):
        return self._cancelled

    def _on_progress(self, payload):
        message = payload.get("message", "Scanning...")
        value = int(payload.get("value", 0))
        total = int(payload.get("total", 0))
        self.progress.emit(message, value, total)

    @QtCore.Slot()
    def run(self):
        try:
            discovery = CameraAutoDiscovery()
            results = discovery.discover(
                progress_cb=self._on_progress,
                should_cancel=self._should_cancel,
                credential_manager=self.credential_manager,
            )
            if self._cancelled:
                self.cancelled.emit()
                return
            self.finished.emit(results)
        except Exception as exc:
            self.failed.emit(str(exc))

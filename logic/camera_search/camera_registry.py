import os
import sqlite3
import threading
from datetime import datetime
import logging


logger = logging.getLogger(__name__)


class CameraRegistry:
    """Persistent registry of discovered/managed network cameras."""

    def __init__(self, db_path=None):
        # Use a stable, writable per-user location by default.
        # This avoids failures when app is launched from non-writable CWDs.
        data_dir = os.getenv("AUTOPTZ_DATA_DIR") or os.path.expanduser("~/.autoptz/data")
        self.db_path = db_path or os.path.join(data_dir, "camera_registry.db")
        self._lock = threading.Lock()
        self._db_error_reported = False
        self._ensure_db()

    def _connect(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        return sqlite3.connect(self.db_path, timeout=5)

    def _ensure_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._lock, self._connect() as conn:
            c = conn.cursor()
            c.execute(
                '''
                CREATE TABLE IF NOT EXISTS cameras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT,
                    label TEXT,
                    rtsp_url TEXT UNIQUE,
                    communication_method TEXT,
                    confidence REAL,
                    enabled INTEGER DEFAULT 1,
                    reconnect_policy TEXT DEFAULT 'aggressive',
                    status TEXT DEFAULT 'unknown',
                    last_seen TEXT,
                    last_error TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                '''
            )
            conn.commit()

    def upsert_camera(self, ip, label, rtsp_url, communication_method, confidence, enabled=1, reconnect_policy='aggressive'):
        now = datetime.utcnow().isoformat()
        with self._lock, self._connect() as conn:
            c = conn.cursor()
            c.execute(
                '''
                INSERT INTO cameras (ip, label, rtsp_url, communication_method, confidence, enabled, reconnect_policy, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(rtsp_url) DO UPDATE SET
                    ip=excluded.ip,
                    label=excluded.label,
                    communication_method=excluded.communication_method,
                    confidence=excluded.confidence,
                    enabled=excluded.enabled,
                    reconnect_policy=excluded.reconnect_policy,
                    updated_at=excluded.updated_at
                ''',
                (ip, label, rtsp_url, communication_method, float(confidence), int(enabled), reconnect_policy, now, now)
            )
            conn.commit()

    def list_enabled(self):
        try:
            with self._lock, self._connect() as conn:
                c = conn.cursor()
                c.execute(
                    '''
                    SELECT ip, label, rtsp_url, communication_method, confidence, reconnect_policy, status, last_seen, last_error
                    FROM cameras
                    WHERE enabled = 1
                    ORDER BY confidence DESC
                    '''
                )
                rows = c.fetchall()
                cols = ["ip", "label", "rtsp_url", "communication_method", "confidence", "reconnect_policy", "status", "last_seen", "last_error"]
                self._db_error_reported = False
                return [dict(zip(cols, r)) for r in rows]
        except sqlite3.OperationalError as exc:
            # Attempt one self-heal and avoid traceback spam in recurring timers.
            try:
                self._ensure_db()
                with self._lock, self._connect() as conn:
                    c = conn.cursor()
                    c.execute(
                        '''
                        SELECT ip, label, rtsp_url, communication_method, confidence, reconnect_policy, status, last_seen, last_error
                        FROM cameras
                        WHERE enabled = 1
                        ORDER BY confidence DESC
                        '''
                    )
                    rows = c.fetchall()
                    cols = ["ip", "label", "rtsp_url", "communication_method", "confidence", "reconnect_policy", "status", "last_seen", "last_error"]
                    self._db_error_reported = False
                    return [dict(zip(cols, r)) for r in rows]
            except Exception:
                if not self._db_error_reported:
                    logger.error("Camera registry unavailable at %s: %s", self.db_path, exc)
                    self._db_error_reported = True
                return []

    def update_health(self, rtsp_url, status, last_error=None):
        now = datetime.utcnow().isoformat()
        with self._lock, self._connect() as conn:
            c = conn.cursor()
            c.execute(
                '''
                UPDATE cameras
                SET status = ?,
                    last_seen = ?,
                    last_error = ?,
                    updated_at = ?
                WHERE rtsp_url = ?
                ''',
                (status, now, last_error or "", now, rtsp_url)
            )
            conn.commit()

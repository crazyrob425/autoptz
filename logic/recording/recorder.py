import sqlite3
import threading
import os
from datetime import datetime


class Recorder:
    """Simple SQLite-backed event/record index for recorded clips and metadata."""

    def __init__(self, db_path=None):
        default_dir = os.path.join(os.path.expanduser('~'), '.autoptz', 'data')
        default_path = os.path.join(default_dir, 'recordings.db')
        self.db_path = db_path or default_path
        self.db_path = os.path.abspath(self.db_path)
        self._lock = threading.Lock()
        self._ensure_db()

    def _ensure_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                '''
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    camera TEXT,
                    event_type TEXT,
                    person_name TEXT,
                    mac_addr TEXT,
                    ble_tag TEXT,
                    phone TEXT,
                    notes TEXT
                )
                '''
            )
            conn.commit()

    def add_record(self, camera, event_type, person_name=None, mac_addr=None, ble_tag=None, phone=None, notes=None, timestamp=None):
        ts = timestamp or datetime.utcnow().isoformat()
        with self._lock, sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                'INSERT INTO records (timestamp, camera, event_type, person_name, mac_addr, ble_tag, phone, notes) VALUES (?,?,?,?,?,?,?,?)',
                (ts, camera, event_type, person_name, mac_addr, ble_tag, phone, notes)
            )
            conn.commit()
            return c.lastrowid

    def search_records(self, query=None, camera=None, event_type=None, person_name=None, mac_addr=None, ble_tag=None, phone=None, start_ts=None, end_ts=None, limit=200):
        q = []
        params = []
        if query:
            q.append('(person_name LIKE ? OR notes LIKE ?)')
            params.extend([f'%{query}%', f'%{query}%'])
        if camera:
            q.append('camera = ?')
            params.append(camera)
        if event_type:
            q.append('event_type = ?')
            params.append(event_type)
        if person_name:
            q.append('person_name = ?')
            params.append(person_name)
        if mac_addr:
            q.append('mac_addr = ?')
            params.append(mac_addr)
        if ble_tag:
            q.append('ble_tag = ?')
            params.append(ble_tag)
        if phone:
            q.append('phone = ?')
            params.append(phone)
        if start_ts:
            q.append('timestamp >= ?')
            params.append(start_ts)
        if end_ts:
            q.append('timestamp <= ?')
            params.append(end_ts)

        where_clause = ('WHERE ' + ' AND '.join(q)) if q else ''
        sql = f'SELECT id, timestamp, camera, event_type, person_name, mac_addr, ble_tag, phone, notes FROM records {where_clause} ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(sql, params)
            rows = c.fetchall()
            cols = ['id', 'timestamp', 'camera', 'event_type', 'person_name', 'mac_addr', 'ble_tag', 'phone', 'notes']
            return [dict(zip(cols, r)) for r in rows]

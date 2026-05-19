import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta

from logic.recording.recorder import Recorder


@dataclass
class AttendanceSnapshot:
    person_name: str
    camera: str
    last_seen: str
    last_confidence: float
    state: str


class AttendanceManager:
    """Tracks visitation state for recognized people.

    The manager stores a small session table alongside the existing recorder
    database so the app can answer:
    - Who is present right now?
    - Who checked in today?
    - Who has checked out after being absent long enough?
    """

    def __init__(self, db_path=None, absence_minutes=10):
        self.recorder = Recorder(db_path=db_path)
        self.db_path = self.recorder.db_path
        self.absence_minutes = int(absence_minutes)
        self._lock = threading.Lock()
        self._ensure_db()

    def _ensure_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance_sessions (
                    person_name TEXT PRIMARY KEY,
                    current_state TEXT NOT NULL DEFAULT 'checked_out',
                    first_seen TEXT,
                    last_seen TEXT,
                    last_camera TEXT,
                    last_confidence REAL DEFAULT 0,
                    updated_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_attendance_sessions_state
                ON attendance_sessions(current_state)
                """
            )
            conn.commit()

    @staticmethod
    def _utcnow_iso():
        return datetime.utcnow().isoformat(timespec="seconds")

    @staticmethod
    def _parse_iso(value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def register_sighting(self, person_name, camera, confidence=0.0, seen_at=None):
        """Register a face sighting and emit a check-in if needed.

        Returns a string describing the attendance transition:
        - 'check-in' when the person transitions into present state
        - 'seen' when they were already present
        - None when the input is invalid
        """
        if not person_name or person_name == "Unknown":
            return None

        seen_at_dt = seen_at if isinstance(seen_at, datetime) else self._parse_iso(seen_at)
        seen_at_dt = seen_at_dt or datetime.utcnow()
        seen_at_iso = seen_at_dt.isoformat(timespec="seconds")
        confidence = float(confidence or 0.0)

        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT person_name, current_state, last_seen, last_camera, last_confidence FROM attendance_sessions WHERE person_name = ?",
                (person_name,),
            ).fetchone()

            if row is None or row["current_state"] != "checked_in":
                self.recorder.add_record(
                    camera=camera,
                    event_type="check-in",
                    person_name=person_name,
                    notes=f"Visitations check-in; confidence={confidence:.2f}"
                )
                conn.execute(
                    """
                    INSERT INTO attendance_sessions (
                        person_name, current_state, first_seen, last_seen, last_camera, last_confidence, updated_at
                    ) VALUES (?, 'checked_in', ?, ?, ?, ?, ?)
                    ON CONFLICT(person_name) DO UPDATE SET
                        current_state = 'checked_in',
                        first_seen = COALESCE(attendance_sessions.first_seen, excluded.first_seen),
                        last_seen = excluded.last_seen,
                        last_camera = excluded.last_camera,
                        last_confidence = excluded.last_confidence,
                        updated_at = excluded.updated_at
                    """,
                    (person_name, seen_at_iso, seen_at_iso, camera, confidence, seen_at_iso),
                )
                conn.commit()
                return "check-in"

            conn.execute(
                """
                UPDATE attendance_sessions
                SET last_seen = ?, last_camera = ?, last_confidence = ?, updated_at = ?
                WHERE person_name = ?
                """,
                (seen_at_iso, camera, confidence, seen_at_iso, person_name),
            )
            conn.commit()
            return "seen"

    def sweep_stale_sessions(self, reference_time=None):
        """Mark stale checked-in sessions as checked-out after absence timeout."""
        now = reference_time if isinstance(reference_time, datetime) else self._parse_iso(reference_time)
        now = now or datetime.utcnow()
        stale_cutoff = now - timedelta(minutes=self.absence_minutes)
        stale_cutoff_iso = stale_cutoff.isoformat(timespec="seconds")
        now_iso = now.isoformat(timespec="seconds")

        checked_out = []
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT person_name, last_seen, last_camera, last_confidence
                FROM attendance_sessions
                WHERE current_state = 'checked_in'
                """
            ).fetchall()

            for row in rows:
                last_seen_dt = self._parse_iso(row["last_seen"])
                if last_seen_dt is None or last_seen_dt > stale_cutoff:
                    continue

                person_name = row["person_name"]
                camera = row["last_camera"] or "attendance"
                confidence = float(row["last_confidence"] or 0.0)
                self.recorder.add_record(
                    camera=camera,
                    event_type="check-out",
                    person_name=person_name,
                    notes=(
                        f"Visitations check-out; last_seen={row['last_seen']}; "
                        f"confidence={confidence:.2f}; timeout={self.absence_minutes}m"
                    )
                )
                conn.execute(
                    """
                    UPDATE attendance_sessions
                    SET current_state = 'checked_out', updated_at = ?, last_seen = ?
                    WHERE person_name = ?
                    """,
                    (now_iso, stale_cutoff_iso, person_name),
                )
                checked_out.append(person_name)

            if checked_out:
                conn.commit()

        return checked_out

    def get_current_present(self):
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT person_name, last_seen, last_camera, last_confidence, current_state
                FROM attendance_sessions
                WHERE current_state = 'checked_in'
                ORDER BY last_seen DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def get_today_summary(self):
        today_prefix = datetime.utcnow().date().isoformat()
        records = self.recorder.search_records(start_ts=today_prefix, limit=5000)
        check_ins = [r for r in records if r.get("event_type") == "check-in"]
        check_outs = [r for r in records if r.get("event_type") == "check-out"]
        return {
            "date": today_prefix,
            "total_events": len(records),
            "check_ins": len(check_ins),
            "check_outs": len(check_outs),
            "records": records,
        }

    def get_people(self):
        """Return people that have visitation history."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT DISTINCT person_name
                FROM records
                WHERE event_type IN ('check-in', 'check-out') AND person_name IS NOT NULL AND person_name != ''
                ORDER BY person_name COLLATE NOCASE
                """
            ).fetchall()
            return [row["person_name"] for row in rows]

    def get_person_history(self, person_name, limit=50):
        """Return recent visitation history for a single person."""
        if not person_name:
            return []
        return self.recorder.search_records(person_name=person_name, limit=limit)

    def get_camera_summary(self, camera=None, limit=200):
        """Return camera-wise visitation summaries."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            params = []
            where_clause = "WHERE event_type IN ('check-in', 'check-out')"
            if camera:
                where_clause += " AND camera = ?"
                params.append(camera)

            rows = conn.execute(
                f"""
                SELECT camera,
                       SUM(CASE WHEN event_type = 'check-in' THEN 1 ELSE 0 END) AS check_ins,
                       SUM(CASE WHEN event_type = 'check-out' THEN 1 ELSE 0 END) AS check_outs,
                       COUNT(*) AS total_events,
                       MAX(timestamp) AS last_event_at
                FROM records
                {where_clause}
                GROUP BY camera
                ORDER BY total_events DESC, camera COLLATE NOCASE
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()

            summaries = []
            for row in rows:
                recent_people = conn.execute(
                    """
                    SELECT person_name, timestamp, event_type, notes
                    FROM records
                    WHERE event_type IN ('check-in', 'check-out') AND camera = ?
                    ORDER BY timestamp DESC
                    LIMIT 5
                    """,
                    (row["camera"],),
                ).fetchall()
                summaries.append({
                    "camera": row["camera"],
                    "check_ins": row["check_ins"] or 0,
                    "check_outs": row["check_outs"] or 0,
                    "total_events": row["total_events"] or 0,
                    "last_event_at": row["last_event_at"],
                    "recent_events": [dict(r) for r in recent_people],
                })
            return summaries

    def rename_person(self, old_name, new_name):
        """Rename a person inside visitation records and active sessions."""
        if not old_name or not new_name or old_name == new_name:
            return False

        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute(
                "UPDATE records SET person_name = ? WHERE person_name = ?",
                (new_name, old_name),
            )

            existing_new = conn.execute(
                "SELECT person_name FROM attendance_sessions WHERE person_name = ?",
                (new_name,),
            ).fetchone()

            if existing_new is not None:
                conn.execute(
                    "DELETE FROM attendance_sessions WHERE person_name = ?",
                    (old_name,),
                )
            else:
                conn.execute(
                    "UPDATE attendance_sessions SET person_name = ? WHERE person_name = ?",
                    (new_name, old_name),
                )

            conn.commit()
        return True

    def get_status_snapshot(self):
        return {
            "present": self.get_current_present(),
            "summary": self.get_today_summary(),
            "absence_minutes": self.absence_minutes,
        }

import json
import os
import re
import pickle
import threading
from dataclasses import dataclass, field
from datetime import datetime

import cv2
import numpy as np

from logic.recording.recorder import Recorder
from shared import constants

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False


@dataclass
class AutoRegistrationSample:
    encoding: np.ndarray
    camera: str
    quality: float
    timestamp: str
    face_location: tuple
    crop_path: str | None = None


@dataclass
class AutoRegistrationBucket:
    bucket_id: str
    samples: list[AutoRegistrationSample] = field(default_factory=list)
    representative: np.ndarray | None = None
    first_seen: str | None = None
    last_seen: str | None = None
    registered_name: str | None = None


class AutoRegistrationManager:
    """Builds high-quality auto profiles from unknown faces seen across cameras."""

    def __init__(
        self,
        encodings_path=None,
        profiles_dir=None,
        min_samples=6,
        min_cameras=1,
        quality_threshold=0.45,
        match_distance_threshold=0.42,
        enabled=True,
        max_profile_samples=12,
    ):
        self.encodings_path = os.path.abspath(encodings_path or constants.ENCODINGS_PATH)
        self.profiles_dir = os.path.abspath(
            profiles_dir or os.path.join(os.path.dirname(self.encodings_path), "auto_registration_profiles")
        )
        self.min_samples = int(min_samples)
        self.min_cameras = int(min_cameras)
        self.quality_threshold = float(quality_threshold)
        self.match_distance_threshold = float(match_distance_threshold)
        self.enabled = enabled
        self.max_profile_samples = int(max_profile_samples)
        self.recorder = Recorder()
        self._lock = threading.Lock()
        self._buckets: dict[str, AutoRegistrationBucket] = {}
        os.makedirs(self.profiles_dir, exist_ok=True)

    def consider_detection(self, face_encoding, camera_name, face_location, frame=None, timestamp=None):
        """Ingest a single unknown face detection from any camera."""
        if not self.enabled or face_encoding is None:
            return None

        timestamp = timestamp or datetime.utcnow().isoformat(timespec="seconds")
        quality = self._score_sample(frame, face_location)
        if quality < self.quality_threshold:
            return None

        encoding = np.asarray(face_encoding, dtype=np.float64)
        with self._lock:
            bucket = self._find_bucket(encoding)
            if bucket is None:
                bucket = self._create_bucket(timestamp)

            crop_path = self._save_sample_crop(bucket.bucket_id, frame, face_location, timestamp, camera_name, quality)
            sample = AutoRegistrationSample(
                encoding=encoding,
                camera=camera_name,
                quality=quality,
                timestamp=timestamp,
                face_location=tuple(face_location) if face_location is not None else None,
                crop_path=crop_path,
            )
            bucket.samples.append(sample)
            if bucket.representative is None or quality >= max((s.quality for s in bucket.samples), default=0.0):
                bucket.representative = encoding
            bucket.first_seen = bucket.first_seen or timestamp
            bucket.last_seen = timestamp

            created_name = self._maybe_register_bucket(bucket)
            if created_name:
                self._buckets.pop(bucket.bucket_id, None)
                return created_name
            return None

    def _create_bucket(self, timestamp):
        bucket_id = f"bucket_{len(self._buckets) + 1}_{timestamp.replace(':', '').replace('-', '').replace('T', '_')}"
        bucket = AutoRegistrationBucket(bucket_id=bucket_id, first_seen=timestamp, last_seen=timestamp)
        self._buckets[bucket_id] = bucket
        return bucket

    def _find_bucket(self, encoding):
        best_bucket = None
        best_distance = None
        for bucket in self._buckets.values():
            if bucket.representative is None:
                continue
            distance = float(np.linalg.norm(bucket.representative - encoding))
            if distance <= self.match_distance_threshold and (best_distance is None or distance < best_distance):
                best_bucket = bucket
                best_distance = distance
        return best_bucket

    def _maybe_register_bucket(self, bucket):
        unique_cameras = {sample.camera for sample in bucket.samples if sample.camera}
        if len(bucket.samples) < self.min_samples or len(unique_cameras) < self.min_cameras:
            return None

        top_samples = sorted(bucket.samples, key=lambda s: s.quality, reverse=True)[: self.max_profile_samples]
        if not top_samples:
            return None

        top_quality = sum(sample.quality for sample in top_samples[:3]) / min(3, len(top_samples))
        if top_quality < self.quality_threshold:
            return None

        user_name = self._next_user_name()
        self._store_profile(user_name, top_samples)
        bucket.registered_name = user_name
        self.recorder.add_record(
            camera=top_samples[0].camera,
            event_type="auto-registration",
            person_name=user_name,
            notes=(
                f"Auto-registered from {len(top_samples)} samples across {len(unique_cameras)} cameras; "
                f"avg_top_quality={top_quality:.2f}"
            ),
        )
        return user_name

    def _store_profile(self, user_name, samples):
        from logic.image_processing.facial_recognition import FacialRecognition

        encodings = self._load_encodings()
        for sample in samples:
            encodings['encodings'].append(sample.encoding)
            encodings['names'].append(user_name)
        self._save_encodings(encodings)

        profile_dir = os.path.join(self.profiles_dir, user_name)
        os.makedirs(profile_dir, exist_ok=True)
        manifest = {
            "user_name": user_name,
            "created_at": datetime.utcnow().isoformat(timespec="seconds"),
            "sample_count": len(samples),
            "samples": [
                {
                    "camera": sample.camera,
                    "quality": sample.quality,
                    "timestamp": sample.timestamp,
                    "crop_path": sample.crop_path,
                }
                for sample in samples
            ],
        }
        with open(os.path.join(profile_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    def _save_sample_crop(self, bucket_id, frame, face_location, timestamp, camera_name, quality):
        if frame is None or face_location is None:
            return None

        try:
            top, right, bottom, left = [max(0, int(v)) for v in face_location]
            crop = frame[top:bottom, left:right]
            if crop.size == 0:
                return None

            profile_dir = os.path.join(self.profiles_dir, bucket_id)
            os.makedirs(profile_dir, exist_ok=True)
            filename = f"{timestamp.replace(':', '').replace('-', '').replace('T', '_')}_{camera_name}_{quality:.2f}.jpg"
            filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)
            crop_path = os.path.join(profile_dir, filename)
            cv2.imwrite(crop_path, crop)
            return crop_path
        except Exception:
            return None

    def _score_sample(self, frame, face_location):
        if frame is None or face_location is None:
            return 0.5

        try:
            if len(frame.shape) == 3 and frame.shape[2] == 4:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
            else:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            h, w = rgb.shape[:2]
            top, right, bottom, left = [max(0, int(v)) for v in face_location]
            top = min(top, h - 1)
            bottom = min(bottom, h)
            left = min(left, w - 1)
            right = min(right, w)
            crop = rgb[top:bottom, left:right]
            if crop.size == 0:
                return 0.5

            gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
            sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            sharpness_score = min(sharpness / 180.0, 1.0)

            face_area = max((bottom - top) * (right - left), 1)
            frame_area = max(h * w, 1)
            area_score = min(face_area / frame_area * 18.0, 1.0)

            center_x = (left + right) / 2.0
            center_y = (top + bottom) / 2.0
            dx = abs(center_x - (w / 2.0)) / max(w / 2.0, 1)
            dy = abs(center_y - (h / 2.0)) / max(h / 2.0, 1)
            center_score = max(0.0, 1.0 - ((dx + dy) / 2.0))

            score = (sharpness_score * 0.45) + (area_score * 0.35) + (center_score * 0.20)
            return float(max(0.0, min(score, 1.0)))
        except Exception:
            return 0.5

    def _load_encodings(self):
        if os.path.exists(self.encodings_path):
            with open(self.encodings_path, "rb") as f:
                data = pickle.load(f)
                if isinstance(data, dict):
                    data.setdefault('encodings', [])
                    data.setdefault('names', [])
                    return data
        return {'encodings': [], 'names': []}

    def _save_encodings(self, encodings):
        with open(self.encodings_path, "wb") as f:
            pickle.dump(encodings, f)

    def _next_user_name(self):
        encodings = self._load_encodings()
        max_id = 0
        for name in encodings.get('names', []):
            match = re.fullmatch(r"User(\d+)", str(name))
            if match:
                max_id = max(max_id, int(match.group(1)))
        return f"User{max_id + 1}"

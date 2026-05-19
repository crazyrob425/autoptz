import math
import os
import pickle
from ctypes import c_char
from multiprocessing import Value
import cv2
import numpy as np
import shared.constants as constants

# Gracefully handle missing face_recognition/dlib
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("Warning: face_recognition not available. Facial recognition will be disabled.")


class FacialRecognition:
    def __init__(self, queue, objectName, confidence_threshold=0.6):
        self.known_face_encodings = None
        self.queue = queue
        self.add_face_name = Value(c_char * 50)
        self.objectName = objectName
        self.confidence_threshold = confidence_threshold  # Threshold for face matching (0.0-1.0)
        self.check_encodings()

    def recognize(self, frame):
        if not FACE_RECOGNITION_AVAILABLE:
            # Return empty face data when face_recognition isn't available
            self.queue.put({"locations": [], "names": [], "confidences": [], "encodings": []})
            return
        
        if frame.shape[2] == 4:
            # Convert from BGR or BGRA to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)

        # Resize the frame to a smaller size
        small_frame = cv2.resize(frame, (0, 0), fx=0.50, fy=0.50)

        face_locations = face_recognition.face_locations(
            small_frame, number_of_times_to_upsample=1, model="hog")
        face_encodings = face_recognition.face_encodings(
            small_frame, face_locations, num_jitters=0, model="small")
        face_names = []
        confidence_list = []

        add_face_name = self.add_face_name.value.decode('utf-8')
        if add_face_name:
            result = self.add_face(face_encodings, add_face_name)
            if result:
                self.queue.put({"locations": face_locations, "names": [add_face_name], "confidences": [1.0], "encodings": face_encodings})
                return

            self.queue.put({"locations": [], "names": [], "confidences": [], "encodings": []})
            return

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(
                self.known_face_encodings['encodings'], face_encoding, tolerance=self.confidence_threshold)
            name = "Unknown"
            confidence = 0.0

            face_distances = face_recognition.face_distance(
                self.known_face_encodings['encodings'], face_encoding)

            # Check if face_distances is empty
            if not face_distances.size:
                continue

            best_match_index = np.argmin(face_distances)
            best_distance = face_distances[best_match_index]
            
            # Apply confidence threshold - only accept matches below threshold distance
            if best_distance < self.confidence_threshold and matches[best_match_index]:
                name = self.known_face_encodings['names'][best_match_index]
                confidence_str = self.face_confidence(best_distance, self.confidence_threshold)
                # Extract numeric value from percentage string
                confidence = float(confidence_str.replace('%', '')) / 100.0
            else:
                # Face doesn't meet confidence threshold
                confidence = 0.0
            
            face_names.append(name)
            confidence_list.append(confidence)
        face_details = {"locations": face_locations, "names": face_names, "confidences": confidence_list, "encodings": face_encodings}
        self.queue.put(face_details)

    def set_add_face_name(self, name):
        self.add_face_name.value = name.encode('utf-8')

    def add_face(self, face_encodings, add_face_name):
        # If a face was found in the frame, add it to the known faces
        if face_encodings:
            self._append_face_encoding(add_face_name, face_encodings[0])
            print(f"Added a new face for {add_face_name}")
            # Reset the add_face_name to stop adding the face
            self.set_add_face_name('')
            return True
        return False

    def add_faces_from_images(self, add_face_name, image_paths):
        """Add one person using multiple photo files."""
        if not image_paths:
            return 0

        added = 0
        for image_path in image_paths:
            encoding = self._extract_encoding_from_image(image_path)
            if encoding is None:
                continue
            self._append_face_encoding(add_face_name, encoding)
            added += 1

        if added:
            print(f"Added {added} face samples for {add_face_name}")
        return added

    def add_faces_from_encodings(self, add_face_name, encodings):
        """Add one person using multiple face encodings."""
        if not encodings:
            return 0

        added = 0
        for encoding in encodings:
            if encoding is None:
                continue
            self._append_face_encoding(add_face_name, np.asarray(encoding, dtype=np.float64))
            added += 1
        if added:
            print(f"Added {added} encoding samples for {add_face_name}")
        return added

    def _append_face_encoding(self, add_face_name, encoding):
        self.known_face_encodings['encodings'].append(encoding)
        self.known_face_encodings['names'].append(add_face_name)

        with open(constants.ENCODINGS_PATH, "wb") as f:
            f.write(pickle.dumps(self.known_face_encodings))

    @staticmethod
    def rename_label(old_name, new_name):
        """Rename a face label inside the encodings pickle."""
        if not old_name or not new_name or old_name == new_name:
            return False
        if not os.path.exists(constants.ENCODINGS_PATH):
            return False

        with open(constants.ENCODINGS_PATH, "rb") as f:
            data = pickle.load(f)

        if not isinstance(data, dict):
            return False

        data.setdefault('encodings', [])
        data.setdefault('names', [])
        data['names'] = [new_name if name == old_name else name for name in data['names']]

        with open(constants.ENCODINGS_PATH, "wb") as f:
            pickle.dump(data, f)
        return True

    @staticmethod
    def get_known_names():
        if not os.path.exists(constants.ENCODINGS_PATH):
            return []
        with open(constants.ENCODINGS_PATH, "rb") as f:
            data = pickle.load(f)
        if not isinstance(data, dict):
            return []
        return sorted({name for name in data.get('names', []) if name})

    @staticmethod
    def _extract_encoding_from_image(image_path):
        if not os.path.exists(image_path):
            return None

        image = cv2.imread(image_path)
        if image is None:
            return None

        if len(image.shape) == 3 and image.shape[2] == 4:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
        else:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_image, number_of_times_to_upsample=1, model="hog")
        if not face_locations:
            return None

        face_encodings = face_recognition.face_encodings(rgb_image, face_locations, num_jitters=1, model="small")
        return face_encodings[0] if face_encodings else None

    @staticmethod
    def face_confidence(face_distance, face_match_threshold=0.6):
        """
        Confidence calculation for Facial Recognition
        :param face_distance:
        :param face_match_threshold:
        :return:
        """
        threshold = (1.0 - face_match_threshold)
        linear_val = (1.0 - face_distance) / (threshold * 2.0)

        if face_distance > face_match_threshold:
            return str(round(linear_val * 100, 2)) + '%'
        else:
            value = (linear_val + ((1.0 - linear_val) *
                                   math.pow((linear_val - 0.5) * 2, 0.2))) * 100
            return str(round(value, 2)) + '%'

    def check_encodings(self):
        self.known_face_encodings = {'encodings': [], 'names': []}
        if os.path.exists(constants.ENCODINGS_PATH):
            encodings = pickle.loads(
                open(constants.ENCODINGS_PATH, "rb").read())
            self.known_face_encodings = encodings

import base64
import json
import os
import threading


class CameraCredentialManager:
    """Simple local credential store for network cameras.

    Note: credentials are obfuscated (base64), not cryptographically encrypted.
    """

    def __init__(self, file_path=None):
        root = os.path.abspath(os.curdir)
        self.file_path = file_path or os.path.join(root, "logic", "camera_search", "camera_credentials.json")
        self._lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({"credentials": {}}, f, indent=2)

    def _load(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _enc(value):
        if value is None:
            return ""
        return base64.b64encode(value.encode("utf-8")).decode("ascii")

    @staticmethod
    def _dec(value):
        if not value:
            return ""
        try:
            return base64.b64decode(value.encode("ascii")).decode("utf-8")
        except Exception:
            return ""

    def upsert(self, host, username, password, port=80, wsdl_path=""):
        key = host.strip()
        with self._lock:
            data = self._load()
            data.setdefault("credentials", {})[key] = {
                "username": self._enc(username.strip()),
                "password": self._enc(password),
                "port": int(port),
                "wsdl_path": wsdl_path or "",
            }
            self._save(data)

    def delete(self, host):
        key = host.strip()
        with self._lock:
            data = self._load()
            if key in data.get("credentials", {}):
                del data["credentials"][key]
                self._save(data)

    def get(self, host):
        key = host.strip()
        with self._lock:
            data = self._load()
            rec = data.get("credentials", {}).get(key)
            if not rec:
                return None
            return {
                "host": key,
                "username": self._dec(rec.get("username", "")),
                "password": self._dec(rec.get("password", "")),
                "port": int(rec.get("port", 80)),
                "wsdl_path": rec.get("wsdl_path", ""),
            }

    def get_all(self):
        with self._lock:
            data = self._load()
            output = []
            for host, rec in data.get("credentials", {}).items():
                output.append({
                    "host": host,
                    "username": self._dec(rec.get("username", "")),
                    "password": self._dec(rec.get("password", "")),
                    "port": int(rec.get("port", 80)),
                    "wsdl_path": rec.get("wsdl_path", ""),
                })
            return output

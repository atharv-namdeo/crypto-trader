import json
import logging
import os
from pathlib import Path

log = logging.getLogger("LocalStorageManager")

class LocalStorageManager:
    """
    Handles local synchronization for the Trading Engine using a JSON database.
    Mimics Firebase Realtime Database interface for easy replacement.
    """
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LocalStorageManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_path="data/local_db.json"):
        if self._initialized:
            return
            
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.db_path.exists():
            with open(self.db_path, "w") as f:
                json.dump({}, f)
        
        self._initialized = True
        log.info(f"✅ Local Storage initialized at {self.db_path}")

    def _read_db(self) -> dict:
        try:
            with open(self.db_path, "r") as f:
                return json.load(f)
        except Exception as e:
            log.error(f"❌ Read error: {e}")
            return {}

    def _write_db(self, data: dict):
        try:
            with open(self.db_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            log.error(f"❌ Write error: {e}")

    def set(self, path: str, data: any):
        """Write data to a specific node."""
        db_data = self._read_db()
        keys = path.strip("/").split("/")
        
        current = db_data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = data
        self._write_db(db_data)

    def update(self, path: str, data: dict):
        """Update specific fields in a node."""
        db_data = self._read_db()
        keys = path.strip("/").split("/")
        
        current = db_data
        for key in keys:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        if isinstance(current, dict):
            current.update(data)
            self._write_db(db_data)
        else:
            log.error(f"❌ Path {path} is not a dictionary, cannot update.")

    def get(self, path: str):
        """Read data from a node."""
        db_data = self._read_db()
        keys = path.strip("/").split("/")
        
        current = db_data
        for key in keys:
            if key not in current:
                return None
            current = current[key]
        return current

    def delete(self, path: str):
        """Remove a node."""
        db_data = self._read_db()
        keys = path.strip("/").split("/")
        
        current = db_data
        for key in keys[:-1]:
            if key not in current:
                return
            current = current[key]
        
        if keys[-1] in current:
            del current[keys[-1]]
            self._write_db(db_data)

    def push(self, path: str, data: any):
        """Push data to a list node (creates a simple incrementing ID)."""
        db_data = self._read_db()
        keys = path.strip("/").split("/")
        
        current = db_data
        for key in keys:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        import time
        new_id = str(int(time.time() * 1000))
        current[new_id] = data
        self._write_db(db_data)
        return new_id

import logging
from core.local_storage_manager import LocalStorageManager

log = logging.getLogger("FirebaseManager")

class FirebaseManager:
    """
    Wrapper for LocalStorageManager that mimics the Firebase interface.
    Ensures absolute local execution while maintaining existing code structure.
    """
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(FirebaseManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, database_url=None):
        if self._initialized:
            return
            
        self.local_storage = LocalStorageManager()
        self._initialized = True
        log.info("✅ FirebaseManager (Local Wrapper) initialized successfully")

    def set(self, path: str, data: any):
        """Write data to a specific node."""
        self.local_storage.set(path, data)

    def update(self, path: str, data: dict):
        """Update specific fields in a node."""
        self.local_storage.update(path, data)

    def get(self, path: str):
        """Read data from a node."""
        return self.local_storage.get(path)

    def delete(self, path: str):
        """Remove a node."""
        self.local_storage.delete(path)

    def push(self, path: str, data: any):
        """Push data to a list node."""
        return self.local_storage.push(path, data)

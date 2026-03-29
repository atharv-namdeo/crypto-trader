import firebase_admin
from firebase_admin import credentials, db
import logging
import os
import json

log = logging.getLogger("FirebaseManager")

class FirebaseManager:
    """
    Handles synchronization between the Trading Engine and Firebase Realtime Database.
    Serves as the Single Source of Truth for the Hedge Fund platform.
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
            
        self.db_url = database_url or os.getenv("FIREBASE_URL")
        cred_json = os.getenv("FIREBASE_CREDENTIALS")
        
        try:
            if cred_json:
                # cred_json can be a path or a JSON string
                if cred_json.endswith('.json'):
                    cred = credentials.Certificate(cred_json)
                else:
                    cred = credentials.Certificate(json.loads(cred_json))
                
                firebase_admin.initialize_app(cred, {
                    'databaseURL': self.db_url
                })
                self._initialized = True
                log.info("✅ Firebase Admin initialized successfully")
            else:
                log.warning("⚠️ FIREBASE_CREDENTIALS missing. Firebase sync will be disabled.")
        except Exception as e:
            log.error(f"❌ Firebase Initialization Error: {e}")

    def set(self, path: str, data: any):
        """Write data to a specific Firebase node."""
        if not self._initialized: return
        try:
            ref = db.reference(path)
            ref.set(data)
        except Exception as e:
            log.error(f"❌ Firebase Write Error [{path}]: {e}")

    def update(self, path: str, data: dict):
        """Update specific fields in a Firebase node."""
        if not self._initialized: return
        try:
            ref = db.reference(path)
            ref.update(data)
        except Exception as e:
            log.error(f"❌ Firebase Update Error [{path}]: {e}")

    def get(self, path: str):
        """Read data from a Firebase node."""
        if not self._initialized: return None
        try:
            ref = db.reference(path)
            return ref.get()
        except Exception as e:
            log.error(f"❌ Firebase Read Error [{path}]: {e}")
            return None

    def delete(self, path: str):
        """Remove a node from Firebase."""
        if not self._initialized: return
        try:
            ref = db.reference(path)
            ref.delete()
        except Exception as e:
            log.error(f"❌ Firebase Delete Error [{path}]: {e}")

    def push(self, path: str, data: any):
        """Push data to a list node (creates unique ID)."""
        if not self._initialized: return
        try:
            ref = db.reference(path)
            ref.push(data)
        except Exception as e:
            log.error(f"❌ Firebase Push Error [{path}]: {e}")

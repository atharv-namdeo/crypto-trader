import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os
import json

# Initialise Firebase (only once)
# Supports: 1) Local firebase_key.json  2) FIREBASE_CREDENTIALS env var (for cloud)
_cred_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'firebase_key.json')

if not firebase_admin._apps:
    if os.path.exists(_cred_path):
        cred = credentials.Certificate(_cred_path)
        firebase_admin.initialize_app(cred)
    elif os.environ.get('FIREBASE_CREDENTIALS'):
        cred_dict = json.loads(os.environ['FIREBASE_CREDENTIALS'])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    else:
        print("[Firebase] No credentials found — logging disabled")

db = firestore.client() if firebase_admin._apps else None


def log_signal(signal):
    """Write a signal document to Firestore."""
    if db is None:
        print(f"[Firebase] (offline) Signal: {signal}")
        return
    try:
        signal['timestamp'] = datetime.utcnow().isoformat()
        db.collection('signals').add(signal)
    except Exception as e:
        print(f"[Firebase] Error logging signal: {e}")


def log_trade(trade):
    """Write a trade document to Firestore."""
    if db is None:
        print(f"[Firebase] (offline) Trade: {trade}")
        return
    try:
        trade['timestamp'] = datetime.utcnow().isoformat()
        db.collection('trades').add(trade)
    except Exception as e:
        print(f"[Firebase] Error logging trade: {e}")


def log_equity(capital):
    """Write an equity snapshot to Firestore."""
    if db is None:
        print(f"[Firebase] (offline) Equity: {capital}")
        return
    try:
        db.collection('equity').add({
            'capital': capital,
            'timestamp': datetime.utcnow().isoformat(),
        })
    except Exception as e:
        print(f"[Firebase] Error logging equity: {e}")


def log_balance(balances):
    """Log a snapshot of current wallet balances (non-zero only)."""
    if db is None:
        return
    try:
        # We store as a document in 'balances' collection with a timestamp
        db.collection('balances').document('current').set({
            'assets': balances,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"[Firebase] Error logging balance: {e}")


def get_settings():
    """Fetch bot settings from Firestore."""
    if db is None:
        return {}
    try:
        doc = db.collection('config').document('bot_settings').get()
        return doc.to_dict() if doc.exists else {}
    except Exception as e:
        print(f"[Firebase] Error fetching settings: {e}")
        return {}


def get_all_trades():
    """Fetch all trades from Firestore."""
    if db is None:
        return []
    try:
        # Fetch all documents from 'trades' collection, ordered by timestamp
        # Using string 'DESCENDING' as proven in read_firebase.py
        docs = db.collection('trades').order_by('timestamp', direction='DESCENDING').stream()
        trades = []
        for doc in docs:
            t = doc.to_dict()
            t['id'] = doc.id  # Include doc ID just in case
            trades.append(t)
        return trades
    except Exception as e:
        print(f"[Firebase] Error fetching trades: {e}")
        return []



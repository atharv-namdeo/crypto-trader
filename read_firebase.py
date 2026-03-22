import os
import sys

# Add project root to path
sys.path.append('c:\\Users\\ACER\\OneDrive\\Desktop\\crypto-trader')

from utils.firebase_client import db

if db is None:
    print("DB is None!")
    sys.exit(1)

try:
    # Get all signals
    docs = db.collection('signals').order_by('timestamp', direction='DESCENDING').limit(10).stream()
    signals = [doc.to_dict() for doc in docs]
    print(f"FOUND {len(signals)} SIGNALS IN FIREBASE!")
    for s in signals:
        print(" ->", s)
        
    trades = db.collection('trades').limit(5).stream()
    print(f"FOUND {len(list(trades))} TRADES IN FIREBASE!")
except Exception as e:
    print(f"Error reading from Firebase: {e}")

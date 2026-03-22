import os
import sys

# Add project root to path
sys.path.append('c:\\Users\\ACER\\OneDrive\\Desktop\\crypto-trader')

try:
    from utils.firebase_client import log_signal, log_equity, log_balance, db
    print("DB initialized:", db is not None)
    
    # 1. Test Signal
    log_signal({
        'strategy': 'TEST_ALGO',
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'confidence': 0.99,
        'reason': 'Testing Firebase Connection'
    })
    print("Test signal logged!")
    
    # 2. Test Equity
    log_equity(1234.56)
    print("Test equity logged!")
    
    # 3. Test Balance
    log_balance([
        {"asset": "USDT", "balance": 1234.56},
        {"asset": "TEST", "balance": 999.9}
    ])
    print("Test balance logged!")

except Exception as e:
    print(f"Error: {e}")

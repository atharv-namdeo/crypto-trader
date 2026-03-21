import os
from dotenv import load_dotenv
import ccxt

load_dotenv()

# Trading Mode
DRY_RUN = os.getenv('DRY_RUN', 'true').lower() == 'true'
CAPITAL = float(os.getenv('CAPITAL', '1000'))
INR_RATE = 84.5 # Fixed conversion rate for display

# Symbols to trade (USDS-M Futures)
SYMBOLS = ['BTC/USDT', 'ETH/USDT']

# Timeframes for analysis
TIMEFRAMES = ['5m', '15m', '1h']
MACRO_TIMEFRAME = '4h'

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


def get_exchange(use_testnet=True):
    """Create and return a configured Binance exchange instance."""
    prefix = 'BINANCE_TEST_' if use_testnet else 'BINANCE_REAL_'
    
    api_key = os.getenv(prefix + 'API_KEY', '')
    api_secret = os.getenv(prefix + 'API_SECRET', '')
    
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
            'adjustForTimeDifference': True,
            'recvWindow': 10000
        },
    })
    
    if use_testnet:
        try:
            exchange.set_sandbox_mode(True)
        except Exception as e:
            print(f"⚠️ Sandbox mode not supported, using production with DRY_RUN: {e}")
            # Fall back to production endpoint but keep DRY_RUN active
    
    return exchange

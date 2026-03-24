import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import List, Optional

load_dotenv()

class Settings(BaseSettings):
    # --- BINANCE KEYS ---
    BINANCE_TEST_API_KEY: str = ""
    BINANCE_TEST_API_SECRET: str = ""
    BINANCE_REAL_API_KEY: str = ""
    BINANCE_REAL_API_SECRET: str = ""
    
    # UNIFIED KEYS
    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""

    # --- BOT SETTINGS ---
    DRY_RUN: bool = False
    BINANCE_TESTNET: bool = True
    CAPITAL: float = 1000.0
    RISK_PER_TRADE: float = 0.02
    
    # --- REDIS ---
    REDIS_URL: str = "redis://localhost:6379"
    
    # --- TELEGRAM ---
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # --- TRADING CONFIG ---
    SYMBOLS: List[str] = [
        'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
        'MATIC/USDT', 'AVAX/USDT', 'LINK/USDT', 'UNI/USDT', 'DOT/USDT'
    ]
    # UPDATED: Dictionary format as requested, plus extras for swing/position
    TIMEFRAMES: Dict[str, str] = {
        'scalper': '1m',
        'swing': '1h',
        'position': '4h',
        'swing_extra': '4h',
        'position_extra': '1d'
    }

settings = Settings()

# Exposed for backward compatibility
SYMBOLS = settings.SYMBOLS
CAPITAL = settings.CAPITAL
REDIS_URL = settings.REDIS_URL
TIMEFRAMES = settings.TIMEFRAMES

def get_exchange(use_testnet=True):
    import ccxt
    prefix = 'BINANCE_TEST_' if use_testnet else 'BINANCE_REAL_'
    
    api_key = getattr(settings, f"{prefix}API_KEY") or settings.BINANCE_API_KEY
    api_secret = getattr(settings, f"{prefix}API_SECRET") or settings.BINANCE_API_SECRET
    
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
            print(f"⚠️ Sandbox mode error: {e}")
            
    return exchange

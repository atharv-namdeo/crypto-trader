import os
import logging
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict
from config_symbols import SYMBOL_CONFIG, CryptoTier

load_dotenv()
log = logging.getLogger("Config")

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

    # --- MULTI-STRATEGY ALLOCATION ---
    STRATEGY_ALLOCATIONS: Dict[str, float] = {
        'scalper': 0.15,      # 15%
        'swing': 0.35,        # 35%
        'position': 0.40,     # 40%
        'ai_ensemble': 0.10   # 10%
    }
    
    # Per-strategy position limits
    MAX_POSITIONS_PER_STRATEGY: Dict[str, int] = {
        'scalper': 5,
        'swing': 3,
        'position': 2,
        'ai_ensemble': 2
    }

    # --- TRADING CONFIG ---
    ACTIVE_TIERS: List[CryptoTier] = [
        CryptoTier.TIER_1,
        CryptoTier.TIER_2,
        CryptoTier.TIER_3,
        # CryptoTier.TIER_4  # Disable tier 4 (lowest liquidity) by default to save resources
    ]

    @property
    def SYMBOLS(self) -> List[str]:
        """Dynamically build symbol list from active tiers"""
        symbols = []
        for tier in self.ACTIVE_TIERS:
            symbols.extend(SYMBOL_CONFIG.get(tier, []))
        return symbols

    def get_symbols(self) -> List[str]:
        """Helper to get symbols if property is not accessible easily"""
        return self.SYMBOLS
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
    import ccxt.async_support as ccxt
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
            # CCXT's set_sandbox_mode(True) for Binance Futures is being deprecated 
            # by Binance in favor of "Demo Trading". 
            exchange.set_sandbox_mode(True)
        except Exception as e:
            if "not supported for futures anymore" in str(e):
                log.warning("⚠️ Binance Testnet Sandbox is deprecated for Futures. Falling back to default (Demo Trading keys).")
            else:
                log.warning(f"⚠️ Sandbox mode error: {e}")
            
    return exchange

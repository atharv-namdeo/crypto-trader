import os
import logging
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict
from config_symbols import SYMBOL_CONFIG, CryptoTier

load_dotenv()
log = logging.getLogger("Config")

class Settings(BaseSettings):
    # --- BINANCE DEMO ACCOUNT KEYS (Replaces Testnet) ---
    # Create at: https://testnet.binance.vision/
    BINANCE_DEMO_API_KEY: str = ""
    BINANCE_DEMO_API_SECRET: str = ""
    
    # LEGACY KEYS (for reference)
    BINANCE_TEST_API_KEY: str = ""
    BINANCE_TEST_API_SECRET: str = ""
    BINANCE_REAL_API_KEY: str = ""
    BINANCE_REAL_API_SECRET: str = ""
    
    # UNIFIED KEYS
    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""

    # --- BOT SETTINGS ---
    DRY_RUN: bool = False
    BINANCE_TESTNET: bool = True  # Use demo account (not sandbox)
    CAPITAL: float = 1000.0
    RISK_PER_TRADE: float = 0.02
    
    # --- REDIS ---
    REDIS_URL: str = "redis://localhost:6379"
    
    # --- TELEGRAM ---
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # --- AUTONOMOUS MODE ---
    AUTONOMOUS_MODE: bool = True          # Fully automated — no user selection needed
    ENABLE_DYNAMIC_REBALANCING: bool = True
    REBALANCE_INTERVAL_SECONDS: int = 3600  # Rebalance every hour
    SHARPE_THRESHOLD: float = 0.5          # Only allocate to strategies with Sharpe > 0.5
    ABANDON_SHARPE: float = -0.5           # Abandon strategies below this Sharpe

    # --- SIGNAL QUALITY FILTERS ---
    MIN_SIGNAL_CONFIRMATIONS: int = 2        # Require 2+ confirmations before entry
    MIN_LIQUIDITY_USD: float = 1_000_000.0   # Skip coins with < $1M daily volume
    MAX_HOURLY_VOLATILITY: float = 0.10      # Skip coins with > 10% hourly moves
    REQUIRE_EMA_TREND_ALIGNMENT: bool = True  # price > EMA20 > EMA50 for longs

    # --- REGIME-AWARE ATR MULTIPLIERS (SL / TP) ---
    REGIME_ATR_MULTIPLIERS: Dict[str, Dict[str, float]] = {
        'TRENDING_BULL':        {'sl': 3.5, 'tp': 7.0},
        'TRENDING_BEAR':        {'sl': 3.5, 'tp': 7.0},
        'TRENDING_NEUTRAL':     {'sl': 3.0, 'tp': 6.5},
        'HIGH_VOL_CHOP':        {'sl': 2.0, 'tp': 5.0},
        'LOW_VOL_ACCUMULATION': {'sl': 4.0, 'tp': 6.0},
        'NEUTRAL':              {'sl': 3.0, 'tp': 6.0},
    }

    # --- KELLY CRITERION POSITION SIZING ---
    KELLY_FRACTION: float = 0.25    # Quarter-Kelly for safety
    MIN_RISK_PCT: float = 0.01      # Minimum 1% per trade
    MAX_RISK_PCT: float = 0.05      # Maximum 5% per trade

    # --- CONSECUTIVE LOSS PROTECTION ---
    MAX_CONSECUTIVE_LOSSES: int = 5  # Throttle after this many losses in a row

    # --- MULTI-STRATEGY ALLOCATION (initial; rebalanced automatically) ---
    STRATEGY_ALLOCATIONS: Dict[str, float] = {
        'scalper': 0.05,          # ↓ Reduced (high false-signal rate)
        'swing': 0.35,            # ↑ Reliable trend-following
        'position': 0.40,         # Best risk:reward
        'ai_ensemble': 0.10,      # Multi-timeframe ensemble
        'mean_reversion': 0.05,   # Range/chop environments
        'ensemble_voting': 0.05,  # Voting-based confirmation
    }
    
    # Per-strategy position limits
    MAX_POSITIONS_PER_STRATEGY: Dict[str, int] = {
        'scalper': 3,
        'swing': 4,
        'position': 3,
        'ai_ensemble': 3,
        'mean_reversion': 3,
        'ensemble_voting': 2,
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
    """
    Initialize Binance SPOT demo trading
    """
    import ccxt.async_support as ccxt
    
    if use_testnet:
        # Try DEMO first, then TEST, then generic keys
        api_key = (
            settings.BINANCE_DEMO_API_KEY or 
            settings.BINANCE_TEST_API_KEY or 
            settings.BINANCE_API_KEY
        )
        api_secret = (
            settings.BINANCE_DEMO_API_SECRET or 
            settings.BINANCE_TEST_API_SECRET or 
            settings.BINANCE_API_SECRET
        )
    else:
        api_key = settings.BINANCE_REAL_API_KEY or settings.BINANCE_API_KEY
        api_secret = settings.BINANCE_REAL_API_SECRET or settings.BINANCE_API_SECRET
    
    if not api_key or not api_secret:
        error_msg = "❌ Missing Binance API credentials!"
        log.error(error_msg)
        raise ValueError(error_msg)
    
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'sandbox': use_testnet,  # ← USE SANDBOX MODE TO BYPASS RESTRICTED LOCATIONS
        'options': {
            'defaultType': 'spot',
            'adjustForTimeDifference': True,
            'recvWindow': 10000,
            'fetchMyTradesMethod': 'private', # Avoid /sapi/ calls that leak to live API
        },
    })
    
    # SET CORRECT DEMO ENDPOINT FOR SPOT
    if use_testnet:
        exchange.urls['api']['spot'] = 'https://demo-api.binance.com/api'
        log.info("✅ Using Binance Demo Account SPOT (demo-api.binance.com)")
    else:
        log.warning("⚠️ LIVE REAL ACCOUNT MODE - USE WITH CAUTION")
    
    return exchange

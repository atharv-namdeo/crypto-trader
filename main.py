import time
import pandas as pd
import os
import numpy as np
from datetime import datetime

# Core Engine Imports
from config import get_exchange, SYMBOLS, DRY_RUN, CAPITAL, INR_RATE, MACRO_TIMEFRAME
from core.regime import RegimeClassifier
from core.router import AlgoRouter
from core.risk import RiskManager
from data.processor import FeatureProcessor

# Utils & Execution
from execution.order_manager import place_order
from utils.telegram_alert import send_alert
from utils.firebase_client import log_signal, log_trade, log_equity, log_balance, get_settings

# Initialize Core Components
regime_classifier = RegimeClassifier()
router = AlgoRouter()
risk_manager = RiskManager()
processor = FeatureProcessor()

# Initial Exchange Setup
current_use_testnet = True 
exchange = get_exchange(use_testnet=current_use_testnet)

CYCLE_INTERVAL = 60  # Check every 60 seconds for faster signals

def sync_exchange():
    """Check Firestore settings and update exchange if mode changed."""
    global exchange, current_use_testnet
    try:
        settings = get_settings()
        new_mode = settings.get('use_testnet', True)
        
        if new_mode != current_use_testnet:
            print(f"🔄 Mode Switch: {'TESTNET' if new_mode else 'REAL'}")
            exchange = get_exchange(use_testnet=new_mode)
            current_use_testnet = new_mode
    except Exception as e:
        print(f"⚠️ Settings sync error: {e}")

def fetch_data(symbol, timeframe='1h', limit=250):
    """Fetch OHLCV and return a cleaned DataFrame."""
    try:
        data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"⚠️ Data Fetch Error ({symbol} {timeframe}): {e}")
        return None

def fetch_all_data(symbols, timeframe='1h', limit=250):
    """Fetch OHLCV for all symbols and return a dictionary of DataFrames."""
    data_dict = {}
    for symbol in symbols:
        df = fetch_data(symbol, timeframe, limit)
        if df is not None:
            data_dict[symbol] = df
    return data_dict

def sync_balances():
    """Fetch and log current wallet balances to Firebase."""
    try:
        balance = exchange.fetch_balance()
        assets = []
        for asset, info in balance.get('total', {}).items():
            if info and float(info) > 0:
                free = balance.get('free', {}).get(asset, 0) or 0
                assets.append({
                    'asset': asset,
                    'balance': float(info),
                    'free': float(free),
                    'pnl': 0
                })
        if assets:
            log_balance(assets)
            print(f"💰 Synced {len(assets)} assets to Firebase")
        
        total_usdt = balance.get('total', {}).get('USDT', CAPITAL)
        return float(total_usdt) if total_usdt else CAPITAL
    except Exception as e:
        print(f"⚠️ Balance sync error: {e}")
        return CAPITAL

def analyze_market(symbol, data_dict):
    """Main Analysis Pipeline per Symbol."""
    df_1h = data_dict.get(symbol)
    df_4h = fetch_data(symbol, MACRO_TIMEFRAME, limit=100)
    
    # Fetch Order Book for OBIS
    order_book = None
    try:
        order_book = exchange.fetch_order_book(symbol, limit=10)
    except: pass

    if df_1h is None or df_4h is None: return

    # 2. Macro Trend
    df_4h['ema_200'] = df_4h['close'].ewm(span=200, adjust=False).mean()
    macro_trend = 'BULLISH' if df_4h['close'].iloc[-1] > df_4h['ema_200'].iloc[-1] else 'BEARISH'

    # 3. Regime Classification
    regime_data = regime_classifier.classify(df_1h, funding_rate=0.01 if macro_trend == 'BULLISH' else -0.01)
    current_regime = regime_data['regime']
    
    # 4. Get Active Strategies
    active_strategies = router.get_active_strategies(current_regime)
    
    if not active_strategies:
        print(f"  ⏭️ No active strategies for regime: {current_regime}")
        return

    print(f"  📊 {symbol} | Regime: {current_regime} | Macro: {macro_trend} | Checking {len(active_strategies)} algos...")

    # 5. Process Signals
    for strategy in active_strategies:
        try:
            signal = None
            
            # Strategy-Specific Inputs
            if strategy.NAME == 'STAT_ARB':
                signal = strategy.calculate_signal(data_dict, portfolio_value=CAPITAL)
                if signal.get('symbol') != symbol: continue 
            elif strategy.NAME == 'OBIS':
                signal = strategy.calculate_signal(df_1h, order_book=order_book, portfolio_value=CAPITAL)
            elif strategy.NAME == 'MTF_MACD':
                signal = strategy.calculate_signal(df_1h, df_4h=df_4h, portfolio_value=CAPITAL)
            else:
                signal = strategy.calculate_signal(df_1h, macro_trend=macro_trend, portfolio_value=CAPITAL)
            
            if signal and signal.get('direction') != 'NONE':
                signal['symbol'] = symbol
                signal['regime'] = current_regime
                signal['strategy'] = strategy.NAME
                print(f"  🎯 [{strategy.NAME}] Signal: {signal['direction']} on {symbol}")

                # 6. Risk Overlay
                if risk_manager.validate_trade(signal, CAPITAL, []):
                    log_signal(signal)
                    send_alert(signal)
                    if not DRY_RUN:
                        place_order(signal, signal['sl'], signal['tp'], signal['qty'])
                        log_trade(signal)
                    else:
                        print(f"  🔬 [DRY RUN] {strategy.NAME} would execute {signal['direction']} on {symbol}")
            
        except Exception as e:
            print(f"  ⚠️ [{strategy.NAME}] Error: {e}")

def run_bot():
    print(f"🤖 Quant Engine v3.0 Starting | 20 Algos Active | Cycle: {CYCLE_INTERVAL}s")
    send_alert({'symbol': 'SYSTEM', 'direction': 'INFO', 'entry': '-', 'reason': '🤖 Engine v3.0 (20-Algo) Started'})
    
    cycle = 0
    while True:
        cycle += 1
        try:
            print(f"\n{'='*60}")
            print(f"🔄 Cycle #{cycle} | {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*60}")
            
            sync_exchange()
            
            # 1. Sync Portfolio & Balances to Firebase
            total_usdt = sync_balances()
            log_equity(total_usdt)
            
            if risk_manager.check_daily_drawdown(CAPITAL, total_usdt):
                print("🛑 Daily drawdown limit hit — pausing engine")
                break

            # 2. Fetch All Market Data
            current_data = fetch_all_data(SYMBOLS)
            
            if not current_data:
                print("⚠️ No market data fetched — retrying next cycle")
                time.sleep(CYCLE_INTERVAL)
                continue
            
            # 3. Analyze each symbol
            for symbol in SYMBOLS:
                if symbol in current_data:
                    analyze_market(symbol, current_data)

            print(f"\n✅ Cycle #{cycle} complete. Next check in {CYCLE_INTERVAL}s...")

        except Exception as e:
            print(f"❌ Core Loop Error: {e}")
            import traceback
            traceback.print_exc()
            
        time.sleep(CYCLE_INTERVAL)

if __name__ == "__main__":
    run_bot()

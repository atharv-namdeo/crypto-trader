"""
main.py — Quant Engine v4.0 (Phase 1: Ensemble + Position Manager)

Architecture:
  - 20 algos each return a directional signal (LONG/SHORT/NONE + confidence)
  - EnsembleScorer combines them → final_score ∈ [-1, +1]
  - Score > 0.25 → open/hold LONG  (size scales with conviction)
  - Score < -0.25 → open/hold SHORT
  - PositionTracker manages trailing stops, TP1/TP2, flip logic every cycle
  - RiskManager gates every entry with RR, heat, exposure checks
"""

import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime

# ── Core Engine ────────────────────────────────────────────────────────────
from config import get_exchange, SYMBOLS, DRY_RUN, CAPITAL, MACRO_TIMEFRAME
from core.regime import RegimeClassifier
from core.ensemble import compute_ensemble
from core.position_tracker import PositionTracker
from core.risk import RiskManager

# ── Strategies (20 algos) ─────────────────────────────────────────────────
from strategies.mtf import MomentumTrendFollowing
from strategies.stat_arb import StatArb
from strategies.mean_reversion import MeanReversion
from strategies.breakout import VolatilityBreakout
from strategies.obis import OrderBookImbalance
from strategies.vwap_reversion import VWAPReversion
from strategies.liquidity_sweep import LiquiditySweep
from strategies.mtf_macd import MTFMACD
from strategies.rsi_divergence import RSIDivergence
from strategies.fibonacci import FibonacciRetracement
from strategies.ichimoku import IchimokuCloud
from strategies.atr_expansion import ATRExpansion
from strategies.volume_profile import VolumeProfile
from strategies.pivot_points import PivotPoints
from strategies.psar import ParabolicSAR
from strategies.supertrend import SupertrendStrategy
from strategies.gann import GANNFan
from strategies.harmonic import HarmonicPatterns
from strategies.liquidity_grabs import LiquidityGrabs
from strategies.trend_exhaustion import TrendExhaustion

# ── Utils & Execution ─────────────────────────────────────────────────────
from execution.order_manager import place_order
from utils.telegram_alert import send_alert
from utils.firebase_client import log_signal, log_trade, log_equity, log_balance, get_settings
import utils.indicators as ta_ind

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)
log = logging.getLogger("ENGINE")

# ── Constants ─────────────────────────────────────────────────────────────
CYCLE_INTERVAL    = 60      # seconds between full engine cycles
SCORE_THRESHOLD   = 0.25    # |score| > this → take action
SCORE_STRONG      = 0.55    # |score| > this → full size
FLIP_THRESHOLD    = 0.45    # score reversal magnitude to flip position

# ── Initialize Components ─────────────────────────────────────────────────
regime_classifier = RegimeClassifier()
position_tracker  = PositionTracker()
risk_manager      = RiskManager()

# ── All 20 Strategies ─────────────────────────────────────────────────────
ALL_STRATEGIES = {
    'MTF':             MomentumTrendFollowing(),
    'STAT_ARB':        StatArb(),
    'MEAN_REVERSION':  MeanReversion(),
    'BREAKOUT':        VolatilityBreakout(),
    'OBIS':            OrderBookImbalance(),
    'VWAP_REVERSION':  VWAPReversion(),
    'LIQUIDITY_SWEEP': LiquiditySweep(),
    'MTF_MACD':        MTFMACD(),
    'RSI_DIV':         RSIDivergence(),
    'FIBONACCI':       FibonacciRetracement(),
    'ICHIMOKU':        IchimokuCloud(),
    'ATR_EXPANSION':   ATRExpansion(),
    'VOLUME_PROFILE':  VolumeProfile(),
    'PIVOT_POINTS':    PivotPoints(),
    'PSAR':            ParabolicSAR(),
    'SUPERTREND':      SupertrendStrategy(),
    'GANN_FAN':        GANNFan(),
    'HARMONIC':        HarmonicPatterns(),
    'LIQUIDITY_GRAB':  LiquidityGrabs(),
    'TREND_EXHAUST':   TrendExhaustion(),
}

# ── Exchange ───────────────────────────────────────────────────────────────
current_use_testnet = True
exchange = get_exchange(use_testnet=current_use_testnet)


# ══ HELPER FUNCTIONS ══════════════════════════════════════════════════════

def sync_exchange():
    """Check Firestore settings and update exchange mode if changed."""
    global exchange, current_use_testnet
    try:
        settings = get_settings()
        new_mode = settings.get('use_testnet', True)
        if new_mode != current_use_testnet:
            log.info(f"🔄 Mode Switch → {'TESTNET' if new_mode else 'LIVE'}")
            exchange = get_exchange(use_testnet=new_mode)
            current_use_testnet = new_mode
    except Exception as e:
        log.warning(f"Settings sync error: {e}")


def fetch_data(symbol: str, timeframe: str = '1h', limit: int = 250) -> pd.DataFrame | None:
    """Fetch OHLCV from exchange."""
    try:
        raw = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df  = pd.DataFrame(raw, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        log.warning(f"Data fetch error ({symbol} {timeframe}): {e}")
        return None


def fetch_all_data(symbols: list, timeframe: str = '1h', limit: int = 250) -> dict:
    return {s: df for s in symbols if (df := fetch_data(s, timeframe, limit)) is not None}


def compute_atr(df: pd.DataFrame, period: int = 14) -> float:
    """ATR for stop/TP calculation."""
    try:
        atr_series = ta_ind.atr(df['high'], df['low'], df['close'], length=period)
        val = float(atr_series.iloc[-1])
        return val if not np.isnan(val) else float(df['close'].iloc[-1] * 0.01)
    except Exception:
        return float(df['close'].iloc[-1] * 0.01)  # fallback: 1% of price


def sync_balances() -> float:
    """Fetch wallet balances and sync to Firebase. Returns USDT balance."""
    try:
        balance = exchange.fetch_balance()
        assets = [
            {
                'asset': asset,
                'balance': float(info),
                'free': float(balance.get('free', {}).get(asset, 0) or 0),
                'pnl': 0,
            }
            for asset, info in balance.get('total', {}).items()
            if info and float(info) > 0
        ]
        if assets:
            log_balance(assets)
            log.info(f"💰 Synced {len(assets)} assets to Firebase")
        usdt = balance.get('total', {}).get('USDT', CAPITAL)
        return float(usdt) if usdt else CAPITAL
    except Exception as e:
        log.warning(f"Balance sync error: {e}")
        return CAPITAL


# ══ SIGNAL COLLECTION ════════════════════════════════════════════════════

def collect_signals(symbol: str, df_1h: pd.DataFrame, df_4h: pd.DataFrame,
                    macro_trend: str, data_dict: dict) -> dict:
    """
    Run all 20 strategies and return a dict of {name: signal_dict}.
    Every strategy returns at minimum: {'direction': 'LONG'|'SHORT'|'NONE', 'confidence': 0–1}
    """
    order_book = None
    try:
        order_book = exchange.fetch_order_book(symbol, limit=10)
    except Exception:
        pass

    signal_map = {}

    for name, strategy in ALL_STRATEGIES.items():
        try:
            if name == 'STAT_ARB':
                sig = strategy.calculate_signal(data_dict, portfolio_value=CAPITAL)
                # StatArb returns a signal for a specific symbol — skip if not ours
                if sig and sig.get('symbol', symbol) != symbol:
                    continue
            elif name == 'OBIS':
                sig = strategy.calculate_signal(df_1h, order_book=order_book,
                                                 portfolio_value=CAPITAL)
            elif name == 'MTF_MACD':
                sig = strategy.calculate_signal(df_1h, df_4h=df_4h,
                                                 portfolio_value=CAPITAL)
            else:
                sig = strategy.calculate_signal(df_1h, macro_trend=macro_trend,
                                                 portfolio_value=CAPITAL)

            if sig:
                # Normalize: ensure 'confidence' key exists
                if 'confidence' not in sig:
                    # Old strategies return LONG/SHORT/NONE with entry/sl/tp
                    # Derive confidence from the directional strength if missing
                    direction = sig.get('direction', 'NONE')
                    if direction != 'NONE' and sig.get('entry') and sig.get('sl') and sig.get('tp'):
                        risk   = abs(sig['entry'] - sig['sl'])
                        reward = abs(sig['tp'] - sig['entry'])
                        rr     = reward / (risk + 1e-9)
                        sig['confidence'] = float(np.clip(rr / 4.0, 0.1, 1.0))
                    else:
                        sig['confidence'] = 0.5 if direction != 'NONE' else 0.0
                signal_map[name] = sig

        except Exception as e:
            log.debug(f"[{name}] signal error: {e}")

    return signal_map


# ══ PER-SYMBOL ANALYSIS ═══════════════════════════════════════════════════

def analyze_symbol(symbol: str, data_dict: dict, capital: float) -> dict | None:
    """
    Full pipeline for one symbol:
      1. Fetch 4h data for macro trend
      2. Classify regime (softened)
      3. Collect all 20 signals
      4. Ensemble score
      5. Position management (trailing stop, TP, flip)
      6. Open/flip/close positions based on score
    """
    df_1h = data_dict.get(symbol)
    if df_1h is None:
        return None

    df_4h = fetch_data(symbol, MACRO_TIMEFRAME, limit=100)
    if df_4h is None:
        df_4h = df_1h  # fallback: use 1h as macro

    # ── Macro Trend ────────────────────────────────────────────────────────
    df_4h = df_4h.copy()
    df_4h['ema_200'] = df_4h['close'].ewm(span=min(200, len(df_4h)), adjust=False).mean()
    macro_trend = 'BULLISH' if df_4h['close'].iloc[-1] > df_4h['ema_200'].iloc[-1] else 'BEARISH'
    funding_rate = 0.0001 if macro_trend == 'BULLISH' else -0.0001

    # ── Regime ────────────────────────────────────────────────────────────
    regime_data   = regime_classifier.classify(df_1h, funding_rate=funding_rate)
    regime_label  = regime_data['regime']
    regime_conf   = regime_data['confidence']

    # ── ATR for stops ─────────────────────────────────────────────────────
    atr   = compute_atr(df_1h)
    price = float(df_1h['close'].iloc[-1])

    log.info(f"  📊 {symbol} | Regime: {regime_label} ({regime_conf:.0%}) | "
             f"Macro: {macro_trend} | Price: {price:.4f} | ATR: {atr:.4f}")

    # ── Collect all 20 signals ────────────────────────────────────────────
    signal_map = collect_signals(symbol, df_1h, df_4h, macro_trend, data_dict)
    fired = sum(1 for s in signal_map.values() if s.get('direction', 'NONE') != 'NONE')
    log.info(f"  🎯 {symbol} | {fired}/{len(signal_map)} algos fired signals")

    # ── Ensemble scoring ──────────────────────────────────────────────────
    ensemble = compute_ensemble(signal_map, regime_label, regime_conf)
    score      = ensemble['final_score']
    action     = ensemble['action']
    conviction = ensemble['conviction']
    agreement  = ensemble['agreement_ratio']

    log.info(f"  📈 {symbol} | Score: {score:+.3f} | Action: {action} | "
             f"Conviction: {conviction:.0%} | Agreement: {agreement:.0%}")

    # Log ensemble to Firebase (always, even if no trade — for dashboard)
    try:
        log_signal({
            'symbol':    symbol,
            'score':     score,
            'action':    action,
            'conviction': conviction,
            'regime':    regime_label,
            'agreement': agreement,
            'signal_scores': ensemble.get('signal_scores', {}),
            'macro_trend': macro_trend,
        })
    except Exception as e:
        log.debug(f"Firebase log error: {e}")

    # ── Position management (check existing position) ──────────────────────
    pos_action = position_tracker.update(symbol, price, atr, score)

    if pos_action['action'] == 'FLIP':
        log.info(f"  🔄 {symbol} POSITION FLIP → {pos_action['new_side']}")
        # Open reverse position immediately
        _open_new_position(symbol, score, conviction, price, atr, capital,
                           force_side=pos_action['new_side'], signal_map=signal_map)
        return ensemble

    if pos_action['action'] in ('CLOSE', 'REDUCE'):
        if pos_action['action'] == 'CLOSE' and not DRY_RUN:
            # Log closed trade
            log_trade({'symbol': symbol, 'action': 'CLOSE',
                       'reason': pos_action.get('reason', ''), 'price': price})
        return ensemble

    # ── Open new position if not already in one ────────────────────────────
    if not position_tracker.has_position(symbol) and action in ('LONG', 'SHORT'):
        _open_new_position(symbol, score, conviction, price, atr, capital,
                           signal_map=signal_map)

    return ensemble


def _open_new_position(symbol: str, score: float, conviction: float,
                       price: float, atr: float, capital: float,
                       force_side: str = None, signal_map: dict = None):
    """Size, validate, and open a new position."""
    side = force_side if force_side else ('LONG' if score > 0 else 'SHORT')

    # Position sizing
    sizing = risk_manager.compute_position_size(capital, conviction, atr, price)
    qty    = sizing['qty']

    if qty <= 0:
        log.warning(f"  ⚠️ {symbol} zero qty calculated — skipping")
        return

    # Stops & targets (ATR-based)
    stop_dist = 1.5 * atr
    tp1_dist  = stop_dist * 2.0
    stop = price - stop_dist if side == 'LONG' else price + stop_dist
    tp1  = price + tp1_dist  if side == 'LONG' else price - tp1_dist

    # Risk guard
    current_heat = position_tracker.total_heat(capital, capital)
    if not risk_manager.validate_trade(side, price, stop, tp1, qty,
                                       capital, current_heat):
        log.info(f"  🛡️ {symbol} trade BLOCKED by risk manager")
        return

    # Register in position tracker
    position_tracker.open_position(symbol, side, price, qty, atr, score)

    log.info(f"  ✅ {symbol} {side} | qty={qty:.6f} | "
             f"entry={price:.4f} stop={stop:.4f} tp1={tp1:.4f} | "
             f"conviction={conviction:.0%}")

    send_alert({
        'symbol':    symbol,
        'direction': side,
        'entry':     price,
        'sl':        stop,
        'tp':        tp1,
        'score':     score,
        'conviction': conviction,
        'reason':    f'EnsembleScore={score:+.3f}',
    })

    if not DRY_RUN:
        try:
            place_order({'symbol': symbol, 'direction': side,
                         'entry': price, 'sl': stop, 'tp': tp1, 'qty': qty})
            log_trade({'symbol': symbol, 'side': side, 'entry': price,
                       'stop': stop, 'tp': tp1, 'qty': qty, 'score': score})
        except Exception as e:
            log.error(f"  ❌ Order execution error: {e}")
    else:
        log.info(f"  🔬 [DRY RUN] Would {side} {qty:.6f} {symbol}")


# ══ MAIN LOOP ════════════════════════════════════════════════════════════

def run_bot():
    log.info("═" * 60)
    log.info("🤖 QUANT ENGINE v4.0 | Ensemble Mode | 20 Algos")
    log.info(f"   Mode: {'📄 PAPER (DRY RUN)' if DRY_RUN else '💰 LIVE TRADING'}")
    log.info(f"   Symbols: {SYMBOLS}")
    log.info(f"   Cycle: {CYCLE_INTERVAL}s | Score threshold: {SCORE_THRESHOLD}")
    log.info("═" * 60)

    send_alert({
        'symbol': 'SYSTEM',
        'direction': 'INFO',
        'entry': '-',
        'reason': f'🤖 Engine v4.0 Ensemble Mode Started | {len(ALL_STRATEGIES)} Algos',
    })

    start_capital = CAPITAL
    cycle = 0

    while True:
        cycle += 1
        cycle_start = time.time()

        try:
            log.info(f"\n{'═' * 60}")
            log.info(f"🔄 Cycle #{cycle} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            log.info(f"{'═' * 60}")

            # 1. Sync exchange mode from Firebase settings
            sync_exchange()

            # 2. Sync balances to Firebase
            current_capital = sync_balances()
            log_equity(current_capital)

            # 3. Emergency drawdown check
            if risk_manager.check_daily_drawdown(start_capital, current_capital):
                log.critical("🛑 HALTING ENGINE — daily drawdown limit hit")
                send_alert({'symbol': 'SYSTEM', 'direction': 'HALT',
                            'entry': '-', 'reason': '🛑 Daily drawdown limit reached'})
                break

            # 4. Fetch market data for all symbols
            data_dict = fetch_all_data(SYMBOLS)
            if not data_dict:
                log.warning("⚠️ No market data — retrying next cycle")
                time.sleep(CYCLE_INTERVAL)
                continue

            # 5. Analyze each symbol
            results = {}
            for symbol in SYMBOLS:
                if symbol in data_dict:
                    result = analyze_symbol(symbol, data_dict, current_capital)
                    if result:
                        results[symbol] = result

            # 6. Print cycle summary
            open_positions = position_tracker.get_all_positions()
            log.info(f"\n✅ Cycle #{cycle} done | "
                     f"Open positions: {len(open_positions)} | "
                     f"Capital: ${current_capital:,.2f}")
            for sym, pos in open_positions.items():
                if pos:
                    pnl_pct = ((data_dict.get(sym, {}) and
                                float(data_dict[sym]['close'].iloc[-1]) - pos.entry)
                               / pos.entry) if data_dict.get(sym) is not None else 0
                    log.info(f"   📌 {sym} {pos.side} @ {pos.entry:.4f} | "
                             f"Stop: {pos.stop:.4f}")

        except Exception as e:
            log.error(f"❌ Core loop error: {e}")
            import traceback
            traceback.print_exc()

        # Sleep for remainder of cycle
        elapsed = time.time() - cycle_start
        sleep_time = max(0, CYCLE_INTERVAL - elapsed)
        log.info(f"⏱️ Next cycle in {sleep_time:.0f}s...")
        time.sleep(sleep_time)


if __name__ == '__main__':
    run_bot()

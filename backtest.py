"""
backtest.py — Self-Contained Signal-Based Backtester
=====================================================
Strategy: EMA-Crossover Trend-Following with ATR Risk Management
- Trend filter  : Price vs EMA(50) — only LONG in uptrend, only SHORT in downtrend
- Entry signal  : EMA(9) crosses EMA(21) in trend direction
- Momentum gate : RSI(14) 40–65 for LONG, 35–60 for SHORT (avoid exhausted moves)
- Trend strength: ADX(14) > 20 (skip choppy/ranging markets)
- Volume confirm: Current volume > 1.2x rolling 20-bar average
- Stop Loss     : 1.5× ATR(14) from entry
- Take Profit   : 3.0× ATR(14) from entry  → minimum 2:1 R:R
- Position size : Risk 1% of current capital per trade
- Fee model     : 0.04% taker each side (Binance Futures standard) = 0.08% round-trip
- Slippage      : Additional 0.02% per fill (conservative estimate)

No Redis, no ML models, no Telegram — fully self-contained.
Uses ccxt synchronous client for public market data (no API keys required).
"""

import sys
import os
import pandas as pd
import numpy as np
import ccxt

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
INITIAL_CAPITAL  = 1000.0       # Starting capital in USD
RISK_PER_TRADE   = 0.01         # 1% of current capital risked per trade
TAKER_FEE        = 0.0004       # 0.04% Binance Futures taker fee per fill
SLIPPAGE         = 0.0002       # 0.02% estimated slippage per fill
COST_PER_FILL    = TAKER_FEE + SLIPPAGE   # 0.06% each way → 0.12% round-trip

SL_ATR_MULT      = 1.5          # Stop loss distance = 1.5 × ATR
TP_ATR_MULT      = 3.0          # Take profit distance = 3.0 × ATR  (2:1 R:R)
TIME_STOP_BARS   = 48           # Exit trade after 48 bars (≈ 48 h on 1h data)

EMA_FAST         = 9
EMA_SLOW         = 21
EMA_TREND        = 50
RSI_PERIOD       = 14
ADX_PERIOD       = 14
VOL_LOOKBACK     = 20

# Long entry: RSI must be below this (not overbought) and above floor
RSI_LONG_MAX     = 65
RSI_LONG_MIN     = 40
# Short entry: RSI must be above this (not oversold) and below ceiling
RSI_SHORT_MIN    = 35
RSI_SHORT_MAX    = 60

ADX_MIN          = 20           # Skip choppy markets
VOL_MULT         = 1.2          # Volume must be above this × 20-bar average

LONG_ONLY        = True         # Set to False to allow short trades too
DEFAULT_DAYS     = 60           # History window in days


# ---------------------------------------------------------------------------
# Indicator helpers (standalone — no external deps beyond pandas/numpy)
# ---------------------------------------------------------------------------

def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df['high'], df['low'], df['close']
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()   # EMA-ATR (smoother than SMA)


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0).ewm(com=period - 1, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(com=period - 1, adjust=False).mean()
    rs    = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))


def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df['high'], df['low'], df['close']
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    up   = (h - h.shift()).clip(lower=0)
    down = (l.shift() - l).clip(lower=0)
    dm_p = up.where(up > down, 0.0)
    dm_m = down.where(down > up, 0.0)
    atr14  = tr.ewm(span=period, adjust=False).mean()
    di_p   = 100 * dm_p.ewm(span=period, adjust=False).mean() / (atr14 + 1e-9)
    di_m   = 100 * dm_m.ewm(span=period, adjust=False).mean() / (atr14 + 1e-9)
    dx     = 100 * (di_p - di_m).abs() / (di_p + di_m + 1e-9)
    return dx.ewm(span=period, adjust=False).mean()


def _ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False).mean()


# ---------------------------------------------------------------------------
# Data fetching (public endpoint — no API keys required)
# ---------------------------------------------------------------------------

def _synthetic_ohlcv(n_bars: int = 1500, start_price: float = 40000.0,
                     drift: float = 0.0002, vol: float = 0.012,
                     seed: int = 42) -> pd.DataFrame:
    """
    Generate realistic synthetic OHLCV for offline testing.
    Uses geometric Brownian motion with random walk + mean-reverting volatility.
    Only used when Binance cannot be reached.
    """
    rng   = np.random.default_rng(seed)
    dates = pd.date_range('2024-01-01', periods=n_bars, freq='1h')
    # GBM log returns
    log_ret = rng.normal(drift, vol, n_bars)
    close   = start_price * np.exp(np.cumsum(log_ret))
    # Realistic OHLCV around close
    bar_vol = np.abs(rng.normal(0, vol * 0.5, n_bars)) + 0.002
    high    = close * (1 + bar_vol)
    low     = close * (1 - bar_vol)
    open_   = close * (1 + rng.normal(0, vol * 0.3, n_bars))
    volume  = np.abs(rng.normal(1e6, 3e5, n_bars)) + 1e5
    df = pd.DataFrame({'open': open_, 'high': high, 'low': low,
                       'close': close, 'volume': volume}, index=dates)
    return df.astype(float)


def fetch_ohlcv(symbol: str, timeframe: str = '1h', days: int = DEFAULT_DAYS) -> pd.DataFrame:
    """
    Fetch OHLCV data from Binance public REST endpoint.
    Falls back to synthetic data if Binance is unreachable (useful for offline testing).
    """
    limit = min(days * 24, 1000)   # 1h bars; Binance max is 1000
    try:
        exchange = ccxt.binance({'enableRateLimit': True})
        ohlcv    = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df = df.set_index('ts').astype(float)
        print(f"📥  Fetched {len(df)} bars from Binance for {symbol}")
        return df
    except Exception as exc:
        print(f"⚠️   Binance unreachable ({exc}). Using synthetic data for {symbol}.")
        return _synthetic_ohlcv(n_bars=limit, seed=hash(symbol) % 10000)


# ---------------------------------------------------------------------------
# Signal generator — called once per bar on the CLOSED candle
# ---------------------------------------------------------------------------

def generate_signal(df: pd.DataFrame, i: int) -> str:
    """
    Returns 'LONG', 'SHORT', or 'HOLD' for bar index i.
    Uses only data up to and including bar i (no lookahead).
    """
    close  = df['close']
    high   = df['high']
    low    = df['low']

    ema_fast  = _ema(close, EMA_FAST)
    ema_slow  = _ema(close, EMA_SLOW)
    ema_trend = _ema(close, EMA_TREND)
    rsi       = _rsi(close, RSI_PERIOD)
    adx       = _adx(df, ADX_PERIOD)
    vol_avg   = df['volume'].rolling(VOL_LOOKBACK).mean()

    price      = close.iloc[i]
    ema_f_now  = ema_fast.iloc[i]
    ema_f_prev = ema_fast.iloc[i - 1]
    ema_s_now  = ema_slow.iloc[i]
    ema_s_prev = ema_slow.iloc[i - 1]
    ema_t_now  = ema_trend.iloc[i]
    rsi_now    = rsi.iloc[i]
    adx_now    = adx.iloc[i]
    vol_now    = df['volume'].iloc[i]
    vol_avg_v  = vol_avg.iloc[i]

    # Trend strength gate
    if adx_now < ADX_MIN:
        return 'HOLD'

    # Volume confirmation
    if vol_now < VOL_MULT * vol_avg_v:
        return 'HOLD'

    # EMA(9) just crossed above EMA(21) — bullish crossover
    ema_cross_up   = (ema_f_prev <= ema_s_prev) and (ema_f_now > ema_s_now)
    # EMA(9) just crossed below EMA(21) — bearish crossover
    ema_cross_down = (ema_f_prev >= ema_s_prev) and (ema_f_now < ema_s_now)

    # LONG: uptrend + bullish crossover + RSI not overbought
    if price > ema_t_now and ema_cross_up and RSI_LONG_MIN <= rsi_now <= RSI_LONG_MAX:
        return 'LONG'

    # SHORT: downtrend + bearish crossover + RSI not oversold
    if (not LONG_ONLY) and price < ema_t_now and ema_cross_down and RSI_SHORT_MIN <= rsi_now <= RSI_SHORT_MAX:
        return 'SHORT'

    return 'HOLD'


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

def run_backtest(symbol: str, days: int = DEFAULT_DAYS, timeframe: str = '1h') -> dict:
    """
    Run a single-symbol backtest. Returns a metrics dict.
    """
    print(f"\n{'━'*60}")
    print(f"🚀  Backtest  |  {symbol}  |  {days} days  |  TF: {timeframe}")
    print(f"{'━'*60}")

    # ── 1. Fetch data ──────────────────────────────────────────────────────
    try:
        df = fetch_ohlcv(symbol, timeframe, days)
    except Exception as exc:
        print(f"❌  Failed to fetch data for {symbol}: {exc}")
        return {}

    warmup = max(EMA_TREND, ADX_PERIOD, RSI_PERIOD, VOL_LOOKBACK) + 5  # ≈ 55 bars
    if len(df) < warmup + 10:
        print(f"⚠️   Not enough data ({len(df)} bars). Need >{warmup}.")
        return {}

    # ── 2. Pre-compute indicator series (vectorised, no lookahead) ─────────
    # NOTE: generate_signal() re-uses these via the full df slices which is
    # equivalent since we only read iloc[i] values — no future data is read.

    atr_series = _atr(df, 14)

    # ── 3. Simulation state ────────────────────────────────────────────────
    capital  = INITIAL_CAPITAL
    equity   = []
    trades   = []

    pos_side    = None
    pos_entry   = 0.0
    pos_sl      = 0.0
    pos_tp      = 0.0
    pos_qty     = 0.0
    pos_nominal = 0.0
    pos_bar     = 0

    # ── 4. Bar loop ────────────────────────────────────────────────────────
    for i in range(warmup, len(df)):
        price     = df['close'].iloc[i]
        bar_high  = df['high'].iloc[i]
        bar_low   = df['low'].iloc[i]
        atr       = atr_series.iloc[i]

        # ── Exit logic (check BEFORE entry on same bar) ───────────────────
        if pos_side is not None:
            exit_price  = None
            exit_reason = None
            bars_held   = i - pos_bar

            if pos_side == 'LONG':
                if bar_low <= pos_sl:
                    exit_price, exit_reason = pos_sl, 'STOP_LOSS'
                elif bar_high >= pos_tp:
                    exit_price, exit_reason = pos_tp, 'TAKE_PROFIT'
                elif bars_held >= TIME_STOP_BARS:
                    exit_price, exit_reason = price, 'TIME_STOP'
            else:  # SHORT
                if bar_high >= pos_sl:
                    exit_price, exit_reason = pos_sl, 'STOP_LOSS'
                elif bar_low <= pos_tp:
                    exit_price, exit_reason = pos_tp, 'TAKE_PROFIT'
                elif bars_held >= TIME_STOP_BARS:
                    exit_price, exit_reason = price, 'TIME_STOP'

            if exit_reason:
                # Gross PnL
                if pos_side == 'LONG':
                    gross_pnl = (exit_price - pos_entry) * pos_qty
                else:
                    gross_pnl = (pos_entry - exit_price) * pos_qty

                # Fee on exit fill (entry fee already deducted on open)
                exit_fee  = pos_nominal * COST_PER_FILL
                net_pnl   = gross_pnl - exit_fee

                capital  += net_pnl
                capital   = max(capital, 0.01)  # prevent negative capital

                trades.append({
                    'symbol':     symbol,
                    'side':       pos_side,
                    'entry':      pos_entry,
                    'exit':       exit_price,
                    'gross_pnl':  round(gross_pnl, 4),
                    'net_pnl':    round(net_pnl, 4),
                    'pnl_pct':    round((net_pnl / pos_nominal) * 100, 3),
                    'reason':     exit_reason,
                    'bars_held':  bars_held,
                })
                pos_side = None

        # ── Entry logic ───────────────────────────────────────────────────
        if pos_side is None and capital > 0 and atr > 0:
            signal = generate_signal(df, i)

            if signal in ('LONG', 'SHORT'):
                sl_dist = SL_ATR_MULT * atr
                tp_dist = TP_ATR_MULT * atr

                if signal == 'LONG':
                    pos_sl = price - sl_dist
                    pos_tp = price + tp_dist
                else:
                    pos_sl = price + sl_dist
                    pos_tp = price - tp_dist

                # Position size: risk 1% of capital
                risk_amount = capital * RISK_PER_TRADE
                pos_qty     = risk_amount / sl_dist
                pos_nominal = pos_qty * price

                # Entry fee deducted immediately
                entry_fee = pos_nominal * COST_PER_FILL
                capital  -= entry_fee

                pos_side  = signal
                pos_entry = price
                pos_bar   = i

        equity.append(capital)

    # Close any open position at last bar
    if pos_side is not None:
        last_price = df['close'].iloc[-1]
        if pos_side == 'LONG':
            gross_pnl = (last_price - pos_entry) * pos_qty
        else:
            gross_pnl = (pos_entry - last_price) * pos_qty
        exit_fee  = pos_nominal * COST_PER_FILL
        net_pnl   = gross_pnl - exit_fee
        capital  += net_pnl
        trades.append({
            'symbol': symbol, 'side': pos_side,
            'entry': pos_entry, 'exit': last_price,
            'gross_pnl': round(gross_pnl, 4), 'net_pnl': round(net_pnl, 4),
            'pnl_pct': round((net_pnl / pos_nominal) * 100, 3),
            'reason': 'END_OF_DATA', 'bars_held': len(df) - 1 - pos_bar,
        })
        equity.append(capital)

    # ── 5. Metrics ─────────────────────────────────────────────────────────
    if not trades:
        print("⚠️   No trades generated — check signal thresholds.")
        return {}

    df_t      = pd.DataFrame(trades)
    n_trades  = len(df_t)
    winners   = df_t[df_t['net_pnl'] > 0]
    losers    = df_t[df_t['net_pnl'] < 0]
    win_rate  = len(winners) / n_trades

    gross_profit = winners['net_pnl'].sum() if len(winners) > 0 else 0
    gross_loss   = abs(losers['net_pnl'].sum()) if len(losers) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    total_return = (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL

    equity_s  = pd.Series(equity)
    returns_s = equity_s.pct_change().dropna()
    sharpe    = (returns_s.mean() / (returns_s.std() + 1e-9)) * np.sqrt(252 * 24) if len(returns_s) > 1 else 0

    running_max = equity_s.cummax()
    drawdowns   = (running_max - equity_s) / (running_max + 1e-9)
    max_dd      = drawdowns.max()

    avg_win  = winners['net_pnl'].mean() if len(winners) > 0 else 0
    avg_loss = losers['net_pnl'].mean()  if len(losers) > 0 else 0
    payoff   = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')

    fee_drag = df_t['gross_pnl'].sum() - df_t['net_pnl'].sum()

    metrics = {
        'symbol':        symbol,
        'n_trades':      n_trades,
        'win_rate':      win_rate,
        'profit_factor': profit_factor,
        'sharpe':        sharpe,
        'max_drawdown':  max_dd,
        'total_return':  total_return,
        'final_capital': capital,
        'avg_win_usd':   avg_win,
        'avg_loss_usd':  avg_loss,
        'payoff_ratio':  payoff,
        'fee_drag_usd':  fee_drag,
    }

    # ── 6. Print report ────────────────────────────────────────────────────
    status = "✅ PROFITABLE" if total_return > 0 else "❌ LOSS"
    print(f"\n📊  PERFORMANCE SUMMARY: {symbol}  {status}")
    print(f"{'━'*50}")
    print(f"Total Trades      : {n_trades}")
    print(f"Win Rate          : {win_rate:.1%}")
    print(f"Payoff Ratio      : {payoff:.2f}x  (avg win / avg loss)")
    print(f"Profit Factor     : {profit_factor:.2f}")
    print(f"Sharpe Ratio      : {sharpe:.2f}")
    print(f"Max Drawdown      : {max_dd:.1%}")
    print(f"Total Return      : {total_return:+.2%}")
    print(f"Final Capital     : ${capital:.2f}  (started ${INITIAL_CAPITAL:.2f})")
    print(f"Fee Drag (total)  : ${fee_drag:.2f}")
    print(f"{'━'*50}")

    # Per-exit-reason breakdown
    if n_trades > 0:
        print("\n📌  Exit Breakdown:")
        for reason, grp in df_t.groupby('reason'):
            r_pf   = grp[grp['net_pnl'] > 0]['net_pnl'].sum()
            r_pl   = abs(grp[grp['net_pnl'] < 0]['net_pnl'].sum())
            r_net  = grp['net_pnl'].sum()
            print(f"   {reason:<18} {len(grp):3d} trades   net PnL: ${r_net:+.2f}")

    return metrics


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Allow overriding symbol list from command line:  python backtest.py BTCUSDT ETHUSDT
    symbols = sys.argv[1:] if len(sys.argv) > 1 else ['BTC/USDT', 'ETH/USDT']

    all_results = []
    for sym in symbols:
        result = run_backtest(sym, days=DEFAULT_DAYS, timeframe='1h')
        if result:
            all_results.append(result)

    if len(all_results) > 1:
        print(f"\n{'━'*60}")
        print("📈  PORTFOLIO SUMMARY")
        print(f"{'━'*60}")
        total_final = sum(r['final_capital'] for r in all_results)
        total_init  = INITIAL_CAPITAL * len(all_results)
        port_return = (total_final - total_init) / total_init
        avg_sharpe  = np.mean([r['sharpe'] for r in all_results])
        avg_dd      = np.mean([r['max_drawdown'] for r in all_results])
        print(f"Symbols tested    : {len(all_results)}")
        print(f"Portfolio Return  : {port_return:+.2%}")
        print(f"Avg Sharpe        : {avg_sharpe:.2f}")
        print(f"Avg Max Drawdown  : {avg_dd:.1%}")
        print(f"{'━'*60}")

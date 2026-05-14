"""
backtest_may2026.py
"Phase 9" — Live-Simulation Backtest Runner
Supports CLI arguments for custom data, date ranges, and output files.
"""

import pandas as pd
import numpy as np
import logging
import asyncio
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta
from collections import defaultdict

sys.path.append(os.getcwd())

from core.strategies.ensemble_algorithm import EnsembleAlgorithm
from core.risk import RiskManager

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("backtest.log", mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger("SovereignBacktest")

# ─── Constants ────────────────────────────────────────────────────────────────
DATA_DIR        = "backtest_data_may2026"
START_DATE      = "2026-04-13"
END_DATE        = "2026-05-13"
INITIAL_CAPITAL       = 10_000.0
COMMISSION_PCT        = 0.0004   # 0.04% per side
SLIPPAGE_PCT          = 0.0005   # 0.05% per side
ROUND_TRIP_COST       = (COMMISSION_PCT + SLIPPAGE_PCT) * 2
MAX_CONCURRENT        = 3        # Phase 9.5: Balanced Risk
TRAILING_ACTIVATION   = 0.03     # Phase 9.5: 3% activates trail
DAILY_DD_LIMIT        = 0.03     # PHASE 9: 3% daily halt
WEEKLY_DD_LIMIT       = 0.08     # PHASE 9: 8% weekly halt

SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT',
    'ADA/USDT', 'DOGE/USDT', 'SHIB/USDT', 'POL/USDT',
    'AVAX/USDT', 'LINK/USDT'
]

def parse_args():
    parser = argparse.ArgumentParser(description='Phase 9 Backtest Runner')
    parser.add_argument('--data', default=DATA_DIR, help='Data directory')
    parser.add_argument('--output', default='backtest_results_may2026.md', help='Output MD report file')
    parser.add_argument('--start', default=START_DATE, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', default=END_DATE, help='End date (YYYY-MM-DD)')
    return parser.parse_args()


# ─── Point-in-time State Manager ─────────────────────────────────────────────
class LiveStateManager:
    """Mimics production StateManager with strict no-lookahead guarantees."""

    def __init__(self, symbol_data: dict):
        self.symbol_data = symbol_data
        self.current_ts  = 0  # set each bar by the runner

        # Stubs for Firebase / Redis
        self.firebase = type("FB", (), {
            "set": lambda s, k, v: None,
            "get": lambda s, k:    None
        })()
        self.redis = type("RD", (), {
            "lrange": lambda s, *a: []
        })()

    async def get_df(self, key: str, n: int = 200) -> pd.DataFrame | None:
        """Return at most n bars whose timestamp <= current_ts."""
        parts    = key.split(":")        # ohlcv:1h:BTC/USDT
        interval = parts[1]
        symbol   = parts[2]

        df_full = self.symbol_data.get(symbol, {}).get(interval)
        if df_full is None:
            return None

        mask = df_full["timestamp"] <= self.current_ts
        sliced = df_full[mask].tail(n).copy()
        return sliced if len(sliced) > 0 else None

    async def get(self, key: str):
        if "ml_signal" in key:
            return {"signal": "NEUTRAL", "confidence": 0.5}
        return None

    async def set(self, key, value):   pass
    async def publish(self, key, value): pass


# ─── Main Backtest Runner ─────────────────────────────────────────────────────
class SovereignBacktestRunner:

    def __init__(self, data_dir=DATA_DIR, start_date=START_DATE, end_date=END_DATE, output_file='backtest_results_may2026.md'):
        self.data_dir = data_dir
        self.start_date = start_date
        self.end_date = end_date
        self.output_file = output_file
        self.capital         = INITIAL_CAPITAL
        self.initial_capital = INITIAL_CAPITAL
        self.trades          = []
        self.equity_curve    = []     # [(datetime, equity)]
        self.symbol_dfs      = {}

        # Phase 9 circuit-breaker tracking
        self.daily_equity   = {}     # date -> open equity
        self.weekly_equity  = {}     # iso-week -> open equity
        self._cb_fired_day  = set()  # dates where CB already logged (no spam)
        self._weekly_halted = set()  # iso-weeks where weekly CB fired

        # Load data
        self._load_data()

    def _load_data(self):
        log.info(f"📂 Loading data from '{self.data_dir}'…")
        for sym in SYMBOLS:
            tag = sym.replace("/", "_")
            self.symbol_dfs[sym] = {}
            for tf in ["1d", "1h", "1m"]:
                path = os.path.join(self.data_dir, f"{tag}_{tf}.csv")
                if os.path.exists(path):
                    df = pd.read_csv(path)
                    df["timestamp"] = df["timestamp"].astype(np.int64)
                    df.sort_values("timestamp", inplace=True)
                    df.reset_index(drop=True, inplace=True)
                    self.symbol_dfs[sym][tf] = df
                    log.info(f"  ✓ {sym} {tf}: {len(df)} bars")
                else:
                    log.warning(f"  ✗ Missing: {path}")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _price_at(self, symbol: str, ts: int) -> float | None:
        """Get close price for a symbol at the given 1h timestamp."""
        df = self.symbol_dfs.get(symbol, {}).get("1h")
        if df is None:
            return None
        row = df[df["timestamp"] == ts]
        if row.empty:
            return None
        return float(row["close"].values[0])

    def _daily_drawdown_ok(self, date_str: str) -> bool:
        """Phase 9: halt if today's loss >= 3% of day-open equity."""
        if date_str not in self.daily_equity:
            return True
        day_start = self.daily_equity[date_str]
        if day_start <= 0:
            return True
        dd = (day_start - self.capital) / day_start
        if dd >= DAILY_DD_LIMIT:
            if date_str not in self._cb_fired_day:   # log only once per day
                log.critical(
                    f"DAILY CIRCUIT BREAKER: {date_str} drawdown={dd:.2%} "
                    f">= {DAILY_DD_LIMIT:.0%}. No new entries today."
                )
                self._cb_fired_day.add(date_str)
            return False
        return True

    def _weekly_drawdown_ok(self, dt) -> bool:
        """Phase 9: halt if this week's loss >= 8% of Monday open equity."""
        iso_week = dt.strftime("%G-W%V")   # e.g. '2026-W17'
        if iso_week in self._weekly_halted:
            return False
        if iso_week not in self.weekly_equity:
            return True
        week_start = self.weekly_equity[iso_week]
        if week_start <= 0:
            return True
        dd = (week_start - self.capital) / week_start
        if dd >= WEEKLY_DD_LIMIT:
            log.critical(
                f"WEEKLY CIRCUIT BREAKER: {iso_week} drawdown={dd:.2%} "
                f">= {WEEKLY_DD_LIMIT:.0%}. No new entries until next Monday 00:00 UTC."
            )
            self._weekly_halted.add(iso_week)
            return False
        return True

    # ── Trailing stop update ─────────────────────────────────────────────────

    def _update_trailing_stop(self, pos: dict, current_price: float) -> dict:
        """Tighten trailing stop once profit ≥ TRAILING_ACTIVATION."""
        entry = pos["entry"]
        side  = pos["side"]

        unrealised = (current_price - entry) / entry if side == "LONG" \
                     else (entry - current_price) / entry

        if unrealised >= TRAILING_ACTIVATION:
            atr     = pos.get("atr", entry * 0.01)
            trail   = atr * 0.8  # Phase 9.5: Aggressive trail to protect 3:1 RR
            if side == "LONG":
                new_sl = current_price - trail
                pos["sl"] = max(pos["sl"], new_sl)   # only ratchet up
            else:
                new_sl = current_price + trail
                pos["sl"] = min(pos["sl"], new_sl)   # only ratchet down
        return pos

    # ── Main Loop ────────────────────────────────────────────────────────────

    async def run(self):
        log.info("=" * 65)
        log.info(f"🚀 SOVEREIGN BACKTEST {self.start_date} to {self.end_date}")
        log.info(f"   Capital: ${self.initial_capital:,.2f}  |  Symbols: {len(SYMBOLS)}")
        log.info("=" * 65)

        # Master clock = BTC/USDT 1h (guaranteed to exist)
        if "BTC/USDT" not in self.symbol_dfs or "1h" not in self.symbol_dfs["BTC/USDT"]:
            log.error("Master clock BTC/USDT 1h missing.")
            return
            
        clock_df = self.symbol_dfs["BTC/USDT"]["1h"]

        start_ts = int(pd.Timestamp(self.start_date, tz="UTC").timestamp() * 1000)
        end_ts   = int(pd.Timestamp(self.end_date,   tz="UTC").timestamp() * 1000) \
                   + 23 * 3600 * 1000  # include last day fully

        sim_bars = clock_df[
            (clock_df["timestamp"] >= start_ts) &
            (clock_df["timestamp"] <= end_ts)
        ]
        log.info(f"📊 Simulation bars: {len(sim_bars)} (1h candles)")

        state    = LiveStateManager(self.symbol_dfs)
        algo     = EnsembleAlgorithm(state)
        risk_mgr = RiskManager(None)

        active_positions: dict[str, dict] = {}

        for _, bar in sim_bars.iterrows():
            ts       = int(bar["timestamp"])
            dt       = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            dt_str   = dt.strftime("%Y-%m-%d %H:%M")
            date_str = dt.strftime("%Y-%m-%d")

            # Record day-open equity
            if date_str not in self.daily_equity:
                self.daily_equity[date_str] = self.capital

            # Record week-open equity (Monday 00:00 UTC resets the week)
            iso_week = dt.strftime("%G-W%V")
            if iso_week not in self.weekly_equity:
                self.weekly_equity[iso_week] = self.capital

            state.current_ts = ts

            for symbol in SYMBOLS:
                # ── 1. Generate Signal ───────────────────────────────────
                try:
                    signal = await algo.generate_signal(symbol)
                except Exception as e:
                    log.error(f"Signal error {symbol}: {e}")
                    signal = {"action": "HOLD", "confidence": 0, "regime": "ERROR"}

                # ── 2. Update Trailing Stops & Check Exits ───────────────
                if symbol in active_positions:
                    pos           = active_positions[symbol]
                    current_price = self._price_at(symbol, ts)

                    if current_price is None:
                        continue

                    # Update trailing stop
                    pos = self._update_trailing_stop(pos, current_price)
                    active_positions[symbol] = pos

                    is_exit     = False
                    exit_reason = ""

                    if pos["side"] == "LONG":
                        if current_price <= pos["sl"]:
                            is_exit = True; exit_reason = "STOP_LOSS"
                        elif current_price >= pos["tp"]:
                            is_exit = True; exit_reason = "TAKE_PROFIT"
                        elif signal["action"] == "SELL" and signal["confidence"] > 0.70:
                            is_exit = True; exit_reason = "REVERSAL"
                    else:  # SHORT
                        if current_price >= pos["sl"]:
                            is_exit = True; exit_reason = "STOP_LOSS"
                        elif current_price <= pos["tp"]:
                            is_exit = True; exit_reason = "TAKE_PROFIT"
                        elif signal["action"] == "BUY" and signal["confidence"] > 0.70:
                            is_exit = True; exit_reason = "REVERSAL"

                    if is_exit:
                        raw_pnl  = (current_price - pos["entry"]) / pos["entry"] \
                                   if pos["side"] == "LONG" \
                                   else (pos["entry"] - current_price) / pos["entry"]
                        net_pnl  = raw_pnl - ROUND_TRIP_COST
                        pnl_amt  = pos["notional"] * net_pnl
                        self.capital += pnl_amt

                        self.trades.append({
                            "time_exit":   dt_str,
                            "time_entry":  pos["entry_time"],
                            "symbol":      symbol,
                            "side":        pos["side"],
                            "entry":       pos["entry"],
                            "exit":        current_price,
                            "notional":    pos["notional"],
                            "pnl_amt":     pnl_amt,
                            "pnl_pct":     net_pnl * 100,
                            "reason":      exit_reason,
                            "regime":      pos.get("regime", "?"),
                            "capital_after": self.capital
                        })
                        del active_positions[symbol]

                        emoji = "✅" if pnl_amt > 0 else "❌"
                        log.info(
                            f"{emoji} EXIT  {symbol:12s} | {exit_reason:12s} | "
                            f"{pos['side']:5s} | PnL: ${pnl_amt:+.2f} ({net_pnl*100:+.2f}%) | "
                            f"Bal: ${self.capital:,.2f}"
                        )

                # ── 3. Circuit Breakers (daily 3% + weekly 8%) ──────────
                cb_triggered = False
                if not self._daily_drawdown_ok(date_str):
                    cb_triggered = True
                elif not self._weekly_drawdown_ok(dt):
                    cb_triggered = True

                if cb_triggered:
                    # Phase 9.1: Hardened - Force close all positions on CB hit
                    if active_positions:
                        log.warning(f"🛡️ CIRCUIT BREAKER triggered. Force-closing {len(active_positions)} positions.")
                        for sym in list(active_positions.keys()):
                            pos = active_positions[sym]
                            cp = self._price_at(sym, ts)
                            if cp is None: continue
                            raw_pnl = (cp - pos["entry"]) / pos["entry"] if pos["side"] == "LONG" else (pos["entry"] - cp) / pos["entry"]
                            net_pnl = raw_pnl - ROUND_TRIP_COST
                            pnl_amt = pos["notional"] * net_pnl
                            self.capital += pnl_amt
                            self.trades.append({
                                "time_exit":   dt_str,
                                "time_entry":  pos["entry_time"],
                                "symbol":      sym,
                                "side":        pos["side"],
                                "entry":       pos["entry"],
                                "exit":        cp,
                                "notional":    pos["notional"],
                                "pnl_amt":     pnl_amt,
                                "pnl_pct":     net_pnl * 100,
                                "reason":      "CB_FORCE_CLOSE",
                                "regime":      pos.get("regime", "?"),
                                "capital_after": self.capital
                            })
                            del active_positions[sym]
                            log.info(f"🛡️ CB CLOSED {sym} | PnL: ${pnl_amt:+.2f}")
                    continue

                # ── 4. Entry Logic ───────────────────────────────────────
                if (
                    signal["action"] in ("BUY", "SELL")
                    and symbol not in active_positions
                    and len(active_positions) < MAX_CONCURRENT
                ):
                    price_row = self.symbol_dfs[symbol]["1h"]
                    price_row = price_row[price_row["timestamp"] == ts]
                    if price_row.empty:
                        continue
                    entry_price = float(price_row["close"].values[0])

                    # Regime-aware size
                    size_info = await risk_mgr.compute_position_size(
                        capital  = self.capital,
                        strategy = "ENSEMBLE",
                        atr      = signal.get("atr", entry_price * 0.01),
                        price    = entry_price,
                        regime   = signal.get("regime", "NEUTRAL"),
                    )

                    if size_info["qty"] <= 0:
                        continue

                    # Adaptive stops
                    stops = risk_mgr.calculate_adaptive_stops(
                        entry_price,
                        signal.get("atr", entry_price * 0.01),
                        signal.get("regime", "NEUTRAL"),
                        "LONG" if signal["action"] == "BUY" else "SHORT",
                    )

                    risk   = abs(entry_price - stops["stop"])
                    reward = abs(stops["tp"]  - entry_price)

                    rr_ratio = (reward / risk) if risk > 0 else 0.0
                    if risk <= 0 or rr_ratio < 2.0:
                        log.debug(
                            f"[{dt_str}] {symbol} Gated - RR={rr_ratio:.2f}"
                        )
                        continue

                    active_positions[symbol] = {
                        "side":       "LONG" if signal["action"] == "BUY" else "SHORT",
                        "entry":      entry_price,
                        "sl":         stops["stop"],
                        "tp":         stops["tp"],
                        "notional":   size_info["notional"],
                        "qty":        size_info["qty"],
                        "atr":        signal.get("atr", entry_price * 0.01),
                        "entry_time": dt_str,
                        "regime":     signal.get("regime", "?"),
                    }
                    log.info(
                        f"🚀 ENTRY {symbol:12s} | {active_positions[symbol]['side']:5s} | "
                        f"@ {entry_price:.4f} | Size: ${size_info['notional']:.2f} | "
                        f"Regime: {signal.get('regime')}"
                    )

            # Equity snapshot at the close of each BTC bar
            self.equity_curve.append((dt_str, self.capital))

        # Force-close any remaining positions at last price
        log.info(f"\n📌 Force-closing {len(active_positions)} open positions at end of period…")
        if not sim_bars.empty:
            last_ts = int(sim_bars["timestamp"].iloc[-1])
            last_dt = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

            for symbol, pos in list(active_positions.items()):
                cp = self._price_at(symbol, last_ts)
                if cp is None:
                    continue
                raw_pnl = (cp - pos["entry"]) / pos["entry"] if pos["side"] == "LONG" \
                          else (pos["entry"] - cp) / pos["entry"]
                net_pnl = raw_pnl - ROUND_TRIP_COST
                pnl_amt = pos["notional"] * net_pnl
                self.capital += pnl_amt
                self.trades.append({
                    "time_exit":     last_dt,
                    "time_entry":    pos["entry_time"],
                    "symbol":        symbol,
                    "side":          pos["side"],
                    "entry":         pos["entry"],
                    "exit":          cp,
                    "notional":      pos["notional"],
                    "pnl_amt":       pnl_amt,
                    "pnl_pct":       net_pnl * 100,
                    "reason":        "PERIOD_END",
                    "regime":        pos.get("regime", "?"),
                    "capital_after": self.capital,
                })
                log.info(f"📌 CLOSED {symbol} at period end | PnL: ${pnl_amt:+.2f}")

        self._generate_report()

    # ── Report Generator ─────────────────────────────────────────────────────

    def _generate_report(self):
        log.info("\n" + "=" * 65)
        log.info("📊 Generating Sovereign Backtest Report…")

        df_trades = pd.DataFrame(self.trades) if self.trades else pd.DataFrame()

        total_trades = len(df_trades)
        total_pnl    = df_trades["pnl_amt"].sum() if total_trades > 0 else 0
        wins         = df_trades[df_trades["pnl_amt"] > 0] if total_trades > 0 else pd.DataFrame()
        losses       = df_trades[df_trades["pnl_amt"] < 0] if total_trades > 0 else pd.DataFrame()
        win_rate     = len(wins) / total_trades if total_trades > 0 else 0

        avg_win   = wins["pnl_amt"].mean()   if len(wins)   > 0 else 0
        avg_loss  = losses["pnl_amt"].mean() if len(losses) > 0 else 0
        profit_factor = (wins["pnl_amt"].sum() / abs(losses["pnl_amt"].sum())
                         if len(losses) > 0 and losses["pnl_amt"].sum() != 0 else float("inf"))

        roi = total_pnl / self.initial_capital * 100

        # Max drawdown from equity curve
        eq_vals   = [e for _, e in self.equity_curve]
        if not eq_vals: eq_vals = [self.initial_capital]
        running_max = np.maximum.accumulate(eq_vals)
        dd_series   = (running_max - eq_vals) / running_max
        max_dd      = dd_series.max() * 100 if len(dd_series) > 0 else 0

        # Sharpe (annualised, hourly returns)
        if len(eq_vals) > 2:
            eq_arr = np.array(eq_vals, dtype=float)
            hr_ret = np.diff(eq_arr) / eq_arr[:-1]
            sharpe = (hr_ret.mean() / (hr_ret.std() + 1e-9)) * np.sqrt(8760)
        else:
            sharpe = 0.0

        # Per-symbol breakdown
        by_sym = defaultdict(lambda: {"trades": 0, "pnl": 0.0, "wins": 0})
        for t in self.trades:
            s = t["symbol"]
            by_sym[s]["trades"] += 1
            by_sym[s]["pnl"]    += t["pnl_amt"]
            if t["pnl_amt"] > 0:
                by_sym[s]["wins"] += 1

        # ── Markdown Report ──────────────────────────────────────────────────
        exit_reasons = (df_trades["reason"].value_counts().to_dict()
                        if total_trades > 0 else {})

        md = f"""# Phase 9 Backtest -- {self.start_date} to {self.end_date}
*3-state regime | MOMENTUM_TREND + RSI_MEAN_REVERSION | Fixed 1% risk | No ML | No Kelly*

---

## Performance Summary

| Metric | Value |
|---|---|
| **Period** | {self.start_date} - {self.end_date} |
| **Engine** | Phase 9 (EMA200 regime + 2-strategy ensemble) |
| **Initial Capital** | ${self.initial_capital:,.2f} |
| **Final Capital** | ${self.capital:,.2f} |
| **Net Profit** | **${total_pnl:+,.2f} ({roi:+.2f}%)** |
| **Max Drawdown** | {max_dd:.2f}% |
| **Sharpe Ratio** | {sharpe:.2f} |
| **Profit Factor** | {profit_factor:.2f} |
| **Win Rate** | {win_rate:.1%} ({len(wins)}W / {len(losses)}L) |
| **Total Trades** | {total_trades} |
| **Avg Win** | ${avg_win:+.2f} |
| **Avg Loss** | ${avg_loss:+.2f} |

## Cost Model (Realistic)
- Commission: **0.04% per side** (Binance Futures maker)
- Slippage:   **0.05% per side** (market-order fill gap)
- **Round-trip cost: {ROUND_TRIP_COST*100:.2f}% per trade**
- **Daily circuit breaker**: 3% (Phase 9)
- **Weekly circuit breaker**: 8% (Phase 9)

## Exit Reasons
"""
        for reason, count in exit_reasons.items():
            md += f"- {reason}: **{count}**\n"

        md += "\n## Per-Symbol Breakdown\n\n"
        md += "| Symbol | Trades | PnL ($) | Win Rate |\n|---|---|---|---|\n"
        for sym, d in sorted(by_sym.items(), key=lambda x: -x[1]["pnl"]):
            wr = d["wins"] / d["trades"] if d["trades"] > 0 else 0
            md += f"| {sym} | {d['trades']} | ${d['pnl']:+.2f} | {wr:.0%} |\n"

        if total_trades > 0:
            md += "\n## Full Trade Log\n\n"
            md += "| # | Entry | Exit | Symbol | Side | Notional | PnL $ | PnL % | Reason | Regime |\n"
            md += "|---|---|---|---|---|---|---|---|---|---|\n"
            for i, t in enumerate(self.trades, 1):
                md += (
                    f"| {i} | {t['time_entry']} | {t['time_exit']} | {t['symbol']} | "
                    f"{t['side']} | ${t['notional']:.0f} | ${t['pnl_amt']:+.2f} | "
                    f"{t['pnl_pct']:+.2f}% | {t['reason']} | {t['regime']} |\n"
                )
        else:
            md += "\n> [!NOTE]\n> No trades fired. Engine stayed in defensive (cash) mode.\n"

        # Write report
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(md)

        # Also write equity curve CSV
        ec_fn = self.output_file.replace(".md", "_equity.csv")
        ec_df = pd.DataFrame(self.equity_curve, columns=["datetime", "equity"])
        ec_df.to_csv(ec_fn, index=False)

        log.info(f"\n✅ Report: {self.output_file}")
        log.info(f"✅ Equity curve: {ec_fn}")
        log.info(f"\n{'='*65}")
        log.info(f"  Net P&L : ${total_pnl:+,.2f}  ({roi:+.2f}%)")
        log.info(f"  Win Rate: {win_rate:.1%}")
        log.info(f"  Sharpe  : {sharpe:.2f}")
        log.info(f"  Max DD  : {max_dd:.2f}%")
        log.info(f"{'='*65}")


async def main():
    args = parse_args()
    runner = SovereignBacktestRunner(
        data_dir=args.data,
        start_date=args.start,
        end_date=args.end,
        output_file=args.output
    )
    await runner.run()

if __name__ == "__main__":
    asyncio.run(main())

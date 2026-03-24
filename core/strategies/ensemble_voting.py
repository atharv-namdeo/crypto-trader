import logging
import pandas as pd
import numpy as np
from core.strategies.base_strategy import BaseStrategy
from core.state_manager import StateManager
from core.pnl_tracker import PnLTracker
from strategies.utils import compute_rsi, compute_atr, compute_ema

log = logging.getLogger("ENSEMBLE_VOTE")

class EnsembleVotingStrategy(BaseStrategy):
    """
    Combine all signals + technical indicators.
    Only trade when multiple signals align.
    """
    def __init__(self, state: StateManager, pnl_tracker: PnLTracker, capital: float = 300.0):
        super().__init__(state, pnl_tracker, capital)
        self.name = "ENSEMBLE_VOTE"

    async def _process(self, symbol: str):
        df_1h = await self.state.get_df(f"ohlcv:1h:{symbol}", n=100)
        if df_1h is None or len(df_1h) < 26: return
        
        price = float(df_1h['close'].iloc[-1])
        votes = {} # {signal: confidence}
        
        # 1. Signal: RSI (Momentum Reversal)
        rsi = compute_rsi(df_1h, 14).iloc[-1]
        if rsi < 30: votes['RSI_LONG'] = 0.7
        elif rsi > 70: votes['RSI_SHORT'] = 0.7
        
        # 2. Signal: EMA Cross (Trend)
        ema20 = compute_ema(df_1h, 20).iloc[-1]
        ema50 = compute_ema(df_1h, 50).iloc[-1]
        if ema20 > ema50: votes['TREND_LONG'] = 0.8
        elif ema20 < ema50: votes['TREND_SHORT'] = 0.8
        
        # 3. Signal: ML Ensemble (AI prediction from main.py)
        prediction = await self.state.get(f"ml_signal:{symbol}")
        if prediction:
            ensemble_val = prediction.get('ensemble_val', 0.5)
            confidence = prediction.get('confidence', 0.5)
            if ensemble_val > 0.6: votes['AI_LONG'] = 0.9 * confidence
            elif ensemble_val < 0.4: votes['AI_SHORT'] = 0.9 * confidence
        
        # 4. Signal: ATR Volatility Gate
        atr = float(compute_atr(df_1h, 14).iloc[-1])
        if (atr / price) < 0.005: 
            return # Skip if market is dead
            
        # 5. Aggregate Votes
        long_score = sum(v for k, v in votes.items() if 'LONG' in k)
        short_score = sum(v for k, v in votes.items() if 'SHORT' in k)
        
        # Entry logic: Need at least 1.5 total confidence
        pos = await self.state.get(f"ensemble_vote:pos:{symbol}")
        
        if pos:
            # Simple Exit on Trend Reversal
            if pos['side'] == 'LONG' and short_score > 1.2:
                await self._close_position(symbol, pos, price, 'ENSEMBLE_REVERSE')
            elif pos['side'] == 'SHORT' and long_score > 1.2:
                await self._close_position(symbol, pos, price, 'ENSEMBLE_REVERSE')
        else:
            if long_score > 1.6:
                log.info(f"🏆 {symbol} Ensemble Voting LONG with score {long_score:.2f}")
                await self._open_position(symbol, 'LONG', price, long_score / 3.0)
            elif short_score > 1.6:
                log.info(f"🏆 {symbol} Ensemble Voting SHORT with score {short_score:.2f}")
                await self._open_position(symbol, 'SHORT', price, short_score / 3.0)

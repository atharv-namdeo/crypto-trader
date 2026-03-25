import logging
import pandas as pd
from core.strategies.base_strategy import BaseStrategy
from core.state_manager import StateManager
from core.pnl_tracker import PnLTracker

log = logging.getLogger("MEAN_REVERT")

class MeanReversionStrategy(BaseStrategy):
    """
    Trades when price deviates >2σ from 20-period moving average.
    Perfect for BTC/ETH ranging markets.
    """
    def __init__(self, state: StateManager, pnl_tracker: PnLTracker, manager=None, capital: float = 200.0):
        super().__init__(state, pnl_tracker, manager, capital)
        self.name = "MEAN_REVERT"

    async def _process(self, symbol: str):
        # 1. Fetch 5m OHLCV data
        df_5m = await self.state.get_df(f"ohlcv:5m:{symbol}", n=100)
        if df_5m is None or len(df_5m) < 20: 
            return

        # 2. Calculate Bollinger Bands
        sma_20 = df_5m['close'].rolling(20).mean()
        std_20 = df_5m['close'].rolling(20).std()
        upper_band = sma_20 + (2 * std_20)
        lower_band = sma_20 - (2 * std_20)
        
        price = float(df_5m['close'].iloc[-1])
        
        # 3. Check current position
        pos = await self.state.get(f"mean_revert:pos:{symbol}")

        if pos:
            # Exit logic: Return to mean
            side = pos['side']
            target_hit = False
            if side == 'LONG' and price >= sma_20.iloc[-1]:
                target_hit = True
            elif side == 'SHORT' and price <= sma_20.iloc[-1]:
                target_hit = True
            
            if target_hit:
                log.info(f"🎯 {symbol} Mean Reversion Target Hit at {price}")
                await self._close_position(symbol, pos, price, 'MEAN_REVERT')
                await self.state.set(f"mean_revert:pos:{symbol}", None)
        else:
            # Entry logic: Extreme deviation
            if price < lower_band.iloc[-1]:
                log.info(f"📉 {symbol} Mean Reversion LONG Entry Triggered at {price}")
                await self._open_position(symbol, 'LONG', price, 0.75) # 75% confidence
                await self.state.set(f"mean_revert:pos:{symbol}", {'side': 'LONG', 'entry': price})
            elif price > upper_band.iloc[-1]:
                log.info(f"📈 {symbol} Mean Reversion SHORT Entry Triggered at {price}")
                await self._open_position(symbol, 'SHORT', price, 0.75)
                await self.state.set(f"mean_revert:pos:{symbol}", {'side': 'SHORT', 'entry': price})

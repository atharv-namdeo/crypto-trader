import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from scipy.optimize import minimize
import logging

log = logging.getLogger("MROptimizer")

class MeanReversionOptimizer:
    """
    Optimizes Triple Barrier parameters (a, b) for maximum strategy efficiency.
    a = minimum return threshold (volatility base)
    b = exit profit/loss threshold (profit base)
    """
    
    def __init__(self, prices: np.ndarray, returns: np.ndarray):
        self.prices = prices
        self.returns = returns
        self.lookahead = 24 # 24 candles lookahead (1 day at 1h)
        self.transaction_cost = 0.0004 # 0.04% Taker fee
        
    def optimize_sharpe(self) -> Dict[str, float]:
        """
        Finds optimal (a, b) using differential evolution or standard minimize.
        Objective: Maximize Net Sharpe Ratio of the mean reversion labeling.
        """
        # Initial guesses: based on quantiles (a: 85th, b: 95th)
        initial_a = np.percentile(np.abs(self.returns), 85)
        initial_b = np.percentile(np.abs(self.returns), 99)
        
        # Optimizer logic (using Nelder-Mead for robustness to noise)
        res = minimize(
            self._objective_function, 
            x0=[initial_a, initial_b], 
            bounds=[(1e-4, 0.05), (1e-4, 0.1)],
            method='SLSQP'
        )
        
        opt_a, opt_b = res.x
        sharpe = -res.fun
        
        log.info(f"✅ Optimized Parameters: a={opt_a:.4f}, b={opt_b:.4f}, Sharpe={sharpe:.2f}")
        return {"a": opt_a, "b": opt_b, "sharpe": sharpe}

    def _objective_function(self, params: List[float]) -> float:
        """
        Negative Sharpe Ratio objective for the optimizer.
        """
        a, b = params
        trade_pnls = self.simulate_strategy(a, b)
        
        if len(trade_pnls) < 5:
            return 0.0 # Penalty for too few trades
            
        mean_pnl = np.mean(trade_pnls)
        std_pnl = np.std(trade_pnls) + 1e-9
        
        sharpe = (mean_pnl / std_pnl) * np.sqrt(len(trade_pnls))
        return -sharpe # Minimize negative sharpe

    def simulate_strategy(self, a: float, b: float) -> List[float]:
        """
        Simulates the Triple Barrier strategy PnL for given thresholds.
        """
        log_pnls = []
        in_trade = False
        entry_price = 0
        side = 0 # 1 long, -1 short
        
        for i in range(len(self.prices) - self.lookahead):
            curr_price = self.prices[i]
            
            # Labeling Logic (as per Triple Barrier)
            # Find the first barrier hit within lookahead window
            future_window = self.prices[i+1 : i + self.lookahead + 1]
            future_max = np.max(future_window)
            future_min = np.min(future_window)
            
            # Check for barriers (a, b)
            # This is a simplification: if it hits +b before -b, it's a BUY
            ret_to_max = (future_max - curr_price) / curr_price
            ret_to_min = (future_min - curr_price) / curr_price
            
            # Entry Signal if conditions met (simplified for optimizer)
            if not in_trade:
                if ret_to_max > b:
                    in_trade = True
                    entry_price = curr_price
                    side = 1
                elif ret_to_min < -b:
                    in_trade = True
                    entry_price = curr_price
                    side = -1
            else:
                # Resolve trade (simplified: next candle if exit hit)
                # In real scenario, we track each candle. 
                # For optimization, we take the result of the labels.
                pnl = ((future_window[0] - entry_price) / entry_price * side) - (self.transaction_cost * 2)
                log_pnls.append(pnl)
                in_trade = False
                
        return log_pnls

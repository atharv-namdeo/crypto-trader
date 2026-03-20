from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    """
    Standard interface for all Algorithms in the Top 20 System.
    """
    
    NAME = "Base"
    TIER = "INTRADAY"
    REGIME_GATE = []  # List of regimes where this algo is active
    
    def __init__(self, config=None):
        self.config = config or {}
    
    @abstractmethod
    def calculate_signal(self, df: pd.DataFrame) -> dict:
        """
        Processes OHLCV data and returns a signal dictionary.
        Returns: { 'symbol': str, 'direction': 'LONG'|'SHORT'|'NONE', 'entry': float, 'sl': float, 'tp': float, 'reason': str }
        """
        pass

    def calculate_position_size(self, portfolio_value: float, risk_pct: float, entry: float, stop_loss: float) -> float:
        """
        Risk-based position sizing: (portfolio * risk) / stop_distance
        """
        if abs(entry - stop_loss) == 0:
            return 0.0
            
        risk_amount = portfolio_value * (risk_pct / 100)
        stop_distance = abs(entry - stop_loss)
        
        return risk_amount / stop_distance

    def is_compatible(self, current_regime: str) -> bool:
        """
        Checks if the strategy is active in the current market regime.
        """
        return current_regime in self.REGIME_GATE

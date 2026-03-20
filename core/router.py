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

class AlgoRouter:
    """
    AlgoRouter / Meta-Selector.
    Responsible for activating and deactivating algorithms based on Market Regime.
    """
    
    def __init__(self):
        self.strategies = {
            'MTF': MomentumTrendFollowing(),
            'STAT_ARB': StatArb(),
            'MEAN_REVERSION': MeanReversion(),
            'BREAKOUT': VolatilityBreakout(),
            'OBIS': OrderBookImbalance(),
            'VWAP_REVERSION': VWAPReversion(),
            'LIQUIDITY_SWEEP': LiquiditySweep(),
            'MTF_MACD': MTFMACD(),
            'RSI_DIV': RSIDivergence(),
            'FIBONACCI': FibonacciRetracement(),
            'ICHIMOKU': IchimokuCloud(),
            'ATR_EXPANSION': ATRExpansion(),
            'VOLUME_PROFILE': VolumeProfile(),
            'PIVOT_POINTS': PivotPoints(),
            'PSAR': ParabolicSAR(),
            'SUPERTREND': SupertrendStrategy(),
            'GANN_FAN': GANNFan(),
            'HARMONIC': HarmonicPatterns(),
            'LIQUIDITY_GRAB': LiquidityGrabs(),
            'TREND_EXHAUST': TrendExhaustion()
        }
        
    def get_active_strategies(self, regime: str) -> list:
        """
        Returns a list of strategy instances that are compatible with the current regime.
        """
        active = []
        
        # In the future, this will be ML-driven (XGBoost/Neural Network)
        # For now, we use the rule-based REGIME_GATE defined in each strategy.
        
        for name, strategy in self.strategies.items():
            if strategy.is_compatible(regime):
                active.append(strategy)
                
        # "Always On" Strategies (Arb, Execution, On-chain)
        # Note: These will be added as they are implemented.
        
        return active

    def log_activation(self, active_names: list, regime: str):
        if not active_names:
            print(f"😴 Market Regime: {regime} | No strategy active. Standing by.")
        else:
            print(f"🔥 Market Regime: {regime} | Active Strategies: {', '.join(active_names)}")

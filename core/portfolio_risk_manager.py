import logging
from typing import Dict, List, Optional
from core.risk import RiskManager

log = logging.getLogger("PortfolioRisk")

class PortfolioRiskManager:
    """
    Advanced cross-asset risk management for multi-asset trading.
    Enforces sector limits and prevents highly correlated over-exposure.
    """

    SECTORS = {
        'L1': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'NEAR/USDT', 'LTC/USDT', 'BCH/USDT', 'TRX/USDT', 'XRP/USDT', 'LINK/USDT', 'ICP/USDT', 'APT/USDT', 'SUI/USDT'],
        'L2': ['POL/USDT', 'ARB/USDT', 'OP/USDT', 'METIS/USDT', 'MANTA/USDT'],
        'DEFI': ['LINK/USDT', 'UNI/USDT', 'AAVE/USDT', 'MKR/USDT', 'RUNE/USDT', 'DYDX/USDT', 'CRV/USDT', 'SNX/USDT'],
        'MEME': ['SHIB/USDT', 'DOGE/USDT', 'PEPE/USDT', 'FLOKI/USDT', 'BONK/USDT', 'WIF/USDT'],
        'PAYMENT': ['XRP/USDT', 'LTC/USDT', 'BCH/USDT', 'XLM/USDT'],
        'AI': ['FET/USDT', 'AGIX/USDT', 'OCEAN/USDT', 'RNDR/USDT', 'NEAR/USDT'],
        'STORAGE': ['FIL/USDT', 'AR/USDT'],
    }

    # Static correlation mapping (conservative estimates)
    CORRELATIONS = {
        ('BTC/USDT', 'ETH/USDT'): 0.85,
        ('SOL/USDT', 'ADA/USDT'): 0.75,
        ('ETH/USDT', 'LINK/USDT'): 0.70,
        ('BTC/USDT', 'SOL/USDT'): 0.65,
    }

    MAX_SECTOR_HEAT = 0.40  # Max 40% of total risk in one sector
    MAX_CORRELATED_EXPOSURE = 0.25  # Max 25% in highly correlated assets (>0.8)

    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager

    def get_symbol_sector(self, symbol: str) -> str:
        """Map symbol to its market sector using the SECTORS map."""
        for sector, symbols in self.SECTORS.items():
            if symbol in symbols:
                return sector
        return 'OTHER'

    async def validate_portfolio_impact(self, symbol: str, notional: float, current_positions: Dict) -> bool:
        """
        Check if adding this trade violates portfolio-wide rules.
        """
        # 1. Total Portfolio Heat (already handled by RiskManager, but we can add more)
        
        # 2. Sector Concentration
        sector = self.get_symbol_sector(symbol)
        sector_usage: float = 0.0
        total_equity: float = 1000.0 
        
        if self.risk_manager.state:
            val = await self.risk_manager.state.get_float('portfolio:value')
            if val is not None:
                total_equity = float(val)

        for s, pos in current_positions.items():
            if self.get_symbol_sector(s) == sector:
                sector_usage += float(abs(pos.get('notional', 0.0)))

        if (sector_usage + notional) / total_equity > self.MAX_SECTOR_HEAT:
            log.warning(f"❌ Sector {sector} limit exceeded: "
                       f"{(sector_usage + notional) / total_equity:.1%} > {self.MAX_SECTOR_HEAT:.1%}")
            return False

        # 3. Correlation Check
        # If we have a high correlation with another active position, limit combined size
        for s, pos in current_positions.items():
            corr = self.CORRELATIONS.get((symbol, s)) or self.CORRELATIONS.get((s, symbol)) or 0
            if corr > 0.8:
                combined_notional = notional + abs(pos.get('notional', 0))
                if combined_notional / total_equity > self.MAX_CORRELATED_EXPOSURE:
                    log.warning(f"❌ Correlation limit exceeded with {s}: "
                               f"{combined_notional / total_equity:.1%} > {self.MAX_CORRELATED_EXPOSURE:.1%}")
                    return False

        return True

    def calculate_global_drawdown(self, positions: Dict) -> float:
        """Sum up unrealized PnL across all assets."""
        total_pnl = sum(pos.get('unrealized_pnl', 0) for pos in positions.values())
        return total_pnl

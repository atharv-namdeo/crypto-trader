import logging

log = logging.getLogger("SlippageModel")

class SlippageModel:
    """
    Expert-grade slippage estimation based on symbol liquidity tiers
    and order size relative to 24h volume.
    """
    
    # Base slippage in decimals (e.g., 0.0002 = 0.02%)
    BASE_SLIPPAGE = {
        'TIER_1': 0.0002,  # BTC, ETH
        'TIER_2': 0.0005,  # High-cap Alts
        'TIER_3': 0.0010,  # Mid-cap Alts
        'TIER_4': 0.0020   # Low-cap/New Alts
    }
    
    # Market impact coefficient (empirical constant)
    IMPACT_COEFFICIENT = 0.1 

    @staticmethod
    def estimate_slippage(symbol: str, tier: str, order_qty: float, price: float, volume_24h_usd: float = 0) -> float:
        """
        Calculates estimated slippage as a decimal percentage of price.
        Formula: slippage = base_tier_slippage + (order_size / 24h_volume * coefficient)
        """
        base = SlippageModel.BASE_SLIPPAGE.get(tier, 0.0010)
        
        order_value_usd = order_qty * price
        
        impact = 0.0
        if volume_24h_usd > 0:
            size_pct = order_value_usd / volume_24h_usd
            impact = size_pct * SlippageModel.IMPACT_COEFFICIENT
            
        total_slippage = base + impact
        
        # Cap slippage at 1% to prevent unrealistic extremes in backtests
        return min(total_slippage, 0.01)

    @staticmethod
    def get_tier(symbol: str) -> str:
        """Helper to map symbols to tiers if SYMBOL_CONFIG is not available."""
        if any(x in symbol for x in ['BTC', 'ETH']): return 'TIER_1'
        if any(x in symbol for x in ['SOL', 'BNB', 'XRP', 'ADA']): return 'TIER_2'
        # Default mid-tier
        return 'TIER_3'

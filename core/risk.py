class RiskManager:
    """
    Risk Management Overlay.
    Hard-stops and limits enforced before any orders are sent to the exchange.
    """
    
    def __init__(self, config=None):
        self.config = config or {}
        self.max_portfolio_heat = 0.06  # 6% Max Risk Exposure
        self.max_asset_exposure = 0.40  # 40% Max Capital in one coin
        self.max_daily_drawdown = 0.03  # 3% Daily Loss Limit
        self.min_rr_ratio = 1.5         # 1.5 Min Risk/Reward
        
    def validate_trade(self, trade_params: dict, current_portfolio_value: float, open_positions: list) -> bool:
        """
        Validates a trade signal against risk parameters.
        trade_params: { 'entry', 'sl', 'tp', 'qty', 'direction' }
        """
        if not trade_params.get('entry') or not trade_params.get('sl'):
            return False
            
        # 1. Risk/Reward Ratio Check
        risk = abs(trade_params['entry'] - trade_params['sl'])
        reward = abs(trade_params['tp'] - trade_params['entry'])
        
        if risk == 0 or (reward / risk) < self.min_rr_ratio:
            print(f"⚠️ Risk/Reward Ratio too low: {(reward/risk):.2f}. Required: {self.min_rr_ratio}")
            return False
            
        # 2. Portfolio Heat (Current Risk exposure)
        # Sum of risk on all open positions + new trade risk
        current_heat = 0 # Placeholder for calculating heat of open positions
        new_trade_risk_amount = trade_params['qty'] * risk
        total_heat = (current_heat + new_trade_risk_amount) / current_portfolio_value
        
        if total_heat > self.max_portfolio_heat:
            print(f"⚠️ Portfolio Heat exceeded: {total_heat:.2%}. Max: {self.max_portfolio_heat:.2%}")
            return False
            
        # 3. Capital Exposure check
        notional_value = trade_params['qty'] * trade_params['entry']
        asset_exposure = notional_value / current_portfolio_value
        
        if asset_exposure > self.max_asset_exposure:
            print(f"⚠️ Asset Exposure exceeded: {asset_exposure:.2%}. Max: {self.max_asset_exposure:.2%}")
            return False
            
        return True

    def check_daily_drawdown(self, starting_capital: float, current_capital: float) -> bool:
        """
        Returns True if daily drawdown limit has been breached.
        """
        drawdown = (starting_capital - current_capital) / starting_capital
        if drawdown >= self.max_daily_drawdown:
            print(f"🛑 CRITICAL: Daily Drawdown Limit Reached ({drawdown:.2%}). Halting trading.")
            return True
        return False

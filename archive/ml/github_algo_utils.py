import numpy as np
import pandas as pd
from typing import Tuple, List, Optional

def compute_thresholds(percentage_returns: np.ndarray) -> Tuple[float, float]:
    """
    Refined Triple Barrier thresholds based on risk/reward distribution.
    a = High conviction threshold
    b = Extreme volatility threshold (noise ceiling)
    """
    if len(percentage_returns) == 0:
        return 0.005, 0.02
    
    returns_abs = np.abs(percentage_returns)
    # Using 90th and 99th percentiles for more consistent labeling
    a = np.percentile(returns_abs, 90)
    b = np.percentile(returns_abs, 99)
    
    # Ensure minimum thresholds to cover fees (at least 0.2%)
    a = max(a, 0.002)
    b = max(b, 0.005)
    
    return a, b

def labeling_algorithm(close_prices: pd.Series, backW: int, forW: int, a: float, b: float, f: float = 0.0004) -> List[str]:
    """
    Upgraded Triple Barrier Labeling with realistic costs and lookahead validation.
    
    Args:
        close_prices: Series of closing prices.
        backW: Backward window for EMA smoothing.
        forW: Forward window (lookahead) for calculating target returns.
        a: Target return threshold (min to consider BUY/SELL).
        b: Noise ceiling (reject if return is extreme/anomalous).
        f: Transaction fee (taker fee 0.04% default).
    """
    # Smooth prices with EMA to filter micro-volatility
    smoothed = close_prices.ewm(span=backW, min_periods=backW).mean().values
    
    labels = []
    # Loop over indices with enough lookahead
    for i in range(len(smoothed) - forW):
        current_val = smoothed[i]
        
        # Look for first barrier hit in the forward window
        # In this simplified version, we just check the price at forW
        future_val = smoothed[i + forW]
        
        # Net return after round-trip fees (2 * f)
        net_ret = ((future_val - current_val) / current_val) - (2 * f)
        
        # Action Gating: Signal must exceed 'a' but stay below anomalous 'b'
        if a < abs(net_ret) < b:
            labels.append('Buy' if net_ret > 0 else 'Sell')
        else:
            labels.append('Hold')
            
    return labels

def calculate_ultosc(data: pd.DataFrame, period1: int = 7, period2: int = 14, period3: int = 28) -> pd.Series:
    """
    Calculate the Ultimate Oscillator (ULTOSC).
    """
    # Use close - low and high - low as per original code
    low_diff = data['close'] - data['low']
    range_diff = data['high'] - data['low']
    
    average1 = low_diff.rolling(window=period1).sum() / range_diff.rolling(window=period1).sum()
    average2 = low_diff.rolling(window=period2).sum() / range_diff.rolling(window=period2).sum()
    average3 = low_diff.rolling(window=period3).sum() / range_diff.rolling(window=period3).sum()

    ultosc = 100 * (4 * average1 + 2 * average2 + average3) / (4 + 2 + 1)
    return ultosc

def calculate_net_profit(close_prices: pd.Series, labels: List[str], initial_investment: float = 10000.0) -> float:
    """
    Simulate trading and calculate net profit based on labels.
    """
    buy_amount = 1000.0  # Reduced for more granular testing
    net_profit = 0.0
    stocks_held = 0.0

    # Ensure length matches
    n = min(len(close_prices), len(labels))
    
    for i in range(n):
        if labels[i] == 'Buy':
            stocks_held += buy_amount / close_prices.iloc[i]
        elif labels[i] == 'Sell' and stocks_held > 0:
            net_profit += (stocks_held * close_prices.iloc[i])
            stocks_held = 0.0

    # Final liquidation
    net_profit += (stocks_held * close_prices.iloc[-1])
    return net_profit - (initial_investment if initial_investment > 0 else 0)

def simulate_strategy(currency_data: pd.DataFrame, backW: int, forW: int, a: float, b: float, 
                      num_simulations: int = 100) -> Tuple[float, float]:
    """
    Monte Carlo Simulation for strategy robustness.
    Returns (stability_score, mean_net_profit).
    stability_score is 1 - (std_dev / mean) normalized.
    """
    simulation_profits = []
    close_prices = currency_data['close']
    
    for _ in range(num_simulations):
        # Add random variations to thresholds
        a_sim = a + np.random.uniform(-0.005, 0.005)
        b_sim = b + np.random.uniform(-0.01, 0.01)
        
        labels = labeling_algorithm(close_prices, backW, forW, a_sim, b_sim)
        profit = calculate_net_profit(close_prices, labels, initial_investment=0)
        simulation_profits.append(profit)
        
    mean_profit = np.mean(simulation_profits)
    std_profit = np.std(simulation_profits)
    
    # Stability score: higher is better (lower relative variance)
    # Using coefficient of variation inverse logic
    if mean_profit != 0:
        stability_score = 1.0 / (1.0 + (std_profit / (abs(mean_profit) + 1e-9)))
    else:
        stability_score = 0.0
        
    return stability_score, mean_profit

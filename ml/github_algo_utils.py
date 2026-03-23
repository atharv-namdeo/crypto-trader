import numpy as np
import pandas as pd
from typing import Tuple, List, Optional

def compute_thresholds(percentage_returns: np.ndarray) -> Tuple[float, float]:
    """
    Compute Triple Barrier Labeling thresholds a and b based on return percentiles.
    """
    if len(percentage_returns) == 0:
        return 0.01, 0.05
    a = np.percentile(percentage_returns, 85)
    b = np.percentile(percentage_returns, 99.7)
    return a, b

def labeling_algorithm(close_prices: pd.Series, backW: int, forW: int, a: float, b: float, f: float = 0.005) -> List[str]:
    """
    Triple Barrier Labeling algorithm from the GitHub repository.
    
    Args:
        close_prices: Series of closing prices.
        backW: Backward window for EMA smoothing.
        forW: Forward window for calculating returns.
        a: Lower threshold for buy/sell.
        b: Upper threshold for buy/sell.
        f: Fee or perturbation factor.
    """
    # Smooth prices with EMA
    smoothed_prices = close_prices.ewm(span=backW, min_periods=backW).mean()
    smoothed_values = smoothed_prices.values

    labels = []
    for i in range(len(smoothed_values) - forW):
        # Compute return of smoothed prices
        future_val = smoothed_values[i + forW]
        current_val = smoothed_values[i]
        
        R = ((1 - f) * future_val - (1 + f) * current_val) / current_val
        
        # Check if return falls within thresholds a and b
        if a < abs(R) < b:
            if R > 0:
                labels.append('Buy')
            else:
                labels.append('Sell')
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

import pandas as pd
import numpy as np
import os
import glob
from tqdm import tqdm
from datetime import datetime

# Import strategy logic (mocking/refactoring for fast backtest)
class StrategyTester:
    def __init__(self, df):
        self.df = df.copy()
        self._calculate_indicators()
    
    def _calculate_indicators(self):
        # Base indicators
        self.df['ema9'] = self.df['close'].ewm(span=9, adjust=False).mean()
        self.df['ema21'] = self.df['close'].ewm(span=21, adjust=False).mean()
        self.df['ema200'] = self.df['close'].ewm(span=200, adjust=False).mean()
        
        # RSI
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        self.df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR
        high_low = self.df['high'] - self.df['low']
        high_cp = (self.df['high'] - self.df['close'].shift()).abs()
        low_cp = (self.df['low'] - self.df['close'].shift()).abs()
        tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        self.df['atr'] = tr.rolling(14).mean()
        self.df['bg_atr'] = tr.rolling(20).mean()
        self.df['local_atr'] = tr.rolling(4).mean()
        
        # Regime
        self.df['regime'] = np.where(self.df['close'] > self.df['ema200'] * 1.01, "BULL", 
                            np.where(self.df['close'] < self.df['ema200'] * 0.99, "BEAR", "NEUTRAL"))

    def run_strategy(self, name):
        results = []
        in_pos = False
        entry_price = 0
        side = None
        
        # Loop through data (starting after indicator warmup)
        for i in range(200, len(self.df)):
            row = self.df.iloc[i]
            prev = self.df.iloc[i-1]
            
            # 1. Check Exit
            if in_pos:
                # Simple exit logic (trailing or fixed % for analysis)
                pnl = (row['close'] - entry_price) / entry_price if side == "BUY" else (entry_price - row['close']) / entry_price
                
                # Exit conditions
                exit_triggered = False
                if name == "MOMENTUM" and ((side=="BUY" and row['ema9'] < row['ema21']) or (side=="SELL" and row['ema9'] > row['ema21'])): exit_triggered = True
                elif name == "RSI" and ((side=="BUY" and row['rsi'] > 70) or (side=="SELL" and row['rsi'] < 30)): exit_triggered = True
                elif pnl > 0.05 or pnl < -0.02: exit_triggered = True # Global safety
                
                if exit_triggered:
                    results.append({"pnl": pnl, "regime": row['regime']})
                    in_pos = False
                continue

            # 2. Check Entry
            signal = "NEUTRAL"
            score = 0.5
            
            if name == "MOMENTUM":
                if row['ema9'] > row['ema21'] and prev['ema9'] <= prev['ema21']: signal = "BUY"
                elif row['ema9'] < row['ema21'] and prev['ema9'] >= prev['ema21']: signal = "SELL"
            
            elif name == "RSI":
                if row['regime'] == "BULL" and prev['rsi'] < 35 and row['rsi'] >= 35: signal = "BUY"
                elif row['regime'] == "BEAR" and prev['rsi'] > 65 and row['rsi'] <= 65: signal = "SELL"
            
            elif name == "VCE":
                contracted = row['local_atr'] < (row['bg_atr'] * 0.82)
                # Simplified VCE
                hi_50 = self.df['high'].iloc[i-50:i].max()
                lo_50 = self.df['low'].iloc[i-50:i].min()
                if contracted and row['close'] < lo_50 + (hi_50-lo_50)*0.35: signal = "BUY"
                elif contracted and row['close'] > hi_50 - (hi_50-lo_50)*0.35: signal = "SELL"
            
            elif name == "MDT":
                # Mean Deviation Trail logic
                ema30 = self.df['close'].iloc[i-30:i].mean()
                mad = (self.df['close'].iloc[i-9:i] - ema30).abs().mean()
                if mad > 0:
                    dev = (row['close'] - ema30) / mad
                    if dev > 1.5: signal = "BUY"
                    elif dev < -1.5: signal = "SELL"
            
            elif name == "PEE":
                # Pulse Entry Engine (ROC sum)
                roc10 = (row['close'] - self.df['close'].iloc[i-10]) / self.df['close'].iloc[i-10]
                roc30 = (row['close'] - self.df['close'].iloc[i-30]) / self.df['close'].iloc[i-30]
                if (roc10 + roc30) > 0.05: signal = "BUY"
                elif (roc10 + roc30) < -0.05: signal = "SELL"

            elif name == "OMEGA_ENSEMBLE":
                # Combined logic
                votes = 0
                if row['ema9'] > row['ema21']: votes += 1
                if row['rsi'] < 40: votes += 1
                if row['local_atr'] < row['bg_atr']: votes += 1
                if votes >= 2 and row['regime'] != "NEUTRAL":
                    signal = "BUY" if row['regime'] == "BULL" else "SELL"

            if signal != "NEUTRAL":
                in_pos = True
                entry_price = row['close']
                side = signal
        
        if not results: return {"total_pnl": 0, "win_rate": 0, "trades": 0}
        
        pnls = [r['pnl'] for r in results]
        return {
            "total_pnl": sum(pnls) * 100,
            "win_rate": (len([p for p in pnls if p > 0]) / len(pnls)) * 100,
            "trades": len(pnls),
            "avg_pnl": (sum(pnls) / len(pnls)) * 100 if pnls else 0
        }

def analyze_all():
    files = glob.glob("data/historical_2yr/*.csv")
    strategies = ["MOMENTUM", "RSI", "VCE", "MDT", "PEE", "OMEGA_ENSEMBLE"]
    
    summary = []
    
    for f in tqdm(files, desc="Analyzing Symbols"):
        symbol = os.path.basename(f).split('_')[0] + "/" + os.path.basename(f).split('_')[1]
        df = pd.read_csv(f)
        tester = StrategyTester(df)
        
        for strat in strategies:
            res = tester.run_strategy(strat)
            summary.append({
                "Symbol": symbol,
                "Strategy": strat,
                "PnL (%)": round(res['total_pnl'], 2),
                "WinRate (%)": round(res['win_rate'], 2),
                "Trades": res['trades'],
                "Avg/Trade (%)": round(res['avg_pnl'], 2)
            })
            
    return pd.DataFrame(summary)

if __name__ == "__main__":
    # Ensure data is ready
    if not os.path.exists("data/historical_2yr"):
        print("Data not found. Run fetcher first.")
    else:
        results_df = analyze_all()
        # Pivot for clean comparison
        pivot_pnl = results_df.pivot(index="Symbol", columns="Strategy", values="PnL (%)")
        pivot_win = results_df.pivot(index="Symbol", columns="Strategy", values="WinRate (%)")
        
        print("\n=== TOTAL PNL (%) Comparison ===")
        print(pivot_pnl)
        print("\n=== WIN RATE (%) Comparison ===")
        print(pivot_win)
        
        results_df.to_csv("strategy_parallel_analysis.csv", index=False)
        
        # Generate Markdown Report
        with open("strategy_analysis_report.md", "w") as r:
            r.write("# Sovereign Omega — 2-Year Strategy Performance Audit\n\n")
            r.write("## Total PnL (%) by Strategy\n")
            r.write(pivot_pnl.to_markdown() + "\n\n")
            r.write("## Win Rate (%) by Strategy\n")
            r.write(pivot_win.to_markdown() + "\n\n")
            r.write("## Top Performer Summary\n")
            top = results_df.sort_values("PnL (%)", ascending=False).head(10)
            r.write(top.to_markdown() + "\n")

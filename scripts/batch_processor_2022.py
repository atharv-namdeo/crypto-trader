import os
import sys
import subprocess
import pandas as pd
from datetime import datetime, timedelta
import re

# Schedule: Dec 1, 2021 to Dec 1, 2022 (Bear Market Survival Audit)
START_DATE = datetime(2021, 12, 1)
END_DATE = datetime(2022, 12, 1)
RESULTS_DIR = "backtest_results_2022"
DATA_BASE_DIR = "bear_market_data_2022"

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(DATA_BASE_DIR, exist_ok=True)

# Define Legacy 20 Symbols for 2022
LEGACY_SYMBOLS = "BTC/USDT,ETH/USDT,SOL/USDT,XRP/USDT,ADA/USDT,DOGE/USDT,SHIB/USDT,AVAX/USDT,LINK/USDT,UNI/USDT,DOT/USDT,BCH/USDT,NEAR/USDT,LTC/USDT,XLM/USDT,ATOM/USDT,HBAR/USDT,ALGO/USDT,FIL/USDT,VET/USDT,ETC/USDT,AAVE/USDT,STX/USDT"

def run_step(start_date, days=7):
    date_str = start_date.strftime("%Y-%m-%d")
    week_dir = os.path.join(DATA_BASE_DIR, f"week_{date_str}")
    report_file = os.path.join(RESULTS_DIR, f"report_{date_str}.md")
    
    print(f"\n--- Processing Week Starting: {date_str} ---")
    
    # 1. Fetch Data (if not already there)
    if not os.path.exists(week_dir) or len(os.listdir(week_dir)) < 10:
        print(f"📦 Fetching data for {date_str}...")
        subprocess.run([
            sys.executable, "scripts/fetch_backtest_data.py",
            "--start", date_str,
            "--days", str(days),
            "--dir", week_dir,
            "--symbols", LEGACY_SYMBOLS
        ], check=True)
    else:
        print(f"✅ Data already exists for {date_str}")

    # 2. Run Backtest
    print(f"📉 Running backtest for {date_str}...")
    subprocess.run([
        sys.executable, "backtest_pro.py",
        "--dir", week_dir,
        "--output", report_file
    ], check=True)
    
    # 3. Parse Results
    return parse_report(report_file, date_str)

def parse_report(file_path, date_str):
    with open(file_path, "r") as f:
        content = f.read()
    
    # regex for PnL
    pnl_match = re.search(r"PnL:.*?\((?P<pnl>[0-9.+-]+)%\)", content)
    usd_match = re.search(r"PnL:.*?\$([-\d\.]+)", content)
    wr_match = re.search(r"Win Rate: ([\d\.]+)%", content)
    trades_match = re.search(r"Total Trades: ([\d]+)", content)
    pf_match = re.search(r"Profit Factor: ([\d\.]+)", content)
    
    return {
        "week_start": date_str,
        "pnl_usd": float(usd_match.group(1)) if usd_match else 0,
        "pnl_pct": float(pnl_match.group('pnl')) if pnl_match else 0,
        "win_rate": float(wr_match.group(1)) if wr_match else 0,
        "trades": int(trades_match.group(1)) if trades_match else 0,
        "profit_factor": float(pf_match.group(1)) if pf_match else 0
    }

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Limit number of weeks to process", default=999)
    args = parser.parse_args()

    current_date = START_DATE
    all_results = []
    processed_count = 0
    master_csv = os.path.join(RESULTS_DIR, "longitudinal_master.csv")
    
    # Load existing results if any
    if os.path.exists(master_csv):
        all_results = pd.read_csv(master_csv).to_dict('records')
        processed_weeks = [r['week_start'] for r in all_results]
    else:
        processed_weeks = []

    try:
        while current_date < END_DATE and processed_count < args.limit:
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str in processed_weeks:
                print(f"⏭️ Skipping {date_str} (already processed)")
            else:
                res = run_step(current_date)
                all_results.append(res)
                processed_count += 1
                # Save progress after each week
                pd.DataFrame(all_results).to_csv(master_csv, index=False)
            
            current_date += timedelta(days=7)
    except KeyboardInterrupt:
        print("\n🛑 Batch stopped by user. Progress saved.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print("\n✨ BATCH COMPLETE ✨")
    if all_results:
        final_df = pd.DataFrame(all_results)
        print(final_df)
        print(f"\nTotal PnL %: {final_df['pnl_pct'].sum():.2f}%")

if __name__ == "__main__":
    main()

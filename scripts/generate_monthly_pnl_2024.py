import glob
import re
import pandas as pd
from datetime import datetime
import sys

def generate_monthly():
    files = sorted(glob.glob('backtest_results/report_2024-*.md'))
    data = []
    
    for f in files:
        date_str = f.split('_')[-1].replace('.md', '')
        date = datetime.strptime(date_str, '%Y-%m-%d')
        month_label = date.strftime('%Y-%m') # e.g., 2024-04
        
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
            # Capture PnL %
            match = re.search(r'PnL:.*?\((?P<pnl>[0-9.+-]+)%\)', content)
            pnl = float(match.group('pnl')) if match else 0.0
            data.append({'Month': month_label, 'PnL': pnl})

    df = pd.DataFrame(data)
    
    # Calculate compounded monthly return (using additive sum for simplicity in this specific audit)
    monthly_summary = df.groupby('Month')['PnL'].sum().reset_index()
    
    sys.stdout.reconfigure(encoding='utf-8')
    print("\n## 2024 HALVING AUDIT: MONTHLY PERFORMANCE")
    print("| Month | ROI (%) | Verdict |")
    print("| :--- | :--- | :--- |")
    
    for _, row in monthly_summary.iterrows():
        status = "✅ ALPHA" if row['PnL'] > 0 else "🛡️ SHIELD"
        if row['PnL'] > 20: status = "🚀 DOMINANT"
        print(f"| {row['Month']} | {row['PnL']:.2f}% | {status} |")

if __name__ == "__main__":
    generate_monthly()

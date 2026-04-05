import glob
import os
import re
import pandas as pd

def summarize():
    # Use the main results directory for 2025-2026
    files = sorted(glob.glob('backtest_results/report_20*.md'))
    results = []
    
    print(f"📊 Analyzing {len(files)} weeks of 2025-26 backtest data...")
    
    for f in files:
        week = f.split('_')[-1].replace('.md', '')
        with open(f, 'r') as file:
            content = file.read()
            if "No trades." in content:
                results.append({'Week': week, 'PnL %': 0.0})
                continue
            # Extract PnL % using robust regex (captures "(+12.3%)" or "(-12.3%)")
            match = re.search(r'PnL:.*?\((?P<pnl>[0-9.+-]+)%\)', content)
            if match:
                results.append({
                    'Week': week,
                    'PnL %': float(match.group('pnl'))
                })
    
    if not results:
        print("❌ No valid PnL data found in reports.")
        return

    df = pd.DataFrame(results)
    total_roi = df['PnL %'].sum()
    max_drawdown = df['PnL %'].min()
    win_weeks = len(df[df['PnL %'] > 0])
    survival_rate = (win_weeks / len(df)) * 100

    output = []
    output.append("# 2024 HALVING RESILIENCE AUDIT (v11.1 Grandmaster)")
    output.append(f"📅 Period: {df['Week'].min()} to {df['Week'].max()}")
    output.append(f"📈 Total Accum. ROI: {total_roi:.2f}%")
    output.append(f"🛡️ Max Weekly Drawdown: {max_drawdown:.2f}%")
    output.append(f"💎 Survival Rate: {survival_rate:.1f}%")
    
    verdict = "✅ VERDICT: INSTITUTIONAL GRADE. Ready for live capital." if total_roi > 15 else "⚠️ VERDICT: RETAIL GRADE. Needs more alpha."
    output.append(f"\n{verdict}")
    
    # Save to file with UTF-8
    summary_path = 'backtest_results/final_audit_summary_2024.md'
    with open(summary_path, 'w', encoding='utf-8') as f_out:
        f_out.write("\n".join(output))
    
    import sys
    # Use utf-8 for stdout printing to avoid Windows charmap errors
    sys.stdout.reconfigure(encoding='utf-8')
    
    print(f"\n✨ Summary generated: {summary_path}")
    print("\n".join(output))

if __name__ == "__main__":
    summarize()

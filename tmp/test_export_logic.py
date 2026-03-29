import os
import sys
import io
import csv
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from utils.firebase_client import get_all_trades

def test_export():
    print("🧪 Calling get_all_trades()...")
    import utils.firebase_client
    print(f"🧪 Firebase client db: {utils.firebase_client.db}")
    trades = utils.firebase_client.get_all_trades()
    print(f"🧪 Fetched {len(trades)} trades.")
    
    if trades:
        print("🧪 Testing CSV generation...")
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=trades[0].keys())
        writer.writeheader()
        writer.writerows(trades)
        csv_content = output.getvalue()
        print(f"CSV length: {len(csv_content)}")
        print("CSV Header:", csv_content.split('\n')[0])
    else:
        print("⚠️ No trades to test CSV generation with.")

if __name__ == "__main__":
    test_export()

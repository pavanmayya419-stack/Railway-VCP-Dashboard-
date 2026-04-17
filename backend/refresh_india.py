import pandas as pd
import os
import sys

# Add current directory to path so we can import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ohlcv_store import bulk_download
from generate_cache import generate_cache

def main():
    # 1. Load Tickers from nifty500.csv
    csv_path = "nifty500.csv"
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    nifty = pd.read_csv(csv_path)
    if "Symbol" not in nifty.columns:
        print(f"Error: 'Symbol' column not found in {csv_path}.")
        return

    tickers = (nifty["Symbol"] + ".NS").tolist()
    print(f"Detected {len(tickers)} Indian tickers.")

    # 2. Bulk Refresh OHLCV (Parquet files)
    # We use incremental=True to only fetch the last week/missing days
    print("\n[Step 1/2] Refreshing OHLCV data via yfinance (incremental)...")
    bulk_download("IN", tickers, incremental=True, workers=10)

    # 3. Regenerate Scanner Cache (pkl files)
    # This will use the refreshed parquet files to regenerate the dashboard results
    print("\n[Step 2/2] Regenerating VCP Scanner cache for the dashboard...")
    generate_cache(market="IN", limit=None)

    print("\nFull refresh complete. All 500 Indian tickers are now up to date.")

if __name__ == "__main__":
    main()

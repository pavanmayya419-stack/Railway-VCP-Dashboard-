import os
import sys
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# Add current dir to path
sys.path.append(os.getcwd())

from ticker_metadata import get_metadata

def populate_all():
    # Load tickers
    csv_path = "fyers_tickers.csv"
    if not os.path.exists(csv_path):
        print("fyers_tickers.csv not found")
        return
        
    df = pd.read_csv(csv_path)
    tickers = df["Symbol"].tolist()
    
    # Pre-load cache
    from ticker_metadata import _metadata_cache, _ensure_cache
    _ensure_cache()
    
    to_fetch = []
    for t in tickers:
        key = t.split(".")[0].upper()
        if key not in _metadata_cache or _metadata_cache[key].get("sector") == "Unknown" or _metadata_cache[key].get("cap") == "Unknown":
            to_fetch.append(t)
            
    print(f"Total Tickers: {len(tickers)} | Already cached: {len(tickers) - len(to_fetch)} | Need to fetch: {len(to_fetch)}")
    
    if not to_fetch:
        print("All metadata already populated.")
        return

    def work(t):
        try:
            m = get_metadata(t, "IN")
            return f"{t}: {m['sector']} | {m['cap']}"
        except Exception as e:
            return f"{t}: Failed ({e})"

    # Use threads to speed up yfinance info fetching
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(work, tickers))
        
    print("\nSample Results:")
    for r in results[:10]:
        print(r)
    
    print("\nMetadata population complete.")

if __name__ == "__main__":
    populate_all()

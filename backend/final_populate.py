import os
import sys
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.getcwd())
from ticker_metadata import get_metadata, _metadata_cache, _ensure_cache, _persist_cache

def force_populate():
    # Load tickers
    csv_path = "fyers_tickers.csv"
    df = pd.read_csv(csv_path)
    tickers = df["Symbol"].tolist()
    
    _ensure_cache()
    
    missing = []
    for t in tickers:
        key = t.split(".")[0].upper()
        m = _metadata_cache.get(key, {})
        if m.get("sector", "Unknown") == "Unknown" or m.get("cap", "Unknown") == "Unknown":
            missing.append(t)
            
    print(f"Total: {len(tickers)} | Missing/Partial: {len(missing)}")
    
    if not missing:
        return

    def work(t):
        for retry in range(3):
            try:
                m = get_metadata(t, "IN")
                if m["sector"] != "Unknown" and m["cap"] != "Unknown":
                    return True
                time.sleep(0.5)
            except:
                time.sleep(1)
        return False

    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(work, missing)
        
    print("Population pass complete.")
    _persist_cache()

if __name__ == "__main__":
    force_populate()

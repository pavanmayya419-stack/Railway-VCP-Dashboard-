import pandas as pd
import os
import pickle
import time
from datetime import datetime
from engine import fetch_data, DETECTOR

def generate_cache(market="IN", limit=None):
    # Standardize market name
    market = "IN" if market.upper() in ["IN", "INDIA", "INDIA (NSE)"] else "US"
    
    # Load tickers from local nifty500.csv or fyers_tickers.csv
    tickers = []
    if market == "IN":
        for csv_name in ["nifty500.csv", "fyers_tickers.csv"]:
            csv_path = os.path.join(os.path.dirname(__file__), csv_name)
            if os.path.exists(csv_path):
                nifty = pd.read_csv(csv_path)
                if "Symbol" in nifty.columns:
                    tickers = (nifty["Symbol"] + ".NS").tolist()
                    break
    else:
        # Default/US - load from sp500_constituents.csv
        csv_path = os.path.join(os.path.dirname(__file__), "sp500_constituents.csv")
        if os.path.exists(csv_path):
            sp500 = pd.read_csv(csv_path)
            tickers = sp500["Symbol"].tolist()
        else:
            tickers = ["AAPL", "MSFT", "NVDA", "TSLA", "META", "AMZN", "GOOGL", "NFLX"]
            
    if not tickers:
        print("Could not find tickers. using fallback list.")
        tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS"] if market == "IN" else ["AAPL", "MSFT"]
        
    if limit:
        tickers = tickers[:limit]
        
    results = []
    print(f"Generating cache for {len(tickers)} tickers in {market}...")
    start_time = time.time()
    
    for i, ticker in enumerate(tickers):
        try:
            data_df = fetch_data(ticker, market=market)
            if data_df is not None and not data_df.empty and len(data_df) >= 60:
                res = DETECTOR.analyse(data_df, ticker=ticker)
                if "df" in res:
                    del res["df"]
                results.append(res)
        except Exception as e:
            pass
            
        if (i+1) % 50 == 0:
            print(f"Processed {i+1}/{len(tickers)}... ({len(results)} valid)")

    # Save cache
    if not results:
        print(f"❌ No results found for {market}. Skipping cache save to avoid overwriting good data.")
        return

    date_str = datetime.now().strftime("%Y-%m-%d")
    cache_dir = os.path.join(os.path.dirname(__file__), "outputs", "scan_cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    out_path = os.path.join(cache_dir, f"{market}_{date_str}.pkl")
    with open(out_path, "wb") as f:
        pickle.dump(results, f)
        
    print(f"Successfully generated cache for {len(results)} tickers at {out_path} in {time.time()-start_time:.1f}s.")

if __name__ == "__main__":
    generate_cache("IN")
    generate_cache("US")

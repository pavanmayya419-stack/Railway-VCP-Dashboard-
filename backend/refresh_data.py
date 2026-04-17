"""
Refresh scan data for both US and India markets.

Smart incremental strategy:
- Historical PKL files are NEVER touched — they remain as permanent record.
- Today's cache is only regenerated if explicitly requested (force=True) or missing.
- This avoids hammering yfinance with repeated full-market refreshes.
"""

import pandas as pd
import os
import pickle
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from engine import fetch_data, DETECTOR

CACHE_DIR = os.path.join(os.path.dirname(__file__), "outputs", "scan_cache")


def _load_tickers(market_key: str) -> list:
    """Load full ticker list for the given market from CSV, with fallback."""
    base = os.path.dirname(__file__)
    if market_key == "IN":
        csv_path = os.path.join(base, "nifty500.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            if "Symbol" in df.columns:
                symbols = df["Symbol"].dropna().astype(str).str.strip().str.upper().unique()
                return [f"{s}.NS" if not s.endswith(".NS") else s for s in symbols]
        return [
            "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
            "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "BAJFINANCE.NS",
        ]
    elif market_key == "US":
        csv_path = os.path.join(base, "sp500_constituents.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            if "Symbol" in df.columns:
                return df["Symbol"].dropna().astype(str).str.strip().tolist()
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "JNJ"]
    return []


def _today_cache_path(market_key: str) -> str:
    date_str = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{market_key}_{date_str}.pkl"), date_str


def generate_cache_for_market(market_key="IN", force=False):
    """
    Generate today's scan cache for a market.

    - If today's cache already exists and force=False, return cached count immediately.
    - Historical caches are never overwritten or deleted.
    - Uses ThreadPoolExecutor with max_workers=6 to avoid overwhelming yfinance.
    """
    out_path, date_str = _today_cache_path(market_key)

    # Skip if today's cache already exists and not forced
    if os.path.exists(out_path) and not force:
        try:
            with open(out_path, "rb") as f:
                existing = pickle.load(f)
            print(f"[SKIP] {market_key} cache for {date_str} already exists ({len(existing)} tickers). Use force=True to regenerate.")
            return len(existing), date_str
        except Exception:
            pass  # corrupted — fall through to regenerate

    # Always do an incremental OHLCV refresh before generating the scanner cache
    # Fetch last 5 days of data to ensure we have latest data
    from ohlcv_store import bulk_download
    tickers = _load_tickers(market_key)
    print(f"[PRE-REFRESH] Updating OHLCV data for {len(tickers)} tickers in {market_key} (last 5 days)...")
    
    # Force update last 5 days for all tickers
    from ohlcv_store import download_ticker
    from datetime import timedelta
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def force_update_5days(ticker):
        try:
            from ohlcv_store import _parquet_path, fetch_local
            import yfinance as yf
            import pandas as pd
            
            path = _parquet_path(ticker, market_key)
            existing = fetch_local(ticker, market_key)
            
            if existing is not None:
                # Get last 5 days
                end_date = pd.Timestamp.now()
                start_date = end_date - timedelta(days=5)
                
                import requests
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
                })
                
                new_data = yf.download(yf_ticker, start=start_date.strftime("%Y-%m-%d"), 
                                      end=end_date.strftime("%Y-%m-%d"), progress=False, auto_adjust=True, session=session)
                
                if new_data is not None and not new_data.empty:
                    if isinstance(new_data.columns, pd.MultiIndex):
                        new_data.columns = new_data.columns.get_level_values(0)
                    new_data.columns = [str(c).title() for c in new_data.columns]
                    new_data = new_data[["Open", "High", "Low", "Close", "Volume"]]
                    
                    combined = pd.concat([existing, new_data])
                    combined = combined[~combined.index.duplicated(keep="last")]
                    combined = combined.sort_index()
                    combined.to_parquet(path)
                    return True
            return True
        except Exception as e:
            return False
    
    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = {ex.submit(force_update_5days, t): t for t in tickers}
        done_count = 0
        for i, fut in enumerate(as_completed(futures)):
            try:
                if fut.result():
                    done_count += 1
            except:
                pass
            if (i + 1) % 100 == 0:
                print(f"  OHLCV update: {i+1}/{len(tickers)}")
    
    print(f"[PRE-REFRESH] OHLCV update complete for {done_count} tickers")

    print(f"[START] Generating cache for {len(tickers)} tickers in {market_key} market ({date_str})...")
    start_time = time.time()

    def process_ticker(ticker):
        try:
            data_df = fetch_data(ticker, period="2y", market=market_key)
            if data_df is not None and not data_df.empty and len(data_df) >= 60:
                res = DETECTOR.analyse(data_df, ticker=ticker)
                if "df" in res:
                    del res["df"]
                return res
        except Exception as e:
            print(f"  [FAIL] {ticker}: {e}")
        return None

    results = []
    # max_workers=6 keeps yfinance request rate reasonable
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(process_ticker, t): t for t in tickers}
        for i, future in enumerate(as_completed(futures)):
            try:
                r = future.result()
                if r:
                    results.append(r)
            except Exception:
                pass
            if (i + 1) % 50 == 0 or (i + 1) == len(tickers):
                print(f"  {i+1}/{len(tickers)} processed — {len(results)} valid so far")

    with open(out_path, "wb") as f:
        pickle.dump(results, f)

    elapsed = time.time() - start_time
    print(f"[OK] {market_key} cache saved: {len(results)} tickers → {out_path} ({elapsed:.1f}s)")
    return len(results), date_str

if __name__ == "__main__":
    # Refresh both markets
    print("=" * 60)
    print("REFRESHING SCAN DATA FOR ALL MARKETS")
    print("=" * 60)
    
    # India market
    print("\n[1/2] India (NSE) Market")
    in_count, in_date = generate_cache_for_market("IN")
    
    # US market  
    print("\n[2/2] US Market")
    us_count, us_date = generate_cache_for_market("US")
    
    print("\n" + "=" * 60)
    print(f"REFRESH COMPLETE:")
    print(f"  - India (IN): {in_count} stocks scanned (through {in_date})")
    print(f"  - US: {us_count} stocks scanned (through {us_date})")
    print("=" * 60)

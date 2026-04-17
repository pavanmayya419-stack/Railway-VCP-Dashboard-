import os
import pandas as pd
import pickle
from datetime import datetime, timedelta
from engine import DETECTOR, fetch_data
from data_manager import SCAN_CACHE_DIR

def backfill(market="IN", days=15):
    os.makedirs(SCAN_CACHE_DIR, exist_ok=True)
    
    # Load tickers
    if market == "IN":
        csv_path = "fyers_tickers.csv"
        if not os.path.exists(csv_path): csv_path = "nifty500.csv"
        df_tickers = pd.read_csv(csv_path)
        tickers = [f"{s}.NS" if not s.endswith(".NS") else s for s in df_tickers["Symbol"].tolist()]
    else:
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK-B", "UNH", "JNJ", "V", "PG", "MA", "HD", "CVX", "LLY", "ABBV", "PEP", "BAC", "KO"]
        # In a real scenario we'd use S&P 500 list, but for backfill let's do a meaningful subset or use existing if any.
        # Let's try to get a larger list if available.
    
    # Last X trading days
    today = datetime.now()
    dates = []
    curr = today
    while len(dates) < days:
        if curr.weekday() < 5: # Monday to Friday
            dates.append(curr.strftime("%Y-%m-%d"))
        curr -= timedelta(days=1)
        
    print(f"\n🚀 Backfilling {market} for dates: {dates}")
    
    for date_str in dates:
        out_path = os.path.join(SCAN_CACHE_DIR, f"{market}_{date_str}.pkl")
        
        print(f"Processing {market} {date_str}...")
        results = []
        for i, ticker in enumerate(tickers):
            try:
                df = fetch_data(ticker, market=market)
                if df is not None and not df.empty:
                    df_historical = df[df.index <= pd.Timestamp(date_str)]
                    if len(df_historical) >= 100:
                        res = DETECTOR.analyse(df_historical, ticker=ticker)
                        if "df" in res: del res["df"]
                        results.append(res)
            except: pass
            
            if (i+1) % 100 == 0:
                print(f"  {i+1}/{len(tickers)} done...")
                
        with open(out_path, "wb") as f:
            pickle.dump(results, f)
        print(f"✅ Saved {len(results)} results for {date_str}")

if __name__ == "__main__":
    backfill("IN", days=10)
    # For US we just do a few to keep it fast, or the user can run it themselves.
    backfill("US", days=10) 

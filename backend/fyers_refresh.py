import os
import time
import pandas as pd
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fyers_apiv3 import fyersModel

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

load_dotenv()

APP_ID = os.getenv("FYERS_APP_ID")
TOKEN_FILE = os.getenv("FYERS_TOKEN_FILE", "fyers_token.txt")
OHLCV_DIR = os.path.join(os.getcwd(), "outputs", "ohlcv", "IN")

def get_fyers():
    if not os.path.exists(TOKEN_FILE):
        raise Exception(f"Token file '{TOKEN_FILE}' not found. Please run fyers_login.py.")
    with open(TOKEN_FILE, "r") as f:
        token = f.read().strip()
    return fyersModel.FyersModel(client_id=APP_ID, token=token, is_async=False, log_path="")

def fetch_one_fyers(fyers, ticker, days=365):
    # Fyers symbol mapping:
    # 1. Strip .NS if present
    base = ticker.replace(".NS", "")
    # 2. Replace & with _
    base = base.replace("&", "_")
    
    # Fyers format: NSE:SYMBOL-EQ
    fyers_symbol = f"NSE:{base}-EQ"
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    data = {
        "symbol": fyers_symbol,
        "resolution": "D",
        "date_format": "1",
        "range_from": start_date.strftime("%Y-%m-%d"),
        "range_to": end_date.strftime("%Y-%m-%d"),
        "cont_flag": "1"
    }
    
    try:
        res = fyers.history(data=data)
        if res.get("s") == "ok" and res.get("candles"):
            df = pd.DataFrame(res["candles"], columns=["timestamp", "Open", "High", "Low", "Close", "Volume"])
            df["Date"] = pd.to_datetime(df["timestamp"], unit="s")
            df.set_index("Date", inplace=True)
            df.drop(columns=["timestamp"], inplace=True)
            df.sort_index(inplace=True)
            return df
        else:
            msg = res.get("message", "Unknown error")
            log.warning(f"Fyers error for {ticker} ({fyers_symbol}): {msg}")
    except Exception as e:
        log.error(f"Exception fetching {ticker}: {e}")
    return None

def main():
    os.makedirs(OHLCV_DIR, exist_ok=True)
    fyers = get_fyers()
    
    # Load Tickers
    csv_path = "fyers_tickers.csv"
    if not os.path.exists(csv_path):
        log.error("fyers_tickers.csv not found")
        return
        
    nifty = pd.read_csv(csv_path)
    tickers = nifty["Symbol"].tolist()
    
    print(f"Refreshing {len(tickers)} Indian tickers from Fyers...")
    
    done = 0
    failed = 0
    
    for ticker in tickers:
        safe_ticker = ticker.replace(".", "_") + "_NS"
        path = os.path.join(OHLCV_DIR, f"{safe_ticker}.parquet")
        
        if os.path.exists(path):
            done += 1
            print(f"Skipping {ticker} (already exists)")
            continue

        df = fetch_one_fyers(fyers, ticker)
        if df is not None:
            df.to_parquet(path)
            done += 1
            if done % 20 == 0:
                print(f"Progress: {done}/{len(tickers)} done...")
        else:
            # Try without -EQ for indices or special cases if needed?
            # But mostly we want stocks
            log.warning(f"Failed to fetch {ticker}")
            failed += 1
        
        # Rate limit: ~10 requests per second
        time.sleep(0.1)

    print(f"\nCompleted! Success={done}, Failed={failed}")
    print(f"Data saved to {OHLCV_DIR}")

if __name__ == "__main__":
    main()

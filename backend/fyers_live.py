import os
import logging
import pandas as pd
from datetime import datetime
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv

log = logging.getLogger(__name__)

load_dotenv()

APP_ID = os.getenv("FYERS_APP_ID")
TOKEN_FILE = os.getenv("FYERS_TOKEN_FILE", "fyers_token.txt")

def get_token_path():
    if os.path.exists(TOKEN_FILE):
        return TOKEN_FILE
    # Try looking in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    alt_path = os.path.join(script_dir, TOKEN_FILE)
    if os.path.exists(alt_path):
        return alt_path
    # Try looking specifically in 'backend' if we are in root
    backend_path = os.path.join(os.getcwd(), "backend", TOKEN_FILE)
    if os.path.exists(backend_path):
        return backend_path
    return None

_fyers_instance = None

def get_fyers():
    global _fyers_instance
    if _fyers_instance:
        return _fyers_instance
        
    token_paths = [
        "fyers_token.txt",
        "backend/fyers_token.txt",
        os.path.join(os.path.dirname(__file__), "fyers_token.txt"),
        os.path.join(os.getcwd(), "fyers_token.txt"),
        os.path.join(os.getcwd(), "backend", "fyers_token.txt"),
    ]
    
    token_file = None
    for p in token_paths:
        if os.path.exists(p):
            token_file = p
            log.info(f"Fyers token found at: {p}")
            break
            
    if not token_file:
        log.error(f"Fyers token not found. searched: {token_paths}")
        return None
        
    try:
        with open(token_file, "r") as f:
            token = f.read().strip()
        _fyers_instance = fyersModel.FyersModel(client_id=APP_ID, token=token, is_async=False, log_path="")
        return _fyers_instance
    except Exception as e:
        log.error(f"Error initializing Fyers: {e}")
        return None

def get_live_quotes(tickers: list[str]) -> dict:
    """
    Fetch live quotes for a list of tickers from Fyers.
    tickers: list of symbols like ['RELIANCE', 'TCS']
    Returns: dict mapping 'NSE:SYMBOL-EQ' -> quote data
    """
    fyers = get_fyers()
    if not fyers:
        log.warning("Fyers not initialized (no token).")
        return {}

    # Map tickers to Fyers symbols
    # NSE:RELIANCE-EQ
    fyers_symbols = []
    symbol_map = {}
    for t in tickers:
        base = t.replace(".NS", "").replace("&", "_")
        fs = f"NSE:{base}-EQ"
        fyers_symbols.append(fs)
        symbol_map[fs] = t

    results = {}
    # Fyers quotes API allows up to 50 symbols per request
    chunk_size = 50
    import time
    for i in range(0, len(fyers_symbols), chunk_size):
        chunk = fyers_symbols[i:i + chunk_size]
        try:
            res = fyers.quotes(data={"symbols": ",".join(chunk)})
            if res.get("s") == "ok" and res.get("d"):
                for quote in res["d"]:
                    if quote.get("s") == "ok":
                        results[quote['n']] = quote['v']
                    else:
                        log.warning(f"Quote error for symbol {quote.get('n')}: {quote.get('errmsg')}")
        except Exception as e:
            log.error(f"Error fetching quotes chunk: {e}")
        time.sleep(0.2) # Rate limiting

    log.info(f"Fetched {len(results)} live quotes from Fyers.")
    return results

def get_live_ohlcv(ticker: str, market: str, quote: dict = None) -> pd.DataFrame | None:
    """
    Fetch local OHLCV and append today's quote data if available.
    Ensures a smooth transition from historical to live data.
    """
    from ohlcv_store import fetch_local
    df = fetch_local(ticker, market)
    
    if df is None or df.empty:
        # Fallback to yfinance if local cache is missing for some reason
        try:
            import yfinance as yf
            df = yf.download(ticker, period="2y", progress=False, auto_adjust=True)
            if df is not None and len(df) >= 60:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df.columns = [str(c).title() for c in df.columns]
                df = df[["Open", "High", "Low", "Close", "Volume"]]
            else:
                return None
        except:
            return None
    
    if quote:
        lp = quote.get("lp", 0)
        if lp <= 0: return df # invalid quote
        
        today = pd.Timestamp.now().normalize()
        
        # Calculate daily OHLC from quote if available, else fallback to lp
        o = quote.get("open_price") or lp
        h = quote.get("high_price") or lp
        l = quote.get("low_price") or lp
        v = quote.get("volume") or 0
        
        if df.index.max() < today:
            # Append today's row
            new_row = pd.DataFrame({
                "Open": [float(o)],
                "High": [float(h)],
                "Low": [float(l)],
                "Close": [float(lp)],
                "Volume": [int(v)]
            }, index=[today])
            df = pd.concat([df, new_row])
            # Ensure index is unique and sorted
            df = df[~df.index.duplicated(keep='last')]
            df = df.sort_index()
        else:
            # Update today's existing row
            last_idx = df.index.max()
            try:
                df.at[last_idx, "Close"] = float(lp)
                df.at[last_idx, "High"]  = float(max(df.at[last_idx, "High"], float(h)))
                df.at[last_idx, "Low"]   = float(min(df.at[last_idx, "Low"], float(l)))
                df.at[last_idx, "Volume"] = int(v) if v > 0 else df.at[last_idx, "Volume"]
            except Exception as e:
                log.warning(f"Error updating today row for {ticker}: {e}")
            
    return df

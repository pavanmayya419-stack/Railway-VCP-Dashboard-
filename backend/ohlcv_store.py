"""
Local OHLCV parquet store.

Layout:
  outputs/ohlcv/<MARKET>/<TICKER>.parquet

Strategy:
- Initial download: 2 years of daily OHLCV via yfinance
- Incremental update: only fetch rows since the last stored date
- fetch_local(ticker, market) → DataFrame or None (used by engine.py)
- bulk_download(market, tickers, workers=6, force=False) → (done, skipped, failed)
"""

import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
import requests

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
})

log = logging.getLogger(__name__)

OHLCV_DIR = os.path.join(os.path.dirname(__file__), "outputs", "ohlcv")
REQUIRED_COLS = ["Open", "High", "Low", "Close", "Volume"]
MIN_ROWS = 60
FULL_PERIOD = "2y"


# ─── Path helpers ─────────────────────────────────────────────────────────────

def _market_dir(market: str) -> str:
    d = os.path.join(OHLCV_DIR, market.upper())
    os.makedirs(d, exist_ok=True)
    return d


def _parquet_path(ticker: str, market: str) -> str:
    safe = ticker.replace(".", "_").replace("/", "_").replace("^", "_")
    return os.path.join(_market_dir(market), f"{safe}.parquet")


# ─── Single ticker I/O ────────────────────────────────────────────────────────

def fetch_local(ticker: str, market: str) -> pd.DataFrame | None:
    """Read ticker from local parquet. Returns None if missing/invalid."""
    path = _parquet_path(ticker, market)
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_parquet(path)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        missing = [c for c in REQUIRED_COLS if c not in df.columns]
        if missing or len(df) < MIN_ROWS:
            return None
        return df[REQUIRED_COLS]
    except Exception as e:
        log.warning(f"[ohlcv] read error {ticker}: {e}")
        return None


def _download_from_yf(ticker: str, period: str = FULL_PERIOD) -> pd.DataFrame | None:
    """Download OHLCV from yfinance. Returns cleaned DataFrame or None."""
    try:
        raw = yf.download(ticker, period=period, progress=False, auto_adjust=True, session=session)
        if raw is None or raw.empty:
            return None
        # Flatten MultiIndex columns (yfinance >=0.2 returns these for single tickers too)
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        # Normalise column names to title-case
        raw.columns = [str(c).strip().title() for c in raw.columns]
        # Remove duplicate columns (keep first occurrence)
        raw = raw.loc[:, ~raw.columns.duplicated(keep="first")]
        available = [c for c in REQUIRED_COLS if c in raw.columns]
        if len(available) < 5 or len(raw) < MIN_ROWS:
            return None
        raw = raw[REQUIRED_COLS].copy()
        raw.index = pd.to_datetime(raw.index)
        raw = raw.sort_index()
        raw = raw.dropna()
        return raw
    except Exception as e:
        log.warning(f"[ohlcv] yf download error {ticker}: {e}")
        return None


def _download_from_fyers(ticker: str, days: int = 730) -> pd.DataFrame | None:
    """Download OHLCV from Fyers API. Returns cleaned DataFrame or None."""
    try:
        from fyers_apiv3 import fyersModel
        from dotenv import load_dotenv
        load_dotenv()
        
        app_id = os.getenv("FYERS_APP_ID")
        token_file = os.getenv("FYERS_TOKEN_FILE", "fyers_token.txt")
        
        if not os.path.exists(token_file):
            return None
            
        with open(token_file, "r") as f:
            token = f.read().strip()
            
        fyers = fyersModel.FyersModel(client_id=app_id, token=token, is_async=False, log_path="")
        
        # Format symbol for Fyers: NSE:RELIANCE-EQ
        base = ticker.replace(".NS", "")
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
        
        res = fyers.history(data=data)
        if res.get("s") == "ok" and res.get("candles"):
            df = pd.DataFrame(res["candles"], columns=["timestamp", "Open", "High", "Low", "Close", "Volume"])
            df.index = pd.to_datetime(df["timestamp"], unit="s")
            df = df.sort_index()
            # Drop duplicates and columns
            df = df[~df.index.duplicated(keep='last')]
            return df[REQUIRED_COLS]
    except Exception as e:
        log.warning(f"[ohlcv] fyers download error {ticker}: {e}")
    return None


def download_ticker(ticker: str, market: str, force: bool = False) -> bool:
    """
    Full history download for a ticker.
    If parquet already exists and force=False, skip.
    Returns True on success.
    """
    path = _parquet_path(ticker, market)
    if os.path.exists(path) and not force:
        return True  # already have it

    df = None
    # Use Fyers for Indian market if available
    if market.upper() in ["IN", "INDIA", "INDIA (NSE)"]:
        df = _download_from_fyers(ticker)
        
    # Fallback to yfinance
    if df is None:
        df = _download_from_yf(ticker, FULL_PERIOD)
        
    if df is None:
        return False
        
    try:
        df.to_parquet(path)
        return True
    except Exception as e:
        log.warning(f"[ohlcv] save error {ticker}: {e}")
        return False


def update_ticker(ticker: str, market: str) -> bool:
    """
    Incremental update: only fetch rows newer than the last stored date.
    If no local file exists, does a full download instead.
    Returns True on success.
    """
    path = _parquet_path(ticker, market)
    if not os.path.exists(path):
        return download_ticker(ticker, market)

    existing = fetch_local(ticker, market)
    if existing is None:
        return download_ticker(ticker, market, force=True)

    last_date = existing.index.max()
    today = pd.Timestamp.now().normalize()

    # Already up to date (last row is today or yesterday for non-trading days)
    if (today - last_date).days <= 1:
        return True

    # Try Fyers for Indian market
    if market.upper() in ["IN", "INDIA", "INDIA (NSE)"]:
        # Fyers history is usually enough for incremental too
        new_df = _download_from_fyers(ticker, days=7)
        if new_df is not None and not new_df.empty:
            combined = pd.concat([existing, new_df])
            combined = combined[~combined.index.duplicated(keep="last")]
            combined = combined.sort_index()
            combined.to_parquet(path)
            return True

    # Fallback to yfinance delta
    start_str = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
    end_str = today.strftime("%Y-%m-%d")

    try:
        new_raw = yf.download(
            ticker,
            period=None,
            start=start_str,
            end=end_str,
            progress=False,
            auto_adjust=True,
            session=session,
        )
        if new_raw is None or new_raw.empty:
            return True  # no new data (weekend/holiday) — not a failure
        if isinstance(new_raw.columns, pd.MultiIndex):
            new_raw.columns = new_raw.columns.get_level_values(0)
        new_raw.columns = [str(c).strip().title() for c in new_raw.columns]
        new_raw = new_raw.loc[:, ~new_raw.columns.duplicated(keep="first")]
        available = [c for c in REQUIRED_COLS if c in new_raw.columns]
        if len(available) < 5:
            return True
        new_raw = new_raw[REQUIRED_COLS].copy()
        new_raw.index = pd.to_datetime(new_raw.index)

        combined = pd.concat([existing, new_raw])
        combined = combined[~combined.index.duplicated(keep="last")]
        combined = combined.sort_index()
        combined.to_parquet(path)
        log.info(f"[ohlcv] updated {ticker}: +{len(new_raw)} rows → {len(combined)} total")
        return True
    except Exception as e:
        log.warning(f"[ohlcv] update error {ticker}: {e}")
        return False


# ─── Bulk operations ──────────────────────────────────────────────────────────

def _store_status(market: str, tickers: list[str]) -> dict:
    """Return per-market store summary."""
    present = []
    missing = []
    stale = []  # last row > 2 trading days old
    today = pd.Timestamp.now().normalize()

    for t in tickers:
        df = fetch_local(t, market)
        if df is None:
            missing.append(t)
        else:
            last = df.index.max()
            if (today - last).days > 3:
                stale.append(t)
            else:
                present.append(t)

    return {
        "market": market,
        "total": len(tickers),
        "present": len(present),
        "stale": len(stale),
        "missing": len(missing),
        "coverage_pct": round(100 * (len(present) + len(stale)) / max(1, len(tickers)), 1),
        "missing_tickers": missing[:20],  # first 20 for display
    }


def bulk_download(
    market: str,
    tickers: list[str],
    workers: int = 6,
    force: bool = False,
    incremental: bool = False,
) -> dict:
    """
    Download or update OHLCV for all tickers in a market.

    incremental=True  → only fetch delta rows (for daily refresh)
    incremental=False → full 2y download, skip existing unless force=True
    force=True        → re-download everything from scratch

    Returns summary dict.
    """
    done = 0
    skipped = 0
    failed = 0
    total = len(tickers)

    fn = update_ticker if incremental else download_ticker

    def _worker(t):
        if market.upper() in ["IN", "INDIA", "INDIA (NSE)"]:
            time.sleep(0.2)  # More conservative for Fyers
        else:
            time.sleep(0.05)  
        if incremental:
            ok = update_ticker(t, market)
        else:
            ok = download_ticker(t, market, force=force)
        return ok

    # Limit workers for Indian market to avoid 429
    actual_workers = workers
    if market.upper() in ["IN", "INDIA", "INDIA (NSE)"]:
        actual_workers = min(workers, 2)

    with ThreadPoolExecutor(max_workers=actual_workers) as ex:
        futures = {ex.submit(_worker, t): t for t in tickers}
        for i, fut in enumerate(as_completed(futures)):
            t = futures[fut]
            try:
                ok = fut.result()
                if ok:
                    done += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
            if (i + 1) % 100 == 0 or (i + 1) == total:
                log.info(f"[ohlcv] {market} {i+1}/{total} — done={done} failed={failed}")

    return {
        "market": market,
        "total": total,
        "done": done,
        "failed": failed,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }

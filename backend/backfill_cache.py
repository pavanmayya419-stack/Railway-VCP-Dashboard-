"""
Backfill historical scan PKL caches using local parquet OHLCV store.

Strategy:
- Split dates into N equal chunks (one per CPU core).
- Each worker process loads ALL parquet files ONCE, then processes its chunk.
- Zero redundant disk reads. All cores saturated.

Usage:
    python backfill_cache.py              # both markets
    python backfill_cache.py US           # US only
    python backfill_cache.py IN           # India only
"""

import os
import sys
import pickle
import time
from multiprocessing import Pool, cpu_count

import pandas as pd

MIN_TICKERS = 490
WORKERS = cpu_count()


def _chunk_worker(args):
    """
    Subprocess: load ALL parquet files once, then process every date in chunk.
    args = (market_key, dates_chunk, ticker_paths, cache_dir)
    """
    import os, pickle, sys
    import pandas as pd

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from engine import DETECTOR

    market_key, dates_chunk, ticker_paths, cache_dir = args

    # Load all parquet files into memory ONCE for this process
    ohlcv = {}
    for ticker, path in ticker_paths:
        try:
            df = pd.read_parquet(path)
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            if len(df) >= 60:
                ohlcv[ticker] = df
        except Exception:
            pass

    results_summary = []
    for date_str in dates_chunk:
        cutoff = pd.Timestamp(date_str)
        results = []
        for ticker, df in ohlcv.items():
            try:
                sliced = df[df.index <= cutoff]
                if len(sliced) < 60:
                    continue
                r = DETECTOR.analyse(sliced, ticker=ticker)
                if r:
                    r.pop("df", None)
                    results.append(r)
            except Exception:
                pass
        pkl_path = os.path.join(cache_dir, f"{market_key}_{date_str}.pkl")
        with open(pkl_path, "wb") as f:
            pickle.dump(results, f)
        results_summary.append((date_str, len(results)))

    return results_summary


def backfill_market(market_key: str):
    from data_manager import list_cached_dates, SCAN_CACHE_DIR
    from ohlcv_store import _parquet_path, fetch_local
    from refresh_data import _load_tickers

    tickers = _load_tickers(market_key)
    all_dates = sorted(list_cached_dates(market_key))
    print(f"\n[{market_key}] {len(all_dates)} dates | {len(tickers)} tickers | {WORKERS} cores")

    # Build (ticker, path) list — no reading yet
    ticker_paths = []
    for t in tickers:
        path = _parquet_path(t, market_key)
        if os.path.exists(path):
            ticker_paths.append((t, path))
    print(f"[{market_key}] {len(ticker_paths)} parquet files on disk")

    # Parquet data window — sample one file
    sample = fetch_local(ticker_paths[0][0], market_key)
    parquet_start = sample.index.min() if sample is not None else pd.Timestamp("2024-04-01")
    print(f"[{market_key}] Parquet starts: {parquet_start.date()}")

    # Find dates needing backfill
    dates_to_backfill = []
    for date_str in all_dates:
        if pd.Timestamp(date_str) < parquet_start:
            continue
        pkl = os.path.join(SCAN_CACHE_DIR, f"{market_key}_{date_str}.pkl")
        try:
            with open(pkl, "rb") as f:
                n = len(pickle.load(f))
            if n < MIN_TICKERS:
                dates_to_backfill.append(date_str)
        except Exception:
            dates_to_backfill.append(date_str)

    total = len(dates_to_backfill)
    print(f"[{market_key}] {total} dates to backfill")
    if not total:
        print(f"[{market_key}] Nothing to do.")
        return

    # Split dates into equal chunks — one chunk per core
    chunk_size = max(1, (total + WORKERS - 1) // WORKERS)
    chunks = [dates_to_backfill[i:i+chunk_size] for i in range(0, total, chunk_size)]
    print(f"[{market_key}] {len(chunks)} chunks x ~{chunk_size} dates each -> launching {len(chunks)} processes")

    tasks = [(market_key, chunk, ticker_paths, SCAN_CACHE_DIR) for chunk in chunks]

    t_start = time.time()
    done = 0

    with Pool(processes=len(chunks)) as pool:
        for chunk_results in pool.imap_unordered(_chunk_worker, tasks):
            for date_str, count in chunk_results:
                done += 1
                elapsed = time.time() - t_start
                rate = done / elapsed
                eta = (total - done) / rate if rate > 0 else 0
                print(f"  [{done}/{total}] {date_str} -> {count} tickers | {rate:.1f}/s | ETA {eta/60:.1f}min")

    print(f"[{market_key}] Done in {(time.time()-t_start)/60:.1f}min")


if __name__ == "__main__":
    markets = sys.argv[1:] if len(sys.argv) > 1 else ["US", "IN"]
    t0 = time.time()
    for market in markets:
        backfill_market(market.upper())
    print(f"\nAll done in {(time.time()-t0)/60:.1f}min")

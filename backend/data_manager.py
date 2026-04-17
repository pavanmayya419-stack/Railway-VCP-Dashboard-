import os
import pickle
from datetime import datetime

SCAN_CACHE_DIR = os.path.join(os.path.dirname(__file__), "outputs", "scan_cache")

def _market_prefixes(market: str) -> list:
    """Return all known file prefixes for a given market key."""
    prefixes = [market]
    # Map short keys to legacy long names
    legacy = {
        "IN": ["India (NSE)", "India"],
        "US": ["US"],
    }
    prefixes += legacy.get(market, [])
    return prefixes

def list_cached_dates(market: str) -> list:
    """Return sorted list of dates (strings) that have cached scan results for the given market."""
    if not os.path.exists(SCAN_CACHE_DIR):
        return []
    
    prefixes = _market_prefixes(market)
    dates = []
    seen = set()
    for fname in os.listdir(SCAN_CACHE_DIR):
        if not fname.endswith(".pkl"):
            continue
        for prefix in prefixes:
            if fname.startswith(prefix + "_"):
                date_str = fname[len(prefix)+1:-4]
                if date_str not in seen:
                    dates.append(date_str)
                    seen.add(date_str)
                break
            
    # Sort descending (newest first)
    dates.sort(reverse=True)
    return dates

def load_scan_cache(market: str, date_str: str) -> list:
    """Load previously persisted compact scan results for a given date."""
    prefixes = _market_prefixes(market)
    for prefix in prefixes:
        path = os.path.join(SCAN_CACHE_DIR, f"{prefix}_{date_str}.pkl")
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    results = pickle.load(f)
                # Remove any non-serializable objects (like DataFrame if it mistakenly exists)
                for r in results:
                    if "df" in r:
                        del r["df"]
                return results
            except Exception:
                continue
    return []

import json
import os
import threading
from typing import Dict

import yfinance as yf

CACHE_PATH = os.path.join(os.path.dirname(__file__), "outputs", "ticker_metadata_cache.json")
_cache_lock = threading.Lock()
_metadata_cache: Dict[str, Dict[str, str]] = {}
_cache_loaded = False

SECTOR_ALIASES = {
    "information technology": "Technology",
    "technology": "Technology",
    "tech": "Technology",
    "health care": "Healthcare",
    "healthcare": "Healthcare",
    "consumer discretionary": "Consumer Discretionary",
    "consumer cyclical": "Consumer Discretionary",
    "consumer staples": "Consumer Staples",
    "consumer defensive": "Consumer Staples",
    "communication services": "Communication Services",
    "telecommunications services": "Communication Services",
    "energy": "Energy",
    "industrials": "Industrials",
    "industrial goods": "Industrials",
    "materials": "Materials",
    "basic materials": "Materials",
    "financials": "Financials",
    "financial services": "Financials",
    "real estate": "Real Estate",
    "utilities": "Utilities",
}

CAP_BUCKETS_USD = [
    (200_000_000_000, "Mega Cap"),
    (10_000_000_000, "Large Cap"),
    (2_000_000_000, "Mid Cap"),
    (300_000_000, "Small Cap"),
    (0, "Micro Cap"),
]

# For Indian market (INR), values are ~84x larger
CAP_BUCKETS_INR = [
    (15_000_000_000_000, "Mega Cap"),  # ~15 Lakh Cr
    (500_000_000_000, "Large Cap"),    # ~50,000 Cr
    (150_000_000_000, "Mid Cap"),      # ~15,000 Cr
    (50_000_000_000, "Small Cap"),     # ~5,000 Cr
    (0, "Micro Cap"),
]


def _ensure_cache() -> None:
    global _cache_loaded
    if _cache_loaded:
        return
    
    # 1. Load local cache if exists
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                _metadata_cache.update(json.load(f))
        except Exception:
            pass
            
    # 2. Seed from OneDrive if available and cache is empty/incomplete
    onedrive_sectors = r"D:\OneDrive\MAYYA CAPITAL PARTNERS\Trading Strategies\TradingKnowledgeBase\ticker_sectors.json"
    if os.path.exists(onedrive_sectors):
        try:
            with open(onedrive_sectors, "r") as f:
                seeds = json.load(f)
                for t, s in seeds.items():
                    # We store with .NS for consistency in cache key if needed, or just upper base
                    # Let's check existing cache keys
                    if t not in _metadata_cache:
                        _metadata_cache[t] = {"sector": _normalize_sector(s), "cap": "Unknown"}
                    elif _metadata_cache[t].get("sector") == "Unknown":
                        _metadata_cache[t]["sector"] = _normalize_sector(s)
        except Exception:
            pass
            
    _cache_loaded = True


def _persist_cache() -> None:
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    tmp_path = CACHE_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(_metadata_cache, f)
    os.replace(tmp_path, CACHE_PATH)


def _normalize_sector(raw: str | None) -> str:
    if not raw:
        return "Unknown"
    key = raw.strip().lower()
    if key in SECTOR_ALIASES:
        return SECTOR_ALIASES[key]
    for alias, canonical in SECTOR_ALIASES.items():
        if alias in key:
            return canonical
    return raw.strip()


def _cap_bucket(value: int | float | None, market: str) -> str:
    if not value or value <= 0:
        return "Unknown"
        
    buckets = CAP_BUCKETS_INR if market.upper() in ["IN", "INDIA", "INDIA (NSE)"] else CAP_BUCKETS_USD
    
    for threshold, label in buckets:
        if value >= threshold:
            return label
    return "Micro Cap"


def _yfinance_symbol(ticker: str, market: str) -> str:
    if market.upper() in ["IN", "INDIA", "INDIA (NSE)"] and not ticker.endswith(".NS"):
        return f"{ticker}.NS"
    return ticker.replace("-", ".")


def get_metadata(ticker: str, market: str) -> Dict[str, str]:
    """Return cached name, sector and cap bucket for a ticker, fetching via yfinance if needed."""
    if not ticker:
        return {"name": "Unknown", "sector": "Unknown", "cap": "Unknown"}

    # Use base symbol as key in cache to be consistent
    key = ticker.split(".")[0].upper()
    _ensure_cache()

    with _cache_lock:
        if key in _metadata_cache:
            m = _metadata_cache[key]
            # If we have name and sector, return
            if m.get("name") and m.get("sector") != "Unknown" and m.get("cap") != "Unknown":
                return m

    yf_symbol = _yfinance_symbol(ticker, market)
    sector = "Unknown"
    company_name = key
    market_cap = None
    try:
        # Avoid full ticker object for performance
        info = yf.Ticker(yf_symbol).info
        company_name = info.get("longName") or info.get("shortName") or key
        sector = info.get("sector") or info.get("industry") or "Unknown"
        market_cap = info.get("marketCap")
    except Exception:
        pass

    normalized_sector = _normalize_sector(sector)
    cap_bucket = _cap_bucket(market_cap, market)

    metadata = {"name": company_name, "sector": normalized_sector, "cap": cap_bucket}

    with _cache_lock:
        # Merge if partially exists
        if key in _metadata_cache:
            _metadata_cache[key].update(metadata)
        else:
            _metadata_cache[key] = metadata
            
        try:
            _persist_cache()
        except Exception:
            pass

    return metadata

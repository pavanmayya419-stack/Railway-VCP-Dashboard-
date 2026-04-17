import os
import logging
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

def get_live_ohlcv(ticker: str, market: str = "US") -> pd.DataFrame | None:
    """
    Fetch OHLCV data using yfinance.
    For US stocks: use ticker as-is (e.g., AAPL, MSFT)
    For Indian stocks: append .NS (e.g., RELIANCE.NS)
    """
    try:
        # Convert ticker format based on market
        if market == "IN" and not ticker.endswith(".NS"):
            yf_ticker = f"{ticker}.NS"
        else:
            yf_ticker = ticker
            
        df = yf.download(yf_ticker, period="2y", progress=False, auto_adjust=True)
        
        if df is None or df.empty or len(df) < 60:
            log.warning(f"Insufficient data for {ticker}")
            return None
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df.columns = [str(c).title() for c in df.columns]
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        
        return df
    except Exception as e:
        log.error(f"Error fetching data for {ticker}: {e}")
        return None


def get_live_quote(ticker: str, market: str = "US") -> dict | None:
    """
    Fetch live quote for a ticker using yfinance.
    Returns dict with lp (last price), open, high, low, volume
    """
    try:
        if market == "IN" and not ticker.endswith(".NS"):
            yf_ticker = f"{ticker}.NS"
        else:
            yf_ticker = ticker
            
        stock = yf.Ticker(yf_ticker)
        info = stock.info
        
        return {
            "lp": info.get("currentPrice", 0) or info.get("regularMarketPrice", 0) or 0,
            "open_price": info.get("open", 0),
            "high_price": info.get("dayHigh", 0),
            "low_price": info.get("dayLow", 0),
            "volume": info.get("volume", 0) or info.get("regularMarketVolume", 0) or 0,
        }
    except Exception as e:
        log.error(f"Error fetching quote for {ticker}: {e}")
        return None


def get_live_quotes(tickers: list[str], market: str = "US") -> dict:
    """
    Fetch live quotes for a list of tickers.
    Returns: dict mapping ticker -> quote data
    """
    results = {}
    
    for ticker in tickers:
        try:
            quote = get_live_quote(ticker, market)
            if quote:
                results[ticker] = quote
        except Exception as e:
            log.warning(f"Error fetching quote for {ticker}: {e}")
            continue
    
    log.info(f"Fetched {len(results)} live quotes from yfinance.")
    return results

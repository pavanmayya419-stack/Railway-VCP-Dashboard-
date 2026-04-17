import math
import numpy as np
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List
from pydantic import BaseModel

from data_manager import list_cached_dates, load_scan_cache
from engine import fetch_data, compute_indicators, DETECTOR, run_alpha_vcp_simulator
from ml_api import router as ml_router
from refresh_data import generate_cache_for_market, _load_tickers
from ticker_metadata import get_metadata
from ohlcv_store import bulk_download, _store_status, fetch_local
from yfinance_live import get_live_ohlcv

class RefreshRequest(BaseModel):
    market: str | None = None

class RefreshResult(BaseModel):
    market: str
    count: int
    date: str

class OHLCVDownloadRequest(BaseModel):
    market: str
    force: bool = False
    incremental: bool = False

def sanitize(obj):
    # numpy scalar types → native Python types
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        v = float(obj)
        return 0 if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(obj, np.ndarray):
        return sanitize(obj.tolist())
    # native Python float NaN/Inf
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return 0
    # recurse into containers
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    return obj

app = FastAPI(title="Pavan Mayya VCP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include ML router
app.include_router(ml_router)

@app.get("/api/health")
def health_check():
    return {
        "status": "ok", 
        "timestamp": datetime.now().isoformat(),
        "data_source": "yfinance",
        "features": {"scanner": True, "ml": True, "charts": True, "portfolio": True}
    }

@app.get("/api/status")
def get_status():
    today = datetime.now().strftime("%Y-%m-%d")
    markets = ["US", "IN"]
    result = {}
    for market in markets:
        dates = list_cached_dates(market)
        if not dates:
            result[market] = {"last_date": None, "count": 0, "freshness": "none"}
            continue
        last_date = dates[0]
        data = load_scan_cache(market, last_date)
        count = len(data)
        try:
            delta = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(last_date, "%Y-%m-%d")).days
        except Exception:
            delta = 999
        if delta == 0:
            freshness = "fresh"
        elif delta == 1:
            freshness = "stale"
        else:
            freshness = "old"
        result[market] = {"last_date": last_date, "count": count, "freshness": freshness, "days_ago": delta}
    return result

@app.get("/api/dates")
def get_dates(market: str = "US"):
    dates = list_cached_dates(market)
    return {"market": market, "dates": dates}

@app.get("/api/scan")
def get_scan(market: str, date: str = ""):
    try:
        if not date:
            dates = list_cached_dates(market)
            if not dates:
                raise HTTPException(status_code=404, detail=f"No scan data found for {market}. Please run data refresh.")
            date = dates[0]

        results = load_scan_cache(market, date)
        if not results:
            raise HTTPException(status_code=404, detail=f"No scan data found for {market} on {date}. Please run data refresh.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading scan data: {str(e)}")

    # Backward compatibility normalization for older cache files
    normalized = []
    for r in results:
        if not isinstance(r, dict):
            continue

        scores = r.get("scores") or {}

        # Ensure always-present display fields
        r.setdefault("sector", "n/a")
        r.setdefault("cap", "n/a")

        # Older cache files may only contain these under `scores`
        if "tight" not in r:
            r["tight"] = scores.get("tightness", 0)
        if "wbase" not in r:
            r["wbase"] = scores.get("wbase", 0)

        # 6M return field support (new field). For legacy rows, fall back to 3M value.
        if "r126" not in r:
            r["r126"] = r.get("r63", 0)

        if not r.get("sector") or r["sector"] in {"n/a", "Unknown"} or not r.get("cap") or r["cap"] in {"n/a", "Unknown"}:
            metadata = get_metadata(r.get("ticker", ""), market)
            r["sector"] = metadata.get("sector", "Unknown")
            r["cap"] = metadata.get("cap", "Unknown")

        normalized.append(r)

    results = normalized
    results = sanitize(results)
    return {"market": market, "date": date, "count": len(results), "results": results}

@app.get("/api/chart")
def get_chart_data(ticker: str):
    # Determine market
    market = "IN" if ".NS" in ticker else "US"
    
    # Base fetch
    df = fetch_data(ticker, market=market)
    
    # Use yfinance for live data
    try:
        from yfinance_live import get_live_ohlcv
        live_df = get_live_ohlcv(ticker, market)
        if live_df is not None and not live_df.empty:
            df = live_df
    except Exception:
        pass

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="Ticker data not found locally.")
    
    res = DETECTOR.analyse(df, ticker)
    
    chart_df = res["df"].copy()
    chart_df.index.name = 'time'
    chart_df = chart_df.reset_index()
    chart_df['time'] = chart_df['time'].dt.strftime('%Y-%m-%d')
    chart_df.columns = [c.lower() for c in chart_df.columns]
    chart_df = chart_df.replace([np.inf, -np.inf], np.nan).fillna(value=0)
    
    res_dict = sanitize({
        "ticker": res["ticker"],
        "score": res["score"],
        "scores": res["scores"],
        "checklist_str": res["checklist_str"],
        "stage": res["stage"],
        "contractions": res["contractions"],
        "signals": res["signals"],
        "data": chart_df.to_dict(orient="records"),
        "spark": res.get("spark"),
        "trend": res.get("trend"),
        "bbw_pctl": res.get("bbw_pctl"),
        "squeeze": res.get("squeeze"),
        "tight": res.get("tight"),
        "vdry": res.get("vdry"),
        "hndl": res.get("hndl"),
        "adx": res.get("adx"),
        "tier_enc": res.get("tier_enc"),
        "pdh_brk": res.get("pdh_brk"),
        "last_price": res.get("last_price"),
        "rsi": res.get("rsi"),
        "vol_ratio": res.get("vol_ratio"),
        "atr_pct": res.get("atr_pct"),
        "r1": res.get("r1"),
        "r5": res.get("r5"),
        "r21": res.get("r21"),
        "r63": res.get("r63"),
        "pct_off_high": res.get("pct_off_high"),
    })
    return res_dict

@app.post("/api/refresh")
async def refresh_data(req: RefreshRequest):
    markets = [req.market] if req.market else ["US", "IN"]
    results = []
    for market in markets:
        count, date_str = await run_in_threadpool(generate_cache_for_market, market, True)
        results.append({"market": market, "count": count, "date": date_str})
    return {"results": results}

@app.get("/api/ohlcv/status")
def ohlcv_status():
    result = {}
    for market in ["US", "IN"]:
        tickers = _load_tickers(market)
        result[market] = _store_status(market, tickers)
    return result

@app.post("/api/ohlcv/download")
async def ohlcv_download(req: OHLCVDownloadRequest):
    tickers = _load_tickers(req.market)
    summary = await run_in_threadpool(
        bulk_download,
        req.market,
        tickers,
        6,           # workers
        req.force,
        req.incremental,
    )
    return summary

@app.get("/api/broker/status")
def broker_status():
    return {"fyers": {"linked": False, "updated_at": None}}

@app.get("/api/broker/fyers/auth_url")
def fyers_auth_url():
    return {"url": "#"}

class FyersLoginRequest(BaseModel):
    url: str

@app.post("/api/broker/fyers/login")
async def fyers_login(req: FyersLoginRequest):
    return {"message": "Fyers integration is disabled."}

class HoldingScanRequest(BaseModel):
    ticker: str
    quantity: float = 0
    avg_cost: float = 0

class PortfolioScanRequest(BaseModel):
    holdings: List[HoldingScanRequest]

@app.post("/api/portfolio/scan")
async def scan_portfolio(req: PortfolioScanRequest):
    results = []
    
    def process_holding(h: HoldingScanRequest):
        try:
            ticker = h.ticker
            if not ticker.endswith(".NS") and not ticker.endswith(".BO") and not any(c.islower() for c in ticker):
                 # Heuristic for IN vs US if not provided
                 # But let's assume if it came from Kite it needs .NS
                 if len(ticker) <= 10: ticker = ticker + ".NS"

            market = "IN" if ".NS" in ticker else "US"
            df = fetch_data(ticker, market)
            if df is not None and not df.empty:
                res = DETECTOR.analyse(df, ticker)
                # Attach the user's data
                res["quantity"] = h.quantity
                res["avg_cost"] = h.avg_cost
                res["ltp"] = res.get("last_price", 0)
                res["open_pnl"] = (res["ltp"] - h.avg_cost) * h.quantity if h.avg_cost > 0 else 0
                return res
        except:
            pass
        return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_holding, h): h for h in req.holdings}
        for future in as_completed(futures):
            res = future.result()
            if res:
                if "df" in res: del res["df"]
                results.append(res)
    
    return {"holdings": sanitize(results)}

@app.get("/api/simulate")
def simulate(market: str = "US", min_score: float = 60.0):
    res = run_alpha_vcp_simulator(market, min_score)
    return sanitize(res)

@app.get("/api/scan/live")
async def get_live_scan(market: str = "IN"):
    tickers = _load_tickers(market)
    
    # Use yfinance for live data
    from yfinance_live import get_live_ohlcv
    
    def process_live(ticker):
        try:
            # Use 1y period for live scan for speed
            df = get_live_ohlcv(ticker, market)
            if df is not None and len(df) >= 60:
                res = DETECTOR.analyse(df, ticker=ticker)
                if "df" in res:
                    del res["df"]
                return res
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error processing live {ticker}: {e}")
        return None

    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(process_live, t): t for t in tickers}
        for future in as_completed(futures):
            try:
                res = future.result()
                if res:
                    results.append(res)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Thread error in live scan: {e}")

    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "market": market, 
        "date": date_str, 
        "live": True, 
        "count": len(results), 
        "total_attempted": len(tickers),
        "data_source": "yfinance",
        "results": sanitize(results)
    }

# Serve frontend static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "..", "frontend", "dist")

@app.get("/")
def serve_root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend not built. Please run npm run build in frontend directory."}

# Serve static assets
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

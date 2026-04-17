# VCP Pro Dashboard - US Market System

This workspace is a dedicated, isolated instance for the **US Stock Market**. It operates independently of the India market instance to ensure data integrity and zero logic overlap.

## 🚀 System Configuration
- **Market Key**: `US`
- **Backend API**: [http://localhost:8001](http://localhost:8001)
- **Frontend UI**: [http://localhost:3001](http://localhost:3001)

## 📁 Architecture & Isolation
- **Codebase**: Fully independent copy of the VCP engine.
- **Data Storage**: 
    - OHLCV Parquet files: `backend/data/` (US tickers only)
    - Scan Caches: `backend/outputs/scan_cache/` (Files prefix: `US_`)
- **Ticker Universe**: S&P 500 constituents (`backend/sp500_constituents.csv`).

## ⚙️ How it Works
1. **Data Refresh**: 
   When you run `python refresh_data.py` (or use the UI button), the system downloads history ONLY for US tickers. The scan results are saved in this folder's private cache.
2. **ML Intelligence**: 
   The ML models trained in this folder are specific to US market price action. The prediction defaults remain locked to `US`.
3. **Ports**: 
   By using Port `8001`, this system avoids conflicting with the India dashboard, allowing you to run both side-by-side.

## 🛠️ Usage
- Use the **START VCP US.bat** shortcut on your desktop to launch.
- To refresh US data specifically: `cd backend && python refresh_data.py`.

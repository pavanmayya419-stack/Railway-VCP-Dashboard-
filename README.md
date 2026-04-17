# VCP Dashboard (US Market) - Complete Guide

An AI-powered stock analysis dashboard for detecting Volatility Contraction Pattern (VCP) setups in the S&P 500 universe.

---

## Table of Contents
1. [What is this?](#what-is-this)
2. [How to Run (3 Methods)](#how-to-run)
3. [System Architecture](#system-architecture)
4. [Data Flow Explained](#data-flow-explained)
5. [Key Files & Their Purpose](#key-files--their-purpose)
6. [Daily Usage Workflow](#daily-usage-workflow)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [Important Commands Reference](#important-commands-reference)

---

## What is this?

**VCP Dashboard** scans 500+ S&P 500 stocks daily to identify high-probability breakout setups using:
- Volatility Contraction Pattern (VCP) detection
- Relative Strength (RS) ranking
- Stage analysis (Stage 1-4)
- ML-powered stock ranking

**Ports:**
- Frontend: http://localhost:3001
- Backend API: http://localhost:8001

---

## How to Run

### Method 1: Simplest (Recommended)
```bash
"START DASHBOARD.bat"
```
This starts both backend and frontend, then opens your browser.

### Method 2: Interactive Launcher
```bash
# PowerShell
.\run.ps1

# Or CMD
run.bat
```
Gives options: Launch, Sync Data, or Full Startup.

### Method 3: Manual (For Debugging)
```bash
# Terminal 1 - Backend
cd backend
venv\Scripts\python main.py

# Terminal 2 - Frontend  
cd frontend
npm run dev

# Open http://localhost:3001
```

---

## System Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Backend       │────▶│   Data Store    │
│   React + Vite  │◀────│   FastAPI       │◀────│   Parquet/PKL   │
│   Port 3001     │     │   Port 8001     │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Backend Components
| File | Purpose |
|------|---------|
| `main.py` | FastAPI server, API routes (/api/scan, /api/dates, /api/status) |
| `engine.py` | Core VCP detection algorithm (RSI, RS, Squeeze, Base detection) |
| `data_manager.py` | Read/write scan cache files (PKL) |
| `ohlcv_store.py` | Manage OHLCV parquet files for 500 tickers |
| `refresh_data.py` | Daily data refresh - downloads new OHLCV, runs scan |
| `backfill_cache.py` | Re-generate historical scans for past dates |
| `ml_api.py` | ML model training and prediction endpoints |

### Frontend Components
| File | Purpose |
|------|---------|
| `App.tsx` | Main layout, state management, coordinates all tabs |
| `Sidebar.tsx` | Market selector, date picker, filters, refresh button |
| `ScannerTab.tsx` | Stock scanner table with sorting/filtering |
| `api.ts` | Backend API client functions |

---

## Data Flow Explained

### 1. OHLCV Data (Price History)
- **Source:** Yahoo Finance via yfinance
- **Storage:** `backend/outputs/ohlcv/US/TICKER.parquet`
- **Coverage:** 2 years of daily OHLCV for 500 S&P 500 stocks
- **Update:** Daily via `refresh_data.py` or sidebar "Refresh Today's Data" button

### 2. Scan Cache (VCP Analysis Results)
- **Storage:** `backend/outputs/scan_cache/US_YYYY-MM-DD.pkl`
- **Content:** VCP scores, stage, RS, RSI, trend signals for each stock
- **Generation:** Created by running VCP engine on OHLCV data
- **One file per trading day**

### 3. How Data Flows
```
Daily Refresh:
  1. Download latest OHLCV (append new days)
  2. Run VCP engine on all 500 stocks
  3. Save results to US_YYYY-MM-DD.pkl
  4. Dashboard reads from PKL file

Historical Backfill:
  1. Load all OHLCV parquet files
  2. For each past date, slice OHLCV up to that date
  3. Run VCP engine (need 60 days history minimum)
  4. Save to corresponding PKL file
```

---

## Key Files & Their Purpose

### Root Directory
| File | What it does |
|------|--------------|
| `START DASHBOARD.bat` | One-click launcher - starts everything |
| `run.bat` / `run.ps1` | Interactive launcher with menu options |
| `refresh-data.bat` | Quick data refresh without UI |
| `refresh-2months.bat` | Refresh last 2 months of data |

### Backend Directory
| File | What it does |
|------|--------------|
| `main.py` | API server - handles all frontend requests |
| `engine.py` | VCP math - calculates scores, stages, patterns |
| `refresh_data.py` | Daily scan - downloads data + runs VCP engine |
| `backfill_cache.py` | Fix historical scans with low stock counts |
| `data_manager.py` | Read/write PKL cache files |
| `ohlcv_store.py` | Read/write parquet OHLCV files |
| `ml_api.py` | Train XGBoost models, predict winners |
| `sp500_constituents.csv` | List of 500 tickers to scan |

### Frontend Directory
| File | What it does |
|------|--------------|
| `src/App.tsx` | Main app, tab switching, data coordination |
| `src/components/Sidebar.tsx` | Controls: date picker, filters, refresh |
| `src/components/ScannerTab.tsx` | Table showing scan results |

---

## Daily Usage Workflow

### Morning Routine (Before Market Opens)
1. **Start Dashboard**
   ```bash
   "START DASHBOARD.bat"
   ```

2. **Refresh Data** (Critical - gets yesterday's closing prices)
   - In sidebar, click **"Refresh Today's Data"**
   - Wait 30-60 seconds for 500 stocks to scan
   - Check "Data freshness" shows today's date

3. **Review Scanner**
   - Go to **Scanner** tab
   - Set filters: Stage 1-2, VCP Score > 60
   - Review stocks near pivot points

4. **Check Top 10 ML Picks**
   - Go to **Top 10 ML** tab
   - These are AI-ranked highest probability setups
   - Shows entry price, target, stop loss

### Weekly Routine (ML Model Maintenance)
1. Go to **ML Intelligence** tab
2. Click **"Build Dataset"** - analyzes last 30 days of winners/losers
3. Click **"Train Models"** - creates fresh XGBoost model
4. Now Top 10 picks use latest market patterns

---

## Troubleshooting Guide

### Problem: Dashboard won't start
```bash
# Kill any stuck processes
taskkill /f /im python.exe
taskkill /f /im node.exe

# Then restart
"START DASHBOARD.bat"
```

### Problem: "No scan data found" or empty scanner
```bash
# Terminal 1: Check backend is running
cd backend
venv\Scripts\python main.py

# Terminal 2: Check API responds
curl http://localhost:8001/api/status

# If no data, run refresh:
cd backend
venv\Scripts\python refresh_data.py
```

### Problem: Historical dates show <100 stocks
This means the scan cache wasn't fully populated for those dates.

```bash
# Backfill all US dates with full 500 stocks
cd backend
venv\Scripts\python backfill_cache.py US

# This takes 20-30 minutes - runs in parallel using all CPU cores
```

### Problem: Frontend shows "Failed to fetch"
1. Backend not running - start it: `cd backend && venv\Scripts\python main.py`
2. Wrong port - check frontend is pointing to port 8001
3. CORS issue - restart backend

### Problem: Charts not loading
1. Ticker needs 2 years of OHLCV data
2. Run OHLCV download: Check sidebar "Local OHLCV store" section
3. Click "Full Download" if coverage < 90%

### Problem: ML Top 10 is empty
1. Need to train models first
2. Go to ML Intelligence tab → Build Dataset → Train Models
3. Takes 5-10 minutes first time

---

## Important Commands Reference

### Start Everything
```bash
"START DASHBOARD.bat"
```

### Refresh Data (Daily)
```bash
cd backend
venv\Scripts\python refresh_data.py
```

### Backfill Historical Scans
```bash
cd backend
venv\Scripts\python backfill_cache.py US
```

### Check Scan File
```python
import pickle
with open('backend/outputs/scan_cache/US_2025-04-10.pkl', 'rb') as f:
    data = pickle.load(f)
print(f"Stocks: {len(data)}")  # Should be ~500
```

### Get Quick Stock Picks (Terminal)
```bash
cd backend
venv\Scripts\python vcp_picks.py
```

### Kill All Processes
```bash
taskkill /f /im python.exe
taskkill /f /im node.exe
```

---

## Data Locations Quick Reference

| Data Type | Path |
|-----------|------|
| OHLCV (prices) | `backend/outputs/ohlcv/US/*.parquet` |
| Scan results | `backend/outputs/scan_cache/US_YYYY-MM-DD.pkl` |
| ML models | `backend/outputs/ml_models/` |
| Ticker list | `backend/sp500_constituents.csv` |

---

## First-Time Setup

If you just cloned/downloaded this:

1. **Backend setup:**
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\pip install -r requirements.txt
   ```

2. **Frontend setup:**
   ```bash
   cd frontend
   npm install
   ```

3. **Download initial OHLCV data:**
   - Start dashboard
   - In sidebar, click "Full Download" under "Local OHLCV store"
   - Wait 10-15 minutes (downloads 2 years for 500 stocks)

4. **Run first scan:**
   - Click "Refresh Today's Data" in sidebar
   - Wait 1-2 minutes

5. **Train ML models:**
   - Go to ML Intelligence tab
   - Click "Build Dataset" then "Train Models"

---

**Dashboard Ready?** Open http://localhost:3001

# VCP Pro Dashboard Architecture & Developer Guide

This document captures the structural decisions, API integrations, and code relationships formed after migrating the prototype to local production — moving from a Streamlit proof-of-concept into the FastAPI + React architecture you see today.

## Stack Overview
- **Backend:** FastAPI (Python 3.11+), Uvicorn, Pandas, Numpy.
- **Data Engine:** Uses pre-calculated `.pkl` files acting as a snapshot cache of the quantitative `engine.py` calculations to allow sub-100ms dashboard latency.
- **Frontend:** React 18 (Vite), TypeScript, Tailwind CSS v4, Lucide React (Icons).
- **State Management:** `@tanstack/react-query` (fetching and cache invalidation), native React contexts.
- **Charting Engine:** lightweight-charts v5 (by TradingView).

---

## 1. Directory Structure

```text
pavan_mayya_vcp_fastapi_react/
│
├── backend/
│   ├── data/                 # Raw OHLCV CSV data repository.
│   ├── outputs/
│   │   └── scan_cache/       # Cached .pkl snapshot arrays used by dashboard.
│   ├── data_manager.py       # Handles reading & writing cache layer files.
│   ├── engine.py             # Core Quant Math (VCP Patterns, RSI, RS, Squeeze, Base calculations).
│   ├── main.py               # FastAPI router entry point (`/api/scan`, `/api/chart`).
│   ├── requirements.txt      # Python dependencies.
│   └── venv/                 # Local python virtual environment.
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── api.ts            # Client stubs mapping exactly to FastAPI endpoints.
│   │   ├── types.ts          # Central source of truth for global Application state interfaces.
│   │   ├── App.tsx           # Institutional layout and query hook orchestrator.
│   │   ├── index.css         # Foundational aesthetic configuration & design tokens.
│   │   │
│   │   └── components/
│   │       ├── Sidebar.tsx   # Global control layer (filters, parameters, caches, ranges).
│   │       ├── ScannerTab.tsx    # Datatable filtering based on FastAPI's scan outputs.
│   │       ├── TVChart.tsx       # Lightweight-charts v5 visualizer with strict Error Boundaries.
│   │       ├── ChartAnalysisTab.tsx  # Layout wrapper passing data payloads into TVChart.
│   │       ├── HeatmapTab.tsx    # Institutional summary views (sectors, bins).
│   │       ├── SimulationTab.tsx # Live paper trading controls.
│   │       ├── BacktestTab.tsx   # Historical performance visualization.
│   │       ├── ForwardTab.tsx    # Forward alpha tracking mechanism.
│   │       └── PortfolioTab.tsx  # Custom portfolio CSV upload capabilities.
│   │
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
```

---

## 2. Core Operational Mechanics

### Serialization Between Python & React
The `engine.py` generates responses wrapped in Pandas configurations containing `numpy.float64` and `numpy.bool_` scalar types. FastAPIs native serialization pipeline throws a `500 Internal Server` error if left unhandled.

**Handler Solution:** `backend/main.py` utilizes a custom recursive `sanitize()` routine to forcibly downcast standard NaN/Infinity conditions alongside nested native conversions (`isinstance(obj, np.floating) -> float()` etc.).

### Auto-Selection & Render Loops
**Anti-Pattern Fixed:** A common flaw in the React migration is enforcing single item selection (`setSelectedTicker`) implicitly during the raw render lifecycle. This caused UI lock-out bounds.
**Handler Solution:** `App.tsx` controls global active tickers by deploying a structured `useEffect` bound to the incoming lengths of active `filteredResults`. This ensures downstream query hooks only launch once the UI settles.

### Institutional Charting Updates
Upgrading from basic UI lines to `lightweight-charts v5` significantly boosts performance but drops backwards functions.
- Setting price scales must occur **inline or independently explicitly**, instead of assigning strings inside addSeries and looking for a global.
- Chart annotations (C1, L1 marker strings) are attached using the new explicit v5 interface: `createSeriesMarkers(candleSeries, markerArray);`.
- `ChartErrorBoundary` class traps malformed arrays in real-time, displaying a "Chart rendering failed" fallback, ensuring the rest of the application remains 100% interactive if a database row fails.

---

## 3. Future Development Scope & Next Steps

If pursuing the next phase of development, prioritize the following extensions:

#### 1. Connecting "Mocks" to the Backtest Engine
Currently, endpoints like `handleRunBacktest` inside `App.tsx` supply local state placeholders (`total_trades: 12`, etc.).
**Requirement:** Update `api.ts` to execute a `POST` interaction pushing the `minVcpScore` parameters to the backend `main.py` routing, bridging directly to the internal functions in `engine.py` -> `run_alpha_vcp_simulator()`.

#### 2. Portfolio Uploads & Chunking
The `PortfolioTab.tsx` is built to visualize VCP logic over arbitrary assets. To make this production-ready, write a lightweight FastAPI handler leveraging `python-multipart` to accept a raw text CSV buffer, map it via `data_manager.py`, and pump it through `engine.py` on-demand (bypassing preloads).

#### 3. Realtime Cron Web Sockets (Optional Architecture)
If implementing live intraday data streams via NSE/NYSE adapters, avoid fetching via `setInterval()` over basic APIs. Upgrade the FastAPI implementation to deploy via native `WebSocket` routing. Extend React Queries in the frontend leveraging the established query invalidations.

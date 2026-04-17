# 🚀 Daily Dashboard Workflow Guide

To ensure your VCP Pro Dashboard provides the most accurate and "intelligent" stock picks every day, follow this simple 3-step routine.

## 1. Start the Dashboard
Always start the project using the master launcher in the root directory:
- 📂 Double-click `run.bat` (Windows)
- This starts both the **FastAPI Backend** and the **React Frontend**.

---

## 2. Refresh Daily Market Data
Once the dashboard is open in your browser (`http://localhost:5173`):

### Indian Market (NSE)
1. Go to the **Broker** tab. Ensure your **Fyers** connection is active (Link Account if needed).
2. Go to the **Scanner** tab.
3. Click 🔄 **Refresh Today's Data** in the Sidebar.
   - This downloads the latest 2-year history and patches it with live Fyers quotes.
   - It then runs the VCP engine on all 800+ stocks.

### US Market (S&P 500)
1. Switch Market to **US** in the Sidebar.
2. Click 🔄 **Refresh Today's Data**.

---

## 3. Update ML Intelligence
The **Top 10 ML Picks** tab uses AI to rank stocks based on their probability of reaching a +5% target within 5 days.

### Why Train?
Markets change! Periodic training ensures the AI recognizes the latest high-probability patterns.

### How to Train:
1. Go to the **Top 10 Picks** tab.
2. Click 📊 **Build Dataset**. This analyzes months of historical scanner data to find "Winners".
3. Click 🧠 **Train Models**. This creates fresh XGBoost models for the current market environment.
4. **Done!** Your Top 10 list will now be updated with the highest probability "Entries".

---

## 🛠 Troubleshooting & Maintenance

- **Stale Data?** If the scanner shows old dates, click "Refresh Today's Data".
- **Missing ML Models?** If the Top 10 tab is empty, run the "Build Dataset" and "Train Models" steps mentioned above.
- **Fyers Disconnected?** Fyers requires daily authentication. If charts don't show live LTP, re-link your Fyers account in the Broker tab.

---

## 💡 Pro Tip: Get Picks via Terminal
If you just want a quick summary of the top stocks without opening the browser, run:
```powershell
# From the backend folder:
python vcp_picks.py
```
This will print a beautiful table of the **Top 10 Stocks** with explicit **Entry**, **Target**, and **Stop Loss** prices.

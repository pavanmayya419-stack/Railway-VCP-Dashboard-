import requests
import json
import os
from datetime import datetime

API_BASE = "http://localhost:8000/api"

def get_top_picks(market):
    print(f"\n{'='*75}")
    print(f" FETCHING TOP 10 {market} VCP PICKS ")
    print(f"{'='*75}")
    
    try:
        # 1. Get scan results (defaults to latest date)
        print(f"Fetching latest scan results...")
        scan_resp = requests.get(f"{API_BASE}/scan?market={market}", timeout=30)
        if scan_resp.status_code != 200:
            print(f"Error: Could not fetch scan results ({scan_resp.status_code})")
            return
            
        scan_data = scan_resp.json()
        results = scan_data.get('results', [])
        
        if not results:
            print(f"No results found for {market} market.")
            return

        # 2. Get ML picks
        print(f"Running ML analysis on {len(results)} stocks...")
        picks_resp = requests.post(
            f"{API_BASE}/ml/top-picks/{market}",
            json={'results': results, 'horizon': 5},
            timeout=60
        )
        
        if picks_resp.status_code != 200:
            # Maybe models are not trained yet?
            print(f"ML Picking failed (Status {picks_resp.status_code}).")
            print(f"Message: {picks_resp.json().get('detail', 'Unknown error')}")
            
            # Fallback: Just show top 10 by VCP Score
            print(f"\nShowing Top 10 by VCP Score (Traditional) instead:\n")
            top_vcp = sorted(results, key=lambda x: x.get('score', 0), reverse=True)[:10]
            display_picks(top_vcp, ml=False)
            return

        picks_data = picks_resp.json()
        if not picks_data.get('success'):
            print(f"Failed to get picks: {picks_data.get('message')}")
            return
            
        display_picks(picks_data.get('picks', []), ml=True)
        
    except Exception as e:
        print(f"Error: {e}")

def display_picks(picks, ml=True):
    header = f"{'RANK':<5} {'TICKER':<12} {'PRICE':<10} {'VCP':<8} {'RS':<6} {'RSI':<6} {'STAGE':<6} {'TREND':<8} {'PROB' if ml else 'SIGNAL':<10}"
    print(header)
    print("-" * len(header))
    
    for i, p in enumerate(picks):
        rank = p.get('rank', i+1)
        ticker = p.get('ticker', 'N/A')
        price = p.get('last_price', 0)
        score = p.get('score', 0)
        rs = p.get('rs_1y', 0)
        rsi = p.get('rsi', 0)
        stage = p.get('stage', 1)
        trend = "YES" if p.get('trend_template') else "NO"
        
        if ml:
            prob = f"{p.get('ml_probability', 0)*100:.1f}%"
        else:
            sigs = p.get('signals', {})
            prob = "BREAKOUT" if sigs.get('pivot_breakout') or sigs.get('tl_breakout') else "TIGHTENING"

        print(f"{rank:<5} {ticker:<12} {price:<10.2f} {score:<8.1f} {rs:<6.0f} {rsi:<6.1f} {stage:<6} {trend:<8} {prob:<10}")
        
        # Display Entry Details
        target = price * 1.05 
        stop = price * 0.93  
        dist_low = p.get('dist_low', 0)
        print(f"      👉 Entry: {price:.2f} | Target: {target:.2f} (+5%) | Stop: {stop:.2f} (-7%) | DistLow: {dist_low:.1f}%")
        print()

if __name__ == "__main__":
    import sys
    # Check if backend is running
    try:
        requests.get(f"{API_BASE}/health", timeout=2)
    except:
        print("Backend server is not running on http://localhost:8000")
        print("Please run 'python main.py' or use 'run.bat' first.")
        sys.exit(1)
        
    get_top_picks("US")
    get_top_picks("IN")

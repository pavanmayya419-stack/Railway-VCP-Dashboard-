"""
Build dataset and train models for both US and IN markets.
Run this script to prepare ML models for Top 10 Picks.
"""
import requests
import json
import time
import sys

def build_dataset(market_key):
    print(f"\n{'='*50}")
    print(f"Building dataset for {market_key}...")
    print(f"{'='*50}")
    
    try:
        resp = requests.post(
            'http://localhost:8000/api/ml/build-dataset',
            json={
                'market_key': market_key,
                'horizons': [2, 5, 10],
                'winner_thresholds': {'2': 3.0, '5': 5.0, '10': 8.0},
                'stop_pct': 7.0
            },
            timeout=300
        )
        data = resp.json()
        print(f"Success: {data.get('success')}")
        print(f"Message: {data.get('message')}")
        print(f"Samples: {data.get('total_samples', 0)}")
        print(f"Tickers: {data.get('unique_tickers', 0)}")
        print(f"Winners: {data.get('winners', 0)}, Losers: {data.get('losers', 0)}")
        return data.get('success', False)
    except Exception as e:
        print(f"Error building dataset: {e}")
        return False

def train_models(market_key):
    print(f"\n{'='*50}")
    print(f"Training models for {market_key}...")
    print(f"{'='*50}")
    
    try:
        resp = requests.post(
            'http://localhost:8000/api/ml/train-models',
            json={
                'market_key': market_key,
                'horizons': [2, 5, 10],
                'winner_thresholds': {'2': 3.0, '5': 5.0, '10': 8.0},
                'stop_pct': 7.0
            },
            timeout=120
        )
        data = resp.json()
        print(f"Success: {data.get('success')}")
        print(f"Message: {data.get('message')}")
        
        if data.get('models'):
            for m in data['models']:
                print(f"  Horizon {m['horizon']}d: AUC={m['auc']:.3f}, Samples={m['n_train']}, Winners={m['n_winners']}, Losers={m['n_losers']}")
        return data.get('success', False)
    except Exception as e:
        print(f"Error training models: {e}")
        return False

def get_top_picks(market_key):
    print(f"\n{'='*50}")
    print(f"Getting Top 10 ML Picks for {market_key}...")
    print(f"{'='*50}")
    
    # First get scan results
    try:
        resp = requests.get(f'http://localhost:8000/api/scan?market={market_key}&date=', timeout=30)
        scan_data = resp.json()
        results = scan_data.get('results', [])
        
        if not results:
            print(f"No scan results found for {market_key}")
            return
        
        print(f"Scan results: {len(results)} stocks")
        
        # Get top picks
        resp = requests.post(
            f'http://localhost:8000/api/ml/top-picks/{market_key}',
            json={'results': results, 'horizon': 5},
            timeout=60
        )
        data = resp.json()
        
        if not data.get('success'):
            print(f"Failed to get picks: {data.get('message')}")
            return
        
        picks = data.get('picks', [])
        print(f"\n🏆 TOP {len(picks)} ML PICKS FOR {market_key}:\n")
        
        for pick in picks:
            rank_icon = "🥇" if pick['rank'] == 1 else "🥈" if pick['rank'] == 2 else "🥉" if pick['rank'] == 3 else f"{pick['rank']}."
            prob_color = "🟢" if pick['ml_probability'] >= 0.7 else "🟡" if pick['ml_probability'] >= 0.5 else "🔴"
            trend_tag = " [TREND VERIFIED]" if pick.get('trend_template') else ""
            
            print(f"{rank_icon} {pick['ticker']}{trend_tag}")
            print(f"   Probability: {prob_color} {pick['ml_probability']*100:.1f}% | VCP Score: {pick['score']:.1f} | Stage: {pick['stage']}")
            print(f"   Price: ${pick['last_price']:.2f} | RS: {pick['rs_1y']:.0f} | RSI: {pick['rsi']:.1f}")
            print(f"   Sector: {pick['sector']} | Cap: {pick['cap']}")
            
            feats = ", ".join([f"{f['name']}={f['value']:.1f}" for f in pick['top_features'][:3]])
            print(f"   Top Features: {feats}\n")
            print()
            
    except Exception as e:
        print(f"Error getting top picks: {e}")

if __name__ == '__main__':
    # Prioritize India as requested
    markets = ['IN', 'US']
    
    for market in markets:
        print(f"\n{'#'*60}")
        print(f"# Processing {market} Market")
        print(f"{'#'*60}")
        
        # 1. Build dataset
        if build_dataset(market):
            time.sleep(1)
            # 2. Train models
            if train_models(market):
                time.sleep(1)
                # 3. Get picks
                get_top_picks(market)
        
        print(f"\n{'#'*60}")
        print(f"# {market} Complete")
        print(f"{'#'*60}\n")
        time.sleep(1)
    
    print("\n✅ All markets processed!")

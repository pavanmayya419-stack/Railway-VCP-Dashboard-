"""Get picks using models from previous training session."""
import requests
import json

def get_picks(market):
    print(f"\n{'='*70}")
    print(f"TOP 10 ML PICKS - {market} STOCKS")
    print(f"{'='*70}")
    
    try:
        # Get scan results
        resp = requests.get(f'http://localhost:8000/api/scan?market={market}&date=', timeout=30)
        scan_data = resp.json()
        results = scan_data.get('results', [])
        print(f"Scan results: {len(results)} stocks")
        
        if not results:
            print("No scan results found!")
            return
        
        # Get top picks
        resp = requests.post(
            f'http://localhost:8000/api/ml/top-picks/{market}',
            json={'results': results, 'horizon': 5},
            timeout=60
        )
        data = resp.json()
        
        if not data.get('success'):
            print(f"Error: {data.get('message')}")
            
            # Try to train models if not available
            print("Attempting to train models...")
            train_resp = requests.post(
                'http://localhost:8000/api/ml/train-models',
                json={
                    'market_key': market,
                    'horizons': [2, 5, 10],
                    'winner_thresholds': {'2': 3.0, '5': 5.0, '10': 8.0},
                    'stop_pct': 7.0
                },
                timeout=120
            )
            print(f"Training response: {train_resp.status_code}")
            return
        
        picks = data.get('picks', [])
        print(f"\n🏆 TOP {len(picks)} ML PICKS FOR {market}:\n")
        
        for pick in picks:
            rank = pick['rank']
            rank_icon = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
            prob = pick['ml_probability'] * 100
            prob_bar = '█' * int(prob/5) + '░' * (20 - int(prob/5))
            
            name = pick['name'][:25] if pick['name'] else ""
            sector = pick['sector'] if pick['sector'] else "N/A"
            
            print(f"{rank_icon} {pick['ticker']:<6} ({name:<25}) | Prob: {prob_bar} {prob:>5.1f}% | Score: {pick['score']:.1f} | Stage {pick['stage']}")
            print(f"   Price: ${pick['last_price']:.2f} | RS: {pick['rs_1y']:.0f} | RSI: {pick['rsi']:.1f} | {sector}")
            
            if pick.get('top_features'):
                feats = ', '.join([f"{f['name']}={f['value']:.1f}" for f in pick['top_features'][:3]])
                print(f"   Features: {feats}")
            print()
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    # Check if backend is running
    try:
        resp = requests.get('http://localhost:8000/api/status', timeout=5)
        print("Backend is running")
    except:
        print("Backend is not running! Please start it first.")
        exit(1)
    
    for market in ['US', 'IN']:
        get_picks(market)

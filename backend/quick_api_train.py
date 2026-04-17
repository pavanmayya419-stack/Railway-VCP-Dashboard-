"""Quick training via API calls."""
import requests
import time

def train_market(market):
    print(f"\n=== Training {market} ===")
    
    # Build dataset
    print("Building dataset...")
    resp = requests.post(
        'http://localhost:8000/api/ml/build-dataset',
        json={
            'market_key': market,
            'horizons': [2, 5, 10],
            'winner_thresholds': {'2': 3.0, '5': 5.0, '10': 8.0},
            'stop_pct': 7.0
        },
        timeout=30
    )
    
    if resp.status_code != 200:
        print(f"Dataset build failed: {resp.status_code}")
        return False
    
    data = resp.json()
    print(f"Dataset: {data.get('total_samples', 0)} samples")
    
    # Train models
    print("Training models...")
    resp = requests.post(
        'http://localhost:8000/api/ml/train-models',
        json={
            'market_key': market,
            'horizons': [2, 5, 10],
            'winner_thresholds': {'2': 3.0, '5': 5.0, '10': 8.0},
            'stop_pct': 7.0
        },
        timeout=30
    )
    
    if resp.status_code != 200:
        print(f"Model training failed: {resp.status_code}")
        return False
    
    data = resp.json()
    print(f"Models trained: {len(data.get('models', []))}")
    
    return True

def get_picks(market):
    print(f"\n=== Top Picks for {market} ===")
    
    # Get scan results
    resp = requests.get('http://localhost:8000/api/scan?market=US&date=2026-04-12', timeout=10)
    if resp.status_code != 200:
        print("No scan data")
        return
    
    scan_data = resp.json()
    results = scan_data.get('results', [])
    
    if not results:
        print("No results")
        return
    
    # Get picks
    resp = requests.post(
        f'http://localhost:8000/api/ml/top-picks/{market}',
        json={'results': results[:50], 'horizon': 5},
        timeout=15
    )
    
    if resp.status_code != 200:
        print(f"Failed to get picks: {resp.status_code}")
        return
    
    data = resp.json()
    if not data.get('success'):
        print(f"Error: {data.get('message')}")
        return
    
    picks = data.get('picks', [])
    print(f"\n🏆 TOP {len(picks)} PICKS:")
    
    for pick in picks[:5]:
        prob = pick['ml_probability'] * 100
        print(f"{pick['rank']}. {pick['ticker']} - {prob:.1f}% prob | Score: {pick['score']:.1f} | Price: ${pick['last_price']:.2f}")

if __name__ == '__main__':
    # Train models
    for market in ['US', 'IN']:
        try:
            train_market(market)
        except Exception as e:
            print(f"Error training {market}: {e}")
    
    # Get picks
    for market in ['US', 'IN']:
        try:
            get_picks(market)
        except Exception as e:
            print(f"Error getting picks for {market}: {e}")

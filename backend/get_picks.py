"""Get Top 10 ML Picks for US and Indian stocks."""
import requests

def get_picks(market):
    print(f"\n{'='*70}")
    print(f"TOP 10 ML PICKS - {market} STOCKS")
    print(f"{'='*70}")
    
    # 1. Get latest available date
    dates_resp = requests.get(f'http://localhost:8000/api/dates?market={market}', timeout=10)
    dates = dates_resp.json().get('dates', [])
    if not dates:
        print(f"No cached dates found for {market}!")
        return
    
    latest_date = dates[0]
    print(f"Using latest scan data from: {latest_date}")

    # 2. Get scan results
    resp = requests.get(f'http://localhost:8000/api/scan?market={market}&date={latest_date}', timeout=30)
    scan_data = resp.json()
    results = scan_data.get('results', [])
    print(f"Scan results: {len(results)} stocks\n")
    
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
        return
    
    picks = data.get('picks', [])
    
    for pick in picks:
        rank = pick['rank']
        if rank == 1:
            rank_icon = "🥇"
        elif rank == 2:
            rank_icon = "🥈"
        elif rank == 3:
            rank_icon = "🥉"
        else:
            rank_icon = f"{rank}."
        
        prob = pick['ml_probability'] * 100
        prob_bar = '█' * int(prob / 5) + '░' * (20 - int(prob / 5))
        
        name = pick['name'][:25] if pick['name'] else ""
        sector = pick['sector'] if pick['sector'] else "N/A"
        
        print(f"{rank_icon} {pick['ticker']:<6} ({name:<25}) | Prob: {prob_bar} {prob:>5.1f}% | Score: {pick['score']:.1f} | Stage {pick['stage']}")
        print(f"   Price: ${pick['last_price']:.2f} | RS: {pick['rs_1y']:.0f} | RSI: {pick['rsi']:.1f} | {sector}")
        
        if pick.get('top_features'):
            feats = ', '.join([f"{f['name']}={f['value']:.1f}" for f in pick['top_features'][:3]])
            print(f"   Features: {feats}")
        print()

if __name__ == '__main__':
    for market in ['US', 'IN']:
        try:
            get_picks(market)
        except Exception as e:
            print(f"Error getting {market} picks: {e}")
        print("\n")

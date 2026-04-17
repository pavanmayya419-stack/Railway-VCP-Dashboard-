import requests
import time

# Refresh US market data
print("Refreshing US market scan cache...")
resp = requests.post('http://localhost:8001/api/refresh', json={"market": "US"})
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print(f"Response: {resp.json()}")
    print("\nWaiting for scan to complete...")
    time.sleep(10)
    
    # Check the new scan data
    print("\nChecking new scan data...")
    scan_resp = requests.get('http://localhost:8001/api/scan?market=US')
    if scan_resp.status_code == 200:
        data = scan_resp.json()
        print(f"Total stocks: {data.get('count', 0)}")
        print("\nFirst 5 stocks with returns:")
        for item in data.get('results', [])[:5]:
            ticker = item.get('ticker')
            r1 = item.get('r1')
            r5 = item.get('r5')
            r63 = item.get('r63')
            r126 = item.get('r126')
            print(f"{ticker}: r1={r1}%, r5={r5}%, r63={r63}%, r126={r126}%")
else:
    print(f"Error: {resp.text}")

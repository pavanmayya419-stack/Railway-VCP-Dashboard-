"""
Refresh last 2 months of data for US and India markets
"""

import os
import sys
from datetime import datetime, timedelta
from refresh_data import generate_cache_for_market

def refresh_last_60_days():
    print("=" * 60)
    print("REFRESHING LAST 60 DAYS OF DATA")
    print("=" * 60)
    
    markets = ["US", "IN"]
    total_days = 60
    
    for market in markets:
        print(f"\n[{markets.index(market) + 1}/2] {market} Market - Last 60 Days")
        print("-" * 40)
        
        # Generate cache for today (which will have all available data)
        count, date = generate_cache_for_market(market, force=True)
        print(f"  Latest data: {count} stocks for {date}")
        
        # The function automatically gets the latest available data
        # We don't need to specify individual dates
    
    print("\n" + "=" * 60)
    print("REFRESH COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    refresh_last_60_days()

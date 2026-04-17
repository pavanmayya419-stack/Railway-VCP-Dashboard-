"""
Refresh last 2 months of data for India market only
"""

import os
import sys
from datetime import datetime, timedelta
from refresh_data import generate_cache_for_market

def refresh_india_last_60_days():
    print("=" * 60)
    print("REFRESHING LAST 60 DAYS - INDIA MARKET ONLY")
    print("=" * 60)
    
    print("\n[1/1] India (NSE) Market - Last 60 Days")
    print("-" * 40)
    
    # Generate cache for today with force refresh
    count, date = generate_cache_for_market("IN", force=True)
    print(f"  Latest data: {count} stocks for {date}")
    
    print("\n" + "=" * 60)
    print("INDIA MARKET REFRESH COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    refresh_india_last_60_days()

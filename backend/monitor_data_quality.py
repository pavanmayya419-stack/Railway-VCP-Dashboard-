"""
Data quality monitoring script.
Run this daily or weekly to detect data corruption early.
"""

import pandas as pd
import numpy as np
import os
import glob
import json
from datetime import datetime, timedelta
from data_validator import validate_returns, validate_price_data, MAX_DAILY_DROP
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SCAN_CACHE_DIR = os.path.join(os.path.dirname(__file__), "outputs", "scan_cache")
OHLCV_DIR = os.path.join(os.path.dirname(__file__), "outputs", "ohlcv")

def detect_stock_splits(df: pd.DataFrame, ticker: str) -> list:
    """Detect potential stock splits in the data."""
    splits = []
    
    if df is None or len(df) < 2:
        return splits
    
    daily_returns = df['Close'].pct_change().dropna() * 100
    
    # Look for extreme drops (>50% in a day)
    extreme_drops = daily_returns[daily_returns < MAX_DAILY_DROP]
    
    for date, drop in extreme_drops.items():
        prev_price = df['Close'].shift(1).loc[date]
        curr_price = df['Close'].loc[date]
        
        # Calculate possible split ratio
        if prev_price > 0 and curr_price > 0:
            ratio = prev_price / curr_price
            # Common split ratios: 2:1 (ratio ~2), 3:1 (ratio ~3), 4:1 (ratio ~4)
            if 1.8 <= ratio <= 2.2:
                splits.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'type': '2:1 split',
                    'ratio': ratio,
                    'drop': drop,
                    'prev_price': prev_price,
                    'curr_price': curr_price
                })
            elif 2.8 <= ratio <= 3.2:
                splits.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'type': '3:1 split',
                    'ratio': ratio,
                    'drop': drop,
                    'prev_price': prev_price,
                    'curr_price': curr_price
                })
            elif 3.8 <= ratio <= 4.2:
                splits.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'type': '4:1 split',
                    'ratio': ratio,
                    'drop': drop,
                    'prev_price': prev_price,
                    'curr_price': curr_price
                })
            else:
                splits.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'type': f'unusual ({ratio:.1f}:1)',
                    'ratio': ratio,
                    'drop': drop,
                    'prev_price': prev_price,
                    'curr_price': curr_price
                })
    
    return splits

def check_scan_cache_quality():
    """Check the scan cache for corrupted return values."""
    log.info("Checking scan cache quality...")
    
    issues = []
    cache_files = glob.glob(os.path.join(SCAN_CACHE_DIR, "US_*.pkl"))
    
    if not cache_files:
        log.warning("No scan cache files found")
        return issues
    
    # Get the most recent cache file
    latest_cache = max(cache_files, key=os.path.getmtime)
    
    try:
        import pickle
        with open(latest_cache, 'rb') as f:
            data = pickle.load(f)
        
        log.info(f"Checking {len(data)} stocks in cache: {os.path.basename(latest_cache)}")
        
        corrupted_count = 0
        for item in data:
            ticker = item.get('ticker', 'UNKNOWN')
            
            # Check for extreme returns
            for period in ['r1', 'r5', 'r21', 'r63', 'r126']:
                ret = item.get(period)
                if ret is not None:
                    if ret > 200 or ret < -95:  # Extreme values
                        issues.append({
                            'ticker': ticker,
                            'issue': f'Extreme {period}',
                            'value': ret,
                            'severity': 'HIGH'
                        })
                        corrupted_count += 1
                        break
        
        log.info(f"Found {corrupted_count} corrupted entries in scan cache")
        
    except Exception as e:
        log.error(f"Error checking scan cache: {e}")
    
    return issues

def check_csv_data_quality(sample_size: int = 50):
    """Check CSV files for data quality issues."""
    log.info(f"Checking CSV data quality (sample of {sample_size} stocks)...")
    
    issues = []
    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    
    # Filter out Indian stocks and special files
    us_files = [f for f in csv_files if not f.endswith('_NS.csv') and 
                not any(x in f for x in ['sp500_constituents', 'fyers_tickers', 'nifty500'])]
    
    # Sample files
    import random
    sample_files = random.sample(us_files, min(sample_size, len(us_files)))
    
    for file_path in sample_files:
        ticker = os.path.basename(file_path).replace('.csv', '').replace('_', '.')
        
        try:
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            
            # Handle timezone
            if df.index.tz is not None:
                df.index = df.index.tz_convert('UTC').tz_localize(None)
            
            # Check for stock splits
            splits = detect_stock_splits(df, ticker)
            if splits:
                issues.append({
                    'ticker': ticker,
                    'issue': f"Stock split detected: {len(splits)} event(s)",
                    'details': splits,
                    'severity': 'MEDIUM'
                })
            
            # Validate returns
            valid, return_issues = validate_returns(df, ticker)
            if not valid:
                issues.append({
                    'ticker': ticker,
                    'issue': f"Return validation failed: {return_issues[:2]}",
                    'severity': 'HIGH' if any('split' in str(i) for i in return_issues) else 'MEDIUM'
                })
            
        except Exception as e:
            issues.append({
                'ticker': ticker,
                'issue': f"Error loading: {str(e)[:50]}",
                'severity': 'HIGH'
            })
    
    log.info(f"Found {len(issues)} issues in CSV data")
    return issues

def generate_report():
    """Generate a comprehensive data quality report."""
    log.info("=" * 60)
    log.info("DATA QUALITY MONITORING REPORT")
    log.info("=" * 60)
    log.info(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("")
    
    # Check scan cache
    scan_issues = check_scan_cache_quality()
    
    # Check CSV files
    csv_issues = check_csv_data_quality(sample_size=50)
    
    all_issues = scan_issues + csv_issues
    
    # Categorize issues
    high_severity = [i for i in all_issues if i.get('severity') == 'HIGH']
    medium_severity = [i for i in all_issues if i.get('severity') == 'MEDIUM']
    
    log.info(f"\nSUMMARY:")
    log.info(f"  Total issues: {len(all_issues)}")
    log.info(f"  HIGH severity: {len(high_severity)}")
    log.info(f"  MEDIUM severity: {len(medium_severity)}")
    
    if high_severity:
        log.info(f"\n⚠️  HIGH SEVERITY ISSUES (Require immediate attention):")
        for issue in high_severity[:10]:  # Show first 10
            log.info(f"  • {issue['ticker']}: {issue['issue']}")
            if 'value' in issue:
                log.info(f"    Value: {issue['value']}")
    
    if medium_severity:
        log.info(f"\n⚡ MEDIUM SEVERITY ISSUES (Monitor):")
        for issue in medium_severity[:10]:  # Show first 10
            log.info(f"  • {issue['ticker']}: {issue['issue']}")
    
    # Recommendations
    log.info(f"\n📋 RECOMMENDATIONS:")
    if high_severity:
        log.info("  1. Clear scan cache and regenerate: python refresh_data.py")
        log.info("  2. Check parquet files for corrupted data")
        log.info("  3. Re-download affected tickers from yfinance")
    else:
        log.info("  ✓ Data quality looks good!")
        log.info("  • Continue daily monitoring")
        log.info("  • Run this check weekly or after major updates")
    
    log.info(f"\n" + "=" * 60)
    
    # Save report to file
    report_file = os.path.join(os.path.dirname(__file__), "data_quality_report.json")
    with open(report_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_issues': len(all_issues),
            'high_severity': len(high_severity),
            'medium_severity': len(medium_severity),
            'issues': all_issues
        }, f, indent=2, default=str)
    
    log.info(f"Report saved to: {report_file}")
    
    return len(high_severity) == 0  # Return True if no high severity issues

def clear_corrupted_cache():
    """Clear scan cache if corrupted data detected."""
    log.info("Checking if cache needs clearing...")
    
    scan_issues = check_scan_cache_quality()
    high_severity = [i for i in scan_issues if i.get('severity') == 'HIGH']
    
    if len(high_severity) > 5:  # If more than 5 corrupted entries
        log.warning(f"Found {len(high_severity)} corrupted entries. Clearing cache...")
        
        cache_files = glob.glob(os.path.join(SCAN_CACHE_DIR, "US_*.pkl"))
        for f in cache_files:
            try:
                os.remove(f)
                log.info(f"  Deleted: {os.path.basename(f)}")
            except Exception as e:
                log.error(f"  Failed to delete {f}: {e}")
        
        log.info("Cache cleared. Run refresh_data.py to regenerate.")
        return True
    
    log.info("Cache looks healthy.")
    return False

if __name__ == "__main__":
    import sys
    
    # Check command line args
    if len(sys.argv) > 1 and sys.argv[1] == '--auto-fix':
        # Auto-fix mode: clear cache if corrupted
        clear_corrupted_cache()
    else:
        # Normal monitoring mode
        healthy = generate_report()
        
        # Exit with error code if issues found
        if not healthy:
            sys.exit(1)

"""
Data validation and quality control module.
Prevents corrupted data from entering the scan cache.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

log = logging.getLogger(__name__)

# Validation thresholds
MAX_REASONABLE_RETURN = 200.0  # Max 200% return (2x) for any period
MIN_REASONABLE_RETURN = -95.0  # Min -95% (stock can't go below zero)
MAX_DAILY_DROP = -50.0  # Max 50% daily drop (indicates split issue)
MAX_VOLUME_SPIKE = 10.0  # Max 10x volume spike

def validate_returns(df: pd.DataFrame, ticker: str) -> Tuple[bool, List[str]]:
    """
    Validate return calculations for a stock.
    Returns (is_valid, list_of_issues)
    """
    issues = []
    
    if df is None or df.empty or len(df) < 10:
        return False, ["Insufficient data"]
    
    # Check for extreme daily returns (indicates stock split)
    daily_returns = df['Close'].pct_change().dropna() * 100
    extreme_drops = daily_returns[daily_returns < MAX_DAILY_DROP]
    
    if len(extreme_drops) > 0:
        issues.append(f"Stock split detected: {len(extreme_drops)} drops > {abs(MAX_DAILY_DROP)}%")
        for date, val in extreme_drops.head(3).items():
            issues.append(f"  {date.strftime('%Y-%m-%d')}: {val:.1f}%")
    
    # Calculate multi-period returns
    if len(df) >= 126:
        returns = {
            'R1': (df['Close'].iloc[-1] / df['Close'].iloc[-2] - 1) * 100 if len(df) >= 2 else 0,
            'R5': (df['Close'].iloc[-1] / df['Close'].iloc[-6] - 1) * 100 if len(df) >= 6 else 0,
            'R21': (df['Close'].iloc[-1] / df['Close'].iloc[-22] - 1) * 100 if len(df) >= 22 else 0,
            'R63': (df['Close'].iloc[-1] / df['Close'].iloc[-64] - 1) * 100 if len(df) >= 64 else 0,
            'R126': (df['Close'].iloc[-1] / df['Close'].iloc[-127] - 1) * 100 if len(df) >= 127 else 0,
        }
        
        # Check for unreasonable returns
        for period, ret in returns.items():
            if ret > MAX_REASONABLE_RETURN:
                issues.append(f"{period} too high: {ret:.1f}% (max: {MAX_REASONABLE_RETURN}%)")
            elif ret < MIN_REASONABLE_RETURN:
                issues.append(f"{period} too low: {ret:.1f}% (min: {MIN_REASONABLE_RETURN}%)")
    
    # Check price consistency
    recent_prices = df['Close'].tail(10)
    if recent_prices.std() / recent_prices.mean() > 0.5:  # High volatility in last 10 days
        # Check for sudden jumps (possible split)
        for i in range(1, len(recent_prices)):
            prev, curr = recent_prices.iloc[i-1], recent_prices.iloc[i]
            if prev > 0:
                change = (curr / prev - 1) * 100
                if abs(change) > 40:  # >40% single day move
                    issues.append(f"Suspicious price jump: {change:.1f}% on {recent_prices.index[i].strftime('%Y-%m-%d')}")
    
    return len(issues) == 0, issues

def validate_price_data(df: pd.DataFrame, ticker: str) -> Tuple[bool, List[str]]:
    """
    Validate price data integrity.
    """
    issues = []
    
    if df is None or df.empty:
        return False, ["No data"]
    
    # Check required columns
    required = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing = [c for c in required if c not in df.columns]
    if missing:
        issues.append(f"Missing columns: {missing}")
    
    # Check for negative prices
    for col in ['Open', 'High', 'Low', 'Close']:
        if col in df.columns and (df[col] < 0).any():
            issues.append(f"Negative values in {col}")
    
    # Check High >= Low
    if 'High' in df.columns and 'Low' in df.columns:
        invalid_hl = (df['High'] < df['Low']).sum()
        if invalid_hl > 0:
            issues.append(f"{invalid_hl} rows where High < Low")
    
    # Check for zero volume
    if 'Volume' in df.columns and (df['Volume'] == 0).all():
        issues.append("All volumes are zero")
    
    # Check for duplicate dates
    if df.index.duplicated().any():
        issues.append(f"{df.index.duplicated().sum()} duplicate dates")
    
    # Check date range
    if len(df) < 60:
        issues.append(f"Only {len(df)} rows, need at least 60")
    
    return len(issues) == 0, issues

def validate_and_clean_data(df: pd.DataFrame, ticker: str) -> Tuple[Optional[pd.DataFrame], List[str]]:
    """
    Validate data and return cleaned DataFrame or None if invalid.
    """
    # First validate price data
    valid_price, price_issues = validate_price_data(df, ticker)
    if not valid_price:
        log.warning(f"{ticker}: Price data validation failed: {price_issues}")
        return None, price_issues
    
    # Then validate returns
    valid_returns, return_issues = validate_returns(df, ticker)
    if not valid_returns:
        log.warning(f"{ticker}: Return validation failed: {return_issues}")
        # Don't reject entirely, just flag for review
    
    all_issues = price_issues + return_issues
    
    # Clean the data
    df_clean = df.copy()
    
    # Remove rows with NaN in critical columns
    df_clean = df_clean.dropna(subset=['Close', 'Volume'])
    
    # Ensure index is datetime
    if not isinstance(df_clean.index, pd.DatetimeIndex):
        try:
            df_clean.index = pd.to_datetime(df_clean.index)
        except:
            return None, ["Cannot convert index to datetime"]
    
    # Sort by date
    df_clean = df_clean.sort_index()
    
    # Remove duplicates (keep last)
    df_clean = df_clean[~df_clean.index.duplicated(keep='last')]
    
    return df_clean, all_issues

def get_data_quality_report(tickers: List[str], data_dir: str) -> Dict:
    """
    Generate a data quality report for all tickers.
    """
    import os
    
    report = {
        'total': len(tickers),
        'valid': 0,
        'invalid': 0,
        'issues_by_ticker': {},
        'common_issues': {}
    }
    
    for ticker in tickers:
        csv_path = os.path.join(data_dir, f"{ticker.replace('.', '_')}.csv")
        
        if not os.path.exists(csv_path):
            report['issues_by_ticker'][ticker] = ["File not found"]
            report['invalid'] += 1
            continue
        
        try:
            df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
            
            # Handle timezone
            if df.index.tz is not None:
                df.index = df.index.tz_convert('UTC').tz_localize(None)
            
            valid, issues = validate_price_data(df, ticker)
            valid_ret, ret_issues = validate_returns(df, ticker)
            
            all_issues = issues + ret_issues
            
            if all_issues:
                report['issues_by_ticker'][ticker] = all_issues
                report['invalid'] += 1
                
                # Count common issues
                for issue in all_issues:
                    issue_type = issue.split(':')[0] if ':' in issue else issue
                    report['common_issues'][issue_type] = report['common_issues'].get(issue_type, 0) + 1
            else:
                report['valid'] += 1
                
        except Exception as e:
            report['issues_by_ticker'][ticker] = [f"Error loading: {str(e)}"]
            report['invalid'] += 1
    
    return report

if __name__ == "__main__":
    import glob
    import os
    
    # Test validation
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    
    # Find all CSV files
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    tickers = [os.path.basename(f).replace('.csv', '').replace('_', '.') 
              for f in csv_files if not f.endswith('_NS.csv')]
    
    print(f"Validating {len(tickers)} US stocks...")
    print("=" * 60)
    
    report = get_data_quality_report(tickers[:20], data_dir)  # Check first 20
    
    print(f"\nValid: {report['valid']}/{report['total']}")
    print(f"Invalid: {report['invalid']}/{report['total']}")
    
    if report['issues_by_ticker']:
        print("\nIssues found:")
        for ticker, issues in list(report['issues_by_ticker'].items())[:10]:
            print(f"  {ticker}: {issues}")
    
    if report['common_issues']:
        print("\nCommon issues:")
        for issue, count in report['common_issues'].items():
            print(f"  {issue}: {count} occurrences")

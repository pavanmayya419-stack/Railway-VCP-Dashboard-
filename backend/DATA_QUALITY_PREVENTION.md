# Data Quality Prevention Guide

## Problem Fixed
The dashboard was showing extreme percentage values like **26557.5%** due to:
1. **Corrupted parquet cache** with unadjusted stock split data
2. **Timezone parsing issues** in CSV files
3. **No data validation** before using data in calculations

## Prevention Measures Implemented

### 1. Data Validator Module (`data_validator.py`)
**Purpose:** Automatically detect and flag corrupted data

**Features:**
- Detects stock splits (price drops >50% in a day)
- Validates return calculations (max 200%, min -95%)
- Checks price consistency (High >= Low, no negative prices)
- Identifies duplicate dates and missing data

**Usage:**
```python
from data_validator import validate_and_clean_data

df_clean, issues = validate_and_clean_data(df, ticker='AAPL')
if issues:
    print(f"Data issues found: {issues}")
```

### 2. Engine Integration (`engine.py`)
**Change:** Added automatic validation when loading CSV files

```python
# In fetch_data() function - now validates all loaded data
df_clean, issues = validate_and_clean_data(df, ticker)
if issues:
    print(f"[WARN] {ticker} data issues: {issues[:3]}")
```

### 3. Monitoring Script (`monitor_data_quality.py`)
**Purpose:** Daily/weekly automated data quality checks

**Run manually:**
```bash
cd backend
python monitor_data_quality.py
```

**Run with auto-fix (clears corrupted cache):**
```bash
python monitor_data_quality.py --auto-fix
```

**What it checks:**
- Scan cache for extreme return values (>200% or <-95%)
- CSV files for stock splits and data corruption
- Price data integrity (High >= Low, no negative values)
- Return calculation sanity checks

**Output:**
- Console report with HIGH/MEDIUM severity issues
- JSON report saved to `data_quality_report.json`
- Recommendations for fixing issues

### 4. Automated Safeguards

**Stock Split Detection:**
- Automatically detects when prices drop >50% in one day
- Calculates split ratios (2:1, 3:1, 4:1)
- Flags data for manual review

**Return Validation:**
- 1D returns: Must be between -50% and +50%
- 5D returns: Must be between -80% and +100%
- 3M/6M returns: Must be between -95% and +200%

**Price Validation:**
- High must be >= Low
- Close must be between High and Low
- Volume must be > 0
- No negative prices allowed

## Regular Maintenance Procedures

### Daily (Before Market Open)
```bash
# 1. Check data quality
python monitor_data_quality.py

# 2. If issues found, regenerate scan cache
python refresh_data.py
```

### Weekly (Sunday Evening)
```bash
# Full data quality check with sample
python monitor_data_quality.py

# Review report
cat data_quality_report.json | python -m json.tool
```

### After Major Events
Run after:
- Stock splits announcements
- Market crashes (>10% drop)
- Data provider changes
- System updates

```bash
# Clear all caches and regenerate
rm -rf outputs/scan_cache/*.pkl
rm -rf outputs/ohlcv/US/*.parquet
python refresh_data.py
```

## Troubleshooting

### Issue: Extreme percentage values in dashboard
**Solution:**
```bash
# 1. Check for corrupted data
python monitor_data_quality.py

# 2. Clear scan cache
rm outputs/scan_cache/US_*.pkl

# 3. Regenerate with fresh data
python refresh_data.py

# 4. Restart backend
# (Stop and restart python main.py)
```

### Issue: Stock split not adjusted
**Symptoms:** Prices show sudden 50%+ drop, returns calculation wrong

**Solution:**
```bash
# 1. Delete the specific ticker parquet file
rm outputs/ohlcv/US/TICKER.parquet

# 2. Re-download data
python -c "from ohlcv_store import download_ticker; download_ticker('TICKER', 'US', force=True)"

# 3. Regenerate scan cache
python refresh_data.py
```

### Issue: Timezone errors in logs
**Solution:** Data validator now handles this automatically. If persists:
```bash
# Re-download affected tickers
python -c "from ohlcv_store import bulk_download; bulk_download('US', ['TICKER1', 'TICKER2'], force=True)"
```

## Data Quality Report Format

The monitoring script generates `data_quality_report.json`:

```json
{
  "timestamp": "2026-04-15T20:42:05",
  "total_issues": 15,
  "high_severity": 3,
  "medium_severity": 12,
  "issues": [
    {
      "ticker": "MSFT",
      "issue": "Stock split detected: 1 event(s)",
      "severity": "MEDIUM"
    }
  ]
}
```

## Best Practices

1. **Always monitor after market crashes** - Volatile periods can cause data issues
2. **Check splits calendar** - Be aware of upcoming stock splits
3. **Use force=True sparingly** - Only when data is known to be corrupted
4. **Keep CSV backups** - Parquet cache can be regenerated from CSV
5. **Run monitoring weekly** - Catches issues before they affect dashboard
6. **Review logs daily** - Look for [WARN] messages in backend logs

## Emergency Contacts (If Implemented)

- Data quality alerts: Check `data_quality_report.json`
- System logs: Backend console output
- Cache status: `outputs/scan_cache/` directory
- Raw data: `data/` directory (CSV files)

---

**Last Updated:** 2026-04-15  
**Version:** 1.0  
**Applies To:** VCP Dashboard US Market

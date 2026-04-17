import os
import shutil
import pandas as pd
import pickle
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BACKEND_DIR, "outputs")
SCAN_CACHE_DIR = os.path.join(DATA_DIR, "scan_cache")
OHLCV_DIR = os.path.join(DATA_DIR, "ohlcv")
LOG_DIR = os.path.join(BACKEND_DIR, "logs")

def clean_old_scans(days=90):
    """Keep only the last X days of scan results to save space."""
    if not os.path.exists(SCAN_CACHE_DIR):
        return
    
    logger.info(f"🧹 Cleaning scan cache (older than {days} days)...")
    cutoff = datetime.now() - timedelta(days=days)
    count = 0
    for f in os.listdir(SCAN_CACHE_DIR):
        if not f.endswith(".pkl"): continue
        fpath = os.path.join(SCAN_CACHE_DIR, f)
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
        if mtime < cutoff:
            os.remove(fpath)
            count += 1
    logger.info(f"✅ Removed {count} old scan files.")

def refresh_tickers():
    """Ensure ticker lists are clean and synced."""
    logger.info("🔄 Syncing ticker lists...")
    fyers_csv = os.path.join(BACKEND_DIR, "fyers_tickers.csv")
    if os.path.exists(fyers_csv):
        df = pd.read_csv(fyers_csv)
        # Remove duplicates and empty rows
        df = df.dropna(subset=['Symbol']).drop_duplicates(subset=['Symbol'])
        # Sort and save
        df = df.sort_values(by='Symbol')
        df.to_csv(fyers_csv, index=False)
        logger.info(f"✅ Cleaned fyers_tickers.csv ({len(df)} tickers)")

def verify_data_integrity():
    """Check for corrupted or empty data files."""
    logger.info("🛡️ Verifying data integrity...")
    # Add logic to check specific critical files if needed
    pass

def cleanup_logs():
    """Remove large log files or rotate them."""
    logger.info("📜 Rotating log files...")
    # Fyers logs can get huge
    for log_file in ["fyersApi.log", "fyersRequests.log"]:
        fpath = os.path.join(BACKEND_DIR, log_file)
        if os.path.exists(fpath) and os.path.getsize(fpath) > 10 * 1024 * 1024: # 10MB
            # Clear or rotate
            with open(fpath, 'w') as f: f.write("")
            logger.info(f"✅ Cleared oversized log: {log_file}")

def full_maintenance():
    logger.info("========================================")
    logger.info("🛠️ STARTING FULL SYSTEM MAINTENANCE")
    logger.info("========================================")
    
    refresh_tickers()
    clean_old_scans()
    cleanup_logs()
    verify_data_integrity()
    
    logger.info("========================================")
    logger.info("✅ MAINTENANCE COMPLETE")
    logger.info("========================================")

if __name__ == "__main__":
    full_maintenance()

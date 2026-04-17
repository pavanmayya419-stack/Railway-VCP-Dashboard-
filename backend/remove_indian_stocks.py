"""
Remove Indian stock data files (.NS suffix) from the data directory.
"""

import os
import glob
import shutil
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Configuration
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "backup_indian_stocks")

def remove_indian_stocks():
    """Remove or backup Indian stock files."""
    
    # Create backup directory
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Find all Indian stock files
    indian_files = glob.glob(os.path.join(DATA_DIR, "*_NS.csv"))
    
    log.info(f"Found {len(indian_files)} Indian stock files")
    
    removed = 0
    failed = 0
    
    for file_path in indian_files:
        try:
            filename = os.path.basename(file_path)
            backup_path = os.path.join(BACKUP_DIR, filename)
            
            # Move to backup instead of delete
            shutil.move(file_path, backup_path)
            removed += 1
            
            if removed <= 10:  # Show first few
                log.info(f"Moved: {filename}")
                
        except Exception as e:
            log.error(f"Failed to move {filename}: {e}")
            failed += 1
    
    log.info(f"\nComplete!")
    log.info(f"Moved: {removed} files to backup directory")
    log.info(f"Failed: {failed} files")
    log.info(f"Backup location: {BACKUP_DIR}")
    
    # Show remaining files
    remaining = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    us_files = [f for f in remaining if not f.endswith('_NS.csv')]
    log.info(f"\nRemaining US stock files: {len(us_files)}")
    
    return removed, failed

def clean_other_files():
    """Remove other India-related files."""
    
    other_files = [
        'fyers_tickers.csv',
        'nifty500.csv'
    ]
    
    log.info("\nChecking for other India-related files...")
    
    for filename in other_files:
        file_path = os.path.join(DATA_DIR, filename)
        if os.path.exists(file_path):
            try:
                backup_path = os.path.join(BACKUP_DIR, filename)
                shutil.move(file_path, backup_path)
                log.info(f"Moved: {filename}")
            except Exception as e:
                log.error(f"Failed to move {filename}: {e}")

def main():
    """Main function."""
    log.info("="*60)
    log.info("REMOVING INDIAN STOCK DATA")
    log.info("="*60)
    
    # Remove Indian stock files
    removed, failed = remove_indian_stocks()
    
    # Clean other files
    clean_other_files()
    
    log.info("\n" + "="*60)
    log.info("CLEANUP COMPLETE")
    log.info("="*60)
    
    # Show final count
    all_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    us_files = [f for f in all_files if not f.endswith('_NS.csv')]
    log.info(f"Final US stock count: {len(us_files)}")

if __name__ == "__main__":
    main()

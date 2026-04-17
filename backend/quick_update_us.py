"""
Quick update US stock data with 2 years history and metadata.
"""

import pandas as pd
import numpy as np
import os
import time
import logging
from datetime import datetime
import yfinance as yf
import glob

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Configuration
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
METADATA_FILE = os.path.join(DATA_DIR, "us_stock_metadata.csv")

def get_us_symbols():
    """Get US stock symbols from existing files."""
    symbols = []
    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    
    for file in csv_files:
        filename = os.path.basename(file)
        symbol = filename.replace('.csv', '')
        
        if not symbol.endswith('_NS') and symbol not in ['sp500_constituents', 'fyers_tickers', 'nifty500']:
            symbols.append(symbol)
    
    return symbols

def download_data_with_metadata(symbols):
    """Download data and metadata for symbols."""
    log.info(f"Processing {len(symbols)} symbols...")
    
    metadata_list = []
    success = 0
    failed = 0
    
    for i, symbol in enumerate(symbols):
        try:
            # Download price data
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2y", auto_adjust=True)
            
            if hist is not None and not hist.empty:
                # Clean and save price data
                hist.columns = [col.title() for col in hist.columns]
                hist = hist[['Open', 'High', 'Low', 'Close', 'Volume']]
                hist.to_csv(os.path.join(DATA_DIR, f"{symbol}.csv"))
                
                # Get metadata
                info = ticker.info
                if info:
                    metadata_list.append({
                        'Symbol': symbol,
                        'MarketCap': info.get('marketCap', np.nan),
                        'Sector': info.get('sector', 'Unknown'),
                        'Industry': info.get('industry', 'Unknown'),
                        'CurrentPrice': info.get('regularMarketPrice', np.nan),
                        'PE_Ratio': info.get('forwardPE', np.nan),
                        'Beta': info.get('beta', np.nan),
                        'LastUpdated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                success += 1
            else:
                failed += 1
                
        except Exception as e:
            failed += 1
            if i < 10:
                log.warning(f"Failed {symbol}: {e}")
        
        # Progress update
        if (i + 1) % 50 == 0:
            log.info(f"Progress: {i+1}/{len(symbols)} - Success: {success}, Failed: {failed}")
        
        # Rate limiting
        time.sleep(0.1)
    
    return metadata_list, success, failed

def main():
    """Main function."""
    start_time = time.time()
    
    log.info("="*60)
    log.info("QUICK UPDATE US STOCK DATA WITH METADATA")
    log.info("="*60)
    
    # Get symbols
    symbols = get_us_symbols()
    log.info(f"Found {len(symbols)} US stock symbols")
    
    # Download data and metadata
    metadata, success, failed = download_data_with_metadata(symbols)
    
    # Process and save metadata
    if metadata:
        df = pd.DataFrame(metadata)
        
        # Add market cap category
        def categorize(mcap):
            if pd.isna(mcap) or mcap <= 0:
                return "Unknown"
            elif mcap >= 200_000_000_000:
                return "Mega-Cap"
            elif mcap >= 10_000_000_000:
                return "Large-Cap"
            elif mcap >= 2_000_000_000:
                return "Mid-Cap"
            elif mcap >= 250_000_000:
                return "Small-Cap"
            else:
                return "Micro-Cap"
        
        df['MarketCapCategory'] = df['MarketCap'].apply(categorize)
        df.to_csv(METADATA_FILE, index=False)
        
        log.info("\nMarket Cap Distribution:")
        log.info(df['MarketCapCategory'].value_counts().to_string())
        
        log.info("\nTop Sectors:")
        log.info(df['Sector'].value_counts().head(10).to_string())
    
    # Summary
    elapsed = time.time() - start_time
    log.info("\n" + "="*60)
    log.info("UPDATE COMPLETE")
    log.info(f"Total processed: {len(symbols)}")
    log.info(f"Success: {success}, Failed: {failed}")
    log.info(f"Metadata records: {len(metadata) if metadata else 0}")
    log.info(f"Time: {elapsed/60:.1f} minutes")
    log.info("="*60)

if __name__ == "__main__":
    main()

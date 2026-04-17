"""
Update existing US stock data with 2 years of history and add metadata.
Focus on stocks that are already cached to ensure we have comprehensive data.
"""

import pandas as pd
import numpy as np
import os
import time
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf
import glob

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Configuration
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
METADATA_FILE = os.path.join(DATA_DIR, "us_stock_metadata.csv")

def get_existing_us_stocks():
    """Get list of existing US stock CSV files."""
    us_stocks = []
    
    # Get all CSV files
    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    
    for file in csv_files:
        filename = os.path.basename(file)
        symbol = filename.replace('.csv', '')
        
        # Filter for US stocks (no .NS suffix and not special files)
        if not symbol.endswith('_NS') and not symbol in ['sp500_constituents', 'fyers_tickers', 'nifty500']:
            # Check if file has data
            try:
                df = pd.read_csv(file, parse_dates=['Date'], index_col='Date')
                if len(df) > 100:  # Has substantial data
                    us_stocks.append(symbol)
            except:
                pass
    
    log.info(f"Found {len(us_stocks)} existing US stock files")
    return us_stocks

def update_price_data(symbols, period="2y"):
    """Update price data for existing symbols."""
    log.info(f"Updating price data for {len(symbols)} symbols...")
    
    def update_single(symbol):
        try:
            # Check existing data
            filename = os.path.join(DATA_DIR, f"{symbol}.csv")
            
            # Read existing data to see last date
            if os.path.exists(filename):
                existing_df = pd.read_csv(filename, parse_dates=['Date'], index_col='Date')
                if not existing_df.empty:
                    last_date = existing_df.index.max()
                    days_old = (datetime.now() - last_date).days
                    
                    # If data is recent, skip
                    if days_old <= 2:
                        return True, "Skipped (recent)"
            
            # Download new data
            time.sleep(0.05)  # Rate limiting
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, auto_adjust=True, timeout=10)
            
            if hist is not None and not hist.empty and len(hist) >= 60:
                # Clean up column names
                hist.columns = [col.title() for col in hist.columns]
                hist = hist[['Open', 'High', 'Low', 'Close', 'Volume']]
                
                # Save to CSV
                hist.to_csv(filename)
                return True, "Updated"
            else:
                return False, "Insufficient data"
                
        except Exception as e:
            return False, str(e)
    
    # Update with threading
    success = 0
    skipped = 0
    failed = 0
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(update_single, symbol): symbol for symbol in symbols}
        
        for i, future in enumerate(as_completed(futures)):
            symbol = futures[future]
            try:
                ok, msg = future.result()
                if ok:
                    if msg == "Skipped (recent)":
                        skipped += 1
                    else:
                        success += 1
                else:
                    failed += 1
                    if i < 20:  # Show first few errors
                        log.warning(f"Failed {symbol}: {msg}")
            except Exception as e:
                failed += 1
                log.error(f"Error processing {symbol}: {e}")
            
            if (i + 1) % 100 == 0:
                log.info(f"Progress: {i+1}/{len(symbols)} - Updated: {success}, Skipped: {skipped}, Failed: {failed}")
    
    log.info(f"Update complete - Updated: {success}, Skipped: {skipped}, Failed: {failed}")
    return success, skipped, failed

def get_metadata(symbols, batch_size=50):
    """Get metadata for symbols."""
    log.info(f"Fetching metadata for {len(symbols)} symbols...")
    
    # Load existing metadata if available
    existing_metadata = pd.DataFrame()
    if os.path.exists(METADATA_FILE):
        existing_metadata = pd.read_csv(METADATA_FILE)
        log.info(f"Loaded {len(existing_metadata)} existing metadata records")
    
    all_info = []
    
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        log.info(f"Processing batch {i//batch_size + 1}/{(len(symbols)-1)//batch_size + 1}")
        
        for symbol in batch:
            try:
                # Check if we already have recent metadata
                if not existing_metadata.empty:
                    existing = existing_metadata[existing_metadata['Symbol'] == symbol]
                    if not existing.empty:
                        last_update = pd.to_datetime(existing['LastUpdated'].iloc[0])
                        if (datetime.now() - last_update).days < 7:
                            all_info.append(existing.iloc[0].to_dict())
                            continue
                
                # Fetch new metadata
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                if info and 'regularMarketPrice' in info:
                    all_info.append({
                        'Symbol': symbol,
                        'MarketCap': info.get('marketCap', np.nan),
                        'Sector': info.get('sector', 'Unknown'),
                        'Industry': info.get('industry', 'Unknown'),
                        'CurrentPrice': info.get('regularMarketPrice', np.nan),
                        'Volume': info.get('regularMarketVolume', np.nan),
                        'PE_Ratio': info.get('forwardPE', np.nan),
                        'DividendYield': info.get('dividendYield', np.nan),
                        'Beta': info.get('beta', np.nan),
                        'EPS': info.get('trailingEps', np.nan),
                        'LastUpdated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                if i < 5:  # Show first few errors
                    log.warning(f"Error fetching info for {symbol}: {e}")
    
    return pd.DataFrame(all_info)

def categorize_market_cap(market_cap):
    """Categorize stocks by market cap."""
    if pd.isna(market_cap) or market_cap <= 0:
        return "Unknown"
    elif market_cap >= 200_000_000_000:  # $200B+
        return "Mega-Cap"
    elif market_cap >= 10_000_000_000:  # $10B-$200B
        return "Large-Cap"
    elif market_cap >= 2_000_000_000:  # $2B-$10B
        return "Mid-Cap"
    elif market_cap >= 250_000_000:  # $250M-$2B
        return "Small-Cap"
    else:
        return "Micro-Cap"

def main():
    """Main execution function."""
    start_time = time.time()
    
    # Create data directory if it doesn't exist
    os.makedirs(DATA_DIR, exist_ok=True)
    
    log.info("="*60)
    log.info("UPDATING EXISTING US STOCK DATA")
    log.info("="*60)
    
    # Step 1: Get existing US stocks
    symbols = get_existing_us_stocks()
    
    if not symbols:
        log.error("No existing US stock files found!")
        return
    
    log.info(f"Found {len(symbols)} US stocks to update")
    
    # Step 2: Update price data
    log.info("\nStep 1: Updating price data...")
    success, skipped, failed = update_price_data(symbols, period="2y")
    
    # Step 3: Get metadata
    log.info("\nStep 2: Fetching metadata...")
    metadata = get_metadata(symbols)
    
    if not metadata.empty:
        # Add market cap category
        metadata['MarketCapCategory'] = metadata['MarketCap'].apply(categorize_market_cap)
        
        # Save metadata
        metadata.to_csv(METADATA_FILE, index=False)
        
        # Log distributions
        log.info("\nMarket Cap Distribution:")
        log.info(metadata['MarketCapCategory'].value_counts().to_string())
        
        log.info("\nTop 10 Sectors:")
        log.info(metadata['Sector'].value_counts().head(10).to_string())
    
    # Step 4: Summary
    elapsed = time.time() - start_time
    log.info("\n" + "="*60)
    log.info("UPDATE COMPLETE")
    log.info(f"Total symbols processed: {len(symbols)}")
    log.info(f"Price data - Updated: {success}, Skipped: {skipped}, Failed: {failed}")
    log.info(f"Metadata records: {len(metadata) if not metadata.empty else 0}")
    log.info(f"Time elapsed: {elapsed/60:.1f} minutes")
    log.info(f"Data saved to: {DATA_DIR}")
    log.info(f"Metadata saved to: {METADATA_FILE}")
    log.info("="*60)

if __name__ == "__main__":
    main()

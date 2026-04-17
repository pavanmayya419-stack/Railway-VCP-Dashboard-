"""
Update US market data for top 2000 stocks with 2 years of history.
Includes market cap and sector information for dashboard filtering.
"""

import pandas as pd
import numpy as np
import os
import time
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Configuration
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
METADATA_FILE = os.path.join(DATA_DIR, "us_stock_metadata.csv")
TOP_2000_FILE = os.path.join(os.path.dirname(__file__), "top_2000_us_stocks.csv")

def get_top_2000_us_stocks():
    """Get top 2000 US stocks by market cap using yfinance screener approach."""
    log.info("Fetching top 2000 US stocks by market cap...")
    
    # Start with major indices constituents
    major_stocks = []
    
    # S&P 500 (largest 500)
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        sp500_symbols = sp500['Symbol'].str.replace('.', '-').tolist()
        major_stocks.extend(sp500_symbols)
        log.info(f"Got {len(sp500_symbols)} S&P 500 stocks")
    except Exception as e:
        log.warning(f"Failed to fetch S&P 500: {e}")
        major_stocks.extend(['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'JPM', 'V', 'JNJ'])
    
    # NASDAQ 100 (largest 100 non-financial)
    try:
        nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/NASDAQ-100')[0]
        nasdaq100_symbols = nasdaq100['Ticker'].tolist()
        major_stocks.extend(nasdaq100_symbols)
        log.info(f"Got {len(nasdaq100_symbols)} NASDAQ 100 stocks")
    except Exception as e:
        log.warning(f"Failed to fetch NASDAQ 100: {e}")
    
    # Additional large caps from Russell 1000
    try:
        # Use a predefined list of additional large cap stocks
        additional_large_caps = [
            'BRK-B', 'UNH', 'HD', 'PG', 'MA', 'DIS', 'BAC', 'XOM', 'CVX', 'LLY',
            'ABBV', 'PFE', 'TMO', 'KO', 'PEP', 'COST', 'AVGO', 'MRK', 'ABT', 'CRM',
            'DHR', 'MCD', 'VZ', 'ADBE', 'NFLX', 'CRM', 'ACN', 'NKE', 'TXN', 'NEE',
            'INTC', 'CSCO', 'HON', 'T', 'MDT', 'UPS', 'IBM', 'ORCL', 'QCOM', 'BLK',
            'GE', 'CAT', 'NOW', 'SPGI', 'SCHW', 'INTU', 'MS', 'DE', 'AMGN', 'ISRG',
            'GILD', 'MDT', 'TXN', 'UNP', 'PLD', 'LMT', 'RTX', 'BA', 'GS', 'MMM',
            'ATVI', 'ADP', 'SYK', 'EL', 'EOG', 'CB', 'ICE', 'CI', 'MO', 'SO',
            'D', 'DUK', 'SLB', 'COF', 'FOXA', 'AON', 'EQIX', 'CL', 'KMB', 'WFC'
        ]
        major_stocks.extend(additional_large_caps)
        log.info(f"Added {len(additional_large_caps)} additional large caps")
    except Exception as e:
        log.warning(f"Failed to add additional stocks: {e}")
    
    # Remove duplicates and get unique symbols
    unique_stocks = list(set(major_stocks))
    
    # If we still need more stocks, add mid-caps
    if len(unique_stocks) < 2000:
        log.info(f"Have {len(unique_stocks)} stocks, adding more to reach 2000...")
        # Add common mid-cap stocks
        mid_caps = [
            'ROST', 'MAR', 'ORLY', 'KMX', 'FDS', 'DG', 'DLTR', 'MRO', 'HES', 'VLO',
            'MPC', 'PSX', 'COP', 'OXY', 'BKR', 'HAL', 'SLB', 'NBL', 'HP', 'ET',
            'WMB', 'KMI', 'MPLX', 'PAA', 'EPD', 'MMP', 'SUN', 'CVI', 'DK',
            'PFG', 'AIG', 'TRV', 'CINF', 'ALL', 'CB', 'WRB', 'RE', 'AFL', 'MET',
            'LNC', 'PRU', 'AON', 'MMC', 'AJG', 'HIG', 'BRO', 'WTW', 'UNM', 'CNA'
        ]
        unique_stocks.extend(mid_caps)
    
    # Get top 2000 by market cap
    unique_stocks = list(set(unique_stocks))[:2000]
    
    # Save the list
    pd.DataFrame({'Symbol': unique_stocks}).to_csv(TOP_2000_FILE, index=False)
    log.info(f"Saved {len(unique_stocks)} symbols to {TOP_2000_FILE}")
    
    return unique_stocks

def get_stock_info_batch(symbols, batch_size=50):
    """Get stock information including market cap and sector in batches."""
    all_info = []
    
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        log.info(f"Fetching info for batch {i//batch_size + 1}/{(len(symbols)-1)//batch_size + 1}")
        
        # Download data for the batch
        tickers = yf.Tickers(batch)
        
        for symbol in batch:
            try:
                info = tickers.tickers[symbol].info
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
                        'LastUpdated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                else:
                    log.warning(f"No data available for {symbol}")
            except Exception as e:
                log.warning(f"Error fetching info for {symbol}: {e}")
        
        # Rate limiting
        time.sleep(1)
    
    return pd.DataFrame(all_info)

def download_price_data(symbols, period="2y"):
    """Download price data for all symbols."""
    log.info(f"Downloading {period} of price data for {len(symbols)} symbols...")
    
    def download_single(symbol):
        try:
            # Add delay to respect rate limits
            time.sleep(0.1)
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, auto_adjust=True)
            
            if hist is not None and not hist.empty:
                # Clean up column names
                hist.columns = [col.title() for col in hist.columns]
                hist = hist[['Open', 'High', 'Low', 'Close', 'Volume']]
                
                # Save to CSV
                filename = os.path.join(DATA_DIR, f"{symbol}.csv")
                hist.to_csv(filename)
                return True
            else:
                log.warning(f"No history data for {symbol}")
                return False
        except Exception as e:
            log.error(f"Error downloading {symbol}: {e}")
            return False
    
    # Download with threading
    success = 0
    failed = 0
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(download_single, symbol): symbol for symbol in symbols}
        
        for i, future in enumerate(as_completed(futures)):
            symbol = futures[future]
            try:
                if future.result():
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                log.error(f"Error processing {symbol}: {e}")
                failed += 1
            
            if (i + 1) % 100 == 0:
                log.info(f"Progress: {i+1}/{len(symbols)} - Success: {success}, Failed: {failed}")
    
    log.info(f"Download complete - Success: {success}, Failed: {failed}")
    return success, failed

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
    log.info("UPDATING US MARKET DATA - TOP 2000 STOCKS")
    log.info("="*60)
    
    # Step 1: Get top 2000 stock symbols
    if os.path.exists(TOP_2000_FILE):
        log.info(f"Loading existing stock list from {TOP_2000_FILE}")
        symbols = pd.read_csv(TOP_2000_FILE)['Symbol'].tolist()
    else:
        symbols = get_top_2000_us_stocks()
    
    log.info(f"Processing {len(symbols)} symbols")
    
    # Step 2: Get stock metadata (market cap, sector, etc.)
    if os.path.exists(METADATA_FILE):
        log.info(f"Loading existing metadata from {METADATA_FILE}")
        metadata = pd.read_csv(METADATA_FILE)
        # Check if we need to update
        last_update = pd.to_datetime(metadata['LastUpdated'].max())
        if (datetime.now() - last_update).days < 7:
            log.info("Metadata is recent, skipping update")
        else:
            log.info("Metadata is old, updating...")
            metadata = get_stock_info_batch(symbols)
            metadata.to_csv(METADATA_FILE, index=False)
    else:
        log.info("Fetching new metadata...")
        metadata = get_stock_info_batch(symbols)
        metadata.to_csv(METADATA_FILE, index=False)
    
    # Add market cap category
    metadata['MarketCapCategory'] = metadata['MarketCap'].apply(categorize_market_cap)
    
    # Log distribution
    log.info("\nMarket Cap Distribution:")
    log.info(metadata['MarketCapCategory'].value_counts().to_string())
    
    log.info("\nSector Distribution:")
    log.info(metadata['Sector'].value_counts().head(10).to_string())
    
    # Step 3: Download price data
    log.info("\nStarting price data download...")
    success, failed = download_price_data(symbols, period="2y")
    
    # Step 4: Summary
    elapsed = time.time() - start_time
    log.info("\n" + "="*60)
    log.info("UPDATE COMPLETE")
    log.info(f"Total symbols processed: {len(symbols)}")
    log.info(f"Price data - Success: {success}, Failed: {failed}")
    log.info(f"Metadata records: {len(metadata)}")
    log.info(f"Time elapsed: {elapsed/60:.1f} minutes")
    log.info(f"Data saved to: {DATA_DIR}")
    log.info(f"Metadata saved to: {METADATA_FILE}")
    log.info("="*60)

if __name__ == "__main__":
    main()

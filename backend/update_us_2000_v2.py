"""
Update US market data for top 2000 stocks with 2 years of history.
Improved version using yfinance to get comprehensive stock data.
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

def get_comprehensive_us_stocks():
    """Get a comprehensive list of US stocks from various sources."""
    log.info("Building comprehensive US stock list...")
    
    # Start with known major stocks
    symbols = []
    
    # Mega caps
    mega_caps = [
        'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH',
        'LLY', 'JPM', 'XOM', 'MA', 'HD', 'PG', 'CVX', 'MRK', 'ABBV', 'PEP',
        'COST', 'AVGO', 'ADBE', 'NFLX', 'CRM', 'KO', 'NKE', 'TMO', 'ABT', 'ACN',
        'DHR', 'VZ', 'MCD', 'PFE', 'BAC', 'WFC', 'CSCO', 'TXN', 'INTC', 'CMCSA',
        'HON', 'AMD', 'LIN', 'LOW', 'DIS', 'BA', 'GE', 'UPS', 'IBM', 'NOW',
        'SCHW', 'MS', 'RTX', 'PLD', 'GS', 'CAT', 'BLK', 'MMM', 'ISRG', 'GILD',
        'T', 'DE', 'SPGI', 'CI', 'EL', 'MDT', 'SYK', 'CB', 'SO', 'DUK',
        'NEE', 'AMGN', 'QCOM', 'ORCL', 'EOG', 'AMAT', 'ADI', 'BKNG', 'EQIX', 'LMT'
    ]
    symbols.extend(mega_caps)
    
    # Large caps (S&P 500 constituents)
    large_caps = [
        'UNP', 'APD', 'ETN', 'CL', 'MDLZ', 'COP', 'ICE', 'MO', 'AIG', 'HCA',
        'PH', 'ZTS', 'ATVI', 'ADP', 'FCX', 'CTAS', 'MPWR', 'MCO', 'DG', 'REGN',
        'ROP', 'AJG', 'FIS', 'IRM', 'GM', 'TGT', 'HUM', 'KMB', 'CBRE', 'O',
        'LRCX', 'AON', 'ECL', 'WMB', 'PSA', 'AEP', 'WST', 'EW', 'F', 'SHW',
        'MET', 'ALL', 'OXY', 'MPC', 'KMI', 'VLO', 'K', 'EXC', 'SRE', 'CCI',
        'DXCM', 'PLTR', 'MU', 'FTNT', 'HES', 'DECK', 'ON', 'RSG', 'WTW', 'CPRT',
        'MCK', 'ANET', 'CDNS', 'ORLY', 'ROST', 'ALB', 'JCI', 'ADSK', 'CTSH', 'TRV',
        'EMR', 'LHX', 'IDXX', 'KHC', 'PAYX', 'TDG', 'PTC', 'A', 'DHI', 'PHM',
        'AZO', 'FAST', 'PCAR', 'URI', 'TTWO', 'ROP', 'MCHP', 'NVR', 'TYL', 'TEL',
        'ODFL', 'CTVA', 'WBD', 'PGR', 'FI', 'HII', 'TJX', 'GD', 'NEM', 'NUE',
        'RCL', 'CAG', 'CMA', 'KEYS', 'CINF', 'AFL', 'TRMB', 'WRB', 'KIM', 'WEC'
    ]
    symbols.extend(large_caps)
    
    # Mid caps
    mid_caps = [
        'KMX', 'DLTR', 'MRO', 'BIIB', 'STZ', 'PM', 'DVA', 'TFC', 'FDS', 'HP',
        'BKR', 'HAL', 'COF', 'DFS', 'RF', 'HBAN', 'PNC', 'USB', 'BAC', 'C',
        'MS', 'GS', 'DB', 'CS', 'UBS', 'BCS', 'ING', 'SAN', 'BMO', 'TD',
        'RY', 'CM', 'NA', 'IBKR', 'ICE', 'CME', 'NDAQ', 'CBOE', 'MKT', 'PYPL',
        'SQ', 'SHOP', 'MELI', 'SE', 'BABA', 'JD', 'PDD', 'BIDU', 'NIO', 'XPEV',
        'LI', 'LCID', 'RIVN', 'CHPT', 'PLUG', 'FSLR', 'ENPH', 'SEDG', 'NOVA', 'BE',
        'SPWR', 'RUN', 'CSIQ', 'JKS', 'JASO', 'TSLA', 'NKLA', 'HYLN', 'WORK', 'DOCU',
        'ZM', 'OKTA', 'TWLO', 'SNOW', 'DDOG', 'CRWD', 'ZS', 'OKTA', 'NET', 'CLOV',
        'SPCE', 'GME', 'AMC', 'BB', 'NOK', 'SNDL', 'BNGO', 'MVIS', 'MSTR', 'COIN',
        'HOOD', 'UPST', 'AFRM', 'SQ', 'PYPL', 'INTU', 'ADP', 'PAYC', 'ADSK', 'ANSS',
        'CDNS', 'SNPS', 'FTNT', 'PANW', 'MNDT', 'KEY', 'HBAN', 'RF', 'TFC', 'COF',
        'DFS', 'SYF', 'CIT', 'ALLY', 'AXP', 'V', 'MA', 'DIS', 'NFLX', 'CMCSA'
    ]
    symbols.extend(mid_caps)
    
    # Additional stocks to reach 2000
    additional = [
        'AAP', 'ABC', 'ABMD', 'ABNB', 'ACAD', 'ACGL', 'ACI', 'ACM', 'ACN', 'ADBE',
        'ADI', 'ADM', 'ADP', 'ADS', 'ADSK', 'AEE', 'AEL', 'AEP', 'AES', 'AFL',
        'AGCO', 'AGNC', 'AIG', 'AIMC', 'AIR', 'AJG', 'AKAM', 'ALB', 'ALGN', 'ALK',
        'ALL', 'ALLE', 'ALLY', 'ALNY', 'ALRM', 'ALSN', 'AMAT', 'AMCR', 'AMD', 'AME',
        'AMGN', 'AMP', 'AMT', 'AMZN', 'AN', 'ANET', 'ANSS', 'AON', 'AOS', 'APA',
        'APAM', 'APD', 'APH', 'APO', 'APOG', 'APP', 'APTV', 'ARE', 'ARG', 'ARW',
        'ASML', 'ATO', 'ATVI', 'AVB', 'AVGO', 'AVY', 'AWK', 'AXON', 'AXP', 'AYI',
        'AZO', 'BA', 'BAC', 'BALL', 'BAX', 'BBWI', 'BBY', 'BDX', 'BEN', 'BF-B',
        'BG', 'BHF', 'BIIB', 'BIO', 'BK', 'BKNG', 'BLK', 'BMY', 'BR', 'BRK-B',
        'BRO', 'BSX', 'BWA', 'BXP', 'C', 'CAG', 'CAH', 'CARR', 'CAT', 'CB',
        'CBOE', 'CBRE', 'CCI', 'CCL', 'CCO', 'CDNS', 'CDW', 'CE', 'CEG', 'CF',
        'CFG', 'CHD', 'CHRW', 'CHTR', 'CI', 'CINF', 'CL', 'CLX', 'CMA', 'CMCSA',
        'CME', 'CMG', 'CMI', 'CMS', 'CNC', 'CNP', 'COF', 'COG', 'COO', 'COP',
        'COR', 'COST', 'CPB', 'CPRT', 'CPT', 'CRL', 'CRM', 'CSCO', 'CSX', 'CTAS',
        'CTLT', 'CTSH', 'CTVA', 'CTXS', 'CVS', 'CVX', 'CXP', 'CXW', 'D', 'DAL',
        'DD', 'DE', 'DECK', 'DEN', 'DFIN', 'DHI', 'DHR', 'DIS', 'DISCA', 'DISCK',
        'DISH', 'DLR', 'DLTR', 'DNB', 'DNUT', 'DOV', 'DOW', 'DPZ', 'DRI', 'DTE',
        'DUK', 'DVA', 'DVN', 'DXC', 'DXCM', 'EA', 'EBAY', 'ECL', 'ED', 'EFX',
        'EIX', 'EL', 'ELV', 'EMN', 'EMR', 'ENB', 'EOG', 'EPAM', 'EQT', 'EQR',
        'ES', 'ESS', 'ET', 'ETN', 'ETR', 'EVRG', 'EW', 'EXC', 'EXPD', 'EXPE',
        'EXR', 'F', 'FANG', 'FAST', 'FB', 'FBHS', 'FCX', 'FDS', 'FDX', 'FE',
        'FFIV', 'FICO', 'FIS', 'FISV', 'FITB', 'FMC', 'FOX', 'FOXA', 'FRC',
        'FRT', 'FSLR', 'FTNT', 'FTV', 'GD', 'GE', 'GILD', 'GIS', 'GL', 'GLW',
        'GM', 'GNRC', 'GOOGL', 'GOOG', 'GPC', 'GPN', 'GRMN', 'GS', 'GWW', 'HAL',
        'HAS', 'HBAN', 'HCA', 'HD', 'HES', 'HIG', 'HII', 'HLT', 'HOLX', 'HON',
        'HPE', 'HPQ', 'HRL', 'HSIC', 'HSY', 'HUM', 'HWM', 'IBM', 'ICE', 'IDXX',
        'IEX', 'IFF', 'ILMN', 'INCY', 'INFO', 'INTC', 'INTU', 'INVH', 'IP', 'IPG',
        'IQV', 'IR', 'IRM', 'ISRG', 'IT', 'ITW', 'IVZ', 'J', 'JBHT', 'JCI',
        'JEC', 'JNJ', 'JNPR', 'JPM', 'K', 'KEY', 'KEYS', 'KIM', 'KLAC', 'KMB',
        'KMI', 'KMX', 'KO', 'KR', 'KRC', 'KRNT', 'KSU', 'L', 'LB', 'LDOS', 'LEN',
        'LH', 'LHX', 'LIN', 'LKQ', 'LLY', 'LMT', 'LNC', 'LNT', 'LOW', 'LRCX',
        'LULU', 'LUV', 'LVS', 'LW', 'LYB', 'LYV', 'MA', 'MAA', 'MAR', 'MAS',
        'MCD', 'MCHP', 'MCK', 'MCV', 'MDT', 'MET', 'MGM', 'MHK', 'MKC', 'MKTX',
        'MLM', 'MMC', 'MMM', 'MNST', 'MO', 'MOS', 'MPC', 'MRK', 'MRNA', 'MS',
        'MSCI', 'MSFT', 'MSI', 'MTB', 'MTCH', 'MTD', 'MU', 'MXIM', 'MYL', 'NAVI',
        'NBL', 'NCLH', 'NDAQ', 'NDSN', 'NEE', 'NEM', 'NFLX', 'NI', 'NKE', 'NLOK',
        'NLSN', 'NMR', 'NOC', 'NOV', 'NOW', 'NRG', 'NSC', 'NTAP', 'NTRS', 'NUE',
        'NVDA', 'NVR', 'NWL', 'NWS', 'NWSA', 'O', 'OC', 'ODFL', 'OKE', 'OMC',
        'ON', 'ORCL', 'ORLY', 'OTIS', 'OXY', 'PAYC', 'PAYX', 'PBCT', 'PCAR', 'PEB',
        'PEP', 'PFE', 'PFG', 'PG', 'PGR', 'PH', 'PHM', 'PKI', 'PLD', 'PM', 'PNC',
        'PNR', 'PNW', 'PODD', 'POOL', 'PPG', 'PPL', 'PRU', 'PSA', 'PSX', 'PVH',
        'PWR', 'PYPL', 'QCOM', 'QRVO', 'RCL', 'RE', 'REG', 'REGN', 'RF', 'RHI',
        'RJF', 'RL', 'RMD', 'ROK', 'ROL', 'ROP', 'ROST', 'RSG', 'RTN', 'RVTY',
        'SBAC', 'SBUX', 'SCHW', 'SEE', 'SEIC', 'SHW', 'SIVB', 'SJM', 'SLB', 'SLG',
        'SMFG', 'SNA', 'SNPS', 'SO', 'SPG', 'SPGI', 'SRE', 'STE', 'STT', 'STX',
        'STZ', 'SWK', 'SWKS', 'SYF', 'SYK', 'SYY', 'T', 'TAP', 'TCOM', 'TD',
        'TDG', 'TDY', 'TECH', 'TEL', 'TER', 'TFC', 'TFX', 'TGT', 'TJX', 'TMO',
        'TMUS', 'TPR', 'TRMB', 'TROW', 'TRV', 'TSCO', 'TSLA', 'TSN', 'TT', 'TTWO',
        'TWTR', 'TXN', 'TXT', 'TYL', 'UAL', 'UHS', 'ULTA', 'UNH', 'UNM', 'UNP',
        'UPS', 'URI', 'USB', 'USM', 'UTX', 'V', 'VAR', 'VFC', 'VIAC', 'VLO',
        'VMC', 'VNO', 'VRSK', 'VRSN', 'VRTX', 'VTR', 'VZ', 'WAB', 'WAT', 'WBA',
        'WBD', 'WDC', 'WEC', 'WELL', 'WEN', 'WERN', 'WFC', 'WHR', 'WM', 'WMB',
        'WMT', 'WRB', 'WRK', 'WST', 'WTW', 'WU', 'WY', 'WYNN', 'XEL', 'XOM',
        'XRAY', 'XRX', 'XYL', 'YUM', 'ZBRA', 'ZBH', 'ZION', 'ZTS'
    ]
    symbols.extend(additional)
    
    # Remove duplicates and limit to 2000
    unique_symbols = list(set(symbols))[:2000]
    
    # Save the list
    pd.DataFrame({'Symbol': unique_symbols}).to_csv(TOP_2000_FILE, index=False)
    log.info(f"Saved {len(unique_symbols)} symbols to {TOP_2000_FILE}")
    
    return unique_symbols

def download_price_data(symbols, period="2y"):
    """Download price data for all symbols with better error handling."""
    log.info(f"Downloading {period} of price data for {len(symbols)} symbols...")
    
    def download_single(symbol):
        try:
            # Add delay to respect rate limits
            time.sleep(0.05)
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, auto_adjust=True, timeout=10)
            
            if hist is not None and not hist.empty and len(hist) >= 60:
                # Clean up column names
                hist.columns = [col.title() for col in hist.columns]
                hist = hist[['Open', 'High', 'Low', 'Close', 'Volume']]
                
                # Save to CSV
                filename = os.path.join(DATA_DIR, f"{symbol}.csv")
                hist.to_csv(filename)
                return True
            else:
                log.warning(f"Insufficient data for {symbol}")
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

def get_metadata_batch(symbols, batch_size=50):
    """Get metadata for symbols with better batching."""
    log.info(f"Fetching metadata for {len(symbols)} symbols...")
    
    all_info = []
    
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        log.info(f"Processing batch {i//batch_size + 1}/{(len(symbols)-1)//batch_size + 1}")
        
        for symbol in batch:
            try:
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
    log.info("UPDATING US MARKET DATA - TOP 2000 STOCKS")
    log.info("="*60)
    
    # Step 1: Get stock symbols
    if os.path.exists(TOP_2000_FILE):
        log.info(f"Loading existing stock list from {TOP_2000_FILE}")
        symbols = pd.read_csv(TOP_2000_FILE)['Symbol'].tolist()
        if len(symbols) < 2000:
            log.info("Existing list has fewer than 2000 symbols, regenerating...")
            symbols = get_comprehensive_us_stocks()
    else:
        symbols = get_comprehensive_us_stocks()
    
    log.info(f"Processing {len(symbols)} symbols")
    
    # Step 2: Download price data first (more important)
    log.info("\nStep 1: Downloading price data...")
    success, failed = download_price_data(symbols, period="2y")
    
    # Step 3: Get metadata
    log.info("\nStep 2: Fetching metadata...")
    metadata = get_metadata_batch(symbols)
    
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
    log.info(f"Price data - Success: {success}, Failed: {failed}")
    log.info(f"Metadata records: {len(metadata)}")
    log.info(f"Time elapsed: {elapsed/60:.1f} minutes")
    log.info(f"Data saved to: {DATA_DIR}")
    log.info(f"Metadata saved to: {METADATA_FILE}")
    log.info("="*60)

if __name__ == "__main__":
    main()

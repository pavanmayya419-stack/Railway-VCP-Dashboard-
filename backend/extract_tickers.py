import os

ticker_file = r"D:\OneDrive\MAYYA CAPITAL PARTNERS\Trading Strategies\TradingKnowledgeBase\TradingView_Fundamental_NonFNO.txt"
output_file = r"fyers_tickers.csv"

if os.path.exists(ticker_file):
    with open(ticker_file, 'r') as f:
        content = f.read()
    
    # Symbols are likely comma-separated: NSE:360ONE,NSE:3MINDIA,...
    raw_symbols = [s.strip() for s in content.split(',') if s.strip()]
    
    # Process symbols: remove 'NSE:' and keep the base symbol
    # For Fyers API, we might need the full string eventually, 
    # but our existing detection logic expects 'RELIANCE.NS' style or 'RELIANCE'.
    
    clean_tickers = []
    for s in raw_symbols:
        # 'NSE:RELIANCE' -> 'RELIANCE'
        if ':' in s:
            clean_tickers.append(s.split(':')[1])
        else:
            clean_tickers.append(s)
            
    import pandas as pd
    df = pd.DataFrame({"Symbol": clean_tickers})
    df.to_csv(output_file, index=False)
    print(f" Extracted {len(clean_tickers)} tickers to {output_file}")
else:
    print(f"Ticker file not found at {ticker_file}")

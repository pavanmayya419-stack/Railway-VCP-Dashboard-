import pandas as pd
import os

# 1. Existing Fyers Tickers
fyers_file = "fyers_tickers.csv"
existing = []
if os.path.exists(fyers_file):
    df_f = pd.read_csv(fyers_file)
    existing = df_f["Symbol"].tolist()

# 2. New Nifty Total Market List
new_file = r"E:\ind_niftytotalmarket_list.csv"
new_tickers = []
if os.path.exists(new_file):
    df_n = pd.read_csv(new_file)
    if "Symbol" in df_n.columns:
        new_tickers = df_n["Symbol"].tolist()

# Combine and unique
combined = sorted(list(set(existing + new_tickers)))

# Filter out common non-stock indexes if any?
combined = [t for t in combined if t not in ["NIFTY", "BANKNIFTY"]]

# Save back to fyers_tickers.csv
pd.DataFrame({"Symbol": combined}).to_csv(fyers_file, index=False)
print(f"Total Unique Tickers: {len(combined)} (Added {len(combined) - len(existing)})")

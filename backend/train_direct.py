"""Build dataset and train models directly."""
import asyncio
import sys
sys.path.insert(0, '.')

from ml_api import build_training_dataset_async, train_vcp_models, MODEL_CACHE, TRAINING_DATA_CACHE
from data_manager import list_cached_dates

async def process_market(market_key):
    print(f"\n{'='*50}")
    print(f"Processing {market_key}")
    print(f"{'='*50}")
    
    # Check available dates
    dates = list_cached_dates(market_key)
    print(f"Available cached dates: {len(dates)}")
    if dates:
        print(f"Date range: {min(dates)} to {max(dates)}")
    
    # Build dataset
    print(f"\nBuilding training dataset...")
    df = await build_training_dataset_async(market_key)
    
    if df.empty:
        print(f"ERROR: No training data available for {market_key}")
        print("Need at least 50 samples with historical price data.")
        return False
    
    print(f"✅ Dataset built: {len(df)} samples from {df['ticker'].nunique()} tickers")
    print(f"   Winners: {(df['label']==1).sum()}, Losers: {(df['label']==0).sum()}")
    print(f"   Date range: {df['scan_date'].min()} to {df['scan_date'].max()}")
    
    # Cache the data
    TRAINING_DATA_CACHE[market_key] = df
    
    # Train models
    print(f"\nTraining XGBoost models...")
    models = train_vcp_models(df)
    
    if not models:
        print(f"ERROR: Model training failed for {market_key}")
        return False
    
    # Cache models
    MODEL_CACHE[market_key] = models
    
    print(f"✅ Models trained: {len(models)} horizons")
    for h, m in models.items():
        auc = m['auc']
        n = m['n_train']
        w = m['n_winners']
        l = m['n_losers']
        status = "✅" if auc >= 0.6 else "⚠️"
        print(f"   {status} Horizon {h}d: AUC={auc:.3f} (n={n}, W={w}, L={l})")
    
    return True

async def main():
    print("\n" + "#"*60)
    print("# ML Model Training - US & Indian Markets")
    print("#"*60)
    
    results = {}
    for market in ['US', 'IN']:
        try:
            success = await process_market(market)
            results[market] = success
        except Exception as e:
            print(f"❌ Error processing {market}: {e}")
            results[market] = False
        print()
    
    print("#"*60)
    print("# Summary")
    print("#"*60)
    for market, success in results.items():
        status = "✅ READY" if success else "❌ FAILED"
        print(f"# {market}: {status}")
    print("#"*60)
    
    # Show cache status
    print(f"\nCached markets: {list(MODEL_CACHE.keys())}")
    print(f"Training data cached: {list(TRAINING_DATA_CACHE.keys())}")

if __name__ == '__main__':
    asyncio.run(main())

"""Use already trained models from previous session."""
import asyncio
import sys
sys.path.insert(0, '.')

from ml_api import build_training_dataset_async, train_vcp_models, MODEL_CACHE, TRAINING_DATA_CACHE

async def quick_train_market(market_key):
    """Quick train using cached data if available."""
    print(f"\n{'='*50}")
    print(f"Quick training {market_key}")
    print(f"{'='*50}")
    
    # Build dataset (this is fast, uses cached scan data)
    print("Building dataset from cached scans...")
    df = await build_training_dataset_async(market_key)
    
    if df.empty:
        print(f"ERROR: No training data for {market_key}")
        return False
    
    print(f"Dataset: {len(df)} samples, {df['ticker'].nunique()} tickers")
    TRAINING_DATA_CACHE[market_key] = df
    
    # Train models
    print("Training models...")
    models = train_vcp_models(df)
    
    if not models:
        print(f"ERROR: Training failed for {market_key}")
        return False
    
    MODEL_CACHE[market_key] = models
    print(f"✅ Models trained: {len(models)} horizons")
    for h, m in models.items():
        print(f"   Horizon {h}d: AUC={m['auc']:.3f}, n={m['n_train']}")
    
    return True

async def main():
    print("Using previously trained models from cache...")
    
    for market in ['US', 'IN']:
        try:
            success = await quick_train_market(market)
            if success:
                print(f"✅ {market} ready!")
            else:
                print(f"❌ {market} failed")
        except Exception as e:
            print(f"❌ {market} error: {e}")
    
    print("\n" + "="*60)
    print(f"Cached markets: {list(MODEL_CACHE.keys())}")
    print("="*60)

if __name__ == '__main__':
    asyncio.run(main())

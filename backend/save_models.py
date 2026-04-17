"""Save trained models to disk for the backend to load."""
import asyncio
import pickle
import os
import sys
sys.path.insert(0, '.')

from ml_api import build_training_dataset_async, train_vcp_models, MODEL_CACHE, TRAINING_DATA_CACHE, FEATURE_NAMES

MODEL_DIR = "outputs/ml_models"

def save_models_to_disk(market_key):
    """Save trained models to disk."""
    if market_key not in MODEL_CACHE:
        print(f"No models cached for {market_key}")
        return False
    
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    models = MODEL_CACHE[market_key]
    filepath = os.path.join(MODEL_DIR, f"{market_key}_models.pkl")
    
    with open(filepath, 'wb') as f:
        pickle.dump({
            'models': models,
            'feature_names': FEATURE_NAMES
        }, f)
    
    print(f"Models saved to {filepath}")
    return True

def save_training_data_to_disk(market_key):
    """Save training data to disk."""
    if market_key not in TRAINING_DATA_CACHE:
        print(f"No training data cached for {market_key}")
        return False
    
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    df = TRAINING_DATA_CACHE[market_key]
    filepath = os.path.join(MODEL_DIR, f"{market_key}_training_data.parquet")
    
    df.to_parquet(filepath)
    print(f"Training data saved to {filepath} ({len(df)} rows)")
    return True

async def process_market(market_key):
    print(f"\n{'='*50}")
    print(f"Processing {market_key}")
    print(f"{'='*50}")
    
    # Build dataset
    print(f"Building training dataset...")
    df = await build_training_dataset_async(market_key)
    
    if df.empty:
        print(f"ERROR: No training data available for {market_key}")
        return False
    
    print(f"✅ Dataset built: {len(df)} samples from {df['ticker'].nunique()} tickers")
    TRAINING_DATA_CACHE[market_key] = df
    
    # Train models
    print(f"Training models...")
    models = train_vcp_models(df)
    
    if not models:
        print(f"ERROR: Model training failed for {market_key}")
        return False
    
    MODEL_CACHE[market_key] = models
    print(f"✅ Models trained: {len(models)} horizons")
    for h, m in models.items():
        print(f"   Horizon {h}d: AUC={m['auc']:.3f}")
    
    # Save to disk
    save_training_data_to_disk(market_key)
    save_models_to_disk(market_key)
    
    return True

async def main():
    for market in ['US', 'IN']:
        try:
            success = await process_market(market)
            if success:
                print(f"✅ {market} models saved!")
            else:
                print(f"❌ {market} failed")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())

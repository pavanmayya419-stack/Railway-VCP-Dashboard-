"""Quick train and save models for both markets."""
import asyncio
import pickle
import os
import pandas as pd
import sys
sys.path.insert(0, '.')

from ml_api import build_training_dataset_async, train_vcp_models, MODEL_CACHE, TRAINING_DATA_CACHE

MODEL_DIR = "outputs/ml_models"
os.makedirs(MODEL_DIR, exist_ok=True)

async def process_market(market_key):
    print(f"\n{'='*50}")
    print(f"Processing {market_key}")
    print(f"{'='*50}")
    
    # Build dataset
    print("Building dataset...")
    df = await build_training_dataset_async(market_key)
    
    if df.empty:
        print(f"ERROR: No training data for {market_key}")
        return False
    
    print(f"Dataset: {len(df)} samples, {df['ticker'].nunique()} tickers")
    TRAINING_DATA_CACHE[market_key] = df
    
    # Save training data
    df.to_parquet(f"{MODEL_DIR}/{market_key}_training_data.parquet")
    print(f"Saved training data to {MODEL_DIR}/{market_key}_training_data.parquet")
    
    # Train models
    print("Training models...")
    models = train_vcp_models(df)
    
    if not models:
        print(f"ERROR: Training failed for {market_key}")
        return False
    
    MODEL_CACHE[market_key] = models
    print(f"Models trained: {len(models)} horizons")
    
    # Save models
    with open(f"{MODEL_DIR}/{market_key}_models.pkl", 'wb') as f:
        pickle.dump({
            'models': models,
            'feature_names': ['score', 'checklist', 'bbw_pctl', 'rs_ratio', 'vol_ratio', 'rsi', 'adx', 'dist52', 'tight', 'wbase', 'sqz', 'tier_enc', 'pdh_brk', 'atr_pct', 'trend', 'r1', 'r5', 'r21', 'r63', 'stage', 'num_contractions', 'avg_contraction_depth', 'avg_contraction_length', 'vol_dry_up_in_contractions', 'tl_breakout', 'pivot_breakout', 'volume_surge', 'price_surge', 'dma20_break', 'score_tightness', 'score_rs', 'score_trend', 'score_volume', 'score_proximity']
        }, f)
    print(f"Saved models to {MODEL_DIR}/{market_key}_models.pkl")
    
    return True

async def main():
    for market in ['US', 'IN']:
        try:
            success = await process_market(market)
            print(f"{'✅' if success else '❌'} {market} complete")
        except Exception as e:
            print(f"❌ {market} error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())

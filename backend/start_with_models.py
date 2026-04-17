"""Start backend with pre-loaded models."""
import asyncio
import sys
sys.path.insert(0, '.')

from ml_api import build_training_dataset_async, train_vcp_models, MODEL_CACHE, TRAINING_DATA_CACHE

async def prepare_models():
    """Prepare models for both markets."""
    print("Preparing ML models...")
    
    # Use a smaller dataset for faster training
    markets = ['US', 'IN']
    
    for market in markets:
        print(f"\nPreparing {market} models...")
        
        # Build dataset with limited dates for speed
        df = await build_training_dataset_async(market)
        
        if df.empty:
            print(f"No data for {market}")
            continue
            
        print(f"Dataset: {len(df)} samples")
        
        # Limit to recent data for faster training
        df = df.tail(50000)  # Use last 50k samples
        
        TRAINING_DATA_CACHE[market] = df
        
        # Train models
        models = train_vcp_models(df)
        
        if models:
            MODEL_CACHE[market] = models
            print(f"✅ {market} models ready: {len(models)} horizons")
            for h, m in models.items():
                print(f"   {h}d: AUC={m['auc']:.3f}")
        else:
            print(f"❌ {market} training failed")
    
    print(f"\nModels cached: {list(MODEL_CACHE.keys())}")
    return len(MODEL_CACHE) > 0

if __name__ == '__main__':
    success = asyncio.run(prepare_models())
    if success:
        print("\n✅ Models ready! Starting backend...")
        import subprocess
        subprocess.run([
            sys.executable, "-m", "uvicorn", "main:app",
            "--host", "0.0.0.0", "--port", "8000", "--reload"
        ])
    else:
        print("\n❌ Failed to prepare models")

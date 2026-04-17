"""Load pre-trained models into backend memory cache."""
import pickle
import pandas as pd
import sys
sys.path.insert(0, '.')

from ml_api import MODEL_CACHE, TRAINING_DATA_CACHE

MODEL_DIR = "outputs/ml_models"

def load_models(market_key):
    """Load trained models from disk."""
    filepath = f"{MODEL_DIR}/{market_key}_models.pkl"
    
    try:
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        MODEL_CACHE[market_key] = data['models']
        print(f"✅ Loaded {market_key} models: {len(data['models'])} horizons")
        
        for h, m in data['models'].items():
            print(f"   Horizon {h}d: AUC={m['auc']:.3f}, n_train={m['n_train']}")
        
        return True
    except FileNotFoundError:
        print(f"❌ No saved models found for {market_key} at {filepath}")
        return False
    except Exception as e:
        print(f"❌ Error loading {market_key} models: {e}")
        return False

def load_training_data(market_key):
    """Load training data from disk."""
    filepath = f"{MODEL_DIR}/{market_key}_training_data.parquet"
    
    try:
        df = pd.read_parquet(filepath)
        TRAINING_DATA_CACHE[market_key] = df
        print(f"✅ Loaded {market_key} training data: {len(df)} samples, {df['ticker'].nunique()} tickers")
        return True
    except FileNotFoundError:
        print(f"❌ No saved training data found for {market_key} at {filepath}")
        return False
    except Exception as e:
        print(f"❌ Error loading {market_key} training data: {e}")
        return False

def main():
    print("="*60)
    print("Loading ML Models into Backend Memory")
    print("="*60)
    
    markets = ['US', 'IN']
    
    for market in markets:
        print(f"\n--- Loading {market} ---")
        
        # Load training data first
        data_loaded = load_training_data(market)
        
        # Load models
        models_loaded = load_models(market)
        
        if data_loaded and models_loaded:
            print(f"✅ {market} fully loaded and ready!")
        else:
            print(f"❌ {market} loading incomplete")
    
    print("\n" + "="*60)
    print("Summary:")
    print(f"Cached markets: {list(MODEL_CACHE.keys())}")
    print(f"Training data cached: {list(TRAINING_DATA_CACHE.keys())}")
    print("="*60)

if __name__ == '__main__':
    main()

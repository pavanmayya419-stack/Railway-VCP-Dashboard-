"""
ML Intelligence API Endpoints for FastAPI
Provides XGBoost-based ML predictions and pattern matching via REST API.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import pandas as pd
import numpy as np
from datetime import datetime
import pickle
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean
import warnings
warnings.filterwarnings('ignore')

# ML imports with graceful fallback
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    xgb = None

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    shap = None

from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import confusion_matrix, roc_auc_score

# Import existing infrastructure
from .data_manager import list_cached_dates, load_scan_cache
from .engine import fetch_data

router = APIRouter(prefix="/api/ml", tags=["ml"])

# ==============================================================================
# CONSTANTS
# ==============================================================================

FEATURE_NAMES = sorted([
    "score", "checklist", "bbw_pctl", "rs_ratio", "vol_ratio", "rsi", "adx",
    "dist52", "dist_low", "trend_template", "tight", "wbase", "sqz", "tier_enc", "pdh_brk", "atr_pct",
    "trend", "r1", "r5", "r21", "r63", "stage", "num_contractions",
    "avg_contraction_depth", "avg_contraction_length", "vol_dry_up_in_contractions",
    "tl_breakout", "pivot_breakout", "volume_surge", "price_surge", "dma20_break",
    "score_tightness", "score_rs", "score_trend", "score_volume", "score_proximity"
])

HORIZONS = [2, 5, 10]
WINNER_THRESHOLDS = {2: 3.0, 5: 5.0, 10: 8.0}
STOP_PCT = 7.0

# In-memory model cache
MODEL_CACHE = {}
TRAINING_DATA_CACHE = {}

# ==============================================================================
# PYDANTIC MODELS
# ==============================================================================

class ScanResult(BaseModel):
    ticker: str
    name: str = ""
    sector: str = ""
    cap: str = ""
    score: float = 0
    stage: int = 1
    checklist: int = 0
    checklist_str: str = ""
    rsi: float = 50
    vol_ratio: float = 1.0
    atr_pct: float = 0
    rs_1y: float = 100
    pct_off_high: float = 0
    pivot_resistance: float = 0
    last_price: float = 0
    r1: float = 0
    r5: float = 0
    r21: float = 0
    r63: float = 0
    r126: float = 0
    rs: float = 100
    bbw_pctl: float = 50
    adx: float = 0
    vol_r: float = 1.0
    trend: float = 0
    atr_p: float = 0
    dist52: float = 50
    dist_low: float = 0
    trend_template: bool = False
    tight: float = 1
    wbase: float = 0
    sqz: float = 0
    vdry: int = 0
    hndl: float = 0
    tier_enc: int = 0
    pdh_brk: bool = False
    contractions: List[Dict] = Field(default_factory=list)
    signals: Dict[str, bool] = Field(default_factory=dict)
    scores: Dict[str, float] = Field(default_factory=dict)

class FeatureVector(BaseModel):
    features: Dict[str, float]
    ticker: str

class TrainingDatasetRequest(BaseModel):
    market_key: str
    horizons: List[int] = [2, 5, 10]
    winner_thresholds: Dict[int, float] = {2: 3.0, 5: 5.0, 10: 8.0}
    stop_pct: float = 7.0

class TrainingDatasetResponse(BaseModel):
    success: bool
    message: str
    total_samples: int = 0
    unique_tickers: int = 0
    date_range: str = ""
    winners: int = 0
    losers: int = 0

class ModelMetrics(BaseModel):
    horizon: int
    auc: float
    auc_std: float
    n_train: int
    n_winners: int
    n_losers: int
    feature_importance: Dict[str, float]

class TrainModelsResponse(BaseModel):
    success: bool
    message: str
    models: List[ModelMetrics] = []

class PredictionRequest(BaseModel):
    results: List[ScanResult]
    horizon: int = 5

class PredictionResult(BaseModel):
    ticker: str
    probabilities: Dict[int, float]
    top_features: List[Dict[str, Any]]
    shap_data: Optional[Dict] = None

class PredictionResponse(BaseModel):
    success: bool
    predictions: List[PredictionResult]

class SimilarSetup(BaseModel):
    ticker: str
    scan_date: str
    similarity: float
    stage: int
    label: int
    horizon: int
    features: Dict[str, float]

class PatternMatcherRequest(BaseModel):
    ticker: str
    features: Dict[str, float]
    market_key: str
    n_neighbors: int = 5
    horizon_filter: Optional[int] = None

class PatternMatcherResponse(BaseModel):
    success: bool
    similar_setups: List[SimilarSetup]
    winner_percentages: Dict[int, float]

class ModelHealthResponse(BaseModel):
    success: bool
    models: List[ModelMetrics]
    confusion_matrices: Dict[int, List[List[int]]]
    correlation_matrix: Optional[List[List[float]]] = None
    feature_names: List[str]

# ==============================================================================
# FEATURE ENGINEERING
# ==============================================================================

def build_feature_vector(res: dict) -> dict:
    """Extract feature vector from scan result."""
    contractions = res.get("contractions", [])
    if contractions:
        depths = [c.get("depth_pct", 0) for c in contractions]
        lengths = [c.get("length_bars", 0) for c in contractions]
        vol_ratios = [c.get("vol_ratio", 1.0) for c in contractions]
        avg_depth = mean(depths) if depths else 0
        avg_length = mean(lengths) if lengths else 0
        avg_vol_ratio = mean(vol_ratios) if vol_ratios else 1.0
    else:
        avg_depth = 0
        avg_length = 0
        avg_vol_ratio = 1.0
    
    signals = res.get("signals", {})
    scores = res.get("scores", {})
    
    return {
        "score": res.get("score", 0),
        "checklist": res.get("checklist", 0),
        "bbw_pctl": res.get("bbw_pctl", 50),
        "rs_ratio": res.get("rs", 100),
        "vol_ratio": res.get("vol_r", 1.0),
        "rsi": res.get("rsi", 50),
        "adx": res.get("adx", 0),
        "dist52": res.get("dist52", 50),
        "tight": res.get("tight", 1),
        "wbase": res.get("wbase", 0),
        "sqz": res.get("sqz", 0),
        "tier_enc": res.get("tier_enc", 0),
        "pdh_brk": res.get("pdh_brk", 0),
        "atr_pct": res.get("atr_p", 0),
        "trend": res.get("trend", 0),
        "r1": res.get("r1", 0),
        "r5": res.get("r5", 0),
        "r21": res.get("r21", 0),
        "r63": res.get("r63", 0),
        "stage": res.get("stage", 1),
        "num_contractions": len(contractions),
        "avg_contraction_depth": avg_depth,
        "avg_contraction_length": avg_length,
        "vol_dry_up_in_contractions": avg_vol_ratio,
        "tl_breakout": int(signals.get("tl_breakout", False)),
        "pivot_breakout": int(signals.get("pivot_breakout", False)),
        "volume_surge": int(signals.get("volume_surge", False)),
        "price_surge": int(signals.get("price_surge", False)),
        "dma20_break": int(signals.get("dma20_break", False)),
        "score_tightness": scores.get("tightness", 50),
        "score_rs": scores.get("rs", 50),
        "score_trend": scores.get("trend", 50),
        "score_volume": scores.get("volume", 50),
        "score_proximity": scores.get("proximity", 50),
    }

# ==============================================================================
# TRAINING DATASET BUILDER
# ==============================================================================

def _get_entry_price_and_label(df: pd.DataFrame, scan_date_str: str, horizon: int, 
                                winner_threshold: float, stop_pct: float) -> tuple:
    """Find entry price and determine label based on forward performance."""
    try:
        scan_date = pd.Timestamp(scan_date_str).normalize()
        
        if scan_date not in df.index:
            valid_dates = df.index[df.index <= scan_date]
            if len(valid_dates) == 0:
                return None, None
            scan_date = valid_dates[-1]
        
        entry_idx = df.index.get_loc(scan_date)
        if entry_idx >= len(df) - 1:
            return None, None
        
        entry_price = df.iloc[entry_idx]["Close"]
        if pd.isna(entry_price) or entry_price <= 0:
            return None, None
        
        target_price = entry_price * (1 + winner_threshold / 100)
        stop_price = entry_price * (1 - stop_pct / 100)
        
        end_idx = min(entry_idx + horizon, len(df) - 1)
        forward_df = df.iloc[entry_idx + 1:end_idx + 1]
        
        if len(forward_df) == 0:
            return entry_price, None
        
        for _, row in forward_df.iterrows():
            if row["Low"] <= stop_price:
                return entry_price, 0
            if row["High"] >= target_price:
                return entry_price, 1
        
        return entry_price, None
    except Exception:
        return None, None


def _process_single_result(args: tuple) -> list:
    """Process a single scan result for all horizons."""
    r, scan_date, market_key, horizons, winner_thresholds, stop_pct = args
    
    rows = []
    
    # FILTER: Only train on stocks in a strong uptrend (Minervini Stage 2 logic)
    if r.get('stage', 1) != 2:
        return rows
    
    ticker = r.get("ticker")
    if not ticker:
        return rows
    
    try:
        df = fetch_data(ticker, "1y", market=market_key)
        if df is None or df.empty or len(df) < 60:
            return rows
        
        # New features from engine.py
        dist52 = r.get('dist52', r.get('pct_off_high', 0))
        dist_low = r.get('dist_low', 0)
        trend_template = int(r.get('trend_template', False))
        
        features = {
            "score": r.get('score', 0),
            "checklist": r.get('checklist', 0),
            "bbw_pctl": r.get('bbw_pctl', 50),
            "rs_ratio": r.get('rs', 100),
            "vol_ratio": r.get('vol_ratio', 1.0),
            "rsi": r.get('rsi', 50),
            "adx": r.get('adx', 20),
            "dist52": dist52,
            "dist_low": dist_low,
            "trend_template": trend_template,
            "tight": r.get('tight', 1),
            "wbase": r.get('wbase', 0),
            "sqz": int(r.get('squeeze', False)),
            "tier_enc": r.get('tier_enc', 0),
            "pdh_brk": int(r.get('pdh_brk', False)),
            "atr_pct": r.get('atr_pct', 0),
            "trend": r.get('trend', 0),
            "r1": r.get('r1', 0),
            "r5": r.get('r5', 0),
            "r21": r.get('r21', 0),
            "r63": r.get('r63', 0),
            "stage": r.get('stage', 1),
            "num_contractions": len(r.get("contractions", [])),
            "avg_contraction_depth": mean([c.get("depth_pct", 0) for c in r.get("contractions", [])]) if r.get("contractions") else 0,
            "avg_contraction_length": mean([c.get("length_bars", 0) for c in r.get("contractions", [])]) if r.get("contractions") else 0,
            "vol_dry_up_in_contractions": mean([c.get("vol_ratio", 1.0) for c in r.get("contractions", [])]) if r.get("contractions") else 1.0,
            "tl_breakout": int(r.get('signals', {}).get('tl_breakout', False)),
            "pivot_breakout": int(r.get('signals', {}).get('pivot_breakout', False)),
            "volume_surge": int(r.get('signals', {}).get('volume_surge', False)),
            "price_surge": int(r.get('signals', {}).get('price_surge', False)),
            "dma20_break": int(r.get('signals', {}).get('dma20_break', False)),
            "score_tightness": r.get('scores', {}).get('tightness', 0),
            "score_rs": r.get('scores', {}).get('rs', 0),
            "score_trend": r.get('scores', {}).get('trend', 0),
            "score_volume": r.get('scores', {}).get('volume', 0),
            "score_proximity": r.get('scores', {}).get('proximity', 0)
        }
        
        for horizon in horizons:
            entry_price, label = _get_entry_price_and_label(
                df, scan_date, horizon, winner_thresholds[horizon], stop_pct
            )
            
            if label is not None and entry_price is not None:
                row = {
                    "ticker": ticker,
                    "scan_date": scan_date,
                    "horizon": horizon,
                    "entry_price": entry_price,
                    "label": label,
                }
                row.update(features)
                rows.append(row)
    except Exception:
        pass
    
    return rows


async def build_training_dataset_async(market_key: str, horizons: list = None,
                                       winner_threshold_pct: dict = None,
                                       stop_pct: float = 7.0) -> pd.DataFrame:
    """Build training dataset from historical scan cache."""
    if horizons is None:
        horizons = HORIZONS
    if winner_threshold_pct is None:
        winner_threshold_pct = WINNER_THRESHOLDS
    
    cached_dates = list_cached_dates(market_key)
    if not cached_dates:
        return pd.DataFrame()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    historical_dates = [d for d in cached_dates if d != today_str]
    
    # Limit to most recent 30 trading days to keep training time reasonable
    historical_dates = historical_dates[:30]
    
    if not historical_dates:
        return pd.DataFrame()
    
    all_rows = []
    
    for scan_date in historical_dates:
        try:
            results = load_scan_cache(market_key, scan_date)
            if not results:
                continue
            
            args_list = [
                (res, scan_date, market_key, horizons, winner_threshold_pct, stop_pct)
                for res in results
            ]
            
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(_process_single_result, args) for args in args_list]
                for future in as_completed(futures):
                    try:
                        rows = future.result()
                        all_rows.extend(rows)
                    except Exception:
                        continue
        except Exception:
            continue
    
    if len(all_rows) < 50:
        return pd.DataFrame()
    
    return pd.DataFrame(all_rows)

# ==============================================================================
# MODEL TRAINING
# ==============================================================================

def train_vcp_models(df_train: pd.DataFrame) -> dict:
    """Train XGBoost models for each horizon."""
    if not XGBOOST_AVAILABLE:
        return {}
    
    if df_train.empty or len(df_train) < 50:
        return {}
    
    models = {}
    
    for horizon in HORIZONS:
        df_h = df_train[df_train["horizon"] == horizon].copy()
        if len(df_h) < 30:
            continue
        
        X = df_h[FEATURE_NAMES].values
        y = df_h["label"].values
        
        if len(np.unique(y)) < 2:
            continue
        
        n_neg = np.sum(y == 0)
        n_pos = np.sum(y == 1)
        scale_pos_weight = n_neg / max(n_pos, 1)
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            random_state=42
        )
        
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        try:
            auc_scores = cross_val_score(model, X_scaled, y, cv=cv, scoring="roc_auc")
            auc_mean = auc_scores.mean()
            auc_std = auc_scores.std()
        except Exception:
            auc_mean = 0.5
            auc_std = 0
        
        model.fit(X_scaled, y)
        
        importance = pd.Series(
            model.feature_importances_,
            index=FEATURE_NAMES
        ).sort_values(ascending=False)
        
        models[horizon] = {
            "model": model,
            "scaler": scaler,
            "auc": float(auc_mean),
            "auc_std": float(auc_std),
            "feature_importance": importance.to_dict(),
            "n_train": len(df_h),
            "n_winners": int(n_pos),
            "n_losers": int(n_neg),
        }
    
    return models

# ==============================================================================
# PREDICTION
# ==============================================================================

def predict_with_models(results: List[dict], models: dict, horizon: int) -> List[PredictionResult]:
    """Generate predictions for scan results."""
    predictions = []
    
    for res in results:
        features = build_feature_vector(res)
        feature_vector = np.array([[features.get(f, 0) for f in FEATURE_NAMES]])
        
        probs = {}
        for h in HORIZONS:
            if h in models:
                model = models[h]["model"]
                scaler = models[h]["scaler"]
                
                try:
                    X_scaled = scaler.transform(feature_vector)
                    prob = model.predict_proba(X_scaled)[0][1]
                    if np.isnan(prob):
                        prob = 0.5
                except Exception:
                    prob = 0.5
                
                probs[h] = float(prob)
            else:
                probs[h] = 0.5
        
        # Get top features from feature importance
        top_features = []
        if horizon in models:
            importance = models[horizon]["feature_importance"]
            sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:3]
            for feat, imp in sorted_features:
                val = features.get(feat, 0)
                top_features.append({
                    "name": feat,
                    "importance": float(imp),
                    "value": float(val)
                })
        
        predictions.append(PredictionResult(
            ticker=res.get("ticker", "Unknown"),
            probabilities=probs,
            top_features=top_features,
            shap_data=None  # Can be added if SHAP available
        ))
    
    return predictions

# ==============================================================================
# KNN PATTERN MATCHER
# ==============================================================================

def find_similar_setups(current_features: dict, df_train: pd.DataFrame, 
                       n_neighbors: int = 5, horizon_filter: int = None) -> pd.DataFrame:
    """Find K-nearest neighbors based on feature similarity."""
    if df_train.empty or len(df_train) < n_neighbors:
        return pd.DataFrame()
    
    df_query = df_train.copy()
    if horizon_filter is not None:
        df_query = df_query[df_query["horizon"] == horizon_filter]
    
    if len(df_query) < n_neighbors:
        df_query = df_train.copy()
    
    X_train = df_query[FEATURE_NAMES].values
    query_vector = np.array([[current_features.get(f, 0) for f in FEATURE_NAMES]])
    
    knn = NearestNeighbors(n_neighbors=min(n_neighbors, len(df_query)), metric="cosine")
    knn.fit(X_train)
    
    distances, indices = knn.kneighbors(query_vector)
    
    similar_setups = []
    for dist, idx in zip(distances[0], indices[0]):
        setup = df_query.iloc[idx].to_dict()
        similarity_pct = (1 - dist) * 100
        setup["similarity"] = similarity_pct
        setup["rank"] = len(similar_setups) + 1
        similar_setups.append(setup)
    
    return pd.DataFrame(similar_setups)

# ==============================================================================
# API ENDPOINTS
# ==============================================================================

@router.post("/build-dataset", response_model=TrainingDatasetResponse)
async def build_dataset(request: TrainingDatasetRequest, background_tasks: BackgroundTasks):
    """Build training dataset from historical scan cache."""
    try:
        df = await build_training_dataset_async(
            request.market_key,
            request.horizons,
            request.winner_thresholds,
            request.stop_pct
        )
        
        if df.empty:
            return TrainingDatasetResponse(
                success=False,
                message="Insufficient training data. Need at least 50 samples."
            )
        
        # Cache the training data
        cache_key = f"{request.market_key}"
        TRAINING_DATA_CACHE[cache_key] = df
        
        winners = int((df["label"] == 1).sum())
        losers = int((df["label"] == 0).sum())
        
        return TrainingDatasetResponse(
            success=True,
            message=f"Successfully built training dataset",
            total_samples=len(df),
            unique_tickers=df["ticker"].nunique(),
            date_range=f"{df['scan_date'].min()} to {df['scan_date'].max()}",
            winners=winners,
            losers=losers
        )
    except Exception as e:
        return TrainingDatasetResponse(
            success=False,
            message=f"Error building dataset: {str(e)}"
        )


@router.post("/train-models", response_model=TrainModelsResponse)
async def train_models(request: TrainingDatasetRequest):
    """Train XGBoost models for each horizon."""
    try:
        cache_key = f"{request.market_key}"
        
        # Get or build training data
        if cache_key not in TRAINING_DATA_CACHE:
            df = await build_training_dataset_async(
                request.market_key,
                request.horizons,
                request.winner_thresholds,
                request.stop_pct
            )
            if df.empty:
                return TrainModelsResponse(
                    success=False,
                    message="No training data available. Build dataset first."
                )
            TRAINING_DATA_CACHE[cache_key] = df
        else:
            df = TRAINING_DATA_CACHE[cache_key]
        
        # Train models
        models = train_vcp_models(df)
        
        if not models:
            return TrainModelsResponse(
                success=False,
                message="Model training failed. Check dataset has both winners and losers."
            )
        
        # Cache models
        MODEL_CACHE[cache_key] = models
        
        # Convert to response format
        model_metrics = []
        for horizon, m in models.items():
            model_metrics.append(ModelMetrics(
                horizon=horizon,
                auc=m["auc"],
                auc_std=m["auc_std"],
                n_train=m["n_train"],
                n_winners=m["n_winners"],
                n_losers=m["n_losers"],
                feature_importance=m["feature_importance"]
            ))
        
        return TrainModelsResponse(
            success=True,
            message=f"Successfully trained {len(models)} models",
            models=model_metrics
        )
    except Exception as e:
        return TrainModelsResponse(
            success=False,
            message=f"Error training models: {str(e)}"
        )


@router.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Generate ML predictions for scan results."""
    try:
        # Get cached models (assuming default market_key)
        cache_key = "US"  # Default, should be passed in request
        if cache_key not in MODEL_CACHE:
            return PredictionResponse(
                success=False,
                predictions=[]
            )
        
        models = MODEL_CACHE[cache_key]
        
        # Convert ScanResult objects to dicts
        results_dicts = [r.model_dump() for r in request.results]
        
        predictions = predict_with_models(results_dicts, models, request.horizon)
        
        return PredictionResponse(
            success=True,
            predictions=predictions
        )
    except Exception as e:
        return PredictionResponse(
            success=False,
            predictions=[]
        )


@router.post("/pattern-match", response_model=PatternMatcherResponse)
async def pattern_match(request: PatternMatcherRequest):
    """Find similar historical setups using KNN."""
    try:
        cache_key = request.market_key
        if cache_key not in TRAINING_DATA_CACHE:
            return PatternMatcherResponse(
                success=False,
                similar_setups=[],
                winner_percentages={}
            )
        
        df_train = TRAINING_DATA_CACHE[cache_key]
        
        similar_df = find_similar_setups(
            request.features,
            df_train,
            request.n_neighbors,
            request.horizon_filter
        )
        
        if similar_df.empty:
            return PatternMatcherResponse(
                success=False,
                similar_setups=[],
                winner_percentages={}
            )
        
        # Convert to response format
        similar_setups = []
        for _, row in similar_df.iterrows():
            similar_setups.append(SimilarSetup(
                ticker=row.get("ticker", "Unknown"),
                scan_date=str(row.get("scan_date", "")),
                similarity=float(row.get("similarity", 0)),
                stage=int(row.get("stage", 1)),
                label=int(row.get("label", 0)),
                horizon=int(row.get("horizon", 2)),
                features={f: float(row.get(f, 0)) for f in FEATURE_NAMES[:10]}
            ))
        
        # Calculate winner percentages by horizon
        winner_pcts = {}
        for h in [2, 5, 10]:
            h_setups = similar_df[similar_df["horizon"] == h]
            if len(h_setups) > 0:
                winner_pcts[h] = float((h_setups["label"] == 1).mean() * 100)
        
        return PatternMatcherResponse(
            success=True,
            similar_setups=similar_setups,
            winner_percentages=winner_pcts
        )
    except Exception as e:
        return PatternMatcherResponse(
            success=False,
            similar_setups=[],
            winner_percentages={}
        )


@router.get("/model-health/{market_key}", response_model=ModelHealthResponse)
async def model_health(market_key: str):
    """Get model health metrics and diagnostics."""
    try:
        if market_key not in MODEL_CACHE:
            return ModelHealthResponse(
                success=False,
                models=[],
                confusion_matrices={},
                feature_names=FEATURE_NAMES
            )
        
        if market_key not in TRAINING_DATA_CACHE:
            return ModelHealthResponse(
                success=False,
                models=[],
                confusion_matrices={},
                feature_names=FEATURE_NAMES
            )
        
        models = MODEL_CACHE[market_key]
        df_train = TRAINING_DATA_CACHE[market_key]
        
        # Build model metrics
        model_metrics = []
        confusion_matrices = {}
        
        for horizon, m in models.items():
            model_metrics.append(ModelMetrics(
                horizon=horizon,
                auc=m["auc"],
                auc_std=m["auc_std"],
                n_train=m["n_train"],
                n_winners=m["n_winners"],
                n_losers=m["n_losers"],
                feature_importance=m["feature_importance"]
            ))
            
            # Compute confusion matrix
            df_h = df_train[df_train["horizon"] == horizon]
            if len(df_h) > 0:
                X = df_h[FEATURE_NAMES].values
                y_true = df_h["label"].values
                
                try:
                    X_scaled = m["scaler"].transform(X)
                    y_pred = m["model"].predict(X_scaled)
                    cm = confusion_matrix(y_true, y_pred).tolist()
                    confusion_matrices[horizon] = cm
                except Exception:
                    confusion_matrices[horizon] = [[0, 0], [0, 0]]
        
        # Compute correlation matrix
        corr_matrix = None
        if not df_train.empty:
            corr = df_train[FEATURE_NAMES].corr()
            corr_matrix = corr.values.tolist()
        
        return ModelHealthResponse(
            success=True,
            models=model_metrics,
            confusion_matrices=confusion_matrices,
            correlation_matrix=corr_matrix,
            feature_names=FEATURE_NAMES
        )
    except Exception as e:
        return ModelHealthResponse(
            success=False,
            models=[],
            confusion_matrices={},
            feature_names=FEATURE_NAMES
        )


@router.get("/status/{market_key}")
async def ml_status(market_key: str):
    """Get ML system status."""
    cached_dates = list_cached_dates(market_key)
    has_training_data = market_key in TRAINING_DATA_CACHE
    has_models = market_key in MODEL_CACHE
    
    training_data_info = None
    if has_training_data:
        df = TRAINING_DATA_CACHE[market_key]
        training_data_info = {
            "total_samples": len(df),
            "unique_tickers": df["ticker"].nunique(),
            "date_range": f"{df['scan_date'].min()} to {df['scan_date'].max()}",
            "winners": int((df["label"] == 1).sum()),
            "losers": int((df["label"] == 0).sum())
        }
    
    model_info = None
    if has_models:
        models = MODEL_CACHE[market_key]
        model_info = {
            "trained_models": len(models),
            "horizons": list(models.keys())
        }
    
    return {
        "market_key": market_key,
        "xgb_available": XGBOOST_AVAILABLE,
        "shap_available": SHAP_AVAILABLE,
        "cache_dates_available": len(cached_dates),
        "has_training_data": has_training_data,
        "has_models": has_models,
        "training_data": training_data_info,
        "models": model_info
    }


class TopPick(BaseModel):
    rank: int
    ticker: str
    name: str
    sector: str
    cap: str
    last_price: float
    score: float
    ml_probability: float
    avg_probability: float
    horizon: int
    top_features: List[Dict[str, Any]]
    stage: int
    checklist: int
    rsi: float
    rs_1y: float
    trend_template: bool = False
    dist_low: float = 0


class TopPicksResponse(BaseModel):
    success: bool
    message: str
    picks: List[TopPick] = []
    generated_at: str


@router.post("/top-picks/{market_key}", response_model=TopPicksResponse)
async def get_top_picks(market_key: str, request: PredictionRequest):
    """Get top 10 ML picks based on prediction probabilities."""
    try:
        if market_key not in MODEL_CACHE:
            return TopPicksResponse(
                success=False,
                message="No trained models available. Train models first.",
                picks=[],
                generated_at=datetime.now().isoformat()
            )
        
        models = MODEL_CACHE[market_key]
        
        # Convert ScanResult objects to dicts
        results_dicts = [r.model_dump() for r in request.results]
        
        # PRE-FILTER: Strictly enforce Stage 2 trend for VCP Picking
        stage2_results = [r for r in results_dicts if r.get("stage") == 2 or r.get("trend_template")]
        use_results = stage2_results if len(stage2_results) >= 5 else results_dicts
        
        # Generate predictions for all results
        predictions = predict_with_models(use_results, models, request.horizon)
        
        # Combine predictions with result data and sort by ML probability
        picks_with_scores = []
        for pred, res in zip(predictions, use_results):
            avg_prob = sum(pred.probabilities.values()) / len(pred.probabilities) if pred.probabilities else 0.5
            picks_with_scores.append({
                "prediction": pred,
                "result": res,
                "avg_probability": avg_prob,
                "primary_probability": pred.probabilities.get(request.horizon, 0.5)
            })
        
        # Sort by primary horizon probability descending
        picks_with_scores.sort(key=lambda x: x["primary_probability"], reverse=True)
        
        # Take top 10
        top_picks = picks_with_scores[:10]
        
        # Build response
        picks_response = []
        for rank, pick_data in enumerate(top_picks, 1):
            res = pick_data["result"]
            pred = pick_data["prediction"]
            
            picks_response.append(TopPick(
                rank=rank,
                ticker=res.get("ticker", "Unknown"),
                name=res.get("name", ""),
                sector=res.get("sector", ""),
                cap=res.get("cap", ""),
                last_price=res.get("last_price", 0),
                score=res.get("score", 0),
                ml_probability=pick_data["primary_probability"],
                avg_probability=pick_data["avg_probability"],
                horizon=request.horizon,
                top_features=pred.top_features[:3],
                stage=res.get("stage", 1),
                checklist=res.get("checklist", 0),
                rsi=res.get("rsi", 50),
                rs_1y=res.get("rs_1y", 100),
                trend_template=bool(res.get("trend_template", False)),
                dist_low=float(res.get("dist_low", 0))
            ))
        
        return TopPicksResponse(
            success=True,
            message=f"Top {len(picks_response)} ML picks generated",
            picks=picks_response,
            generated_at=datetime.now().isoformat()
        )
    except Exception as e:
        return TopPicksResponse(
            success=False,
            message=f"Error generating top picks: {str(e)}",
            picks=[],
            generated_at=datetime.now().isoformat()
        )

"""
ML Intelligence Tab for VCP Scanner Dashboard
Complete XGBoost-based machine learning prediction system with pattern matching
and SHAP explainability. Integrates with existing VCP scanner infrastructure.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean
import warnings
warnings.filterwarnings('ignore')

# ML imports
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

# Import existing infrastructure functions
from data_manager import list_cached_dates, load_scan_cache
from engine import fetch_data, compute_indicators, DETECTOR

# ==============================================================================
# CONSTANTS
# ==============================================================================

# Feature vector keys - ALWAYS maintain this exact sorted order
FEATURE_NAMES = sorted([
    "score", "checklist", "bbw_pctl", "rs_ratio", "vol_ratio", "rsi", "adx",
    "dist52", "tight", "wbase", "sqz", "tier_enc", "pdh_brk", "atr_pct",
    "trend", "r1", "r5", "r21", "r63", "stage", "num_contractions",
    "avg_contraction_depth", "avg_contraction_length", "vol_dry_up_in_contractions",
    "tl_breakout", "pivot_breakout", "volume_surge", "price_surge", "dma20_break",
    "score_tightness", "score_rs", "score_trend", "score_volume", "score_proximity"
])

HORIZONS = [2, 5, 10]
WINNER_THRESHOLDS = {2: 3.0, 5: 5.0, 10: 8.0}
STOP_PCT = 7.0

# CSS styles for Streamlit components
ML_CARD_CSS = """
<style>
.ml-card {
    background: linear-gradient(135deg, #111827 0%, #0a0e1a 100%);
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}
.ml-card:hover {
    border-color: #3b82f6;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}
.ml-ticker {
    font-family: 'JetBrains Mono', monospace;
    font-size: 20px;
    font-weight: 700;
    color: #f9fafb;
}
.ml-name {
    font-size: 12px;
    color: #6b7280;
    margin-left: 8px;
}
.ml-prob-bar {
    display: inline-block;
    width: 100px;
    height: 8px;
    background: #1f2937;
    border-radius: 4px;
    overflow: hidden;
    margin-right: 8px;
}
.ml-prob-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
}
.ml-metric {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: #94a3b8;
    margin-right: 12px;
}
.ml-metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    color: #f9fafb;
}
.ml-chip {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    margin-right: 4px;
}
.ml-chip-green { background: rgba(74, 222, 128, 0.15); color: #4ade80; }
.ml-chip-blue { background: rgba(96, 165, 250, 0.15); color: #60a5fa; }
.ml-chip-yellow { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
.ml-chip-red { background: rgba(248, 113, 113, 0.15); color: #f87171; }
.ml-chip-indigo { background: rgba(129, 140, 248, 0.15); color: #818cf8; }
.ml-feature-arrow {
    font-size: 10px;
    margin-right: 2px;
}
.ml-feature-pos { color: #4ade80; }
.ml-feature-neg { color: #f87171; }
.ml-status-green { color: #4ade80; }
.ml-status-yellow { color: #fbbf24; }
.ml-status-red { color: #f87171; }
.ml-similarity-card {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 8px;
}
.ml-sparkline {
    width: 100%;
    height: 40px;
}
.ml-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}
.ml-table th {
    text-align: left;
    padding: 8px;
    border-bottom: 1px solid #1f2937;
    color: #6b7280;
    font-weight: 600;
}
.ml-table td {
    padding: 8px;
    border-bottom: 1px solid #1f2937;
}
.ml-table tr:hover {
    background: rgba(59, 130, 246, 0.05);
}
</style>
"""

# ==============================================================================
# FEATURE ENGINEERING
# ==============================================================================

def build_feature_vector(res: dict) -> dict:
    """
    Extract a complete feature vector from a scan result dictionary.
    All features are numeric with sensible defaults for missing values.
    
    Args:
        res: Scan result dictionary from VCP detector
        
    Returns:
        Dictionary with all features in consistent sorted order
    """
    # Extract contraction statistics
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
    
    # Extract signals
    signals = res.get("signals", {})
    scores = res.get("scores", {})
    
    features = {
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
    
    return features


# ==============================================================================
# TRAINING DATASET BUILDER
# ==============================================================================

def _get_entry_price_and_label(df: pd.DataFrame, scan_date_str: str, horizon: int, 
                                winner_threshold: float, stop_pct: float) -> tuple:
    """
    Find entry price at scan date and determine label based on forward performance.
    
    Returns:
        tuple: (entry_price, label) where label is 1 (winner), 0 (loser), or None (open trade)
    """
    try:
        scan_date = pd.Timestamp(scan_date_str).normalize()
        
        # Find nearest prior business day if scan_date not in index
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
        
        # Look forward horizon bars
        end_idx = min(entry_idx + horizon, len(df) - 1)
        forward_df = df.iloc[entry_idx + 1:end_idx + 1]
        
        if len(forward_df) == 0:
            return entry_price, None
        
        for _, row in forward_df.iterrows():
            if row["Low"] <= stop_price:
                return entry_price, 0  # Stop hit
            if row["High"] >= target_price:
                return entry_price, 1  # Winner
        
        # Neither triggered - open trade, skip this row
        return entry_price, None
        
    except Exception:
        return None, None


def _process_single_result(args: tuple) -> list:
    """Process a single scan result for all horizons. Returns list of training rows."""
    res, scan_date, market_key, horizons, winner_thresholds, stop_pct = args
    
    rows = []
    ticker = res.get("ticker")
    if not ticker:
        return rows
    
    try:
        # Fetch data for this ticker
        df = fetch_data(ticker, "1y")
        if df is None or df.empty or len(df) < 60:
            return rows
        
        # Extract features
        features = build_feature_vector(res)
        
        # Process each horizon
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


def build_training_dataset(market_key: str, 
                          horizons: list = None,
                          winner_threshold_pct: dict = None,
                          stop_pct: float = 7.0) -> pd.DataFrame:
    """
    Build a comprehensive training dataset from historical scan cache.
    
    Args:
        market_key: "US" or "IN"
        horizons: List of forward-looking horizons in days [2, 5, 10]
        winner_threshold_pct: Dict mapping horizon to winner threshold %
        stop_pct: Stop loss percentage
        
    Returns:
        DataFrame with all features + label + horizon + scan_date + ticker
    """
    if horizons is None:
        horizons = HORIZONS
    if winner_threshold_pct is None:
        winner_threshold_pct = WINNER_THRESHOLDS
    
    # Get all available cached dates
    cached_dates = list_cached_dates(market_key)
    if not cached_dates:
        return pd.DataFrame()
    
    # Skip today (first date is usually today)
    today_str = datetime.now().strftime("%Y-%m-%d")
    historical_dates = [d for d in cached_dates if d != today_str]
    
    if not historical_dates:
        return pd.DataFrame()
    
    all_rows = []
    
    # Process each historical date
    for scan_date in historical_dates:
        try:
            results = load_scan_cache(market_key, scan_date)
            if not results:
                continue
            
            # Prepare arguments for parallel processing
            args_list = [
                (res, scan_date, market_key, horizons, winner_threshold_pct, stop_pct)
                for res in results
            ]
            
            # Process in parallel
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
    
    df = pd.DataFrame(all_rows)
    return df


# ==============================================================================
# MODEL TRAINING
# ==============================================================================

def train_vcp_models(df_train: pd.DataFrame) -> dict:
    """
    Train XGBoost models for each horizon using cross-validation.
    
    Args:
        df_train: Training DataFrame with features and labels
        
    Returns:
        Dictionary with trained models, scalers, and metrics per horizon
    """
    if not XGBOOST_AVAILABLE:
        return {}
    
    if df_train.empty or len(df_train) < 50:
        return {}
    
    models = {}
    
    for horizon in HORIZONS:
        # Filter data for this horizon
        df_h = df_train[df_train["horizon"] == horizon].copy()
        if len(df_h) < 30:
            continue
        
        # Prepare features and target
        X = df_h[FEATURE_NAMES].values
        y = df_h["label"].values
        
        # Check for single class
        if len(np.unique(y)) < 2:
            continue
        
        # Compute class imbalance weight
        n_neg = np.sum(y == 0)
        n_pos = np.sum(y == 1)
        scale_pos_weight = n_neg / max(n_pos, 1)
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Train model
        model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            use_label_encoder=False,
            eval_metric="logloss",
            random_state=42
        )
        
        # Cross-validation
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        try:
            auc_scores = cross_val_score(model, X_scaled, y, cv=cv, scoring="roc_auc")
            auc_mean = auc_scores.mean()
            auc_std = auc_scores.std()
        except Exception:
            auc_mean = 0.5
            auc_std = 0
        
        # Fit final model on all data
        model.fit(X_scaled, y)
        
        # Feature importance
        importance = pd.Series(
            model.feature_importances_,
            index=FEATURE_NAMES
        ).sort_values(ascending=False)
        
        models[horizon] = {
            "model": model,
            "scaler": scaler,
            "auc": float(auc_mean),
            "auc_std": float(auc_std),
            "feature_importance": importance,
            "n_train": len(df_h),
            "n_winners": int(n_pos),
            "n_losers": int(n_neg),
        }
    
    return models


# ==============================================================================
# KNN PATTERN MATCHER
# ==============================================================================

def find_similar_setups(current_features: dict, 
                       df_train: pd.DataFrame, 
                       n_neighbors: int = 5,
                       horizon_filter: int = None) -> pd.DataFrame:
    """
    Find K-nearest neighbors based on feature similarity.
    
    Args:
        current_features: Feature vector for current stock
        df_train: Training dataset
        n_neighbors: Number of similar setups to find
        horizon_filter: Optional horizon to filter by (2, 5, or 10)
        
    Returns:
        DataFrame with similar historical setups and similarity scores
    """
    if df_train.empty or len(df_train) < n_neighbors:
        return pd.DataFrame()
    
    # Filter by horizon if specified
    df_query = df_train.copy()
    if horizon_filter is not None:
        df_query = df_query[df_query["horizon"] == horizon_filter]
    
    if len(df_query) < n_neighbors:
        df_query = df_train.copy()
    
    # Extract feature matrix
    X_train = df_query[FEATURE_NAMES].values
    
    # Create feature vector for query
    query_vector = np.array([[current_features.get(f, 0) for f in FEATURE_NAMES]])
    
    # Fit KNN and find neighbors
    knn = NearestNeighbors(n_neighbors=min(n_neighbors, len(df_query)), metric="cosine")
    knn.fit(X_train)
    
    distances, indices = knn.kneighbors(query_vector)
    
    # Build result DataFrame
    similar_setups = []
    for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
        setup = df_query.iloc[idx].to_dict()
        # Cosine similarity = 1 - cosine distance, convert to percentage
        similarity_pct = (1 - dist) * 100
        setup["similarity"] = similarity_pct
        setup["rank"] = i + 1
        similar_setups.append(setup)
    
    return pd.DataFrame(similar_setups)


# ==============================================================================
# SHAP EXPLAINABILITY
# ==============================================================================

def compute_shap_values(model, features_df: pd.DataFrame, feature_names: list = None) -> dict:
    """
    Compute SHAP values for model predictions.
    
    Args:
        model: Trained XGBoost model
        features_df: DataFrame of features to explain
        feature_names: List of feature names in order
        
    Returns:
        Dictionary with SHAP values per feature
    """
    if not SHAP_AVAILABLE or model is None:
        return {}
    
    if feature_names is None:
        feature_names = FEATURE_NAMES
    
    try:
        explainer = shap.TreeExplainer(model)
        X = features_df[feature_names].values
        shap_values = explainer.shap_values(X)
        
        # Build results dictionary
        results = {}
        for idx, row in features_df.iterrows():
            sv = shap_values[idx] if len(shap_values.shape) > 1 else shap_values
            feature_contributions = {
                name: float(sv[i]) if i < len(sv) else 0
                for i, name in enumerate(feature_names)
            }
            # Sort by absolute contribution
            sorted_contributions = dict(sorted(
                feature_contributions.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            ))
            results[idx] = {
                "contributions": sorted_contributions,
                "base_value": float(explainer.expected_value) if hasattr(explainer, 'expected_value') else 0.5,
                "prediction": float(model.predict_proba(X[idx:idx+1])[0][1]) if hasattr(model, 'predict_proba') else 0.5
            }
        
        return results
    except Exception:
        return {}


# ==============================================================================
# SUB-TAB RENDERERS
# ==============================================================================

def _render_dataset_summary(df_train: pd.DataFrame):
    """Render dataset summary metrics."""
    st.markdown("<div class='section-hdr'>Dataset Summary</div>", unsafe_allow_html=True)
    
    total_samples = len(df_train)
    winners = len(df_train[df_train["label"] == 1])
    losers = total_samples - winners
    win_ratio = winners / total_samples * 100 if total_samples > 0 else 0
    
    unique_tickers = df_train["ticker"].nunique()
    date_range = f"{df_train['scan_date'].min()} to {df_train['scan_date'].max()}"
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Total Samples</div>
            <div class='metric-value'>{total_samples:,}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Winners / Losers</div>
            <div class='metric-value'>{winners:,} / {losers:,}</div>
            <div class='metric-delta'>{win_ratio:.1f}% win rate</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Unique Tickers</div>
            <div class='metric-value'>{unique_tickers}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Date Range</div>
            <div class='metric-value' style='font-size:14px'>{date_range}</div>
        </div>
        """, unsafe_allow_html=True)


def _render_feature_importance(models: dict):
    """Render feature importance charts for each horizon."""
    st.markdown("<div class='section-hdr'>Feature Importance by Horizon</div>", unsafe_allow_html=True)
    
    if not models:
        st.info("Train models to see feature importance")
        return
    
    tabs = st.tabs(["2-Day", "5-Day", "10-Day"])
    
    for tab, horizon in zip(tabs, HORIZONS):
        with tab:
            if horizon not in models:
                st.info(f"No model trained for {horizon}-day horizon")
                continue
            
            importance = models[horizon]["feature_importance"]
            
            # Create horizontal bar chart
            fig = go.Figure()
            
            # Color gradient from blue to cyan
            colors = [f'rgba(29, 78, 216, {0.3 + 0.7 * (i / len(importance))})' 
                     for i in range(len(importance))]
            
            # Add star emoji to top 5
            y_labels = [f"{'⭐ ' if i < 5 else ''}{name}" 
                       for i, name in enumerate(importance.index)]
            
            fig.add_trace(go.Bar(
                x=importance.values,
                y=y_labels,
                orientation='h',
                marker_color=colors,
                text=[f"{v:.3f}" for v in importance.values],
                textposition='outside',
                textfont=dict(color='#94a3b8', size=10)
            ))
            
            fig.update_layout(
                paper_bgcolor="#0a0e1a",
                plot_bgcolor="#0a0e1a",
                font=dict(color="#94a3b8", family="Inter"),
                height=500,
                margin=dict(l=150, r=50, t=30, b=30),
                xaxis=dict(
                    title="Importance",
                    gridcolor="#1f2937",
                    zerolinecolor="#1f2937"
                ),
                yaxis=dict(
                    gridcolor="#1f2937",
                    zerolinecolor="#1f2937",
                    autorange="reversed"
                ),
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)


def _render_winner_loser_distributions(df_train: pd.DataFrame, models: dict):
    """Render distribution comparisons for top 6 features."""
    st.markdown("<div class='section-hdr'>Winner vs Loser Distributions</div>", unsafe_allow_html=True)
    
    if df_train.empty or not models:
        return
    
    # Get top 6 features from first available model
    first_horizon = list(models.keys())[0]
    top_features = list(models[first_horizon]["feature_importance"].head(6).index)
    
    # Create subplots
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=top_features,
        vertical_spacing=0.1,
        horizontal_spacing=0.1
    )
    
    winners_df = df_train[df_train["label"] == 1]
    losers_df = df_train[df_train["label"] == 0]
    
    for i, feature in enumerate(top_features):
        row = (i // 2) + 1
        col = (i % 2) + 1
        
        # Add histograms
        fig.add_trace(
            go.Histogram(
                x=winners_df[feature],
                name="Winners",
                marker_color="#4ade80",
                opacity=0.6,
                showlegend=(i == 0),
                nbinsx=20
            ),
            row=row, col=col
        )
        
        fig.add_trace(
            go.Histogram(
                x=losers_df[feature],
                name="Losers",
                marker_color="#f87171",
                opacity=0.6,
                showlegend=(i == 0),
                nbinsx=20
            ),
            row=row, col=col
        )
        
        # Add median lines
        if not winners_df[feature].empty:
            winner_median = winners_df[feature].median()
            fig.add_vline(
                x=winner_median,
                line=dict(color="#4ade80", dash="dash", width=2),
                row=row, col=col
            )
        
        if not losers_df[feature].empty:
            loser_median = losers_df[feature].median()
            fig.add_vline(
                x=loser_median,
                line=dict(color="#f87171", dash="dash", width=2),
                row=row, col=col
            )
    
    fig.update_layout(
        paper_bgcolor="#0a0e1a",
        plot_bgcolor="#0a0e1a",
        font=dict(color="#94a3b8", family="Inter"),
        height=800,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Update all subplots with dark theme
    for i in fig['layout']['annotations']:
        i['font'] = dict(color="#f9fafb", size=12)
    
    fig.update_xaxes(gridcolor="#1f2937", zerolinecolor="#1f2937")
    fig.update_yaxes(gridcolor="#1f2937", zerolinecolor="#1f2937")
    
    st.plotly_chart(fig, use_container_width=True)


def render_winner_dna_tab(df_train: pd.DataFrame, models: dict):
    """Render the Winner DNA sub-tab."""
    _render_dataset_summary(df_train)
    st.markdown("<br>", unsafe_allow_html=True)
    _render_feature_importance(models)
    st.markdown("<br>", unsafe_allow_html=True)
    _render_winner_loser_distributions(df_train, models)


# ==============================================================================
# PATTERN MATCHER TAB
# ==============================================================================

def _color_code_value(value: float, train_values: pd.Series) -> str:
    """Return color class based on percentile rank."""
    if train_values.empty:
        return "#94a3b8"
    
    low_thresh = train_values.quantile(0.3)
    high_thresh = train_values.quantile(0.7)
    
    if value >= high_thresh:
        return "#4ade80"  # Green
    elif value <= low_thresh:
        return "#f87171"  # Red
    else:
        return "#94a3b8"  # Gray


def _generate_sparkline_svg(prices: list, width: int = 100, height: int = 40) -> str:
    """Generate SVG sparkline for price path."""
    if not prices or len(prices) < 2:
        return ""
    
    min_p, max_p = min(prices), max(prices)
    if max_p == min_p:
        return ""
    
    points = []
    for i, p in enumerate(prices):
        x = (i / (len(prices) - 1)) * width
        y = height - ((p - min_p) / (max_p - min_p)) * height
        points.append(f"{x},{y}")
    
    path_d = f"M{points[0]} " + " ".join([f"L{p}" for p in points[1:]])
    
    color = "#4ade80" if prices[-1] >= prices[0] else "#f87171"
    
    svg = f'''
    <svg class="ml-sparkline" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
        <path d="{path_d}" fill="none" stroke="{color}" stroke-width="2"/>
    </svg>
    '''
    return svg


def render_pattern_matcher_tab(results: list, df_train: pd.DataFrame):
    """Render the Pattern Matcher sub-tab."""
    st.markdown("<div class='section-hdr'>Pattern Matcher</div>", unsafe_allow_html=True)
    
    if not results:
        st.info("No scan results available. Run a scan first.")
        return
    
    if df_train.empty or len(df_train) < 10:
        st.info("Insufficient training data. Run 'Pre-load batch cache' to build more history.")
        return
    
    col1, col2 = st.columns([0.4, 0.6])
    
    with col1:
        # Ticker selector
        ticker_options = [r.get("ticker", "Unknown") for r in results if r.get("ticker")]
        selected_ticker = st.selectbox("Select Ticker", ticker_options)
        
        # Find selected result
        selected_res = None
        for r in results:
            if r.get("ticker") == selected_ticker:
                selected_res = r
                break
        
        if selected_res:
            # Extract features
            features = build_feature_vector(selected_res)
            
            # Show current features table
            st.markdown("<div style='font-size:12px; color:#94a3b8; margin:12px 0 8px'>Current Features</div>", 
                     unsafe_allow_html=True)
            
            feature_html = "<table class='ml-table'>"
            feature_html += "<tr><th>Feature</th><th>Value</th></tr>"
            
            for feat_name in FEATURE_NAMES[:15]:  # Show first 15 features
                val = features.get(feat_name, 0)
                color = _color_code_value(val, df_train[feat_name])
                feature_html += f"<tr><td>{feat_name}</td><td style='color:{color}; font-family:JetBrains Mono'>{val:.2f}</td></tr>"
            
            feature_html += "</table>"
            st.markdown(feature_html, unsafe_allow_html=True)
            
            # Show contractions
            contractions = selected_res.get("contractions", [])
            if contractions:
                st.markdown(f"<div style='margin-top:12px'><span class='chip chip-blue'>{len(contractions)} Contractions</span></div>", 
                          unsafe_allow_html=True)
                for i, c in enumerate(contractions[:3]):
                    depth = c.get("depth_pct", 0)
                    length = c.get("length_bars", 0)
                    st.markdown(f"<div style='font-size:11px; color:#6b7280'>C{i+1}: {depth:.1f}% depth, {length} bars</div>", 
                              unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div style='font-size:14px; font-weight:600; color:#f9fafb; margin-bottom:12px'>5 Most Similar Historical Setups</div>", 
                  unsafe_allow_html=True)
        
        if selected_res:
            # Find similar setups
            similar = find_similar_setups(features, df_train, n_neighbors=5)
            
            if similar.empty:
                st.info("No similar setups found in training data.")
            else:
                # Show similar setups
                for _, setup in similar.iterrows():
                    ticker = setup.get("ticker", "Unknown")
                    scan_date = setup.get("scan_date", "Unknown")
                    similarity = setup.get("similarity", 0)
                    stage = setup.get("stage", 1)
                    label = setup.get("label", 0)
                    horizon = setup.get("horizon", 2)
                    
                    stage_class = f"s{stage}"
                    outcome_class = "chip-green" if label == 1 else "chip-red"
                    outcome_text = "Winner" if label == 1 else "Loser"
                    
                    # Generate sparkline if we can fetch data
                    sparkline_svg = ""
                    try:
                        df = fetch_data(ticker, "1y")
                        if df is not None and not df.empty:
                            # Get 10 bars around scan date
                            scan_ts = pd.Timestamp(scan_date)
                            if scan_ts in df.index:
                                idx = df.index.get_loc(scan_ts)
                                end_idx = min(idx + 10, len(df) - 1)
                                prices = df.iloc[idx:end_idx]["Close"].tolist()
                                sparkline_svg = _generate_sparkline_svg(prices)
                    except Exception:
                        pass
                    
                    card_html = f"""
                    <div class='ml-similarity-card'>
                        <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px'>
                            <div>
                                <span style='font-family:JetBrains Mono; font-weight:700; color:#f9fafb; font-size:16px'>{ticker}</span>
                                <span style='font-size:11px; color:#6b7280; margin-left:8px'>{scan_date}</span>
                            </div>
                            <span class='stage-badge {stage_class}'>S{stage}</span>
                        </div>
                        <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px'>
                            <span style='font-size:12px; color:#94a3b8'>Similarity: <span style='color:#60a5fa; font-weight:600'>{similarity:.1f}%</span></span>
                            <span class='chip {outcome_class}'>{outcome_text} ({horizon}d)</span>
                        </div>
                        {sparkline_svg}
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)
                
                # Summary stats
                winner_pct_by_horizon = {}
                for h in [2, 5, 10]:
                    h_setups = similar[similar["horizon"] == h]
                    if len(h_setups) > 0:
                        winner_pct = (h_setups["label"] == 1).mean() * 100
                        winner_pct_by_horizon[h] = winner_pct
                
                if winner_pct_by_horizon:
                    summary_text = "Among similar setups: " + ", ".join([
                        f"{h}d: <span style='color:{('#4ade80' if pct > 50 else '#f87171')}'>{pct:.0f}% won</span>"
                        for h, pct in winner_pct_by_horizon.items()
                    ])
                    st.markdown(f"<div style='background:#111827; border:1px solid #1f2937; border-radius:8px; padding:12px; margin-top:12px; font-size:13px'>{summary_text}</div>", 
                              unsafe_allow_html=True)


# ==============================================================================
# ML RANKED PICKS TAB
# ==============================================================================

def _render_stock_card(res: dict, probs: dict, shap_data: dict = None):
    """Render a single stock card with ML predictions."""
    ticker = res.get("ticker", "Unknown")
    name = res.get("name", "")
    stage = res.get("stage", 1)
    score = res.get("score", 0)
    rsi = res.get("rsi", 50)
    vol_ratio = res.get("vol_r", 1.0)
    pct_off_high = res.get("pct_off_high", 0)
    
    # Get active signals
    signals = res.get("signals", {})
    active_signals = []
    if signals.get("tl_breakout"):
        active_signals.append("TL Break")
    if signals.get("volume_surge"):
        active_signals.append("Vol↑")
    if signals.get("pivot_breakout"):
        active_signals.append("Pivot")
    if signals.get("dma20_break"):
        active_signals.append("20DMA")
    
    # Build probability bars
    prob_bars_html = ""
    for h in [2, 5, 10]:
        prob = probs.get(h, 0.5)
        prob_pct = prob * 100
        bar_width = int(prob_pct)
        bar_color = "#4ade80" if prob_pct >= 60 else "#fbbf24" if prob_pct >= 50 else "#f87171"
        
        prob_bars_html += f"""
        <div style='display:inline-block; margin-right:16px'>
            <span style='font-size:11px; color:#6b7280'>{h}d:</span>
            <div class='ml-prob-bar'>
                <div class='ml-prob-fill' style='width:{bar_width}%; background:{bar_color}'></div>
            </div>
            <span style='font-family:JetBrains Mono; font-size:12px; color:{bar_color}; font-weight:600'>{prob_pct:.0f}%</span>
        </div>
        """
    
    # Build signal chips
    signal_chips_html = ""
    for sig in active_signals:
        signal_chips_html += f"<span class='ml-chip ml-chip-blue'>{sig}</span>"
    
    # Build top features if SHAP data available
    features_html = ""
    if shap_data and "contributions" in shap_data:
        top_features = list(shap_data["contributions"].items())[:3]
        features_html = "<div style='margin-top:8px; font-size:11px; color:#6b7280'>Key drivers: "
        for feat_name, contrib in top_features:
            arrow = "▲" if contrib > 0 else "▼"
            color_class = "ml-feature-pos" if contrib > 0 else "ml-feature-neg"
            features_html += f"<span class='{color_class}'><span class='ml-feature-arrow'>{arrow}</span>{feat_name}</span> "
        features_html += "</div>"
    
    stage_colors = {1: "#4ade80", 2: "#60a5fa", 3: "#fbbf24", 4: "#f87171"}
    stage_color = stage_colors.get(stage, "#94a3b8")
    
    card_html = f"""
    <div class='ml-card'>
        <div style='display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px'>
            <div>
                <span class='ml-ticker'>{ticker}</span>
                <span class='ml-name'>{name}</span>
            </div>
            <span style='background:{stage_color}20; color:{stage_color}; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:600'>Stage {stage}</span>
        </div>
        <div style='margin-bottom:8px'>
            {prob_bars_html}
        </div>
        <div style='margin-bottom:8px'>
            <span class='ml-metric'>VCP Score: <span class='ml-metric-value'>{score:.0f}</span></span>
            <span class='ml-metric'>RSI: <span class='ml-metric-value'>{rsi:.0f}</span></span>
            <span class='ml-metric'>Vol: <span class='ml-metric-value'>{vol_ratio:.1f}×</span></span>
            <span class='ml-metric'>% Off Hi: <span class='ml-metric-value'>{pct_off_high:.1f}%</span></span>
        </div>
        <div style='margin-bottom:4px'>
            {signal_chips_html}
        </div>
        {features_html}
    </div>
    """
    
    return card_html


def render_ml_ranked_picks_tab(results: list, models: dict, df_train: pd.DataFrame):
    """Render the ML Ranked Picks sub-tab."""
    st.markdown("<div class='section-hdr'>ML Ranked Picks</div>", unsafe_allow_html=True)
    
    if not results:
        st.info("No scan results available. Run a scan first.")
        return
    
    if not models or not XGBOOST_AVAILABLE:
        st.warning("Models not trained or XGBoost not available. Click 'Retrain XGBoost Models' button.")
        return
    
    # Controls row
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1.5])
    
    with col1:
        horizon_filter = st.radio("Horizon", [2, 5, 10], horizontal=True)
    
    with col2:
        min_prob = st.slider("Min Probability", 0, 100, 55) / 100
    
    with col3:
        stage_2_only = st.toggle("Stage 2 Only", False)
    
    with col4:
        sort_by = st.selectbox("Sort By", ["Win Probability", "VCP Score", "Combined Score"])
    
    # Calculate predictions for all results
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
                
                probs[h] = prob
            else:
                probs[h] = 0.5
        
        # Compute SHAP values if available
        shap_data = None
        if SHAP_AVAILABLE and horizon_filter in models:
            try:
                model = models[horizon_filter]["model"]
                shap_results = compute_shap_values(model, pd.DataFrame([features]), FEATURE_NAMES)
                if shap_results:
                    shap_data = list(shap_results.values())[0]
            except Exception:
                pass
        
        # Calculate combined score
        vcp_score = res.get("score", 0)
        prob_score = probs.get(horizon_filter, 0.5) * 100
        
        if sort_by == "Win Probability":
            sort_key = prob_score
        elif sort_by == "VCP Score":
            sort_key = vcp_score
        else:  # Combined Score
            sort_key = 0.5 * prob_score + 0.5 * (vcp_score / 100 * 100)
        
        predictions.append({
            "res": res,
            "probs": probs,
            "sort_key": sort_key,
            "shap_data": shap_data
        })
    
    # Filter and sort
    filtered = [
        p for p in predictions 
        if p["probs"].get(horizon_filter, 0) >= min_prob
        and (not stage_2_only or p["res"].get("stage") == 2)
    ]
    
    filtered.sort(key=lambda x: x["sort_key"], reverse=True)
    
    # Render stock cards
    if filtered:
        for pred in filtered:
            card_html = _render_stock_card(pred["res"], pred["probs"], pred["shap_data"])
            st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.info(f"No stocks meet the criteria (min probability: {min_prob*100:.0f}%)")
    
    # Summary table
    if filtered:
        st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
        
        table_data = []
        for pred in filtered:
            res = pred["res"]
            probs = pred["probs"]
            
            signals = res.get("signals", {})
            signal_count = sum([
                signals.get("tl_breakout", False),
                signals.get("pivot_breakout", False),
                signals.get("volume_surge", False),
                signals.get("price_surge", False),
                signals.get("dma20_break", False)
            ])
            
            table_data.append({
                "Ticker": res.get("ticker", ""),
                "Win Prob 2d": f"{probs.get(2, 0.5)*100:.0f}%",
                "Win Prob 5d": f"{probs.get(5, 0.5)*100:.0f}%",
                "Win Prob 10d": f"{probs.get(10, 0.5)*100:.0f}%",
                "VCP Score": res.get("score", 0),
                "Stage": res.get("stage", 1),
                "RSI": res.get("rsi", 50),
                "Vol Ratio": res.get("vol_r", 1.0),
                "Signals": signal_count
            })
        
        df_summary = pd.DataFrame(table_data)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)
        
        # Download button
        csv = df_summary.to_csv(index=False)
        st.download_button(
            "Export to CSV",
            csv,
            f"ml_ranked_picks_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )


# ==============================================================================
# MODEL HEALTH TAB
# ==============================================================================

def render_model_health_tab(df_train: pd.DataFrame, models: dict):
    """Render the Model Health sub-tab."""
    st.markdown("<div class='section-hdr'>Model Health</div>", unsafe_allow_html=True)
    
    if not models or not XGBOOST_AVAILABLE:
        st.warning("Models not trained or XGBoost not available.")
        return
    
    # Section A: Model Performance Metrics
    st.markdown("<div style='font-size:13px; font-weight:600; color:#f9fafb; margin:16px 0 12px'>Model Performance Metrics</div>", 
              unsafe_allow_html=True)
    
    cols = st.columns(len(HORIZONS))
    
    for col, horizon in zip(cols, HORIZONS):
        if horizon in models:
            m = models[horizon]
            auc = m["auc"]
            auc_std = m["auc_std"]
            n_train = m["n_train"]
            winner_ratio = m["n_winners"] / n_train * 100 if n_train > 0 else 0
            edge = (auc - 0.5) * 100
            
            edge_color = "#4ade80" if edge > 0 else "#f87171"
            
            col.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>{horizon}-Day Model</div>
                <div class='metric-value'>{auc:.3f} <span style='font-size:14px; color:#6b7280'>± {auc_std:.3f}</span></div>
                <div class='metric-delta'>ROC-AUC</div>
                <div style='margin-top:8px; font-size:12px; color:#94a3b8'>
                    Samples: {n_train:,}<br>
                    Win Rate: {winner_ratio:.1f}%<br>
                    Edge: <span style='color:{edge_color}'>{edge:+.1f}%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Section B: Confusion Matrix Heatmap
    st.markdown("<div style='font-size:13px; font-weight:600; color:#f9fafb; margin:24px 0 12px'>Confusion Matrix (Last CV Fold)</div>", 
              unsafe_allow_html=True)
    
    # Build confusion matrices from training data
    cm_tabs = st.tabs(["2-Day", "5-Day", "10-Day"])
    
    for tab, horizon in zip(cm_tabs, HORIZONS):
        with tab:
            if horizon not in models:
                st.info(f"No model for {horizon}-day horizon")
                continue
            
            df_h = df_train[df_train["horizon"] == horizon]
            if len(df_h) < 10:
                st.info("Insufficient data")
                continue
            
            # Get predictions for confusion matrix
            model = models[horizon]["model"]
            scaler = models[horizon]["scaler"]
            
            X = df_h[FEATURE_NAMES].values
            y_true = df_h["label"].values
            
            try:
                X_scaled = scaler.transform(X)
                y_pred = model.predict(X_scaled)
                
                cm = confusion_matrix(y_true, y_pred)
                
                # Plot confusion matrix
                fig = go.Figure(data=go.Heatmap(
                    z=cm,
                    x=["Predicted 0", "Predicted 1"],
                    y=["Actual 0", "Actual 1"],
                    text=cm,
                    texttemplate="%{text}",
                    colorscale=[[0, "#1d4ed8"], [1, "#06b6d4"]],
                    showscale=False
                ))
                
                fig.update_layout(
                    paper_bgcolor="#0a0e1a",
                    plot_bgcolor="#0a0e1a",
                    font=dict(color="#94a3b8", family="Inter"),
                    height=300,
                    margin=dict(l=80, r=50, t=30, b=50)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error computing confusion matrix: {str(e)}")
    
    # Section C: Feature Correlation Matrix
    st.markdown("<div style='font-size:13px; font-weight:600; color:#f9fafb; margin:24px 0 12px'>Feature Correlation Matrix</div>", 
              unsafe_allow_html=True)
    
    if not df_train.empty:
        # Compute correlation matrix
        corr_matrix = df_train[FEATURE_NAMES].corr()
        
        # Get lower triangle mask
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
        corr_masked = corr_matrix.copy()
        corr_masked[mask] = np.nan
        
        fig = go.Figure(data=go.Heatmap(
            z=corr_masked.values,
            x=corr_matrix.columns,
            y=corr_matrix.index,
            colorscale="RdBu",
            zmid=0,
            zmin=-1,
            zmax=1,
            text=np.round(corr_masked.values, 2),
            texttemplate="%{text}",
            textfont=dict(size=8),
            hoverongaps=False
        ))
        
        fig.update_layout(
            paper_bgcolor="#0a0e1a",
            plot_bgcolor="#0a0e1a",
            font=dict(color="#94a3b8", family="Inter", size=8),
            height=600,
            margin=dict(l=100, r=50, t=30, b=100),
            xaxis=dict(tickangle=45)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Section D: Dataset Timeline
    st.markdown("<div style='font-size:13px; font-weight:600; color:#f9fafb; margin:24px 0 12px'>Dataset Timeline</div>", 
              unsafe_allow_html=True)
    
    if not df_train.empty:
        # Count samples per date
        timeline = df_train.groupby(["scan_date", "label"]).size().unstack(fill_value=0)
        timeline = timeline.reset_index()
        
        if 0 not in timeline.columns:
            timeline[0] = 0
        if 1 not in timeline.columns:
            timeline[1] = 0
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=timeline["scan_date"],
            y=timeline[1],
            name="Winners",
            marker_color="#4ade80"
        ))
        
        fig.add_trace(go.Bar(
            x=timeline["scan_date"],
            y=timeline[0],
            name="Losers",
            marker_color="#f87171"
        ))
        
        # Add reference line at y=20
        fig.add_hline(
            y=20,
            line_dash="dash",
            line_color="#fbbf24",
            annotation_text="Min recommended: 20",
            annotation_position="right"
        )
        
        fig.update_layout(
            paper_bgcolor="#0a0e1a",
            plot_bgcolor="#0a0e1a",
            font=dict(color="#94a3b8", family="Inter"),
            height=400,
            barmode="stack",
            margin=dict(l=50, r=50, t=50, b=50),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(title="Scan Date", gridcolor="#1f2937"),
            yaxis=dict(title="Samples", gridcolor="#1f2937")
        )
        
        st.plotly_chart(fig, use_container_width=True)


# ==============================================================================
# MAIN RENDER FUNCTION
# ==============================================================================

def render_ml_tab(results: list, market_key: str, min_score: float):
    """
    Main entry point for the ML Intelligence Tab.
    
    Args:
        results: Current scan results from st.session_state.results
        market_key: "US" or "IN"
        min_score: Minimum VCP score from sidebar
    """
    # Inject CSS
    st.markdown(ML_CARD_CSS, unsafe_allow_html=True)
    
    # Initialize session state keys
    training_data_key = f"ml_training_data_{market_key}"
    models_key = f"ml_models_{market_key}"
    
    if training_data_key not in st.session_state:
        st.session_state[training_data_key] = None
    if models_key not in st.session_state:
        st.session_state[models_key] = None
    
    # Get cached data
    df_train = st.session_state[training_data_key]
    models = st.session_state[models_key]
    
    # Status bar
    st.markdown("<div class='section-hdr'>ML Intelligence Status</div>", unsafe_allow_html=True)
    
    # Check cache dates
    cached_dates = list_cached_dates(market_key)
    cache_count = len(cached_dates)
    date_range_str = f"{min(cached_dates)} to {max(cached_dates)}" if cached_dates else "None"
    
    # Dataset status
    if df_train is not None and not df_train.empty:
        n_samples = len(df_train)
        if n_samples >= 100:
            dataset_status = f"<span class='ml-status-green'>{n_samples:,} samples across {df_train['scan_date'].nunique()} dates</span>"
        elif n_samples >= 50:
            dataset_status = f"<span class='ml-status-yellow'>{n_samples:,} samples across {df_train['scan_date'].nunique()} dates</span>"
        else:
            dataset_status = f"<span class='ml-status-red'>{n_samples} samples — Run Pre-load batch cache to build training data</span>"
    else:
        dataset_status = "<span class='ml-status-red'>No training data — Click 'Rebuild Training Dataset'</span>"
    
    # Model status
    if models and XGBOOST_AVAILABLE:
        model_status = f"<span class='ml-status-green'>Models trained ({len(models)} horizons)</span>"
    elif not XGBOOST_AVAILABLE:
        model_status = "<span class='ml-status-red'>XGBoost not installed — pip install xgboost</span>"
    else:
        model_status = "<span class='ml-status-red'>Not trained — Click 'Retrain XGBoost Models'</span>"
    
    # Cache status
    cache_status = f"<span class='ml-status-green'>Scan cache: {cache_count} dates ({date_range_str})</span>" if cache_count > 0 else "<span class='ml-status-red'>No scan cache available</span>"
    
    # Render status bar
    st.markdown(f"""
    <div style='display:flex; gap:32px; background:#111827; border:1px solid #1f2937; border-radius:8px; padding:12px 16px; margin-bottom:16px'>
        <div>
            <span style='font-size:11px; color:#6b7280; text-transform:uppercase'>Dataset</span><br>
            {dataset_status}
        </div>
        <div>
            <span style='font-size:11px; color:#6b7280; text-transform:uppercase'>Models</span><br>
            {model_status}
        </div>
        <div>
            <span style='font-size:11px; color:#6b7280; text-transform:uppercase'>Cache</span><br>
            {cache_status}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Rebuild Training Dataset", use_container_width=True):
            with st.spinner("Building training dataset... This may take a few minutes."):
                df_train = build_training_dataset(
                    market_key,
                    horizons=HORIZONS,
                    winner_threshold_pct=WINNER_THRESHOLDS,
                    stop_pct=STOP_PCT
                )
                st.session_state[training_data_key] = df_train
                if df_train is not None and not df_train.empty:
                    st.success(f"Built dataset with {len(df_train)} samples")
                else:
                    st.error("Failed to build training dataset. Check that scan cache exists.")
            st.rerun()
    
    with col2:
        if st.button("Retrain XGBoost Models", use_container_width=True):
            if df_train is None or df_train.empty:
                st.error("No training data available. Rebuild dataset first.")
            else:
                with st.spinner("Training XGBoost models..."):
                    models = train_vcp_models(df_train)
                    st.session_state[models_key] = models
                    if models:
                        st.success(f"Trained {len(models)} models")
                    else:
                        st.error("Model training failed. Check dataset has both winners and losers.")
                st.rerun()
    
    with col3:
        if df_train is not None and not df_train.empty:
            csv = df_train.to_csv(index=False)
            st.download_button(
                "Export Training Data CSV",
                csv,
                f"ml_training_data_{market_key}_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                use_container_width=True
            )
        else:
            st.button("Export Training Data CSV", disabled=True, use_container_width=True)
    
    st.markdown("<hr style='border-color:#1f2937; margin:16px 0'>", unsafe_allow_html=True)
    
    # Warning banner if insufficient data
    insufficient_data = (
        df_train is None or 
        df_train.empty or 
        len(df_train) < 50 or 
        not models or 
        not XGBOOST_AVAILABLE
    )
    
    if insufficient_data:
        st.markdown("""
        <div style='background:rgba(251, 191, 36, 0.1); border:1px solid rgba(251, 191, 36, 0.3); border-radius:8px; padding:12px 16px; margin-bottom:16px'>
            <span style='color:#fbbf24; font-weight:600'>⚠️ Setup Required</span>
            <p style='margin:8px 0 0; font-size:13px; color:#94a3b8'>
                The ML Intelligence system needs training data and models to make predictions. 
                Click "Rebuild Training Dataset" to collect historical data, then "Retrain XGBoost Models" 
                to train the prediction engines. This requires at least 50 historical samples across 
                multiple dates (use the "Pre-load 1 Month History" feature if needed).
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Sub-tabs
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
        "🏆 Winner DNA",
        "🔍 Pattern Matcher", 
        "📊 ML Ranked Picks",
        "🏥 Model Health"
    ])
    
    with sub_tab1:
        if df_train is not None and not df_train.empty:
            render_winner_dna_tab(df_train, models if models else {})
        else:
            st.info("Winner DNA analysis requires training data. Click 'Rebuild Training Dataset' above.")
    
    with sub_tab2:
        if not results:
            st.info("Pattern Matcher requires current scan results. Run a scan first.")
        elif df_train is not None and not df_train.empty:
            render_pattern_matcher_tab(results, df_train)
        else:
            st.info("Pattern Matcher requires training data. Click 'Rebuild Training Dataset' above.")
    
    with sub_tab3:
        if not results:
            st.info("ML Ranked Picks requires current scan results. Run a scan first.")
        else:
            render_ml_ranked_picks_tab(results, models if models else {}, df_train if df_train is not None else pd.DataFrame())
    
    with sub_tab4:
        if df_train is not None and not df_train.empty:
            render_model_health_tab(df_train, models if models else {})
        else:
            st.info("Model Health requires training data. Click 'Rebuild Training Dataset' above.")


# ==============================================================================
# USAGE EXAMPLE (for integration)
# ==============================================================================

# In your main Streamlit app:
#
# with tab_ml:  # or with st.tabs([...])[3] etc.
#     from ml_intelligence_tab import render_ml_tab
#     render_ml_tab(
#         results=st.session_state.get("results", []),
#         market_key=st.session_state.get("market_key", "US"),
#         min_score=st.session_state.get("min_score", 0)
#     )

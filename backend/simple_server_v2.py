"""Simple server with pre-loaded data."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import os
from datetime import datetime

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample scan data - 15 stocks each
SAMPLE_US_DATA = [
    {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "cap": "Mega Cap", "score": 95.2, "stage": 2, "checklist": 6, "rsi": 55.3, "vol_ratio": 1.2, "last_price": 178.45, "rs_1y": 115, "pct_off_high": 5.2, "pct_off_52w_high": 5.2, "atr": 2.5, "dist_20dma": 1.2, "dist_200dma": 8.5, "bb_width": 3.2, "rs_21": 108, "rs_63": 112, "volume": 85000000, "avg_volume": 75000000},
    {"ticker": "NVDA", "name": "NVIDIA Corp", "sector": "Technology", "cap": "Mega Cap", "score": 92.8, "stage": 2, "checklist": 5, "rsi": 62.1, "vol_ratio": 1.5, "last_price": 485.30, "rs_1y": 180, "pct_off_high": 3.1},
    {"ticker": "MSFT", "name": "Microsoft", "sector": "Technology", "cap": "Mega Cap", "score": 88.5, "stage": 3, "checklist": 5, "rsi": 58.7, "vol_ratio": 1.1, "last_price": 378.22, "rs_1y": 125, "pct_off_high": 7.8},
    {"ticker": "GOOGL", "name": "Alphabet", "sector": "Technology", "cap": "Mega Cap", "score": 85.3, "stage": 3, "checklist": 4, "rsi": 52.4, "vol_ratio": 1.0, "last_price": 142.65, "rs_1y": 95, "pct_off_high": 12.3},
    {"ticker": "AMZN", "name": "Amazon", "sector": "Consumer Discretionary", "cap": "Mega Cap", "score": 83.7, "stage": 2, "checklist": 5, "rsi": 60.2, "vol_ratio": 1.3, "last_price": 155.80, "rs_1y": 110, "pct_off_high": 8.5},
    {"ticker": "META", "name": "Meta Platforms", "sector": "Technology", "cap": "Mega Cap", "score": 87.9, "stage": 2, "checklist": 5, "rsi": 59.8, "vol_ratio": 1.4, "last_price": 312.45, "rs_1y": 145, "pct_off_high": 6.2},
    {"ticker": "TSLA", "name": "Tesla Inc", "sector": "Consumer Discretionary", "cap": "Large Cap", "score": 81.3, "stage": 2, "checklist": 4, "rsi": 65.2, "vol_ratio": 1.8, "last_price": 242.68, "rs_1y": 85, "pct_off_high": 15.3},
    {"ticker": "BRK.B", "name": "Berkshire Hathaway", "sector": "Financials", "cap": "Mega Cap", "score": 79.8, "stage": 3, "checklist": 4, "rsi": 51.5, "vol_ratio": 0.9, "last_price": 358.92, "rs_1y": 102, "pct_off_high": 9.7},
    {"ticker": "JPM", "name": "JPMorgan Chase", "sector": "Financials", "cap": "Mega Cap", "score": 77.4, "stage": 3, "checklist": 4, "rsi": 53.8, "vol_ratio": 1.0, "last_price": 148.65, "rs_1y": 98, "pct_off_high": 11.2},
    {"ticker": "V", "name": "Visa Inc", "sector": "Financials", "cap": "Mega Cap", "score": 82.1, "stage": 2, "checklist": 5, "rsi": 56.3, "vol_ratio": 1.1, "last_price": 258.33, "rs_1y": 108, "pct_off_high": 7.5},
    {"ticker": "UNH", "name": "UnitedHealth", "sector": "Healthcare", "cap": "Mega Cap", "score": 76.5, "stage": 3, "checklist": 4, "rsi": 49.8, "vol_ratio": 0.8, "last_price": 525.40, "rs_1y": 92, "pct_off_high": 13.8},
    {"ticker": "MA", "name": "Mastercard", "sector": "Financials", "cap": "Mega Cap", "score": 80.7, "stage": 2, "checklist": 5, "rsi": 57.2, "vol_ratio": 1.0, "last_price": 401.55, "rs_1y": 105, "pct_off_high": 8.9},
    {"ticker": "HD", "name": "Home Depot", "sector": "Consumer Discretionary", "cap": "Mega Cap", "score": 74.9, "stage": 3, "checklist": 3, "rsi": 50.5, "vol_ratio": 0.9, "last_price": 312.10, "rs_1y": 88, "pct_off_high": 14.2},
    {"ticker": "PG", "name": "Procter & Gamble", "sector": "Consumer Staples", "cap": "Mega Cap", "score": 71.2, "stage": 3, "checklist": 3, "rsi": 48.3, "vol_ratio": 0.7, "last_price": 152.78, "rs_1y": 85, "pct_off_high": 16.5},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare", "cap": "Mega Cap", "score": 69.8, "stage": 4, "checklist": 3, "rsi": 46.5, "vol_ratio": 0.6, "last_price": 158.92, "rs_1y": 78, "pct_off_high": 18.3},
]

SAMPLE_IN_DATA = [
    {"ticker": "RELIANCE", "name": "Reliance Industries", "sector": "Energy", "cap": "Mega Cap", "score": 91.2, "stage": 2, "checklist": 6, "rsi": 58.5, "vol_ratio": 1.2, "last_price": 2856.30, "rs_1y": 105, "pct_off_high": 4.2},
    {"ticker": "TCS", "name": "Tata Consultancy", "sector": "Technology", "cap": "Mega Cap", "score": 88.9, "stage": 3, "checklist": 5, "rsi": 54.3, "vol_ratio": 1.0, "last_price": 4125.60, "rs_1y": 98, "pct_off_high": 9.7},
    {"ticker": "INFY", "name": "Infosys", "sector": "Technology", "cap": "Large Cap", "score": 86.4, "stage": 2, "checklist": 5, "rsi": 56.8, "vol_ratio": 1.1, "last_price": 1658.40, "rs_1y": 88, "pct_off_high": 11.2},
    {"ticker": "HDFC", "name": "HDFC Bank", "sector": "Financials", "cap": "Mega Cap", "score": 84.7, "stage": 3, "checklist": 4, "rsi": 52.1, "vol_ratio": 0.9, "last_price": 1678.50, "rs_1y": 92, "pct_off_high": 13.5},
    {"ticker": "BAJFINANCE", "name": "Bajaj Finance", "sector": "Financials", "cap": "Large Cap", "score": 82.3, "stage": 2, "checklist": 5, "rsi": 61.2, "vol_ratio": 1.4, "last_price": 7256.80, "rs_1y": 118, "pct_off_high": 6.8},
    {"ticker": "HUL", "name": "Hindustan Unilever", "sector": "Consumer Staples", "cap": "Mega Cap", "score": 79.5, "stage": 3, "checklist": 4, "rsi": 49.8, "vol_ratio": 0.8, "last_price": 2586.30, "rs_1y": 85, "pct_off_high": 12.3},
    {"ticker": "ICICIBANK", "name": "ICICI Bank", "sector": "Financials", "cap": "Mega Cap", "score": 77.8, "stage": 3, "checklist": 4, "rsi": 53.2, "vol_ratio": 1.0, "last_price": 945.60, "rs_1y": 95, "pct_off_high": 10.7},
    {"ticker": "KOTAKBANK", "name": "Kotak Mahindra", "sector": "Financials", "cap": "Large Cap", "score": 75.6, "stage": 3, "checklist": 4, "rsi": 50.7, "vol_ratio": 0.9, "last_price": 1856.40, "rs_1y": 88, "pct_off_high": 14.2},
    {"ticker": "SBIN", "name": "SBI", "sector": "Financials", "cap": "Mega Cap", "score": 73.2, "stage": 4, "checklist": 3, "rsi": 47.5, "vol_ratio": 1.1, "last_price": 625.80, "rs_1y": 82, "pct_off_high": 17.8},
    {"ticker": "BHARTIARTL", "name": "Bharti Airtel", "sector": "Communication", "cap": "Mega Cap", "score": 80.4, "stage": 2, "checklist": 5, "rsi": 58.9, "vol_ratio": 1.3, "last_price": 945.20, "rs_1y": 108, "pct_off_high": 8.5},
    {"ticker": "ASIANPAINT", "name": "Asian Paints", "sector": "Materials", "cap": "Large Cap", "score": 71.8, "stage": 3, "checklist": 3, "rsi": 48.2, "vol_ratio": 0.7, "last_price": 3125.60, "rs_1y": 78, "pct_off_high": 15.6},
    {"ticker": "MARUTI", "name": "Maruti Suzuki", "sector": "Consumer Discretionary", "cap": "Large Cap", "score": 74.5, "stage": 3, "checklist": 4, "rsi": 52.6, "vol_ratio": 1.0, "last_price": 9856.30, "rs_1y": 92, "pct_off_high": 11.3},
    {"ticker": "AXISBANK", "name": "Axis Bank", "sector": "Financials", "cap": "Large Cap", "score": 72.9, "stage": 3, "checklist": 4, "rsi": 51.3, "vol_ratio": 1.0, "last_price": 1125.40, "rs_1y": 86, "pct_off_high": 13.7},
    {"ticker": "SUNPHARMA", "name": "Sun Pharma", "sector": "Healthcare", "cap": "Large Cap", "score": 70.3, "stage": 4, "checklist": 3, "rsi": 45.8, "vol_ratio": 0.8, "last_price": 1456.80, "rs_1y": 75, "pct_off_high": 19.2},
    {"ticker": "TITAN", "name": "Titan Company", "sector": "Consumer Discretionary", "cap": "Large Cap", "score": 76.1, "stage": 2, "checklist": 4, "rsi": 57.4, "vol_ratio": 1.2, "last_price": 3456.20, "rs_1y": 112, "pct_off_high": 9.8},
]

# Sample ML picks - Top 10 each
SAMPLE_ML_PICKS = {
    "US": [
        {"rank": 1, "ticker": "NVDA", "name": "NVIDIA Corp", "sector": "Technology", "cap": "Mega Cap", "last_price": 485.30, "score": 92.8, "ml_probability": 0.85, "avg_probability": 0.78, "horizon": 5, "top_features": [{"name": "rs_ratio", "importance": 0.25, "value": 180}, {"name": "volume_surge", "importance": 0.20, "value": 1}, {"name": "score", "importance": 0.18, "value": 92.8}], "stage": 2, "checklist": 5, "rsi": 62.1, "rs_1y": 180},
        {"rank": 2, "ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "cap": "Mega Cap", "last_price": 178.45, "score": 95.2, "ml_probability": 0.78, "avg_probability": 0.72, "horizon": 5, "top_features": [{"name": "score", "importance": 0.22, "value": 95.2}, {"name": "checklist", "importance": 0.19, "value": 6}, {"name": "tight", "importance": 0.17, "value": 1.1}], "stage": 2, "checklist": 6, "rsi": 55.3, "rs_1y": 115},
        {"rank": 3, "ticker": "META", "name": "Meta Platforms", "sector": "Technology", "cap": "Mega Cap", "last_price": 312.45, "score": 87.9, "ml_probability": 0.74, "avg_probability": 0.69, "horizon": 5, "top_features": [{"name": "rs_ratio", "importance": 0.23, "value": 145}, {"name": "vol_ratio", "importance": 0.19, "value": 1.4}, {"name": "stage", "importance": 0.17, "value": 2}], "stage": 2, "checklist": 5, "rsi": 59.8, "rs_1y": 145},
        {"rank": 4, "ticker": "MSFT", "name": "Microsoft", "sector": "Technology", "cap": "Mega Cap", "last_price": 378.22, "score": 88.5, "ml_probability": 0.72, "avg_probability": 0.68, "horizon": 5, "top_features": [{"name": "rs_ratio", "importance": 0.21, "value": 125}, {"name": "stage", "importance": 0.18, "value": 3}, {"name": "score_trend", "importance": 0.16, "value": 75.3}], "stage": 3, "checklist": 5, "rsi": 58.7, "rs_1y": 125},
        {"rank": 5, "ticker": "AMZN", "name": "Amazon", "sector": "Consumer Discretionary", "cap": "Mega Cap", "last_price": 155.80, "score": 83.7, "ml_probability": 0.68, "avg_probability": 0.65, "horizon": 5, "top_features": [{"name": "vol_ratio", "importance": 0.22, "value": 1.3}, {"name": "rsi", "importance": 0.18, "value": 60.2}, {"name": "checklist", "importance": 0.16, "value": 5}], "stage": 2, "checklist": 5, "rsi": 60.2, "rs_1y": 110},
        {"rank": 6, "ticker": "V", "name": "Visa Inc", "sector": "Financials", "cap": "Mega Cap", "last_price": 258.33, "score": 82.1, "ml_probability": 0.65, "avg_probability": 0.62, "horizon": 5, "top_features": [{"name": "score", "importance": 0.20, "value": 82.1}, {"name": "checklist", "importance": 0.18, "value": 5}, {"name": "stage", "importance": 0.16, "value": 2}], "stage": 2, "checklist": 5, "rsi": 56.3, "rs_1y": 108},
        {"rank": 7, "ticker": "GOOGL", "name": "Alphabet", "sector": "Technology", "cap": "Mega Cap", "last_price": 142.65, "score": 85.3, "ml_probability": 0.62, "avg_probability": 0.60, "horizon": 5, "top_features": [{"name": "score", "importance": 0.21, "value": 85.3}, {"name": "rs_ratio", "importance": 0.17, "value": 95}, {"name": "tight", "importance": 0.15, "value": 1.0}], "stage": 3, "checklist": 4, "rsi": 52.4, "rs_1y": 95},
        {"rank": 8, "ticker": "MA", "name": "Mastercard", "sector": "Financials", "cap": "Mega Cap", "last_price": 401.55, "score": 80.7, "ml_probability": 0.60, "avg_probability": 0.58, "horizon": 5, "top_features": [{"name": "score", "importance": 0.19, "value": 80.7}, {"name": "vol_ratio", "importance": 0.17, "value": 1.0}, {"name": "rsi", "importance": 0.16, "value": 57.2}], "stage": 2, "checklist": 5, "rsi": 57.2, "rs_1y": 105},
        {"rank": 9, "ticker": "UNH", "name": "UnitedHealth", "sector": "Healthcare", "cap": "Mega Cap", "last_price": 525.40, "score": 76.5, "ml_probability": 0.58, "avg_probability": 0.56, "horizon": 5, "top_features": [{"name": "stage", "importance": 0.20, "value": 3}, {"name": "score", "importance": 0.18, "value": 76.5}, {"name": "rsi", "importance": 0.15, "value": 49.8}], "stage": 3, "checklist": 4, "rsi": 49.8, "rs_1y": 92},
        {"rank": 10, "ticker": "JPM", "name": "JPMorgan Chase", "sector": "Financials", "cap": "Mega Cap", "last_price": 148.65, "score": 77.4, "ml_probability": 0.55, "avg_probability": 0.54, "horizon": 5, "top_features": [{"name": "score", "importance": 0.19, "value": 77.4}, {"name": "stage", "importance": 0.17, "value": 3}, {"name": "checklist", "importance": 0.15, "value": 4}], "stage": 3, "checklist": 4, "rsi": 53.8, "rs_1y": 98},
    ],
    "IN": [
        {"rank": 1, "ticker": "RELIANCE", "name": "Reliance Industries", "sector": "Energy", "cap": "Mega Cap", "last_price": 2856.30, "score": 91.2, "ml_probability": 0.82, "avg_probability": 0.75, "horizon": 5, "top_features": [{"name": "score", "importance": 0.24, "value": 91.2}, {"name": "rs_ratio", "importance": 0.20, "value": 105}, {"name": "checklist", "importance": 0.18, "value": 6}], "stage": 2, "checklist": 6, "rsi": 58.5, "rs_1y": 105},
        {"rank": 2, "ticker": "BAJFINANCE", "name": "Bajaj Finance", "sector": "Financials", "cap": "Large Cap", "last_price": 7256.80, "score": 82.3, "ml_probability": 0.76, "avg_probability": 0.70, "horizon": 5, "top_features": [{"name": "volume_surge", "importance": 0.23, "value": 1}, {"name": "rs_ratio", "importance": 0.19, "value": 118}, {"name": "vol_ratio", "importance": 0.17, "value": 1.4}], "stage": 2, "checklist": 5, "rsi": 61.2, "rs_1y": 118},
        {"rank": 3, "ticker": "TCS", "name": "Tata Consultancy", "sector": "Technology", "cap": "Mega Cap", "last_price": 4125.60, "score": 88.9, "ml_probability": 0.71, "avg_probability": 0.67, "horizon": 5, "top_features": [{"name": "score", "importance": 0.22, "value": 88.9}, {"name": "stage", "importance": 0.18, "value": 3}, {"name": "rsi", "importance": 0.16, "value": 54.3}], "stage": 3, "checklist": 5, "rsi": 54.3, "rs_1y": 98},
        {"rank": 4, "ticker": "INFY", "name": "Infosys", "sector": "Technology", "cap": "Large Cap", "last_price": 1658.40, "score": 86.4, "ml_probability": 0.68, "avg_probability": 0.64, "horizon": 5, "top_features": [{"name": "score", "importance": 0.21, "value": 86.4}, {"name": "checklist", "importance": 0.18, "value": 5}, {"name": "stage", "importance": 0.16, "value": 2}], "stage": 2, "checklist": 5, "rsi": 56.8, "rs_1y": 88},
        {"rank": 5, "ticker": "BHARTIARTL", "name": "Bharti Airtel", "sector": "Communication", "cap": "Mega Cap", "last_price": 945.20, "score": 80.4, "ml_probability": 0.65, "avg_probability": 0.62, "horizon": 5, "top_features": [{"name": "vol_ratio", "importance": 0.22, "value": 1.3}, {"name": "rs_ratio", "importance": 0.19, "value": 108}, {"name": "stage", "importance": 0.16, "value": 2}], "stage": 2, "checklist": 5, "rsi": 58.9, "rs_1y": 108},
        {"rank": 6, "ticker": "HDFC", "name": "HDFC Bank", "sector": "Financials", "cap": "Mega Cap", "last_price": 1678.50, "score": 84.7, "ml_probability": 0.63, "avg_probability": 0.60, "horizon": 5, "top_features": [{"name": "score", "importance": 0.20, "value": 84.7}, {"name": "stage", "importance": 0.17, "value": 3}, {"name": "checklist", "importance": 0.15, "value": 4}], "stage": 3, "checklist": 4, "rsi": 52.1, "rs_1y": 92},
        {"rank": 7, "ticker": "TITAN", "name": "Titan Company", "sector": "Consumer Discretionary", "cap": "Large Cap", "last_price": 3456.20, "score": 76.1, "ml_probability": 0.61, "avg_probability": 0.58, "horizon": 5, "top_features": [{"name": "rs_ratio", "importance": 0.21, "value": 112}, {"name": "vol_ratio", "importance": 0.18, "value": 1.2}, {"name": "checklist", "importance": 0.16, "value": 4}], "stage": 2, "checklist": 4, "rsi": 57.4, "rs_1y": 112},
        {"rank": 8, "ticker": "MARUTI", "name": "Maruti Suzuki", "sector": "Consumer Discretionary", "cap": "Large Cap", "last_price": 9856.30, "score": 74.5, "ml_probability": 0.59, "avg_probability": 0.56, "horizon": 5, "top_features": [{"name": "stage", "importance": 0.19, "value": 3}, {"name": "score", "importance": 0.17, "value": 74.5}, {"name": "rsi", "importance": 0.15, "value": 52.6}], "stage": 3, "checklist": 4, "rsi": 52.6, "rs_1y": 92},
        {"rank": 9, "ticker": "ICICIBANK", "name": "ICICI Bank", "sector": "Financials", "cap": "Mega Cap", "last_price": 945.60, "score": 77.8, "ml_probability": 0.57, "avg_probability": 0.55, "horizon": 5, "top_features": [{"name": "score", "importance": 0.19, "value": 77.8}, {"name": "vol_ratio", "importance": 0.17, "value": 1.0}, {"name": "stage", "importance": 0.15, "value": 3}], "stage": 3, "checklist": 4, "rsi": 53.2, "rs_1y": 95},
        {"rank": 10, "ticker": "HUL", "name": "Hindustan Unilever", "sector": "Consumer Staples", "cap": "Mega Cap", "last_price": 2586.30, "score": 79.5, "ml_probability": 0.55, "avg_probability": 0.53, "horizon": 5, "top_features": [{"name": "score", "importance": 0.20, "value": 79.5}, {"name": "stage", "importance": 0.17, "value": 3}, {"name": "rsi", "importance": 0.15, "value": 49.8}], "stage": 3, "checklist": 4, "rsi": 49.8, "rs_1y": 85},
    ]
}

@app.get("/api/status")
def get_status():
    return {"status": "ok"}

@app.get("/api/dates")
def get_dates(market: str = "US"):
    dates = ["2026-04-12", "2026-04-11", "2026-04-10"]
    return {"dates": dates}

@app.get("/api/scan")
def get_scan(market: str = "US", date: str = ""):
    data = SAMPLE_US_DATA if market == "US" else SAMPLE_IN_DATA
    return {"results": data}

@app.post("/api/ml/build-dataset")
def build_dataset():
    return {"success": True, "message": "Dataset built successfully", "total_samples": 50000, "unique_tickers": 100}

@app.post("/api/ml/train-models")
def train_models():
    return {"success": True, "message": "Models trained successfully", "models": [
        {"horizon": 2, "auc": 0.75, "auc_std": 0.02, "n_train": 15000, "n_winners": 9000, "n_losers": 6000},
        {"horizon": 5, "auc": 0.73, "auc_std": 0.02, "n_train": 18000, "n_winners": 10000, "n_losers": 8000},
        {"horizon": 10, "auc": 0.71, "auc_std": 0.03, "n_train": 22000, "n_winners": 11000, "n_losers": 11000}
    ]}

@app.post("/api/ml/top-picks/{market}")
def get_top_picks(market: str, request: dict):
    picks = SAMPLE_ML_PICKS.get(market, [])
    return {"success": True, "message": f"Top {len(picks)} picks generated", "picks": picks, "generated_at": datetime.now().isoformat()}

@app.get("/api/ml/status/{market}")
def ml_status(market: str):
    return {"market_key": market, "xgb_available": True, "shap_available": True, "has_training_data": True, "has_models": True}

@app.get("/api/ml/model-health/{market}")
def model_health(market: str):
    return {"status": "healthy", "models_loaded": True}

@app.post("/api/ml/predict")
def predict(request: dict):
    return {"predictions": [{"ticker": "AAPL", "probability": 0.75}]}

@app.get("/api/ohlcv/status")
def ohlcv_status():
    return {"status": "ok", "last_updated": datetime.now().isoformat()}

@app.get("/api/chart")
def get_chart(ticker: str):
    return {"dates": [], "prices": [], "volumes": []}

if __name__ == "__main__":
    print("Starting simple server on http://localhost:8002")
    uvicorn.run(app, host="0.0.0.0", port=8002)

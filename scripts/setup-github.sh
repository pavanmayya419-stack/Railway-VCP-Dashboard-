#!/bin/bash

echo "Setting up GitHub repository for VCP Dashboard..."

# Initialize git if not already done
if [ ! -d .git ]; then
    git init
    echo "Git repository initialized"
fi

# Add .gitignore if not exists
if [ ! -f .gitignore ]; then
    echo ".gitignore already exists"
fi

# Create data directories structure for cloud
mkdir -p data/scan_results
mkdir -p data/ohlcv
mkdir -p data/ml_models
mkdir -p logs

# Create .gitkeep files to preserve empty directories
touch data/scan_results/.gitkeep
touch data/ohlcv/.gitkeep
touch data/ml_models/.gitkeep
touch logs/.gitkeep

# Add initial files
git add .
git commit -m "Initial commit: VCP Dashboard

Features:
- Scanner with real-time data
- ML-powered Top 10 picks
- Chart analysis
- Portfolio tracking
- Backtesting simulation

Tech stack:
- FastAPI backend
- React TypeScript frontend
- PostgreSQL database
- Redis caching
- XGBoost ML models"

# Instructions for GitHub
echo ""
echo "=== GitHub Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Go to github.com and create a new repository"
echo "2. Run these commands:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/vcp-dashboard.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "3. For deployment, connect your repo to:"
echo "   - Railway.app (easiest)"
echo "   - Render.com (alternative)"
echo "   - AWS/Azure/GCP (production)"
echo ""
echo "Note: Large data files are excluded via .gitignore"
echo "They will be stored in the cloud, not in Git"

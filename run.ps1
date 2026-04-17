# VCP Dashboard - Auto Launcher
$ErrorActionPreference = "Stop"

Clear-Host
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   VCP DASHBOARD - AUTO LAUNCHER" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to check and kill processes
function Stop-Processes {
    Write-Host "[CLEANUP] Stopping existing processes..." -ForegroundColor Yellow
    Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# Function to setup Python environment
function Setup-Python {
    Write-Host "[PYTHON] Setting up Python environment..." -ForegroundColor Yellow
    Set-Location backend
    if (-not (Test-Path "venv\Scripts\python.exe")) {
        Write-Host "Creating virtual environment..." -ForegroundColor Gray
        python -m venv venv
        & venv\Scripts\pip.exe install -r requirements.txt
    }
}

# Function to start backend
function Start-Backend {
    Write-Host "[BACKEND] Starting server on port 8003..." -ForegroundColor Yellow
    $script = {
        Set-Location backend
        & venv\Scripts\python.exe main.py
    }
    Start-Job -Name "Backend" -ScriptBlock $script | Out-Null
    Start-Sleep -Seconds 5
}

# Function to setup Node.js
function Setup-Node {
    Write-Host "[NODE] Setting up Node.js environment..." -ForegroundColor Yellow
    Set-Location frontend
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing dependencies..." -ForegroundColor Gray
        npm install
    }
}

# Function to start frontend
function Start-Frontend {
    Write-Host "[FRONTEND] Starting development server..." -ForegroundColor Yellow
    $script = {
        Set-Location frontend
        npm run dev
    }
    Start-Job -Name "Frontend" -ScriptBlock $script | Out-Null
    Start-Sleep -Seconds 10
}

# Function to open browser
function Open-Browser {
    Write-Host "[BROWSER] Opening dashboard..." -ForegroundColor Yellow
    Start-Process "http://localhost:3001"
}

# Main execution
try {
    Stop-Processes
    Setup-Python
    Start-Backend
    Setup-Node
    Start-Frontend
    Open-Browser
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "   DASHBOARD IS READY!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "URL: http://localhost:3001" -ForegroundColor White
    Write-Host ""
    Write-Host "Press Ctrl+C to stop all servers" -ForegroundColor Gray
    
    # Keep running
    try {
        while ($true) { Start-Sleep -Seconds 1 }
    }
    finally {
        Write-Host ""
        Write-Host "[SHUTDOWN] Stopping all servers..." -ForegroundColor Red
        Stop-Job -Name "Backend" -Force -ErrorAction SilentlyContinue
        Stop-Job -Name "Frontend" -Force -ErrorAction SilentlyContinue
        Remove-Job -Name "Backend" -Force -ErrorAction SilentlyContinue
        Remove-Job -Name "Frontend" -Force -ErrorAction SilentlyContinue
        Stop-Processes
        Write-Host "Done!" -ForegroundColor Green
    }
}
catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
    Write-Host "Press any key to exit..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

@echo off
title VCP PRO Dashboard - Institutional Launcher
color 0B
cls

echo ============================================================
echo          VCP PRO DASHBOARD - INSTITUTIONAL LAUNCHER
echo ============================================================
echo.
echo [1] Launch Dashboard (Browser + Backend)
echo [2] Run FULL AUTO-SYNC (Maintenance + Data Refresh + ML)
echo [3] COMPLETE STARTUP (Full Auto-Sync + Launch)
echo [4] Maintenance Only (Cleanup logs/scans)
echo.
set /p choice="Enter choice (1-4, Default=3): " 
if "%choice%"=="" set choice=3

:: Kill existing processes to ensure clean start
echo [🧹] Cleaning up existing processes...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
timeout /t 2 /nobreak >nul

if "%choice%"=="1" goto launch
if "%choice%"=="2" goto sync
if "%choice%"=="3" goto full
if "%choice%"=="4" goto maint

:maint
echo.
echo [🛠️] Running System Maintenance...
cd /d "%~dp0backend"
venv\Scripts\python master_maintenance.py
pause
exit

:sync
echo.
echo [🔄] Running Full Auto-Sync...
cd /d "%~dp0backend"
venv\Scripts\python master_auto_sync.py
echo.
echo Sync Complete.
pause
exit

:full
echo.
echo [⚡] Starting COMPLETE Sync...
cd /d "%~dp0backend"
call venv\Scripts\python master_auto_sync.py
if errorlevel 1 (
    echo.
    echo ❌ ERROR: Sync failed. Please check the logs above.
    pause
    exit /b
)
echo ✅ Sync successful!
goto launch_steps

:launch
echo.
echo [🚀] Launching Dashboard...
:launch_steps
:: Start Backend
echo Starting Backend...
cd /d "%~dp0backend"
start "VCP_Backend" /min cmd /c "title VCP_Backend && venv\Scripts\python main.py || (echo Backend Failed to start && pause)"
timeout /t 5 /nobreak >nul

:: Start Frontend
echo Starting Frontend...
cd /d "%~dp0frontend"
start "VCP_Frontend" /min cmd /c "title VCP_Frontend && npm run dev || (echo Frontend Failed to start && pause)"

timeout /t 5 /nobreak >nul
echo.
echo ============================================================
echo ✅ Dashboard Ready at http://localhost:3001
echo ============================================================
start http://localhost:3001
echo Processes are running in the background.
echo Keep this window open or close it as you like.
timeout /t 10
exit

@echo off
title VCP Dashboard Launcher
cd /d "%~dp0"

echo Starting VCP Dashboard (US)...

:: Start backend if not running
netstat -ano | find ":8001 " >nul
if errorlevel 1 (
    echo Starting backend on 8001...
    start /min cmd /c "cd backend && venv\Scripts\python main.py"
    timeout /t 5 >nul
)

:: Start frontend if not running
netstat -ano | find ":3001 " >nul
if errorlevel 1 (
    echo Starting frontend on 3001...
    start /min cmd /c "cd frontend && npm run dev"
    timeout /t 10 >nul
)

:: Open browser at US URL
echo Opening US dashboard...
start http://localhost:3001

echo Dashboard is running!
echo URL: http://localhost:3001
echo.
echo This window will close in 5 seconds...
timeout /t 5 >nul

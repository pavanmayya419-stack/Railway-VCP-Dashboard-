@echo off
title VCP Dashboard - Offline Mode
color 0A
echo.
echo ========================================
echo   VCP Dashboard - Starting Offline
echo ========================================
echo.

:: Start Backend
echo [1/3] Starting Backend Server...
cd /d "%~dp0backend"
start "Backend Server" cmd /k "title Backend Server & .\venv\Scripts\python main.py"

:: Wait for backend to start
timeout /t 5 /nobreak >nul

:: Start Frontend
echo [2/3] Starting Frontend...
cd /d "%~dp0frontend"
start "Frontend Server" cmd /k "title Frontend Server & npm run dev"

:: Wait for frontend to start
timeout /t 10 /nobreak >nul

:: Open Browser
echo [3/3] Opening Dashboard...
start http://localhost:3001

echo.
echo ========================================
echo   Dashboard is running offline!
echo ========================================
echo.
echo Frontend: http://localhost:3001
echo Backend:  http://localhost:8001
echo.
echo Press any key to stop all servers...
pause >nul

:: Stop all servers
echo.
echo Stopping servers...
taskkill /f /im python.exe 2>nul
taskkill /f /im node.exe 2>nul
echo Done!
pause

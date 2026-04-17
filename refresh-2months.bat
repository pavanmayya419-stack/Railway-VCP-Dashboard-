@echo off
title Refreshing 2 Months of Data
color 0B

echo ========================================
echo  REFRESHING LAST 2 MONTHS OF DATA
echo ========================================
echo.

cd /d "d:\Production\pavan_mayya_vcp_fastapi_react\backend"

echo This will take 10-20 minutes...
echo Do not close this window!
echo.

:: Refresh last 2 months of data
echo [1/2] Refreshing US and India market data...
venv\Scripts\python refresh_2months_custom.py

echo.
echo ========================================
echo     REFRESH COMPLETE!
echo ========================================
echo.
echo All data for the last 2 months has been refreshed.
echo You can now check the dashboard.
echo.
pause

@echo off
echo Refreshing market data...
cd /d "d:\Production\pavan_mayya_vcp_fastapi_react\backend"
venv\Scripts\python refresh_data.py --market US --force
echo Done! Check dashboard for updated data.
pause

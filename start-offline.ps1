# VCP Dashboard - Offline Launcher
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VCP Dashboard - Starting Offline" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start Backend
Write-Host "[1/3] Starting Backend Server..." -ForegroundColor Yellow
$backend = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "cd backend; .\venv\Scripts\python main.py" -PassThru

# Wait for backend
Start-Sleep -Seconds 5

# Start Frontend
Write-Host "[2/3] Starting Frontend..." -ForegroundColor Yellow
$frontend = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev" -PassThru

# Wait for frontend
Start-Sleep -Seconds 10

# Open Browser
Write-Host "[3/3] Opening Dashboard..." -ForegroundColor Yellow
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Dashboard is running offline!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "Backend:  http://localhost:8000" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop all servers" -ForegroundColor Gray

# Wait for user to stop
try {
    while ($true) { Start-Sleep -Seconds 1 }
}
finally {
    Write-Host ""
    Write-Host "Stopping servers..." -ForegroundColor Red
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
    Write-Host "Done!" -ForegroundColor Green
}

# Start ViableOS in development mode
# Run from the ViableOS root directory

Write-Host "Starting ViableOS in dev mode..." -ForegroundColor Cyan

# Start FastAPI backend in background
$python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
$nodeDir = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.18.0-win-x64"
$env:Path = "$nodeDir;$env:LOCALAPPDATA\Programs\Python\Python312;$env:Path"

# Set JWT key for dev
$env:JWT_SECRET_KEY = "viableos-dev-insecure-change-me"
$env:USERS_JSON = (Get-Location).Path + "\users.dev.json"

Write-Host "Starting API on http://localhost:8000 ..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath $python -ArgumentList "-m uvicorn viableos.api.main:app --reload --host 0.0.0.0 --port 8000" -WorkingDirectory (Get-Location).Path

Start-Sleep -Seconds 2

Write-Host "Starting Frontend on http://localhost:5173 ..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath "npm" -ArgumentList "run dev" -WorkingDirectory (Join-Path (Get-Location).Path "frontend")

Write-Host ""
Write-Host "  API:      http://localhost:8000" -ForegroundColor Green
Write-Host "  Docs:     http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host "  Health:   http://localhost:8000/health" -ForegroundColor Green
Write-Host ""
Write-Host "Auth (dev):" -ForegroundColor Cyan
Write-Host "  POST /api/auth/login  { 'username': 'admin', 'password': 'admin123' }" -ForegroundColor Gray
Write-Host "  POST /api/auth/login  { 'username': 'user', 'password': 'admin123' }" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop both processes" -ForegroundColor Magenta

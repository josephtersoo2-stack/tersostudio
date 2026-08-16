# Tersuite AI Studio Local Services Startup Script
# Launches Django ASGI Backend, Celery Worker, and React Control Center

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "TERSUITE AI STUDIO — STARTING LOCAL SERVICES" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Check PostgreSQL (port 5432) & Redis (port 6379)
Write-Host "Verifying database and message broker connectivity..." -ForegroundColor Yellow
$pgCheck = Test-NetConnection -ComputerName 127.0.0.1 -Port 5432 -InformationLevel Quiet
$redisCheck = Test-NetConnection -ComputerName 127.0.0.1 -Port 6379 -InformationLevel Quiet

if (-not $pgCheck) {
    Write-Host "[WARNING] PostgreSQL is not reachable on port 5432." -ForegroundColor Red
} else {
    Write-Host "[OK] PostgreSQL is active on port 5432." -ForegroundColor Green
}

if (-not $redisCheck) {
    Write-Host "[WARNING] Redis is not reachable on port 6379." -ForegroundColor Red
} else {
    Write-Host "[OK] Redis is active on port 6379." -ForegroundColor Green
}

# 1. Start Django Backend in a separate window
Write-Host "Starting Django Backend on http://127.0.0.1:8000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$BackendDir'; .\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000"

# 2. Start Celery Worker in a separate window
Write-Host "Starting Celery Background Worker (solo pool)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$BackendDir'; .\.venv\Scripts\celery.exe -A config worker --loglevel=info -P solo"

# 3. Start React Control Center Frontend in a separate window
Write-Host "Starting React Control Center Frontend on http://localhost:5173..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$FrontendDir'; npm.cmd run dev"

Write-Host "==================================================" -ForegroundColor Green
Write-Host "ALL SERVICES LAUNCHED SUCCESSFULLY" -ForegroundColor Green
Write-Host "Backend API:      http://127.0.0.1:8000/api/v1/" -ForegroundColor White
Write-Host "API Health Live:  http://127.0.0.1:8000/api/v1/health/live/" -ForegroundColor White
Write-Host "Control Center:   http://localhost:5173/login" -ForegroundColor White
Write-Host "Staff Login:      admin@tersuite.com / AdminPassword123!" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Green

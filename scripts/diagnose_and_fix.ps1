# scripts/diagnose_and_fix.ps1
# Unified diagnostic and recovery script for Windows

Write-Host "🔍 Starting System Diagnosis..." -ForegroundColor Cyan

# 1. Check Redis
if (Get-Process "redis-server" -ErrorAction SilentlyContinue) {
    Write-Host "✅ Redis Server is running." -ForegroundColor Green
} else {
    Write-Host "⚠️ Redis Server is NOT running. Attempting to start..." -ForegroundColor Yellow
    if (Test-Path ".\scripts\setup-redis.ps1") {
        powershell -ExecutionPolicy Bypass -File .\scripts\setup-redis.ps1
    } else {
        Write-Host "❌ setup-redis.ps1 not found. Please install Redis manually." -ForegroundColor Red
    }
}

# 2. Check Environment
if (Test-Path ".env") {
    Write-Host "✅ .env file exists." -ForegroundColor Green
} else {
    Write-Host "❌ .env file MISSING! Creating from .env.example..." -ForegroundColor Red
    Copy-Item .env.example .env
}

# 3. Running Diagnostic Suite
Write-Host "📂 Running Python Diagnostics..." -ForegroundColor Cyan
$env:PYTHONPATH = ".;$env:PYTHONPATH"
python diagnostic/system_health_check.py

Write-Host "✨ Diagnosis Complete. If everything is green, run 'python main.py' to start the bot." -ForegroundColor Green

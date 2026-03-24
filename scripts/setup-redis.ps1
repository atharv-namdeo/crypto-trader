# scripts/setup-redis.ps1
# Helper script to install/start Redis on Windows

$redisUrl = "https://github.com/microsoftarchive/redis/releases/download/win-3.2.100/Redis-x64-3.2.100.zip"
$installPath = "$env:USERPROFILE\Redis"

if (-not (Test-Path $installPath)) {
    Write-Host "📥 Downloading Redis..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $installPath -Force | Out-Null
    Invoke-WebRequest -Uri $redisUrl -OutFile "$installPath\redis.zip"
    
    Write-Host "📦 Extracting Redis..." -ForegroundColor Cyan
    Expand-Archive -Path "$installPath\redis.zip" -DestinationPath $installPath -Force
    Remove-Item "$installPath\redis.zip"
}

Write-Host "🚀 Starting Redis Server on localhost:6379..." -ForegroundColor Green
Write-Host "Keep this window open or run 'redis-server' from $installPath" -ForegroundColor Yellow

Start-Process -FilePath "$installPath\redis-server.exe" -WorkingDirectory $installPath -WindowStyle Normal

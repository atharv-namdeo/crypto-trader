@echo off
TITLE ACE Trader - Sovereign Omega Engine
echo ======================================================
echo           ACE TRADER - SOVEREIGN OMEGA
echo ======================================================
echo.
echo [1/2] Starting Sovereign Core Engine (Python API)...
start cmd /k "python sovereign_local_live.py"

echo [2/2] Starting ACE Dashboard (React)...
cd dashboard
start cmd /k "npm run dev"

echo.
echo ======================================================
echo    SYSTEM ONLINE. Access Dashboard at http://localhost:5173
echo ======================================================
pause

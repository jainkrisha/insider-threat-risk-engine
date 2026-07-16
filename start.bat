@echo off
echo ============================================
echo  Vigil Risk Engine - Starting servers...
echo ============================================

echo [1/2] Starting FastAPI backend on port 8000...
start "Vigil Backend" cmd /k "cd /d %~dp0backend && uvicorn api:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak > nul

echo [2/2] Starting React frontend on port 5173...
start "Vigil Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 3 /nobreak > nul

echo.
echo ============================================
echo  Both servers are starting!
echo  Open http://localhost:5173 in your browser
echo ============================================
echo.
pause

@echo off
echo ================================================
echo   DerivInsight NL2SQL Frontend Launcher
echo ================================================
echo.

REM Check if the API server is already running
echo [1/3] Checking API server...
curl -s http://localhost:8080/health >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo     ✓ API server is running
) else (
    echo     ✗ API server is not running
    echo.
    echo Starting API server in a new window...
    start "NL2SQL API Server" cmd /k "cd /d %~dp0.. && python app\main.py"
    echo.
    echo Waiting for server to start...
    timeout /t 5 /nobreak >nul
)

echo.
echo [2/3] Opening frontend in browser...
start "" "http://localhost:8080"

echo.
echo [3/3] Done!
echo ================================================
echo.
echo Frontend URL: http://localhost:8080
echo API Endpoint: http://localhost:8080/api/v1
echo Health Check: http://localhost:8080/health
echo.
echo The frontend should now be open in your browser.
echo If not, manually navigate to: http://localhost:8080
echo.
echo Press any key to exit...
pause >nul

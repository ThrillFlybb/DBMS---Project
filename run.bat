@echo off
title DBMS Project - Flask + Cloudflared Tunnel
color 0A

echo ========================================
echo   DBMS Project - Flask + Cloudflared
echo ========================================
echo.

:: Change to script directory
cd /d "%~dp0"

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.9+ and try again
    echo.
    pause
    exit /b 1
)

:: Check if virtual environment exists, create if not
if not exist ".venv" (
    echo [1/4] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)

:: Activate virtual environment
echo [2/4] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

:: Install/update requirements
echo [3/4] Installing requirements...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [WARNING] Some packages may not have installed correctly
)

:: Set Flask port
set PORT=5000
set USE_WAITRESS=1

:: Start Flask app in new window
echo [4/4] Starting Flask app...
start "Flask App - Port 5000" cmd /k "python app.py"

:: Wait for Flask to start (2 seconds)
echo.
echo Waiting 2 seconds for Flask to start...
timeout /t 2 /nobreak >nul

:: Open browser to local app
start "" http://localhost:5000/

:: Start Cloudflared tunnel
echo.
echo ========================================
echo   Starting Cloudflared Tunnel...
echo ========================================
echo.
echo Flask app is running on: http://localhost:5000
echo.
echo Starting Cloudflared tunnel...
echo The public URL will be displayed below:
echo.

if exist "cloudflared.exe" (
    cloudflared.exe tunnel --url http://localhost:5000
) else (
    cloudflared tunnel --url http://localhost:5000
)

echo.
echo Cloudflared tunnel stopped.
echo Flask app may still be running in the other window.
echo.
pause

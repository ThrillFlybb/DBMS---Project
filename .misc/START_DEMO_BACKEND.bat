@echo off
echo ========================================
echo Starting Demo Backend Server
echo ========================================
echo.
echo This will start a demo backend server on port 5001
echo that demonstrates the REST API functionality.
echo.
echo To use it:
echo 1. Keep this window open
echo 2. Go to Settings in the main app
echo 3. Change Data Source to "REST"
echo 4. Set Backend URL to: http://localhost:5001
echo 5. Save settings
echo.
echo ========================================
echo.

python demo_backend.py

pause


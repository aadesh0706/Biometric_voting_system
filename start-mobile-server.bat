@echo off
echo ========================================
echo  Biometric Voting System - Mobile API
echo ========================================
echo.
echo Starting FastAPI server...
echo Server will be available at: http://0.0.0.0:8000
echo.
echo IMPORTANT: Update mobile/App.js with your local IP address
echo To find your IP: run 'ipconfig' and look for IPv4 Address
echo.
echo Press Ctrl+C to stop the server
echo.
echo ========================================

python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload

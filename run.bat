@echo off
REM DARKNEXT Quick Start Script for Windows

echo 🌐 DARKNEXT - Dark Web Content Monitor
echo ======================================

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Check if .env exists
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo ⚠️  Please edit .env file with your configuration before running!
)

REM Run component test
echo Testing components...
python src/main.py --mode test

echo.
echo 🚀 Setup complete! You can now run:
echo    python src/main.py --mode single      # Single scan
echo    python src/main.py --mode continuous  # Continuous monitoring
echo    python src/main.py --mode stats       # View statistics
echo.
echo ⚠️  Make sure Tor is running and .env is configured!

pause
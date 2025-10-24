@echo off
echo Starting BookBot...
echo.

REM Check if .env file exists
if not exist .env (
    echo Error: .env file not found!
    echo Please create .env file with your bot token and channel ID
    echo.
    echo Example .env content:
    echo BOT_TOKEN=your_bot_token_here
    echo CHANNEL_ID=@your_channel_username
    echo TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
    pause
    exit /b 1
)

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

REM Install requirements if needed
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing/updating requirements...
pip install -r requirements.txt

echo.
echo Starting BookBot...
echo Press Ctrl+C to stop the bot
echo.

python bookbot.py

pause

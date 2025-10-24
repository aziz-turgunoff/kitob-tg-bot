#!/bin/bash

echo "Starting BookBot..."
echo

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please create .env file with your bot token and channel ID"
    echo
    echo "Example .env content:"
    echo "BOT_TOKEN=your_bot_token_here"
    echo "CHANNEL_ID=@your_channel_username"
    echo "TESSERACT_PATH=/usr/bin/tesseract"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed"
    echo "Please install Python3"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing/updating requirements..."
pip install -r requirements.txt

echo
echo "Starting BookBot..."
echo "Press Ctrl+C to stop the bot"
echo

python3 bookbot.py

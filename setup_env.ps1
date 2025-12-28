# PowerShell script to set up development environment for BookBot
# Usage: Open PowerShell and run: .\setup_env.ps1

$ErrorActionPreference = 'Stop'

Write-Host "🔧 Creating virtual environment in '.venv'..." -ForegroundColor Cyan
if (-Not (Test-Path -Path ".venv")) {
    python -m venv .venv
} else {
    Write-Host "'.venv' already exists — skipping creation." -ForegroundColor Yellow
}

$python = Join-Path -Path (Resolve-Path .venv).Path -ChildPath "Scripts\python.exe"

Write-Host "📦 Upgrading pip and installing requirements..." -ForegroundColor Cyan
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt

# Create .env if it doesn't exist
if (-Not (Test-Path -Path ".env")) {
    Write-Host "📄 Copying env.example to .env..." -ForegroundColor Cyan
    Copy-Item -Path .\env.example -Destination .\.env
    Write-Host "⚠️  Please open '.env' and fill in BOT_TOKEN and CHANNEL_ID before running the bot." -ForegroundColor Yellow
} else {
    Write-Host "'.env' already exists — keep your existing values." -ForegroundColor Yellow
}

Write-Host "🗄️  Initializing the database (SQLite default)..." -ForegroundColor Cyan
& $python db_manager.py init

Write-Host "✅ Setup complete. To run the bot use: .\start_bot.ps1" -ForegroundColor Green
Write-Host "If you prefer, you can also run: .\.venv\Scripts\python.exe bookbot.py" -ForegroundColor Green

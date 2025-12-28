# PowerShell script to activate virtual environment and start BookBot
# Usage: Open PowerShell and run: .\start_bot.ps1

$venvPath = Join-Path -Path (Get-Location) -ChildPath ".venv\Scripts\python.exe"

if (-Not (Test-Path -Path $venvPath)) {
    Write-Host "❌ Virtual environment not found. Run .\setup_env.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "▶️ Starting BookBot using virtual environment..." -ForegroundColor Cyan
& $venvPath bookbot.py

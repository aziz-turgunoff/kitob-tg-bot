# Windows Development Setup (PowerShell)

Follow these steps to prepare a local environment to run the bot:

1. Open PowerShell in the project root.
2. Run the setup script:

   .\setup_env.ps1

   - This creates a `.venv` virtual environment, installs dependencies from `requirements.txt`, copies `env.example` -> `.env` (if `.env` doesn't exist) and runs `python db_manager.py init` to create the database (defaults to SQLite `bookbot.db`).

3. Edit `.env` and fill in at least these values:

   - `BOT_TOKEN` (from BotFather)
   - `CHANNEL_ID` (your channel username with @)

4. Start the bot:

   .\start_bot.ps1

   or

   .\.venv\Scripts\python.exe bookbot.py

Notes:
- If you want to use PostgreSQL, set `DATABASE_URL` in `.env` before running `setup_env.ps1`.
- On some systems, PowerShell execution policy may prevent running scripts; run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` as admin if needed.

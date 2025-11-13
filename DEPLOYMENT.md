# Deployment Guide - Database Setup

## Problem
After deployment, the database was lost because SQLite files are stored in the local filesystem, which is **ephemeral** on platforms like Railway. Each deployment or restart wipes the filesystem, causing data loss.

## Solution
The bot now supports both **SQLite** (for local development) and **PostgreSQL** (for production deployments). The database type is automatically detected from the `DATABASE_URL` environment variable.

## Railway Setup

### 1. Add PostgreSQL Database Service

1. In your Railway project dashboard, click **"+ New"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. Railway will automatically create a PostgreSQL database and provide a `DATABASE_URL` environment variable

### 2. Configure Environment Variables

Railway automatically sets the `DATABASE_URL` environment variable when you add a PostgreSQL service. The format is:
```
postgresql://user:password@host:port/database
```

**Important:** Make sure your bot service is connected to the PostgreSQL service:
- In Railway dashboard, go to your bot service
- Click on the **"Variables"** tab
- Verify that `DATABASE_URL` is available (it should be automatically linked)

### 3. Deploy

The bot will automatically:
- Detect PostgreSQL from `DATABASE_URL`
- Create the necessary tables on first run
- Use PostgreSQL for all database operations

## Local Development

For local development, you can continue using SQLite:

1. **Don't set** `DATABASE_URL` environment variable (or set it to `sqlite:///bookbot.db`)
2. The bot will automatically use SQLite with the local `bookbot.db` file

## Migration from SQLite to PostgreSQL

If you have existing data in SQLite that you want to migrate:

1. **Export from SQLite:**
   ```bash
   sqlite3 bookbot.db .dump > backup.sql
   ```

2. **Import to PostgreSQL:**
   - Connect to your Railway PostgreSQL database
   - Use `psql` or a database tool to import the data
   - Note: You may need to adjust the SQL syntax for PostgreSQL compatibility

## Verification

After deployment, verify the database is working:

1. Check the bot logs - you should see: `"Using PostgreSQL database"` or `"Using SQLite database"`
2. Use the `/status` command in Telegram to verify posts are being stored
3. Check Railway logs for any database connection errors

## Troubleshooting

### Database connection errors
- Verify `DATABASE_URL` is set correctly in Railway
- Check that the PostgreSQL service is running
- Ensure the bot service has network access to the database service

### Tables not created
- The bot automatically creates tables on first run
- Check logs for initialization messages
- You can manually run: `python db_manager.py init`

### Data still being lost
- Make sure you're using PostgreSQL (check logs for database type)
- Verify the `DATABASE_URL` points to PostgreSQL, not SQLite
- Check that the PostgreSQL service is persistent (not being recreated)


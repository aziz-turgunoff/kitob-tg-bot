import os
from pathlib import Path

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
ADMIN_IDS = os.getenv('ADMIN_IDS', '').split(',') if os.getenv('ADMIN_IDS') else []
ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS if admin_id.strip().isdigit()]

# Database Configuration
DATABASE_PATH = 'bookbot.db'

# Image Configuration
IMAGES_DIR = 'images'

# Reposting Configuration
REPOST_INTERVAL_DAYS = 7

# Validation
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID environment variable is required")

# Create directories
Path(IMAGES_DIR).mkdir(exist_ok=True)

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
ADMIN_IDS = os.getenv('ADMIN_IDS', '').split(',') if os.getenv('ADMIN_IDS') else []
ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS if admin_id.strip().isdigit()]

# Database Configuration
DATABASE_PATH = 'bookbot.db'

# Contact Configuration
CONTACT_USERNAME = os.getenv('CONTACT_USERNAME', '@Yollovchi')

# Image Configuration
IMAGES_DIR = 'images'


# Validation
if not BOT_TOKEN:
    print("❌ Error: BOT_TOKEN environment variable is required", file=sys.stderr)
    raise ValueError("BOT_TOKEN environment variable is required")
if not CHANNEL_ID:
    print("❌ Error: CHANNEL_ID environment variable is required", file=sys.stderr)
    raise ValueError("CHANNEL_ID environment variable is required")

# Create directories
Path(IMAGES_DIR).mkdir(exist_ok=True)

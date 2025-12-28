#!/usr/bin/env python3
"""Import channel messages into BookBot database using Telethon.

Requirements:
- TELETHON_API_ID and TELETHON_API_HASH in .env
- CHANNEL_ID (username or numeric id) in .env

This script imports messages with photos/captions into the local database storing channel_message_id and text_content.
"""

from dotenv import load_dotenv
import os
import sys
import json
import asyncio
import logging
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto
from database import db
from datetime import timezone

load_dotenv()
logging.basicConfig(level=logging.INFO)

API_ID_STR = os.getenv("TELETHON_API_ID")
API_HASH = os.getenv("TELETHON_API_HASH")
CHANNEL = os.getenv("CHANNEL_ID")  # e.g. @your_channel or numeric id

try:
    API_ID = int(API_ID_STR) if API_ID_STR is not None else None
except ValueError:
    logging.error("TELETHON_API_ID must be an integer. Set TELETHON_API_ID in .env")
    sys.exit(1)

try:
    LIMIT = int(os.getenv("IMPORT_LIMIT", "500"))
except (TypeError, ValueError):
    logging.warning("Invalid IMPORT_LIMIT value; using default 500")
    LIMIT = 500

if API_ID is None or not API_HASH or not CHANNEL:
    logging.error("Set TELETHON_API_ID, TELETHON_API_HASH and CHANNEL_ID in .env")
    sys.exit(1) 

async def run():
    async with TelegramClient('import_session', int(API_ID), API_HASH) as client:
        count = 0
        async for m in client.iter_messages(CHANNEL, limit=LIMIT):
            # We only import messages with media (photo) or a caption/text
            has_media = m.media is not None
            text = m.message or m.caption
            # Ensure we have at least an image and text (similar to how bot handles posts)
            if not has_media:
                continue
            if not text:
                continue

            # Skip if already imported (run DB call in thread to avoid blocking event loop)
            exists = await asyncio.to_thread(db.execute_fetchone, 'SELECT id FROM posts WHERE channel_message_id = ?', (m.id,))
            if exists:
                continue

            user_id = getattr(m.from_id, 'user_id', None) or 0
            created_at = m.date.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            channel_ids_json = json.dumps([m.id])

            # For file_ids we don't have bot file_ids, so leave empty list
            file_ids_json = json.dumps([])

            await asyncio.to_thread(db.execute, '''
                INSERT INTO posts (user_id, message_id, channel_message_id, channel_message_ids, text_content, file_ids, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, 0, m.id, channel_ids_json, text, file_ids_json, created_at))

            count += 1

        print(f"Imported {count} posts from {CHANNEL}")

if __name__ == '__main__':
    asyncio.run(run())

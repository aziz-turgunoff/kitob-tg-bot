import os
import logging
import sqlite3
import asyncio
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Optional
import re
import hashlib
from database import db
from config import BOT_TOKEN, CHANNEL_ID, ADMIN_IDS, CONTACT_USERNAME



def parse_db_datetime(dt_value):
    """Safely parse datetime from database (handles both string and datetime objects)"""
    if dt_value is None:
        return None
    if isinstance(dt_value, datetime):
        return dt_value
    if isinstance(dt_value, str):
        # Try ISO format first
        try:
            return datetime.fromisoformat(dt_value.replace(' ', 'T'))
        except ValueError:
            # Try SQLite format: YYYY-MM-DD HH:MM:SS
            try:
                return datetime.strptime(dt_value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                # Try just date
                try:
                    return datetime.strptime(dt_value, '%Y-%m-%d')
                except ValueError:
                    logger.warning(f"Could not parse datetime: {dt_value}")
                    return None
    return None

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError, RetryAfter

# Environment variables are loaded in config.py

# Async DB wrapper functions to avoid blocking the event loop
async def async_db_execute(query: str, params: tuple = None):
    """Execute non-blocking DB write operation"""
    return await asyncio.to_thread(db.execute, query, params)

async def async_db_fetchone(query: str, params: tuple = None):
    """Fetch one DB result non-blocking"""
    return await asyncio.to_thread(db.execute_fetchone, query, params)

async def async_db_fetchall(query: str, params: tuple = None):
    """Fetch all DB results non-blocking"""
    return await asyncio.to_thread(db.execute_fetchall, query, params)


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database setup
def init_database():
    """Initialize database (SQLite or PostgreSQL)"""
    db.init_database()

class BookBot:
    def __init__(self, bot_token: str, channel_id: str, admin_ids: List[int] = None):
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.admin_ids = admin_ids or []
        self.application = Application.builder().token(bot_token).build()
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup command and message handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("addadmin", self.add_admin_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_text = """
📚 **BookBot ga xush kelibsiz!**

Bu bot orqali siz kitob rasmlarini yuborib, ularni kanalga avtomatik tarzda joylashtirishingiz mumkin.

**Qanday ishlatish:**
1. Kitob rasmini yuboring
2. Rasm bilan birga matnni ham yuboring
3. Bot avtomatik ravishda kanalga joylashtiradi

**Matn formati:**
Har bir qator alohida bo'lishi kerak:
- Kitob nomi
- Muallif
- Betlar soni
- Holati
- Muqova
- Nashr yili
- Qo'shimcha ma'lumot
- Narx

/help - yordam olish uchun
        """
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📖 **Yordam**

**Buyruqlar:**
/start - Botni ishga tushirish
/help - Yordam olish
/addadmin - Admin qo'shish (faqat adminlar uchun)
/status - Botning statusini ko'rish

**Kitob yuborish:**
1. Kitob rasmini yuboring
2. Rasm bilan birga matnni ham yuboring
3. Bot avtomatik ravishda kanalga joylashtiradi

**Avtomatik qayta joylashtirish:**
- Agar kitob 1 hafta ichida qayta joylashtirilmagan bo'lsa, avtomatik ravishda qayta joylashtiriladi
- Eski post o'chiriladi va yangisi yuboriladi

**Matn formati:**
Har bir qator alohida bo'lishi kerak:
```
Kitob nomi
Muallif
Betlar soni
Holati
Muqova
Nashr yili
Qo'shimcha ma'lumot
Narx
```
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
        
    async def add_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addadmin command"""
        user_id = update.effective_user.id
        
        # Check if user is already admin or in admin list
        if user_id in self.admin_ids or self.is_admin(user_id):
            await update.message.reply_text("✅ Siz allaqachon admin ekansiz!")
            return
            
        # Add to admin list
        self.admin_ids.append(user_id)
        self.add_admin_to_db(user_id, update.effective_user.username)
        
        await update.message.reply_text("✅ Siz admin sifatida qo'shildingiz!")
        
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        if user_id in self.admin_ids:
            return True
            
        # Check database
        result = db.execute_fetchone('SELECT user_id FROM admins WHERE user_id = ?', (user_id,))
        return result is not None
        
    def add_admin_to_db(self, user_id: int, username: str = None):
        """Add admin to database"""
        db.execute('''
            INSERT OR REPLACE INTO admins (user_id, username) 
            VALUES (?, ?)
        ''', (user_id, username))
        
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            # Get database stats
            result = await async_db_fetchone('SELECT COUNT(*) FROM posts')
            total_posts = result[0] if result else 0
            
            status_text = f"""📊 **Bot Status**

📚 Total posts: {total_posts}
🤖 Bot is running normally
            """
            
            await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Status command error: {e}")
            await update.message.reply_text("❌ Error getting status.")
        
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages with text"""
        try:
            # Check if we're already processing a photo for this user
            if context.user_data.get('processing_photo'):
                return
                
            # Mark that we're processing a photo
            context.user_data['processing_photo'] = True
            
            # Get all photos from the message
            photos = update.message.photo
            if not photos:
                await update.message.reply_text("❌ No photos found.")
                return
            
            # Check if this is part of a media group
            media_group_id = update.message.media_group_id
            if media_group_id:
                # This is part of a media group - buffer it
                await self.buffer_media_group(update, context, media_group_id)
                return
            
            # Single photo processing (existing logic)
            await self.process_single_photo(update, context)
                
        except Exception as e:
            logger.error(f"Photo handling error: {e}")
            await update.message.reply_text("❌ Error processing photo. Please try again.")
        finally:
            # Clear processing flag
            context.user_data['processing_photo'] = False

    async def buffer_media_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE, media_group_id: str):
        """Buffer photos from media group and process after delay"""
        try:
            # Initialize bot_data if it doesn't exist
            if not hasattr(context, 'bot_data') or context.bot_data is None:
                context.bot_data = {}
            
            # Initialize media group buffer if not exists
            if 'media_groups' not in context.bot_data:
                context.bot_data['media_groups'] = {}
            
            # Add this photo to the group
            if media_group_id not in context.bot_data['media_groups']:
                context.bot_data['media_groups'][media_group_id] = {
                    'photos': [],
                    'caption': None,
                    'user_id': update.effective_user.id,
                    'timestamp': datetime.now(),
                    'processed': False,
                    'scheduled_job': None
                }
            
            group_data = context.bot_data['media_groups'][media_group_id]
            group_data['photos'].append(update.message)
            
            # Store caption from first message with caption
            if update.message.caption and not group_data['caption']:
                group_data['caption'] = update.message.caption
            
            # Note: We don't process media groups immediately because we need to wait
            # for all photos in the group to arrive before processing
            
            # Cancel existing job if it exists
            if group_data.get('scheduled_job'):
                try:
                    group_data['scheduled_job'].schedule_removal()
                except Exception as e:
                    logger.debug(f"Could not cancel scheduled job for media_group {media_group_id}: {e}")
            
            # Schedule new processing job after 1 second delay to ensure all photos are collected
            job = context.job_queue.run_once(
                self.process_media_group,
                when=1,
                data={'media_group_id': media_group_id}
            )
            group_data['scheduled_job'] = job
            
        except Exception as e:
            logger.error(f"Media group buffering error: {e}")
            await update.message.reply_text("❌ Error processing media group. Please try again.")

    async def process_media_group(self, context: ContextTypes.DEFAULT_TYPE):
        """Process complete media group after buffering"""
        try:
            job = context.job
            media_group_id = job.data['media_group_id']
            
            # Initialize bot_data if it doesn't exist
            if not hasattr(context, 'bot_data') or context.bot_data is None:
                context.bot_data = {}
            
            if 'media_groups' not in context.bot_data or media_group_id not in context.bot_data['media_groups']:
                return
            
            group_data = context.bot_data['media_groups'][media_group_id]
            
            # Check if already processed to prevent duplicate posting
            if group_data.get('processed', False):
                return
            photos = group_data['photos']
            caption = group_data['caption']
            user_id = group_data['user_id']
            
            if not photos:
                # Clean up buffer and return
                del context.bot_data['media_groups'][media_group_id]
                return
            
            # Get the first message for user interaction
            first_message = photos[0]
            
            # Store all photo file IDs (highest resolution from each)
            photo_file_ids = [photo.photo[-1].file_id for photo in photos]
            
            # Use the first photo for callback data
            file_id = photo_file_ids[0]
            
            # Create a shorter hash for callback data
            file_hash = hashlib.md5(file_id.encode()).hexdigest()[:8]
            
            # Store the mapping in database for persistence
            await async_db_execute(
                "INSERT INTO callback_mappings (callback_hash, file_id) VALUES (?, ?)",
                (file_hash, file_id)
            )
            
            # Store processed data before cleaning up
            processed_data = {
                'original_photo_messages': photos,
                'pending_file_ids': photo_file_ids,
                'pending_file_id': file_id,
                'user_id': user_id
            }
            
            if caption is not None:
                # Store text content for later use
                processed_data['pending_text_content'] = caption
                
                # Process the text
                lines = [line.strip() for line in caption.split('\n')]
                
                if len(lines) >= 8:
                    # Auto-post directly without confirmation
                    result = await self.post_book_content(
                        text_content=caption,
                        photos=photos,
                        photo_file_ids=photo_file_ids,
                        user_id=user_id,
                        message_id=first_message.message_id,
                        context=context,
                        is_media_group=True
                    )
                    
                    await first_message.reply_text(result)

                    # Clean up callback mapping
                    await async_db_execute("DELETE FROM callback_mappings WHERE callback_hash = ?", (file_hash,))
                    
                    # Mark as processed to prevent duplicate posting
                    group_data['processed'] = True
                    group_data['scheduled_job'] = None
                    
                    # Clean up media group data after successful posting
                    if 'media_groups' in context.bot_data and media_group_id in context.bot_data['media_groups']:
                        del context.bot_data['media_groups'][media_group_id]
                else:
                    await first_message.reply_text(
                        "❌ Kamida 8 qator matn kerak. Rasm bilan birga to'liq matnni yuboring va qaytadan urinib ko'ring."
                    )
                    # Mark as processed to prevent duplicate processing
                    group_data['processed'] = True
                    group_data['scheduled_job'] = None
            else:
                # No text provided, reject the submission
                await first_message.reply_text(
                    "❌ **Matn yuborilmadi!**\n\nRasm bilan birga matnni ham yuboring va qaytadan urinib ko'ring."
                )
                # Mark as processed to prevent duplicate processing
                group_data['processed'] = True
                group_data['scheduled_job'] = None
            
            # Store processed data in bot_data for later retrieval
            context.bot_data['media_groups'][media_group_id] = {
                'processed_data': processed_data,
                'timestamp': datetime.now()
            }
            
            # Schedule cleanup of processed data after 1 hour
            context.job_queue.run_once(
                self.cleanup_media_group_data,
                when=3600,  # 1 hour
                data={'media_group_id': media_group_id}
            )
                
        except Exception as e:
            logger.error(f"Media group processing error: {e}")

    async def cleanup_media_group_data(self, context: ContextTypes.DEFAULT_TYPE):
        """Clean up old media group data"""
        try:
            job = context.job
            media_group_id = job.data['media_group_id']
            
            if 'media_groups' in context.bot_data and media_group_id in context.bot_data['media_groups']:
                del context.bot_data['media_groups'][media_group_id]
                logger.info(f"Cleaned up media group data for {media_group_id}")
        except Exception as e:
            logger.error(f"Error cleaning up media group data: {e}")

    async def process_single_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process single photo (existing logic)"""
        try:
            # Get all photos from the message
            photos = update.message.photo
            if not photos:
                await update.message.reply_text("❌ No photos found.")
                return
                
            # Store only the highest resolution photo file ID
            photo_file_ids = [photos[-1].file_id]
            context.user_data['photo_file_ids'] = photo_file_ids
            
            # Use the first photo for callback data (they all have the same message)
            file_id = photo_file_ids[0]
            
            # Create a shorter hash for callback data
            file_hash = hashlib.md5(file_id.encode()).hexdigest()[:8]
            
            # Store the mapping in database for persistence
            await async_db_execute(
                "INSERT INTO callback_mappings (callback_hash, file_id) VALUES (?, ?)",
                (file_hash, file_id)
            )
            
            # Store original message and text content in user data
            context.user_data['original_photo_message'] = update.message
            context.user_data['pending_file_id'] = file_id
            
            # Check if there's text with the photo (caption)
            text_content = update.message.caption
            
            if text_content is not None:
                # Store text content for later use
                context.user_data['pending_text_content'] = text_content
                
                # Process the text
                lines = [line.strip() for line in text_content.split('\n')]
                
                if len(lines) >= 8:
                    # Auto-post directly without confirmation
                    photos = [update.message]
                    photo_file_ids = [update.message.photo[-1].file_id]
                    
                    result = await self.post_book_content(
                        text_content=text_content,
                        photos=photos,
                        photo_file_ids=photo_file_ids,
                        user_id=update.effective_user.id,
                        message_id=update.message.message_id,
                        context=context,
                        is_media_group=False
                    )
                    
                    await update.message.reply_text(result)

                    # Clean up callback mapping
                    await async_db_execute("DELETE FROM callback_mappings WHERE callback_hash = ?", (file_hash,))
                else:
                    await update.message.reply_text(
                        "❌ Kamida 8 qator matn kerak. Rasm bilan birga to'liq matnni yuboring va qaytadan urinib ko'ring."
                    )
            else:
                # No text provided, reject the submission
                await update.message.reply_text(
                    "❌ **Matn yuborilmadi!**\n\nRasm bilan birga matnni ham yuboring va qaytadan urinib ko'ring."
                )
                
        except Exception as e:
            logger.error(f"Single photo processing error: {e}")
            await update.message.reply_text("❌ Error processing photo. Please try again.")
            
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data

        # Validate callback payload format (expected: action_filehash)
        if not isinstance(data, str) or '_' not in data:
            await query.edit_message_text('❌ Invalid callback data.')
            return

        action, file_hash = data.split('_', 1)
        
        # Get the actual file_id from the database
        mapping = await async_db_fetchone("SELECT file_id FROM callback_mappings WHERE callback_hash = ?", (file_hash,))
        if not mapping:
            await query.edit_message_text("❌ Xatolik: Rasm topilmadi yoki muddati o'tgan.")
            return
        
        file_id = mapping[0]
        
        if action == "confirm":
            await self.confirm_and_post(query, file_id, context)
        # Edit action removed - no manual text entry
        elif action == "cancel":
            await query.edit_message_text("❌ Cancelled.")
            
        # Clear processing flag after any button action
        context.user_data['processing_photo'] = False
            
    async def post_book_content(self, text_content: str, photos: list, photo_file_ids: list, 
                               user_id: int, message_id: int, context: ContextTypes.DEFAULT_TYPE, 
                               is_media_group: bool = False):
        """Post book content to channel - extracted reusable method"""
        try:
            # Save to database first to get post_id
            post_id = self.save_post(
                user_id=user_id,
                message_id=message_id,
                channel_message_id=0,  # Will be updated after posting
                text_content=text_content,
                file_ids=photo_file_ids  # Store file_ids directly
            )
            
            # Post to channel with timeout
            try:
                channel_message = await asyncio.wait_for(
                    self.post_to_channel(text_content, photo_file_ids, post_id, context),
                    timeout=60.0  # 1 minute timeout for posting
                )
            except asyncio.TimeoutError:
                logger.error("Timeout posting to channel")
                return "❌ Kanalga joylashtirish vaqtida xatolik. Qaytadan urinib ko'ring."
            
            if channel_message:
                # Update channel_message_id in database
                # Handle both single message and list of messages (for media groups)
                if isinstance(channel_message, list):
                    # Media group: store all message IDs
                    message_ids = [msg.message_id for msg in channel_message]
                    self.update_channel_message_id(post_id, channel_message[0].message_id, message_ids)
                else:
                    # Single message
                    self.update_channel_message_id(post_id, channel_message.message_id, [channel_message.message_id])
                
                # Send success message
                photo_count = len(photos)
                if is_media_group and photo_count > 1:
                    success_msg = f"✅ Kitob muvaffaqiyatli kanalga joylashtirildi! ({photo_count} rasm)"
                else:
                    success_msg = "✅ Kitob muvaffaqiyatli kanalga joylashtirildi!"
                
                return success_msg
            else:
                return "❌ Kanalga joylashtirishda xatolik."
                
        except Exception as e:
            logger.error(f"Post book content error: {e}")
            return "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring."

    async def confirm_and_post(self, query, file_id: str, context: ContextTypes.DEFAULT_TYPE):
        """Confirm and post to channel"""
        try:
            # Get the original message to extract text
            original_message = query.message.reply_to_message
            
            # Check if this is from a media group first
            media_group_data = None
            for group_id, group_data in context.bot_data.get('media_groups', {}).items():
                if 'processed_data' in group_data and group_data['processed_data'].get('pending_file_id') == file_id:
                    media_group_data = group_data['processed_data']
                    break
            
            if media_group_data:
                # Media group - get text from processed data
                text_content = media_group_data.get('pending_text_content')
                if not text_content:
                    await query.edit_message_text("❌ Error: Could not find text content.")
                    return
                photos = media_group_data['original_photo_messages']
                photo_file_ids = media_group_data['pending_file_ids']
                is_media_group = True
            elif not original_message:
                # Try to get from user data if reply_to_message is not available
                text_content = context.user_data.get('pending_text_content')
                if not text_content:
                    await query.edit_message_text("❌ Error: Could not find original message.")
                    return
                stored_message = context.user_data.get('original_photo_message')
                if not stored_message:
                    await query.edit_message_text("❌ Error: Photos not found.")
                    return
                photos = [stored_message]
                photo_file_ids = [stored_message.photo[-1].file_id]
                is_media_group = False
            else:
                # Extract text from the message
                text_content = self.extract_text_from_message(original_message)
                
                if not text_content:
                    await query.edit_message_text("❌ Text not found.")
                    return
                photos = [original_message]
                photo_file_ids = [original_message.photo[-1].file_id]
                is_media_group = False
            
            # Use the extracted posting method
            result = await self.post_book_content(
                text_content=text_content,
                photos=photos,
                photo_file_ids=photo_file_ids,
                user_id=query.from_user.id,
                message_id=query.message.message_id,
                context=context,
                is_media_group=is_media_group
            )
            
            await query.edit_message_text(result)

            # Clean up callback mapping
            await async_db_execute("DELETE FROM callback_mappings WHERE callback_hash = ?", (file_hash,))
                
        except Exception as e:
            logger.error(f"Confirm and post error: {e}")
            await query.edit_message_text("❌ An error occurred.")
            
    # handle_sold_button function removed - Sotildi functionality removed
            
    # request_manual_input function removed - no manual text entry
        
    # handle_manual_text function removed - no manual text entry
        
    def extract_text_from_message(self, message) -> Optional[str]:
        """Extract text from message for posting"""
        if message.caption:
            return message.caption
        elif message.text:
            return message.text
        return None
    
    async def repost_with_copy_message(self, context: ContextTypes.DEFAULT_TYPE, from_chat_id: int, 
                                       message_id: int, text_content: str, max_retries: int = 3) -> Optional[int]:
        """Copy a message from channel to channel with exponential backoff for rate-limiting.
        Returns: new message object on success, None on failure"""
        backoff = 1  # Start with 1 second
        
        for attempt in range(max_retries):
            try:
                # Use Telegram's copy_message API - efficient and avoids re-upload
                copied_msg = await context.bot.copy_message(
                    chat_id=self.channel_id,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                    caption=None  # Don't duplicate caption; message already has its content
                )
                logger.info(f"Copied message {message_id} to channel, new id: {copied_msg.message_id}")
                return copied_msg  # Return the full message object, not just ID
            
            except RetryAfter as e:
                # Telegram rate-limited us; respect the server's backoff
                wait_time = e.retry_after
                logger.warning(f"RetryAfter from Telegram: waiting {wait_time} seconds (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
                continue
            
            except BadRequest as e:
                err_str = str(e).lower()
                if "not found" in err_str or "deleted" in err_str:
                    logger.error(f"Message {message_id} not found or deleted: {e}")
                    return None
                elif attempt < max_retries - 1:
                    logger.warning(f"BadRequest copying message {message_id} (attempt {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30)  # Cap at 30 seconds
                    continue
                else:
                    logger.error(f"Failed to copy message {message_id} after {max_retries} attempts: {e}")
                    return None
            
            except TelegramError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"TelegramError copying message {message_id} (attempt {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                    continue
                else:
                    logger.error(f"Failed to copy message {message_id} after {max_retries} attempts: {e}")
                    return None
            
            except Exception as e:
                logger.error(f"Unexpected error copying message {message_id}: {e}", exc_info=True)
                return None
        
        return None
        
    async def post_to_channel(self, text_content: str, file_ids: list, post_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Post book to channel with formatted text and multiple photos using file_ids"""
        try:
            lines = [line.strip() for line in text_content.split('\n')]
            
            if len(lines) < 8:
                return None
                
            # Format the post with premium layout
            formatted_text = (
                f"📚 **YANGI KITOB SOTUVDA** 📚\n"
                f"───────────────────\n"
                f"📖 **Nomi:** {lines[0]}\n"
                f"✍️ **Muallifi:** {lines[1]}\n"
                f"📄 **Sahifalar:** {lines[2]}\n"
                f"✨ **Holati:** {lines[3]}\n"
                f"🎨 **Muqovasi:** {lines[4]}\n"
                f"📅 **Yil:** {lines[5]}\n"
                f"ℹ️ **Tavsif:** {lines[6]}\n\n"
                f"👤 **Murojaat:** {CONTACT_USERNAME}\n"
                f"💰 **Narxi:** `{lines[7]}`\n\n"
                f"#kitob #sotuvda"
            )
            
            # Send multiple photos as media group
            if len(file_ids) > 1:
                # Send as media group for multiple photos using file_ids
                media_group = []

                for i, file_id in enumerate(file_ids):
                    if i == 0:
                        # First photo gets the caption
                        media_group.append(InputMediaPhoto(
                            media=file_id,
                            caption=formatted_text,
                            parse_mode=ParseMode.MARKDOWN
                        ))
                    else:
                        # Other photos without caption
                        media_group.append(InputMediaPhoto(
                            media=file_id
                        ))

                # Send media group with targeted exception handling
                try:
                    messages = await context.bot.send_media_group(
                        chat_id=self.channel_id,
                        media=media_group
                    )
                    return messages
                except BadRequest as e:
                    logger.error(f"send_media_group BadRequest: {e}", exc_info=True)
                    # Fallback: send first photo with caption, then remaining photos without caption
                    try:
                        first_msg = await context.bot.send_photo(
                            chat_id=self.channel_id,
                            photo=file_ids[0],
                            caption=formatted_text,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        if len(file_ids) > 1:
                            others = [InputMediaPhoto(media=fid) for fid in file_ids[1:]]
                            await context.bot.send_media_group(chat_id=self.channel_id, media=others)
                        return first_msg
                    except Exception as e2:
                        logger.error(f"Fallback failed for media group: {e2}", exc_info=True)
                        return None
                except TelegramError as e:
                    logger.error(f"send_media_group TelegramError: {e}", exc_info=True)
                    return None
                except Exception as e:
                    logger.error(f"Unexpected error in send_media_group: {e}", exc_info=True)
                    return None
            else:
                # Single photo using file_id
                try:
                    message = await context.bot.send_photo(
                        chat_id=self.channel_id,
                        photo=file_ids[0],
                        caption=formatted_text,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return message
                except BadRequest as e:
                    logger.error(f"send_photo BadRequest: {e}", exc_info=True)
                    return None
                except TelegramError as e:
                    logger.error(f"send_photo TelegramError: {e}", exc_info=True)
                    return None
                except Exception as e:
                    logger.error(f"Unexpected error in send_photo: {e}", exc_info=True)
                    return None
            
        except Exception as e:
            logger.error(f"Post to channel error: {e}")
            return None
            
    def update_channel_message_id(self, post_id: int, channel_message_id: int, all_message_ids: list = None):
        """Update channel message ID(s) in database"""
        # Store all message IDs as JSON for media groups
        if all_message_ids:
            message_ids_json = json.dumps(all_message_ids)
            db.execute('''
                UPDATE posts 
                SET channel_message_id = ?, channel_message_ids = ? 
                WHERE id = ?
            ''', (channel_message_id, message_ids_json, post_id))
        else:
            # Backward compatibility: if no list provided, just store single ID
            db.execute('UPDATE posts SET channel_message_id = ? WHERE id = ?', (channel_message_id, post_id))
            
    def save_post(self, user_id: int, message_id: int, channel_message_id: int, 
                  text_content: str, file_ids: list):
        """Save post to database"""
        # Convert file_ids list to JSON string for storage
        file_ids_json = json.dumps(file_ids)
        
        def execute_insert(cursor, conn):
            cursor.execute('''
                INSERT INTO posts (user_id, message_id, channel_message_id, text_content, file_ids)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, message_id, channel_message_id, text_content, file_ids_json))
            # Get the last inserted ID (works for both SQLite and PostgreSQL)
            if db.db_type == 'postgresql':
                cursor.execute('SELECT LASTVAL()')
                post_id = cursor.fetchone()[0]
            else:
                post_id = cursor.lastrowid
            return post_id
        
        return db.execute_with_cursor(execute_insert)
        
    async def repost_test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("ℹ️ Repost functionality has been removed.")

    async def repost_now_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("ℹ️ Repost functionality has been removed.")

    async def repost_now_by_date_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("ℹ️ Repost functionality has been removed.")

    def run(self):
        """Start the bot"""
        # Initialize database
        init_database()
        
        # Add error handler
        self.application.add_error_handler(self.error_handler)
        
        # Start the bot
        self.application.run_polling()
        
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error."""
        logger.error("Exception while handling an update:", exc_info=context.error)

def main():
    """Main function"""
    # Create and run bot
    bot = BookBot(BOT_TOKEN, CHANNEL_ID, ADMIN_IDS)
    bot.run()

if __name__ == '__main__':
    main()

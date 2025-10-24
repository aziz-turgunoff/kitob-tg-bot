import os
import logging
import sqlite3
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Optional
import re
import hashlib
from dotenv import load_dotenv

# Fix SQLite datetime deprecation warning for Python 3.12+
def adapt_datetime_iso(val):
    """Adapt datetime.datetime to ISO 8601 date."""
    return val.isoformat()

def convert_datetime(val):
    """Convert ISO 8601 datetime to datetime.datetime object."""
    return datetime.fromisoformat(val.decode())

# Register the adapter and converter
sqlite3.register_adapter(datetime, adapt_datetime_iso)
sqlite3.register_converter("datetime", convert_datetime)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

# Load environment variables from .env file
load_dotenv()

# Global file mapping for callback data
file_mappings = {}

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database setup
def init_database():
    """Initialize SQLite database for storing posts"""
    conn = sqlite3.connect('bookbot.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    # Enable proper datetime handling for Python 3.12+
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    
    # First, create the posts table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message_id INTEGER,
            channel_message_id INTEGER,
            text_content TEXT,
            image_path TEXT,
            file_ids TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            repost_count INTEGER DEFAULT 0,
            last_repost TIMESTAMP
        )
    ''')
    
    # Now check if file_ids column exists, if not add it
    cursor.execute("PRAGMA table_info(posts)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'file_ids' not in columns:
        # Add file_ids column for new file_id based storage
        cursor.execute('ALTER TABLE posts ADD COLUMN file_ids TEXT')
        logger.info("Added file_ids column to posts table")
    
    # Check if is_sold column exists, if it does remove it
    if 'is_sold' in columns:
        # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
        cursor.execute('''
            CREATE TABLE posts_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message_id INTEGER,
                channel_message_id INTEGER,
                text_content TEXT,
                image_path TEXT,
                file_ids TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                repost_count INTEGER DEFAULT 0,
                last_repost TIMESTAMP
            )
        ''')
        
        # Copy data from old table to new table (excluding is_sold column)
        cursor.execute('''
            INSERT INTO posts_new (id, user_id, message_id, channel_message_id, text_content, image_path, file_ids, created_at, repost_count, last_repost)
            SELECT id, user_id, message_id, channel_message_id, text_content, image_path, file_ids, created_at, repost_count, last_repost
            FROM posts
        ''')
        
        # Drop old table and rename new table
        cursor.execute('DROP TABLE posts')
        cursor.execute('ALTER TABLE posts_new RENAME TO posts')
        logger.info("Removed is_sold column from posts table")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

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
        # Manual text handler removed - no manual text entry
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
        conn = sqlite3.connect('bookbot.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM admins WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
        
    def add_admin_to_db(self, user_id: int, username: str = None):
        """Add admin to database"""
        conn = sqlite3.connect('bookbot.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO admins (user_id, username) 
            VALUES (?, ?)
        ''', (user_id, username))
        conn.commit()
        conn.close()
        
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            # Get database stats
            conn = sqlite3.connect('bookbot.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
            cursor = conn.cursor()
            
            # Total posts
            cursor.execute('SELECT COUNT(*) FROM posts')
            total_posts = cursor.fetchone()[0]
            
            # Total active posts
            active_posts = total_posts
            
            # Posts needing repost
            week_ago = datetime.now() - timedelta(days=7)
            cursor.execute('''
                SELECT COUNT(*) FROM posts 
                WHERE created_at <= ? 
                AND (last_repost IS NULL OR last_repost <= ?)
            ''', (week_ago, week_ago))
            repost_needed = cursor.fetchone()[0]
            
            conn.close()
            
            status_text = f"""📊 **Bot Status**

📚 Total posts: {total_posts}
🔄 Active posts: {active_posts}
⏰ Posts needing repost: {repost_needed}

🤖 Bot is running normally
📅 Repost job: Active (runs daily)
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
                except:
                    pass  # Job might already be removed
            
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
            
            # Store the mapping globally
            file_mappings[file_hash] = file_id
            
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
            
            # Store the mapping globally
            file_mappings[file_hash] = file_id
            
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
        
        # Sold button functionality removed
            
        action, file_hash = data.split('_', 1)
        
        # Get the actual file_id from the hash mapping
        file_id = file_mappings.get(file_hash)
        if not file_id:
            await query.edit_message_text("❌ Error: File not found.")
            return
        
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
                self.update_channel_message_id(post_id, channel_message.message_id)
                
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
        
    async def post_to_channel(self, text_content: str, file_ids: list, post_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Post book to channel with formatted text and multiple photos using file_ids"""
        try:
            lines = [line.strip() for line in text_content.split('\n')]
            
            if len(lines) < 8:
                return None
                
            # Format the post
            formatted_text = (
                f"*#kitob*\n"
                f"📜 *Nomi:* {lines[0]}\n"
                f"👥 *Muallifi:* {lines[1]}\n"
                f"📖 *Beti:* {lines[2]}\n"
                f"🕵‍♂ *Holati:* {lines[3]}\n"
                f"📚 *Muqovasi:* {lines[4]}\n"
                f"🗓 *Nashr etilgan yili:* {lines[5]}\n"
                f"📝 *Qo'shimcha ma'lumot:* {lines[6]}\n"
                f"🎭 *Murojaat uchun:* @Yollovchi\n"
                f"💰 *Narxi:* *{lines[7]} 000 soʻm*"
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
                
                # Send media group
                messages = await context.bot.send_media_group(
                    chat_id=self.channel_id,
                    media=media_group
                )
                
                return messages[0]  # Return first message for tracking
            else:
                # Single photo using file_id
                message = await context.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=file_ids[0],
                    caption=formatted_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                return message
                
        except Exception as e:
            logger.error(f"Post to channel error: {e}")
            return None
            
    # send_admin_sold_button function removed - Sotildi functionality removed
            
    def update_channel_message_id(self, post_id: int, channel_message_id: int):
        """Update channel message ID in database"""
        conn = sqlite3.connect('bookbot.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()
        cursor.execute('UPDATE posts SET channel_message_id = ? WHERE id = ?', (channel_message_id, post_id))
        conn.commit()
        conn.close()
            
    def save_post(self, user_id: int, message_id: int, channel_message_id: int, 
                  text_content: str, file_ids: list):
        """Save post to database"""
        conn = sqlite3.connect('bookbot.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()
        
        # Convert file_ids list to JSON string for storage
        file_ids_json = json.dumps(file_ids)
        
        cursor.execute('''
            INSERT INTO posts (user_id, message_id, channel_message_id, text_content, file_ids)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, message_id, channel_message_id, text_content, file_ids_json))
        
        post_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return post_id
        
    async def check_and_repost(self, context: ContextTypes.DEFAULT_TYPE):
        """Check for posts that need reposting (weekly)"""
        conn = sqlite3.connect('bookbot.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()
        
        # Get posts that are 7 days old and need reposting
        week_ago = datetime.now() - timedelta(days=7)
        cursor.execute('''
            SELECT id, channel_message_id, text_content, image_path, file_ids, repost_count
            FROM posts 
            WHERE created_at <= ? 
            AND (last_repost IS NULL OR last_repost <= ?)
        ''', (week_ago, week_ago))
        
        posts = cursor.fetchall()
        
        for post in posts:
            post_id, channel_message_id, text_content, image_path, file_ids_json, repost_count = post
            
            try:
                # Delete old message from channel
                if channel_message_id:
                    await context.bot.delete_message(chat_id=self.channel_id, message_id=channel_message_id)
                
                # Determine which data format to use (backward compatibility)
                if file_ids_json:
                    # New format: use file_ids
                    try:
                        file_ids = json.loads(file_ids_json)
                        new_message = await self.post_to_channel(text_content, file_ids, post_id, context)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.error(f"Error parsing file_ids for post {post_id}: {e}")
                        continue
                elif image_path:
                    # Old format: convert single image_path to list for compatibility
                    file_ids = [image_path]  # This won't work with new post_to_channel, but we'll handle it
                    logger.warning(f"Post {post_id} uses old image_path format, skipping repost")
                    continue
                else:
                    logger.error(f"No valid image data for post {post_id}")
                    continue
                
                if new_message:
                    # Update database
                    cursor.execute('''
                        UPDATE posts 
                        SET channel_message_id = ?, repost_count = ?, last_repost = ?
                        WHERE id = ?
                    ''', (new_message.message_id, repost_count + 1, datetime.now(), post_id))
                    
                    logger.info(f"Reposted book post {post_id}")
                    
            except Exception as e:
                logger.error(f"Repost error for post {post_id}: {e}")
        
        conn.commit()
        conn.close()
        
    async def repost_job(self, context: ContextTypes.DEFAULT_TYPE):
        """Job to run reposting check"""
        await self.check_and_repost(context)
        
    def run(self):
        """Start the bot"""
        # Initialize database
        init_database()
        
        # Add error handler
        self.application.add_error_handler(self.error_handler)
        
        # Schedule reposting job (run daily)
        job_queue = self.application.job_queue
        job_queue.run_repeating(self.repost_job, interval=timedelta(days=1), first=10)
        
        # Start the bot (initialize is called automatically by run_polling)
        self.application.run_polling()
        
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error and send a telegram message to notify the developer."""
        logger.error("Exception while handling an update:", exc_info=context.error)
        
        # Check if it's a conflict error (multiple bot instances)
        if "Conflict" in str(context.error):
            logger.error("Multiple bot instances detected. Please stop other instances.")
            return
            
        # For other errors, just log them
        logger.error(f"Update {update} caused error {context.error}")

def main():
    """Main function"""
    # Get configuration from environment variables
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    CHANNEL_ID = os.getenv('CHANNEL_ID')
    ADMIN_IDS = os.getenv('ADMIN_IDS', '').split(',') if os.getenv('ADMIN_IDS') else []
    ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS if admin_id.strip().isdigit()]
    
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ Please set BOT_TOKEN and CHANNEL_ID environment variables!")
        print("Example:")
        print("BOT_TOKEN=your_bot_token")
        print("CHANNEL_ID=@your_channel")
        print("ADMIN_IDS=123456789,987654321  # Optional")
        return
        
    # Create and run bot
    bot = BookBot(BOT_TOKEN, CHANNEL_ID, ADMIN_IDS)
    bot.run()

if __name__ == '__main__':
    main()

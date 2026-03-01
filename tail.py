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

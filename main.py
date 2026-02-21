"""AutoXMail v2 - Main bot entry point."""
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
import config
from database import db
from handlers import handlers
from oauth_handler import oauth_handler

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    """Initialize database after bot starts."""
    logger.info("Initializing database...")
    await db.init_db()
    logger.info("Database initialized")


async def error_handler(update: Update, context):
    """Handle errors."""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred. Please try again or contact support."
        )


def main():
    """Start the bot."""
    logger.info("Starting AutoXMail v2...")
    
    # Create application
    app = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help_command))
    
    # Callback query handlers
    app.add_handler(CallbackQueryHandler(handlers.start, pattern="^start$"))
    app.add_handler(CallbackQueryHandler(handlers.accounts, pattern="^accounts$"))
    app.add_handler(CallbackQueryHandler(handlers.inbox, pattern="^inbox$"))
    app.add_handler(CallbackQueryHandler(handlers.view_message, pattern="^view_msg:"))
    app.add_handler(CallbackQueryHandler(handlers.mark_read, pattern="^mark_read:"))
    app.add_handler(CallbackQueryHandler(handlers.mark_unread, pattern="^mark_unread:"))
    app.add_handler(CallbackQueryHandler(handlers.delete_message, pattern="^delete:"))
    app.add_handler(CallbackQueryHandler(handlers.confirm_delete, pattern="^confirm_delete:"))
    app.add_handler(CallbackQueryHandler(handlers.help_command, pattern="^help$"))
    
    # OAuth handlers
    app.add_handler(CallbackQueryHandler(oauth_handler.start_oauth, pattern="^add_account$"))
    app.add_handler(MessageHandler(
        filters.Document.ALL & ~filters.COMMAND,
        oauth_handler.handle_credentials
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        oauth_handler.handle_auth_code
    ))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Start bot
    logger.info("Bot started successfully!")
    logger.info(f"Admin chat: {config.ADMIN_CHAT_ID}")
    logger.info(f"Max accounts per user: {config.MAX_ACCOUNTS_PER_USER}")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

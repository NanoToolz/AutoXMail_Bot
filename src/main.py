"""AutoXMail Bot - Main entry point."""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters
)
import config
from database import db
from handlers import handlers
from oauth_handler import oauth_handler
from email_handlers import email_handlers, SELECT_FROM, ENTER_TO, ENTER_SUBJECT, ENTER_BODY, CONFIRM
from search_handler import search_handler, SELECT_ACCOUNT, ENTER_QUERY

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    """Initialize database and set bot commands after bot starts."""
    logger.info("Initializing database...")
    await db.init_db()
    logger.info("Database initialized")
    
    # Set bot commands
    logger.info("Setting bot commands...")
    from telegram import BotCommand
    commands = [
        BotCommand("start", "🏠 Main menu"),
        BotCommand("help", "ℹ️ Help and information"),
        BotCommand("accounts", "📧 Manage Gmail accounts"),
        BotCommand("inbox", "📬 View inbox"),
        BotCommand("search", "🔍 Search emails"),
        BotCommand("settings", "⚙️ Bot settings"),
    ]
    await application.bot.set_my_commands(commands)
    
    # Set bot description
    await application.bot.set_my_short_description(
        "Secure multi-account Gmail client for Telegram with end-to-end encryption"
    )
    
    await application.bot.set_my_description(
        "AutoXMail is a powerful Gmail client for Telegram that lets you manage "
        "multiple Gmail accounts securely. Features include:\n\n"
        "• Multi-account support with end-to-end encryption\n"
        "• Browse, search, and manage emails\n"
        "• Real-time push notifications\n"
        "• Label management and organization\n"
        "• Spam and trash management\n"
        "• Rate limiting and security features\n\n"
        "Get started with /start"
    )
    
    logger.info("Bot commands and description set")


async def error_handler(update: Update, context):
    """Handle errors."""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred. Please try again or contact support."
        )


def main():
    """Start the bot."""
    logger.info("Starting AutoXMail Bot...")
    
    # Create application
    app = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help_command))
    
    # Compose email conversation handler
    compose_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(email_handlers.start_compose, pattern="^compose$")],
        states={
            SELECT_FROM: [CallbackQueryHandler(email_handlers.select_from_account, pattern="^compose_from:")],
            ENTER_TO: [MessageHandler(filters.TEXT & ~filters.COMMAND, email_handlers.receive_to_email)],
            ENTER_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, email_handlers.receive_subject)],
            ENTER_BODY: [MessageHandler(filters.TEXT & ~filters.COMMAND, email_handlers.receive_body)],
            CONFIRM: [
                CallbackQueryHandler(email_handlers.send_email, pattern="^compose_send$"),
                CallbackQueryHandler(email_handlers.edit_compose, pattern="^compose_edit$")
            ]
        },
        fallbacks=[CallbackQueryHandler(email_handlers.cancel_compose, pattern="^cancel_compose$")],
        allow_reentry=True
    )
    app.add_handler(compose_handler)
    
    # Search conversation handler
    search_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(search_handler.start_search, pattern="^search$")],
        states={
            SELECT_ACCOUNT: [CallbackQueryHandler(search_handler.select_search_account, pattern="^search_account:")],
            ENTER_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler.perform_search)]
        },
        fallbacks=[CallbackQueryHandler(search_handler.cancel_search, pattern="^cancel_search$")],
        allow_reentry=True
    )
    app.add_handler(search_conv_handler)
    
    # Email interaction handlers
    app.add_handler(CallbackQueryHandler(email_handlers.start_reply, pattern="^email:reply:"))
    app.add_handler(CallbackQueryHandler(email_handlers.start_forward, pattern="^email:forward:"))
    app.add_handler(CallbackQueryHandler(email_handlers.view_full_email, pattern="^email:full:"))
    
    # Reply/Forward message handlers (must be before unknown handler)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        email_handlers.send_reply
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        email_handlers.send_forward
    ))
    
    # Callback query handlers
    app.add_handler(CallbackQueryHandler(handlers.verify_join, pattern="^verify_join$"))
    app.add_handler(CallbackQueryHandler(handlers.start, pattern="^start$"))
    app.add_handler(CallbackQueryHandler(handlers.accounts, pattern="^accounts$"))
    app.add_handler(CallbackQueryHandler(handlers.inbox, pattern="^inbox$"))
    app.add_handler(CallbackQueryHandler(handlers.view_message, pattern="^view_msg:"))
    app.add_handler(CallbackQueryHandler(handlers.mark_read, pattern="^mark_read:"))
    app.add_handler(CallbackQueryHandler(handlers.mark_unread, pattern="^mark_unread:"))
    app.add_handler(CallbackQueryHandler(handlers.delete_message, pattern="^delete:"))
    app.add_handler(CallbackQueryHandler(handlers.confirm_delete, pattern="^confirm_delete:"))
    app.add_handler(CallbackQueryHandler(handlers.help_command, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(handlers.settings, pattern="^settings$"))
    app.add_handler(CallbackQueryHandler(handlers.toggle_notifications, pattern="^toggle_notifications$"))
    app.add_handler(CallbackQueryHandler(handlers.toggle_spam_filter, pattern="^toggle_spam_filter$"))
    app.add_handler(CallbackQueryHandler(handlers.toggle_promo_filter, pattern="^toggle_promo_filter$"))
    
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
    
    # Unknown input handler (MUST BE LAST)
    app.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND,
        handlers.unknown_handler
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

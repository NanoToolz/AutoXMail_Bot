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
from admin_handler import admin_handler
from labels_handler import labels_handler
from folders_handler import folders_handler
from advanced_handlers import advanced_handlers
from push_service import PushService

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(config.LOGS_DIR / 'bot.log'),
        logging.StreamHandler()
    ]
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
    
    # Notify admin on startup
    try:
        from datetime import datetime
        from formatter import to_tiny_caps, escape_markdown
        startup_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await application.bot.send_message(
            chat_id=config.ADMIN_CHAT_ID,
            text=(
                f"✅ *{to_tiny_caps('Bot Started Successfully')}*\n"
                f"`────────────────────────`\n\n"
                f"🕐 {to_tiny_caps('Time')}: `{startup_time}`\n"
                f"🤖 {to_tiny_caps('Status')}: {to_tiny_caps('Running')}\n"
                f"📊 {to_tiny_caps('Ready to serve users')}"
            ),
            parse_mode='MarkdownV2'
        )
        logger.info("Startup notification sent to admin")
    except Exception as e:
        logger.error(f"Failed to send startup notification: {e}")
    
    # Start webhook server if configured
    if config.WEBHOOK_URL:
        logger.info("Starting webhook server...")
        push_service = PushService(application.bot)
        asyncio.create_task(push_service.start_server())
        logger.info("Webhook server started")
    
    # Start push renewal background task
    asyncio.create_task(renew_push_subscriptions())
    logger.info("Push renewal task started")


async def renew_push_subscriptions():
    """Background task to renew push subscriptions every 6 days."""
    while True:
        try:
            # Wait 6 days
            await asyncio.sleep(6 * 24 * 3600)
            
            logger.info("Renewing push subscriptions...")
            
            # Get all active accounts
            async with db.db_path as conn:
                conn.row_factory = db.aiosqlite.Row
                cursor = await conn.execute(
                    "SELECT id, email, user_id FROM gmail_accounts WHERE is_active = 1"
                )
                accounts = await cursor.fetchall()
            
            # Renew each account
            for account in accounts:
                try:
                    account_id = account['id']
                    email = account['email']
                    
                    # Setup push notification
                    if config.WEBHOOK_URL:
                        topic_name = f"projects/{config.GCP_PROJECT_ID}/topics/gmail-push"
                        result = await gmail_service.setup_push(account_id, topic_name)
                        
                        # Update history ID
                        async with db.db_path as conn:
                            await conn.execute(
                                "UPDATE gmail_accounts SET last_history_id = ? WHERE id = ?",
                                (result['historyId'], account_id)
                            )
                            await conn.commit()
                        
                        logger.info(f"Push renewed for {email}")
                    
                except Exception as e:
                    logger.error(f"Push renewal failed for {account.get('email', 'unknown')}: {e}")
                    continue
            
            logger.info("Push renewal completed")
            
        except Exception as e:
            logger.error(f"Push renewal task error: {e}")
            # Continue running even if error occurs
            await asyncio.sleep(3600)  # Wait 1 hour before retry


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
    
    # Admin commands
    app.add_handler(CommandHandler("logs", admin_handler.logs_command))
    app.add_handler(CommandHandler("health", admin_handler.health_command))
    app.add_handler(CommandHandler("restart", admin_handler.restart_command))
    app.add_handler(CommandHandler("broadcast", admin_handler.broadcast_command))
    app.add_handler(CommandHandler("stats", admin_handler.stats_command))
    app.add_handler(CallbackQueryHandler(admin_handler.restart_command, pattern="^admin_restart$"))
    
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
    
    # Labels handlers
    app.add_handler(CallbackQueryHandler(labels_handler.show_labels, pattern="^labels$"))
    app.add_handler(CallbackQueryHandler(labels_handler.select_labels_account, pattern="^labels_account:"))
    app.add_handler(CallbackQueryHandler(labels_handler.view_label_emails, pattern="^label_view:"))
    app.add_handler(CallbackQueryHandler(labels_handler.confirm_delete_label, pattern="^label_delete:"))
    app.add_handler(CallbackQueryHandler(labels_handler.delete_label, pattern="^label_delete_confirm:"))
    app.add_handler(CallbackQueryHandler(labels_handler.start_create_label, pattern="^label_create$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, labels_handler.create_label))
    
    # Folders handlers
    app.add_handler(CallbackQueryHandler(folders_handler.show_folders, pattern="^folders$"))
    app.add_handler(CallbackQueryHandler(folders_handler.select_folders_account, pattern="^folders_account:"))
    app.add_handler(CallbackQueryHandler(folders_handler.view_folder_emails, pattern="^folder_view:"))
    
    # Advanced handlers (blocklist, VIP, privacy, bot settings)
    app.add_handler(CallbackQueryHandler(advanced_handlers.show_blocklist, pattern="^blocklist$"))
    app.add_handler(CallbackQueryHandler(advanced_handlers.start_add_blocklist, pattern="^blocklist_add$"))
    app.add_handler(CallbackQueryHandler(advanced_handlers.remove_from_blocklist, pattern="^blocklist_remove:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, advanced_handlers.add_to_blocklist_handler))
    
    app.add_handler(CallbackQueryHandler(advanced_handlers.show_vip_senders, pattern="^vip_senders$"))
    app.add_handler(CallbackQueryHandler(advanced_handlers.start_add_vip, pattern="^vip_add$"))
    app.add_handler(CallbackQueryHandler(advanced_handlers.remove_vip_sender, pattern="^vip_remove:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, advanced_handlers.add_vip_sender_handler))
    
    app.add_handler(CallbackQueryHandler(advanced_handlers.show_privacy_settings, pattern="^privacy_settings$"))
    app.add_handler(CallbackQueryHandler(advanced_handlers.set_privacy_timer, pattern="^privacy_timer:"))
    
    app.add_handler(CallbackQueryHandler(advanced_handlers.show_bot_settings, pattern="^bot_settings$"))
    app.add_handler(CallbackQueryHandler(advanced_handlers.start_change_photo, pattern="^bot_change_photo$"))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, advanced_handlers.change_bot_photo))
    
    app.add_handler(CallbackQueryHandler(advanced_handlers.show_account_auto_delete, pattern="^account_autodelete:"))
    app.add_handler(CallbackQueryHandler(advanced_handlers.set_account_auto_delete, pattern="^account_timer:"))
    
    app.add_handler(CallbackQueryHandler(advanced_handlers.confirm_unsubscribe, pattern="^email:unsub:"))
    app.add_handler(CallbackQueryHandler(advanced_handlers.execute_unsubscribe, pattern="^email:unsub_confirm:"))
    
    # Inbox time range handlers
    app.add_handler(CallbackQueryHandler(handlers.inbox_with_time, pattern="^inbox_time:"))
    
    # OAuth force add handler
    app.add_handler(CallbackQueryHandler(oauth_handler.force_add_account, pattern="^oauth_force_add:"))
    
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

"""Admin commands handler."""
import os
import sys
import psutil
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from formatter import to_tiny_caps, escape_markdown
import config

# Bot start time
START_TIME = datetime.now()


class AdminHandler:
    """Handler for admin-only commands."""
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return str(user_id) == config.ADMIN_CHAT_ID
    
    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show last 50 lines of bot logs."""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ Unauthorized. Admin only.")
            return
        
        try:
            log_file = config.LOGS_DIR / 'bot.log'
            
            if not log_file.exists():
                await update.message.reply_text(
                    f"📋 *{to_tiny_caps('Logs')}*\n"
                    f"`────────────────────────`\n\n"
                    f"No log file found\\.",
                    parse_mode='MarkdownV2'
                )
                return
            
            # Read last 50 lines
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                last_lines = lines[-50:] if len(lines) > 50 else lines
            
            log_text = ''.join(last_lines)
            
            # Truncate if too long
            if len(log_text) > 3800:
                log_text = log_text[-3800:]
                log_text = "...\n" + log_text
            
            await update.message.reply_text(
                f"📋 *{to_tiny_caps('Bot Logs')}* \\(Last 50 lines\\)\n"
                f"`────────────────────────`\n\n"
                f"```\n{escape_markdown(log_text)}```",
                parse_mode='MarkdownV2'
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error reading logs: {str(e)}")
    
    async def health_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot health status."""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ Unauthorized. Admin only.")
            return
        
        try:
            # Get system info
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            ram_usage_mb = memory_info.rss / 1024 / 1024
            
            # Get DB size
            db_size = 0
            if config.DB_PATH.exists():
                db_size = config.DB_PATH.stat().st_size / 1024 / 1024  # MB
            
            # Get user counts
            async with db.db_path as conn:
                conn.row_factory = None
                cursor = await conn.execute("SELECT COUNT(*) FROM users")
                total_users = (await cursor.fetchone())[0]
                
                cursor = await conn.execute("SELECT COUNT(*) FROM gmail_accounts WHERE is_active = 1")
                total_accounts = (await cursor.fetchone())[0]
            
            # Calculate uptime
            uptime = datetime.now() - START_TIME
            uptime_str = str(uptime).split('.')[0]  # Remove microseconds
            
            text = (
                f"🏥 *{to_tiny_caps('Bot Health')}*\n"
                f"`────────────────────────`\n\n"
                f"*{to_tiny_caps('System')}:*\n"
                f"• RAM Usage: {ram_usage_mb:.1f} MB\n"
                f"• DB Size: {db_size:.2f} MB\n"
                f"• Uptime: {escape_markdown(uptime_str)}\n\n"
                f"*{to_tiny_caps('Statistics')}:*\n"
                f"• Total Users: {total_users}\n"
                f"• Gmail Accounts: {total_accounts}\n\n"
                f"*{to_tiny_caps('Status')}:* ✅ Running"
            )
            
            keyboard = [[InlineKeyboardButton(
                f"♻️ {to_tiny_caps('Restart Bot')}",
                callback_data="admin_restart"
            )]]
            
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting health info: {str(e)}")
    
    async def restart_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Restart the bot."""
        # Handle both message and callback query
        if update.callback_query:
            user_id = update.callback_query.from_user.id
            query = update.callback_query
            await query.answer()
        else:
            user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            if update.callback_query:
                await query.answer("❌ Unauthorized", show_alert=True)
            else:
                await update.message.reply_text("❌ Unauthorized. Admin only.")
            return
        
        try:
            text = (
                f"♻️ *{to_tiny_caps('Restarting Bot')}*\n"
                f"`────────────────────────`\n\n"
                f"Bot is restarting\\.\\.\\.\n"
                f"This may take a few seconds\\."
            )
            
            if update.callback_query:
                await query.edit_message_text(text, parse_mode='MarkdownV2')
            else:
                await update.message.reply_text(text, parse_mode='MarkdownV2')
            
            # Restart the bot
            os.execv(sys.executable, [sys.executable] + sys.argv)
            
        except Exception as e:
            error_text = f"❌ {escape_markdown(f'Restart failed: {str(e)}')}"
            if update.callback_query:
                await query.edit_message_text(error_text, parse_mode='MarkdownV2')
            else:
                await update.message.reply_text(error_text, parse_mode='MarkdownV2')


# Global instance
admin_handler = AdminHandler()

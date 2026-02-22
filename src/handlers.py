"""Telegram bot handlers."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from gmail_service import gmail_service
from utils import (
    parse_email_headers, get_message_body, extract_otp,
    truncate_text, escape_markdown, format_timestamp, split_message
)
import config


class BotHandlers:
    """Main bot command and callback handlers."""
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command - Main menu."""
        user = update.effective_user
        
        # Register user
        await db.add_user(user.id, user.username, user.first_name)
        
        keyboard = [
            [
                InlineKeyboardButton("📧 My Accounts", callback_data="accounts"),
                InlineKeyboardButton("➕ Add Account", callback_data="add_account")
            ],
            [
                InlineKeyboardButton("📬 Inbox", callback_data="inbox"),
                InlineKeyboardButton("🔍 Search", callback_data="search")
            ],
            [
                InlineKeyboardButton("🏷️ Labels", callback_data="labels"),
                InlineKeyboardButton("⚙️ Settings", callback_data="settings")
            ],
            [
                InlineKeyboardButton("ℹ️ Help", callback_data="help")
            ]
        ]
        
        message = (
            "✨ *Welcome to AutoXMail*\n\n"
            "🔐 *Secure Multi-Account Gmail Client*\n\n"
            "Manage all your Gmail accounts in one place with "
            "end-to-end encryption, real-time notifications, and "
            "powerful search capabilities.\n\n"
            "🚀 *Get Started:*\n"
            "• Add your Gmail accounts securely\n"
            "• Browse, search, and manage emails\n"
            "• Receive instant notifications\n"
            "• Organize with labels and filters\n\n"
            "Choose an option below to begin:"
        )
        
        if update.message:
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.callback_query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    async def accounts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's Gmail accounts."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        accounts = await db.get_gmail_accounts(user_id)
        
        if not accounts:
            keyboard = [
                [InlineKeyboardButton("➕ Add Account", callback_data="add_account")],
                [InlineKeyboardButton("« Back", callback_data="start")]
            ]
            
            await query.edit_message_text(
                "📧 *My Accounts*\n\n"
                "No accounts added yet.\n\n"
                "Add your first Gmail account to get started!",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return
        
        keyboard = []
        message = "📧 *My Accounts*\n\n"
        
        for acc in accounts:
            message += f"• {acc['email']}\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"📬 {truncate_text(acc['email'], 30)}",
                    callback_data=f"select_account:{acc['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("➕ Add Account", callback_data="add_account")])
        keyboard.append([InlineKeyboardButton("« Back", callback_data="start")])
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def inbox(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show inbox messages."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        accounts = await db.get_gmail_accounts(user_id)
        
        if not accounts:
            await query.edit_message_text(
                "❌ No accounts found. Add an account first!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data="start")
                ]])
            )
            return
        
        # Use first account by default
        account_id = accounts[0]['id']
        
        try:
            # Check rate limit
            if not await db.check_rate_limit(user_id, 'inbox'):
                await query.edit_message_text(
                    "⚠️ Rate limit exceeded. Please wait a moment.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back", callback_data="start")
                    ]])
                )
                return
            
            result = await gmail_service.get_messages(account_id, 'INBOX', max_results=10)
            messages = result['messages']
            
            if not messages:
                await query.edit_message_text(
                    "📭 Inbox is empty!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back", callback_data="start")
                    ]])
                )
                return
            
            keyboard = []
            text = f"📬 *Inbox* ({result['resultSizeEstimate']} total)\n\n"
            
            for msg in messages[:10]:
                full_msg = await gmail_service.get_message(account_id, msg['id'])
                subject, sender, date = parse_email_headers(full_msg)
                
                # Check if unread
                is_unread = 'UNREAD' in full_msg.get('labelIds', [])
                icon = "🔵" if is_unread else "⚪"
                
                text += f"{icon} {truncate_text(subject, 40)}\n"
                text += f"   From: {truncate_text(sender, 30)}\n\n"
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"{icon} {truncate_text(subject, 35)}",
                        callback_data=f"view_msg:{account_id}:{msg['id']}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="inbox")])
            keyboard.append([InlineKeyboardButton("« Back", callback_data="start")])
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ Error: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data="start")
                ]])
            )
    
    async def view_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View full message."""
        query = update.callback_query
        await query.answer()
        
        # Parse callback data
        _, account_id, message_id = query.data.split(':')
        account_id = int(account_id)
        
        try:
            message = await gmail_service.get_message(account_id, message_id)
            
            subject, sender, date = parse_email_headers(message)
            body = get_message_body(message['payload'])
            otp = extract_otp(body)
            
            text = f"📧 *Message*\n\n"
            text += f"*Subject:* {escape_markdown(subject)}\n"
            text += f"*From:* {escape_markdown(sender)}\n"
            text += f"*Date:* {format_timestamp(date)}\n\n"
            
            if otp:
                text += f"🔑 *OTP:* `{otp}`\n\n"
            
            text += f"*Preview:*\n{escape_markdown(truncate_text(body, 500))}\n"
            
            # Action buttons
            is_unread = 'UNREAD' in message.get('labelIds', [])
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        "✅ Mark Read" if is_unread else "📧 Mark Unread",
                        callback_data=f"mark_read:{account_id}:{message_id}" if is_unread 
                                    else f"mark_unread:{account_id}:{message_id}"
                    ),
                    InlineKeyboardButton("🗑️ Delete", callback_data=f"delete:{account_id}:{message_id}")
                ],
                [
                    InlineKeyboardButton("⚠️ Spam", callback_data=f"spam:{account_id}:{message_id}"),
                    InlineKeyboardButton("🏷️ Labels", callback_data=f"msg_labels:{account_id}:{message_id}")
                ],
                [InlineKeyboardButton("« Back to Inbox", callback_data="inbox")]
            ]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ Error: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data="inbox")
                ]])
            )
    
    async def mark_read(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mark message as read."""
        query = update.callback_query
        await query.answer("Marking as read...")
        
        _, account_id, message_id = query.data.split(':')
        account_id = int(account_id)
        
        try:
            await gmail_service.mark_as_read(account_id, message_id)
            await query.answer("✅ Marked as read", show_alert=True)
            # Refresh message view
            context.user_data['callback_data'] = f"view_msg:{account_id}:{message_id}"
            await self.view_message(update, context)
        except Exception as e:
            await query.answer(f"❌ Error: {str(e)}", show_alert=True)
    
    async def mark_unread(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mark message as unread."""
        query = update.callback_query
        await query.answer("Marking as unread...")
        
        _, account_id, message_id = query.data.split(':')
        account_id = int(account_id)
        
        try:
            await gmail_service.mark_as_unread(account_id, message_id)
            await query.answer("✅ Marked as unread", show_alert=True)
            context.user_data['callback_data'] = f"view_msg:{account_id}:{message_id}"
            await self.view_message(update, context)
        except Exception as e:
            await query.answer(f"❌ Error: {str(e)}", show_alert=True)
    
    async def delete_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete message."""
        query = update.callback_query
        
        _, account_id, message_id = query.data.split(':')
        account_id = int(account_id)
        
        # Confirmation
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete:{account_id}:{message_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"view_msg:{account_id}:{message_id}")
            ]
        ]
        
        await query.edit_message_text(
            "🗑️ *Delete Message*\n\n"
            "Are you sure you want to move this message to trash?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def confirm_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm delete message."""
        query = update.callback_query
        await query.answer("Deleting...")
        
        _, account_id, message_id = query.data.split(':')
        account_id = int(account_id)
        
        try:
            await gmail_service.move_to_trash(account_id, message_id)
            await query.answer("✅ Moved to trash", show_alert=True)
            # Go back to inbox
            context.user_data['callback_data'] = "inbox"
            await self.inbox(update, context)
        except Exception as e:
            await query.answer(f"❌ Error: {str(e)}", show_alert=True)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help."""
        query = update.callback_query
        if query:
            await query.answer()
        
        text = (
            "ℹ️ *AutoXMail Help*\n\n"
            "*Features:*\n"
            "• Multi-account Gmail support\n"
            "• Browse inbox, sent, labels\n"
            "• Search messages\n"
            "• Mark read/unread\n"
            "• Delete & spam management\n"
            "• Label management\n"
            "• Push notifications\n\n"
            "*Commands:*\n"
            "/start - Main menu\n"
            "/help - This help message\n\n"
            "*Security:*\n"
            "• End-to-end encryption\n"
            "• Per-user credential isolation\n"
            "• Rate limiting\n"
            "• Session timeout\n\n"
            "*Support:*\n"
            "GitHub: github.com/NanoToolz/AutoXMail_Bot"
        )
        
        keyboard = [[InlineKeyboardButton("« Back", callback_data="start")]]
        
        if query:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show settings menu."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        settings = await db.get_notification_settings(user_id)
        
        notif_status = "✅ Enabled" if settings.get('enabled') else "❌ Disabled"
        spam_filter = "✅ Yes" if settings.get('exclude_spam') else "❌ No"
        promo_filter = "✅ Yes" if settings.get('exclude_promotions') else "❌ No"
        
        text = (
            "⚙️ *Settings*\n\n"
            f"*Notifications:* {notif_status}\n"
            f"*Filter Spam:* {spam_filter}\n"
            f"*Filter Promotions:* {promo_filter}\n\n"
            "Configure your preferences below:"
        )
        
        keyboard = [
            [InlineKeyboardButton(
                "🔔 Toggle Notifications",
                callback_data="toggle_notifications"
            )],
            [InlineKeyboardButton(
                "🚫 Toggle Spam Filter",
                callback_data="toggle_spam_filter"
            )],
            [InlineKeyboardButton(
                "📢 Toggle Promo Filter",
                callback_data="toggle_promo_filter"
            )],
            [InlineKeyboardButton("« Back", callback_data="start")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def toggle_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle notifications on/off."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        settings = await db.get_notification_settings(user_id)
        
        new_status = not settings.get('enabled', True)
        await db.update_notification_settings(user_id, enabled=new_status)
        
        await query.answer(
            f"✅ Notifications {'enabled' if new_status else 'disabled'}",
            show_alert=True
        )
        
        # Refresh settings
        await self.settings(update, context)
    
    async def toggle_spam_filter(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle spam filter."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        settings = await db.get_notification_settings(user_id)
        
        new_status = not settings.get('exclude_spam', True)
        await db.update_notification_settings(user_id, exclude_spam=new_status)
        
        await query.answer(
            f"✅ Spam filter {'enabled' if new_status else 'disabled'}",
            show_alert=True
        )
        
        # Refresh settings
        await self.settings(update, context)
    
    async def toggle_promo_filter(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle promotions filter."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        settings = await db.get_notification_settings(user_id)
        
        new_status = not settings.get('exclude_promotions', True)
        await db.update_notification_settings(user_id, exclude_promotions=new_status)
        
        await query.answer(
            f"✅ Promotions filter {'enabled' if new_status else 'disabled'}",
            show_alert=True
        )
        
        # Refresh settings
        await self.settings(update, context)


# Global handlers instance
handlers = BotHandlers()

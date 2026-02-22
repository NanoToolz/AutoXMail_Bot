"""Telegram bot handlers."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import ContextTypes
from database import db
from gmail_service import gmail_service
from formatter import to_tiny_caps, escape_markdown, format_button_text
from utils import (
    parse_email_headers, get_message_body, extract_otp,
    truncate_text, format_timestamp, split_message
)
from auto_delete import schedule_delete, DELETE_WARNING
import config
import asyncio


class BotHandlers:
    """Main bot command and callback handlers."""
    
    async def force_join_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user has joined required channel.
        
        Returns:
            True if check passed or no channel required, False if blocked
        """
        # Skip if no channel configured
        if not config.FORCE_JOIN_CHANNEL:
            return True
        
        user_id = update.effective_user.id
        
        # Skip for admin
        if str(user_id) == config.ADMIN_CHAT_ID:
            return True
        
        try:
            # Check membership
            member = await context.bot.get_chat_member(
                chat_id=config.FORCE_JOIN_CHANNEL,
                user_id=user_id
            )
            
            # Allow if member or admin
            if member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
                return True
            
            # User not a member - show join message
            keyboard = [
                [InlineKeyboardButton(
                    f"📢 {to_tiny_caps('Join Channel')}",
                    url=f"https://t.me/{config.FORCE_JOIN_CHANNEL.lstrip('@')}"
                )],
                [InlineKeyboardButton(
                    f"✅ {to_tiny_caps('I have Joined')}",
                    callback_data="verify_join"
                )]
            ]
            
            text = (
                f"⚠️ *{to_tiny_caps('Join Required')}*\n"
                f"`────────────────────────`\n\n"
                f"Please join our channel to use this bot\\.\n\n"
                f"After joining, click the button below\\."
            )
            
            if update.callback_query:
                await update.callback_query.answer(
                    "❌ Please join the channel first!",
                    show_alert=True
                )
            elif update.message:
                await update.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='MarkdownV2'
                )
            
            return False
            
        except Exception as e:
            # If channel check fails, allow access (channel might be misconfigured)
            return True
    
    async def verify_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Verify user joined the channel."""
        query = update.callback_query
        
        # Check membership again
        if await self.force_join_check(update, context):
            await query.answer("✅ Verified! Welcome!", show_alert=True)
            # Show main menu
            await self.start(update, context)
        else:
            await query.answer("❌ You haven't joined yet!", show_alert=True)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command - Main menu."""
        # Force join check
        if not await self.force_join_check(update, context):
            return
        
        user = update.effective_user
        
        # Register user
        await db.add_user(user.id, user.username, user.first_name)
        
        keyboard = [
            [
                InlineKeyboardButton(f"📧 {to_tiny_caps('My Accounts')}", callback_data="accounts"),
                InlineKeyboardButton(f"➕ {to_tiny_caps('Add Account')}", callback_data="add_account")
            ],
            [
                InlineKeyboardButton(f"📬 {to_tiny_caps('Inbox')}", callback_data="inbox"),
                InlineKeyboardButton(f"✉️ {to_tiny_caps('Compose')}", callback_data="compose")
            ],
            [
                InlineKeyboardButton(f"🔍 {to_tiny_caps('Search')}", callback_data="search"),
                InlineKeyboardButton(f"⚙️ {to_tiny_caps('Settings')}", callback_data="settings")
            ],
            [
                InlineKeyboardButton(f"ℹ️ {to_tiny_caps('Help')}", callback_data="help")
            ]
        ]
        
        message = (
            f"✨ *{to_tiny_caps('Welcome to AutoXMail')}*\n\n"
            f"🔐 *{to_tiny_caps('Secure Multi-Account Gmail Client')}*\n\n"
            f"Manage all your Gmail accounts in one place with "
            f"end\\-to\\-end encryption, real\\-time notifications, and "
            f"powerful search capabilities\\.\n\n"
            f"🚀 *{to_tiny_caps('Get Started')}:*\n"
            f"• Add your Gmail accounts securely\n"
            f"• Browse, search, and manage emails\n"
            f"• Receive instant notifications\n"
            f"• Organize with labels and filters\n\n"
            f"Choose an option below to begin:"
        )
        
        if update.message:
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
        else:
            await update.callback_query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
    
    async def accounts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's Gmail accounts."""
        # Force join check
        if not await self.force_join_check(update, context):
            return
        
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        accounts = await db.get_gmail_accounts(user_id)
        
        if not accounts:
            keyboard = [
                [InlineKeyboardButton(f"➕ {to_tiny_caps('Add Account')}", callback_data="add_account")],
                [InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="start")]
            ]
            
            await query.edit_message_text(
                f"📧 *{to_tiny_caps('My Accounts')}*\n"
                f"`────────────────────────`\n\n"
                f"No accounts added yet\\.\n\n"
                f"Add your first Gmail account to get started\\!",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
            return
        
        keyboard = []
        message = f"📧 *{to_tiny_caps('My Accounts')}*\n`────────────────────────`\n\n"
        
        for acc in accounts:
            message += f"• {escape_markdown(acc['email'])}\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"📬 {truncate_text(acc['email'], 30)}",
                    callback_data=f"select_account:{acc['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(f"➕ {to_tiny_caps('Add Account')}", callback_data="add_account")])
        keyboard.append([InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="start")])
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
    
    async def inbox(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show inbox messages."""
        # Force join check
        if not await self.force_join_check(update, context):
            return
        
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        accounts = await db.get_gmail_accounts(user_id)
        
        if not accounts:
            await query.edit_message_text(
                f"❌ {escape_markdown('No accounts found. Add an account first!')}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="start")
                ]]),
                parse_mode='MarkdownV2'
            )
            return
        
        # Use first account by default
        account_id = accounts[0]['id']
        
        try:
            # Check rate limit
            if not await db.check_rate_limit(user_id, 'inbox'):
                await query.edit_message_text(
                    f"⚠️ {escape_markdown('Rate limit exceeded. Please wait a moment.')}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="start")
                    ]]),
                    parse_mode='MarkdownV2'
                )
                return
            
            result = await gmail_service.get_messages(account_id, 'INBOX', max_results=10)
            messages = result['messages']
            
            if not messages:
                await query.edit_message_text(
                    f"📭 {escape_markdown('Inbox is empty!')}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="start")
                    ]]),
                    parse_mode='MarkdownV2'
                )
                return
            
            keyboard = []
            text = f"📬 *{to_tiny_caps('Inbox')}* \\({result['resultSizeEstimate']} total\\)\n`────────────────────────`\n\n"
            
            for msg in messages[:10]:
                full_msg = await gmail_service.get_message(account_id, msg['id'])
                subject, sender, date = parse_email_headers(full_msg)
                
                # Check if unread
                is_unread = 'UNREAD' in full_msg.get('labelIds', [])
                icon = "🔵" if is_unread else "⚪"
                
                text += f"{icon} {escape_markdown(truncate_text(subject, 40))}\n"
                text += f"   From: {escape_markdown(truncate_text(sender, 30))}\n\n"
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"{icon} {truncate_text(subject, 35)}",
                        callback_data=f"view_msg:{account_id}:{msg['id']}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton(f"🔄 {to_tiny_caps('Refresh')}", callback_data="inbox")])
            keyboard.append([InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="start")])
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ {escape_markdown(f'Error: {str(e)}')}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="start")
                ]]),
                parse_mode='MarkdownV2'
            )
    
    async def view_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View full message."""
        # Force join check
        if not await self.force_join_check(update, context):
            return
        
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
            
            text = f"📧 *{to_tiny_caps('Message')}*\n`────────────────────────`\n\n"
            text += f"*{to_tiny_caps('Subject')}:* {escape_markdown(subject)}\n"
            text += f"*{to_tiny_caps('From')}:* {escape_markdown(sender)}\n"
            text += f"*{to_tiny_caps('Date')}:* {escape_markdown(format_timestamp(date))}\n\n"
            
            if otp:
                text += f"🔑 *{to_tiny_caps('OTP')}:* `{otp}`\n\n"
            
            text += f"*{to_tiny_caps('Preview')}:*\n{escape_markdown(truncate_text(body, 500))}\n"
            
            # Action buttons
            is_unread = 'UNREAD' in message.get('labelIds', [])
            
            keyboard = [
                [
                    InlineKeyboardButton(f"↩️ {to_tiny_caps('Reply')}", callback_data=f"email:reply:{account_id}:{message_id}"),
                    InlineKeyboardButton(f"↪️ {to_tiny_caps('Forward')}", callback_data=f"email:forward:{account_id}:{message_id}")
                ],
                [
                    InlineKeyboardButton(
                        f"✅ {to_tiny_caps('Mark Read')}" if is_unread else f"📧 {to_tiny_caps('Mark Unread')}",
                        callback_data=f"mark_read:{account_id}:{message_id}" if is_unread 
                                    else f"mark_unread:{account_id}:{message_id}"
                    ),
                    InlineKeyboardButton(f"🗑️ {to_tiny_caps('Delete')}", callback_data=f"delete:{account_id}:{message_id}")
                ],
                [
                    InlineKeyboardButton(f"📄 {to_tiny_caps('Full Email')}", callback_data=f"email:full:{account_id}:{message_id}:1"),
                    InlineKeyboardButton(f"⚠️ {to_tiny_caps('Spam')}", callback_data=f"spam:{account_id}:{message_id}")
                ],
                [InlineKeyboardButton(f"🔙 {to_tiny_caps('Back to Inbox')}", callback_data="inbox")]
            ]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ {escape_markdown(f'Error: {str(e)}')}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="inbox")
                ]]),
                parse_mode='MarkdownV2'
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
                InlineKeyboardButton(f"✅ {to_tiny_caps('Yes, Delete')}", callback_data=f"confirm_delete:{account_id}:{message_id}"),
                InlineKeyboardButton(f"❌ {to_tiny_caps('Cancel')}", callback_data=f"view_msg:{account_id}:{message_id}")
            ]
        ]
        
        await query.edit_message_text(
            f"🗑️ *{to_tiny_caps('Delete Message')}*\n"
            f"`────────────────────────`\n\n"
            f"Are you sure you want to move this message to trash?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
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
            f"ℹ️ *{to_tiny_caps('AutoXMail Help')}*\n"
            f"`────────────────────────`\n\n"
            f"*{to_tiny_caps('Features')}:*\n"
            f"• Multi\\-account Gmail support\n"
            f"• Browse inbox, sent, labels\n"
            f"• Search messages\n"
            f"• Mark read/unread\n"
            f"• Delete \\& spam management\n"
            f"• Label management\n"
            f"• Push notifications\n\n"
            f"*{to_tiny_caps('Commands')}:*\n"
            f"/start \\- Main menu\n"
            f"/help \\- This help message\n\n"
            f"*{to_tiny_caps('Security')}:*\n"
            f"• End\\-to\\-end encryption\n"
            f"• Per\\-user credential isolation\n"
            f"• Rate limiting\n"
            f"• Session timeout\n\n"
            f"*{to_tiny_caps('Support')}:*\n"
            f"GitHub: github\\.com/NanoToolz/AutoXMail\\_Bot"
        )
        
        keyboard = [[InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="start")]]
        
        if query:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
    
    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show settings menu."""
        # Force join check
        if not await self.force_join_check(update, context):
            return
        
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        settings = await db.get_notification_settings(user_id)
        
        notif_status = "✅ Enabled" if settings.get('enabled') else "❌ Disabled"
        spam_filter = "✅ Yes" if settings.get('exclude_spam') else "❌ No"
        promo_filter = "✅ Yes" if settings.get('exclude_promotions') else "❌ No"
        
        text = (
            f"⚙️ *{to_tiny_caps('Settings')}*\n"
            f"`────────────────────────`\n\n"
            f"*{to_tiny_caps('Notifications')}:* {escape_markdown(notif_status)}\n"
            f"*{to_tiny_caps('Filter Spam')}:* {escape_markdown(spam_filter)}\n"
            f"*{to_tiny_caps('Filter Promotions')}:* {escape_markdown(promo_filter)}\n\n"
            f"Configure your preferences below:"
        )
        
        keyboard = [
            [InlineKeyboardButton(
                f"🔔 {to_tiny_caps('Toggle Notifications')}",
                callback_data="toggle_notifications"
            )],
            [InlineKeyboardButton(
                f"🚫 {to_tiny_caps('Toggle Spam Filter')}",
                callback_data="toggle_spam_filter"
            )],
            [InlineKeyboardButton(
                f"📢 {to_tiny_caps('Toggle Promo Filter')}",
                callback_data="toggle_promo_filter"
            )],
            [InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="start")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
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


    async def unknown_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown input."""
        # Skip if waiting for specific input
        if context.user_data.get('state'):
            return
        
        # Delete user's message immediately
        try:
            await update.message.delete()
        except:
            pass
        
        # Send warning
        keyboard = [[InlineKeyboardButton(f"🏠 {to_tiny_caps('Main Menu')}", callback_data="start")]]
        
        text = (
            f"⚠️ *{to_tiny_caps('Unknown Input')}*\n"
            f"`────────────────────────`\n\n"
            f"Please use the buttons below\\."
        )
        
        msg = await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
        
        # Auto-delete warning after 5 seconds
        asyncio.create_task(schedule_delete(
            context.bot,
            update.effective_chat.id,
            msg.message_id,
            DELETE_WARNING
        ))


# Global handlers instance
handlers = BotHandlers()

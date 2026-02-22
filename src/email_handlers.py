"""Email composition and interaction handlers."""
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from gmail_service import gmail_service
from formatter import to_tiny_caps, escape_markdown
from paginator import paginate, create_pagination_keyboard
from utils import parse_email_headers, get_message_body
import asyncio
from auto_delete import schedule_delete, DELETE_SUCCESS

# Compose flow states
SELECT_FROM, ENTER_TO, ENTER_SUBJECT, ENTER_BODY, CONFIRM = range(5)


class EmailHandlers:
    """Handlers for email composition and interactions."""
    
    async def start_compose(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start compose email flow - select from account."""
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
            return ConversationHandler.END
        
        # If only one account, skip selection
        if len(accounts) == 1:
            context.user_data['compose_from_account'] = accounts[0]['id']
            return await self.ask_to_email(update, context)
        
        # Show account selection
        keyboard = []
        for acc in accounts:
            keyboard.append([InlineKeyboardButton(
                f"📧 {acc['email']}",
                callback_data=f"compose_from:{acc['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            f"❌ {to_tiny_caps('Cancel')}",
            callback_data="cancel_compose"
        )])
        
        text = (
            f"*{to_tiny_caps('AutoXMail')}* · *{to_tiny_caps('Send Mail — Step 1/4')}*\n"
            f"`────────────────────────`\n\n"
            f"Select the account to send from:"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
        
        context.user_data['waiting_for'] = 'compose_from'
        return SELECT_FROM
    
    async def select_from_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle from account selection."""
        query = update.callback_query
        await query.answer()
        
        account_id = int(query.data.split(':')[1])
        context.user_data['compose_from_account'] = account_id
        
        return await self.ask_to_email(update, context)
    
    async def ask_to_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ask for recipient email."""
        query = update.callback_query if update.callback_query else None
        
        text = (
            f"*{to_tiny_caps('AutoXMail')}* · *{to_tiny_caps('Send Mail — Step 2/4')}*\n"
            f"`────────────────────────`\n\n"
            f"Enter recipient email address:\n\n"
            f"Example: `user@example\\.com`"
        )
        
        keyboard = [[InlineKeyboardButton(
            f"❌ {to_tiny_caps('Cancel')}",
            callback_data="cancel_compose"
        )]]
        
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
        
        context.user_data['waiting_for'] = 'compose_to'
        return ENTER_TO
    
    async def receive_to_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive and validate recipient email."""
        to_email = update.message.text.strip()
        
        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, to_email):
            msg = await update.message.reply_text(
                f"❌ {escape_markdown('Invalid email format. Please try again.')}",
                parse_mode='MarkdownV2'
            )
            asyncio.create_task(schedule_delete(context.bot, update.effective_chat.id, msg.message_id, 5))
            return ENTER_TO
        
        context.user_data['compose_to'] = to_email
        
        text = (
            f"*{to_tiny_caps('AutoXMail')}* · *{to_tiny_caps('Send Mail — Step 3/4')}*\n"
            f"`────────────────────────`\n\n"
            f"Enter email subject:"
        )
        
        keyboard = [[InlineKeyboardButton(
            f"❌ {to_tiny_caps('Cancel')}",
            callback_data="cancel_compose"
        )]]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
        
        context.user_data['waiting_for'] = 'compose_subject'
        return ENTER_SUBJECT
    
    async def receive_subject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive email subject."""
        subject = update.message.text.strip()
        context.user_data['compose_subject'] = subject
        
        text = (
            f"*{to_tiny_caps('AutoXMail')}* · *{to_tiny_caps('Send Mail — Step 4/4')}*\n"
            f"`────────────────────────`\n\n"
            f"Enter email body:"
        )
        
        keyboard = [[InlineKeyboardButton(
            f"❌ {to_tiny_caps('Cancel')}",
            callback_data="cancel_compose"
        )]]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
        
        context.user_data['waiting_for'] = 'compose_body'
        return ENTER_BODY
    
    async def receive_body(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive email body and show confirmation."""
        body = update.message.text.strip()
        context.user_data['compose_body'] = body
        
        # Show confirmation
        to_email = context.user_data['compose_to']
        subject = context.user_data['compose_subject']
        
        # Prepare body preview with ellipsis
        body_preview = body[:100]
        ellipsis = '\\.\\.\\.' if len(body) > 100 else ''
        
        text = (
            f"*{to_tiny_caps('AutoXMail')}* · *{to_tiny_caps('Confirm Send')}*\n"
            f"`────────────────────────`\n\n"
            f"*{to_tiny_caps('To')}:* {escape_markdown(to_email)}\n"
            f"*{to_tiny_caps('Subject')}:* {escape_markdown(subject)}\n"
            f"*{to_tiny_caps('Body')}:* {escape_markdown(body_preview)}{ellipsis}\n\n"
            f"Ready to send?"
        )
        
        keyboard = [
            [
                InlineKeyboardButton(f"✅ {to_tiny_caps('Send')}", callback_data="compose_send"),
                InlineKeyboardButton(f"✏️ {to_tiny_caps('Edit')}", callback_data="compose_edit")
            ],
            [InlineKeyboardButton(f"❌ {to_tiny_caps('Cancel')}", callback_data="cancel_compose")]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
        
        context.user_data['waiting_for'] = 'compose_confirm'
        return CONFIRM
    
    async def send_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send the composed email."""
        query = update.callback_query
        await query.answer("Sending...")
        
        try:
            account_id = context.user_data['compose_from_account']
            to_email = context.user_data['compose_to']
            subject = context.user_data['compose_subject']
            body = context.user_data['compose_body']
            
            # Send email
            await gmail_service.send_email(account_id, to_email, subject, body)
            
            text = (
                f"✅ *{to_tiny_caps('Email Sent Successfully')}\\!*\n"
                f"`────────────────────────`\n\n"
                f"Your email has been sent to {escape_markdown(to_email)}\\."
            )
            
            keyboard = [[InlineKeyboardButton(f"🏠 {to_tiny_caps('Main Menu')}", callback_data="start")]]
            
            msg = await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
            
            # Auto-delete success message
            asyncio.create_task(schedule_delete(
                context.bot,
                update.effective_chat.id,
                msg.message_id,
                DELETE_SUCCESS
            ))
            
            # Clear compose data
            for key in ['compose_from_account', 'compose_to', 'compose_subject', 'compose_body', 'waiting_for']:
                context.user_data.pop(key, None)
            
            return ConversationHandler.END
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ {escape_markdown(f'Failed to send: {str(e)}')}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="start")
                ]]),
                parse_mode='MarkdownV2'
            )
            return ConversationHandler.END
    
    async def edit_compose(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Edit composed email - restart from step 2."""
        query = update.callback_query
        await query.answer()
        
        return await self.ask_to_email(update, context)
    
    async def cancel_compose(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel compose flow."""
        query = update.callback_query
        await query.answer("Cancelled")
        
        # Clear compose data
        for key in ['compose_from_account', 'compose_to', 'compose_subject', 'compose_body', 'waiting_for']:
            context.user_data.pop(key, None)
        
        await query.edit_message_text(
            f"❌ {escape_markdown('Compose cancelled.')}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f"🏠 {to_tiny_caps('Main Menu')}", callback_data="start")
            ]]),
            parse_mode='MarkdownV2'
        )
        
        return ConversationHandler.END
    
    async def start_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start reply flow."""
        query = update.callback_query
        await query.answer()
        
        # Parse message ID from callback
        _, _, account_id, message_id = query.data.split(':')
        account_id = int(account_id)
        
        context.user_data['reply_account_id'] = account_id
        context.user_data['reply_message_id'] = message_id
        context.user_data['waiting_for'] = 'reply_body'
        
        text = (
            f"*{to_tiny_caps('AutoXMail')}* · *{to_tiny_caps('Reply to Email')}*\n"
            f"`────────────────────────`\n\n"
            f"Enter your reply:"
        )
        
        keyboard = [[InlineKeyboardButton(
            f"❌ {to_tiny_caps('Cancel')}",
            callback_data=f"view_msg:{account_id}:{message_id}"
        )]]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
    
    async def send_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send reply email."""
        if context.user_data.get('waiting_for') != 'reply_body':
            return
        
        reply_body = update.message.text.strip()
        account_id = context.user_data['reply_account_id']
        message_id = context.user_data['reply_message_id']
        
        try:
            await update.message.reply_text("⏳ Sending reply...")
            
            # Send reply
            await gmail_service.reply_email(account_id, message_id, reply_body)
            
            text = (
                f"✅ *{to_tiny_caps('Reply Sent Successfully')}\\!*\n"
                f"`────────────────────────`\n\n"
                f"Your reply has been sent\\."
            )
            
            keyboard = [[InlineKeyboardButton(
                f"📬 {to_tiny_caps('Back to Inbox')}",
                callback_data="inbox"
            )]]
            
            msg = await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
            
            # Auto-delete success message
            asyncio.create_task(schedule_delete(
                context.bot,
                update.effective_chat.id,
                msg.message_id,
                DELETE_SUCCESS
            ))
            
            # Clear reply data
            for key in ['reply_account_id', 'reply_message_id', 'waiting_for']:
                context.user_data.pop(key, None)
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ {escape_markdown(f'Failed to send reply: {str(e)}')}",
                parse_mode='MarkdownV2'
            )
    
    async def start_forward(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start forward flow."""
        query = update.callback_query
        await query.answer()
        
        # Parse message ID from callback
        _, _, account_id, message_id = query.data.split(':')
        account_id = int(account_id)
        
        context.user_data['forward_account_id'] = account_id
        context.user_data['forward_message_id'] = message_id
        context.user_data['waiting_for'] = 'forward_to'
        
        text = (
            f"*{to_tiny_caps('AutoXMail')}* · *{to_tiny_caps('Forward Email')}*\n"
            f"`────────────────────────`\n\n"
            f"Enter recipient email address:"
        )
        
        keyboard = [[InlineKeyboardButton(
            f"❌ {to_tiny_caps('Cancel')}",
            callback_data=f"view_msg:{account_id}:{message_id}"
        )]]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
    
    async def send_forward(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send forwarded email."""
        if context.user_data.get('waiting_for') != 'forward_to':
            return
        
        forward_to = update.message.text.strip()
        
        # Validate email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, forward_to):
            msg = await update.message.reply_text(
                f"❌ {escape_markdown('Invalid email format. Please try again.')}",
                parse_mode='MarkdownV2'
            )
            asyncio.create_task(schedule_delete(context.bot, update.effective_chat.id, msg.message_id, 5))
            return
        
        account_id = context.user_data['forward_account_id']
        message_id = context.user_data['forward_message_id']
        
        try:
            await update.message.reply_text("⏳ Forwarding...")
            
            # Forward email
            await gmail_service.forward_email(account_id, message_id, forward_to)
            
            text = (
                f"✅ *{to_tiny_caps('Email Forwarded Successfully')}\\!*\n"
                f"`────────────────────────`\n\n"
                f"Email forwarded to {escape_markdown(forward_to)}\\."
            )
            
            keyboard = [[InlineKeyboardButton(
                f"📬 {to_tiny_caps('Back to Inbox')}",
                callback_data="inbox"
            )]]
            
            msg = await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
            
            # Auto-delete success message
            asyncio.create_task(schedule_delete(
                context.bot,
                update.effective_chat.id,
                msg.message_id,
                DELETE_SUCCESS
            ))
            
            # Clear forward data
            for key in ['forward_account_id', 'forward_message_id', 'waiting_for']:
                context.user_data.pop(key, None)
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ {escape_markdown(f'Failed to forward: {str(e)}')}",
                parse_mode='MarkdownV2'
            )
    
    async def view_full_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View full email with pagination."""
        query = update.callback_query
        await query.answer()
        
        # Parse callback data
        parts = query.data.split(':')
        account_id = int(parts[2])
        message_id = parts[3]
        page = int(parts[4]) if len(parts) > 4 else 1
        
        try:
            # Fetch full message
            message = await gmail_service.get_message(account_id, message_id)
            subject, sender, date = parse_email_headers(message)
            body = get_message_body(message['payload'])
            
            # Build full email text
            full_text = (
                f"*{to_tiny_caps('Subject')}:* {escape_markdown(subject)}\n"
                f"*{to_tiny_caps('From')}:* {escape_markdown(sender)}\n"
                f"*{to_tiny_caps('Date')}:* {escape_markdown(date)}\n\n"
                f"*{to_tiny_caps('Body')}:*\n"
                f"{escape_markdown(body)}"
            )
            
            # Paginate
            chunks = paginate(full_text, chunk_size=3500)
            total_pages = len(chunks)
            
            # Get current page
            current_text = chunks[page - 1]
            
            # Add header
            header = (
                f"*{to_tiny_caps('AutoXMail')}* · *{to_tiny_caps('Full Email')}* — "
                f"{to_tiny_caps(f'Page {page} of {total_pages}')}\n"
                f"`────────────────────────`\n\n"
            )
            
            # Create pagination keyboard
            keyboard = create_pagination_keyboard(
                page,
                total_pages,
                f"email:full:{account_id}:{message_id}",
                f"view_msg:{account_id}:{message_id}"
            )
            
            await query.edit_message_text(
                header + current_text,
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


# Global instance
email_handlers = EmailHandlers()

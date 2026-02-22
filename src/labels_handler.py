"""Labels management handler."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from gmail_service import gmail_service
from formatter import to_tiny_caps, escape_markdown
from utils import parse_email_headers, truncate_text
import asyncio
from auto_delete import schedule_delete, DELETE_SUCCESS

# States
SELECT_ACCOUNT, ENTER_LABEL_NAME = range(2)


class LabelsHandler:
    """Handler for Gmail labels management."""
    
    async def show_labels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show labels for selected account."""
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
        
        # If only one account, show labels directly
        if len(accounts) == 1:
            context.user_data['labels_account_id'] = accounts[0]['id']
            return await self.list_labels(update, context)
        
        # Show account selection
        keyboard = []
        for acc in accounts:
            keyboard.append([InlineKeyboardButton(
                f"📧 {acc['email']}",
                callback_data=f"labels_account:{acc['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            f"🔙 {to_tiny_caps('Back')}",
            callback_data="start"
        )])
        
        text = (
            f"*{to_tiny_caps('AutoXMail')}* · *{to_tiny_caps('Labels')}*\n"
            f"`────────────────────────`\n\n"
            f"Select account:"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
    
    async def select_labels_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle labels account selection."""
        query = update.callback_query
        await query.answer()
        
        account_id = int(query.data.split(':')[1])
        context.user_data['labels_account_id'] = account_id
        
        return await self.list_labels(update, context)
    
    async def list_labels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all labels for account."""
        query = update.callback_query if update.callback_query else None
        account_id = context.user_data.get('labels_account_id')
        
        try:
            if query:
                await query.answer("Loading labels...")
            
            # Get labels
            labels = await gmail_service.get_labels(account_id)
            
            # Filter out system labels we don't want to show
            user_labels = [l for l in labels if l['type'] == 'user']
            system_labels = [l for l in labels if l['type'] == 'system' and l['id'] in [
                'INBOX', 'SENT', 'DRAFT', 'SPAM', 'TRASH', 'STARRED', 'IMPORTANT', 'UNREAD'
            ]]
            
            keyboard = []
            text = (
                f"🏷️ *{to_tiny_caps('Labels')}*\n"
                f"`────────────────────────`\n\n"
            )
            
            # System labels
            if system_labels:
                text += f"*{to_tiny_caps('System Labels')}:*\n"
                for label in system_labels:
                    name = label['name']
                    total = label.get('messagesTotal', 0)
                    unread = label.get('messagesUnread', 0)
                    
                    text += f"• {escape_markdown(name)} \\({total} total, {unread} unread\\)\n"
                    
                    keyboard.append([InlineKeyboardButton(
                        f"📖 {name} ({unread})",
                        callback_data=f"label_view:{account_id}:{label['id']}"
                    )])
                text += "\n"
            
            # User labels
            if user_labels:
                text += f"*{to_tiny_caps('Custom Labels')}:*\n"
                for label in user_labels:
                    name = label['name']
                    total = label.get('messagesTotal', 0)
                    
                    text += f"• {escape_markdown(name)} \\({total}\\)\n"
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            f"📖 {truncate_text(name, 20)}",
                            callback_data=f"label_view:{account_id}:{label['id']}"
                        ),
                        InlineKeyboardButton(
                            f"🗑️",
                            callback_data=f"label_delete:{account_id}:{label['id']}"
                        )
                    ])
                text += "\n"
            
            # Create new label button
            keyboard.append([InlineKeyboardButton(
                f"➕ {to_tiny_caps('Create New Label')}",
                callback_data="label_create"
            )])
            keyboard.append([InlineKeyboardButton(
                f"🔙 {to_tiny_caps('Back')}",
                callback_data="start"
            )])
            
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
            
        except Exception as e:
            error_text = f"❌ {escape_markdown(f'Error loading labels: {str(e)}')}"
            if query:
                await query.edit_message_text(
                    error_text,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="start")
                    ]]),
                    parse_mode='MarkdownV2'
                )
            else:
                await update.message.reply_text(error_text, parse_mode='MarkdownV2')
    
    async def view_label_emails(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View emails with specific label."""
        query = update.callback_query
        await query.answer()
        
        _, _, account_id, label_id = query.data.split(':')
        account_id = int(account_id)
        
        try:
            # Get messages with this label
            result = await gmail_service.get_messages(account_id, label_id, max_results=10)
            messages = result['messages']
            
            if not messages:
                await query.edit_message_text(
                    f"📭 {escape_markdown('No emails with this label.')}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="labels")
                    ]]),
                    parse_mode='MarkdownV2'
                )
                return
            
            keyboard = []
            text = (
                f"🏷️ *{to_tiny_caps('Label Emails')}*\n"
                f"`────────────────────────`\n\n"
            )
            
            for msg in messages[:10]:
                full_msg = await gmail_service.get_message(account_id, msg['id'])
                subject, sender, date = parse_email_headers(full_msg)
                
                is_unread = 'UNREAD' in full_msg.get('labelIds', [])
                icon = "🔵" if is_unread else "⚪"
                
                text += f"{icon} {escape_markdown(truncate_text(subject, 40))}\n"
                text += f"   From: {escape_markdown(truncate_text(sender, 30))}\n\n"
                
                keyboard.append([InlineKeyboardButton(
                    f"{icon} {truncate_text(subject, 35)}",
                    callback_data=f"view_msg:{account_id}:{msg['id']}"
                )])
            
            keyboard.append([InlineKeyboardButton(
                f"🔙 {to_tiny_caps('Back to Labels')}",
                callback_data="labels"
            )])
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ {escape_markdown(f'Error: {str(e)}')}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="labels")
                ]]),
                parse_mode='MarkdownV2'
            )
    
    async def confirm_delete_label(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm label deletion."""
        query = update.callback_query
        await query.answer()
        
        _, _, account_id, label_id = query.data.split(':')
        
        keyboard = [
            [
                InlineKeyboardButton(
                    f"✅ {to_tiny_caps('Yes, Delete')}",
                    callback_data=f"label_delete_confirm:{account_id}:{label_id}"
                ),
                InlineKeyboardButton(
                    f"❌ {to_tiny_caps('Cancel')}",
                    callback_data="labels"
                )
            ]
        ]
        
        await query.edit_message_text(
            f"🗑️ *{to_tiny_caps('Delete Label')}*\n"
            f"`────────────────────────`\n\n"
            f"Are you sure you want to delete this label?\n\n"
            f"⚠️ This action cannot be undone\\.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
    
    async def delete_label(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete label."""
        query = update.callback_query
        await query.answer("Deleting...")
        
        _, _, _, account_id, label_id = query.data.split(':')
        account_id = int(account_id)
        
        try:
            service = await gmail_service.get_service(account_id)
            service.users().labels().delete(userId='me', id=label_id).execute()
            
            text = (
                f"✅ *{to_tiny_caps('Label Deleted')}*\n"
                f"`────────────────────────`\n\n"
                f"Label has been deleted successfully\\."
            )
            
            msg = await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🏷️ {to_tiny_caps('Back to Labels')}", callback_data="labels")
                ]]),
                parse_mode='MarkdownV2'
            )
            
            # Auto-delete success message
            asyncio.create_task(schedule_delete(
                context.bot,
                update.effective_chat.id,
                msg.message_id,
                DELETE_SUCCESS
            ))
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ {escape_markdown(f'Failed to delete: {str(e)}')}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="labels")
                ]]),
                parse_mode='MarkdownV2'
            )
    
    async def start_create_label(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start create label flow."""
        query = update.callback_query
        await query.answer()
        
        context.user_data['waiting_for'] = 'label_name'
        
        text = (
            f"*{to_tiny_caps('AutoXMail')}* · *{to_tiny_caps('Create Label')}*\n"
            f"`────────────────────────`\n\n"
            f"Enter label name:"
        )
        
        keyboard = [[InlineKeyboardButton(
            f"❌ {to_tiny_caps('Cancel')}",
            callback_data="labels"
        )]]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
    
    async def create_label(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create new label."""
        if context.user_data.get('waiting_for') != 'label_name':
            return
        
        label_name = update.message.text.strip()
        account_id = context.user_data.get('labels_account_id')
        
        try:
            await update.message.reply_text("⏳ Creating label...")
            
            service = await gmail_service.get_service(account_id)
            label_object = {
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            
            service.users().labels().create(userId='me', body=label_object).execute()
            
            text = (
                f"✅ *{to_tiny_caps('Label Created')}*\n"
                f"`────────────────────────`\n\n"
                f"Label '{escape_markdown(label_name)}' created successfully\\."
            )
            
            msg = await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🏷️ {to_tiny_caps('Back to Labels')}", callback_data="labels")
                ]]),
                parse_mode='MarkdownV2'
            )
            
            # Auto-delete success message
            asyncio.create_task(schedule_delete(
                context.bot,
                update.effective_chat.id,
                msg.message_id,
                DELETE_SUCCESS
            ))
            
            context.user_data.pop('waiting_for', None)
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ {escape_markdown(f'Failed to create label: {str(e)}')}",
                parse_mode='MarkdownV2'
            )


# Global instance
labels_handler = LabelsHandler()

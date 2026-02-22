"""Folders (system labels) handler."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from gmail_service import gmail_service
from formatter import to_tiny_caps, escape_markdown
from utils import parse_email_headers, truncate_text


class FoldersHandler:
    """Handler for Gmail folders (system labels)."""
    
    async def show_folders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show folder selection."""
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
        
        # If only one account, show folders directly
        if len(accounts) == 1:
            context.user_data['folders_account_id'] = accounts[0]['id']
            return await self.list_folders(update, context)
        
        # Show account selection
        keyboard = []
        for acc in accounts:
            keyboard.append([InlineKeyboardButton(
                f"📧 {acc['email']}",
                callback_data=f"folders_account:{acc['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            f"🔙 {to_tiny_caps('Back')}",
            callback_data="start"
        )])
        
        text = (
            f"*{to_tiny_caps('AutoXMail')}* · *{to_tiny_caps('Folders')}*\n"
            f"`────────────────────────`\n\n"
            f"Select account:"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
    
    async def select_folders_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle folders account selection."""
        query = update.callback_query
        await query.answer()
        
        account_id = int(query.data.split(':')[1])
        context.user_data['folders_account_id'] = account_id
        
        return await self.list_folders(update, context)
    
    async def list_folders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all folders."""
        query = update.callback_query if update.callback_query else None
        account_id = context.user_data.get('folders_account_id')
        
        try:
            # Get labels to show counts
            labels = await gmail_service.get_labels(account_id)
            label_map = {l['id']: l for l in labels}
            
            # Define folders
            folders = [
                {'id': 'INBOX', 'name': 'Inbox', 'icon': '📬'},
                {'id': 'SENT', 'name': 'Sent', 'icon': '📤'},
                {'id': 'DRAFT', 'name': 'Drafts', 'icon': '📝'},
                {'id': 'SPAM', 'name': 'Spam', 'icon': '⚠️'},
                {'id': 'TRASH', 'name': 'Trash', 'icon': '🗑️'},
                {'id': 'STARRED', 'name': 'Starred', 'icon': '⭐'},
                {'id': 'IMPORTANT', 'name': 'Important', 'icon': '❗'},
            ]
            
            keyboard = []
            text = (
                f"📁 *{to_tiny_caps('Folders')}*\n"
                f"`────────────────────────`\n\n"
                f"Select a folder to view:\n\n"
            )
            
            for folder in folders:
                folder_id = folder['id']
                label_info = label_map.get(folder_id, {})
                total = label_info.get('messagesTotal', 0)
                unread = label_info.get('messagesUnread', 0)
                
                text += f"{folder['icon']} {escape_markdown(folder['name'])} \\({total} total, {unread} unread\\)\n"
                
                keyboard.append([InlineKeyboardButton(
                    f"{folder['icon']} {folder['name']} ({unread})",
                    callback_data=f"folder_view:{account_id}:{folder_id}"
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
            error_text = f"❌ {escape_markdown(f'Error loading folders: {str(e)}')}"
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
    
    async def view_folder_emails(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View emails in specific folder."""
        query = update.callback_query
        await query.answer()
        
        _, _, account_id, folder_id = query.data.split(':')
        account_id = int(account_id)
        
        # Map folder names
        folder_names = {
            'INBOX': 'Inbox',
            'SENT': 'Sent',
            'DRAFT': 'Drafts',
            'SPAM': 'Spam',
            'TRASH': 'Trash',
            'STARRED': 'Starred',
            'IMPORTANT': 'Important'
        }
        folder_name = folder_names.get(folder_id, folder_id)
        
        try:
            # Get messages
            result = await gmail_service.get_messages(account_id, folder_id, max_results=10)
            messages = result['messages']
            
            if not messages:
                await query.edit_message_text(
                    f"📭 {escape_markdown(f'{folder_name} is empty.')}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="folders")
                    ]]),
                    parse_mode='MarkdownV2'
                )
                return
            
            keyboard = []
            text = (
                f"📁 *{to_tiny_caps(folder_name)}*\n"
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
                f"🔙 {to_tiny_caps('Back to Folders')}",
                callback_data="folders"
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
                    InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="folders")
                ]]),
                parse_mode='MarkdownV2'
            )


# Global instance
folders_handler = FoldersHandler()

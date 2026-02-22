"""Search email handler."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from gmail_service import gmail_service
from formatter import to_tiny_caps, escape_markdown
from utils import parse_email_headers, truncate_text

# Search flow states
SELECT_ACCOUNT, ENTER_QUERY = range(2)


class SearchHandler:
    """Handler for email search functionality."""
    
    async def start_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start search flow - select account."""
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
            context.user_data['search_account_id'] = accounts[0]['id']
            return await self.ask_query(update, context)
        
        # Show account selection
        keyboard = []
        for acc in accounts:
            keyboard.append([InlineKeyboardButton(
                f"📧 {acc['email']}",
                callback_data=f"search_account:{acc['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            f"❌ {to_tiny_caps('Cancel')}",
            callback_data="cancel_search"
        )])
        
        text = (
            f"*{to_tiny_caps('AutoXMail')}* · *{to_tiny_caps('Search Emails')}*\n"
            f"`────────────────────────`\n\n"
            f"Select account to search:"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
        
        context.user_data['waiting_for'] = 'search_account'
        return SELECT_ACCOUNT
    
    async def select_search_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle search account selection."""
        query = update.callback_query
        await query.answer()
        
        account_id = int(query.data.split(':')[1])
        context.user_data['search_account_id'] = account_id
        
        return await self.ask_query(update, context)
    
    async def ask_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ask for search query."""
        query = update.callback_query if update.callback_query else None
        
        text = (
            f"*{to_tiny_caps('AutoXMail')}* · *{to_tiny_caps('Search Emails')}*\n"
            f"`────────────────────────`\n\n"
            f"Enter search query:\n\n"
            f"*{to_tiny_caps('Examples')}:*\n"
            f"• `from:user@example\\.com`\n"
            f"• `subject:invoice`\n"
            f"• `has:attachment`\n"
            f"• `is:unread`\n"
            f"• `after:2024/01/01`\n"
            f"• `larger:5M`\n\n"
            f"You can combine multiple terms\\."
        )
        
        keyboard = [[InlineKeyboardButton(
            f"❌ {to_tiny_caps('Cancel')}",
            callback_data="cancel_search"
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
        
        context.user_data['waiting_for'] = 'search_query'
        return ENTER_QUERY
    
    async def perform_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Perform search and show results."""
        if context.user_data.get('waiting_for') != 'search_query':
            return
        
        search_query = update.message.text.strip()
        account_id = context.user_data['search_account_id']
        
        try:
            await update.message.reply_text("🔍 Searching...")
            
            # Search emails
            message_ids = await gmail_service.search_messages(account_id, search_query, max_results=20)
            
            if not message_ids:
                text = (
                    f"📭 {escape_markdown('No results found.')}\n\n"
                    f"Try a different search query\\."
                )
                
                keyboard = [
                    [InlineKeyboardButton(f"🔍 {to_tiny_caps('Search Again')}", callback_data="search")],
                    [InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="start")]
                ]
                
                await update.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='MarkdownV2'
                )
                
                # Clear search data
                for key in ['search_account_id', 'waiting_for']:
                    context.user_data.pop(key, None)
                
                return ConversationHandler.END
            
            # Fetch message details
            keyboard = []
            text = (
                f"🔍 *{to_tiny_caps('Search Results')}*\n"
                f"`────────────────────────`\n\n"
                f"Found {len(message_ids)} results:\n\n"
            )
            
            for msg_id_obj in message_ids[:10]:
                msg_id = msg_id_obj['id']
                full_msg = await gmail_service.get_message(account_id, msg_id)
                subject, sender, date = parse_email_headers(full_msg)
                
                is_unread = 'UNREAD' in full_msg.get('labelIds', [])
                icon = "🔵" if is_unread else "⚪"
                
                text += f"{icon} {escape_markdown(truncate_text(subject, 40))}\n"
                text += f"   From: {escape_markdown(truncate_text(sender, 30))}\n\n"
                
                keyboard.append([InlineKeyboardButton(
                    f"{icon} {truncate_text(subject, 35)}",
                    callback_data=f"view_msg:{account_id}:{msg_id}"
                )])
            
            keyboard.append([InlineKeyboardButton(f"🔍 {to_tiny_caps('Search Again')}", callback_data="search")])
            keyboard.append([InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="start")])
            
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
            
            # Clear search data
            for key in ['search_account_id', 'waiting_for']:
                context.user_data.pop(key, None)
            
            return ConversationHandler.END
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ {escape_markdown(f'Search failed: {str(e)}')}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="start")
                ]]),
                parse_mode='MarkdownV2'
            )
            return ConversationHandler.END
    
    async def cancel_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel search flow."""
        query = update.callback_query
        await query.answer("Cancelled")
        
        # Clear search data
        for key in ['search_account_id', 'waiting_for']:
            context.user_data.pop(key, None)
        
        await query.edit_message_text(
            f"❌ {escape_markdown('Search cancelled.')}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f"🏠 {to_tiny_caps('Main Menu')}", callback_data="start")
            ]]),
            parse_mode='MarkdownV2'
        )
        
        return ConversationHandler.END


# Global instance
search_handler = SearchHandler()

"""Advanced handlers for blocklist, VIP, privacy, and bot settings."""
import json
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from gmail_service import gmail_service
from formatter import to_tiny_caps, escape_markdown
import asyncio
from auto_delete import schedule_delete, DELETE_SUCCESS, DELETE_IMMEDIATE


class AdvancedHandlers:
    """Handler for advanced features."""
    
    async def show_blocklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show blocklist."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        async with db.db_path as conn:
            conn.row_factory = db.aiosqlite.Row
            cursor = await conn.execute("SELECT * FROM blocklist WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
            blocked = await cursor.fetchall()
        keyboard = []
        text = f"🚫 *{to_tiny_caps('Blocklist')}*\n`────────────────────────`\n\n"
        if blocked:
            text += f"Blocked senders/domains:\n\n"
            for entry in blocked:
                text += f"• {escape_markdown(entry['blocked_value'])}\n"
                keyboard.append([InlineKeyboardButton(f"🗑️ {entry['blocked_value'][:30]}", callback_data=f"blocklist_remove:{entry['id']}")])
            text += "\n"
        else:
            text += "No blocked senders yet\\.\n\n"
        keyboard.append([InlineKeyboardButton(f"➕ {to_tiny_caps('Add')}", callback_data="blocklist_add")])
        keyboard.append([InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="settings")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
    
    async def start_add_blocklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start adding to blocklist."""
        query = update.callback_query
        await query.answer()
        text = f"🚫 *{to_tiny_caps('Add to Blocklist')}*\n`────────────────────────`\n\nSend email or domain:\n• spam@example\\.com\n• @spammer\\.com"
        keyboard = [[InlineKeyboardButton(f"🔙 {to_tiny_caps('Cancel')}", callback_data="blocklist")]]
        msg = await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
        context.user_data['waiting_for'] = 'blocklist_add'
        context.user_data['menu_msg_id'] = msg.message_id
        await schedule_delete(msg, 60)
    
    async def add_to_blocklist_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle blocklist addition."""
        if context.user_data.get('waiting_for') != 'blocklist_add':
            return
        user_id = update.effective_user.id
        value = update.message.text.strip()
        await update.message.delete()
        if not re.match(r'^(@?[\w\.-]+@?[\w\.-]+\.\w+|@[\w\.-]+\.\w+)$', value):
            msg = await context.bot.send_message(chat_id=user_id, text="❌ Invalid format", parse_mode="MarkdownV2")
            await schedule_delete(msg, 15)
            return
        async with db.db_path as conn:
            try:
                await conn.execute("INSERT INTO blocklist (user_id, blocked_value) VALUES (?, ?)", (user_id, value))
                await conn.commit()
            except:
                msg = await context.bot.send_message(chat_id=user_id, text="❌ Already blocked", parse_mode="MarkdownV2")
                await schedule_delete(msg, 15)
                return
        context.user_data.pop('waiting_for', None)
        msg = await context.bot.send_message(chat_id=user_id, text=f"✅ Added to blocklist", parse_mode="MarkdownV2")
        await schedule_delete(msg, 15)
    
    async def remove_from_blocklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove from blocklist."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        entry_id = int(query.data.split(':')[1])
        async with db.db_path as conn:
            await conn.execute("DELETE FROM blocklist WHERE id = ? AND user_id = ?", (entry_id, user_id))
            await conn.commit()
        await query.answer("✅ Removed")
        await self.show_blocklist(update, context)
    
    async def show_vip_senders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show VIP senders."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        async with db.db_path as conn:
            conn.row_factory = db.aiosqlite.Row
            cursor = await conn.execute("SELECT * FROM vip_senders WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
            vips = await cursor.fetchall()
        keyboard = []
        text = f"⭐ *{to_tiny_caps('VIP Senders')}*\n`────────────────────────`\n\nVIP senders always trigger push\\.\n\n"
        if vips:
            text += "VIP senders:\n\n"
            for entry in vips:
                text += f"• {escape_markdown(entry['sender_value'])}\n"
                keyboard.append([InlineKeyboardButton(f"🗑️ {entry['sender_value'][:30]}", callback_data=f"vip_remove:{entry['id']}")])
            text += "\n"
        else:
            text += "No VIP senders yet\\.\n\n"
        keyboard.append([InlineKeyboardButton(f"➕ {to_tiny_caps('Add VIP')}", callback_data="vip_add")])
        keyboard.append([InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="settings")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
    
    async def start_add_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start adding VIP."""
        query = update.callback_query
        await query.answer()
        text = f"⭐ *{to_tiny_caps('Add VIP')}*\n`────────────────────────`\n\nSend email or domain:\n• boss@company\\.com\n• @important\\.com"
        keyboard = [[InlineKeyboardButton(f"🔙 {to_tiny_caps('Cancel')}", callback_data="vip")]]
        msg = await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
        context.user_data['waiting_for'] = 'vip_add'
        context.user_data['menu_msg_id'] = msg.message_id
    
    async def add_vip_sender_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle VIP addition."""
        if context.user_data.get('waiting_for') != 'vip_add':
            return
        user_id = update.effective_user.id
        value = update.message.text.strip()
        await update.message.delete()
        if not re.match(r'^(@?[\w\.-]+@?[\w\.-]+\.\w+|@[\w\.-]+\.\w+)$', value):
            msg = await context.bot.send_message(chat_id=user_id, text="❌ Invalid format", parse_mode="MarkdownV2")
            await schedule_delete(msg, 15)
            return
        async with db.db_path as conn:
            try:
                await conn.execute("INSERT INTO vip_senders (user_id, sender_value) VALUES (?, ?)", (user_id, value))
                await conn.commit()
            except:
                msg = await context.bot.send_message(chat_id=user_id, text="❌ Already in VIP", parse_mode="MarkdownV2")
                await schedule_delete(msg, 15)
                return
        context.user_data.pop('waiting_for', None)
        msg = await context.bot.send_message(chat_id=user_id, text="✅ Added to VIP", parse_mode="MarkdownV2")
        await schedule_delete(msg, 15)
    
    async def remove_vip_sender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove VIP."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        entry_id = int(query.data.split(':')[1])
        async with db.db_path as conn:
            await conn.execute("DELETE FROM vip_senders WHERE id = ? AND user_id = ?", (entry_id, user_id))
            await conn.commit()
        await query.answer("✅ Removed")
        await self.show_vip_senders(update, context)
    
    async def show_privacy_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show privacy settings."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        async with db.db_path as conn:
            conn.row_factory = db.aiosqlite.Row
            cursor = await conn.execute("SELECT * FROM privacy_settings WHERE user_id = ?", (user_id,))
            settings = await cursor.fetchone()
        current = settings['global_auto_delete_secs'] if settings else 0
        text = f"🔒 *{to_tiny_caps('Privacy')}*\n`────────────────────────`\n\nAuto\\-delete: *{current}s*\n"
        keyboard = [[InlineKeyboardButton(f"{'✅' if current==0 else ''}❌ Off", callback_data="privacy_timer:0"), InlineKeyboardButton(f"{'✅' if current==30 else ''}⚡30s", callback_data="privacy_timer:30")], [InlineKeyboardButton(f"{'✅' if current==60 else ''}🕐1m", callback_data="privacy_timer:60"), InlineKeyboardButton(f"{'✅' if current==300 else ''}🕐5m", callback_data="privacy_timer:300")], [InlineKeyboardButton(f"{'✅' if current==1800 else ''}📅30m", callback_data="privacy_timer:1800"), InlineKeyboardButton(f"{'✅' if current==3600 else ''}📅1h", callback_data="privacy_timer:3600")], [InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="settings")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
    
    async def set_privacy_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set privacy timer."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        timer = int(query.data.split(':')[1])
        async with db.db_path as conn:
            await conn.execute("INSERT OR REPLACE INTO privacy_settings (user_id, global_auto_delete_secs) VALUES (?, ?)", (user_id, timer))
            await conn.commit()
        await self.show_privacy_settings(update, context)
    
    async def show_bot_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot settings."""
        query = update.callback_query
        await query.answer()
        text = f"🤖 *{to_tiny_caps('Bot Settings')}*\n`────────────────────────`\n"
        keyboard = [[InlineKeyboardButton(f"🖼️ {to_tiny_caps('Change Photo')}", callback_data="bot_change_photo")], [InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="settings")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
    
    async def start_change_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start photo change."""
        query = update.callback_query
        await query.answer()
        text = f"🖼️ *{to_tiny_caps('Change Photo')}*\n`────────────────────────`\n\nSend a photo\\."
        keyboard = [[InlineKeyboardButton(f"🔙 {to_tiny_caps('Cancel')}", callback_data="bot_settings")]]
        msg = await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
        context.user_data['waiting_for'] = 'bot_photo'
        context.user_data['menu_msg_id'] = msg.message_id
    
    async def change_bot_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo change."""
        if context.user_data.get('waiting_for') != 'bot_photo':
            return
        user_id = update.effective_user.id
        import config
        if user_id != config.ADMIN_ID:
            await update.message.delete()
            return
        if not update.message.photo:
            await update.message.delete()
            return
        await update.message.delete()
        try:
            photo = update.message.photo[-1]
            file = await photo.get_file()
            photo_bytes = await file.download_as_bytearray()
            await context.bot.set_chat_photo(chat_id=user_id, photo=bytes(photo_bytes))
            context.user_data.pop('waiting_for', None)
            msg = await context.bot.send_message(chat_id=user_id, text="✅ Photo updated", parse_mode="MarkdownV2")
            await schedule_delete(msg, 15)
        except Exception as e:
            msg = await context.bot.send_message(chat_id=user_id, text=f"❌ Failed", parse_mode="MarkdownV2")
            await schedule_delete(msg, 15)
    
    async def confirm_unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm unsubscribe."""
        query = update.callback_query
        await query.answer()
        parts = query.data.split(':')
        account_id = parts[1]
        msg_id = parts[2]
        text = f"⚠️ *{to_tiny_caps('Unsubscribe')}*\n`────────────────────────`\n\n1\\. Send unsubscribe\n2\\. Block sender\n\nContinue?"
        keyboard = [[InlineKeyboardButton(f"✅ Yes", callback_data=f"unsub_exec:{account_id}:{msg_id}"), InlineKeyboardButton(f"❌ No", callback_data=f"email_view:{msg_id}")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
    
    async def execute_unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Execute unsubscribe."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        parts = query.data.split(':')
        account_id = int(parts[1])
        msg_id = parts[2]
        try:
            service = await gmail_service.get_service(account_id)
            success = await gmail_service.unsubscribe_email(service, msg_id)
            if success:
                message = await gmail_service.get_message(service, msg_id)
                sender = message.get('from', '')
                sender_email = re.search(r'<(.+?)>', sender)
                sender_email = sender_email.group(1) if sender_email else sender
                async with db.db_path as conn:
                    try:
                        await conn.execute("INSERT INTO blocklist (user_id, blocked_value) VALUES (?, ?)", (user_id, sender_email))
                        await conn.commit()
                    except:
                        pass
                text = "✅ Unsubscribed and blocked"
            else:
                text = "❌ No unsubscribe link found"
            keyboard = [[InlineKeyboardButton(f"🔙 Back", callback_data=f"email_view:{msg_id}")]]
            msg = await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
            await schedule_delete(msg, 15)
        except Exception as e:
            msg = await query.edit_message_text(f"❌ Error", parse_mode="MarkdownV2")
            await schedule_delete(msg, 15)


# Create singleton
advanced_handlers = AdvancedHandlers()

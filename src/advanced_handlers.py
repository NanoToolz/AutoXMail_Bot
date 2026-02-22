"""Advanced handlers for blocklist, VIP, privacy, and bot settings."""
<<<<<<< HEAD
import json
=======
>>>>>>> 8f519e51b3bf55d776dca3f2279d5275cfd38277
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from gmail_service import gmail_service
from formatter import to_tiny_caps, escape_markdown
from auto_delete import schedule_delete, DELETE_SUCCESS, DELETE_IMMEDIATE, DELETE_WARNING

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
DOMAIN_REGEX = re.compile(r'^@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

TIMER_OPTIONS = [
    ("❌ ᴏғғ", 0),
    ("⚡ 30s", 30),
    ("🕐 1ᴍ", 60),
    ("🕐 5ᴍ", 300),
    ("📅 30ᴍ", 1800),
    ("📅 1ʜ", 3600),
    ("📅 24ʜ", 86400),
]


def _timer_label(secs: int) -> str:
    """Convert seconds to human-readable label."""
    if secs == 0:
        return "Never"
    elif secs < 60:
        return f"{secs}s"
    elif secs < 3600:
        return f"{secs // 60}m"
    else:
        return f"{secs // 3600}h"


class AdvancedHandlers:
    """Handler for advanced features: blocklist, VIP, privacy, bot settings, unsubscribe."""

    # ─────────────────────────────────────────────
    # BLOCKLIST
    # ─────────────────────────────────────────────

    async def show_blocklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the blocklist with all blocked senders/domains."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id

        async with db.get_connection() as conn:
            conn.row_factory = db.aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM blocklist WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            )
            blocked = await cursor.fetchall()

        keyboard = []
        text = f"🚫 *{to_tiny_caps('Blocklist')}*\n`────────────────────────`\n\n"

        if blocked:
            text += f"*{len(blocked)}* blocked sender\\(s\\):\n\n"
            for entry in blocked:
                val = escape_markdown(entry['blocked_value'])
                text += f"• `{val}`\n"
                keyboard.append([
                    InlineKeyboardButton(
                        f"🗑️ {entry['blocked_value'][:35]}",
                        callback_data=f"blocklist_remove:{entry['id']}"
                    )
                ])
        else:
            text += "_No blocked senders yet\\._\n\n"

        text += f"\n`────────────────────────`"
        keyboard.append([InlineKeyboardButton(f"➕ {to_tiny_caps('Add Email/Domain')}", callback_data="blocklist_add")])
        keyboard.append([InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="settings")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")

    async def start_add_blocklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
<<<<<<< HEAD
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
=======
        """Ask user for email or domain to block."""
        query = update.callback_query
        await query.answer()

        context.user_data['waiting_for'] = 'blocklist_add'

        text = (
            f"🚫 *{to_tiny_caps('Block Sender')}*\n"
            f"`────────────────────────`\n\n"
            f"✍️ Send the email address or domain to block:\n\n"
            f"*Examples:*\n"
            f"`spam@example.com`\n"
            f"`@newsletters.com`\n\n"
            f"`────────────────────────`\n"
            f"⏳ _Waiting for your input\\.\\.\\._"
        )
        keyboard = [[InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="blocklist_cancel")]]
        msg = await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
        await schedule_delete(context.bot, msg.chat.id, msg.message_id, 60)

    async def add_to_blocklist_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process the user's input and add to blocklist."""
        if context.user_data.get('waiting_for') != 'blocklist_add':
            return

        user_id = update.effective_user.id
        value = update.message.text.strip()
        await update.message.delete()

        if not (EMAIL_REGEX.match(value) or DOMAIN_REGEX.match(value)):
            msg = await update.message.chat.send_message(
                f"⚠️ *{to_tiny_caps('Invalid Format')}*\n"
                f"`────────────────────────`\n"
                f"Use `user@example.com` or `@domain.com`\\.\n\n"
                f"Please try again\\.",
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 ᴄᴀɴᴄᴇʟ", callback_data="blocklist_cancel")
                ]])
            )
            await schedule_delete(context.bot, msg.chat.id, msg.message_id, DELETE_WARNING)
            return

        async with db.get_connection() as conn:
            try:
                await conn.execute(
                    "INSERT OR IGNORE INTO blocklist (user_id, blocked_value) VALUES (?, ?)",
                    (user_id, value.lower())
                )
                await conn.commit()
            except Exception as e:
                logger.error(f"Blocklist insert error: {e}")

        context.user_data.pop('waiting_for', None)

        msg = await update.message.chat.send_message(
            f"✅ *{to_tiny_caps('Blocked')}*\n"
            f"`────────────────────────`\n"
            f"`{escape_markdown(value)}` added to blocklist\\.",
            parse_mode="MarkdownV2"
        )
        await schedule_delete(context.bot, msg.chat.id, msg.message_id, DELETE_SUCCESS)

        # Refresh blocklist screen via fake callback
        context.user_data['_refresh_blocklist'] = True

    async def remove_from_blocklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove an entry from the blocklist."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        entry_id = int(query.data.split(":")[1])

        async with db.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT blocked_value FROM blocklist WHERE id = ? AND user_id = ?",
                (entry_id, user_id)
            )
            row = await cursor.fetchone()
            if row:
                await conn.execute(
                    "DELETE FROM blocklist WHERE id = ? AND user_id = ?",
                    (entry_id, user_id)
                )
                await conn.commit()

        await self.show_blocklist(update, context)

    # ─────────────────────────────────────────────
    # VIP SENDERS
    # ─────────────────────────────────────────────

    async def show_vip_senders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show VIP senders list."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id

        async with db.get_connection() as conn:
            conn.row_factory = db.aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM vip_senders WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            )
            vips = await cursor.fetchall()

        keyboard = []
        text = f"⭐ *{to_tiny_caps('VIP Senders')}*\n`────────────────────────`\n\n"

        if vips:
            text += f"*{len(vips)}* VIP sender\\(s\\) — always notified:\n\n"
            for entry in vips:
                val = escape_markdown(entry['sender_value'])
                text += f"⭐ `{val}`\n"
                keyboard.append([
                    InlineKeyboardButton(
                        f"🗑️ {entry['sender_value'][:35]}",
                        callback_data=f"vip_remove:{entry['id']}"
                    )
                ])
        else:
            text += "_No VIP senders yet\\._\n\n"
            text += "VIP senders always trigger notifications\nregardless of your push mode setting\\.\n\n"

        text += f"`────────────────────────`"
        keyboard.append([InlineKeyboardButton(f"➕ {to_tiny_caps('Add VIP Sender')}", callback_data="vip_add")])
        keyboard.append([InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="settings")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")

    async def start_add_vip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ask user for VIP sender email or domain."""
        query = update.callback_query
        await query.answer()

        context.user_data['waiting_for'] = 'vip_add'

        text = (
            f"⭐ *{to_tiny_caps('Add VIP Sender')}*\n"
            f"`────────────────────────`\n\n"
            f"✍️ Send the email address or domain:\n\n"
            f"*Examples:*\n"
            f"`boss@company.com`\n"
            f"`@hbl.com`\n\n"
            f"`────────────────────────`\n"
            f"⏳ _Waiting for your input\\.\\.\\._"
        )
        keyboard = [[InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="vip_cancel")]]
        msg = await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
        await schedule_delete(context.bot, msg.chat.id, msg.message_id, 60)

    async def add_vip_sender_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process and save VIP sender."""
        if context.user_data.get('waiting_for') != 'vip_add':
            return

        user_id = update.effective_user.id
        value = update.message.text.strip()
        await update.message.delete()

        if not (EMAIL_REGEX.match(value) or DOMAIN_REGEX.match(value)):
            msg = await update.message.chat.send_message(
                f"⚠️ *{to_tiny_caps('Invalid Format')}*\n"
                f"`────────────────────────`\n"
                f"Use `user@example.com` or `@domain.com`\\.\n\n"
                f"Please try again\\.",
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 ᴄᴀɴᴄᴇʟ", callback_data="vip_cancel")
                ]])
            )
            await schedule_delete(context.bot, msg.chat.id, msg.message_id, DELETE_WARNING)
            return

        async with db.get_connection() as conn:
            try:
                await conn.execute(
                    "INSERT OR IGNORE INTO vip_senders (user_id, sender_value) VALUES (?, ?)",
                    (user_id, value.lower())
                )
                await conn.commit()
            except Exception as e:
                logger.error(f"VIP insert error: {e}")

        context.user_data.pop('waiting_for', None)

        msg = await update.message.chat.send_message(
            f"✅ *{to_tiny_caps('VIP Added')}*\n"
            f"`────────────────────────`\n"
            f"⭐ `{escape_markdown(value)}` is now a VIP sender\\.",
            parse_mode="MarkdownV2"
        )
        await schedule_delete(context.bot, msg.chat.id, msg.message_id, DELETE_SUCCESS)

    async def remove_vip_sender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove a VIP sender."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        entry_id = int(query.data.split(":")[1])

        async with db.get_connection() as conn:
            await conn.execute(
                "DELETE FROM vip_senders WHERE id = ? AND user_id = ?",
                (entry_id, user_id)
            )
            await conn.commit()

        await self.show_vip_senders(update, context)

    # ─────────────────────────────────────────────
    # PRIVACY SETTINGS
    # ─────────────────────────────────────────────

    async def show_privacy_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show global auto-delete timer settings."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id

        async with db.get_connection() as conn:
            conn.row_factory = db.aiosqlite.Row
            cursor = await conn.execute(
                "SELECT global_auto_delete_secs FROM privacy_settings WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            current_secs = row['global_auto_delete_secs'] if row else 0

        text = (
            f"🔒 *{to_tiny_caps('Privacy Settings')}*\n"
            f"`────────────────────────`\n\n"
            f"*{to_tiny_caps('Global Auto-Delete')}*\n"
            f"Email notifications auto\\-delete after:\n\n"
            f"Current: *{escape_markdown(_timer_label(current_secs))}*\n\n"
            f"`────────────────────────`"
        )

        # Build timer buttons (2 per row), mark current with ✅
        keyboard = []
        row_buttons = []
        for label, secs in TIMER_OPTIONS:
            display = f"✅ {label}" if secs == current_secs else label
            row_buttons.append(InlineKeyboardButton(display, callback_data=f"privacy_set:{secs}"))
            if len(row_buttons) == 2:
                keyboard.append(row_buttons)
                row_buttons = []
        if row_buttons:
            keyboard.append(row_buttons)

        keyboard.append([InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="settings")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")

    async def set_privacy_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Save the selected global auto-delete timer."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        secs = int(query.data.split(":")[1])

        async with db.get_connection() as conn:
            await conn.execute(
                "INSERT OR REPLACE INTO privacy_settings (user_id, global_auto_delete_secs) VALUES (?, ?)",
                (user_id, secs)
            )
            await conn.commit()

        await self.show_privacy_settings(update, context)

    # ─────────────────────────────────────────────
    # BOT SETTINGS
    # ─────────────────────────────────────────────

    async def show_bot_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot settings screen."""
        query = update.callback_query
        await query.answer()

        text = (
            f"🤖 *{to_tiny_caps('Bot Settings')}*\n"
            f"`────────────────────────`\n\n"
            f"Customize your AutoXMail bot\\.\n\n"
            f"`────────────────────────`"
        )
        keyboard = [
            [InlineKeyboardButton(f"🖼️ {to_tiny_caps('Change Profile Pic')}", callback_data="bot_change_photo")],
            [InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="settings")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")

    async def start_change_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ask user to send a photo for bot profile picture."""
        query = update.callback_query
        await query.answer()

        context.user_data['waiting_for'] = 'bot_photo'

        text = (
            f"🖼️ *{to_tiny_caps('Change Profile Pic')}*\n"
            f"`────────────────────────`\n\n"
            f"📸 Send the photo to use as bot profile picture\\.\n\n"
            f"⚠️ _Your photo will be deleted from chat immediately\\._\n\n"
            f"`────────────────────────`\n"
            f"⏳ _Waiting for photo\\.\\.\\._"
        )
        keyboard = [[InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="bot_settings")]]
        msg = await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
        await schedule_delete(context.bot, msg.chat.id, msg.message_id, 120)

    async def change_bot_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle received photo and set as bot profile picture."""
        if context.user_data.get('waiting_for') != 'bot_photo':
            return
        if not update.message.photo:
            return

        await update.message.delete()

>>>>>>> 8f519e51b3bf55d776dca3f2279d5275cfd38277
        try:
            photo = update.message.photo[-1]
            file = await photo.get_file()
            photo_bytes = await file.download_as_bytearray()
<<<<<<< HEAD
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
=======
            await context.bot.set_my_photo(photo=bytes(photo_bytes))
            context.user_data.pop('waiting_for', None)

            msg = await update.effective_chat.send_message(
                f"✅ *{to_tiny_caps('Profile Pic Updated')}*\n"
                f"`────────────────────────`\n"
                f"Bot profile picture changed successfully\\!",
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🔙 {to_tiny_caps('Bot Settings')}", callback_data="bot_settings")
                ]])
            )
            await schedule_delete(context.bot, msg.chat.id, msg.message_id, DELETE_SUCCESS)

        except Exception as e:
            logger.error(f"Error setting bot photo: {e}")
            msg = await update.effective_chat.send_message(
                f"❌ *{to_tiny_caps('Error')}*\n"
                f"`────────────────────────`\n"
                f"Failed to update profile picture\\.\n"
                f"`{escape_markdown(str(e)[:100])}`",
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="bot_settings")
                ]])
            )
            await schedule_delete(context.bot, msg.chat.id, msg.message_id, DELETE_WARNING)

    # ─────────────────────────────────────────────
    # UNSUBSCRIBE
    # ─────────────────────────────────────────────

    async def confirm_unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show unsubscribe confirmation screen."""
        query = update.callback_query
        await query.answer()

        parts = query.data.split(":")
        account_id = parts[1]
        message_id = parts[2]

        context.user_data['unsub_account_id'] = account_id
        context.user_data['unsub_message_id'] = message_id

        text = (
            f"⚠️ *{to_tiny_caps('Confirm Unsubscribe')}*\n"
            f"`────────────────────────`\n\n"
            f"This will:\n"
            f"• Unsubscribe from this mailing list\n"
            f"• Add sender to your blocklist\n\n"
            f"Are you sure\\?\n\n"
            f"`────────────────────────`"
        )
        keyboard = [
            [
                InlineKeyboardButton(f"✅ {to_tiny_caps('Yes, Unsubscribe')}", callback_data=f"unsub_confirm:{account_id}:{message_id}"),
                InlineKeyboardButton(f"❌ {to_tiny_caps('Cancel')}", callback_data="inbox"),
            ]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")

    async def execute_unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Execute unsubscribe and add sender to blocklist."""
        query = update.callback_query
        await query.answer()

        parts = query.data.split(":")
        account_id = int(parts[1])
        message_id = parts[2]
        user_id = update.effective_user.id

        try:
            service = await gmail_service.get_service(user_id, account_id)
            result = await gmail_service.unsubscribe_email(service, message_id)

            msg_data = await gmail_service.get_message(service, message_id)
            headers = {h['name']: h['value'] for h in msg_data.get('payload', {}).get('headers', [])}
            sender_email = re.search(r'[\w.+\-]+@[\w.\-]+', headers.get('From', ''))
            sender = sender_email.group(0).lower() if sender_email else None

            if sender:
                async with db.get_connection() as conn:
                    await conn.execute(
                        "INSERT OR IGNORE INTO blocklist (user_id, blocked_value) VALUES (?, ?)",
                        (user_id, sender)
                    )
                    await conn.commit()

            if result:
                status_text = (
                    f"✅ *{to_tiny_caps('Unsubscribed')}*\n"
                    f"`────────────────────────`\n"
                    f"Successfully unsubscribed\\!\n"
                )
                if sender:
                    status_text += f"`{escape_markdown(sender)}` added to blocklist\\."
            else:
                status_text = (
                    f"⚠️ *{to_tiny_caps('No Unsubscribe Link')}*\n"
                    f"`────────────────────────`\n"
                    f"No unsubscribe link found in this email\\.\n"
                )
                if sender:
                    status_text += f"Sender `{escape_markdown(sender)}` added to blocklist anyway\\."

        except Exception as e:
            logger.error(f"Unsubscribe error: {e}")
            status_text = (
                f"❌ *{to_tiny_caps('Error')}*\n"
                f"`────────────────────────`\n"
                f"Unsubscribe failed\\: `{escape_markdown(str(e)[:80])}`"
            )

        keyboard = [[InlineKeyboardButton(f"🔙 {to_tiny_caps('Back to Inbox')}", callback_data="inbox")]]
        msg = await query.edit_message_text(
            status_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="MarkdownV2"
        )
        await schedule_delete(context.bot, msg.chat.id, msg.message_id, DELETE_SUCCESS)

    # ─────────────────────────────────────────────
    # PER-ACCOUNT AUTO-DELETE
    # ─────────────────────────────────────────────

    async def show_account_auto_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show per-account auto-delete timer options."""
        query = update.callback_query
        await query.answer()

        parts = query.data.split(":")
        account_id = int(parts[1])

        async with db.get_connection() as conn:
            conn.row_factory = db.aiosqlite.Row
            cursor = await conn.execute(
                "SELECT email, auto_delete_secs FROM gmail_accounts WHERE id = ?",
                (account_id,)
            )
            account = await cursor.fetchone()

        if not account:
            await query.answer("Account not found.", show_alert=True)
            return

        current_secs = account['auto_delete_secs'] or 0
        email = escape_markdown(account['email'])

        text = (
            f"⏱️ *{to_tiny_caps('Auto-Delete Override')}*\n"
            f"`────────────────────────`\n\n"
            f"Account: `{email}`\n\n"
            f"Notifications from this account\nauto\\-delete after:\n\n"
            f"Current: *{escape_markdown(_timer_label(current_secs))}*\n"
            f"\\(0 \\= use global setting\\)\n\n"
            f"`────────────────────────`"
        )

        keyboard = []
        row_buttons = []
        for label, secs in TIMER_OPTIONS:
            display = f"✅ {label}" if secs == current_secs else label
            row_buttons.append(InlineKeyboardButton(
                display,
                callback_data=f"acc_autodel_set:{account_id}:{secs}"
            ))
            if len(row_buttons) == 2:
                keyboard.append(row_buttons)
                row_buttons = []
        if row_buttons:
            keyboard.append(row_buttons)

        keyboard.append([InlineKeyboardButton(
            f"🔙 {to_tiny_caps('Back')}",
            callback_data=f"account_manage:{account_id}"
        )])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")

    async def set_account_auto_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Save per-account auto-delete timer."""
        query = update.callback_query
        await query.answer()

        parts = query.data.split(":")
        account_id = int(parts[1])
        secs = int(parts[2])

        async with db.get_connection() as conn:
            await conn.execute(
                "UPDATE gmail_accounts SET auto_delete_secs = ? WHERE id = ?",
                (secs, account_id)
            )
            await conn.commit()

        # Refresh the screen with updated value
        query.data = f"acc_autodel:{account_id}"
        await self.show_account_auto_delete(update, context)


# Singleton instance
>>>>>>> 8f519e51b3bf55d776dca3f2279d5275cfd38277
advanced_handlers = AdvancedHandlers()

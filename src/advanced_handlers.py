"""Advanced handlers for blocklist, VIP, privacy, and bot settings."""
import re
import logging
import aiosqlite
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

    async def show_blocklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the blocklist with all blocked senders/domains."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id

        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
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
        keyboard = [[InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="blocklist")]]
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
                    InlineKeyboardButton("🔙 ᴄᴀɴᴄᴇʟ", callback_data="blocklist")
                ]])
            )
            await schedule_delete(context.bot, msg.chat.id, msg.message_id, DELETE_WARNING)
            return

        async with aiosqlite.connect(db.db_path) as conn:
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

    async def remove_from_blocklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove an entry from the blocklist."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        entry_id = int(query.data.split(":")[1])

        async with aiosqlite.connect(db.db_path) as conn:
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

    async def show_vip_senders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show VIP senders list."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id

        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
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
        keyboard = [[InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="vip_senders")]]
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
                    InlineKeyboardButton("🔙 ᴄᴀɴᴄᴇʟ", callback_data="vip_senders")
                ]])
            )
            await schedule_delete(context.bot, msg.chat.id, msg.message_id, DELETE_WARNING)
            return

        async with aiosqlite.connect(db.db_path) as conn:
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

        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute(
                "DELETE FROM vip_senders WHERE id = ? AND user_id = ?",
                (entry_id, user_id)
            )
            await conn.commit()

        await self.show_vip_senders(update, context)

    async def show_privacy_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show global auto-delete timer settings."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id

        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
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

        keyboard = []
        row_buttons = []
        for label, secs in TIMER_OPTIONS:
            display = f"✅ {label}" if secs == current_secs else label
            row_buttons.append(InlineKeyboardButton(display, callback_data=f"privacy_timer:{secs}"))
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

        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute(
                "INSERT OR REPLACE INTO privacy_settings (user_id, global_auto_delete_secs) VALUES (?, ?)",
                (user_id, secs)
            )
            await conn.commit()

        await self.show_privacy_settings(update, context)


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

        try:
            photo = update.message.photo[-1]
            file = await photo.get_file()
            photo_bytes = await file.download_as_bytearray()
            await context.bot.set_chat_photo(chat_id=update.effective_chat.id, photo=bytes(photo_bytes))
            context.user_data.pop('waiting_for', None)

            msg = await update.effective_chat.send_message(
                f"✅ *{to_tiny_caps('Profile Pic Updated')}*\n"
                f"`────────────────────────`\n"
                f"Bot profile picture changed successfully\\!",
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="bot_settings")
                ]])
            )
            await schedule_delete(context.bot, msg.chat.id, msg.message_id, DELETE_SUCCESS)
        except Exception as e:
            logger.error(f"Photo change error: {e}")
            msg = await update.effective_chat.send_message(
                f"❌ *{to_tiny_caps('Failed')}*\n"
                f"`────────────────────────`\n"
                f"Could not update profile picture\\.",
                parse_mode="MarkdownV2"
            )
            await schedule_delete(context.bot, msg.chat.id, msg.message_id, DELETE_WARNING)

    async def show_account_auto_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show per-account auto-delete timer settings."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        account_id = int(query.data.split(":")[1])

        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT email, auto_delete_secs FROM gmail_accounts WHERE id = ? AND user_id = ?",
                (account_id, user_id)
            )
            account = await cursor.fetchone()

        if not account:
            await query.answer("❌ Account not found", show_alert=True)
            return

        current_secs = account['auto_delete_secs'] or 0
        email = escape_markdown(account['email'])

        text = (
            f"⏱️ *{to_tiny_caps('Auto-Delete Timer')}*\n"
            f"`────────────────────────`\n\n"
            f"*Account:* `{email}`\n\n"
            f"Notifications for this account auto\\-delete after:\n\n"
            f"Current: *{escape_markdown(_timer_label(current_secs))}*\n\n"
            f"`────────────────────────`"
        )

        keyboard = []
        row_buttons = []
        for label, secs in TIMER_OPTIONS:
            display = f"✅ {label}" if secs == current_secs else label
            row_buttons.append(InlineKeyboardButton(display, callback_data=f"account_timer:{account_id}:{secs}"))
            if len(row_buttons) == 2:
                keyboard.append(row_buttons)
                row_buttons = []
        if row_buttons:
            keyboard.append(row_buttons)

        keyboard.append([InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="accounts")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")

    async def set_account_auto_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Save the selected per-account auto-delete timer."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        parts = query.data.split(":")
        account_id = int(parts[1])
        secs = int(parts[2])

        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute(
                "UPDATE gmail_accounts SET auto_delete_secs = ? WHERE id = ? AND user_id = ?",
                (secs, account_id, user_id)
            )
            await conn.commit()

        await self.show_account_auto_delete(update, context)

    async def confirm_unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show confirmation dialog for unsubscribe action."""
        query = update.callback_query
        await query.answer()
        
        parts = query.data.split(":")
        account_id = parts[2]
        msg_id = parts[3]

        text = (
            f"⚠️ *{to_tiny_caps('Unsubscribe Confirmation')}*\n"
            f"`────────────────────────`\n\n"
            f"This will:\n"
            f"1\\. Send unsubscribe request to sender\n"
            f"2\\. Add sender to your blocklist\n\n"
            f"Continue?\n\n"
            f"`────────────────────────`"
        )
        keyboard = [
            [
                InlineKeyboardButton(f"✅ {to_tiny_caps('Yes, Unsubscribe')}", callback_data=f"email:unsub_confirm:{account_id}:{msg_id}"),
                InlineKeyboardButton(f"❌ {to_tiny_caps('Cancel')}", callback_data=f"view_msg:{account_id}:{msg_id}")
            ]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")

    async def execute_unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Execute the unsubscribe action and add sender to blocklist."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        
        parts = query.data.split(":")
        account_id = int(parts[2])
        msg_id = parts[3]

        try:
            # Fixed: Pass account_id directly, not service object
            message = await gmail_service.get_message(account_id, msg_id)
            
            sender = message.get('from', '')
            sender_match = re.search(r'<(.+?)>', sender)
            sender_email = sender_match.group(1) if sender_match else sender.strip()

            # Fixed: Pass account_id directly, not service object
            success = await gmail_service.unsubscribe_email(account_id, msg_id)

            async with aiosqlite.connect(db.db_path) as conn:
                try:
                    await conn.execute(
                        "INSERT OR IGNORE INTO blocklist (user_id, blocked_value) VALUES (?, ?)",
                        (user_id, sender_email.lower())
                    )
                    await conn.commit()
                except Exception as e:
                    logger.error(f"Blocklist insert error during unsubscribe: {e}")

            if success:
                text = (
                    f"✅ *{to_tiny_caps('Unsubscribed')}*\n"
                    f"`────────────────────────`\n\n"
                    f"Unsubscribe request sent\\!\n"
                    f"Sender added to blocklist\\.\n\n"
                    f"`────────────────────────`"
                )
            else:
                text = (
                    f"⚠️ *{to_tiny_caps('No Unsubscribe Link')}*\n"
                    f"`────────────────────────`\n\n"
                    f"No unsubscribe link found in email\\.\n"
                    f"Sender added to blocklist\\.\n\n"
                    f"`────────────────────────`"
                )

            keyboard = [[InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data=f"view_msg:{account_id}:{msg_id}")]]
            msg = await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
            await schedule_delete(context.bot, msg.chat.id, msg.message_id, DELETE_SUCCESS)

        except Exception as e:
            logger.error(f"Unsubscribe error: {e}")
            text = (
                f"❌ *{to_tiny_caps('Error')}*\n"
                f"`────────────────────────`\n\n"
                f"Failed to unsubscribe\\.\n"
                f"Please try again later\\.\n\n"
                f"`────────────────────────`"
            )
            keyboard = [[InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data=f"view_msg:{account_id}:{msg_id}")]]
            msg = await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
            await schedule_delete(context.bot, msg.chat.id, msg.message_id, DELETE_WARNING)


advanced_handlers = AdvancedHandlers()

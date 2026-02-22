"""Push notification service with webhook server."""
import base64
import json
import asyncio
import logging
from aiohttp import web
from telegram import Bot
from database import db
from gmail_service import gmail_service
from formatter import to_tiny_caps, escape_markdown
from utils import parse_email_headers, get_message_body, extract_otp
from auto_delete import schedule_delete
import config

logger = logging.getLogger(__name__)


class PushService:
    """Gmail Push notification service."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.app = None
        self.runner = None
    
    async def handle_push_notification(self, request):
        """Handle Gmail Pub/Sub push notification."""
        try:
            data = await request.json()
            
            # Extract message data
            message = data.get('message', {})
            encoded_data = message.get('data', '')
            
            if not encoded_data:
                return web.Response(status=200)
            
            # Decode base64 data
            decoded = base64.b64decode(encoded_data).decode('utf-8')
            notification_data = json.loads(decoded)
            
            email_address = notification_data.get('emailAddress')
            history_id = notification_data.get('historyId')
            
            if not email_address or not history_id:
                return web.Response(status=200)
            
            logger.info(f"Push notification for {email_address}, historyId: {history_id}")
            
            # Find user and account in database
            async with db.db_path as conn:
                conn.row_factory = db.aiosqlite.Row
                cursor = await conn.execute(
                    "SELECT ga.*, u.user_id FROM gmail_accounts ga "
                    "JOIN users u ON ga.user_id = u.user_id "
                    "WHERE ga.email = ? AND ga.is_active = 1",
                    (email_address,)
                )
                account = await cursor.fetchone()
            
            if not account:
                logger.warning(f"No account found for {email_address}")
                return web.Response(status=200)
            
            account_id = account['id']
            user_id = account['user_id']
            last_history_id = account.get('last_history_id', history_id)
            
            # Get new messages from history
            try:
                new_message_ids = await gmail_service.get_history(account_id, last_history_id)
            except Exception as e:
                logger.error(f"Failed to get history: {e}")
                new_message_ids = []
            
            # Get notification settings
            settings = await db.get_notification_settings(user_id)
            push_mode = settings.get('push_mode', 'all')  # off, otp, vip, all
            
            # Get blocklist
            async with db.db_path as conn:
                cursor = await conn.execute(
                    "SELECT blocked_value FROM blocklist WHERE user_id = ?",
                    (user_id,)
                )
                blocklist = [row[0] for row in await cursor.fetchall()]
            
            # Get VIP senders
            async with db.db_path as conn:
                cursor = await conn.execute(
                    "SELECT sender_value FROM vip_senders WHERE user_id = ?",
                    (user_id,)
                )
                vip_senders = [row[0] for row in await cursor.fetchall()]
            
            # Process each new message
            for msg_id in new_message_ids:
                try:
                    # Fetch message
                    message = await gmail_service.get_message(account_id, msg_id)
                    subject, sender, date = parse_email_headers(message)
                    body = get_message_body(message['payload'])
                    
                    # Check blocklist
                    is_blocked = any(
                        blocked in sender for blocked in blocklist
                    )
                    if is_blocked:
                        logger.info(f"Blocked sender: {sender}")
                        continue
                    
                    # Check if VIP
                    is_vip = any(
                        vip in sender for vip in vip_senders
                    )
                    
                    # Determine if should send notification
                    should_send = False
                    
                    if is_vip:
                        # VIP always sends
                        should_send = True
                    elif push_mode == 'off':
                        should_send = False
                    elif push_mode == 'otp':
                        # Only send if OTP detected
                        otp = extract_otp(body)
                        should_send = bool(otp)
                    elif push_mode == 'vip':
                        # Only VIP (already handled above)
                        should_send = False
                    elif push_mode == 'all':
                        should_send = True
                    
                    if not should_send:
                        continue
                    
                    # Format notification
                    otp = extract_otp(body)
                    
                    text = (
                        f"📧 *{to_tiny_caps('New Email')}*\n"
                        f"`────────────────────────`\n\n"
                        f"*{to_tiny_caps('From')}:* {escape_markdown(sender[:50])}\n"
                        f"*{to_tiny_caps('Subject')}:* {escape_markdown(subject[:50])}\n"
                    )
                    
                    if otp:
                        text += f"\n🔑 *{to_tiny_caps('OTP')}:* `{otp}`\n"
                    
                    text += f"\n*{to_tiny_caps('Preview')}:*\n{escape_markdown(body[:200])}"
                    
                    # Send to Telegram
                    msg = await self.bot.send_message(
                        chat_id=user_id,
                        text=text,
                        parse_mode='MarkdownV2'
                    )
                    
                    # Get auto-delete timer
                    # Check account-specific first
                    account_timer = account.get('auto_delete_secs', 0)
                    
                    if account_timer > 0:
                        delete_delay = account_timer
                    else:
                        # Use global privacy settings
                        async with db.db_path as conn:
                            cursor = await conn.execute(
                                "SELECT global_auto_delete_secs FROM privacy_settings WHERE user_id = ?",
                                (user_id,)
                            )
                            row = await cursor.fetchone()
                            delete_delay = row[0] if row else 0
                    
                    # Schedule auto-delete
                    if delete_delay > 0:
                        asyncio.create_task(schedule_delete(
                            self.bot,
                            user_id,
                            msg.message_id,
                            delete_delay
                        ))
                    
                    logger.info(f"Sent push notification to user {user_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to process message {msg_id}: {e}")
                    continue
            
            # Update last history ID
            async with db.db_path as conn:
                await conn.execute(
                    "UPDATE gmail_accounts SET last_history_id = ? WHERE id = ?",
                    (history_id, account_id)
                )
                await conn.commit()
            
            return web.Response(status=200)
            
        except Exception as e:
            logger.error(f"Push notification error: {e}")
            return web.Response(status=500)
    
    async def handle_oauth_callback(self, request):
        """Handle OAuth2 callback."""
        try:
            # Get code and state from query params
            code = request.query.get('code')
            state = request.query.get('state')
            
            if not code or not state:
                return web.Response(text="Missing code or state", status=400)
            
            # Find session in database
            session = await db.get_session(state)
            
            if not session:
                return web.Response(text="Invalid or expired session", status=400)
            
            user_id = session['user_id']
            session_data = session.get('data', {})
            
            # Exchange code for token (handled in oauth_handler)
            # This is a simplified version - full implementation in oauth_handler.py
            
            # Send success message to user
            await self.bot.send_message(
                chat_id=user_id,
                text=(
                    f"✅ *{to_tiny_caps('OAuth Successful')}*\n\n"
                    f"Please complete the setup in the bot\\."
                ),
                parse_mode='MarkdownV2'
            )
            
            return web.Response(text="Authorization successful! You can close this window.", status=200)
            
        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            return web.Response(text="Authorization failed", status=500)
    
    async def handle_health(self, request):
        """Health check endpoint."""
        return web.Response(text="OK", status=200)
    
    async def start_server(self, host='0.0.0.0', port=8080):
        """Start webhook server."""
        self.app = web.Application()
        
        # Add routes
        self.app.router.add_post('/webhook/push', self.handle_push_notification)
        self.app.router.add_get('/oauth/callback', self.handle_oauth_callback)
        self.app.router.add_get('/health', self.handle_health)
        
        # Start server
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        site = web.TCPSite(self.runner, host, port)
        await site.start()
        
        logger.info(f"Webhook server started on {host}:{port}")
    
    async def stop_server(self):
        """Stop webhook server."""
        if self.runner:
            await self.runner.cleanup()
            logger.info("Webhook server stopped")


# Global instance (initialized in main.py)
push_service = None

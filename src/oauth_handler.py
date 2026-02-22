"""OAuth flow handler for adding Gmail accounts."""
import json
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from google_auth_oauthlib.flow import Flow
from database import db
from crypto import encrypt_credentials, encrypt_token, decrypt_token
from formatter import to_tiny_caps, escape_markdown
import config
import asyncio
from auto_delete import schedule_delete, DELETE_IMMEDIATE


class OAuthHandler:
    """Handle Gmail OAuth flow via Telegram."""
    
    def __init__(self):
        self.flows = {}  # Store active OAuth flows
    
    async def force_add_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Force add account despite warning."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        force_data = context.user_data.get('oauth_force_data')
        
        if not force_data:
            await query.edit_message_text(
                f"❌ {escape_markdown('Session expired. Please try again.')}",
                parse_mode='MarkdownV2'
            )
            return
        
        try:
            email = force_data['email']
            credentials_json = force_data['credentials_json']
            token_info = force_data['token_info']
            
            # Encrypt credentials and token
            credentials_enc, _ = encrypt_credentials(credentials_json, user_id)
            token_enc = encrypt_token(json.dumps(token_info), user_id)
            
            # Save to database
            await db.add_gmail_account(user_id, email, credentials_enc, token_enc)
            
            # Cleanup
            context.user_data.pop('oauth_force_data', None)
            
            # Success message
            text = (
                f"✅ *{to_tiny_caps('Account Added Successfully')}\\!*\n"
                f"`────────────────────────`\n\n"
                f"📧 Email: {escape_markdown(email)}\n\n"
                f"Your Gmail account is now connected\\.\n"
                f"All credentials are encrypted and stored securely\\."
            )
            
            keyboard = [[InlineKeyboardButton(f"📬 {to_tiny_caps('View Inbox')}", callback_data="inbox")]]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ {escape_markdown(f'Failed to add account: {str(e)}')}",
                parse_mode='MarkdownV2'
            )
    
    async def start_oauth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start OAuth flow for adding Gmail account."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        # Check account limit
        accounts = await db.get_gmail_accounts(user_id)
        if len(accounts) >= config.MAX_ACCOUNTS_PER_USER:
            keyboard = [
                [InlineKeyboardButton(f"⚙️ {to_tiny_caps('Manage Accounts')}", callback_data="accounts")],
                [InlineKeyboardButton(f"🔙 {to_tiny_caps('Back')}", callback_data="accounts")]
            ]
            
            await query.edit_message_text(
                f"⚠️ *{to_tiny_caps('Limit Reached')}*\n"
                f"`────────────────────────`\n\n"
                f"Maximum 75 Gmail accounts allowed\\.\n\n"
                f"Remove an existing account to add a new one\\.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
            return
        
        # Instructions
        text = (
            f"➕ *{to_tiny_caps('Add Gmail Account')}*\n"
            f"`────────────────────────`\n\n"
            f"*{to_tiny_caps('Step 1')}:* Upload your credentials\\.json file\n\n"
            f"To get credentials\\.json:\n"
            f"1\\. Go to Google Cloud Console\n"
            f"2\\. Create OAuth 2\\.0 Client ID\n"
            f"3\\. Download credentials\\.json\n"
            f"4\\. Send the file here\n\n"
            f"⚠️ Your credentials will be encrypted and stored securely\\."
        )
        
        keyboard = [[InlineKeyboardButton(f"❌ {to_tiny_caps('Cancel')}", callback_data="accounts")]]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
        
        # Set state
        context.user_data['state'] = 'waiting_credentials'
    
    async def handle_credentials(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle uploaded credentials.json."""
        if context.user_data.get('state') != 'waiting_credentials':
            return
        
        # DELETE CREDENTIALS FILE IMMEDIATELY
        try:
            await update.message.delete()
        except:
            pass
        
        user_id = update.effective_user.id
        
        # Get document
        document = update.message.document
        if not document or not document.file_name.endswith('.json'):
            msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ {escape_markdown('Please send a valid credentials.json file.')}",
                parse_mode='MarkdownV2'
            )
            # Auto-delete error message
            asyncio.create_task(schedule_delete(context.bot, update.effective_chat.id, msg.message_id, 5))
            return
        
        try:
            # Download file
            file = await context.bot.get_file(document.file_id)
            credentials_data = await file.download_as_bytearray()
            credentials_json = credentials_data.decode('utf-8')
            
            # Validate JSON
            creds_info = json.loads(credentials_json)
            if 'installed' not in creds_info and 'web' not in creds_info:
                raise ValueError("Invalid credentials format")
            
            # Create OAuth flow
            session_id = str(uuid.uuid4())
            
            flow = Flow.from_client_config(
                creds_info,
                scopes=config.SCOPES,
                redirect_uri='http://localhost'
            )
            
            auth_url, state = flow.authorization_url(
                prompt='consent',
                access_type='offline'
            )
            
            # Store flow and credentials
            self.flows[session_id] = {
                'flow': flow,
                'credentials_json': credentials_json,
                'user_id': user_id
            }
            
            # Save session
            await db.create_session(
                session_id,
                user_id,
                'oauth_pending',
                {'state': state}
            )
            
            # Send auth URL
            text = (
                f"✅ *{to_tiny_caps('Credentials Received')}*\n"
                f"`────────────────────────`\n\n"
                f"*{to_tiny_caps('Step 2')}:* Authorize Gmail Access\n\n"
                f"1\\. Click the link below\n"
                f"2\\. Sign in to your Gmail account\n"
                f"3\\. Grant permissions\n"
                f"4\\. Copy the ENTIRE redirect URL\n"
                f"5\\. Send it back here\n\n"
                f"[🔗 Click here to authorize]({auth_url})\n\n"
                f"After authorizing, send the URL that starts with:\n"
                f"`http://localhost/?code=...`"
            )
            
            keyboard = [[InlineKeyboardButton(f"❌ {to_tiny_caps('Cancel')}", callback_data="accounts")]]
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
            
            # Update state
            context.user_data['state'] = 'waiting_auth_code'
            context.user_data['session_id'] = session_id
            
        except Exception as e:
            msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    f"❌ {escape_markdown(f'Error processing credentials: {str(e)}')}\n\n"
                    f"Please make sure you uploaded a valid credentials\\.json file\\."
                ),
                parse_mode='MarkdownV2'
            )
            # Auto-delete error message
            asyncio.create_task(schedule_delete(context.bot, update.effective_chat.id, msg.message_id, 10))
            context.user_data['state'] = None
    
    async def handle_auth_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle authorization code/URL."""
        if context.user_data.get('state') != 'waiting_auth_code':
            return
        
        user_id = update.effective_user.id
        session_id = context.user_data.get('session_id')
        
        if not session_id or session_id not in self.flows:
            await update.message.reply_text(
                "❌ Session expired. Please start over with /start"
            )
            context.user_data['state'] = None
            return
        
        response = update.message.text.strip()
        
        await update.message.reply_text("⏳ Processing authorization...")
        
        try:
            # Extract code from URL
            if response.startswith('http://localhost'):
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(response)
                code = parse_qs(parsed.query).get('code', [None])[0]
                if not code:
                    raise ValueError("No code found in URL")
            else:
                code = response
            
            # Get flow
            flow_data = self.flows[session_id]
            flow = flow_data['flow']
            credentials_json = flow_data['credentials_json']
            
            # Exchange code for token
            flow.fetch_token(code=code)
            creds = flow.credentials
            
            # Get email address
            from googleapiclient.discovery import build
            service = build('gmail', 'v1', credentials=creds)
            profile = service.users().getProfile(userId='me').execute()
            email = profile['emailAddress']
            
            # Extract API project email from credentials
            creds_info = json.loads(credentials_json)
            api_project_email = None
            if 'installed' in creds_info:
                api_project_email = creds_info['installed'].get('client_email')
            elif 'web' in creds_info:
                api_project_email = creds_info['web'].get('client_email')
            
            # Check if user is trying to add API project email
            if api_project_email and email == api_project_email:
                # Show warning
                keyboard = [
                    [
                        InlineKeyboardButton(
                            f"⚠️ {to_tiny_caps('Add Anyway')}",
                            callback_data=f"oauth_force_add:{session_id}"
                        ),
                        InlineKeyboardButton(
                            f"🔙 {to_tiny_caps('Cancel')}",
                            callback_data="accounts"
                        )
                    ]
                ]
                
                text = (
                    f"⚠️ *{to_tiny_caps('Warning')}*\n"
                    f"`────────────────────────`\n\n"
                    f"You're trying to add the API project email\\.\n\n"
                    f"This is usually not what you want\\. "
                    f"Make sure you authorized the correct Gmail account\\.\n\n"
                    f"Continue anyway?"
                )
                
                await update.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='MarkdownV2'
                )
                
                # Store data for force add
                context.user_data['oauth_force_data'] = {
                    'email': email,
                    'credentials_json': credentials_json,
                    'token_info': token_info
                }
                
                return
            
            # Prepare token info
            token_info = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes
            }
            
            # Encrypt credentials and token
            credentials_enc, _ = encrypt_credentials(credentials_json, user_id)
            token_enc = encrypt_token(json.dumps(token_info), user_id)
            
            # Save to database
            await db.add_gmail_account(user_id, email, credentials_enc, token_enc)
            
            # Cleanup
            del self.flows[session_id]
            await db.delete_session(session_id)
            context.user_data['state'] = None
            
            # Success message
            text = (
                f"✅ *{to_tiny_caps('Account Added Successfully')}\\!*\n"
                f"`────────────────────────`\n\n"
                f"📧 Email: {escape_markdown(email)}\n\n"
                f"Your Gmail account is now connected\\.\n"
                f"All credentials are encrypted and stored securely\\."
            )
            
            keyboard = [[InlineKeyboardButton(f"📬 {to_tiny_caps('View Inbox')}", callback_data="inbox")]]
            
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ {escape_markdown(f'Authorization failed: {str(e)}')}\n\n"
                f"Please make sure you:\n"
                f"1\\. Copied the entire URL correctly\n"
                f"2\\. Authorized the correct account\n\n"
                f"Try again with /start",
                parse_mode='MarkdownV2'
            )
            context.user_data['state'] = None


# Global OAuth handler
oauth_handler = OAuthHandler()

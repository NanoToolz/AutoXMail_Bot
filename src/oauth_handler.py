"""OAuth flow handler for adding Gmail accounts."""
import json
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from google_auth_oauthlib.flow import Flow
from database import db
from crypto import crypto
import config


class OAuthHandler:
    """Handle Gmail OAuth flow via Telegram."""
    
    def __init__(self):
        self.flows = {}  # Store active OAuth flows
    
    async def start_oauth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start OAuth flow for adding Gmail account."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        # Check account limit
        accounts = await db.get_gmail_accounts(user_id)
        if len(accounts) >= config.MAX_ACCOUNTS_PER_USER:
            await query.edit_message_text(
                f"❌ *Account Limit Reached*\n\n"
                f"You can add maximum {config.MAX_ACCOUNTS_PER_USER} accounts.\n"
                f"Remove an account first to add a new one.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data="accounts")
                ]]),
                parse_mode='Markdown'
            )
            return
        
        # Instructions
        text = (
            "➕ *Add Gmail Account*\n\n"
            "*Step 1:* Upload your credentials.json file\n\n"
            "To get credentials.json:\n"
            "1. Go to Google Cloud Console\n"
            "2. Create OAuth 2.0 Client ID\n"
            "3. Download credentials.json\n"
            "4. Send the file here\n\n"
            "⚠️ Your credentials will be encrypted and stored securely."
        )
        
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="accounts")]]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        # Set state
        context.user_data['state'] = 'waiting_credentials'
    
    async def handle_credentials(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle uploaded credentials.json."""
        if context.user_data.get('state') != 'waiting_credentials':
            return
        
        user_id = update.effective_user.id
        
        # Get document
        document = update.message.document
        if not document or not document.file_name.endswith('.json'):
            await update.message.reply_text(
                "❌ Please send a valid credentials.json file."
            )
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
                "✅ *Credentials Received*\n\n"
                "*Step 2:* Authorize Gmail Access\n\n"
                "1. Click the link below\n"
                "2. Sign in to your Gmail account\n"
                "3. Grant permissions\n"
                "4. Copy the ENTIRE redirect URL\n"
                "5. Send it back here\n\n"
                f"[🔗 Click here to authorize]({auth_url})\n\n"
                "After authorizing, send the URL that starts with:\n"
                "`http://localhost/?code=...`"
            )
            
            keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="accounts")]]
            
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            # Update state
            context.user_data['state'] = 'waiting_auth_code'
            context.user_data['session_id'] = session_id
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Error processing credentials: {str(e)}\n\n"
                "Please make sure you uploaded a valid credentials.json file."
            )
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
            credentials_enc = crypto.encrypt_credentials(credentials_json, user_id)
            token_enc = crypto.encrypt_token(json.dumps(token_info), user_id)
            
            # Save to database
            await db.add_gmail_account(user_id, email, credentials_enc, token_enc)
            
            # Cleanup
            del self.flows[session_id]
            await db.delete_session(session_id)
            context.user_data['state'] = None
            
            # Success message
            text = (
                "✅ *Account Added Successfully!*\n\n"
                f"📧 Email: {email}\n\n"
                "Your Gmail account is now connected.\n"
                "All credentials are encrypted and stored securely."
            )
            
            keyboard = [[InlineKeyboardButton("📬 View Inbox", callback_data="inbox")]]
            
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Authorization failed: {str(e)}\n\n"
                "Please make sure you:\n"
                "1. Copied the entire URL correctly\n"
                "2. Authorized the correct account\n\n"
                "Try again with /start"
            )
            context.user_data['state'] = None


# Global OAuth handler
oauth_handler = OAuthHandler()

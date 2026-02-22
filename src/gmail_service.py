"""Gmail API service layer."""
import json
import base64
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import aiohttp
import config
from crypto import decrypt_token, encrypt_token
from database import db


class GmailService:
    """Gmail API operations."""
    
    def __init__(self):
        self.services = {}  # Cache Gmail service instances
    
    async def get_service(self, account_id: int):
        """Get or create Gmail service for account."""
        # Check cache
        if account_id in self.services:
            return self.services[account_id]
        
        # Load from database
        account = await db.get_gmail_account(account_id)
        if not account:
            raise ValueError("Account not found")
        
        # Decrypt token
        token_data = decrypt_token(account['token_enc'], account['user_id'])
        token_info = json.loads(token_data)
        
        # Create credentials
        creds = Credentials(
            token=token_info['token'],
            refresh_token=token_info.get('refresh_token'),
            token_uri=token_info['token_uri'],
            client_id=token_info['client_id'],
            client_secret=token_info['client_secret'],
            scopes=token_info['scopes']
        )
        
        # Refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            
            # Save refreshed token
            new_token_info = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes
            }
            token_enc = encrypt_token(
                json.dumps(new_token_info), 
                account['user_id']
            )
            await db.update_token(account_id, token_enc)
        
        # Build service
        service = build('gmail', 'v1', credentials=creds)
        self.services[account_id] = service
        return service
    
    async def get_labels(self, account_id: int) -> List[Dict[str, Any]]:
        """Get all labels."""
        service = await self.get_service(account_id)
        results = service.users().labels().list(userId='me').execute()
        return results.get('labels', [])
    
    async def get_messages(self, account_id: int, label_id: str = 'INBOX',
                          max_results: int = 20, page_token: str = None) -> Dict[str, Any]:
        """Get messages from label."""
        service = await self.get_service(account_id)
        
        results = service.users().messages().list(
            userId='me',
            labelIds=[label_id],
            maxResults=max_results,
            pageToken=page_token
        ).execute()
        
        return {
            'messages': results.get('messages', []),
            'nextPageToken': results.get('nextPageToken'),
            'resultSizeEstimate': results.get('resultSizeEstimate', 0)
        }
    
    async def get_message(self, account_id: int, message_id: str) -> Dict[str, Any]:
        """Get full message details."""
        service = await self.get_service(account_id)
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        return message
    
    async def search_messages(self, account_id: int, query: str,
                             max_results: int = 20) -> List[Dict[str, Any]]:
        """Search messages."""
        service = await self.get_service(account_id)
        
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        return results.get('messages', [])
    
    async def mark_as_read(self, account_id: int, message_id: str):
        """Mark message as read."""
        service = await self.get_service(account_id)
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
    
    async def mark_as_unread(self, account_id: int, message_id: str):
        """Mark message as unread."""
        service = await self.get_service(account_id)
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'addLabelIds': ['UNREAD']}
        ).execute()
    
    async def move_to_trash(self, account_id: int, message_id: str):
        """Move message to trash."""
        service = await self.get_service(account_id)
        service.users().messages().trash(
            userId='me',
            id=message_id
        ).execute()
    
    async def mark_as_spam(self, account_id: int, message_id: str):
        """Mark message as spam."""
        service = await self.get_service(account_id)
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'addLabelIds': ['SPAM']}
        ).execute()
    
    async def add_label(self, account_id: int, message_id: str, label_id: str):
        """Add label to message."""
        service = await self.get_service(account_id)
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'addLabelIds': [label_id]}
        ).execute()
    
    async def remove_label(self, account_id: int, message_id: str, label_id: str):
        """Remove label from message."""
        service = await self.get_service(account_id)
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': [label_id]}
        ).execute()
    
    async def get_profile(self, account_id: int) -> Dict[str, Any]:
        """Get Gmail profile."""
        service = await self.get_service(account_id)
        profile = service.users().getProfile(userId='me').execute()
        return profile
    
    async def send_email(self, account_id: int, to_email: str, subject: str, 
                        body: str, reply_to_id: str = None) -> Dict[str, Any]:
        """Send email.
        
        Args:
            account_id: Gmail account ID
            to_email: Recipient email
            subject: Email subject
            body: Email body (plain text)
            reply_to_id: Optional message ID to reply to
            
        Returns:
            Sent message object
        """
        try:
            service = await self.get_service(account_id)
            
            # Get sender email
            profile = await self.get_profile(account_id)
            from_email = profile['emailAddress']
            
            # Build RFC 2822 message
            message = MIMEText(body, 'plain', 'utf-8')
            message['To'] = to_email
            message['From'] = from_email
            message['Subject'] = subject
            
            # Add reply headers if replying
            if reply_to_id:
                original = await self.get_message(account_id, reply_to_id)
                thread_id = original.get('threadId')
                
                # Extract Message-ID from original
                headers = original['payload']['headers']
                original_msg_id = next(
                    (h['value'] for h in headers if h['name'].lower() == 'message-id'),
                    None
                )
                
                if original_msg_id:
                    message['In-Reply-To'] = original_msg_id
                    message['References'] = original_msg_id
            else:
                thread_id = None
            
            # Base64url encode
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send
            body_data = {'raw': raw_message}
            if thread_id:
                body_data['threadId'] = thread_id
            
            sent_message = service.users().messages().send(
                userId='me',
                body=body_data
            ).execute()
            
            return sent_message
            
        except Exception as e:
            raise Exception(f"Failed to send email: {str(e)}")
    
    async def reply_email(self, account_id: int, original_message_id: str, 
                         body: str) -> Dict[str, Any]:
        """Reply to email.
        
        Args:
            account_id: Gmail account ID
            original_message_id: Message ID to reply to
            body: Reply body text
            
        Returns:
            Sent reply message object
        """
        try:
            service = await self.get_service(account_id)
            
            # Fetch original message
            original = await self.get_message(account_id, original_message_id)
            headers = original['payload']['headers']
            
            # Extract details
            original_subject = next(
                (h['value'] for h in headers if h['name'].lower() == 'subject'),
                'No Subject'
            )
            original_from = next(
                (h['value'] for h in headers if h['name'].lower() == 'from'),
                ''
            )
            original_msg_id = next(
                (h['value'] for h in headers if h['name'].lower() == 'message-id'),
                None
            )
            thread_id = original.get('threadId')
            
            # Extract email from "Name <email>" format
            to_email = re.search(r'<(.+?)>', original_from)
            if to_email:
                to_email = to_email.group(1)
            else:
                to_email = original_from
            
            # Add "Re:" if not already there
            if not original_subject.lower().startswith('re:'):
                subject = f"Re: {original_subject}"
            else:
                subject = original_subject
            
            # Get sender email
            profile = await self.get_profile(account_id)
            from_email = profile['emailAddress']
            
            # Build reply message
            message = MIMEText(body, 'plain', 'utf-8')
            message['To'] = to_email
            message['From'] = from_email
            message['Subject'] = subject
            
            # Add reply headers
            if original_msg_id:
                message['In-Reply-To'] = original_msg_id
                message['References'] = original_msg_id
            
            # Base64url encode
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send as reply in same thread
            sent_message = service.users().messages().send(
                userId='me',
                body={
                    'raw': raw_message,
                    'threadId': thread_id
                }
            ).execute()
            
            return sent_message
            
        except Exception as e:
            raise Exception(f"Failed to reply to email: {str(e)}")
    
    async def forward_email(self, account_id: int, original_message_id: str,
                           forward_to: str, extra_note: str = "") -> Dict[str, Any]:
        """Forward email.
        
        Args:
            account_id: Gmail account ID
            original_message_id: Message ID to forward
            forward_to: Recipient email address
            extra_note: Optional note to add before forwarded content
            
        Returns:
            Sent forwarded message object
        """
        try:
            service = await self.get_service(account_id)
            
            # Fetch original message
            original = await self.get_message(account_id, original_message_id)
            headers = original['payload']['headers']
            
            # Extract details
            original_subject = next(
                (h['value'] for h in headers if h['name'].lower() == 'subject'),
                'No Subject'
            )
            original_from = next(
                (h['value'] for h in headers if h['name'].lower() == 'from'),
                'Unknown'
            )
            original_date = next(
                (h['value'] for h in headers if h['name'].lower() == 'date'),
                ''
            )
            
            # Get original body
            original_body = self._extract_body(original['payload'])
            
            # Add "Fwd:" if not already there
            if not original_subject.lower().startswith('fwd:'):
                subject = f"Fwd: {original_subject}"
            else:
                subject = original_subject
            
            # Build forwarded message body
            forwarded_body = ""
            if extra_note:
                forwarded_body += f"{extra_note}\n\n"
            
            forwarded_body += "---------- Forwarded message ---------\n"
            forwarded_body += f"From: {original_from}\n"
            forwarded_body += f"Date: {original_date}\n"
            forwarded_body += f"Subject: {original_subject}\n\n"
            forwarded_body += original_body
            
            # Get sender email
            profile = await self.get_profile(account_id)
            from_email = profile['emailAddress']
            
            # Build message
            message = MIMEText(forwarded_body, 'plain', 'utf-8')
            message['To'] = forward_to
            message['From'] = from_email
            message['Subject'] = subject
            
            # Base64url encode
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send
            sent_message = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return sent_message
            
        except Exception as e:
            raise Exception(f"Failed to forward email: {str(e)}")
    
    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body from payload.
        
        Args:
            payload: Message payload
            
        Returns:
            Email body text
        """
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        break
                elif part['mimeType'] == 'text/html' and not body:
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
        else:
            if 'body' in payload and 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        
        return body
    
    async def unsubscribe_email(self, account_id: int, message_id: str) -> bool:
        """Unsubscribe from mailing list.
        
        Args:
            account_id: Gmail account ID
            message_id: Message ID to unsubscribe from
            
        Returns:
            True if unsubscribe successful, False if no unsubscribe header found
        """
        try:
            service = await self.get_service(account_id)
            
            # Get message headers
            message = await self.get_message(account_id, message_id)
            headers = message['payload']['headers']
            
            # Find List-Unsubscribe header
            unsubscribe_header = next(
                (h['value'] for h in headers if h['name'].lower() == 'list-unsubscribe'),
                None
            )
            
            if not unsubscribe_header:
                return False
            
            # Parse unsubscribe methods
            # Format: <mailto:unsub@example.com>, <http://example.com/unsub>
            mailto_match = re.search(r'<mailto:([^>]+)>', unsubscribe_header)
            http_match = re.search(r'<(https?://[^>]+)>', unsubscribe_header)
            
            # Try mailto first
            if mailto_match:
                unsub_email = mailto_match.group(1)
                
                # Send unsubscribe email
                profile = await self.get_profile(account_id)
                from_email = profile['emailAddress']
                
                message = MIMEText('unsubscribe', 'plain', 'utf-8')
                message['To'] = unsub_email
                message['From'] = from_email
                message['Subject'] = 'Unsubscribe'
                
                raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
                
                service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message}
                ).execute()
                
                return True
            
            # Try HTTP/HTTPS
            elif http_match:
                unsub_url = http_match.group(1)
                
                # Make GET request
                async with aiohttp.ClientSession() as session:
                    async with session.get(unsub_url, timeout=10) as response:
                        if response.status in [200, 201, 202, 204]:
                            return True
                
                return False
            
            return False
            
        except Exception as e:
            # Log error but don't raise - unsubscribe is best-effort
            return False
    
    async def setup_push(self, account_id: int, topic_name: str) -> Dict[str, Any]:
        """Setup Gmail push notifications.
        
        Args:
            account_id: Gmail account ID
            topic_name: Google Cloud Pub/Sub topic name (format: projects/{project}/topics/{topic})
            
        Returns:
            Dict with historyId and expiration timestamp
        """
        try:
            service = await self.get_service(account_id)
            
            # Call users.watch()
            request_body = {
                'topicName': topic_name,
                'labelIds': ['INBOX']  # Watch inbox only
            }
            
            result = service.users().watch(
                userId='me',
                body=request_body
            ).execute()
            
            return {
                'historyId': result.get('historyId'),
                'expiration': result.get('expiration')
            }
            
        except Exception as e:
            raise Exception(f"Failed to setup push notifications: {str(e)}")
    
    async def get_history(self, account_id: int, start_history_id: str) -> List[str]:
        """Get message history since historyId.
        
        Args:
            account_id: Gmail account ID
            start_history_id: Starting history ID
            
        Returns:
            List of new message IDs
        """
        try:
            service = await self.get_service(account_id)
            
            # Call users.history.list()
            result = service.users().history().list(
                userId='me',
                startHistoryId=start_history_id,
                historyTypes=['messageAdded']
            ).execute()
            
            # Extract message IDs
            message_ids = []
            
            if 'history' in result:
                for history_item in result['history']:
                    if 'messagesAdded' in history_item:
                        for msg_added in history_item['messagesAdded']:
                            message_ids.append(msg_added['message']['id'])
            
            return message_ids
            
        except Exception as e:
            # If history ID is too old, return empty list
            if 'Not Found' in str(e) or '404' in str(e):
                return []
            raise Exception(f"Failed to get history: {str(e)}")


# Global service instance
gmail_service = GmailService()

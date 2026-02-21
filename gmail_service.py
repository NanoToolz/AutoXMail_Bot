"""Gmail API service layer."""
import json
from typing import Optional, List, Dict, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import config
from crypto import crypto
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
        token_data = crypto.decrypt_token(account['token_enc'], account['user_id'])
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
            token_enc = crypto.encrypt_token(
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


# Global service instance
gmail_service = GmailService()

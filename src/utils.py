"""Utility functions."""
import re
import base64
from typing import Optional, Tuple
from datetime import datetime


def parse_email_headers(message: dict) -> Tuple[str, str, str]:
    """Extract subject, sender, date from message."""
    headers = message['payload']['headers']
    
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
    sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
    date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
    
    return subject, sender, date


def get_message_body(payload: dict) -> str:
    """Extract message body from payload."""
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
    
    return body[:1000]  # Limit to 1000 chars


def extract_otp(text: str) -> Optional[str]:
    """Extract OTP from text."""
    patterns = [
        r'\b(\d{6})\b',  # 6-digit
        r'\b(\d{4})\b',  # 4-digit
        r'\b(\d{8})\b',  # 8-digit
        r'code[:\s]+(\d+)',
        r'OTP[:\s]+(\d+)',
        r'verification code[:\s]+(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def escape_markdown(text: str) -> str:
    """Escape markdown special characters."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def format_timestamp(timestamp: str) -> str:
    """Format email timestamp to readable format."""
    try:
        # Parse various date formats
        dt = datetime.strptime(timestamp[:25], '%a, %d %b %Y %H:%M:%S')
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return timestamp[:16]


def split_message(text: str, max_length: int = 4000) -> list:
    """Split long message into chunks."""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        
        # Find last newline before max_length
        split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            split_pos = max_length
        
        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip()
    
    return chunks


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

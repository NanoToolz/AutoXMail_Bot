"""Message formatting utilities with tiny caps and MarkdownV2."""
import re
from datetime import datetime


# Tiny caps mapping
TINY_CAPS = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ',
    'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ',
    'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x',
    'y': 'ʏ', 'z': 'ᴢ',
    'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ', 'H': 'ʜ',
    'I': 'ɪ', 'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ', 'O': 'ᴏ', 'P': 'ᴘ',
    'Q': 'ǫ', 'R': 'ʀ', 'S': 's', 'T': 'ᴛ', 'U': 'ᴜ', 'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x',
    'Y': 'ʏ', 'Z': 'ᴢ'
}


def to_tiny_caps(text: str) -> str:
    """Convert text to tiny caps.
    
    Args:
        text: Input text
        
    Returns:
        Text in tiny caps
    """
    return ''.join(TINY_CAPS.get(c, c) for c in text)


def escape_markdown(text: str) -> str:
    """Escape special characters for MarkdownV2.
    
    Args:
        text: Input text
        
    Returns:
        Escaped text safe for MarkdownV2
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def format_header(title: str, subtitle: str = None) -> str:
    """Format message header with tiny caps.
    
    Args:
        title: Main title
        subtitle: Optional subtitle
        
    Returns:
        Formatted header
    """
    header = f"*{to_tiny_caps(title)}*"
    if subtitle:
        header += f" · *{to_tiny_caps(subtitle)}*"
    header += "\n`────────────────────────`\n"
    return header


def format_button_text(text: str) -> str:
    """Format button text with tiny caps.
    
    Args:
        text: Button text
        
    Returns:
        Formatted button text
    """
    return to_tiny_caps(text)


def format_email_preview(subject: str, sender: str, date: str, is_unread: bool = False) -> str:
    """Format email preview.
    
    Args:
        subject: Email subject
        sender: Sender email
        date: Date string
        is_unread: Whether email is unread
        
    Returns:
        Formatted preview
    """
    icon = "🔵" if is_unread else "⚪"
    subject_escaped = escape_markdown(truncate_text(subject, 50))
    sender_escaped = escape_markdown(truncate_text(sender, 35))
    
    return f"{icon} {subject_escaped}\n   From: {sender_escaped}\n"


def format_timestamp(timestamp: str) -> str:
    """Format timestamp to readable format.
    
    Args:
        timestamp: ISO timestamp or epoch
        
    Returns:
        Formatted date string
    """
    try:
        if isinstance(timestamp, str) and timestamp.isdigit():
            dt = datetime.fromtimestamp(int(timestamp) / 1000)
        else:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        now = datetime.now()
        diff = now - dt
        
        if diff.days == 0:
            return dt.strftime('%H:%M')
        elif diff.days == 1:
            return 'Yesterday'
        elif diff.days < 7:
            return dt.strftime('%A')
        else:
            return dt.strftime('%d %b')
    except:
        return timestamp


def truncate_text(text: str, max_length: int) -> str:
    """Truncate text to max length.
    
    Args:
        text: Input text
        max_length: Maximum length
        
    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 1] + '…'


def format_success(message: str) -> str:
    """Format success message.
    
    Args:
        message: Success message
        
    Returns:
        Formatted success message
    """
    return f"✅ {escape_markdown(message)}"


def format_error(message: str) -> str:
    """Format error message.
    
    Args:
        message: Error message
        
    Returns:
        Formatted error message
    """
    return f"❌ {escape_markdown(message)}"


def format_warning(message: str) -> str:
    """Format warning message.
    
    Args:
        message: Warning message
        
    Returns:
        Formatted warning message
    """
    return f"⚠️ {escape_markdown(message)}"


def format_info(message: str) -> str:
    """Format info message.
    
    Args:
        message: Info message
        
    Returns:
        Formatted info message
    """
    return f"ℹ️ {escape_markdown(message)}"


def split_message(text: str, max_length: int = 4000) -> list[str]:
    """Split long message into chunks.
    
    Args:
        text: Long text
        max_length: Maximum length per chunk
        
    Returns:
        List of text chunks
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    for line in text.split('\n'):
        if len(current_chunk) + len(line) + 1 <= max_length:
            current_chunk += line + '\n'
        else:
            if current_chunk:
                chunks.append(current_chunk.rstrip())
            current_chunk = line + '\n'
    
    if current_chunk:
        chunks.append(current_chunk.rstrip())
    
    return chunks


def extract_otp(text: str) -> str:
    """Extract OTP code from text.
    
    Args:
        text: Email body text
        
    Returns:
        OTP code if found, empty string otherwise
    """
    # Common OTP patterns
    patterns = [
        r'\b(\d{6})\b',  # 6-digit code
        r'\b(\d{4})\b',  # 4-digit code
        r'\b([A-Z0-9]{6})\b',  # 6-char alphanumeric
        r'code[:\s]+(\d+)',  # "code: 123456"
        r'OTP[:\s]+(\d+)',  # "OTP: 123456"
        r'verification[:\s]+(\d+)',  # "verification: 123456"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return ""

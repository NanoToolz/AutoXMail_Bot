"""Pagination utilities for long messages."""
import re


def paginate(text: str, chunk_size: int = 3500) -> list[str]:
    """Split long text into chunks for Telegram messages.
    
    Args:
        text: Text to paginate
        chunk_size: Maximum characters per chunk (default 3500, Telegram limit is 4096)
        
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    remaining = text
    
    while remaining:
        if len(remaining) <= chunk_size:
            chunks.append(remaining)
            break
        
        # Try to split on double newline (paragraph boundary)
        split_pos = remaining.rfind('\n\n', 0, chunk_size)
        
        # Fallback: split on single newline
        if split_pos == -1:
            split_pos = remaining.rfind('\n', 0, chunk_size)
        
        # Fallback: split on space
        if split_pos == -1:
            split_pos = remaining.rfind(' ', 0, chunk_size)
        
        # Last resort: hard cut at chunk_size
        if split_pos == -1:
            split_pos = chunk_size
        
        # Check if we're inside a code block
        chunk = remaining[:split_pos]
        code_blocks = chunk.count('```')
        
        # If odd number of code blocks, we're inside one - find the end
        if code_blocks % 2 == 1:
            # Find the closing ```
            close_pos = remaining.find('```', split_pos)
            if close_pos != -1 and close_pos < len(remaining):
                split_pos = close_pos + 3
        
        chunks.append(remaining[:split_pos].rstrip())
        remaining = remaining[split_pos:].lstrip()
    
    return chunks


def create_pagination_keyboard(current_page: int, total_pages: int, 
                               callback_prefix: str, back_callback: str = "start") -> list:
    """Create pagination keyboard buttons.
    
    Args:
        current_page: Current page number (1-indexed)
        total_pages: Total number of pages
        callback_prefix: Prefix for page callbacks (e.g., "email_page")
        back_callback: Callback for back button
        
    Returns:
        List of button rows
    """
    from telegram import InlineKeyboardButton
    from formatter import to_tiny_caps
    
    buttons = []
    nav_row = []
    
    # Previous button
    if current_page > 1:
        nav_row.append(InlineKeyboardButton(
            f"◀ {to_tiny_caps('Prev Page')}",
            callback_data=f"{callback_prefix}:{current_page - 1}"
        ))
    
    # Next button
    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton(
            f"{to_tiny_caps('Next Page')} ▶",
            callback_data=f"{callback_prefix}:{current_page + 1}"
        ))
    
    if nav_row:
        buttons.append(nav_row)
    
    # Back button
    buttons.append([InlineKeyboardButton(
        f"🔙 {to_tiny_caps('Back')}",
        callback_data=back_callback
    )])
    
    return buttons

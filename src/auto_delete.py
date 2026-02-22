"""Auto-delete message system."""
import asyncio
from telegram import Bot


# Delete delays (in seconds)
DELETE_IMMEDIATE = 0  # Credentials, sensitive data
DELETE_SENSITIVE = 5  # Auth codes, OTPs
DELETE_SUCCESS = 15  # Success messages
DELETE_WARNING = 30  # Warnings, errors
DELETE_GUIDE = 60  # Help, guides


async def schedule_delete(bot: Bot, chat_id: int, message_id: int, delay: int):
    """Schedule message deletion.
    
    Args:
        bot: Bot instance
        chat_id: Chat ID
        message_id: Message ID to delete
        delay: Delay in seconds before deletion
    """
    if delay > 0:
        await asyncio.sleep(delay)
    
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        # Message already deleted or not found
        pass


def get_delete_delay(message_type: str) -> int:
    """Get delete delay for message type.
    
    Args:
        message_type: Type of message (credentials, sensitive, success, warning, guide)
        
    Returns:
        Delay in seconds
    """
    delays = {
        'credentials': DELETE_IMMEDIATE,
        'sensitive': DELETE_SENSITIVE,
        'success': DELETE_SUCCESS,
        'warning': DELETE_WARNING,
        'guide': DELETE_GUIDE,
    }
    return delays.get(message_type, DELETE_WARNING)

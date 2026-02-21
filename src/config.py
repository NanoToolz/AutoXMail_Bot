"""Configuration management for AutoXMail v2."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
LOGS_DIR = BASE_DIR / 'logs'

# Create directories
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Telegram Bot
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')  # For logs
LOG_TOPIC_ID = os.getenv('LOG_TOPIC_ID')  # Optional: Telegram topic for logs

# Database
DB_PATH = DATA_DIR / 'autoxmail.db'

# Encryption
MASTER_KEY = os.getenv('MASTER_KEY')  # Master encryption key

# Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Limits
MAX_ACCOUNTS_PER_USER = int(os.getenv('MAX_ACCOUNTS_PER_USER', '3'))
MAX_MESSAGE_LENGTH = 4000
MEMORY_LIMIT_MB = 100

# Webhook (optional)
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # For push notifications
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')

# Rate limiting
RATE_LIMIT_REQUESTS = 30  # per minute per user
RATE_LIMIT_WINDOW = 60  # seconds

# Session timeout
SESSION_TIMEOUT = 300  # 5 minutes

# Validation
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set in .env")
if not MASTER_KEY:
    raise ValueError("MASTER_KEY not set in .env")
if not ADMIN_CHAT_ID:
    raise ValueError("ADMIN_CHAT_ID not set in .env")

#!/usr/bin/env python3
"""Setup script for AutoXMail v2."""
import os
import secrets
from pathlib import Path


def generate_master_key():
    """Generate secure master key."""
    return secrets.token_urlsafe(32)


def create_env_file():
    """Create .env file from template."""
    env_path = Path('.env')
    
    if env_path.exists():
        print("⚠️  .env file already exists!")
        response = input("Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Setup cancelled.")
            return False
    
    print("\n🔧 AutoXMail v2 Setup\n")
    
    # Get inputs
    bot_token = input("Enter Telegram BOT_TOKEN: ").strip()
    admin_chat_id = input("Enter your Telegram ADMIN_CHAT_ID: ").strip()
    log_topic_id = input("Enter LOG_TOPIC_ID (optional, press Enter to skip): ").strip()
    
    # Generate master key
    master_key = generate_master_key()
    
    # Create .env
    env_content = f"""# Telegram Bot Configuration
BOT_TOKEN={bot_token}
ADMIN_CHAT_ID={admin_chat_id}
LOG_TOPIC_ID={log_topic_id}

# Encryption (Auto-generated)
MASTER_KEY={master_key}

# Limits
MAX_ACCOUNTS_PER_USER=3

# Webhook (Optional)
WEBHOOK_URL=
WEBHOOK_SECRET=
"""
    
    env_path.write_text(env_content)
    
    print("\n✅ Setup complete!")
    print(f"✅ .env file created")
    print(f"✅ Master key generated: {master_key[:20]}...")
    print("\n⚠️  IMPORTANT: Keep your MASTER_KEY safe!")
    print("⚠️  If you lose it, you won't be able to decrypt stored credentials.\n")
    
    return True


def create_directories():
    """Create required directories."""
    Path('data').mkdir(exist_ok=True)
    Path('logs').mkdir(exist_ok=True)
    print("✅ Created data/ and logs/ directories")


def main():
    """Run setup."""
    print("=" * 50)
    print("AutoXMail v2 - Setup")
    print("=" * 50)
    
    if create_env_file():
        create_directories()
        
        print("\n📝 Next steps:")
        print("1. Review your .env file")
        print("2. Run: python main.py")
        print("3. Or use Docker: docker-compose up -d")
        print("\n🚀 Ready to start!")
    else:
        print("\n❌ Setup failed or cancelled")


if __name__ == '__main__':
    main()

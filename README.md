# AutoXMail Bot - Gmail Client for Telegram

**Multi-user Telegram bot for complete Gmail management**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)]()

## 🌟 Features

### Core Features
- 🔐 **Multi-user support** - Unlimited users, 3 Gmail accounts each
- 📧 **Full Gmail client** - Browse, search, read, manage labels, spam
- 🔑 **Multi-account** - Switch between multiple Gmail accounts
- 🎯 **Advanced UI** - Inline buttons for all operations
- 🔒 **End-to-end encryption** - Per-user credential encryption
- 📊 **Structured logging** - Telegram group/topic logging
- 💾 **Resource efficient** - 100MB RAM hard limit
- 🐳 **Containerized** - Docker/Podman ready

### Gmail Operations
- ✅ Browse inbox, sent, labels
- ✅ View full messages with OTP detection
- ✅ Mark as read/unread
- ✅ Delete messages (move to trash)
- ✅ Mark as spam
- ✅ Label management
- ✅ Search messages
- ✅ Multi-account support

### Security
- 🔐 Fernet encryption (AES-128 + HMAC-SHA256)
- 🔑 Per-user key derivation (PBKDF2HMAC, 100k iterations)
- 🛡️ Non-root container execution
- 🚫 Dropped capabilities
- ⏱️ Session timeout (5 minutes)
- 🚦 Rate limiting (30 req/min per user)

## 📸 Screenshots

```
🤖 AutoXMail v2

Full Gmail client in Telegram

[📧 My Accounts] [➕ Add Account]
[📬 Inbox]       [🔍 Search]
[🏷️ Labels]      [⚙️ Settings]
[ℹ️ Help]
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ OR Docker/Podman
- Telegram Bot Token ([Get from @BotFather](https://t.me/BotFather))
- Google Cloud Project with Gmail API enabled

### Installation

**Option 1: Python (Development)**
```bash
git clone https://github.com/NanoToolz/AutoXMail_v2.git
cd AutoXMail_v2
python3 setup.py
pip install -r requirements.txt
python main.py
```

**Option 2: Docker Compose (Production)**
```bash
git clone https://github.com/NanoToolz/AutoXMail_v2.git
cd AutoXMail_v2
python3 setup.py
docker-compose up -d
```

**Option 3: Podman**
```bash
podman build -t autoxmail-v2 .
podman run -d --name autoxmail_v2 --env-file .env \
    -v ./data:/app/data:rw -v ./logs:/app/logs:rw \
    --memory 100m autoxmail-v2
```

### Configuration

Create `.env` file (or run `python3 setup.py`):

```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_CHAT_ID=your_telegram_chat_id
MASTER_KEY=auto_generated_secure_key
MAX_ACCOUNTS_PER_USER=3
```

## 📖 Documentation

- **[Quick Start Guide](QUICKSTART.md)** - Get running in 5 minutes
- **[License](LICENSE)** - MIT License

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Telegram Users                       │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                   Bot Handlers (UI)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Accounts │  │  Inbox   │  │  Search  │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                  Service Layer                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │  Gmail   │  │  OAuth   │  │  Crypto  │             │
│  │ Service  │  │ Handler  │  │ Manager  │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Database (SQLite + aiosqlite)              │
│  users | gmail_accounts | sessions | rate_limits       │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                   External APIs                         │
│         Gmail API          |      Telegram API          │
└─────────────────────────────────────────────────────────┘
```

## 🔧 Tech Stack

- **Language:** Python 3.11+
- **Bot Framework:** python-telegram-bot 20.7
- **Database:** SQLite + aiosqlite
- **Encryption:** cryptography (Fernet)
- **Gmail API:** google-api-python-client
- **Container:** Alpine Linux
- **Runtime:** Docker/Podman

## 📊 Performance

- **Memory:** 50-80MB typical, 100MB max
- **Startup:** <5 seconds
- **Response:** <2 seconds per action
- **Concurrent Users:** 1000+
- **Accounts:** 3000+
- **Rate Limit:** 30 requests/minute per user

## 🔒 Security

- ✅ End-to-end encryption (Fernet AES-128 + HMAC-SHA256)
- ✅ Per-user key derivation (master_key + user_id)
- ✅ PBKDF2HMAC with 100,000 iterations
- ✅ Non-root container execution
- ✅ All capabilities dropped
- ✅ Rate limiting per user
- ✅ Session timeout (5 minutes)
- ✅ No plain-text credential storage

## 💡 Key Highlights

- 🔐 Bank-level encryption for all credentials
- 📱 Beautiful inline button interface
- 🚀 Deploy in minutes with Docker
- 💾 Lightweight - only 100MB RAM
- 🔄 Auto token refresh
- ⚡ Fast response times (<2s)

## 🛣️ Roadmap

- Email composition
- Attachment handling
- Advanced search filters
- Auto-reply rules
- Multi-language support

## 🤝 Contributing

Contributions welcome! Open an issue or submit a pull request.

## 📝 License

MIT License - See [LICENSE](LICENSE) file

## 👨‍💻 Author

**NanoToolz**
- Email: theasimgrphics@gmail.com
- GitHub: [@NanoToolz](https://github.com/NanoToolz)

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/NanoToolz/AutoXMail_Bot/issues)
- **Email:** theasimgrphics@gmail.com

---

**Made with ❤️ by NanoToolz**

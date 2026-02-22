# AutoXMail Bot v3.0

**Multi-user Gmail client for Telegram with end-to-end encryption**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](docs/LICENSE)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://telegram.org/)

---

## ✨ Features

- 📧 **Multi-Account Support** - Manage up to 75 Gmail accounts
- 🔐 **End-to-End Encryption** - AES-128 with per-user isolation
- 🔔 **Push Notifications** - Real-time email alerts via Pub/Sub
- 📱 **Clean UI** - Intuitive Telegram interface with inline buttons
- 🔍 **Advanced Search** - Full Gmail search syntax support
- ⭐ **Starred Messages** - Quick access to important emails
- 🏷️ **Label Management** - Organize emails with Gmail labels
- ✉️ **Email Composition** - Send emails with attachments (25MB)
- 🔒 **Security First** - JWT authentication, rate limiting, auto-delete

---

## 🚀 Quick Start

### One-Command Installation

```bash
curl -sSL https://raw.githubusercontent.com/NanoToolz/AutoXMail_Bot/main/FRESH_SETUP.sh | bash
```

### Manual Installation

```bash
# Clone repository
git clone https://github.com/NanoToolz/AutoXMail_Bot.git
cd AutoXMail_Bot

# Configure environment
python3 config/setup.py

# Create directories
mkdir -p data logs
chmod 777 data logs

# Build and run
podman build -t autoxmail-bot -f config/Dockerfile .
podman run -d \
  --name autoxmail_bot \
  --restart always \
  --env-file .env \
  -v ./data:/app/data:rw \
  -v ./logs:/app/logs:rw \
  --memory 150m \
  autoxmail-bot

# Check logs
podman logs -f autoxmail_bot
```

---

## 📋 Requirements

- **Python:** 3.11+
- **Container:** Podman or Docker
- **Telegram:** Bot token from [@BotFather](https://t.me/BotFather)
- **Google Cloud:** OAuth 2.0 credentials with Gmail API enabled

---

## 📚 Documentation

- **[Setup Guide](SETUP_GUIDE.md)** - Complete step-by-step installation
- **[Fresh Setup Script](FRESH_SETUP.sh)** - Automated clean installation
- **[Azure Deployment](DEPLOY_AZURE.sh)** - Deploy to Azure VM
- **[Quick Start](docs/QUICKSTART.md)** - Get running in 5 minutes

---

## 🔒 Security Features

- ✅ **Per-user encryption** with random salts
- ✅ **JWT webhook authentication** for Pub/Sub
- ✅ **JSON serialization** (no pickle vulnerability)
- ✅ **Rate limiting** per endpoint
- ✅ **Auto-delete** sensitive messages
- ✅ **Non-root** container execution
- ✅ **No credential logging**

---

## 🛠️ Tech Stack

- **Backend:** Python 3.11, aiosqlite, cryptography
- **Bot Framework:** python-telegram-bot 20.7
- **Gmail API:** google-api-python-client
- **Container:** Alpine Linux, Podman
- **Database:** SQLite with WAL mode

---

## 📁 Project Structure

```
AutoXMail_Bot/
├── src/                    # Source code
│   ├── main.py            # Bot entry point
│   ├── config.py          # Configuration
│   ├── database.py        # Database layer
│   ├── crypto.py          # Encryption
│   ├── gmail_service.py   # Gmail API
│   ├── handlers.py        # Telegram handlers
│   ├── oauth_handler.py   # OAuth flow
│   └── utils.py           # Utilities
├── config/                 # Configuration files
│   ├── Dockerfile         # Container image
│   ├── docker-compose.yml # Compose config
│   ├── requirements.txt   # Python dependencies
│   ├── setup.py           # Setup script
│   └── .env.example       # Environment template
├── docs/                   # Documentation
│   ├── README.md          # Detailed docs
│   ├── QUICKSTART.md      # Quick start guide
│   └── LICENSE            # MIT License
├── .github/                # GitHub workflows
│   └── workflows/         # CI/CD
├── SETUP_GUIDE.md         # Complete setup guide
├── FRESH_SETUP.sh         # Fresh install script
├── DEPLOY_AZURE.sh        # Azure deployment
└── README.md              # This file
```

---

## 🎯 Usage

### Basic Commands

```bash
# View logs
podman logs -f autoxmail_bot

# Restart bot
podman restart autoxmail_bot

# Stop bot
podman stop autoxmail_bot

# Check status
podman ps | grep autoxmail
```

### Telegram Commands

- `/start` - Start bot and show main menu
- `/help` - Show help and features
- `/accounts` - Manage Gmail accounts
- `/inbox` - Browse inbox
- `/search` - Search emails
- `/compose` - Compose new email

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📞 Support

- **GitHub Issues:** [Report bugs](https://github.com/NanoToolz/AutoXMail_Bot/issues)
- **Email:** theasimgrphics@gmail.com
- **Developer:** [NanoToolz](https://github.com/NanoToolz)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](docs/LICENSE) file for details.

---

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [Google Gmail API](https://developers.google.com/gmail/api) - Gmail integration
- [Cryptography](https://cryptography.io/) - Encryption library

---

**Made with ❤️ by NanoToolz**

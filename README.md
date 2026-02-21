# AutoXMail Bot

**Multi-user Gmail client for Telegram**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](docs/LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)]()

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/NanoToolz/AutoXMail_Bot.git
cd AutoXMail_Bot

# Setup
python config/setup.py

# Run
python src/main.py

# Or use Docker
docker-compose -f config/docker-compose.yml up -d
```

## ✨ Features

- 🔐 Multi-user support with encryption
- 📧 Full Gmail client (browse, search, manage)
- 🔑 Multi-account support (3 per user)
- 🎯 Inline button interface
- 🐳 Docker deployment ready
- 💾 Lightweight (100MB RAM)

## 📁 Project Structure

```
AutoXMail_Bot/
├── src/              # Source code
│   ├── main.py
│   ├── handlers.py
│   ├── gmail_service.py
│   └── ...
├── config/           # Configuration files
│   ├── .env.example
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/             # Documentation
│   ├── QUICKSTART.md
│   └── LICENSE
└── .github/          # CI/CD workflows
```

## 📖 Documentation

- [Quick Start Guide](docs/QUICKSTART.md) - Get running in 5 minutes
- [License](docs/LICENSE) - MIT License

## 🔧 Tech Stack

- Python 3.11+
- python-telegram-bot 20.7
- SQLite + aiosqlite
- Google Gmail API
- Docker/Podman

## 👨‍💻 Author

**NanoToolz**
- Email: theasimgrphics@gmail.com
- GitHub: [@NanoToolz](https://github.com/NanoToolz)

## 📞 Support

- Issues: [GitHub Issues](https://github.com/NanoToolz/AutoXMail_Bot/issues)
- Email: theasimgrphics@gmail.com

---

**Made with ❤️ by NanoToolz**

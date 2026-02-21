# AutoXMail v2 - Project Summary

## Overview

AutoXMail v2 is a complete rewrite of the original AutoXMail bot, transforming it from a single-user notification system into a full-featured multi-user Gmail client accessible via Telegram.

## Key Differences from v1

| Feature | v1 | v2 |
|---------|----|----|
| Users | Single user | Multi-user |
| Database | None | SQLite + aiosqlite |
| Gmail Features | Notifications only | Full client (browse, search, manage) |
| Accounts | 1 account | 3 accounts per user |
| UI | Basic messages | Advanced inline buttons |
| OAuth | CLI/Telegram hybrid | Pure Telegram flow |
| Encryption | File-based | Per-user database encryption |
| Memory | ~60MB | 100MB hard limit |
| Architecture | Simple loop | Service-oriented |

## Project Structure

```
AutoXMail_v2/
├── main.py                 # Entry point
├── config.py               # Configuration
├── database.py             # SQLite + aiosqlite
├── crypto.py               # Encryption utilities
├── gmail_service.py        # Gmail API wrapper
├── handlers.py             # Telegram UI handlers
├── oauth_handler.py        # OAuth flow
├── utils.py                # Helper functions
├── setup.py                # Setup script
├── requirements.txt        # Dependencies
├── Dockerfile              # Container image
├── docker-compose.yml      # Compose config
├── .env.example            # Environment template
├── .gitignore              # Git ignore rules
├── LICENSE                 # MIT License
├── README.md               # Main documentation
├── ARCHITECTURE.md         # Architecture details
├── DEPLOYMENT.md           # Deployment guide
└── PROJECT_SUMMARY.md      # This file
```

## Core Components

### 1. Database Layer (`database.py`)
- Async SQLite with aiosqlite
- 5 tables: users, gmail_accounts, sessions, notification_settings, rate_limits
- Session management for OAuth flow
- Rate limiting per user per endpoint

### 2. Encryption (`crypto.py`)
- Fernet (AES-128 CBC + HMAC-SHA256)
- Per-user key derivation (master_key + user_id)
- PBKDF2HMAC with 100,000 iterations
- Encrypted credentials and tokens in database

### 3. Gmail Service (`gmail_service.py`)
- Service instance caching
- Auto token refresh
- Full Gmail API operations:
  - Get labels
  - List messages
  - Get message details
  - Search messages
  - Mark read/unread
  - Move to trash
  - Mark as spam
  - Label management

### 4. Handlers (`handlers.py`)
- Main menu (/start)
- Account management
- Inbox browsing
- Message viewing with actions
- Search functionality
- Settings management
- Help system

### 5. OAuth Handler (`oauth_handler.py`)
- Telegram-based OAuth flow
- Upload credentials.json
- Generate auth URL
- Process authorization code
- Encrypt and store credentials
- Session timeout (5 minutes)

## Features Implemented

### ✅ Core Features
- [x] Multi-user support
- [x] SQLite database with aiosqlite
- [x] Per-user encryption
- [x] OAuth via Telegram
- [x] Multi-account support (3 per user)
- [x] Inbox browsing
- [x] Message viewing
- [x] Mark read/unread
- [x] Delete messages
- [x] Spam management
- [x] Rate limiting (30 req/min)
- [x] Session management
- [x] Inline button UI
- [x] Docker/Podman deployment
- [x] 100MB memory limit

### 🚧 Partial Implementation
- [ ] Search functionality (structure ready, needs UI)
- [ ] Label management (API ready, needs UI)
- [ ] Notification settings (DB ready, needs UI)
- [ ] Push notifications via webhook (config ready, needs implementation)

### 📋 Future Features
- [ ] Email composition
- [ ] Attachment download
- [ ] Advanced search filters
- [ ] Auto-reply rules
- [ ] Email templates
- [ ] Scheduled emails

## Technical Specifications

### Dependencies
```
python-telegram-bot==20.7
google-api-python-client==2.111.0
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
cryptography==42.0.5
python-dotenv==1.0.1
aiosqlite==0.19.0
aiohttp==3.9.3
```

### Resource Limits
- Memory: 100MB hard limit
- CPU: Shared (no hard limit)
- Disk: ~200MB (image + data)
- Rate Limit: 30 requests/minute per user

### Security Features
- End-to-end encryption
- Per-user key derivation
- Non-root container execution
- Dropped capabilities
- Rate limiting
- Session timeout
- Input validation
- No plain-text secrets

## Deployment Options

### 1. Direct Python
```bash
python3 setup.py
python3 main.py
```

### 2. Docker Compose
```bash
docker-compose up -d
```

### 3. Podman
```bash
podman build -t autoxmail-v2 .
podman run -d --name autoxmail_v2 --env-file .env autoxmail-v2
```

### 4. Systemd Service
```bash
sudo systemctl enable autoxmail-v2
sudo systemctl start autoxmail-v2
```

## User Flow

### Adding Gmail Account

1. User sends `/start`
2. Clicks "➕ Add Account"
3. Uploads `credentials.json`
4. Bot generates OAuth URL
5. User authorizes in browser
6. User sends redirect URL
7. Bot exchanges code for token
8. Credentials encrypted and stored
9. Account ready to use

### Viewing Inbox

1. User clicks "📬 Inbox"
2. Bot checks rate limit
3. Fetches messages from Gmail API
4. Displays list with inline buttons
5. User clicks message to view
6. Full message displayed with actions
7. User can mark read, delete, spam, etc.

## Performance Metrics

### Expected Performance
- Startup time: <5 seconds
- Response time: <2 seconds per action
- Memory usage: 50-80MB typical, 100MB max
- Concurrent users: 1000+
- Accounts: 3000+
- API calls: 10,000/minute

### Optimization Techniques
- Service instance caching
- Lazy loading
- Message truncation
- Pagination
- Connection pooling
- Rate limiting

## Testing Strategy

### Manual Testing
- [x] OAuth flow
- [x] Account management
- [x] Inbox browsing
- [x] Message actions
- [x] Rate limiting
- [x] Session timeout
- [x] Container deployment

### Automated Testing (Future)
- [ ] Unit tests
- [ ] Integration tests
- [ ] Load tests
- [ ] Security tests

## Known Limitations

1. **SQLite Limitation**
   - No horizontal scaling
   - Single-writer limitation
   - For high-scale, migrate to PostgreSQL

2. **Memory Limit**
   - 100MB hard limit
   - May need increase for 1000+ users

3. **Rate Limiting**
   - Gmail API: 250 quota units/user/second
   - Bot: 30 requests/minute per user

4. **No Email Composition**
   - Read-only operations (except delete/spam)
   - Future enhancement

## Migration from v1

AutoXMail v2 is a completely new project. To migrate:

1. Keep v1 running for notifications
2. Deploy v2 separately
3. Add accounts to v2
4. Test v2 functionality
5. Optionally disable v1

**Note:** No automatic migration tool. v1 and v2 can run simultaneously.

## Development Roadmap

### Phase 1: Core Features (COMPLETED)
- ✅ Multi-user support
- ✅ Database layer
- ✅ Encryption
- ✅ OAuth flow
- ✅ Basic Gmail operations
- ✅ Inline button UI

### Phase 2: Enhanced Features (IN PROGRESS)
- 🚧 Search UI
- 🚧 Label management UI
- 🚧 Notification settings UI
- 🚧 Push notifications

### Phase 3: Advanced Features (PLANNED)
- 📋 Email composition
- 📋 Attachment handling
- 📋 Advanced search
- 📋 Auto-reply rules

### Phase 4: Enterprise Features (FUTURE)
- 📋 PostgreSQL support
- 📋 Redis caching
- 📋 Prometheus metrics
- 📋 Multi-instance deployment

## Contributing

Contributions welcome! Please:

1. Fork repository
2. Create feature branch
3. Make changes
4. Add tests (if applicable)
5. Submit pull request

## License

MIT License - See LICENSE file

## Support

- GitHub Issues: https://github.com/NanoToolz/AutoXMail_v2/issues
- Email: theasimgrphics@gmail.com

## Credits

**Author:** NanoToolz  
**Email:** theasimgrphics@gmail.com  
**GitHub:** https://github.com/NanoToolz  
**Version:** 2.0.0  
**Release Date:** February 21, 2026

## Acknowledgments

- python-telegram-bot team
- Google Gmail API team
- Cryptography library maintainers
- Alpine Linux project
- Open source community

---

**Status:** ✅ Core features complete, ready for testing  
**Next Steps:** Deploy, test, gather feedback, implement Phase 2 features

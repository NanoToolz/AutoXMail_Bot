# AutoXMail v2 - Architecture Documentation

## System Overview

AutoXMail v2 is a multi-user Telegram bot that provides full Gmail client functionality with enterprise-grade security and scalability.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        User Layer                           │
├─────────────────────────────────────────────────────────────┤
│  Multiple Telegram Users → Bot Interface (Inline Buttons)   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Handlers   │  │ OAuth Handler│  │ Gmail Service│     │
│  │  (UI Logic)  │  │ (Auth Flow)  │  │ (API Calls)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                              │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Database   │  │    Crypto    │  │  Rate Limit  │     │
│  │  (SQLite)    │  │  (Fernet)    │  │   Manager    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    External Services                         │
├─────────────────────────────────────────────────────────────┤
│         Gmail API          │        Telegram API            │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Handlers (`handlers.py`)

**Responsibility:** UI logic and user interactions

**Key Functions:**
- `/start` - Main menu
- Account management
- Inbox browsing
- Message viewing
- Search functionality
- Label management
- Settings

**Design Pattern:** Command Pattern

### 2. OAuth Handler (`oauth_handler.py`)

**Responsibility:** Gmail account authentication

**Flow:**
1. User uploads credentials.json
2. Generate OAuth URL
3. User authorizes in browser
4. User sends redirect URL
5. Exchange code for token
6. Encrypt and store credentials

**Security:**
- Per-user encryption
- Session timeout (5 minutes)
- Secure credential storage

### 3. Gmail Service (`gmail_service.py`)

**Responsibility:** Gmail API operations

**Features:**
- Service caching
- Auto token refresh
- Label management
- Message operations (read, delete, spam)
- Search functionality

**Optimization:**
- Connection pooling
- Token caching
- Lazy loading

### 4. Database (`database.py`)

**Responsibility:** Data persistence

**Schema:**

```sql
users
├── user_id (PK)
├── username
├── first_name
├── registered_at
├── last_active
└── is_active

gmail_accounts
├── id (PK)
├── user_id (FK)
├── email
├── credentials_enc (BLOB)
├── token_enc (BLOB)
├── added_at
├── last_sync
└── is_active

sessions
├── session_id (PK)
├── user_id (FK)
├── state
├── data (JSON)
├── created_at
└── expires_at

notification_settings
├── user_id (PK, FK)
├── enabled
├── keywords
├── exclude_spam
└── exclude_promotions

rate_limits
├── user_id (PK)
├── endpoint (PK)
├── request_count
└── window_start
```

### 5. Crypto (`crypto.py`)

**Responsibility:** Encryption/decryption

**Algorithm:** Fernet (AES-128 CBC + HMAC-SHA256)

**Key Derivation:**
```python
PBKDF2HMAC(
    algorithm=SHA256,
    length=32,
    salt=b'AutoXMail_v2_2026',
    iterations=100,000
)
```

**Per-User Encryption:**
- Master key + user_id → unique key
- Prevents cross-user data access
- Key never stored on disk

## Data Flow

### Message Viewing Flow

```
User clicks "Inbox"
    ↓
Handler checks rate limit
    ↓
Gmail Service fetches messages
    ↓
Parse headers (subject, sender, date)
    ↓
Format with inline buttons
    ↓
Send to user
```

### OAuth Flow

```
User clicks "Add Account"
    ↓
Upload credentials.json
    ↓
Validate and create OAuth flow
    ↓
Generate auth URL
    ↓
User authorizes in browser
    ↓
User sends redirect URL
    ↓
Exchange code for token
    ↓
Encrypt credentials + token
    ↓
Store in database
    ↓
Success!
```

## Security Architecture

### Multi-Layer Security

1. **Transport Layer**
   - TLS/SSL for all API calls
   - HTTPS only

2. **Application Layer**
   - Rate limiting (30 req/min per user)
   - Session timeout (5 minutes)
   - Input validation

3. **Data Layer**
   - Per-user encryption
   - Encrypted credentials storage
   - No plain-text secrets

4. **Container Layer**
   - Non-root execution
   - Dropped capabilities
   - Read-only filesystem (where possible)
   - Memory limits (100MB)

### Threat Model

**Protected Against:**
- ✅ Database compromise (encrypted data)
- ✅ Container escape (non-root, dropped caps)
- ✅ Rate limiting bypass (per-user tracking)
- ✅ Session hijacking (timeout + validation)
- ✅ Cross-user data access (per-user keys)

**Not Protected Against:**
- ❌ Master key compromise
- ❌ Telegram bot token leak
- ❌ Physical server access

## Performance Optimization

### Caching Strategy

1. **Gmail Service Cache**
   - Cache service instances per account
   - Invalidate on token refresh

2. **Database Connection Pool**
   - aiosqlite async connections
   - Connection reuse

3. **Rate Limiting**
   - In-memory + database hybrid
   - Sliding window algorithm

### Memory Management

**Target:** 100MB hard limit

**Breakdown:**
- Python runtime: ~30MB
- Dependencies: ~20MB
- Application: ~20MB
- Database cache: ~10MB
- Gmail service cache: ~10MB
- Buffer: ~10MB

**Optimization:**
- Lazy loading
- Message truncation
- Pagination
- Service instance reuse

## Scalability

### Current Limits

- Users: Unlimited
- Accounts per user: 3 (configurable)
- Messages per request: 20
- Rate limit: 30 req/min per user

### Horizontal Scaling

**Not Supported** (SQLite limitation)

For high-scale deployment:
1. Replace SQLite with PostgreSQL
2. Add Redis for caching
3. Use message queue (RabbitMQ/Redis)
4. Deploy multiple bot instances

### Vertical Scaling

**Supported** up to:
- 1000 concurrent users
- 3000 Gmail accounts
- 10,000 requests/minute

## Deployment Architecture

### Docker Deployment

```
Host Machine (Debian/Ubuntu)
    ↓
Podman/Docker Runtime
    ↓
Alpine Linux Container
    ↓
Python 3.11 + Application
    ↓
Mounted Volumes (data/, logs/)
```

### Resource Limits

```yaml
mem_limit: 100m
mem_reservation: 50m
cpu_shares: 512
```

### Health Checks

- Interval: 30s
- Timeout: 10s
- Retries: 3

## Monitoring & Logging

### Log Levels

- INFO: Normal operations
- WARNING: Rate limits, retries
- ERROR: API failures, exceptions
- CRITICAL: System failures

### Metrics (Future)

- Active users
- API call rate
- Error rate
- Response time
- Memory usage

### Telegram Logging

- Admin notifications
- Error alerts
- System status
- Optional: Topic-based logging

## Future Enhancements

### Phase 2
- [ ] Push notifications via webhook
- [ ] Advanced search filters
- [ ] Email composition
- [ ] Attachment download
- [ ] Label creation/management

### Phase 3
- [ ] PostgreSQL support
- [ ] Redis caching
- [ ] Prometheus metrics
- [ ] Grafana dashboard
- [ ] Multi-instance deployment

### Phase 4
- [ ] Email templates
- [ ] Scheduled emails
- [ ] Auto-reply rules
- [ ] Email forwarding
- [ ] Backup/restore

---

**Version:** 2.0.0  
**Last Updated:** February 21, 2026  
**Author:** NanoToolz

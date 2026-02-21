# AutoXMail v2 - Quick Start Guide

Get up and running in 5 minutes! 🚀

## Prerequisites

- Python 3.11+ OR Docker/Podman
- Telegram account
- Google Cloud account

## Step 1: Get Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Follow instructions to create bot
4. Copy the bot token (looks like: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)
5. Get your chat ID:
   - Search for `@userinfobot`
   - Send `/start`
   - Copy your ID (looks like: `8034712119`)

## Step 2: Setup Google Cloud

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project (or use existing)
3. Enable Gmail API:
   - Go to "APIs & Services" → "Library"
   - Search "Gmail API"
   - Click "Enable"
4. Create OAuth credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: "Desktop app"
   - Name: "AutoXMail v2"
   - Click "Create"
5. Download credentials:
   - Click download icon next to your OAuth client
   - Save as `credentials.json`

## Step 3: Install AutoXMail v2

### Option A: Python (Recommended for testing)

```bash
# Clone repository
git clone https://github.com/NanoToolz/AutoXMail_v2.git
cd AutoXMail_v2

# Run setup
python3 setup.py
```

Enter your bot token and chat ID when prompted.

```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start bot
python main.py
```

### Option B: Docker (Recommended for production)

```bash
# Clone repository
git clone https://github.com/NanoToolz/AutoXMail_v2.git
cd AutoXMail_v2

# Run setup
python3 setup.py

# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
```

## Step 4: Add Gmail Account

1. Open Telegram and find your bot
2. Send `/start`
3. Click "➕ Add Account"
4. Upload your `credentials.json` file
5. Click the authorization link
6. Sign in to Gmail and grant permissions
7. Copy the ENTIRE URL from browser (starts with `http://localhost/?code=...`)
8. Send the URL to bot
9. Done! ✅

## Step 5: Use the Bot

### Main Menu
- 📧 My Accounts - View connected accounts
- 📬 Inbox - Browse your inbox
- 🔍 Search - Search messages
- 🏷️ Labels - Manage labels
- ⚙️ Settings - Configure notifications

### View Messages
1. Click "📬 Inbox"
2. Click any message to view
3. Use action buttons:
   - ✅ Mark Read/Unread
   - 🗑️ Delete
   - ⚠️ Mark as Spam
   - 🏷️ Manage Labels

## Troubleshooting

### Bot not responding?

```bash
# Check if running
docker ps  # or: ps aux | grep python

# View logs
docker logs autoxmail_v2  # or: tail -f logs/autoxmail.log
```

### OAuth error?

Make sure:
- Redirect URI in Google Console is `http://localhost`
- You copied the ENTIRE URL (including `http://localhost/?code=...`)
- Credentials.json is valid JSON

### Rate limit error?

Wait 1 minute. Rate limit: 30 requests/minute per user.

### Database locked?

```bash
# Stop bot
docker stop autoxmail_v2

# Remove lock
rm data/autoxmail.db-journal

# Start bot
docker start autoxmail_v2
```

## Configuration

Edit `.env` file:

```env
# Required
BOT_TOKEN=your_bot_token
ADMIN_CHAT_ID=your_chat_id
MASTER_KEY=auto_generated

# Optional
MAX_ACCOUNTS_PER_USER=3
LOG_TOPIC_ID=
WEBHOOK_URL=
WEBHOOK_SECRET=
```

## Commands

- `/start` - Main menu
- `/help` - Help message

## Security Tips

1. ✅ Keep `.env` file secure (never commit to git)
2. ✅ Keep `MASTER_KEY` safe (can't decrypt without it)
3. ✅ Use strong bot token
4. ✅ Don't share credentials.json
5. ✅ Enable 2FA on Gmail account

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- Read [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- Check [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for feature list

## Need Help?

- GitHub Issues: https://github.com/NanoToolz/AutoXMail_v2/issues
- Email: theasimgrphics@gmail.com

---

**Enjoy AutoXMail v2!** 🎉

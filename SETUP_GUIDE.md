# AutoXMail Bot v3.0 - Complete Setup Guide

**Complete step-by-step setup guide for Azure Debian VM**

---

## Prerequisites

- Azure Debian VM (or any Linux server)
- Domain name (optional, for webhook)
- Telegram account
- Google Cloud account

---

## Step 1: Create Telegram Bot

### 1.1 Talk to BotFather

```
1. Open Telegram and search for @BotFather
2. Send: /newbot
3. Enter bot name: AutoXMail Bot
4. Enter username: autoxmail_bot (must end with 'bot')
5. Copy the bot token (looks like: 8251153745:AAHCRzRI0KNWj-rCM-e6TSax3BYcGY8eSPo)
```

### 1.2 Get Your Chat ID

```
1. Send any message to your new bot
2. Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
3. Look for "chat":{"id":8034712119} - this is your ADMIN_CHAT_ID
```

---

## Step 2: Setup Google Cloud Project

### 2.1 Create Project

```
1. Go to: https://console.cloud.google.com
2. Click "Select a project" → "New Project"
3. Name: AutoXMail Bot
4. Click "Create"
```

### 2.2 Enable Gmail API

```
1. Go to: APIs & Services → Library
2. Search: Gmail API
3. Click "Enable"
```

### 2.3 Create OAuth Credentials

```
1. Go to: APIs & Services → Credentials
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: Web application
4. Name: AutoXMail Bot
5. Authorized redirect URIs:
   - http://localhost:8080/oauth/callback
   - https://your-domain.com/oauth/callback (if using webhook)
6. Click "Create"
7. Download JSON file (client_secret.json)
```

### 2.4 Configure OAuth Consent Screen

```
1. Go to: APIs & Services → OAuth consent screen
2. User Type: External
3. App name: AutoXMail Bot
4. User support email: your-email@gmail.com
5. Developer contact: your-email@gmail.com
6. Scopes: Add Gmail API scopes:
   - https://www.googleapis.com/auth/gmail.modify
   - https://www.googleapis.com/auth/gmail.send
   - https://www.googleapis.com/auth/gmail.compose
7. Test users: Add your Gmail address
8. Click "Save and Continue"
```

---

## Step 3: Setup Azure Debian VM

### 3.1 SSH into VM

```bash
ssh vm-01@your-vm-ip
```

### 3.2 Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y podman git python3 python3-pip python3-venv

# Verify installations
podman --version
git --version
python3 --version
```

### 3.3 Clone Repository

```bash
# Clone from GitHub
git clone https://github.com/NanoToolz/AutoXMail_Bot.git
cd AutoXMail_Bot

# Or if you have local changes, push first then clone
```

---

## Step 4: Configure Environment

### 4.1 Create .env File

```bash
# Copy example
cp config/.env.example .env

# Edit with your values
nano .env
```

### 4.2 .env Configuration

```env
# Telegram Bot
BOT_TOKEN=8251153745:AAHCRzRI0KNWj-rCM-e6TSax3BYcGY8eSPo
ADMIN_CHAT_ID=8034712119
LOG_TOPIC_ID=

# Security (IMPORTANT: Change these!)
MASTER_KEY=AdminMasterKey2026SecureEncryption
JWT_SECRET=YourSecureJWTSecret2026RandomString

# Limits
MAX_ACCOUNTS_PER_USER=3

# Webhook (Optional - for push notifications)
WEBHOOK_URL=
WEBHOOK_SECRET=
PUBSUB_TOPIC=
PUBSUB_PROJECT_ID=
```

**IMPORTANT:** Generate secure keys:
```bash
# Generate MASTER_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate JWT_SECRET
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4.3 Upload Google OAuth Credentials

```bash
# Create config directory if not exists
mkdir -p config

# Upload client_secret.json to VM
# Option 1: Using SCP from local machine
scp client_secret.json vm-01@your-vm-ip:~/AutoXMail_Bot/config/

# Option 2: Copy-paste content
nano config/client_secret.json
# Paste the JSON content, save with Ctrl+X, Y, Enter
```

---

## Step 5: Create Required Directories

```bash
# Create data and logs directories
mkdir -p data logs

# Set proper permissions (CRITICAL for Docker)
chmod 777 data logs

# Verify
ls -la | grep -E "data|logs"
# Should show: drwxrwxrwx
```

---

## Step 6: Build Docker Image

```bash
# Build the image
podman build -t autoxmail-bot -f config/Dockerfile .

# Verify image created
podman images | grep autoxmail
```

**Expected output:**
```
localhost/autoxmail-bot  latest  abc123def456  2 minutes ago  150 MB
```

---

## Step 7: Run the Bot

### 7.1 Start Container

```bash
# Run in detached mode
podman run -d \
  --name autoxmail_bot \
  --restart always \
  --env-file .env \
  -v ./data:/app/data:rw \
  -v ./logs:/app/logs:rw \
  --memory 150m \
  autoxmail-bot

# Check if running
podman ps
```

### 7.2 View Logs

```bash
# Follow logs in real-time
podman logs -f autoxmail_bot

# View last 50 lines
podman logs --tail 50 autoxmail_bot
```

**Expected output:**
```
2026-02-22 19:00:00,000 - __main__ - INFO - Starting AutoXMail Bot...
2026-02-22 19:00:00,100 - __main__ - INFO - Bot started successfully!
2026-02-22 19:00:00,100 - __main__ - INFO - Admin chat: 8034712119
2026-02-22 19:00:00,100 - __main__ - INFO - Max accounts per user: 3
2026-02-22 19:00:00,500 - __main__ - INFO - Initializing database...
2026-02-22 19:00:00,600 - __main__ - INFO - Database initialized successfully
2026-02-22 19:00:00,700 - __main__ - INFO - Bot is running!
```

---

## Step 8: Test the Bot

### 8.1 Send /start Command

```
1. Open Telegram
2. Search for your bot (@autoxmail_bot)
3. Send: /start
```

**Expected response:**
```
ᴀᴜᴛᴏxᴍᴀɪʟ · ᴡᴇʟᴄᴏᴍᴇ
────────────────────────
Welcome to AutoXMail Bot!

Manage your Gmail accounts directly from Telegram.

[➕ ᴀᴅᴅ ᴀᴄᴄᴏᴜɴᴛ] [ℹ️ ʜᴇʟᴘ]
```

### 8.2 Add Gmail Account

```
1. Click [➕ ᴀᴅᴅ ᴀᴄᴄᴏᴜɴᴛ]
2. Bot will send OAuth URL
3. Click the URL
4. Login with your Gmail
5. Grant permissions
6. Copy the authorization code
7. Send code to bot
```

### 8.3 Test Inbox

```
1. Click [📥 ɪɴʙᴏx]
2. Select time range (e.g., Last 24 hours)
3. Bot should show your recent emails
```

---

## Step 9: Container Management

### 9.1 Stop Bot

```bash
podman stop autoxmail_bot
```

### 9.2 Start Bot

```bash
podman start autoxmail_bot
```

### 9.3 Restart Bot

```bash
podman restart autoxmail_bot
```

### 9.4 Remove Container

```bash
# Stop first
podman stop autoxmail_bot

# Remove
podman rm autoxmail_bot
```

### 9.5 Rebuild After Code Changes

```bash
# Stop and remove old container
podman stop autoxmail_bot
podman rm autoxmail_bot

# Pull latest code
git pull origin main

# Rebuild image
podman build -t autoxmail-bot -f config/Dockerfile .

# Run new container
podman run -d \
  --name autoxmail_bot \
  --restart always \
  --env-file .env \
  -v ./data:/app/data:rw \
  -v ./logs:/app/logs:rw \
  --memory 150m \
  autoxmail-bot
```

---

## Step 10: Enable Auto-Start on Boot

### 10.1 Create Systemd Service

```bash
# Create service file
sudo nano /etc/systemd/system/autoxmail-bot.service
```

**Service file content:**
```ini
[Unit]
Description=AutoXMail Telegram Bot
After=network.target

[Service]
Type=simple
User=vm-01
WorkingDirectory=/home/vm-01/AutoXMail_Bot
ExecStart=/usr/bin/podman start -a autoxmail_bot
ExecStop=/usr/bin/podman stop autoxmail_bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 10.2 Enable Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable autoxmail-bot.service

# Start service
sudo systemctl start autoxmail-bot.service

# Check status
sudo systemctl status autoxmail-bot.service
```

---

## Step 11: Setup Webhook (Optional)

**Only if you want push notifications for new emails**

### 11.1 Setup Domain & SSL

```bash
# Install Nginx
sudo apt install -y nginx certbot python3-certbot-nginx

# Configure Nginx
sudo nano /etc/nginx/sites-available/autoxmail
```

**Nginx config:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /webhook/push {
        proxy_pass http://localhost:8443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/autoxmail /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

### 11.2 Update .env

```env
WEBHOOK_URL=https://your-domain.com
WEBHOOK_SECRET=YourWebhookSecret123
```

### 11.3 Restart Bot

```bash
podman restart autoxmail_bot
```

---

## Troubleshooting

### Issue 1: Database Permission Error

**Error:** `sqlite3.OperationalError: unable to open database file`

**Fix:**
```bash
chmod 777 data logs
podman restart autoxmail_bot
```

### Issue 2: Bot Not Responding

**Check logs:**
```bash
podman logs --tail 100 autoxmail_bot
```

**Common causes:**
- Wrong BOT_TOKEN
- Network issues
- Container not running

### Issue 3: OAuth Not Working

**Check:**
1. client_secret.json exists in config/
2. OAuth consent screen configured
3. Test users added
4. Redirect URI matches

### Issue 4: Container Keeps Restarting

**Check logs:**
```bash
podman logs autoxmail_bot
```

**Common causes:**
- Missing .env variables
- Invalid MASTER_KEY
- Database corruption

**Fix database:**
```bash
# Backup first
cp data/autoxmail.db data/autoxmail.db.backup

# Remove and recreate
rm data/autoxmail.db
podman restart autoxmail_bot
```

### Issue 5: Out of Memory

**Increase memory limit:**
```bash
podman stop autoxmail_bot
podman rm autoxmail_bot

# Run with more memory
podman run -d \
  --name autoxmail_bot \
  --restart always \
  --env-file .env \
  -v ./data:/app/data:rw \
  -v ./logs:/app/logs:rw \
  --memory 256m \
  autoxmail-bot
```

---

## Monitoring

### Check Container Status

```bash
# Container status
podman ps -a | grep autoxmail

# Resource usage
podman stats autoxmail_bot

# Disk usage
du -sh data/ logs/
```

### View Logs

```bash
# Real-time logs
podman logs -f autoxmail_bot

# Last 100 lines
podman logs --tail 100 autoxmail_bot

# Logs with timestamps
podman logs --timestamps autoxmail_bot

# Save logs to file
podman logs autoxmail_bot > bot_logs.txt
```

### Database Backup

```bash
# Create backup
cp data/autoxmail.db data/autoxmail.db.$(date +%Y%m%d_%H%M%S)

# Automated daily backup (crontab)
crontab -e

# Add this line:
0 2 * * * cp /home/vm-01/AutoXMail_Bot/data/autoxmail.db /home/vm-01/AutoXMail_Bot/data/autoxmail.db.$(date +\%Y\%m\%d)
```

---

## Security Best Practices

1. **Never commit .env file**
   - Already in .gitignore
   - Contains sensitive tokens

2. **Use strong MASTER_KEY**
   - Minimum 32 characters
   - Random alphanumeric

3. **Restrict VM access**
   - Use SSH keys only
   - Disable password authentication
   - Configure firewall

4. **Regular updates**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

5. **Monitor logs**
   - Check for suspicious activity
   - Set up log rotation

6. **Backup database**
   - Daily automated backups
   - Store off-server

---

## Useful Commands

```bash
# Quick restart
podman restart autoxmail_bot && podman logs -f autoxmail_bot

# Check if bot is responding
curl -s https://api.telegram.org/bot<BOT_TOKEN>/getMe

# View container details
podman inspect autoxmail_bot

# Execute command in container
podman exec -it autoxmail_bot python -c "print('Hello')"

# Copy file from container
podman cp autoxmail_bot:/app/data/autoxmail.db ./backup.db

# View environment variables
podman exec autoxmail_bot env | grep BOT
```

---

## Next Steps

1. ✅ Bot is running
2. ✅ Test all features
3. ✅ Add your Gmail accounts
4. ✅ Configure notifications
5. ✅ Setup webhook (optional)
6. ✅ Enable auto-start
7. ✅ Setup monitoring
8. ✅ Configure backups

---

## Support

- **GitHub Issues:** https://github.com/NanoToolz/AutoXMail_Bot/issues
- **Email:** theasimgrphics@gmail.com
- **Documentation:** Check docs/ folder

---

## Quick Reference

```bash
# Start bot
podman start autoxmail_bot

# Stop bot
podman stop autoxmail_bot

# View logs
podman logs -f autoxmail_bot

# Restart bot
podman restart autoxmail_bot

# Rebuild bot
git pull && podman build -t autoxmail-bot -f config/Dockerfile . && podman restart autoxmail_bot

# Check status
podman ps | grep autoxmail
```

---

**Setup Complete! Bot is ready to use.** 🚀

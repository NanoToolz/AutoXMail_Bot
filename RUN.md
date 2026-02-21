# Run AutoXMail Bot in Podman Container

## Quick Start

### Step 1: Setup Environment

```bash
cd AutoXMail_Bot

# Copy example env file
cp config/.env.example .env

# Edit .env file with your details
nano .env
```

Add these values:
```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_CHAT_ID=your_telegram_chat_id
MASTER_KEY=generate_random_32_char_key
MAX_ACCOUNTS_PER_USER=3
```

### Step 2: Build Image

```bash
podman build -t autoxmail-bot -f config/Dockerfile .
```

### Step 3: Run Container

```bash
podman run -d \
    --name autoxmail_bot \
    --restart always \
    --env-file .env \
    -v ./data:/app/data:rw \
    -v ./logs:/app/logs:rw \
    --memory 100m \
    autoxmail-bot
```

### Step 4: Check Logs

```bash
podman logs -f autoxmail_bot
```

## Using Docker Compose

```bash
cd AutoXMail_Bot

# Setup .env first
cp config/.env.example .env
nano .env

# Run with compose
podman-compose -f config/docker-compose.yml up -d

# Or use docker-compose
docker-compose -f config/docker-compose.yml up -d
```

## Management Commands

```bash
# Check status
podman ps

# View logs
podman logs autoxmail_bot

# Follow logs
podman logs -f autoxmail_bot

# Stop bot
podman stop autoxmail_bot

# Start bot
podman start autoxmail_bot

# Restart bot
podman restart autoxmail_bot

# Remove container
podman stop autoxmail_bot
podman rm autoxmail_bot

# Check resource usage
podman stats autoxmail_bot
```

## Troubleshooting

### Container won't start
```bash
# Check logs
podman logs autoxmail_bot

# Check if .env is correct
cat .env

# Rebuild image
podman build -t autoxmail-bot -f config/Dockerfile . --no-cache
```

### Permission errors
```bash
# Fix data folder permissions
chmod 777 data logs
```

### Memory issues
```bash
# Increase memory limit
podman update --memory 150m autoxmail_bot
podman restart autoxmail_bot
```

## Production Setup

```bash
# Create systemd service
sudo nano /etc/systemd/system/autoxmail-bot.service
```

Add:
```ini
[Unit]
Description=AutoXMail Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/AutoXMail_Bot
ExecStart=/usr/bin/podman start -a autoxmail_bot
ExecStop=/usr/bin/podman stop -t 10 autoxmail_bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable autoxmail-bot
sudo systemctl start autoxmail-bot
sudo systemctl status autoxmail-bot
```

---

**Ready to use!** 🚀

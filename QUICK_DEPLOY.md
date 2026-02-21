# Quick Deploy to Azure Debian VM

## One-Command Deployment

```bash
# SSH into your Azure VM
ssh vm-01@your-vm-ip

# Run deployment script
curl -sSL https://raw.githubusercontent.com/NanoToolz/AutoXMail_Bot/main/DEPLOY_AZURE.sh | bash
```

## Manual Deployment

### Step 1: SSH into VM
```bash
ssh vm-01@your-vm-ip
```

### Step 2: Install Dependencies
```bash
sudo apt update
sudo apt install -y podman git python3 python3-pip python3-venv
```

### Step 3: Clone Repository
```bash
git clone https://github.com/NanoToolz/AutoXMail_Bot.git
cd AutoXMail_Bot
```

### Step 4: Setup Environment
```bash
# Run setup script
python3 config/setup.py

# It will ask for:
# - BOT_TOKEN (from @BotFather)
# - ADMIN_CHAT_ID (your Telegram ID)
# - LOG_TOPIC_ID (optional)
```

### Step 5: Build & Run
```bash
# Build image
podman build -t autoxmail-bot -f config/Dockerfile .

# Run container
podman run -d \
    --name autoxmail_bot \
    --restart always \
    --env-file .env \
    -v ./data:/app/data:rw \
    -v ./logs:/app/logs:rw \
    --memory 100m \
    autoxmail-bot

# Check logs
podman logs -f autoxmail_bot
```

## Management Commands

```bash
# Check status
podman ps

# View logs
podman logs autoxmail_bot

# Follow logs (live)
podman logs -f autoxmail_bot

# Stop bot
podman stop autoxmail_bot

# Start bot
podman start autoxmail_bot

# Restart bot
podman restart autoxmail_bot

# Check resource usage
podman stats autoxmail_bot
```

## Update Bot

```bash
cd AutoXMail_Bot

# Pull latest code
git pull origin main

# Rebuild image
podman build -t autoxmail-bot -f config/Dockerfile .

# Restart container
podman stop autoxmail_bot
podman rm autoxmail_bot

podman run -d \
    --name autoxmail_bot \
    --restart always \
    --env-file .env \
    -v ./data:/app/data:rw \
    -v ./logs:/app/logs:rw \
    --memory 100m \
    autoxmail-bot
```

## Troubleshooting

### Bot not starting?
```bash
# Check logs
podman logs autoxmail_bot

# Check .env file
cat .env

# Rebuild without cache
podman build -t autoxmail-bot -f config/Dockerfile . --no-cache
```

### Permission errors?
```bash
# Fix permissions
chmod 777 data logs
```

### Memory issues?
```bash
# Increase memory
podman update --memory 150m autoxmail_bot
podman restart autoxmail_bot
```

## Setup Systemd (Auto-start on boot)

```bash
# Create service file
sudo nano /etc/systemd/system/autoxmail-bot.service
```

Add:
```ini
[Unit]
Description=AutoXMail Bot
After=network.target

[Service]
Type=simple
User=vm-01
WorkingDirectory=/home/vm-01/AutoXMail_Bot
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

**Bot is now running on Azure VM!** 🚀

Access via Telegram and start using!

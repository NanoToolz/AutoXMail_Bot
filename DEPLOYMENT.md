# AutoXMail v2 - Deployment Guide

## Prerequisites

- Python 3.11+
- Docker/Podman (for containerized deployment)
- Telegram Bot Token
- Google Cloud Project with Gmail API enabled

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/NanoToolz/AutoXMail_v2.git
cd AutoXMail_v2
```

### 2. Run Setup

```bash
python3 setup.py
```

This will:
- Create `.env` file
- Generate master encryption key
- Create data/ and logs/ directories

### 3. Configure Environment

Edit `.env` file:

```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_CHAT_ID=your_chat_id
MASTER_KEY=auto_generated_key
MAX_ACCOUNTS_PER_USER=3
```

### 4. Start Bot

**Option A: Direct Python**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**Option B: Docker Compose**
```bash
docker-compose up -d
```

**Option C: Podman**
```bash
podman build -t autoxmail-v2 .
podman run -d \
    --name autoxmail_v2 \
    --restart always \
    --env-file .env \
    -v ./data:/app/data:rw \
    -v ./logs:/app/logs:rw \
    --memory 100m \
    autoxmail-v2
```

## Production Deployment

### Azure VM Setup

#### 1. Create VM

```bash
# Create Debian VM
az vm create \
    --resource-group myResourceGroup \
    --name autoxmail-vm \
    --image Debian11 \
    --size Standard_B1s \
    --admin-username azureuser \
    --generate-ssh-keys
```

#### 2. Install Dependencies

```bash
# SSH into VM
ssh azureuser@<vm-ip>

# Update system
sudo apt update && sudo apt upgrade -y

# Install Podman
sudo apt install -y podman

# Install Python (if running directly)
sudo apt install -y python3.11 python3.11-venv python3-pip
```

#### 3. Deploy Application

```bash
# Clone repository
git clone https://github.com/NanoToolz/AutoXMail_v2.git
cd AutoXMail_v2

# Setup
python3 setup.py

# Build and run
podman build -t autoxmail-v2 .
podman run -d \
    --name autoxmail_v2 \
    --restart always \
    --env-file .env \
    -v ./data:/app/data:rw \
    -v ./logs:/app/logs:rw \
    --memory 100m \
    autoxmail-v2
```

#### 4. Setup Systemd Service

Create `/etc/systemd/system/autoxmail-v2.service`:

```ini
[Unit]
Description=AutoXMail v2 Bot
After=network.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=/home/azureuser/AutoXMail_v2
ExecStart=/usr/bin/podman start -a autoxmail_v2
ExecStop=/usr/bin/podman stop -t 10 autoxmail_v2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable autoxmail-v2
sudo systemctl start autoxmail-v2
```

### Security Hardening

#### 1. Firewall

```bash
# Install UFW
sudo apt install -y ufw

# Allow SSH
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable
```

#### 2. SSH Hardening

Edit `/etc/ssh/sshd_config`:

```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

Restart SSH:
```bash
sudo systemctl restart sshd
```

#### 3. Automatic Updates

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

#### 4. File Permissions

```bash
chmod 600 .env
chmod 700 data/
chmod 700 logs/
```

## Monitoring

### Check Container Status

```bash
# Podman
podman ps
podman logs -f autoxmail_v2
podman stats autoxmail_v2

# Docker
docker ps
docker logs -f autoxmail_v2
docker stats autoxmail_v2
```

### Check System Resources

```bash
# Memory usage
free -h

# Disk usage
df -h

# Process list
ps aux | grep python
```

### View Logs

```bash
# Application logs
tail -f logs/autoxmail.log

# Container logs
podman logs --tail 100 -f autoxmail_v2

# System logs
journalctl -u autoxmail-v2 -f
```

## Backup & Restore

### Backup

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/autoxmail_v2"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
cp data/autoxmail.db $BACKUP_DIR/autoxmail_${DATE}.db

# Backup .env
cp .env $BACKUP_DIR/env_${DATE}.backup

# Compress
tar -czf $BACKUP_DIR/autoxmail_${DATE}.tar.gz \
    $BACKUP_DIR/autoxmail_${DATE}.db \
    $BACKUP_DIR/env_${DATE}.backup

# Cleanup
rm $BACKUP_DIR/autoxmail_${DATE}.db
rm $BACKUP_DIR/env_${DATE}.backup

echo "Backup created: $BACKUP_DIR/autoxmail_${DATE}.tar.gz"
```

### Restore

```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./restore.sh <backup_file.tar.gz>"
    exit 1
fi

# Stop bot
podman stop autoxmail_v2

# Extract backup
tar -xzf $BACKUP_FILE -C /tmp/

# Restore database
cp /tmp/backup/autoxmail_v2/autoxmail_*.db data/autoxmail.db

# Restore .env
cp /tmp/backup/autoxmail_v2/env_*.backup .env

# Start bot
podman start autoxmail_v2

echo "Restore complete!"
```

## Troubleshooting

### Bot Not Starting

```bash
# Check logs
podman logs autoxmail_v2

# Check environment
podman exec autoxmail_v2 env

# Verify .env file
cat .env
```

### Database Locked

```bash
# Stop bot
podman stop autoxmail_v2

# Check for locks
lsof data/autoxmail.db

# Remove lock file
rm data/autoxmail.db-journal

# Start bot
podman start autoxmail_v2
```

### Memory Issues

```bash
# Check memory usage
podman stats autoxmail_v2

# Increase limit (if needed)
podman update --memory 150m autoxmail_v2

# Restart
podman restart autoxmail_v2
```

### OAuth Errors

```bash
# Verify credentials format
cat credentials.json | jq .

# Check redirect URI
# Must be: http://localhost

# Re-authorize account
# Delete account and add again
```

## Maintenance

### Daily Tasks

- Check bot status: `podman ps`
- Review logs: `podman logs --tail 50 autoxmail_v2`

### Weekly Tasks

- Check disk space: `df -h`
- Review error logs: `grep ERROR logs/autoxmail.log`
- Backup database: `./backup.sh`

### Monthly Tasks

- Update system: `sudo apt update && sudo apt upgrade`
- Rebuild container: `podman build -t autoxmail-v2 .`
- Rotate logs: `logrotate /etc/logrotate.d/autoxmail`
- Review security: Check for CVEs

## Scaling

### Vertical Scaling

Increase container resources:

```bash
podman update --memory 200m --cpus 1.0 autoxmail_v2
```

### Database Optimization

```bash
# Vacuum database
sqlite3 data/autoxmail.db "VACUUM;"

# Analyze tables
sqlite3 data/autoxmail.db "ANALYZE;"
```

### Log Rotation

Create `/etc/logrotate.d/autoxmail`:

```
/home/azureuser/AutoXMail_v2/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 azureuser azureuser
}
```

## Updates

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild container
podman build -t autoxmail-v2 .

# Stop old container
podman stop autoxmail_v2
podman rm autoxmail_v2

# Start new container
podman run -d \
    --name autoxmail_v2 \
    --restart always \
    --env-file .env \
    -v ./data:/app/data:rw \
    -v ./logs:/app/logs:rw \
    --memory 100m \
    autoxmail-v2
```

### Database Migration

```bash
# Backup first!
./backup.sh

# Run migration script (if provided)
python migrate.py

# Verify
sqlite3 data/autoxmail.db ".schema"
```

---

**Need Help?**
- GitHub Issues: https://github.com/NanoToolz/AutoXMail_v2/issues
- Email: theasimgrphics@gmail.com

**Version:** 2.0.0  
**Last Updated:** February 21, 2026

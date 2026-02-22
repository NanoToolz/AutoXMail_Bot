#!/bin/bash
# AutoXMail Bot - Fresh Setup Script
# Removes old installation and sets up v3.0 from scratch

set -e

echo "🚀 AutoXMail Bot v3.0 - Fresh Setup"
echo "===================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}❌ Don't run as root! Run as regular user.${NC}"
    exit 1
fi

echo -e "${YELLOW}⚠️  WARNING: This will remove ALL existing AutoXMail data!${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Setup cancelled."
    exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Cleaning Old Installation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Stop and remove old containers
echo "🗑️  Stopping old containers..."
podman stop autoxmail_bot 2>/dev/null || true
podman stop autoxmail-bot 2>/dev/null || true
podman rm autoxmail_bot 2>/dev/null || true
podman rm autoxmail-bot 2>/dev/null || true

# Remove old images
echo "🗑️  Removing old images..."
podman rmi autoxmail-bot 2>/dev/null || true
podman rmi localhost/autoxmail-bot 2>/dev/null || true

# Backup old data if exists
if [ -d "AutoXMail_Bot/data" ]; then
    echo "💾 Backing up old data..."
    timestamp=$(date +%Y%m%d_%H%M%S)
    mkdir -p ~/autoxmail_backups
    cp -r AutoXMail_Bot/data ~/autoxmail_backups/data_$timestamp 2>/dev/null || true
    cp -r AutoXMail_Bot/logs ~/autoxmail_backups/logs_$timestamp 2>/dev/null || true
    echo -e "${GREEN}✅ Backup saved to: ~/autoxmail_backups/${NC}"
fi

# Remove old directory
echo "🗑️  Removing old installation..."
rm -rf AutoXMail_Bot 2>/dev/null || true

echo -e "${GREEN}✅ Cleanup complete!${NC}"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: Installing Dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "📦 Updating system packages..."
sudo apt update -qq

echo "📦 Installing required packages..."
sudo apt install -y podman git python3 python3-pip python3-venv >/dev/null 2>&1

echo -e "${GREEN}✅ Dependencies installed!${NC}"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3: Cloning Repository"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "📥 Cloning from GitHub..."
git clone https://github.com/NanoToolz/AutoXMail_Bot.git
cd AutoXMail_Bot

echo -e "${GREEN}✅ Repository cloned!${NC}"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4: Environment Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if .env already exists
if [ -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file already exists${NC}"
    read -p "Keep existing .env? (y/N): " keep_env
    if [ "$keep_env" != "y" ]; then
        rm .env
        echo "🔧 Creating new .env file..."
        python3 config/setup.py
    else
        echo "✅ Keeping existing .env"
    fi
else
    echo "🔧 Creating .env file..."
    python3 config/setup.py
fi

echo ""
echo -e "${GREEN}✅ Environment configured!${NC}"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 5: Creating Directories"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "📁 Creating data and logs directories..."
mkdir -p data logs

echo "🔒 Setting permissions..."
chmod 777 data logs

echo -e "${GREEN}✅ Directories created!${NC}"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 6: Building Docker Image"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "🔨 Building container image..."
podman build -t autoxmail-bot -f config/Dockerfile . 

echo -e "${GREEN}✅ Image built successfully!${NC}"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 7: Starting Bot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "🚀 Starting container..."
podman run -d \
    --name autoxmail_bot \
    --restart always \
    --env-file .env \
    -v ./data:/app/data:rw \
    -v ./logs:/app/logs:rw \
    --memory 150m \
    autoxmail-bot

echo ""
echo "⏳ Waiting for bot to start..."
sleep 3

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 8: Checking Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if container is running
if podman ps | grep -q autoxmail_bot; then
    echo -e "${GREEN}✅ Container is running!${NC}"
    echo ""
    podman ps | grep autoxmail_bot
else
    echo -e "${RED}❌ Container failed to start!${NC}"
    echo ""
    echo "Checking logs..."
    podman logs autoxmail_bot
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 9: Viewing Logs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "📝 Last 20 lines of logs:"
echo ""
podman logs --tail 20 autoxmail_bot

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📱 Next Steps:"
echo "   1. Open Telegram and search for your bot"
echo "   2. Send /start command"
echo "   3. Add your Gmail account"
echo ""
echo "📊 Useful Commands:"
echo "   View logs:    podman logs -f autoxmail_bot"
echo "   Stop bot:     podman stop autoxmail_bot"
echo "   Start bot:    podman start autoxmail_bot"
echo "   Restart bot:  podman restart autoxmail_bot"
echo ""
echo "📖 Documentation:"
echo "   Setup Guide:  cat SETUP_GUIDE.md"
echo "   Quick Deploy: cat QUICK_DEPLOY.md"
echo ""
echo "🆘 Support:"
echo "   GitHub: https://github.com/NanoToolz/AutoXMail_Bot"
echo "   Email:  theasimgrphics@gmail.com"
echo ""
echo -e "${GREEN}Bot is now running! 🚀${NC}"
echo ""

# Ask if user wants to follow logs
read -p "Do you want to follow logs now? (y/N): " follow_logs
if [ "$follow_logs" = "y" ]; then
    echo ""
    echo "Press Ctrl+C to stop viewing logs"
    echo ""
    sleep 2
    podman logs -f autoxmail_bot
fi

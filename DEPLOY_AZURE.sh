#!/bin/bash
# AutoXMail Bot - Azure Debian VM Deployment Script

set -e

echo "🚀 AutoXMail Bot - Azure Deployment"
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

echo "📦 Step 1: Installing Dependencies..."
sudo apt update
sudo apt install -y podman git python3 python3-pip python3-venv

echo ""
echo "📥 Step 2: Cloning Repository..."
if [ -d "AutoXMail_Bot" ]; then
    echo "Repository already exists, pulling latest..."
    cd AutoXMail_Bot
    git pull origin main
else
    git clone https://github.com/NanoToolz/AutoXMail_Bot.git
    cd AutoXMail_Bot
fi

echo ""
echo "⚙️  Step 3: Setting up Environment..."

# Create directories with proper permissions
mkdir -p data logs
chmod 777 data logs

# Check if .env exists
if [ -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file already exists${NC}"
    read -p "Overwrite? (y/N): " overwrite
    if [ "$overwrite" != "y" ]; then
        echo "Keeping existing .env"
    else
        rm .env
        python3 config/setup.py
    fi
else
    python3 config/setup.py
fi

echo ""
echo "🔨 Step 4: Building Container Image..."
podman build -t autoxmail-bot -f config/Dockerfile .

echo ""
echo "🗑️  Step 5: Cleaning up old container (if exists)..."
podman stop autoxmail_bot 2>/dev/null || true
podman rm autoxmail_bot 2>/dev/null || true

echo ""
echo "🚀 Step 6: Starting Container..."
podman run -d \
    --name autoxmail_bot \
    --restart always \
    --env-file .env \
    -v ./data:/app/data:rw \
    -v ./logs:/app/logs:rw \
    --memory 100m \
    autoxmail-bot

echo ""
echo "⏳ Waiting for container to start..."
sleep 3

echo ""
echo "📊 Step 7: Checking Status..."
podman ps | grep autoxmail_bot

echo ""
echo "📝 Step 8: Viewing Logs..."
echo "Press Ctrl+C to stop viewing logs"
echo ""
sleep 2
podman logs -f autoxmail_bot

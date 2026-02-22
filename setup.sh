#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#   AutoXMail Bot - Interactive Setup & Deployment
# ═══════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Icons
OK="${GREEN}✓${NC}"
FAIL="${RED}✘${NC}"
WAIT="${YELLOW}◌${NC}"
INFO="${BLUE}ℹ${NC}"

print_header() {
    echo -e "\n${CYAN}${BOLD}"
    echo "  ╔══════════════════════════════════════╗"
    echo "  ║     🤖 AutoXMail Bot Setup           ║"
    echo "  ╚══════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e " ${BOLD}${BLUE}▶ $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() { echo -e " ${OK}  ${GREEN}$1${NC}"; }
print_error() { echo -e " ${FAIL}  ${RED}$1${NC}"; }
print_warning() { echo -e " ${WAIT}  ${YELLOW}$1${NC}"; }
print_info() { echo -e " ${INFO}  ${BLUE}$1${NC}"; }

# Check if .env exists
ENV_FILE=".env"
ENV_EXISTS=false

if [ -f "$ENV_FILE" ]; then
    ENV_EXISTS=true
fi

print_header

# ═══════════════════════════════════════════════════════════════
# STEP 1: Configuration
# ═══════════════════════════════════════════════════════════════

print_step "Configuration Setup"

if [ "$ENV_EXISTS" = true ]; then
    echo -e "${YELLOW}Existing configuration found!${NC}"
    echo ""
    echo "1) Use existing configuration"
    echo "2) Reconfigure (enter new values)"
    echo ""
    read -p "Choose option [1/2]: " CONFIG_CHOICE
    
    if [ "$CONFIG_CHOICE" = "2" ]; then
        RECONFIGURE=true
    else
        RECONFIGURE=false
        print_success "Using existing configuration"
    fi
else
    RECONFIGURE=true
fi

if [ "$RECONFIGURE" = true ]; then
    echo ""
    print_info "Please provide the following information:"
    echo ""
    
    # Bot Token
    read -p "🤖 Telegram Bot Token: " BOT_TOKEN
    while [ -z "$BOT_TOKEN" ]; do
        print_error "Bot token cannot be empty!"
        read -p "🤖 Telegram Bot Token: " BOT_TOKEN
    done
    
    # Admin Chat ID
    read -p "👤 Admin Chat ID (your Telegram user ID): " ADMIN_CHAT_ID
    while [ -z "$ADMIN_CHAT_ID" ]; do
        print_error "Admin chat ID cannot be empty!"
        read -p "👤 Admin Chat ID: " ADMIN_CHAT_ID
    done
    
    # Master Key
    read -p "🔐 Master Encryption Key (min 16 chars): " MASTER_KEY
    while [ ${#MASTER_KEY} -lt 16 ]; do
        print_error "Master key must be at least 16 characters!"
        read -p "🔐 Master Encryption Key: " MASTER_KEY
    done
    
    # Max Accounts
    read -p "📧 Max accounts per user [default: 75]: " MAX_ACCOUNTS
    MAX_ACCOUNTS=${MAX_ACCOUNTS:-75}
    
    # Optional: Webhook URL
    read -p "🌐 Webhook URL (optional, press Enter to skip): " WEBHOOK_URL
    
    # Optional: GCP Project ID
    read -p "☁️  GCP Project ID (optional, press Enter to skip): " GCP_PROJECT_ID
    
    # Optional: Required Channel
    read -p "📢 Required Channel Username (optional, press Enter to skip): " REQUIRED_CHANNEL
    
    # Create .env file
    cat > "$ENV_FILE" << EOF
BOT_TOKEN=$BOT_TOKEN
ADMIN_CHAT_ID=$ADMIN_CHAT_ID
MASTER_KEY=$MASTER_KEY
MAX_ACCOUNTS_PER_USER=$MAX_ACCOUNTS
WEBHOOK_URL=$WEBHOOK_URL
GCP_PROJECT_ID=$GCP_PROJECT_ID
REQUIRED_CHANNEL=$REQUIRED_CHANNEL
EOF
    
    print_success "Configuration saved to .env"
fi

# ═══════════════════════════════════════════════════════════════
# STEP 2: Verify Python Syntax
# ═══════════════════════════════════════════════════════════════

print_step "Verifying Code Syntax"

if python3 -m py_compile src/main.py 2>/dev/null; then
    print_success "main.py syntax OK"
else
    print_error "main.py has syntax errors!"
    exit 1
fi

if python3 -m py_compile src/advanced_handlers.py 2>/dev/null; then
    print_success "advanced_handlers.py syntax OK"
else
    print_error "advanced_handlers.py has syntax errors!"
    exit 1
fi

# ═══════════════════════════════════════════════════════════════
# STEP 3: Stop & Remove Old Container
# ═══════════════════════════════════════════════════════════════

print_step "Cleaning Up Old Deployment"

if podman stop autoxmail_bot 2>/dev/null; then
    print_success "Old container stopped"
else
    print_info "No running container found"
fi

if podman rm autoxmail_bot 2>/dev/null; then
    print_success "Old container removed"
fi

if podman rmi autoxmail-bot 2>/dev/null; then
    print_success "Old image removed"
fi

# ═══════════════════════════════════════════════════════════════
# STEP 4: Build Container Image
# ═══════════════════════════════════════════════════════════════

print_step "Building Container Image"
print_info "This may take 2-3 minutes..."

if podman build --no-cache -t autoxmail-bot -f config/Dockerfile . > /tmp/build.log 2>&1; then
    print_success "Image built successfully"
else
    print_error "Build failed! Check /tmp/build.log"
    tail -20 /tmp/build.log
    exit 1
fi

# ═══════════════════════════════════════════════════════════════
# STEP 5: Start Container
# ═══════════════════════════════════════════════════════════════

print_step "Starting AutoXMail Bot"

# Calculate memory limit (25% of total RAM)
MEM_LIMIT=$(awk '/MemTotal/ {printf "%dm", int(($2/1024)*0.25)}' /proc/meminfo)
print_info "Memory limit: ${MEM_LIMIT}"

# Create data and logs directories
mkdir -p data logs

# Start container
CONTAINER_ID=$(podman run -d \
  --name autoxmail_bot \
  --restart always \
  --env-file .env \
  -v ./data:/app/data:rw \
  -v ./logs:/app/logs:rw \
  --memory "$MEM_LIMIT" \
  --memory-swap "$MEM_LIMIT" \
  autoxmail-bot 2>&1)

if [ $? -eq 0 ]; then
    print_success "Container started: ${CONTAINER_ID:0:12}"
else
    print_error "Failed to start container"
    echo "$CONTAINER_ID"
    exit 1
fi

# Wait for initialization
print_info "Waiting for bot to initialize..."
sleep 5

# ═══════════════════════════════════════════════════════════════
# STEP 6: Verify Deployment
# ═══════════════════════════════════════════════════════════════

print_step "Verifying Deployment"

# Check if container is running
if podman ps | grep -q autoxmail_bot; then
    print_success "Bot is running!"
    
    # Show container info
    echo ""
    print_info "Container Status:"
    podman ps --filter "name=autoxmail_bot" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    # Check logs for errors
    echo ""
    print_info "Recent Logs:"
    podman logs --tail 10 autoxmail_bot
    
else
    print_error "Bot failed to start!"
    echo ""
    print_info "Error Logs:"
    podman logs --tail 30 autoxmail_bot
    exit 1
fi

# ═══════════════════════════════════════════════════════════════
# Success!
# ═══════════════════════════════════════════════════════════════

echo ""
echo -e "${GREEN}${BOLD}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║     ✓ Deployment Successful!         ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${CYAN}Useful Commands:${NC}"
echo -e "  ${BOLD}View logs:${NC}      podman logs -f autoxmail_bot"
echo -e "  ${BOLD}Stop bot:${NC}       podman stop autoxmail_bot"
echo -e "  ${BOLD}Start bot:${NC}      podman start autoxmail_bot"
echo -e "  ${BOLD}Restart bot:${NC}    podman restart autoxmail_bot"
echo -e "  ${BOLD}Check status:${NC}   podman ps"
echo ""

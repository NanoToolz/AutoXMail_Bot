#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#   AutoXMail Bot - Fix & Deploy Script
#   Fixes method name mismatches and deploys with visual feedback
# ═══════════════════════════════════════════════════════════════

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Symbols
CHECK="✓"
CROSS="✗"
ARROW="→"

# Functions
print_header() {
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
}

print_step() {
    echo -e "${BLUE}${ARROW}${NC} $1"
}

print_success() {
    echo -e "${GREEN}${CHECK}${NC} $1"
}

print_error() {
    echo -e "${RED}${CROSS}${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Start
clear
print_header "AutoXMail Bot - Fix & Deploy"

# Step 1: Fix method names in main.py
print_step "Fixing method name mismatches in main.py..."
sed -i 's/advanced_handlers\.add_to_blocklist\b/advanced_handlers.add_to_blocklist_handler/g' src/main.py
sed -i 's/advanced_handlers\.add_vip_sender\b/advanced_handlers.add_vip_sender_handler/g' src/main.py
sed -i 's/advanced_handlers\.unsubscribe_email/advanced_handlers.execute_unsubscribe/g' src/main.py
print_success "Method names fixed"

# Step 2: Verify Python syntax
print_step "Verifying Python syntax..."
if python3 -c "import ast; ast.parse(open('src/main.py').read())" 2>/dev/null; then
    print_success "main.py syntax OK"
else
    print_error "main.py has syntax errors"
    exit 1
fi

if python3 -c "import ast; ast.parse(open('src/advanced_handlers.py').read())" 2>/dev/null; then
    print_success "advanced_handlers.py syntax OK"
else
    print_error "advanced_handlers.py has syntax errors"
    exit 1
fi

# Step 3: Stop old container
print_step "Stopping old container..."
if podman stop autoxmail_bot 2>/dev/null; then
    print_success "Container stopped"
else
    print_warning "No running container found"
fi

# Step 4: Remove old container
print_step "Removing old container..."
if podman rm autoxmail_bot 2>/dev/null; then
    print_success "Container removed"
else
    print_warning "No container to remove"
fi

# Step 5: Remove old image
print_step "Removing old image..."
if podman rmi autoxmail-bot 2>/dev/null; then
    print_success "Image removed"
else
    print_warning "No image to remove"
fi

# Step 6: Build new image
print_header "Building New Container Image"
print_step "Building autoxmail-bot image (this may take 2-3 minutes)..."
if podman build --no-cache -t autoxmail-bot -f config/Dockerfile . > /tmp/build.log 2>&1; then
    print_success "Image built successfully"
else
    print_error "Build failed! Check /tmp/build.log"
    tail -20 /tmp/build.log
    exit 1
fi

# Step 7: Calculate memory limit
print_step "Calculating memory limit..."
MEM_LIMIT=$(awk '/MemTotal/ {printf "%dm", int(($2/1024)*0.25)}' /proc/meminfo)
print_success "Memory limit set to: ${MEM_LIMIT}"

# Step 8: Start new container
print_header "Starting New Container"
print_step "Starting autoxmail_bot container..."
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
    exit 1
fi

# Step 9: Wait for startup
print_step "Waiting for bot to initialize (5 seconds)..."
sleep 5
print_success "Initialization complete"

# Step 10: Show logs
print_header "Bot Logs (Last 40 Lines)"
podman logs --tail 40 autoxmail_bot

# Step 11: Check if bot is running
print_header "Final Status Check"
if podman ps | grep -q autoxmail_bot; then
    print_success "Bot is running!"
    echo ""
    echo -e "${CYAN}Container Info:${NC}"
    podman ps --filter name=autoxmail_bot --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    print_success "Deployment complete! Bot is live."
else
    print_error "Bot is not running. Check logs above for errors."
    exit 1
fi

print_header "Deployment Complete"
echo -e "${GREEN}${CHECK}${NC} All steps completed successfully!"
echo -e "${CYAN}${ARROW}${NC} Monitor logs: ${YELLOW}podman logs -f autoxmail_bot${NC}"
echo -e "${CYAN}${ARROW}${NC} Check status: ${YELLOW}podman ps${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"

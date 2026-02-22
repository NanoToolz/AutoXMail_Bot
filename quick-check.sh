#!/bin/bash

# Quick health check for AutoXMail Bot

echo "🔍 Quick Bot Health Check"
echo ""

# Check if container is running
if podman ps --filter name=autoxmail_bot --format "{{.Names}}" | grep -q autoxmail_bot; then
    echo "✓ Container is running"
else
    echo "✗ Container is NOT running"
    echo "  Run: podman start autoxmail_bot"
    exit 1
fi

# Check for critical errors in last 10 lines
if podman logs --tail 10 autoxmail_bot 2>&1 | grep -qi "error\|exception\|traceback"; then
    echo "✗ Errors found in recent logs:"
    echo ""
    podman logs --tail 20 autoxmail_bot 2>&1 | grep -i "error\|exception" | tail -5
    echo ""
    echo "  View full logs: podman logs autoxmail_bot"
    exit 1
else
    echo "✓ No recent errors"
fi

# Check if bot started successfully
if podman logs --tail 50 autoxmail_bot 2>&1 | grep -q "Bot started successfully"; then
    echo "✓ Bot started successfully"
else
    echo "⚠ Bot may not have started properly"
    echo "  Check logs: podman logs autoxmail_bot"
fi

echo ""
echo "✓ Bot appears healthy!"
echo ""
echo "Test OAuth: See test-oauth-flow.md"
echo "View logs:  podman logs -f autoxmail_bot"

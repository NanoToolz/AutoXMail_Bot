#!/bin/bash

echo "╔══════════════════════════════════════╗"
echo "║   🔍 Deployment Verification         ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Check git commit
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▶ Git Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
CURRENT_COMMIT=$(git log --oneline -1)
echo "Current commit: $CURRENT_COMMIT"
echo ""

# Check if ContextTypes is in main.py
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▶ Code Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if grep -q "ContextTypes" src/main.py; then
    echo "✓  ContextTypes import found in main.py"
else
    echo "✗  ContextTypes import MISSING in main.py"
    exit 1
fi
echo ""

# Check container status
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▶ Container Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
podman ps --filter name=autoxmail_bot --format "{{.Names}}: {{.Status}}"
echo ""

# Check recent logs for errors
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▶ Recent Logs (last 20 lines)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
podman logs --tail 20 autoxmail_bot 2>&1
echo ""

# Check for specific errors
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▶ Error Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if podman logs --tail 50 autoxmail_bot 2>&1 | grep -q "ContextTypes"; then
    echo "✗  ContextTypes error found in logs!"
    echo "   Container may be running old code."
    echo ""
    echo "   Try: podman restart autoxmail_bot"
    exit 1
elif podman logs --tail 50 autoxmail_bot 2>&1 | grep -q "ERROR"; then
    echo "⚠  Some errors found in logs (check above)"
    exit 1
else
    echo "✓  No critical errors found"
fi
echo ""

echo "╔══════════════════════════════════════╗"
echo "║   ✓ Verification Complete            ║"
echo "╚══════════════════════════════════════╝"

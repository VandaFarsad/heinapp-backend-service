#!/bin/bash
# Deploy combined Caddy configuration (Frontend + Backend)
# This script combines the individual Caddyfiles from both projects

set -e

ENVIRONMENT=$1

if [ -z "$ENVIRONMENT" ]; then
    echo "Usage: $0 <staging|production>"
    exit 1
fi

if [ "$ENVIRONMENT" != "staging" ] && [ "$ENVIRONMENT" != "production" ]; then
    echo "Error: Environment must be 'staging' or 'production'"
    exit 1
fi

FRONTEND_DIR="/root/heinapp/heinapp-frontend-service"
BACKEND_DIR="/root/heinapp/heinapp-backend-service"

FRONTEND_CADDYFILE="${FRONTEND_DIR}/deployment/caddy/Caddyfile.${ENVIRONMENT}"
BACKEND_CADDYFILE="${BACKEND_DIR}/deployment/caddy/Caddyfile.${ENVIRONMENT}"

# Verify both files exist
if [ ! -f "$FRONTEND_CADDYFILE" ]; then
    echo "Error: Frontend Caddyfile not found: $FRONTEND_CADDYFILE"
    exit 1
fi

if [ ! -f "$BACKEND_CADDYFILE" ]; then
    echo "Error: Backend Caddyfile not found: $BACKEND_CADDYFILE"
    exit 1
fi

# Create combined Caddyfile
echo "# Combined Caddy Configuration for ${ENVIRONMENT} Environment" > /tmp/Caddyfile.combined
echo "# Generated on $(date)" >> /tmp/Caddyfile.combined
echo "# DO NOT EDIT - This file is auto-generated" >> /tmp/Caddyfile.combined
echo "" >> /tmp/Caddyfile.combined
echo "# =============================================" >> /tmp/Caddyfile.combined
echo "# Frontend Configuration" >> /tmp/Caddyfile.combined
echo "# =============================================" >> /tmp/Caddyfile.combined
cat "$FRONTEND_CADDYFILE" >> /tmp/Caddyfile.combined
echo "" >> /tmp/Caddyfile.combined
echo "# =============================================" >> /tmp/Caddyfile.combined
echo "# Backend Configuration" >> /tmp/Caddyfile.combined
echo "# =============================================" >> /tmp/Caddyfile.combined
cat "$BACKEND_CADDYFILE" >> /tmp/Caddyfile.combined

# Validate the combined configuration
echo "📋 Validating combined Caddy configuration..."
sudo caddy validate --config /tmp/Caddyfile.combined

# Deploy to Caddy
echo "🚀 Deploying combined Caddyfile to /etc/caddy/Caddyfile..."
sudo cp /tmp/Caddyfile.combined /etc/caddy/Caddyfile

# Reload Caddy
echo "♻️  Reloading Caddy..."
sudo systemctl reload caddy || sudo systemctl restart caddy

# Verify Caddy is running
if systemctl is-active --quiet caddy; then
    echo "✅ Caddy configuration deployed successfully!"
    echo "🌐 Frontend: $(grep -o '[a-z0-9.-]*heina.org' "$FRONTEND_CADDYFILE" | head -1)"
    echo "🌐 Backend:  $(grep -o 'api.[a-z0-9.-]*heina.org' "$BACKEND_CADDYFILE" | head -1)"
else
    echo "❌ Caddy failed to start! Check logs:"
    echo "   sudo journalctl -u caddy -n 50"
    exit 1
fi

# Cleanup
rm /tmp/Caddyfile.combined

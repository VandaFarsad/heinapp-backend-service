#!/usr/bin/env bash

set -e

echo "🚀 Deploying heinapp-backend to PRODUCTION..."

# Change to project root
cd "$(dirname "$0")/.."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env not found!"
    exit 1
fi

# Safety check for production
read -p "⚠️  Are you sure you want to deploy to PRODUCTION? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Deployment cancelled."
    exit 0
fi

# Create directories for static/media files
echo "📁 Creating directories..."
sudo mkdir -p /var/www/heinapp-backend-production/static
sudo mkdir -p /var/www/heinapp-backend-production/media
sudo mkdir -p /var/log/caddy
sudo chown -R caddy:caddy /var/log/caddy 2>/dev/null || true

# Build Docker image
echo "🐳 Building Docker image..."
docker build --network=host -t heinapp-backend-service .

# Stop and remove old container
echo "🔄 Stopping old container..."
docker rm -f heinapp-backend 2>/dev/null || true

# Run new container with bind mounts for static/media
echo "▶️  Starting new container..."
docker run -d \
  --name heinapp-backend \
  --env-file .env \
  -p 8000:8000 \
  -v /var/www/heinapp-backend-production/static:/code/static \
  -v /var/www/heinapp-backend-production/media:/code/media \
  --restart unless-stopped \
  heinapp-backend-service

# Wait for container to be ready
echo "⏳ Waiting for container to be ready..."
sleep 5

# Check container status
if docker ps | grep -q heinapp-backend; then
    echo "✅ Container is running!"
else
    echo "❌ Container failed to start. Showing logs:"
    docker logs heinapp-backend
    exit 1
fi

# Show container logs
echo ""
echo "📋 Container logs:"
docker logs heinapp-backend --tail 20

# Deploy combined Caddy configuration (Frontend + Backend)
echo ""
echo "🔧 Deploying combined Caddy configuration..."
./deployment/deploy-caddy.sh production

echo ""
echo "🎉 Production deployment complete!"
echo ""
echo "📊 Useful commands:"
echo "   docker logs -f heinapp-backend    # Follow logs"
echo "   docker exec -it heinapp-backend bash    # Enter container"
echo "   sudo journalctl -u caddy -f    # Caddy logs"

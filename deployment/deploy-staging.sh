#!/usr/bin/env bash

set -e

echo "🚀 Deploying heinapp-backend to STAGING..."

# Change to project root
cd "$(dirname "$0")/.."

# Check if .env.staging exists
if [ ! -f .env.staging ]; then
    echo "❌ Error: .env.staging not found!"
    exit 1
fi

# Create directories for static/media files
echo "📁 Creating directories..."
sudo mkdir -p /var/www/heinapp-backend-staging/static
sudo mkdir -p /var/www/heinapp-backend-staging/media
sudo mkdir -p /var/log/caddy
sudo chown -R caddy:caddy /var/log/caddy 2>/dev/null || true

# Build Docker image
echo "🐳 Building Docker image..."
docker build --network=host -t heinapp-backend-service-staging .

# Stop and remove old container
echo "🔄 Stopping old container..."
docker rm -f heinapp-backend-staging 2>/dev/null || true

# Run new container with bind mounts for static/media
echo "▶️  Starting new container..."
docker run -d \
  --name heinapp-backend-staging \
  --env-file .env.staging \
  -p 8002:8000 \
  -v /var/www/heinapp-backend-staging/static:/code/static \
  -v /var/www/heinapp-backend-staging/media:/code/media \
  --restart unless-stopped \
  heinapp-backend-service-staging

# Wait for container to be ready
echo "⏳ Waiting for container to be ready..."
sleep 5

# Check container status
if docker ps | grep -q heinapp-backend-staging; then
    echo "✅ Container is running!"
else
    echo "❌ Container failed to start. Showing logs:"
    docker logs heinapp-backend-staging
    exit 1
fi

# Show container logs
echo ""
echo "📋 Container logs:"
docker logs heinapp-backend-staging --tail 20

# Deploy combined Caddy configuration (Frontend + Backend)
echo ""
echo "🔧 Deploying combined Caddy configuration..."
./deployment/deploy-caddy.sh staging

echo ""
echo "🎉 Staging deployment complete!"
echo ""
echo "📊 Useful commands:"
echo "   docker logs -f heinapp-backend-staging    # Follow logs"
echo "   docker exec -it heinapp-backend-staging bash    # Enter container"
echo "   sudo journalctl -u caddy -f    # Caddy logs"

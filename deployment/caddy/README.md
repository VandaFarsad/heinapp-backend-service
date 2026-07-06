# Caddy Configuration

This directory contains Caddy reverse proxy configurations for the heinapp backend service.

## Overview

Caddy serves as a reverse proxy and provides:
- ✅ **Automatic HTTPS** with Let's Encrypt (certificates and renewal)
- ✅ **Static file serving** (faster than Django/Gunicorn)
- ✅ **Security headers** (HSTS, X-Frame-Options, etc.)
- ✅ **Request logging**
- ✅ **Health checks**

## Files

- `Caddyfile.staging` - Configuration for api.staging.heina.org (Backend only)
- `Caddyfile.production` - Configuration for production backend (Backend only)
- ~~`Caddyfile.staging-combined`~~ - **DEPRECATED** (auto-generated now)
- ~~`Caddyfile.production-combined`~~ - **DEPRECATED** (auto-generated now)

## Dynamic Combined Deployment

The backend Caddyfile is **automatically combined** with the frontend Caddyfile during deployment:

1. Backend config: `/root/heinapp/heinapp-backend-service/caddy/Caddyfile.{environment}`
2. Frontend config: `/root/heinapp/heinapp-frontend-service/caddy/Caddyfile.{environment}`
3. Combined to: `/etc/caddy/Caddyfile`

The frontend deployment script (`deploy-caddy.sh`) handles this automatically.

**Each project manages its own Caddy configuration independently!**

## Setup Instructions

### First-time Setup

1. **Install Caddy** (already done):
```bash
sudo apt install caddy
```

2. **Create log directory**:
```bash
sudo mkdir -p /var/log/caddy
sudo chown caddy:caddy /var/log/caddy
```

3. **Create static/media directories**:
```bash
# For Staging
sudo mkdir -p /var/www/heinapp-backend-staging/static
sudo mkdir -p /var/www/heinapp-backend-staging/media

# For Production
sudo mkdir -p /var/www/heinapp-backend-production/static
sudo mkdir -p /var/www/heinapp-backend-production/media
```

4. **Link Docker volumes to Caddy directories** (do this during deployment):
```bash
# This will be done in the deployment script
# Docker volumes will be mounted to these locations
```

### Deployment

#### Staging

```bash
# Copy Caddyfile
sudo cp /root/heinapp/heinapp-backend-service/caddy/Caddyfile.staging /etc/caddy/Caddyfile

# Validate configuration
sudo caddy validate --config /etc/caddy/Caddyfile

# Reload Caddy (applies new config without downtime)
sudo systemctl reload caddy

# Check status
sudo systemctl status caddy
```

#### Production

```bash
# 1. First, update the domain in Caddyfile.production
# 2. Then copy and reload:
sudo cp /root/heinapp/heinapp-backend-service/caddy/Caddyfile.production /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

### Troubleshooting

**View logs:**
```bash
# Caddy system logs
sudo journalctl -u caddy -f

# Application logs
sudo tail -f /var/log/caddy/staging.heina.org.log
```

**Test configuration:**
```bash
sudo caddy validate --config /etc/caddy/Caddyfile
```

**Manual start/stop:**
```bash
sudo systemctl start caddy
sudo systemctl stop caddy
sudo systemctl restart caddy
sudo systemctl reload caddy  # Preferred - no downtime
```

**Check if ports are listening:**
```bash
sudo netstat -tlnp | grep caddy
# Should show ports 80 and 443
```

## DNS Configuration

Ensure your DNS records point to the server:

```
staging.heina.org    A    <SERVER_IP_ADDRESS>
```

For production, add:
```
your-domain.com      A    <SERVER_IP_ADDRESS>
```

## Static Files

Django's `collectstatic` command writes to Docker volumes. These volumes need to be accessible to Caddy:

### Option 1: Bind Mounts (Recommended)
Mount Docker volumes to host filesystem locations that Caddy can read.

### Option 2: Named Volumes with Access
Configure Docker to allow Caddy to access the named volumes.

The deployment scripts will handle this setup.

## Security Notes

- HTTPS is **automatic** - Caddy handles Let's Encrypt certificates
- Certificates auto-renew before expiration
- HTTP automatically redirects to HTTPS
- Security headers are pre-configured
- Rate limiting is available (currently commented out)

## Testing

After deployment, test:

```bash
# Check HTTPS
curl -I https://staging.heina.org

# Check static files
curl -I https://staging.heina.org/static/

# Check API
curl https://staging.heina.org/api/
```

## Performance Tips

- Static files are served directly by Caddy (not Django)
- Caching headers are set for static assets
- Compression is enabled by default
- Keep-alive connections are handled automatically

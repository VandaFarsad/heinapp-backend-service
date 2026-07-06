# Deployment-Guide für Frontend + Backend mit Caddy

## DNS-Setup (WICHTIG - zuerst konfigurieren!)

Füge folgende DNS-Einträge hinzu:

```
staging.heina.org        A    91.98.34.73
api.staging.heina.org    A    91.98.34.73
```

## Deployment-Reihenfolge

### 1. Backend deployen

```bash
cd /root/heinapp/heinapp-backend-service/deployment
./deploy-staging.sh
```

Das startet:
- ✅ Backend-Container (Port 8002)
- ✅ Kombinierte Caddyfile (Frontend + Backend)
- ✅ SSL-Zertifikate für beide Domains

### 2. Frontend deployen (nach DNS-Propagierung)

```bash
cd /root/heinapp/heinapp-frontend-service/deployment
./deploy-staging.sh
```

Das startet:
- ✅ Frontend-Container (Port 8082)
- ✅ Aktualisiert Caddy-Config

## DNS prüfen

```bash
dig staging.heina.org
dig api.staging.heina.org
```

Beide sollten auf `91.98.34.73` zeigen.

## Testen

```bash
# Backend API
curl -I https://api.staging.heina.org/admin/

# Frontend
curl -I https://staging.heina.org
```

## URLs

- **Frontend:** https://staging.heina.org
- **Backend API:** https://api.staging.heina.org
- **Django Admin:** https://api.staging.heina.org/admin/

## Troubleshooting

### SSL-Zertifikat-Fehler

Wenn Let's Encrypt fehlschlägt, prüfe:

```bash
# DNS korrekt?
dig api.staging.heina.org

# Caddy Logs
sudo journalctl -u caddy -f
```

### Container läuft nicht

```bash
# Backend
docker logs heinapp-backend-staging

# Frontend
docker logs heinapp-frontend-staging
```

## GitHub Actions

Sobald DNS konfiguriert ist, funktionieren die automatischen Deployments via Tags:

```bash
# Backend + Frontend Staging
git tag -a v0.1.0-rc.1 -m "First staging release"
git push origin v0.1.0-rc.1
```

# Caddy Deployment Guide

## 🚀 Schnellstart für Staging-Deployment

### Voraussetzungen

- ✅ Caddy installiert und läuft
- ✅ DNS konfiguriert (`staging.heina.org → Server-IP`)
- ✅ `.env.staging` auf dem Server erstellt
- ✅ PostgreSQL Datenbank erstellt

### Option 1: Manuelles Deployment (Empfohlen zum ersten Test)

```bash
cd /root/heinapp/heinapp-backend-service/deployment
./deploy-staging.sh
```

Das Skript macht:
- Docker-Image bauen
- Container starten
- Static files sammeln
- Caddy neu laden

### Option 2: Automatisches Deployment via GitHub Actions

Siehe: [GITHUB_ACTIONS.md](GITHUB_ACTIONS.md)

```bash
git tag -a v0.1.0-rc.1 -m "First staging release"
git push origin v0.1.0-rc.1
```

---

## 🏭 Production Deployment

**Manuell:**
```bash
cd /root/heinapp/heinapp-backend-service/deployment
./deploy-production.sh
```

**Automatisch:**
```bash
git tag -a v1.0.0 -m "First production release"
git push origin v1.0.0
```

---

## 1️⃣ DNS konfigurieren

Stelle sicher, dass dein DNS-Record gesetzt ist:
```
staging.heina.org  →  A  →  [DEINE_SERVER_IP]
```

### 2️⃣ Umgebungsvariablen setzen (.env.staging)

Erstelle auf dem Server: `/root/heinapp/heinapp-backend-service/.env.staging`

**Wichtige Variablen:**
```bash
# Django
SECRET_KEY=dein-super-geheimer-key-hier
DEBUG=False
ALLOWED_HOSTS=staging.heina.org,localhost,127.0.0.1

# CORS (wenn du ein Frontend hast)
CORS_ALLOWED_ORIGINS=https://staging-frontend.heina.org,https://staging.heina.org

# Datenbank
DATABASE_ENGINE=postgresql
DATABASE_NAME=heinapp_staging
DATABASE_USER=heinapp_staging
DATABASE_PASSWORD=sicheres-passwort
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Email (Djoser)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=email-password

# Django Admin
DJANGO_SUPERUSER_EMAIL=admin@heina.org
DJANGO_SUPERUSER_PASSWORD=admin-password
DJANGO_SUPERUSER_FIRST_NAME=Admin
DJANGO_SUPERUSER_LAST_NAME=User
```

### 3️⃣ Manuelle Ersteinrichtung auf dem Server

Führe **einmalig** auf dem Server aus:

```bash
# 1. Verzeichnisse erstellen
sudo mkdir -p /var/www/heinapp-backend-staging/static
sudo mkdir -p /var/www/heinapp-backend-staging/media
sudo mkdir -p /var/log/caddy
sudo chown -R caddy:caddy /var/log/caddy

# 2. Caddy-Konfiguration aktivieren
cd /root/heinapp/heinapp-backend-service
sudo cp caddy/Caddyfile.staging /etc/caddy/Caddyfile

# 3. Caddy-Konfiguration testen
sudo caddy validate --config /etc/caddy/Caddyfile

# 4. Caddy starten/neu laden
sudo systemctl restart caddy

# 5. Status prüfen
sudo systemctl status caddy
```

### 4️⃣ Ersten Tag erstellen und pushen

```bash
# Lokal auf deinem Entwicklungsrechner
git tag -a v0.1.0-rc.1 -m "First staging release"
git push origin v0.1.0-rc.1
```

Das GitHub Action Workflow startet automatisch und deployed auf Staging! ✨

### 5️⃣ Testen

```bash
# HTTPS prüfen
curl -I https://staging.heina.org

# Admin-Panel öffnen
open https://staging.heina.org/admin/

# API testen (wenn vorhanden)
curl https://staging.heina.org/api/
```

---

## 🏭 Production Deployment

### Vorbereitung

1. **Domain festlegen** und in `caddy/Caddyfile.production` eintragen
2. **DNS konfigurieren**: `deine-domain.com → A → [PRODUCTION_SERVER_IP]`
3. **`.env` Datei** auf Production Server erstellen (wie oben, aber mit Production-Werten)

### Deployment

```bash
# 1. Production-Domain in Caddyfile.production setzen
# Editiere: /root/heinapp/heinapp-backend-service/caddy/Caddyfile.production

# 2. Einmalige Einrichtung auf Production-Server
sudo mkdir -p /var/www/heinapp-backend-production/static
sudo mkdir -p /var/www/heinapp-backend-production/media
sudo mkdir -p /var/log/caddy
sudo chown -R caddy:caddy /var/log/caddy

# 3. Production Tag erstellen (lokal)
git tag -a v1.0.0 -m "First production release"
git push origin v1.0.0
```

Das Workflow deployed automatisch auf Production (ohne `-rc.` im Tag)! 🎉

---

## 🔧 Troubleshooting

### Caddy läuft nicht

```bash
# Logs anschauen
sudo journalctl -u caddy -f

# Konfiguration validieren
sudo caddy validate --config /etc/caddy/Caddyfile

# Caddy neu starten
sudo systemctl restart caddy
```

### Docker Container läuft nicht

```bash
# Container-Logs anschauen
docker logs heinapp-backend-staging

# Container status
docker ps -a

# Container neu starten
docker restart heinapp-backend-staging
```

### Static Files werden nicht gefunden

```bash
# Prüfen ob Verzeichnisse existieren
ls -la /var/www/heinapp-backend-staging/static/

# In Container schauen
docker exec -it heinapp-backend-staging ls -la /code/static/

# Manuell collectstatic
docker exec -it heinapp-backend-staging python manage.py collectstatic --noinput
```

### HTTPS funktioniert nicht

```bash
# Caddy Logs für Let's Encrypt Fehler
sudo journalctl -u caddy -f

# Häufigste Probleme:
# - DNS nicht korrekt gesetzt (warte bis Propagierung fertig)
# - Port 80/443 nicht offen (Firewall prüfen)
# - Domain ist bereits zu oft fehlgeschlagen (Rate Limit)
```

### Firewall-Ports öffnen

```bash
# UFW (Ubuntu Firewall)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload

# Oder direkt in Hetzner Cloud Console
```

---

## 📊 Monitoring & Logs

### Caddy Logs

```bash
# System logs
sudo journalctl -u caddy -f

# Application logs (aus Caddyfile)
sudo tail -f /var/log/caddy/staging.heina.org.log
```

### Django/Gunicorn Logs

```bash
# Container logs
docker logs -f heinapp-backend-staging

# Logs im Volume (falls konfiguriert)
tail -f ../heinapp-backend-logs/staging.log
```

---

## 🔄 Updates deployen

**Staging:**
```bash
git tag -a v0.2.0-rc.1 -m "New features"
git push origin v0.2.0-rc.1
```

**Production:**
```bash
git tag -a v1.1.0 -m "Production update"
git push origin v1.1.0
```

---

## ✅ Checkliste vor dem ersten Deployment

- [ ] DNS konfiguriert (staging.heina.org)
- [ ] `.env.staging` auf Server erstellt
- [ ] Verzeichnisse erstellt (`/var/www`, `/var/log/caddy`)
- [ ] Caddy installiert und läuft
- [ ] Caddy-Konfiguration kopiert und validiert
- [ ] GitHub Secrets gesetzt:
  - `HETZNER_STAGING_HOST`
  - `HETZNER_STAGING_USER`
  - `HETZNER_STAGING_SSH_KEY`
- [ ] PostgreSQL Datenbank erstellt
- [ ] Firewall Ports 80/443 offen

---

## 🎯 Nächste Schritte

Nach erfolgreichem Staging-Deployment:

1. **Monitoring einrichten** (z.B. Sentry, Uptime Kuma)
2. **Backups konfigurieren** (PostgreSQL, Media-Files)
3. **CI/CD erweitern** (automatische Tests, Slack-Benachrichtigungen)
4. **Rate Limiting aktivieren** (in Caddyfile auskommentieren)
5. **Production-Domain festlegen** und deployen

---

## 📚 Weiterführende Infos

- [Caddy Dokumentation](https://caddyserver.com/docs/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Let's Encrypt Rate Limits](https://letsencrypt.org/docs/rate-limits/)

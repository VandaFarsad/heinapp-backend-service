# GitHub Actions Setup

## GitHub Secrets konfigurieren

Für automatisches Deployment via GitHub Actions müssen folgende Secrets in deinem GitHub Repository gesetzt werden.

**Gehe zu:** `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

### Staging Secrets

| Secret Name | Beschreibung | Beispiel |
|------------|--------------|----------|
| `HETZNER_STAGING_HOST` | IP oder Domain des Staging-Servers | `staging.heina.org` oder `91.98.34.73` |
| `HETZNER_STAGING_USER` | SSH-Benutzername | `root` |
| `HETZNER_STAGING_SSH_KEY` | Privater SSH-Key (vollständig mit `-----BEGIN` und `-----END`) | `-----BEGIN OPENSSH PRIVATE KEY-----\nMIIE...` |

### Production Secrets

| Secret Name | Beschreibung | Beispiel |
|------------|--------------|----------|
| `HETZNER_HOST` | IP oder Domain des Production-Servers | `api.heina.org` |
| `HETZNER_USER` | SSH-Benutzername | `root` |
| `HETZNER_SSH_KEY` | Privater SSH-Key für Production | `-----BEGIN OPENSSH PRIVATE KEY-----\nMIIE...` |

---

## SSH-Key erstellen (falls noch nicht vorhanden)

```bash
# Auf deinem lokalen Rechner
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy_key

# Public Key auf Server kopieren
ssh-copy-id -i ~/.ssh/github_deploy_key.pub root@staging.heina.org

# Private Key für GitHub Secret
cat ~/.ssh/github_deploy_key
# → Komplett kopieren und als Secret einfügen
```

---

## Deployment-Workflow

### Automatisches Deployment

#### Staging

```bash
# Tag mit '-rc.' erstellen (release candidate)
git tag -a v0.1.0-rc.1 -m "First staging release"
git push origin v0.1.0-rc.1
```

GitHub Actions startet automatisch:
1. ✅ Tests laufen
2. ✅ Docker-Build
3. ✅ Deployment auf Staging
4. 🌐 https://staging.heina.org ist live

#### Production

```bash
# Tag OHNE '-rc.' erstellen
git tag -a v1.0.0 -m "First production release"
git push origin v1.0.0
```

GitHub Actions startet automatisch:
1. ✅ Tests laufen
2. ✅ Docker-Build
3. ✅ Deployment auf Production
4. 🌐 Deine Production-Domain ist live

---

### Manuelles Deployment (ohne GitHub Actions)

#### Auf dem Server

```bash
# Staging
cd /root/heinapp/heinapp-backend-service/deployment
./deploy-staging.sh

# Production
cd /root/heinapp/heinapp-backend-service/deployment
./deploy-production.sh
```

---

## Workflow Details

Die Workflows findest du in: [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)

### Trigger

| Trigger | Beschreibung |
|---------|--------------|
| `push` auf beliebigen Branch | Nur Tests laufen (kein Deployment) |
| Tag `v*.*.*-rc.*` | → Deployment auf **Staging** |
| Tag `v*.*.*` (ohne `-rc.`) | → Deployment auf **Production** |
| Pull Request | Nur Tests laufen |

### Beispiel-Tags

```bash
# Staging
v0.1.0-rc.1
v0.2.0-rc.2
v1.0.0-rc.1

# Production
v1.0.0
v1.1.0
v2.0.0
```

---

## Troubleshooting

### SSH-Verbindung schlägt fehl

```
Error: dial tcp: lookup staging.heina.org: no such host
```

**Lösung:** Überprüfe `HETZNER_STAGING_HOST` Secret

---

### Permission denied (publickey)

**Lösung:**
1. Überprüfe `HETZNER_STAGING_SSH_KEY` Secret
2. Stelle sicher, dass der Public Key auf dem Server ist:
```bash
cat ~/.ssh/authorized_keys
```

---

### Container startet nicht

**Lösung:** Logs auf dem Server prüfen:
```bash
ssh root@staging.heina.org
docker logs heinapp-backend-staging
```

---

## Nächste Schritte

Nach dem Setup:

1. **Secrets in GitHub setzen** (siehe oben)
2. **Ersten Tag erstellen und pushen:**
   ```bash
   git tag -a v0.1.0-rc.1 -m "First staging deployment"
   git push origin v0.1.0-rc.1
   ```
3. **GitHub Actions beobachten:** GitHub → Repository → Actions
4. **Ergebnis prüfen:** https://staging.heina.org

---

## Monitoring

### Container-Status

```bash
docker ps | grep heinapp
docker logs -f heinapp-backend-staging
```

### Caddy-Status

```bash
sudo systemctl status caddy
sudo journalctl -u caddy -f
```

### SSL-Zertifikat prüfen

```bash
curl -vI https://staging.heina.org 2>&1 | grep -i -e "subject:" -e "issuer:" -e "expire"
```

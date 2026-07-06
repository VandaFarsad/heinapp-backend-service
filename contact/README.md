# contact

Django-App für das öffentliche Kontaktformular. Nimmt Nachrichten von nicht-authentifizierten Nutzern entgegen, persistiert sie in der Datenbank und versendet E-Mail-Benachrichtigungen an den Admin sowie eine Bestätigung an den Absender.

## Architektur

```
┌──────────┐     REST API     ┌─────────┐     SMTP      ┌────────────┐
│ Frontend │ ───────────────► │ contact │ ────────────► │ Mailserver │
│ (Next.js)│ ◄─────────────── │ (Django)│               └────────────┘
└──────────┘   JSON Response  └────┬────┘
                                   │
                                   ▼
                            ┌──────────────┐
                            │ PostgreSQL   │
                            │ (Persistenz) │
                            └──────────────┘
```

### Datenfluss

**Formular absenden (POST /contact/submit/):**

1. Request mit Kontaktdaten (E-Mail, Betreff, Nachricht, optional Name)
2. Validierung durch DRF-Serializer (Mindestlängen, E-Mail-Format)
3. Speicherung in der Datenbank inkl. IP-Adresse des Absenders
4. E-Mail-Versand: Admin-Benachrichtigung + Bestätigungs-E-Mail an Absender
5. Response an Frontend (inkl. Warning bei E-Mail-Fehler)

### Fehlerbehandlung

E-Mail-Fehler verhindern **nicht** die erfolgreiche Speicherung der Nachricht. Bei einem SMTP-Fehler wird die Nachricht trotzdem mit `201 Created` gespeichert und ein `warning`-Feld in der Response zurückgegeben.

## Dateistruktur

```
contact/
├── models.py              # ContactMessage Model
├── views.py               # REST-API Endpoint (Function-Based View)
├── serializers.py         # DRF Serializer mit Feld-Validierung
├── urls.py                # URL-Routing
├── admin.py               # Django Admin Konfiguration
├── helpers/
│   └── contact_emails_helpers.py  # E-Mail-Versand (Admin + Bestätigung)
└── migrations/
```

## API-Endpoint

Der Endpoint ist **öffentlich** (keine Authentifizierung erforderlich), aber durch Rate-Limiting geschützt.

| Methode | URL                       | Beschreibung             |
| ------- | ------------------------- | ------------------------ |
| POST    | `/api/v1/contact/submit/` | Kontaktformular absenden |

### Request-Body (POST)

| Feld         | Typ    | Pflicht | Validierung                           |
| ------------ | ------ | ------- | ------------------------------------- |
| `email`      | string | Ja      | Gültige E-Mail-Adresse                |
| `subject`    | string | Ja      | Mindestens 3 Zeichen                  |
| `message`    | string | Ja      | Mindestens 10 Zeichen                 |
| `first_name` | string | Nein    | Mindestens 2 Zeichen (wenn angegeben) |
| `last_name`  | string | Nein    | Mindestens 2 Zeichen (wenn angegeben) |

### Responses

**201 Created** – Erfolgreiche Übermittlung:

```json
{
  "success": true,
  "message": "Deine Nachricht wurde erfolgreich übermittelt. Du erhältst in Kürze eine Bestätigungs-E-Mail.",
  "id": 123
}
```

Bei E-Mail-Fehler zusätzlich:

```json
{
  "success": true,
  "message": "Deine Nachricht wurde erfolgreich übermittelt.",
  "id": 123,
  "warning": "E-Mail-Versendung konnte nicht abgeschlossen werden."
}
```

**400 Bad Request** – Validierungsfehler:

```json
{
  "success": false,
  "errors": {
    "email": ["Dieses Feld ist erforderlich."],
    "subject": ["Der Betreff muss mindestens 3 Zeichen lang sein."]
  }
}
```

## Spam-Schutz

- **Rate-Limiting:** `AnonRateThrottle` begrenzt die Anzahl der Requests pro IP-Adresse
- **IP-Logging:** Die IP-Adresse des Absenders wird gespeichert (inkl. `X-Forwarded-For`-Header-Unterstützung)

## E-Mail-Versand

Der E-Mail-Versand wird über `contact_emails_helpers.py` gesteuert und umfasst zwei E-Mails:

| E-Mail                 | Empfänger     | `fail_silently` | Beschreibung                                |
| ---------------------- | ------------- | --------------- | ------------------------------------------- |
| Admin-Benachrichtigung | `ADMIN_EMAIL` | `False`         | Enthält alle Details + Link zum Admin-Panel |
| Bestätigungs-E-Mail    | Absender      | `True`          | Bestätigt den Eingang der Nachricht         |

### Konfiguration

Umgebungsvariablen bzw. Django-Settings:

| Setting              | Beschreibung                                         |
| -------------------- | ---------------------------------------------------- |
| `DEFAULT_FROM_EMAIL` | Absender-Adresse für beide E-Mails                   |
| `ADMIN_EMAIL`        | Empfänger der Admin-Benachrichtigung                 |
| `BACKEND_BASE_URL`   | Basis-URL für den Admin-Panel-Link in der Admin-Mail |

## Model: ContactMessage

Persistiert Kontaktformular-Nachrichten mit folgenden Besonderheiten:

- **Status-Workflow:** `new` → `read` → `replied` → `closed` (via `TextChoices`)
- **Admin-Notizen:** Freitextfeld für interne Vermerke
- **Sortierung:** Neueste Nachrichten zuerst (`-created_at`)

## Django Admin

Konfigurierte Admin-Oberfläche mit:

- **List-Display:** E-Mail, Name, Betreff, Datum, Status
- **Filter:** Erstelldatum, Status
- **Suche:** Über Name, E-Mail, Betreff, Nachricht
- **Readonly-Felder:** Alle vom Nutzer übermittelten Felder (Manipulationsschutz)
- **Editierbar:** Nur `status` und `admin_notes`

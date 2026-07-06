# calendar_app

Django-App zur Integration eines Nextcloud-Kalenders über das CalDAV-Protokoll. Die App fungiert als Proxy mit lokalem Datenbank-Cache zwischen dem Frontend und dem CalDAV-Server.

### CalDAV & iCalendar

- **CalDAV** (Calendaring Extensions to WebDAV) ist ein Internet-Protokoll (RFC 4791), mit dem Clients Kalenderdaten auf einem entfernten Server lesen und schreiben können – vergleichbar mit einer REST-API speziell für Kalender. In unserem Fall ist der CalDAV-Server eine Nextcloud-Instanz.
- **iCalendar** (RFC 5545) ist das Datenformat, in dem Kalender-Events übertragen werden (`.ics`-Dateien). Es definiert Felder wie `VEVENT`, `DTSTART`, `DTEND`, `SUMMARY` usw.

Unsere `CalDAVService`-Klasse ([services.py](services.py)) verbindet beide Konzepte: Sie nutzt die Python-Bibliothek `caldav` (DAVClient), um über das CalDAV-Protokoll mit Nextcloud zu kommunizieren, und die Bibliothek `icalendar`, um Events im iCalendar-Format zu parsen und zu erzeugen. Der Service wird als Kontextmanager verwendet, kapselt Authentifizierung, Verbindungsaufbau und Timezone-Handling und liefert typisierte `CalDAVEvent`-Objekte zurück.

## Architektur

```
┌──────────┐     REST API     ┌──────────────┐    CalDAV     ┌───────────┐
│ Frontend │ ───────────────► │ calendar_app │ ────────────► │ Nextcloud │
│ (Next.js)│ ◄─────────────── │  (Django)    │ ◄──────────── │  CalDAV   │
└──────────┘   JSON Response  └──────┬───────┘   iCalendar   └───────────┘
                                     │
                                     ▼
                              ┌─────────────┐
                              │ PostgreSQL   │
                              │ (DB-Cache)   │
                              └─────────────┘
```

### Datenfluss

**Lesen (GET /events/):**

1. Request mit optionalen `start_date`, `end_date`, `force_sync` Parametern
2. Prüfung ob Sync nötig ist (Cache-TTL: 15 Minuten)
3. Falls Sync nötig → CalDAV-Events holen → Differential Sync mit DB
4. Gecachte Events aus DB serialisieren und zurückgeben

**Schreiben (POST/PUT/DELETE):**

1. Validierung durch DRF-Serializer
2. Operation auf dem CalDAV-Server ausführen
3. Lokalen DB-Cache aktualisieren
4. Response an Frontend

### Sync-Strategie

Die App nutzt einen **Write-Through-Cache** mit zeitbasierter Invalidierung:

- **Cache-TTL:** 15 Minuten (konfigurierbar via `cache_minutes`)
- **Staleness-Check:** Basiert auf dem ältesten `last_synced_at` im angefragten Zeitraum
- **Zombie-Cleanup:** Events, die auf dem CalDAV-Server gelöscht wurden, werden aus der DB entfernt
- **Force-Sync:** Über Query-Parameter `force_sync=true` erzwingbar
- **Bulk-Operationen:** `bulk_create` / `bulk_update` mit Batch-Size 100

## Dateistruktur

```
calendar_app/
├── models.py          # CalendarEvent Model (DB-Cache)
├── views.py           # REST-API Endpoints (Function-Based Views)
├── services.py        # CalDAVService – CalDAV-Server-Kommunikation
├── serializers.py     # DRF Serializer mit Validierung
├── urls.py            # URL-Routing
├── admin.py           # Django Admin Konfiguration
├── helpers/
│   ├── date_helpers.py    # Datum-Parsing, Cache-Queries, Sync-Entscheidung
│   ├── event_helpers.py   # Event-Parsing, Differenz-Erkennung, Serialisierung
│   └── sync_helpers.py    # Differential Sync, Bulk-DB-Operationen
└── migrations/
```

## API-Endpoints

Alle Endpoints erfordern Authentifizierung (JWT).

| Methode | URL                              | Beschreibung          |
| ------- | -------------------------------- | --------------------- |
| GET     | `/calendar/events/`              | Events laden (+ Sync) |
| POST    | `/calendar/events/create/`       | Event erstellen       |
| PUT     | `/calendar/events/<uid>/`        | Event aktualisieren   |
| DELETE  | `/calendar/events/<uid>/delete/` | Event löschen         |

### Query-Parameter (GET)

| Parameter    | Typ    | Beschreibung                    |
| ------------ | ------ | ------------------------------- |
| `start_date` | string | ISO 8601 Startdatum (optional)  |
| `end_date`   | string | ISO 8601 Enddatum (optional)    |
| `force_sync` | bool   | Cache ignorieren und neu syncen |

## Konfiguration

Umgebungsvariablen in `.env.local`:

```env
CALDAV_URL=https://nextcloud.example.com/remote.php/dav/
CALDAV_USER=username
CALDAV_PASSWORD=password
CALDAV_ID=calendar_id
```

Die Werte werden in `conf/settings.py` unter `CALDAV_CONFIG` zusammengefasst.

## Recurring Events (Wiederkehrende Termine)

Die App unterstützt wiederkehrende Events gemäß **RFC 5545** mit folgenden Feldern:

- **`rrule`** (Recurrence Rule): Definiert das Wiederholungsmuster, z.B.:
  - `FREQ=WEEKLY;BYDAY=MO,WE,FR` – Jeden Montag, Mittwoch und Freitag
  - `FREQ=MONTHLY;BYMONTHDAY=15` – Jeden 15. des Monats
  - `FREQ=DAILY;INTERVAL=2;COUNT=10` – Jeden 2. Tag, 10 Mal

- **`exdate`** (Exception Dates): Kommagetrennte ISO 8601-Strings für ausgeschlossene Termine, z.B.:
  - `2026-05-01T10:00:00Z,2026-05-15T10:00:00Z`

### Verarbeitung

- **Backend:** Speichert `rrule` und `exdate` unverändert aus dem CalDAV-Server
- **Frontend:** Übernimmt die Expansion wiederkehrender Events (z.B. mit `rrule.js`)
- **CalDAV-Sync:** Holt Master-Events mit `expand=False` – keine Instanzen-Expansion im Backend

## Community Room Validation

Die App verhindert Doppelbuchungen für Gemeinschaftsräume durch automatische Überschneidungsprüfung.

### Geschützte Räume

| Konstante       | Location-String                  |
| --------------- | -------------------------------- |
| `GROUND_FLOOR`  | Gemeinschaftsraum: Erdgeschoss   |
| `ROOFTOP`       | Gemeinschaftsraum: Dach          |

### Validierungslogik

Beim Erstellen oder Aktualisieren eines Events prüft `EventInputSerializer`:

1. Ist `location` einer der Gemeinschaftsräume?
2. Gibt es überschneidende Buchungen? (Start₁ < Ende₂ **UND** Start₂ < Ende₁)
3. Falls ja → **ValidationError** mit Details zum Konflikt

**Beispiel-Fehlermeldung:**

```json
{
  "location": "Gemeinschaftsraum: Erdgeschoss ist bereits gebucht vom 20.04.2026 14:00 bis 20.04.2026 16:00 (Event: Team Meeting)"
}
```

### Ausnahmen

- Beim **Update** wird das aktuelle Event von der Prüfung ausgeschlossen (via `uid` im Context)
- **Andere Locations** (z.B. private Räume) haben keine Validierung

## Django Admin Interface

Erweiterte Admin-Konfiguration in [admin.py](admin.py) mit folgenden Features:

### List Display

- Standard-Felder: UID, Titel, Datum, Location
- **Custom Boolean Columns:**
  - `has_recurrence` (✓/✗) – Zeigt ob `rrule` gesetzt ist
  - `has_exceptions` (✓/✗) – Zeigt ob `exdate` gesetzt ist

### Fieldsets

Logische Gruppierung der Felder:

1. **Basic Information:** UID, Recurrence ID, Titel, Beschreibung
2. **Date & Time:** Start, Ende, All-Day-Flag
3. **Location & URL:** Ort, Meeting-Link
4. **Recurrence:** `rrule`, `exdate` (mit RFC 5545 Hinweis)
5. **Metadata:** Timestamps (collapsed, readonly)

### Features

- **Search:** Durchsucht Titel, Beschreibung, Location, UID und `rrule`
- **Filters:** All-Day, Start/End Date, Last Synced
- **Date Hierarchy:** Drill-Down nach Startdatum
- **Readonly Fields:** Timestamps (created, updated, synced)

## Abhängigkeiten

| Paket       | Zweck                                         |
| ----------- | --------------------------------------------- |
| `caldav`    | CalDAV-Protokoll (RFC 4791)                   |
| `icalendar` | iCalendar-Generierung und -Parsing (RFC 5545) |
| `dateutil`  | Flexibles Datetime-Parsing                    |

## Model: CalendarEvent

Lokaler Cache der CalDAV-Events mit folgenden Besonderheiten:

- **Composite Key:** `(uid, recurrence_id)` – ermöglicht eindeutige Zuordnung wiederkehrender Events
- **Compound Index:** `(start_date, end_date)` – optimiert Range-Queries
- **Sync-Tracking:** `last_synced_at` pro Event für granulare Cache-Invalidierung
- **Recurring Events:** `rrule` (RFC 5545 Recurrence Rule) und `exdate` (Exception Dates als kommagetrennte ISO-Strings)

### Felder

| Feld             | Typ           | Beschreibung                                              |
| ---------------- | ------------- | --------------------------------------------------------- |
| `uid`            | CharField     | Eindeutige Event-ID (CalDAV UID)                          |
| `recurrence_id`  | CharField     | Rekurrenz-Instanz-ID für wiederkehrende Events (optional) |
| `title`          | CharField     | Event-Titel                                               |
| `description`    | TextField     | Ausführliche Beschreibung                                 |
| `start_date`     | DateTimeField | Startdatum/-zeit                                          |
| `end_date`       | DateTimeField | Enddatum/-zeit                                            |
| `all_day`        | BooleanField  | Ganztägiges Event                                         |
| `location`       | CharField     | Ort/Raum                                                  |
| `url`            | URLField      | Meeting-Link (z.B. Zoom, Teams)                           |
| `rrule`          | TextField     | RFC 5545 Recurrence Rule (optional)                       |
| `exdate`         | TextField     | Ausnahmedaten als kommagetrennte ISO-Strings (optional)   |
| `created_at`     | DateTimeField | Erstellungszeitpunkt (auto)                               |
| `updated_at`     | DateTimeField | Letztes Update (auto)                                     |
| `last_synced_at` | DateTimeField | Letzter CalDAV-Sync (manuell gesetzt)                     |

## CalDAVService

Zentrale Service-Klasse in `services.py` für die gesamte CalDAV-Server-Kommunikation. Kapselt Verbindungsmanagement, iCalendar-Serialisierung (RFC 5545) und Event-Parsing.

### Verwendung

Der Service wird als Context Manager genutzt, um die Verbindung sauber aufzuräumen:

```python
with CalDAVService() as service:
    events = service.get_events(start_date, end_date)
    new_event = service.create_event(event_data)
    updated = service.update_event(uid, event_data)
    deleted = service.delete_event(uid)
```

### Methoden

| Methode                   | Return-Typ          | Beschreibung                                   |
| ------------------------- | ------------------- | ---------------------------------------------- |
| `get_events(start, end)`  | `list[CalDAVEvent]` | Events im Zeitraum vom Server holen            |
| `create_event(data)`      | `CalDAVEvent`       | Neues Event erstellen und auf Server speichern |
| `update_event(uid, data)` | `CalDAVEvent`       | Bestehendes Event per UID aktualisieren        |
| `delete_event(uid)`       | `bool`              | Event per UID löschen (`True`/`False`)         |

### CalDAVEvent Dataclass

Typisiertes, immutables Value Object (`frozen=True, slots=True`), das von allen Service-Methoden zurückgegeben wird.

**Felder:**

```python
@dataclass(frozen=True, slots=True)
class CalDAVEvent:
    uid: str
    title: str
    description: str
    start_date: datetime
    end_date: datetime
    location: str
    url: str
    all_day: bool
    recurrence_id: str | None = None
    rrule: str | None = None
    exdate: str | None = None
```

**Konvertierungsmethoden:**

- **`to_model_fields()`** – Dict mit `datetime`-Objekten für die direkte DB-Persistierung via `CalendarEvent`
- **`to_response_dict()`** – Dict mit ISO 8601-Strings für JSON-API-Responses

### Dependency Injection

Für Tests kann der Service ohne echten CalDAV-Server instanziiert werden:

```python
service = CalDAVService(client=mock_client, calendar=mock_calendar)
```

Ohne Argumente verbindet sich der Service wie gewohnt eager zum konfigurierten Server.

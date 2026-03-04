# CosherAlert — Architecture (Gate B)

## Architect Decisions Summary

| Decision | Choice | Rationale |
|---|---|---|
| Telephony provider | **Yemot HaMashiach (call2all.co.il)** | Only provider with: native tzintuq API, full IVR, kosher-native platform, confirmed REST API (`call2all.co.il/ym/api/`), active community with live oref.org.il integrations |
| Hosting | **Kamatera Israel — Tel Aviv** | Israeli IP (required for oref.org.il), cheapest reliable VPS ($4–8/month), 24/7 support, instant provisioning |
| Database | **SQLite** | 50 users → zero ops overhead; file-based; no separate server; can migrate to PostgreSQL later |
| Language | **Python 3.11+** | Per Ayala's requirement |
| Process manager | **systemd** | Auto-restart on crash (uptime ≥ 99.5%), standard on Linux, zero cost |
| TTS | **Yemot built-in Hebrew TTS** | No external TTS service needed; Yemot sends TTS strings natively via API |
| IVR logic | **Yemot-native IVR + webhook to our app** | Yemot handles telephony; our app handles business logic via HTTP callback |

---

## Telephony Provider: Yemot HaMashiach

### Why Yemot (and not competitors)

| Provider | Verdict | Reason |
|---|---|---|
| **Yemot HaMashiach** | ✅ **SELECTED** | Native tzintuq, confirmed REST API, kosher-native numbers, IVR + outbound, active developer community, existing oref integrations |
| **Kol Kasher** | ❌ Eliminated | No documented public API; tzintuq capability unconfirmed |
| **Calltech** | ❌ Eliminated | Enterprise-grade, no per-user IVR self-registration flow; pricing opaque |
| **Cloudonix** | ❌ Eliminated | Requires BYO kosher-whitelisted carrier; additional complexity for Phase 1 |
| **Twilio** | ❌ Eliminated | Not kosher-whitelisted; cannot reach kosher phones without local carrier partner |
| **Kishurit** | ❌ Eliminated | No public API documentation found |

### Confirmed Yemot API Endpoints (base: `https://www.call2all.co.il/ym/api/`)

| Endpoint | Use |
|---|---|
| `POST /RunTzintuk` | Trigger tzintuq to a list of phones or distribution list |
| `POST /RunCampaign` | Run an outbound voice campaign (TTS or recorded) |
| `POST /CreateTemplate` | Create/manage distribution lists |
| Webhook callback (inbound) | Yemot calls our HTTP server for IVR logic during inbound calls |

**RunTzintuk key parameters:**
```
callerId=<our_yemot_number>
TzintukTimeOut=<1-10 seconds>
phones=tpl:<distribution_list_id>   # 0.1 units/number
token=<system_id>:<password>
```

**Cost model (Yemot units):**
- Tzintuq to distribution list: ~0.1 units/number
- At 50 users × 1 alert/day × 0.1 units = 5 units/day ≈ ~₪5–15/month at typical pricing
- Exact pricing requires account setup (contact 077-2222-770)

---

## Hosting: Kamatera Israel (Tel Aviv)

**Spec for Phase 1:**
- 1 vCPU, 1 GB RAM, 20 GB SSD
- ~$4–6/month
- Israeli IP address (satisfies oref.org.il constraint)
- systemd available (Ubuntu 22.04 LTS)

**Alternative (if Kamatera unavailable):** Vultr Tel Aviv at $6/month (same specs)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 CosherAlert — Kamatera Israel VPS               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   cosheralert (Python service)           │   │
│  │                                                          │   │
│  │   ┌─────────────┐        ┌────────────────────────────┐ │   │
│  │   │  Poller     │──────▶ │  Dispatcher                │ │   │
│  │   │  (5s loop)  │        │  - filter cat=10           │ │   │
│  │   │  GET oref   │        │  - deduplicate by id       │ │   │
│  │   └─────────────┘        │  - match zones→subscribers │ │   │
│  │                          └──────────┬─────────────────┘ │   │
│  │                                     │                    │   │
│  │                          ┌──────────▼─────────────────┐ │   │
│  │                          │  TelephonyAdapter (abstract)│ │   │
│  │                          │  ┌─────────────────────┐   │ │   │
│  │                          │  │ YemotAdapter        │   │ │   │
│  │                          │  │ Phase 1: cat=10     │   │ │   │
│  │                          │  │ callerId=NUMBER_A   │   │ │   │
│  │                          │  └─────────────────────┘   │ │   │
│  │                          │  ┌─────────────────────┐   │ │   │
│  │                          │  │ [Phase 2 slot]      │   │ │   │
│  │                          │  │ callerId=NUMBER_B   │   │ │   │
│  │                          │  └─────────────────────┘   │ │   │
│  │                          └────────────────────────────┘ │   │
│  │                                                          │   │
│  │   ┌─────────────┐        ┌────────────────────────────┐ │   │
│  │   │  IVR Server │        │  SQLite Database           │ │   │
│  │   │  (Flask)    │◀──────▶│  - users                  │ │   │
│  │   │  /ivr/*     │        │  - subscriptions           │ │   │
│  │   │  webhook    │        │  - alert_log               │ │   │
│  │   └─────────────┘        └────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
  oref.org.il/WarningMessages/       Yemot HaMashiach
  alert/alerts.json (GET, 5s)        call2all.co.il/ym/api/
                                     - RunTzintuk (outbound)
                                     - IVR webhook (inbound)
```

---

## Module Structure

```
cosheralert/
├── main.py                  # Entry point: starts poller + IVR server
├── poller.py                # Polls oref every 5s, emits alert events
├── dispatcher.py            # Filters cat=10, deduplicates, fans out
├── db.py                    # SQLite CRUD (users, subscriptions, alert_log)
├── telephony/
│   ├── base.py              # Abstract TelephonyAdapter
│   └── yemot.py             # YemotAdapter (call2all REST API)
├── ivr/
│   └── routes.py            # Flask webhook: handles Yemot IVR callbacks
├── tts.py                   # Hebrew TTS message builder (Yemot format)
├── config.py                # Settings (env vars)
└── tests/
    ├── test_poller.py
    ├── test_dispatcher.py
    └── test_db.py
```

---

## Database Schema

```sql
-- Registered users
CREATE TABLE users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    phone       TEXT NOT NULL UNIQUE,    -- Israeli format: 05XXXXXXXX
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    active      INTEGER DEFAULT 1        -- 0 = unsubscribed
);

-- Zone subscriptions (many-to-many)
CREATE TABLE subscriptions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(id),
    zone        TEXT NOT NULL,           -- Hebrew city/zone name from oref data[]
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, zone)
);

-- Alert delivery log (deduplication + audit)
CREATE TABLE alert_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    oref_id       TEXT NOT NULL,         -- alert.id from oref JSON
    cat           TEXT NOT NULL,
    zones         TEXT NOT NULL,         -- JSON array of zones
    dispatched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    recipients    INTEGER DEFAULT 0      -- count of numbers called
);
CREATE UNIQUE INDEX idx_alert_log_oref_id ON alert_log(oref_id);
```

---

## Component Specifications

### 1. Poller (`poller.py`)
- Poll interval: **5 seconds**
- URL: `https://www.oref.org.il/WarningMessages/alert/alerts.json`
- Headers: `Accept: application/json`, `Referer: https://www.oref.org.il/` (required to avoid 403)
- Empty/null/`{}` response = no active alert — handle gracefully, do not dispatch
- On HTTP error: exponential backoff (5s → 10s → 30s), log error, never crash
- Emits `AlertEvent` dataclass to dispatcher via in-process queue (`asyncio.Queue`)

### 2. Dispatcher (`dispatcher.py`)
- Receives `AlertEvent` from poller queue
- **Filter**: `cat == "10"` only (Phase 1)
- **Deduplicate**: check `alert_log` for `oref_id`; skip if already dispatched
- **Zone match**: for each zone in `alert.data[]`, query subscriptions for active users
- **Fanout**: collect unique phone numbers, call `TelephonyAdapter.send_tzintuq()`
- Write to `alert_log` after successful dispatch

### 3. TelephonyAdapter (`telephony/base.py`)
```python
from abc import ABC, abstractmethod

class TelephonyAdapter(ABC):
    @abstractmethod
    def send_tzintuq(self, phones: list[str], tts_message: str) -> bool:
        """Send tzintuq + TTS voice message to list of phone numbers."""
        ...

    @abstractmethod
    def send_call(self, phones: list[str], tts_message: str) -> bool:
        """Send full outbound voice call (Phase 2 sirens — not implemented in Phase 1)."""
        ...
```

### 4. YemotAdapter (`telephony/yemot.py`)
- `BASE_URL = "https://www.call2all.co.il/ym/api"`
- `send_tzintuq()`: POST to `/RunTzintuk` with phone list + TTS payload
- `send_call()`: raises `NotImplementedError` in Phase 1 (Phase 2 stub)
- Auth: `token = f"{YEMOT_SYSTEM_ID}:{YEMOT_PASSWORD}"` (from env)
- Caller ID: `YEMOT_CALLER_ID_A` env var (Phase 1 pre-warning number)
- Retry: 3 attempts with 2s sleep on HTTP 5xx error

### 5. IVR Server (`ivr/routes.py`)
- **Framework**: Flask (lightweight webhook handler)
- Yemot calls our HTTPS endpoint during inbound user calls
- **Flow**:
  1. User calls Yemot system number
  2. Yemot IVR → webhook `GET /ivr/start?phone=05XXXXXXXX`
  3. Response: greeting + menu (press 1 = register, press 2 = unsubscribe)
  4. Register path: present zone list (DTMF), collect selections, save to DB, confirm
  5. Unsubscribe path: remove all subscriptions for caller's number, confirm
- Zones offered in IVR: fetched from oref at startup and cached (provides real zone names)
- **HTTPS**: required by Yemot for webhooks — use Let's Encrypt + Nginx on VPS

### 6. TTS Messages (`tts.py`)
Pre-warning message template (Hebrew, Yemot TTS format):
```
"התראה מפיקוד העורף: בדקות הקרובות צפויות התרעות באזורי {zones}. יש להתקרב למרחב המוגן הקרוב."
```

---

## NFR Targets

| NFR | Target | How Met |
|---|---|---|
| Alert delivery latency | ≤ 60s | 5s poll + ~5s dispatch + Yemot API ≈ 15–20s total |
| Uptime | ≥ 99.5% | systemd `Restart=always` + Kamatera SLA + poller never crashes |
| Registration time | ≤ 2 min | IVR ≤ 6 steps; Yemot handles all telephony |
| Monthly cost | Minimized | ~$6/month VPS + ~₪15/month Yemot units |
| Israeli law (unsubscribe) | ✅ Required | IVR option 2 removes all subscriptions immediately |
| Phase 2 modularity | ✅ | `TelephonyAdapter` ABC; Phase 2 adds `YemotAdapter(caller_id=NUMBER_B)` |

---

## Configuration (Environment Variables)

```bash
YEMOT_SYSTEM_ID=               # Yemot system number
YEMOT_PASSWORD=                # Yemot admin password
YEMOT_CALLER_ID_A=             # Phone number for pre-warning tzintuqim (Phase 1)
YEMOT_CALLER_ID_B=             # Phone number for siren calls (Phase 2, unused now)
OREF_POLL_INTERVAL=5           # seconds
DB_PATH=/var/cosheralert/cosheralert.db
IVR_WEBHOOK_PORT=8443
LOG_LEVEL=INFO
```

---

## Deployment Stack

```
Kamatera VPS (Ubuntu 22.04 LTS)
├── /opt/cosheralert/              # app code (git clone)
│   └── venv/                      # Python virtualenv
├── /var/cosheralert/              # runtime data
│   ├── cosheralert.db             # SQLite database
│   └── cosheralert.log            # application log
├── /etc/cosheralert/env           # secrets (not in git)
├── /etc/systemd/system/cosheralert.service
└── Nginx (reverse proxy, HTTPS via Let's Encrypt → Flask :8443)
```

**systemd unit:**
```ini
[Unit]
Description=CosherAlert Service
After=network.target

[Service]
User=cosheralert
WorkingDirectory=/opt/cosheralert
EnvironmentFile=/etc/cosheralert/env
ExecStart=/opt/cosheralert/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## Risk Register

| Risk | Mitigation |
|---|---|
| oref.org.il 403 from VPS | Add `Referer: https://www.oref.org.il/` header (confirmed community workaround) |
| oref returns empty body when no alert | Treat empty/`{}`/non-JSON as "no alert" — never raise exception |
| Hebrew zone name mismatches | Normalize: strip niqqud, strip whitespace; log unmatched zones for tuning |
| Yemot API rate limits | 50 users → single batch call per alert; well within limits |
| Yemot account setup delay | Open account immediately; this is the only external dependency blocking dev start |

---

## Open Items for Developer

1. **Yemot account** must be opened before development (Ayala to action — 077-2222-770)
2. **SSL cert** provisioning on VPS (Let's Encrypt via Certbot) is part of deployment setup
3. **Zone list for IVR**: fetch from oref at app startup and cache for IVR menu generation
4. **IVR zone UX**: Phase 1 — offer top zones as numbered DTMF options (confirm count with Ayala)

---

## Gate B Decision

**Status: ✅ PASS**

> Architect assessment: Architecture is minimal and implementable. Single VPS + Yemot HaMashiach covers all Phase 1 requirements (tzintuq, IVR, kosher-ready, REST API confirmed). SQLite is sufficient for 50 users. Modular `TelephonyAdapter` ABC future-proofs Phase 2. All NFR targets are achievable within this design. No blockers.
>
> **Next owner: Developer Agent** → implement against `artifacts/architecture.md`, produce `artifacts/implementation.md`.

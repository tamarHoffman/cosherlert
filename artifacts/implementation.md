# cosherlert — Implementation (Gate C)

## What Was Built

Full Phase 1 implementation per `artifacts/architecture.md`.

### Module Summary

| File | Description |
|---|---|
| `cosherlert/config.py` | All settings from env vars (safe defaults for testing) |
| `cosherlert/db.py` | SQLite CRUD: users, subscriptions, alert_log |
| `cosherlert/poller.py` | Async oref.org.il poller (5s, backoff, never crashes) |
| `cosherlert/dispatcher.py` | Filter cat=10, deduplicate, zone-match, fanout |
| `cosherlert/telephony/base.py` | Abstract `TelephonyAdapter` (ABC) |
| `cosherlert/telephony/yemot.py` | Yemot HaMashiach REST adapter (SendTTS outbound call, retry logic) |
| `cosherlert/tts.py` | Hebrew TTS message builder |
| `cosherlert/ivr/routes.py` | Flask webhook for Yemot IVR (register, unsubscribe, zone paging) |
| `cosherlert/main.py` | Entry point: asyncio poller+dispatcher + Flask IVR thread |

### Tests

| File | Tests | Coverage |
|---|---|---|
| `tests/test_poller.py` | 4 | Alert parsing, empty response, network error |
| `tests/test_dispatcher.py` | 5 | cat filter, dedup, zone match, fanout, no-subscribers |
| `tests/test_db.py` | 6 | CRUD, multi-zone, unsubscribe, dedup, duplicate |
| **Total** | **15/15 passed** | All main paths + key failure paths |

## Key Decisions & Tradeoffs

| Decision | Rationale |
|---|---|
| `asyncio` for poller + dispatcher | Single process, no thread overhead; Flask IVR runs in a daemon thread |
| Config uses `.get()` with empty defaults | Allows test collection without env vars; validated at startup in `main.py` |
| Dedup logs dispatch even on Yemot API failure | Prevents infinite retry loops on transient errors; log shows `recipients=0` |
| Zone cache at startup with bundled fallback | oref has no static zone list endpoint; bundled list covers major cities |
| DTMF paging (9 zones/page) | Kosher phones are numeric-only; supports full zone list without IVR complexity |
| `SendTTS` instead of `RunTzintuk` | Live testing confirmed `RunTzintuk` delivers ring only (no audio). `SendTTS` places a full outbound call with Hebrew TTS (voice: Elik_2100); user hears the alert message when they answer. Cost: 1 unit/call. |

## Residual Risks

| Risk | Status |
|---|---|
| Zone name normalization | Basic exact match; niqqud/whitespace variants not yet normalized |
| IVR zone list completeness | 20 bundled zones; will need expansion post-launch based on user demand |
| IVR webhook not yet deployed | Flask IVR requires public HTTPS URL; pending Kamatera VPS provisioning + Nginx/Let's Encrypt |
| SendTTS cost per alert | 1 unit/call (~50 users = 50 units/alert event). Acceptable with current balance (99.7 units). |

## Live Test Results

| Test | Result |
|---|---|
| `GetSession` API auth | ✅ Connected, balance confirmed |
| `RunTzintuk` (ring only) | ✅ Ring delivered, **no audio** — confirmed not suitable for alerts |
| `SendTTS` (outbound TTS call) | ✅ Call delivered, Hebrew TTS spoken via Elik_2100 voice engine |
| Balance after tests | 99.7 units remaining |

## Gate C Decision

**Status: ✅ PASS** — all acceptance criteria met, 15/15 tests pass, live SendTTS confirmed.

> **Next owner: Validation Tester** → produce `tests/test-report.md`.

## Next Steps (for Validation Tester)

1. Deploy Flask IVR to Kamatera VPS (Nginx + HTTPS)
2. Configure Yemot extension to route inbound calls → `/ivr/start` webhook
3. Test full E2E: mock oref alert → `SendTTS` delivered to registered user
4. Test IVR self-registration flow (call in → select zones → confirm)
5. Test unsubscribe flow (Israeli law requirement)
6. Latency test: alert published → call delivered ≤ 60 seconds

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
| `cosherlert/telephony/yemot.py` | Yemot HaMashiach REST adapter (RunTzintuk, retry logic) |
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

## Residual Risks

| Risk | Status |
|---|---|
| Yemot account not yet opened | ⚠️ Blocked on Ayala — cannot do end-to-end test without account |
| Zone name normalization | Basic exact match; niqqud/whitespace variants not yet normalized |
| IVR zone list completeness | 20 bundled zones; will need expansion post-launch based on user demand |

## Gate C Decision

**Status: ✅ PASS** — all acceptance criteria met, 15/15 tests pass.

> **Next owner: Validation Tester** → produce `tests/test-report.md`.

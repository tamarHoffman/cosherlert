# cosherlert — Project Plan (Gate A)

## Problem Statement

Kosher phone users (feature phones used by the Haredi/ultra-Orthodox community) cannot receive Home Front Command rocket pre-warnings because all current alert channels rely on GPS-based smartphone apps. This leaves hundreds of thousands of Israeli citizens — including in Beit Shemesh — without a pre-warning mechanism.

## Proposed Solution

**cosherlert**: an automated system that polls the Home Front Command real-time feed, detects pre-warning alerts for user-selected geographic zones, and delivers a tzintuq (short ring + hangup for attention) followed by a TTS voice message to registered Kosher phone numbers.

---

## Scope

### Phase 1 (this project) — IN SCOPE
| # | Feature |
|---|---------|
| 1 | Poll `https://www.oref.org.il/WarningMessages/alert/alerts.json` continuously (every 3–5 seconds) |
| 2 | Filter for pre-warning alerts (`cat=10`) only |
| 3 | Match alert zones (cities/regions in `data[]`) against user subscriptions |
| 4 | Deliver tzintuq + TTS voice message to all subscribed phone numbers |
| 5 | Self-registration via inbound phone call (IVR): user calls, selects zone(s), gets registered |
| 6 | Persistent user registry (phone number → list of subscribed zones) |
| 7 | All outbound calls from a single consistent number per alert type |
| 8 | Modular telephony layer: Phase 2 (real-time sirens) can plug in a second number/channel without redesign |

### OUT OF SCOPE (Phase 1)
- Real-time siren alerts (Phase 2)
- Mobile app, web portal, SMS channels
- Manual operator dashboard
- Multi-language support beyond Hebrew

---

## Success KPIs
| KPI | Target |
|-----|--------|
| Alert delivery latency | ≤ 60 seconds from oref.org.il publication |
| System uptime during active alerts | ≥ 99.5% |
| Self-registration flow completion time | ≤ 2 minutes for non-technical user |
| Cost per tzintuq delivery | Tracked; minimize while maintaining robustness |

---

## Technology Recommendations (for Architect evaluation)

### Critical Constraint Discovered
> ⚠️ The `oref.org.il` API **blocks requests from servers outside Israel**. The polling service **must run on Israeli-hosted infrastructure**.

### Telephony Provider — Market Survey

| Provider | Tzintuq Support | Outbound API | IVR/Inbound | Notes |
|---|---|---|---|---|
| **Yemot HaMashiach** (ימות המשיח) | ✅ Native | ✅ REST API | ✅ Full IVR | Active developer forum; existing community implementations of oref.org.il integration with tzintuq (f2.freeivr.co.il). Pricing per unit/call — contact 077-2222-770 for quote. |
| **Kol Kasher** (קול כשר) | Unknown | Unknown | Likely | Needs direct evaluation |
| **019 SMS API** | ❌ SMS only | ✅ SMS | N/A | Used by CobaltRedAlert project; business account required; not phone-call based |

**Recommendation for Architect**: Evaluate Yemot HaMashiach first — the community has already implemented oref.org.il → tzintuq pipelines on this platform (see f2.freeivr.co.il/topic/13104). This significantly reduces development risk.

### Prior Art (open source reference)
- **CobaltRedAlert** (GitHub: shilosiani/CobaltRedAlert): Python, polls oref.org.il, sends SMS via 019 or email. Good reference for the polling/filtering logic.
- **freeivr.co.il community plugin**: Yemot-native implementation with tzintuq for oref alerts — strong reference for telephony integration.

### Hosting (Israeli cloud required)
| Option | Notes |
|---|---|
| AWS Israel (il-central-1) | GA since 2023; reliable, familiar DevOps tooling |
| Azure Israel Central | Available |
| Local Israeli VPS (e.g., Cloudwm, Netvision) | Cheaper; less SLA guarantee |

---

## System Components (high-level)

```
┌──────────────────────────────────────────────────────┐
│                    cosherlert                        │
│                                                       │
│  ┌──────────────┐    ┌────────────────────────────┐  │
│  │  Poller      │───▶│  Alert Dispatcher          │  │
│  │  (Python)    │    │  (zone matching + fanout)  │  │
│  │  polls oref  │    └──────────┬─────────────────┘  │
│  └──────────────┘               │                    │
│                                 ▼                    │
│  ┌──────────────┐    ┌────────────────────────────┐  │
│  │  IVR / Reg.  │    │  Telephony Adapter         │  │
│  │  (inbound    │    │  (tzintuq + TTS)           │  │
│  │   self-reg)  │    │  Phase 1: Yemot/provider   │  │
│  └──────┬───────┘    │  Phase 2: pluggable        │  │
│         │            └────────────────────────────┘  │
│         ▼                                            │
│  ┌──────────────┐                                    │
│  │  User Store  │                                    │
│  │  (DB: phone  │                                    │
│  │   → zones)   │                                    │
│  └──────────────┘                                    │
└──────────────────────────────────────────────────────┘
```

---

## Priorities (ordered by dependency & risk)

| Priority | Item | Rationale |
|---|---|---|
| P0 | Telephony provider selection & API access | Blocks everything; must verify tzintuq + outbound API availability |
| P0 | Israeli hosting setup | Blocks poller — oref.org.il blocks foreign IPs |
| P1 | Alert poller (Python) | Core data source |
| P1 | User registry (DB schema + CRUD) | Required for dispatch and registration |
| P2 | Alert dispatcher (zone matching + fanout) | Core business logic |
| P2 | IVR self-registration flow | User onboarding |
| P3 | TTS message generation | Voice delivery |
| P3 | Monitoring & alerting (uptime ≥ 99.5%) | Operational requirement |

---

## Per-Agent Acceptance Criteria

### Architect (Gate B)
- [ ] Telephony provider selected with confirmed tzintuq + outbound call API
- [ ] Cloud/hosting provider selected (must be Israeli or Israel-routed)
- [ ] Database choice specified (schema for users, zones, alert log)
- [ ] Modular telephony interface defined (allows Phase 2 second channel)
- [ ] Polling strategy defined (interval, deduplication, error handling)
- [ ] NFRs addressed: latency ≤ 60s, uptime ≥ 99.5%, cost model
- [ ] `artifacts/architecture.md` produced

### Developer (Gate C)
- [ ] Poller correctly filters `cat=10` events and deduplicates by `id`
- [ ] Dispatcher matches zones and fans out to all subscribed numbers
- [ ] Telephony adapter sends tzintuq + TTS within 60s of alert detection
- [ ] IVR flow: user can register ≥1 zone in ≤ 2 minutes
- [ ] Unit tests for poller, dispatcher, and zone-matching logic
- [ ] `artifacts/implementation.md` produced

### Validation Tester (Gate D)
- [ ] End-to-end test: mock oref alert → tzintuq delivered to registered number
- [ ] Latency test: ≤ 60s from mock alert to call delivery
- [ ] Registration test: new user can register via IVR in ≤ 2 minutes
- [ ] Deduplication test: same alert `id` not delivered twice
- [ ] Uptime/resilience test: service recovers from poller failure within 30s
- [ ] `tests/test-report.md` produced

---

## Open Items / Risks

| Risk | Impact | Owner |
|---|---|---|
| Yemot HaMashiach API may not support bulk outbound tzintuqim at the required concurrency | HIGH | Architect to validate; escalate to Ayala if pricing/limits block progress |
| oref.org.il may rate-limit or block automated polling | HIGH | Architect to evaluate polling interval and headers; check if a community-approved mirror exists |
| Zone names in oref `data[]` are Hebrew city names — fuzzy matching may be needed | MEDIUM | Developer to handle normalization |
| Cost per tzintuq at scale (many registered users, frequent alerts) | MEDIUM | Architect to model; escalate to Ayala if cost is high |

---

## Decisions Confirmed by Ayala

| Question | Answer |
|---|---|
| Expected user scale (Phase 1 launch) | ~50 users |
| Telephony account | None — Architect must evaluate all providers from scratch |
| Multi-zone registration | ✅ Users can subscribe to multiple zones in one call |
| De-registration | ✅ Required (Israeli law & policy — users must be able to unsubscribe via phone) |

### Telephony Provider Longlist (for Architect evaluation)

| Provider | Tzintuq | Outbound API | IVR Inbound | Kosher-ready | Notes |
|---|---|---|---|---|---|
| **Yemot HaMashiach** | ✅ Native | ✅ REST | ✅ Full IVR | ✅ | Best-known kosher IVR platform; community has live oref→tzintuq implementations; 077-2222-770 |
| **Kol Kasher** | Unknown | Unknown | Likely | ✅ | Direct competitor to Yemot; evaluate API availability |
| **Calltech** | Unknown | ✅ | ✅ | Likely | Israeli company, graphical IVR builder (Xbuilder), local support |
| **Cloudonix** | Unknown | ✅ SIP/API | ✅ | Possible (BYO carrier) | Flexible VoIP/SIP; can bring own kosher-approved number |
| **Twilio** | Unknown | ✅ | ✅ | ❌ (needs partner) | Strong API; foreign; kosher number routing requires local carrier partner |
| **Kishurit** | Unknown | Possible | Likely | ✅ | Frum-market focused, Bnei Brak |

> ⚠️ **Critical factor**: outbound calls to Kosher phones must originate from a number whitelisted by the Rabbinical kosher phone committee (Bezeq / kosher network). The Architect must verify which providers supply or accept such numbers.

---

## Gate A Decision

**Status: ✅ PASS**

> Manager assessment: Scope is clear, KPIs are measurable, user scale is defined (50 users Phase 1), priorities are ordered, per-agent handoffs are explicit, and all open questions are resolved. Telephony provider selection remains the highest-risk item and is formally delegated to the Architect (Gate B).
>
> **Next owner: Architect Agent** → produce `artifacts/architecture.md`.

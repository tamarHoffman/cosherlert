"""
Yemot IVR webhook handler.

Yemot calls GET /ivr/<path> with query params during inbound calls.
We respond with Yemot IVR commands as plain text.

Session state is passed via Yemot's ApiPhone parameter (caller number).
"""

import logging
import requests
from flask import Flask, request

from cosherlert import db, config

logger = logging.getLogger(__name__)
app = Flask(__name__)

# Cached zone list fetched from oref at startup (Hebrew city names)
_zone_cache: list[str] = []

ZONES_PER_PAGE = 9  # DTMF 1–9 per menu page


def init_zone_cache():
    global _zone_cache
    try:
        resp = requests.get(
            "https://www.oref.org.il/WarningMessages/alert/alerts.json",
            headers=config.OREF_HEADERS,
            timeout=8,
        )
        # oref doesn't expose a static zone list — use a bundled fallback
        # populated from known zones; this will be refined post-launch
    except Exception:
        pass
    # Bundled common zones (expandable)
    _zone_cache = [
        "בית שמש", "ירושלים", "תל אביב", "חיפה", "באר שבע",
        "אשדוד", "אשקלון", "רחובות", "נתניה", "פתח תקווה",
        "ראשון לציון", "הרצליה", "כפר סבא", "רמת גן", "בני ברק",
        "מודיעין", "אילת", "נהריה", "טבריה", "עפולה",
    ]
    logger.info("Zone cache initialized with %d zones", len(_zone_cache))


def _yemot_response(*lines: str) -> str:
    return "\n".join(lines)


def _phone_from_request() -> str:
    return request.args.get("ApiPhone", "").replace("-", "").replace("+972", "0")


@app.route("/ivr/start")
def ivr_start():
    phone = _phone_from_request()
    logger.info("IVR start: phone=%s", phone)
    subs = db.get_subscriptions_for_phone(phone)
    if subs:
        zones_str = ", ".join(subs)
        current = f"read_file=אתה רשום לאזורים: {zones_str}"
    else:
        current = "read_file=אינך רשום למערכת"

    return _yemot_response(
        "read_file=ברוכים הבאים למערכת התראות כשר-לרט",
        current,
        "read_file=לרישום לחץ 1. לביטול רישום לחץ 2. לסיום לחץ 9",
        "read_input=digit,1,5,goes=/ivr/menu,goes=/ivr/menu",
    )


@app.route("/ivr/menu")
def ivr_menu():
    digit = request.args.get("digit", "")
    phone = _phone_from_request()
    if digit == "1":
        return _show_zone_page(phone, page=0)
    elif digit == "2":
        db.remove_all_subscriptions(phone)
        logger.info("Unsubscribed phone=%s", phone)
        return _yemot_response(
            "read_file=הרישום שלך בוטל בהצלחה. תודה ולהתראות",
            "hangup=now",
        )
    else:
        return _yemot_response("read_file=בחירה לא חוקית", "goes=/ivr/start")


@app.route("/ivr/zones")
def ivr_zones():
    phone = _phone_from_request()
    page = int(request.args.get("page", "0"))
    digit = request.args.get("digit", "")

    # Handle zone selection from previous page
    if digit and digit != "0":
        prev_page = int(request.args.get("prev_page", "0"))
        idx = prev_page * ZONES_PER_PAGE + (int(digit) - 1)
        if 0 <= idx < len(_zone_cache):
            zone = _zone_cache[idx]
            db.add_subscription(phone, zone)
            logger.info("Subscribed phone=%s zone=%s", phone, zone)
            return _yemot_response(
                f"read_file=נרשמת לאזור {zone}",
                "read_file=לרישום לאזור נוסף לחץ 1. לסיום לחץ 9",
                "read_input=digit,1,5,goes=/ivr/zones?page=0,goes=/ivr/done",
            )

    return _show_zone_page(phone, page)


def _show_zone_page(phone: str, page: int) -> str:
    start = page * ZONES_PER_PAGE
    page_zones = _zone_cache[start: start + ZONES_PER_PAGE]
    if not page_zones:
        return _yemot_response("read_file=אין עוד אזורים", "goes=/ivr/done")

    lines = ["read_file=בחר אזור להתרעה"]
    for i, zone in enumerate(page_zones, 1):
        lines.append(f"read_file=לחץ {i} עבור {zone}")

    has_next = (start + ZONES_PER_PAGE) < len(_zone_cache)
    if has_next:
        lines.append("read_file=לחץ 0 לאזורים נוספים")

    lines.append(
        f"read_input=digit,1,5,"
        f"goes=/ivr/zones?prev_page={page}&page={page + 1 if has_next else page},"
        f"goes=/ivr/zones?prev_page={page}&page={page + 1 if has_next else page}"
    )
    return _yemot_response(*lines)


@app.route("/ivr/done")
def ivr_done():
    phone = _phone_from_request()
    subs = db.get_subscriptions_for_phone(phone)
    zones_str = ", ".join(subs) if subs else "אין"
    return _yemot_response(
        f"read_file=הרישום הושלם. האזורים שלך: {zones_str}",
        "read_file=תודה ושמרו על עצמכם",
        "hangup=now",
    )

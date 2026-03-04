"""
Yemot IVR webhook handler.

Yemot calls GET /ivr/start (and other paths) with query params during inbound calls.
We respond with Yemot IVR commands as plain text (Content-Type: text/plain; charset=utf-8).

Yemot IVR command reference:
  read=t-TEXT          — play TTS (Hebrew text-to-speech)
  read=f-FILENAME      — play uploaded audio file
  read_input=VAR,DIGITS,TIMEOUT,goes=URL,goes=URL  — capture DTMF input
  id_list_message=...  — read a sequence of audio IDs
  hangup=now           — hang up the call
  goes=URL             — redirect to another webhook URL

Session state: Yemot passes the caller's number as ApiPhone on every request.
"""

import logging
import requests
from flask import Flask, request, Response

from cosherlert import db, config

logger = logging.getLogger(__name__)
app = Flask(__name__)

ZONES_PER_PAGE = 9  # DTMF digits 1–9 per menu page

# Bundled zone list (expandable; oref has no static zone API)
ZONE_LIST: list[str] = [
    "בית שמש", "ירושלים", "תל אביב", "חיפה", "באר שבע",
    "אשדוד", "אשקלון", "רחובות", "נתניה", "פתח תקווה",
    "ראשון לציון", "הרצליה", "כפר סבא", "רמת גן", "בני ברק",
    "מודיעין", "אילת", "נהריה", "טבריה", "עפולה",
]


def _resp(*lines: str) -> Response:
    """Return a plain-text Yemot IVR response."""
    body = "\n".join(lines)
    return Response(body, content_type="text/plain; charset=utf-8")


def _phone() -> str:
    """Extract normalised Israeli phone number from Yemot's ApiPhone param."""
    raw = request.args.get("ApiPhone", "")
    return raw.replace("-", "").replace("+972", "0").strip()


# ─── Main entry point ────────────────────────────────────────────────────────

@app.route("/ivr/start")
def ivr_start():
    phone = _phone()
    logger.info("IVR start: phone=%s", phone)
    subs = db.get_subscriptions_for_phone(phone)
    if subs:
        zones_str = ", ".join(subs)
        current_status = f"read=t-אתה רשום לאזורים: {zones_str}"
    else:
        current_status = "read=t-אינך רשום למערכת"

    return _resp(
        "read=t-ברוכים הבאים למערכת כשר-לרט, מערכת התראות מוקדמות לטלפונים כשרים",
        current_status,
        "read=t-לרישום לאזורי התרעה לחץ 1. לביטול רישום לחץ 2. לסיום לחץ 9",
        "read_input=digit,1,10,goes=/ivr/menu,goes=/ivr/start",
    )


# ─── Main menu ───────────────────────────────────────────────────────────────

@app.route("/ivr/menu")
def ivr_menu():
    digit = request.args.get("digit", "")
    phone = _phone()
    if digit == "1":
        return _show_zone_page(phone, page=0)
    elif digit == "2":
        db.remove_all_subscriptions(phone)
        logger.info("Unsubscribed all zones: phone=%s", phone)
        return _resp(
            "read=t-הרישום שלך בוטל בהצלחה. לא תקבל עוד התראות מוקדמות.",
            "read=t-תודה ושמרו על עצמכם.",
            "hangup=now",
        )
    else:
        return _resp(
            "read=t-בחירה לא חוקית, נסה שנית",
            "goes=/ivr/start",
        )


# ─── Zone selection ───────────────────────────────────────────────────────────

@app.route("/ivr/zones")
def ivr_zones():
    phone = _phone()
    page = int(request.args.get("page", "0"))
    digit = request.args.get("digit", "")
    prev_page = int(request.args.get("prev_page", str(page)))

    if digit and digit.isdigit() and digit != "0":
        idx = prev_page * ZONES_PER_PAGE + (int(digit) - 1)
        if 0 <= idx < len(ZONE_LIST):
            zone = ZONE_LIST[idx]
            db.add_subscription(phone, zone)
            logger.info("Subscribed: phone=%s zone=%s", phone, zone)
            return _resp(
                f"read=t-נרשמת לאזור {zone}",
                "read=t-לרישום לאזור נוסף לחץ 1. לסיום לחץ 9.",
                "read_input=digit,1,10,goes=/ivr/zones?page=0,goes=/ivr/done",
            )

    return _show_zone_page(phone, page)


def _show_zone_page(phone: str, page: int) -> Response:
    start = page * ZONES_PER_PAGE
    page_zones = ZONE_LIST[start: start + ZONES_PER_PAGE]
    if not page_zones:
        return _resp("read=t-אין עוד אזורים", "goes=/ivr/done")

    lines = ["read=t-בחר אזור להתרעה מוקדמת"]
    for i, zone in enumerate(page_zones, 1):
        lines.append(f"read=t-לחץ {i} עבור {zone}")

    has_next = (start + ZONES_PER_PAGE) < len(ZONE_LIST)
    if has_next:
        lines.append("read=t-לחץ 0 לאזורים נוספים")

    next_page = page + 1 if has_next else page
    lines.append(
        f"read_input=digit,1,10,"
        f"goes=/ivr/zones?prev_page={page}&page={next_page},"
        f"goes=/ivr/zones?prev_page={page}&page={next_page}"
    )
    return _resp(*lines)


# ─── Done / confirmation ──────────────────────────────────────────────────────

@app.route("/ivr/done")
def ivr_done():
    phone = _phone()
    subs = db.get_subscriptions_for_phone(phone)
    if subs:
        zones_str = ", ".join(subs)
        summary = f"read=t-הרישום הושלם. תקבל התראות עבור האזורים: {zones_str}"
    else:
        summary = "read=t-לא נרשמת לאף אזור."
    return _resp(
        summary,
        "read=t-תודה ושמרו על עצמכם.",
        "hangup=now",
    )


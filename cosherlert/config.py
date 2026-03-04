import os

YEMOT_SYSTEM_ID = os.environ.get("YEMOT_SYSTEM_ID", "")
YEMOT_PASSWORD = os.environ.get("YEMOT_PASSWORD", "")
YEMOT_CALLER_ID_A = os.environ.get("YEMOT_CALLER_ID_A", "")     # Phase 1: pre-warning tzintuqim
YEMOT_CALLER_ID_B = os.environ.get("YEMOT_CALLER_ID_B", "")     # Phase 2: siren calls (unused)

OREF_POLL_INTERVAL = int(os.environ.get("OREF_POLL_INTERVAL", "5"))
DB_PATH = os.environ.get("DB_PATH", "cosherlert.db")
IVR_WEBHOOK_PORT = int(os.environ.get("IVR_WEBHOOK_PORT", "8443"))
IVR_BASE_URL = os.environ.get("IVR_BASE_URL", "")  # e.g. https://1.2.3.4 — required in production
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

OREF_ALERTS_URL = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
OREF_HEADERS = {
    "Accept": "application/json",
    "Referer": "https://www.oref.org.il/",
    "X-Requested-With": "XMLHttpRequest",
}

CAT_PRE_WARNING = "10"  # Phase 1: pre-warning alerts only

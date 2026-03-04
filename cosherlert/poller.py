import asyncio
import logging
import time
from dataclasses import dataclass, field

import requests
from cosherlert import config

logger = logging.getLogger(__name__)


@dataclass
class AlertEvent:
    oref_id: str
    cat: str
    title: str
    zones: list[str] = field(default_factory=list)
    desc: str = ""


def _fetch_alert() -> AlertEvent | None:
    try:
        resp = requests.get(
            config.OREF_ALERTS_URL,
            headers=config.OREF_HEADERS,
            timeout=8,
        )
        resp.raise_for_status()
        text = resp.content.decode("utf-8-sig").strip()  # utf-8-sig strips BOM
        if not text or text in ("{}", "null", "[]"):
            return None
        import json
        data = json.loads(text)
        if not data or not data.get("id"):
            return None
        return AlertEvent(
            oref_id=str(data["id"]),
            cat=str(data.get("cat", "")),
            title=data.get("title", ""),
            zones=data.get("data", []),
            desc=data.get("desc", ""),
        )
    except Exception as exc:
        logger.warning("Poller fetch error: %s", exc)
        return None


async def run_poller(queue: asyncio.Queue):
    backoff = config.OREF_POLL_INTERVAL
    logger.info("Poller started (interval=%ds)", config.OREF_POLL_INTERVAL)
    while True:
        try:
            alert = _fetch_alert()
            if alert:
                await queue.put(alert)
                logger.debug("Queued alert id=%s cat=%s zones=%s", alert.oref_id, alert.cat, alert.zones)
            backoff = config.OREF_POLL_INTERVAL  # reset on success
        except Exception as exc:
            logger.error("Poller unexpected error: %s", exc)
            backoff = min(backoff * 2, 30)  # exponential backoff, max 30s
        await asyncio.sleep(backoff)

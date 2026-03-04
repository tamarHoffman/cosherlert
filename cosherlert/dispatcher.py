import asyncio
import logging

from cosherlert import config, db
from cosherlert.poller import AlertEvent
from cosherlert.telephony.base import TelephonyAdapter
from cosherlert.tts import build_pre_warning_message

logger = logging.getLogger(__name__)


async def run_dispatcher(queue: asyncio.Queue, telephony: TelephonyAdapter):
    logger.info("Dispatcher started")
    while True:
        alert: AlertEvent = await queue.get()
        try:
            _process(alert, telephony)
        except Exception as exc:
            logger.error("Dispatcher error for alert %s: %s", alert.oref_id, exc)
        finally:
            queue.task_done()


def _process(alert: AlertEvent, telephony: TelephonyAdapter):
    # Phase 1: pre-warnings only
    if alert.cat != config.CAT_PRE_WARNING:
        logger.debug("Skipping cat=%s (not pre-warning)", alert.cat)
        return

    # Deduplicate
    if db.already_dispatched(alert.oref_id):
        logger.info("Alert %s already dispatched, skipping", alert.oref_id)
        return

    # Zone match
    phones = db.get_subscribers_for_zones(alert.zones)
    if not phones:
        logger.info("Alert %s: no subscribers for zones %s", alert.oref_id, alert.zones)
        db.log_dispatch(alert.oref_id, alert.cat, alert.zones, 0)
        return

    # Build message and dispatch
    message = build_pre_warning_message(alert.zones)
    logger.info(
        "Dispatching alert %s to %d subscribers (zones: %s)",
        alert.oref_id, len(phones), alert.zones,
    )
    success = telephony.send_tzintuq(phones, message)

    # Log regardless of success (prevent duplicate retries on transient error)
    db.log_dispatch(alert.oref_id, alert.cat, alert.zones, len(phones) if success else 0)

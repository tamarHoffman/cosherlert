import asyncio
import logging
import threading

from cosherlert import config, db
from cosherlert.poller import run_poller
from cosherlert.dispatcher import run_dispatcher
from cosherlert.telephony.yemot import YemotAdapter
from cosherlert.ivr.routes import app as ivr_app

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def start_ivr_server():
    # In production: Nginx terminates TLS, forwards to this port
    ivr_app.run(host="127.0.0.1", port=config.IVR_WEBHOOK_PORT, debug=False)


async def main():
    logger.info("cosherlert starting up")
    db.init_db()

    if not all([config.YEMOT_SYSTEM_ID, config.YEMOT_PASSWORD, config.YEMOT_CALLER_ID_A]):
        raise EnvironmentError(
            "Missing required env vars: YEMOT_SYSTEM_ID, YEMOT_PASSWORD, YEMOT_CALLER_ID_A"
        )
    telephony = YemotAdapter(caller_id=config.YEMOT_CALLER_ID_A)
    queue: asyncio.Queue = asyncio.Queue()

    # IVR Flask server in a background thread (blocking WSGI)
    ivr_thread = threading.Thread(target=start_ivr_server, daemon=True)
    ivr_thread.start()
    logger.info("IVR server started on port %d", config.IVR_WEBHOOK_PORT)

    # Run poller + dispatcher concurrently
    await asyncio.gather(
        run_poller(queue),
        run_dispatcher(queue, telephony),
    )


if __name__ == "__main__":
    asyncio.run(main())

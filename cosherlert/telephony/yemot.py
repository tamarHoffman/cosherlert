import logging
import time
import requests
from cosherlert.telephony.base import TelephonyAdapter
from cosherlert import config

logger = logging.getLogger(__name__)

BASE_URL = "https://www.call2all.co.il/ym/api"
MAX_RETRIES = 3
RETRY_SLEEP_SEC = 2


class YemotAdapter(TelephonyAdapter):
    def __init__(self, caller_id: str):
        self.token = f"{config.YEMOT_SYSTEM_ID}:{config.YEMOT_PASSWORD}"
        self.caller_id = caller_id

    def _post(self, endpoint: str, params: dict) -> dict:
        params["token"] = self.token
        url = f"{BASE_URL}/{endpoint}"
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(url, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                if data.get("responseStatus") == "OK":
                    return data
                logger.warning(
                    "Yemot %s returned non-OK status: %s — %s",
                    endpoint, data.get("responseStatus"), data.get("message"),
                )
                return {}
            except Exception as exc:
                logger.warning("Yemot %s attempt %d failed: %s", endpoint, attempt, exc)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_SLEEP_SEC)
        logger.error("Yemot %s failed after %d attempts", endpoint, MAX_RETRIES)
        return {}

    def send_tzintuq(self, phones: list[str], tts_message: str) -> bool:
        """Calls phones and plays a TTS message when answered (SendTTS).
        Phones separated by ':' for batch delivery.
        """
        if not phones:
            return True
        phones_param = ":".join(phones)
        result = self._post(
            "SendTTS",
            {
                "phones": phones_param,
                "ttsMessage": tts_message,
            },
        )
        ok_calls = result.get("OKCalls", 0) if result else 0
        logger.info(
            "SendTTS -> %d phones | OKCalls=%s | billing=%s | result=%s",
            len(phones), ok_calls, result.get("billing"), result,
        )
        return bool(result)

    def send_call(self, phones: list[str], tts_message: str) -> bool:
        raise NotImplementedError("send_call is reserved for Phase 2 siren alerts.")

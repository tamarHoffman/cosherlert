from abc import ABC, abstractmethod


class TelephonyAdapter(ABC):
    @abstractmethod
    def send_tzintuq(self, phones: list[str], tts_message: str) -> bool:
        """Send tzintuq (short ring + hangup) followed by TTS message to phones."""
        ...

    @abstractmethod
    def send_call(self, phones: list[str], tts_message: str) -> bool:
        """Send full outbound voice call. Phase 2 (sirens) only."""
        ...

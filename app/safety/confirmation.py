from __future__ import annotations

from app.voice.listener import VoiceListener
from app.voice.text_to_speech import TextToSpeech


class ConfirmationService:
    def __init__(self, listener: VoiceListener, tts: TextToSpeech) -> None:
        self.listener = listener
        self.tts = tts
        self.assistant_name = "Jarvis"

    def ask(self, message: str) -> bool:
        print(f"{self.assistant_name}: {message}")
        self.tts.speak(message)
        answer = self.listener.listen() or ""
        answer = answer.lower().strip()
        return answer in {"ya", "iya", "lanjut", "ya lanjut", "oke", "ok"}

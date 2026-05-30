from __future__ import annotations

import json
import subprocess


class TextToSpeech:
    def __init__(
        self,
        enabled: bool = True,
        rate: int = 175,
        volume: float = 1.0,
        reinitialize_each_call: bool = True,
        engine_name: str = "sapi",
    ) -> None:
        self.enabled = enabled
        self.rate = rate
        self.volume = volume
        self.reinitialize_each_call = reinitialize_each_call
        self.engine_name = engine_name.lower().strip()
        self.engine = None
        self._pyttsx3 = None

        if not enabled:
            return

        if self.engine_name == "sapi":
            return

        try:
            import pyttsx3

            self._pyttsx3 = pyttsx3
            if not self.reinitialize_each_call:
                self._create_pyttsx3_engine()
        except Exception as exc:
            print(f"TTS is unavailable, falling back to text: {exc}")
            self.enabled = False

    def speak(self, text: str) -> None:
        if not self.enabled:
            return

        if self.engine_name == "sapi":
            self._speak_with_sapi(text)
            return

        self._speak_with_pyttsx3(text)

    def _speak_with_sapi(self, text: str) -> None:
        escaped_text = json.dumps(text)
        volume = int(max(0, min(100, self.volume * 100)))
        rate = int(max(-10, min(10, round((self.rate - 175) / 25))))
        command = (
            "Add-Type -AssemblyName System.Speech; "
            "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$speaker.Volume = {volume}; "
            f"$speaker.Rate = {rate}; "
            f"$speaker.Speak({escaped_text}); "
            "$speaker.Dispose();"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except Exception as exc:
            print(f"SAPI TTS failed: {exc}")

    def _speak_with_pyttsx3(self, text: str) -> None:
        if self.reinitialize_each_call:
            self._speak_with_fresh_pyttsx3_engine(text)
            return

        try:
            self._speak_with_existing_pyttsx3_engine(text)
        except Exception as exc:
            print(f"TTS failed, retrying with a fresh engine: {exc}")
            self._destroy_pyttsx3_engine()
            try:
                self._speak_with_fresh_pyttsx3_engine(text)
            except Exception as retry_exc:
                print(f"TTS failed: {retry_exc}")

    def _speak_with_fresh_pyttsx3_engine(self, text: str) -> None:
        self._destroy_pyttsx3_engine()
        self._create_pyttsx3_engine()
        self._speak_with_existing_pyttsx3_engine(text)
        self._destroy_pyttsx3_engine()

    def _speak_with_existing_pyttsx3_engine(self, text: str) -> None:
        if self.engine is None:
            self._create_pyttsx3_engine()
        if self.engine is None:
            return

        self.engine.stop()
        self.engine.say(text)
        self.engine.runAndWait()

    def _create_pyttsx3_engine(self) -> None:
        if self._pyttsx3 is None:
            return
        self.engine = self._pyttsx3.init()
        self.engine.setProperty("rate", self.rate)
        self.engine.setProperty("volume", self.volume)

    def _destroy_pyttsx3_engine(self) -> None:
        if self.engine is None:
            return
        try:
            self.engine.stop()
        except Exception:
            pass
        self.engine = None

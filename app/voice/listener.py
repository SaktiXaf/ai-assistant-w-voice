from __future__ import annotations

from difflib import SequenceMatcher
import logging
from typing import Any


class VoiceListener:
    def __init__(
        self,
        language: str,
        text_mode: bool,
        logger: logging.Logger,
        languages: list[str] | None = None,
        try_all_languages: bool = False,
        microphone_index: Any = None,
        listen_timeout: float = 3,
        phrase_time_limit: float = 5,
        ambient_calibration_duration: float = 0.25,
        calibrate_once: bool = True,
        pause_threshold: float = 0.55,
    ) -> None:
        self.language = language
        self.languages = languages or [language]
        if language not in self.languages:
            self.languages.insert(0, language)
        self.try_all_languages = try_all_languages
        self.microphone_index = microphone_index
        self.listen_timeout = listen_timeout
        self.phrase_time_limit = phrase_time_limit
        self.ambient_calibration_duration = ambient_calibration_duration
        self.calibrate_once = calibrate_once
        self.pause_threshold = pause_threshold
        self.text_mode = text_mode
        self.logger = logger
        self._sr = None
        self._recognizer = None
        self._microphone_cls = None
        self._is_calibrated = False

        if not text_mode:
            try:
                import speech_recognition as sr

                self._sr = sr
                self._recognizer = sr.Recognizer()
                self._recognizer.pause_threshold = self.pause_threshold
                self._recognizer.non_speaking_duration = min(0.3, self.pause_threshold)
                self._microphone_cls = sr.Microphone
                self.microphone_index = self._resolve_microphone_index(microphone_index)
            except Exception as exc:
                print(f"Voice input is unavailable: {exc}")
                print("Tip: install microphone support with: python -m pip install PyAudio")
                self.logger.warning("Microphone/STT unavailable, falling back to text mode: %s", exc)
                self.text_mode = True

    def listen(self) -> str | None:
        if self.text_mode:
            try:
                text = input("Kamu: ").strip()
            except (EOFError, KeyboardInterrupt):
                return "keluar"
            return text.lower() or None

        try:
            return self._listen_from_microphone()
        except KeyboardInterrupt:
            return "exit"

    def _listen_from_microphone(self) -> str | None:
        if self._recognizer is None or self._microphone_cls is None:
            return None

        try:
            mic_kwargs = {}
            if self.microphone_index is not None:
                mic_kwargs["device_index"] = int(self.microphone_index)
            with self._microphone_cls(**mic_kwargs) as source:
                mic_name = self._current_microphone_name()
                print(f"Listening{f' on {mic_name}' if mic_name else ''}...")
                if not self.calibrate_once or not self._is_calibrated:
                    self._recognizer.adjust_for_ambient_noise(source, duration=self.ambient_calibration_duration)
                    self._is_calibrated = True
                audio = self._recognizer.listen(
                    source,
                    timeout=self.listen_timeout,
                    phrase_time_limit=self.phrase_time_limit,
                )
            text = self._recognize_audio(audio)
            if not text:
                return None
            print(f"You: {text}")
            return text.lower().strip()
        except KeyboardInterrupt:
            raise
        except self._sr.WaitTimeoutError:
            print("No speech detected.")
            self.logger.warning("STT timeout: no speech detected")
            return None
        except Exception as exc:
            print(f"Voice input failed: {exc}")
            self.logger.warning("STT failed: %s", exc)
            return None

    def _recognize_audio(self, audio) -> str | None:
        if self._recognizer is None or self._sr is None:
            return None

        last_error: Exception | None = None
        candidates: list[tuple[str, str, float]] = []
        for language in self.languages:
            try:
                result = self._recognizer.recognize_google(audio, language=language, show_all=True)
                language_candidates = self._extract_candidates(result, language)
                candidates.extend(language_candidates)
                if language_candidates and not self.try_all_languages:
                    break
            except self._sr.UnknownValueError as exc:
                last_error = exc
                continue
            except self._sr.RequestError as exc:
                print(f"Speech recognition service error: {exc}")
                self.logger.warning("Google STT request failed: %s", exc)
                return None

        if candidates:
            ranked_candidates = sorted(
                candidates,
                key=lambda candidate: self._score_candidate(candidate[0], candidate[1], candidate[2]),
                reverse=True,
            )
            selected = ranked_candidates[0]
            alternatives = ", ".join(f"{text} ({language})" for text, language, _ in ranked_candidates[:6])
            print(f"Heard alternatives: {alternatives}")
            print(f"Selected transcript: {selected[0]} ({selected[1]})")
            return selected[0]

        if last_error:
            print("Speech was heard, but I could not understand it.")
            self.logger.warning("STT could not understand audio after trying languages: %s", self.languages)
        return None

    def _extract_candidates(self, result, language: str) -> list[tuple[str, str, float]]:
        if not result:
            return []
        if isinstance(result, str):
            return [(result, language, 0.0)]
        alternatives = result.get("alternative", []) if isinstance(result, dict) else []
        candidates = []
        for alternative in alternatives:
            transcript = str(alternative.get("transcript", "")).strip()
            if transcript:
                confidence = float(alternative.get("confidence", 0.0) or 0.0)
                candidates.append((transcript, language, confidence))
        return candidates

    def _score_candidate(self, text: str, language: str, confidence: float) -> float:
        normalized = text.lower()
        score = confidence
        if language.lower().startswith("en"):
            score += 0.45

        wake_like_words = {"jarvis", "jervis", "travis", "service", "jarves", "jars"}
        wake_starters = {"hey", "hei", "hai", "hi"}
        command_words = {
            "open",
            "play",
            "search",
            "find",
            "close",
            "type",
            "write",
            "note",
            "time",
            "thanks",
            "thank",
            "hello",
        }
        target_words = {"spotify", "sportify", "youtube", "google", "github", "chrome", "notepad", "song", "music"}
        words = normalized.split()

        if any(word in normalized for word in wake_like_words):
            score += 3.0
        if words and words[0] in wake_starters:
            score += 1.0
        if len(words) >= 2 and words[0] in wake_starters:
            score += max(SequenceMatcher(None, words[1], "jarvis").ratio(), SequenceMatcher(None, words[1], "jervis").ratio())
        score += sum(0.55 for word in words if word in command_words)
        score += sum(0.45 for word in words if word in target_words)
        if "play this song" in normalized or "play the song" in normalized:
            score += 2.0
        if "open spotify" in normalized or "play spotify" in normalized:
            score += 1.5
        return score

    def _current_microphone_name(self) -> str | None:
        if self._microphone_cls is None:
            return None
        try:
            names = self._microphone_cls.list_microphone_names()
        except Exception:
            return None
        if self.microphone_index is None:
            return names[0] if names else None
        index = int(self.microphone_index)
        if 0 <= index < len(names):
            return f"#{index} {names[index]}"
        return None

    def _resolve_microphone_index(self, requested_index: Any) -> int | None:
        if self._microphone_cls is None:
            return None
        if requested_index is not None and str(requested_index).lower() != "auto":
            return int(requested_index)

        try:
            names = self._microphone_cls.list_microphone_names()
        except Exception:
            return None

        scored: list[tuple[int, int, str]] = []
        for index, name in enumerate(names):
            lowered = name.lower()
            if any(blocked in lowered for blocked in ["mapper", "output", "speaker", "headphone", "stereo mix", "primary sound"]):
                continue

            score = 0
            if "microphone array" in lowered:
                score += 50
            if "microphone" in lowered or "mic" in lowered:
                score += 30
            if "realtek" in lowered:
                score += 10
            if score:
                scored.append((score, -index, name))

        if not scored:
            return None

        best = max(scored)
        selected_index = -best[1]
        print(f"Auto-selected microphone #{selected_index}: {best[2]}")
        return selected_index

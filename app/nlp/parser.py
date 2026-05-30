from __future__ import annotations

from difflib import SequenceMatcher
import re

from app.config import AppConfig
from app.models import ParsedCommand
from app.nlp import intents
from app.nlp.gemini_parser import GeminiParser


class CommandParser:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.gemini = GeminiParser(config.gemini_api_key, config.gemini_model)

    def parse(self, raw_text: str) -> ParsedCommand:
        original_text = self._normalize(self._correct_common_transcript_errors(raw_text))
        text, wake_invoked = self._extract_wake_command(original_text)
        if wake_invoked and not text:
            return ParsedCommand(
                intent=intents.WAKE_PROMPT,
                raw_text=original_text,
                metadata={"wake_invoked": True},
            )

        command = self._parse_rule_based(text)
        command.raw_text = original_text
        command.metadata["wake_invoked"] = wake_invoked
        command.metadata["command_text"] = text

        use_ai = bool(self.config.settings.get("use_ai_parser", False))
        only_unknown = bool(self.config.settings.get("ai_parser_only_for_unknown", True))
        after_wake_only = bool(self.config.settings.get("ai_parser_after_wake_only", False))
        should_try_ai = use_ai and (not only_unknown or command.intent == intents.UNKNOWN)
        should_try_ai = should_try_ai and (not after_wake_only or wake_invoked)
        if should_try_ai:
            ai_command = self.gemini.parse(
                text,
                list(self.config.apps.keys()),
                list(self.config.websites.keys()),
                timeout=float(self.config.settings.get("gemini_timeout_seconds", 2)),
            )
            if ai_command and ai_command.intent != intents.UNKNOWN:
                ai_command.raw_text = original_text
                ai_command.metadata["wake_invoked"] = wake_invoked
                ai_command.metadata["command_text"] = text
                return self._apply_safety(ai_command)

        return self._apply_safety(command)

    def _parse_rule_based(self, text: str) -> ParsedCommand:
        conversation = self._parse_conversation(text)
        if conversation:
            return conversation

        if self._matches_any(text, ["stop", "exit", "shutdown", "shut down"]):
            return ParsedCommand(intent=intents.EXIT_ASSISTANT, raw_text=text)

        if self._matches_any(text, ["what time", "current time"]):
            return ParsedCommand(intent=intents.READ_TIME, raw_text=text)

        if text in {"play this song", "play the song", "play this music", "play current song"}:
            return ParsedCommand(
                intent=intents.PLAY_MEDIA,
                raw_text=text,
                metadata={"click_current_result": True},
            )

        if text in {"play", "play it", "play that"}:
            return ParsedCommand(
                intent=intents.PLAY_MEDIA,
                raw_text=text,
                metadata={"use_last_query": True},
            )

        play_match = re.match(r"^(play|put on)\s+(.+?)(\s+(on|in)\s+(.+))?$", text)
        if play_match:
            query = play_match.group(2).strip()
            target = (play_match.group(5) or "spotify").strip()
            website_key = self._match_config_target(target, self.config.websites)
            return ParsedCommand(
                intent=intents.PLAY_MEDIA,
                target=website_key or target,
                text=query,
                raw_text=text,
                metadata={"custom_site": website_key is None},
            )

        for prefix in ["make note", "create note", "note", "write down"]:
            if text.startswith(prefix):
                note_text = text.removeprefix(prefix).strip()
                return ParsedCommand(intent=intents.CREATE_NOTE, text=note_text, raw_text=text)

        for prefix in ["type", "write"]:
            if text.startswith(prefix):
                typed_text = text.removeprefix(prefix).strip()
                return ParsedCommand(intent=intents.TYPE_TEXT, text=typed_text, raw_text=text)

        site_search_match = re.match(r"^(search for|look up|search|find)\s+(.+?)\s+(on|in)\s+(.+)$", text)
        if site_search_match:
            query = site_search_match.group(2).strip()
            target = site_search_match.group(4).strip()
            website_key = self._match_config_target(target, self.config.websites)
            return ParsedCommand(
                intent=intents.SEARCH_SITE,
                target=website_key or target,
                text=query,
                raw_text=text,
                metadata={"custom_site": website_key is None},
            )

        for prefix in ["search for", "search", "find", "look up"]:
            if text.startswith(prefix):
                query = text.removeprefix(prefix).strip()
                return ParsedCommand(intent=intents.SEARCH_WEB, text=query, raw_text=text)

        close_match = re.match(r"^(close)\s+(.+)$", text)
        if close_match:
            return ParsedCommand(
                intent=intents.CLOSE_APP,
                target=close_match.group(2).strip(),
                raw_text=text,
                requires_confirmation=True,
            )

        open_match = re.match(r"^(open|please open|can you open|could you open)\s+(.+)$", text)
        if open_match:
            target = open_match.group(2).strip()
            target, prefer_website = self._strip_website_words(target)
            app_key = self._match_config_target(target, self.config.apps)
            if app_key and not prefer_website:
                return ParsedCommand(intent=intents.OPEN_APP, target=app_key, raw_text=text)

            website_key = self._match_config_target(target, self.config.websites)
            if website_key:
                return ParsedCommand(intent=intents.OPEN_WEBSITE, target=website_key, raw_text=text)

            if prefer_website and " " not in target and "." not in target:
                return ParsedCommand(
                    intent=intents.OPEN_WEBSITE,
                    target=f"{target}.com",
                    raw_text=text,
                    metadata={"custom_url": f"{target}.com"},
                )

            if self._looks_like_website(target):
                return ParsedCommand(
                    intent=intents.OPEN_WEBSITE,
                    target=target,
                    raw_text=text,
                    metadata={"custom_url": target},
                )

            return ParsedCommand(
                intent=intents.SEARCH_WEB,
                text=target,
                raw_text=text,
                requires_confirmation=True,
                metadata={"reason": "unknown_website_or_app"},
            )

        return ParsedCommand(intent=intents.UNKNOWN, raw_text=text)

    def _parse_conversation(self, text: str) -> ParsedCommand | None:
        cleaned = text.strip(" ,.!?")
        compact = cleaned.replace(" ", "")

        if cleaned in {"hello", "hi", "hey", "good morning", "good afternoon", "good evening"}:
            return self._conversation("Hello, sir.")

        if cleaned in {"thanks", "thank you", "thank you jarvis", "thanks jarvis"}:
            return self._conversation("You are welcome, sir.")

        if compact in {"terimakasih", "makasih"} or cleaned in {"terima kasih", "terima kasih jarvis"}:
            return self._conversation("You are welcome, sir.")

        if cleaned in {"how are you", "how are you doing", "are you okay"}:
            return self._conversation("I am fully operational, sir.")

        if cleaned in {"what is your name", "who are you", "introduce yourself"}:
            return self._conversation("I am Jarvis, your personal desktop assistant.")

        if cleaned in {"what can you do", "what are your commands", "help", "can you help me"}:
            return self._conversation(
                "I can open apps and websites, search the web, search Spotify, create notes, type text, and tell the time."
            )

        if cleaned in {"goodbye", "bye", "see you"}:
            return self._conversation("Goodbye, sir.")

        if cleaned in {"nice", "great", "good job", "well done"}:
            return self._conversation("Glad to be of service, sir.")

        return None

    def _conversation(self, response: str) -> ParsedCommand:
        return ParsedCommand(intent=intents.CONVERSATION, text=response, raw_text="")

    def _apply_safety(self, command: ParsedCommand) -> ParsedCommand:
        long_limit = int(self.config.settings.get("long_text_confirmation_chars", 120))
        if command.intent == intents.TYPE_TEXT and command.text and len(command.text) > long_limit:
            command.requires_confirmation = True
        if command.intent == intents.CLOSE_APP:
            command.requires_confirmation = True
        return command

    def _match_config_target(self, target: str, config_items: dict) -> str | None:
        best_key: str | None = None
        best_score = 0.0
        normalized_target = self._compact(target)

        for key, value in config_items.items():
            aliases = [key, *value.get("aliases", [])]
            if target in aliases:
                return key
            for alias in aliases:
                score = self._similar(normalized_target, self._compact(alias))
                if score > best_score:
                    best_score = score
                    best_key = key

        if best_key and best_score >= 0.74:
            return best_key
        return None

    def _matches_any(self, text: str, phrases: list[str]) -> bool:
        return any(phrase in text for phrase in phrases)

    def _normalize(self, text: str) -> str:
        return " ".join(text.lower().strip().split())

    def _compact(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", text.lower())

    def _correct_common_transcript_errors(self, text: str) -> str:
        normalized = self._normalize(text)
        replacements = {
            "sportify": "spotify",
            "spot if i": "spotify",
            "spotifi": "spotify",
            "spotty fi": "spotify",
            "spotty fly": "spotify",
            "you tube": "youtube",
            "git hub": "github",
            "chat gpt": "chatgpt",
            "hay jarvis": "hey jarvis",
            "hi service": "hey service",
            "hey surface": "hey service",
            "hey jeremy": "hey jarvis",
            "open spot": "open spotify",
            "play spot": "play spotify",
            "place song": "play this song",
            "play the sun": "play this song",
            "play this sound": "play this song",
            "play these song": "play this song",
            "play disco": "play this song",
        }
        for wrong, right in replacements.items():
            normalized = normalized.replace(wrong, right)
        return normalized

    def _strip_website_words(self, target: str) -> tuple[str, bool]:
        prefixes = ["website ", "web ", "site "]
        for prefix in prefixes:
            if target.startswith(prefix):
                return target.removeprefix(prefix).strip(), True
        return target, False

    def _looks_like_website(self, target: str) -> bool:
        if target.startswith(("http://", "https://")):
            return True
        return "." in target and " " not in target

    def _extract_wake_command(self, text: str) -> tuple[str, bool]:
        if not self.config.settings.get("wake_word_enabled", False):
            return text, False

        wake_words = [
            str(self.config.settings.get("wake_word", "")).strip().lower(),
            *[str(alias).strip().lower() for alias in self.config.settings.get("wake_word_aliases", [])],
        ]
        wake_words = [word for word in dict.fromkeys(wake_words) if word]
        for wake_word in sorted(wake_words, key=len, reverse=True):
            if text == wake_word:
                return "", True
            if text.startswith(wake_word + " "):
                return text.removeprefix(wake_word).strip(" ,.!?"), True
        if self.config.settings.get("wake_word_fuzzy", True):
            fuzzy_text, fuzzy_match = self._extract_fuzzy_wake_command(text)
            if fuzzy_match:
                return fuzzy_text, True
        return text, False

    def _extract_fuzzy_wake_command(self, text: str) -> tuple[str, bool]:
        words = text.split()
        if not words:
            return text, False

        wake_starters = {"hey", "hei", "hai", "hi"}
        jarvis_like = {"jarvis", "jervis", "travis", "service", "jarves", "jars"}

        if words[0] in jarvis_like or self._similar(words[0], "jarvis") >= 0.78:
            return " ".join(words[1:]).strip(), True

        if len(words) >= 2 and words[0] in wake_starters:
            second_word = words[1]
            similarity = max(self._similar(second_word, "jarvis"), self._similar(second_word, "jervis"))
            if second_word in jarvis_like or similarity >= 0.55:
                return " ".join(words[2:]).strip(), True

        for prefix_len in range(1, min(4, len(words)) + 1):
            prefix = " ".join(words[:prefix_len])
            for alias in self.config.settings.get("wake_word_aliases", []):
                if self._similar(prefix, str(alias).lower()) >= 0.78:
                    return " ".join(words[prefix_len:]).strip(), True

        return text, False

    def _similar(self, left: str, right: str) -> float:
        return SequenceMatcher(None, left, right).ratio()

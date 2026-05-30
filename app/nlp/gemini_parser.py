from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.models import ParsedCommand
from app.nlp import intents


ALLOWED_INTENTS = {
    intents.OPEN_APP,
    intents.OPEN_WEBSITE,
    intents.CLOSE_APP,
    intents.SEARCH_WEB,
    intents.SEARCH_SITE,
    intents.PLAY_MEDIA,
    intents.TYPE_TEXT,
    intents.CREATE_NOTE,
    intents.READ_TIME,
    intents.EXIT_ASSISTANT,
    intents.CONVERSATION,
    intents.UNKNOWN,
}


class GeminiParser:
    def __init__(self, api_key: str | None, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def parse(self, text: str, apps: list[str], websites: list[str], timeout: float = 2) -> ParsedCommand | None:
        if not self.api_key:
            return None

        prompt = self._build_prompt(text, apps, websites)
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

        response_text = self._extract_text(body)
        if not response_text:
            return None

        try:
            data = json.loads(self._strip_code_fence(response_text))
        except json.JSONDecodeError:
            return None

        intent = str(data.get("intent", intents.UNKNOWN))
        if intent not in ALLOWED_INTENTS:
            intent = intents.UNKNOWN

        target = data.get("target")
        command_text = data.get("text")
        if intent in {intents.CREATE_NOTE, intents.TYPE_TEXT, intents.SEARCH_WEB} and not command_text:
            command_text = target
            target = None

        return ParsedCommand(
            intent=intent,
            target=target,
            text=command_text,
            raw_text=text,
            requires_confirmation=bool(data.get("requires_confirmation", False)),
            metadata={"parser": "gemini"},
        )

    def _build_prompt(self, text: str, apps: list[str], websites: list[str]) -> str:
        return (
            "You are an intent parser for an English-only desktop assistant. "
            "Reply with valid JSON only, without markdown. "
            "Schema: {\"intent\":\"...\",\"target\":null|string,\"text\":null|string,"
            "\"requires_confirmation\":false|true}. "
            f"Intent valid: {sorted(ALLOWED_INTENTS)}. "
            f"Available apps: {apps}. Available websites: {websites}. "
            "Use open_app when the target app matches, open_website when the target website matches, "
            "search_web for general search, type_text for typing text, "
            "search_site for searching inside a website such as search for bohemian rhapsody on spotify, "
            "play_media for playing media such as play bohemian rhapsody on spotify, "
            "create_note for notes, read_time for time questions, "
            "conversation for simple small talk such as thanks, hello, who are you, how are you. "
            "exit_assistant for stop/exit/shut down. "
            "For create_note, type_text, and search_web, put the content in the text field. "
            "For unknown websites, use search_web and put the query in text. "
            f"User command: {text}"
        )

    def _extract_text(self, body: dict) -> str | None:
        try:
            parts = body["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError):
            return None
        return "".join(part.get("text", "") for part in parts).strip()

    def _strip_code_fence(self, text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            cleaned = cleaned.removesuffix("```").strip()
        return cleaned

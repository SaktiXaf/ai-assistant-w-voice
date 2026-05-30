from __future__ import annotations

import logging

from app.actions.notes import create_note
from app.actions.open_app import open_app
from app.actions.open_website import open_website, search_site
from app.actions.play_media import play_media
from app.actions.search_web import search_web
from app.actions.system import close_app, read_time
from app.actions.type_text import type_text
from app.config import AppConfig
from app.models import CommandResult, ParsedCommand
from app.nlp import intents


class ActionDispatcher:
    def __init__(self, config: AppConfig, logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger
        self.current_website: str | None = None
        self.last_site_search_query: str | None = None

    @property
    def _search_same_tab(self) -> bool:
        return bool(self.config.settings.get("search_in_same_tab", True))

    def execute(self, command: ParsedCommand) -> CommandResult:
        try:
            if command.intent == intents.OPEN_APP:
                result = open_app(command, self.config)
                if result.success and command.target in self.config.websites:
                    self.current_website = command.target
                if not result.success and command.target in self.config.websites:
                    website_command = ParsedCommand(
                        intent=intents.OPEN_WEBSITE,
                        target=command.target,
                        raw_text=command.raw_text,
                    )
                    result = open_website(website_command, self.config)
                    if result.success:
                        self.current_website = command.target
                return result
            if command.intent == intents.OPEN_WEBSITE:
                result = open_website(command, self.config)
                if result.success and result.data:
                    self.current_website = str(result.data.get("site") or command.target)
                return result
            if command.intent == intents.SEARCH_SITE:
                result = search_site(command, self.config, self.current_website, same_tab=self._search_same_tab)
                if result.success and result.data:
                    self.current_website = str(result.data.get("site") or self.current_website)
                    self.last_site_search_query = command.text
                return result
            if command.intent == intents.PLAY_MEDIA:
                if command.metadata.get("use_last_query"):
                    if self.current_website == "spotify" and self.last_site_search_query:
                        command.text = self.last_site_search_query
                    else:
                        command.metadata["click_current_result"] = True
                result = play_media(command, self.config, same_tab=self._search_same_tab)
                if result.success and result.data:
                    self.current_website = str(result.data.get("site") or self.current_website)
                    if command.text:
                        self.last_site_search_query = command.text
                return result
            if command.intent == intents.SEARCH_WEB:
                if self.current_website and self.config.settings.get("search_in_current_website", True):
                    result = search_site(command, self.config, self.current_website, same_tab=self._search_same_tab)
                    if result.success:
                        self.last_site_search_query = command.text
                    return result
                return search_web(command)
            if command.intent == intents.CREATE_NOTE:
                return create_note(command, self.config)
            if command.intent == intents.TYPE_TEXT:
                return type_text(command)
            if command.intent == intents.READ_TIME:
                return read_time()
            if command.intent == intents.CLOSE_APP:
                return close_app(command)
            return CommandResult(success=False, message="I do not recognize that command yet.")
        except Exception as exc:
            self.logger.exception("Action failed")
            return CommandResult(success=False, message=f"The action failed: {exc}")

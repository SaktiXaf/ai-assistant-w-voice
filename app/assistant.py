from __future__ import annotations

import logging

from app.actions.dispatcher import ActionDispatcher
from app.config import AppConfig, load_config
from app.logger import setup_logger
from app.models import CommandResult, ParsedCommand
from app.nlp import intents
from app.nlp.parser import CommandParser
from app.safety.confirmation import ConfirmationService
from app.voice.listener import VoiceListener
from app.voice.text_to_speech import TextToSpeech


class SaktiAssistant:
    def __init__(self, text_mode: bool = False, voice_enabled: bool = True) -> None:
        self.config: AppConfig = load_config()
        self.logger = setup_logger(self.config.logs_dir)
        self.text_mode = text_mode
        self.running = True

        settings_voice = bool(self.config.settings.get("voice_enabled", True))
        self.tts = TextToSpeech(
            enabled=voice_enabled and settings_voice,
            engine_name=str(self.config.settings.get("tts_engine", "sapi")),
            reinitialize_each_call=bool(self.config.settings.get("tts_reinitialize_each_call", True)),
        )
        self.listener = VoiceListener(
            language=str(self.config.settings.get("language", "id-ID")),
            languages=list(self.config.settings.get("stt_languages", [])),
            try_all_languages=bool(self.config.settings.get("stt_try_all_languages", False)),
            microphone_index=self.config.settings.get("microphone_index"),
            listen_timeout=float(self.config.settings.get("listen_timeout_seconds", 3)),
            phrase_time_limit=float(self.config.settings.get("phrase_time_limit_seconds", 5)),
            ambient_calibration_duration=float(self.config.settings.get("ambient_calibration_seconds", 0.25)),
            calibrate_once=bool(self.config.settings.get("calibrate_microphone_once", True)),
            pause_threshold=float(self.config.settings.get("pause_threshold_seconds", 0.55)),
            text_mode=text_mode,
            logger=self.logger,
        )
        self.parser = CommandParser(self.config)
        self.confirmation = ConfirmationService(self.listener, self.tts)
        self.confirmation.assistant_name = str(self.config.settings.get("assistant_name", "Jarvis"))
        self.dispatcher = ActionDispatcher(self.config, self.logger)

    def run(self) -> None:
        self._say(f"Hello, I am {self.config.settings.get('assistant_name', 'Jarvis')}.")
        try:
            while self.running:
                raw_text = self.listener.listen()
                if not raw_text:
                    self._print_only("I did not catch that command.")
                    continue
                self.handle_text(raw_text)
        except KeyboardInterrupt:
            self.running = False
            self._print_only("Assistant shutting down.")

    def handle_text(self, raw_text: str) -> CommandResult:
        command = self.parser.parse(raw_text)
        self._log_command(command)

        if command.intent == intents.WAKE_PROMPT:
            result = CommandResult(
                success=True,
                message=str(self.config.settings.get("wake_prompt_response", "what do you need sir")),
            )
            self._say(result.message)
            self._log_result(result)
            return result

        if command.intent == intents.CONVERSATION:
            result = CommandResult(success=True, message=command.text or "Yes, sir.")
            self._say(result.message)
            self._log_result(result)
            return result

        if command.intent == intents.EXIT_ASSISTANT:
            result = CommandResult(success=True, message="Assistant shutting down.")
            self._say(result.message)
            self.running = False
            self._log_result(result)
            return result

        if command.requires_confirmation and self.config.settings.get("confirm_sensitive_actions", True):
            confirmed = self.confirmation.ask("This command is sensitive. Are you sure you want to continue?")
            if not confirmed:
                result = CommandResult(success=False, message="Understood. Action cancelled.")
                self._say(result.message)
                self._log_result(result)
                return result

        if self._should_acknowledge_wake_command(command):
            self._say(str(self.config.settings.get("command_ack_response", "as your command")))

        result = self.dispatcher.execute(command)
        self._say(result.message)
        self._log_result(result)
        return result

    def _say(self, message: str) -> None:
        assistant_name = self.config.settings.get("assistant_name", "Jarvis")
        print(f"{assistant_name}: {message}")
        self.tts.speak(message)

    def _print_only(self, message: str) -> None:
        assistant_name = self.config.settings.get("assistant_name", "Jarvis")
        print(f"{assistant_name}: {message}")

    def _should_acknowledge_wake_command(self, command: ParsedCommand) -> bool:
        if not command.metadata.get("wake_invoked"):
            return False
        return command.intent not in {intents.UNKNOWN, intents.WAKE_PROMPT, intents.READ_TIME, intents.CONVERSATION}

    def _log_command(self, command: ParsedCommand) -> None:
        if not self.config.settings.get("log_commands", True):
            return
        self.logger.info("RAW: %s", command.raw_text)
        self.logger.info("INTENT: %s", command.intent)
        self.logger.info("TARGET: %s", command.target or "-")

    def _log_result(self, result: CommandResult) -> None:
        if not self.config.settings.get("log_commands", True):
            return
        status = "success" if result.success else "failed"
        self.logger.info("RESULT: %s - %s", status, result.message)

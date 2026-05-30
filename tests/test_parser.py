from __future__ import annotations

import unittest

from app.config import load_config
from app.nlp import intents
from app.nlp.parser import CommandParser


class ParserTest(unittest.TestCase):
    def setUp(self) -> None:
        config = load_config()
        config.settings["use_ai_parser"] = False
        self.parser = CommandParser(config)

    def test_open_app(self) -> None:
        command = self.parser.parse("open chrome")
        self.assertEqual(command.intent, intents.OPEN_APP)
        self.assertEqual(command.target, "chrome")

    def test_open_spotify_with_transcript_error(self) -> None:
        command = self.parser.parse("open sportify")
        self.assertEqual(command.intent, intents.OPEN_APP)
        self.assertEqual(command.target, "spotify")

    def test_open_youtube_with_spaced_transcript(self) -> None:
        command = self.parser.parse("open you tube")
        self.assertEqual(command.intent, intents.OPEN_WEBSITE)
        self.assertEqual(command.target, "youtube")

    def test_open_website(self) -> None:
        command = self.parser.parse("open youtube")
        self.assertEqual(command.intent, intents.OPEN_WEBSITE)
        self.assertEqual(command.target, "youtube")

    def test_search(self) -> None:
        command = self.parser.parse("search tutorial laravel")
        self.assertEqual(command.intent, intents.SEARCH_WEB)
        self.assertEqual(command.text, "tutorial laravel")

    def test_search_inside_website(self) -> None:
        command = self.parser.parse("search bohemian rhapsody on spotify")
        self.assertEqual(command.intent, intents.SEARCH_SITE)
        self.assertEqual(command.target, "spotify")
        self.assertEqual(command.text, "bohemian rhapsody")

    def test_open_custom_domain(self) -> None:
        command = self.parser.parse("open detik.com")
        self.assertEqual(command.intent, intents.OPEN_WEBSITE)
        self.assertEqual(command.target, "detik.com")

    def test_open_custom_website_without_dot(self) -> None:
        command = self.parser.parse("open website detik")
        self.assertEqual(command.intent, intents.OPEN_WEBSITE)
        self.assertEqual(command.target, "detik.com")

    def test_note(self) -> None:
        command = self.parser.parse("create note learn database at 8")
        self.assertEqual(command.intent, intents.CREATE_NOTE)
        self.assertEqual(command.text, "learn database at 8")

    def test_type_text(self) -> None:
        command = self.parser.parse("type hello world")
        self.assertEqual(command.intent, intents.TYPE_TEXT)
        self.assertEqual(command.text, "hello world")

    def test_exit(self) -> None:
        command = self.parser.parse("shut down")
        self.assertEqual(command.intent, intents.EXIT_ASSISTANT)

    def test_wake_prompt(self) -> None:
        command = self.parser.parse("hey jarvis")
        self.assertEqual(command.intent, intents.WAKE_PROMPT)
        self.assertTrue(command.metadata["wake_invoked"])

    def test_wake_command(self) -> None:
        command = self.parser.parse("hey jarvis open spotify")
        self.assertEqual(command.intent, intents.OPEN_APP)
        self.assertEqual(command.target, "spotify")
        self.assertTrue(command.metadata["wake_invoked"])

    def test_wake_polite_open(self) -> None:
        command = self.parser.parse("hey jarvis please open spotify")
        self.assertEqual(command.intent, intents.OPEN_APP)
        self.assertEqual(command.target, "spotify")
        self.assertTrue(command.metadata["wake_invoked"])

    def test_play_defaults_to_spotify_search(self) -> None:
        command = self.parser.parse("hey jarvis play bohemian rhapsody")
        self.assertEqual(command.intent, intents.PLAY_MEDIA)
        self.assertEqual(command.target, "spotify")
        self.assertEqual(command.text, "bohemian rhapsody")

    def test_play_current_result(self) -> None:
        command = self.parser.parse("hey jarvis play")
        self.assertEqual(command.intent, intents.PLAY_MEDIA)
        self.assertTrue(command.metadata["use_last_query"])

    def test_play_this_song_clicks_current_result(self) -> None:
        command = self.parser.parse("hey jarvis play this song")
        self.assertEqual(command.intent, intents.PLAY_MEDIA)
        self.assertTrue(command.metadata["click_current_result"])

    def test_search_for_inside_website(self) -> None:
        command = self.parser.parse("hey jarvis search for bohemian rhapsody on spotify")
        self.assertEqual(command.intent, intents.SEARCH_SITE)
        self.assertEqual(command.target, "spotify")
        self.assertEqual(command.text, "bohemian rhapsody")

    def test_wake_typo_alias(self) -> None:
        command = self.parser.parse("hey jervis open website spotify")
        self.assertEqual(command.intent, intents.OPEN_WEBSITE)
        self.assertEqual(command.target, "spotify")
        self.assertTrue(command.metadata["wake_invoked"])

    def test_indonesian_command_is_not_supported(self) -> None:
        command = self.parser.parse("buka spotify")
        self.assertEqual(command.intent, intents.UNKNOWN)

    def test_thank_you_conversation(self) -> None:
        command = self.parser.parse("thank you")
        self.assertEqual(command.intent, intents.CONVERSATION)
        self.assertEqual(command.text, "You are welcome, sir.")

    def test_indonesian_thanks_conversation(self) -> None:
        command = self.parser.parse("terima kasih")
        self.assertEqual(command.intent, intents.CONVERSATION)
        self.assertEqual(command.text, "You are welcome, sir.")

    def test_help_conversation(self) -> None:
        command = self.parser.parse("hey jarvis what can you do")
        self.assertEqual(command.intent, intents.CONVERSATION)
        self.assertIn("open apps", command.text)
        self.assertTrue(command.metadata["wake_invoked"])

    def test_who_are_you_conversation(self) -> None:
        command = self.parser.parse("who are you")
        self.assertEqual(command.intent, intents.CONVERSATION)
        self.assertEqual(command.text, "I am Jarvis, your personal desktop assistant.")

    def test_wake_fuzzy_travis(self) -> None:
        command = self.parser.parse("hey travis open spotify")
        self.assertEqual(command.intent, intents.OPEN_APP)
        self.assertEqual(command.target, "spotify")
        self.assertTrue(command.metadata["wake_invoked"])

    def test_wake_fuzzy_service(self) -> None:
        command = self.parser.parse("hey service open spotify")
        self.assertEqual(command.intent, intents.OPEN_APP)
        self.assertEqual(command.target, "spotify")
        self.assertTrue(command.metadata["wake_invoked"])


if __name__ == "__main__":
    unittest.main()

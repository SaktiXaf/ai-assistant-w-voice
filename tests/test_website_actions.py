from __future__ import annotations

import logging
import unittest
from unittest.mock import patch

from app.actions.dispatcher import ActionDispatcher
from app.actions.play_media import play_media
from app.actions.open_website import open_website, search_site
from app.config import load_config
from app.models import ParsedCommand
from app.nlp import intents


class WebsiteActionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config()
        self.config.settings["spotify_play_backend"] = "web"

    @patch("webbrowser.open")
    def test_open_custom_domain_adds_https(self, open_mock) -> None:
        command = ParsedCommand(
            intent=intents.OPEN_WEBSITE,
            target="detik.com",
            raw_text="buka detik.com",
            metadata={"custom_url": "detik.com"},
        )
        result = open_website(command, self.config)
        self.assertTrue(result.success)
        open_mock.assert_called_once_with("https://detik.com")

    @patch("webbrowser.open")
    def test_spotify_search_uses_spotify_search_url(self, open_mock) -> None:
        command = ParsedCommand(
            intent=intents.SEARCH_SITE,
            target="spotify",
            text="bohemian rhapsody",
            raw_text="cari bohemian rhapsody di spotify",
        )
        result = search_site(command, self.config)
        self.assertTrue(result.success)
        open_mock.assert_called_once_with("https://open.spotify.com/search/bohemian+rhapsody")

    @patch("pyautogui.press")
    @patch("pyautogui.write")
    @patch("pyautogui.hotkey")
    @patch("webbrowser.open")
    def test_spotify_search_same_tab_uses_address_bar(self, open_mock, hotkey_mock, write_mock, press_mock) -> None:
        command = ParsedCommand(
            intent=intents.SEARCH_SITE,
            target="spotify",
            text="bohemian rhapsody",
            raw_text="cari bohemian rhapsody di spotify",
        )
        result = search_site(command, self.config, same_tab=True)
        self.assertTrue(result.success)
        hotkey_mock.assert_called_once_with("ctrl", "l")
        write_mock.assert_called_once_with("https://open.spotify.com/search/bohemian+rhapsody", interval=0)
        press_mock.assert_called_once_with("enter")
        open_mock.assert_not_called()

    @patch("time.sleep")
    @patch("pyautogui.doubleClick")
    @patch("pyautogui.moveTo")
    @patch("pyautogui.size", return_value=(1000, 800))
    @patch("pyautogui.press")
    @patch("pyautogui.write")
    @patch("pyautogui.hotkey")
    def test_play_spotify_opens_search_and_clicks_first_result(
        self,
        hotkey_mock,
        write_mock,
        press_mock,
        size_mock,
        move_mock,
        double_click_mock,
        sleep_mock,
    ) -> None:
        command = ParsedCommand(
            intent=intents.PLAY_MEDIA,
            target="spotify",
            text="bohemian rhapsody",
            raw_text="play bohemian rhapsody",
        )
        result = play_media(command, self.config, same_tab=True)
        self.assertTrue(result.success)
        self.assertTrue(result.data["autoplay_ok"])
        hotkey_mock.assert_called_once_with("ctrl", "l")
        write_mock.assert_called_once_with("https://open.spotify.com/search/bohemian+rhapsody", interval=0)
        move_mock.assert_called_once_with(350, 288, duration=0.1)
        double_click_mock.assert_called_once()

    @patch("time.sleep")
    @patch("pyautogui.doubleClick")
    @patch("pyautogui.moveTo")
    @patch("pyautogui.size", return_value=(1000, 800))
    @patch("pyautogui.press")
    @patch("os.startfile")
    def test_play_spotify_desktop_protocol_first(
        self,
        startfile_mock,
        press_mock,
        size_mock,
        move_mock,
        double_click_mock,
        sleep_mock,
    ) -> None:
        self.config.settings["spotify_play_backend"] = "desktop_first"
        command = ParsedCommand(
            intent=intents.PLAY_MEDIA,
            target="spotify",
            text="bohemian rhapsody",
            raw_text="play bohemian rhapsody",
        )
        result = play_media(command, self.config, same_tab=True)
        self.assertTrue(result.success)
        startfile_mock.assert_called_once_with("spotify:search:bohemian%20rhapsody")
        double_click_mock.assert_called_once()

    @patch("time.sleep")
    @patch("pyautogui.doubleClick")
    @patch("pyautogui.moveTo")
    @patch("pyautogui.size", return_value=(1000, 800))
    @patch("pyautogui.press")
    @patch("pyautogui.write")
    @patch("pyautogui.hotkey")
    def test_search_then_play_uses_last_spotify_query(
        self,
        hotkey_mock,
        write_mock,
        press_mock,
        size_mock,
        move_mock,
        double_click_mock,
        sleep_mock,
    ) -> None:
        dispatcher = ActionDispatcher(self.config, logging.getLogger("test"))
        dispatcher.current_website = "spotify"
        search_command = ParsedCommand(intent=intents.SEARCH_WEB, text="the cure", raw_text="search the cure")
        dispatcher.execute(search_command)

        play_command = ParsedCommand(
            intent=intents.PLAY_MEDIA,
            raw_text="play",
            metadata={"use_last_query": True},
        )
        result = dispatcher.execute(play_command)
        self.assertTrue(result.success)
        self.assertEqual(dispatcher.last_site_search_query, "the cure")
        write_mock.assert_called_with("https://open.spotify.com/search/the+cure", interval=0)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import os
import time
from urllib.parse import quote, quote_plus

from app.actions.open_website import open_url
from app.config import AppConfig
from app.models import CommandResult, ParsedCommand


def play_media(command: ParsedCommand, config: AppConfig, same_tab: bool = True) -> CommandResult:
    query = (command.text or "").strip()
    service = (command.target or "spotify").strip().lower()
    if not query:
        if command.metadata.get("click_current_result"):
            autoplay_ok = _try_start_spotify_playback(config, search_was_opened=False)
            if autoplay_ok:
                return CommandResult(
                    success=True,
                    message="Playing this song on Spotify.",
                    data={"site": "spotify", "autoplay_attempted": True, "autoplay_ok": True},
                )
        return CommandResult(success=False, message="What should I play?")

    if service != "spotify":
        return CommandResult(success=False, message=f"I can only play media on Spotify for now.")

    autoplay_enabled = bool(config.settings.get("spotify_autoplay", True))
    autoplay_ok = False
    backend = str(config.settings.get("spotify_play_backend", "desktop_first")).lower()

    if autoplay_enabled:
        if backend in {"desktop", "desktop_first", "auto"}:
            autoplay_ok = _try_play_with_spotify_desktop(query, config)

    url = _spotify_search_url(query, config)
    if not autoplay_ok:
        open_url(url, same_tab=same_tab)
        if autoplay_enabled:
            autoplay_ok = _try_start_spotify_playback(config, search_was_opened=True)

    if autoplay_ok:
        message = f"Playing {query} on Spotify."
    else:
        message = f"I opened Spotify search for {query}. Please select the first result if it does not start playing."

    return CommandResult(
        success=True,
        message=message,
        data={"url": url, "site": "spotify", "autoplay_attempted": autoplay_enabled, "autoplay_ok": autoplay_ok},
    )


def _spotify_search_url(query: str, config: AppConfig) -> str:
    spotify_config = config.websites.get("spotify", {})
    search_url = str(spotify_config.get("search_url", "https://open.spotify.com/search/{query}"))
    return search_url.replace("{query}", quote_plus(query))


def _spotify_search_uri(query: str) -> str:
    return "spotify:search:" + quote(query, safe="")


def _try_play_with_spotify_desktop(query: str, config: AppConfig) -> bool:
    try:
        os.startfile(_spotify_search_uri(query))
        time.sleep(float(config.settings.get("spotify_desktop_wait_seconds", 3)))
        return _try_start_spotify_playback(config, search_was_opened=True)
    except Exception:
        return False


def _try_start_spotify_playback(config: AppConfig, search_was_opened: bool) -> bool:
    try:
        import pyautogui

        wait_seconds = float(config.settings.get("spotify_play_wait_seconds", 4 if search_was_opened else 0.8))
        x_ratio = float(config.settings.get("spotify_first_result_click_x_ratio", 0.35))
        y_ratio = float(config.settings.get("spotify_first_result_click_y_ratio", 0.36))

        time.sleep(wait_seconds)
        width, height = pyautogui.size()
        x = int(width * x_ratio)
        y = int(height * y_ratio)

        pyautogui.press("esc")
        time.sleep(0.1)

        if search_was_opened:
            pyautogui.moveTo(x, y, duration=0.1)
            pyautogui.doubleClick()
            time.sleep(0.8)
            pyautogui.press("enter")
        else:
            pyautogui.press("enter")
        return True
    except Exception:
        return False

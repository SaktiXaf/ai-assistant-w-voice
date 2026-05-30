from __future__ import annotations

import webbrowser
from urllib.parse import quote_plus

from app.config import AppConfig
from app.models import CommandResult, ParsedCommand


def open_website(command: ParsedCommand, config: AppConfig) -> CommandResult:
    if not command.target:
        return CommandResult(success=False, message="Which website should I open?")

    is_known_site = command.target in config.websites
    if is_known_site:
        url = str(config.websites[command.target].get("url", "")).strip()
        site_name = command.target
    else:
        url = _normalize_url(str(command.metadata.get("custom_url") or command.target))
        site_name = command.target

    if not url:
        return CommandResult(success=False, message="The website URL is not configured yet.")

    open_url(url)
    return CommandResult(
        success=True,
        message=f"Opening {site_name}.",
        data={"url": url, "site": site_name, "known_site": is_known_site},
    )


def search_site(
    command: ParsedCommand,
    config: AppConfig,
    fallback_site: str | None = None,
    same_tab: bool = False,
) -> CommandResult:
    query = (command.text or "").strip()
    site = (command.target or fallback_site or "").strip()
    if not query:
        return CommandResult(success=False, message="What should I search for?")
    if not site:
        return CommandResult(success=False, message="Which website should I search in?")

    if site in config.websites:
        site_config = config.websites[site]
        search_url = str(site_config.get("search_url", "")).strip()
        if search_url:
            url = search_url.replace("{query}", quote_plus(query))
        else:
            url = _google_site_search(query, str(site_config.get("url", site)))
        label = site
    else:
        url = _google_site_search(query, site)
        label = site

    open_url(url, same_tab=same_tab)
    return CommandResult(
        success=True,
        message=f"Searching for {query} on {label}.",
        data={"url": url, "site": label},
    )


def _normalize_url(value: str) -> str:
    value = value.strip()
    if value.startswith(("http://", "https://")):
        return value
    return "https://" + value


def _google_site_search(query: str, site: str) -> str:
    normalized = _normalize_url(site)
    domain = normalized.removeprefix("https://").removeprefix("http://").split("/", 1)[0]
    return "https://www.google.com/search?q=" + quote_plus(f"site:{domain} {query}")


def open_url(url: str, same_tab: bool = False) -> None:
    if not same_tab:
        webbrowser.open(url)
        return

    try:
        import pyautogui

        pyautogui.hotkey("ctrl", "l")
        pyautogui.write(url, interval=0)
        pyautogui.press("enter")
    except Exception:
        webbrowser.open(url, new=0)

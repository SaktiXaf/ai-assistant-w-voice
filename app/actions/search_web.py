from __future__ import annotations

import urllib.parse
import webbrowser

from app.models import CommandResult, ParsedCommand


def search_web(command: ParsedCommand) -> CommandResult:
    query = (command.text or command.target or "").strip()
    if not query:
        return CommandResult(success=False, message="What should I search for?")

    url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
    webbrowser.open(url)
    return CommandResult(success=True, message=f"Searching for {query}.", data={"url": url})

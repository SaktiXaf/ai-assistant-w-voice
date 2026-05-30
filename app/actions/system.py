from __future__ import annotations

import subprocess
from datetime import datetime

from app.models import CommandResult, ParsedCommand


def read_time() -> CommandResult:
    now = datetime.now()
    return CommandResult(success=True, message=f"The time is {now:%H:%M}.")


def close_app(command: ParsedCommand) -> CommandResult:
    target = (command.target or "").strip().lower()
    if not target:
        return CommandResult(success=False, message="Which application should I close?")

    process_map = {
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "vscode": "Code.exe",
        "vs code": "Code.exe",
        "notepad": "notepad.exe",
        "spotify": "Spotify.exe",
    }
    process_name = process_map.get(target, target if target.endswith(".exe") else f"{target}.exe")
    completed = subprocess.run(
        ["taskkill", "/IM", process_name, "/F"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return CommandResult(success=False, message=f"I could not find or close {target}.")
    return CommandResult(success=True, message=f"Closing {target}.")

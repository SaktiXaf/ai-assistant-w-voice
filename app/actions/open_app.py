from __future__ import annotations

import os
import subprocess
from pathlib import Path

from app.config import AppConfig
from app.models import CommandResult, ParsedCommand


def open_app(command: ParsedCommand, config: AppConfig) -> CommandResult:
    if not command.target or command.target not in config.apps:
        return CommandResult(success=False, message="That application is not registered in the config.")

    app_config = config.apps[command.target]
    raw_path = str(app_config.get("path", "")).strip()
    if not raw_path:
        return CommandResult(success=False, message="The application path is not configured yet.")

    path = os.path.expandvars(raw_path)
    executable = path

    if "\\" in path or "/" in path:
        if not Path(path).exists():
            return CommandResult(success=False, message=f"I could not find {command.target}.")
        executable = path

    subprocess.Popen([executable], shell=False)
    return CommandResult(success=True, message=f"Opening {command.target}.")

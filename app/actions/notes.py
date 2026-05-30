from __future__ import annotations

from datetime import datetime

from app.config import AppConfig
from app.models import CommandResult, ParsedCommand


def create_note(command: ParsedCommand, config: AppConfig) -> CommandResult:
    text = (command.text or "").strip()
    if not text:
        return CommandResult(success=False, message="What should I write in the note?")

    now = datetime.now()
    filename = now.strftime("%Y%m%d_%H%M%S.txt")
    path = config.notes_dir / filename
    content = f"Tanggal: {now:%Y-%m-%d}\nIsi: {text}\n"
    path.write_text(content, encoding="utf-8")

    return CommandResult(
        success=True,
        message="The note has been created.",
        data={"path": str(path)},
    )

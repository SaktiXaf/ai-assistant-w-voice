from __future__ import annotations

from app.models import CommandResult, ParsedCommand


def type_text(command: ParsedCommand) -> CommandResult:
    text = (command.text or "").strip()
    if not text:
        return CommandResult(success=False, message="There is no text to type yet.")

    try:
        import pyautogui

        pyautogui.write(text, interval=0.01)
    except Exception as exc:
        return CommandResult(success=False, message=f"I could not type the text: {exc}")

    return CommandResult(success=True, message="The text has been typed.")

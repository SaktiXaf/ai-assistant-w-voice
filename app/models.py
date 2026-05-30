from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ParsedCommand(BaseModel):
    intent: str = "unknown"
    target: str | None = None
    text: str | None = None
    raw_text: str
    requires_confirmation: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommandResult(BaseModel):
    success: bool
    message: str
    data: dict[str, Any] | None = None

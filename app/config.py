from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class AppConfig:
    base_dir: Path
    data_dir: Path
    notes_dir: Path
    logs_dir: Path
    apps: dict[str, Any]
    websites: dict[str, Any]
    settings: dict[str, Any]
    gemini_api_key: str | None
    gemini_model: str


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in {path}: line {exc.lineno}, column {exc.colno}. "
                "Check for missing quotes, commas, or broken keys."
            ) from exc


def load_config() -> AppConfig:
    load_dotenv(BASE_DIR / ".env")

    data_dir = BASE_DIR / "data"
    notes_dir = data_dir / "notes"
    logs_dir = data_dir / "logs"
    notes_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    return AppConfig(
        base_dir=BASE_DIR,
        data_dir=data_dir,
        notes_dir=notes_dir,
        logs_dir=logs_dir,
        apps=_read_json(BASE_DIR / "config" / "apps.json"),
        websites=_read_json(BASE_DIR / "config" / "websites.json"),
        settings=_read_json(BASE_DIR / "config" / "settings.json"),
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
    )

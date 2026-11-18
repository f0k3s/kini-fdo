"""Настройки приложения. Значения можно переопределить переменными окружения."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./finance.db"
    debug: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///./finance.db"),
            debug=os.getenv("DEBUG", "0") == "1",
        )

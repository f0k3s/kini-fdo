"""Пакет репозиториев."""

from app.repositories.base import Repository
from app.repositories.memory import InMemoryRepository
from app.repositories.sql import SqlRepository

__all__ = ["Repository", "InMemoryRepository", "SqlRepository"]

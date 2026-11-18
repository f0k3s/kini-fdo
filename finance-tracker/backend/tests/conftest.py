"""Общие фикстуры тестов."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.memory import InMemoryRepository

FROZEN_TODAY = date(2026, 11, 17)


@pytest.fixture
def repository() -> InMemoryRepository:
    """Свежее хранилище в памяти на каждый тест."""
    return InMemoryRepository()


@pytest.fixture
def today() -> date:
    """Фиксированная «сегодняшняя» дата, чтобы тесты не ломались со временем."""
    return FROZEN_TODAY


@pytest.fixture
def client(repository: InMemoryRepository) -> TestClient:
    """HTTP-клиент без сети: запросы идут прямо в приложение."""
    return TestClient(create_app(repository))


@pytest.fixture
def account(repository: InMemoryRepository):
    """Счёт с начальным балансом 1000.00 для тестов операций."""
    return repository.create_account("Основной", Decimal("1000.00"))

"""Интеграционные тесты SqlRepository на SQLite в памяти.

Проверяют, что ORM-слой и in-memory реализация ведут себя одинаково.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.pool import StaticPool

from app.db.session import create_engine_for, create_session_factory, init_schema
from app.domain.models import OperationType
from app.repositories.sql import SqlRepository


@pytest.fixture
def repo() -> SqlRepository:
    engine = create_engine_for("sqlite://")
    init_schema(engine)
    yield SqlRepository(create_session_factory(engine))
    engine.dispose()


def test_account_round_trip(repo):
    account = repo.create_account("Основной", Decimal("1000.50"))
    fetched = repo.get_account(account.id)
    assert fetched is not None
    assert fetched.name == "Основной"
    assert fetched.initial_balance == Decimal("1000.50")


def test_balance_counts_income_and_expense(repo):
    account = repo.create_account("Основной", Decimal("100.00"))
    repo.create_operation(account.id, OperationType.INCOME, Decimal("50"), "зарплата", date(2026, 11, 1))
    repo.create_operation(account.id, OperationType.EXPENSE, Decimal("30"), "продукты", date(2026, 11, 2))
    assert repo.balance(account.id) == Decimal("120.00")


def test_balance_for_missing_account_is_none(repo):
    assert repo.balance("нет-такого") is None


def test_list_operations_respects_range(repo):
    account = repo.create_account("Основной", Decimal("0"))
    repo.create_operation(account.id, OperationType.EXPENSE, Decimal("1"), "прочее", date(2026, 11, 1))
    repo.create_operation(account.id, OperationType.EXPENSE, Decimal("2"), "прочее", date(2026, 12, 1))
    found = repo.list_operations(start=date(2026, 11, 1), end=date(2026, 11, 30))
    assert [op.amount for op in found] == [Decimal("1.00")]


def test_delete_account_removes_operations(repo):
    account = repo.create_account("Временный", Decimal("0"))
    repo.create_operation(account.id, OperationType.EXPENSE, Decimal("1"), "прочее", date(2026, 11, 1))
    assert repo.delete_account(account.id) is True
    assert repo.list_operations() == []


def test_delete_missing_account_returns_false(repo):
    assert repo.delete_account("нет-такого") is False


def test_delete_operation(repo):
    account = repo.create_account("Основной", Decimal("0"))
    operation = repo.create_operation(account.id, OperationType.EXPENSE, Decimal("1"), "прочее", date(2026, 11, 1))
    assert repo.delete_operation(operation.id) is True
    assert repo.get_operation(operation.id) is None


def test_money_is_stored_as_integer_cents(repo):
    account = repo.create_account("Копейки", Decimal("0.07"))
    assert repo.get_account(account.id).initial_balance == Decimal("0.07")

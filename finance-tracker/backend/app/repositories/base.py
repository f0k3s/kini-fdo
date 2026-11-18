"""Интерфейс репозитория.

Сервисы зависят только от этого протокола, поэтому в юнит-тестах
подставляется InMemoryRepository, а в приложении — SqlRepository.
Репозиторий работает с доменными объектами, а не с ORM-строками.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol, runtime_checkable

from app.domain.models import Account, Operation, OperationType


@runtime_checkable
class Repository(Protocol):
    """Контракт хранилища счетов и операций."""

    def create_account(self, name: str, initial_balance: Decimal) -> Account: ...

    def get_account(self, account_id: str) -> Account | None: ...

    def list_accounts(self) -> list[Account]: ...

    def delete_account(self, account_id: str) -> bool: ...

    def create_operation(
        self,
        account_id: str,
        op_type: OperationType,
        amount: Decimal,
        category: str,
        day: date,
        comment: str = "",
    ) -> Operation: ...

    def get_operation(self, operation_id: str) -> Operation | None: ...

    def list_operations(
        self,
        start: date | None = None,
        end: date | None = None,
        account_id: str | None = None,
    ) -> list[Operation]: ...

    def delete_operation(self, operation_id: str) -> bool: ...

    def balance(self, account_id: str) -> Decimal | None: ...

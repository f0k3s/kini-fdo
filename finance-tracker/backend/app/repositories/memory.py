"""Репозиторий в памяти.

Используется в юнит-тестах и в деморежиме: ни базы, ни сети.
Поведение должно совпадать с SqlRepository.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.domain.models import Account, Operation, OperationType


class InMemoryRepository:
    """Хранилище в словарях."""

    def __init__(self) -> None:
        self._accounts: dict[str, Account] = {}
        self._operations: dict[str, Operation] = {}

    def create_account(self, name: str, initial_balance: Decimal) -> Account:
        account = Account(
            id=str(uuid.uuid4()), name=name, initial_balance=initial_balance
        )
        self._accounts[account.id] = account
        return account

    def get_account(self, account_id: str) -> Account | None:
        return self._accounts.get(account_id)

    def list_accounts(self) -> list[Account]:
        return list(self._accounts.values())

    def delete_account(self, account_id: str) -> bool:
        if account_id not in self._accounts:
            return False
        del self._accounts[account_id]
        for operation_id in [
            op.id for op in self._operations.values() if op.account_id == account_id
        ]:
            del self._operations[operation_id]
        return True

    def create_operation(
        self,
        account_id: str,
        op_type: OperationType,
        amount: Decimal,
        category: str,
        day: date,
        comment: str = "",
    ) -> Operation:
        operation = Operation(
            id=str(uuid.uuid4()),
            account_id=account_id,
            type=op_type,
            amount=amount,
            category=category,
            day=day,
            comment=comment,
        )
        self._operations[operation.id] = operation
        return operation

    def get_operation(self, operation_id: str) -> Operation | None:
        return self._operations.get(operation_id)

    def list_operations(
        self,
        start: date | None = None,
        end: date | None = None,
        account_id: str | None = None,
    ) -> list[Operation]:
        result = []
        for operation in self._operations.values():
            if start is not None and operation.day < start:
                continue
            if end is not None and operation.day > end:
                continue
            if account_id is not None and operation.account_id != account_id:
                continue
            result.append(operation)
        return sorted(result, key=lambda op: (op.day, op.id))

    def delete_operation(self, operation_id: str) -> bool:
        if operation_id not in self._operations:
            return False
        del self._operations[operation_id]
        return True

    def balance(self, account_id: str) -> Decimal | None:
        account = self._accounts.get(account_id)
        if account is None:
            return None
        total = account.initial_balance
        for operation in self._operations.values():
            if operation.account_id == account_id:
                total += operation.signed_amount
        return total

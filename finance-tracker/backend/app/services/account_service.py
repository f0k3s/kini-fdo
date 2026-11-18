"""Сервис счетов: валидация и работа с балансом."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.errors import NotFoundError, ValidationError
from app.domain.models import Account, Operation
from app.domain.money import to_decimal
from app.repositories.base import Repository

MAX_NAME_LENGTH = 100


@dataclass(frozen=True)
class AccountView:
    """Счёт вместе с вычисленным текущим балансом."""

    account: Account
    balance: Decimal


class AccountService:
    """Бизнес-правила по счетам."""

    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    def create(self, name: str, initial_balance: str | Decimal = "0") -> Account:
        if not isinstance(name, str):
            raise ValidationError("имя счёта должно быть строкой")
        clean_name = name.strip()
        if not clean_name:
            raise ValidationError("имя счёта не может быть пустым")
        if len(clean_name) > MAX_NAME_LENGTH:
            raise ValidationError(
                f"имя счёта длиннее {MAX_NAME_LENGTH} символов"
            )
        try:
            balance = to_decimal(initial_balance)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"некорректный начальный баланс: {exc}") from exc
        if balance < 0:
            raise ValidationError("начальный баланс не может быть отрицательным")
        return self._repository.create_account(clean_name, balance)

    def get(self, account_id: str) -> Account:
        account = self._repository.get_account(account_id)
        if account is None:
            raise NotFoundError(f"счёт {account_id} не найден")
        return account

    def get_view(self, account_id: str) -> AccountView:
        account = self.get(account_id)
        balance = self._repository.balance(account_id)
        return AccountView(account=account, balance=balance or Decimal("0.00"))

    def list(self) -> list[AccountView]:
        return [self.get_view(account.id) for account in self._repository.list_accounts()]

    def delete(self, account_id: str) -> None:
        self.get(account_id)
        self._repository.delete_account(account_id)

    def operations(self, account_id: str) -> list[Operation]:
        self.get(account_id)
        return self._repository.list_operations(account_id=account_id)

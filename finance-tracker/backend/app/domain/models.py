"""Сущности предметной области.

Это обычные dataclass'ы, не связанные с SQLAlchemy и FastAPI:
их удобно создавать в тестах и сравнивать между собой.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum


class OperationType(str, Enum):
    """Тип операции."""

    INCOME = "income"
    EXPENSE = "expense"

    @classmethod
    def parse(cls, value) -> "OperationType":
        if isinstance(value, cls):
            return value
        aliases = {
            "income": cls.INCOME,
            "доход": cls.INCOME,
            "expense": cls.EXPENSE,
            "расход": cls.EXPENSE,
        }
        key = str(value).strip().lower()
        if key not in aliases:
            raise ValueError(f"неизвестный тип операции: {value!r}")
        return aliases[key]


@dataclass(frozen=True)
class Account:
    """Счёт пользователя. balance — начальный баланс, текущий считается по операциям."""

    id: str
    name: str
    initial_balance: Decimal

    @property
    def is_empty(self) -> bool:
        return self.initial_balance == Decimal("0.00")


@dataclass(frozen=True)
class Operation:
    """Запись о движении денег. Сумма всегда положительная."""

    id: str
    account_id: str
    type: OperationType
    amount: Decimal
    category: str
    day: date
    comment: str = ""

    @property
    def month(self) -> str:
        return self.day.strftime("%Y-%m")

    @property
    def signed_amount(self) -> Decimal:
        """Сумма со знаком: доход положительный, расход отрицательный."""
        return self.amount if self.type is OperationType.INCOME else -self.amount

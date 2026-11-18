"""Схемы запросов и ответов.

Суммы принимаются и отдаются строками: JSON-числа в JavaScript
теряют точность на больших значениях.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    initial_balance: str = Field(default="0", description="Сумма строкой, например '1000.50'")


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    balance: str


class OperationCreate(BaseModel):
    account_id: str
    type: Literal["income", "expense", "доход", "расход"]
    amount: str = Field(description="Сумма строкой, всегда больше нуля")
    category: str = Field(min_length=1, max_length=64)
    day: date
    comment: str = Field(default="", max_length=255)


class OperationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    account_id: str
    type: str
    amount: str
    category: str
    day: date
    comment: str


class CategoryRead(BaseModel):
    name: str
    amount: str
    share: float


class ReportRead(BaseModel):
    month: str
    operations: int
    income: str
    expense: str
    balance: str
    categories: dict[str, str]
    top_category: CategoryRead | None
    average_expense: str
    warnings: list[str]


class ErrorRead(BaseModel):
    detail: str


def money_str(value: Decimal) -> str:
    """Приводит Decimal к строке с двумя знаками, без разделителя тысяч."""
    return f"{value:.2f}"

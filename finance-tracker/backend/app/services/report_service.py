"""Сервис отчётов.

build_monthly_report — целевая функция для лабораторной по метрикам:
в ней несколько независимых ветвлений, поэтому цикломатическая
сложность получается содержательной (radon cc даёт ранг A/B).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.domain.models import Operation, OperationType
from app.domain.money import percent
from app.repositories.base import Repository
from app.services.operation_service import month_bounds

LARGE_EXPENSE_THRESHOLD = Decimal("50000.00")
MONTHLY_EXPENSE_LIMIT = Decimal("200000.00")


@dataclass(frozen=True)
class CategoryShare:
    name: str
    amount: Decimal
    share: float


@dataclass(frozen=True)
class MonthlyReport:
    month: str
    operations: int
    income: Decimal
    expense: Decimal
    balance: Decimal
    categories: dict[str, Decimal] = field(default_factory=dict)
    top_category: CategoryShare | None = None
    average_expense: Decimal = Decimal("0.00")
    warnings: list[str] = field(default_factory=list)


class ReportService:
    """Считает сводку по месяцу."""

    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    def build_monthly_report(
        self,
        month: str,
        *,
        category: str | None = None,
        account_id: str | None = None,
    ) -> MonthlyReport:
        start, end = month_bounds(month)
        month_operations = self._repository.list_operations(
            start=start, end=end, account_id=account_id
        )

        warnings: list[str] = []
        expenses_all = [
            op for op in month_operations if op.type is OperationType.EXPENSE
        ]
        if expenses_all:
            biggest = max(op.amount for op in expenses_all)
            total_expense_all = sum(
                (op.amount for op in expenses_all), Decimal("0.00")
            )
            if biggest >= LARGE_EXPENSE_THRESHOLD:
                warnings.append("есть отдельная трата больше 50 000 \u20bd")
            if total_expense_all > MONTHLY_EXPENSE_LIMIT:
                warnings.append("расходы за месяц превышают 200 000 \u20bd")

        if not month_operations:
            return MonthlyReport(
                month=month,
                operations=0,
                income=Decimal("0.00"),
                expense=Decimal("0.00"),
                balance=Decimal("0.00"),
                warnings=["за выбранный месяц операций нет"],
            )

        selected = month_operations
        if category is not None:
            needle = category.strip().casefold()
            selected = [op for op in selected if op.category.casefold() == needle]

        income = Decimal("0.00")
        expense = Decimal("0.00")
        for operation in selected:
            if operation.type is OperationType.INCOME:
                income += operation.amount
            else:
                expense += operation.amount

        categories: dict[str, Decimal] = {}
        expense_count = 0
        for operation in selected:
            if operation.type is not OperationType.EXPENSE:
                continue
            expense_count += 1
            categories[operation.category] = (
                categories.get(operation.category, Decimal("0.00")) + operation.amount
            )
        categories = dict(
            sorted(categories.items(), key=lambda item: item[1], reverse=True)
        )

        top_category = None
        if categories:
            name, value = next(iter(categories.items()))
            top_category = CategoryShare(
                name=name, amount=value, share=percent(value, expense)
            )

        average_expense = (
            (expense / expense_count).quantize(Decimal("0.01"))
            if expense_count
            else Decimal("0.00")
        )

        if income and expense > income:
            warnings.append("расходы превышают доходы")

        return MonthlyReport(
            month=month,
            operations=len(selected),
            income=income,
            expense=expense,
            balance=income - expense,
            categories=categories,
            top_category=top_category,
            average_expense=average_expense,
            warnings=warnings,
        )

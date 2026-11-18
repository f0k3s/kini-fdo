"""Сервис операций: проверка правил и создание записей."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.errors import InsufficientFunds, NotFoundError, ValidationError
from app.domain.models import Operation, OperationType
from app.domain.money import to_decimal
from app.repositories.base import Repository

MAX_CATEGORY_LENGTH = 64
MAX_COMMENT_LENGTH = 255


@dataclass(frozen=True)
class OperationFilter:
    """Условия выборки операций."""

    month: str | None = None
    category: str | None = None
    op_type: OperationType | None = None
    account_id: str | None = None


def month_bounds(month: str) -> tuple[date, date]:
    """Возвращает первый и последний день месяца в формате YYYY-MM."""
    if not isinstance(month, str) or len(month) != 7 or month[4] != "-":
        raise ValidationError(f"месяц должен быть в формате YYYY-MM, получено {month!r}")
    try:
        year = int(month[:4])
        number = int(month[5:])
        first = date(year, number, 1)
    except ValueError as exc:
        raise ValidationError(f"некорректный месяц: {month!r}") from exc
    if number == 12:
        last = date(year, 12, 31)
    else:
        next_first = date(year, number + 1, 1)
        last = date.fromordinal(next_first.toordinal() - 1)
    return first, last


class OperationService:
    """Бизнес-правила по операциям."""

    def __init__(self, repository: Repository, today: date | None = None) -> None:
        self._repository = repository
        self._today = today

    def _current_date(self) -> date:
        return self._today or date.today()

    def create(
        self,
        account_id: str,
        op_type: str | OperationType,
        amount: str | Decimal,
        category: str,
        day: date,
        comment: str = "",
    ) -> Operation:
        if self._repository.get_account(account_id) is None:
            raise NotFoundError(f"счёт {account_id} не найден")
        try:
            parsed_type = OperationType.parse(op_type)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        try:
            parsed_amount = to_decimal(amount)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"некорректная сумма: {exc}") from exc
        if parsed_amount <= 0:
            raise ValidationError("сумма операции должна быть больше нуля")
        if not isinstance(category, str):
            raise ValidationError("категория должна быть строкой")
        clean_category = category.strip()
        if not clean_category:
            raise ValidationError("категория не может быть пустой")
        if len(clean_category) > MAX_CATEGORY_LENGTH:
            raise ValidationError(
                f"категория длиннее {MAX_CATEGORY_LENGTH} символов"
            )
        if len(comment) > MAX_COMMENT_LENGTH:
            raise ValidationError(f"комментарий длиннее {MAX_COMMENT_LENGTH} символов")
        if not isinstance(day, date):
            raise ValidationError("дата операции должна быть типа date")
        if day > self._current_date():
            raise ValidationError("дата операции не может быть в будущем")

        if parsed_type is OperationType.EXPENSE:
            balance = self._repository.balance(account_id) or Decimal("0.00")
            if parsed_amount > balance:
                raise InsufficientFunds(
                    f"недостаточно средств: на счёте {balance}, требуется {parsed_amount}"
                )

        return self._repository.create_operation(
            account_id=account_id,
            op_type=parsed_type,
            amount=parsed_amount,
            category=clean_category,
            day=day,
            comment=comment.strip(),
        )

    def get(self, operation_id: str) -> Operation:
        operation = self._repository.get_operation(operation_id)
        if operation is None:
            raise NotFoundError(f"операция {operation_id} не найдена")
        return operation

    def delete(self, operation_id: str) -> None:
        self.get(operation_id)
        self._repository.delete_operation(operation_id)

    def list(self, filters: OperationFilter | None = None) -> list[Operation]:
        filters = filters or OperationFilter()
        start = end = None
        if filters.month is not None:
            start, end = month_bounds(filters.month)
        operations = self._repository.list_operations(
            start=start, end=end, account_id=filters.account_id
        )
        if filters.category is not None:
            needle = filters.category.strip().casefold()
            operations = [
                op for op in operations if op.category.casefold() == needle
            ]
        if filters.op_type is not None:
            operations = [op for op in operations if op.type is filters.op_type]
        return operations

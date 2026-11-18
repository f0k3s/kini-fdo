"""Юнит-тесты сервиса операций и границ месяца."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.errors import InsufficientFunds, NotFoundError, ValidationError
from app.domain.models import OperationType
from app.services.operation_service import (
    OperationFilter,
    OperationService,
    month_bounds,
)


@pytest.fixture
def account(repository):
    return repository.create_account("Основной", Decimal("1000.00"))


@pytest.fixture
def service(repository, today):
    return OperationService(repository, today=today)


class TestMonthBounds:
    def test_regular_month(self):
        assert month_bounds("2026-11") == (date(2026, 11, 1), date(2026, 11, 30))

    def test_december(self):
        assert month_bounds("2026-12") == (date(2026, 12, 1), date(2026, 12, 31))

    def test_february_common_year(self):
        assert month_bounds("2027-02") == (date(2027, 2, 1), date(2027, 2, 28))

    def test_february_leap_year(self):
        assert month_bounds("2028-02") == (date(2028, 2, 1), date(2028, 2, 29))

    def test_wrong_format_rejected(self):
        with pytest.raises(ValidationError):
            month_bounds("2026-1")

    def test_month_13_rejected(self):
        with pytest.raises(ValidationError):
            month_bounds("2026-13")

    def test_non_numeric_rejected(self):
        with pytest.raises(ValidationError):
            month_bounds("абв-гд")


class TestCreate:
    def test_income_created(self, service, account):
        operation = service.create(
            account.id, "income", "500", "зарплата", date(2026, 11, 1)
        )
        assert operation.type is OperationType.INCOME
        assert operation.amount == Decimal("500.00")

    def test_russian_type_alias(self, service, account):
        operation = service.create(
            account.id, "расход", "100", "продукты", date(2026, 11, 1)
        )
        assert operation.type is OperationType.EXPENSE

    def test_comment_trimmed(self, service, account):
        operation = service.create(
            account.id, "income", "1", "прочее", date(2026, 11, 1), "  заметка  "
        )
        assert operation.comment == "заметка"

    def test_unknown_account_rejected(self, service):
        with pytest.raises(NotFoundError):
            service.create("нет-счёта", "income", "1", "прочее", date(2026, 11, 1))

    def test_unknown_type_rejected(self, service, account):
        with pytest.raises(ValidationError):
            service.create(account.id, "подарок", "1", "прочее", date(2026, 11, 1))

    def test_zero_amount_rejected(self, service, account):
        with pytest.raises(ValidationError):
            service.create(account.id, "income", "0", "прочее", date(2026, 11, 1))

    def test_negative_amount_rejected(self, service, account):
        with pytest.raises(ValidationError):
            service.create(account.id, "income", "-5", "прочее", date(2026, 11, 1))

    def test_garbage_amount_rejected(self, service, account):
        with pytest.raises(ValidationError):
            service.create(account.id, "income", "немного", "прочее", date(2026, 11, 1))

    def test_empty_category_rejected(self, service, account):
        with pytest.raises(ValidationError):
            service.create(account.id, "income", "1", "   ", date(2026, 11, 1))

    def test_too_long_category_rejected(self, service, account):
        with pytest.raises(ValidationError):
            service.create(account.id, "income", "1", "к" * 65, date(2026, 11, 1))

    def test_too_long_comment_rejected(self, service, account):
        with pytest.raises(ValidationError):
            service.create(account.id, "income", "1", "прочее", date(2026, 11, 1), "к" * 256)

    def test_future_date_rejected(self, service, account):
        with pytest.raises(ValidationError):
            service.create(account.id, "income", "1", "прочее", date(2026, 11, 18))

    def test_today_is_allowed(self, service, account):
        operation = service.create(account.id, "income", "1", "прочее", date(2026, 11, 17))
        assert operation.day == date(2026, 11, 17)

    def test_expense_above_balance_rejected(self, service, account):
        with pytest.raises(InsufficientFunds):
            service.create(account.id, "expense", "1000.01", "продукты", date(2026, 11, 1))

    def test_expense_equal_to_balance_allowed(self, service, account):
        operation = service.create(
            account.id, "expense", "1000", "продукты", date(2026, 11, 1)
        )
        assert operation.amount == Decimal("1000.00")

    def test_expense_uses_balance_after_income(self, service, account):
        service.create(account.id, "income", "500", "зарплата", date(2026, 11, 1))
        operation = service.create(
            account.id, "expense", "1500", "техника", date(2026, 11, 2)
        )
        assert operation.amount == Decimal("1500.00")


class TestList:
    def test_filters_by_month(self, service, account):
        service.create(account.id, "income", "10", "прочее", date(2026, 10, 5))
        service.create(account.id, "income", "20", "прочее", date(2026, 11, 5))
        found = service.list(OperationFilter(month="2026-11"))
        assert [op.amount for op in found] == [Decimal("20.00")]

    def test_filters_by_category_case_insensitive(self, service, account):
        service.create(account.id, "expense", "10", "Продукты", date(2026, 11, 1))
        service.create(account.id, "expense", "20", "транспорт", date(2026, 11, 2))
        found = service.list(OperationFilter(category="ПРОДУКТЫ"))
        assert len(found) == 1

    def test_filters_by_type(self, service, account):
        service.create(account.id, "income", "10", "прочее", date(2026, 11, 1))
        service.create(account.id, "expense", "20", "прочее", date(2026, 11, 2))
        found = service.list(OperationFilter(op_type=OperationType.EXPENSE))
        assert [op.amount for op in found] == [Decimal("20.00")]

    def test_invalid_month_rejected(self, service):
        with pytest.raises(ValidationError):
            service.list(OperationFilter(month="2026-99"))


class TestDelete:
    def test_delete_removes_operation(self, service, account):
        operation = service.create(
            account.id, "income", "10", "прочее", date(2026, 11, 1)
        )
        service.delete(operation.id)
        with pytest.raises(NotFoundError):
            service.get(operation.id)

    def test_delete_missing_raises(self, service):
        with pytest.raises(NotFoundError):
            service.delete("нет-такой")

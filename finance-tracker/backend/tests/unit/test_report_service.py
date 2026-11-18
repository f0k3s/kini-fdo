"""Юнит-тесты месячного отчёта.

Здесь же проверяются краевые случаи: пустой месяц, деление на ноль,
високосный февраль и фильтр по категории.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.models import OperationType
from app.services.report_service import ReportService


@pytest.fixture
def account(repository):
    return repository.create_account("Основной", Decimal("0.00"))


@pytest.fixture
def service(repository):
    return ReportService(repository)


def add(repository, account_id, op_type, amount, category, day):
    return repository.create_operation(
        account_id=account_id,
        op_type=op_type,
        amount=Decimal(amount),
        category=category,
        day=day,
    )


class TestEmptyMonth:
    def test_returns_zeros_and_warning(self, service, account):
        report = service.build_monthly_report("2026-11")
        assert report.income == Decimal("0.00")
        assert report.expense == Decimal("0.00")
        assert report.balance == Decimal("0.00")
        assert report.operations == 0
        assert report.top_category is None
        assert report.warnings == ["за выбранный месяц операций нет"]

    def test_zero_total_share_does_not_divide_by_zero(
        self, repository, service, account
    ):
        add(repository, account.id, OperationType.INCOME, "100", "зарплата", date(2026, 11, 1))
        report = service.build_monthly_report("2026-11")
        assert report.expense == Decimal("0.00")
        assert report.top_category is None


class TestTotals:
    def test_income_and_expense(self, repository, service, account):
        add(repository, account.id, OperationType.INCOME, "1000", "зарплата", date(2026, 11, 1))
        add(repository, account.id, OperationType.EXPENSE, "300", "продукты", date(2026, 11, 2))
        report = service.build_monthly_report("2026-11")
        assert report.income == Decimal("1000.00")
        assert report.expense == Decimal("300.00")
        assert report.balance == Decimal("700.00")

    def test_other_month_not_counted(self, repository, service, account):
        add(repository, account.id, OperationType.INCOME, "1000", "зарплата", date(2026, 10, 1))
        report = service.build_monthly_report("2026-11")
        assert report.operations == 0

    def test_average_expense(self, repository, service, account):
        add(repository, account.id, OperationType.EXPENSE, "100", "продукты", date(2026, 11, 2))
        add(repository, account.id, OperationType.EXPENSE, "200", "транспорт", date(2026, 11, 3))
        report = service.build_monthly_report("2026-11")
        assert report.average_expense == Decimal("150.00")

    def test_leap_february_last_day_counted(self, repository, service, account):
        add(repository, account.id, OperationType.EXPENSE, "10", "прочее", date(2028, 2, 29))
        report = service.build_monthly_report("2028-02")
        assert report.operations == 1


class TestCategories:
    def test_sorted_by_amount_desc(self, repository, service, account):
        add(repository, account.id, OperationType.EXPENSE, "100", "продукты", date(2026, 11, 2))
        add(repository, account.id, OperationType.EXPENSE, "300", "техника", date(2026, 11, 3))
        report = service.build_monthly_report("2026-11")
        assert list(report.categories) == ["техника", "продукты"]

    def test_top_category_share(self, repository, service, account):
        add(repository, account.id, OperationType.EXPENSE, "300", "техника", date(2026, 11, 3))
        add(repository, account.id, OperationType.EXPENSE, "100", "продукты", date(2026, 11, 2))
        report = service.build_monthly_report("2026-11")
        assert report.top_category.name == "техника"
        assert report.top_category.share == 75.0

    def test_income_not_in_categories(self, repository, service, account):
        add(repository, account.id, OperationType.INCOME, "1000", "зарплата", date(2026, 11, 1))
        report = service.build_monthly_report("2026-11")
        assert report.categories == {}

    def test_category_filter_narrows_totals(self, repository, service, account):
        add(repository, account.id, OperationType.EXPENSE, "300", "техника", date(2026, 11, 3))
        add(repository, account.id, OperationType.EXPENSE, "100", "продукты", date(2026, 11, 2))
        report = service.build_monthly_report("2026-11", category="ПРОДУКТЫ")
        assert report.expense == Decimal("100.00")
        assert list(report.categories) == ["продукты"]

    def test_category_filter_keeps_month_level_warnings(self, repository, service, account):
        add(repository, account.id, OperationType.EXPENSE, "60000", "техника", date(2026, 11, 3))
        add(repository, account.id, OperationType.EXPENSE, "100", "продукты", date(2026, 11, 2))
        report = service.build_monthly_report("2026-11", category="продукты")
        assert "есть отдельная трата больше 50 000 \u20bd" in report.warnings


class TestWarnings:
    def test_large_single_expense(self, repository, service, account):
        add(repository, account.id, OperationType.EXPENSE, "50000", "техника", date(2026, 11, 3))
        report = service.build_monthly_report("2026-11")
        assert "есть отдельная трата больше 50 000 \u20bd" in report.warnings

    def test_threshold_not_reached(self, repository, service, account):
        add(repository, account.id, OperationType.EXPENSE, "49999.99", "техника", date(2026, 11, 3))
        report = service.build_monthly_report("2026-11")
        assert "есть отдельная трата больше 50 000 \u20bd" not in report.warnings

    def test_monthly_expense_limit(self, repository, service, account):
        for day in range(1, 6):
            add(repository, account.id, OperationType.EXPENSE, "49999", "техника", date(2026, 11, day))
        report = service.build_monthly_report("2026-11")
        assert "расходы за месяц превышают 200 000 \u20bd" in report.warnings

    def test_expense_over_income(self, repository, service, account):
        add(repository, account.id, OperationType.INCOME, "100", "зарплата", date(2026, 11, 1))
        add(repository, account.id, OperationType.EXPENSE, "300", "продукты", date(2026, 11, 2))
        report = service.build_monthly_report("2026-11")
        assert "расходы превышают доходы" in report.warnings

    def test_no_false_warning_when_income_covers(self, repository, service, account):
        add(repository, account.id, OperationType.INCOME, "1000", "зарплата", date(2026, 11, 1))
        add(repository, account.id, OperationType.EXPENSE, "300", "продукты", date(2026, 11, 2))
        report = service.build_monthly_report("2026-11")
        assert "расходы превышают доходы" not in report.warnings


class TestAccountFilter:
    def test_only_selected_account(self, repository, service):
        first = repository.create_account("Первый", Decimal("0.00"))
        second = repository.create_account("Второй", Decimal("0.00"))
        add(repository, first.id, OperationType.EXPENSE, "100", "продукты", date(2026, 11, 2))
        add(repository, second.id, OperationType.EXPENSE, "200", "техника", date(2026, 11, 3))
        report = service.build_monthly_report("2026-11", account_id=first.id)
        assert report.expense == Decimal("100.00")

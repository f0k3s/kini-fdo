"""Юнит-тесты сервиса счетов. Репозиторий — в памяти, без базы и сети."""

from decimal import Decimal

import pytest

from app.domain.errors import NotFoundError, ValidationError
from app.services.account_service import AccountService


@pytest.fixture
def service(repository):
    return AccountService(repository)


class TestCreate:
    def test_creates_account_with_balance(self, service):
        account = service.create("Основной", "1000.50")
        assert account.name == "Основной"
        assert account.initial_balance == Decimal("1000.50")

    def test_trims_name(self, service):
        assert service.create("  Кошелёк  ").name == "Кошелёк"

    def test_default_balance_is_zero(self, service):
        assert service.create("Пустой").initial_balance == Decimal("0.00")

    def test_accepts_decimal_balance(self, service):
        account = service.create("Вклад", Decimal("500"))
        assert account.initial_balance == Decimal("500.00")

    def test_empty_name_rejected(self, service):
        with pytest.raises(ValidationError):
            service.create("   ")

    def test_too_long_name_rejected(self, service):
        with pytest.raises(ValidationError):
            service.create("а" * 101)

    def test_non_string_name_rejected(self, service):
        with pytest.raises(ValidationError):
            service.create(123)

    def test_negative_balance_rejected(self, service):
        with pytest.raises(ValidationError):
            service.create("Долг", "-1")

    def test_garbage_balance_rejected(self, service):
        with pytest.raises(ValidationError):
            service.create("Странный", "много")

    def test_boundary_name_length_ok(self, service):
        assert len(service.create("а" * 100).name) == 100


class TestRead:
    def test_get_missing_raises(self, service):
        with pytest.raises(NotFoundError):
            service.get("нет-такого")

    def test_get_view_returns_balance(self, service):
        account = service.create("Основной", "100")
        view = service.get_view(account.id)
        assert view.balance == Decimal("100.00")

    def test_list_is_empty_initially(self, service):
        assert service.list() == []

    def test_list_contains_created(self, service):
        service.create("А")
        service.create("Б")
        assert len(service.list()) == 2


class TestDelete:
    def test_delete_removes_account(self, service):
        account = service.create("Временный")
        service.delete(account.id)
        with pytest.raises(NotFoundError):
            service.get(account.id)

    def test_delete_missing_raises(self, service):
        with pytest.raises(NotFoundError):
            service.delete("нет-такого")

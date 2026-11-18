from datetime import date
from decimal import Decimal

import pytest

from app.domain.models import Account, Operation, OperationType
from app.services.notification_service import NotificationService


@pytest.fixture
def account():
    return Account(
        id="account-1",
        name="Основной",
        initial_balance=Decimal("250000.00"),
    )


def test_large_expense_creates_one_notification(account):
    service = NotificationService()
    operation = Operation(
        id="operation-1",
        account_id=account.id,
        type=OperationType.EXPENSE,
        amount=Decimal("125000.00"),
        category="Техника",
        day=date(2026, 11, 18),
        comment="Покупка ноутбука",
    )

    service.notify_large_expense(operation, account)

    expected = ["Крупная трата: 125000.00 ₽ на счёте Основной"]
    assert service.get_notifications() == expected

    notifications = service.get_notifications()
    notifications.clear()
    assert service.get_notifications() == expected


def test_small_expense_creates_no_notification(account):
    service = NotificationService()
    operation = Operation(
        id="operation-2",
        account_id=account.id,
        type=OperationType.EXPENSE,
        amount=Decimal("5000.00"),
        category="Продукты",
        day=date(2026, 11, 18),
        comment="Покупки в супермаркете",
    )

    service.notify_large_expense(operation, account)

    assert service.get_notifications() == []

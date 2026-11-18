from decimal import Decimal

from app.domain.models import Account, Operation


class NotificationService:
    threshold = Decimal("100000.00")

    def __init__(self) -> None:
        self.notifications: list[str] = []

    def notify_large_expense(self, operation: Operation, account: Account) -> None:
        if operation.amount >= self.threshold:
            self.notifications.append(
                f"Крупная трата: {operation.amount} ₽ на счёте {account.name}"
            )

    def get_notifications(self) -> list[str]:
        return self.notifications.copy()

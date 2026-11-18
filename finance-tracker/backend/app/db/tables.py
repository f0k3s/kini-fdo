"""ORM-модели SQLAlchemy 2.0.

Суммы хранятся целыми копейками: тип Numeric на SQLite теряет точность
на больших значениях, а INTEGER — нет.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.models import OperationType


class Base(DeclarativeBase):
    """Базовый класс всех ORM-моделей."""


def new_id() -> str:
    return str(uuid.uuid4())


class AccountRow(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("initial_balance_cents >= 0", name="initial_balance_nonnegative"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100))
    initial_balance_cents: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    operations: Mapped[list["OperationRow"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class OperationRow(Base):
    __tablename__ = "operations"
    __table_args__ = (CheckConstraint("amount_cents > 0", name="amount_positive"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[OperationType] = mapped_column(
        SAEnum(
            OperationType,
            values_callable=lambda members: [m.value for m in members],
            native_enum=False,
            length=16,
        )
    )
    amount_cents: Mapped[int]
    category: Mapped[str] = mapped_column(String(64))
    day: Mapped[date] = mapped_column(index=True)
    comment: Mapped[str] = mapped_column(String(255), default="")

    account: Mapped[AccountRow] = relationship(back_populates="operations")

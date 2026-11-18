"""Репозиторий на SQLAlchemy.

Каждый метод открывает собственную сессию через фабрику: так сервис
не зависит от жизненного цикла сессии и его проще вызывать из тестов.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.tables import AccountRow, OperationRow
from app.domain.models import Account, Operation, OperationType
from app.domain.money import from_cents, to_cents


def _account_from_row(row: AccountRow) -> Account:
    return Account(
        id=row.id,
        name=row.name,
        initial_balance=from_cents(row.initial_balance_cents),
    )


def _operation_from_row(row: OperationRow) -> Operation:
    return Operation(
        id=row.id,
        account_id=row.account_id,
        type=row.type,
        amount=from_cents(row.amount_cents),
        category=row.category,
        day=row.day,
        comment=row.comment,
    )


class SqlRepository:
    """Хранилище в SQLite/PostgreSQL через SQLAlchemy ORM."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_account(self, name: str, initial_balance: Decimal) -> Account:
        with self._session_factory() as session:
            row = AccountRow(
                name=name, initial_balance_cents=to_cents(initial_balance)
            )
            session.add(row)
            session.commit()
            return _account_from_row(row)

    def get_account(self, account_id: str) -> Account | None:
        with self._session_factory() as session:
            row = session.get(AccountRow, account_id)
            return _account_from_row(row) if row else None

    def list_accounts(self) -> list[Account]:
        with self._session_factory() as session:
            rows = session.scalars(select(AccountRow).order_by(AccountRow.name))
            return [_account_from_row(row) for row in rows]

    def delete_account(self, account_id: str) -> bool:
        with self._session_factory() as session:
            row = session.get(AccountRow, account_id)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True

    def create_operation(
        self,
        account_id: str,
        op_type: OperationType,
        amount: Decimal,
        category: str,
        day: date,
        comment: str = "",
    ) -> Operation:
        with self._session_factory() as session:
            row = OperationRow(
                account_id=account_id,
                type=op_type,
                amount_cents=to_cents(amount),
                category=category,
                day=day,
                comment=comment,
            )
            session.add(row)
            session.commit()
            return _operation_from_row(row)

    def get_operation(self, operation_id: str) -> Operation | None:
        with self._session_factory() as session:
            row = session.get(OperationRow, operation_id)
            return _operation_from_row(row) if row else None

    def list_operations(
        self,
        start: date | None = None,
        end: date | None = None,
        account_id: str | None = None,
    ) -> list[Operation]:
        query = select(OperationRow)
        if start is not None:
            query = query.where(OperationRow.day >= start)
        if end is not None:
            query = query.where(OperationRow.day <= end)
        if account_id is not None:
            query = query.where(OperationRow.account_id == account_id)
        query = query.order_by(OperationRow.day, OperationRow.id)
        with self._session_factory() as session:
            return [_operation_from_row(row) for row in session.scalars(query)]

    def delete_operation(self, operation_id: str) -> bool:
        with self._session_factory() as session:
            if session.get(OperationRow, operation_id) is None:
                return False
            session.execute(
                delete(OperationRow).where(OperationRow.id == operation_id)
            )
            session.commit()
            return True

    def balance(self, account_id: str) -> Decimal | None:
        signed = case(
            (OperationRow.type == OperationType.INCOME, OperationRow.amount_cents),
            else_=-OperationRow.amount_cents,
        )
        with self._session_factory() as session:
            account = session.get(AccountRow, account_id)
            if account is None:
                return None
            flow = session.scalar(
                select(func.coalesce(func.sum(signed), 0)).where(
                    OperationRow.account_id == account_id
                )
            )
            return from_cents(account.initial_balance_cents + int(flow or 0))

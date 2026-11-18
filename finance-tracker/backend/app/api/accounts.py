"""Роутер счетов. Только распаковка запроса и сериализация ответа."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import get_account_service
from app.schemas import AccountCreate, AccountRead, money_str
from app.services.account_service import AccountService

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    service: AccountService = Depends(get_account_service),
) -> AccountRead:
    account = service.create(payload.name, payload.initial_balance)
    balance = service.get_view(account.id).balance
    return AccountRead(id=account.id, name=account.name, balance=money_str(balance))


@router.get("", response_model=list[AccountRead])
def list_accounts(
    service: AccountService = Depends(get_account_service),
) -> list[AccountRead]:
    return [
        AccountRead(
            id=view.account.id, name=view.account.name, balance=money_str(view.balance)
        )
        for view in service.list()
    ]


@router.get("/{account_id}", response_model=AccountRead)
def get_account(
    account_id: str, service: AccountService = Depends(get_account_service)
) -> AccountRead:
    view = service.get_view(account_id)
    return AccountRead(
        id=view.account.id, name=view.account.name, balance=money_str(view.balance)
    )


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: str, service: AccountService = Depends(get_account_service)
) -> None:
    service.delete(account_id)

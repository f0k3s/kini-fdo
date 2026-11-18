"""Роутер операций."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_operation_service
from app.domain.models import OperationType
from app.schemas import OperationCreate, OperationRead, money_str
from app.services.operation_service import OperationFilter, OperationService

router = APIRouter(prefix="/api/operations", tags=["operations"])


def _to_read(operation) -> OperationRead:
    return OperationRead(
        id=operation.id,
        account_id=operation.account_id,
        type=operation.type.value,
        amount=money_str(operation.amount),
        category=operation.category,
        day=operation.day,
        comment=operation.comment,
    )


@router.post("", response_model=OperationRead, status_code=status.HTTP_201_CREATED)
def create_operation(
    payload: OperationCreate,
    service: OperationService = Depends(get_operation_service),
) -> OperationRead:
    operation = service.create(
        account_id=payload.account_id,
        op_type=payload.type,
        amount=payload.amount,
        category=payload.category,
        day=payload.day,
        comment=payload.comment,
    )
    return _to_read(operation)


@router.get("", response_model=list[OperationRead])
def list_operations(
    month: str | None = Query(default=None, description="Месяц в формате YYYY-MM"),
    category: str | None = Query(default=None),
    op_type: OperationType | None = Query(default=None, alias="type"),
    account_id: str | None = Query(default=None),
    service: OperationService = Depends(get_operation_service),
) -> list[OperationRead]:
    filters = OperationFilter(
        month=month, category=category, op_type=op_type, account_id=account_id
    )
    return [_to_read(operation) for operation in service.list(filters)]


@router.get("/{operation_id}", response_model=OperationRead)
def get_operation(
    operation_id: str, service: OperationService = Depends(get_operation_service)
) -> OperationRead:
    return _to_read(service.get(operation_id))


@router.delete("/{operation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_operation(
    operation_id: str, service: OperationService = Depends(get_operation_service)
) -> None:
    service.delete(operation_id)
